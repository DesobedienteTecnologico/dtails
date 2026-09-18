import os, pwd, subprocess
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from src.runner import (
    run_selected_actions,
    run_selected_actions_stream,
    run_selected_actions_stream_docker,
    container_build_available,
    remove_container_build_image,
    build_container_image,
)

from PyQt5.QtCore import Qt, QSize, QThread, pyqtSignal, pyqtSlot, QUrl
from PyQt5.QtGui import QIcon, QPixmap, QDesktopServices
from PyQt5.QtWidgets import (
    QAction,
    QApplication,
    QDialog,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QScrollArea,
    QTabBar,
    QTabWidget,
    QVBoxLayout,
    QWidget,
    QPushButton,
    QMessageBox,
    QSizePolicy,
    QPlainTextEdit,
    QStyle,
    QInputDialog,
    QCheckBox,
    QProgressDialog
)

from src.state import AppState, load_options, save_options
from src.theme import apply_theme
from src.compare_images import ImageCompareDialog
from src import tails_download as td

_REPO = Path(__file__).resolve().parents[1]


class TailsWorker(QThread):
    """Runs a download/verify function off the UI thread. `fn(progress_cb)` must
    return (ok: bool, message: str); progress_cb takes (done_bytes, total_bytes)."""
    progress = pyqtSignal(int)            # percent 0..100
    done = pyqtSignal(bool, str)

    def __init__(self, fn, parent=None):
        super().__init__(parent)
        self._fn = fn

    def run(self):
        def cb(done, total):
            self.progress.emit(int(done * 100 / total) if total else 0)
        try:
            ok, msg = self._fn(cb)
            self.done.emit(bool(ok), msg)
        except Exception as e:
            self.done.emit(False, str(e))

# ---------- helpers: widgets ----------

def make_nav_buttons(go_back, go_next=None, go_write=None, back_text="Back", next_text="Next", write_text="Write Image"):
    nav = QHBoxLayout()
    nav.setContentsMargins(0, 12, 0, 0)
    nav.setSpacing(8)
    nav.addStretch(1)
    def make_btn(text, callback):
        btn = QPushButton(text)
        btn.setObjectName("navButton")
        btn.setMinimumWidth(120)
        btn.setFixedHeight(40)
        if callback:
            btn.clicked.connect(callback)
        return btn
    nav.addWidget(make_btn(back_text, go_back))
    if go_next:
        nav.addWidget(make_btn(next_text, go_next))
    if go_write:
        write_btn = make_btn(write_text, go_write)
        write_btn.setObjectName("WriteButton")
        nav.addWidget(write_btn)
    return nav

class NoSwitchTabWidget(QTabWidget):
    def keyPressEvent(self, e):
        if (e.modifiers() & Qt.ControlModifier) and e.key() in (
            Qt.Key_Tab,
            Qt.Key_Backtab,
            Qt.Key_PageUp,
            Qt.Key_PageDown,
        ):
            e.accept()
            return
        super().keyPressEvent(e)


class LeftTabBar(QTabBar):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setDrawBase(False)
        self.setExpanding(True)
        self.setElideMode(Qt.ElideRight)
        self.setIconSize(QSize(18, 18))
    def tabSizeHint(self, index):
        base = super().tabSizeHint(index)
        return QSize(max(170, base.width()), 40)

def open_url_safely(url: str) -> None:
    if QDesktopServices.openUrl(QUrl(url)):
        return
    # If we are root, we will run the web browser as user
    try_user = os.environ.get("SUDO_USER") or os.environ.get("PKEXEC_UID") or ""
    if os.geteuid() == 0 and try_user:
        try:
            pw = pwd.getpwnam(try_user)
            uid = pw.pw_uid
            runtime = f"/run/user/{uid}"
            env = os.environ.copy()
            env.setdefault("XDG_RUNTIME_DIR", runtime)
            env.setdefault("DBUS_SESSION_BUS_ADDRESS", f"unix:path={runtime}/bus")
            cmd = ["sudo", "-u", try_user, "xdg-open", url]
            try:
                subprocess.Popen(cmd, env=env)
                return
            except Exception:
                subprocess.Popen(["sudo", "-u", try_user, "gio", "open", url], env=env)
                return
        except Exception:
            pass

    try:
        subprocess.Popen(["xdg-open", url])
    except Exception:
        pass

# ---------- dialogs ----------

class IntroDialog(QDialog):
    def __init__(self, on_continue, parent=None):
        super().__init__(parent)
        self.setWindowTitle("DTails")
        self.setFixedSize(520, 280)
        self.setWindowIcon(QIcon("img/dtails.png"))
        self.setWindowFlags(Qt.Window | Qt.CustomizeWindowHint | Qt.WindowTitleHint)

        v = QVBoxLayout(self)
        v.setContentsMargins(20, 16, 20, 16)
        v.setSpacing(12)

        logo = QLabel(alignment=Qt.AlignCenter)
        pm = QPixmap("img/dtails.png")
        if not pm.isNull():
            logo.setPixmap(pm)
            logo.setScaledContents(True)
            logo.setFixedSize(100, 39)
        v.addWidget(logo, alignment=Qt.AlignCenter)
        
        title = QLabel("<br>Welcome")
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet("font-size:18px; font-weight:600; margin-top:4px;")
        v.addWidget(title)

        body = QLabel(
            "Remaster a Debian based OS with a guided and streamlined flow<br><br><br>Modify, Flash, Compare."
        )
        body.setWordWrap(True)
        body.setAlignment(Qt.AlignCenter)
        body.setStyleSheet("font-size:13px; color:#9aa2b2;")
        v.addWidget(body)

        v.addStretch(1)

        btn = QPushButton("Continue")
        btn.setObjectName("primaryButton")
        btn.setMinimumWidth(140)
        btn.setFixedHeight(38)
        btn.clicked.connect(lambda: (on_continue(), self.accept()))
        v.addWidget(btn, alignment=Qt.AlignCenter)

