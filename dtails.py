import sys
from PyQt5.QtWidgets import QApplication
from src.ui import launch_app

def main() -> None:
    app = QApplication(sys.argv)
    launch_app(app)
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()
