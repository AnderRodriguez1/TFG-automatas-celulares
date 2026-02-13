from _ctypes import alignment
from pathlib import Path
from PySide6 import QtWidgets, QtCore
from PySide6.QtOpenGLWidgets import QOpenGLWidget
import numpy as np
import moderngl
from config_modern import Config
from PIL import Image
import numpy as np
import time

def load_shader_source(shader_file: str) -> str:
    """
    Lee el contenido de un archivo de shader
    """
    shader_path = Path(__file__).parent / shader_file
    try:
        with open(shader_path, 'r', encoding='utf-8') as f:
            return f.read()
    except FileNotFoundError:
        raise FileNotFoundError(f"Error Crítico: No se pudo encontrar el archivo de shader: {shader_path}")

class GridWidget(QOpenGLWidget):
    def __init__(self, config: Config):
        super().__init__()
        self.config = config

        self.ctx = None # Contexto de ModernGL
        # Programas de shaders
        self.display_program = None
        self.activate_cell_program = None
        self.fhn_program = None
        self.block_program = None
        # VAOs
        self.display_vao = None
        self.activate_cell_vao = None
        self.fhn_vao = None
        self.block_vao = None
        # FBOs y Texturas
        self.fbos = []
        self.textures = []
        self.current_texture_idx = 0
        # Variables para zoom y paneo
        self.zoom_level = 1.0
        self.view_offset_x = self.config.grid_width / 2.0
        self.view_offset_y = self.config.grid_height / 2.0
        self.panning = False
        self.last_pan_pos = QtCore.QPointF()

        self._is_initialized = False
        self.noise_pool = []          # Pool de texturas de ruido pre-generadas
        self.noise_pool_size = 8       # Número de texturas en el pool
        self.noise_pool_idx = 0

        self.time_accumulator = 0.0
        self.last_time = time.perf_counter()

    def initializeGL(self):
        """
        Funcion para inicializar OpenGL y los shaders
        """
        try:
            self.ctx = moderngl.create_context()
            # Cargar los shaders
            vertex_source = load_shader_source("shaders/vertex.glsl")
            display_source = load_shader_source("shaders/display.glsl")
            activate_cell_source = load_shader_source("shaders/activate_cell.glsl")
            fhn_source = load_shader_source("shaders/fhn.glsl")
            block_source = load_shader_source("shaders/block_cell.glsl")
            # Crear los programas de shaders
            self.display_program = self.ctx.program(vertex_shader=vertex_source, fragment_shader=display_source)
            self.activate_cell_program = self.ctx.program(vertex_shader=vertex_source, fragment_shader=activate_cell_source)
            self.fhn_program = self.ctx.program(vertex_shader=vertex_source, fragment_shader=fhn_source)
            self.block_program = self.ctx.program(vertex_shader=vertex_source, fragment_shader=block_source)
            # Crear los VAOs
            vertices = np.array([-1, -1, 1, -1, 1, 1, -1, 1], dtype='f4')
            indices = np.array([0, 1, 2, 0, 2, 3], dtype='i4')

            vbo = self.ctx.buffer(vertices)
            ebo = self.ctx.buffer(indices)

            self.display_vao = self.ctx.vertex_array(self.display_program, [(vbo, '2f', 'aPos')], index_buffer=ebo)
            self.activate_cell_vao = self.ctx.vertex_array(self.activate_cell_program, [(vbo, '2f', 'aPos')], index_buffer=ebo)
            self.fhn_vao = self.ctx.vertex_array(self.fhn_program, [(vbo, '2f', 'aPos')], index_buffer=ebo)
            self.block_vao = self.ctx.vertex_array(self.block_program, [(vbo, '2f', 'aPos')], index_buffer=ebo)
            # Crear las texturas y FBOs
            for _ in range(2):
                tex = self.ctx.texture((self.config.grid_width, self.config.grid_height), 4, dtype='f4')
                tex.filter = (moderngl.NEAREST, moderngl.NEAREST)
                self.textures.append(tex)
                self.fbos.append(self.ctx.framebuffer(color_attachments=[tex]))
            # Pre-generar pool de texturas de ruido (distribución normal)
            for _ in range(self.noise_pool_size):
                noise = np.random.randn(self.config.grid_height, self.config.grid_width, 4).astype('f4') * self.config.noise_amplitude
                tex = self.ctx.texture((self.config.grid_width, self.config.grid_height), 4, dtype='f4')
                tex.filter = (moderngl.NEAREST, moderngl.NEAREST)
                tex.repeat_x = True
                tex.repeat_y = True
                tex.write(noise.tobytes())
                self.noise_pool.append(tex)
            QtCore.QTimer.singleShot(0, self.perform_initial_render)
        except Exception as e:
            print(f"Error durante la inicialización de OpenGL: {e}")
            self.window().close()

    def perform_initial_render(self):
        self.run_init_shader()
        self._is_initialized = True
        self.update()

    def paintGL(self):
        if not self._is_initialized: 
            return
        
        paint_fbo = self.ctx.detect_framebuffer()
        paint_fbo.use()

        self.ctx.clear(0.1, 0.1, 0.1)

        self.display_program['u_zoom_level'].value = self.zoom_level
        self.display_program['u_view_offset'].value = (self.view_offset_x, self.view_offset_y)
        self.display_program['u_grid_size'].value = (self.config.grid_width, self.config.grid_height)

        self.textures[self.current_texture_idx].use(location=0)
        self.display_program['u_state_texture'].value = 0
        self.display_vao.render(moderngl.TRIANGLES)

    def _release_resources(self):

        #print("Liberando recursos de ModernGL...")
        self.makeCurrent()
        try:
            for fbo in self.fbos: 
                fbo.release()
            for texture in self.textures: 
                texture.release()
            if self.display_vao: 
                self.display_vao.release()
            if self.activate_cell_vao: 
                self.activate_cell_vao.release()
            if self.display_program: 
                self.display_program.release()
            if self.activate_cell_program: 
                self.activate_cell_program.release()
            if self.fhn_vao: 
                self.fhn_vao.release()
            if self.fhn_program: 
                self.fhn_program.release()
            if self.block_program: 
                self.block_program.release()
            if self.block_vao: 
                self.block_vao.release()
            if self.ctx: 
                self.ctx.release()
            for noise_tex in self.noise_pool:
                noise_tex.release()
            #print("Recursos liberados.")
        finally:
            self.doneCurrent()

    def next_generation(self):
        now = time.perf_counter()
        frame_dt = now - self.last_time
        self.last_time = now
        # No se hasta que punto es necesario limitar el dt, asi que lo dejo comentado por ahora
        # frame_dt = min(frame_dt, 0.1)  
        self.time_accumulator += frame_dt * self.config.time_scale
        max_steps = 300  # Evitar bucles infinitos en caso de que la simulación no pueda seguir el ritmo
        steps = 0
        while self.time_accumulator >= self.config.dt_simulation and steps < max_steps:
            self.run_fhn_shader()
            self.time_accumulator -= self.config.dt_simulation
            steps += 1
        self.update()
        

    def restart_grid(self):
        self.run_init_shader()
        self.update()

    def activate_cell(self, x, y):
        """
        Establece el estado de una celda en (x, y) al estado
        "more stable phase" para iniciar una nueva onda.
        """
        self.makeCurrent()
        try:
            source_idx = self.current_texture_idx
            dest_idx = 1 - source_idx

            self.fbos[dest_idx].use()

            self.activate_cell_program['u_grid_size'].value = (self.config.grid_width, self.config.grid_height)
            self.activate_cell_program['u_flip_coord'].value = (x, y)

            self.textures[source_idx].use(location=0)
            self.activate_cell_program['u_state_texture'].value = 0

            self.activate_cell_vao.render(moderngl.TRIANGLES)
            self.current_texture_idx = dest_idx
        finally:
            self.doneCurrent()
        self.update()

    def run_init_shader(self):
        """
        Funcion para ejecutar el shader de inicializacion.
        """
        self.makeCurrent()
        try:
            # Todo negro excepto un cuadrado en el centro
            u_background = 0.0
            v_background = 0.0

            # Cuadrado del centro (valores sacados de "Pattern Formation of the FitzHugh-Nagumo Model:
            # Cellular Automata Approach")
            u_spot = 0.9
            v_spot = 0.11
            
            spot_size = 30 # Tamaño del cuadrado
            # Inicializar con todo 0
            rgba_grid = np.zeros((self.config.grid_height, self.config.grid_width, 4), dtype='f4')
            rgba_grid[..., 0] = u_background
            rgba_grid[..., 1] = v_background
            rgba_grid[..., 3] = 1.0  # Canal Alpha

            # Calcular la posicion del centro
            center_x = self.config.grid_width // 2
            center_y = self.config.grid_height // 2
            
            start_x = center_x - spot_size // 2
            end_x = center_x + spot_size // 2
            start_y = center_y - spot_size // 2
            end_y = center_y + spot_size // 2

            # Se pinta el cuadrado con los valores spot
            # Igual habria que cambiar la condicion inicial
            rgba_grid[start_y:end_y, start_x:end_x, 0] = u_spot  # Canal R = u
            rgba_grid[start_y:end_y, start_x:end_x, 1] = v_spot  # Canal G = v

            # Se escribe la textura en la gpu
            dest_idx = 1 - self.current_texture_idx
            self.textures[dest_idx].write(rgba_grid.tobytes(), alignment=1)
            self.current_texture_idx = dest_idx
        finally:
            self.doneCurrent()

    def run_fhn_shader(self):
        self.makeCurrent()
        try:
            # Actualizar la textura que NO está en pantalla
            source_idx = self.current_texture_idx
            dest_idx = 1 - source_idx

            self.fbos[dest_idx].use()
            # Configurar los parámetros del shader
            self.fhn_program['u_grid_size'].value = (self.config.grid_width, self.config.grid_height)
            self.fhn_program['dt'].value = self.config.dt_simulation
            self.fhn_program['sqrt_dt'].value = np.sqrt(self.config.dt_simulation)
            self.fhn_program['a'].value = self.config.a
            self.fhn_program['b'].value = self.config.b
            self.fhn_program['e'].value = self.config.e
            self.fhn_program['Du'].value = self.config.Du
            self.fhn_program['Dv'].value = self.config.Dv
            
            # Enlazar la textura de origen
            self.textures[source_idx].use(location=0)
            self.fhn_program['u_state_texture'].value = 0

            # Usar textura de ruido pre-generada con offset aleatorio para variedad
            noise_tex = self.noise_pool[self.noise_pool_idx % self.noise_pool_size]
            self.noise_pool_idx += 1
            noise_tex.use(location=1)
            self.fhn_program['u_noise_texture'].value = 1
            self.fhn_program['u_noise_offset'].value = (np.random.random(), np.random.random())
            # Ejecutar el shader
            self.fhn_vao.render(moderngl.TRIANGLES)
            self.current_texture_idx = dest_idx
        finally:
            self.doneCurrent()

    def block_cell(self, x, y):
        """
        Bloquea una celda (actua como un muro)
        """
        self.makeCurrent()
        try:
            source_idx = self.current_texture_idx
            dest_idx = 1 - source_idx

            self.fbos[dest_idx].use()

            self.block_program['u_grid_size'].value = (self.config.grid_width, self.config.grid_height)
            self.block_program['u_block_coord'].value = (x, y)

            self.textures[source_idx].use(location=0)
            self.block_program['u_state_texture'].value = 0

            self.block_vao.render(moderngl.TRIANGLES)
            self.current_texture_idx = dest_idx
        finally:
            self.doneCurrent()
        self.update()

    def wheelEvent(self, event):
        """
        Evento de rueda del raton para zoom 
        """
        mouse_pos = event.position()
        grid_pos_before_zoom = self._pixel_to_grid(mouse_pos)
        zoom_factor = 1.05

        if event.angleDelta().y() > 0: 
            self.zoom_level *= zoom_factor
        else: 
            self.zoom_level /= zoom_factor

        self.zoom_level = max(0.2, min(self.zoom_level, 20.0))

        grid_pos_after_zoom = self._pixel_to_grid(mouse_pos)

        self.view_offset_x += grid_pos_before_zoom.x() - grid_pos_after_zoom.x()
        self.view_offset_y += grid_pos_before_zoom.y() - grid_pos_after_zoom.y()

        self.update()

    def mousePressEvent(self, event):
        """
        Evento de pulsar un boton del raton
        """
        if event.button() == QtCore.Qt.LeftButton:
            grid_pos = self._pixel_to_grid(event.position())
            grid_x = int(grid_pos.x())
            grid_y = int(grid_pos.y())

            if 0 <= grid_x < self.config.grid_width and 0 <= grid_y < self.config.grid_height: 
                self.activate_cell(grid_x, grid_y)
        elif event.button() == QtCore.Qt.RightButton:
            self.panning = True
            self.last_pan_pos = event.position()
            self.setCursor(QtCore.Qt.ClosedHandCursor)
        elif event.button() == QtCore.Qt.MiddleButton:
            grid_pos = self._pixel_to_grid(event.position())
            grid_x = int(grid_pos.x())
            grid_y = int(grid_pos.y())

            if 0 <= grid_x < self.config.grid_width and 0 <= grid_y < self.config.grid_height: 
                self.block_cell(grid_x, grid_y)
        event.accept()

    def mouseMoveEvent(self, event):
        """
        Evento de mover el raton para arrastre
        """
        if self.panning:
            delta = event.position() - self.last_pan_pos
            self.last_pan_pos = event.position()

            grid_units_visible_x = self.config.grid_width / self.zoom_level
            grid_units_visible_y = self.config.grid_height / self.zoom_level

            delta_grid_x = (delta.x()) * grid_units_visible_x / self.width()
            delta_grid_y = (delta.y()) * grid_units_visible_y / self.height()

            self.view_offset_x -= delta_grid_x
            self.view_offset_y += delta_grid_y

            self.update()

    def mouseReleaseEvent(self, event):
        """
        Evento de soltar un boton del raton
        """
        if self.panning and (event.button() == QtCore.Qt.MiddleButton or event.button() == QtCore.Qt.RightButton):
            self.panning = False
            self.setCursor(QtCore.Qt.ArrowCursor)
        event.accept()

    def _pixel_to_grid(self, pos):
        """
        Funcion para convertir coordenadas de pixel a coordenadas de la cuadricula
        """
        dpr = self.devicePixelRatio()
        pixel_x = pos.x() * dpr
        pixel_y = pos.y() * dpr

        view_width = self.width() * dpr
        view_height = self.height() * dpr

        norm_x = pixel_x / view_width - 0.5
        norm_y = (view_height - pixel_y) / view_height - 0.5

        grid_units_visible_x = self.config.grid_width / self.zoom_level
        grid_units_visible_y = self.config.grid_height / self.zoom_level

        grid_x = self.view_offset_x + norm_x * grid_units_visible_x
        grid_y = self.view_offset_y + norm_y * grid_units_visible_y
        
        return QtCore.QPointF(grid_x, grid_y)

    # En grid_widget_modern.py

    def save_pattern(self, file_path: str):
        """
        Guarda la textura actual en un archivo de imagen
        """
        self.makeCurrent()
        try:
            # Leer la textura actual
            texture = self.textures[self.current_texture_idx]
            # Pasar la textura a un array
            raw_data = texture.read(alignment=1)
            width, height = texture.size
            components = texture.components
            #print("Guardando patrón")
            # Pasar a un array de floats
            float_array = np.frombuffer(raw_data, dtype=np.float32) # El dtype es f32 para 4 componentes (RGBA)
            float_array = float_array.reshape((height, width, components))
            # Pasar a un array de uint8
            uint8_array = (float_array * 255).astype(np.uint8)
            # Crear la imagen con PIL y guardarla
            image = Image.fromarray(uint8_array, 'RGBA' if components == 4 else 'RGB')
            # En openGL el eje y está invertido respecto a PIL
            image = image.transpose(Image.FLIP_TOP_BOTTOM)
            image.save(file_path)
            #print(f"Patrón guardado correctamente en: {file_path}")

        except Exception as e:
            print(f"Se ha producido un error: {e}")
            import traceback
            traceback.print_exc()
        finally:
            self.doneCurrent()
            

    def import_pattern(self, file_path: str):
        """
        Importa un patrón desde un archivo de imagen
        """
        self.makeCurrent()
        try:
            # Abrir la imagen
            image = Image.open(file_path)
            image = image.resize((self.config.grid_width, self.config.grid_height))
            image = image.convert("RGBA") 
            image = image.transpose(method=Image.Transpose.FLIP_TOP_BOTTOM) # ModernGL tiene el eje y cambiado
            # El array uint8 viene de la imagen
            uint8_array = np.array(image)
            # Convertir a float32
            float_array = (uint8_array / 255.0).astype(np.float32)
            # Pasar a bytes
            data_for_texture = float_array.tobytes()
            # Aplicar la imagen a la textura que no está en pantalla
            dest_idx = 1 - self.current_texture_idx
            self.textures[dest_idx].write(data_for_texture, alignment=1)

            self.current_texture_idx = dest_idx

            print(f"Patrón importado desde {file_path}")

        except Exception as e:
            print(f"Error al importar el patrón: {e}")

        finally:
            self.doneCurrent()

            self.update()