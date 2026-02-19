import numpy as np
import matplotlib.pyplot as plt
import PySide6.QtWidgets as QtWidgets
from grid_widget_modern import GridWidget
from config_modern import Config


def check_stability_energy():
    """
    Es una funcion para ver la estabilidad de la norma u^2 + v^2 a lo largo del tiempo. En un sistema estable, esta energía debería disiparse o mantenerse constante, pero no crecer indefinidamente.
    """
    energies = []
    steps = []
    app = QtWidgets.QApplication([])
    grid_widget = GridWidget(config=Config(a=0.18, Du=1.0, Dv=3.0))    
    
    grid_widget.show()  # Contexto activo
    app.processEvents()  # Procesar eventos para asegurar que la ventana se muestre
    grid_widget.makeCurrent()  # Asegurar que el contexto OpenGL esté activo
    grid_widget.perform_initial_render()

    for i in range(400000):
        grid_widget.run_fhn_shader()
        grid_widget.update()  # Actualizar la visualización
        
        # Capturar la norma cada 100 iteraciones
        grid_widget.makeCurrent()
        if i % 100 == 0: 
            raw = grid_widget.textures[grid_widget.current_texture_idx].read(alignment=1)
            data = np.frombuffer(raw, dtype='f4')
            
            # Separar canales u y v
            u = data[0::4]
            v = data[1::4]
            
            # Energía = Suma de cuadrados
            total_energy = np.sum(u**2 + v**2)
            energies.append(total_energy)
            steps.append(i)

            app.processEvents()  # Permitir que la interfaz responda
        
    # Graficar
    plt.figure(figsize=(10,5))
    plt.plot(steps, energies, label="Energía Total ($L_2^2$)")
    plt.title("Prueba de Estabilidad Numérica (Disipación)")
    plt.xlabel("Iteración")
    plt.ylabel(r"$\sum (u^2 + v^2)$")
    plt.grid(True)
    plt.legend()
    plt.show()

def main():
    check_stability_energy()

if __name__ == "__main__":
    main()