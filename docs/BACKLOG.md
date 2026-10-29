# DroidDS implementation queue

<!-- CodexAstraUlt: Reduce the supplied 119-ticket catalog to bounded work packages with explicit tests and links back to the source requirements. -->

<!-- CodexAstraUlt: Record the delivered CPU subset and the resolved current
probe notice inventory; keep full-runtime and broader semantic gates open. -->
DDS-001/002 now have a pinned CPU dependency inventory, original workspace, build
runner and passing local checks. The current Android probe's distribution notice
inventory is resolved by the reviewed collector and
[third-party notice record](../THIRD_PARTY_NOTICES.md); full-runtime/platform
qualification remains open. DDS-003's bounded first fixture
scope is implemented: four native/interpreter cases, strict expected results and
negative controls. See [build evidence](builds/0.0.1-foundation.md).
<!-- CodexAstraUlt: Replace the pending Thor CPU status with validated uploaded
results without treating its self-reported metadata as a fresh ADB/package bind. -->
DDS-010 now has a CPU loader APK/build audit, local ADB runner and a passing
[owner-supplied Thor CPU report](device-tests/0.0.2-thor-cpu.md): four cases and
two negative controls on reported Android ARM64 with 4 KiB pages. The
[0.0.3 Thor CPU/Vulkan report](device-tests/0.0.3-thor-cpu-vulkan.md) also passes:
nine exact readbacks and nine pixel-mutation controls on Adreno 740/Android 13.
Those reports do not qualify actual PICA, picker lifecycle, sustained memory or
the remaining platform gates. Version 0.0.3's APK and host rendering checks also pass. See
[the build evidence](builds/0.0.3-android-vulkan.md) and [the probe](ANDROID_PROBE.md).
<!-- CodexAstraUlt: Advance the bounded runtime with the validated Thor report
and keep upcoming interactive-device work distinct from automated evidence. -->
Version 0.0.4 implements bounded subsets of DDS-004/005/010: eight CPU cases,
code-origin/changed-code/write-protection controls, full-renderer capability
queries and a representative Vulkan backend pipeline fixture. The owner's
[0.0.4 Thor report](device-tests/0.0.4-thor-runtime-probe.md) passes its required
checks. Optional dynamic blend/logic state is absent, so the actual renderer
must also pass forced-static host tests. The manual upload does not independently
bind an installed APK hash or establish gameplay performance.

