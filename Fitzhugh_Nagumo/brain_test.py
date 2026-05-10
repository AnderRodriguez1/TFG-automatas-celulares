"""
Experimento con el patrón "brain". Se mide el factor de correlación de pearson tras haber puesto unos valores que hacen
que el sistema genere ondas de forma permanente. Luego se añaden lesiones en el cuerpo calloso (área de conexión entre hemisferios) 
y se mide cómo afecta a la propagación de las ondas.
"""

import numpy as np
from scipy.signal import correlate
from pathlib import Path
from datetime import datetime
from PIL import Image
from grid_widget_modern import GridWidget
from config_modern import Config
import sys
from PySide6 import QtWidgets, QtCore
import matplotlib.pyplot as plt
from matplotlib.widgets import CheckButtons

RANDOM_SEED = 46
np.random.seed(RANDOM_SEED) # Para reproducibilidad
# Semillas importantes
# 45: zona R6 sale muy decorrelacionada del resto, las demas salen bien entre si
# 46: Hay decorrelacion entre zonas, ademas las zonas izquierdas salen algo menos correlacionadas entre si que las derechas, lo cual es interesante porque el pulso se da en el hemisferio derecho. La zona R6 vuelve a salir un poco menos correlacionada que el resto, aunque no tanto como con la semilla 45. En general parece un resultado más realista que con la semilla 45, donde todas las zonas estaban demasiado sincronizadas entre si

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
PULSE_PROBABILITY = 0.005  # Probabilidad de pulso aleatorio por frame
PULSE_MODE = "periodic"  # "periodic" o "random_right"
FFT_VERTICAL_OFFSET_SCALE = 1.15  # Aumenta/reduce el desfase vertical entre curvas FFT
FFT_VERTICAL_MIN_OFFSET = 0.05  # Separación mínima cuando la magnitud FFT es muy pequeña

# Cuerpo calloso: rectángulo inclinado definido por 4 vértices (x, y) en orden
CORPUS_CALLOSUM_COORDS = [
    (228, 468),  # esquina superior-izquierda
    (232, 468),  # esquina superior-derecha
    (247, 67),  # esquina inferior-derecha
    (239, 56),  # esquina inferior-izquierda
]
LESION_PROBABILITY = 0.001  # 0.0 = sin lesión, 1.0 = lesión total. Depreciado, ahora se calcula automáticamente para alcanzar TARGET_LESION_FRACTION
TARGET_LESION_FRACTION = 0.7  # área deseada (0.0-1.0). Si es 0.0 no se lesiona.


def _fmt_float_for_name(value, ndigits=3):
    """
    Formatea flotantes para nombres de archivo
    """
    txt = f"{float(value):.{ndigits}f}".rstrip("0").rstrip(".")
    if txt in {"", "-0"}:
        txt = "0"
    return txt.replace("-", "m").replace(".", "p")


