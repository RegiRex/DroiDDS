# DroiDDS

<!-- CodexAstraUlt: Match the owner-renamed repository; preserve released artifact names. -->

<!-- CodexAstraUlt: Replace the initial placeholder with the owner's recompilation project plan, its evidence limits, and the next implementation step. -->

An Android ARM64 3DS recompilation project built around **3dsrecomp + Zakuro**.
The desktop builder will translate supported guest CPU code into native libraries;
a shared runtime will retain 3DS services, graphics, audio and interpreter fallback.

<!-- CodexAstraUlt: Lead with the verified current candidate and downloads;
retain private performance evidence separately from passed cloud gates. -->
**[0.0.8-preview.7/code 17 is published](https://github.com/RegiRex/DroiDDS/releases/tag/v0.0.8-preview.7), the current generic Android title player candidate.**
The new path builds a separate per-title ARM64 app, imports its matching game
data, retains saves, and supplies native/interpreter execution, Vulkan rendering,
controls, touch and audio. Cloud checks use an original interactive guest.
Host, main and release CI pass for that published candidate; the four public
downloads are independently verified.
[Download the original-title Android APK](https://github.com/RegiRex/DroiDDS/releases/download/v0.0.8-preview.7/DroiDDS-0.0.8-preview.7-original-android-arm64.apk).
The earlier fixture probe remains 0.0.6. See the [current roadmap](docs/ROADMAP.md),
[title-player contract](docs/ANDROID_TITLE_CONTRACT.md) and
[local Android builder](docs/ANDROID_TITLE_BUILD.md).
The [candidate build record](docs/builds/0.0.8-transfer-followup.md)
records implementation `9296010`, release source
`1c7fffa`, exact public artifact identities and executed gates.

<!-- CodexAstraUlt: Credit private menu boot separately from the new public
original-fixture release; neither establishes a qualified playable segment. -->
**Dark Moon now reaches interactive title and file-selection menus on the Thor
in the owner's Native test.** The A button responds and the bounded run stopped
normally with no reported runtime faults. This achieves the central **0.0.7 boot
objective**. The [two device reports](docs/device-tests/0.0.7-dark-moon-thor-menu.md)
retain **1,361 and 2,889 audio underruns**, with zero reported PCM drops and all
converted samples written. Their core timing establishes slow sample production,
consistent with the owner's crackling/slow-frame observation.

<!-- CodexAstraUlt: Record the completed private audio follow-up separately
from its later restart and the next unqualified development candidate. -->
The [private code 11 follow-up](docs/device-tests/0.0.8-preview1-dark-moon-thor.md)
reached file selection during a 110-second Native run and stopped normally;
severe slowdown and crackling remain. A later restart replaced that run's JSON.
Its now-supplied restart JSON covers **43.117 seconds** of worker execution and
confirms **57.64% of core time in command processing**, **568 audio underruns**
and zero reported PCM loss. It remains separate from the 110-second test.
Local testing now [uploads reviewed diagnostic reports](docs/DEVICE_REPORT_HANDOFF.md)
with verified GitHub links for cloud retrieval.

<!-- CodexAstraUlt: A failed GPU trial closes the comparison attempt without
qualifying GPU performance; retain the measured CPU path and next candidate. -->
The [code 12 Thor comparison](docs/device-tests/0.0.8-preview2-dark-moon-thor.md)
is complete. Native/CPU vertices reached file selection at **17.72% emulated
speed**, with **1,426 underruns** and no recorded PCM loss. CPU vertex processing
consumed **33.42% of core time**. Native/GPU vertices failed during pipeline
creation before any GPU-vertex draw or Vulkan submission; there is no usable
GPU performance comparison. The owner’s later Interpreter observations remain
separate. Unmatched code 11/12 scene coverage and duration do not establish a regression.

<!-- CodexAstraUlt: Advance from the completed code 13 device run without
claiming a speed gain or scheduling more GPU trials. -->
The [code 13 Thor test](docs/device-tests/0.0.8-preview3-dark-moon-thor.md) is
complete: Native/CPU vertices reached file selection at **18.12% speed**, with
**1,471 underruns** and short audio bursts/gaps. No clear performance gain is
established. GPU pipeline creation still fails; further Thor GPU tests and
audio-perfection work are deferred. The published code 13
[build record](docs/builds/0.0.8-pipeline-followup.md) retains its passed cloud
gates and verified public downloads.

<!-- CodexAstraUlt: Preserve code 14's separate menu/intro results while
advancing the published CPU candidate without claiming a new Thor result. -->
The [code 14 Thor reports](docs/device-tests/0.0.8-preview4-dark-moon-thor.md) are
now available. The bounded menu run reaches file selection at **17.31% emulated
speed** with choppy audio. A separate owner intro session runs at **16.66%**;
the owner reports **no graphical glitches**, and the report records no
runtime/rendering errors. These different scenes and durations do not establish
a performance improvement. The menu and intro retain 1,382 and 2,793 audio
underruns respectively; no new intro audio observation was supplied.

**0.0.8-preview.5/code 15 is published.** It specializes attribute decoding,
checks GPU health without copying the full report after every dispatch, and
records fixed SVC/frame/audio timings with their nested command subsets.
Local correctness/runtime, retained-library APK and independent bundle checks
pass at implementation `f687911`; hosted main checks pass there, with tag
build/publication and independent public-download verification at `365c1a0`.
See the [build record](docs/builds/0.0.8-cpu-decode-followup.md). The previous
[code 14 build record](docs/builds/0.0.8-cpu-work-followup.md) preserves its own
source and artifact identities.

<!-- CodexAstraUlt: Preserve the earlier code 15 measurement and published
code 16 identities while recording its completed device evidence separately. -->
The [code 15 Thor test](docs/device-tests/0.0.8-preview5-dark-moon-thor.md) reaches
file selection at **16.70% speed**, with no reported runtime/rendering errors.
No improvement is established; the saved File 1 panel changes the post-A workload.
New counters identify **33.975 seconds of SVC work outside the PICA command-list
timer**, which can still include transfers and GPU synchronization. Another
6.779 seconds remains unclassified. No new audio observation was supplied.

**Preview.6/code 16 is published.** It projects completed CPU shader outputs
directly into compact raster vertices and adds fixed SVC/service/GSP attribution
for the previously unclassified nested work. Local correctness/runtime,
retained-library APK, independent bundle and hosted main checks pass at
`64f1404`; tag publication and independent public-download
verification pass at `2354ed0`.
The [code 16 Thor test](docs/device-tests/0.0.8-preview6-dark-moon-thor.md) is now
complete: file selection at **18.70% speed**, no reported runtime/rendering
errors or visible corruption, A at 91.056 seconds and Stop at 110.111 seconds.
The single comparison with code 15's 16.70% does not establish a sustained or
causal gain. Display transfers (**26.917 s**) and texture copies (**6.061 s**)
account for 97.82% of SVC time outside PICA lists. Audio retains 1,532 underruns
and 160 discarded input frames, without a fresh listening assessment.

<!-- CodexAstraUlt: Publish verified transfer work without treating cloud
correctness or component measurements as a new private handheld speed result. -->
**Preview.7/code 17 is published.** Accepted tiled-output hardware transfers
now defer capture/presentation/submission, bounded to 32 transfers per batch,
with surface revalidation and separate logical cache idleness. The previous
linear route and texture-copy visibility remain unchanged. Fixed route/phase
metrics distinguish the work. Local correctness/runtime, retained-library APK,
independent bundle and hosted main checks pass at `9296010`;
tag publication and independent public-download verification pass at
`1c7fffa`. The new Thor test is **unperformed**, and no handheld speed
gain is established. Native execution, CPU vertex shaders and Vulkan 1× remain
the priority. No unchanged code 16 run is needed. Gameplay, reliable audio,
save/resume and sustained speed remain unqualified.

<!-- CodexAstraUlt: The owner's connection instruction requires an actual pause,
while cloud development and preparation of a reviewable package may continue. -->
Before any new Thor/ADB connection or device-work batch, including discovery,
export, installation or testing, **signal the owner and stop until explicit
approval**. Notification alone is not approval. Cloud work can continue; prepare
the compatible package before requesting connection approval when possible.
The [local procedure](docs/ANDROID_TITLE_BUILD.md#current-dark-moon-repackaging-and-audio-test)
preserves existing libraries, signer, imports, saves and reports. Further Thor
GPU tests remain deferred.

<!-- CodexAstraUlt: Add actual owner evidence without promoting the original
test guest to a playable owned title or the whole 0.0.7 milestone. -->
The [0.0.7-preview.2 Thor report](docs/device-tests/0.0.7-preview2-thor-title.md)
records 368,884 native instructions and 5,658 Vulkan draws with no reported
runtime errors or software raster fallback. Its title-artifact hashes match that
historical preview. The owner confirmed both images, D-pad/A, touch, pause/resume
and steady sound for that build. Those observations remain separate from the
new candidate's pending device check and the private Dark Moon result above.

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
1,999,970 native instructions with raw CPU/scheduler differences. The
[completed follow-up](docs/host-tests/dark-moon-native-2026-11-02.md) has matching
first-checkpoint scheduling and one matching synchronized state, while raw CPSR
differences remain. General mutable native code remains unfinished. The owner
has since completed the separate ARM64 compilation and reported private menu
boot on Thor; host results alone did not establish that device result.

The corrected-device evidence now includes measured touch and view recreation
plus the owner's steady-tone confirmation. Automated success alone cannot qualify
human observations. Original NCCH fixtures
do not establish a 3DSX loader or broad retail-title support. Dark Moon's playable
route and the other primary titles remain separate qualification work, using
private local inputs. See the [title build instructions](docs/ANDROID_TITLE_BUILD.md)
for current packaging and signing.

<!-- CodexAstraUlt: Persist the owner's report-driven release instruction in the
public overview without promising background execution or bypassing hardware. -->
After each owner-supplied report, cloud development proceeds to the next
qualified build through 0.1.0 without a routine approval round. Failed gates
receive diagnosis and a corrective build before promotion. New Thor/ADB access
requires signaling the owner and waiting for explicit approval, as above.

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
