import sys, os, subprocess
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QLabel, QPushButton, QHBoxLayout, QTabWidget, QSizePolicy, QAction,
    QFileDialog, QDialog, QListWidget, QListWidgetItem)
from PyQt5.QtGui import QPixmap
from PyQt5.QtCore import Qt, QStorageInfo

class TabbedApp(QMainWindow):

    button_style = """
    QPushButton {
        background-color: #4CAF50;  /* Green background */
        color: white;                /* White text */
        border: none;                /* No border */
        padding: 10px;              /* Padding around text */
        border-radius: 5px;         /* Rounded corners */
        font-size: 14px;            /* Font size */
    }

    QPushButton:hover {
        background-color: #45a049;   /* Darker green on hover */
    }

    QPushButton:pressed {
        background-color: #3e8e41;   /* Even darker green when pressed */
    }

    QPushButton:disabled {
        background-color: #a9a9a9;   /* Gray background for disabled state */
        color: #d3d3d3;              /* Light gray text for disabled state */
    }

    """


    def __init__(self):
        super().__init__()
        self.setWindowTitle("Dtails v2.0")
        self.setFixedSize(600, 350)

        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.layout = QVBoxLayout(self.central_widget)

        self.tabs = QTabWidget()
        self.layout.addWidget(self.tabs)

        self.create_menu()
        self.create_tabs()
        self.tabs.tabBar().setVisible(False)

    def create_tabs(self):
        tab1 = QWidget()
        tab1_layout = QVBoxLayout()
        tab1_layout.setContentsMargins(20, 0, 20, 10)

        image_label = QLabel()
        pixmap = QPixmap("img/dtails.png")
        image_label.setPixmap(pixmap)
        image_label.setScaledContents(True)
        image_label.setFixedSize(100, 100)
        image_label.setAlignment(Qt.AlignCenter)

        tab1_layout.addWidget(image_label, alignment=Qt.AlignCenter)

        button_layout = QHBoxLayout()
        button_layout.setSpacing(20) 

        self.button_select_image = QPushButton("Select Image")
        self.button_select_image.setStyleSheet(self.button_style)
        self.button_select_image.clicked.connect(self.select_image_file)

        self.button_select_storage = QPushButton("Select Storage")
        self.button_select_storage.setStyleSheet(self.button_style)
        self.button_select_storage.setEnabled(False)
        self.button_select_storage.clicked.connect(self.choose_block_device)

        self.button_select_software = QPushButton("Add / Remove Sofware")
        self.button_select_software.setStyleSheet(self.button_style)
        self.button_select_software.setEnabled(False)


        size_policy = QSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.button_select_image.setSizePolicy(size_policy)
        self.button_select_storage.setSizePolicy(size_policy)
        self.button_select_software.setSizePolicy(size_policy)

        left_v = QVBoxLayout()
        left_label = QLabel("Image to modify")
        left_label.setAlignment(Qt.AlignCenter)
        left_label.setWordWrap(True)
        left_label.setStyleSheet("font-size:12px;")
        left_v.setSpacing(4)
        left_v.addWidget(left_label)
        left_v.addWidget(self.button_select_image)
        left_v.setEnabled(False)

        middle_v = QVBoxLayout()
        middle_label = QLabel("Storage")
        middle_label.setAlignment(Qt.AlignCenter)
        middle_label.setWordWrap(True)
        middle_label.setStyleSheet("font-size:12px;")
        middle_v.setSpacing(4)
        middle_v.addWidget(middle_label)
        middle_v.addWidget(self.button_select_storage)

        right_v = QVBoxLayout()
        right_label = QLabel("Manage Software")
        right_label.setAlignment(Qt.AlignCenter)
        right_label.setWordWrap(True)
        right_label.setStyleSheet("font-size:12px;")
        right_v.setSpacing(4)
        right_v.addWidget(right_label)
        right_v.addWidget(self.button_select_software)

        button_layout.addLayout(left_v)
        button_layout.addLayout(middle_v)
        button_layout.addLayout(right_v)

        button_layout.setAlignment(Qt.AlignCenter)
        tab1_layout.addLayout(button_layout)

        self.nav_layout1 = QHBoxLayout()
        self.nav_button_to_tab2 = QPushButton("Confirm")
        self.nav_button_to_tab2.setStyleSheet(self.button_style)
        self.nav_button_to_tab2.setEnabled(False)
        self.nav_button_to_tab2.clicked.connect(lambda: self.tabs.setCurrentIndex(1))
        self.nav_layout1.addWidget(self.nav_button_to_tab2, alignment=Qt.AlignRight)
        tab1_layout.addLayout(self.nav_layout1)
        tab1.setLayout(tab1_layout)
        self.tabs.addTab(tab1, "Tab 1")


    def create_menu(self):
        menu_bar = self.menuBar()

        file_menu = menu_bar.addMenu("File")
        exit_action = QAction("Exit", self)
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

        help_menu = menu_bar.addMenu("Verify")
        verify_action = QAction("Verify", self)
        help_menu.addAction(verify_action)

        help_menu = menu_bar.addMenu("Help")
        about_action = QAction("About", self)
        help_menu.addAction(about_action)

    def select_image_file(self):
        options = QFileDialog.Options()
        options |= QFileDialog.ReadOnly
        file_filter = "Image Files (*.iso *.img);;All Files (*)"
        file_path, _ = QFileDialog.getOpenFileName(self, "Select Image File", "", file_filter, options=options)
        if file_path:
            self.selected_image = file_path
            self.button_select_image.setText(os.path.basename(file_path))
            self.button_select_storage.setEnabled(True)

    def choose_block_device(self):
        # Only run on Linux
        if os.name != 'posix' or not os.path.isdir('/sys'):
            QMessageBox.warning(self, "Unsupported OS", "Device selection is supported only on Linux.")
            return None

        dlg = QDialog(self)
        dlg.setWindowTitle("Select Storage")
        dlg.resize(520, 300)

        layout = QVBoxLayout(dlg)
        layout.addWidget(QLabel("Select a device from the list:"))

        list_widget = QListWidget()
        layout.addWidget(list_widget)

        btn_row = QHBoxLayout()
        ok_btn = QPushButton("Select")
        cancel_btn = QPushButton("Cancel")
        btn_row.addWidget(ok_btn)
        btn_row.addWidget(cancel_btn)
        layout.addLayout(btn_row)

        def _format_size(bytes_size):
            for unit in ['B','KB','MB','GB','TB','PB']:
                if bytes_size < 1000:
                    return f"{bytes_size:.1f}{unit}" if unit != 'B' else f"{int(bytes_size)}{unit}"
                bytes_size = bytes_size / 1000.0
            return f"{bytes_size:.1f}PB"

        def gather_block_devices():
            try:
                out = subprocess.check_output(
                    ['lsblk', '-o', 'NAME,TYPE,SIZE,MOUNTPOINT,RM,MODEL,VENDOR', '-P', '-b'],
                    text=True
                )
            except Exception:
                return []
            devices = []
            for line in out.splitlines():
                info = {}
                for part in line.split():
                    if '=' not in part:
                        continue
                    k, v = part.split('=', 1)
                    info[k] = v.strip('"')
                if info.get('TYPE') != 'disk':
                    continue
                name = info.get('NAME')
                path = f"/dev/{name}" if name else None
                if not path or not os.path.exists(path):
                    continue
                if name.startswith('loop'):
                    continue
                size = int(info.get('SIZE', '0'))
                model = (info.get('MODEL') or '').strip()
                vendor = (info.get('VENDOR') or '').strip()
                if not model or not vendor:
                    sys_model = ''
                    sys_vendor = ''
                    sysbase = f"/sys/block/{name}/device"
                    try:
                        if os.path.exists(os.path.join(sysbase, 'model')):
                            with open(os.path.join(sysbase, 'model'), 'r', encoding='utf-8', errors='ignore') as f:
                                sys_model = f.read().strip()
                        if os.path.exists(os.path.join(sysbase, 'vendor')):
                            with open(os.path.join(sysbase, 'vendor'), 'r', encoding='utf-8', errors='ignore') as f:
                                sys_vendor = f.read().strip()
                    except Exception:
                        pass
                    if not model:
                        model = sys_model
                    if not vendor:
                        vendor = sys_vendor

                devices.append({
                    'path': path,
                    'size': _format_size(size),
                    'removable': info.get('RM') == '1',
                    'model': model,
                    'vendor': vendor,
                    'name': name,
                })
            devices.sort(key=lambda d: (not d['removable'], d['path']))
            return devices

        def accept_selection():
            item = list_widget.currentItem()
            if not item:
                return
            dev = item.data(0x0100)
            dlg.selected = dev
            dlg.accept()

        ok_btn.clicked.connect(accept_selection)
        cancel_btn.clicked.connect(dlg.reject)

        for dev in gather_block_devices():
            vendor_part = f"{dev['vendor']} " if dev['vendor'] else ''
            model_part = f"{dev['model']}" if dev['model'] else dev['name']
            display = f"{dev['path']} — {dev['size']} — {vendor_part}{model_part} — removable: {dev['removable']}"
            item = QListWidgetItem(display)
            item.setData(0x0100, dev)  # Qt.UserRole
            list_widget.addItem(item)

        if list_widget.count():
            list_widget.setCurrentRow(0)

        if dlg.exec_() == QDialog.Accepted:
            chosen_dev = getattr(dlg, 'selected', None)
            if chosen_dev:
                self.selected_device = chosen_dev['path']
                vendor_part = f"{chosen_dev['vendor']} " if chosen_dev['vendor'] else ''
                model_part = f"{chosen_dev['model']}" if chosen_dev['model'] else chosen_dev['name']
                self.button_select_storage.setText(os.path.basename(chosen_dev['path']) + ' - ' + vendor_part + model_part)
                if getattr(self, 'selected_image', None):
                    self.button_select_software.setEnabled(True)
                return chosen_dev['path']

        return None

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = TabbedApp()
    window.show()
    sys.exit(app.exec_())
