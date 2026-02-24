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
        self.init_pattern_combobox.addItem("Cerebro", "brain")
        index = self.init_pattern_combobox.findData(config_to_use.initial_pattern)
        self.init_pattern_combobox.setCurrentIndex(index)

        # Parametros del cerebro (materia blanca), los anteriores hacen de materia gris
        self.a_white_spinbox = QtWidgets.QDoubleSpinBox()
        self.a_white_spinbox.setRange(-10.0, 10.0)
        self.a_white_spinbox.setDecimals(3)
        self.a_white_spinbox.setValue(config_to_use.a_white)

        self.Du_white_spinbox = QtWidgets.QDoubleSpinBox()
        self.Du_white_spinbox.setRange(-10.0, 10.0)
        self.Du_white_spinbox.setDecimals(3)
        self.Du_white_spinbox.setValue(config_to_use.Du_white)

        self.black_threshold_spinbox = QtWidgets.QDoubleSpinBox()
        self.black_threshold_spinbox.setRange(0.0, 1.0)
        self.black_threshold_spinbox.setDecimals(3)
        self.black_threshold_spinbox.setSingleStep(0.01)
        self.black_threshold_spinbox.setValue(config_to_use.brain_black_threshold)

        self.white_threshold_spinbox = QtWidgets.QDoubleSpinBox()
        self.white_threshold_spinbox.setRange(0.0, 1.0)
        self.white_threshold_spinbox.setDecimals(3)
        self.white_threshold_spinbox.setSingleStep(0.01)
        self.white_threshold_spinbox.setValue(config_to_use.brain_white_threshold)

        form_layout.addRow("Alto de la red:", self.height_spinbox)
        form_layout.addRow("Ancho de la red:", self.width_spinbox)

        # Labels que cambian según el patrón
        self.a_label = QtWidgets.QLabel("Parámetro a:")
        self.Du_label = QtWidgets.QLabel("Difusión Du:")
        form_layout.addRow(self.a_label, self.a_spinbox)
        form_layout.addRow("Parámetro b:", self.b_spinbox)
        form_layout.addRow("Parámetro e:", self.e_spinbox)
        form_layout.addRow(self.Du_label, self.Du_spinbox)
        form_layout.addRow("Difusión Dv:", self.Dv_spinbox)
        form_layout.addRow("Amplitud del ruido:", self.noise_spinbox)
        form_layout.addRow("Diferencial de tiempo de simulación:", self.dt_simulation_spinbox)
        form_layout.addRow("Escala de tiempo:", self.time_scale_spinbox)
        form_layout.addRow("Tamaño del patrón inicial:", self.spot_size_spinbox)
        form_layout.addRow("Patrón inicial:", self.init_pattern_combobox)

        # Filas de cerebro (se muestran/ocultan dinámicamente)
        self.brain_separator = QtWidgets.QFrame()
        self.brain_separator.setFrameShape(QtWidgets.QFrame.HLine)
        self.brain_separator.setFrameShadow(QtWidgets.QFrame.Sunken)
        self.brain_header = QtWidgets.QLabel("<b>Parámetros cerebro (materia blanca)</b>")
        self.a_white_label = QtWidgets.QLabel("a (materia blanca):")
        self.Du_white_label = QtWidgets.QLabel("Du (materia blanca):")
        self.black_threshold_label = QtWidgets.QLabel("Umbral negro (bloqueado):")
        self.white_threshold_label = QtWidgets.QLabel("Umbral blanco (mat. blanca):")

        form_layout.addRow(self.brain_separator)
        form_layout.addRow(self.brain_header)
        form_layout.addRow(self.a_white_label, self.a_white_spinbox)
        form_layout.addRow(self.Du_white_label, self.Du_white_spinbox)
        form_layout.addRow(self.black_threshold_label, self.black_threshold_spinbox)
        form_layout.addRow(self.white_threshold_label, self.white_threshold_spinbox)

        # Conectar cambio de patrón para mostrar/ocultar filas cerebro
        self.init_pattern_combobox.currentIndexChanged.connect(self._update_brain_fields_visibility)
        self._update_brain_fields_visibility()

        layout.addLayout(form_layout)

        button_box = QtWidgets.QDialogButtonBox(QtWidgets.QDialogButtonBox.StandardButton.Ok | QtWidgets.QDialogButtonBox.StandardButton.Cancel)
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)

    def _update_brain_fields_visibility(self):
        """
        Muestra/oculta los campos de cerebro según el patrón seleccionado.
        Cuando es cerebro: a y Du se renombran como 'materia gris' y se muestran los de materia blanca.
        Cuando no es cerebro: a y Du tienen nombres normales y se ocultan los de materia blanca.
        """
        is_brain = self.init_pattern_combobox.currentData() == "brain"

        # Cambiar labels de a y Du
        if is_brain:
            self.a_label.setText("a (materia gris):")
            self.Du_label.setText("Du (materia gris):")
        else:
            self.a_label.setText("Parámetro a:")
            self.Du_label.setText("Difusión Du:")

        # Mostrar/ocultar campos de materia blanca
        brain_widgets = [
            self.brain_separator, self.brain_header,
            self.a_white_label, self.a_white_spinbox,
            self.Du_white_label, self.Du_white_spinbox,
            self.black_threshold_label, self.black_threshold_spinbox,
            self.white_threshold_label, self.white_threshold_spinbox,
        ]
        for w in brain_widgets:
            w.setVisible(is_brain)

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
            initial_pattern=self.init_pattern_combobox.currentData(),
            a_white=self.a_white_spinbox.value(),
            Du_white=self.Du_white_spinbox.value(),
            brain_black_threshold=self.black_threshold_spinbox.value(),
            brain_white_threshold=self.white_threshold_spinbox.value(),
        )
        
