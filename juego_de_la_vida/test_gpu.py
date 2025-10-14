# ... (Importaciones y Shaders se mantienen igual, no los pego por brevedad) ...
import sys
from PySide6 import QtWidgets, QtCore, QtGui
from PySide6.QtOpenGLWidgets import QOpenGLWidget
import numpy as np
from OpenGL.GL import *
import ctypes

# ... SHADERS AQUÍ ...
VERTEX_SHADER = """
#version 330 core
layout (location = 0) in vec2 aPos;
out vec2 TexCoords;
void main()
{
    gl_Position = vec4(aPos.x, aPos.y, 0.0, 1.0);
    TexCoords = (aPos + 1.0) / 2.0;
}
"""

INIT_SHADER = """
#version 330 core
out vec4 FragColor;
uniform float u_seed;

float random(vec2 st) {
    return fract(sin(dot(st.xy, vec2(12.9898, 78.233))) * 43758.5453123);
}

void main()
{
    vec2 grid_coord = floor(gl_FragCoord.xy); 
    float r = random(grid_coord + u_seed);
    float state = step(0.5, r);
    FragColor = vec4(vec3(state), 1.0);
}
"""

DISPLAY_SHADER = """
#version 330 core
out vec4 FragColor;
in vec2 TexCoords;

uniform sampler2D u_state_texture; 
uniform float u_zoom_level; 
uniform vec2 u_view_offset;
uniform vec2 u_grid_size;

void main()
{
    vec2 sample_coord = (TexCoords - 0.5) / u_zoom_level + (u_view_offset / u_grid_size);

    if (sample_coord.x < 0.0 || sample_coord.x > 1.0 || sample_coord.y < 0.0 || sample_coord.y > 1.0) {
        FragColor = vec4(0.1, 0.1, 0.1, 1.0); // Color de fondo
        return;
    }

    vec3 final_color = texture(u_state_texture, sample_coord).rgb;
    
    vec2 grid_coord_float = sample_coord * u_grid_size;
    vec2 inside_cell_coord = fract(grid_coord_float);
    float border_thickness = 0.05;
    bool is_border = inside_cell_coord.x < border_thickness || inside_cell_coord.x > (1.0 - border_thickness) ||
                     inside_cell_coord.y < border_thickness || inside_cell_coord.y > (1.0 - border_thickness);

    if (is_border && u_zoom_level > 0.6) {
        final_color = vec3(0.2);
    }
    
    FragColor = vec4(final_color, 1.0);
}
"""

FLIP_SHADER = """
#version 330 core
out vec4 FragColor;
in vec2 TexCoords;

uniform sampler2D u_state_texture;
uniform vec2 u_grid_size;
uniform vec2 u_flip_coord;

void main(){
    vec4 current_state = texture(u_state_texture, TexCoords);
    vec2 current_grid_coord = floor(TexCoords * u_grid_size);

    if (int(current_grid_coord.x) == int(u_flip_coord.x) && int(current_grid_coord.y) == int(u_flip_coord.y)){
        FragColor = vec4(1.0 - current_state.rgb, 1.0);
    } else {
        FragColor = current_state;
    }
}
"""


