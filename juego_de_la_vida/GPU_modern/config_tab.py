from PySide6 import QtWidgets, QtCore
from config_modern import Config

class ConfigTab(QtWidgets.QDialog):
    """
    Clase para configurar los parámetros a traves de una pantalla previa
    """

    def __init__(self, parent=None, actual_config: Config = None):
        super().__init__(parent)

        self.setWindowTitle("Configuracion del juego de la vida")

        layout = QtWidgets.QVBoxLayout(self)
        form_layout = QtWidgets.QFormLayout()

        config_to_use = actual_config if actual_config else Config()

        self.height_spinbox = QtWidgets.QSpinBox()
        self.height_spinbox.setRange(2, 1000)
        self.height_spinbox.setValue(config_to_use.grid_height)

        self.width_spinbox = QtWidgets.QSpinBox()
        self.width_spinbox.setRange(2, 1000)
        self.width_spinbox.setValue(config_to_use.grid_width)

        self.density_slider = QtWidgets.QSlider(QtCore.Qt.Orientation.Horizontal)
        self.density_slider.setRange(0, 100)
        self.density_slider.setValue(config_to_use.density * 100)
        self.density_label = QtWidgets.QLabel(f"{self.density_slider.value()}%")
        self.density_slider.valueChanged.connect(lambda val: self.density_label.setText(f"{val}%"))
        self.density_layout = QtWidgets.QHBoxLayout()
        self.density_layout.addWidget(self.density_slider)
        self.density_layout.addWidget(self.density_label)

        self.speed_spinbox = QtWidgets.QSpinBox()
        self.speed_spinbox.setRange(1, 60)
        self.speed_spinbox.setValue(config_to_use.speed)
        self.speed_spinbox.setSuffix(" Generaciones/segundo")

        form_layout.addRow("Alto de la red:", self.height_spinbox)
        form_layout.addRow("Ancho de la red:", self.width_spinbox)
        form_layout.addRow("Densidad inicial:", self.density_layout)
        form_layout.addRow("Velocidad inicial:", self.speed_spinbox)

        layout.addLayout(form_layout)

        button_box = QtWidgets.QDialogButtonBox(QtWidgets.QDialogButtonBox.StandardButton.Ok | QtWidgets.QDialogButtonBox.StandardButton.Cancel)
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)

    def get_config(self):
        """
        Devuelve la configuración seleccionada por el usuario
        """

        return Config(
            grid_width=self.width_spinbox.value(),
            grid_height=self.height_spinbox.value(),
            initial_density=self.density_slider.value() / 100,
            initial_speed=self.speed_spinbox.value()
        )
