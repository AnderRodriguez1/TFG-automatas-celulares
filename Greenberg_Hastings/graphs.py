import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import os
import re
from PySide6 import QtWidgets

def process_data():
    folder_path = QtWidgets.QFileDialog.getExistingDirectory(
        None,
        "Seleccionar carpeta con archivos CSV"
    )

    if not folder_path:
        print("No se seleccionó ninguna carpeta. Saliendo.")
        return

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

def plot_data_average():
    averages_hundred_last = process_data()
    periods, averages = zip(*averages_hundred_last)

    plt.figure(figsize=(10, 6))
    plt.plot(periods, averages, marker='o', linestyle='-')
    plt.title('Proporción promedio de células activas en función del período refractario', fontsize=14, fontweight='bold')
    plt.xlabel('Período refractario')
    plt.ylabel('Proporción promedio de células activas (últimos 100 pasos)')
    plt.grid(True)
    plt.show()

def plot_data_replicate():

    csv_path = QtWidgets.QFileDialog.getOpenFileName(
        None,
        "Seleccionar archivo CSV",
        "",
        "Archivos CSV (*.csv)"
    )[0]

    data = pd.read_csv(csv_path)
    if 'Active_cells' in data.columns:
        active_cells = data['Active_cells'].values
        refractory_cells = data['Refractory_cells'].values
        inactive_cells = data['Resting_cells'].values
        total_cells = active_cells + refractory_cells + inactive_cells
        active_proportion = active_cells / total_cells
        refractory_proportion = refractory_cells / total_cells
        inactive_proportion = inactive_cells / total_cells
        steps = data['Step'].values

        shannon_entropy = -(active_proportion * np.log2(active_proportion+1e-10) +
                            refractory_proportion * np.log2(refractory_proportion+1e-10) +
                            inactive_proportion * np.log2(inactive_proportion+1e-10))

        plt.figure(figsize=(10, 6))
        plt.plot(steps, active_proportion, label='Células activas', color='blue')
        plt.plot(steps, refractory_proportion, label='Células refractarias', color='orange')
        plt.plot(steps, inactive_proportion, label='Células inactivas', color='green')
        plt.plot(steps, shannon_entropy, label='Entropía de Shannon', color='red', linestyle='--')
        plt.legend()
        plt.title('Proporción de estados celulares a lo largo del tiempo', fontsize=14, fontweight='bold')
        plt.xlabel('Paso de tiempo')
        plt.ylabel('Proporción de células')
        plt.show()

def main():
    app = QtWidgets.QApplication([])
    #plot_data_average()
    plot_data_replicate()
if __name__=="__main__":
    main()