GRID_WIDTH = 100
GRID_HEIGHT = 100

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
        self.init_program = self.create_shader_program(VERTEX_SHADER, INIT_SHADER)
        self.display_program = self.create_shader_program(VERTEX_SHADER, DISPLAY_SHADER)
        self.flip_program = self.create_shader_program(VERTEX_SHADER, FLIP_SHADER)

        self.vao = self.create_fullscreen_quad()

        self.textures[0], self.fbos[0] = self.create_fbo_texture_pair(GRID_WIDTH, GRID_HEIGHT)
        self.textures[1], self.fbos[1] = self.create_fbo_texture_pair(GRID_WIDTH, GRID_HEIGHT)

        # ### PASO 2.2: Retrasar la renderización inicial ###
        # No llamar a run_init_shader() directamente. En su lugar, programarlo para
        # que se ejecute una vez que el bucle de eventos de Qt se haya iniciado.
        QtCore.QTimer.singleShot(0, self.perform_initial_render)

    # ### PASO 2.3: Nuevo método para la renderización inicial ###
    def perform_initial_render(self):
        """Ejecuta el shader de inicialización y prepara el primer frame."""
        self.run_init_shader()  # Esta función ya gestiona el contexto correctamente
        self._is_initialized = True
        self.update()  # Solicita la primera llamada a paintGL

    def paintGL(self):
        # Si aún no se ha generado el primer estado, no hacer nada.
        if not self._is_initialized:
            return

        # ### PASO 1: LA CORRECCIÓN MÁS IMPORTANTE ###
        # No llames a glBindFramebuffer(GL_FRAMEBUFFER, 0). Es innecesario y peligroso.
        # QOpenGLWidget YA prepara el framebuffer correcto para ti antes de llamar a esta función.
        # Esta línea era la que reportaba el error, pero no la que lo causaba.
        
        dpr = self.devicePixelRatio()
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
        self.run_init_shader()
        self.update()

    def flip_cell(self, x, y):
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

    # ... El resto de la clase (eventos de ratón y helpers) no necesita cambios ...
    def wheelEvent(self, event):
        mouse_pos = event.position()
        grid_pos_before_zoom = self._pixel_to_grid(mouse_pos)
        zoom_factor = 1.15
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
        if event.button() == QtCore.Qt.LeftButton:
            grid_pos = self._pixel_to_grid(event.position())
            grid_x, grid_y = int(grid_pos.x()), int(grid_pos.y())
            if 0 <= grid_x < GRID_WIDTH and 0 <= grid_y < GRID_HEIGHT:
                self.flip_cell(grid_x, grid_y)
        elif event.button() == QtCore.Qt.MiddleButton or event.button() == QtCore.Qt.RightButton:
            self.panning = True
            self.last_pan_pos = event.position()
            self.setCursor(QtCore.Qt.ClosedHandCursor)
        event.accept()
    def mouseMoveEvent(self, event):
        if self.panning:
            delta = event.position() - self.last_pan_pos
            self.last_pan_pos = event.position()
            dpr = self.devicePixelRatio()
            grid_units_visible_x = GRID_WIDTH / self.zoom_level
            grid_units_visible_y = GRID_HEIGHT / self.zoom_level
            delta_grid_x = (delta.x()) * grid_units_visible_x / (self.width())
            delta_grid_y = (delta.y()) * grid_units_visible_y / (self.height())
            self.view_offset_x -= delta_grid_x
            self.view_offset_y += delta_grid_y
            self.update()
    def mouseReleaseEvent(self, event):
        if self.panning and (event.button() == QtCore.Qt.MiddleButton or event.button() == QtCore.Qt.RightButton):
            self.panning = False
            self.setCursor(QtCore.Qt.ArrowCursor)
        event.accept()
    def _pixel_to_grid(self, pos):
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
        vertices = np.array([-1, -1, 1, -1, 1, 1, -1, 1], dtype=np.float32)
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
        shader = glCreateShader(shader_type)
        glShaderSource(shader, shader_source)
        glCompileShader(shader)
        if not glGetShaderiv(shader, GL_COMPILE_STATUS):
            sys.stderr.write(f"Error compiling shader: {glGetShaderInfoLog(shader).decode()}\n")
            return None
        return shader

# El resto del script (MainWindow y el main) se queda exactamente igual.
class MainWindow(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Juego de la Vida")
        container = QtWidgets.QWidget()
        self.setCentralWidget(container)
        self.grid_widget = GridWidget()
        self.next_button = QtWidgets.QPushButton("Siguiente Generación")
        self.next_button.clicked.connect(self.grid_widget.next_generation)
        self.timer_button = QtWidgets.QPushButton("Iniciar animación")
        self.timer_button.setCheckable(True)
        self.timer_button.clicked.connect(self.toggle_timer)
        layout = QtWidgets.QVBoxLayout(container)
        layout.addWidget(self.grid_widget)
        layout.addWidget(self.next_button)
        layout.addWidget(self.timer_button)
        self.timer = QtCore.QTimer()
        self.timer.setInterval(500)
        self.timer.timeout.connect(self.grid_widget.next_generation)
    @QtCore.Slot()
    def toggle_timer(self):
        if self.timer_button.isChecked():
            self.timer.start()
            self.timer_button.setText("Detener animación")
        else:
            self.timer.stop()
            self.timer_button.setText("Iniciar animación")

if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    window = MainWindow()
    window.resize(800, 600)
    window.show()
    sys.exit(app.exec())