#version 330 core
out vec4 FragColor;
in vec2 TexCoords;

uniform sampler2D u_state_texture;
uniform sampler2D u_noise_texture; 
uniform sampler2D u_brain_texture;   // Textura del cerebro (1 canal, intensidad 0..1)
uniform vec2 u_noise_offset;
uniform vec2 u_grid_size;
uniform float dt;
uniform float sqrt_dt;

// Parametros del modelo FitzHugh-Nagumo (valores base = materia gris)
uniform float a;
uniform float b;
uniform float e;
uniform float Du;
uniform float Dv;

// Parametros de materia blanca
uniform float a_white;
uniform float Du_white;

// Umbrales para distinguir regiones del cerebro
uniform float u_black_threshold;  // < este valor = bloqueado
uniform float u_white_threshold;  // > este valor = materia blanca, intermedio = gris

// Flag para activar/desactivar la textura cerebral
uniform bool u_use_brain;

void main(){
    vec4 current_state = texture(u_state_texture, TexCoords);
    float u_val = current_state.r;
    float v = current_state.g;
    float is_blocked = current_state.b;
    float noise = texture(u_noise_texture, TexCoords + u_noise_offset).r;

    // Determinar parametros locales segun la region cerebral
    float local_a = a;
    float local_Du = Du;

    if (u_use_brain) {
        float brain_intensity = texture(u_brain_texture, TexCoords).r;

        if (brain_intensity < u_black_threshold || is_blocked > 0.5) {
            // Region negra o bloqueada: no hay actividad
            FragColor = vec4(0.0, 0.0, current_state.b, 1.0);
            return;
        }

        if (brain_intensity >= u_white_threshold) {
            // Materia blanca: usar parametros de materia blanca
            local_a = a_white;
            local_Du = Du_white;
        }
        // else: materia gris, se usan los parametros base (a, Du)
    } else {
        if (is_blocked > 0.5) {
            FragColor = current_state;
            return;
        }
    }

    vec2 px = 1.0 / u_grid_size;
    float sum_u_neighbors = 0.0;
    float sum_v_neighbors = 0.0;

    // Bucle para los 8 vecinos
    for (int i = -1; i <= 1; i++){
        for (int j = -1; j <= 1; j++){
            if (i == 0 && j == 0) {
                continue; // Saltar el centro
            }
            vec2 neighbor_uv = TexCoords + vec2(float(i), float(j)) * px;
            // Si el vecino está fuera de la grid, se trata como muro (estado en reposo u=0, v=0)
            if (neighbor_uv.x < 0.0 || neighbor_uv.x > 1.0 || neighbor_uv.y < 0.0 || neighbor_uv.y > 1.0) {
                // No sumar nada: el muro tiene u=0, v=0
            } else {
                vec4 neighbor_state = texture(u_state_texture, neighbor_uv);
                // Si el vecino esta bloqueado (o negro cerebral), no aporta difusion
                bool neighbor_blocked = neighbor_state.b > 0.5;
                if (u_use_brain) {
                    float nb_brain = texture(u_brain_texture, neighbor_uv).r;
                    neighbor_blocked = neighbor_blocked || (nb_brain < u_black_threshold);
                }
                if (!neighbor_blocked) {
                    sum_u_neighbors += neighbor_state.r;
                    sum_v_neighbors += neighbor_state.g;
                }
            }
        }
    }

    // Laplaciano de reaccion difusion
    float laplacian_u = sum_u_neighbors / 8.0 - u_val;
    float laplacian_v = sum_v_neighbors / 8.0 - v;

    // Aplicar la ecuacion de FitzHugh-Nagumo con parametros locales
    float R1_u = (local_a - u_val)*(u_val - 1.0)*u_val - v;
    float R1_v = e * (b*u_val - v);
    float u_pred = u_val + R1_u * dt;
    float v_pred = v + R1_v * dt;
    float R2_u = (local_a - u_pred)*(u_pred - 1.0)*u_pred - v_pred;
    float R2_v = e * (b*u_pred - v_pred);

    float du_react = 0.5 * dt * (R1_u + R2_u);
    float dv_react = 0.5 * dt * (R1_v + R2_v);

    float du_diff = local_Du * laplacian_u * dt;
    float dv_diff = Dv * laplacian_v * dt;
    float stochastic_term = noise * sqrt_dt;

    float u_new = u_val + du_react + du_diff + stochastic_term;
    float v_new = v + dv_react + dv_diff;
    
    FragColor = vec4(u_new, v_new, current_state.b, 1.0);
}