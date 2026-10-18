#version 450

// CodexAstraUlt: Original vertex-buffer-free full-screen triangle covers every
// pixel center of the 16 by 16 offscreen target without a diagonal seam.
void main() {
    const vec2 positions[3] = vec2[3](vec2(-1.0, -1.0),
                                     vec2(3.0, -1.0),
                                     vec2(-1.0, 3.0));
    gl_Position = vec4(positions[gl_VertexIndex], 0.0, 1.0);
}
