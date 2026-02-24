// En shaders/activate_cell.glsl

#version 330 core
out vec4 FragColor;
in vec2 TexCoords;

uniform sampler2D u_state_texture;
uniform vec2 u_grid_size;
uniform vec2 u_flip_coord; // El nombre del uniform no es ideal, pero funciona
uniform float u_radius; // Radio de activación en coordenadas de celda

// Valores del "more stable phase" del paper
const float U_SPOT = 1.5;
const float V_SPOT = 0.0;

void main(){
    vec4 current_state = texture(u_state_texture, TexCoords);
    vec2 current_grid_coord = floor(TexCoords * u_grid_size);
    float distance_to_flip = distance(current_grid_coord, u_flip_coord);

    if (distance_to_flip <= u_radius){
        // Establecemos la célula al estado "more stable phase"
        FragColor = vec4(U_SPOT, V_SPOT, 0.0, 1.0);
    } else {
        // Dejamos las demás células como están
        FragColor = current_state;
    }
}