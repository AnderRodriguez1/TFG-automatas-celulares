import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from PySide6 import QtWidgets
import os

def _select_csv_folder():
    """
    Selecciona una carpeta que contenga los CSVs generados por sweep_sigma.py
    """
    app = QtWidgets.QApplication([])
    dialog = QtWidgets.QFileDialog()
    dialog.setFileMode(QtWidgets.QFileDialog.FileMode.Directory)
    dialog.setOption(QtWidgets.QFileDialog.Option.ShowDirsOnly, True)

    if dialog.exec():
        folder_path = dialog.selectedFiles()[0]
        return folder_path
    else:
        return None

def load_csv_data():
    """
    Carga los datos de los CSVs y devuelve un dataframe
    Args:
        folder_path: Ruta de la carpeta que contiene los CSVs
    Returns:
        DataFrame con columnas: ['sigma', 'total_runs', 'success_runs', 'success_rate']
    """
    folder_path = _select_csv_folder()
    all_data = []
    
    for file_name in os.listdir(folder_path):
        if file_name.endswith('.csv'):
            with open(os.path.join(folder_path, file_name), 'r') as f:
                reader = pd.read_csv(f)
                sigma_value = float(file_name.split('_')[1])
                total_runs = len(reader)
                success_runs = reader['success'].sum()  
                success_rate = success_runs / total_runs if total_runs > 0 else 0
                all_data.append({'sigma': sigma_value, 'total_runs': total_runs, 'success_runs': success_runs, 'success_rate': success_rate})

    df = pd.DataFrame(all_data)
    return df.sort_values(by='sigma')

def plot_success_rate():
    """
    Carga los datos de los CSVs y grafica la tasa de éxito en función de sigma
    """
    df = load_csv_data()
    plt.figure(figsize=(10, 6))
    plt.plot(df['sigma'], df['success_rate'], marker='o')
    plt.title('Tasa de Éxito vs Amplitud del Ruido (Sigma)')
    plt.xlabel('Amplitud del Ruido (Sigma)')
    plt.ylabel('Tasa de Éxito')
    plt.grid()
    plt.show()

def main():
    df = plot_success_rate()
    print(df)

if __name__ == "__main__":
    main()
            