The [0.0.5 runtime integration](builds/0.0.5-runtime-integration.md) implements
bounded portions of DDS-004/005/006/007/008/012: an original guest-driven NCCH
fixture reaches real loader, kernel, services and PICA code through interpreter,
native/software and native/Vulkan routes, with an independent asymmetric pixel
oracle. Compiler budget-boundary and Vulkan validation defects found during
execution are corrected. Compiler admission and retained-object counts are
limited; diagnostic evidence rejects unexpected software raster fallback and
resource-limit events. All required source-bound host and CI gates pass; the
[0.0.5 prerelease](https://github.com/RegiRex/DroiDDS/releases/tag/v0.0.5-probe.1)
is published and its public downloads are verified after
[run 39341905818](https://github.com/RegiRex/DroiDDS/actions/runs/39341905818).
The owner's [0.0.5 Thor report](device-tests/0.0.5-thor-runtime.md) now passes
three actual guest routes, five memory layouts and runtime code guards. The
hardware route uses CPU vertex shading and static-state Vulkan rasterization
without software raster fallback. No retail title is qualified by this fixture.

<!-- CodexAstraUlt: Record the implemented DDS-012 subset and local verification
while retaining separate verified publication and manual-device acceptance. -->
[0.0.6](builds/0.0.6-interactive-homebrew.md) develops bounded DDS-012 integration:
an original NCCH guest uses HID/GSP/DSP HLE, three automatic routes compare images
and PCM, and an Android frontend presents 400×240/320×240 readbacks with
Bitmap/Canvas, D-pad/A/touch input and resampled guest audio. A single session
thread owns runtime pause/resume and exit. Both guest views share one Android
display; physical dual-display output is not included. All 0.0.5 regressions
remain required, with the package expanded to twelve native libraries.
Implementation, final local/main/tag CI gates and independent public-download
verification pass; the prerelease is published. The combined Thor evidence
below now covers images, controls/touch, audible audio, lifecycle recovery and
normal exit sufficiently to proceed into 0.0.7 development. The latest report's
standalone missing-A result remains separate; automatic success alone is insufficient.

<!-- CodexAstraUlt: Combine corrected device measurements with the owner's
steady-tone confirmation without rewriting the original missing A observation. -->
The [corrected 0.0.6 Thor report](device-tests/0.0.6-correction2-thor.md)
passes every automatic check and records 42 submitted/consumed touch frames,
six view replacements and working pause/resume. Both guest views and sound are
confirmed. Audio underruns fell from 197 to 11 across different-duration runs;
the owner confirmed on 2026-10-20 that the tone “Sounded steady.” The combined
0.0.6 evidence supports 0.0.7 development. This run omitted A;
unchanged-path evidence from the earlier run is retained separately. No new
full test is required solely because A was omitted.

Generic [local private-title reconnaissance](PRIVATE_TITLE_RECONNAISSANCE.md)
is implemented and passes the [host verification gates](builds/0.0.7-reconnaissance-tools.md).
It identifies an owned game's first observed runtime blocker. This
interpreter/software host tool does not promote milestone 0.0.7 or produce a
game-playing Android APK.

The [New 3DS audit](NEW3DS_AUDIT.md) now leads to implemented loader/header,
physical-region, commitment-limit and configuration/service corrections with
original regression cases. Broader floating-point, scheduler, CRO lifecycle,
private-title and sustained-memory gates remain open. The 256 MiB staging-ring
baseline, surfaces/textures/driver memory and first-use static generic pipeline
compilation still require measurement and optimization. Disabling the optional
CPU PICA JIT avoids its unqualified worker policy; it does not qualify that JIT.
The table defines acceptance, not completion of every related ticket.
The original [119-ticket catalog](research/2026-10-17/06_IMPLEMENTATION_BACKLOG.md)
is reference material, not an instruction to implement everything at once.

<!-- CodexAstraUlt: Connect task-level work to the requested alpha release plan;
target versions do not override acceptance checks or claim unfinished work. -->
The [versioned roadmap through 0.1.0](ROADMAP.md#versioned-path-to-010) maps these
tickets to user-visible builds: first real 3DS homebrew on Android at target
0.0.6, first owned-game boot at 0.0.7 and a playable segment at 0.0.8. These are
planned release gates, not completed results or fixed delivery dates. Resource
bounds start during runtime integration; 0.0.9 stresses and refines them.

<!-- CodexAstraUlt: Ground upcoming private-title work in exact identity,
local signing and durable data ownership before claiming a game build. -->
The [0.0.7 private title build plan](PRIVATE_TITLE_BUILD_PLAN.md) specifies the
local builder, matching data import, signing/save identity and host/Thor boot
checks. It records the compiler/loader update mismatch and keeps private inputs
on the owner's Linux computer. This is planned work after the 0.0.6 gate.

<!-- CodexAstraUlt: Advance a concrete native prerequisite independently of
the private guest activation trace, retaining the remaining delivery work. -->
The [permission-remap correction](builds/0.0.7-memory-remap.md) now prevents
revoked read/write access through stale fast pointers. General native-code
freshness and private packaging remain open.
<!-- CodexAstraUlt: Mark preparation as implemented without treating its identity
record as already enforced by a native runtime or Android package. -->
[Native-source preparation](PRIVATE_TITLE_PREPARATION.md) now resolves strict
base inputs, excludes ambient hints, checks compiler/runtime reader agreement,
emits C and binds its inputs/outputs in a SHA-256 manifest. Consuming that manifest
before native execution and packaging remains work. Run-019 closes the bounded
voice trace without demonstrating an audio defect. Private preparation run-002
passes with corrected streaming admission and an explicit 1024 MiB allowance.
[Bounded host compilation](PRIVATE_TITLE_COMPILATION.md) is implemented and tested
on originals, with verified object reuse and static library identity audits. The
private compilation now completes 521/521 objects after three bounded resumes,
with a linked/static-validated library and no execution. The next task is
[guarded native comparison](PRIVATE_TITLE_NATIVE_RUN.md), using new manifest/table
admission and an immutable-base fence while modules stay interpreted. General
mutable-code support and private execution qualification remain open. See the
[compilation record](host-tests/dark-moon-compilation-2026-10-28.md).
No repeated unchanged interpreter prefix is required.

| Ticket | Scope and concrete output | Acceptance | Depends on | Pack mapping |
| --- | --- | --- | --- | --- |
| DDS-001 | Source map, exact dependency resolution, ABI/generation inventory, notice inventory, architecture decision records | Verifier/runtime mismatch addressed explicitly; actual ABI documented; proposed vs observed claims separate; missing license notice provenance tracked | This plan | NRR-0002/0005/0101/0301/0401 |
| DDS-002 | Minimal workspace and repeatable Linux build; exact Rust/compiler/tool pins and locked Cargo graph | Clean checkout builds without private data; source-pin mismatch fails; meaningful existing tests execute and skips are explicit | 001 | NRR-0001/0004/0102–0105/0107 |
| DDS-003 | Tiny original ARM/Thumb fixture, real C generation/loading, strict comparator | Counted native and fallback execution match known outputs; deliberately wrong integer/memory results fail; timeouts report inconclusive; no compiler means failure/explicit skip | 002 | NRR-0106/0203–0205; TEST-001/002 |
| DDS-004 | Expand CPU transitions, VFP policy and scheduler-edge corpus | Flags, shifts, interworking, unsupported instructions, SVC, nested fallback/unwind, exclusive accesses and tiny budgets behave correctly; checkpoint policy documented | 003 | CPU-001–009/014/015 |
| DDS-005 | Module/code freshness policy and regression cases | Origin mismatch, absent metadata, changed executable bytes, multiple CRO bases, unload/reload and stale direct calls never execute invalid native code | 003 | NRR-0206/0207; CPU-010–013 |
| DDS-006 | Execute existing GPU tests; capture pipeline creation thread/phase and state-family coverage | Real Vulkan execution reported; fixed independent expected cases added; startup vs gameplay vs explicit wait distinguished; first generic/helper misses reproduced | 002 | NRR-0401–0405; GPU-001–008 |
| DDS-007 | Ready accurate fallback for the tested pipeline/capability families | Delayed/failed/absent workers, dynamic blend/logic differences and unseen states preserve correct complete draws without hidden synchronous specialization; uncovered mandatory families fail the gate | 006 | NRR-0406–0409; GPU-004/007/011 |
| DDS-008 | Bound Vulkan and CPU PICA-JIT admission, results, retained objects and logs | Unique-state flood and duplicate jobs stay within configured counts; no blocking queue push; failures don't retry forever; title switch/shutdown retires objects safely; memory tracked | 006; integrate with 007 | NRR-1003/1005 moved earlier; THR/OBS |
| DDS-009 | Harden existing driver cache identity, persistence, quotas and invalidation | Corrupt/truncated/mismatched cache ignored safely; existing atomic replacement retained; write quota and runtime limits checked; private paths Android-safe | 006 | CACHE-002/004–006/010 |
| DDS-010 | Early NDK/Bionic ABI and Vulkan smoke probe | Public fixture executes on Thor; ABI/ELF dependencies and static 16 KiB ELF/APK alignment checked; host page size recorded; actual Vulkan device and representative generic pipeline create and draw | 003; source audit may begin after 001 | NRR-0302–0304/0601/0602 |
| DDS-011 | Private Linux control-title scenario plus early Dark Moon reconnaissance | Exact revision, routes and cache scope recorded; native/fallback counters; save round trip; bounded memory; separate Dark Moon compatibility findings | 004/005/007/008/009 | NRR-0201/0202/0209/0210/0801/0802 |
| DDS-012 | Android host around core crates, initial two-screen viewport, input/audio/SAF and lifecycle | Public fixture works; surface changes/pause/audio routing/reconnect/process death recover; no desktop runtime or mandatory services; touch mapping correct | 010, 004/005/007/008/009 | NRR-0501–0508/0512/0603–0608 |
| DDS-013 | Private local builder and package/data identity workflow | Stable per-title package ID/signing; wrong revision blocked for AOT; progress/cancellation; space checks; save-safe upgrade; artifact destinations remain private | 010/012 | NRR-0701–0707 |
| DDS-014 | Private Android control-title slice and reusable device runner | Actual Thor AOT execution, graphics/audio/input/save; repeated cold/warm normal-speed measurements; memory and teardown gates pass; one device operator | 011/012/013 | NRR-0803–0808 |
| DDS-015 | Dark Moon-specific diagnosis and correction | Matching opening moon/ghost clips; CPU/HLE/PICA route evidence; minimized reproducer for each fault; no-glitch acceptance separate from speed; long-run memory evidence | 014; early diagnosis in 011 | Owner goal; TEST-006/013/014 |
| DDS-016 | Stage-specific performance and product qualification | 1×/2×/4× matrix, sustained thermals/memory, Thor physical-display test; regression title matrix; each claimed improvement has a matched baseline | 014; Dark Moon claims require 015 | PERF/TEST; later M6/M7 work |
| DDS-017 | [Automatic encrypted-title import](ENCRYPTED_TITLE_IMPORT.md): one bounded normalization stage shared by compiler/runtime, explicit local keys/seeds, original and decoded identity binding | Original encrypted fixtures decode exactly; wrong/missing keys, seeds and hashes reject; no secrets in reports; cancellation/space bounds; one matched private revision and separate Android qualification | 013; runtime manifest consumption for native execution | Owner import-usability request; optional to current decrypted-title gate |

<!-- CodexAstraUlt: Add the owner's automatic-decryption request as a separate
import task; it does not reopen the successful decrypted-title preparation. -->
DDS-017 is planned; automatic decryption is not yet implemented. The current
decrypted Dark Moon preparation and compilation remain valid without this feature.

## Foundation context and continuation

Deliver a source/ABI map, version/feature manifest and one reproducible Linux build
entry point. Use the exact commits in the [review](RESEARCH_REVIEW.md); preserve
upstream history/notices. Choose dependency integration after examining the
existing Cargo graph. Do not recreate upstream's compiler abstraction or ABI.

<!-- CodexAstraUlt: Retain ongoing provenance checks without reopening the
current probe's resolved notice hold; new components require their own review. -->
Validation must record the compiler, Rust version, upstream SHA, verifier CPU SHA,
feature flags, lockfile hashes, command exit status, executed tests and explicit
skips. A clean build with zero relevant tests is build evidence only. Preserve
the current probe's complete generated distribution notices and review additions
or dependency changes against actual source declarations and supplied notices;
the pack's MIT summary does not replace that inventory.

DDS-003 now supplies separate ARM/Thumb cases, actual native ARM-to-Thumb
interworking, fixed memory output and intentional missing-entry fallback. Continue
with DDS-004/005 beyond 0.0.4's finite-VFP, reverse interworking, tiny-budget and
bounded code-safety cases. Version 0.0.5 adds actual runtime SVC/service
execution, missing-entry interpreter resumption and executed ARM/Thumb loop-budget
regressions; broad VFP, scheduling and CRO coverage remain follow-up work.
A missing-compiler skip cannot pass DDS-003/M1 or unblock A0. Static 16 KiB
alignment checks do not establish runtime compatibility on a 16 KiB-page host;
record that execution as untested unless such a device actually runs the fixture.

<!-- CodexAstraUlt: Replace already-implemented New 3DS tasks with qualification
and remaining coverage, without promoting a public fixture to Xenoblade support. -->
Version **0.0.5** ships the bounded
[New 3DS integration work](builds/0.0.5-runtime-integration.md): corrected header
bits, physical regions and title commitment limits resolved before construction,
matching configuration/model data, allocation-boundary and reserved-mapping
checks, and restore preflight. Host/CI, publication and five bounded memory-layout
cases in the owner's 0.0.5 Thor report pass. Scheduling, clocks/audio,
remaining services and general module lifecycle need their own cases. Xenoblade's
private header/boot baseline remains necessary; neither the public fixture nor
the passing Thor fixture reports establish title compatibility. The 0.0.6 DSP
HLE tone exercises a narrow audio path, not DSP firmware or complete title audio.

## Work to defer until evidence supports it

Portable pipeline journals and prewarm; GUI builder; universal title launcher;
on-device compilation; custom shader replacement/compute rasterization; wholesale
Azahar integration; broad enhancement/mod framework; automatic online services;
large compatibility dashboards. HD textures remain a goal, with memory and
correctness qualification before enabling them in a default profile.

Do not file 119 GitHub issues automatically. Turn the next small batch into issues
when execution begins, keeping this queue as the dependency map. Parallel reviews
are useful; competing renderer rewrites or simultaneous benchmarks are not.
