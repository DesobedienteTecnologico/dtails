import os, threading, time, re, subprocess
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Callable

Sink = Callable[[str], None]


# Streaming helpers

def _emit(sink: Optional[Sink], text: str) -> None:
    if sink:
        sink(text)


def _log_title(title: str) -> str:
    line = "-" * max(16, len(title))
    return f"\n{line}\n{title}\n{line}\n"


def _run_stream(cmd: str, sink: Optional[Sink], cwd: Optional[str] = None) -> str:
    header = f"$ {cmd}\n"
    _emit(sink, header)
    buf = [header]

    try:
        proc = subprocess.Popen(
            cmd,
            shell=True,
            cwd=cwd,
            stdin=subprocess.DEVNULL,   # builds never read stdin...
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
        )
        if proc.stdout:
            for line in proc.stdout:
                _emit(sink, line)
                buf.append(line)
        proc.wait()
        footer = f"[{'OK' if proc.returncode == 0 else f'EXIT {proc.returncode}'}]\n"
        _emit(sink, footer)
        buf.append(footer)
        return "".join(buf)
    except Exception as e:
        line = f"[ERROR] {e}\n"
        _emit(sink, line)
        buf.append(line)
        return "".join(buf)


def _ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def _script_path(cwd: Optional[str] = None) -> Path:
    base = Path(cwd).resolve() if cwd else Path.cwd()
    return base / "shared_with_chroot" / "script"


def _reset_script(sink: Optional[Sink], epoch: int, cwd: Optional[str] = None) -> None:
    sp = _script_path(cwd)
    _ensure_dir(sp.parent)
    # SOURCE_DATE_EPOCH makes build-time generators deterministic inside the
    # chroot (e.g. Python writes hash-based .pyc instead of mtime-based ones),
    # so installed software repacks reproducibly without deleting anything.
    sp.write_text(
        "#!/bin/bash\n"
        "export PATH=$PATH:/usr/local/sbin:/usr/sbin:/sbin\n"
        f"export SOURCE_DATE_EPOCH={epoch}\n\n",
        encoding="utf-8",
    )
    _emit(sink, f"[INFO] Script file created: {sp}\n")

def _end_script(sink: Optional[Sink], cwd: Optional[str] = None) -> None:
    _append_script_line("\nrm -rf ~/.bash_history", sink, cwd)

def _append_script_line(line: str, sink: Optional[Sink], cwd: Optional[str] = None) -> None:
    sp = _script_path(cwd)
    with open(sp, "a", encoding="utf-8") as f:
        f.write((line or "").rstrip() + "\n")
    _emit(sink, f"[script (chroot)] {line.rstrip()}\n")


def _as_list(val: Any) -> List[str]:
    if val is None:
        return []
    if isinstance(val, str):
        return [val]
    if isinstance(val, list):
        return [x for x in val if isinstance(x, str)]
    return []

def _category_meta_map(options_json: Dict[str, Any]) -> Dict[str, Dict[str, str]]:
    out: Dict[str, Dict[str, str]] = {}
    add = (options_json or {}).get("add_software", {})
    cats = (add.get("categories") or []) if isinstance(add, dict) else []

    default_menu_files = {
        "bitcoin": "Bitcoin.menu",
        "nostr": "Nostr.menu",
        "monero": "Monero.menu",
    }

    for cat in cats:
        if not isinstance(cat, dict):
            continue
        key = (cat.get("key") or "").strip().lower()
        title = (cat.get("title") or key.title()).strip()
        menu_file = cat.get("menu_file")
        if menu_file is None:
            menu_file = default_menu_files.get(key, "")
        else:
            menu_file = str(menu_file).strip()
        out[key] = {"title": title, "menu_file": menu_file}
    return out


def _item_category_index(options_json: Dict[str, Any]) -> Dict[str, str]:
    out: Dict[str, str] = {}
    add = (options_json or {}).get("add_software", {})
    cats = (add.get("categories") or []) if isinstance(add, dict) else []
    for cat in cats:
        if not isinstance(cat, dict):
            continue
        key = (cat.get("key") or "").strip().lower()
        items = cat.get("items") or []
        for it in items:
            if not isinstance(it, dict):
                continue
            nm = (it.get("name") or "").strip().lower()
            if nm and key:
                out[nm] = key
    return out


# Reproducibility helpers
def _source_date_epoch(image_path: str) -> int:
    return 1231006505


def _fat_serial(epoch: int) -> str:
    """8-hex-digit FAT32 volume id derived from the epoch (mformat -N)."""
    return f"{epoch & 0xFFFFFFFF:08x}"


def _guid(epoch: int, salt: str) -> str:
    import hashlib, uuid
    h = hashlib.sha256(f"dtails:{epoch}:{salt}".encode()).digest()[:16]
    return str(uuid.UUID(bytes=h)).upper()


def _original_disk_guid(image_path: str) -> Optional[str]:
    try:
        out = subprocess.check_output(
            f"sgdisk --print '{image_path}'", shell=True, text=True,
            stderr=subprocess.DEVNULL
        )
        for line in out.splitlines():
            if line.startswith("Disk identifier (GUID)"):
                return line.split(":", 1)[1].strip()
    except Exception:
        pass
    return None


