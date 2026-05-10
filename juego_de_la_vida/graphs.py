import pandas as pd
import re
from PySide6 import QtWidgets
import sys
import os
import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path
from collections import defaultdict
from mpl_toolkits.axes_grid1.inset_locator import inset_axes, mark_inset


MAX_STABLE_ITERATIONS = 50
MIN_RELATIVE_CHANGE = 0.001


def trim_stable_tail(series, max_stable_iterations=MAX_STABLE_ITERATIONS, min_relative_change=MIN_RELATIVE_CHANGE):
    """
    Recorta el final de una serie cuando lleva demasiadas iteraciones sin cambio
    porcentual apreciable. Retorna la serie recortada y el índice de corte.
    """
    if len(series) <= 1:
        return series, len(series)

    values = np.asarray(series)
    stable_count = 0
    cutoff_index = len(values)

    for idx in range(1, len(values)):
        previous_value = values[idx - 1]
        current_value = values[idx]

        if previous_value == 0:
            relative_change = abs(current_value - previous_value)
        else:
            relative_change = abs(current_value - previous_value) / abs(previous_value)

        if relative_change <= min_relative_change:
            stable_count += 1
            if stable_count >= max_stable_iterations:
                cutoff_index = idx - max_stable_iterations + 1
                break
        else:
            stable_count = 0

    # Extender el gráfico unos cuantos puntos más allá del corte para verificar
    # que es constante (mostrar 50 puntos adicionales después del corte)
    extend_idx = min(cutoff_index + 50, len(values))
    return values[:extend_idx], cutoff_index


def plot_life_evolution_by_density():
    """
    Lee archivos CSV del Juego de la Vida y grafica la evolución del número de 
    células vivas para cada densidad inicial, mostrando todas en subplots.
    """
    app = QtWidgets.QApplication([])

    folder_path = QtWidgets.QFileDialog.getExistingDirectory(
        None,
        "Seleccionar carpeta con archivos CSV"
    )

    if not folder_path:
        print("No se seleccionó ninguna carpeta. Saliendo.")
        return
    
    # Agrupar archivos por densidad
    densities_data = defaultdict(list)
    
    # Expresión regular para extraer densidad del nombre del archivo
    pattern = re.compile(r'GoL_size(\d+)x(\d+)_density(\d+)_survive(\d+)_birth(\d+)\.csv$')
    
    print(f"Buscando archivos CSV en: {folder_path}")
    
    for filename in os.listdir(folder_path):
        if filename.endswith('.csv'):
            match = pattern.match(filename)
            if match:
                size_w, size_h, density, survive, birth = map(int, match.groups())
                densities_data[density].append((filename, survive, birth))
                print(f"Encontrado: {filename}")
    
    if not densities_data:
        print("No se encontraron archivos CSV con el patrón esperado.")
        return
    
    # Ordenar densidades
    sorted_densities = sorted(densities_data.keys())
    
    # Crear figura con subplots
    num_plots = len(sorted_densities)
    cols = 3
    rows = (num_plots + cols - 1) // cols
    
    fig, axes = plt.subplots(rows, cols, figsize=(15, 5 * rows))
    
    # Si hay solo un subplot, axes no es una matriz
    if num_plots == 1:
        axes = [[axes]]
    elif rows == 1:
        axes = [axes]
    
    # Aplanar axes para facilitar iteración
    axes_flat = []
    for row in axes:
        if isinstance(row, np.ndarray):
            axes_flat.extend(row)
        else:
            axes_flat.append(row)
    
    # Crear una gráfica por densidad
    for idx, density in enumerate(sorted_densities):
        ax = axes_flat[idx]
        
        # Leer todos los CSVs de esta densidad y promediar si hay varios
        all_data = []
        
        for filename, survive, birth in densities_data[density]:
            full_path = os.path.join(folder_path, filename)
            try:
                df = pd.read_csv(full_path)
                all_data.append(df)
                print(f"  Leyendo: {filename}")
            except Exception as e:
                print(f"  Error al leer {filename}: {e}")
        
        if not all_data:
            ax.text(0.5, 0.5, f"No data for density {density}%", 
                   ha='center', va='center', transform=ax.transAxes)
            ax.set_title(f'Densidad inicial {density}%', fontsize=16)
            continue
        
        # Si hay múltiples archivos (diferentes survive/birth), graficar todos
        # o promediar
        density_percent = density / 100
        for df in all_data:
            survive = int(df.iloc[0]['Survive'])
            birth = int(df.iloc[0]['Birth'])
            live_prop = df['Live Cells'] / (df.iloc[0]['Width'] * df.iloc[0]['Height'])
            live_prop_trimmed, cutoff_idx = trim_stable_tail(live_prop)
            iterations = df['Iteration'].iloc[:len(live_prop_trimmed)]
            ax.plot(iterations, live_prop_trimmed, linewidth=0.8, alpha=0.7,
                   label=f'B{birth}/S{survive}')
            # Marcar visualmente el punto de corte (donde comienza la región estable)
            if cutoff_idx < len(live_prop):
                continue
                # ax.axvline(x=df['Iteration'].iloc[cutoff_idx], color='red', 
                #           linestyle='--', linewidth=0.5, alpha=0.5)
        
        ax.set_xlabel('Iteración', fontsize=14)
        ax.set_ylabel('Proporción de células vivas', fontsize=14)
        ax.set_title(f'Densidad inicial {density}%', fontsize=16)
        ax.grid(True, alpha=0.3)
        if len(all_data) > 1:
            ax.legend(fontsize=8)
    
    # Ocultar los subplots vacíos
    for idx in range(num_plots, len(axes_flat)):
        axes_flat[idx].set_visible(False)
    
    plt.tight_layout()
    plt.suptitle('Evolución de la proporción de células vivas con diferentes densidades iniciales',
                 fontsize=18, fontweight='bold', y=1.00)
    plt.savefig('plot_evolution.png', dpi=300, bbox_inches='tight')
    plt.show()


