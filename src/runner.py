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


def _script_path() -> Path:
    return Path("shared_with_chroot") / "script"


def _reset_script(sink: Optional[Sink]) -> None:
    sp = _script_path()
    _ensure_dir(sp.parent)
    sp.write_text("#!/bin/bash\nexport PATH=$PATH:/usr/local/sbin:/usr/sbin:/sbin\n\n", encoding="utf-8")
    _emit(sink, f"[INFO] Script file created: {sp}\n")

def _end_script(sink: Optional[Sink]) -> None:
    _append_script_line("\nrm -rf ~/.bash_history", sink)

def _append_script_line(line: str, sink: Optional[Sink]) -> None:
    sp = _script_path()
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

def _flash_future_iso_direct_to_device(device_path: str, sink: Optional[Sink], cwd: str) -> None:
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
    buffer_bytes = 0
    #buffer_bytes = 200 * 1024 * 1024
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

    # Format FAT32 and copy the payload
    _run_stream(f"sudo mkfs.fat -F 32 -n Tails '{part1}'", sink, cwd)
    _run_stream("sudo mkdir -p mount_p", sink, cwd)
    _run_stream(f"sudo mount '{part1}' mount_p", sink, cwd)
    _run_stream("sudo cp -r future_iso/* mount_p", sink, cwd)
    _run_stream("sync", sink, cwd)
    _run_stream("sudo umount mount_p", sink, cwd)
    _run_stream("rmdir mount_p", sink, cwd)
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

def _mount_and_prepare(local_image: str, logs: List[str], sink: Optional[Sink], cwd: str) -> None:
    logs.append(_run_stream("mkdir -p iso_mounted future_iso", sink, cwd))
    _emit(sink, "\n[INFO] Type your sudo password in the terminal\n")
    if local_image.endswith(".iso"):
        logs.append(_run_stream(f"sudo mount -o loop '{local_image}' iso_mounted", sink, cwd))
    elif local_image.endswith(".img"):
        logs.append(_run_stream(f"sudo mount -o loop,offset=1048576 '{local_image}' iso_mounted", sink, cwd))

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
    return True   # ← UNCOMMENT THIS LINE TO ENABLE .img CREATION
    #return False   # Default: no image file is created; we just flash directly if a device is selected

def _build_img_from_future_iso(sink: Optional[Sink], cwd: str, out_name: str = "DTails.img") -> str:
    import os, time

    img_path = os.path.abspath(out_name)

    # Compute required sizes
    content_bytes = int(subprocess.check_output(["du", "-sb", "future_iso"], text=True, cwd=cwd).split()[0])
    # Add custom space to the partition
    buffer_bytes = 0
    #buffer_bytes = 200 * 1024 * 1024
    part_bytes = content_bytes + buffer_bytes
    one_mib = 1024 * 1024
    img_bytes = part_bytes + (2 * one_mib)

    _emit(sink, _log_title("Create .img file"))
    _emit(sink, f"[INFO] future_iso: {content_bytes/1e6:.1f} MB; partition target: {part_bytes/1e6:.1f} MB; image: {img_bytes/1e6:.1f} MB\n")

    # Create sparse file
    _run_stream(f"truncate -s {img_bytes} '{img_path}'", sink, cwd)

    # Attach loop with partitions visible
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

        # Check
        _run_stream(f"sudo partprobe '{loopdev}' || true", sink, cwd)
        _run_stream("sudo udevadm settle || true", sink, cwd)

        # Find partition node
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
            raise RuntimeError("Cannot find loop partition device")

        # Format and copy payload
        _run_stream(f"sudo mkfs.fat -F 32 -n Tails '{part1}'", sink, cwd)
        _run_stream("sudo mkdir -p mount_p", sink, cwd)
        _run_stream(f"sudo mount '{part1}' mount_p", sink, cwd)
        _run_stream("sudo cp -r future_iso/* mount_p", sink, cwd)
        _run_stream("sync", sink, cwd)
        _run_stream("sudo umount mount_p", sink, cwd)
        _run_stream("rmdir mount_p", sink, cwd)

        _emit(sink, f"[INFO] Image built: {img_path}\n")
    finally:
        _emit(sink, "[INFO] Detaching loop device…\n")
        _run_stream(f"sudo losetup -d '{loopdev}' || true", sink, cwd)

    return img_path

