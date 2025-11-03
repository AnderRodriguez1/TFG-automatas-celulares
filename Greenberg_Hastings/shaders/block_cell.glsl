#version 330 core

out vec4 FragColor;
in vec2 TexCoords;

uniform sampler2D u_state_texture;
uniform vec2 u_grid_size;
uniform vec2 u_block_coord;

void main(){
    vec4 current_state = texture(u_state_texture, TexCoords);
    vec2 current_grid_coord = floor(TexCoords * u_grid_size);
    vec4 block_color = vec4(0.0, 0.0, 1.0, 0.0); // Canal azul indica bloqueado

    if (int(current_grid_coord.x) == int(u_block_coord.x) && int(current_grid_coord.y) == int(u_block_coord.y)){
        if (current_state.b <= 0.5){
            FragColor = vec4(current_state.r, current_state.g, 1.0, 1.0);
        }else{
            FragColor = vec4(current_state.r, current_state.g, 0.0, 1.0);
        }
    } else {
        FragColor = current_state;
    }
}