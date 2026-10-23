# Local Dark Moon display and audio check

<!-- CodexAstraUlt: Advance from resource completion and draw admission to
selected-screen images and the first silent audio stage, without a speculative fix. -->
Read `AGENTS.md` and the latest batch in
[the local findings](host-tests/dark-moon-2026-10-22.md). Use the existing owned
input and batch-003 reports on the laptop. The cloud has reviewed the published
findings, not the private reports or game images. This is a new local task;
it does not connect sessions or start execution from the cloud.

Run-014 completes the observed resource at about 114 million steps, enters its
first indexed draw at 125,851,274, and reaches 95,458 draws at 500 million steps.
It spans about 8.451 emulated seconds. Correct selected-screen output remains
unobserved. Its 274,720 silent stereo pairs correspond to 1,717 160-pair DSP
mixer-frame equivalents: output generation occurred, while voice/source/gain
state is unknown.
No generic runtime fix follows from those facts alone.

## Execution and ownership

<!-- CodexAstraUlt: Preserve the owner's permission for parallel builds while
separating their artifacts and avoiding an unsupported explanation of SIGKILL. -->
Keep local changes and work on a dedicated investigation branch. Parallel builds
are allowed with separate build/output directories, including distinct
`CARGO_TARGET_DIR` values for overlapping Cargo builds. Use a stable source copy
for each build; one coordinator integrates changes. Do not modify another
session's source or outputs. Shared host load can affect timings, so do not
interpret these observations as performance benchmarks.

Preserve run-013 as `worker_failed / worker_signal_9`, with unavailable counters.
The reported server restart does not establish the kill's cause. Do not attribute
it to another build, a memory leak or an out-of-memory kill without evidence.
Retain the existing bounded checkpoint scheme and all previous reports.

First inspect retained evidence and implement only missing private observation.
Use one combined display/audio run with the successful run-014 limits:

```text
--max-steps 500000000
--max-cycles 2681118560
--max-frames 1200
--max-seconds 120
--timeout 130
--memory-mib 4096
--trace-scheduler
--trace-cpu-progress
```

Keep strict interpreter/software execution, old-model configuration, neutral
input, existing pinned offline tools and locked dependencies. Use a fresh absent
output directory outside Git and check space for its full input snapshot. Preserve
the original, saves, previous snapshots and permission settings. At most two
additional runs may answer a concrete missing observation or verify a justified
fix; do not use all three automatically or extend these ceilings in this batch.
USB work stays with the already-connected session. No ADB readiness test or Thor
run is needed for this host task.

## Inspect the selected screens

<!-- CodexAstraUlt: Capture guest-selected LCD output through the production
scanout conversion, not an arbitrary render target that may never be displayed. -->
Use `System::read_screen(Screen::Top)` and `System::read_screen(Screen::Bottom)`
after `System::step` completes a frame. Normal `end_frame`/`gsp::refresh` must
latch queued swaps; do not invoke refresh manually or alter buffer selection.
This path selects the active A/B buffer, respects `lcd_force_black`, translates
addresses, synchronizes backing data, handles format/stride, and converts
column-major bottom-first storage to upright RGBA8: 400×240 and 320×240.

Validate each descriptor before reading: supported format, effective stride
(`height * bytes_per_pixel` when zero), checked address/length arithmetic, full
mapped source range, and at most 4 MiB of source bytes per screen. Record an
invalid or oversized capture as such; do not force an alternate buffer or hide
runtime faults. Record step/cycle/frame, active slot, selected addresses, raw
format, effective stride and force-black state. Count nonblack RGB pixels rather
than nonzero RGBA bytes, since alpha can be nonzero in an entirely black image.

