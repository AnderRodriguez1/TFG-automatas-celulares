from matplotlib.pyplot import title
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import os
import re
from PySide6 import QtWidgets
from scipy.optimize import curve_fit

def process_data():
    folder_path = QtWidgets.QFileDialog.getExistingDirectory(
        None,
        "Seleccionar carpeta con archivos CSV"
    )

    if not folder_path:
        print("No se seleccionó ninguna carpeta. Saliendo.")
        return

    data_by_size = {}
    
    for filename in os.listdir(folder_path):
        if filename.endswith('.csv'):
            file_path = os.path.join(folder_path, filename)

            match = re.search(r'refr(\d+)', filename)
            size_match = re.search(r'size(\d+)x(\d+)', filename)
            if match and size_match:
                refractory = int(match.group(1))
                width = int(size_match.group(1))
                height = int(size_match.group(2))
                size_label = f"{width}x{height}"

                try:
                    data = pd.read_csv(file_path)

                    if 'Active_cells' in data.columns:
                        active_cells = data['Active_cells'].values
                        total_cells = int(size_match.group(1)) * int(size_match.group(2))
                        active_proportion = active_cells / total_cells

                        last_hundred_steps = active_proportion[-100:]
                        average_active = np.mean(last_hundred_steps)

                        if size_label not in data_by_size:
                            data_by_size[size_label] = []
                        data_by_size[size_label].append((refractory, average_active))

                except Exception as e:
                    print(f"Error al procesar el archivo {filename}: {e}")
            
    for size_label in data_by_size:
        data_by_size[size_label].sort(key=lambda x: x[0])
                        
    return data_by_size

def plot_data_average(fit_bool=False):
    data_by_size = process_data()

    if not data_by_size:
        print("No se encontraron datos para graficar.")
        return

    
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(11.69, 8.27))

    sorted_sizes = sorted(data_by_size.keys(), key=lambda x: int(x.split('x')[0]))
    critical_periods = {}

    for size_label in sorted_sizes:
        data = data_by_size[size_label]
        periods, averages = zip(*data)
        size = int(size_label.split('x')[0])
        index = size / 100 - 1
        ax1.plot(periods, np.array(averages)+0.1*index, marker='o', linestyle='-', label=f'Tamaño {size_label}')
        
        for idx, avg in enumerate(averages):
            if avg == 0:
                if np.sum(averages[idx:]) == 0:
                    critical_periods[size_label] = periods[idx]
                    break
        


        if fit_bool:
            try:
                non_zero_averages = [avg for avg in averages if avg > 0]
                non_zero_periods = [periods[i] for i in range(len(averages)) if averages[i] > 0]

                fit_params = curve_fit(curve_fit_function, non_zero_periods, non_zero_averages)
                fit_curve = curve_fit_function(np.array(periods), *fit_params[0])
                print(f"Parámetros de ajuste: a={fit_params[0][0]}, b={fit_params[0][1]}")
                plt.plot(periods, fit_curve, linestyle='--', color='red', label='Ajuste de curva')
            except Exception as e:
                print(f"Error al ajustar la curva para el tamaño {size_label}: {e}")

    ax2.plot(critical_periods.values(), marker='o', linestyle='-', color='purple')
    fig.suptitle('Proporción promedio de células activas en función del período refractario', fontsize=14, fontweight='bold')
    ax1.set_xlabel('Período refractario')
    ax1.set_ylabel('Proporción promedio de células activas (últimos 100 pasos)')
    ax1.grid(True)
    ax1.legend(title='Tamaños de grid')
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
        print(f"refractory_proportion[-1]: {refractory_proportion[-1]}")
        print(f"inactive_proportion[-1]: {inactive_proportion[-1]}")
        print(f"active_proportion[-1]: {active_proportion[-1]}")
        print(f"shannon_entropy[-1]: {shannon_entropy[-1]}")
        plt.show()

def curve_fit_function(x, a, b):
    return (a / x) + b

def main():
    app = QtWidgets.QApplication([])
    plot_data_average()
    #plot_data_replicate()

if __name__=="__main__":
    main()