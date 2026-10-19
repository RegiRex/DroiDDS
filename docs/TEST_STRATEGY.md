# DroidDS validation and measurement

<!-- CodexAstraUlt: Define observable correctness, cold rendering and sustained-memory gates before device optimization; carry forward the owner's temporal moon correction. -->

These are planned checks, not test results. Public tests use original or explicitly
licensed fixtures. Private title execution stays on the owner's local machine.

## Evidence levels

Record each claim as source-inspected, built, synthetic-tested, private-title-tested
or device-qualified. An upstream compatibility label is not a DroidDS result.
Differential agreement is not independent hardware correctness; add known expected
outputs derived from specifications or independently established reference cases.

For every run record source/ABI/toolchain versions, test count, pass/fail/skip/
inconclusive counts and backend initialization. Required GPU and C-layout tests
must not return success without running. Keep invalid test runs out of benchmarks.

## CPU and loader matrix

| Area | Required cases |
| --- | --- |
| Actual AOT | Generate C with pinned producer, compile and load through actual ABI; prove native entries execute |
| Strict oracle | Exact integer/register/memory checks; known-bad outputs fail; bounded VFP NaN policy; limit exhaustion is inconclusive |
| Instruction semantics | ARM/Thumb interworking, flags/carry/shifts, VFP conversions/rounding/subnormals, known-result fixtures |
| Transitions | Unknown entry, unsupported instruction, SVC, scheduler budget, recursion/unwind, mixed native/interpreter calls |
| Memory/modules | Page crossing/alignment, permission faults, watched writes, executable changes, exclusive monitors, CRO multiple bases/unload/reload |
| ABI/identity | C/Rust layouts and exports, ABI/generation mismatch, missing origin metadata, changed executable/update/module hashes |
| Android | Same outputs on AArch64; Bionic dependencies, native loading, static ELF/APK alignment; record actual host page size and separately qualify 16 KiB-host execution |

Choose canonical checkpoints or explicitly documented live state for budget exits;
upstream permits some dead registers to be stale there. Start with deterministic
fixtures. For full titles, record input and external timing sources and explain
where nondeterminism prevents exact whole-state replay.

## Graphics correctness and cold behavior

Extend existing Zakuro generic/specialized and vertex translation tests. Retain
their narrowly justified interpolation tolerances; do not introduce a global
percentage tolerance that hides missing geometry or wrong colors. Cover
color/depth/stencil/blend/logic operations, textures, lighting, TEV, fog and any
supported procedural paths, plus independent known-output cases.

Instrument creation calls, thread identity, phase, fallback choice and publication
in diagnostic builds. Test:

1. First unseen generic family and helper compute/transfer pipeline.
2. Delayed specialization; compile failure; absent workers and injected
   thread-creation failure.
3. Dynamic blend present with logic-op dynamic state absent, and other supported
   capability profiles. A profile not tested is not certified.
4. Full optional-work queues, duplicate requests and failed-job deduplication.
5. Promotion while earlier GPU work remains in flight, title switch, cancellation
   and teardown. No use-after-free or stale-generation publication.

During the qualified gameplay path, a specialized miss must not trigger a wait,
synchronous specialization or skipped draw. Missing mandatory fallback creation
must also be visible and fail the cold-readiness gate. Startup preparation time
is measured separately. Pipeline lookup p99 below 1 ms is an initial target from
the pack, not sufficient evidence by itself: inspect the maximum and all explicit
creation/wait events. Other CPU, synchronization, I/O and driver costs can still
cause stalls even when specialization is correctly asynchronous.

## Memory, concurrency and logging

Test both Vulkan compilation and the separate CPU PICA shader JIT. Define limits
for active workers, pending jobs, completed results, retained specializations,
guest/title/surface data, and diagnostic buffers. Verify nonblocking admission and
accurate fallback at the limit. Preserve resources until their users finish.

Use unique-state stress, repeated scene traversal and at least three normal
launch/exit cycles. Report object counts, known bytes, process RSS/PSS where
available, available system memory and own-process GPU accounting where supported.
Unknown driver allocations stay explicitly unknown. Memory must settle within the
documented workload budget after warmup; continuing growth needs attribution
before acceptance. Recovering on exit alone does not prove bounded gameplay memory.

Provisional logging policy: one writer, size-bounded current/prior files, aggregate
metrics at an existing cadence, and incident-only bounded evidence. Set concrete
file/retention and queue limits in DDS-008 using measured overhead. Trace mode is
off by default, stops at its byte/record cap and exports only on request. Measure
logging enabled/disabled; a provisional target is under 1% workload overhead within
measurement uncertainty. Do not add a separate periodic writer to meet this test.

## Device protocol

One local coordinator owns the Thor. Confirm authorized ADB, exact package and
signing identity, driver, physical display layout, resolution, speed limit, power
mode, fan policy, battery/charging and available thermal readings. Missing sensors
are unknown, not evidence of a cool device. Preserve saves and unrelated caches.

