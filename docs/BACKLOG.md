# DroidDS implementation queue

<!-- CodexAstraUlt: Reduce the supplied 119-ticket catalog to bounded work packages with explicit tests and links back to the source requirements. -->

<!-- CodexAstraUlt: Record the delivered CPU subset and the resolved current
probe notice inventory; keep full-runtime and broader semantic gates open. -->
DDS-001/002 now have a pinned CPU dependency inventory, original workspace, build
runner and passing local checks. The current Android probe's distribution notice
inventory is resolved by the reviewed collector and
[third-party notice record](../THIRD_PARTY_NOTICES.md); full-runtime/platform
qualification remains open. DDS-003's bounded first fixture
scope is implemented: four native/interpreter cases, strict expected results and
negative controls. See [build evidence](builds/0.0.1-foundation.md).
<!-- CodexAstraUlt: Replace the pending Thor CPU status with validated uploaded
results without treating its self-reported metadata as a fresh ADB/package bind. -->
DDS-010 now has a CPU loader APK/build audit, local ADB runner and a passing
[owner-supplied Thor CPU report](device-tests/0.0.2-thor-cpu.md): four cases and
two negative controls on reported Android ARM64 with 4 KiB pages. Vulkan drawing
and the remaining platform gates stay open. The next planned 0.0.3 work is a
bounded offscreen Vulkan probe and **Save report** action; it has no device result
yet. See [the probe](ANDROID_PROBE.md).
Other DDS-004 onward items remain planned. The table defines acceptance, not completion of
every item merely because a related source component exists.
The original [119-ticket catalog](research/2026-10-17/06_IMPLEMENTATION_BACKLOG.md)
is reference material, not an instruction to implement everything at once.

| Ticket | Scope and concrete output | Acceptance | Depends on | Pack mapping |
| --- | --- | --- | --- | --- |
| DDS-001 | Source map, exact dependency resolution, ABI/generation inventory, notice inventory, architecture decision records | Verifier/runtime mismatch addressed explicitly; actual ABI documented; proposed vs observed claims separate; missing license notice provenance tracked | This plan | NRR-0002/0005/0101/0301/0401 |
| DDS-002 | Minimal workspace and repeatable Linux build; exact Rust/compiler/tool pins and locked Cargo graph | Clean checkout builds without private data; source-pin mismatch fails; meaningful existing tests execute and skips are explicit | 001 | NRR-0001/0004/0102–0105/0107 |
| DDS-003 | Tiny original ARM/Thumb fixture, real C generation/loading, strict comparator | Counted native and fallback execution match known outputs; deliberately wrong integer/memory results fail; timeouts report inconclusive; no compiler means failure/explicit skip | 002 | NRR-0106/0203–0205; TEST-001/002 |
| DDS-004 | Expand CPU transitions, VFP policy and scheduler-edge corpus | Flags, shifts, interworking, unsupported instructions, SVC, nested fallback/unwind, exclusive accesses and tiny budgets behave correctly; checkpoint policy documented | 003 | CPU-001–009/014/015 |
| DDS-005 | Module/code freshness policy and regression cases | Origin mismatch, absent metadata, changed executable bytes, multiple CRO bases, unload/reload and stale direct calls never execute invalid native code | 003 | NRR-0206/0207; CPU-010–013 |
| DDS-006 | Execute existing GPU tests; capture pipeline creation thread/phase and state-family coverage | Real Vulkan execution reported; fixed independent expected cases added; startup vs gameplay vs explicit wait distinguished; first generic/helper misses reproduced | 002 | NRR-0401–0405; GPU-001–008 |
| DDS-007 | Ready accurate fallback for the tested pipeline/capability families | Delayed/failed/absent workers, dynamic blend/logic differences and unseen states preserve correct complete draws without hidden synchronous specialization; uncovered mandatory families fail the gate | 006 | NRR-0406–0409; GPU-004/007/011 |
| DDS-008 | Bound Vulkan and CPU PICA-JIT admission, results, retained objects and logs | Unique-state flood and duplicate jobs stay within configured counts; no blocking queue push; failures don't retry forever; title switch/shutdown retires objects safely; memory tracked | 006; integrate with 007 | NRR-1003/1005 moved earlier; THR/OBS |
| DDS-009 | Harden existing driver cache identity, persistence, quotas and invalidation | Corrupt/truncated/mismatched cache ignored safely; existing atomic replacement retained; write quota and runtime limits checked; private paths Android-safe | 006 | CACHE-002/004–006/010 |
| DDS-010 | Early NDK/Bionic ABI and Vulkan smoke probe | Public fixture executes on Thor; ABI/ELF dependencies and static 16 KiB ELF/APK alignment checked; host page size recorded; actual Vulkan device and representative generic pipeline create and draw | 003; source audit may begin after 001 | NRR-0302–0304/0601/0602 |
| DDS-011 | Private Linux control-title scenario plus early Dark Moon reconnaissance | Exact revision, routes and cache scope recorded; native/fallback counters; save round trip; bounded memory; separate Dark Moon compatibility findings | 004/005/007/008/009 | NRR-0201/0202/0209/0210/0801/0802 |
| DDS-012 | Android host around core crates, initial two-screen viewport, input/audio/SAF and lifecycle | Public fixture works; surface changes/pause/audio routing/reconnect/process death recover; no desktop runtime or mandatory services; touch mapping correct | 010, 004/005/007/008/009 | NRR-0501–0508/0512/0603–0608 |
| DDS-013 | Private local builder and package/data identity workflow | Stable per-title package ID/signing; wrong revision blocked for AOT; progress/cancellation; space checks; save-safe upgrade; artifact destinations remain private | 010/012 | NRR-0701–0707 |
| DDS-014 | Private Android control-title slice and reusable device runner | Actual Thor AOT execution, graphics/audio/input/save; repeated cold/warm normal-speed measurements; memory and teardown gates pass; one device operator | 011/012/013 | NRR-0803–0808 |
| DDS-015 | Dark Moon-specific diagnosis and correction | Matching opening moon/ghost clips; CPU/HLE/PICA route evidence; minimized reproducer for each fault; no-glitch acceptance separate from speed; long-run memory evidence | 014; early diagnosis in 011 | Owner goal; TEST-006/013/014 |
| DDS-016 | Stage-specific performance and product qualification | 1×/2×/4× matrix, sustained thermals/memory, Thor physical-display test; regression title matrix; each claimed improvement has a matched baseline | 014; Dark Moon claims require 015 | PERF/TEST; later M6/M7 work |

