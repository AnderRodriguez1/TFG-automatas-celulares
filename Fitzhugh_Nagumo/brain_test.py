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
# Coordenadas de las regiones de interes, se toma la media de una zona de ZONE_SIZE x ZONE_SIZE
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

# Cuerpo calloso: rectángulo inclinado definido por 4 vértices (x, y) en orden
CORPUS_CALLOSUM_COORDS = [
    (228, 468),  # esquina superior-izquierda
    (232, 468),  # esquina superior-derecha
    (247, 67),  # esquina inferior-derecha
    (239, 56),  # esquina inferior-izquierda
]
LESION_PROBABILITY = 0.001  # 0.0 = sin lesión, 1.0 = lesión total. Depreciado, ahora se calcula automáticamente para alcanzar TARGET_LESION_FRACTION
TARGET_LESION_FRACTION = 0.7  # área deseada (0.0-1.0). Si es 0.0 no se lesiona.

def apply_corpus_callosum_lesion(widget, coords, probability):
    """
    Lesiona el cuerpo calloso colocando círculos de radio spot_size centrados en píxeles
    elegidos aleatoriamente dentro del polígono.
    - probability: fracción de píxeles del polígono usados como centros de círculo.
      Con círculos solapados, el área real lesionada será mayor; se imprime el % real.
    Devuelve el porcentaje de área del polígono efectivamente lesionada.
    """
    from matplotlib.path import Path as MplPath

    # Ordenar vértices por ángulo respecto al centroide para evitar aristas cruzadas
    cx = sum(p[0] for p in coords) / len(coords)
    cy = sum(p[1] for p in coords) / len(coords)
    coords_sorted = sorted(coords, key=lambda p: np.arctan2(p[1] - cy, p[0] - cx))

    poly = MplPath(coords_sorted + [coords_sorted[0]])

    # Bounding box
    xs = [p[0] for p in coords]
    ys = [p[1] for p in coords]
    x0 = max(0, min(xs))
    x1 = min(widget.config.grid_width - 1, max(xs))
    y0 = max(0, min(ys))
    y1 = min(widget.config.grid_height - 1, max(ys))

    # Grid de puntos dentro del bounding box y dentro del polígono
    gx, gy = np.meshgrid(np.arange(x0, x1 + 1), np.arange(y0, y1 + 1))
    points = np.column_stack([gx.ravel(), gy.ravel()])
    inside_flat = poly.contains_points(points)
    inside = inside_flat.reshape(gx.shape)

    # Coordenadas absolutas de los píxeles dentro del polígono
    inside_ys, inside_xs = np.where(inside)
    inside_ys += y0
    inside_xs += x0
    total_poly_pixels = len(inside_xs)

    # Seleccionar aleatoriamente un subconjunto como centros de círculos
    n_centers = max(1, int(total_poly_pixels * probability))
    chosen = np.random.choice(total_poly_pixels, size=n_centers, replace=False)
    center_xs = inside_xs[chosen]
    center_ys = inside_ys[chosen]

    # Pintar círculos de radio spot_size alrededor de cada centro
    radius = widget.config.spot_size
    H, W = widget.no_diffusion_data.shape
    Y_all, X_all = np.ogrid[:H, :W]
    for cx_c, cy_c in zip(center_xs, center_ys):
        dist2 = (X_all - cx_c) ** 2 + (Y_all - cy_c) ** 2
        widget.no_diffusion_data[dist2 <= radius ** 2] = 0.0

    # Calcular área real lesionada dentro del polígono
    lesioned_in_poly = int(np.sum(widget.no_diffusion_data[inside_ys, inside_xs] == 0.0))
    lesion_fraction = lesioned_in_poly / total_poly_pixels if total_poly_pixels > 0 else 0.0
    print(f"Área del cuerpo calloso lesionada: {lesion_fraction * 100:.1f}%  "
          f"({lesioned_in_poly}/{total_poly_pixels} píxeles)")

    widget.makeCurrent()
    try:
        widget.no_diffusion_mask.write(widget.no_diffusion_data.tobytes())
    finally:
        widget.doneCurrent()

    return lesion_fraction


