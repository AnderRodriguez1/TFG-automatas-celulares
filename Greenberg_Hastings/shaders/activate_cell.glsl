// Shader para activar o desactivar una celda especifica

#version 330 core
out vec4 FragColor;
in vec2 TexCoords;

uniform sampler2D u_state_texture; // Textura actual del estado del grid
uniform vec2 u_grid_size; // Tamaño del grid
uniform vec2 u_flip_coord; // Coordenadas de la celda a cambiar
uniform float dt; // Paso de tiempo (se usa para activar el temporizador en caso de que la celda este inactiva)

void main(){
    vec4 current_state = texture(u_state_texture, TexCoords);
    vec2 current_grid_coord = floor(TexCoords * u_grid_size);

    if (int(current_grid_coord.x) == int(u_flip_coord.x) && int(current_grid_coord.y) == int(u_flip_coord.y)){
        // Si la celda coincide con la que se ha pulsado
        if (current_state.g <= 0.0){
            // Si la celda esta inactiva, activarla
            FragColor = vec4(1.0, dt, 0.0, 1.0);
        }else{
            // Si la celda esta activa, desactivarla
            FragColor = vec4(0.0, 0.0, 0.0, 1.0);
        }
    }else{
        FragColor = current_state;
    }
}

