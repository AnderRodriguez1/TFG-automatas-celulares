import numpy as np
import matplotlib.pyplot as plt
from scipy.ndimage import label
from matplotlib.colors import ListedColormap

def analizar_huecos_iniciales(grid_size, density_active, density_refractory):
    """
    Genera la distribución inicial y analiza el tamaño de los 'lagos' de células inactivas.
    """
    # Densidades
    # Se define la densidad de activos
    # El resto se divide entre refractario e inactivo a partes iguales
    
    p_active = density_active
    p_refractory = density_refractory
    p_resting = 1.0 - p_active - p_refractory
    
    print(f"Configuracion inicial:")
    print(f"Activos: {p_active:.3f}")
    print(f"Refractarios: {p_refractory:.3f}")
    print(f"Inactivos: {p_resting:.3f}")
    
    # Se genera el grid usando las probabilidades
    grid = np.random.choice([0, 1, 2], 
                            size=(grid_size, grid_size), 
                            p=[p_resting, p_active, p_refractory])
    
    # Como interesa el espacio vacio, se hace una mascara que sea True donde haya 0 (inactivo)
    empty_space_mask = (grid == 0)

    plt.figure(figsize=(8, 8))
    plt.imshow(empty_space_mask, cmap='gray', interpolation='nearest')
    plt.title(f"Distribución Inicial (Negro = Inactivo)\nDimensión: {grid_size}x{grid_size}")
    plt.show()
    
    # Usamos label para identificar islas conectadas (vecindad de 8 para Moore)
    structure = np.array([
        [0, 1, 0],
        [1, 1, 1],
        [0, 1, 0]
    ], dtype=int)
    labeled_array, num_features = label(empty_space_mask, structure=structure)
    
    # 4. Calcular tamaños de los clusters
    # bincount cuenta cuántos píxeles tiene cada cluster
    cluster_sizes = np.bincount(labeled_array.ravel())
    # El índice 0 es el fondo (los obstáculos), lo quitamos
    cluster_sizes = cluster_sizes[1:]
    
    # 5. Calcular el "Diámetro Efectivo" de los huecos
    # Asumimos que el área es A ~ L^2, así que L ~ sqrt(A)
    # Esto nos da una idea de "cuántos píxeles de ancho" tiene el hueco
    cluster_diameters = np.sqrt(cluster_sizes)
    
    return cluster_diameters

# --- EJECUCIÓN ---
GRID_SIZE = 500
DENSIDAD_ACTIVOS = 0.15
# El resto (0.85) se divide entre 2 para refractarios
DENSIDAD_REFRACTARIOS = (1.0 - DENSIDAD_ACTIVOS) / 2 

diameters = analizar_huecos_iniciales(GRID_SIZE, DENSIDAD_ACTIVOS, DENSIDAD_REFRACTARIOS)

# Estadísticas
max_diameter = np.max(diameters)
mean_diameter = np.mean(diameters)
median_diameter = np.median(diameters)

# Percentil 99 (El tamaño de los huecos más grandes, que son los que importan para sobrevivir)
top_1_percent_diameter = np.percentile(diameters, 99)

print(f"\n--- RESULTADOS TOPOLÓGICOS ---")
print(f"Tamaño medio de un hueco (Lado): {mean_diameter:.2f} celdas")
print(f"Tamaño mediano de un hueco: {median_diameter:.2f} celdas")
print(f"Tamaño de los huecos grandes (Top 1%): {top_1_percent_diameter:.2f} celdas")
print(f"Tamaño del hueco más gigante: {max_diameter:.2f} celdas")
print(f"\nCOMPARACIÓN:")
print(f"Tu Periodo Refractario Crítico (donde muere): R ≈ 29")

# Graficar histograma
plt.figure(figsize=(10, 6))
plt.hist(diameters, bins=50, log=True, color='green', alpha=0.7)
plt.axvline(x=29, color='red', linestyle='--', label='R Crítico (29)')
plt.title("Distribución de tamaños de huecos libres iniciales")
plt.xlabel("Tamaño característico del hueco ($\sqrt{Area}$)")
plt.ylabel("Frecuencia (Log)")
plt.legend()
plt.show()