def show_about(parent: QWidget) -> None:
    dlg = QDialog(parent)
    dlg.setWindowTitle("About")
    dlg.setFixedSize(400, 300)

    layout = QVBoxLayout(dlg)

    image_label = QLabel()
    pixmap = QPixmap("img/dtails.png")
    image_label.setPixmap(pixmap)
    image_label.setScaledContents(True)
    image_label.setFixedSize(100, 39)
    layout.addWidget(image_label, alignment=Qt.AlignCenter)

    text_label = QLabel()
    text_label.setWordWrap(True)
    text_label.setTextFormat(Qt.RichText)
    text_label.setOpenExternalLinks(True)
    text_label.setAlignment(Qt.AlignCenter)
    text_label.setText(
        "Remastering tool for Debian Live based OS.<br><br>"
        "<b>Version:</b> 2.0<br>"
        "<b>Developed by:</b> Desobediente Tecnológico<br><br>"
        '<a href="https://github.com/DesobedienteTecnologico/dtails" style="color:#56347C; text-decoration:none;">'
        "View project on GitHub</a>"
    )
    layout.addWidget(text_label)

    close_button = QPushButton("Close")
    close_button.clicked.connect(dlg.close)
    layout.addWidget(close_button, alignment=Qt.AlignCenter)

    dlg.exec_()


def choose_block_device(on_selected):
    if os.name != "posix" or not os.path.isdir("/sys"):
        QMessageBox.warning(None, "Unsupported OS", "Device selection is supported only on Linux.")
        return None

    class _DeviceRow(QWidget):
        def __init__(self, dev: dict, on_toggle, parent=None):
            super().__init__(parent)
            self.setObjectName("listRow")
            self._dev = dev
            self._on_toggle = on_toggle

            lay = QHBoxLayout(self)
            lay.setContentsMargins(0, 0, 0, 0)
            lay.setSpacing(10)

            main = f"{dev['path']} — {dev['size']}"
            self.chk = QCheckBox(main)
            self.chk.setCursor(Qt.PointingHandCursor)
            self.chk.stateChanged.connect(lambda _: self._on_toggle(self._dev, self.chk.isChecked()))
            lay.addWidget(self.chk, 1)

            details = " ".join(x for x in (dev.get("vendor") or "", dev.get("model") or dev.get("name", "")) if x).strip()
            self.details_lbl = QLabel(details)
            self.details_lbl.setStyleSheet("color:#888;")
            lay.addWidget(self.details_lbl, 0, Qt.AlignRight)

        def set_checked(self, val: bool):
            blocked = self.chk.blockSignals(True)
            self.chk.setChecked(bool(val))
            self.chk.blockSignals(blocked)

        def mousePressEvent(self, ev):
            self.set_checked(not self.chk.isChecked())
            self._on_toggle(self._dev, self.chk.isChecked())
            ev.accept()

    dlg = QDialog()
    dlg.setWindowTitle("Select Storage")
    dlg.resize(480, 340)

    layout = QVBoxLayout(dlg)
    layout.addWidget(QLabel("Please select a device from the list carefully:"))

    list_widget = QListWidget()
    list_widget.setSelectionMode(QListWidget.NoSelection)
    list_widget.setSpacing(6)
    list_widget.setStyleSheet("QListWidget{ padding:8px; } QListWidget::item{ margin:4px; }")
    layout.addWidget(list_widget)

    btn_row = QHBoxLayout()
    btn_row.addStretch(1)
    ok_btn = QPushButton("Select")
    ok_btn.setEnabled(False)
    cancel_btn = QPushButton("Cancel")
    btn_row.addWidget(ok_btn)
    btn_row.addWidget(cancel_btn)
    layout.addLayout(btn_row)

    # --- helpers ---
    def _format_size(n):
        for unit in ["B", "KB", "MB", "GB", "TB", "PB"]:
            if n < 1000:
                return f"{n:.1f}{unit}" if unit != "B" else f"{int(n)}{unit}"
            n = n / 1000.0
        return f"{n:.1f}PB"

    def gather():
        try:
            out = subprocess.check_output(
                ["lsblk", "-o", "NAME,TYPE,SIZE,MOUNTPOINT,RM,MODEL,VENDOR", "-P", "-b"],
                text=True,
            )
        except Exception:
            return []
        devices = []
        for line in out.splitlines():
            info = {}
            for part in line.split():
                if "=" not in part:
                    continue
                k, v = part.split("=", 1)
                info[k] = v.strip('"')
            if info.get("TYPE") != "disk":
                continue
            name = info.get("NAME")
            path = f"/dev/{name}" if name else None
            if not path or not os.path.exists(path):
                continue
            if name.startswith("loop"):
                continue
            size = int(info.get("SIZE", "0"))
            model = (info.get("MODEL") or "").strip()
            vendor = (info.get("VENDOR") or "").strip()
            devices.append(
                {
                    "path": path,
                    "size": _format_size(size),
                    "removable": info.get("RM") == "1",
                    "model": model,
                    "vendor": vendor,
                    "name": name,
                }
            )
        devices.sort(key=lambda d: (not d["removable"], d["path"]))
        return devices

    selected_dev: Optional[dict] = None

    def _on_row_toggled(dev: dict, checked: bool):
        nonlocal selected_dev
        if checked:
            for i in range(list_widget.count()):
                it = list_widget.item(i)
                w = list_widget.itemWidget(it)
                if w and w is not dev and w._dev["path"] != dev["path"]:
                    w.set_checked(False)
            selected_dev = dev
            ok_btn.setEnabled(True)
        else:
            if selected_dev and selected_dev["path"] == dev["path"]:
                selected_dev = None
                ok_btn.setEnabled(False)

    def accept():
        if not selected_dev:
            return
        dlg.selected = selected_dev
        dlg.accept()

    ok_btn.clicked.connect(accept)
    cancel_btn.clicked.connect(dlg.reject)

    devices = gather()
    for dev in devices:
        row_widget = _DeviceRow(dev, on_toggle=_on_row_toggled)
        item = QListWidgetItem(list_widget)
        item.setSizeHint(QSize(10, 40))
        item.setData(Qt.UserRole, dev)
        list_widget.addItem(item)
        list_widget.setItemWidget(item, row_widget)

    if devices:
        first = list_widget.itemWidget(list_widget.item(0))
        if first:
            first.set_checked(True)
            _on_row_toggled(first._dev, True)

    if dlg.exec_() == QDialog.Accepted:
        chosen = getattr(dlg, "selected", None)
        if chosen:
            on_selected(chosen)
    return None


