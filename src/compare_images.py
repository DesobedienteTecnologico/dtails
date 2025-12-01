import os
import subprocess
import hashlib
import shutil
import threading
import time
import json
from pathlib import Path
from datetime import datetime
from typing import Dict, Tuple, Any

from PyQt5.QtCore import QThread, pyqtSignal, QUrl, Qt
from PyQt5.QtGui import QDesktopServices
from PyQt5.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QPushButton,
    QLabel,
    QFileDialog,
    QMessageBox,
    QProgressDialog,
)


class ImageCompareWorker(QThread):
    done = pyqtSignal(str, str)  # (report_path, error_message)

    def __init__(self, path_a: str, path_b: str, parent=None):
        super().__init__(parent)
        self.path_a = path_a
        self.path_b = path_b

    # ---- helpers ----
    def _is_iso(self, p: str) -> bool:
        return p.lower().endswith(".iso")

    def _is_img(self, p: str) -> bool:
        return p.lower().endswith(".img")

    def _run(self, cmd: str, timeout: int = 1800) -> None:
        try:
            completed = subprocess.run(
                cmd,
                shell=True,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                timeout=timeout,
            )
        except subprocess.TimeoutExpired as e:
            out = (e.stdout or "") + (e.stderr or "")
            raise RuntimeError(f"Command timed out: {cmd}\n{out}")
        if completed.returncode != 0:
            raise RuntimeError(
                f"Command failed ({completed.returncode}): {cmd}\n{completed.stdout}"
            )

    def _mount_image(self, image: str, mount_dir: str) -> None:
        as_root = (os.geteuid() == 0)
        sudo = "" if as_root else "sudo "
        if self._is_iso(image):
            self._run(f"{sudo}mount -o loop '{image}' '{mount_dir}'", timeout=120)
        elif self._is_img(image):
            self._run(f"{sudo}mount -o loop,offset=1048576 '{image}' '{mount_dir}'", timeout=120)
        else:
            raise RuntimeError(f"Unsupported image: {image}")

    def _hash_file(self, fp: str) -> str:
        try:
            h = hashlib.sha256()
            with open(fp, "rb") as f:
                for chunk in iter(lambda: f.read(1 << 20), b""):
                    h.update(chunk)
            return h.hexdigest()
        except PermissionError:
            return self._hash_file_with_sudo(fp)
        except FileNotFoundError:
            return ""
        except OSError:
            return ""

    def _hash_file_with_sudo(self, fp: str) -> str:
        as_root = (os.geteuid() == 0)
        if as_root:
            cmd = ["sha256sum", fp]
        else:
            cmd = ["sudo", "sha256sum", fp]

        try:
            out = subprocess.check_output(
                cmd,
                stderr=subprocess.STDOUT,
                text=True,
            )
        except Exception:
            return ""

        if not out:
            return ""

        first_line = out.splitlines()[0].strip()
        if not first_line:
            return ""
        parts = first_line.split()
        if not parts:
            return ""

        candidate = parts[0]
        if len(candidate) == 64 and all(c in "0123456789abcdefABCDEF" for c in candidate):
            return candidate.lower()

        return ""


    def _walk_entries(self, root: str) -> Dict[str, Dict[str, Any]]:
        out: Dict[str, Dict[str, Any]] = {}
        for base, dirs, files in os.walk(root, followlinks=False):
            # directories
            for dn in dirs:
                full = os.path.join(base, dn)
                rel = os.path.relpath(full, root)
                try:
                    st = os.lstat(full)
                    out[rel] = {
                        "type": "dir",
                        "sha256": "",
                        "size": 0,
                        "mode": int(st.st_mode),
                        "mtime": int(st.st_mtime),
                    }
                except Exception:
                    continue

            # files and other non-dir entries in this folder
            for fn in files:
                full = os.path.join(base, fn)
                rel = os.path.relpath(full, root)
                try:
                    st = os.lstat(full)

                    if os.path.islink(full):
                        try:
                            target = os.readlink(full)
                        except OSError:
                            target = ""
                        out[rel] = {
                            "type": "symlink",
                            "sha256": "",
                            "size": 0,
                            "mode": int(st.st_mode),
                            "mtime": int(st.st_mtime),
                            "link_target": target,
                        }
                        continue

                    # regular file
                    if os.path.isfile(full):
                        sha = ""
                        try:
                            sha = self._hash_file(full)
                        except Exception:
                            sha = ""
                        out[rel] = {
                            "type": "file",
                            "sha256": sha,
                            "size": int(st.st_size),
                            "mode": int(st.st_mode),
                            "mtime": int(st.st_mtime),
                        }
                        continue

                    mode = st.st_mode
                    if (mode & 0o170000) == 0o060000:
                        typ = "block"
                    elif (mode & 0o170000) == 0o020000:
                        typ = "char"
                    elif (mode & 0o170000) == 0o010000:
                        typ = "fifo"
                    elif (mode & 0o170000) == 0o140000:
                        typ = "socket"
                    else:
                        typ = "other"

                    out[rel] = {
                        "type": typ,
                        "sha256": "",
                        "size": 0,
                        "mode": int(st.st_mode),
                        "mtime": int(st.st_mtime),
                    }
                except Exception:
                    continue

        # Include the root itself (.)
        try:
            st = os.lstat(root)
            out["."] = {
                "type": "dir",
                "sha256": "",
                "size": 0,
                "mode": int(st.st_mode),
                "mtime": int(st.st_mtime),
            }
        except Exception:
            pass

        return out

    def _umount(self, m: str) -> None:
        as_root = (os.geteuid() == 0)
        sudo = "" if as_root else "sudo "
        try:
            self._run(f"{sudo}umount -lf '{m}'", timeout=10)
        except Exception:
            pass

    def _unsquash(self, mounted_dir: str, out_dir: str) -> str:
        as_root = (os.geteuid() == 0)
        sudo = "" if as_root else "sudo "

        candidates = [
            os.path.join(mounted_dir, "live", "filesystem.squashfs"),
            os.path.join(mounted_dir, "casper", "filesystem.squashfs"),
        ]
        fs = next((p for p in candidates if os.path.isfile(p)), None)
        if not fs:
            raise RuntimeError(
                "filesystem.squashfs not found (checked live/ and casper/)."
            )

        # Ensure the target dir exists and is empty
        if os.path.isdir(out_dir):
            shutil.rmtree(out_dir, ignore_errors=True)
        os.makedirs(out_dir, exist_ok=True)

        # Quiet + force overwrite; use all CPUs
        self._run(f"{sudo} unsquashfs -f -q -processors {os.cpu_count() or 1} -d '{out_dir}' '{fs}'")
        return out_dir

    def _write_json(
        self,
        json_path: str,
        entriesA: Dict[str, Dict[str, Any]],
        entriesB: Dict[str, Dict[str, Any]],
        summary: Dict[str, Any],
        rows: list,
    ) -> None:
        # rows is a list of (path, typeA, shaA, typeB, shaB, status)
        rows_json = [
            {
                "path": path,
                "typeA": typeA,
                "shaA": ha,
                "typeB": typeB,
                "shaB": hb,
                "status": st,
            }
            for (path, typeA, ha, typeB, hb, st) in rows
        ]

        data = {
            "imageA": {
                "path": self.path_a,
                "entries": entriesA,
            },
            "imageB": {
                "path": self.path_b,
                "entries": entriesB,
            },
            "summary": summary,
            "rows": rows_json,
        }
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)


    def _entry_label(self, meta: Dict[str, Any]) -> str:
        t = meta.get("type", "")
        if t == "symlink":
            tgt = meta.get("link_target", "")
            return f"symlink → {tgt}" if tgt else "symlink"
        return t

    def _diff_sides(
        self,
        entriesA: Dict[str, Dict[str, Any]],
        entriesB: Dict[str, Dict[str, Any]],
    ) -> Tuple[int, int, int, int, list, Dict[str, Any]]:
        """
        Returns counts, table rows and a JSON-friendly summary.
        Row format: (path, typeA, hashA, typeB, hashB, status)
        Status: 'same' | 'diff' | 'missing in A' | 'missing in B'
        """
        keysA = set(entriesA.keys())
        keysB = set(entriesB.keys())
        all_keys = sorted(keysA | keysB)

        same = diff = onlyA = onlyB = 0
        rows = []
        per_path = {}

        for path in all_keys:
            ma = entriesA.get(path)
            mb = entriesB.get(path)

            if ma and not mb:
                status = "missing in B"
                onlyB += 1
                rows.append((path, self._entry_label(ma), ma.get("sha256",""), "", "", status))
                per_path[path] = {"status": status}
                continue
            if mb and not ma:
                status = "missing in A"
                onlyA += 1
                rows.append((path, "", "", self._entry_label(mb), mb.get("sha256",""), status))
                per_path[path] = {"status": status}
                continue

            # Both exist
            ta, tb = ma.get("type"), mb.get("type")
            ha, hb = ma.get("sha256", ""), mb.get("sha256", "")
            type_same = (ta == tb)

            if ta == "file" and tb == "file":
                if ha and hb and ha == hb:
                    status = "same"
                    same += 1
                else:
                    status = "diff"
                    diff += 1
            else:
                # Non-regulars or mixed types: treat exact same type (and for symlink, same target) as 'same'
                if type_same:
                    if ta == "symlink":
                        if ma.get("link_target", "") == mb.get("link_target", ""):
                            status = "same"
                            same += 1
                        else:
                            status = "diff"
                            diff += 1
                    else:
                        # For dirs/devices/FIFOs/etc., consider same type as 'same'
                        status = "same"
                        same += 1
                else:
                    status = "diff"
                    diff += 1

            rows.append((
                path,
                self._entry_label(ma), ha,
                self._entry_label(mb), hb,
                status
            ))
            per_path[path] = {"status": status}

        summary = {
            "counts": {"same": same, "diff": diff, "missing_in_A": onlyA, "missing_in_B": onlyB},
            "per_path": per_path
        }
        return same, diff, onlyA, onlyB, rows, summary


    def _write_html_report(
        self,
        report_path: str,
        json_path: str,
        same: int,
        diff: int,
        onlyA: int,
        onlyB: int,
        rows: list,
    ) -> None:
        # Only embed NON-"same" rows into the HTML to keep it small & fast
        rows_non_same = [
            {
                "path": path,
                "typeA": typeA,
                "shaA": ha,
                "typeB": typeB,
                "shaB": hb,
                "status": st,
            }
            for (path, typeA, ha, typeB, hb, st) in rows
            if st != "same"
        ]
        rows_js = json.dumps(rows_non_same, separators=(",", ":"))

        json_name = os.path.basename(json_path)

        with open(report_path, "w", encoding="utf-8") as f:
            f.write(f"""<!doctype html>
    <html lang="en"><head><meta charset="utf-8">
    <title>Image Compare Report</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
    body{{font-family:system-ui,-apple-system,Segoe UI,Roboto,Ubuntu,Arial,sans-serif;background:#0e1117;color:#e8ecf3;margin:24px;}}
    h1{{font-size:20px;margin:0 0 8px;}}
    .summary{{margin:8px 0 16px;color:#9aa2b2}}
    .controls{{margin:12px 0 16px;}}
    .controls label{{margin-right:12px;cursor:pointer;}}
    .controls small{{color:#9aa2b2;margin-left:4px;}}
    table{{border-collapse:collapse;width:100%;}}
    th,td{{border:1px solid #2d3541;padding:6px 8px;font-size:13px;vertical-align:top;}}
    th{{background:#1a202b;position:sticky;top:0;}}
    tr:nth-child(even){{background:#0f131a;}}
    .bad{{color:#ff7676;font-weight:600}}
    .good{{color:#00bfa6;font-weight:600}}
    .dim{{color:#9aa2b2;}}
    .path,.hash{{font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,monospace;word-break:break-all;}}
    small{{color:#9aa2b2}}
    </style>
    </head><body>
    <h1>Image Compare Report</h1>
    <div class="summary">
    A: {os.path.basename(self.path_a)} &nbsp;|&nbsp;
    B: {os.path.basename(self.path_b)}<br>
    Same: <span class="good">{same}</span> &nbsp;
    Different: <span class="bad">{diff}</span> &nbsp;
    Missing in A: {onlyA} &nbsp; Missing in B: {onlyB} &nbsp;&nbsp;
    <small>Full data in JSON: {json_name}</small>
    </div>

    <div class="controls">
    <label><input type="checkbox" id="toggleDiff" checked> Show Different</label>
    <label><input type="checkbox" id="toggleOnlyA" checked> Show Missing in A</label>
    <label><input type="checkbox" id="toggleOnlyB" checked> Show Missing in B</label>
    </div>

    <table id="diffTable">
    <thead>
        <tr>
        <th>Path</th><th>Type (A)</th><th>SHA256 (A)</th>
        <th>Type (B)</th><th>SHA256 (B)</th><th>Status</th>
        </tr>
    </thead>
    <tbody>
    </tbody>
    </table>

    <!-- Embedded JSON data for non-"same" rows only -->
    <script id="rowsData" type="application/json">{rows_js}</script>

    <script>
    const tbody = document.querySelector('#diffTable tbody');
    const allRows = JSON.parse(document.getElementById('rowsData').textContent || "[]");

    function escapeHtml(str) {{
    if (!str) return '';
    return String(str)
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;');
    }}

    function createRow(row) {{
    const tr = document.createElement('tr');
    tr.setAttribute('data-state', row.status);
    const cls = (row.status === 'diff')
        ? 'bad'
        : (row.status === 'missing in A' || row.status === 'missing in B' ? 'dim' : '');
    tr.innerHTML =
        '<td class="path">' + escapeHtml(row.path) + '</td>' +
        '<td>' + escapeHtml(row.typeA || '') + '</td>' +
        '<td class="hash">' + escapeHtml(row.shaA || '') + '</td>' +
        '<td>' + escapeHtml(row.typeB || '') + '</td>' +
        '<td class="hash">' + escapeHtml(row.shaB || '') + '</td>' +
        '<td class="' + cls + '">' + escapeHtml(row.status) + '</td>';
    return tr;
    }}

    function applyFilters() {{
    const showDiff = document.getElementById('toggleDiff').checked;
    const showOnlyA = document.getElementById('toggleOnlyA').checked;
    const showOnlyB = document.getElementById('toggleOnlyB').checked;

    tbody.querySelectorAll('tr').forEach(tr => {{
        const state = tr.getAttribute('data-state');
        let vis = true;

        if (state === 'diff' && !showDiff) vis = false;
        if (state === 'missing in A' && !showOnlyA) vis = false;
        if (state === 'missing in B' && !showOnlyB) vis = false;

        tr.style.display = vis ? '' : 'none';
    }});
    }}

    function renderInitialRows() {{
    const fragment = document.createDocumentFragment();
    allRows.forEach(row => {{
        // These rows never include "same" – only diff / missing
        fragment.appendChild(createRow(row));
    }});
    tbody.appendChild(fragment);
    applyFilters();
    }}

    ['toggleDiff','toggleOnlyA','toggleOnlyB'].forEach(id => {{
    const el = document.getElementById(id);
    if (!el) return;
    el.addEventListener('change', applyFilters);
    }});

    window.addEventListener('load', renderInitialRows);
    </script>
    </body></html>""")



    def run(self):
        # Make sure required tools are present
        for tool in ["mount", "umount", "unsquashfs"]:
            if shutil.which(tool) is None:
                raise RuntimeError(f"Required tool not found in PATH for UID {os.geteuid()}: {tool}")

        subprocess.check_call(["sudo", "-v"])
        _keep = {"run": True}
        def _keepalive():
            while _keep["run"]:
                subprocess.call(["sudo", "-n", "-v"],
                                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                time.sleep(60)
        threading.Thread(target=_keepalive, daemon=True).start()

        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        cwd = os.getcwd()
        work_root = os.path.join(cwd, f"compare_run_{stamp}")
        os.makedirs(work_root, exist_ok=True)

        report_path = os.path.join(cwd, f"compare_report_{stamp}.html")
        json_path = os.path.join(cwd, f"compare_hashes_{stamp}.json")

        # work dirs
        mA = os.path.join(work_root, "mountA")
        mB = os.path.join(work_root, "mountB")
        uA = os.path.join(work_root, "unsquashA")
        uB = os.path.join(work_root, "unsquashB")
        os.makedirs(mA, exist_ok=True)
        os.makedirs(mB, exist_ok=True)

        try:
            # Mount both images
            self._mount_image(self.path_a, mA)
            self._mount_image(self.path_b, mB)

            # Unsquash both images (uses your existing helper signatures)
            self._unsquash(mA, uA)
            self._unsquash(mB, uB)

            # Walk entries (all types) + hash regular files
            entriesA = self._walk_entries(uA)
            entriesB = self._walk_entries(uB)

            # Diff + HTML report
            same, diff, onlyA, onlyB, rows, summary = self._diff_sides(entriesA, entriesB)

            # JSON now contains all entries + summary (including missing files)
            self._write_json(json_path, entriesA, entriesB, summary, rows)

            self._write_html_report(
                report_path=report_path,
                json_path=json_path,
                same=same, diff=diff, onlyA=onlyA, onlyB=onlyB,
                rows=rows,
            )

            self.done.emit(report_path, "")
        except Exception as e:
            self.done.emit("", str(e))
        finally:
            # stop keepalive + drop sudo timestamp
            _keep["run"] = False
            for m in (mA, mB):
                self._umount(m)
            try:
                subprocess.call(["sudo", "-k"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            except Exception:
                pass
            try:
                shutil.rmtree(work_root, ignore_errors=True)
            except Exception:
                pass


class ImageCompareDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Compare Images")
        self.setFixedSize(780, 300)

        v = QVBoxLayout(self)
        v.setContentsMargins(20, 12, 20, 12)
        v.setSpacing(20)

        # Title
        title = QLabel("Compare Two Images")
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet("font-size:16px; font-weight:600; margin-bottom:8px;")
        v.addWidget(title)

        # Row of columns
        row = QHBoxLayout()
        row.setSpacing(40)
        v.addLayout(row)

        # Column 1: Image A
        colA = QVBoxLayout()
        colA.setSpacing(6)
        lblA_title = QLabel("Image A (.iso / .img)")
        lblA_title.setAlignment(Qt.AlignCenter)
        lblA_title.setStyleSheet("font-size:13px; color:#888;")
        colA.addWidget(lblA_title)

        self.btnA = QPushButton("Select Image A")
        self.btnA.setObjectName("primaryButton")
        self.btnA.setMinimumWidth(180)
        self.btnA.setFixedHeight(40)
        self.btnA.clicked.connect(self.pick_a)
        colA.addWidget(self.btnA, alignment=Qt.AlignCenter)
        row.addLayout(colA)

        # Column 2: Image B
        colB = QVBoxLayout()
        colB.setSpacing(6)
        lblB_title = QLabel("Image B (.iso / .img)")
        lblB_title.setAlignment(Qt.AlignCenter)
        lblB_title.setStyleSheet("font-size:13px; color:#888;")
        colB.addWidget(lblB_title)

        self.btnB = QPushButton("Select Image B")
        self.btnB.setObjectName("primaryButton")
        self.btnB.setMinimumWidth(180)
        self.btnB.setFixedHeight(40)
        self.btnB.clicked.connect(self.pick_b)
        colB.addWidget(self.btnB, alignment=Qt.AlignCenter)
        row.addLayout(colB)

        # Column 3: Run comparison
        colC = QVBoxLayout()
        colC.setSpacing(6)
        lblRun_title = QLabel("Compare Both Images")
        lblRun_title.setAlignment(Qt.AlignCenter)
        lblRun_title.setStyleSheet("font-size:13px; color:#888;")
        colC.addWidget(lblRun_title)

        self.runBtn = QPushButton("Run Comparison")
        self.runBtn.setObjectName("primaryButton")
        self.runBtn.setMinimumWidth(180)
        self.runBtn.setFixedHeight(40)
        self.runBtn.setEnabled(False)
        self.runBtn.clicked.connect(self.run_compare)
        colC.addWidget(self.runBtn, alignment=Qt.AlignCenter)
        row.addLayout(colC)

        # Description
        desc = QLabel(
            "This will mount both images, extract their squashfs contents, list ALL entries (files, dirs, symlinks), "
            "hash regular files, and generate a JSON + HTML report showing matches, differences, and missing files."
        )
        desc.setWordWrap(True)
        desc.setAlignment(Qt.AlignCenter)
        desc.setStyleSheet("font-size:12px; color:#888; margin-top:12px;")
        v.addWidget(desc)

        v.addStretch(1)

        # State
        self.path_a = ""
        self.path_b = ""
        self.worker = None

    # Helpers
    def _enable_run(self):
        self.runBtn.setEnabled(bool(self.path_a and self.path_b))

    def pick_a(self):
        p, _ = QFileDialog.getOpenFileName(self, "Select Image A", "", "Images (*.iso *.img);;All files (*)")
        if p:
            self.path_a = p
            self.btnA.setText(Path(p).name)
            self._enable_run()

    def pick_b(self):
        p, _ = QFileDialog.getOpenFileName(self, "Select Image B", "", "Images (*.iso *.img);;All files (*)")
        if p:
            self.path_b = p
            self.btnB.setText(Path(p).name)
            self._enable_run()

    def run_compare(self):
        if not (self.path_a and self.path_b):
            return

        self.runBtn.setEnabled(False)

        # Create a progress dialog
        self.progress_dialog = QProgressDialog("The process can last more than 5 minutes...<br>Please wait.", None, 0, 0, self)
        self.progress_dialog.setWindowTitle("Comparing Images")
        self.progress_dialog.setCancelButton(None)
        self.progress_dialog.setModal(True)

        self.worker = ImageCompareWorker(self.path_a, self.path_b)
        self.worker.done.connect(self._on_done)
        self.worker.finished.connect(self.progress_dialog.accept)
        # Start the worker thread
        self.worker.start()

        # Show the progress dialog
        self.progress_dialog.exec_()

    def _on_done(self, report_path: str, err: str):
        self.runBtn.setEnabled(True)
        self.progress_dialog.close()

        if err:
            QMessageBox.critical(self, "Compare Images", f"Failed: {err}")
            return

        m = QMessageBox(self)
        m.setWindowTitle("Compare Images")
        m.setText("Report created successfully.")
        m.setInformativeText(report_path)
        open_btn = m.addButton("Open report", QMessageBox.AcceptRole)
        m.addButton("Close", QMessageBox.RejectRole)
        m.exec_()
        if m.clickedButton() is open_btn:
            QDesktopServices.openUrl(QUrl.fromLocalFile(report_path))
