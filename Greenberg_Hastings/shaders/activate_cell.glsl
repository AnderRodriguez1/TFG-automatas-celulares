#version 330 core
out vec4 FragColor;
in vec2 TexCoords;

uniform sampler2D u_state_texture;
uniform vec2 u_grid_size;
uniform vec2 u_flip_coord;
uniform float dt;

void main(){
    vec4 current_state = texture(u_state_texture, TexCoords);
    vec2 current_grid_coord = floor(TexCoords * u_grid_size);

    if (int(current_grid_coord.x) == int(u_flip_coord.x) && int(current_grid_coord.y) == int(u_flip_coord.y)){
        if (current_state.g <= 0.0){
            FragColor = vec4(1.0, dt, 0.0, 1.0);
        }else{
            FragColor = vec4(0.0, 0.0, 0.0, 1.0);
        }
    } else {
        FragColor = current_state;
    }
}

