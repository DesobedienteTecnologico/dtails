"""Download and verify official Tails images.

Reads the current release metadata from tails.net (so new versions are picked up
automatically), downloads the .img/.iso, and verifies them two ways:

  * SHA256 against the hash published in latest.json (over HTTPS), and
  * the OpenPGP detached signature, checked against Tails' signing key whose
    fingerprint is *pinned* below — the key is imported into a throwaway keyring
    and rejected unless its fingerprint matches, so a tampered key (even served
    over HTTPS) can't be trusted.

No third-party Python deps (stdlib urllib/hashlib). Requires the `gpg` CLI and
network access.
"""
import hashlib
import json
import os
import shutil
import subprocess
import tempfile
import urllib.request
from typing import Callable, Optional, Tuple

CHANNEL = "stable"
LATEST_JSON_URL = f"https://tails.net/install/v2/Tails/amd64/{CHANNEL}/latest.json"
SIGNING_KEY_URL = "https://tails.net/tails-signing.key"
SIG_BASE = "https://tails.net/torrents/files"           # /<filename>.sig
# Tails OpenPGP signing key (0xDBB802B258ACD84F), confirmed on
# https://tails.net/doc/about/openpgp_keys/ — pinned so a swapped key is refused.
SIGNING_KEY_FPR = "A490D0F4D311A4153E2BB7CADBB802B258ACD84F"

# progress callback: (bytes_done, bytes_total)  — total may be 0 if unknown
ProgressCb = Optional[Callable[[int, int], None]]


def _urlopen(url: str, timeout: int = 60):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:153.0) Gecko/20100101 Firefox/153.0"})
    return urllib.request.urlopen(req, timeout=timeout)   # verifies TLS by default


def fetch_release() -> dict:
    """Return {'version', 'img': {...}, 'iso': {...}} from tails.net latest.json.
    Each image entry: {'url', 'size', 'sha256', 'filename'}."""
    with _urlopen(LATEST_JSON_URL, timeout=30) as r:
        data = json.loads(r.read().decode("utf-8"))
    inst = data["installations"][0]
    out = {"version": inst["version"], "img": None, "iso": None}
    for path in inst.get("installation-paths", []):
        tf = (path.get("target-files") or [{}])[0]
        url = tf.get("url", "")
        entry = {"url": url, "size": tf.get("size"), "sha256": tf.get("sha256"),
                 "filename": url.rsplit("/", 1)[-1]}
        if url.endswith(".img"):
            out["img"] = entry
        elif url.endswith(".iso"):
            out["iso"] = entry
    return out


def download(url: str, dest: str, progress_cb: ProgressCb = None,
             expected_size: Optional[int] = None) -> str:
    """Stream `url` to `dest` (atomically via a .part file). Returns dest."""
    tmp = dest + ".part"
    try:
        with _urlopen(url) as r:
            total = expected_size or int(r.headers.get("Content-Length") or 0)
            done = 0
            with open(tmp, "wb") as f:
                while True:
                    chunk = r.read(1 << 20)
                    if not chunk:
                        break
                    f.write(chunk)
                    done += len(chunk)
                    if progress_cb:
                        progress_cb(done, total)
        os.replace(tmp, dest)
        return dest
    except BaseException:
        if os.path.exists(tmp):
            os.remove(tmp)
        raise


def sha256_file(path: str, progress_cb: ProgressCb = None) -> str:
    total = os.path.getsize(path)
    h = hashlib.sha256()
    done = 0
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
            done += len(chunk)
            if progress_cb:
                progress_cb(done, total)
    return h.hexdigest()


def verify_sha256(path: str, expected_hex: str, progress_cb: ProgressCb = None) -> Tuple[bool, str]:
    if not expected_hex:
        return False, "no expected SHA256 available"
    got = sha256_file(path, progress_cb)
    if got.lower() == expected_hex.lower():
        return True, f"OK ({got})"
    return False, f"MISMATCH\n      expected {expected_hex}\n      got      {got}"


def sig_url_for(filename: str) -> str:
    return f"{SIG_BASE}/{filename}.sig"


def _gpg(args, gnupghome):
    return subprocess.run(["gpg", "--homedir", gnupghome, "--batch", "--no-tty", *args],
                          capture_output=True, text=True)


