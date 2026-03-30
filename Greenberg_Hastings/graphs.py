import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import os
import re
from PySide6 import QtWidgets
from scipy.optimize import curve_fit

def process_data(folder_path=None):
    if folder_path is None:
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

def plot_data_average():
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

    ax2.plot(critical_periods.values(), marker='o', linestyle='-', color='purple')
    fig.suptitle('Proporción promedio de células activas en función del período refractario', fontsize=14, fontweight='bold')
    ax1.set_xlabel('Período refractario')
    ax1.set_ylabel('Proporción promedio de células activas (últimos 100 pasos)')
    ax1.grid(True)
    ax1.legend(title='Tamaños de grid')
    plt.show()

def compare_critical_periods():
    general_folder = select_general_folder()

    if not general_folder:
        print("No se encontraron datos para graficar.")
        return

    
    plt.figure(figsize=(11.69, 8.27))

    all_items = os.listdir(general_folder)
    data_folders = []
    for item in all_items:
        full_path = os.path.join(general_folder, item)
        match = re.search(r'Cambio_tamaño_grid(?:_(\d+))?', item)

        if os.path.isdir(full_path) and match:
            data_folders.append(item)

    print(f"Carpetas de datos encontradas: {data_folders}")
    
    aggregated_data = {}

    for folder in data_folders:
        folder_path = os.path.join(general_folder, folder)
        round = folder.split('_')[-1] if '_' in folder else 'Desconocido'
        if isinstance(round, str) and not round.isdigit():
            round = 1
        data_by_size = process_data(folder_path)
        sorted_sizes = sorted(data_by_size.keys(), key=lambda x: int(x.split('x')[0]))
        critical_periods = {}
        size_numeric = []
        for size_label in sorted_sizes:
            data = data_by_size[size_label]
            periods, averages = zip(*data)
            size = int(size_label.split('x')[0])
            size_numeric.append(size / 100)
            
            for idx, avg in enumerate(averages):
                if avg == 0:
                    if np.sum(averages[idx:]) == 0:
                        critical_periods[size_label] = periods[idx]
                        break
            if size not in aggregated_data:
                aggregated_data[size] = []
            aggregated_data[size].append(critical_periods[size_label])

        #plt.plot(size_numeric, critical_periods.values(), marker='o', linestyle='-', label=f'{round}', alpha=0.5)

    if aggregated_data:
        final_sizes = sorted(aggregated_data.keys())
        final_averages = []
        final_averages_std = []

        for size in final_sizes:
            mean_val = np.mean(aggregated_data[size])
            final_averages.append(mean_val)
            std_val = np.std(aggregated_data[size])
            final_averages_std.append(std_val)

        plt.errorbar(np.array(final_sizes) / 100, final_averages, yerr=final_averages_std, fmt='o', 
        color='red', ecolor='black', elinewidth=1.5, capsize=4, label='Promedio $\pm \sigma$')

        fit_params = curve_fit(fss_function, np.array(final_sizes) / 100, final_averages, maxfev=10000)
        fit_curve = fss_function(np.linspace(np.min(final_sizes) / 100, np.max(final_sizes) / 100, 100), *fit_params[0])

        print(f"Parámetros de ajuste FSS: {fit_params[0]}")
        plt.plot(np.linspace(np.min(final_sizes) / 100, np.max(final_sizes) / 100, 100), fit_curve, color='green', label='Curva ajustada')

    plt.title('Proporción promedio de células activas en función del período refractario', fontsize=18, fontweight='bold')
    plt.xlabel('Tamaño del grid (en cientos, escala logarítmica)', fontsize=14)
    plt.ylabel('Periodo refractario crítico', fontsize=14)
    plt.xscale('log')
    custom_ticks = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
    plt.xticks(custom_ticks, custom_ticks)
    from matplotlib.ticker import ScalarFormatter
    plt.gca().xaxis.set_major_formatter(ScalarFormatter())
    plt.grid(True)
    plt.legend(fontsize=12)
    plt.tight_layout()
    plt.show()

