# Configuración por defecto

class Config:
    """
    Almacena los datos de configuracion:
        - Tamaño de la red
        - Velocidad inicial
        - Densidad inicial de células vivas
    """
    def __init__(self, grid_width=500, grid_height=500, visual_speed=24, initial_density=0.3,
                 a=0.16, b=0.14, e=0.025, Du=4.0, Dv=0.5, noise_amplitude=0.0, repetitions_per_frame=50,
                 dt_simulation=0.02, time_scale = 50.0):
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