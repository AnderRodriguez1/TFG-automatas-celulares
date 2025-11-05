#version 330 core

out vec4 FragColor;
in vec2 TexCoords;

uniform sampler2D u_diffused_texture;
uniform float dt; // time step

const float a = 0.18;
const float b = 0.14;
const float e = 0.025;

const float M_u = 55.0;
const float M_v = 255.0;

uint hash( uint x ) {
    x += ( x << 10u );
    x ^= ( x >>  6u );
    x += ( x <<  3u );
    x ^= ( x >> 11u );
    x += ( x << 15u );
    return x;
}

uint hash( uvec2 v ) {
    return hash( v.x ^ hash(v.y) );
}

float random(vec2 f) {
        const uint mantissaMask = 0x007FFFFFu;
        const uint one          = 0x3F800000u;
       
        uint h = hash( floatBitsToUint( f ) );
        h &= mantissaMask;
        h |= one;
        
        float  r2 = uintBitsToFloat( h );
        return r2 - 1.0;
}

void main(){
    vec2 uv_norm = texture(u_diffused_texture, TexCoords).rg;
    float u = uv_norm.r * M_u;
    float v = uv_norm.g * M_v;

    float u_scaled = u / 45.0;
    float v_scaled = v / 45.0;

    float f_u = (a - u_scaled) * (u_scaled - 1.0) * u_scaled - v_scaled;
    float f_v = e * (b * u_scaled - v_scaled);

    float u_reac = u + f_u * dt * 45.0;
    float v_reac = v + f_v * dt * 45.0;

    float p_u = fract(u_reac);
    float u_final_int = floor(u_reac);
    if (random(TexCoords) < p_u) {
        u_final_int += 1.0;
    }

    float p_v = fract(v_reac);
    float v_final_int = floor(v_reac);
    if (random(TexCoords.yx) < p_v) {
        v_final_int += 1.0;
    }

    u_final_int = clamp(u_final_int, 0.0, M_u);
    v_final_int = clamp(v_final_int, 0.0, M_v);

    vec2 uv_final_norm = vec2(u_final_int / M_u, v_final_int / M_v);

    FragColor = vec4(uv_final_norm, 0.0, 1.0);
}