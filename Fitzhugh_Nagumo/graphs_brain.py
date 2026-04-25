from matplotlib import pyplot as plt
import numpy as np
from pathlib import Path

MODEL_DIR = Path(__file__).parent
NPZ_DIR = MODEL_DIR / "NPZs_brain_test"
BRAIN_TEST_NPZ = NPZ_DIR / "braintest_mode-periodic_seed-46_lesT-0p7_lesA-0p778_a-0p05_b-0p24_Du-0p75_ts-100_20260425_034104.npz"


def plot_brain_curves():
    data = np.load(BRAIN_TEST_NPZ)
    print(data.files)
    roi_labels = np.array(data["roi_labels"])
    fft_freqs = np.array(data["fft_freqs"])
    fft_magnitudes = np.array(data["fft_magnitudes"])
    fft_magnitudes_shifted = np.array(data["fft_magnitudes_shifted"])
    signals = np.array(data["signals"])

    high_frequency_mask = fft_freqs[0] < 0.05 # Las frecuencias altas no tienen intensidad significativa, así que las filtramos para mejorar la visualización

    fft_magnitudes_low_freq = fft_magnitudes[:, high_frequency_mask]
    fft_freqs_low_freq = fft_freqs[:, high_frequency_mask]
    fft_magnitudes_shifted_low_freq = fft_magnitudes_shifted[:, high_frequency_mask]

    # Se libera de la memoriaestas variables, que ocupan muchisima ram
    del fft_freqs
    del fft_magnitudes
    del fft_magnitudes_shifted

    plt.figure(figsize=(12, 8))
    for i, row in enumerate(fft_magnitudes_low_freq):
        roi_label = roi_labels[i]
        plt.plot(fft_freqs_low_freq[i], fft_magnitudes_low_freq[i], label=roi_label)
    
    plt.xlabel("Frecuencia (Ciclos por muestra)")
    plt.ylabel("Intensidad")
    plt.title("FFT de las señales de las regiones cerebrales")
    plt.legend(loc="upper right")
    plt.tight_layout()

    plt.figure(figsize=(12, 8))
    for i, row in enumerate(fft_magnitudes_shifted_low_freq):
        roi_label = roi_labels[i]
        plt.plot(fft_freqs_low_freq[i], fft_magnitudes_shifted_low_freq[i], label=roi_label)

    plt.xlabel("Frecuencia (Ciclos por muestra)")
    plt.ylabel("Intensidad")
    plt.title("FFT de las señales de las regiones cerebrales (desplazadas)")
    plt.legend(loc="upper right")
    plt.tight_layout()

    # Matriz de correlacion

    correlation_matrix = np.array(data["fc_matrix"])
    plt.figure(figsize=(8, 8))
    plt.imshow(correlation_matrix, cmap="viridis", vmin=0, vmax=1)
    # Incluir los valores en los cuadrados
    for i in range(correlation_matrix.shape[0]):
        for j in range(correlation_matrix.shape[1]):
            plt.text(j, i, f"{correlation_matrix[i, j]:.2f}", ha="center", va="center", color="white" if correlation_matrix[i, j] < 0.8 else "black", fontsize=8)
    plt.xticks(ticks=np.arange(len(roi_labels)), labels=roi_labels)
    plt.yticks(ticks=np.arange(len(roi_labels)), labels=roi_labels)
    plt.colorbar(label="Correlación")
    plt.title("Matriz de Correlación entre las señales de las regiones cerebrales")
    plt.tight_layout()
    plt.xlabel("Regiones Cerebrales")
    plt.ylabel("Regiones Cerebrales")

    # Si signals tiene shape (16, N_tiempo)
    fig, axes = plt.subplots(3, 1, figsize=(12, 6))
    axes[0].plot(signals[1])  # R2 - driver
    axes[0].set_title("R2 (fundamental)")
    axes[1].plot(signals[8])  # región sospechosa
    axes[1].set_title("L1 (¿period-3?)")
    axes[2].plot(signals[1]*signals[8])  # producto de R2 y L1
    axes[2].set_title("Producto R2 * L1")
    # Si L1 dispara una vez por cada 3 pulsos de R2, confirma la hipótesis

    plt.show()
    
    # plt.figure(figsize=(12, 8))
    # signals = {name: np.array(signals[i]) for i, name in enumerate(SIGNAL_NAMES)}
    

if __name__ == "__main__":
    plot_brain_curves()