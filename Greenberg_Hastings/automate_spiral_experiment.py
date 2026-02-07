from numpy._core.numeric import full
import sys
import os
import time
import tqdm
from PySide6 import QtWidgets
import numpy as np

from config_modern import Config
from grid_widget_modern import GridWidget

NUM_STEPS = 2000

INITIAL_DENSITY = 0.15

REFRACTORY_PERIODS = np.linspace(1, 100, 100, dtype=int)
GRID_SIZES = np.linspace(100, 2000, 20, dtype=int)

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

    total_experiments = len(REFRACTORY_PERIODS) * len(GRID_SIZES)
    # Barra de progreso
    pbar = tqdm.tqdm(total=total_experiments, desc="Experimentos completados")

    for grid_size in GRID_SIZES:
        # Configuracion inicial, solo importa el tamaño del grid y la velocidad, 
        # el resto es irrelevante porque se va a cambiar dentro del bucle
        config = Config(grid_width=grid_size, grid_height=grid_size, initial_speed=1000, init_pattern='Aleatorio',
                        initial_density=INITIAL_DENSITY, refractory_period=REFRACTORY_PERIODS[0],threshold=1,
                        neighborhood='Von Neumann')

        widget = GridWidget(config=config)
        widget.show()
        app.processEvents()
        time.sleep(0.1)
        app.processEvents()
        widget.hide()  # Ocultar la ventana ya que no es necesaria

        for refractory_period in REFRACTORY_PERIODS:
                    
            # Generar el nombre del archivo basado en los parametros
            density_percent = int(INITIAL_DENSITY * 100)
            
            # Hay que cambiar los parametros del widget directamente
            # Se cambia en ambos sitios, en las variables y en la config interna
            widget.config.density = INITIAL_DENSITY
            widget.config.refractory_period = refractory_period
            widget.init_csv_buffer()
            filename = f"GH_size{config.grid_width}x{config.grid_height}_density{density_percent}_refr{refractory_period}.csv"
            full_path = os.path.join(save_directory, filename)
            widget._init_random_pattern()

            for step in range(NUM_STEPS):
                widget.run_neuron_shader()
                widget.capture_step_data(step_index=step)
                if (step + 1) % 100 == 0:
                    app.processEvents() # Procesar eventos cada 100 pasos para evitar que la app se congele
            
            widget.flush_csv_buffer(full_path)  # Escribir los datos almacenados en el buffer al archivo CSV
            pbar.update(1)
        widget.release_resources()
        widget.deleteLater()  # Asegurarse de que el widget se elimine correctamente
    pbar.close()
    print("Todos los experimentos han sido completados.")
    app.quit()

if __name__ == "__main__":
    run_batch_simulation()