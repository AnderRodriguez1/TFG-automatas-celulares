# Configuración por defecto

class Config:
    """
    Almacena los datos de configuracion:
        - Tamaño de la red
        - Velocidad inicial
        - Densidad inicial de células vivas
    """
    def __init__(self, grid_width=500, grid_height=500, initial_speed=24, initial_density=0.3):
        self.grid_width = grid_width
        self.grid_height = grid_height
        self.speed = initial_speed # frames por segundo
        self.density = initial_density # Proporción de células vivas al inicio