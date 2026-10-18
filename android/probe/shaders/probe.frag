#version 450

// CodexAstraUlt: One real graphics pipeline uses explicit draw-time color data
// for both solid cases and the two scissored halves; no shader variants exist.
layout(push_constant) uniform ProbeColor {
    vec4 value;
} color;
layout(location = 0) out vec4 out_color;

void main() {
    out_color = color.value;
}
