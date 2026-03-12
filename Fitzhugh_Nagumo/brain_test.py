"""
Experimento con el patrón "brain". Se mide el factor de correlación de pearson tras haber puesto unos valores que hacen
que el sistema genere ondas de forma permanente. Luego se añaden lesiones en el cuerpo calloso (área de conexión entre hemisferios) 
y se mide cómo afecta a la propagación de las ondas.
"""

import numpy as np
from scipy.signal import correlate
from pathlib import Path
from PIL import Image
from grid_widget_modern import GridWidget
from config_modern import Config
import sys
from PySide6 import QtWidgets, QtCore
import matplotlib.pyplot as plt

X_PULSE = 340
Y_PULSE = 180

ROIS =[# De 0 a 3, derecho, de 4 a 7, izquierdo
    (265, 65,  "R1"),
    (340, 180, "R2"),
    (260, 250, "R3"),
    (320, 400, "R4"),
    (280, 160, "R5"),
    (245, 370, "R6"),
    (265, 320, "R7"),
    (275, 460, "R8"),
    (225, 65,  "L1"),
    (120, 180, "L2"),
    (210, 250, "L3"),
    (145, 400, "L4"),
    (202, 140, "L5"),
    (217, 370, "L6"),
    (200, 320, "L7"),
    (200, 460, "L8")
]
N_ROIS = len(ROIS)

ZONE_SIZE = 5
PULSE_INTERVAL_SIM = 200  # Tiempo simulado entre pulsos (unidades del modelo)
PULSE_PROBABILITY = 0.005  # Probabilidad de pulso aleatorio por frame
PULSE_MODE = "periodic"  # "periodic" o "random_right"

def get_right_grey_matter_coords(config):
    """
    Devuelve las coordenadas (x, y) de materia gris del hemisferio derecho.
    """
    image_path = Path(__file__).parent / "Cerebro.jpg"
    img = Image.open(image_path).convert('L')
    img = img.resize((config.grid_width, config.grid_height))
    img = img.transpose(Image.FLIP_TOP_BOTTOM)
    brain_data = np.array(img) / 255.0

    grey_mask = (brain_data >= config.brain_black_threshold) & (brain_data < config.brain_white_threshold)
    ys, xs = np.where(grey_mask)
    right_mask = xs > config.grid_width // 2
    return xs[right_mask], ys[right_mask]

