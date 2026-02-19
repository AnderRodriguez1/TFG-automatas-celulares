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

        self.a_spinbox = QtWidgets.QDoubleSpinBox()
        self.a_spinbox.setRange(-10.0, 10.0)
        self.a_spinbox.setDecimals(3)
        self.a_spinbox.setValue(config_to_use.a)

        self.b_spinbox = QtWidgets.QDoubleSpinBox()
        self.b_spinbox.setRange(-10.0, 10.0)
        self.b_spinbox.setDecimals(3)
        self.b_spinbox.setValue(config_to_use.b)

        self.e_spinbox = QtWidgets.QDoubleSpinBox()
        self.e_spinbox.setRange(-10.0, 10.0)
        self.e_spinbox.setDecimals(3)
        self.e_spinbox.setValue(config_to_use.e)

        self.Du_spinbox = QtWidgets.QDoubleSpinBox()
        self.Du_spinbox.setRange(-10.0, 10.0)
        self.Du_spinbox.setDecimals(3)
        self.Du_spinbox.setValue(config_to_use.Du)

        self.Dv_spinbox = QtWidgets.QDoubleSpinBox()
        self.Dv_spinbox.setRange(-10.0, 10.0)
        self.Dv_spinbox.setDecimals(3)
        self.Dv_spinbox.setValue(config_to_use.Dv)
        
        self.noise_spinbox = QtWidgets.QDoubleSpinBox()
        self.noise_spinbox.setRange(0.0, 1)
        self.noise_spinbox.setDecimals(5)
        self.noise_spinbox.setValue(config_to_use.noise_amplitude)

        self.dt_simulation_spinbox = QtWidgets.QDoubleSpinBox()
        self.dt_simulation_spinbox.setRange(0.0001, 10.0)
        self.dt_simulation_spinbox.setDecimals(5)
        self.dt_simulation_spinbox.setValue(config_to_use.dt_simulation)

        self.time_scale_spinbox = QtWidgets.QDoubleSpinBox()
        self.time_scale_spinbox.setRange(0.1, 1000.0)
        self.time_scale_spinbox.setDecimals(1)
        self.time_scale_spinbox.setValue(config_to_use.time_scale)
        self.time_scale_spinbox.setSuffix("x")

        self.spot_size_spinbox = QtWidgets.QSpinBox()
        self.spot_size_spinbox.setRange(1, 500)
        self.spot_size_spinbox.setValue(config_to_use.spot_size)
        self.spot_size_spinbox.setSuffix(" px")

        self.init_pattern_combobox = QtWidgets.QComboBox()
        self.init_pattern_combobox.addItem("Cuadrado", "square")
        self.init_pattern_combobox.addItem("Dos manchas", "two_spots")
        index = self.init_pattern_combobox.findData(config_to_use.initial_pattern)
        self.init_pattern_combobox.setCurrentIndex(index)

        form_layout.addRow("Alto de la red:", self.height_spinbox)
        form_layout.addRow("Ancho de la red:", self.width_spinbox)
        form_layout.addRow("Parámetro a:", self.a_spinbox)
        form_layout.addRow("Parámetro b:", self.b_spinbox)
        form_layout.addRow("Parámetro e:", self.e_spinbox)
        form_layout.addRow("Difusión Du:", self.Du_spinbox)
        form_layout.addRow("Difusión Dv:", self.Dv_spinbox)
        form_layout.addRow("Amplitud del ruido:", self.noise_spinbox)
        form_layout.addRow("Diferencial de tiempo de simulación:", self.dt_simulation_spinbox)
        form_layout.addRow("Escala de tiempo:", self.time_scale_spinbox)
        form_layout.addRow("Tamaño del patrón inicial:", self.spot_size_spinbox)
        form_layout.addRow("Patrón inicial:", self.init_pattern_combobox)

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
            a=self.a_spinbox.value(),
            b=self.b_spinbox.value(),
            e=self.e_spinbox.value(),
            Du=self.Du_spinbox.value(),
            Dv=self.Dv_spinbox.value(),
            noise_amplitude=self.noise_spinbox.value(),
            dt_simulation=self.dt_simulation_spinbox.value(),
            time_scale=self.time_scale_spinbox.value(),
            spot_size=self.spot_size_spinbox.value(),
            initial_pattern=self.init_pattern_combobox.currentData()
        )
        