def _parse_density_token(density_token, force_percentage=False):
    """Convierte tokens de densidad a fracción (p.ej. '30'->0.30, '0.15'->0.15)."""
    token_str = str(density_token)
    raw_density = float(token_str)

    if force_percentage:
        return raw_density / 100

    # Convención: enteros en nombres (p.ej. density30, density1) representan porcentaje.
    if '.' not in token_str:
        return raw_density / 100

    # Si viene decimal > 1, también se interpreta como porcentaje (p.ej. 15.0 -> 0.15).
    return raw_density / 100 if raw_density > 1 else raw_density

def _extract_refractory_curves_by_density(folder_path, density_override=None):
    """Construye curvas promedio (y sigma) de células activas por periodo refractario para cada densidad."""
    data_by_density = {}

    for filename in os.listdir(folder_path):
        if not filename.endswith('.csv'):
            continue

        file_path = os.path.join(folder_path, filename)
        refr_match = re.search(r'refr(\d+)', filename)
        density_match = re.search(r'density(\d+(?:\.\d+)?)', filename)

        if not refr_match:
            continue

        refractory = int(refr_match.group(1))
        if density_override is not None:
            density = density_override
        else:
            if not density_match:
                continue
            density = _parse_density_token(density_match.group(1))

        try:
            data = pd.read_csv(file_path)
            if 'Active_cells' not in data.columns:
                continue

            active_cells = data['Active_cells'].values
            size_match = re.search(r'size(\d+)x(\d+)', filename)
            if size_match:
                total_cells = int(size_match.group(1)) * int(size_match.group(2))
            else:
                # Fallback por si el tamaño no está en el nombre.
                state_columns = ['Active_cells', 'Refractory_cells', 'Resting_cells']
                if all(col in data.columns for col in state_columns):
                    total_cells = np.mean((
                        data['Active_cells'] + data['Refractory_cells'] + data['Resting_cells']
                    ).values)
                else:
                    continue

            active_proportion = active_cells / total_cells
            average_active = np.mean(active_proportion[-100:])

            if density not in data_by_density:
                data_by_density[density] = {}
            if refractory not in data_by_density[density]:
                data_by_density[density][refractory] = []

            data_by_density[density][refractory].append(average_active)

        except Exception as e:
            print(f"Error al procesar el archivo {filename}: {e}")

    curves_by_density = {}
    for density, refr_dict in data_by_density.items():
        sorted_refr = sorted(refr_dict.keys())
        mean_averages = [np.mean(refr_dict[refr]) for refr in sorted_refr]
        std_averages = [np.std(refr_dict[refr]) for refr in sorted_refr]
        curves_by_density[density] = {
            'refractory': sorted_refr,
            'mean': mean_averages,
            'std': std_averages,
        }

    return curves_by_density

def _get_critical_refractory(periods, means, tol=1e-12):
    """Primer periodo refractario a partir del cual la curva permanece en 0."""
    for idx, avg in enumerate(means):
        if avg <= tol and np.all(np.array(means[idx:]) <= tol):
            return periods[idx]
    return None

