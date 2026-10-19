# Selected Zakuro runtime sources

<!-- CodexAstraUlt: Vendor only the runtime components requiring integration
patches, preserve attribution and keep the shared Cargo checkout immutable. -->

These `zakuro-core`, `zakuro-fs` and `zakuro-gpu` sources originate from
`fearkov/zakuro` commit `412900a5a020301da15c1cc382585e05a489a535`.
`UPSTREAM.json` records the original blob SHA-256 values; `LICENSE` preserves the
upstream MIT notice. Original upstream comments remain their authors' work.
DroidDS modifications carry adjacent `CodexAstraUlt` commentary.

CPU/common and recompilation ABI/compiler dependencies remain at their explicit
Git pins. Desktop frontend sources are not imported. The optional unbounded CPU
PICA JIT is disabled for the initial runtime qualification; the existing accurate
shader interpreter and Vulkan renderer remain available. This is an explicit
baseline policy, not a claim about eventual gameplay performance.

Original upstream GLSL and its tracked SPIR-V are included as renderer inputs;
these are public implementation assets, not retail-derived shaders. Build tooling
must validate/reproduce the shader inputs before distributing the runtime.
