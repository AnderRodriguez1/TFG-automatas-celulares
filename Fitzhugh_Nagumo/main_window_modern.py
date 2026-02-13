from PySide6 import QtWidgets, QtCore, QtGui
from grid_widget_modern import GridWidget
from config_modern import Config
from config_tab import ConfigTab

class MainWindow(QtWidgets.QMainWindow):
    def __init__(self, config: Config):
        super().__init__()
        self.setWindowTitle("Modelo de FitzHugh-Nagumo")
        self.config = config
        # Menu superior
        menu_bar = self.menuBar()
        # Opcion de configuracion
        config_menu = menu_bar.addMenu("&Configuración")
        # Accion de reconfigurar
        reconfigure_action = QtGui.QAction("Reconfigurar...", self)
        reconfigure_action.triggered.connect(self.reconfigure_simulation)
        config_menu.addAction(reconfigure_action)
        # Opcion de guardar/importar patron
        file_menu = menu_bar.addMenu("&Archivo")

        save_texture_action = QtGui.QAction("Guardar patrón...", self)
        save_texture_action.triggered.connect(self.save_texture)
        file_menu.addAction(save_texture_action)

        import_texture_action = QtGui.QAction("Importar patrón...", self)
        import_texture_action.triggered.connect(self.import_texture)
        file_menu.addAction(import_texture_action)

        simulation_menu = menu_bar.addMenu("&Simulación")

        select_simulation_action = QtGui.QAction("Seleccionar tipo de simulación...", self)
        #select_simulation_action.triggered.connect(self.select_simulation)
        simulation_menu.addAction(select_simulation_action)

        # Añadir todo a los widgets
        container = QtWidgets.QWidget()

        self.setCentralWidget(container)
        self.grid_widget = GridWidget(config=self.config)

        self.next_button = QtWidgets.QPushButton("Siguiente Generación")
        self.next_button.clicked.connect(self.grid_widget.next_generation)
        self.restart_button = QtWidgets.QPushButton("Reiniciar")
        self.restart_button.clicked.connect(self.grid_widget.restart_grid)

        self.timer_button = QtWidgets.QPushButton("Iniciar animación")
        self.timer_button.setCheckable(True)
        self.timer_button.clicked.connect(self.toggle_timer)

        self.layout = QtWidgets.QVBoxLayout(container)
        self.layout.addWidget(self.grid_widget)
        self.layout.addWidget(self.next_button)
        self.layout.addWidget(self.timer_button)
        self.layout.addWidget(self.restart_button)

        self.timer = QtCore.QTimer()
        self.timer.setInterval(1000/self.config.visual_speed) # Intervalo entre frames en ms
        self.timer.timeout.connect(self.grid_widget.next_generation)
        self.connect_signals()

    def connect_signals(self):
        """
        Conecta las señales de los widgets para poder reconfigurar la simulación
        """

        self.next_button.clicked.disconnect()
        self.restart_button.clicked.disconnect()
        self.timer_button.clicked.disconnect()
        self.timer.timeout.disconnect()

        self.next_button.clicked.connect(self.grid_widget.next_generation)
        self.restart_button.clicked.connect(self.grid_widget.restart_grid)
        self.timer_button.clicked.connect(self.toggle_timer)
        self.timer.setInterval(1000/self.config.visual_speed) # Intervalo entre frames en ms
        self.timer.timeout.connect(self.grid_widget.next_generation)

    @QtCore.Slot()
    def reconfigure_simulation(self):
        """
        Abre la ventana de configuración para reconfigurar la simulación
        """
        if self.timer.isActive():
            self.timer.stop()
            self.timer_button.setChecked(False)
            self.timer_button.setText("Iniciar animación")


        config_tab = ConfigTab(parent=self, actual_config=self.config)
        
        if config_tab.exec() == QtWidgets.QDialog.DialogCode.Accepted:
            self.config = config_tab.get_config()

            self.grid_widget._release_resources()

            self.layout.removeWidget(self.grid_widget)
            self.grid_widget.deleteLater()

            self.grid_widget = GridWidget(config=self.config)

            self.layout.insertWidget(0, self.grid_widget)

            self.connect_signals()

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

    @QtCore.Slot()
    def save_texture(self):
        """
        Abre un diálogo para guardar el patrón actual
        """

        file_path, _ = QtWidgets.QFileDialog.getSaveFileName(self, 
                        "Guardar patrón", 
                        "", 
                        "Imagen PNG (*.png);;Imagen BMP (*.bmp);;Imagen JPEG (*.jpg *.jpeg);;Todos los archivos (*)")

        if file_path:
            self.grid_widget.save_pattern(file_path)

    @QtCore.Slot()
    def import_texture(self):
        """
        Abre un diálogo para importar un patrón desde una imagen
        """

        file_path, _ = QtWidgets.QFileDialog.getOpenFileName(self, 
                        "Importar patrón", 
                        "", 
                        "Imagen PNG (*.png);;Imagen BMP (*.bmp);;Imagen JPEG (*.jpg *.jpeg);;Todos los archivos (*)")

        if file_path:
            self.grid_widget.import_pattern(file_path)