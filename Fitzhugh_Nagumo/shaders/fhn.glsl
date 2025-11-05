#version 330 core
out vec4 FragColor;
in vec2 TexCoords;

uniform sampler2D u_state_texture;
uniform vec2 u_grid_size;
uniform float dt;

// --- PARÁMETROS EXACTOS DE LA FIGURA 2 DEL PAPER ---
const float a = 0.18;
const float b = 0.14;
const float e = 0.025;
const float Du = 0.1;
const float Dv = 0.5;

void main(){
    vec4 current_state = texture(u_state_texture, TexCoords);
    float u = current_state.r;
    float v = current_state.g;

    // ===================================================================
    // 1. CALCULAR LAPLACIANO CON VECINDAD DE MOORE (8 VECINOS)
    // ===================================================================
    vec2 px = 1.0 / u_grid_size;
    float sum_u_neighbors = 0.0;
    float sum_v_neighbors = 0.0;

    // Bucle 3x3 para sumar los valores de los 8 vecinos
    for (int i = -1; i <= 1; i++){
        for (int j = -1; j <= 1; j++){
            if (i == 0 && j == 0) {
                continue; // No nos contamos a nosotros mismos en la suma de vecinos
            }
            vec2 offset = vec2(float(i), float(j)) * px;
            // Usamos fract() para las condiciones de contorno periódicas
            vec4 neighbor_state = texture(u_state_texture, fract(TexCoords + offset));
            sum_u_neighbors += neighbor_state.r;
            sum_v_neighbors += neighbor_state.g;
        }
    }

    // El Laplaciano de Reacción-Difusión a menudo se define con el promedio de los vecinos
    // O con la suma. Una formulación común es (Promedio_Vecinos - Valor_Central)
    float laplacian_u = sum_u_neighbors - 8.0 * u;
    float laplacian_v = sum_v_neighbors - 8.0 * v;
    // (Nota: a veces se divide por h^2, pero esto se puede absorber en los coeficientes D)


    // 2. Aplicar la Ecuación (5) del paper COMPLETA (Reacción + Difusión)
    float du_dt = Du * laplacian_u + (a - u)*(u - 1.0)*u - v;
    float dv_dt = Dv * laplacian_v + e * (b*u - v);

    // 3. Actualizar usando el método de Euler
    float u_new = u + dt * du_dt;
    float v_new = v + dt * dv_dt;

    // 4. Guardarraíl de seguridad: Clamping
    u_new = clamp(u_new, -0.5, 1.5);
    v_new = clamp(v_new, -0.5, 1.5);
    
    FragColor = vec4(u_new, v_new, 0.0, 1.0);
}