def verify_gpg(image_path: str, sig_path: Optional[str] = None,
               progress_cb: ProgressCb = None) -> Tuple[bool, str, str]:
    """Verify `image_path` against its detached OpenPGP signature using the pinned
    Tails signing key, in an isolated keyring. Downloads the .sig and the key if
    needed. Returns (ok, detail, code) where code is one of: good, bad, no-sig,
    no-key, import-fail, fpr-mismatch, no-gpg."""
    if shutil.which("gpg") is None:
        return False, "gpg is not installed (install gnupg).", "no-gpg"
    fn = os.path.basename(image_path)
    home = tempfile.mkdtemp(prefix="dtails_gpg_")
    os.chmod(home, 0o700)
    try:
        if not sig_path:
            sig_path = os.path.join(home, fn + ".sig")
            try:
                download(sig_url_for(fn), sig_path)
            except Exception as e:
                # 404 usually means this isn't the current release: Tails only
                # keeps the latest release's signature on the server.
                return False, f"signature not available on the server ({e})", "no-sig"
        key = os.path.join(home, "tails-signing.key")
        try:
            download(SIGNING_KEY_URL, key)
        except Exception as e:
            return False, f"could not fetch Tails signing key:\n  {e}", "no-key"

        imp = _gpg(["--import", key], home)
        if imp.returncode != 0:
            return False, "failed to import Tails signing key:\n" + imp.stderr, "import-fail"

        fprs = _gpg(["--with-colons", "--fingerprint"], home).stdout
        got = [ln.split(":")[9] for ln in fprs.splitlines() if ln.startswith("fpr:")]
        if SIGNING_KEY_FPR not in got:
            return False, ("signing-key fingerprint mismatch — refusing!\n"
                           f"  expected {SIGNING_KEY_FPR}\n  got      {', '.join(got) or '(none)'}"), "fpr-mismatch"

        v = _gpg(["--status-fd", "1", "--verify", sig_path, image_path], home)
        good = v.returncode == 0 and "Good signature" in (v.stderr + v.stdout)
        valid_key = SIGNING_KEY_FPR in (v.stdout + v.stderr)
        detail = (v.stderr.strip() or v.stdout.strip())
        if good and valid_key:
            return True, f"OK (Tails signing key {SIGNING_KEY_FPR[-8:]})", "good"
        return False, "BAD signature — content does not match the signature\n      " + \
            detail.replace("\n", "\n      "), "bad"
    finally:
        shutil.rmtree(home, ignore_errors=True)


def verify_image(image_path: str, release: Optional[dict] = None,
                 progress_cb: ProgressCb = None) -> Tuple[bool, str]:
    """Run SHA256 (against latest.json) + GPG verification. Returns (ok, report)."""
    fn = os.path.basename(image_path)
    if release is None:
        try:
            release = fetch_release()
        except Exception:
            release = None

    expected = None
    current_names = set()
    if release:
        for kind in ("img", "iso"):
            e = release.get(kind)
            if e:
                current_names.add(e.get("filename"))
                if e.get("filename") == fn:
                    expected = e.get("sha256")
    # Is this file the current release, or an older/renamed one?
    is_current = (fn in current_names) if release else None

    report = [f"Verifying {fn}"]

    # --- SHA256 ---
    if expected:
        sha_ok, msg = verify_sha256(image_path, expected, progress_cb)
        report.append(f"  SHA256 ........ {'OK  (matches latest.json)' if sha_ok else 'FAILED  ' + msg}")
    else:
        sha_ok = None
        report.append("  SHA256 ........ skipped (no published hash for this filename)")

    # --- GPG ---
    gpg_ok, gmsg, code = verify_gpg(image_path)
    report.append(f"  GPG signature  {'OK  (Tails signing key A490…D84F)' if gpg_ok else 'FAILED  ' + gmsg}")

    # --- Outcome ---
    # Distinguish a genuine mismatch (tampered/corrupt) from simply being unable
    # to verify because the file is an older release the server no longer signs.
    tampered = (sha_ok is False) or (code == "bad")
    verified = (gpg_ok and (sha_ok is not False))

    if verified:
        report.append("  -> VERIFIED ✔")
        return True, "\n".join(report)

    if tampered:
        report.append("  -> NOT VERIFIED ✘  (content differs from the official image)")
        return False, "\n".join(report)

    # Not tampered, just couldn't complete verification.
    if release and is_current is False and code == "no-sig":
        ver = release.get("version", "?")
        report.append(f"  -> CANNOT VERIFY  — '{fn}' is not the current release ({ver}).")
        report.append(f"     Tails only publishes the checksum/signature for the latest")
        report.append(f"     release, so older images can't be verified here. Download the")
        report.append(f"     current release ({ver}) and verify that instead.")
        return False, "\n".join(report)

    report.append("  -> COULD NOT VERIFY  (" + code + ")")
    return False, "\n".join(report)