def _pin_gpt_guids(target: str, sink: Optional[Sink], cwd: str, epoch: int,
                   disk_guid: Optional[str] = None) -> None:
    disk = disk_guid or _guid(epoch, 'disk')
    _run_stream(
        f"sudo sgdisk -U {disk} -u 1:{_guid(epoch, 'part1')} "
        f"-A 1:set:0 -A 1:set:2 -A 1:set:60 -A 1:set:62 -A 1:set:63 '{target}'",
        sink, cwd
    )


def _format_and_copy_fat(target: str, sink: Optional[Sink], cwd: str, epoch: int) -> None:
    serial = _fat_serial(epoch)
    # mkfs.fat expects the serial as an 8-hex-digit string (XXXXXXXX)
    _run_stream(
        f"sudo env SOURCE_DATE_EPOCH={epoch} mkfs.fat -F 32 -v -n TAILS -i {serial} '{target}'",
        sink, cwd
    )
    cmd = (
        "sudo bash -c '"
        f"set -e; export SOURCE_DATE_EPOCH={epoch}; cd future_iso; "
        f"find . -mindepth 1 -type d | LC_ALL=C sort | while IFS= read -r d; do mmd -i \"{target}\" \"::${{d#./}}\"; done; "
        f"find . ! -type d | LC_ALL=C sort | while IFS= read -r f; do mcopy -i \"{target}\" -m -p -Q -o \"$f\" \"::${{f#./}}\"; done"
        "'"
    )
    _run_stream(cmd, sink, cwd)


def _build_iso(sink: Optional[Sink], cwd: str, epoch: int) -> None:
    """Build DTails.iso. Uses xorriso (reproducible) when available, falling
    back to genisoimage (not byte-reproducible) otherwise."""
    serial = _fat_serial(epoch)
    mdate = time.strftime("%Y%m%d%H%M%S00", time.gmtime(epoch))
    has_xorriso = subprocess.call("command -v xorriso >/dev/null 2>&1", shell=True) == 0

    _emit(sink, "\n[INFO] Building the final .iso image…\n")
    if has_xorriso:
        _run_stream(
            "sudo xorriso -as mkisofs -r -J "
            f"--modification-date={mdate} "
            "-b isolinux/isolinux.bin -c isolinux/boot.cat "
            "-no-emul-boot -boot-load-size 4 -boot-info-table "
            "-o DTails.iso future_iso",
            sink, cwd
        )
    else:
        _emit(sink, "[WARN] xorriso not found; using genisoimage — the ISO will NOT be byte-reproducible.\n")
        _emit(sink, "[WARN] You may see 'unrecognize xattr prefix system.posix_acl_access' — harmless when scripted.\n")
        _run_stream(
            "sudo genisoimage -r -J -b isolinux/isolinux.bin -c isolinux/boot.cat "
            "-no-emul-boot -boot-load-size 4 -boot-info-table -o DTails.iso future_iso",
            sink, cwd
        )
    # Fix the MBR disk id so the hybrid image is also deterministic.
    _run_stream(f"isohybrid --id {serial} DTails.iso", sink, cwd)
    _emit(sink, "[INFO] DTails.iso image created.\n")


# Directories that the chroot installs perturb non-deterministically (logs,
# machine-id, apt indexes/caches). Instead of deleting them — which would make
# the output differ from the base image — we snapshot their pristine state
# before the installs and restore it afterwards, so they end up byte-identical
# to the original image (no files added or removed). Newly installed software
# (under /usr, /etc, /var/lib/dpkg, …) is left untouched.
_PRISTINE_PATHS = [
    "var/log",
    "etc/machine-id",
    "var/lib/dbus/machine-id",
    "var/lib/apt/lists",
    "var/cache/apt",
    "var/cache/ldconfig",
]
_PRISTINE_TAR = "pristine_repro.tar"


def _snapshot_pristine(logs: List[str], sink: Optional[Sink], cwd: str) -> None:
    _emit(sink, _log_title("Snapshot pristine state (for reproducibility)"))
    checks = " ".join(_PRISTINE_PATHS)
    logs.append(_run_stream(
        "sudo bash -c '"
        f"p=\"\"; for x in {checks}; do [ -e system_to_edit/\"$x\" ] && p=\"$p $x\"; done; "
        f"tar --numeric-owner -C system_to_edit -cf {_PRISTINE_TAR} $p'",
        sink, cwd
    ))


def _restore_pristine(logs: List[str], sink: Optional[Sink], cwd: str) -> None:
    _emit(sink, _log_title("Restore pristine state (logs, machine-id, apt)"))
    rm_targets = " ".join(f"system_to_edit/{p}" for p in _PRISTINE_PATHS)
    logs.append(_run_stream(f"sudo rm -rf {rm_targets}", sink, cwd))
    logs.append(_run_stream(f"sudo tar --numeric-owner -C system_to_edit -xpf {_PRISTINE_TAR}", sink, cwd))
    logs.append(_run_stream(f"rm -f {_PRISTINE_TAR}", sink, cwd))


