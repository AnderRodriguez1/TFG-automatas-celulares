import sys
import os
import tqdm
from PySide6 import QtWidgets
import numpy as np

from config_modern import Config
from grid_widget_modern import GridWidget

NUM_STEPS = 1000
INITIAL_DENSITY = 0.15
REFRACTORY_PERIODS = 2

def run_batch_simulation():
    app = QtWidgets.QApplication(sys.argv)

    print("Selecciona la carpeta donde se guardarán los archivos CSV:")
    save_directory = QtWidgets.QFileDialog.getExistingDirectory(None, "Seleccionar carpeta")
    if not save_directory:
        return

    
    config = Config(
        grid_width=500, 
        grid_height=500, 
        initial_speed=1000, 
        init_pattern='Patrón GH', 
        initial_density=INITIAL_DENSITY, 
        refractory_period=REFRACTORY_PERIODS,
        threshold=1,
        neighborhood='Von Neumann'
    )

    widget = GridWidget(config=config)
    
    -
    widget.show()
    
    
    app.processEvents()
    app.processEvents()
    
    widget.hide() 
    
    widget.use_buffer_mode = True

    pbar = tqdm.tqdm(total=1, desc="Simulando")

    filename = f"GH_size{config.grid_width}x{config.grid_height}_Replicate_GH.csv"
    full_path = os.path.join(save_directory, filename)
    
    widget.config.density = INITIAL_DENSITY
    widget.config.refractory_period = REFRACTORY_PERIODS
    
    widget.init_csv_buffer()
    
    
    widget._init_replicate_pattern() 

    for step in range(NUM_STEPS):
        widget.run_neuron_shader()
        widget.capture_step_data(step_index=step)
        
        
        if (step + 1) % 100 == 0:
            app.processEvents() 
    
 
    widget.flush_csv_buffer(full_path)
    pbar.update(1)
    pbar.close()
    
    print("Experimento completado.")
    widget.release_resources()
    app.quit()

if __name__ == "__main__":
    run_batch_simulation()