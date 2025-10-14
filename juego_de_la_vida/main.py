import sys
import random
from PySide6 import QtWidgets, QtCore, QtGui
import numpy as np

GRID_WIDTH = 50
GRID_HEIGHT = 50
BASE_CELL_SIZE = 15
#TODO: hacer que quizas se use la gpu para renderizar?
class GridWidget(QtWidgets.QWidget):
    def __init__(self):
        super().__init__()

        self.grid_state = None
        self.init_grid()

        self.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)

        self.zoom_level = 1.0
        self.view_offset_x = 0.0
        self.view_offset_y = 0.0

        self.panning = False
        self.last_pan_pos = QtCore.QPoint()

        self._initial_fit_done = False

    def init_grid(self):
        """
        Inicializa las cuadriculas en un estado aleatorio
        """

        self.grid_state = np.random.choice([0, 1], size=(GRID_HEIGHT, GRID_WIDTH))

    def resizeEvent(self, event):
        """
        LLamado cuando se cambia el tamaño
        """

        if not self._initial_fit_done and self.width() > 1 and self.height() > 1:
            self.fit_grid_to_window()
            self._initial_fit_done = True
        
        super().resizeEvent(event)

    def fit_grid_to_window(self):
        """
        Ajusta el zoom y el offset para que la cuadricula se vea completa en la ventana
        """

        if GRID_WIDTH == 0 or GRID_HEIGHT == 0:
            return
        
        world_width = GRID_WIDTH * BASE_CELL_SIZE
        world_height = GRID_HEIGHT * BASE_CELL_SIZE

        zoom_x = self.width() / world_width
        zoom_y = self.height() / world_height

        self.zoom_level = min(zoom_x, zoom_y)

        new_grid_pixel_width = world_width * self.zoom_level
        new_grid_pixel_height = world_height * self.zoom_level

        cell_size = BASE_CELL_SIZE * self.zoom_level

        offset_pixels_x = (self.width() - new_grid_pixel_width) / 2
        offset_pixels_y = (self.height() - new_grid_pixel_height) / 2

        self.view_offset_x = -offset_pixels_x / cell_size
        self.view_offset_y = -offset_pixels_y / cell_size

        self.update()

    def wheelEvent(self, event):
        """
        Zoom con la rueda del raton
        """

        delta = event.angleDelta().y()

        mouse_pos = event.position()
        grid_pos_before_zoom = self._pixel_to_grid(mouse_pos)

        if delta > 0:
            self.zoom_level *= 1.05
        else:
            self.zoom_level /= 1.05

        self.zoom_level = max(0.1, min(self.zoom_level, 10.0))

        grid_pos_after_zoom = self._pixel_to_grid(mouse_pos)
        self.view_offset_x += grid_pos_before_zoom.x() - grid_pos_after_zoom.x() 
        self.view_offset_y += grid_pos_before_zoom.y() - grid_pos_after_zoom.y()

        self.update()

    def mousePressEvent(self, event):
        if event.button() == QtCore.Qt.LeftButton:
            grid_pos = self._pixel_to_grid(event.position())
            grid_x = int(grid_pos.x())
            grid_y = int(grid_pos.y())

            if 0 <= grid_x < GRID_WIDTH and 0 <= grid_y < GRID_HEIGHT:
                self.grid_state[grid_y, grid_x] = 1 - self.grid_state[grid_y, grid_x]
                self.update()
                event.accept()
        elif event.button() == QtCore.Qt.MiddleButton or event.button() == QtCore.Qt.RightButton:
            self.panning = True
            self.last_pan_pos = event.position()
            self.setCursor(QtCore.Qt.ClosedHandCursor)
            event.accept()

    def mouseMoveEvent(self, event):
        if self.panning:
            delta = event.position() - self.last_pan_pos
            self.last_pan_pos = event.position()

            cell_size = BASE_CELL_SIZE * self.zoom_level

            self.view_offset_x -= delta.x() / cell_size
            self.view_offset_y -= delta.y() / cell_size
            self.update()

    def mouseReleaseEvent(self, event):
        if event.button() == QtCore.Qt.MiddleButton or event.button() == QtCore.Qt.RightButton:
            self.panning = False
            self.setCursor(QtCore.Qt.ArrowCursor)
    
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
        painter.fillRect(self.rect(), QtGui.QColor('black'))

        cell_size = BASE_CELL_SIZE * self.zoom_level

        start_x = max(0, int(self.view_offset_x))
        start_y = max(0, int(self.view_offset_y))
        end_x = min(GRID_WIDTH, int(self.view_offset_x + self.width() / cell_size) + 1)
        end_y = min(GRID_HEIGHT, int(self.view_offset_y + self.height() / cell_size) + 1)

        
        for y in range(start_y, end_y):
            for x in range(start_x, end_x):
                
                screen_x = (x - self.view_offset_x) * cell_size
                screen_y = (y - self.view_offset_y) * cell_size

                if self.grid_state[y][x] == 1:
                    #celula viva
                    brush = QtGui.QColor('white')
                else:
                    #celula muerta
                    brush = QtGui.QColor('black')
                painter.setBrush(brush)
                
                if self.zoom_level >= 0.6:
                    painter.setPen(QtGui.QColor('#333333'))
                else:
                    painter.setPen(QtCore.Qt.NoPen)

                painter.drawRect(QtCore.QRectF(screen_x, screen_y, cell_size, cell_size))

    def _pixel_to_grid(self, pos):
        """
        Convierte una posicion en pixeles a coordenadas de la cuadricula
        """

        cell_size = BASE_CELL_SIZE * self.zoom_level

        grid_x = self.view_offset_x + pos.x() / cell_size
        grid_y = self.view_offset_y + pos.y() / cell_size

        return QtCore.QPointF(grid_x, grid_y)
                
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

