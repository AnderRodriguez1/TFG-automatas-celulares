from numpy._core.numeric import full
import sys
import os
import time
import tqdm
from PySide6 import QtWidgets, QtCore
import numpy as np

from config_modern import Config
from grid_widget_modern import GridWidget

NUM_STEPS = 5000

DENSITIES = [0.05, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9]

BIRTH_RULES = np.arange(0, 9)
SURVIVE_RULES = np.arange(0, 9)

def run_batch_simulation():

    app = QtWidgets.QApplication(sys.argv)

    print("Selecciona la carpeta donde se guardarán los archivos CSV:")
    save_directory = QtWidgets.QFileDialog.getExistingDirectory(
        None,
        "Seleccionar carpeta"
    )

    if not save_directory:
        print("No se seleccionó ninguna carpeta. Saliendo.")
        return

    print(f"Guardando archivos en: {save_directory}")
    # Configuracion inicial, solo importa el tamaño del grid y la velocidad, 
    # el resto es irrelevante porque se va a cambiar dentro del bucle
    config = Config(grid_width=100, grid_height=100, initial_speed=1000,
                    initial_density=0.3, survive=2, birth=3, save_csv=True)

    widget = GridWidget(config=config)
    widget.show()
    widget.hide()  # Ocultar la ventana ya que no es necesaria
    widget.use_buffer_mode = True  # Activar el modo buffer para CSV

    total_experiments = len(DENSITIES) * len(BIRTH_RULES) * len(SURVIVE_RULES)
    # Barra de progreso, queda muy bien
    pbar = tqdm.tqdm(total=total_experiments, desc="Experimentos completados")

    for density in DENSITIES:
        for survive in SURVIVE_RULES:
            for birth in BIRTH_RULES:
                
                # Generar el nombre del archivo basado en los parametros
                density_percent = int(density * 100)
                filename = f"GoL_size{config.grid_width}x{config.grid_height}_density{density_percent}_survive{survive}_birth{birth}.csv"
                full_path = os.path.join(save_directory, filename)
                # Hay que cambiar los parametros del widget directamente
                # Se cambia en ambos sitios, en las variables y en la config interna
                widget.density = density
                widget.config.density = density

                widget.survive_rule = survive
                widget.config.survive = survive

                widget.birth_rule = birth
                widget.config.birth = birth

                widget.save_csv_bool = True
                widget.csv_filename = full_path

                if hasattr(widget, 'life_program'):
                    pass

                widget.csv_buffer.clear() # Por si acaso no se hubiera limpoado antes

                widget.restart_grid()

                for step in range(NUM_STEPS):
                    widget.run_life_shader()
                    if (step + 1) % 100 == 0:
                        app.processEvents() # Procesar eventos cada 100 pasos para evitar que la app se congele
                
                widget.flush_csv_buffer()  # Escribir los datos almacenados en el buffer al archivo CSV
                pbar.update(1)
    pbar.close()
    print("Todos los experimentos han sido completados.")

    widget.release_resources()
    app.quit()

if __name__ == "__main__":
    run_batch_simulation()