def _flash_future_iso_direct_to_device(device_path: str, sink: Optional[Sink], cwd: str, epoch: int,
                                       disk_guid: Optional[str] = None) -> None:
    if not device_path or not device_path.startswith("/dev/"):
        _emit(sink, f"[ERROR] Invalid device path: {device_path!r}\n")
        return

    _emit(sink, _log_title(f"Direct flash (partition+format) to: {device_path}"))

    # Unmount anything on the device
    _run_stream(
        "set -euo pipefail; "
        f"for p in $(lsblk -ln {device_path} | awk '{{print $1}}'); do "
        "  mp=$(lsblk -no MOUNTPOINT /dev/${p} 2>/dev/null || true); "
        "  if [ -n \"$mp\" ]; then echo umount /dev/${p}; sudo umount -lf /dev/${p} || true; fi; "
        "done",
        sink, cwd
    )

    try:
        out_sz = subprocess.check_output(["du", "-sb", "future_iso"], text=True, cwd=cwd).split()[0]
        content_bytes = int(out_sz)
    except Exception:
        content_bytes = 0
    buffer_bytes = 10 * 1024 * 1024
    part_bytes = content_bytes + buffer_bytes
    one_mib = 1024 * 1024
    part_mib = (part_bytes + one_mib - 1) // one_mib

    start_mib = 1
    end_mib = start_mib + part_mib

    _emit(sink, f"[INFO] future_iso: {content_bytes/1e6:.1f} MB; partition target: {part_bytes/1e6:.1f} MB (~{part_mib} MiB)\n")

    _run_stream(f"sudo parted -s '{device_path}' mklabel gpt", sink, cwd)
    _run_stream(f"sudo parted -s '{device_path}' mkpart primary fat32 0% {end_mib}MiB name 1 Tails", sink, cwd)
    _run_stream(f"sudo parted -s '{device_path}' set 1 boot on", sink, cwd)
    _run_stream(f"sudo parted -s '{device_path}' set 1 hidden on", sink, cwd)
    _run_stream(f"sudo parted -s '{device_path}' set 1 legacy_boot on", sink, cwd)
    _run_stream(f"sudo parted -s '{device_path}' set 1 esp on", sink, cwd)
    _run_stream(f"sudo parted -s '{device_path}' set 1 no_automount on", sink, cwd)

    # Pin GPT GUIDs (keep base disk GUID so Tails repartitions on first boot)
    _pin_gpt_guids(device_path, sink, cwd, epoch, disk_guid)

    # Make sure the partition node appears (sda1 vs mmcblk0p1)
    _run_stream(f"sudo partprobe '{device_path}' || true", sink, cwd)
    _run_stream("sudo udevadm settle || true", sink, cwd)

    # Resolve partition path robustly
    part_candidates = [f"{device_path}1", f"{device_path}p1"]
    part1 = ""
    for c in part_candidates:
        if os.path.exists(c):
            part1 = c
            break
    if not part1:
        try:
            ls = subprocess.check_output(["lsblk", "-ln", "-o", "PATH", device_path], text=True).splitlines()
            if len(ls) >= 2:
                part1 = ls[1].strip()
        except Exception:
            pass
    if not part1 or not os.path.exists(part1):
        _emit(sink, "[ERROR] Partition device not found (expected /dev/sdX1 or /dev/mmcblkXp1).\n")
        return

    # Reproducibly format FAT32 and copy the payload with mtools
    _format_and_copy_fat(part1, sink, cwd, epoch)
    _run_stream("sync", sink, cwd)
    _emit(sink, "[INFO] Direct flash completed.\n")

def _dd_to_device(img_path: str, device_path: str, sink: Optional[Sink], cwd: str) -> None:
    if not device_path or not device_path.startswith("/dev/"):
        _emit(sink, f"[ERROR] Invalid device path: {device_path!r}\n")
        return

    _emit(sink, _log_title(f"Flash to device with dd: {device_path}"))

    _run_stream(
        "set -euo pipefail; "
        f"for p in $(lsblk -ln {device_path} | awk '{{print $1}}'); do "
        "  mp=$(lsblk -no MOUNTPOINT /dev/${p} 2>/dev/null || true); "
        "  if [ -n \"$mp\" ]; then echo umount /dev/${p}; sudo umount -lf /dev/${p} || true; fi; "
        "done",
        sink, cwd
    )

    # write image
    _run_stream(f"sudo dd if='{img_path}' of='{device_path}' bs=4M status=progress conv=fsync", sink, cwd)
    _run_stream("sync", sink, cwd)
    _run_stream(f"sudo sgdisk -e '{device_path}'", sink, cwd)

    # nudge kernel and show result
    _run_stream(f"sudo udevadm settle || true", sink, cwd)
    _run_stream(f"sudo partprobe '{device_path}' || true", sink, cwd)
    _run_stream(f"lsblk -f '{device_path}' || true", sink, cwd)
    _emit(sink, "[INFO] Flashing completed.\n")

