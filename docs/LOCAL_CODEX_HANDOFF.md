# Local implementation handoff

<!-- CodexAstraUlt: Supply an executable project direction without silently starting implementation or requiring a cloud-to-local session bridge. -->

<!-- CodexAstraUlt: Supersede the initial planning-only handoff after the first
verified CPU build; local work should reproduce it and continue the next gates. -->
DroidDS's first Linux CPU foundation build 0.0.1 passes in cloud. Read
[build instructions](BUILDING.md) and [the result](builds/0.0.1-foundation.md).
The existing Nobara laptop and USB-connected Thor can host the private
development/test loop once their current readiness is checked. This cloud chat
does not share a live session, device connection or private files with local Codex.

## Starting scope

Work in a separate DroidDS checkout. Read `AGENTS.md`, `docs/RESEARCH_REVIEW.md`,
`docs/ARCHITECTURE.md` and `docs/BACKLOG.md`. Keep Uberhar files, APK and saves intact.
Check branch and local changes before fetching; do not reset another session's work.

<!-- CodexAstraUlt: Replace the obsolete repeat-0.0.2 handoff after the owner's
passing 0.0.3 hardware report; continue broader gates without redoing known tests. -->
The initial CPU dependency/build/fixture batch is implemented. Automated Linux
checks and the owner's [0.0.3 Thor CPU/Vulkan report](device-tests/0.0.3-thor-cpu-vulkan.md)
pass; routine manual repetition is not a prerequisite. Continue 0.0.4's
DDS-004/005 CPU/code-safety work, full-renderer capability checks and the early
New 3DS audit. The small Vulkan fixture does not qualify full PICA rendering.
Do not attempt all prompts in the research archive. No game upload, full Android
frontend, release signing change or retail APK is needed for this first batch.

Use one coordinator and assigned-file ownership. Reviewers can independently audit
CPU semantics, GPU resource lifetimes and Android contracts. Only one agent performs
Thor operations; no concurrent benchmarks. At each completed ticket, record exact
commands/results, commit scope and the smallest next task. Use existing session
authorization for routine work and respect actual approval/account limits.

## Local inputs and device work

Public fixtures must work without private input. Later, select a user-supplied
local title path and preserve it outside Git, derived output outside public CI, and
saves outside disposable directories. A Proton link or chat upload is unnecessary
when the local agent already has an authorized local file path.

For A0, check `adb devices -l`, device properties and Vulkan capability evidence.
Authorize USB on the device if needed. Test only the new synthetic DroidDS package;
do not uninstall Uberhar, reuse its signing key or clear its application data.
Any game/cache reset follows explicit local owner scope and keeps unrelated data.

<!-- CodexAstraUlt: Carry the owner's primary test set into local device work;
New 3DS guest support is an early audit, and MH4U remains optional. -->
Primary private targets are Dark Moon, Xenoblade Chronicles 3D and Sonic &
All-Stars Racing Transformed. Monster Hunter 4 Ultimate is an optional comparison.
Confirm available local files and exact revisions; choose the first control
using actual boot evidence. Audit Xenoblade's New 3DS guest requirements during
0.0.4 and record implementation gaps before interpreting performance. Use the
[title matrix](TEST_STRATEGY.md#primary-title-matrix) and record each primary
title's result or blocker separately. Dark Moon opening reconnaissance is
required at M3 and becomes a separate correction/performance track. Its old
Uberhar moon observation
remains: Native has no observed flashing, Combo flashes segments. It is a temporal
comparison, with ghost corruption tracked separately; do not assume DroidDS has
the same defect until tested.

## Result record for each ticket

Include ticket and source commits, toolchain and lockfile identity, changed files,
commands and statuses, executed test counts and skips/inconclusive results,
device/driver where relevant, exact private scene identity without private content,
observed result versus expected result, remaining blockers, and next action.

Separate source-inspected, built and actually tested evidence. Publish generic
plans/code/fixtures only within the authorized DroidDS workflow. Keep private
title libraries, game APKs, captures and credentials local. Before publishing an
application artifact, establish DroidDS's own versioning, signing and release gates.

## Suggested task to give local Codex when ready

> Continue DroidDS from the published plans. Read AGENTS.md and the research review.
> Read docs/device-tests/0.0.3-thor-cpu-vulkan.md and docs/ANDROID_PROBE.md.
> The owner's basic CPU/Vulkan report passes. Continue one bounded 0.0.4
> CPU/code-safety, full-renderer capability or New 3DS audit task. For new device
> tests, select the authorized Thor's explicit ADB serial and record actual
> execution separately from compilation. Do not infer PICA/game compatibility
> from the existing tiny Vulkan fixture or repeat the old probe without a reason.
> Use CodexAstraUlt comments, preserve local
> changes, keep all retail inputs/derived outputs private, and leave Uberhar intact.
> Do not execute the archive's entire prompt pack or claim Android/game readiness
> from compilation alone. Checkpoint after each ticket and report concrete blockers.

The prompt is a proposed bounded implementation task for the owner to invoke; its
presence in this planning document does not start a local session automatically.