class LiveLogDialog(QDialog):
    append_text = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Live Log")
        self.setMinimumSize(740, 420)
        self.setWindowFlags(Qt.Window | Qt.CustomizeWindowHint | Qt.WindowTitleHint)

        v = QVBoxLayout(self)
        v.setContentsMargins(8, 8, 8, 8)
        v.setSpacing(6)

        self.out = QPlainTextEdit(self)
        self.out.setReadOnly(True)
        self.out.setLineWrapMode(QPlainTextEdit.NoWrap)
        self.out.setStyleSheet("font-family: Consolas, Menlo, monospace; font-size:12px;")
        v.addWidget(self.out)

        row = QHBoxLayout()
        row.addStretch(1)

        warn_lbl = QLabel("(Do not close until finished)")
        warn_lbl.setStyleSheet("color:#d9534f; font-size:12px; margin-right:8px;")
        row.addWidget(warn_lbl, 0, Qt.AlignVCenter)

        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.accept)
        row.addWidget(close_btn, 0, Qt.AlignVCenter)

        v.addLayout(row)


        self._auto_follow = True
        sb = self.out.verticalScrollBar()
        sb.valueChanged.connect(self._on_scroll_value_changed)
        sb.rangeChanged.connect(self._maybe_follow_bottom)

        self.append_text.connect(self._append_chunk)

    @pyqtSlot(str)
    def _append_chunk(self, chunk: str) -> None:
        cursor = self.out.textCursor()
        cursor.movePosition(cursor.End)
        cursor.insertText(chunk)
        if self._auto_follow:
            self._scroll_to_bottom()

    def _scroll_to_bottom(self):
        sb = self.out.verticalScrollBar()
        sb.setValue(sb.maximum())

    def _on_scroll_value_changed(self, _):
        sb = self.out.verticalScrollBar()
        self._auto_follow = (sb.value() >= sb.maximum() - 1)

    def _maybe_follow_bottom(self, _min, _max):
        if self._auto_follow:
            self._scroll_to_bottom()

    def sink(self, chunk: str) -> None:
        self.append_text.emit(chunk)

class LogWorker(QThread):
    chunk = pyqtSignal(str)
    finished_code = pyqtSignal(int)

    def __init__(self, state, image_path: str, cwd: str):
        super().__init__()
        self.state = state
        self.image_path = image_path
        self.cwd = cwd
        self.log_path = os.path.join(self.cwd, "log.txt")

    def run(self):
        exit_code = 0
        try:
            with open(self.log_path, "w", encoding="utf-8") as f:

                def _sink(s: str):
                    f.write(s)
                    f.flush()
                    self.chunk.emit(s)

                build_fn = (run_selected_actions_stream_docker
                            if getattr(self.state, "use_container_build", False)
                            else run_selected_actions_stream)
                build_fn(
                    self.state,
                    self.image_path,
                    sink=_sink,
                    cwd=self.cwd
                )

        except Exception as e:
            err_line = f"\n[ERROR] {e}\n"
            self.chunk.emit(err_line)
            try:
                with open(self.log_path, "a", encoding="utf-8") as f:
                    f.write(err_line)
            except Exception:
                pass
            exit_code = 1

        self.finished_code.emit(exit_code)

class ContainerImageBuildWorker(QThread):
    chunk = pyqtSignal(str)
    finished_ok = pyqtSignal(bool)

    def __init__(self, cwd: str):
        super().__init__()
        self.cwd = cwd

    def run(self):
        def _sink(s: str):
            self.chunk.emit(s)
        ok = False
        try:
            ok = build_container_image(sink=_sink, cwd=self.cwd)
        except Exception as e:
            self.chunk.emit(f"\n[ERROR] {e}\n")
        self.finished_ok.emit(ok)


class DDFlashWorker(QThread):
    progress = pyqtSignal(int)
    finished = pyqtSignal(int, str)

    def __init__(self, image_path: str, device_path: str, parent=None):
        super().__init__(parent)
        self.image_path = image_path
        self.device_path = device_path

    def run(self):
        try:
            total = os.path.getsize(self.image_path)
        except Exception as e:
            self.finished.emit(1, f"Could not stat image: {e}")
            return

        as_root = (os.geteuid() == 0)
        base_cmd = [
            "dd",
            f"if={self.image_path}",
            f"of={self.device_path}",
            "bs=4M",
            "status=progress",
            "conv=fsync",
        ]
        cmd = base_cmd if as_root else ["sudo"] + base_cmd

        try:
            proc = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
            )
        except Exception as e:
            self.finished.emit(1, f"Failed to start dd: {e}")
            return

        try:
            for line in proc.stdout:
                line = line.strip()
                if not line:
                    continue
                parts = line.split()
                if parts and parts[0].isdigit():
                    try:
                        copied = int(parts[0])
                        pct = int((copied / total) * 100)
                        if pct > 100:
                            pct = 100
                        self.progress.emit(pct)
                    except Exception:
                        pass
        except Exception as e:
            proc.kill()
            self.finished.emit(1, f"Error while running dd: {e}")
            return

        ret = proc.wait()
        if ret == 0:
            self.progress.emit(100)
            self.finished.emit(0, "")
        else:
            self.finished.emit(ret, f"dd exited with code {ret}")


# ---------- helper widget for an installable item ----------
class InstallItemWidget(QWidget):
    def __init__(self, state, item_obj: dict, on_toggle, parent=None):
        super().__init__(parent)
        self.setObjectName("listRow")
        self.state = state
        self.item = item_obj
        self.on_toggle = on_toggle
        name = item_obj.get("name") or "Item"
        version = self.state.get_effective_version(name) or (item_obj.get("version") or "")
        size = AppState._size_from_item(item_obj)
        size_disp = f" ({AppState._fmt_bytes(size)})" if size is not None else ""

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)

        self.chk = QCheckBox(f"{name}{size_disp}")
        self.chk.setCursor(Qt.PointingHandCursor)
        self.chk.stateChanged.connect(lambda: self.on_toggle(name, self.chk.isChecked()))
        layout.addWidget(self.chk, 1)

        self.version_lbl = QLabel(f"v{version}" if version else "")
        self.version_lbl.setStyleSheet("color:#888;")
        layout.addWidget(self.version_lbl, 0, Qt.AlignRight)

        self.btn = QPushButton()
        self.btn.setToolTip("Edit version")
        self.btn.setIcon(self.style().standardIcon(QStyle.SP_FileDialogDetailedView))
        self.btn.setFixedSize(26, 26)
        self.btn.clicked.connect(self._edit_version)
        layout.addWidget(self.btn, 0, Qt.AlignRight)

    def toggle(self, force: bool = None):
        if force is None:
            new_state = (self.chk.checkState() != Qt.Checked)
        else:
            new_state = bool(force)
        self.chk.setChecked(new_state)

    def mousePressEvent(self, event):
        child = self.childAt(event.pos())
        if child is self.btn:
            return super().mousePressEvent(event)
        self.toggle()
        event.accept()

    def keyPressEvent(self, event):
        if event.key() in (Qt.Key_Space, Qt.Key_Return, Qt.Key_Enter):
            self.toggle()
            event.accept()
        else:
            super().keyPressEvent(event)

    def _edit_version(self):
        name = (self.item.get("name") or "").strip()
        cur = self.state.get_effective_version(name) or (self.item.get("version") or "")
        text, ok = QInputDialog.getText(self, f"{name}", "Version:", text=cur)
        if ok:
            if not self.state.set_version_override(name, text):
                QMessageBox.warning(
                    self, "Invalid version",
                    "Version may only contain letters, digits, '.', '_' and '-'.",
                )
                return
            self.version_lbl.setText(f"v{text.strip()}" if text.strip() else "")

