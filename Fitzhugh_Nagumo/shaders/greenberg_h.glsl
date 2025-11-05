// Shader para actualizar los automatas segun el modelo de Greenberg-Hastings
#version 330 core
// Salida
out vec4 FragColor;
//Entrada
in vec2 TexCoords;
// Parametros uniforms
uniform sampler2D u_state_texture; // Textura con el estado actual 
uniform vec2 u_grid_size; // Tamaño del grid
uniform float dt; // Paso temporal
// Constantes del modelo (se podria cambiar para pasarlos como uniforms)
const float UMBRAL_ACTIVACION = 0.7; // Umbral para activar una celda
const float TIEMPO_ACTIVO = 3.0; // Tiempo que una celda permanece activa
const float DURACION_CICLO = 10.0; // Duración total del ciclo de activación



void main(){

    vec4 current_state = texture(u_state_texture, TexCoords);
    float v = current_state.r; // Voltaje actual segun el canal rojo
    float timer = current_state.g; // Temporizador segun el canal verde
    float is_blocked = current_state.b; // Canal azul indica si la celda es un "muro" (bool)

    float v_new = v;
    float timer_new = timer;

    if (is_blocked > 0.5){
        // Celda bloqueada, no se cambia su estado
        FragColor = vec4(0.0, 0.0, 1.0, 1.0);
        return;
    }

    if (timer <= 0.0){
        // Fase inactiva, se comprueban los vecinos
        float suma_vecinos = 0.0;
        vec2 pixel_step = 1.0 / u_grid_size;

        for (int i = -1; i <= 1; i++){
            for (int j = -1; j <= 1; j++){
                if (i == j || i == -j){
                    // Ahora mismo solo se consideran los vecinos ortogonales (von Neumann neighborhood)
                    continue;
                }
                vec2 neighbor_coords = TexCoords + vec2(i, j) * pixel_step; // Coordenadas del vecino
                vec4 neighbor_state = texture(u_state_texture, neighbor_coords);
                if (neighbor_state.g > 0.0 && neighbor_state.g <= TIEMPO_ACTIVO){
                    // Si el vecino esta en fase activa (no refractaria), se suma su contribución
                    suma_vecinos += neighbor_state.r;
                }
            }
        }
        if (suma_vecinos >= UMBRAL_ACTIVACION){
            // Suma de vecinos supera el umbral, se activa la celda
            v_new = 0.5; // Valor al que se pone la celda, igual se puede ajustar
            timer_new = dt;
        }
    }else{
        // Fase activa o refractaria
        timer_new += dt; // Se incrementa el temporizador

        v_new = 1.0 - (timer_new / DURACION_CICLO);
        if (timer_new >= DURACION_CICLO){
            // Cuando el temporizador supera la duracion del ciclo, se apaga la celda
            timer_new = 0.0;
            v_new = 0.0;
        }
    }
    
    FragColor = vec4(v_new, timer_new, 0.0, 1.0);
}