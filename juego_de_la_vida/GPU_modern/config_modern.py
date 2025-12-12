# Configuración por defecto

from numpy.lib._npyio_impl import save
class Config:
    """
    Almacena los datos de configuracion:
        - Tamaño de la red
        - Velocidad inicial
        - Densidad inicial de células vivas
    """
    def __init__(self, grid_width=100, grid_height=100, initial_speed=24, initial_density=0.3,
                survive=2, birth=3, save_csv=False, csv_filename=None):
        self.grid_width = grid_width
        self.grid_height = grid_height
        self.speed = initial_speed # frames por segundo
        self.density = initial_density # Proporción de células vivas al inicio
        self.survive = survive
        self.birth = birth
        self.save_csv = save_csv
        self.csv_filename = csv_filename