def _repack_and_build(local_image: str, logs: List[str], sink: Optional[Sink], cwd: str, device_path: Optional[str] = None) -> None:
    _emit(sink, "[INFO] Umounting… please wait…\n")
    logs.append(_run_stream("sudo umount system_to_edit/run", sink, cwd))
    logs.append(_run_stream("sudo umount system_to_edit/dev", sink, cwd))
    logs.append(_run_stream("sudo umount system_to_edit/proc", sink, cwd))
    logs.append(_run_stream("sudo umount system_to_edit/tmp", sink, cwd))
    logs.append(_run_stream("sudo umount iso_mounted", sink, cwd))
    _emit(sink, "[INFO]  Done! Image unmounted.\n")
    logs.append(_run_stream("sudo mksquashfs system_to_edit/ filesystem.squashfs -comp zstd", sink, cwd))
    logs.append(_run_stream("sudo chmod 755 filesystem.squashfs", sink, cwd))
    logs.append(_run_stream("mv filesystem.squashfs future_iso/live/", sink, cwd))

    if local_image.endswith(".iso"):
        _emit(sink, "\n[INFO] Building the final .iso image…\n")
        _emit(sink, "\n[WARN] You may see 'unrecognize xattr prefix system.posix_acl_access' — harmless when scripted.\n")
        logs.append(_run_stream(
            "sudo genisoimage -r -J -b isolinux/isolinux.bin -c isolinux/boot.cat "
            "-no-emul-boot -boot-load-size 4 -boot-info-table -o DTails.iso future_iso",
            sink, cwd
        ))
        logs.append(_run_stream("isohybrid DTails.iso", sink, cwd))
        _emit(sink, "[INFO] DTails.iso image created.\n")
    else:
        if _create_image_file_enabled():
            img_path = _build_img_from_future_iso(sink=sink, cwd=cwd)
            if device_path:
                _dd_to_device(img_path=img_path, device_path=device_path, sink=sink, cwd=cwd)
            else:
                _emit(sink, f"[INFO] Image built and left on disk: {img_path}\n")
        else:
            # Default (Flash directly to the selected device)
            if device_path:
                _emit(sink, "[INFO] Flashing future_iso/* directly to the device (partition + format + copy)…\n")
                _flash_future_iso_direct_to_device(device_path, sink, cwd)
            else:
                _emit(sink, "[WARN] No device selected; skipping device flash.\n")


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

        options_json: Dict[str, Any] = getattr(state, "options_json", {}) or {}
        selected_installations: List[str] = getattr(state, "selected_additions", []) or []
        selected_deletions: List[str] = getattr(state, "selected_deletions", []) or []
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
        _reset_script(sink)

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
            _append_script_line(line, sink)

        for entry in plan_items:
            internals = _as_list(entry.get("internal_commands"))
            if not internals:
                _emit(sink, "[info] (no internal/chroot commands)\n")
            for line in internals:
                _append_script_line(line, sink)
        _end_script(sink)

        # Mount, chroot, repack/flash
        _mount_and_prepare(local_image, logs, sink, cwd)
        _chroot_execute_script(logs, sink, cwd)
        dev = getattr(state, "selected_device", {}) or {}
        dev_path = (dev.get("path") or "").strip()
        _repack_and_build(local_image, logs, sink, cwd, device_path=dev_path)

        return "".join(logs) if collect else ""
    finally:
        try:
            stop_sudo_keepalive()
        except Exception:
            pass

