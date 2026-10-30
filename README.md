# DroiDDS

<!-- CodexAstraUlt: Match the owner-renamed repository; preserve released artifact names. -->

<!-- CodexAstraUlt: Replace the initial placeholder with the owner's recompilation project plan, its evidence limits, and the next implementation step. -->

An Android ARM64 3DS recompilation project built around **3dsrecomp + Zakuro**.
The desktop builder will translate supported guest CPU code into native libraries;
a shared runtime will retain 3DS services, graphics, audio and interpreter fallback.

<!-- CodexAstraUlt: Lead with the current product work instead of making readers
infer progress from the historical probe and private tracing records below. -->
**Current development: 0.0.7-preview.2, the first generic Android title player.**
The new path builds a separate per-title ARM64 app, imports its matching game
data, retains saves, and supplies native/interpreter execution, Vulkan rendering,
controls, touch and audio. Cloud checks use an original interactive guest;
an owned-game Android boot and playable beta remain unqualified. The previously
published app is 0.0.6. See the [current roadmap](docs/ROADMAP.md),
[title-player contract](docs/ANDROID_TITLE_CONTRACT.md) and
[local Android builder](docs/ANDROID_TITLE_BUILD.md).
The [candidate build record](docs/builds/0.0.7-android-title-candidate.md)
records the completed local APK and executed host checks.

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

<!-- CodexAstraUlt: Advance the published runtime with the independently
validated Thor upload while preserving bounded fixture and game boundaries. -->
**[0.0.5 is published](https://github.com/RegiRex/DroiDDS/releases/tag/v0.0.5-probe.1);
its host/release checks, downloaded APK verification and
[owner-supplied Thor runtime report](docs/device-tests/0.0.5-thor-runtime.md)
pass.** It adds an original NCCH program
that calls real HLE services and submits PICA commands. Required checks compare
CPU interpreter/software rendering, native CPU/software rendering, and native
CPU/Vulkan rendering against exact expected pixels. Vulkan rasterization and GPU
vertex execution are reported separately: the Thor result uses CPU PICA vertex
interpretation with Vulkan rasterization, static blend/logic state and no
software raster fallback. All five device memory-layout cases pass. The uploaded
report is not an independent installed-APK identity check or a game benchmark.

The [New 3DS corrections](docs/NEW3DS_AUDIT.md#005-integration-corrections) fix the
audited parser, memory regions, commitment limits and configuration reporting;
actual loader/kernel regressions also cover heap bounds and rejected-state
recovery. The selected runtime and host compiler are now vendored for reviewable
patches, while their shared ABI remains pinned. Shader work and selected retained
resources have admission limits; the optional PICA CPU JIT is disabled. These
limits do not establish total GPU-memory bounds or eliminate every first-use
pipeline stall.

<!-- CodexAstraUlt: Record verified publication after local and CI gates
while retaining the unperformed manual Thor qualification. -->
**[0.0.6 correction 2 is published](https://github.com/RegiRex/DroiDDS/releases/tag/v0.0.6-probe.2); local and CI gates pass, and all four public
downloads are independently verified. Combined Thor evidence now supports
0.0.7 development.** [Download the Android ARM64 APK](https://github.com/RegiRex/DroiDDS/releases/download/v0.0.6-probe.2/DroidDS-0.0.6-android-arm64.apk).
Read the [correction and verification record](docs/builds/0.0.6-frontend-correction.md).
It adds an original NCCH guest that uses real HID, GSP/PICA and DSP HLE paths for
two images, D-pad/A/touch interaction and a tone. Automated native/interpreter
checks compare image and PCM output; the Android frontend presents 400×240 and
320×240 guest views together on **one Android display** using CPU readback and
Bitmap/Canvas. PICA rasterization remains Vulkan; this is not direct Vulkan
presentation or Thor physical dual-display support.

<!-- CodexAstraUlt: Combine corrected device measurements with the owner's
steady-tone confirmation without rewriting the original missing A observation. -->
The [corrected 0.0.6 Thor report](docs/device-tests/0.0.6-correction2-thor.md)
passes every automatic check and records 42 submitted/consumed touch frames,
six view replacements and working pause/resume. Both guest views and sound are
confirmed. Audio underruns fell from 197 to 11 across different-duration runs;
the owner confirmed on 2026-10-20 that the tone “Sounded steady.” The combined
0.0.6 evidence supports 0.0.7 development. This run omitted A;
unchanged-path evidence from the earlier run is retained separately. No new
full test is required solely because A was omitted.

Generic [local private-title reconnaissance](docs/PRIVATE_TITLE_RECONNAISSANCE.md)
is implemented and passes the [host verification gates](docs/builds/0.0.7-reconnaissance-tools.md).
It identifies an owned game's first observed runtime blocker. This
interpreter/software host tool does not promote milestone 0.0.7 or produce a
game-playing Android APK.

<!-- CodexAstraUlt: Expose the next implemented host build stage while keeping
native execution, package production and private device qualification distinct. -->
[Native-source preparation](docs/PRIVATE_TITLE_PREPARATION.md) now resolves strict
base-title inputs, compares compiler/runtime reader selections, disables ambient
hints, emits C and records a SHA-256 manifest. Run-019 closes the bounded Dark Moon
audio investigation without demonstrating an audio defect. Private preparation
run-002 now passes. The [bounded host compiler](docs/PRIVATE_TITLE_COMPILATION.md)
has completed the private library: 521/521 objects, linked and statically audited.
[Guarded native host comparison](docs/PRIVATE_TITLE_NATIVE_RUN.md) adds manifest/
table admission and an immutable-base fence, with dynamic modules interpreted.
Original fixtures execute and match both routes. The first
[private native run](docs/host-tests/dark-moon-native-2026-10-29.md) executes
1,999,970 native instructions with raw CPU/scheduler differences. The next task
uses corrected scheduling and supplemental synchronized comparisons, reusing
the existing library. General mutable native code and private boot evidence
remain unfinished. Android packaging now has its own implementation and
qualification path described above; host results alone do not qualify it.

The corrected-device evidence now includes measured touch and view recreation
plus the owner's steady-tone confirmation. Automated success alone cannot qualify
human observations. Original NCCH fixtures
do not establish a 3DSX loader or retail-title support. Private Dark Moon,
Xenoblade and Sonic baselines remain open because their inputs are not present
here. See [Android instructions](docs/ANDROID_PROBE.md) for testing and signing.

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
| [Thor integrated runtime result](docs/device-tests/0.0.5-thor-runtime.md) | Passing 0.0.5 guest/PICA/memory evidence and its limits |
| [0.0.6 interactive homebrew](docs/builds/0.0.6-interactive-homebrew.md) | Passing local/CI gates, verified public assets and required device observations |
| [Corrected Thor result](docs/device-tests/0.0.6-correction2-thor.md) | Measured touch and view recreation; owner confirms steady audio |
| [Local title reconnaissance](docs/PRIVATE_TITLE_RECONNAISSANCE.md) | Bounded interpreter/software baseline for owned decrypted inputs on the laptop |
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
