import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import re
from PySide6 import QtWidgets
import os
from scipy.optimize import curve_fit

def _select_csv_folder():
    app = QtWidgets.QApplication([])
    dialog = QtWidgets.QFileDialog()
    dialog.setFileMode(QtWidgets.QFileDialog.FileMode.Directory)
    dialog.setOption(QtWidgets.QFileDialog.Option.ShowDirsOnly, True)

    if dialog.exec():
        return dialog.selectedFiles()[0]
    return None

def load_csv_data():
    folder_path = _select_csv_folder()
    if folder_path is None:
        return pd.DataFrame()

    subdirs =[]
    for name in os.listdir(folder_path):
        path = os.path.join(folder_path, name)
        if os.path.isdir(path) and re.match(r'^CSVs_FHN_\d+$', name):
            subdirs.append(path)

    if not subdirs:
        subdirs = [folder_path]

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

            m = re.search(r'sigma_([0-9]+\.?[0-9]*)', file_name)
            if m:
                sigma_value = float(m.group(1))
            else:
                parts = os.path.splitext(file_name)[0].split('_')
                sigma_value = float(parts[1]) if len(parts) >= 2 else np.nan

            total_runs = len(df)
            if np.isnan(sigma_value) or total_runs == 0:
                continue

            # Leer columna 'success'
            if 'success' in df.columns:
                strict_bool = df['success'].astype(str).str.strip().str.lower().isin(['true', '1', 't', 'yes'])
            else:
                strict_bool = pd.Series([False] * total_runs)

            # Leer columna 'auto_excited'
            if 'auto_excited' in df.columns:
                auto_bool = df['auto_excited'].astype(str).str.strip().str.lower().isin(['true', '1', 't', 'yes'])
            else:
                auto_bool = pd.Series([False] * total_runs)

            # Métrica 1: Éxito Estricto (solo success)
            # Métrica 2: Ignición Total (success OR auto_excited)
            ignition_bool = strict_bool | auto_bool

            key = float(sigma_value)
            if key not in agg:
                agg[key] = {'total': 0, 'strict_trials':[], 'ignition_trials': []}
            
            agg[key]['total'] += total_runs
            agg[key]['strict_trials'].extend(strict_bool.astype(float).tolist())
            agg[key]['ignition_trials'].extend(ignition_bool.astype(float).tolist())

    all_data =[]
    for sigma_key, vals in agg.items():
        total_runs = vals['total']
        
        strict_rate = np.mean(vals['strict_trials'])
        # Calculamos el Error Estándar (SEM) binomial: sqrt(p * (1-p) / N)
        strict_std = np.sqrt(strict_rate * (1.0 - strict_rate) / total_runs) if total_runs > 0 else 0.0
        
        ignition_rate = np.mean(vals['ignition_trials'])
        # Calculamos el Error Estándar (SEM) binomial: sqrt(p * (1-p) / N)
        ignition_std = np.sqrt(ignition_rate * (1.0 - ignition_rate) / total_runs) if total_runs > 0 else 0.0
        
        all_data.append({
            'sigma': sigma_key,
            'total_runs': total_runs,
            'strict_rate': strict_rate,
            'strict_std': strict_std,
            'ignition_rate': ignition_rate,
            'ignition_std': ignition_std,
        })

    df_out = pd.DataFrame(all_data)
    return df_out.sort_values(by='sigma').reset_index(drop=True)


def hybrid_fit(x, alpha, k, sigma_c):
    """ Ajuste completo: Kramers (Ignición) * Sigmoide (Corte por turbulencia) """
    x_safe = np.maximum(np.asarray(x, dtype=float), 1e-8)
    p_ignicion = np.exp(-alpha / x_safe**2)
    p_corte = 1 / (1 + np.exp(k * (x_safe - sigma_c)))
    return p_ignicion * p_corte

