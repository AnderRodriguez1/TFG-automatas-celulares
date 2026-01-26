from numpy import dtype
from _ctypes import alignment
from pathlib import Path
from PySide6 import QtWidgets, QtCore
from PySide6.QtOpenGLWidgets import QOpenGLWidget
import numpy as np
import moderngl
from config_modern import Config
from PIL import Image
import numpy as np

def load_shader_source(shader_file: str) -> str:
    """
    Lee el contenido de un archivo de shader
    """
    shader_path = Path(__file__).parent / shader_file
    try:
        with open(shader_path, 'r') as f:
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
        self.neuron_program = None
        self.block_program = None
        # VAOs
        self.display_vao = None
        self.activate_cell_vao = None
        self.neuron_vao = None
        self.block_vao = None
        self.paste_vao = None
        self.ghost_vao = None
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

        #Variables para el pegado de patrones
        self.paste_program = None
        self.paste_texture = None # Textura temporal para el patrón a pegar
        self.is_pasting = False # Bandera para indicar si se está en modo pegado
        self.paste_pos = QtCore.QPointF(0, 0) # Posición donde se pegará el patrón
        self.paste_size = (0, 0) # Tamaño del patrón a pegar
        self.setMouseTracking(True)

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
            neuron_source = load_shader_source("shaders/greenberg_h.glsl")
            block_source = load_shader_source("shaders/block_cell.glsl")
            paste_source = load_shader_source("shaders/paste.glsl")
            ghost_source = load_shader_source("shaders/ghost.glsl")
            # Crear los programas de shaders
            self.display_program = self.ctx.program(vertex_shader=vertex_source, fragment_shader=display_source)
            self.activate_cell_program = self.ctx.program(vertex_shader=vertex_source, fragment_shader=activate_cell_source)
            self.neuron_program = self.ctx.program(vertex_shader=vertex_source, fragment_shader=neuron_source)
            self.block_program = self.ctx.program(vertex_shader=vertex_source, fragment_shader=block_source)
            self.paste_program = self.ctx.program(vertex_shader=vertex_source, fragment_shader=paste_source)
            self.ghost_program = self.ctx.program(vertex_shader=vertex_source, fragment_shader=ghost_source)
            # Crear los VAOs
            vertices = np.array([-1, -1, 1, -1, 1, 1, -1, 1], dtype='f4')
            indices = np.array([0, 1, 2, 0, 2, 3], dtype='i4')

            vbo = self.ctx.buffer(vertices)
            ebo = self.ctx.buffer(indices)

            self.display_vao = self.ctx.vertex_array(self.display_program, [(vbo, '2f', 'aPos')], index_buffer=ebo)
            self.activate_cell_vao = self.ctx.vertex_array(self.activate_cell_program, [(vbo, '2f', 'aPos')], index_buffer=ebo)
            self.neuron_vao = self.ctx.vertex_array(self.neuron_program, [(vbo, '2f', 'aPos')], index_buffer=ebo)
            self.block_vao = self.ctx.vertex_array(self.block_program, [(vbo, '2f', 'aPos')], index_buffer=ebo)
            self.paste_vao = self.ctx.vertex_array(self.paste_program, [(vbo, '2f', 'aPos')], index_buffer=ebo)
            self.ghost_vao = self.ctx.vertex_array(self.ghost_program, [(vbo, '2f', 'aPos')], index_buffer=ebo)
            # Crear las texturas y FBOs
            for _ in range(2):
                tex = self.ctx.texture((self.config.grid_width, self.config.grid_height), 4, dtype='f4')
                tex.filter = (moderngl.NEAREST, moderngl.NEAREST)
                tex.repeat_x = False
                tex.repeat_y = False
                self.textures.append(tex)
                self.fbos.append(self.ctx.framebuffer(color_attachments=[tex]))
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

        if self.is_pasting and self.paste_texture is not None:
            self.ctx.enable(moderngl.BLEND)
            self.ctx.blend_func = moderngl.SRC_ALPHA, moderngl.ONE_MINUS_SRC_ALPHA

            self.ghost_program['u_zoom_level'].value = self.zoom_level
            self.ghost_program['u_view_offset'].value = (self.view_offset_x, self.view_offset_y)
            self.ghost_program['u_grid_size'].value = (self.config.grid_width, self.config.grid_height)
            self.ghost_program['u_pattern_size'].value = (self.paste_size[0], self.paste_size[1])
            self.ghost_program['u_paste_pos'].value = (self.paste_pos.x(), self.paste_pos.y())

            self.paste_texture.use(location=0)
            self.ghost_program['u_paste_pattern'].value = 0

            self.ghost_vao.render(moderngl.TRIANGLES)
            
            self.ctx.disable(moderngl.BLEND)

    def release_resources(self):

        #print("Liberando recursos de ModernGL...")
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
        if self.neuron_program: 
            self.neuron_program.release()
        if self.neuron_vao: 
            self.neuron_vao.release()
        if self.block_program: 
            self.block_program.release()
        if self.block_vao: 
            self.block_vao.release()
        if self.ctx: 
            self.ctx.release()
        #print("Recursos liberados.")

    def next_generation(self):
        self.run_neuron_shader()
        self.update()

    def restart_grid(self):
        self.run_init_shader()
        self.update()

    def activate_cell(self, x, y):
        """
        Funcion para alternar el estado de una celda en (x, y)
        0 -> 1 o 1 -> 0
        """
        self.makeCurrent()
        try:
            source_idx = self.current_texture_idx
            dest_idx = 1 - source_idx

            self.fbos[dest_idx].use()

            self.activate_cell_program['u_grid_size'].value = (self.config.grid_width, self.config.grid_height)
            self.activate_cell_program['u_flip_coord'].value = (x, y)
            self.activate_cell_program['dt'].value = 1.0 / self.config.speed

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
        self._init_random_pattern()
        #self._init_replicate_pattern()

    def _init_replicate_pattern(self):
        """
        Funcion para generar el patron replicando el paper de greenberg-hastings
        """

        self.makeCurrent()
        try:
            rgba_grid = np.zeros((self.config.grid_height, self.config.grid_width, 4), dtype='f4')
            
            # Todas las celdas en estado de reposo (u=0) y no bloqueadas (is_blocked=0)
            rgba_grid[..., 0] = 0.0 # Canal rojo para el estado (0.5 representa el estado de reposo u=0)
            rgba_grid[..., 1] = 0.0 # Canal verde para nada por ahora
            rgba_grid[..., 2] = 0.0 # Canal azul para 'is_blocked' (0.0 significa no bloqueado)
            rgba_grid[..., 3] = 1.0 # Canal alfa

            # Calcular el centro de la cuadrícula
            center_x = self.config.grid_width // 2
            center_y = self.config.grid_height // 2

            # Hay que determinar las filas para las lineas iniciales (replicar el paper)
            
            refractory_row_idx = center_y
            excited_row_idx = center_y + 1

            # Aplicar las condiciones iniciales del paper para la Figura 2:
            # u^0_{i,0} = -1 (Refractario) -> Valor mapeado 0.0
            # Esta línea comienza desde center_x y se extiende hacia la derecha (hasta grid_width-1)
            if refractory_row_idx >= 0 and refractory_row_idx < self.config.grid_height:
                rgba_grid[refractory_row_idx, center_x:, 0] = 0.5 

            # u^0_{i,1} = 1 (Excitado) -> Valor mapeado 1.0
            # Esta línea comienza desde center_x y se extiende hacia la derecha (hasta grid_width-1)
            if excited_row_idx >= 0 and excited_row_idx < self.config.grid_height:
                rgba_grid[excited_row_idx, center_x:, 0] = 1.0 
        

            dest_idx = 1 - self.current_texture_idx
            self.textures[dest_idx].write(rgba_grid.tobytes(), alignment=1)
            self.current_texture_idx = dest_idx
        finally:
            self.doneCurrent()
    
    def _init_random_pattern(self):
        """
        Funcion para generar un patron aleatorio
        """

        self.makeCurrent()
        try:
            rgba_grid = np.zeros((self.config.grid_height, self.config.grid_width, 4), dtype='f4')

            # Generar estados aleatorios entre 0, 0.5 y 1.0
            random_states = np.random.choice([0.0, 0.5, 1.0], size=(self.config.grid_height, self.config.grid_width))

            rgba_grid[..., 0] = random_states  # Canal rojo para el estado
            rgba_grid[..., 3] = 1.0 # Canal alfa

            dest_idx = 1 - self.current_texture_idx
            self.textures[dest_idx].write(rgba_grid.tobytes(), alignment=1)
            self.current_texture_idx = dest_idx

        finally:
            self.doneCurrent()
    
    def run_neuron_shader(self):
        """
        Funcion para ejecutar el shader de la neurona
        """
        self.makeCurrent()
        try:
            source_idx = self.current_texture_idx
            dest_idx = 1 - source_idx

            self.fbos[dest_idx].use()

            self.neuron_program['u_grid_size'].value = (self.config.grid_width, self.config.grid_height)

            self.textures[source_idx].use(location=0)
            self.neuron_program['u_state_texture'].value = 0
            self.neuron_program['u_threshold'].value = 2
            self.neuron_program['u_refractory_period'].value = 15

            self.neuron_vao.render(moderngl.TRIANGLES)
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

        if event.button() == QtCore.Qt.LeftButton and self.is_pasting:
            self.apply_paste()
            self.is_pasting = False
            self.setCursor(QtCore.Qt.ArrowCursor)
            if self.paste_texture:
                self.paste_texture.release()
                self.paste_texture = None
            self.update()
            return

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

        if self.is_pasting:
            grid_pos = self._pixel_to_grid(event.position())
            self.paste_pos = QtCore.QPointF(
                grid_pos.x() - self.paste_size[0] / 2,
                grid_pos.y() - self.paste_size[1] / 2
            )
            self.update()

    def mouseReleaseEvent(self, event):
        """
        Evento de soltar un boton del raton
        """
        if self.panning and (event.button() == QtCore.Qt.MiddleButton or event.button() == QtCore.Qt.RightButton):
            self.panning = False
            self.setCursor(QtCore.Qt.ArrowCursor)
        event.accept()

    def apply_paste(self):
        """
        Aplica el patrón cargado en la posición actual de pegado
        """
        self.makeCurrent()

        try:
            source_idx = self.current_texture_idx
            dest_idx = 1 - source_idx

            self.fbos[dest_idx].use()

            self.paste_program['u_grid_size'].value = (self.config.grid_width, self.config.grid_height)
            self.paste_program['u_offset'].value = (self.paste_pos.x(), self.paste_pos.y())
            self.paste_program['u_pattern_size'].value = (self.paste_size[0], self.paste_size[1])

            self.textures[source_idx].use(location=0)
            self.paste_program['u_state_texture'].value = 0

            self.paste_texture.use(location=1)
            self.paste_program['u_paste_pattern'].value = 1

            self.paste_vao.render(moderngl.TRIANGLES)

            self.current_texture_idx = dest_idx

        except Exception as e:
            print(f"Error al aplicar el patrón pegado: {e}")
            import traceback
            traceback.print_exc()
        finally:
            self.doneCurrent()

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
            texture = self.textures[self.current_texture_idx]
            raw_data = texture.read(alignment=1)
            width, height = texture.size
            components = texture.components
            #print("Guardando patrón")
            
            float_array = np.frombuffer(raw_data, dtype=np.float32) # El dtype es f32 para 4 componentes (RGBA)
            float_array = float_array.reshape((height, width, components))
            uint8_array = (float_array * 255).astype(np.uint8)
                
            image = Image.fromarray(uint8_array, 'RGBA' if components == 4 else 'RGB')

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
            image = Image.open(file_path)
            image = image.resize((self.config.grid_width, self.config.grid_height))
            image = image.convert("RGBA") 
            image = image.transpose(method=Image.Transpose.FLIP_TOP_BOTTOM) # ModernGL tiene el eje y cambiado

            uint8_array = np.array(image)
            float_array = (uint8_array / 255.0).astype(np.float32)

            data_for_texture = float_array.tobytes()

            dest_idx = 1 - self.current_texture_idx
            self.textures[dest_idx].write(data_for_texture, alignment=1)

            self.current_texture_idx = dest_idx

            print(f"Patrón importado desde {file_path}")

        except Exception as e:
            print(f"Error al importar el patrón: {e}")

        finally:
            self.doneCurrent()

            self.update()

    def start_pasting_from_file(self, file_path: str):
        """
        Inicia el modo de pegado cargando un patrón desde un archivo
        """
        self.makeCurrent()
        try:
            image = Image.open(file_path)

            data = np.array(image)
            r, g, b, a = data.T
            background_mask = (r < 50) & (g < 50) & (b < 50)

            data[..., 3][background_mask.T] = 0

            clean_image = Image.fromarray(data)
            bbox = clean_image.getbbox()
            if bbox:
                cropped_image = clean_image.crop(bbox)
            else:
                print("La imagen está vacía o no tiene contenido válido para pegar.")
                cropped_image = clean_image

            cropped_image = cropped_image.transpose(method=Image.Transpose.FLIP_TOP_BOTTOM)
            self.paste_size = cropped_image.size

            img_data = np.array(cropped_image).astype('f4') / 255.0

            if self.paste_texture:
                self.paste_texture.release()

            self.paste_texture = self.ctx.texture(self.paste_size, 4, data=img_data.tobytes(), dtype='f4')
            self.paste_texture.filter = (moderngl.NEAREST, moderngl.NEAREST)
            
            self.is_pasting = True
            self.setCursor(QtCore.Qt.CrossCursor)
            print(f"Modo pegado iniciado, dimensiones del patrón: {self.paste_size}")

        except Exception as e:
            print(f"Error al iniciar el modo pegado: {e}")

        finally:
            self.doneCurrent()