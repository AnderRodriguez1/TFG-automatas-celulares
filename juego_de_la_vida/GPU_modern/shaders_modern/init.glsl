#version 330 core
out vec4 FragColor;
uniform float u_seed;

float random(vec2 st) {
    return fract(sin(dot(st.xy, vec2(12.9898, 78.233))) * 43758.5453123);
}

void main()
{
    vec2 grid_coord = floor(gl_FragCoord.xy); 
    float r = random(grid_coord + u_seed);
    float state = step(0.5, r);
    FragColor = vec4(vec3(0), 1.0);
}