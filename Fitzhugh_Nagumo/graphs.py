import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import re
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
    if folder_path is None:
        return pd.DataFrame(columns=['sigma', 'total_runs', 'success_runs', 'success_rate'])

    # Look for subfolders named like CSVs_FHN_\d+
    subdirs = []
    for name in os.listdir(folder_path):
        path = os.path.join(folder_path, name)
        if os.path.isdir(path) and re.match(r'^CSVs_FHN_\d+$', name):
            subdirs.append(path)

    # If no matching subdirs, consider the selected folder itself
    if not subdirs:
        subdirs = [folder_path]

    # Aggregate results per sigma across all matching subfolders
    agg = {}
    for sub in subdirs:
        for file_name in sorted(os.listdir(sub)):
            if not file_name.endswith('.csv'):
                continue
            file_path = os.path.join(sub, file_name)
            try:
                df = pd.read_csv(file_path)
            except Exception:
                continue

            # Try to extract sigma from filename using regex
            m = re.search(r'sigma_([0-9]+\.?[0-9]*)', file_name)
            if m:
                try:
                    sigma_value = float(m.group(1))
                except Exception:
                    sigma_value = np.nan
            else:
                # fallback: try splitting by underscore
                parts = os.path.splitext(file_name)[0].split('_')
                sigma_value = float(parts[1]) if len(parts) >= 2 else np.nan

            total_runs = len(df)

            # Normalize 'success' to boolean-like values
            success_count = 0
            if 'success' in df.columns and total_runs > 0:
                success_bool = df['success'].astype(str).str.lower().isin(['true', '1', 't', 'yes'])
                success_count = int(success_bool.sum())

            key = float(sigma_value) if not np.isnan(sigma_value) else sigma_value
            if key not in agg:
                agg[key] = {'total': 0, 'success': 0}
            agg[key]['total'] += total_runs
            agg[key]['success'] += success_count

    all_data = []
    for sigma_key, vals in agg.items():
        total_runs = vals['total']
        success_runs = vals['success']
        success_rate = success_runs / total_runs if total_runs > 0 else 0
        all_data.append({'sigma': sigma_key, 'total_runs': total_runs, 'success_runs': success_runs, 'success_rate': success_rate})

    df_out = pd.DataFrame(all_data)
    return df_out.sort_values(by='sigma', na_position='last')

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

def rename_csv_files():
    """
    Renombra los archivos CSV para que incluyan en tamaño
    Args:
        folder_path: Ruta de la carpeta que contiene los CSVs
    """
    folder_path = _select_csv_folder()
    for file_name in os.listdir(folder_path):
        if file_name.endswith('.csv'):
            new_file_name = file_name.replace('.csv', '_500x500.csv')
            os.rename(os.path.join(folder_path, file_name), os.path.join(folder_path, new_file_name))

def main():
    df = plot_success_rate()
    print(df)

if __name__ == "__main__":
    main()
            
