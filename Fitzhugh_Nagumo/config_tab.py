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

        self.a_spinbox = QtWidgets.QDoubleSpinBox()
        self.a_spinbox.setRange(-10.0, 10.0)
        self.a_spinbox.setDecimals(6)
        self.a_spinbox.setValue(config_to_use.a)

        self.b_spinbox = QtWidgets.QDoubleSpinBox()
        self.b_spinbox.setRange(-10.0, 10.0)
        self.b_spinbox.setDecimals(6)
        self.b_spinbox.setValue(config_to_use.b)

        self.e_spinbox = QtWidgets.QDoubleSpinBox()
        self.e_spinbox.setRange(-10.0, 10.0)
        self.e_spinbox.setDecimals(6)
        self.e_spinbox.setValue(config_to_use.e)

        self.Du_spinbox = QtWidgets.QDoubleSpinBox()
        self.Du_spinbox.setRange(-10.0, 10.0)
        self.Du_spinbox.setDecimals(6)
        self.Du_spinbox.setValue(config_to_use.Du)

        self.Dv_spinbox = QtWidgets.QDoubleSpinBox()
        self.Dv_spinbox.setRange(-10.0, 10.0)
        self.Dv_spinbox.setDecimals(6)
        self.Dv_spinbox.setValue(config_to_use.Dv)

        form_layout.addRow("Alto de la red:", self.height_spinbox)
        form_layout.addRow("Ancho de la red:", self.width_spinbox)
        form_layout.addRow("Densidad inicial:", self.density_layout)
        form_layout.addRow("Velocidad inicial:", self.speed_spinbox)
        form_layout.addRow("Parámetro a:", self.a_spinbox)
        form_layout.addRow("Parámetro b:", self.b_spinbox)
        form_layout.addRow("Parámetro e:", self.e_spinbox)
        form_layout.addRow("Difusión Du:", self.Du_spinbox)
        form_layout.addRow("Difusión Dv:", self.Dv_spinbox)

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
            initial_speed=self.speed_spinbox.value(),
            a=self.a_spinbox.value(),
            b=self.b_spinbox.value(),
            e=self.e_spinbox.value(),
            Du=self.Du_spinbox.value(),
            Dv=self.Dv_spinbox.value()
        )
