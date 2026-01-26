// Este shader se encarga de mostrar una preview del patrón que se va a pegar sobre el grid

#version 330 core

out vec4 FragColor;
in vec2 TexCoords;

uniform sampler2D u_paste_pattern; // Patrón que se va a pegar
uniform vec2 u_grid_size; 
uniform vec2 u_pattern_size;
uniform vec2 u_paste_pos;

uniform float u_zoom_level; 
uniform vec2 u_view_offset;

void main(){

    vec2 grid_uv = (TexCoords - 0.5) / u_zoom_level + (u_view_offset / u_grid_size);
    vec2 grid_pixel_pos = grid_uv * u_grid_size;

    vec2 local_pos = grid_pixel_pos - u_paste_pos; // Poisicon relativa al patrón

    if (local_pos.x >= 0.0 && local_pos.x < u_pattern_size.x &&
        local_pos.y >= 0.0 && local_pos.y < u_pattern_size.y){

        vec2 tex_uv = local_pos / u_pattern_size;

        vec4 visual_color = texture(u_paste_pattern, tex_uv);

        if (visual_color.a < 0.1){
            discard;
        }else{
            FragColor = vec4(visual_color.rgb, visual_color.a * 0.6); // Hacerlo semi-transparente
        }
    }else{
        discard;
    }
}