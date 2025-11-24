// Shader para actualizar los automatas segun el modelo de Greenberg-Hastings (Three-State Model)
#version 330 core
// Salida
out vec4 FragColor;
//Entrada
in vec2 TexCoords;
// Parametros uniforms
uniform sampler2D u_state_texture; // Textura con el estado actual
uniform vec2 u_grid_size; // Tamaño del grid


void main(){

    vec4 current_state_data = texture(u_state_texture, TexCoords);
    // Mapear los valores del canal rojo de [0,1] a los estados del modelo:
    // 0.0 -> -1.0 (Refractario)
    // 0.5 ->  0.0 (Reposo)
    // 1.0 ->  1.0 (Excitado)
    float v_norm = current_state_data.r;
    float v = round(v_norm * 2.0 - 1.0); // Asegurarse de que es -1, 0, o 1

    float is_blocked = current_state_data.b; // Canal azul indica si la celda esta bloqueada
    vec2 pixel_step = 1.0 / u_grid_size;

    float v_new;
    float E;
    float D; // Término de difusión

    // Calcular E(v) basado en el modelo de tres estados (E(0)=0, E(-1)=0, E(1)=-1)
    if (v == 1.0){ // Si está en estado excitado (1)
        E = -1.0;
    } else { // Si está en estado de reposo (0) o refractario (-1)
        E = 0.0;
    }

    // Término de difusión
    D = 0.0; // Inicializar D a 0

    if (v == 0.0) { // SOLO aplicar difusión si la celda actual está en estado de reposo (0)
        // Verificar vecinos inmediatos (no diagonales)
        vec2 neighbors_coords[4];
        neighbors_coords[0] = TexCoords + vec2(0.0, pixel_step.y);    // Arriba
        neighbors_coords[1] = TexCoords + vec2(0.0, -pixel_step.y);   // Abajo
        neighbors_coords[2] = TexCoords + vec2(pixel_step.x, 0.0);    // Derecha
        neighbors_coords[3] = TexCoords + vec2(-pixel_step.x, 0.0);   // Izquierda

        float excited_neighbor_found = 0.0; // Será 1.0 si algún vecino está excitado, 0.0 de lo contrario

        for (int k = 0; k < 4; k++) {

            vec2 nc = neighbors_coords[k];

            if (nc.x < 0.0 || nc.x > 1.0 || nc.y < 0.0 || nc.y > 1.0) {
                continue; // Saltar vecinos fuera de los límites
            }

            float neigh_v_norm = texture(u_state_texture, neighbors_coords[k]).r;
            float neigh_v = round(neigh_v_norm * 2.0 - 1.0); // Obtener el estado real del vecino (-1, 0, 1)
            if (neigh_v == 1.0) { // Si un vecino está en estado excitado (1)
                excited_neighbor_found = 1.0;
                break; // Encontró un vecino excitado, no necesita revisar otros
            }
        }
        D = excited_neighbor_found; // D es 1.0 si existe un vecino excitado, 0.0 de lo contrario
    }


    if (is_blocked > 0.5){
        // Celda bloqueada, no se cambia su estado (permanece azul en el shader de display)
        // Mantener su valor de estado actual para evitar la propagación a través de ella.
        // Mapearemos el valor actual de v de nuevo a v_mapped
        FragColor = vec4(v_norm, v_norm, 1.0, 1.0); // Mantener R y G, establecer B a 1.0 (bloqueado)
        return;
    }

    // Calcular el nuevo estado u^{n+1} = E(u^n) + D
    v_new = E + D;

    // Mapear el valor del modelo de nuevo a [0,1] para almacenamiento en textura.
    // -1 -> 0.0
    //  0 -> 0.5
    //  1 -> 1.0
    float v_mapped = (v_new + 1.0) * 0.5;

    // Salida del nuevo estado y mantener el estado de bloqueo
    FragColor = vec4(v_mapped, v_mapped, is_blocked, 1.0);
}