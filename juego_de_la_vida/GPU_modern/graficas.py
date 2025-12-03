from matplotlib.offsetbox import HPacker
from cProfile import label
from PIL._imaging import font
from pyparsing.util import line
import matplotlib.pyplot as plt
import pandas as pd
from pathlib import Path
from mpl_toolkits.axes_grid1.inset_locator import inset_axes, mark_inset

def plot_rules():
    # Load the CSV file
    csv_path = Path(__file__).parent / "output"
    data = []

    # Collect CSVs in a deterministic (sorted) order so layout is reproducible
    csv_files = sorted(csv_path.glob("*.csv"), key=lambda p: p.name)
    for csv in csv_files:
        if "0" not in csv.name:
            df = pd.read_csv(csv)
            data.append(df)

    # Move the second CSV in `data` to be the first plotted item (if available)
    if len(data) >= 2:
        data.insert(0, data.pop(1))

    # Plot the data
    fig, axes = plt.subplots(2, 2, figsize=(11.69, 8.27))
    axes = axes.flatten()
    # Only plot up to the number of axes we have
    max_plots = min(len(axes), len(data))
    for i in range(max_plots):
        df = data[i]
        axes[i].plot(df['Iteration'], df['Live Cell Count'], marker='.', linestyle=' ')
        axes[i].set_xlabel('Iteración')
        axes[i].set_ylabel('Número de células vivas')
        axes[i].grid(True)

    axes[0].set_title('Reglas típicas (2 mantienen estado, 3 reviven)')
    axes[1].set_title('1 mantiene estado, 2 reviven')
    axes[2].set_title('3 mantienen estado, 4 reviven')
    axes[3].set_title('4 mantienen estado, 5 reviven')
    fig.suptitle('Evolución del número de células vivas en diferentes reglas del Juego de la Vida', fontsize=16, fontweight='bold')
    fig.tight_layout()
    plt.show()

def plot_density():
    # Load the CSV file
    csv_path = Path(__file__).parent / "output"
    data = []

    # Collect CSVs in a deterministic (sorted) order so layout is reproducible
    csv_files = sorted(csv_path.glob("*.csv"), key=lambda p: p.name)
    for csv in csv_files:
        if "0" in csv.name:
            df = pd.read_csv(csv)
            data.append(df)

    # Plot the data
    fig, axes = plt.subplots(2, 3, figsize=(11.69, 8.27))
    axes = axes.flatten()
    # Only plot up to the number of axes we have
    max_plots = min(len(axes), len(data))
    for i in range(max_plots):
        df = data[i]
        axes[i].plot(df['Iteration'], df['Live Cell Count'], marker='.', linestyle=' ')
        axes[i].set_xlabel('Iteración')
        axes[i].set_ylabel('Número de células vivas')
        axes[i].grid(True)

    axes[0].set_title('Densidad inicial 5%')
    axes[1].set_title('Densidad inicial 10%')
    axes[2].set_title('Densidad inicial 30%')
    axes[3].set_title('Densidad inicial 50%')
    axes[4].set_title('Densidad inicial 70%')
    axes[5].set_title('Densidad inicial 90%')

    fig.suptitle('Evolución del número de células vivas con diferentes densidades iniciales', fontsize=16, fontweight='bold')
    fig.tight_layout()
    plt.show()

