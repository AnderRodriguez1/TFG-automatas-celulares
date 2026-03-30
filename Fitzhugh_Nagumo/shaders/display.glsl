// Shader para mostrar el grid

#version 330 core
out vec4 FragColor;
in vec2 TexCoords;

uniform sampler2D u_state_texture; // Textura actual del estado del grid
uniform sampler2D u_brain_texture; // Textura del cerebro (1 canal)
uniform sampler2D u_no_diffusion_mask; // Mascara de no-difusion (1 canal)
uniform sampler2D u_voltage_roi_mask; // Mascara de ROIs donde se miden voltajes
uniform float u_zoom_level; // Nivel de zoom
uniform vec2 u_view_offset; // Offset de la vista en coordenadas de celda
uniform vec2 u_grid_size; // Tamaño del grid
uniform bool u_use_brain;           // Flag para activar overlay cerebral
uniform bool u_show_brain_regions;  // Flag para mostrar regiones del cerebro
uniform bool u_show_brain_boundary; // Flag para mostrar frontera gris/blanca
uniform bool u_show_voltage_rois;   // Flag para mostrar ROIs de voltaje
uniform float u_black_threshold;    // Umbral negro
uniform float u_white_threshold;    // Umbral blanco

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
    float diffusion_factor = texture(u_no_diffusion_mask, sample_coord).r; // Leer de textura separada

    vec3 final_color;

    // Modo visualizacion de regiones cerebrales
    if (u_use_brain && u_show_brain_regions) {
        float brain_intensity = texture(u_brain_texture, sample_coord).r;
        if (brain_intensity < u_black_threshold) {
            final_color = vec3(0.05, 0.05, 0.05); // Negro: bloqueado
        } else if (brain_intensity >= u_white_threshold) {
            final_color = vec3(0.95, 0.95, 0.95); // Blanco: materia blanca
        } else {
            final_color = vec3(0.5, 0.5, 0.5); // Gris: materia gris
        }
    } else if (is_blocked > 0.5){
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

    // Overlay frontera de zona sin difusión (solo borde, no relleno)
    if (diffusion_factor < 0.5) {
        vec2 texel = 1.0 / u_grid_size;
        float a_right = texture(u_no_diffusion_mask, sample_coord + vec2(texel.x, 0.0)).r;
        float a_left  = texture(u_no_diffusion_mask, sample_coord - vec2(texel.x, 0.0)).r;
        float a_up    = texture(u_no_diffusion_mask, sample_coord + vec2(0.0, texel.y)).r;
        float a_down  = texture(u_no_diffusion_mask, sample_coord - vec2(0.0, texel.y)).r;
        // Es frontera si algún vecino tiene difusión normal (>= 0.5)
        bool is_no_diff_boundary = (a_right >= 0.5 || a_left >= 0.5 || a_up >= 0.5 || a_down >= 0.5);
        if (is_no_diff_boundary) {
            final_color = mix(final_color, vec3(0.0, 1.0, 0.0), 0.85);
        }
    }
    
    // Overlay de la frontera entre materia gris y blanca
    if (u_use_brain && u_show_brain_boundary) {
        float brain_here = texture(u_brain_texture, sample_coord).r;
        vec2 texel = 1.0 / u_grid_size;
        float brain_right = texture(u_brain_texture, sample_coord + vec2(texel.x, 0.0)).r;
        float brain_left  = texture(u_brain_texture, sample_coord - vec2(texel.x, 0.0)).r;
        float brain_up    = texture(u_brain_texture, sample_coord + vec2(0.0, texel.y)).r;
        float brain_down  = texture(u_brain_texture, sample_coord - vec2(0.0, texel.y)).r;

        // Clasificar regiones: 0=negro, 1=gris, 2=blanco
        int region_here  = (brain_here  < u_black_threshold) ? 0 : (brain_here  >= u_white_threshold) ? 2 : 1;
        int region_right = (brain_right < u_black_threshold) ? 0 : (brain_right >= u_white_threshold) ? 2 : 1;
        int region_left  = (brain_left  < u_black_threshold) ? 0 : (brain_left  >= u_white_threshold) ? 2 : 1;
        int region_up    = (brain_up    < u_black_threshold) ? 0 : (brain_up    >= u_white_threshold) ? 2 : 1;
        int region_down  = (brain_down  < u_black_threshold) ? 0 : (brain_down  >= u_white_threshold) ? 2 : 1;

        // Si algún vecino está en una región distinta (gris<->blanca), es frontera
        bool is_boundary = (region_here == 1 || region_here == 2) && (
            (region_right != region_here && region_right != 0) ||
            (region_left  != region_here && region_left  != 0) ||
            (region_up    != region_here && region_up    != 0) ||
            (region_down  != region_here && region_down  != 0)
        );

        if (is_boundary) {
            final_color = mix(final_color, vec3(1.0, 0.0, 0.0), 0.85);
        }
    }

    // Overlay de ROIs de voltaje (relleno tenue + borde intenso)
    if (u_show_voltage_rois) {
        float roi_here = texture(u_voltage_roi_mask, sample_coord).r;
        if (roi_here > 0.5) {
            vec2 texel = 1.0 / u_grid_size;
            float r = texture(u_voltage_roi_mask, sample_coord + vec2(texel.x, 0.0)).r;
            float l = texture(u_voltage_roi_mask, sample_coord - vec2(texel.x, 0.0)).r;
            float u2 = texture(u_voltage_roi_mask, sample_coord + vec2(0.0, texel.y)).r;
            float d = texture(u_voltage_roi_mask, sample_coord - vec2(0.0, texel.y)).r;
            bool roi_boundary = (r < 0.5 || l < 0.5 || u2 < 0.5 || d < 0.5);
            vec3 roi_fill_color = vec3(0.0, 0.85, 1.0);
            vec3 roi_border_color = vec3(1.0, 0.35, 0.0);
            final_color = mix(final_color, roi_fill_color, 0.28);
            if (roi_boundary) {
                final_color = mix(final_color, roi_border_color, 0.9);
            }
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
