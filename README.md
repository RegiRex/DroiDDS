# DroidDS

<!-- CodexAstraUlt: Replace the initial placeholder with the owner's recompilation project plan, its evidence limits, and the next implementation step. -->

An Android ARM64 3DS recompilation project, planned around **3dsrecomp + Zakuro**.
The desktop builder will translate supported guest CPU code into native libraries;
a shared runtime will retain 3DS services, graphics, audio and interpreter fallback.

**Status, 2026-10-17: planning and source reconnaissance. No DroidDS runtime,
APK, game compatibility result or performance improvement has been demonstrated.**

The first objective is a reproducible Linux synthetic fixture that executes both
recompiled and interpreted code, with trustworthy comparison results. A small
Android/Bionic loading experiment should run early to expose platform risks.
Real-title and sustained Thor testing follow those foundations.

| Read | Purpose |
| --- | --- |
| [Architecture](docs/ARCHITECTURE.md) | Components, design decisions, boundaries and risks |
| [Roadmap](docs/ROADMAP.md) | Ordered milestones with measurable exit gates |
| [Implementation backlog](docs/BACKLOG.md) | Bounded tasks, dependencies and acceptance checks |
| [Testing strategy](docs/TEST_STRATEGY.md) | CPU correctness, graphics continuity, memory and device tests |
| [Research review](docs/RESEARCH_REVIEW.md) | ZIP inventory, verified pins, source findings and corrections |
| [Local Codex handoff](docs/LOCAL_CODEX_HANDOFF.md) | How to start implementation on the Nobara/Thor setup |
| [Original research pack](docs/research/2026-10-17/00_README.md) | Preserved input; proposals and example prompts, not completed work |

CPU recompilation does not remove PICA graphics translation or guarantee smooth
cold runs. The inherited renderer has synchronous generic-pipeline creation and
resource-management gaps that must be measured and addressed. The owner's targets
remain correct cold gameplay at 4× where achievable, with substantial headroom at
2×, including Luigi's Mansion: Dark Moon. These are qualification goals.

DroidDS is separate from Uberhar. Reuse its testing lessons and device workflow;
review provenance before importing implementation. Keep retail inputs and all
derived code, assets, local packages and signing keys outside public source and CI.
