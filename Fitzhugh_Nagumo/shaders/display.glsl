// Shader para mostrar el grid

#version 330 core
out vec4 FragColor;
in vec2 TexCoords;

uniform sampler2D u_state_texture; // Textura actual del estado del grid
uniform float u_zoom_level; // Nivel de zoom
uniform vec2 u_view_offset; // Offset de la vista en coordenadas de celda
uniform vec2 u_grid_size; // Tamaño del grid

void main()
{
    // Calcular las coordenadas de muestreo teniendo en cuenta el zoom y el offset
    vec2 sample_coord = (TexCoords - 0.5) / u_zoom_level + (u_view_offset / u_grid_size); 

    if (sample_coord.x < 0.0 || sample_coord.x > 1.0 || sample_coord.y < 0.0 || sample_coord.y > 1.0) {
        // Si la coordenada de muestreo esta fuera del grid, dibujar fondo
        FragColor = vec4(0.1, 0.1, 0.1, 1.0); // Color de fondo
        return;
    }

    vec4 current_state = texture(u_state_texture, sample_coord); // Leer el estado actual de la celda
    float u = current_state.r; // Voltaje de la celda (canal rojo)
    float u_norm = (u + 2) / 4.0; // Normalizar u a [0, 1] para el colormap
    float is_blocked = current_state.b; // Bloqueo de la celda (canal azul)

    vec3 final_color;

    if (is_blocked > 0.5){
        // Si esta bloqueada
        final_color = vec3(0.4, 0.4, 0.5); // Azul celeste para células bloqueadas
    }else{
        // Se define un rango maximo de visualizacion
        float max_val = 1.0;
        float intensity = clamp(abs(u) / max_val, 0.0, 1.0); // Intensidad para el colormap

        if (u > 0.5){// Solo mostrar valores mayores a 0.3 para evitar ruido visual, ajustar segun sea necesario
            final_color = vec3(1.0, 1.0, 0.0) * intensity; // Rojo para valores positivos
            if (u > 0.8){
                float white_intensity = (intensity - 0.8) / 0.5; // Intensidad para el blanco
                final_color = mix(final_color, vec3(1.0), white_intensity); // Mezclar con blanco
            }
        }else{
            final_color = vec3(0.78, 0.0, 1.0) * intensity; // Azul para valores negativos
        }
    }
    
    // Calcular las coordenadas dentro de la celda para dibujar bordes
    vec2 grid_coord_float = sample_coord * u_grid_size;
    vec2 inside_cell_coord = fract(grid_coord_float);

    // Estimar el tamaño de un pixel en coordenadas de celda
    float px_x = fwidth(grid_coord_float.x);
    float px_y = fwidth(grid_coord_float.y);
    float pixel_size_in_cells = max(px_x, px_y);

    // Calcular el numero de pixeles que cubre una celda, evitar division por cero
    float cell_pixels = 1.0 / max(pixel_size_in_cells, 1e-6);

    // Solo dibujar bordes si una celda cubre al menos este numero de pixeles en pantalla
    float min_pixels_for_borders = 2.0; 

    if (cell_pixels >= min_pixels_for_borders) {
        // Distancia al borde mas cercano de la celda (en unidades de celda)
        vec2 dist_to_edge = min(inside_cell_coord, 1.0 - inside_cell_coord);
        float min_dist = min(dist_to_edge.x, dist_to_edge.y);

        // Grosor base en unidades de celda 
        float base_thickness = 0.05;

        // Asegurar que el grosor no caiga por debajo de aproximadamente un pixel en pantalla
        float thickness = max(base_thickness, 0.6 * pixel_size_in_cells);

        // Factor de borde anti-aliasing: 1.0 en el centro del borde, 0.0 alejado del borde
        float edge_fade = smoothstep(thickness + pixel_size_in_cells, thickness - pixel_size_in_cells, min_dist);

        // mezclar el color del borde con el color final calculado
        vec3 border_color = vec3(0.2);
        final_color = mix(final_color, border_color, clamp(edge_fade, 0.0, 1.0));
    }
    
    FragColor = vec4(final_color, 1.0);
}
