import sys
from pathlib import Path
from PySide6 import QtWidgets, QtCore, QtGui
from PySide6.QtOpenGLWidgets import QOpenGLWidget
import numpy as np
from OpenGL.GL import *
import ctypes
from config import GRID_WIDTH, GRID_HEIGHT

def load_shader_source(shader_file: str) -> str:
    """
    Lee el contenido de un archivo de shader.
    """
    shader_path = Path(__file__).parent / shader_file
    try:
        with open(shader_path, 'r') as f:
            return f.read()
    except FileNotFoundError:
        print(f"Error: No se pudo encontrar el archivo de shader: {shader_path}")
        # En una aplicación real, podrías lanzar una excepción más específica.
        return ""

class GridWidget(QOpenGLWidget):
    def __init__(self):
        super().__init__()
        self.init_program = None
        self.display_program = None
        self.flip_program = None
        self.vao = None
        
        self.fbos = [None, None]
        self.textures = [None, None]
        self.current_texture_idx = 0

        self.zoom_level = 1.0
        self.view_offset_x = GRID_WIDTH / 2.0
        self.view_offset_y = GRID_HEIGHT / 2.0
        self.panning = False
        self.last_pan_pos = QtCore.QPointF()
        
        # ### PASO 2.1: Añadir un flag de inicialización ###
        self._is_initialized = False

    def initializeGL(self):
        vertex_source = load_shader_source("shaders/vertex.glsl")
        init_source = load_shader_source("shaders/init.glsl")
        display_source = load_shader_source("shaders/display.glsl")
        flip_source = load_shader_source("shaders/flip.glsl")

        self.init_program = self.create_shader_program(vertex_source, init_source)
        self.display_program = self.create_shader_program(vertex_source, display_source)
        self.flip_program = self.create_shader_program(vertex_source, flip_source)

        self.vao = self.create_fullscreen_quad()

        self.textures[0], self.fbos[0] = self.create_fbo_texture_pair(GRID_WIDTH, GRID_HEIGHT)
        self.textures[1], self.fbos[1] = self.create_fbo_texture_pair(GRID_WIDTH, GRID_HEIGHT)

        # Usar un QTimer para retrasar la renderización inicial
        # hasta que el contexto esté completamente listo
        QtCore.QTimer.singleShot(0, self.perform_initial_render)

    def perform_initial_render(self):
        """
        Ejecuta el shader de inicialización y prepara el primer frame.
        """
        self.run_init_shader()  # Ejecuta el shader de inicialización (celulas en estado aleatorio)
        self._is_initialized = True
        self.update()  # Solicita la primera llamada a paintGL

    def paintGL(self):
        """
        Renderiza el estado actual de la simulación en pantalla
        Usa el DISPLAY_SHADER para mostrar la textura actual
        con el nivel de zoom y el offset de vista actuales.
        glViewport: pasa de coordenadas normalizadas (-1 a 1) a coordenadas
                    de pixel (0 a width, 0 a height)
        glClear: limpia la pantalla
        """

        # Si aún no se ha generado el primer estado, no hacer nada.
        if not self._is_initialized:
            return
        
        dpr = self.devicePixelRatio() # Device Pixel Ratio para pantallas HiDPI
        glViewport(0, 0, int(self.width() * dpr), int(self.height() * dpr)) 
        glClear(GL_COLOR_BUFFER_BIT)

        glUseProgram(self.display_program)
        
        glActiveTexture(GL_TEXTURE0)
        glBindTexture(GL_TEXTURE_2D, self.textures[self.current_texture_idx])
        glUniform1i(glGetUniformLocation(self.display_program, "u_state_texture"), 0)
        
        glUniform1f(glGetUniformLocation(self.display_program, "u_zoom_level"), self.zoom_level)
        glUniform2f(glGetUniformLocation(self.display_program, "u_view_offset"), self.view_offset_x, self.view_offset_y)
        glUniform2f(glGetUniformLocation(self.display_program, "u_grid_size"), GRID_WIDTH, GRID_HEIGHT)

        glBindVertexArray(self.vao)
        glDrawElements(GL_TRIANGLES, 6, GL_UNSIGNED_INT, None)

    def next_generation(self):
        """
        Funcion encargada de avanzar a la siguiente generacion
        Ahora mismo es aleatorio, pero en el futuro será el juego de
        la vida
        """
        self.run_init_shader()
        self.update()

    def flip_cell(self, x, y):
        """
        Alterna el estado de una celda en las coordenadas (x, y)
        usando el FLIP_SHADER.
        """

        self.makeCurrent()
        try:
            source_idx = self.current_texture_idx
            dest_idx = 1 - source_idx

            glBindFramebuffer(GL_FRAMEBUFFER, self.fbos[dest_idx])

            glViewport(0, 0, GRID_WIDTH, GRID_HEIGHT)

            glUseProgram(self.flip_program)

            glActiveTexture(GL_TEXTURE0)
            glBindTexture(GL_TEXTURE_2D, self.textures[source_idx])

            glUniform1i(glGetUniformLocation(self.flip_program, "u_state_texture"), 0)
            glUniform2f(glGetUniformLocation(self.flip_program, "u_grid_size"), GRID_WIDTH, GRID_HEIGHT)
            glUniform2f(glGetUniformLocation(self.flip_program, "u_flip_coord"), x, y)

            glBindVertexArray(self.vao)
            
            glDrawElements(GL_TRIANGLES, 6, GL_UNSIGNED_INT, None)
            self.current_texture_idx = dest_idx
        finally:
            self.doneCurrent()
        self.update()

    def run_init_shader(self):
        """
        Modifica el estado actual de la simulación usando el INIT_SHADER
        para generar un nuevo estado aleatorio, de cara a añadir
        el juego de la vida, habría que cambiar el modo de 
        actualización del estado.
        """
        self.makeCurrent()
        try:
            dest_idx = 1 - self.current_texture_idx

            glBindFramebuffer(GL_FRAMEBUFFER, self.fbos[dest_idx])
            glViewport(0, 0, GRID_WIDTH, GRID_HEIGHT)
            glUseProgram(self.init_program)

            glUniform1f(glGetUniformLocation(self.init_program, "u_seed"), np.random.random())
            glBindVertexArray(self.vao)

            glDrawElements(GL_TRIANGLES, 6, GL_UNSIGNED_INT, None)

            self.current_texture_idx = dest_idx
        finally:
            self.doneCurrent()
            
    def create_fbo_texture_pair(self, width, height):
        """
        FBO: Framebuffer Object
        glGenTextures: genera un identificador de textura
        glBindTexture: enlaza la textura a un target (GL_TEXTURE_2D)
        glTexParameteri: configura parametros de la textura
            -GL_NEAREST: si se intenta leer una coordenada que no
                         es exactamente un pixel, se toma el más
                         cercano (no se interpola). Para interpolar
                         se puede usar GL_LINEAR.
            -GL_CLAMP_TO_EDGE: si se intenta leer fuera de los limites
                               de la textura, se devuelve el color del
                               borde (en lugar de repetir la textura)
        glTexImage2D: crea la textura en la GPU (se reserva memoria)
            -GL_RGBA32F: formato de la textura (RGBA, 32 bits por canal)
            -El none significa que no se suben datos desde la cpu, se 
             llenara la memoria con  el INIT_SHADER
        glGenFramebuffers: genera un identificador de framebuffer
        glBindFramebuffer: enlaza el framebuffer a un target
        glFramebufferTexture2D: le dice al FBO cual será su textura, 
                                todo lo que se dibuje mientras este
                                FBO este activo, irá a esa textura
        glCheckFramebufferStatus: verifica que el FBO esté completo
        """

        texture = glGenTextures(1)
        glBindTexture(GL_TEXTURE_2D, texture)

        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_NEAREST)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_NEAREST)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_S, GL_CLAMP_TO_EDGE)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_T, GL_CLAMP_TO_EDGE)
        # Usar un formato de tamaño explícito es una mejor práctica
        glTexImage2D(GL_TEXTURE_2D, 0, GL_RGBA32F, width, height, 0, GL_RGBA, GL_FLOAT, None)

        fbo = glGenFramebuffers(1)
        glBindFramebuffer(GL_FRAMEBUFFER, fbo)
        glFramebufferTexture2D(GL_FRAMEBUFFER, GL_COLOR_ATTACHMENT0, GL_TEXTURE_2D, texture, 0)
        
        if glCheckFramebufferStatus(GL_FRAMEBUFFER) != GL_FRAMEBUFFER_COMPLETE:
            raise Exception("Framebuffer no está completo")

        glBindFramebuffer(GL_FRAMEBUFFER, 0)
        return texture, fbo

    def wheelEvent(self, event):
        """
        Evento de la rueda del raton para hacer zoom
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
        Evento de click del raton, varias opciones:
            -Click izquierdo: alterna el estado de la celda
            -Click derecho o rueda: inicia el modo de arrastre
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
        Evento de movimiento del raton para arrastrar la vista
        """
        if self.panning:
            delta = event.position() - self.last_pan_pos

            self.last_pan_pos = event.position()

            grid_units_visible_x = GRID_WIDTH / self.zoom_level
            grid_units_visible_y = GRID_HEIGHT / self.zoom_level

            delta_grid_x = (delta.x()) * grid_units_visible_x / (self.width())
            delta_grid_y = (delta.y()) * grid_units_visible_y / (self.height())

            self.view_offset_x -= delta_grid_x
            self.view_offset_y += delta_grid_y

            self.update()

    def mouseReleaseEvent(self, event):
        """
        Evento de soltar el boton del raton para terminar el arrastre
        """
        if self.panning and (event.button() == QtCore.Qt.MiddleButton or event.button() == QtCore.Qt.RightButton):
            self.panning = False
            self.setCursor(QtCore.Qt.ArrowCursor)

        event.accept()

    def _pixel_to_grid(self, pos):
        """
        Funcion para convertir coordenadas de pixel
        a coordenadas de la cuadricula
        """
        dpr = self.devicePixelRatio()
        pixel_x = pos.x() * dpr
        pixel_y = pos.y() * dpr

        norm_x = pixel_x / (self.width() * dpr) - 0.5
        norm_y = (self.height() * dpr - pixel_y) / (self.height() * dpr) - 0.5

        grid_units_visible_x = GRID_WIDTH / self.zoom_level
        grid_units_visible_y = GRID_HEIGHT / self.zoom_level

        grid_x = self.view_offset_x + norm_x * grid_units_visible_x
        grid_y = self.view_offset_y + norm_y * grid_units_visible_y

        return QtCore.QPointF(grid_x, grid_y)
    
    def create_fullscreen_quad(self):
        """
        Funcion para crear un rectangulo que cubra toda la pantalla
        VBO: Vertex Buffer Object
        EBO: Element Buffer Object
        VAO: Vertex Array Object
        glGenBuffers: genera un buffer en la gpu
        glBindBuffer: enlaza el buffer a un target (GL_ARRAY_BUFFER 
                      o GL_ELEMENT)
        glBufferData: carga los datos en el buffer
        glGenVertexArrays: genera un array de vertices en la gpu
        glBindVertexArray: enlaza el array de vertices
            -Estas dos ultimas funciones graban:
                *Que VBO usar para los datos de los vertices
                *Que EBO usar para los indices
                *Como estan estructurados los datos dentro del VBO
                (esto ultimo se hace con glVertexAttribPointer)
        glVertexAttribPointer: le dice a la gpu como interpretar
                               los datos del VBO:
                               -0 -> location en el shader
                               -2 -> numero de componentes en cada vertice
                               -GL_FLOAT -> tipo de dato (float)
                               -GL_FALSE -> no normalizar los datos

        """
        # Vertices de un cuadrado
        vertices = np.array([-1, -1, 1, -1, 1, 1, -1, 1], dtype=np.float32) 

        # Los indices definen dos triangulos que forman el rectangulo
        indices = np.array([0, 1, 2, 0, 2, 3], dtype=np.uint32)

        vao = glGenVertexArrays(1)
        glBindVertexArray(vao)

        vbo = glGenBuffers(1)
        glBindBuffer(GL_ARRAY_BUFFER, vbo)

        glBufferData(GL_ARRAY_BUFFER, vertices.nbytes, vertices, GL_STATIC_DRAW)
        ebo = glGenBuffers(1)

        glBindBuffer(GL_ELEMENT_ARRAY_BUFFER, ebo)
        glBufferData(GL_ELEMENT_ARRAY_BUFFER, indices.nbytes, indices, GL_STATIC_DRAW)

        glVertexAttribPointer(0, 2, GL_FLOAT, GL_FALSE, 2 * vertices.itemsize, ctypes.c_void_p(0))
        glEnableVertexAttribArray(0)
        glBindVertexArray(0)
        return vao
    
    def create_shader_program(self, vertex_source, fragment_source):
        """
        Funcion para crear el programa de shader
        glCreateProgram: crea un programa de shader vacio en la gpu
        glAttachShader: adjunta los shaders compilados al programa
        glLinkProgram: enlaza el programa de shader (verifica que 
                       las salidas (out) de un shader coincidan 
                       con las entradas (in) del siguiente shader)
        """
        vs = self.compile_shader(GL_VERTEX_SHADER, vertex_source)
        fs = self.compile_shader(GL_FRAGMENT_SHADER, fragment_source)

        if not vs or not fs: 
            return None
        
        program = glCreateProgram()

        glAttachShader(program, vs)
        glAttachShader(program, fs)
        glLinkProgram(program)

        if not glGetProgramiv(program, GL_LINK_STATUS):
            error = glGetProgramInfoLog(program).decode()
            raise RuntimeError(f"Error al enlazar el programa de shader: {error}")
        
        glDeleteShader(vs)
        glDeleteShader(fs)

        return program
    
    def compile_shader(self, shader_type, shader_source):
        """
        Funcion para compilar el shader
        glCreateShader: crea un objeto shader vacio en la gpu
        glShaderSource: carga el codigo fuente del shader en el objeto shader
        glCompileShader: compila el shader
        glGetShaderiv: obtiene el estado de compilacion del shader
        glGetShaderInfoLog: obtiene el log de errores si la compilacion falla
        """
        shader = glCreateShader(shader_type)

        glShaderSource(shader, shader_source)

        glCompileShader(shader)

        if not glGetShaderiv(shader, GL_COMPILE_STATUS):
            sys.stderr.write(f"Error compiling shader: {glGetShaderInfoLog(shader).decode()}\n")
            return None
        
        return shader