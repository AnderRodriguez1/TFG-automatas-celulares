// En shaders/reaction.glsl

#version 330 core
out vec4 FragColor;
in vec2 TexCoords;

uniform sampler2D u_diffused_texture;
uniform float dt;

// Parámetros del modelo FHN (forma clásica)
const float a = 0.05;
const float b = 0.2;
const float epsilon = 0.005;

void main(){
    // 1. Leer el estado continuo (u, v) después de la difusión
    vec2 uv = texture(u_diffused_texture, TexCoords).rg;
    float u = uv.x;
    float v = uv.y;

    // 2. Aplicar la reacción (forma clásica de FHN)
    float du_dt = u - (u*u*u)/3.0 - v;
    float dv_dt = epsilon * (u - b*v + a);

    // 3. Actualizar usando el método de Euler
    float u_new = u + dt * du_dt;
    float v_new = v + dt * dv_dt;

    // Medida de seguridad
    u_new = clamp(u_new, -2.0, 2.0);
    v_new = clamp(v_new, -2.0, 2.0);

    // 4. Output del nuevo estado continuo
    FragColor = vec4(u_new, v_new, 0.0, 1.0);
}