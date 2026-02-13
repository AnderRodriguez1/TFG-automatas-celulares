#version 330 core
out vec4 FragColor;
in vec2 TexCoords;

uniform sampler2D u_state_texture;
uniform sampler2D u_noise_texture; 
uniform vec2 u_noise_offset;
uniform vec2 u_grid_size;
uniform float dt;
uniform float sqrt_dt;

// Parametros del modelo FitzHugh-Nagumo
uniform float a;
uniform float b;
uniform float e;
uniform float Du;
uniform float Dv;

void main(){
    vec4 current_state = texture(u_state_texture, TexCoords);
    float u = current_state.r;
    float v = current_state.g;
    float noise = texture(u_noise_texture, TexCoords + u_noise_offset).r; // Ruido con offset aleatorio

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
                sum_u_neighbors += neighbor_state.r;
                sum_v_neighbors += neighbor_state.g;
            }
        }
    }

    // Laplaciano de reaccion difusion (formula sacada de "Predator_prey laplacian")
    float laplacian_u = sum_u_neighbors / 8.0 - u;
    float laplacian_v = sum_v_neighbors / 8.0 - v;


    // Aplicar la ecuacion de FitzHugh-Nagumo ("Pattern formation")
    float R1_u = (a - u)*(u - 1.0)*u - v; // Termino de reaccion
    float R1_v = e * (b*u - v); // Termino de reaccion
    float u_pred = u + R1_u * dt; // Paso intermedio para RK2
    float v_pred = v + R1_v * dt; // Paso intermedio para RK2
    float R2_u = (a - u_pred)*(u_pred - 1.0)*u_pred - v_pred; // Termino de reaccion en el paso intermedio
    float R2_v = e * (b*u_pred - v_pred); // Termino de reaccion en el paso intermedio

    float du_react = 0.5 * dt * (R1_u + R2_u); // Promedio de las reacciones en el paso actual y el intermedio
    float dv_react = 0.5 * dt * (R1_v + R2_v); // Promedio de las reacciones en el paso actual y el intermedio

    float du_diff = Du * laplacian_u * dt; // Termino de difusion
    float dv_diff = Dv * laplacian_v * dt; // Termino de difusion
    float stochastic_term = noise * sqrt_dt; // Termino estocástico escalado por sqrt(dt)

    // Metodo de euler (igual se puede mejorar con RK4 u otro)
    float u_new = u + du_react + du_diff + stochastic_term; // Suma de reaccion, difusion y ruido
    float v_new = v + dv_react + dv_diff; // Suma de reaccion y difusion (sin ruido)
    
    FragColor = vec4(u_new, v_new, 0.0, 1.0);
}