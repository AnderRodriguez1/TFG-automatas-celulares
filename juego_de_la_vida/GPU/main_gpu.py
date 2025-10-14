import sys
from PySide6 import QtWidgets
# Importamos la clase de la ventana principal
from main_window import MainWindow

if __name__ == "__main__":
    # El bloque estándar para iniciar una aplicación Qt
    app = QtWidgets.QApplication(sys.argv)

    window = MainWindow()
    window.resize(800, 600)
    window.show()

    sys.exit(app.exec())