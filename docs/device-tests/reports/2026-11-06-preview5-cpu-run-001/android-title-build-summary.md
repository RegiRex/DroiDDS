<!-- CodexAstraUlt: Preserve the single code15 Native/CPU result and new non-overlapping core timing attribution without claiming a gain from different scene content. -->

**Preview.5/code 15 reached file selection and stopped normally, with no reported runtime/rendering failure. Emulated speed was 16.70%, versus 17.31% in the code 14 menu run; no overall improvement is established. The new counters attribute 33.975 seconds to SVC handling outside rendering command work, narrowing the remaining unclassified core time to 6.779 seconds.**

Test date: **2026-11-06**, America/New_York (execution/export **2026-11-07 UTC**). Full reviewed [CPU JSON](cpu-session.json). Source `fdd0cf1447acbdb97a14befcbb20ee2055178a5e`, implementation `f6879110dace4d47edd3796ab4b85acc69effcb0`, published release source `365c1a0ffa3fce8d7001f625a0c42e399ea5b1aa`. The documented cloud correctness/runtime/publication/download gates passed before this batch. Source changes after implementation are documentation only.

Repackaged once with the retained ARM64 title library and existing owner signer, using Rust/Cargo **1.95.0**, NDK **27.3.13750724/r27d**, SDK/build-tools **35/35.0.0** and JDK **17.0.20.1**. Build completed in **53.632 seconds**. All **61 actual packaging commands**, **107 title JVM + 76 audio checks**, shader/library/manifest/signature/alignment gates passed; all **311 source hashes** matched independent review. No title generation, title-object compilation or tool setup was repeated.

| Identity | SHA-256 |
| --- | --- |
| Private APK, 287,691,626 bytes | `2d29989b10a63f209c4abeeb42d37f9b443560c7bf14c0e3db3204fa1bb4d9cc` |
| Existing public signing certificate | `a2aabf473b0c308ef2624e403231db947ebf1e64a6004d856962a8d139f94f0f` |
| Retained ARM64 title library | `44219eb7d1b769464639351dfca200d35ca74224cb9909040855835a428c5c2b` |
| Base input | `e1c69aa34aa8fe4d95ca1a174f9ceb0485f596775cdba94205559c6de809a07a` |
| Title manifest | `c601dff93c6e69d339715c8f5bc802eb8fe6dd99dcd14358209c76eb24762557` |

The compatible update is package `org.droidds.title.t0004000000055f00`, **0.0.8-preview.5/code 15**, API **29/35**, non-debuggable. The installed APK hash matched; app-data identity and retained import were preserved. The pre-update latest report was exported separately and exactly matches the already preserved code 14 owner-intro JSON. Both **521-object** builds/libraries, preparation, original input, signer and previous reports remain intact; preservation checks cover **6,819 protected file records**. Local report branches, stashes and owner preferences were preserved. No uninstall, data clear, save reset or reimport occurred.

**One Play**, Native guest execution, explicit **CPU vertex shaders**, **Vulkan 1×**, Thor/Adreno 740. The current title prompt was visually confirmed before admitting one A. Observer timings were **A 91.130 seconds**, normal **Stop sent 110.190 seconds**, and **Stopped observed 114.474 seconds**, within the 120-second bound. No replay, extra game input or GPU trial occurred. Observer errors/omissions were zero. The full JSON was exported before any restart.

Reviewed game captures showed no obvious corruption. File selection displayed **File 1 plus two Empty slots**, with a populated lower File 1 panel. The earlier code 14 menu had three Empty slots and an Empty Profile panel. This batch did not create/select a profile; the captures do not independently establish when File 1 was created. Preserving that state means the post-A workload is not identical to the earlier run. Both guest views use Canvas readback on the primary physical display. One post-stop document-picker capture was unreadable; a fresh capture was normal and export completed. That isolated capture does not identify a guest rendering failure.

Comparison uses the preserved [code 14 menu report](../2026-11-05-preview4-cpu-run-001/cpu-session.json), SHA-256 `78dd8b128fb9a8ba41889b7165c36c3a65c3e46e18557d5bc86959cc521c0cf2`. The separate owner-intro report is not a controlled comparison.