def save_plotted_data_npz(sig_arr, FC_matrix, fft_data, fft_offset, labels, metadata, lag_matrix=None):
    """
    Guarda en NPZ todos los datos usados para las gráficas.
    """
    output_dir = Path(__file__).parent / "NPZs_brain_test"
    output_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    mode_tag = str(metadata.get("pulse_mode", "na"))
    seed_tag = str(int(metadata.get("random_seed", -1)))
    target_lesion_tag = _fmt_float_for_name(metadata.get("target_lesion_fraction", 0.0))
    actual_lesion_tag = _fmt_float_for_name(metadata.get("actual_lesion_fraction", 0.0))
    a_tag = _fmt_float_for_name(metadata.get("a", 0.0))
    b_tag = _fmt_float_for_name(metadata.get("b", 0.0))
    du_tag = _fmt_float_for_name(metadata.get("Du", 0.0))
    ts_tag = _fmt_float_for_name(metadata.get("time_scale", 1.0))

    file_name = (
        f"braintest_mode-{mode_tag}_seed-{seed_tag}"
        f"_lesT-{target_lesion_tag}_lesA-{actual_lesion_tag}"
        f"_a-{a_tag}_b-{b_tag}_Du-{du_tag}_ts-{ts_tag}_{timestamp}.npz"
    )
    out_path = output_dir / file_name

    if fft_data:
        fft_freqs = np.vstack([freqs for freqs, _ in fft_data])
        fft_magnitudes = np.vstack([mags for _, mags in fft_data])
        fft_magnitudes_shifted = np.vstack([
            mags + i * fft_offset for i, (_, mags) in enumerate(fft_data)
        ])
    else:
        fft_freqs = np.empty((0, 0), dtype=float)
        fft_magnitudes = np.empty((0, 0), dtype=float)
        fft_magnitudes_shifted = np.empty((0, 0), dtype=float)

    sig_arr = np.asarray(sig_arr, dtype=float)
    sample_index = np.arange(sig_arr.shape[1], dtype=int) if sig_arr.ndim == 2 else np.array([], dtype=int)
    roi_positions = np.array([(x, y) for x, y, _ in ROIS], dtype=int)
    roi_labels = np.array(labels)

    save_payload = {
        "sample_index": sample_index,
        "signals": sig_arr,
        "fc_matrix": np.asarray(FC_matrix, dtype=float),
        "fft_freqs": fft_freqs,
        "fft_magnitudes": fft_magnitudes,
        "fft_magnitudes_shifted": fft_magnitudes_shifted,
        "fft_vertical_offset": np.array([float(fft_offset)], dtype=float),
        "roi_labels": roi_labels,
        "roi_positions_xy": roi_positions,
        "rois_xyz_label": np.array(ROIS, dtype=object),
        "metadata": np.array([str(metadata)], dtype=object),
    }

    if lag_matrix is not None:
        save_payload["lag_matrix"] = np.asarray(lag_matrix, dtype=float)

    np.savez_compressed(out_path, **save_payload)
    print(f"Datos graficados guardados en: {out_path}")
    return out_path

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
    Devuelve la probabilidad encontrada e imprime el resultado. No es exacto
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

    actual_lesion_fraction = 0.7
    if lesion_prob > 0.0:
        actual_lesion_fraction = apply_corpus_callosum_lesion(widget, CORPUS_CALLOSUM_COORDS, lesion_prob)

    t_warmup = 60.0 * 100 / config.time_scale   # segundos reales de calentamiento
    t_simulation = 300 * 100 / config.time_scale  # segundos reales de simulación tras calentamiento
    signals = [[] for _ in range(N_ROIS)]
    measuring = [False]  # lista para poder modificar desde closure
    PULSE_INTERVAL_SIM = 200 * 100 / config.time_scale # Tiempo simulado entre pulsos (unidades del modelo)

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


        results['sig_arr'] = sig_arr
        results['FC_matrix'] = FC_matrix
        results['Lag_matrix'] = Lag_matrix
        results['metadata'] = {
            'random_seed': RANDOM_SEED,
            'pulse_mode': PULSE_MODE,
            'pulse_probability': PULSE_PROBABILITY,
            'pulse_interval_sim': PULSE_INTERVAL_SIM,
            'x_pulse': X_PULSE,
            'y_pulse': Y_PULSE,
            'zone_size': ZONE_SIZE,
            'n_rois': N_ROIS,
            'target_lesion_fraction': TARGET_LESION_FRACTION,
            'lesion_probability': lesion_prob,
            'actual_lesion_fraction': actual_lesion_fraction,
            'a': config.a,
            'b': config.b,
            'Du': config.Du,
            'a_white': config.a_white,
            'Du_white': config.Du_white,
            'spot_size': config.spot_size,
            'time_scale': config.time_scale,
            't_warmup_s': t_warmup,
            't_simulation_s': t_simulation,
            'grid_width': config.grid_width,
            'grid_height': config.grid_height,
        }
        app.quit()

    timer.timeout.connect(step)
    timer.start()

    t_warmup_ms = int(t_warmup * 1000)
    t_total_ms = int((t_warmup + t_simulation) * 1000)
    QtCore.QTimer.singleShot(t_warmup_ms, start_measuring)
    QtCore.QTimer.singleShot(t_total_ms, finish)

    app.exec()

    fft_data = []
    max_fft_mag = 0.0

    for arr in results['sig_arr']:
        centered = arr - np.mean(arr)
        fft_mag = np.abs(np.fft.rfft(centered)) / max(len(centered), 1)
        freqs = np.fft.rfftfreq(len(centered), d=1.0)
        fft_data.append((freqs, fft_mag))
        if len(fft_mag) > 0:
            max_fft_mag = max(max_fft_mag, float(np.max(fft_mag)))

    fft_offset = max_fft_mag * FFT_VERTICAL_OFFSET_SCALE if max_fft_mag > 0 else FFT_VERTICAL_MIN_OFFSET
    save_plotted_data_npz(sig_arr=results['sig_arr'], FC_matrix=results['FC_matrix'], 
                          fft_data=fft_data, fft_offset=fft_offset, labels=[r[2] for r in ROIS], 
                          metadata=results["metadata"], lag_matrix=results['Lag_matrix'])
    

if __name__ == "__main__":
    run_brain_test()