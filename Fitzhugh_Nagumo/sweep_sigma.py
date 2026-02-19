"""
Barrido de sigma (amplitud de ruido) para resonancia estocastica.

Para cada valor de sigma se ejecutan N ensayos de propagacion de onda
FitzHugh-Nagumo y se guardan los resultados en un CSV independiente
dentro de la carpeta CSVs/.

Uso:
    python sweep_sigma.py
"""

import sys
import os
import csv
import time
import numpy as np
from PySide6 import QtWidgets, QtCore
from config_modern import Config
from grid_widget_modern import GridWidget
import tqdm

# Parametros del barrido
SIGMA_VALUES = np.arange(0.0, 0.25, 0.005)   # Array de sigmas a probar
N_TRIALS     = 100                             # Repeticiones por sigma
MAX_STEPS    = 80_000                         # Pasos maximos por ensayo
ANALYZE_EVERY = 200                           # Pasos entre analisis de estado
OUTPUT_DIR   = os.path.join(os.path.dirname(__file__), "CSVs")

def run_sweep():
    app = QtWidgets.QApplication(sys.argv)

    os.makedirs(OUTPUT_DIR, exist_ok=True)

    config = Config(noise_amplitude=0.0)

    widget = GridWidget(config)
    widget.resize(300, 300)
    widget.show()

    def start_sweep():
        total_sigmas = len(SIGMA_VALUES)
        total_trials = total_sigmas * N_TRIALS

        print(f"BARRIDO DE SIGMA — {total_sigmas} valores × {N_TRIALS} ensayos = {total_trials} ensayos")
        print(f"Sigmas: {SIGMA_VALUES[0]:.3f} hasta {SIGMA_VALUES[-1]:.3f}")
        print(f"Max steps/ensayo: {MAX_STEPS}   analyze_every: {ANALYZE_EVERY}")
        print(f"Output: {OUTPUT_DIR}")

        sweep_start = time.perf_counter()
        pbar = tqdm.tqdm(total=total_trials, desc="Barrido", unit="trial")

        for sigma_idx, sigma in enumerate(SIGMA_VALUES):
            sigma = float(sigma)
            csv_path = os.path.join(OUTPUT_DIR, f"sigma_{sigma:.4f}.csv")

            # Actualizar amplitud de ruido y regenerar texturas
            config.noise_amplitude = sigma
            widget.config.noise_amplitude = sigma
            widget.regenerate_noise_pool()

            # Escribir cabecera del CSV
            with open(csv_path, 'w', newline='') as f:
                writer = csv.writer(f)
                writer.writerow([
                    "trial", "sigma", "success", "hit_target", "auto_excited",
                    "system_dead", "stagnated", "steps", "sim_time", "wall_time"
                ])

            for trial_idx in range(N_TRIALS):
                trial_start = time.perf_counter()

                # Regenerar el pool de ruido para cada ensayo individual
                # para que los ensayos sean estadísticamente independientes
                widget.regenerate_noise_pool()

                result = widget.run_single_trial(
                    max_steps=MAX_STEPS,
                    analyze_every=ANALYZE_EVERY,
                    verbose=False,
                    stop_on_auto_excitation=True,
                )
                wall_time = time.perf_counter() - trial_start

                # Etiqueta de resultado
                if result["success"]:
                    label = "EXITO"
                elif result["auto_excited"]:
                    label = "AUTO-EXC"
                elif result["system_dead"]:
                    label = "MUERTO"
                elif result["stagnated"]:
                    label = "ESTANCADO"
                else:
                    label = "TIMEOUT"

                # Append al CSV
                with open(csv_path, 'a', newline='') as f:
                    writer = csv.writer(f)
                    writer.writerow([
                        trial_idx + 1,
                        f"{sigma:.4f}",
                        result["success"],
                        result["hit_target"],
                        result["auto_excited"],
                        result["system_dead"],
                        result["stagnated"],
                        result["steps"],
                        f"{result['sim_time']:.4f}",
                        f"{wall_time:.2f}",
                    ])

                pbar.set_postfix(sigma=f"{sigma:.3f}", trial=f"{trial_idx+1}/{N_TRIALS}", res=label)
                pbar.update(1)

                # Procesar eventos Qt para que el SO no marque la app como "no responde"
                app.processEvents()

        pbar.close()
        elapsed = time.perf_counter() - sweep_start
        print(f"BARRIDO COMPLETADO — {total_trials} ensayos en {elapsed:.0f}s ({elapsed/60:.1f} min)")
        print(f"CSVs guardados en: {OUTPUT_DIR}")
        app.quit()

    QtCore.QTimer.singleShot(500, start_sweep)
    sys.exit(app.exec())


if __name__ == "__main__":
    run_sweep()