def plot_individual_data(fit_bool=False, folder_path=None, show_plot=True):
    if folder_path is None:
        folder_path = QtWidgets.QFileDialog.getExistingDirectory(
            None,
            "Seleccionar carpeta con archivos CSV")

    if not folder_path:
        print("No se seleccionó ninguna carpeta.")
        return {}

    curves_by_density = _extract_refractory_curves_by_density(folder_path)

    if not curves_by_density:
        print("No se encontraron curvas válidas en la carpeta seleccionada.")
        return {}

    if not show_plot:
        return curves_by_density

    sorted_densities = sorted(curves_by_density.keys())
    density_to_plot = sorted_densities[0]
    if len(sorted_densities) > 1:
        print(
            "Se encontraron múltiples densidades; "
            f"se graficará solo density={density_to_plot:.4g}."
        )

    sorted_refr = curves_by_density[density_to_plot]['refractory']
    mean_averages = curves_by_density[density_to_plot]['mean']
    std_averages = curves_by_density[density_to_plot]['std']

    plt.figure(figsize=(11.69, 8.27))

    plt.errorbar(sorted_refr, mean_averages, yerr=std_averages, fmt='o',
                 color='blue', ecolor='black', linewidth=2, capsize=5,
                 label='Promedio $\\pm \\sigma$', zorder=10)
    critical_period = None
    if fit_bool:
        try:
            # Find critical period (first refr where mean is 0)
            nonzero = [(r, m) for r, m in zip(sorted_refr, mean_averages) if m > 0]
            if nonzero:
                clean_refr, clean_avg = zip(*nonzero)
                clean_refr = np.array(clean_refr)
                clean_avg = np.array(clean_avg)
                p_c_guess = clean_refr[-1] + 1  # Just past the last nonzero point
                p_0 = [0.5, 0.5, 0.01, p_c_guess, 0.5]
                bounds_lower = [0.0001, 0.0001, 0.0, clean_refr[-1], 0.0001]
                bounds_upper = [10, 5, 1, 250, 5]
                fit_params = curve_fit(curve_fit_function, clean_refr, clean_avg,
                                        p0=p_0, bounds=(bounds_lower, bounds_upper), maxfev=100000)
                fit_x = np.linspace(min(sorted_refr), max(sorted_refr), 200)
                fit_curve = curve_fit_function(fit_x, *fit_params[0])
                print(f"Parámetros de ajuste: {fit_params[0]}")

                # El ajuste log-log con beta sale medio pocho por la variacion, igual con muchas mas muestras se podría mejorar
                # critical_period = fit_params[0][3]
                # log_mask = (clean_refr > critical_period - 8) & (clean_refr < critical_period - 3)
                # log_density = np.log(clean_avg)[log_mask]
                # log_refr = np.log(critical_period - np.array(clean_refr)[log_mask])

                # slope = np.polyfit(log_refr, log_density, 1)[0]
                # print(f"Exponente crítico (beta): {slope:.4f}")


                plt.plot(fit_x, fit_curve, linestyle='--', color='red', linewidth=2, label='Curva ajustada')
        except Exception as e:
            import traceback
            traceback.print_exc()
            print(f"Error al ajustar la curva: {e}")

    plt.title(
        f'Proporción promedio de células activas (densidad={density_to_plot:.4g})',
        fontsize=18,
        fontweight='bold'
    )
    plt.xlabel('Período refractario', fontsize=14)
    plt.ylabel('Proporción promedio de células activas (últimos 100 pasos)', fontsize=14)
    plt.grid(True)
    plt.legend(fontsize=12)
    plt.tight_layout()
    plt.show()

    # if critical_period is not None:
    #     plt.figure(figsize=(11.69, 8.27))
    #     plt.plot(log_refr, log_density, 'o-', color='green', label='Datos para log-log')
    #     plt.xlabel('log(Período refractario crítico - Refractario)', fontsize=14)
    #     plt.ylabel('log(Proporción de células activas)', fontsize=14)
    #     plt.title('Relación log-log cerca del período refractario crítico', fontsize=18, fontweight='bold')
    #     plt.grid(True)
    #     plt.tight_layout()
    #     plt.show()

    return curves_by_density

def select_general_folder():
    folder_path = QtWidgets.QFileDialog.getExistingDirectory(
        None,
        "Seleccionar carpeta con subcarpetas de experimentos"
    )

    if not folder_path:
        print("No se seleccionó ninguna carpeta. Saliendo.")
        return None

    return folder_path

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

