from numpy.lib._npyio_impl import save
from PySide6 import QtWidgets, QtCore
from config_modern import Config
import os

class ConfigTab(QtWidgets.QDialog):
    """
    Clase para configurar los parámetros a traves de una pantalla previa
    """

    def __init__(self, parent=None, actual_config: Config = None):
        super().__init__(parent)

        self.setWindowTitle("Configuracion del juego de la vida")

        layout = QtWidgets.QVBoxLayout(self)
        form_layout = QtWidgets.QFormLayout()

        # Flag para que el nombre se pueda editar manualmente o se ponga automatico
        self._manual_filename_edit = False
        self._save_directory = ""

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
        self.save_csv_checkbox.toggled.connect(self.toggle_csv_selection)

        self.csv_container = QtWidgets.QWidget()
        self.csv_layout = QtWidgets.QHBoxLayout(self.csv_container)
        self.csv_layout.setContentsMargins(0, 0, 0, 0)
        self.csv_lineedit = QtWidgets.QLineEdit()
        self.csv_lineedit.setPlaceholderText("Seleccionar ruta de guardado...")

        if hasattr(config_to_use, 'csv_filename') and config_to_use.csv_filename:
            self.csv_lineedit.setText(config_to_use.csv_filename)
            self._manual_filename_edit = True
            self._current_csv_path = os.path.dirname(config_to_use.csv_filename)

        self.csv_browse_button = QtWidgets.QPushButton("Examinar")
        self.csv_browse_button.clicked.connect(self.browse_csv_file)

        self.csv_layout.addWidget(self.csv_lineedit)
        self.csv_layout.addWidget(self.csv_browse_button)

        form_layout.addRow("Alto de la red:", self.height_spinbox)
        form_layout.addRow("Ancho de la red:", self.width_spinbox)
        form_layout.addRow("Densidad inicial:", self.density_layout)
        form_layout.addRow("Velocidad inicial:", self.speed_spinbox)
        form_layout.addRow("Vecinos vivos para sobrevivir:", self.survive_spinbox)
        form_layout.addRow("Vecinos vivos para nacer:", self.birth_spinbox)
        form_layout.addRow("Guardar datos en CSV:", self.save_csv_checkbox)

        self.csv_path_label = QtWidgets.QLabel("Ruta del archivo:")
        form_layout.addRow(self.csv_path_label, self.csv_container)

        layout.addLayout(form_layout)

        button_box = QtWidgets.QDialogButtonBox(QtWidgets.QDialogButtonBox.StandardButton.Ok | QtWidgets.QDialogButtonBox.StandardButton.Cancel)
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)

        self.density_spinbox.valueChanged.connect(self.update_auto_filename)
        self.survive_spinbox.valueChanged.connect(self.update_auto_filename)
        self.birth_spinbox.valueChanged.connect(self.update_auto_filename)

        self.csv_lineedit.textEdited.connect(self.on_user_edit_filename)

        self.toggle_csv_selection(self.save_csv_checkbox.isChecked())

        if not self._manual_filename_edit:
            self.update_auto_filename()

    def update_auto_filename(self):
        """
        Genera un nombre automatico para el archivo csv basado en los parametros
        Formato: GoL_densidad{XX}_survive{Y}_birth{Z}.csv
        """

        if self._manual_filename_edit:
            return

        density = self.density_spinbox.value()
        survive = self.survive_spinbox.value()
        birth = self.birth_spinbox.value()

        filename = f"GoL_densidad{density}_survive{survive}_birth{birth}.csv"

        if self._save_directory:
            full_path = os.path.join(self._save_directory, filename)
        else:
            full_path = filename

        self.csv_lineedit.setText(full_path)

    def on_user_edit_filename(self, text):
        """
        Marca que el usuario ha editado manualmente el nombre del archivo
        """

        if not text.strip():
            self._manual_filename_edit = False
            self.update_auto_filename()
        else:
            self._manual_filename_edit = True


    def toggle_csv_selection(self, checked):
        """
        Muestra u oculta los botones para la seleccion de la ruta para guardar el csv
        """
        self.csv_container.setVisible(checked)
        self.csv_path_label.setVisible(checked)

        if checked and not self.csv_lineedit.text().strip():
            self._manual_filename_edit = False
            self.update_auto_filename()

    def browse_csv_file(self):
        """
        Abre un dialogo para seleccionar la ruta para  guardar el csv
        """
        current_path = self.csv_lineedit.text()

        if not current_path:
            self.update_auto_filename()
            current_path = self.csv_lineedit.text()

        suggestion = current_path

        if self._save_directory and not os.path.dirname(current_path):
            suggestion

        elif not os.path.dirname(current_path):
            suggestion = os.path.join(os.getcwd(), current_path)

        file_path, _ = QtWidgets.QFileDialog.getSaveFileName(
            self,
            "Guardar archivo CSV",
            suggestion,
            "Archivos CSV (*.csv);;Todos los archivos (*)"
        )

        if file_path:
            self.csv_lineedit.setText(file_path)
            self._manual_filename_edit = True
            self._save_directory = os.path.dirname(file_path)

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
            birth = self.birth_spinbox.value(),
            save_csv = self.save_csv_checkbox.isChecked(),
            csv_filename = self.csv_lineedit.text()
        )
