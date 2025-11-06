# Configuración por defecto

class Config:
    """
    Almacena los datos de configuracion:
        - Tamaño de la red
        - Velocidad inicial
        - Densidad inicial de células vivas
    """
    def __init__(self, grid_width=500, grid_height=500, initial_speed=24, initial_density=0.3,
                 a=0.18, b=0.14, e=0.025, Du=0.5, Dv=4.0):
        self.grid_width = grid_width
        self.grid_height = grid_height
        self.speed = initial_speed # frames por segundo
        self.density = initial_density # Proporción de células vivas al inicio
        self.Dv = Dv # Coeficiente de difusión para v
        self.Du = Du # Coeficiente de difusión para u
        self.a = a # Parámetro 'a' del modelo
        self.b = b # Parámetro 'b' del modelo
        self.e = e # Parámetro 'e' del modelo