def plot_density_dependence():
    """
    Funcion para graficar el periodo refractario critico en funcion de la densidad inicial
    """
    root_folder = QtWidgets.QFileDialog.getExistingDirectory(
        None,
        "Seleccionar carpeta raíz con subcarpetas CSVs_GH_densidad_XX"
    )

    if not root_folder:
        print("No se seleccionó ninguna carpeta.")
        return

    relevant_folders = []
    for item in os.listdir(root_folder):
        full_path = os.path.join(root_folder, item)
        density_folder_match = re.fullmatch(r'CSVs_GH_densidad_(\d+(?:\.\d+)?)', item)
        if os.path.isdir(full_path) and density_folder_match:
            density = _parse_density_token(density_folder_match.group(1), force_percentage=True)
            relevant_folders.append((density, full_path, item))

    if not relevant_folders:
        print("No se encontraron subcarpetas con formato CSVs_GH_densidad_XX.")
        return

    critical_periods_by_density = {}

    for density, folder_path, folder_name in sorted(relevant_folders, key=lambda x: x[0]):
        curves_by_density = _extract_refractory_curves_by_density(folder_path, density_override=density)
        if density not in curves_by_density:
            print(f"No se pudieron construir curvas en {folder_name}.")
            continue

        periods = curves_by_density[density]['refractory']
        means = curves_by_density[density]['mean']
        critical_period = _get_critical_refractory(periods, means)

        if critical_period is not None:
            if density not in critical_periods_by_density:
                critical_periods_by_density[density] = []
            critical_periods_by_density[density].append(critical_period)

    if not critical_periods_by_density:
        print("No se encontró un período refractario crítico para ninguna densidad.")
        return

    critical_densities = sorted(critical_periods_by_density.keys())
    critical_period_means = [np.mean(critical_periods_by_density[d]) for d in critical_densities]
    critical_period_stds = [np.std(critical_periods_by_density[d]) for d in critical_densities]

    if critical_period_means is not None:
        params_fit = curve_fit(density_fit_function, critical_densities, critical_period_means, maxfev=10000)
        fit_x = np.linspace(min(critical_densities), max(critical_densities), 100)
        fit_curve = density_fit_function(fit_x, *params_fit[0])
        print(f"Parámetros de ajuste de dependencia con densidad: {params_fit[0]}")

    plt.figure(figsize=(11.69, 8.27))
    has_repetitions = any(len(vals) > 1 for vals in critical_periods_by_density.values())
    plt.errorbar(
            critical_densities,
            critical_period_means,
            yerr=critical_period_stds,
            marker='o',
            linestyle='none',
            color='blue',
            ecolor='black',
            capsize=4,
            label='Promedio $\\pm \\sigma$'
        )
    plt.legend()
    # if has_repetitions:
    #     plt.errorbar(
    #         critical_densities,
    #         critical_period_means,
    #         yerr=critical_period_stds,
    #         marker='o',
    #         color='blue',
    #         ecolor='black',
    #         capsize=4,
    #         label='Promedio $\\pm \\sigma$'
    #     )
    #     plt.legend()
    # else:
    #     plt.plot(critical_densities, critical_period_means, marker='o', linestyle='-', color='blue')
    if params_fit is not None:
        plt.plot(fit_x, fit_curve, linestyle='--', color='red', label='Curva ajustada')
        plt.legend()
        
    plt.title('Período refractario crítico en función de la densidad inicial', fontsize=18, fontweight='bold')
    plt.xlabel('Densidad inicial', fontsize=14)
    plt.ylabel('Período refractario crítico', fontsize=14)
    plt.grid(True)
    plt.tight_layout()
    plt.show()

