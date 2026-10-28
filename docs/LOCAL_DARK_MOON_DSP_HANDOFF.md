# Local Dark Moon voice-publication investigation

<!-- CodexAstraUlt: Preserve the completed task as history and direct new work
to the guest producer after runs 017–018 found no voice writes in either bank. -->
**Completed as a bounded diagnostic in batch-005, runs 017–018.** Read the
[findings](host-tests/dark-moon-2026-10-22.md#locally-executed-voice-production-batch-runs-017018).
The current task is the [guest voice-activation investigation](LOCAL_DARK_MOON_VOICE_ACTIVATION.md).
Do not repeat the procedure below unchanged; it records the previous experiment.

<!-- CodexAstraUlt: Trace the first guest-to-DSP voice handoff after inspected
screens and repeated mixer updates locate silence before sample fetching. -->
Read `AGENTS.md`, the latest [published findings](host-tests/dark-moon-2026-10-22.md),
and the existing private batch-004 summary/checkpoints. The local images show a
preparation panel followed by a dark scene with a brightening window; bottom
captures are black. The cloud has not inspected those private images. At the
last durable checkpoint, frame 445, the DSP has consumed 1,497 mixer settings
but no voice settings, buffers or sample reads. Master volume reaches 1.0.
That observation does not establish that the guest should already be playing
sound, nor prove a faulty bank selector, semaphore or decoder.

## Run with an explicit CPU allowance

<!-- CodexAstraUlt: The public coordinator now separates process CPU from wall
time; this new batch deliberately increases only the former, rather than hiding it. -->
Use the current DroiDDS source on an investigation branch, preserving local work.
Bring the reviewed parent-only `--cpu-seconds` change into the private coordinator
without losing its validated observation opt-ins. Verify the child's installed
soft/hard CPU limits and reported resolved allowance using an original fixture
before private execution. Keep the failed runs and their snapshots intact.

Run one combined production/publication/consumption observation with:

```text
--max-steps 500000000
--max-cycles 2681118560
--max-frames 1200
--max-seconds 120
--timeout 130
--cpu-seconds 260
--memory-mib 4096
--trace-scheduler
--trace-cpu-progress
```

The CPU allowance increases from 131 to 260 seconds, summed across each process's
threads. It is not a process-tree or wall-time allowance. All other caps stay
unchanged. Run-016's 131.747268 accounted CPU seconds are consistent with its
131-second hard cap, without kernel attribution; earlier SIGKILL causes remain
unknown. The new cap does not guarantee a complete run. Preserve actual failed,
partial and completed outcomes rather than inferring a final report from checkpoints.

Use existing pinned offline tools, strict interpreter/software execution, the
old model and neutral input. Use a fresh output outside Git with space for the
input snapshot; preserve original data, saves, earlier reports and permissions.
Concurrent builds may use separate stable source copies and output/target
directories. Keep the existing bounded durable checkpoints. Reuse inspected
images instead of repeating the full capture sequence; preserve truthful capture
flags and use at most two new screen pairs if a new startup transition needs them.
USB operations stay with the already-connected session. At most two additional
private runs may answer a concrete missing observation or verify a justified fix;
do not spend all three automatically or increase these ceilings further.

## Follow one actual voice publication

<!-- CodexAstraUlt: Observe what the guest writes and publishes before what
the HLE consumes; post-consumption zero dirty words alone cannot prove no producer. -->
Derive the actual DSP layout from the initialization response and guest conversion,
checking it against the runtime. The current runtime returns 15 word addresses;
conversion is `0x1FF00000 + 0x40000 + word_address*2`. Bank stride is `0x20000`.
Voice configuration banks currently start at `0x1FF53D24` / `0x1FF73D24`, with
24 records of `0xC0` bytes; frame counters are at `0x1FF57FFE` / `0x1FF77FFE`.
Use source constants and verified guest destinations, not an assumed title layout.
Address/count fields use high-halfword-first encoding where specified; dirty
flags and floats are ordinary little endian.

Combine these observations in the existing private observer:

- Bounded DSP IPC entry/return records for initialization, address-table reads,
  conversion, register/semaphore operations, event registration and correlated
  waits. Preserve register/channel selectors, returned scalar addresses and byte
  counts, actual SVC PC and thread identity; never log raw pipe or sample payloads.
- Narrowly filtered guest-store observations for voice fields/dirty words and
  frame-counter publication in both banks. The pinned interpreter routes stores
  through `Bus::write8/16/32`, including constituent block/VFP stores; fast paths
  are inside their `Memory` implementations. A private Bus wrapper can identify
  original guest requests; forward every Bus operation faithfully. Hooking only
  `write_bytes` misses ordinary stores. Preserve the instruction PC/thread and
  distinguish attempted stores from accepted writes. CPU-dispatch scope alone
  is insufficient: memory guards can invoke nested GPU writeback, which must not
  be attributed to the guest. Tag HLE clears/status writes separately.
- Both frame counters, the selected bank and each bank's 24-bit dirty-voice mask
  immediately before consumption. Record the actual selected dirty fields before
  parsing clears them, then tag the consumer clear and first enabled/queued buffer.
- Aggregate other guest writes within mapped DSP RAM, retaining only a few
  unexpected destination/PC examples. If the producer writes elsewhere, bind its
  actual pointer/copy destination before concluding that no production occurred.

Use fixed per-bank/per-voice counters and at most 32 correlated publication/wait
records plus 16 milestones, including omissions and bounded pending correlations.
Match the full write-range intersection with watched fields, including stores
that begin before a field. Preserve constituent multi-store order; avoid double
counting cross-page fallback. Do not scan/log all memory per instruction. Prefer
values already read or written. For otherwise-unread unselected-bank dirty words,
allow only bounded, validated, non-mutating peeks at those fixed fields; ordinary
`Memory::read*`/`peek32` can activate guards or record faults. Add no PCM drain or
forced notification.
Keep private instruction analysis and all derived data outside Git.

## Interpret and validate the handoff

<!-- CodexAstraUlt: Existing HLE shortcuts are hypotheses until a measured
guest sequence and an independent regression demonstrate a mismatch. -->
The current selector uses two frame counters, special `0xFFFF` cases, and bank 1
on ties. It consumes/clears the selected bank and writes status to the opposite
bank. Audio advances periodically while running; several guest register and
semaphore commands currently return success without changing state. Neither
those shortcuts nor absent voice activity alone justify changing the emulation.

Distinguish payload without publication, dirty data in the unselected bank,
guest overwrites before consumption, and selected dirty data actually reaching
the voice parser. If no producer is observed, follow its actual startup/resource
or input dependency. Do not assume the dark window already requires sound.
Keep neutral input unless an inspected prompt establishes a concrete dependency;
any input experiment needs a separately identified run and bounded input sequence.

Before private execution, validate the observer with an original interpreter
guest: payload without dirty flags; dirty data in an unselected bank followed by
publication; payload→dirty→counter consumed exactly once; and a dirty word cleared
by a guest overwrite before a tick. Include queued-buffer activation, semaphore
wait/wake and counter ordering/tie/wrap cases with independently justified expected
behavior. Do not turn the existing selector implementation into its own oracle.
Verify guest-store coverage across widths/fast paths and distinguish HLE writes.
Include overlapping/cross-page stores, multi-store ordering, nested writeback and
failed exclusive stores so an attempted or internally generated write is not
reported as accepted guest publication.
Compare observation off/on PCM, registers, relevant memory/status, counters and
stop outcomes; force retention overflow to verify bounded storage.

Use `CodexAstraUlt` commentary for new code. A demonstrated generic defect needs
an original failing regression, correction and matched rerun. Do not patch the
game, force gains or dirty bits, skip work, or weaken strict/report validation.
The new CPU allowance changes host admission, not guest behavior: compare the
existing 100-million-step/resource/first-draw checkpoints and retain all later
observations as new evidence. Never substitute partial counters for final totals.

Return a fresh `dark-moon-investigation-summary.md` identifying the first broken
or unobserved production/publication/consumption edge, its thread/PC and startup
dependency, exact input/tool identity, configured CPU/wall limits, outcomes,
regressions and next action. State whether voice playback or nonzero PCM began.
If the evidence supports no runtime correction, say so. Keep images, raw reports
and game data local; publish only reviewed generic code/tests or nonprivate findings
on the investigation branch. No interactive boot or Thor result is implied.