Distinguish these conditions instead of calling all of them cold:

| Condition | What the report must say |
| --- | --- |
| Process-cold | New process; all persistent caches may remain |
| Application-cache-cold | Named title's runtime caches cleared under local authorization; driver/OS caches may remain |
| Warm | Same source/title/driver/settings and identified retained cache layers |
| Driver/runtime changed | Explicit invalidation and newly populated cache evidence |

Do not claim control of opaque driver-global caches. Keep data-import, AOT build
time, startup/preparation, loading and measured gameplay separate. Use the same
recorded scene/input/checkpoint route and speed limit. Run at least three matched
samples for performance claims; alternate baseline/candidate order where practical.
Report median and spread, frame-time p50/p95/p99/max, recurring stalls, normal-speed
time below 95%, audio underruns, native/fallback time, and generic/specialized draws.
Use supported emulation-speed accounting; do not infer it from display FPS alone.

Start at 1× correctness, then qualify 2× and 4× independently. Normal runs use
100% limit. Separate uncapped headroom tests from playability tests. A proposed
qualification target is at least 99% of measured gameplay at 95% emulation speed
or better, no recurring stalls and correct audio/visual output; retain the full
distribution and scene context rather than hiding short faults behind averages.
Run a 30-minute repeated/gameplay route for a candidate sustained claim and report
thermal trends. An opening cutscene alone is a scene qualification, not full-game
compatibility. Longer coverage grows with the claimed supported playthrough.

## Primary title matrix

<!-- CodexAstraUlt: Make the owner's three selected workloads reproducible and
distinct; do not use an optional title or another Sonic game as proxy evidence. -->

Primary private targets are **Luigi's Mansion: Dark Moon**, **Xenoblade Chronicles
3D**, and **Sonic & All-Stars Racing Transformed**. **Monster Hunter 4 Ultimate**
is optional comparison coverage. Keep per-title source/game/update identity,
scene, settings and pass/failure/untested status; never average them into one
compatibility result. Sonic Generations results cannot qualify Racing Transformed.

| Title | Planned repeatable route | Evidence to collect |
| --- | --- | --- |
| Dark Moon | Opening moon and laboratory ghosts, then fixed gameplay with normal exit/relaunch | Temporal visual correctness, native/fallback and GPU work, speed distribution, allocation growth and recovery |
| Xenoblade Chronicles 3D | Boot, fixed save/checkpoint, repeatable exploration/loading route and battle | Selected New 3DS guest mode and supported memory/services; CPU/fallback time, load behavior, frame pacing and sustained memory |
| Sonic & All-Stars Racing Transformed | Fixed event/track/settings with race-start and lap markers; include transformation sections where available | Cold/warm graphics behavior, first-seen effects, frame-time spikes, audio and per-lap speed distribution |
| Monster Hunter 4 Ultimate (optional) | Fixed quest/location and repeatable encounter | Additional compatibility/regression comparison; cannot replace primary-title qualification |

Exact routes depend on the privately available revisions and saves; document
them before comparing builds. For Xenoblade, establish required New 3DS guest
behavior before drawing performance conclusions. Unsupported model detection,
memory mappings, scheduling or services are compatibility blockers, not evidence
that the Thor is too slow. Use deterministic public fixtures to isolate gaps
without publishing private game data.

For Sonic, record lap/checkpoint markers without changing the normal-speed limit.
The owner's older turbo toggles are useful historical boundaries; timed benchmark
runs keep the same speed limit throughout. Run uncapped headroom tests separately.
All titles use the existing 1× correctness, then 2×/4× qualification sequence and
the repeated/sustained device protocol above.

### Dark Moon checkpoints

Use separate matching temporal captures for the opening moon and laboratory ghosts.
The owner's Uberhar Native reference has no observed moon flashing; Combo does.
Do not infer flashing from a faceted still or compare different animation phases.
Document moon flashing, ghost corruption and performance independently. A fix to
one symptom does not clear the other. Confirm whether DroidDS exhibits each fault
before assigning the old Uberhar diagnosis to a different architecture.

Brief visual capture may be separated from timing runs if recording changes
performance. Keep raw private clips local; public reports can contain sanitized
findings and synthetic reproducers. Compare changed CPU/PICA paths under fixed
settings, and reduce actual discrepancies into tests before speculative rewrites.

## Android reliability and release gates

Public fixture jobs cover install/upgrade, activity/surface loss, pause/resume,
controller reconnect, touch scaling, audio route changes, storage failure, cache
corruption and interrupted save writes. Device tests cover Android process death
and app-private recovery. Do not uninstall to solve a signing mismatch or use
force-stop as evidence of a normal clean shutdown.

Public CI/release artifacts contain only generic tools/runtime and licensed
synthetic fixtures. Private title APKs and derived code remain local. Before a
release claim, require the matching source tests, actual device evidence, notice
inventory, artifact checks and version/signing continuity. A build success is not
a playability result.
