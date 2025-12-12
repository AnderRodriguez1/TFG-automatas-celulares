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

        self.density_spinbox = QtWidgets.QSpinBox()
        self.density_spinbox.setRange(0, 100)
        self.density_spinbox.setValue(config_to_use.density * 100)
        self.density_label = QtWidgets.QLabel(f"{self.density_spinbox.value()}%")
        self.density_spinbox.valueChanged.connect(lambda val: self.density_label.setText(f"{val}%"))
        self.density_layout = QtWidgets.QHBoxLayout()
        self.density_layout.addWidget(self.density_spinbox)
        self.density_layout.addWidget(self.density_label)

        self.speed_spinbox = QtWidgets.QSpinBox()
        self.speed_spinbox.setRange(1, 60)
        self.speed_spinbox.setValue(config_to_use.speed)
        self.speed_spinbox.setSuffix(" Generaciones/segundo")

        self.survive_spinbox = QtWidgets.QSpinBox()
        self.survive_spinbox.setRange(0, 8)
        self.survive_spinbox.setValue(config_to_use.survive)

        self.birth_spinbox = QtWidgets.QSpinBox()
        self.birth_spinbox.setRange(0, 8)
        self.birth_spinbox.setValue(config_to_use.birth)

        self.save_csv_checkbox = QtWidgets.QCheckBox()
        self.save_csv_checkbox.setChecked(config_to_use.save_csv)

        form_layout.addRow("Alto de la red:", self.height_spinbox)
        form_layout.addRow("Ancho de la red:", self.width_spinbox)
        form_layout.addRow("Densidad inicial:", self.density_layout)
        form_layout.addRow("Velocidad inicial:", self.speed_spinbox)
        form_layout.addRow("Vecinos vivos para sobrevivir:", self.survive_spinbox)
        form_layout.addRow("Vecinos vivos para nacer:", self.birth_spinbox)
        form_layout.addRow("Guardar datos en CSV:", self.save_csv_checkbox)


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
            grid_width = self.width_spinbox.value(),
            grid_height = self.height_spinbox.value(),
            initial_density = self.density_spinbox.value() / 100,
            initial_speed = self.speed_spinbox.value(),
            survive = self.survive_spinbox.value(),
            birth = self.birth_spinbox.value()
        )