def plot_rules_grouped_by_rule():
    """
    Para cada regla (S/B) crea un subplot que contiene las curvas de varias
    densidades (0.05..0.9). Añade un inset (recuadro) con zoom tras la caída
    inicial para facilitar la comparación, y marca el inset sobre la gráfica.
    """
    app = QtWidgets.QApplication([])

    folder_path = QtWidgets.QFileDialog.getExistingDirectory(
        None,
        "Seleccionar carpeta con archivos CSV"
    )

    if not folder_path:
        print("No se seleccionó ninguna carpeta. Saliendo.")
        return

    rules = [(1, 2), (2, 3), (3, 4), (4, 5)]
    titles = {
        (1, 2): "1 mantienen, 2 reviven",
        (2, 3): "2 mantienen, 3 reviven (Clásico)",
        (3, 4): "3 mantienen, 4 reviven",
        (4, 5): "4 mantienen, 5 reviven",
    }
    
    # Configuración individual de insets para cada regla
    # Parámetros: width, height, loc, x0, x1 (iteraciones exactas), y0, y1 (valores de células vivas en el eje Y)
    inset_config = {
        (1, 2): {"width": "60%", "height": "35%", "loc": "upper right", "x0": 10, "x1": 100, "y0": 0.28, "y1": 0.296},
        (2, 3): {"width": "60%", "height": "35%", "loc": "upper right", "x0": 400, "x1": 7_000, "y0": -0.01, "y1": 0.04},
        (3, 4): {"width": "60%", "height": "35%", "loc": "upper right", "x0": 5, "x1": 40, "y0": -0.01, "y1": 0.02},
        (4, 5): {"width": "60%", "height": "35%", "loc": "upper right", "x0": 1, "x1": 8, "y0": -0.01, "y1": 0.04},
    }

    densities = [0.05, 0.1, 0.3, 0.5, 0.7, 0.9]
    density_percents = [int(d * 100) for d in densities]
    colors = plt.rcParams['axes.prop_cycle'].by_key()['color']

    fig, axes = plt.subplots(2, 2, figsize=(14, 9))
    axes = axes.flatten()

    for ax, rule in zip(axes, rules):
        survive, birth = rule
        matched_any = False
        ref_length = None

        for i, dp in enumerate(density_percents):
            pattern = re.compile(rf"GoL_size(\d+)x(\d+)_density{dp}_survive{survive}_birth{birth}\.csv$")
            matched = None
            for fn in os.listdir(folder_path):
                if pattern.match(fn):
                    matched = os.path.join(folder_path, fn)
                    break
            if not matched:
                continue
            matched_any = True
            df = pd.read_csv(matched)
            if ref_length is None:
                ref_length = len(df)
            total_cells = df.iloc[0]['Width'] * df.iloc[0]['Height']
            live_prop = df['Live Cells'] / total_cells
            ax.plot(df['Iteration'], live_prop, label=f"{dp}%", color=colors[i % len(colors)], linewidth=0.9)

        if not matched_any:
            ax.text(0.5, 0.5, "No se encontraron CSVs para esta regla", ha='center')
            ax.set_title(titles.get(rule, f'B{birth}/S{survive}'), fontsize=16)
            continue

        ax.set_title(titles.get(rule, f'B{birth}/S{survive}'), fontsize=16)
        ax.set_xlabel('Iteración', fontsize=14)
        ax.set_ylabel('Proporción de células vivas', fontsize=14)
        ax.grid(True, alpha=0.3)

        # Inset: zona tras la caída inicial. Calcular ventana a partir de ref_length
        if ref_length is None:
            ref_length = 200
        
        # Obtener configuración del inset para esta regla
        cfg = inset_config.get(rule, {"width": "40%", "height": "35%", "loc": "upper right", "x0": 0, "x1": 100, "y_factor": 0.25})
        
        x0 = cfg["x0"]
        x1 = cfg["x1"]

        axins = inset_axes(ax, width=cfg["width"], height=cfg["height"], loc=cfg["loc"])
        for i, dp in enumerate(density_percents):
            pattern = re.compile(rf"GoL_size(\d+)x(\d+)_density{dp}_survive{survive}_birth{birth}\.csv$")
            matched = None
            for fn in os.listdir(folder_path):
                if pattern.match(fn):
                    matched = os.path.join(folder_path, fn)
                    break
            if not matched:
                continue
            df = pd.read_csv(matched)
            total_cells = df.iloc[0]['Width'] * df.iloc[0]['Height']
            live_prop = df['Live Cells'] / total_cells
            axins.plot(df['Iteration'], live_prop, color=colors[i % len(colors)], linewidth=0.8)

        axins.set_xlim(x0, x1)
        axins.set_ylim(cfg["y0"], cfg["y1"])
        axins.grid(True, alpha=0.25)
        mark_inset(ax, axins, loc1=2, loc2=4, fc="none", ec="0.5")

        ax.legend(title='Densidad', loc='upper left', fontsize=8)

    axes[0].set_xlim(-1, 125)
    axes[1].set_xlim(-50, 8000)
    axes[2].set_xlim(-1, 60)
    axes[3].set_xlim(-0.5, 20)
    plt.suptitle('Comparación de Reglas por Densidad', fontsize=18, fontweight='bold')
    plt.tight_layout()
    plt.subplots_adjust(top=0.92)
    plt.savefig('plot_rules_comparison.png', dpi=300, bbox_inches='tight')
    plt.show()


if __name__ == "__main__":
    #plot_rules_grouped_by_rule()
    plot_life_evolution_by_density()
