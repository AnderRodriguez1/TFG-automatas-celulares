#version 330 core

out vec4 FragColor;
in vec2 TexCoords;

uniform sampler2D u_state_texture;
uniform vec2 u_grid_size;

void main(){
    vec2 px = 1.0 / u_grid_size;
    vec2 sum_uv = vec2(0.0, 0.0);

    for (int i = -1; i <= 1; i++) {
        for (int j = -1; j <= 1; j++) {
            vec2 offset = vec2(float(i), float(j)) * px;
            sum_uv += texture(u_state_texture, TexCoords + offset).rg;
        }
    }

    vec2 avg_uv = sum_uv / 9.0;

    FragColor = vec4(avg_uv.r, avg_uv.g, 0.0, 1.0);
}