# DroidDS

<!-- CodexAstraUlt: Replace the initial placeholder with the owner's recompilation project plan, its evidence limits, and the next implementation step. -->

An Android ARM64 3DS recompilation project built around **3dsrecomp + Zakuro**.
The desktop builder will translate supported guest CPU code into native libraries;
a shared runtime will retain 3DS services, graphics, audio and interpreter fallback.

<!-- CodexAstraUlt: Replace planning-only status after the first verified host
build; keep its small CPU proof separate from Android and game qualification. -->
**Status, 2026-10-17: the first Linux CPU foundation build, 0.0.1, passes.**
Four original ARM/Thumb cases execute generated native code and match the selected
interpreter and known expected outputs, including native interworking and deliberate
missing-entry fallback. Validation passed 151 Rust tests and 15 Python gate tests,
plus the executable's four cases and four negative controls.

<!-- CodexAstraUlt: Record the owner's passing CPU/GPU report while keeping the
small platform fixture separate from full 3DS rendering and game qualification. -->
**The owner-supplied 0.0.2 Thor CPU report passes all four fixtures and both error
controls.** It reports Android ARM64 with 4 KiB pages. Read
[the device result and its scope](docs/device-tests/0.0.2-thor-cpu.md).
Version **0.0.3** adds an original Vulkan offscreen draw/readback test and a
**Save report** button. Its three patterns pass across three fresh device/resource
cycles on host software Vulkan with validation enabled. The
[owner's 0.0.3 Thor report](docs/device-tests/0.0.3-thor-cpu-vulkan.md) also passes
all CPU and offscreen GPU checks on Android 13/Adreno 740, with Vulkan 1.3.128
reported. That result alone did not establish full renderer, lifecycle or game qualification;
the JSON does not record which export method was used.

<!-- CodexAstraUlt: Advance to the expanded diagnostic without treating original
backend operations or reproduced New 3DS defects as game integration. -->
Version **0.0.4 passes its owner-supplied Thor report**: eight CPU cases,
executable-code safety controls, all required Vulkan capabilities, eleven image
readbacks and the compute checks. The Thor lacks optional dynamic blend/logic
state, so integration explicitly tests static pipeline state. Read
[the device result](docs/device-tests/0.0.4-thor-runtime-probe.md).

<!-- CodexAstraUlt: Record verified public availability while preserving the
bounded original guest and pending physical-device/game qualification. -->
**[0.0.5 is published](https://github.com/RegiRex/DroidDS/releases/tag/v0.0.5-probe.1);
its host/release checks and downloaded APK verification pass. Its Thor test is
pending.** It adds an original NCCH program
that calls real HLE services and submits PICA commands. Required checks compare
CPU interpreter/software rendering, native CPU/software rendering, and native
CPU/Vulkan rendering against exact expected pixels. Vulkan rasterization and GPU
vertex execution are reported separately; the Thor may use the CPU PICA vertex
interpreter with Vulkan rasterization.

The [New 3DS corrections](docs/NEW3DS_AUDIT.md#005-integration-corrections) fix the
audited parser, memory regions, commitment limits and configuration reporting;
actual loader/kernel regressions also cover heap bounds and rejected-state
recovery. The selected runtime and host compiler are now vendored for reviewable
patches, while their shared ABI remains pinned. Shader work and selected retained
resources have admission limits; the optional PICA CPU JIT is disabled. These
limits do not establish total GPU-memory bounds or eliminate every first-use
pipeline stall.

This diagnostic still has no game presentation, controller/audio frontend or
retail-title evidence. It uses original NCCH fixtures, not a 3DSX loader. Private
Dark Moon, Xenoblade and Sonic baselines remain open because their inputs are not
present in this environment. See [Android instructions](docs/ANDROID_PROBE.md)
for the diagnostic workflow and signing details.

<!-- CodexAstraUlt: Persist the owner's report-driven release instruction in the
public overview without promising background execution or bypassing hardware. -->
After each owner-supplied report, development proceeds to the next qualified build
through 0.1.0 without a routine approval round. Failed gates receive diagnosis and
a corrective build before promotion; required hardware/input decisions remain
explicit.

| Read | Purpose |
| --- | --- |
| [Build and run](docs/BUILDING.md) | Reproduce the Linux CPU foundation and actual runtime gate |
| [Android CPU/Vulkan/runtime probe](docs/ANDROID_PROBE.md) | Build the ARM64 test app and run it on the Thor |
| [Thor CPU result](docs/device-tests/0.0.2-thor-cpu.md) | Owner-supplied 0.0.2 execution and its qualification boundary |
| [Thor CPU/Vulkan result](docs/device-tests/0.0.3-thor-cpu-vulkan.md) | Passing 0.0.3 hardware readbacks and remaining renderer gates |
| [Thor expanded probe result](docs/device-tests/0.0.4-thor-runtime-probe.md) | Passing 0.0.4 CPU/safety/capability checks and the static-state requirement |
| [0.0.5 build and release evidence](docs/builds/0.0.5-runtime-integration.md) | Actual runtime integration, fixes, host tests and verified public APK |
| [0.0.4 build evidence](docs/builds/0.0.4-runtime-probe.md) | Expanded CPU, renderer operations and packaging checks |
| [New 3DS audit and corrections](docs/NEW3DS_AUDIT.md) | Reproduced defects, implemented runtime fixes and remaining title gates |
| [First build evidence](docs/builds/0.0.1-foundation.md) | Results, scope, limitations and next work |
| [Additional reuse candidates](docs/REUSE_CANDIDATES.md) | AnyPS5, Azahar, Citra MMJ and Uberhar source review |
| [Architecture](docs/ARCHITECTURE.md) | Components, design decisions, boundaries and risks |
| [Versions through 0.1.0](docs/ROADMAP.md#versioned-path-to-010) | Planned builds, first Android game boot at 0.0.7 and playable segment at 0.0.8 |
| [Roadmap](docs/ROADMAP.md) | Ordered milestones with measurable exit gates |
| [Implementation backlog](docs/BACKLOG.md) | Bounded tasks, dependencies and acceptance checks |
| [Testing strategy](docs/TEST_STRATEGY.md) | CPU correctness, graphics continuity, memory and device tests |
| [Research review](docs/RESEARCH_REVIEW.md) | ZIP inventory, verified pins, source findings and corrections |
| [Local Codex handoff](docs/LOCAL_CODEX_HANDOFF.md) | How to continue on the Nobara/Thor setup |
| [Original research pack](docs/research/2026-10-17/00_README.md) | Preserved input; proposals and example prompts, not completed work |

CPU recompilation does not remove PICA graphics translation or guarantee smooth
cold runs. The inherited renderer has synchronous generic-pipeline creation and
resource-management gaps that must be measured and addressed. The owner's targets
remain correct cold gameplay at 4× where achievable, with substantial headroom at
2×, including Luigi's Mansion: Dark Moon. These are qualification goals.

DroidDS is separate from Uberhar. Reuse its testing lessons and device workflow;
review provenance before importing implementation. Keep retail inputs and all
derived code, assets, local packages and signing keys outside public source and CI.