def kramers_fit(x, alpha):
    """ Ajuste aislado: Solo Kramers (Ignición sin parámetro A) """
    x_safe = np.maximum(np.asarray(x, dtype=float), 1e-8)
    return np.exp(-alpha / x_safe**2)


def plot_combined_analysis():
    df = load_csv_data()
    if df.empty:
        return

    x_data = df['sigma'].to_numpy(dtype=float)
    y_strict = df['strict_rate'].to_numpy(dtype=float)
    y_ignit = df['ignition_rate'].to_numpy(dtype=float)

    x_min, x_max = np.min(x_data), np.max(x_data)
    x_fit = np.linspace(0, x_max, 500)

    # Ajuste total
    p0_hybrid =[0.002, 150, 0.05]
    bounds_hybrid = ([1e-5, 50, 1e-4],[0.05, 1000000, 0.25])
    try:
        popt_hybrid, _ = curve_fit(hybrid_fit, x_data*np.sqrt(0.02), y_strict, p0=p0_hybrid, bounds=bounds_hybrid)
        fit_strict = hybrid_fit(x_fit, *popt_hybrid)
    except:
        fit_strict = None

    # Ajuste de Ignición Total (Solo Kramers de 1 parámetro)
    p0_kramers = [0.002]
    bounds_kramers = ([1e-5],[0.05])
    try:
        popt_kramers, _ = curve_fit(kramers_fit, x_data*np.sqrt(0.02), y_ignit, p0=p0_kramers, bounds=bounds_kramers)
        fit_ignit = kramers_fit(x_fit, *popt_kramers)
    except:
        fit_ignit = None

    # Solo kramers
    plt.figure(figsize=(9, 6))
    plt.errorbar(x_data*np.sqrt(0.02), y_ignit, yerr=df['ignition_std'], fmt='s', color='forestgreen', alpha=0.7,
                 capsize=4, label='Datos (Ignorando Autoexcitación)')
    
    if fit_ignit is not None:
        plt.plot(x_fit, fit_ignit, '--', color='forestgreen', linewidth=2.5, 
                 label=r'Ajuste Arrhenius-Kramers')

    plt.title('Aislamiento de la componente de disparo', fontsize=24, fontweight="bold")
    plt.xlabel(r'Amplitud del Ruido escalada ($\sigma \cdot \sqrt{\Delta t}$)', fontsize=18)
    plt.xlim(0, 0.035)
    plt.ylabel('Probabilidad de Éxito', fontsize=18)
    plt.grid(True)
    plt.legend()
    plt.tight_layout()

    # Ajuste completo
    plt.figure(figsize=(9, 6))
    plt.errorbar(x_data*np.sqrt(0.02), y_strict, yerr=df['strict_std'], fmt='o', color='tab:blue',
                 capsize=4, label='Datos')
    
    if fit_strict is not None:
        plt.plot(x_fit, fit_strict, '-', color='darkorange', linewidth=2.5, 
                 label=r'Ajuste')

    plt.title('Resonancia Estocástica', fontsize=24, fontweight="bold")
    plt.xlabel(r'Amplitud del Ruido escalada ($\sigma \cdot \sqrt{\Delta t}$)', fontsize=18)
    plt.xlim(0, 0.035)
    plt.ylabel('Probabilidad de Éxito', fontsize=18)
    plt.grid(True)
    plt.legend()
    plt.tight_layout()

    
    plt.show()  

    print("PARÁMETROS DEL AJUSTE AISLADO (KRAMERS)")
    if fit_ignit is not None:
        print(f"Barrera Ignición (alpha): {popt_kramers[0]:.10f}\n")
    
    print("PARÁMETROS DEL AJUSTE GENERAL")
    if fit_strict is not None:
        print(f"Barrera Ignición (alpha): {popt_hybrid[0]:.10f}")
        print(f"Umbral Turbulencia (sigma_c): {popt_hybrid[2]:.10f} (Pendiente: {popt_hybrid[1]:.10f})")

if __name__ == "__main__":
    plot_combined_analysis()