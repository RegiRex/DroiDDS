# Local Dark Moon investigation after the offline identity fix

<!-- CodexAstraUlt: Give the local session one bounded diagnose/fix/retest task
instead of requiring the owner to relay each intermediate trace measurement.
Advance the task after the first batch clears the old loop and IsChild blocker. -->
The next investigation belongs on the owner's Nobara laptop, where the owned
decrypted title and private run reports already exist. The Thor is connected
and available for relevant testing. This document is the task to execute when
the owner starts it in local Codex; it does not connect sessions or start work
on that computer from the cloud.

Read `AGENTS.md` and [the reported evidence](host-tests/dark-moon-2026-10-22.md#owner-reported-local-investigation-after-run-006).
Preserve local changes and work on a dedicated local investigation branch based
on the current DroidDS source. Record the base commit and any existing changes.
The local session owns this CPU/HLE investigation until it returns a result;
avoid concurrent cloud edits to the same implementation. Parallel reviewers
may inspect source or tests, with one coordinator integrating changes and one
operator serializing private execution and device access.

## Start with the existing evidence

<!-- CodexAstraUlt: Replace the completed run-006 target with the latest
post-fix evidence; do not turn a suggested decoding operation into a finding. -->
Read the latest local `dark-moon-investigation-summary.md` and its linked
`report.json` and `worker-report.json`. Record source and worker identities,
verify the input matches earlier baselines, and retain the exact limits. The
source must include `8c15ce2`, which makes the existing local `IsChild` identity
query available offline without enabling wireless commands.

The owner reports that the original startup loop clears. After the identity
fix, execution reaches the 100-million-step limit at `0x0018806C`, with 268 GPU
command lists, zero draws and silent PCM. Inspect the full reports for cycles,
thread identity, drained/nonzero PCM counts and sampled memory; those details
are not established by the short supplied summary. Treat decoding-table work as
the next hypothesis to check from actual code and state, not a diagnosed defect.

Inspect the relevant instructions locally before another execution. Resolve
the guest address through the parsed title's executable segments: a guest PC
is not a byte offset in a cartridge container. The existing `zakuro_fs::Title`
loader and `code()` handle container selection and `.code` decompression;
`zakuro_core::loader` maps segment offsets using page counts. Verify that the
window belongs to the loaded main text and has not been remapped or replaced
by a CRO. If it has, resolve the actual runtime code provenance first.

Decode an initial window of at most 256 bytes using existing local tools or a
small local helper built with the existing dependencies. Identify the loop's
continuation/exit condition, loads/stores and state it changes. Keep any bytes,
disassembly and derived notes in a fresh private location outside Git. Do not
run `examples/dumpcode.rs` unchanged: it writes the entire code image to a
fixed output path. A new helper must preserve existing files and extract only
the validated window needed for this diagnosis.

## Diagnose, fix and verify in one batch

<!-- CodexAstraUlt: Allow measured local iteration within explicit bounds,
without inventing a game workaround or another default tracing subsystem. -->
If static analysis is insufficient, add a temporary host diagnostic that
captures at most 32 same-thread visits to one loop anchor, or at most 256
consecutive scalar instruction states near the latest stopping point. Select
the window using the existing report, and ensure the samples belong to the
same thread/guest incarnation. Preserve the actual dispatch PC and ARM/Thumb
mode after scheduling; pre-`System::step` thread identity can be stale. Retain
only the registers/counters needed to inspect that loop. Do not add diagnostic
guest-memory reads with side effects or enable an unbounded profiler. Test the
capture on an original fixture and keep it out of normal Android execution.

<!-- CodexAstraUlt: Distinguish command-list processing from reaching a draw
before diagnosing downstream shaders or rasterization from a zero-draw count. -->
Inspect the PICA command path in `vendor/zakuro/crates/zakuro-gpu/src/lib.rs`.
`command_lists` counts processed lists, including ones with no draws; `draw_calls`
increments on entry to array/indexed or immediate drawing, before rasterization.
Determine whether the submitted lists contain only setup, whether writes to
`REG_DRAW_ARRAYS`/`REG_DRAW_ELEMENTS` reach their handlers, or whether an expected
immediate draw never becomes ready. Include chained lists and burst writes when
checking the parser. Start with existing private evidence; if a run needs added
observability, use bounded counters and at most 64 scalar command-path samples
across the entire run. Keep command payloads and shader/game data private.

Measure the CPU operation's exit condition and state progression alongside that
path. Establish whether startup has reached drawing at all before attributing
the absence of draws to a graphics defect.

Use up to **three new private executions** in this batch, each answering a
distinct recorded question: focused observation, a matched correction check,
and one necessary follow-up. Do not stop between these steps merely to ask the
owner to relay another counter. Use the previous batch's step ceiling and the
other existing limits; check their identities against the retained reports:

```text
--max-steps 100000000
--max-cycles 2681118560
--max-frames 1200
--max-seconds 120
--timeout 130
--memory-mib 4096
--trace-scheduler
--trace-cpu-progress
```

Keep strict diagnostics, interpreter/software execution, neutral input and the
fresh base-game configuration. Check free space before each run: the coordinator
creates a full new input snapshot. Use new absent output directories outside
Git; preserve the original, saves, earlier reports and snapshots. Build offline
with the existing pinned toolchain and locked dependencies.

Do not extend these limits again in this batch. If finite useful initialization
needs more work, report its decoded bounds, measured progression and estimated
remaining work. If execution is not progressing, identify the dependency or
incorrect operation. Neither case warrants skipping the guest's work.

For a concrete CPU/HLE/command-processing defect, author an original regression that
fails before the generic fix, implement the fix, run relevant checks, and
repeat the matched private baseline within the batch. Use `CodexAstraUlt`
commentary. Do not copy private game instructions into public fixtures, patch
the game, force return/register values, skip draws or weaken fault handling to
manufacture progress. A correct finite initialization loop needs no runtime
workaround. Keep title-specific investigative instrumentation private until a
generic, tested diagnostic is justified.

Return after a diagnosed-and-tested correction, a clearly identified remaining
blocker, or the three-run ceiling. Stop a dependent action if a required input,
tool, permission or resource is unavailable; continue independent analysis.
Preserve current permission settings and do not install additional software as
part of this batch. A hardware test remains separate from a host result.

## Use the connected Thor where relevant

<!-- CodexAstraUlt: The owner confirms another local session already uses the
Thor; remove the redundant readiness check from this host investigation. -->
The owner confirms that another Codex session is currently connected to the
Thor. No additional ADB readiness check is needed for this batch. The blocked
session reported missing `/dev/bus/usb` and socket creation failing with
`Operation not permitted`; these suggest restrictions in its execution context.
Continue host diagnosis there, leaving USB work with the already-working session.
Do not keep retrying, kill/restart its ADB server, change permissions or work
around access controls. Device tests remain serialized with the session that
owns the Thor. If a relevant device test is scheduled later, use its explicitly
identified serial and record the actual installed artifact and device identity.

Repeating the unchanged, already qualified 0.0.6 probe does not validate the
new identity fix. If a shared runtime fix warrants an Android regression and
the existing build tools and matching APK are available, use the
[supported device runner](ANDROID_PROBE.md#run-from-the-laptop-with-adb).
Use an artifact containing the fix when validating that fix; an older APK is
only a comparison baseline. A claim that the affected service works on Android
also needs an original fixture exercising it; an unrelated probe pass is only
a general regression check. Preserve the existing `files/latest-probe.json`
before the runner replaces it. The runner always installs with `adb install -r`;
it has no installed-only mode. Do not uninstall to resolve signing conflicts,
clear app data or change USB/network permissions. The current probe cannot
launch Dark Moon; an Android game-launch test needs the separate private-title
package path and its existing build/identity gates.

## Return one useful handoff

<!-- CodexAstraUlt: Return semantic findings and reviewable generic code,
keeping private title bytes and raw evidence on the owner's computer. -->
Prepare `dark-moon-investigation-summary.md` with the verified loop behavior,
evidence of progression or the blocking dependency, source/worker/input identity
comparisons, changes made, regression results, each private run's limits and
outcome, and the next concrete action. Include device readiness or a relevant
device result separately. State whether any drawing, audio or interactive boot
was actually observed. Do not infer compatibility from elapsed cycles or draws.

Keep game bytes, disassembly, raw captures, generated title code and private
APKs local. Commit only reviewed generic changes/tests and nonprivate findings
on the investigation branch. Push that branch if existing repository access
permits it; otherwise return its local commit or generic diff. Do not force-push
or upload private evidence to overcome an access restriction. Report a meaningful
diagnosis or tested fix, rather than requesting another identical trace run.
