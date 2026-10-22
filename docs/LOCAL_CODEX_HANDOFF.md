# Local implementation handoff

<!-- CodexAstraUlt: Continue from the passed bounded runtime report into
interactive-device qualification without claiming a cloud/local session bridge. -->
As of 2026-10-20, the owner's
[0.0.5 Thor report](device-tests/0.0.5-thor-runtime.md) passes all required
CPU/Vulkan/runtime, five memory-layout and code-safety checks. The
[0.0.5 runtime integration](builds/0.0.5-runtime-integration.md) is published in
[prerelease v0.0.5-probe.1](https://github.com/RegiRex/DroidDS/releases/tag/v0.0.5-probe.1).
All required host/CI gates pass in
[run 39341905818](https://github.com/RegiRex/DroidDS/actions/runs/39341905818),
and public downloads are verified. **0.0.6 interactive homebrew is implemented
and published. Local/main/tag CI gates and independent public-download
verification pass; combined Thor evidence now supports the next development
stage. No retail title is qualified.** Read [build instructions](BUILDING.md),
[0.0.6 scope](builds/0.0.6-interactive-homebrew.md) and
[Android probe instructions](ANDROID_PROBE.md) for the current gate and artifact.
The existing Nobara laptop and USB-connected Thor can host the private
development/test loop once their current readiness is checked. This cloud chat
does not share a live session, device connection or private files with local Codex.

<!-- CodexAstraUlt: Carry forward the owner's steady-tone confirmation with
corrected device evidence, preserving the standalone missing-A qualification. -->
The [0.0.6 correction 2 report](device-tests/0.0.6-correction2-thor.md), reviewed
2026-10-20, now passes every automatic check and records both views, audible
sound, 42 guest-consumed touch frames, six view replacements and pause/resume.
The standalone manual qualifier remains pending because A was not consumed in
this run; unchanged-path historical evidence is recorded separately. The owner
confirmed on 2026-10-20 that the tone “Sounded steady” between intentional pauses.
This closes audible quality for this run; the eleven underruns remain recorded.
Combined evidence supports 0.0.7 development without a new full .6 replay. Do not
rewrite the latest JSON as a fresh A-button or zero-underrun observation.
The [verified correction](builds/0.0.6-frontend-correction.md) remains version
0.0.6 / install code 7. No private title or 0.0.7 APK is qualified.

<!-- CodexAstraUlt: A bounded local host baseline can expose the next real-title
blocker after the combined Android evidence supports the next stage. -->
The immediate development task is [private title reconnaissance](PRIVATE_TITLE_RECONNAISSANCE.md)
on the owner's Nobara laptop. The implemented host worker uses the interpreter
and software renderer in a fresh isolated run, without loading existing saves,
updates, DLC or user configuration. It does not compile a title, build an APK,
run Vulkan or establish playable speed. Use it to identify the first actual
loader/service/CPU blocker from an authorized local decrypted game file.

<!-- CodexAstraUlt: Advance from the owner's first bounded execution report
without promoting a timer event to a rendered frame or repeating setup. -->
The owner has now reported a [first local run](host-tests/dark-moon-2026-10-22.md)
that reached the default cycle budget with 316,366 interpreted instructions,
59 frame events and zero draws. Its ten-second follow-up still ended at
`0x004B23A8`, with 433,366 instructions, no acquired service handles or draws,
and unchanged sampled guest memory. Run-004's bounded trace then recorded 9,999
one-millisecond sleeps at `0x004B23A4`, each observed wake returning on its
deadline before another sleep. The [shared-page readiness correction](builds/0.0.7-shared-page-ready.md)
initializes a missing startup byte and passes an original guest regression on
both models. The owner's matched run-005 now records zero sleeps and reaches
five services and 80 IPC calls. It stops on the dispatch budget at `0x003B4FD8`
after 9,998,658 instructions and approximately 0.05774 emulated seconds, with
zero GPU/audio activity. The next local task is one run with bounded CPU progress
sampling and the same limits, to distinguish advancing startup work from a
repeated unchanged state. Rebuild offline and record the new worker hash;
preserve the input hash and earlier reports. These private-run records are
owner text, not independent JSON validation.

<!-- CodexAstraUlt: Ground upcoming private-title work in exact identity,
local signing and durable data ownership before claiming a game build. -->
The [0.0.7 private title build plan](PRIVATE_TITLE_BUILD_PLAN.md) specifies the
local builder, matching data import, signing/save identity and host/Thor boot
checks. It records the compiler/loader update mismatch and keeps private inputs
on the owner's Linux computer. This is planned work after the 0.0.6 gate.

## Starting scope

<!-- CodexAstraUlt: Reuse the existing DroidDS checkout while preserving the
separate Uberhar project and other local sessions' uncommitted work. -->
Work in the existing DroidDS checkout, separate from Uberhar. Read `AGENTS.md`, `docs/RESEARCH_REVIEW.md`,
`docs/ARCHITECTURE.md` and `docs/BACKLOG.md`. Keep Uberhar files, APK and saves intact.
Check branch and local changes before fetching; do not reset another session's work.

<!-- CodexAstraUlt: Carry the owner's laptop-cleanup preference into local work
without deleting preexisting software or requesting unnecessary new tooling. -->
The owner requests exact selective cleanup commands when version **0.1.0 is
built**. Follow [host setup cleanup](HOST_SETUP_CLEANUP.md): record the actual
DNF transaction, Rust ownership and project output paths now using read-only
checks; preserve uncertain or shared items. Install additional tools only for a
concrete need. Prepare cleanup for review later, without automatic removals.

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

<!-- CodexAstraUlt: Carry combined device evidence forward without asking for
unrelated replay or claiming the separate private-title gate has passed. -->
The 0.0.6 local/main/tag CI gates and public-download verification pass.
The [published correction](https://github.com/RegiRex/DroidDS/releases/tag/v0.0.6-probe.2)
now has the device evidence summarized above. Keep its 400×240 and 320×240
Bitmap/Canvas views on one Android display distinct from physical dual-display
support. Guest PICA rasterization uses Vulkan; guest PCM is resampled from
32728.498046875 Hz to 48000 Hz, without qualifying DSP firmware.
Retain the steady-tone observation and the control-attribution limits. No new
full .6 replay is needed solely for the closed audio question or omitted A.
Record installed artifact identity where ADB
is available and preserve failed/partial reports. The bounded host
reconnaissance below is the next local step. The combined .6 evidence is enough
to proceed; neither it nor a host diagnostic outcome completes the 0.0.7
private-boot gate.
Continue necessary fixes and the next qualified build through 0.1.0 under the
owner's standing instruction. Do not execute all archive prompts or claim a
background device/session bridge. No cloud game upload is needed.

Use one coordinator and assigned-file ownership. Reviewers can independently audit
CPU semantics, GPU resource lifetimes and Android contracts. Only one agent performs
Thor operations; no concurrent benchmarks. At each completed ticket, record exact
commands/results, commit scope and the smallest next task. Use existing session
authorization for routine work and respect actual approval/account limits.

## Local inputs and device work

<!-- CodexAstraUlt: Keep the first private baseline local and isolated instead
of importing existing saves or requesting unnecessary cloud transfers. -->
Public fixtures must work without private input. For the new host baseline,
local Codex should inspect the owner's already authorized paths, select the
exact decrypted title and follow [the reconnaissance procedure](PRIVATE_TITLE_RECONNAISSANCE.md).
Keep the original and each fresh output directory outside every Git checkout.
Do not supply an existing save/configuration tree or reset Uberhar data. A Proton
link or chat upload is unnecessary when the local agent has an authorized local
file path. Review the small diagnostic summary before sharing it; do not upload
the staged game copy, runtime files or other private derived material.

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

## Suggested task to give local Codex

<!-- CodexAstraUlt: Give the local session the executable next task, preserving
its filesystem knowledge and avoiding unnecessary manual command transcription. -->

> Update the DroidDS diagnostic source while preserving local changes. Read
> AGENTS.md, docs/PRIVATE_TITLE_RECONNAISSANCE.md and
> docs/host-tests/dark-moon-2026-10-22.md. Rebuild droidds-private-title with the
> existing pinned toolchain and locked dependencies, offline. Run the same authorized
> Dark Moon input once with --trace-scheduler --trace-cpu-progress and the run-005 limits:
> --max-steps 10000000 --max-cycles 2681118560 --max-frames 1200
> --max-seconds 120 --timeout 130. Keep other baseline settings unchanged and
> choose a fresh output directory outside Git. Confirm the input hash matches;
> record the rebuilt worker's new identity. Compare execution counters against
> run-005 and inspect cpu_progress for recurring PCs, changing registers and
> current thread identities near 0x003B4FD8. Report the final recent dispatch
> addresses and a compact comparison of the last relevant snapshots, plus the
> stop/blocker, service activity, GPU/audio activity and sampled memory. Keep
> game data local; do not increase limits again or infer boot from timer events.

The owner can paste this task into local Codex; they do not need to transcribe
all build/run commands themselves. This document does not connect sessions or
start unattended local/device work. The host reconnaissance needs a local title
path but does not need USB/ADB; later Thor tests still require the explicitly
selected and authorized device.