## Foundation context and continuation

Deliver a source/ABI map, version/feature manifest and one reproducible Linux build
entry point. Use the exact commits in the [review](RESEARCH_REVIEW.md); preserve
upstream history/notices. Choose dependency integration after examining the
existing Cargo graph. Do not recreate upstream's compiler abstraction or ABI.

<!-- CodexAstraUlt: Retain ongoing provenance checks without reopening the
current probe's resolved notice hold; new components require their own review. -->
Validation must record the compiler, Rust version, upstream SHA, verifier CPU SHA,
feature flags, lockfile hashes, command exit status, executed tests and explicit
skips. A clean build with zero relevant tests is build evidence only. Preserve
the current probe's complete generated distribution notices and review additions
or dependency changes against actual source declarations and supplied notices;
the pack's MIT summary does not replace that inventory.

DDS-003 now supplies separate ARM/Thumb cases, actual native ARM-to-Thumb
interworking, fixed memory output and intentional missing-entry fallback. Continue
with DDS-004/005; broader VFP/CRO/service coverage remains named follow-up work.
A missing-compiler skip cannot pass DDS-003/M1 or unblock A0. Static 16 KiB
alignment checks do not establish runtime compatibility on a 16 KiB-page host;
record that execution as untested unless such a device actually runs the fixture.

## Work to defer until evidence supports it

Portable pipeline journals and prewarm; GUI builder; universal title launcher;
on-device compilation; custom shader replacement/compute rasterization; wholesale
Azahar integration; broad enhancement/mod framework; automatic online services;
large compatibility dashboards. HD textures remain a goal, with memory and
correctness qualification before enabling them in a default profile.

Do not file 119 GitHub issues automatically. Turn the next small batch into issues
when execution begins, keeping this queue as the dependency map. Parallel reviews
are useful; competing renderer rewrites or simultaneous benchmarks are not.
