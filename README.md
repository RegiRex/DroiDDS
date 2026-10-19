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

<!-- CodexAstraUlt: Link the new diagnostic release without claiming it runs a
game or qualifies PICA rendering from a small platform Vulkan fixture. -->
The **[0.0.3 Android probe prerelease](https://github.com/RegiRex/DroidDS/releases/tag/v0.0.3-probe.1)**
provides an installable ARM64 APK. Launch **DroidDS Probe** to run the CPU and
Vulkan checks automatically, then use **Save report** to choose a JSON destination.
See [Android instructions](docs/ANDROID_PROBE.md) and the release notes for its
diagnostic signing identity and installation requirements.

This is an original DroidDS integration workspace using pinned 3dsrecomp compiler/
ABI and Zakuro CPU components. HLE services, graphics and game performance are
not included in these diagnostic probes. The original Vulkan fixture establishes
an API path, not a PICA renderer. Continue the CPU lifecycle/semantic gates,
Android device probe and graphics foundation from the roadmap.

| Read | Purpose |
| --- | --- |
| [Build and run](docs/BUILDING.md) | Reproduce the first Linux CPU foundation |
| [Android CPU/Vulkan probe](docs/ANDROID_PROBE.md) | Build the ARM64 test app and run it on the Thor |
| [Thor CPU result](docs/device-tests/0.0.2-thor-cpu.md) | Owner-supplied 0.0.2 execution and its qualification boundary |
| [Thor CPU/Vulkan result](docs/device-tests/0.0.3-thor-cpu-vulkan.md) | Passing 0.0.3 hardware readbacks and remaining renderer gates |
| [CPU/Vulkan build evidence](docs/builds/0.0.3-android-vulkan.md) | Executed rendering/package checks and device gates still open |
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
