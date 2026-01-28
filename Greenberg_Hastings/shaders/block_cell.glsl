// Shader para bloquear o desbloquear una celda en el grid

#version 330 core

out vec4 FragColor;
in vec2 TexCoords;

uniform sampler2D u_state_texture; // Textura actual del estado del grid
uniform vec2 u_grid_size; // Tamaño del grid
uniform vec2 u_block_coord; // Coordenadas de la celda a bloquear

void main(){
    vec4 current_state = texture(u_state_texture, TexCoords);
    vec2 current_grid_coord = floor(TexCoords * u_grid_size);

    if (int(current_grid_coord.x) == int(u_block_coord.x) && int(current_grid_coord.y) == int(u_block_coord.y)){
        // Si la celda coincide con la que se ha pulsado
        if (current_state.b <= 0.5){
            // Celda no bloqueada, bloquearla 
            FragColor = vec4(current_state.r, current_state.g, 1.0, 1.0);
        }else{
            // Si la celda esta bloqueada, desbloquearla
            FragColor = vec4(current_state.r, current_state.g, 0.0, 1.0);
        }
    }else{
        FragColor = current_state;
    }
}