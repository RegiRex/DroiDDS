#version 450

// CodexAstraUlt: A pushed texture contains magenta/cyan; a separately pushed
// uniform removes blue. Rejected blue draws test real depth/stencil behavior.
layout(set=0, binding=0) uniform sampler2D source_texture;
layout(set=0, binding=1) uniform Tint { vec4 multiplier; } tint;
layout(push_constant) uniform RendererState { float depth; uint mode; } state;
layout(location=0) out vec4 out_color;
void main() {
    vec4 color = texelFetch(source_texture, ivec2(int(gl_FragCoord.x) / 8, 0), 0);
    out_color = state.mode == 0 ? color * tint.multiplier : vec4(0, 0, 1, 1);
}
