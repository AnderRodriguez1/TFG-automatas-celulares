#version 330 core
out vec4 FragColor;
in vec2 TexCoords;

uniform sampler2D u_state_texture; 
uniform float u_zoom_level; 
uniform vec2 u_view_offset;
uniform vec2 u_grid_size;

void main()
{
    vec2 sample_coord = (TexCoords - 0.5) / u_zoom_level + (u_view_offset / u_grid_size);

    if (sample_coord.x < 0.0 || sample_coord.x > 1.0 || sample_coord.y < 0.0 || sample_coord.y > 1.0) {
        FragColor = vec4(0.1, 0.1, 0.1, 1.0); // Color de fondo
        return;
    }

    vec3 final_color = texture(u_state_texture, sample_coord).rgb;
    
    vec2 grid_coord_float = sample_coord * u_grid_size;
    vec2 inside_cell_coord = fract(grid_coord_float);
    float border_thickness = 0.05;
    bool is_border = inside_cell_coord.x < border_thickness || inside_cell_coord.x > (1.0 - border_thickness) ||
                     inside_cell_coord.y < border_thickness || inside_cell_coord.y > (1.0 - border_thickness);

    if (is_border && u_zoom_level >= 1) {
        final_color = vec3(0.2);
    }
    
    FragColor = vec4(final_color, 1.0);
}
