import sys, os
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QLabel, QPushButton, QHBoxLayout, QTabWidget, QSizePolicy, QAction,
    QFileDialog)
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

        self.button1 = QPushButton("Select Image")
        self.button1.setStyleSheet(self.button_style)
        self.button1.clicked.connect(self.select_image_file)

        self.button2 = QPushButton("Select Storage")
        self.button2.setStyleSheet(self.button_style)
        self.button2.setEnabled(False)

        self.button3 = QPushButton("Add / Remove Sofware")
        self.button3.setStyleSheet(self.button_style)
        self.button3.setEnabled(False)


        size_policy = QSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.button1.setSizePolicy(size_policy)
        self.button2.setSizePolicy(size_policy)
        self.button3.setSizePolicy(size_policy)

        left_v = QVBoxLayout()
        left_label = QLabel("Image to modify")
        left_label.setAlignment(Qt.AlignCenter)
        left_label.setWordWrap(True)
        left_label.setStyleSheet("font-size:12px;")
        left_v.setSpacing(4)
        left_v.addWidget(left_label)
        left_v.addWidget(self.button1)
        left_v.setEnabled(False)

        middle_v = QVBoxLayout()
        middle_label = QLabel("Storage")
        middle_label.setAlignment(Qt.AlignCenter)
        middle_label.setWordWrap(True)
        middle_label.setStyleSheet("font-size:12px;")
        middle_v.setSpacing(4)
        middle_v.addWidget(middle_label)
        middle_v.addWidget(self.button2)

        right_v = QVBoxLayout()
        right_label = QLabel("Manage Software")
        right_label.setAlignment(Qt.AlignCenter)
        right_label.setWordWrap(True)
        right_label.setStyleSheet("font-size:12px;")
        right_v.setSpacing(4)
        right_v.addWidget(right_label)
        right_v.addWidget(self.button3)

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


    def select_image_file(self):
        options = QFileDialog.Options()
        options |= QFileDialog.ReadOnly
        file_filter = "Image Files (*.iso *.img);;All Files (*)"
        file_path, _ = QFileDialog.getOpenFileName(self, "Select Image File", "", file_filter, options=options)
        if file_path:
            self.selected_image = file_path
            self.button1.setText(os.path.basename(file_path))
            self.button2.setEnabled(True)

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

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = TabbedApp()
    window.show()
    sys.exit(app.exec_())
