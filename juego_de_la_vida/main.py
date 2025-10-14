import sys
import random
from PySide6 import QtWidgets, QtCore, QtGui

GRID_WIDTH = 40
GRID_HEIGHT = 30

class GridWidget(QtWidgets.QWidget):
    def __init__(self):
        super().__init__()

        self.grid_state = []
        self.init_grid()

        self.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)

        self.cell_size = 0
        self.offset_x = 0
        self.offset_y = 0

    def init_grid(self):
        """
        Inicializa las cuadriculas en un estado aleatorio
        """

        self.grid_state = [[random.choice([0, 1]) for _ in range(GRID_WIDTH)] for _ in range(GRID_HEIGHT)]

    def resizeEvent(self, event):
        self.recalculate_geometry()
        return super().resizeEvent(event)
    
    def recalculate_geometry(self):
        """
        Calcula los tamaños de las celdas y los margenes
        """

        cell_width = self.width() / GRID_WIDTH
        cell_height = self.height() / GRID_HEIGHT

        self.cell_size = min(cell_width, cell_height)

        grid_pixel_width = self.cell_size * GRID_WIDTH
        grid_pixel_height = self.cell_size * GRID_HEIGHT

        self.offset_x = (self.width() - grid_pixel_width) / 2
        self.offset_y = (self.height() - grid_pixel_height) / 2

    def paintEvent(self, event):
        """
        LLamado por Qt cuando es necesario repintar el widget
        """

        painter = QtGui.QPainter(self)

        if self.cell_size == 0:
            return

        
        for y in range(GRID_HEIGHT):
            for x in range(GRID_WIDTH):
                
                if self.grid_state[y][x] == 1:
                    #celula viva
                    brush = QtGui.QColor('white')
                else:
                    #celula muerta
                    brush = QtGui.QColor('black')
                painter.setBrush(brush)
                painter.setPen(QtGui.QColor('gray'))

                painter.drawRect(
                    self.offset_x + x * self.cell_size,
                    self.offset_y + y * self.cell_size,
                    self.cell_size,
                    self.cell_size
                )
    
    def mousePressEvent(self, event):
        """
        Evento de click del raton
        """
        click_x = event.position().x()
        click_y = event.position().y()

        relative_x = click_x - self.offset_x
        relative_y = click_y - self.offset_y

        grid_x = int(relative_x // self.cell_size)
        grid_y = int(relative_y // self.cell_size)

        if 0 <= grid_x < GRID_WIDTH and 0 <= grid_y < GRID_HEIGHT:
            self.grid_state[grid_y][grid_x] = 1 - self.grid_state[grid_y][grid_x]
            self.update()

    
    def next_generation(self):
        """
        Placeholder para la logica de actualizadon de la cuadricula
        """
        self.init_grid()
        self.update()

class MainWindow(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("Juego de la Vida")

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
        self.timer.setInterval(500)  # 100 ms
        self.timer.timeout.connect(self.grid_widget.next_generation)

    @QtCore.Slot()
    def toggle_timer(self):
        if self.timer_button.isChecked():
            self.timer.start()
            self.timer_button.setText("Detener animación")
        else:
            self.timer.stop()
            self.timer_button.setText("Iniciar animación")


if __name__ == "__main__":

    app = QtWidgets.QApplication(sys.argv)

    window = MainWindow()
    window.resize(800, 600)
    window.show()

    sys.exit(app.exec())

