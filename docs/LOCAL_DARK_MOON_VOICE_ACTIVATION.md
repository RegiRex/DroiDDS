# Local Dark Moon voice-activation investigation

<!-- CodexAstraUlt: Replace repeated observations of silent DSP banks with a
bounded decision about the guest producer, without assuming sound is yet due. -->
Read `AGENTS.md`, the [runs 017–018 findings](host-tests/dark-moon-2026-10-22.md#locally-executed-voice-production-batch-runs-017018)
and the existing private batch-005 summary. Both runs complete 500 million
steps with matching execution counters: 95,458 draws, 505 frame events, no
recorded runtime fault and silent PCM. Across this prefix the guest writes no
voice payload or dirty fields to either DSP bank. The observed consumer skips
voice work because its source-state predicates remain clear. Resource 67 is
still advancing; its completion is not known to trigger sound.

The next question is who can change those source predicates, and whether that
producer should execute in the observed startup phase. This is not yet a
demonstrated audio defect. Generic 0.0.7 manifest/compiler/package development
can proceed independently; an unfinished private audio investigation does not
block that implementation or qualify its later native/Thor acceptance gates.

## Inspect before running

<!-- CodexAstraUlt: Retain a matched runtime and use local source analysis to
avoid another unchanged prefix that cannot reach the activation being sought. -->
Preserve the frozen run-018 runtime, coordinator and existing private observer
as the baseline for this diagnostic. Obtain these instructions from current
DroiDDS main without silently rebasing that runtime onto unrelated fixes.
Record both the instructions commit and the actual investigated source/worker
identities. Keep originals, saves, prior reports, installed tools and permissions
unchanged. Use existing pinned Rust 1.95.0 and offline/locked builds in a separate
stable source copy/target directory; this task does not need USB operations.

Use the existing private code analysis to identify the constructor/reset path
and candidate writers of the measured fields: the halfword at voice-state
offset `0x6C`, the byte at `0x6F`, and the earlier gate byte at `0x0D`.
The observed halfword is `0x8000` with its low six bits clear; the bytes are
zero. The two observed skipping branches are `0x0023AE84 → 0x0023AF78` and
`0x00276A3C → 0x00276AFC`. Treat these as verified measured fields/branches,
not names for assumed enable semantics. Bind the actual caller and relevant
request/queue or startup condition, following at most two caller/dependency
levels in this batch. Keep instructions, disassembly and game-derived code local.

Do not assume the producer runs on consumer thread 7. Follow all guest threads
that can write the bound objects. Revalidate code identity, instruction mode,
mapping/backing and pointer ownership; a stable consumer pointer does not prove
unchanged object lifetime. Bind initialization before it happens where possible.
If binding starts later, report the earlier interval as unobserved. Do not use a
raw LR as caller identity inside a helper that repurposes it; use verified call
edges or stack slots as in batch-005.

If existing evidence already places the candidate activation outside the tested
prefix, return that evidence and the first missing phase transition without
repeating the same run. Static reachability alone cannot prove execution or its
absence. If the candidate is unresolved, instrument the nearest concrete missing
edge; do not substitute a broad instruction log or another general counter sample.

## Observe the writer and its prerequisite together

<!-- CodexAstraUlt: Track changes and their cause across object lifetimes,
including early initialization and writes that cross the watched field. -->
For one combined run, extend the already tested private observer narrowly:

- Bind the 24 actual objects to their pool/slot and lifetime, including allocation,
  reset, reuse and mapping changes. Record first known state and whether writes
  before binding are covered. Invalidate a binding on uncertain reuse/remapping;
  do not silently attribute a later object to an earlier voice.
- Watch full-range overlap with the three fields across all threads, including
  bulk clears/copies and aliases of the same backing. Retain attempted/accepted
  status, before/after scalar values when non-mutating reads are available,
  writer PC/mode/thread and verified caller. Distinguish initialization/reset
  from a transition making a consumer predicate true, and guest stores from
  HLE/GPU writes. A changed field is not proof of DSP publication.
- At the candidate producer and its immediate prerequisite, count entry, return,
  branch outcome and bounded scalar request/result state. Correlate an accepted
  activating write through the next consumer decision, actual DSP publication,
  consumption and PCM result. If the producer is skipped, name the observed
  controlling condition and its writer/return instead of guessing from silence.
- Reuse existing resource milestones only where a verified call/queue/field
  establishes their relationship to activation. Resource numbering and temporal
  proximity alone do not establish that resource 67 controls audio startup.

Use fixed aggregates for 24 slots and at most eight candidate writer/caller
sites, 64 retained change/call records and 16 milestones, with omission/overflow
counts and bounded pending correlations. Preserve the first activating transition
if one occurs. Stop expanding the probe when these bounds cannot represent the
needed dependency; report that limitation. Add no whole-memory scan, raw payload
dump, extra PCM drain, forced state or notification. Reuse batch-005 images;
new screen capture and input injection are not part of this writer test.

Extend original-fixture coverage only for new observer behavior: early
initialization versus later activation from a different thread, overlapping
stores, clear/reuse or remapping, wrong caller/provenance, and retained first
activation under overflow. Reuse the existing store/publication/consumer tests.
Confirm observer-off/on registers, relevant memory, PCM, execution counters and
stop outcome match before the private run. Use `CodexAstraUlt` comments for new
code and preserve the strict report and capture validation.

## Run bounds and decision

<!-- CodexAstraUlt: Require a causal decision at the existing budget rather
than indefinitely repeating a silent prefix or manufacturing a runtime fix. -->
Use a fresh output outside Git, strict interpreter/software execution, old model
and neutral input. Keep every bound from run-018:

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

Compare the run-018 checkpoints and final counters; investigate any divergence
before treating the new observation as equivalent evidence. Perform at most
one further private run, only to check a concrete generic correction or a specific
missing correlation. Do not automatically spend both runs or increase the limits.
A generic correction requires an original failing regression and a matched
private rerun; do not force game predicates or modify game instructions.

Return a fresh `dark-moon-investigation-summary.md` with source/input/tool
identity, exact limits and outcome, the first observed or still-missing causal
edge, object/lifetime and actor attribution, writer/caller/prerequisite evidence,
and whether DSP publication or nonzero PCM began. Distinguish a reached writer,
an observed skipped producer, and activation unobserved within this prefix.
If startup is still progressing and activation remains outside the evidence,
close this bounded investigation without declaring an audio bug. State the
specific later transition needed to revisit it; do not recommend another
unchanged prefix. Native-builder implementation can continue separately.
Publish only reviewed generic code/tests or nonprivate findings on the
investigation branch. Keep raw reports, snapshots, images and derived code local.
This test does not establish interactive boot, audible output or Thor performance.
