#version 330 core
// Salida
out vec4 FragColor;
// Entrada
in vec2 TexCoords;

// Parametros de entrada, se definen desde el programa principal
uniform sampler2D u_state_texture; // Textura del estado actual
uniform vec2 u_grid_size; // Tamaño del grid

void main(){
    vec2 pixel_step = 1.0 / u_grid_size; // Tamaño de un pixel respecto al tamaño del grid
    
    float current_state = texture(u_state_texture, TexCoords).r; // El estado actual se obtiene con la intensidad del color

    int live_neighbors = 0;
    // Bucle para contar los vecinos vivos
    for (int i = -1; i<= 1; i++){
        for (int j = -1; j<= 1; j++){
            if (i == 0 && j == 0){
               // No se cuenta el pixel actual
                continue;
            }
            vec2 neighbor_coords = TexCoords + vec2(i, j) * pixel_step; // Coordenadas del vecino
            
            if (texture(u_state_texture, neighbor_coords).r > 0.5){ // Si la intensidad del color es mayor a 0.5, el vecino esta vivo
                live_neighbors += 1;
            }

        }
    }
    float new_state = 0.0;
    // Logica de cambio de estado
    if (current_state > 0.5){// Si esta vivo
        if (live_neighbors == 2 || live_neighbors == 3){// Si tiene 2 o 3 vecinos vivos, sigue vivo
            new_state = 1.0;
        }
    } else {// Si esta muerto
        if (live_neighbors == 3){// Si tiene exactamente 3 vecinos vivos, nace
            new_state = 1.0;
        }
    }
    FragColor = vec4(vec3(new_state), 1.0);// Se asigna el nuevo estado al color de salida

}

