# Local Dark Moon decoder-completion investigation

<!-- CodexAstraUlt: Retain the completed decoder task as history and route
continuation to selected-screen and DSP evidence after successful drawing. -->
This batch is complete; its findings are published in `a9b9cb1`. The current
task is [the local display/audio check](LOCAL_DARK_MOON_OUTPUT_CHECK.md).

<!-- CodexAstraUlt: Give the local session one bounded diagnose/fix/retest task
instead of requiring the owner to relay each intermediate trace measurement.
Advance from measured table/checksum progress to decoder and caller completion. -->
The next investigation belongs on the owner's Nobara laptop, where the owned
decrypted title and private run reports already exist. The Thor is connected
and available for relevant testing. This document is the task to execute when
the owner starts it in local Codex; it does not connect sessions or start work
on that computer from the cloud.

Read `AGENTS.md` and the latest section of
[the reported evidence](host-tests/dark-moon-2026-10-22.md).
Preserve local changes and work on a dedicated local investigation branch based
on the current DroidDS source. Record the base commit and any existing changes.
The local session owns this CPU/HLE investigation until it returns a result;
avoid concurrent cloud edits to the same implementation. Parallel reviewers
may inspect source or tests, with one coordinator integrating changes and one
operator serializing private execution and device access.

## Start with the existing evidence

<!-- CodexAstraUlt: Carry measured finite work forward rather than repeating
the completed table-progress and no-draw-request measurements. -->
Read the latest local `dark-moon-investigation-summary.md` and its linked
`report.json` and `worker-report.json`. Record source and worker identities,
verify the input matches earlier baselines, and retain the exact limits. The
source must include `8c15ce2`, which makes the existing local `IsChild` identity
query available offline without enabling wireless commands.

Published findings `39f6fa6` record three matched runs, 010–012, on `03b2760`.
Each stops at 100 million steps and `0x0018806C`: 99,969,272 interpreted
instructions, 225,985,001 cycles (about 0.843 emulated seconds), 50 frame events,
268 GPU lists, zero draws/vertices and 25,760 silent stereo PCM pairs. The
normal worker is unchanged; private observation does not change these results.

The table builder advances toward its finite bound. Stream accounting reaches
2,680,467 output bytes, with final cursor differences consistent with 2,729,470
output bytes. Checksum processing also advances. The enclosing resource's full
extent and completion remain unobserved. All captured GPU commands are setup;
there are no array/indexed draw writes, immediate vertices or list jumps. These
findings support following initialization further, not a CPU or renderer fix.

Inspect the relevant instructions locally before another execution. Resolve
the guest address through the parsed title's executable segments: a guest PC
is not a byte offset in a cartridge container. The existing `zakuro_fs::Title`
loader and `code()` handle container selection and `.code` decompression;
`zakuro_core::loader` maps segment offsets using page counts. Verify that the
window belongs to the loaded main text and has not been remapped or replaced
by a CRO. If it has, resolve the actual runtime code provenance first.

Inspect the existing private decoding work, then decode only missing windows
around the continuation at `0x0018898C`, return at `0x001889F4`, and its caller.
Start with at most 256 bytes per necessary window using existing tools. Verify
the actual return instruction and caller target for this title revision; a
return may restore PC from the stack rather than use the current LR. Keep bytes,
disassembly and derived notes in a fresh private location outside Git. Do not
run `examples/dumpcode.rs` unchanged: it writes the entire code image to a
fixed output path. A new helper must preserve existing files and extract only
the validated window needed for this diagnosis.

## Diagnose, fix and verify in one batch

<!-- CodexAstraUlt: Replace the checksum instruction window with correlated
return/caller observations that answer whether a chunk or resource is complete. -->
Extend the existing private observer only as needed, using one combined
measurement rather than separate runs for each address. Capture continuation
after checksum, actual decoder return status and post-return target, then the
same thread/guest incarnation's caller decision: refill, continue, complete or
error. Interpret the status using that caller; zero is not automatically proof
of completion. Distinguish a 262,144-byte quota/chunk return from completion of
the enclosing resource.

Correlate each return with the stream/resource instance, available or declared
input/output extent, cumulative consumption/production and remaining work. Keep
unknown extents explicit. Read only validated scalar state without side effects;
retain at most 32 semantic return/caller records with a small prefix and tail,
omission counts, and at most 16 completion/first-draw milestone records. Bound
pending correlations too; do not use an unbounded map or per-instruction log.
Preserve actual dispatch PC/mode and identity after scheduling. Test the observer
with original fixtures and keep it out of normal Android execution.

Keep the established GPU counters. Record the first draw request and draw-call
entry if they occur, including their relation to resource completion. There is
no reason to repeat three observations proving the same setup-only lists.
Disarm capture once its question is answered, but let execution reach its genuine
budget, exit or runtime blocker. The coordinator does not accept an early observer
stop falsely labeled `budget_exhausted`; do not change its validation to hide one.

Use **at most three new private executions**, not a quota of three. Prepare the
combined observer using existing code/captures, then run with a step-only ceiling
of **1,000,000,000 steps** (or a smaller evidence-supported bound). The measured
progress in runs 010–012 justifies this extension without another confirmation;
it does not prove resource completion. Recover any still-missing extent during
the same extended observation rather than requiring another 100-million-step
replay first. Reserve further runs for a concrete missing observation or matched
verification of a justified fix. Do not pause merely to ask the owner to relay
another counter.

Use these ceilings, with every non-step limit unchanged:

```text
--max-steps 1000000000
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

During an extended run, capture one 100-million-step checkpoint and compare its
steps, instructions, cycles, frames and GPU counters with run-012 before
interpreting later results. Do not drain PCM or alter guest state for the
checkpoint; a stopped worker's final audio drain is a different boundary. The existing
rate suggests roughly 2.26 billion cycles and 63–65 host seconds at one billion
steps, within the unchanged limits, but this estimate is not a completion bound
or handheld performance measurement. Do not extend beyond this batch's ceilings.
If a ceiling still stops useful work, report the measured remaining extent and
estimated work, or explicitly state why that bound is still unknown. If execution
stops progressing, identify the dependency instead of skipping guest work.

For a concrete CPU/HLE/command-processing defect, author an original regression that
fails before the generic fix, implement the fix, run relevant checks, and
repeat the matched private baseline within the batch. Use `CodexAstraUlt`
commentary. Do not copy private game instructions into public fixtures, patch
the game, force return/register values, skip draws or weaken fault handling to
manufacture progress. A correct finite initialization loop needs no runtime
workaround. Keep title-specific investigative instrumentation private until a
generic, tested diagnostic is justified.

Return after a diagnosed-and-tested correction, a useful completion/next-blocker
finding, or the three-run ceiling. Stop a dependent action if a required input,
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
Prepare a fresh `dark-moon-investigation-summary.md` with decoder return status,
the caller's interpretation, chunk versus resource completion, extent/progress
or blocking dependency, source/worker/input identity comparisons, changes made,
regression results, each run's limits and outcome, and the next concrete action.
If loading completes, identify the next executed operation and any actual draw
request or runtime blocker. Keep device work separate. State whether drawing,
audio or interactive boot was actually observed. Do not infer compatibility
from elapsed cycles or draws.

Keep game bytes, disassembly, raw captures, generated title code and private
APKs local. Commit only reviewed generic changes/tests and nonprivate findings
on the investigation branch. Push that branch if existing repository access
permits it; otherwise return its local commit or generic diff. Do not force-push
or upload private evidence to overcome an access restriction. Report a meaningful
diagnosis or tested fix, rather than requesting another identical trace run.