| Measurement | Code 14 menu | Code 15 menu |
| --- | ---: | ---: |
| Worker-running seconds | 102.612507 | 103.013388 |
| Core slice seconds | 100.000786 | 100.869019 |
| Guest cycles | 4,762,726,240 | 4,613,064,985 |
| Guest seconds / emulated speed | 17.763952 / 17.31% | 17.205748 / 16.70% |
| Frame events / image deliveries | 1,054 / 1,054 | 1,021 / 1,021 |
| Native / interpreted instructions | 2,064,824,389 / 213,733 | 1,999,652,115 / 213,211 |
| Command-processing seconds | 58.268575 | 58.794150 |
| CPU shader / decode / placement seconds | 31.175055 / 10.760378 / 7.750576 | 32.618247 / 9.983917 / 7.569679 |
| CPU vertex inputs | 197,133,760 | 188,655,172 |
| Decode / shader ns per counted input | 54.584 / 158.142 | 52.922 / 172.899 |
| Scanout seconds | 1.012470 | 1.269030 |
| Core seconds outside command + scanout | 40.719741 | 40.805840 |
| Audio underruns / flushed frames | 1,382 / 0 | 1,362 / 0 |

Guest duration uses **268,111,856 cycles/second** and matching worker time. Frame events are not unique game FPS. Different post-A scene content, work counts and uncontrolled load/thermal variation limit interpretation. Aggregate decode cost per input is lower and shader cost higher in this sample; neither establishes causal component savings or a regression. The report cannot isolate the effect of the renderer health-query change. Missing code 14 `core_work` fields are unmeasured, not zero.

The new **non-overlapping** accounting is:

| Scope | Calls | Inclusive seconds | Nested command seconds | Seconds excluding nested command |
| --- | ---: | ---: | ---: | ---: |
| SVC/HLE handling | 182,737 | 92.768780 | 58.794150 | **33.974630** |
| End-frame work | 1,021 | 0.002220 | 0 | 0.002220 |
| Audio/peripheral events | 3,519 | 0.049903 | 0 | 0.049903 |

All **58.794150 command seconds** are nested in SVC handling. Do not add the inclusive SVC total to command time. Subtracting each scope's `(wall − nested command)` from `core − command − scanout` gives **6.779087 seconds unclassified**. That still includes execution, scheduling, guards and memory synchronization; it is not native execution time alone. Non-command SVC work is **33.68% of core**. CPU shader work remains **32.34%**, decode **9.90%**, placement **7.50%**, other command work **8.55%**, and scanout **1.26%**. These are wall-time scopes, not hardware utilization. Audio scope includes peripheral ticks as well as DSP work.

Rendering recorded **9,411 command lists**, **609,551 draw calls**, **426,662,238 vertex references**, **606,125 placed/recorded draws** and **11,341 submissions**. CPU/decode/placement batches were **609,551** each, geometry-mode selections **0**, and parallel-threshold selections **35,178 (5.77%)**; that count does not measure active workers. Actual GPU-vertex draws, software fallback, draw/compiler errors and resource-limit events were zero; all pipeline-failure slots were null. Error/first-blocker/diagnostic-fault fields were null, with zero fatal errors, prefetch aborts and unsupported services/SVCs. Final PC was **`0x0011894C`**. Memory-fault pages were zero and sample null; **64 MiB** denotes guest allocation. Outer status is stopped; the nested running snapshot precedes closure.

Audio generated **561,280 PCM frames**, **385,598 nonzero**; all **823,179 converted frames were written**. Drops, discarded input, flushes and queued frames were zero. There were **1,362 underruns**, one playback start and a **336.100 ms** maximum PCM-submission gap. No new listening assessment has yet been supplied for this run; counters alone cannot establish audible quality.

**Next diagnostic:** attribute the **33.975 seconds of non-command SVC handling** using bounded per-SVC totals, then service/command categories only where the first attribution points. Retain nested rendering subtraction and authored-fixture correctness checks. The **32.618-second shader scope** remains another major cost. These results narrow the target but do not justify a particular generic correction. No application fix was authored locally; no longer unchanged run or GPU retry is needed. Gameplay, reliable save/load, sustained speed and reliable audio remain unqualified.

The original/reviewed full JSON is **4,982 bytes**, SHA-256 **`f54f724d18d31a100038138d3a0a1a302f9e0c47bbce2d717d50adec5da39633`**, with **no redactions**. No reported runtime failure required a driver-log capture. Only this summary and the full JSON are shared; private game/build/signing data and captures remain local.