# ---------- tabs ----------

class StartTab(QWidget):
    def __init__(self, state: AppState, parent=None):
        super().__init__(parent)
        self.state = state
        v = QVBoxLayout(self)
        v.setContentsMargins(12, 6, 12, 6)
        v.setSpacing(6)
        logo_wrap = QVBoxLayout()
        logo_wrap.addStretch(1)
        logo = QLabel(alignment=Qt.AlignCenter)
        pix = QPixmap("img/dtails.png")
        if not pix.isNull():
            logo.setPixmap(pix)
            logo.setScaledContents(True)
            logo.setFixedSize(100, 39)
        logo_wrap.addWidget(logo, alignment=Qt.AlignCenter)
        logo_wrap.addStretch(1)
        v.addLayout(logo_wrap)
        self.btn_image = self._btn("Select Image", "primaryButton", self.select_image, "Ctrl+1", True)
        self.btn_storage = self._btn("Select Storage", "primaryButton", self.pick_storage, "Ctrl+2", False)
        self.btn_manage = self._btn("Add / Remove Software", "primaryButton", self.to_manage, "Ctrl+3", False)
        row = QHBoxLayout()
        row.setSpacing(40)
        row.addStretch(1)
        row.addLayout(self._col(self.btn_image, "Image to modify"))
        row.addLayout(self._col(self.btn_storage, "Storage to flash"))
        row.addLayout(self._col(self.btn_manage, "Manage Software"))
        row.addStretch(1)
        v.addLayout(row)

    def _btn(self, text, obj, slot, shortcut, enabled):
        b = QPushButton(text)
        b.setObjectName(obj)
        if shortcut:
            b.setShortcut(shortcut)
        b.clicked.connect(slot)
        b.setEnabled(enabled)
        b.setMinimumWidth(150)
        b.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        return b

    def _col(self, button, label_text):
        col = QVBoxLayout()
        col.setSpacing(4)
        lbl = QLabel(label_text, alignment=Qt.AlignCenter)
        lbl.setWordWrap(True)
        lbl.setStyleSheet("font-size: 12px;")
        col.addWidget(lbl)
        col.addWidget(button)
        return col

    def _refresh_summary_if_present(self):
        win = self.window()
        if hasattr(win, "summary_tab") and win.summary_tab:
            win.summary_tab.refresh()

    def select_image(self):
        opts = ["Browse for a local file…",
                "Download the latest Tails image…",
                "Verify an image (SHA256 + GPG)…"]
        prompt = ("Choose image source:\n\n"
                  "You can also download and verify images on the official Tails site:\n"
                  "https://tails.net/install/download/index.en.html")
        choice, ok = QInputDialog.getItem(self, "Image", prompt, opts, 0, False)
        if not ok:
            return
        if choice == opts[0]:
            self._browse_image()
        elif choice == opts[1]:
            self._download_image()
        else:
            self._verify_image()

    def _set_image(self, path: str):
        self.state.selected_image = path
        self.btn_image.setText(Path(path).name)
        self.btn_storage.setEnabled(True)
        self._refresh_summary_if_present()

    def _browse_image(self):
        file_filter = "Image Files (*.iso *.img);;All Files (*)"
        path, _ = QFileDialog.getOpenFileName(self, "Select Image File", "", file_filter)
        if path:
            self._set_image(path)

    def _download_image(self):
        try:
            rel = td.fetch_release()
        except Exception as e:
            QMessageBox.critical(self, "Download", f"Could not fetch release info:\n{e}")
            return
        items = [
            f"USB image  tails-amd64-{rel['version']}.img  ({(rel['img']['size'] or 0)//(1024*1024)} MB)",
            f"ISO image  tails-amd64-{rel['version']}.iso  ({(rel['iso']['size'] or 0)//(1024*1024)} MB)",
        ]
        choice, ok = QInputDialog.getItem(
            self, f"Download Tails {rel['version']}", "Choose image:", items, 0, False)
        if not ok:
            return
        entry = rel["img"] if choice.startswith("USB") else rel["iso"]
        dest = str(_REPO / entry["filename"])
        if os.path.exists(dest) and QMessageBox.question(
                self, "Overwrite?",
                f"{entry['filename']} already exists.\nRe-download it?") != QMessageBox.Yes:
            return

        dlg = QProgressDialog(f"Downloading {entry['filename']}…", None, 0, 100, self)
        dlg.setWindowModality(Qt.WindowModal)
        dlg.setCancelButton(None)
        dlg.setMinimumDuration(0)
        dlg.setValue(0)
        self._dl_worker = TailsWorker(
            lambda cb: (td.download(entry["url"], dest, cb, entry["size"]), (True, dest))[1])
        self._dl_worker.progress.connect(dlg.setValue)

        def on_done(ok_, msg):
            dlg.close()
            if not ok_:
                QMessageBox.critical(self, "Download failed", msg)
                return
            self._set_image(dest)
            if QMessageBox.question(self, "Verify?",
                                    "Download complete.\nVerify SHA256 + GPG signature now?"
                                    ) == QMessageBox.Yes:
                self._run_verify(dest, rel)
        self._dl_worker.done.connect(on_done)
        self._dl_worker.start()
        dlg.exec_()

    def _verify_image(self):
        start = self.state.selected_image or str(_REPO)
        path, _ = QFileDialog.getOpenFileName(
            self, "Select image to verify", start, "Image Files (*.iso *.img);;All Files (*)")
        if path:
            self._run_verify(path)

    def _run_verify(self, path: str, rel=None):
        dlg = QProgressDialog(f"Verifying {Path(path).name}…", None, 0, 100, self)
        dlg.setWindowModality(Qt.WindowModal)
        dlg.setCancelButton(None)
        dlg.setValue(0)
        self._vf_worker = TailsWorker(lambda cb: td.verify_image(path, release=rel, progress_cb=cb))
        self._vf_worker.progress.connect(dlg.setValue)

        def on_done(ok_, report):
            dlg.close()
            box = QMessageBox(self)
            box.setIcon(QMessageBox.Information if ok_ else QMessageBox.Critical)
            box.setWindowTitle("Verified" if ok_ else "NOT verified")
            box.setText("✔ VERIFIED" if ok_ else "✘ NOT VERIFIED")
            box.setDetailedText(report)
            box.exec_()
        self._vf_worker.done.connect(on_done)
        self._vf_worker.start()
        dlg.exec_()

    def pick_storage(self):
        opts = ["No — just build a DTails.img file",
                "Yes — choose a device to flash directly"]
        choice, ok = QInputDialog.getItem(
            self, "Storage", "Flash the result to a physical device?", opts, 0, False)
        if not ok:
            return
        if choice == opts[0]:
            self.on_device_chosen({})
        else:
            choose_block_device(self.on_device_chosen)

    def on_device_chosen(self, dev: dict):
        dev = dev or {}
        self.state.selected_device = dev
        if not dev:
            text = "Image-only build (no device)"
        else:
            vendor = dev.get("vendor") or ""
            model = dev.get("model") or dev.get("name", "")
            size = dev.get("size") or ""
            text = " ".join(x for x in (vendor, size, model) if x).strip() or "Storage selected"
        self.btn_storage.setText(text)
        self.btn_manage.setEnabled(True)
        self._refresh_summary_if_present()

    def to_manage(self):
        p = self.parent()
        while p and not isinstance(p, QTabWidget):
            p = p.parent()
        if p:
            p.setCurrentIndex(1)

