#version 450

// CodexAstraUlt: Original full-screen geometry with controllable clip-space depth
// exercises depth rejection and depth clamping without guest/PICA shader code.
layout(push_constant) uniform RendererState { float depth; uint mode; } state;
void main() {
    const vec2 p[3] = vec2[3](vec2(-1, -1), vec2(3, -1), vec2(-1, 3));
    gl_Position = vec4(p[gl_VertexIndex], state.depth, 1.0);
}