Capture at most eight screen pairs, beginning at the first completed frame after
the first draw, then approximately every 60 frames. At stopping, identify the
last captured frame and its age rather than claiming it is a final-frame image.
Bound metadata/transition retention as well. Write
create-new private image files with an existing encoder or standard-library
format writer, with no new dependency installation. Inspect the actual images
using existing local image tools. Hash changes or nonblack counts alone do not
identify the scene or establish visual correctness. Record if no viewer is
available instead of claiming an image was inspected.

The public worker/coordinator currently require `scanout_captured=false`.
Actual capture must truthfully opt in in the private worker and matching private
coordinator validation; preserve the public default and unrelated checks. Record
the changed source/worker identities. Keep image paths and game pixels local.
Validate the capture on original fixtures with independent expected pixels,
including orientation, A/B selection, padded stride and force-black handling.
The existing homebrew image/PCM oracle provides a starting point; its frontend
does not launch retail games.

## Locate the first silent audio stage

<!-- CodexAstraUlt: The DSP generated silent blocks; observe existing parsed
state and computed samples before classifying the cause or changing behavior. -->
Use bounded private hooks in the existing DSP/voice/mixer processing paths.
Record component/running transitions, mixer-frame counts, selected shared-memory
region and configuration changes consumed, enabled/queued/playing voice counts,
buffer starts/completions and playback-position progress. Observe dirty fields
where consumed, rather than sampling them only after they have been cleared.

Record scalar nonzero counts/peaks from already-computed source/voice, filtered,
routed and final mixed output, plus effective voice gains and master/aux volume.
Count bulk-read fallbacks separately from individual sample-read failures that
substitute zero, and distinguish both from valid zero-valued sources. A bulk
lookup miss can still lead to successful individual reads. Actual sample-read
failures can produce silence without CPU fault counters. Observe binary
pipe/AAC request/result counts only if that path is actually used. Keep unknown
stages explicit; voice gains and mixer volume default to zero in this runtime.

Retain aggregates and at most 16 audio milestone records: first running state,
first voice/buffer progress, first nonzero intermediate/final output, relevant
configuration change and final state. Keep the ordinary audio-drain schedule;
do not call `take_audio` again for diagnostics. Do not serialize `DspState`, log
raw pipes, export audio payloads, or reread source samples merely for tracing.

Original fixtures must distinguish a stopped DSP, running silence with no voice,
known PCM playback, nonzero intermediate samples muted by master volume, and
missing sample memory versus valid silent input. Verify observation preserves
PCM and execution/state results with retention bounded. Reuse relevant existing
voice/mixer tests and the homebrew tone oracle.

## Return evidence or a tested correction

<!-- CodexAstraUlt: Keep diagnostic stops honest and make the next action
depend on visible output and observed audio state, not draw-count promotion. -->
Compare the 100-million-step checkpoint and final execution counters with the
established baseline. Do not drain PCM at an intermediate checkpoint; final
audio draining is a different boundary. Preserve genuine stop reasons and
strict faults. A diagnostic interruption must not masquerade as guest exit or
budget exhaustion. Stop a dependent action if tools/resources are unavailable
and continue independent analysis without changing access controls.

If a concrete defect is demonstrated, implement a generic correction with an
original regression and matched verification. Use `CodexAstraUlt` commentary;
do not patch the game, force gains/buffers, skip guest work or weaken validation.
Otherwise retain the measured behavior and identify the next actual dependency.
If loading still obstructs observation, establish that resource's live code and
extent before calling the final copying loop stuck. Do not infer it from one PC.

Prepare a fresh `dark-moon-investigation-summary.md` describing the actually
inspected top/bottom scenes over time, display-selection/blanking state, the
first silent audio stage and its supporting counters, input/tool identity,
limits/outcomes, regression results and next action. Distinguish draws, selected
screen images, visible host presentation, audio generation and interactive boot.
This task does not establish an interactive or Thor result from static captures.
Keep game bytes, images, raw captures, derived notes and private artifacts local.
Publish only reviewed generic changes/tests or nonprivate findings on the
investigation branch, preserving existing work and never force-pushing.