# Options / selection interpretation
def _index_options_by_name(options_json: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    by_name: Dict[str, Dict[str, Any]] = {}
    add = (options_json or {}).get("add_software")

    # New format: {"categories":[{"items":[{...}, ...]}, ...]}
    if isinstance(add, dict) and isinstance(add.get("categories"), list):
        for cat in (add.get("categories") or []):
            if not isinstance(cat, dict):
                continue
            for item in (cat.get("items") or []):
                if isinstance(item, dict):
                    nm = (item.get("name") or "").strip()
                    if nm:
                        by_name[nm.lower()] = item

    return by_name


def _index_remove_by_name(options_json: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    by_name: Dict[str, Dict[str, Any]] = {}
    rem_list = (options_json or {}).get("remove_software", []) or []
    for item in rem_list:
        nm = (item.get("name") or "").strip()
        if nm:
            by_name[nm.lower()] = item
    return by_name

# Ask for sudo password only when needed
def _sudo_preflight():
    subprocess.check_call(["sudo", "-v"])
    stop = {"run": True}

    def _keepalive():
        while stop["run"]:
            subprocess.call(["sudo", "-n", "-v"],
                            stdout=subprocess.DEVNULL,
                            stderr=subprocess.DEVNULL)
            time.sleep(60)  # refresh every minute

    t = threading.Thread(target=_keepalive, daemon=True)
    t.start()

    def _stopper():
        stop["run"] = False
        try:
            subprocess.call(["sudo", "-k"],
                            stdout=subprocess.DEVNULL,
                            stderr=subprocess.DEVNULL)
        except Exception:
            pass

    return _stopper

class _SafeDict(dict):
    def __missing__(self, key):
        return "{" + key + "}" 

def _version_vars(name: str, version: Optional[str]) -> Dict[str, str]:
    version = (version or "").strip()
    nodots = version.replace(".", "") if version else ""
    underscores = version.replace(".", "_") if version else ""
    return {
        "version": version,
        "vversion": f"v{version}" if version else "",
        "version_nodots": nodots,
        "version_underscores": underscores,
        "name": name,
        "name_lower": name.lower(),
    }


def _render_cmds(cmds: List[str], name: str, version: Optional[str]) -> List[str]:
    if not cmds:
        return []
    env = _SafeDict(_version_vars(name, version))
    out: List[str] = []
    for c in cmds:
        try:
            out.append(c.format_map(env))
        except Exception:
            out.append(c)
    return out


def _extract_commands_from_item(item: Dict[str, Any], eff_version: Optional[str]) -> Tuple[List[str], List[str]]:
    name = (item.get("name") or "").strip() or "item"
    external = _as_list(item.get("external_commands"))
    internal = item.get("chroot_commands", None)
    if internal is None:
        internal = item.get("internal_commands", [])
    external = _render_cmds(_as_list(external), name, eff_version)
    internal = _render_cmds(_as_list(internal), name, eff_version)
    return external, internal


def _copy_image_to_pwd(image_path: str, work_dir: str, sink: Optional[Sink]) -> Tuple[str, str]:
    # If we need to create a copy of the image file in the future instead using the original, we have this function here
    src = Path(image_path).expanduser().resolve()
    if not src.exists():
        _emit(sink, f"[ERROR] Source image not found: {src}\n")
        raise FileNotFoundError(str(src))
    msg = f"[INFO] Using source image directly: {src}\n"
    _emit(sink, msg)
    return str(src), msg

def _clean_build_dirs(sink: Optional[Sink], cwd: str) -> None:
    """Remove build working directories left over from a previous run in this
    cwd. Without this, a second build reuses the previous run's already-
    mutated system_to_edit/ — `mv squashfs-root/ system_to_edit` nests instead
    of replacing when the target already exists — so the chroot script runs
    against stale, previously-mutated state instead of a fresh copy of the
    base image, and the output size/hash silently depends on build history
    instead of only on the base image + selection. This is why manual
    rebuilds in the same directory stopped being reproducible."""
    _emit(sink, _log_title("Clean previous build state"))
    # Defensively unmount anything a crashed previous run left mounted before
    # rm -rf: system_to_edit/{run,dev,proc} are bind mounts of the *host*
    # directories, and recursing into a live bind mount would delete real
    # host files.
    for m in ("system_to_edit/tmp", "system_to_edit/proc", "system_to_edit/dev",
              "system_to_edit/run", "iso_mounted"):
        _run_stream(f"sudo umount -lf '{m}' 2>/dev/null || true", sink, cwd)
    _run_stream(
        "sudo rm -rf iso_mounted future_iso system_to_edit shared_with_chroot "
        "squashfs-root pristine_repro.tar",
        sink, cwd
    )


def _mount_and_prepare(local_image: str, logs: List[str], sink: Optional[Sink], cwd: str) -> None:
    logs.append(_run_stream("mkdir -p iso_mounted future_iso", sink, cwd))
    _emit(sink, "\n[INFO] Type your sudo password in the terminal\n")
    # Mount read-only: the source image is never modified, which keeps its mtime
    # (and thus SOURCE_DATE_EPOCH) stable across runs.
    if local_image.endswith(".iso"):
        logs.append(_run_stream(f"sudo mount -o ro,loop '{local_image}' iso_mounted", sink, cwd))
    elif local_image.endswith(".img"):
        logs.append(_run_stream(f"sudo mount -o ro,loop,offset=1048576 '{local_image}' iso_mounted", sink, cwd))

    logs.append(_run_stream("rsync --exclude=/live/filesystem.squashfs -a iso_mounted/ future_iso", sink, cwd))
    logs.append(_run_stream("sudo unsquashfs iso_mounted/live/filesystem.squashfs", sink, cwd))
    logs.append(_run_stream("sudo mv squashfs-root/ system_to_edit", sink, cwd))
    logs.append(_run_stream("sudo mount --bind /run system_to_edit/run", sink, cwd))
    logs.append(_run_stream("sudo mount --bind /dev system_to_edit/dev", sink, cwd))
    logs.append(_run_stream("sudo mount --bind /proc system_to_edit/proc", sink, cwd))
    logs.append(_run_stream("sudo mount --bind shared_with_chroot system_to_edit/tmp", sink, cwd))


def _chroot_execute_script(logs: List[str], sink: Optional[Sink], cwd: str) -> None:
    _emit(sink, "[INFO] Running script in Chroot\n")
    logs.append(_run_stream("sudo chroot system_to_edit /bin/bash -c 'bash /tmp/script'", sink, cwd))

def _create_image_file_enabled() -> bool:
    return True   # Default: COMMENT THIS LINE TO DISABLE .img CREATION
    #return False   # No image file is created; we just flash directly if a device is selected

def _build_img_from_future_iso(sink: Optional[Sink], cwd: str, epoch: int, out_name: str = "DTails.img",
                               disk_guid: Optional[str] = None) -> str:
    import os, time

    # Resolve img_path as absolute path inside cwd so each build directory gets
    # its own copy and the path is valid regardless of subprocess cwd.
    img_path = os.path.join(os.path.abspath(cwd), out_name) if not os.path.isabs(out_name) else out_name

    # Compute required sizes
    content_bytes = int(subprocess.check_output(["du", "-sb", "future_iso"], text=True, cwd=cwd).split()[0])
    # Add custom space to the partition
    buffer_bytes = 10 * 1024 * 1024
    part_bytes = content_bytes + buffer_bytes
    one_mib = 1024 * 1024
    img_bytes = part_bytes + (2 * one_mib)
    # Round up to a whole MiB so the image is sector-aligned (the official Tails
    # image is an exact MiB multiple). A non-512-multiple size leaves a partial
    # trailing sector and makes gdisk/firmware warn about a damaged GPT.
    img_bytes = ((img_bytes + one_mib - 1) // one_mib) * one_mib

    _emit(sink, _log_title("Create .img file"))
    _emit(sink, f"[INFO] future_iso: {content_bytes/1e6:.1f} MB; partition target: {part_bytes/1e6:.1f} MB; image: {img_bytes/1e6:.1f} MB\n")

    # Create sparse file
    _run_stream(f"truncate -s {img_bytes} '{img_path}'", sink, cwd)

    # --partscan asks the kernel to create /dev/loopNp1 immediately on attach
    # (reliable on standard desktop Linux). kpartx below is the fallback for
    # environments (Docker) where --partscan produces no partition nodes.
    loopdev = subprocess.check_output(
        f"sudo losetup --find --show --partscan '{img_path}'",
        shell=True, text=True, cwd=cwd
    ).strip()
    _emit(sink, f"[INFO] loop device: {loopdev}\n")

    try:
        # GPT + 1º partition
        _run_stream(f"sudo parted -s '{loopdev}' mklabel gpt", sink, cwd)
        _run_stream(f"sudo parted -s '{loopdev}' mkpart primary fat32 0% 100% name 1 Tails", sink, cwd)
        _run_stream(f"sudo parted -s '{loopdev}' set 1 boot on", sink, cwd)
        _run_stream(f"sudo parted -s '{loopdev}' set 1 hidden on", sink, cwd)
        _run_stream(f"sudo parted -s '{loopdev}' set 1 legacy_boot on", sink, cwd)
        _run_stream(f"sudo parted -s '{loopdev}' set 1 esp on", sink, cwd)
        _run_stream(f"sudo parted -s '{loopdev}' set 1 no_automount on", sink, cwd)

        # Pin GPT GUIDs (keep base disk GUID so Tails repartitions on first boot)
        _pin_gpt_guids(loopdev, sink, cwd, epoch, disk_guid)

        # Expose partition devices. Try partprobe/udevadm first (native); fall
        # back to kpartx for environments (Docker) where the kernel won't create
        # /dev/loopNp1 nodes automatically.
        _run_stream(f"sudo partprobe '{loopdev}' || true", sink, cwd)
        _run_stream("sudo udevadm settle || true", sink, cwd)

        # Prefer kernel-native partition nodes (created by partprobe+udevadm).
        # Only invoke kpartx when they are absent — on Arch/Debian desktop the
        # kernel already owns /dev/loopNp1, and kpartx would hold it busy,
        # causing mkfs.fat to fail with "Device or resource busy".
        loop_name = os.path.basename(loopdev)
        part1 = ""
        for c in (f"{loopdev}p1", f"{loopdev}1"):
            if os.path.exists(c):
                part1 = c
                break
        if not part1:
            try:
                lines = subprocess.check_output(["lsblk", "-ln", "-o", "PATH", loopdev], text=True).splitlines()
                if len(lines) >= 2 and os.path.exists(lines[1].strip()):
                    part1 = lines[1].strip()
            except Exception:
                pass
        if not part1:
            # Kernel didn't expose partition nodes (e.g. Docker) — fall back to kpartx.
            _run_stream(f"sudo kpartx -av '{loopdev}' || true", sink, cwd)
            mapper = f"/dev/mapper/{loop_name}p1"
            if os.path.exists(mapper):
                part1 = mapper
        if not part1:
            raise RuntimeError("Cannot find loop partition device")

        # Reproducibly format and copy payload with mtools
        _format_and_copy_fat(part1, sink, cwd, epoch)
        _run_stream("sync", sink, cwd)

        _emit(sink, f"[INFO] Image built: {img_path}\n")
    finally:
        _emit(sink, "[INFO] Detaching loop device…\n")
        _run_stream(f"sudo kpartx -d '{loopdev}' || true", sink, cwd)
        _run_stream(f"sudo losetup -d '{loopdev}' || true", sink, cwd)

    # Patch dosfstools 4.2 bug: volume label dir entry CrtTime/WrtTime use
    # wall-clock time instead of SOURCE_DATE_EPOCH. Fix after loop detach.
    _patch_fat_vol_label_time(img_path, epoch, sink)

    return img_path


def _patch_fat_vol_label_time(img_path: str, epoch: int, sink: Optional[Sink]) -> None:
    """Overwrite the FAT32 volume-label directory-entry CrtTime/WrtTime with
    the epoch-derived value. dosfstools ≤ 4.2 writes wall-clock time into
    these two fields even when SOURCE_DATE_EPOCH is set."""
    import struct, datetime
    PART_OFFSET = 1048576  # partition always starts at 1 MiB (GPT alignment)
    try:
        with open(img_path, "r+b") as f:
            # Read BPB fields to locate the data area
            f.seek(PART_OFFSET + 14); reserved = struct.unpack("<H", f.read(2))[0]
            f.seek(PART_OFFSET + 16); fat_count = struct.unpack("<B", f.read(1))[0]
            f.seek(PART_OFFSET + 36); fat_size  = struct.unpack("<I", f.read(4))[0]
            data_off = PART_OFFSET + (reserved + fat_count * fat_size) * 512

            # Deterministic FAT time from epoch
            dt = datetime.datetime.fromtimestamp(epoch)
            fat_time = dt.hour * 2048 + dt.minute * 32 + dt.second // 2
            tb = struct.pack("<H", fat_time)

            # Volume label is the first 32-byte entry at data area start.
            # Patch CrtTime (entry offset 14) and WrtTime (entry offset 22).
            f.seek(data_off + 14); f.write(tb)
            f.seek(data_off + 22); f.write(tb)
        _emit(sink, f"[INFO] Patched FAT vol-label timestamps → 0x{fat_time:04x}\n")
    except Exception as e:
        _emit(sink, f"[WARN] Could not patch FAT vol-label time: {e}\n")

def _repack_and_build(local_image: str, logs: List[str], sink: Optional[Sink], cwd: str, epoch: int, device_path: Optional[str] = None) -> None:
    _emit(sink, "[INFO] Umounting… please wait…\n")
    logs.append(_run_stream("sudo umount system_to_edit/run", sink, cwd))
    logs.append(_run_stream("sudo umount system_to_edit/dev", sink, cwd))
    logs.append(_run_stream("sudo umount system_to_edit/proc", sink, cwd))
    logs.append(_run_stream("sudo umount system_to_edit/tmp", sink, cwd))
    logs.append(_run_stream("sudo umount iso_mounted", sink, cwd))
    _emit(sink, "[INFO]  Done! Image unmounted.\n")
    # Restore logs / machine-id / apt state to the pristine base-image content
    # before repacking, so they are reproducible and match the original.
    _restore_pristine(logs, sink, cwd)
    # Deterministic squashfs: fixed superblock time, flattened inode times, no
    # append, no NFS export table.
    logs.append(_run_stream(
        "sudo mksquashfs system_to_edit/ filesystem.squashfs -comp zstd -noappend -no-exports "
        f"-all-time {epoch} -mkfs-time {epoch}",
        sink, cwd
    ))
    logs.append(_run_stream("sudo chmod 755 filesystem.squashfs", sink, cwd))
    logs.append(_run_stream("sudo mv -f filesystem.squashfs future_iso/live/filesystem.squashfs", sink, cwd))
    logs.append(_run_stream(f"sudo find future_iso -exec touch -h -d @{epoch} {{}} +", sink, cwd))

    img_path = None
    if local_image.endswith(".iso"):
        _build_iso(sink, cwd, epoch)
        img_path = os.path.join(os.path.abspath(cwd), "DTails.iso")
    else:
        disk_guid = _original_disk_guid(local_image)
        if disk_guid:
            _emit(sink, f"[INFO] Preserving base image disk GUID for first-boot repartition: {disk_guid}\n")
        else:
            _emit(sink, "[WARN] Could not read base image disk GUID; Tails may skip first-boot repartition.\n")
        if _create_image_file_enabled():
            img_path = _build_img_from_future_iso(sink=sink, cwd=cwd, epoch=epoch, disk_guid=disk_guid)
            if device_path:
                _dd_to_device(img_path=img_path, device_path=device_path, sink=sink, cwd=cwd)
            else:
                _emit(sink, f"[INFO] Image built and left on disk: {img_path}\n")
        else:
            if device_path:
                _emit(sink, "[INFO] Flashing future_iso/* directly to the device (partition + format + copy)…\n")
                _flash_future_iso_direct_to_device(device_path, sink, cwd, epoch, disk_guid)
            else:
                _emit(sink, "[WARN] No device selected; skipping device flash.\n")
    return img_path


def _sha256(path: str, chunk: int = 1 << 20) -> str:
    import hashlib
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for b in iter(lambda: f.read(chunk), b""):
            h.update(b)
    return h.hexdigest()


def _emit_build_manifest(sink: Optional[Sink], cwd: str, artifact_path: Optional[str],
                         device_path: str, installs: List[Tuple[str, Optional[str]]],
                         removals: List[str], epoch: int, base_image: str) -> None:
    """Print — and save next to the image — a shareable build manifest: the exact
    software selection with versions, what was removed, and the SHA256 of the
    produced image, so a build can be reproduced and its hash verified by others."""
    _emit(sink, "\n")
    _emit(sink, _log_title("Build manifest (shareable / verifiable)"))

    lines = ["DTails build manifest",
             f"  base image : {os.path.basename(base_image)}"]

    if base_image and os.path.exists(base_image):
        _emit(sink, f"[INFO] Computing SHA256 of base image {os.path.basename(base_image)}…\n")
        lines.append(f"  base sha256: {_sha256(base_image)}")

    if artifact_path and os.path.exists(artifact_path):
        size = os.path.getsize(artifact_path)
        _emit(sink, f"[INFO] Computing SHA256 of {os.path.basename(artifact_path)} "
                    f"({size / 1e9:.2f} GB)…\n")
        digest = _sha256(artifact_path)
        lines.append(f"  output     : {os.path.basename(artifact_path)}  ({size / (1024*1024):.1f} MiB)")
        lines.append(f"  sha256     : {digest}")
        try:   # sidecar so `sha256sum -c DTails.img.sha256` works
            with open(artifact_path + ".sha256", "w") as f:
                f.write(f"{digest}  {os.path.basename(artifact_path)}\n")
        except Exception:
            pass
    else:
        lines.append("  output     : (flashed directly to device; no image file)")

    if device_path:
        lines.append(f"  flashed to : {device_path}")
    lines.append(f"  build epoch: {epoch} (SOURCE_DATE_EPOCH — reproducible)")

    lines.append("")
    lines.append(f"  Installed ({len(installs)}):")
    lines += [f"    + {name}" + (f"  v{ver}" if ver else "") for name, ver in installs] or []
    if not installs:
        lines.append("    (none)")
    lines.append(f"  Removed ({len(removals)}):")
    lines += [f"    - {name}" for name in removals]
    if not removals:
        lines.append("    (none)")

    lines.append("")
    lines.append("  Reproducible: the same base image + same selection rebuilds to the")
    lines.append("  same SHA256. Share this manifest so others can verify the hash.")

    text = "\n".join(lines) + "\n"
    _emit(sink, text)

    try:
        out = (artifact_path + ".manifest.txt") if artifact_path \
            else os.path.join(cwd, "DTails.manifest.txt")
        with open(out, "w") as f:
            f.write(text)
        _emit(sink, f"[INFO] Manifest saved: {out}\n")
    except Exception as e:
        _emit(sink, f"[WARN] Could not save manifest: {e}\n")


# Public runner functions

def run_selected_actions_stream(state: Any, image_path: str, sink: Sink, cwd: Optional[str] = None) -> None:
    _run_internal(state, image_path, sink=sink, cwd=cwd, collect=False)


def run_selected_actions(state: Any, image_path: str, cwd: Optional[str] = None) -> str:
    return _run_internal(state, image_path, sink=None, cwd=cwd, collect=True)


def _run_internal(state: Any, image_path: str, sink: Optional[Sink], cwd: Optional[str], collect: bool) -> str:
    if not image_path:
        raise ValueError("Image path is required.")

    # One password prompt in the launching terminal; keep sudo alive for the duration
    stop_sudo_keepalive = _sudo_preflight()
    _emit(sink, _log_title("DTails Write Job"))
    _emit(sink, "[INFO] Initializing...\n")

    try:
        cwd = cwd or os.getcwd()
        logs: List[str] = []

        _clean_build_dirs(sink, cwd)

        epoch = _source_date_epoch(image_path)
        _emit(sink, f"[INFO] Reproducible build timestamp (SOURCE_DATE_EPOCH) = {epoch}\n")

        options_json: Dict[str, Any] = getattr(state, "options_json", {}) or {}
        selected_installations: List[str] = getattr(state, "selected_additions", []) or []
        selected_deletions: List[str] = getattr(state, "selected_deletions", []) or []
        # Reproducibility: the GUI collects selections from Qt selectedItems(),
        # whose order reflects the user's click order, not a canonical order.
        # Two GUI builds of the *same* packages would then emit chroot/copy
        # commands in a different order and produce different image bytes. The
        # in-process test never sees this because it passes a fixed-order list.
        # Normalise here (stable, de-duplicated, case-insensitive sort) so every
        # caller builds reproducibly regardless of how the selection was made.
        def _canonical(names: List[str]) -> List[str]:
            return sorted(dict.fromkeys(n for n in names if n is not None),
                          key=lambda s: str(s).strip().lower())
        selected_installations = _canonical(selected_installations)
        selected_deletions = _canonical(selected_deletions)
        _emit(sink, _log_title("Selections"))
        _emit(sink, f"[INFO] Install: {', '.join(selected_installations) or '(none)'}\n")
        _emit(sink, f"[INFO] Remove:  {', '.join(selected_deletions) or '(none)'}\n")

        idx = _index_options_by_name(options_json)
        version_overrides: Dict[str, str] = getattr(state, "version_overrides", {}) or {}


        cat_index = _item_category_index(options_json)
        cat_meta = _category_meta_map(options_json)

        selected_cats = set()
        for sel in selected_installations:
            cat = cat_index.get((sel or "").strip().lower())
            if cat:
                selected_cats.add(cat)

        extra_external_cmds: List[str] = []
        extra_internal_cmds: List[str] = []

        # Only add a menu if this category has a menu_file (non-empty)
        for key in sorted(selected_cats):
            meta = cat_meta.get(key) or {}
            menu_file = (meta.get("menu_file") or "").strip()
            if not menu_file:
                continue
            title = meta.get("title") or key.title()
            extra_external_cmds.append(f"cp dotfiles/menu/{menu_file} shared_with_chroot/")
            extra_internal_cmds.append(f"cp /tmp/{menu_file} /etc/xdg/menus/applications-merged/")

        plan_items: List[dict] = []
        install_manifest: List[Tuple[str, Optional[str]]] = []   # (name, version) for the build manifest
        for sel in selected_installations:
            key = (sel or "").strip().lower()
            item = idx.get(key) or {}
            if not item:
                _emit(sink, f"[WARN] No details found for '{sel}' in options.json. (No commands will run for this item.)\n")
            name = item.get("name", sel)
            default_version = (item.get("version") or "").strip() or None
            eff_version = (version_overrides.get(name) or default_version)
            ext, intr = _extract_commands_from_item(item, eff_version)
            if not ext and not intr:
                _emit(sink, f"[WARN] '{name}' has no external/chroot commands.\n")
            plan_items.append({"name": name, "external_commands": ext, "internal_commands": intr, "version": eff_version})
            install_manifest.append((name, eff_version))

        # Handle removals
        rem_idx = _index_remove_by_name(options_json)

        for sel in selected_deletions:
            key = (sel or "").strip().lower()
            item = rem_idx.get(key) or {}
            if not item:
                _emit(sink, f"[WARN] No removal details found for '{sel}' in options.json.\n")
                continue

            name = item.get("name", sel)
            # Usually no version for removal entries
            ext, intr = _extract_commands_from_item(item, eff_version=None)

            if not ext and not intr:
                _emit(sink, f"[WARN] '{name}' has no removal commands.\n")

            # Prefix name for clarity in logs
            plan_items.append({
                "name": f"REMOVE: {name}",
                "external_commands": ext,   # likely empty
                "internal_commands": intr,
                "version": None,
            })


        # Init script
        _emit(sink, _log_title("Initialize chroot script"))
        _reset_script(sink, epoch, cwd)

        # Stage image
        _emit(sink, _log_title("Stage image"))
        local_image, copy_block = _copy_image_to_pwd(image_path, cwd, sink)
        logs.append(copy_block)
        _emit(sink, f"[INFO] Working on image: {local_image}\n")

        # Host downloads (external commands)
        if extra_external_cmds or plan_items:
            _emit(sink, _log_title("Host downloads & staging (external commands)"))

        # Copy only the selected category menus into shared_with_chroot
        for cmd in extra_external_cmds:
            logs.append(_run_stream(cmd, sink, cwd=cwd))

        for entry in plan_items:
            name = entry.get("name", "(unknown)")
            ver = entry.get("version") or ""
            _emit(sink, _log_title(f"Item: {name}  {'(version '+ver+')' if ver else ''}"))
            for cmd in _as_list(entry.get("external_commands")):
                if cmd.strip():
                    logs.append(_run_stream(cmd, sink, cwd=cwd))

        # Build the chroot script
        if extra_internal_cmds or plan_items:
            _emit(sink, _log_title("Generate chroot script (installs)"))

        # Ensure menus copied inside chroot if any were selected
        for line in extra_internal_cmds:
            _append_script_line(line, sink, cwd)

        for entry in plan_items:
            internals = _as_list(entry.get("internal_commands"))
            if not internals:
                _emit(sink, "[info] (no internal/chroot commands)\n")
            for line in internals:
                _append_script_line(line, sink, cwd)
        _end_script(sink, cwd)

        # Mount, snapshot pristine state, chroot, repack/flash
        _mount_and_prepare(local_image, logs, sink, cwd)
        _snapshot_pristine(logs, sink, cwd)
        _chroot_execute_script(logs, sink, cwd)
        dev = getattr(state, "selected_device", {}) or {}
        dev_path = (dev.get("path") or "").strip()
        artifact = _repack_and_build(local_image, logs, sink, cwd, epoch, device_path=dev_path)
        _emit_build_manifest(sink, cwd, artifact, dev_path, install_manifest,
                             selected_deletions, epoch, image_path)

        return "".join(logs) if collect else ""
    finally:
        try:
            stop_sudo_keepalive()
        except Exception:
            pass

