from pathlib import Path
from PySide6 import QtWidgets, QtCore
from PySide6.QtOpenGLWidgets import QOpenGLWidget
import numpy as np
import moderngl
from config_modern import GRID_WIDTH, GRID_HEIGHT

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
    def __init__(self):
        super().__init__()
        self.ctx = None # Contexto de ModernGL
        # Programas de shaders
        self.init_program = None
        self.display_program = None
        self.flip_program = None
        # VAOs
        self.init_vao = None
        self.display_vao = None
        self.flip_vao = None
        # FBOs y Texturas
        self.fbos = []
        self.textures = []
        self.current_texture_idx = 0
        # Variables para zoom y paneo
        self.zoom_level = 1.0
        self.view_offset_x = GRID_WIDTH / 2.0
        self.view_offset_y = GRID_HEIGHT / 2.0
        self.panning = False
        self.last_pan_pos = QtCore.QPointF()

        self._is_initialized = False

    def initializeGL(self):
        """
        Funcion para inicializar OpenGL y los shaders
        """
        try:
            self.ctx = moderngl.create_context()
            
            vertex_source = load_shader_source("shaders_modern/vertex.glsl")
            init_source = load_shader_source("shaders_modern/init.glsl")
            display_source = load_shader_source("shaders_modern/display.glsl")
            flip_source = load_shader_source("shaders_modern/flip.glsl")

            self.init_program = self.ctx.program(vertex_shader=vertex_source, fragment_shader=init_source)
            self.display_program = self.ctx.program(vertex_shader=vertex_source, fragment_shader=display_source)
            self.flip_program = self.ctx.program(vertex_shader=vertex_source, fragment_shader=flip_source)

            vertices = np.array([-1, -1, 1, -1, 1, 1, -1, 1], dtype='f4')
            indices = np.array([0, 1, 2, 0, 2, 3], dtype='i4')

            vbo = self.ctx.buffer(vertices)
            ebo = self.ctx.buffer(indices)

            self.init_vao = self.ctx.vertex_array(self.init_program, [(vbo, '2f', 'aPos')], index_buffer=ebo)
            self.display_vao = self.ctx.vertex_array(self.display_program, [(vbo, '2f', 'aPos')], index_buffer=ebo)
            self.flip_vao = self.ctx.vertex_array(self.flip_program, [(vbo, '2f', 'aPos')], index_buffer=ebo)

            for _ in range(2):
                tex = self.ctx.texture((GRID_WIDTH, GRID_HEIGHT), 4, dtype='f4')
                tex.filter = (moderngl.NEAREST, moderngl.NEAREST)
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
        self.display_program['u_grid_size'].value = (GRID_WIDTH, GRID_HEIGHT)

        self.textures[self.current_texture_idx].use(location=0)
        self.display_program['u_state_texture'].value = 0
        self.display_vao.render(moderngl.TRIANGLES)

    def release_resources(self):

        print("Liberando recursos de ModernGL...")
        for fbo in self.fbos: 
            fbo.release()
        for texture in self.textures: 
            texture.release()
        if self.init_vao: 
            self.init_vao.release()
        if self.display_vao: 
            self.display_vao.release()
        if self.flip_vao: 
            self.flip_vao.release()
        if self.init_program: 
            self.init_program.release()
        if self.display_program: 
            self.display_program.release()
        if self.flip_program: 
            self.flip_program.release()
        if self.ctx: 
            self.ctx.release()
        print("Recursos liberados.")

    def next_generation(self):
        self.run_init_shader()
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

            self.flip_program['u_grid_size'].value = (GRID_WIDTH, GRID_HEIGHT)
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
            self.fbos[dest_idx].use()

            self.init_program['u_seed'].value = np.random.random()

            self.init_vao.render(moderngl.TRIANGLES)

            self.current_texture_idx = dest_idx
        finally:
            self.doneCurrent()

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

            if 0 <= grid_x < GRID_WIDTH and 0 <= grid_y < GRID_HEIGHT: 
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

            grid_units_visible_x = GRID_WIDTH / self.zoom_level
            grid_units_visible_y = GRID_HEIGHT / self.zoom_level

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

        grid_units_visible_x = GRID_WIDTH / self.zoom_level
        grid_units_visible_y = GRID_HEIGHT / self.zoom_level

        grid_x = self.view_offset_x + norm_x * grid_units_visible_x
        grid_y = self.view_offset_y + norm_y * grid_units_visible_y
        
        return QtCore.QPointF(grid_x, grid_y)