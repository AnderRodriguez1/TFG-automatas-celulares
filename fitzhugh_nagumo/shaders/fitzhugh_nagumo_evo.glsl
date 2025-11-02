#version 330 core

out vec4 FragColor;
in vec2 TexCoords;

uniform sampler2D u_state_texture;
uniform vec2 u_grid_size;
uniform float dt;

const float UMBRAL_ACTIVACION = 0.7;
const float TIEMPO_ACTIVO = 3.0;
const float DURACION_CICLO = 10.0;



void main(){

    vec4 current_state = texture(u_state_texture, TexCoords);
    float v = current_state.r;
    float timer = current_state.g;

    float v_new = v;
    float timer_new = timer;

    if (timer <= 0.0){
        // Fase inactiva
        float suma_vecinos = 0.0;
        vec2 pixel_step = 1.0 / u_grid_size;

        for (int i = -1; i <= 1; i++){
            for (int j = -1; j <= 1; j++){
                if (i == j || i == -j){
                    continue;
                }
                vec2 neighbor_coords = TexCoords + vec2(i, j) * pixel_step;
                vec4 estado_vecino = texture(u_state_texture, neighbor_coords);
                if (estado_vecino.g > 0.0 && estado_vecino.g <= TIEMPO_ACTIVO){
                    suma_vecinos += estado_vecino.r;
                }
            }
        }
        if (suma_vecinos >= UMBRAL_ACTIVACION){
            v_new = 0.5;
            timer_new = dt;
        }
    }else{
        // Fase activa o refractaria
        timer_new += dt;

        v_new = 1.0 - (timer_new / DURACION_CICLO);
        if (timer_new >= DURACION_CICLO){
            timer_new = 0.0;
            v_new = 0.0;
        }
    }
    FragColor = vec4(v_new, timer_new, 0.0, 1.0);
}