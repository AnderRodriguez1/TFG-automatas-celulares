# Configuración por defecto

class Config:
    """
    Almacena los datos de configuracion:
        - Tamaño de la red
        - Velocidad inicial
        - Densidad inicial de células vivas
    """
    def __init__(self, grid_width=500, grid_height=500, a=0.16, b=0.14, e=0.025, 
                Du=4.0, Dv=0.5, noise_amplitude=0.0, dt_simulation=0.02, 
                time_scale = 50.0, spot_size=30, initial_pattern="square"):
        self.grid_width = grid_width
        self.grid_height = grid_height
        self.Dv = Dv # Coeficiente de difusión para v
        self.Du = Du # Coeficiente de difusión para u
        self.a = a # Parámetro 'a' del modelo
        self.b = b # Parámetro 'b' del modelo
        self.e = e # Parámetro 'e' del modelo
        self.noise_amplitude = noise_amplitude # Amplitud del ruido 
        self.dt_simulation = dt_simulation # Paso de tiempo para la simulación (en segundos)
        self.time_scale = time_scale # Escala de tiempo para la visualización (1.0 = tiempo real, >1.0 = más rápido, <1.0 = más lento)
        self.spot_size = spot_size # Tamaño del patrón inicial (en píxeles)
        self.initial_pattern = initial_pattern # Tipo de patrón inicial ("square", "two_spots")