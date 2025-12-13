import pandas as pd
import re
from PySide6 import QtWidgets
import sys
import os
import numpy as np
from mpl_toolkits.mplot3d import Axes3D
import matplotlib.pyplot as plt

def generate_3d_plot():
    app = QtWidgets.QApplication([])

    folder_path = QtWidgets.QFileDialog.getExistingDirectory(
        None,
        "Seleccionar carpeta con archivos CSV"
    )

    if not folder_path:
        print("No se seleccionó ninguna carpeta. Saliendo.")
        return
    
    density_value = 0.3
    density_str = str(int(density_value * 100))
    survive_range = np.arange(9)
    birth_range = np.arange(9)

    entropy_matrix = np.zeros((len(survive_range), len(birth_range)))

    print("Procesando archivos con una densidad de:", density_value)

    for birth in birth_range:
        for survive in survive_range:

            pattern_str = rf"GoL_size\d+x\d+_density{density_str}_survive{survive}_birth{birth}\.csv$"
            pattern = re.compile(pattern_str)

            matched_file = None

            for filename in os.listdir(folder_path):
                if pattern.match(filename):
                    matched_file = os.path.join(folder_path, filename)
                    break

            if matched_file is not None:
                try:
                    df = pd.read_csv(matched_file)

                    number_of_average_rows = min(100, len(df))
                    last_rows = df.tail(number_of_average_rows)

                    total_cells = df.iloc[0]['Width'] * df.iloc[0]['Height']

                    entropy_vector = last_rows['Live Cells'].apply(
                        lambda x: calculate_shannon_entropy(x, total_cells)
                    )
                    
                    average_entropy = np.mean(entropy_vector)
                    entropy_matrix[survive, birth] = average_entropy

                except Exception as e:
                    print(f"Error al procesar {matched_file}: {e}")
                    entropy_matrix[survive, birth] = 0.0
            else:
                print(f"No se encontró archivo para survive={survive}, birth={birth}")
                entropy_matrix[survive, birth] = 0.0

    fig = plt.figure(figsize=(11.69, 8.27))
    ax = fig.add_subplot(111, projection='3d')

    X, Y = np.meshgrid(birth_range, survive_range)
    Z = entropy_matrix

    surf = ax.plot_surface(X, Y, Z, cmap='viridis')

    ax.set_xlabel('Regla de nacimiento')
    ax.set_ylabel('Regla de supervivencia')
    ax.set_zlabel('Entropía de Shannon')
    ax.set_title(f'Entropía de Shannon para la densidad inicial $\\rho = {density_value}$')

    fig.colorbar(surf, shrink=0.5, aspect=10)

    ax.scatter([3], [2], [entropy_matrix[2, 3]+0.01], color='r', s=50, label='Regla Clásica (B3/S2)')
    ax.plot([3, 3], [2, 2], [entropy_matrix[2, 3], 1], color='red', linewidth=1, zorder=1000)

    plt.legend()
    plt.show()

def calculate_shannon_entropy(live_cells, total_cells):
    """
    Calcula la entropía de Shannon dada la cantidad de células vivas y el total de células
    """

    if total_cells == 0:
        return 0.0

    p_live = live_cells / total_cells
    p_dead = 1 - p_live

    if p_live <= 0 or p_dead <= 0:
        return 0.0

    shannon_entropy = - (p_live * np.log2(p_live) + p_dead * np.log2(p_dead))
    return shannon_entropy

if __name__ == "__main__":

    generate_3d_plot()