def plot_data_collapse():
    """
    Función para graficar el colapso de datos usando los parámetros reales (A y tau)
    ajustados individualmente para cada densidad.
    Eje X: 1 - R / R_c
    Eje Y: (rho * R^tau) / (A * R_c^beta)
    """
    root_folder = QtWidgets.QFileDialog.getExistingDirectory(
        None,
        "Seleccionar carpeta raíz con subcarpetas CSVs_GH_densidad_XX\n(Para el colapso de datos)"
    )

    if not root_folder:
        return

    relevant_folders =[]
    for item in os.listdir(root_folder):
        full_path = os.path.join(root_folder, item)
        density_folder_match = re.fullmatch(r'CSVs_GH_densidad_(\d+(?:\.\d+)?)', item)
        if os.path.isdir(full_path) and density_folder_match:
            density = _parse_density_token(density_folder_match.group(1), force_percentage=True)
            relevant_folders.append((density, full_path, item))

    if not relevant_folders:
        return

    plt.figure(figsize=(11.69, 8.27))

    for density, folder_path, folder_name in sorted(relevant_folders, key=lambda x: x[0]):
        curves_by_density = _extract_refractory_curves_by_density(folder_path, density_override=density)
        if density not in curves_by_density:
            continue

        periods = np.array(curves_by_density[density]['refractory'])
        means = np.array(curves_by_density[density]['mean'])
        
        # Filtrar régimen activo
        mask = means > 0
        if not np.any(mask):
            continue
            
        clean_refr = periods[mask]
        clean_avg = means[mask]
        
        # 1. Ajustar la curva para ESTA densidad y sacar sus parámetros reales
        try:
            p_c_guess = clean_refr[-1] + 1.0  
            p_0 =[0.5, 0.5, p_c_guess, 0.5]
            bounds_lower =[0.001, 0.001, clean_refr[-1], 0.001]
            bounds_upper =[10.0, 5.0, 250.0, 5.0]
            
            fit_params, _ = curve_fit(curve_fit_function, clean_refr, clean_avg,
                                      p0=p_0, bounds=(bounds_lower, bounds_upper), maxfev=100000)
            
            A_opt = fit_params[0]
            tau_opt = fit_params[1]
            #c_opt = fit_params[2]
            Rc_opt = fit_params[2]
            beta_opt = fit_params[3]  # ¡Extraemos el exponente crítico de la transición!
            
            # 2. TRANSFORMACIÓN DE COLAPSO EXACTA Y NORMALIZADA
            X = 1 - clean_refr / Rc_opt
            
            # El Eje Y aísla puramente la función (1 - R/Rc)^beta
            Y = (clean_avg * (clean_refr ** tau_opt)) / (A_opt * (Rc_opt ** beta_opt))
            
            plt.plot(X, Y, marker='o', linestyle='-', alpha=0.8, 
                     label=f'Densidad {density:.2f} ($\\tau$={tau_opt:.2f}, $R_c$={Rc_opt:.1f}, $\\beta$={beta_opt:.2f}, A={A_opt:.2f})')
                     
        except Exception as e:
            print(f"Fallo al ajustar la densidad {density}: {e}")
            continue

    plt.title('Colapso de Datos', fontsize=18, fontweight='bold')
    plt.xlabel('$1 - R / R_c$ (Periodo Refractario Normalizado)', fontsize=14)
    plt.ylabel('$\\rho \\cdot R^{\\tau} / A \\cdot R_c^{\\beta}$ (Amplitud Reescalada)', fontsize=14)
    plt.grid(True)
    plt.legend(fontsize=10)
    plt.tight_layout()
    plt.show()

def curve_fit_function(x, a, b, p_c, beta):
    # CUANDO SE QUITA C, EL AJUSTE ES BASICAMENTE IGUAL, PREGUNTAR ESO
    base = np.maximum(p_c - x, 0)
    return a * (x**(-b)) * (base)**beta

def fss_function(x, a, b, c):
    return a - b * (x**(-c))

def density_fit_function(x, a, b, c):
    return a * x**(-b) + c

def main():
    app = QtWidgets.QApplication([])
    #plot_data_average(fit_bool=True)
    #plot_data_replicate()
    #compare_critical_periods()
    #plot_individual_data(fit_bool=True)
    plot_density_dependence()
    #plot_data_collapse()

if __name__=="__main__":
    main()