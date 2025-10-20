import sys
from PySide6 import QtWidgets
from main_window_modern import MainWindow

if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)

    window = MainWindow()
    window.resize(1200, 800)
    window.show()

    sys.exit(app.exec())