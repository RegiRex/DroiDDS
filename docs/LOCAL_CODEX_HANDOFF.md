# Local implementation handoff

<!-- CodexAstraUlt: Supply an executable project direction without silently starting implementation or requiring a cloud-to-local session bridge. -->

<!-- CodexAstraUlt: Continue from the passed bounded runtime report into
interactive-device qualification without claiming a cloud/local session bridge. -->
As of 2026-10-19, the owner's
[0.0.5 Thor report](device-tests/0.0.5-thor-runtime.md) passes all required
CPU/Vulkan/runtime, five memory-layout and code-safety checks. The
[0.0.5 runtime integration](builds/0.0.5-runtime-integration.md) is published in
[prerelease v0.0.5-probe.1](https://github.com/RegiRex/DroidDS/releases/tag/v0.0.5-probe.1).
All required host/CI gates pass in
[run 39341905818](https://github.com/RegiRex/DroidDS/actions/runs/39341905818),
and public downloads are verified. **0.0.6 interactive homebrew is implemented
and published. Local/main/tag CI gates and independent public-download
verification pass; manual Thor qualification remains pending. No
retail title is qualified.** Read [build instructions](BUILDING.md),
[0.0.6 scope](builds/0.0.6-interactive-homebrew.md) and
[Android probe instructions](ANDROID_PROBE.md) for the current gate and artifact.
The existing Nobara laptop and USB-connected Thor can host the private
development/test loop once their current readiness is checked. This cloud chat
does not share a live session, device connection or private files with local Codex.

<!-- CodexAstraUlt: Update the interactive gate from the received report;
physical dual-display expectations do not imply a missing guest image. -->
The [first 0.0.6 Thor report](device-tests/0.0.6-thor-homebrew.md) passes
all automatic checks, and the owner confirms both guest views on the top
physical screen. Measured guest touch, view recreation and audio continuity
still need a focused retest. The [frontend correction](builds/0.0.6-frontend-correction.md)
retains version 0.0.6 with install code 7; it does not promote milestone 0.0.7.
Read its build status before installing or claiming publication.

<!-- CodexAstraUlt: Ground upcoming private-title work in exact identity,
local signing and durable data ownership before claiming a game build. -->
The [0.0.7 private title build plan](PRIVATE_TITLE_BUILD_PLAN.md) specifies the
local builder, matching data import, signing/save identity and host/Thor boot
checks. It records the compiler/loader update mismatch and keeps private inputs
on the owner's Linux computer. This is planned work after the 0.0.6 gate.

## Starting scope

Work in a separate DroidDS checkout. Read `AGENTS.md`, `docs/RESEARCH_REVIEW.md`,
`docs/ARCHITECTURE.md` and `docs/BACKLOG.md`. Keep Uberhar files, APK and saves intact.
Check branch and local changes before fetching; do not reset another session's work.

<!-- CodexAstraUlt: The next device task is visible original-guest qualification;
retain existing reports and the owner's report-driven continuation instruction. -->
Do not repeat 0.0.4/0.0.5 manually without a relevant change. Their Thor reports show optional dynamic
blend/logic state is absent; retain the forced-static renderer gate. Version 0.0.5
uses selected Zakuro loader/core/GPU sources and the corrected
3dsrecomp compiler to execute an original guest through real SVC/service IPC and
two PICA draws. Three CPU/rendering routes must match an independently decoded
asymmetric 8×8 image. This is bounded public-fixture evidence, not retail support
or complete PICA coverage. The actual Thor result uses CPU vertex shading with
Vulkan rasterization; retain that distinction in future reports.

The 0.0.6 local/main/tag CI gates pass and its public downloads are verified.
Use the [published prerelease](https://github.com/RegiRex/DroidDS/releases/tag/v0.0.6-probe.2) for the manual Thor test.
The original NCCH guest must visibly display its 400×240
and 320×240 images, respond to D-pad/A/touch and produce audible guest audio.
Both views use CPU readback/Bitmap/Canvas on one Android display while PICA
rasterization remains Vulkan. Do not claim Thor physical dual-display support.
Guest PCM is resampled from 32728.498046875 Hz to Android 48000 Hz; a tone is not
DSP firmware compatibility. Verify pause/resume, view replacement and normal exit.
Automatic image/PCM success alone cannot qualify these human observations or
permit 0.0.7 promotion. Record installed artifact identity where ADB is available.
Save failed/partial reports too. After the required gate passes, proceed directly
into fixes and the next roadmap build through 0.1.0 under the owner's standing
instruction; failed gates require correction before promotion.
Do not attempt all archive prompts or claim a background device/session bridge.
Public fixture work needs no game upload or retail APK.

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

For each new device run, check `adb devices -l`, select the authorized Thor's
explicit serial, and record device/driver and installed artifact identity.
Authorize USB on the device if needed. Test only the new synthetic DroidDS package;
do not uninstall Uberhar, reuse its signing key or clear its application data.
Any game/cache reset follows explicit local owner scope and keeps unrelated data.

<!-- CodexAstraUlt: Preserve the private title matrix after implemented New 3DS
loader fixes; public model/memory tests do not replace private boot evidence. -->
Primary private targets are Dark Moon, Xenoblade Chronicles 3D and Sonic &
All-Stars Racing Transformed. Monster Hunter 4 Ultimate is an optional comparison.
Confirm available local files and exact revisions; choose the first control
using actual boot evidence. Version 0.0.5 corrects New 3DS header decoding,
physical regions, title commitment limits and configuration/model reporting,
with loader/allocation regression cases. Xenoblade's private header, services
and boot still need separate evidence; scheduling and clocks/audio remain open.
Use the
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
application artifact, satisfy DroidDS's versioning, signing and four-file release
gates. Preserve the current diagnostic signing limitation; stable product signing
remains separate work before private-title packages.

<!-- CodexAstraUlt: Keep unresolved architecture gates explicit when handing
off a functioning bounded fixture, so a successful image cannot close them. -->
Keep general CRO unload/remap/concurrent-code safety, full scheduling/services,
private control-title runs, and sustained memory/teardown qualification open.
Version 0.0.5 limits compiler admission and some retained objects but still has
a 256 MiB staging-ring baseline and unqualified surface/texture/driver memory.
Static generic pipelines can still compile synchronously on first use. Require
matched cold/warm and long-run evidence before claiming those problems solved.

## Suggested task to give local Codex when ready

> Continue DroidDS from the passing 0.0.5 Thor runtime report. Read AGENTS.md,
> docs/device-tests/0.0.5-thor-runtime.md,
> docs/builds/0.0.6-interactive-homebrew.md and docs/ANDROID_PROBE.md.
> Version 0.0.6 is published with passing local/main/tag CI gates and verified
> public downloads. Its manual Thor gate remains pending. Retain all prior
> regressions, then run the automatic probe and manual original-homebrew test
> on the authorized Thor's explicit ADB serial and record installed APK identity.
> Verify visible guest screens, D-pad/A/touch, audible tone, pause/resume, view
> replacement and normal exit. A passing automatic JSON does not replace these
> observations. Preserve failed/partial evidence and distinguish CPU vertex
> shading, Vulkan rasterization and CPU-readback presentation. Continue through
> 0.1.0 under the standing instruction, but do not promote to 0.0.7 before this
> manual device gate passes. Keep private-title, scheduler, CRO and sustained-memory gates open.
> Use CodexAstraUlt comments, preserve local
> changes, keep all retail inputs/derived outputs private, and leave Uberhar intact.
> Do not execute the archive's entire prompt pack or claim Android/game readiness
> from compilation alone. Checkpoint after each ticket and report concrete blockers.

The owner can give this task to the local session. This document does not itself
connect sessions or start unattended local/device work.