def plot_all_rules_and_densities():
    csv_path = Path(__file__).parent / "output"
    
    rules_data = {}

    csv_files = sorted(csv_path.glob("*.csv"), key=lambda p: p.name)
    
    for csv in csv_files:
        # Formato esperado: live_cell_count_S_B_0_D.csv
        # Ejemplo: live_cell_count_1_2_0_05.csv
        parts = csv.stem.split('_')
        
        if len(parts) < 7:
            continue
            
        survive = parts[3]
        born = parts[4]
        density_part = parts[6] # El '05', '1', '3', etc.
        
        rule_key = f"{survive}_{born}"
        
        # Convertir la parte de densidad a float para ordenar correctamente 
        try:
            density_val = float(f"0.{density_part}")
        except ValueError:
            continue

        if rule_key not in rules_data:
            rules_data[rule_key] = []
            
        df = pd.read_csv(csv)
        rules_data[rule_key].append((density_val, df))

    for rule_key, data_list in rules_data.items():
        # Hacer que las listas tengan la misma longitud

        if rule_key == "1_2":
            continue  # No hacer nada para esta regla, ya que es caótica, no llega a ser estable

        max_len = 0

        for _, df in data_list:
            # use .iat for fast positional access and avoid using 'raise' inside a conditional expression
            last_iter_val = df['Iteration'].iat[-1]
            if last_iter_val != df['Iteration'].max():
                raise ValueError("Inconsistent iteration lengths found.")
            current_max = last_iter_val
            if current_max > max_len:
                max_len = current_max

        updated_list = []

        for density, df in data_list:
            last_iter = df['Iteration'].iat[-1] if max_len != 0 else None
            if last_iter < max_len:
                last_value = df['Live Cell Count'].get(last_iter, df['Live Cell Count'].iloc[-1])

                missing_iters = range(int(last_iter) + 1, int(max_len) + 1)

                extension_df = pd.DataFrame({
                    'Iteration': missing_iters,
                    'Live Cell Count': last_value #Repetir el ultimo valor, ya que en todas se llega a un estado estable
                                                  # excepto la 1_2
                })

                df_extended = pd.concat([df, extension_df], ignore_index=True)
                updated_list.append((density, df_extended))
            else:
                updated_list.append((density, df))
        rules_data[rule_key] = updated_list



    zoom_settings = {
        "1_2": {
            "xlim": (25, 150), 
            "ylim": (2500, 3200), 
            "loc": "upper center", # Abajo derecha para no tapar el inicio
            "width": "50%", "height": "50%" 
        },
        "2_3": {
            "xlim": (200, 3920),  
            "ylim": (-50, 1000),
            "loc": "upper center", 
            "width": "45%", "height": "50%"
        },
        "3_4": {
            "xlim": (7, 49),
            "ylim": (-50, 200),
            "loc": "upper center",
            "width": "50%", "height": "50%"
        },
        "4_5": {
            "xlim": (3, 47),
            "ylim": (-20, 100),
            "loc": "upper center",
            "width": "50%", "height": "50%"
        }
    }
    # Crear la figura 2x2
    fig, axes = plt.subplots(2, 2, figsize=(14, 10))
    axes = axes.flatten()
    
    # Ordenar las reglas para que salgan en orden (1_2, 2_3, 3_4, 4_5)
    sorted_rules = sorted(rules_data.keys())
    
    # Títulos descriptivos para cada regla (puedes personalizarlos)
    titles = {
        "1_2": "1 mantiene, 2 reviven",
        "2_3": "2 mantienen, 3 reviven (Clásico)",
        "3_4": "3 mantienen, 4 reviven",
        "4_5": "4 mantienen, 5 reviven"
    }

    for i, ax in enumerate(axes):
        if i >= len(sorted_rules):
            break
            
        rule = sorted_rules[i]
        data_list = rules_data[rule]
        
        # Ordenar por densidad de menor a mayor para la leyenda
        data_list.sort(key=lambda x: x[0])
        
        # Graficar cada densidad
        for density, df in data_list:
            ax.plot(df['Iteration'], df['Live Cell Count'], 
                    marker='.', markersize=2, linestyle='-', linewidth=1, 
                    label=f'{int(density*100)}%')
        
        # Configuración de cada subplot
        title_text = titles.get(rule, f"Regla S:{rule.split('_')[0]} B:{rule.split('_')[1]}")
        ax.set_title(title_text, fontsize=11, fontweight='bold', pad=10)
        ax.set_xlabel('Iteración', labelpad=5)
        ax.set_ylabel('Células vivas', labelpad=5)
        #ax.set_yscale('log')
        ax.grid(True, which='both', linestyle='--', alpha=0.6)
        ax.legend(title="Densidad Inicial", fontsize='small')

        if rule in zoom_settings:
            cfg = zoom_settings[rule]
            
            # Usamos inset_axes para garantizar el tamaño físico de la caja
            axins = inset_axes(ax, width=cfg["width"], height=cfg["height"], loc=cfg["loc"])
            
            # Volver a graficar los datos dentro de la caja
            for density, df in data_list:
                axins.plot(df['Iteration'], df['Live Cell Count'], 
                        marker='.', markersize=2, linestyle='-', linewidth=1)

            # Establecer límites del zoom
            axins.set_xlim(*cfg["xlim"])
            axins.set_ylim(*cfg["ylim"])

            # Estética de la caja
            axins.tick_params(axis='both', which='both', labelsize=7)
            axins.grid(True, which='both', linestyle='--', alpha=0.6)
            
            # Dibujar líneas conectoras
            # Si la caja está a la derecha, conectamos las esquinas de la izquierda (2 y 3)
            # Si está arriba, las de abajo, etc. Ajuste automático básico:
            if "right" in cfg["loc"]:
                loc1, loc2 = 2, 4 # Conectar esquinas izquierda-arriba y derecha-abajo (diagonal) o 2 y 3
                mark_inset(ax, axins, loc1=2, loc2=4, fc="none", ec="0.5")
            else:
                mark_inset(ax, axins, loc1=1, loc2=3, fc="none", ec="0.5")


    fig.suptitle('Comparación de Reglas y Densidades', fontsize=16, fontweight='bold')
    fig.tight_layout(rect=[0, 0, 1, 0.96], h_pad = 2)
    plt.show()

if __name__ == "__main__":
    plot_all_rules_and_densities()