def run_brain_test():
    """
    Ejecuta el experimento: pulsos periódicos en un punto fijo, se mide correlación de Pearson
    entre dos zonas.
    """
    app = QtWidgets.QApplication(sys.argv)
    config = Config(a=0.05, b=0.24, Du=0.75, a_white=0.22, Du_white=10.0,
                    initial_pattern="brain", spot_size=10, time_scale=100.0)
    widget = GridWidget(config)
    widget.show()
    app.processEvents()
    while not widget._is_initialized:
        app.processEvents()

    t_warmup = 40.0   # segundos reales de calentamiento
    t_simulation = 60.0
    signals = [[] for _ in range(N_ROIS)]
    measuring = [False]  # lista para poder modificar desde closure

    # Configurar pulsos según el modo
    pulse_timer = QtCore.QTimer()
    grey_xs, grey_ys, n_grey = None, None, 0

    if PULSE_MODE == "periodic":
        widget.activate_cell(X_PULSE, Y_PULSE)
        pulse_interval_real = PULSE_INTERVAL_SIM / config.time_scale
        pulse_timer.setInterval(int(pulse_interval_real * 1000))
        pulse_timer.timeout.connect(lambda: widget.activate_cell(X_PULSE, Y_PULSE))
        pulse_timer.start()
    elif PULSE_MODE == "random_right":
        grey_xs, grey_ys = get_right_grey_matter_coords(config)
        n_grey = len(grey_xs)

    results = {}

    timer = QtCore.QTimer()
    timer.setInterval(0)

    def step():
        if PULSE_MODE == "random_right" and np.random.random() < PULSE_PROBABILITY:
            idx = np.random.randint(n_grey)
            widget.activate_cell(int(grey_xs[idx]), int(grey_ys[idx]))

        widget.next_generation()
        if measuring[0]:
            widget.makeCurrent()
            u = widget._read_u()
            widget.doneCurrent()
            for i, (x, y, label) in enumerate(ROIS):
                zone = u[y-ZONE_SIZE:y+ZONE_SIZE+1, x-ZONE_SIZE:x+ZONE_SIZE+1]
                signals[i].append(np.mean(zone))

    def start_measuring():
        measuring[0] = True
        print("Warmup terminado, empezando a medir...")

    def finish():
        timer.stop()
        pulse_timer.stop()

        print("Medición terminada, analizando resultados...")

        sig_arr = np.array(signals)
        FC_matrix = np.zeros((N_ROIS, N_ROIS))
        Lag_matrix = np.zeros((N_ROIS, N_ROIS))

        for i in range(N_ROIS):
            for j in range(N_ROIS):
                if i == j:
                    FC_matrix[i, j] = 1.0 # Auto-correlación perfecta
                    Lag_matrix[i, j] = 0
                else:
                    s1 = sig_arr[i] - np.mean(sig_arr[i])
                    s2 = sig_arr[j] - np.mean(sig_arr[j])
                    
                    xcorr = correlate(s1, s2, mode='full')
                    norm = np.std(sig_arr[i]) * np.std(sig_arr[j]) * len(s1)
                    
                    if norm > 0:
                        xcorr /= norm
                        
                    max_idx = np.argmax(xcorr)
                    lags = np.arange(-len(s1) + 1, len(s1))
                    
                    FC_matrix[i, j] = xcorr[max_idx]
                    Lag_matrix[i, j] = lags[max_idx]

        # s1 = np.array(zone_1) - np.mean(zone_1)
        # s2 = np.array(zone_2) - np.mean(zone_2)
        # xcorr = correlate(s1, s2, mode='full')
        # norm = np.std(zone_1) * np.std(zone_2) * len(zone_1)
        # if norm > 0:
        #     xcorr /= norm
        # lags = np.arange(-len(s1) + 1, len(s1))
        # max_idx = np.argmax(xcorr)
        # best_lag = lags[max_idx]
        # r_max = xcorr[max_idx]

        # print(f"Muestras recogidas: {len(zone_1)}")
        # print(f"Max cross-correlation: {r_max:.4f} (lag = {best_lag} muestras)")

        results['sig_arr'] = sig_arr
        results['FC_matrix'] = FC_matrix
        results['Lag_matrix'] = Lag_matrix
        app.quit()

    timer.timeout.connect(step)
    timer.start()

    t_warmup_ms = int(t_warmup * 1000)
    t_total_ms = int((t_warmup + t_simulation) * 1000)
    QtCore.QTimer.singleShot(t_warmup_ms, start_measuring)
    QtCore.QTimer.singleShot(t_total_ms, finish)

    app.exec()
    plot_results(results['sig_arr'], results['FC_matrix'])

def plot_results(sig_arr, FC_matrix):
    labels = [r[2] for r in ROIS]

    fig, axes = plt.subplots(1, 2, figsize=(15, 6))

    axes[0].plot(sig_arr[1], label=labels[1], color='blue')       # R2
    axes[0].plot(sig_arr[2], label=labels[2], color='cyan')       # R3
    axes[0].plot(sig_arr[5], label=labels[5], color='red', linestyle='--')  # L2
    axes[0].plot(sig_arr[6], label=labels[6], color='orange', linestyle='--') # L3
    axes[0].set_xlabel("Muestra")
    axes[0].set_ylabel("Voltaje (u)")
    axes[0].set_title("Ondas propágandose (Muestra representativa)")
    axes[0].legend()
    axes[0].grid(True, alpha=0.3)

    cax = axes[1].imshow(FC_matrix, cmap='viridis', vmin=0, vmax=1)
    axes[1].set_xticks(np.arange(N_ROIS))
    axes[1].set_yticks(np.arange(N_ROIS))
    axes[1].set_xticklabels(labels, rotation=45, ha="right")
    axes[1].set_yticklabels(labels)
    axes[1].set_title("Matriz de Conectividad Funcional (FC)")
    fig.colorbar(cax, ax=axes[1], fraction=0.046, pad=0.04)

    for i in range(N_ROIS):
        for j in range(N_ROIS):
            axes[1].text(j, i, f"{FC_matrix[i, j]:.2f}", 
                         ha="center", va="center", color="white" if FC_matrix[i,j] < 0.8 else "black", fontsize=8)
            
    plt.tight_layout()
    plt.show()

if __name__ == "__main__":
    run_brain_test()