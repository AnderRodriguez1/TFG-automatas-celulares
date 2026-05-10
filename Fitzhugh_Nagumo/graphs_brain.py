from matplotlib import pyplot as plt
import numpy as np
from pathlib import Path
from scipy.signal import find_peaks

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
    
    plt.xlabel("Frecuencia (Ciclos por muestra)", fontsize=14)
    plt.xlim(0, 0.012)
    plt.ylabel("Intensidad", fontsize=14)
    plt.title("FFT de las señales de las regiones cerebrales", fontsize=26, fontweight="bold")
    plt.legend(loc="upper right")
    plt.tight_layout()

    plt.figure(figsize=(12, 8))
    for i, row in enumerate(fft_magnitudes_shifted_low_freq):
        roi_label = roi_labels[i]
        plt.plot(fft_freqs_low_freq[i], fft_magnitudes_shifted_low_freq[i], label=roi_label)

    plt.xlabel("Frecuencia (Ciclos por muestra)", fontsize=18)
    plt.xlim(0, 0.012)
    plt.ylabel("Intensidad", fontsize=18)
    plt.title("FFT de las señales de las regiones cerebrales (desplazadas)", fontsize=26, fontweight="bold")
    plt.legend(loc="upper right")
    plt.tight_layout()

    # Matriz de correlacion

    correlation_matrix = np.array(data["fc_matrix"])
    plt.figure(figsize=(8, 8))
    plt.imshow(correlation_matrix, cmap="viridis", vmin=0, vmax=1)
    # Incluir los valores en los cuadrados
    for i in range(correlation_matrix.shape[0]):
        for j in range(correlation_matrix.shape[1]):
            plt.text(j, i, f"{correlation_matrix[i, j]:.2f}", ha="center", va="center", color="white" if correlation_matrix[i, j] < 0.8 else "black", fontsize=10)
    plt.xticks(ticks=np.arange(len(roi_labels)), labels=roi_labels, fontsize=14)
    plt.yticks(ticks=np.arange(len(roi_labels)), labels=roi_labels, fontsize=14)
    plt.colorbar(label="Correlación")
    plt.title("Matriz de Correlación", fontsize=26, fontweight="bold")
    plt.tight_layout()
    plt.xlabel("Regiones Cerebrales", fontsize=18)
    plt.ylabel("Regiones Cerebrales", fontsize=18)

    # Si signals tiene shape (16, N_tiempo)
    fig, axes = plt.subplots(3, 1, figsize=(12, 6))
    axes[0].plot(signals[1])  # R2 - driver
    axes[0].set_title("R2 (fundamental)", fontsize=14, fontweight="bold")
    axes[1].plot(signals[8])  # región sospechosa
    axes[1].set_title("L1 (¿period-3?)", fontsize=14, fontweight="bold")
    axes[2].plot(signals[1]*signals[8])  # producto de R2 y L1
    axes[2].set_title("Producto R2 * L1", fontsize=14, fontweight="bold")
    # Si L1 dispara una vez por cada 3 pulsos de R2, confirma la hipótesis

    peaks_R2, _ = find_peaks(signals[1], height=0.8)  # Ajusta el umbral según sea necesario
    peaks_L1, _ = find_peaks(signals[8], height=0.5)  # Ajusta el umbral según sea necesario
    print(f"Numero de picos en R2: {len(peaks_R2)}")
    print(f"Numero de picos en L1: {len(peaks_L1)}")
    print(f"Cociente de picos R2/L1: {len(peaks_R2)/len(peaks_L1) if len(peaks_L1) > 0 else 'Inf'}")
    spacing_R2 = np.diff(peaks_R2)
    spacing_L1 = np.diff(peaks_L1)

    print(f"Periodo medio R2: {np.mean(spacing_R2):.1f} muestras")
    print(f"Periodo medio L1: {np.mean(spacing_L1):.1f} muestras")
    print(f"Cociente periodos L1/R2: {np.mean(spacing_L1)/np.mean(spacing_R2):.3f}")  # debería dar ~1.5
    print(f"Std L1 (uniformidad): {np.std(spacing_L1):.1f}")  # bajo = pulsos regulares
    print(f"Spacings L1: {np.sort(spacing_L1)}")
    print("Spacings pares:", spacing_L1[::2].mean())   # alternos 1
    print("Spacings impares:", spacing_L1[1::2].mean()) # alternos 2
    print("Suma:", spacing_L1[::2].mean() + spacing_L1[1::2].mean())  # ~717 ≈ 3×239
    # Histograma de spacings L1
    plt.figure(figsize=(8, 4))
    plt.hist(spacing_L1, bins=35, color="skyblue", edgecolor="black")
    plt.title("Espaciados entre picos de L1", fontsize=26, fontweight="bold")
    plt.xlabel("Espaciado (muestras)", fontsize=18)
    plt.ylabel("Número de picos", fontsize=18)

    plt.figure(figsize=(12, 8))
    plt.plot(signals[8], label="L1", color="red")
    plt.xlabel("Muestra", fontsize=18)
    plt.ylabel("Amplitud", fontsize=18)
    plt.xlim(500000, 500000+5000)  # Limitar el eje x para ver mejor los primeros pulsos
    plt.title("Señal de la región L1", fontsize=26, fontweight="bold")
    plt.tight_layout()


    plt.show()

    # plt.figure(figsize=(12, 8))
    # signals = {name: np.array(signals[i]) for i, name in enumerate(SIGNAL_NAMES)}
    

if __name__ == "__main__":
    plot_brain_curves()