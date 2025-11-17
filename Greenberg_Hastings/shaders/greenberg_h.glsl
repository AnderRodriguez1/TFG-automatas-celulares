// Shader para actualizar los automatas segun el modelo de Greenberg-Hastings (Three-State Model)
#version 330 core
// Salida
out vec4 FragColor;
//Entrada
in vec2 TexCoords;
// Parametros uniforms
uniform sampler2D u_state_texture; // Textura con el estado actual
uniform vec2 u_grid_size; // Tamaño del grid


void main(){

    vec4 current_state_data = texture(u_state_texture, TexCoords);
    // Convert stored texture value (0..1) to model value (-1, 0, 1) and ROUND it
    // 0.0 -> -1.0 (Refractory)
    // 0.5 ->  0.0 (Resting)
    // 1.0 ->  1.0 (Excited)
    float v_norm = current_state_data.r;
    float v = round(v_norm * 2.0 - 1.0); // Ensures v is exactly -1, 0, or 1

    float is_blocked = current_state_data.b; // Blue channel indicates if the cell is a "wall" (bool)
    vec2 pixel_step = 1.0 / u_grid_size;

    float v_new;
    float E;
    float D; // Diffusion term

    // --- Calculate E(v) based on the three-state model (E(0)=0, E(-1)=0, E(1)=-1) ---
    if (v == 1.0){ // If in excited state (1)
        E = -1.0;
    } else { // If in resting (0) or refractory (-1) state
        E = 0.0;
    }

    // --- Calculate D based on the ad hoc rule (Page 3 of the paper) ---
    // D = max {0, u^n_{i-1,j}, u^n_{i,j-1}, u^n_{i+1,j}, u^n_{i,j+1}}, if u^n_{i,j} = 0.
    // D = 0, if u^n_{i,j} != 0.
    D = 0.0; // Initialize D to 0

    if (v == 0.0) { // ONLY apply diffusion if the current cell is in the resting state (0)
        // Check immediate (non-diagonal) neighbors
        vec2 neighbors_coords[4];
        neighbors_coords[0] = TexCoords + vec2(0.0, pixel_step.y);    // Up
        neighbors_coords[1] = TexCoords + vec2(0.0, -pixel_step.y);   // Down
        neighbors_coords[2] = TexCoords + vec2(pixel_step.x, 0.0);    // Right
        neighbors_coords[3] = TexCoords + vec2(-pixel_step.x, 0.0);   // Left

        float excited_neighbor_found = 0.0; // Will be 1.0 if any neighbor is excited, 0.0 otherwise

        for (int k = 0; k < 4; k++) {
            float neigh_v_norm = texture(u_state_texture, neighbors_coords[k]).r;
            float neigh_v = round(neigh_v_norm * 2.0 - 1.0); // Get neighbor's actual state (-1, 0, 1)

            if (neigh_v == 1.0) { // If a neighbor is in the excited state (1)
                excited_neighbor_found = 1.0;
                break; // Found an excited neighbor, no need to check others
            }
        }
        D = excited_neighbor_found; // D is 1.0 if an excited neighbor exists, 0.0 otherwise
    }


    if (is_blocked > 0.5){
        // Celda bloqueada, no se cambia su estado (permanece azul in the display shader)
        // Keep its current state value to prevent propagation through it.
        // We'll map the current v back to v_mapped (e.g. 0.0, 0.5, 1.0)
        FragColor = vec4(v_norm, v_norm, 1.0, 1.0); // Keep R and G, set B to 1.0 (blocked)
        return;
    }

    // --- Calculate the new state u^{n+1} = E(u^n) + D ---
    v_new = E + D;

    // After E+D, v_new should ideally be -1, 0, or 1.
    // If v=1 (excited), E=-1. D=0. v_new = -1.
    // If v=0 (resting) and excited neighbor, E=0. D=1. v_new = 1.
    // If v=0 (resting) and no excited neighbor, E=0. D=0. v_new = 0.
    // If v=-1 (refractory), E=0. D=0. v_new = 0.

    // Map model value back to [0,1] for texture storage.
    // -1 -> 0.0
    //  0 -> 0.5
    //  1 -> 1.0
    float v_mapped = (v_new + 1.0) * 0.5;

    // Output the new state and maintain the block status
    FragColor = vec4(v_mapped, v_mapped, is_blocked, 1.0);
}