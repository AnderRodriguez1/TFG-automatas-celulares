// Shader para bloquear o desbloquear una celda en el grid

#version 330 core

out vec4 FragColor;
in vec2 TexCoords;

uniform sampler2D u_state_texture; // Textura actual del estado del grid
uniform vec2 u_grid_size; // Tamaño del grid
uniform vec2 u_block_coord; // Coordenadas de la celda a bloquear
uniform float u_block_radius; // Radio de la celda a bloquear (en coordenadas de textura)

void main(){
    vec4 current_state = texture(u_state_texture, TexCoords);
    vec2 current_grid_coord = floor(TexCoords * u_grid_size);
    float distance_to_block = distance(current_grid_coord, u_block_coord);

    if (distance_to_block <= u_block_radius){ // Si la celda está dentro del área de bloqueo
        FragColor = vec4(current_state.r, current_state.g, 1.0, current_state.a);
    }else{
        FragColor = current_state;
    }
}