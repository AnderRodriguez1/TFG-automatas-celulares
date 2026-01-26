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

        self.init_pattern_combo = QtWidgets.QComboBox()
        self.init_pattern_combo.addItems(['Aleatorio', 'Patrón GH'])
        index = self.init_pattern_combo.findText(config_to_use.init_pattern)
        if index >= 0:
            self.init_pattern_combo.setCurrentIndex(index)

        self.init_pattern_combo.currentTextChanged.connect(self.toggle_density_visibility)

        self.density_container = QtWidgets.QWidget()
        density_layout = QtWidgets.QHBoxLayout(self.density_container)
        density_layout.setContentsMargins(0, 0, 0, 0)

        self.density_slider = QtWidgets.QSlider(QtCore.Qt.Orientation.Horizontal)
        self.density_slider.setRange(0, 100)
        self.density_slider.setValue(config_to_use.density * 100)

        self.density_label = QtWidgets.QLabel(f"{self.density_slider.value()}%")
        self.density_slider.valueChanged.connect(lambda val: self.density_label.setText(f"{val}%"))
        self.density_title_label = QtWidgets.QLabel("Densidad inicial:")

        self.speed_spinbox = QtWidgets.QSpinBox()
        self.speed_spinbox.setRange(1, 60)
        self.speed_spinbox.setValue(config_to_use.speed)
        self.speed_spinbox.setSuffix(" Generaciones/segundo")

        self.threshold_spinbox = QtWidgets.QSpinBox()
        self.threshold_spinbox.setRange(1, 8)
        self.threshold_spinbox.setValue(config_to_use.threshold)
        self.threshold_spinbox.setSuffix(" Vecinos")
        self.threshold_title_label = QtWidgets.QLabel("Umbral de excitación:")

        self.refractory_period_spinbox = QtWidgets.QSpinBox()
        self.refractory_period_spinbox.setRange(1, 100)
        self.refractory_period_spinbox.setValue(config_to_use.refractory_period)
        self.refractory_period_spinbox.setSuffix(" Iteraciones")
        self.refractory_period_title_label = QtWidgets.QLabel("Periodo refractario:")

        self.neighborhood_combo = QtWidgets.QComboBox()
        self.neighborhood_combo.addItems(['Moore (8)', 'Von Neumann (4)'])
        self.neighborhood_combo.setCurrentText(config_to_use.neighborhood)

        form_layout.addRow("Alto de la red:", self.height_spinbox)
        form_layout.addRow("Ancho de la red:", self.width_spinbox)
        form_layout.addRow("Patrón inicial:", self.init_pattern_combo)
        form_layout.addRow(self.density_title_label, self.density_container)
        density_layout.addWidget(self.density_slider)
        density_layout.addWidget(self.density_label)
        form_layout.addRow("Velocidad inicial:", self.speed_spinbox)
        form_layout.addRow(self.threshold_title_label, self.threshold_spinbox)
        form_layout.addRow(self.refractory_period_title_label, self.refractory_period_spinbox)
        form_layout.addRow("Vecindario:", self.neighborhood_combo)
        layout.addLayout(form_layout)

        button_box = QtWidgets.QDialogButtonBox(QtWidgets.QDialogButtonBox.StandardButton.Ok | QtWidgets.QDialogButtonBox.StandardButton.Cancel)
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)

        self.toggle_density_visibility(self.init_pattern_combo.currentText())

    def toggle_density_visibility(self, text):
        """
        Muestra u oculta el control de densidad segun el patron inicial seleccionado
        """
        if text == 'Aleatorio':
            self.density_container.show()
            self.density_title_label.show()
        else:
            self.density_container.hide()
            self.density_title_label.hide()

    def get_config(self):
        """
        Devuelve la configuración seleccionada por el usuario
        """

        return Config(
            grid_width=self.width_spinbox.value(),
            grid_height=self.height_spinbox.value(),
            initial_density=self.density_slider.value() / 100,
            initial_speed=self.speed_spinbox.value(),
            init_pattern=self.init_pattern_combo.currentText(), 
            refractory_period=self.refractory_period_spinbox.value(),
            threshold=self.threshold_spinbox.value(),
            neighborhood=self.neighborhood_combo.currentText()
        )