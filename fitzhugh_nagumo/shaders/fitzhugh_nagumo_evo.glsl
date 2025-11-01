#version 330 core

out vec4 FragColor;
in vec2 TexCoords;

uniform sampler2D u_state_texture;
uniform vec2 u_grid_size;


void main(){
    vec2 pixel_step = 1.0 / u_grid_size;
    
    float current_state = texture(u_state_texture, TexCoords).r;

    int live_neighbors = 0;

    for (int i = -1; i<= 1; i++){
        for (int j = -1; j<= 1; j++){
            if (i == 0 && j == 0){
                continue;
            }
            vec2 neighbor_coords = TexCoords + vec2(i, j) * pixel_step;
            
            if (texture(u_state_texture, neighbor_coords).r > 0.5){
                live_neighbors += 1;
            }

        }
    }
    float new_state = 0.0;
    if (current_state > 0.5){
        if (live_neighbors == 2 || live_neighbors == 3){
            new_state = 1.0;
        }
    } else {
        if (live_neighbors == 3){
            new_state = 1.0;
        }
    }
    FragColor = vec4(vec3(new_state), 1.0);

}