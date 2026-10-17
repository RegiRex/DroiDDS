# Local implementation handoff

<!-- CodexAstraUlt: Supply an executable project direction without silently starting implementation or requiring a cloud-to-local session bridge. -->

DroidDS planning is complete enough to start DDS-001/002. Implementation has not
started. The existing Nobara laptop and USB-connected Thor can host the private
development/test loop once their current readiness is checked. This cloud chat
does not share a live session, device connection or private files with local Codex.

## Starting scope

Work in a separate DroidDS checkout. Read `AGENTS.md`, `docs/RESEARCH_REVIEW.md`,
`docs/ARCHITECTURE.md` and `docs/BACKLOG.md`. Keep Uberhar files, APK and saves intact.
Check branch and local changes before fetching; do not reset another session's work.

The first implementation batch is source/dependency/ABI reconciliation and a
repeatable Linux build, followed by the small synthetic AOT/interpreter fixture.
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

The first private control title is selected by verified ownership, revision and
upstream compatibility. Dark Moon opening reconnaissance is required at M3 and
becomes a separate correction/performance track. Its old Uberhar moon observation
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
> Implement only DDS-001/002 first: reconcile exact producer/runtime/verifier pins,
> document the real ABI and provenance gaps, establish a locked Linux build and
> report tests that actually ran. Then tackle the small public synthetic fixture
> in DDS-003 if the foundation passes. Use CodexAstraUlt comments, preserve local
> changes, keep all retail inputs/derived outputs private, and leave Uberhar intact.
> Do not execute the archive's entire prompt pack or claim Android/game readiness
> from compilation alone. Checkpoint after each ticket and report concrete blockers.

The prompt is a proposed bounded implementation task for the owner to invoke; its
presence in this planning document does not start a local session automatically.
