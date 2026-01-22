#version 330 core

out vec4 FragColor;
in vec2 TexCoords;

uniform sampler2D u_state_texture; // Textura actual del estado del grid
uniform sampler2D u_paste_pattern;
uniform vec2 u_grid_size; // Tamaño del grid
uniform vec2 u_pattern_size; // Tamaño del patrón a pegar
uniform vec2 u_offset; // Offset en coordenadas de celda donde pegar el patrón

void main(){
    vec4 current_state = texture(u_state_texture, TexCoords);

    vec2 pixel_pos = TexCoords * u_grid_size;

    vec2 pos_in_pattern = pixel_pos - u_offset;

    if (pos_in_pattern.x >= 0.0 && pos_in_pattern.x < u_pattern_size.x &&
        pos_in_pattern.y >= 0.0 && pos_in_pattern.y < u_pattern_size.y){

        vec2 pattern_uv = pos_in_pattern / u_pattern_size;

        vec4 visual_color = texture(u_paste_pattern, pattern_uv);

        if (visual_color.a < 0.1){
            FragColor = current_state;
            return;
        }

        if (visual_color.r > 0.5 && visual_color.b > 0.5){
            // Celda activa 
            FragColor = vec4(1.0, 0.0, 0.0, 1.0); // Estado activo
        }else{
            FragColor = vec4(0.0, 0.0, 1.0, 1.0); // Celda bloqueada
        }
        return;
    }
    FragColor = current_state;
}
