# DroidDS

<!-- CodexAstraUlt: Replace the initial placeholder with the owner's recompilation project plan, its evidence limits, and the next implementation step. -->

An Android ARM64 3DS recompilation project, planned around **3dsrecomp + Zakuro**.
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
reported. Full renderer capability, lifecycle and game qualification remain open;
the JSON does not record which export method was used.

<!-- CodexAstraUlt: Advance to the expanded diagnostic without treating original
backend operations or reproduced New 3DS defects as game integration. -->
Version **0.0.4** expands the CPU corpus to eight cases, adds executable-code
freshness/write protection controls, and tests the pinned renderer's Vulkan 1.3
requirements with actual texture, depth/stencil and compute operations. The
[0.0.4 prerelease](https://github.com/RegiRex/DroidDS/releases/tag/v0.0.4-probe.1)
is the next ARM64 diagnostic. Launch **DroidDS Probe**, wait for the result, then
use **Save report**. Device qualification remains pending until its own report
passes; 0.0.3's pass does not qualify the new checks. See
[Android instructions](docs/ANDROID_PROBE.md) for installation and signing details.

The [New 3DS audit](docs/NEW3DS_AUDIT.md) executes the pinned parser/allocator with
original headers and reproduces incorrect header decoding and application-memory
limits. These are concrete integration tasks for 0.0.5; no Xenoblade execution or
fix is claimed.

This is an original DroidDS integration workspace using pinned 3dsrecomp compiler/
ABI and Zakuro CPU components. HLE services and game execution are not integrated
in these diagnostic APKs. The original Vulkan fixtures exercise backend features,
not PICA translation or game performance. Continue from the roadmap's runtime,
CPU lifecycle and actual PICA qualification gates.

<!-- CodexAstraUlt: Persist the owner's report-driven release instruction in the
public overview without promising background execution or bypassing hardware. -->
After each owner-supplied report, development proceeds to the next qualified build
through 0.1.0 without a routine approval round. Failed gates receive diagnosis and
a corrective build before promotion; required hardware/input decisions remain
explicit.

| Read | Purpose |
| --- | --- |
| [Build and run](docs/BUILDING.md) | Reproduce the first Linux CPU foundation |
| [Android CPU/Vulkan probe](docs/ANDROID_PROBE.md) | Build the ARM64 test app and run it on the Thor |
| [Thor CPU result](docs/device-tests/0.0.2-thor-cpu.md) | Owner-supplied 0.0.2 execution and its qualification boundary |
| [Thor CPU/Vulkan result](docs/device-tests/0.0.3-thor-cpu-vulkan.md) | Passing 0.0.3 hardware readbacks and remaining renderer gates |
| [0.0.4 build evidence](docs/builds/0.0.4-runtime-probe.md) | Expanded CPU, renderer operations and packaging checks |
| [New 3DS audit](docs/NEW3DS_AUDIT.md) | Reproduced parser/memory defects and integration fixes required |
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