class InstallTab(QWidget):
    def __init__(self, state: AppState, go_back, go_next, parent=None):
        super().__init__(parent)
        self.state = state
        self.go_back = go_back
        self.go_next = go_next
        outer = QVBoxLayout(self)
        outer.setContentsMargins(6, 4, 6, 4)
        outer.setSpacing(6)
        row = QHBoxLayout()
        self.tabs = QTabWidget()
        self.tabs.setObjectName("categoryTabs")
        self.tabs.setTabBar(LeftTabBar(self.tabs))
        self.tabs.setTabPosition(QTabWidget.West)
        row.addWidget(self.tabs)
        outer.addLayout(row)
        nav_layout = make_nav_buttons(go_back, self._collect_and_next)
        outer.addLayout(nav_layout)

        self.next_btn = None
        for i in range(nav_layout.count()):
            item = nav_layout.itemAt(i)
            w = item.widget() if item is not None else None
            if isinstance(w, QPushButton) and w.text() == "Next":
                self.next_btn = w
                break

        if self.next_btn:
            self.next_btn.setEnabled(False)
        self._lists_by_key: Dict[str, QListWidget] = {}
        self._build_tabs_from_options()

    def _category_meta(self) -> List[Tuple[str, str, str, List[dict]]]:
        data = self.state.options_json or {}
        add = data.get("add_software")
        results: List[Tuple[str, str, str, List[dict]]] = []

        if isinstance(add, dict) and isinstance(add.get("categories"), list):
            for cat in add["categories"]:
                if not isinstance(cat, dict):
                    continue
                key = (cat.get("key") or "").strip().lower()
                if not key:
                    continue
                title = cat.get("title") or key.title()
                icon_path = cat.get("icon") or "img/dtails.png"
                items = cat.get("items") or []
                results.append((key, title, icon_path, items))
            return results

        if isinstance(add, dict):
            meta = data.get("add_software_meta", {})
            for key, items in add.items():
                if key == "categories":
                    continue
                k = (key or "").strip().lower()
                if not k:
                    continue
                m = meta.get(k, {}) if isinstance(meta, dict) else {}
                title = m.get("title") or k.title()
                icon_path = m.get("icon") or "img/dtails.png"
                items_list = items or []
                results.append((k, title, icon_path, items_list))

        return results

    def _build_tabs_from_options(self) -> None:
        self._lists_by_key.clear()
        while self.tabs.count():
            self.tabs.removeTab(0)

        cats = self._category_meta()
        if not cats:
            placeholder = QWidget()
            v = QVBoxLayout(placeholder)
            v.setContentsMargins(16, 16, 16, 16)
            msg = QLabel("No installable categories found in options.json → add_software.categories.")
            msg.setWordWrap(True)
            v.addWidget(msg)
            self.tabs.addTab(placeholder, "No categories")
            return

        for key, title, icon_path, items in cats:
            w = QWidget()
            v = QVBoxLayout(w)
            v.setSpacing(6)
            v.setContentsMargins(8, 8, 8, 8)
            v.addWidget(QLabel(f"Select {title} software to install"))
            lw = QListWidget()
            lw.setSelectionMode(QListWidget.NoSelection)
            v.addWidget(lw)
            idx = self.tabs.addTab(w, QIcon(), "")
            self._inject_tab_header(idx, title, icon_path)
            self._lists_by_key[key] = lw
            self._fill_list_for_category(lw, items)

        self.tabs.setCurrentIndex(0)

    def _inject_tab_header(self, index: int, title: str, icon_path: str) -> None:
        bar = self.tabs.tabBar()
        container = QWidget()
        lay = QHBoxLayout(container)
        lay.setContentsMargins(10, 6, 10, 6)
        lay.setSpacing(8)
        ico_label = QLabel()
        pm = QPixmap(icon_path)
        if not pm.isNull():
            ico_label.setPixmap(pm.scaled(18, 18, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        ico_label.setFixedSize(18, 18)
        lay.addWidget(ico_label)
        txt = QLabel(title)
        txt.setObjectName("tabTextLabel")
        txt.setAlignment(Qt.AlignVCenter | Qt.AlignLeft)
        txt.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        lay.addWidget(txt, 1)
        bar.setTabText(index, "")
        bar.setTabIcon(index, QIcon())
        bar.setTabButton(index, QTabBar.LeftSide, container)
        bar.setMinimumWidth(180)

    def _fill_list_for_category(self, lw: QListWidget, items: List[dict]) -> None:
        lw.clear()
        for it in items:
            name = (it.get("name") or "").strip()
            if not name:
                continue
            size = AppState._size_from_item(it)
            row_widget = InstallItemWidget(self.state, it, on_toggle=lambda n, checked: self._on_toggle_item(lw, n, checked))
            list_item = QListWidgetItem(lw)
            list_item.setSizeHint(QSize(10, 40))
            list_item.setData(Qt.UserRole, name)
            lw.addItem(list_item)
            lw.setItemWidget(list_item, row_widget)

        lw.setSpacing(6)
        lw.setStyleSheet("""
            QListWidget{ padding:8px; }
            QListWidget::item{ margin:4px; }
        """)

    def _on_toggle_item(self, list_widget: QListWidget, name: str, checked: bool):
        self._update_next_enabled()

    def _checked_names(self, lw: QListWidget) -> List[str]:
        names: List[str] = []
        for i in range(lw.count()):
            it = lw.item(i)
            w = lw.itemWidget(it)
            if w is not None and w.chk.isChecked():
                names.append(it.data(Qt.UserRole) or it.text())
        return names

    def _collect_and_next(self) -> None:
        selected: List[str] = []
        for lw in self._lists_by_key.values():
            selected.extend(self._checked_names(lw))

        if not selected:
            QMessageBox.warning(
                self,
                "No software selected",
                "Please select at least one item to install before continuing."
            )
            if getattr(self, "next_btn", None):
                self.next_btn.setEnabled(False)
            return

        self.state.selected_additions = selected
        self.go_next()


    def _update_next_enabled(self) -> None:
        any_selected = any(self._checked_names(lw) for lw in self._lists_by_key.values())
        if getattr(self, "next_btn", None):
            self.next_btn.setEnabled(any_selected)

class RemoveItemWidget(QWidget):
    def __init__(self, name: str, size_bytes: Optional[int], on_toggle, parent=None):
        super().__init__(parent)
        self.setObjectName("listRow")
        self._name = name
        self._on_toggle = on_toggle

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)

        size_disp = f" ({AppState._fmt_bytes(size_bytes)})" if size_bytes is not None else ""
        self.chk = QCheckBox(f"{name}{size_disp}")
        self.chk.setCursor(Qt.PointingHandCursor)
        self.chk.stateChanged.connect(lambda: self._on_toggle(self._name, self.chk.isChecked()))
        layout.addWidget(self.chk, 1)

    def toggle(self, force: bool = None):
        if force is None:
            new_state = (self.chk.checkState() != Qt.Checked)
        else:
            new_state = bool(force)
        self.chk.setChecked(new_state)

    def mousePressEvent(self, event):
        self.toggle()
        event.accept()

    def keyPressEvent(self, event):
        if event.key() in (Qt.Key_Space, Qt.Key_Return, Qt.Key_Enter):
            self.toggle()
            event.accept()
        else:
            super().keyPressEvent(event)


class RemoveTab(QWidget):
    def __init__(self, state: AppState, go_back, go_next, parent=None):
        super().__init__(parent)
        self.state = state
        self._go_next = go_next

        v = QVBoxLayout(self)
        v.setContentsMargins(6, 4, 6, 4)
        v.setSpacing(6)

        v.addWidget(QLabel("Select the software to be removed (optional)"))

        self.list = QListWidget()
        self.list.setSelectionMode(QListWidget.NoSelection)
        self.list.setSpacing(6)
        self.list.setStyleSheet("""
            QListWidget{ padding:8px; }
            QListWidget::item{ margin:4px; }
        """)
        v.addWidget(self.list)

        v.addLayout(make_nav_buttons(go_back, self._proceed))

    def _on_toggle_item(self, name: str, checked: bool):
        pass

    def _add_item(self, name: str, size_bytes: Optional[int]) -> None:
        row_widget = RemoveItemWidget(name, size_bytes, on_toggle=self._on_toggle_item)
        list_item = QListWidgetItem(self.list)
        list_item.setSizeHint(QSize(10, 40))
        list_item.setData(Qt.UserRole, name)
        self.list.addItem(list_item)
        self.list.setItemWidget(list_item, row_widget)

    def populate_from_options(self) -> None:
        self.list.clear()
        data = self.state.options_json or {}
        for r in data.get("remove_software", []):
            if not isinstance(r, dict):
                continue
            name = (r.get("name") or "").strip()
            if not name:
                continue
            size = AppState._size_from_item(r)
            self._add_item(name, size)

    def _proceed(self) -> None:
        selected = []
        for i in range(self.list.count()):
            it = self.list.item(i)
            w = self.list.itemWidget(it)
            if w is not None and w.chk.isChecked():
                selected.append(it.data(Qt.UserRole) or it.text())
        self.state.selected_deletions = selected
        self._go_next()

class SummaryTab(QWidget):
    def __init__(self, state: AppState, go_back, on_write_image, parent=None):
        super().__init__(parent)
        self.state = state
        self.on_write_image = on_write_image
        v = QVBoxLayout(self)
        v.setContentsMargins(6, 4, 6, 4)
        v.setSpacing(6)
        title = QLabel("Summary", alignment=Qt.AlignLeft)
        title.setStyleSheet("font-size:15px; font-weight:600;")
        v.addWidget(title)
        self.scroll = QScrollArea()
        self.scroll.setObjectName("summaryScroll")
        self.scroll.setStyleSheet("background: transparent;")
        self.scroll.setWidgetResizable(True)
        v.addWidget(self.scroll)
        inner = QWidget()
        inner_v = QVBoxLayout(inner)
        inner_v.setContentsMargins(0, 0, 0, 0)
        inner_v.setSpacing(0)
        self.lbl = QLabel("", alignment=Qt.AlignTop)
        self.lbl.setWordWrap(True)
        self.lbl.setMargin(8)
        inner_v.addWidget(self.lbl)
        self.scroll.setWidget(inner)

        container_row = QHBoxLayout()
        self.container_chk = QCheckBox("Build inside pinned Docker container (reproducible across machines)")
        self.container_chk.toggled.connect(self._on_container_toggle)
        container_row.addWidget(self.container_chk)
        container_row.addStretch(1)
        self.build_img_btn = QPushButton("Build Docker Image")
        self.build_img_btn.setStyleSheet(
            "QPushButton { background-color: #eaf2ff; color: #1a1a1a; border: 1px solid #c3d6f0; "
            "border-radius: 4px; padding: 4px 10px; }"
            "QPushButton:disabled { background-color: #f0f0f0; color: #999999; border-color: #dddddd; }"
        )
        self.build_img_btn.clicked.connect(self._build_container_image)
        container_row.addWidget(self.build_img_btn)
        v.addLayout(container_row)
        self._refresh_container_availability()

        v.addLayout(make_nav_buttons(go_back=go_back, go_write=self._write))
        self.refresh()
    def refresh(self) -> None:
        self.lbl.setText(self.state.summary_html())
    def _on_container_toggle(self, checked: bool) -> None:
        self.state.use_container_build = bool(checked)
    def _refresh_container_availability(self) -> None:
        ok, reason = container_build_available()
        self.container_chk.setChecked(bool(getattr(self.state, "use_container_build", False)) and ok)
        self.container_chk.setEnabled(ok)
        self.container_chk.setToolTip("" if ok else reason)
        if not ok:
            self.state.use_container_build = False
        # No docker at all, or no permission to use it: the button can't fix either.
        docker_missing = (not ok) and reason.startswith("docker is not installed")
        permission_issue = "permission denied" in reason.lower()
        self.build_img_btn.setVisible(not docker_missing)
        self.build_img_btn.setEnabled(not ok and not permission_issue)
        if ok:
            self.build_img_btn.setToolTip("Image already built.")
        elif permission_issue:
            self.build_img_btn.setToolTip(reason)
        else:
            self.build_img_btn.setToolTip("")
    def _build_container_image(self) -> None:
        dlg = LiveLogDialog(self)
        dlg.setWindowTitle("Building Docker Image")
        dlg.setWindowModality(Qt.WindowModal)
        dlg.show()

        self._img_build_worker = ContainerImageBuildWorker(cwd=os.getcwd())
        self._img_build_worker.chunk.connect(dlg.append_text)

        def _on_done(ok: bool):
            dlg.append_text.emit(
                "\n[INFO] Image build succeeded.\n" if ok else
                "\n[ERROR] Image build failed — see output above.\n"
            )
            self._refresh_container_availability()
            if ok:
                self.state.use_container_build = True
                self.container_chk.setChecked(True)
            dlg.raise_()
            dlg.activateWindow()
        self._img_build_worker.finished_ok.connect(_on_done)
        self._img_build_worker.start()
    def _write(self) -> None:
        if callable(self.on_write_image):
            self.on_write_image()

# ---------- main window + bootstrap ----------

class MainWindow(QMainWindow):
    def __init__(self, initial_options: dict):
        super().__init__()
        self.setWindowIcon(QIcon("img/dtails.png"))
        self.setWindowTitle("DTails v2.0")
        self.setFixedSize(760, 360)
        self.state = AppState(options_json=initial_options or {})
        apply_theme(QApplication.instance(), self.state.dark_mode)
        central = QWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setContentsMargins(12, 8, 12, 8)
        root.setSpacing(8)

        self.tabs = NoSwitchTabWidget()
        self.tabs.tabBar().setVisible(False)
        root.addWidget(self.tabs)

        self.start_tab = StartTab(state=self.state)
        self.install_tab = InstallTab(state=self.state, go_back=lambda: self.tabs.setCurrentIndex(0), go_next=self._to_remove)
        self.remove_tab = RemoveTab(state=self.state, go_back=lambda: self.tabs.setCurrentIndex(1), go_next=self._to_summary)
        self.summary_tab = SummaryTab(state=self.state, go_back=lambda: self.tabs.setCurrentIndex(2), on_write_image=self._on_write_image)

        self.tabs.addTab(self.start_tab, "Start")
        self.tabs.addTab(self.install_tab, "Install Software")
        self.tabs.addTab(self.remove_tab, "Remove Software")
        self.tabs.addTab(self.summary_tab, "Summary")

        self._create_menu()

        self.remove_tab.populate_from_options()
        self.summary_tab.refresh()

    def _create_menu(self):
        m = self.menuBar()
        file_menu = m.addMenu("&File")
        theme_menu = file_menu.addMenu("&Theme")
        light = QAction("&Light", self)
        light.triggered.connect(lambda: self._set_theme(False))
        dark = QAction("&Dark", self)
        dark.triggered.connect(lambda: self._set_theme(True))
        theme_menu.addActions([light, dark])
        file_menu.addSeparator()
        see_report_action = QAction("&See report", self)
        see_report_action.triggered.connect(self._open_log_file)
        file_menu.addAction(see_report_action)
        clean_all = QAction("&Clean all", self)
        clean_all.triggered.connect(self._run_clean_all)
        file_menu.addAction(clean_all)
        exit_action = QAction("&Exit", self)
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

        tools_menu = m.addMenu("&Tools")
        cmp_action = QAction("&Compare Images", self)
        cmp_action.triggered.connect(lambda: ImageCompareDialog(self).exec_())
        tools_menu.addAction(cmp_action)

        flash_dd_action = QAction("&Flash image", self)
        flash_dd_action.triggered.connect(self._flash_image_dd)
        tools_menu.addAction(flash_dd_action)


        help_menu = m.addMenu("&Help")
        submit_bug_action = QAction("&Submit Bug", self)
        submit_bug_action.triggered.connect(lambda: open_url_safely("https://github.com/DesobedienteTecnologico/dtails/issues"))
        help_menu.addAction(submit_bug_action)

        help_menu.addAction(submit_bug_action)
        donate_action = QAction("&V4V", self)
        donate_action.triggered.connect(lambda: open_url_safely("http://btcpay.desobedientetecnologico.com/"))

        help_menu.addAction(donate_action)
        about_action = QAction("&About", self)
        about_action.triggered.connect(lambda: show_about(self))
        help_menu.addAction(about_action)

    def _set_theme(self, dark):
        self.state.dark_mode = bool(dark)
        apply_theme(QApplication.instance(), self.state.dark_mode)

    def _open_log_file(self):
        """Open log.txt from the app’s current directory."""
        log_path = os.path.join(os.getcwd(), "log.txt")
        if not os.path.isfile(log_path):
            QMessageBox.warning(self, "Log not found", f"You have to create a custom image first")
            return
        QDesktopServices.openUrl(QUrl.fromLocalFile(log_path))

    def _flash_image_dd(self):
        """
        Flash the currently selected image to the selected device using dd,
        with a simple progress bar based on dd's status=progress output.
        """
        img = self.state.selected_image
        dev_info = self.state.selected_device or {}
        dev_path = dev_info.get("path")

        if not img:
            QMessageBox.warning(self, "Flash image", "Please select an image first in the Start tab.")
            return
        if not dev_path:
            QMessageBox.warning(self, "Flash image", "Please select a target device first in the Start tab.")
            return

        vendor = dev_info.get("vendor") or ""
        model = dev_info.get("model") or dev_info.get("name", "")
        size = dev_info.get("size") or ""
        dev_desc = " ".join(x for x in (dev_path, vendor, model, size) if x).strip()

        try:
            img_size_bytes = os.path.getsize(img)
            img_size_gib = img_size_bytes / (1024 ** 3)
            img_size_str = f"{img_size_gib:.2f} GiB"
        except Exception:
            img_size_str = "unknown size"

        confirm_text = (
            "This will overwrite the selected device with the image using dd.\n\n"
            f"Image: {img}\n"
            f"Size:  {img_size_str}\n\n"
            f"Target device: {dev_desc}\n\n"
            "ALL DATA ON THE TARGET DEVICE WILL BE LOST.\n\n"
            "Do you want to continue?\n\n"
            "Type sudo password in the terminal if requested."
        )

        if QMessageBox.question(
            self,
            "Flash image with dd – confirmation",
            confirm_text,
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        ) != QMessageBox.Yes:
            return

        self._dd_progress = QProgressDialog("Flashing image... Do NOT remove the device.",None,0,100,self,)
        self._dd_progress.setWindowTitle("Flashing image (dd)")
        self._dd_progress.setWindowModality(Qt.ApplicationModal)
        self._dd_progress.setCancelButton(None)
        self._dd_progress.setAutoClose(False)
        self._dd_progress.setAutoReset(False)
        self._dd_progress.setValue(0)

        self._dd_worker = DDFlashWorker(img, dev_path)
        self._dd_worker.progress.connect(self._dd_progress.setValue)

        def _on_finished(code: int, err: str):
            self._dd_progress.close()
            if code == 0:
                QMessageBox.information(self, "Flash image", "Image flashed successfully.")
            else:
                QMessageBox.critical(
                    self,
                    "Flash image",
                    f"Flashing failed (exit code {code}).\n{err}",
                )

        self._dd_worker.finished.connect(_on_finished)
        self._dd_worker.start()
        self._dd_progress.show()

    def _to_remove(self):
        self.tabs.setCurrentIndex(2)

    def _to_summary(self):
        self.summary_tab.refresh()
        self.tabs.setCurrentIndex(3)

    def _on_write_image(self):
        if not self.state.ready_to_write():
            QMessageBox.warning(self, "Incomplete", "Please select an image and a storage option.")
            return

        add_ct = len(self.state.selected_additions)
        del_ct = len(self.state.selected_deletions)
        summary = (
            f"This will run actions for:\n"
            f"  • Install: {add_ct} item(s)\n"
            f"  • Remove:  {del_ct} item(s)\n\nProceed?"
        )
        if QMessageBox.question(self, "Run actions", summary,
                                QMessageBox.Yes | QMessageBox.No, QMessageBox.No) != QMessageBox.Yes:
            return

        dlg = LiveLogDialog(self)
        dlg.setWindowModality(Qt.WindowModal)
        dlg.accepted.connect(self._on_log_dialog_closed)
        dlg.show()

        self._log_worker = LogWorker(self.state, self.state.selected_image, cwd=os.getcwd())
        self._log_worker.chunk.connect(dlg.append_text)
        def _on_done(code: int):
            dlg.append_text.emit(f"\n[INFO] Job finished with code {code}.\n")
            log_file = os.path.join(os.getcwd(), "log.txt")
            QMessageBox.information(dlg, "Done", f"Write job completed.\n\nLog saved to:\n{log_file}")
            if getattr(self.state, "use_container_build", False):
                reply = QMessageBox.question(
                    dlg, "Scrub the container?",
                    "Scrub the dtails-build container/image now?\n\n"
                    "Next container build will need the image rebuilt — use the "
                    "'Build Docker Image' button on the Summary screen.",
                    QMessageBox.Yes | QMessageBox.No, QMessageBox.No,
                )
                if reply == QMessageBox.Yes:
                    remove_container_build_image(sink=dlg.append_text.emit)
            dlg.raise_()
            dlg.activateWindow()
        self._log_worker.finished_code.connect(_on_done)
        self._log_worker.start()

    def _on_log_dialog_closed(self):
        self.tabs.setCurrentIndex(0)
        show_about(self)

    def _run_clean_all(self):
        cfg = self.state.options_json or {}
        payload = cfg.get("clean_system")
        if not payload:
            QMessageBox.information(self, "Clean system", "No 'clean_system' section found in options.json.")
            return
        manual_text = ""
        cmds: List[str] = []
        if isinstance(payload, list):
            cmds = [c for c in payload if isinstance(c, str) and c.strip()]
        elif isinstance(payload, dict):
            if isinstance(payload.get("message"), str):
                manual_text = payload["message"]
            if isinstance(payload.get("commands"), list):
                cmds = [c for c in payload["commands"] if isinstance(c, str) and c.strip()]
            elif isinstance(payload.get("linux"), list):
                cmds = [c for c in payload["linux"] if isinstance(c, str) and c.strip()]
        else:
            QMessageBox.warning(self, "Clean system", "'clean_system' must be a list or an object.")
            return
        if not cmds:
            QMessageBox.information(self, "Clean system", "No commands found to run.")
            return
        cmd_list = "\n".join(f"  • {c}" for c in cmds)
        note = manual_text.strip() if manual_text else "The following commands will be executed:"
        confirm_text = f"{note}\n\n{cmd_list}\n\nDo you want to proceed?\n\nType sudo password in the terminal."
        if QMessageBox.question(
            self,
            "Clean DTails old jobs – confirmation",
            confirm_text,
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        ) != QMessageBox.Yes:
            return

        project_cwd = os.path.abspath(os.getcwd())
        for cmd in cmds:
            try:
                subprocess.run(cmd, shell=True, cwd=project_cwd)
            except Exception as e:
                print(f"Error running {cmd}: {e}")

        QMessageBox.information(self, "Clean system", "System cleanup completed successfully.")

def launch_app(app: QApplication) -> None:
    opts = load_options()
    meta = (opts.get("meta") if isinstance(opts.get("meta"), dict) else {}) or {}
    saw = bool(meta.get("saw"))
    def open_main_and_mark_saw():
        opts_local = load_options() or {}
        m = (opts_local.get("meta") if isinstance(opts_local.get("meta"), dict) else {}) or {}
        m["saw"] = True
        opts_local["meta"] = m
        save_options(opts_local)
        w = MainWindow(opts_local)
        w.show()
    if not saw:
        intro = IntroDialog(on_continue=open_main_and_mark_saw)
        apply_theme(app, False)
        intro.exec_()
    else:
        w = MainWindow(opts)
        w.show()
