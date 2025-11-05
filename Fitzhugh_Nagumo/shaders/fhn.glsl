#version 330 core
out vec4 FragColor;
in vec2 TexCoords;

uniform sampler2D u_state_texture;
uniform vec2 u_grid_size;
uniform float dt;

// --- PARÁMETROS EXACTOS DE LA FIGURA 2 DEL PAPER ---
const float a = 0.18;
const float b = 0.14;
const float e = 0.025; // Epsilon en la Ecuación (5)

// Coeficientes de difusión. Du/Dv = 3
const float Du = 1.5;
const float Dv = 0.5;

void main(){
    vec4 current_state = texture(u_state_texture, TexCoords);
    float u = current_state.r;
    float v = current_state.g;

    // 1. Calcular el Laplaciano para 'u' y 'v' por separado
    vec2 px = 1.0 / u_grid_size;
    
    // Vecinos para 'u'
    float u_up = texture(u_state_texture, TexCoords + vec2(0.0, px.y)).r;
    float u_down = texture(u_state_texture, TexCoords - vec2(0.0, px.y)).r;
    float u_left = texture(u_state_texture, TexCoords - vec2(px.x, 0.0)).r;
    float u_right = texture(u_state_texture, TexCoords + vec2(px.x, 0.0)).r;
    float laplacian_u = u_up + u_down + u_left + u_right - 4.0 * u;

    // Vecinos para 'v'
    float v_up = texture(u_state_texture, TexCoords + vec2(0.0, px.y)).g;
    float v_down = texture(u_state_texture, TexCoords - vec2(0.0, px.y)).g;
    float v_left = texture(u_state_texture, TexCoords - vec2(px.x, 0.0)).g;
    float v_right = texture(u_state_texture, TexCoords + vec2(px.x, 0.0)).g;
    float laplacian_v = v_up + v_down + v_left + v_right - 4.0 * v;

    // 2. Aplicar la Ecuación (5) del paper COMPLETA (Reacción + Difusión)
    float du_dt = Du * laplacian_u + (a - u)*(u - 1.0)*u - v;
    float dv_dt = Dv * laplacian_v + e * (b*u - v);

    // 3. Actualizar usando el método de Euler
    float u_new = u + dt * du_dt;
    float v_new = v + dt * dv_dt;

    // No necesitamos clamping aquí, los valores de este modelo son estables en [0,1]
    
    FragColor = vec4(u_new, v_new, 0.0, 1.0);