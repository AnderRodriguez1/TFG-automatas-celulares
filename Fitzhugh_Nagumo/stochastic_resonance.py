"""
Script de prueba VISUAL para run_single_trial.
Ejecuta un unico ensayo de propagacion de onda FitzHugh-Nagumo
con visualizacion en tiempo real, para poder observar la onda
y verificar cuando/como se detecta la autoexcitacion.

Uso:
    python stochastic_resonance.py
"""

import sys
import time
import numpy as np
from PySide6 import QtWidgets, QtCore
from config_modern import Config
from grid_widget_modern import GridWidget


class VisualTrial(QtWidgets.QMainWindow):
    """Ventana que ejecuta la simulacion paso a paso, actualizando la vista."""

    def __init__(self, config, steps_per_tick=200, max_steps=40_000):
        super().__init__()
        self.setWindowTitle(f"Stochastic Resonance — σ = {config.noise_amplitude}")
        self.config = config
        self.steps_per_tick = steps_per_tick   # Pasos de simulacion por refresco visual
        self.max_steps = max_steps

        self.widget = GridWidget(config)
        self.setCentralWidget(self.widget)
        self.resize(800, 800)

        # Estado del ensayo
        self.step = 0
        self.sim_time = 0.0
        self.trial_running = False
        self.wall_start = 0.0

        # Timer para avanzar la simulacion (~30 fps visual)
        self.sim_timer = QtCore.QTimer(self)
        self.sim_timer.timeout.connect(self._tick)

        # Iniciar el ensayo tras la inicializacion de OpenGL
        QtCore.QTimer.singleShot(300, self._start_trial)

    def _start_trial(self):
        """Prepara y arranca el ensayo."""
        w = self.widget
        w.run_init_shader()   # ya hace makeCurrent/doneCurrent internamente
        w._reset_tracking()

        self.step = 0
        self.sim_time = 0.0
        self.wall_start = time.perf_counter()
        self.trial_running = True

        print("=" * 60)
        print(f"Grid:  {self.config.grid_width}x{self.config.grid_height}")
        print(f"Sigma: {self.config.noise_amplitude}")
        print(f"dt:    {self.config.dt_simulation}   max_steps: {self.max_steps}")
        print(f"steps_per_tick: {self.steps_per_tick}")
        print("=" * 60)

        self.sim_timer.start(16)  # ~60 ticks/s

    def _tick(self):
        """Avanza la simulacion varios pasos y refresca la pantalla."""
        if not self.trial_running:
            return

        w = self.widget
        remaining = self.max_steps - self.step
        n = min(self.steps_per_tick, remaining)
        if n <= 0:
            self._finish_trial()
            return

        # Batch de N pasos de FHN en un solo contexto GL
        w.run_fhn_steps(n)
        self.step += n
        self.sim_time += n * self.config.dt_simulation

        # Analizar estado (1 readback + numpy por tick)
        w.analyze_state()

        # Refrescar pantalla
        w.update()

        # Actualizar titulo con progreso
        n_ever = int(np.sum(w.ever_activated))
        n_reached = int(np.sum(w.reached))
        status = ""
        if w.auto_excited:
            status = f"  \u26a0 AUTO-EXCITACI\u00d3N ({n_ever - n_reached} espureas)"
        self.setWindowTitle(
            f"\u03c3={self.config.noise_amplitude}  "
            f"step {self.step}/{self.max_steps}  "
            f"t={self.sim_time:.1f}s  "
            f"reached={n_reached}  ever={n_ever}{status}"
        )

        if self.step % 2000 < self.steps_per_tick:
            print(f"  step {self.step}/{self.max_steps}  t={self.sim_time:.2f}s  "
                  f"ever={n_ever}  reached={n_reached}  auto_exc={w.auto_excited}  "
                  f"u_max={w._last_u_max:.3f}")

        # Condiciones de parada
        if w.hit_target or w.system_dead or self.step >= self.max_steps:
            self._finish_trial()

    def _finish_trial(self):
        """Imprime resultados y para el timer (la ventana sigue abierta)."""
        self.sim_timer.stop()
        self.trial_running = False
        w = self.widget
        wall_elapsed = time.perf_counter() - self.wall_start
        success = w.hit_target and not w.auto_excited
        n_ever = int(np.sum(w.ever_activated))
        n_reached = int(np.sum(w.reached))

        print("-" * 60)
        if success:
            print("RESULTADO: ÉXITO — La onda llegó sin autoexcitación")
        elif w.hit_target and w.auto_excited:
            print("RESULTADO: FALLO (autoexcitación) — Llegó pero hubo activación espontánea")
        elif w.system_dead:
            print("RESULTADO: FALLO (sistema muerto) — Toda la actividad cesó")
        else:
            print("RESULTADO: FALLO (timeout) — La onda no alcanzó la pared")
        print(f"  hit_target:      {w.hit_target}")
        print(f"  auto_excited:    {w.auto_excited}")
        print(f"  system_dead:     {w.system_dead}")
        print(f"  last u_max:      {w._last_u_max:.4f}")
        print(f"  ever_activated:  {n_ever}")
        print(f"  reached:         {n_reached}")
        print(f"  espúreas:        {n_ever - n_reached}")
        print(f"  pasos:           {self.step}")
        print(f"  tiempo sim:      {self.sim_time:.2f} s")
        print(f"  tiempo real:     {wall_elapsed:.1f} s")
        print("=" * 60)

        if success:
            final_status = "ÉXITO ✓"
        elif w.auto_excited:
            final_status = "AUTO-EXCITACIÓN"
        elif w.system_dead:
            final_status = "SISTEMA MUERTO"
        else:
            final_status = "TIMEOUT"
        self.setWindowTitle(
            f"TERMINADO — {final_status}  σ={self.config.noise_amplitude}  "
            f"steps={self.step}  t={self.sim_time:.1f}s"
        )


def run_test():
    app = QtWidgets.QApplication(sys.argv)

    # ── Parametros del ensayo ──────────────────────────────────
    sigma = 0.03            # Amplitud del ruido
    config = Config(
        noise_amplitude=sigma,
    )

    window = VisualTrial(
        config,
        steps_per_tick=200,      # Pasos de FHN por refresco visual (batch GPU)
        max_steps=100000,        # Maximo pasos antes de declarar fracaso
    )
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    run_test()
