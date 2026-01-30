import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import os
import re
from PySide6 import QtWidgets

def process_data(folder_path):

    averages_hundred_last = []
    
    for filename in os.listdir(folder_path):
        if filename.endswith('.csv'):
            file_path = os.path.join(folder_path, filename)

            match = re.search(r'refr(\d+)', filename)
            size_match = re.search(r'size(\d+)x(\d+)', filename)
            if match and size_match:
                refractory = int(match.group(1))

                try:
                    data = pd.read_csv(file_path)

                    if 'Active_cells' in data.columns:
                        active_cells = data['Active_cells'].values
                        total_cells = int(size_match.group(1)) * int(size_match.group(2))
                        active_proportion = active_cells / total_cells

                        last_hundred_steps = active_proportion[-100:]
                        average_active = np.mean(last_hundred_steps)
                        averages_hundred_last.append((refractory, average_active))
                except Exception as e:
                    print(f"Error al procesar el archivo {filename}: {e}")
            
    averages_hundred_last.sort(key=lambda x: x[0])
                        
    return averages_hundred_last

def plot_data(averages_hundred_last):
    periods, averages = zip(*averages_hundred_last)

    plt.figure(figsize=(10, 6))
    plt.plot(periods, averages, marker='o', linestyle='-')
    plt.title('Proporción promedio de células activas en función del período refractario', fontsize=14, fontweight='bold')
    plt.xlabel('Período refractario')
    plt.ylabel('Proporción promedio de células activas (últimos 100 pasos)')
    plt.grid(True)
    plt.show()

def main():
    app = QtWidgets.QApplication([])

    folder_path = QtWidgets.QFileDialog.getExistingDirectory(
        None,
        "Seleccionar carpeta con archivos CSV"
    )

    if not folder_path:
        print("No se seleccionó ninguna carpeta. Saliendo.")
        return

    averages_hundred_last = process_data(folder_path)
    plot_data(averages_hundred_last)

if __name__=="__main__":
    main()