def find_lesion_probability(config, coords, target_fraction, tol=0.01, max_iter=150):
    """
    Usa bisección para encontrar la probabilidad de centros que produce
    una cobertura de `target_fraction` (0-1) sobre el polígono del cuerpo calloso.
    Devuelve la probabilidad encontrada e imprime el resultado.
    """
    from matplotlib.path import Path as MplPath

    if target_fraction <= 0.0:
        return 0.0
    if target_fraction >= 1.0:
        return 1.0

    # Precalcular la geometría del polígono (igual que en estimate/apply)
    cx = sum(p[0] for p in coords) / len(coords)
    cy = sum(p[1] for p in coords) / len(coords)
    coords_sorted = sorted(coords, key=lambda p: np.arctan2(p[1] - cy, p[0] - cx))
    poly = MplPath(coords_sorted + [coords_sorted[0]])

    xs = [p[0] for p in coords]
    ys = [p[1] for p in coords]
    x0 = max(0, min(xs))
    x1 = min(config.grid_width - 1, max(xs))
    y0 = max(0, min(ys))
    y1 = min(config.grid_height - 1, max(ys))

    gx, gy = np.meshgrid(np.arange(x0, x1 + 1), np.arange(y0, y1 + 1))
    points = np.column_stack([gx.ravel(), gy.ravel()])
    inside_flat = poly.contains_points(points)
    inside = inside_flat.reshape(gx.shape)
    inside_ys, inside_xs = np.where(inside)
    inside_ys += y0
    inside_xs += x0
    total_poly_pixels = len(inside_xs)

    radius = config.spot_size
    H, W = config.grid_height, config.grid_width
    Y_all, X_all = np.ogrid[:H, :W]

    def coverage_for_prob(prob):
        n_centers = max(1, int(total_poly_pixels * prob))
        chosen = np.random.choice(total_poly_pixels, size=n_centers, replace=False)
        lesion_map = np.zeros((H, W), dtype=bool)
        for cx_c, cy_c in zip(inside_xs[chosen], inside_ys[chosen]):
            lesion_map[(X_all - cx_c) ** 2 + (Y_all - cy_c) ** 2 <= radius ** 2] = True
        return int(np.sum(lesion_map[inside_ys, inside_xs])) / total_poly_pixels

    lo, hi = 0.0, 1.0
    prob = 0.5
    for _ in range(max_iter):
        prob = (lo + hi) / 2.0
        frac = coverage_for_prob(prob)
        if abs(frac - target_fraction) <= tol:
            break
        if frac < target_fraction:
            lo = prob
        else:
            hi = prob

    final_frac = coverage_for_prob(prob)
    print(f"[Bisección] probabilidad={prob:.4f} → cobertura={final_frac*100:.1f}% "
          f"(objetivo={target_fraction*100:.1f}%)")
    return prob


def estimate_lesion_coverage(config, coords, probability):
    """
    Calcula en numpy (sin GPU) qué porcentaje del polígono quedaría lesionado
    con los parámetros dados. Imprime el resultado y lo devuelve.
    """
    from matplotlib.path import Path as MplPath

    cx = sum(p[0] for p in coords) / len(coords)
    cy = sum(p[1] for p in coords) / len(coords)
    coords_sorted = sorted(coords, key=lambda p: np.arctan2(p[1] - cy, p[0] - cx))
    poly = MplPath(coords_sorted + [coords_sorted[0]])

    xs = [p[0] for p in coords]
    ys = [p[1] for p in coords]
    x0 = max(0, min(xs))
    x1 = min(config.grid_width - 1, max(xs))
    y0 = max(0, min(ys))
    y1 = min(config.grid_height - 1, max(ys))

    gx, gy = np.meshgrid(np.arange(x0, x1 + 1), np.arange(y0, y1 + 1))
    points = np.column_stack([gx.ravel(), gy.ravel()])
    inside_flat = poly.contains_points(points)
    inside = inside_flat.reshape(gx.shape)

    inside_ys, inside_xs = np.where(inside)
    inside_ys += y0
    inside_xs += x0
    total_poly_pixels = len(inside_xs)

    n_centers = max(1, int(total_poly_pixels * probability))
    chosen = np.random.choice(total_poly_pixels, size=n_centers, replace=False)
    center_xs = inside_xs[chosen]
    center_ys = inside_ys[chosen]

    radius = config.spot_size
    H, W = config.grid_height, config.grid_width
    lesion_map = np.zeros((H, W), dtype=bool)
    Y_all, X_all = np.ogrid[:H, :W]
    for cx_c, cy_c in zip(center_xs, center_ys):
        lesion_map[(X_all - cx_c) ** 2 + (Y_all - cy_c) ** 2 <= radius ** 2] = True

    lesioned_in_poly = int(np.sum(lesion_map[inside_ys, inside_xs]))
    lesion_fraction = lesioned_in_poly / total_poly_pixels if total_poly_pixels > 0 else 0.0
    print(f"[Estimación previa] Área del cuerpo calloso lesionada: {lesion_fraction * 100:.1f}%  "
          f"({lesioned_in_poly}/{total_poly_pixels} píxeles)")
    return lesion_fraction


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
    config = Config(a=0.05, b=0.24, Du=0.75, a_white=0.22, Du_white=10.0,
                    initial_pattern="brain", spot_size=10, time_scale=100.0)

    lesion_prob = 0.0
    if TARGET_LESION_FRACTION > 0.0:
        lesion_prob = find_lesion_probability(config, CORPUS_CALLOSUM_COORDS, TARGET_LESION_FRACTION)

    app = QtWidgets.QApplication(sys.argv)
    widget = GridWidget(config)
    widget.show()
    app.processEvents()
    while not widget._is_initialized:
        app.processEvents()

    if lesion_prob > 0.0:
        apply_corpus_callosum_lesion(widget, CORPUS_CALLOSUM_COORDS, lesion_prob)

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