// Shader para actualizar los automatas segun el modelo de Greenberg-Hastings (Three-State Model)
#version 330 core
// Salida
out vec4 FragColor;
//Entrada
in vec2 TexCoords;
// Parametros uniforms
uniform sampler2D u_state_texture; // Textura con el estado actual
uniform vec2 u_grid_size; // Tamaño del grid

uniform float u_refractory_period; // Periodo refractario, si es 2, dos pasos, si es 10, diez pasos...
uniform int u_threshold; // Umbral para excitacion desde el estado de reposo

const float epsilon = 10e-6; // Valor pequeño, para tener cierta tolerancia en comparaciones de punto flotante. QUIZAS DA PROBLEMAS


void main(){

    vec4 current_state_data = texture(u_state_texture, TexCoords);
    float v = current_state_data.r; // Asegurarse de que es -1, 0, o 1

    float is_blocked = current_state_data.b; // Canal azul indica si la celda esta bloqueada

    if (is_blocked > 0.5){
        FragColor = current_state_data; // Mantener el estado actual si está bloqueado
        return;
    }

    float v_new = 0.0;

    // Logica general del modelo de Greenberg-Hastings
    // Si v == 1, excitado (solo durante un paso)
    // Si v == 0, reposo
    // Si 0 < v < 1, refractario (durante el numero de pasos definido por u_refractory_period)

    if (v > epsilon){
        // Estado excitado o refractario, debe bajar a 0 gradualmente
        float decay = 1.0 / u_refractory_period;
        v_new = v - decay; // Disminuir el valor de v en cada paso

        if (v_new < 0.0){
            v_new = 0.0; // Asegurarse de que no baje de 0
        }

    }else{// Estado de reposo, verificar vecinos para posible excitacion
        vec2 pixel_step = 1.0 / u_grid_size;

        vec2 neighbors[8];

        neighbors[0] = vec2(0.0, pixel_step.y); // Arriba
        neighbors[1] = vec2(0.0, -pixel_step.y); // Abajo
        neighbors[2] = vec2(pixel_step.x, 0.0); // Derecha
        neighbors[3] = vec2(-pixel_step.x, 0.0); // Izquierda
        neighbors[4] = vec2(pixel_step.x, pixel_step.y); // Arriba-Derecha
        neighbors[5] = vec2(-pixel_step.x, pixel_step.y); // Arriba-Izquierda
        neighbors[6] = vec2(pixel_step.x, -pixel_step.y); // Abajo-Derecha
        neighbors[7] = vec2(-pixel_step.x, -pixel_step.y); // Abajo-Izquierda

        int excited_neighbors = 0;

        for (int i = 0; i < 8; i++){
            vec2 neighbor_coords = TexCoords + neighbors[i];

            // Asegurarse de que las coordenadas del vecino estén dentro de los límites
            if (neighbor_coords.x < 0.0 || neighbor_coords.x > 1.0 || neighbor_coords.y < 0.0 || neighbor_coords.y > 1.0){
                continue; // Saltar vecinos fuera de los límites
            }

            float neighbor_v = texture(u_state_texture, neighbor_coords).r;

            if (neighbor_v > 1.0 - epsilon){ // Si el vecino está en estado excitado (1)
                excited_neighbors += 1;
            }
        }

        if (excited_neighbors >= int(u_threshold)){
            v_new = 1.0; // Excitar la celda
        }else{
            v_new = 0.0; // Mantener en reposo
        }
    }

    FragColor = vec4(v_new, v_new, is_blocked, 1.0); // Canal rojo para el estado, verde y azul en 0, alfa en 1

    
}