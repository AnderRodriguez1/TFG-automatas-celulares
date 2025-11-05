"""
Simulación de autómatas celulares usando el modelo de Greenberg-Hastings.
· Controles:
    - Click izquierdo: activar o desactivar células
    - Click derecho y arrastrar: mover la vista
    - Pulsar la rueda del raton: bloquear/desbloquear un autómata (muro)
    - Rueda del ratón: hacer zoom in/out
"""

import sys
from PySide6 import QtWidgets
from main_window_modern import MainWindow
from config_tab import ConfigTab

if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)

    config_tab = ConfigTab()

    if config_tab.exec() == QtWidgets.QDialog.DialogCode.Accepted:
        config = config_tab.get_config()

        window = MainWindow(config=config)
        window.resize(1200, 800)
        window.show()

        sys.exit(app.exec())