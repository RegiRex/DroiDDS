<!-- CodexAstraUlt: Preserve this owner-played intro session separately from the bounded code 14 CPU test and distinguish human visual evidence from counters. -->

**The owner played into the intro and reported no graphical glitches.** The separate [full session JSON](intro-session.json) records a stopped **0.0.8-preview.4/code 14** session using **Native execution, CPU vertex shaders and Vulkan 1×** on Thor/Adreno 740, with no reported runtime or rendering failure.

Collected **2026-11-05 at 23:11:20 UTC**. The app was already stopped, with an intro scene retained on screen. Collection used Save Report and a distinct export name; no Play, Stop, game input, installation or settings change was issued. The original [bounded CPU run](../2026-11-05-preview4-cpu-run-001/android-title-build-summary.md) and all previous reports remain separate and preserved. This owner-operated follow-up is not another agent-run bounded test: its start/stop wall-clock timing and input sequence were not independently observed.

The package is `org.droidds.title.t0004000000055f00`. App/version, input, manifest and native-library identities match the earlier code 14 report and retained installed candidate, built from source `ce09834b4eca63aeafef7102571690ad1efc90fd`. No rebuild was performed.

| Identity | SHA-256 |
| --- | --- |
| Base input | `e1c69aa34aa8fe4d95ca1a174f9ceb0485f596775cdba94205559c6de809a07a` |
| Title manifest | `c601dff93c6e69d339715c8f5bc802eb8fe6dd99dcd14358209c76eb24762557` |
| Retained ARM64 title library | `44219eb7d1b769464639351dfca200d35ca74224cb9909040855835a428c5c2b` |

| Measurement | Owner intro session |
| --- | ---: |
| Worker-running / active seconds | 197.999015 / 197.973877 |
| Core slice seconds | 194.825630 |
| Guest cycles / guest seconds | 8,844,758,769 / 32.989062 |
| Emulated speed, matching worker denominator | 16.66% |
| Frame events / image deliveries | 1,957 / 1,957 |
| Native / interpreted instructions | 3,287,060,427 / 47,435,035 |
| Callback-interpreted instructions | 0 |
| Command / CPU vertex seconds | 125.896471 / 73.207828 |
| Decode / placement / scanout seconds | 22.685086 / 17.269249 / 1.724649 |
| Core seconds outside command processing and scanout | 67.204510 |
| Command lists / draw calls / submissions | 21,296 / 837,186 / 24,351 |
| CPU vertex inputs / vertex references | 434,677,337 / 876,813,285 |

Guest duration uses 268,111,856 cycles/second. Different duration, input sequence and intro workload prevent a controlled performance comparison with the earlier menu run; frame events are not unique game FPS. Shader/decode/placement are disjoint command-time subsets, not extra time to add to the parent. The shader scope accounts for 37.58% of core; the unclassified remainder outside command processing and scanout accounts for 34.49%. These remain profiling targets rather than evidence for a particular correction. The report records interpreted work separately; it does not identify which code regions account for it.

Actual GPU-vertex draws, software raster fallbacks, draw/compiler errors, resource-limit events, fatal errors, prefetch aborts and unsupported services/SVCs are zero. Error, first-blocker and all three pipeline-failure fields are null. Final observed PC is `0x0011894C`. Memory-fault pages are zero and the sample is null; the 64 MiB guest allocation is not process memory. The nested running snapshot precedes closure; the outer report is stopped.

Audio generated **1,077,760 PCM frames**, including **902,078 nonzero**. All **1,580,655 converted frames were written**; drops, discarded input, flushes and queued frames are zero. There were **2,793 underruns**, one playback start and a **318.889 ms** maximum PCM-submission gap. No new audible-quality observation was supplied for this owner session. The earlier choppy-audio observation remains attached to the bounded run.

The owner's observation extends visual evidence into part of the intro. It does not qualify the full intro, sustained playability, save/load reliability or reliable audio. Native/CPU performance remains the priority; GPU testing remains deferred. No application fix or additional run was performed to collect this report.

The original and reviewed JSON are byte-identical: **4,714 bytes**, SHA-256 **`33929e275c447c3ddd52d9137a0cbb555dc74559592d48794ad15eb4e8a5f563`**. All fields were reviewed; no redactions were needed. Only this summary and the full JSON are shared. Private captures and game/build/signing data remain local. No failure required a driver-log capture.
