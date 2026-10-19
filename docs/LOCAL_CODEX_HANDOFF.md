# Local implementation handoff

<!-- CodexAstraUlt: Supply an executable project direction without silently starting implementation or requiring a cloud-to-local session bridge. -->

<!-- CodexAstraUlt: Continue from the validated Thor 0.0.4 report and implemented
0.0.5 runtime candidate rather than repeating completed foundation work. -->
As of 2026-10-19, the owner's
[0.0.4 Thor report](device-tests/0.0.4-thor-runtime-probe.md) passes all required
CPU/code-safety and Vulkan checks. The
[0.0.5 runtime integration candidate](builds/0.0.5-runtime-integration.md) is
implemented; its final source-bound build/publication gates and Thor execution
are pending. Read [build instructions](BUILDING.md) and
[Android probe instructions](ANDROID_PROBE.md) for the current gate and artifact.
The existing Nobara laptop and USB-connected Thor can host the private
development/test loop once their current readiness is checked. This cloud chat
does not share a live session, device connection or private files with local Codex.

## Starting scope

Work in a separate DroidDS checkout. Read `AGENTS.md`, `docs/RESEARCH_REVIEW.md`,
`docs/ARCHITECTURE.md` and `docs/BACKLOG.md`. Keep Uberhar files, APK and saves intact.
Check branch and local changes before fetching; do not reset another session's work.

<!-- CodexAstraUlt: The next local task is qualification of the actual runtime
candidate; the owner's standing authorization covers subsequent roadmap builds. -->
Do not repeat 0.0.4 routinely. Its Thor report also shows that optional dynamic
blend/logic state is absent; retain the forced-static renderer gate. The 0.0.5
candidate uses selected Zakuro loader/core/GPU sources and the corrected
3dsrecomp compiler to execute an original guest through real SVC/service IPC and
two PICA draws. Three CPU/rendering routes must match an independently decoded
asymmetric 8×8 image. This is bounded public-fixture evidence, not retail support
or complete PICA coverage. GPU rasterization may use CPU vertex shading on
integrated devices; the report records that mode explicitly.

Complete the final 0.0.5 gates, verify its published diagnostic artifact when
available, then obtain the owner's actual Thor runtime report. Save failures and
partial reports too. After a validated report, proceed directly into fixes and
the next roadmap build through 0.1.0 under the owner's standing instruction;
a failed gate requires a corrective build before promotion. The next planned
0.0.6 work is visible interactive 3DS homebrew and Android lifecycle behavior.
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
using actual boot evidence. The 0.0.5 candidate corrects New 3DS header decoding,
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
The candidate limits compiler admission and some retained objects but still has
a 256 MiB staging-ring baseline and unqualified surface/texture/driver memory.
Static generic pipelines can still compile synchronously on first use. Require
matched cold/warm and long-run evidence before claiming those problems solved.

## Suggested task to give local Codex when ready

> Continue DroidDS from its implemented 0.0.5 runtime candidate. Read AGENTS.md,
> docs/builds/0.0.5-runtime-integration.md,
> docs/device-tests/0.0.4-thor-runtime-probe.md and docs/ANDROID_PROBE.md.
> The owner's 0.0.4 required checks pass; 0.0.5 publication and Thor execution
> remain pending until verified. Finish source-bound gates, verify the published
> diagnostic artifact when available, and run it on the authorized Thor's explicit
> ADB serial. Preserve a failed/partial report and record actual execution
> separately from compilation. After the report passes, continue into the next
> roadmap build under the standing authorization through 0.1.0; do not bypass
> failed gates. Keep private-title, scheduler, CRO and sustained-memory gates open.
> Use CodexAstraUlt comments, preserve local
> changes, keep all retail inputs/derived outputs private, and leave Uberhar intact.
> Do not execute the archive's entire prompt pack or claim Android/game readiness
> from compilation alone. Checkpoint after each ticket and report concrete blockers.

The owner can give this task to the local session. This document does not itself
connect sessions or start unattended local/device work.
