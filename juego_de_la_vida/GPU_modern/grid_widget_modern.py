from _ctypes import alignment
from pathlib import Path
from PySide6 import QtWidgets, QtCore
from PySide6.QtOpenGLWidgets import QOpenGLWidget
from PySide6.QtCore import Signal
import numpy as np
import moderngl
from config_modern import Config
from PIL import Image
import numpy as np
import csv
import os
from pathlib import Path

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

    live_count_changed = Signal(int)

    def __init__(self, config: Config):
        super().__init__()
        self.config = config

        self.ctx = None # Contexto de ModernGL
        # Programas de shaders
        self.display_program = None
        self.flip_program = None
        self.life_program = None
        # VAOs
        self.init_vao = None
        self.display_vao = None
        self.flip_vao = None
        self.life_vao = None
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

        self.iteration_count = 0
        self.csv_filename = "live_cell_count_4_5_0_9_borrar.csv"

        output_dir = Path(__file__).parent / "output"
        output_dir.mkdir(exist_ok=True)
        self.csv_filename = output_dir / self.csv_filename

        try:
            with open(self.csv_filename, mode='w', newline='') as file:
                writer = csv.writer(file)
                writer.writerow(["Iteration", "Live Cell Count"])
        except Exception as e:
                print(f"Error al crear el archivo CSV: {e}")

    def initializeGL(self):
        """
        Funcion para inicializar OpenGL y los shaders
        """
        try:
            self.ctx = moderngl.create_context()
            # Cargar los shaders
            vertex_source = load_shader_source("shaders_modern/vertex.glsl")
            display_source = load_shader_source("shaders_modern/display.glsl")
            flip_source = load_shader_source("shaders_modern/flip.glsl")
            life_source = load_shader_source("shaders_modern/life_game.glsl")
            # Crear los programas de shaders
            self.display_program = self.ctx.program(vertex_shader=vertex_source, fragment_shader=display_source)
            self.flip_program = self.ctx.program(vertex_shader=vertex_source, fragment_shader=flip_source)
            self.life_program = self.ctx.program(vertex_shader=vertex_source, fragment_shader=life_source)
            # Crear los VAOs
            vertices = np.array([-1, -1, 1, -1, 1, 1, -1, 1], dtype='f4')
            indices = np.array([0, 1, 2, 0, 2, 3], dtype='i4')

            vbo = self.ctx.buffer(vertices)
            ebo = self.ctx.buffer(indices)

            self.display_vao = self.ctx.vertex_array(self.display_program, [(vbo, '2f', 'aPos')], index_buffer=ebo)
            self.flip_vao = self.ctx.vertex_array(self.flip_program, [(vbo, '2f', 'aPos')], index_buffer=ebo)
            self.life_vao = self.ctx.vertex_array(self.life_program, [(vbo, '2f', 'aPos')], index_buffer=ebo)
            # Crear las texturas y FBOs
            for _ in range(2):
                tex = self.ctx.texture((self.config.grid_width, self.config.grid_height), 4, dtype='f4')
                tex.filter = (moderngl.NEAREST, moderngl.NEAREST)
                self.textures.append(tex)
                self.fbos.append(self.ctx.framebuffer(color_attachments=[tex]))
            QtCore.QTimer.singleShot(0, self.perform_initial_render)
        except Exception as e:
            print(f"Error durante la inicialización de OpenGL: {e}")
            self.window().close()

    def perform_initial_render(self):
        self.restart_grid()
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

    def release_resources(self):

        #print("Liberando recursos de ModernGL...")
        for fbo in self.fbos: 
            fbo.release()
        for texture in self.textures: 
            texture.release()
        if self.display_vao: 
            self.display_vao.release()
        if self.flip_vao: 
            self.flip_vao.release()
        if self.display_program: 
            self.display_program.release()
        if self.flip_program: 
            self.flip_program.release()
        if self.life_program: 
            self.life_program.release()
        if self.life_vao: 
            self.life_vao.release()
        if self.ctx: 
            self.ctx.release()
        #print("Recursos liberados.")

    def next_generation(self):
        self.run_life_shader()
        self.update()

    def restart_grid(self):
        self.run_init_shader()
        self.iteration_count = 0
        initial_data = self.textures[self.current_texture_idx].read(alignment=1)
        float_array = np.frombuffer(initial_data, dtype=np.float32)
        initial_live_count = int(np.sum(float_array[::4] > 0.5))  # Contar células vivas en el canal R
        self._write_count_to_csv(initial_live_count)
        self.live_count_changed.emit(initial_live_count)
        self.update()

    def flip_cell(self, x, y):
        """
        Funcion para alternar el estado de una celda en (x, y)
        0 -> 1 o 1 -> 0
        """
        self.makeCurrent()
        try:
            source_idx = self.current_texture_idx
            dest_idx = 1 - source_idx

            self.fbos[dest_idx].use()

            self.flip_program['u_grid_size'].value = (self.config.grid_width, self.config.grid_height)
            self.flip_program['u_flip_coord'].value = (x, y)

            self.textures[source_idx].use(location=0)
            self.flip_program['u_state_texture'].value = 0

            self.flip_vao.render(moderngl.TRIANGLES)
            self.current_texture_idx = dest_idx
        finally:
            self.doneCurrent()
        self.update()

    def run_init_shader(self):
        """
        Funcion para ejecutar el shader de inicializacion
        """
        self.makeCurrent()
        try:
            dest_idx = 1 - self.current_texture_idx
            tex = self.textures[dest_idx] if dest_idx < len(self.textures) else None
            # Inicializar una matriz con 1 y 0 aleatorios segun la densidad
            initial_state = np.random.choice([0.0, 1.0], size=(self.config.grid_height, self.config.grid_width), 
                            p=[1 - self.config.density, self.config.density]).astype('f4')

            # Generar la textura RGBA a partir del estado inicial
            rgba_grid = np.zeros((self.config.grid_height, self.config.grid_width, 4), dtype='f4')
            rgba_grid[..., 0] = initial_state  # R
            rgba_grid[..., 1] = initial_state  # G
            rgba_grid[..., 2] = initial_state  # B
            rgba_grid[..., 3] = 1.0  # A

            # Escribir los datos de la textura en bytes
            self.textures[dest_idx].write(rgba_grid.tobytes(), alignment=1)

            self.current_texture_idx = dest_idx
        finally:
            self.doneCurrent()

    def run_life_shader(self):
        """
        Funcion para ejecutar el shader de la vida
        """
        self.makeCurrent()
        try:
            source_idx = self.current_texture_idx
            dest_idx = 1 - source_idx

            self.fbos[dest_idx].use()

            self.life_program['u_grid_size'].value = (self.config.grid_width, self.config.grid_height)

            self.textures[source_idx].use(location=0)
            self.life_program['u_state_texture'].value = 0

            self.life_vao.render(moderngl.TRIANGLES)

            self.ctx.finish()

            dest_texture = self.textures[dest_idx]
            raw_data = dest_texture.read(alignment=1)
            float_array = np.frombuffer(raw_data, dtype=np.float32)
            live_count = int(np.sum(float_array[::4] > 0.5))  # Contar células vivas en el canal R
            self.iteration_count += 1
            self._write_count_to_csv(live_count)
            self.live_count_changed.emit(live_count)

            self.current_texture_idx = dest_idx

        finally:
            self.doneCurrent()

    def _write_count_to_csv(self, count: int):
        with open(self.csv_filename, mode='a', newline='') as file:
            writer = csv.writer(file)
            writer.writerow([self.iteration_count, count])

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
                self.flip_cell(grid_x, grid_y)
        elif event.button() == QtCore.Qt.MiddleButton or event.button() == QtCore.Qt.RightButton:
            self.panning = True
            self.last_pan_pos = event.position()
            self.setCursor(QtCore.Qt.ClosedHandCursor)
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