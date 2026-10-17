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

<!-- CodexAstraUlt: Android development follows the automated Linux gate without
requiring the owner to duplicate it manually. Device evidence remains separate. -->
**Android development has begun with the 0.0.2 CPU loader probe.** It cross-compiles
and packages those fixtures for ARM64/Bionic in a small test app. See
[Android build/device instructions](docs/ANDROID_PROBE.md). Actual Thor execution,
graphics and game compatibility remain unverified.

This is an original DroidDS integration workspace using pinned 3dsrecomp compiler/
ABI and Zakuro CPU components. HLE services, graphics and game performance are
not included in these CPU probes. Continue the CPU lifecycle/semantic gates,
Android device probe and graphics foundation from the roadmap.

| Read | Purpose |
| --- | --- |
| [Build and run](docs/BUILDING.md) | Reproduce the first Linux CPU foundation |
| [Android CPU probe](docs/ANDROID_PROBE.md) | Build the ARM64 test app and run it on the Thor |
| [Android build evidence](docs/builds/0.0.2-android-probe.md) | Executed package/regression checks and device gates still open |
| [First build evidence](docs/builds/0.0.1-foundation.md) | Results, scope, limitations and next work |
| [Additional reuse candidates](docs/REUSE_CANDIDATES.md) | AnyPS5, Azahar, Citra MMJ and Uberhar source review |
| [Architecture](docs/ARCHITECTURE.md) | Components, design decisions, boundaries and risks |
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
