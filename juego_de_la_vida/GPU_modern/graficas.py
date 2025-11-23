from PIL._imaging import font
from pyparsing.util import line
import matplotlib.pyplot as plt
import pandas as pd
from pathlib import Path

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

if __name__ == "__main__":
    plot_density()