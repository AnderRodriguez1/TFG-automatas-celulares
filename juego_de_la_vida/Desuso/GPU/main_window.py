from PySide6 import QtWidgets, QtCore
from grid_widget import GridWidget

class MainWindow(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Juego de la Vida - GPU")

        container = QtWidgets.QWidget()

        self.setCentralWidget(container)
        self.grid_widget = GridWidget()

        self.next_button = QtWidgets.QPushButton("Siguiente Generación")
        self.next_button.clicked.connect(self.grid_widget.next_generation)

        self.timer_button = QtWidgets.QPushButton("Iniciar animación")
        self.timer_button.setCheckable(True)
        self.timer_button.clicked.connect(self.toggle_timer)

        layout = QtWidgets.QVBoxLayout(container)
        layout.addWidget(self.grid_widget)
        layout.addWidget(self.next_button)
        layout.addWidget(self.timer_button)

        self.timer = QtCore.QTimer()
        self.timer.setInterval(500)
        self.timer.timeout.connect(self.grid_widget.next_generation)

    @QtCore.Slot()
    def toggle_timer(self):
        """
        Funcion para iniciar/detener la animacion
        """
        if self.timer_button.isChecked():
            self.timer.start()
            self.timer_button.setText("Detener animación")
        else:
            self.timer.stop()
            self.timer_button.setText("Iniciar animación")