<!-- CodexAstraUlt: Record the single approved code16 Native/CPU run, preserve nested timer scopes and separate observations from performance inference. -->

**Preview.6/code 16 reached file selection and stopped normally with no reported runtime/rendering failure. Measured emulated speed was 18.70%, versus code 15's 16.70%. The new attribution identifies display transfers (26.917 s) and texture copies (6.061 s) as 97.82% of SVC time outside the PICA command-list timer. These are the next performance investigation targets; this single comparison does not establish a sustained or causal speed gain.**

Test: **2026-11-09**, America/New_York; execution started **06:21:54 UTC**. Full reviewed [CPU JSON](cpu-session.json). Source `c69eb7646abbbf799a180a2614c2b2986f0d8cb2`; implementation `64f1404ed0a357cf9325568a2376137079b120ad`; release `2354ed0f516926ff11fd613d95333141040cc3af`. Later source changes are documentation only. Before packaging, [CPU main](https://github.com/RegiRex/DroiDDS/actions/runs/42331432861), [Android main](https://github.com/RegiRex/DroiDDS/actions/runs/42331432854) and [publication](https://github.com/RegiRex/DroiDDS/actions/runs/42331843524) were verified successful on their expected sources. Four jobs passed, with 48 successful steps and three intentional failure-reporting skips. Published asset identities match the build record; independent public-download verification remains documented cloud evidence, without another local download.

Repackaging reused the validated preparation, ARM64 title library and existing owner signer. Rust/Cargo **1.95.0**, NDK **27.3.13750724/r27d**, SDK/build-tools **35/35.0.0**, JDK **17.0.20.1**. Build: **308.471 s**, **61 successful commands**, **107 title JVM + 76 audio checks**, passing shader/library/manifest/signature/alignment gates. Independent review matched **311 source hashes**, the signer certificate and all three stored, 16-KiB-aligned ARM64 ELF entries. No title regeneration/recompilation, setup or permission changes occurred.

| Identity | Value / SHA-256 |
| --- | --- |
| Package | `org.droidds.title.t0004000000055f00`, `0.0.8-preview.6`, code **16**, API **29/35**, non-debuggable |
| Private APK | **287,708,010 bytes**; `345bdf70232184945dcccdfd114a2d478b62a8710205ffe82fda751eb990c6fc` |
| Existing public signer certificate | `a2aabf473b0c308ef2624e403231db947ebf1e64a6004d856962a8d139f94f0f` |
| Retained ARM64 title library | `44219eb7d1b769464639351dfca200d35ca74224cb9909040855835a428c5c2b` |
| Base input | `e1c69aa34aa8fe4d95ca1a174f9ceb0485f596775cdba94205559c6de809a07a` |
| Title manifest | `c601dff93c6e69d339715c8f5bc802eb8fe6dd99dcd14358209c76eb24762557` |

Package verification preceded the explicit approval request and STOP. Only after the owner's approval did the sole operator connect, verify actual code 15 against its retained APK/signature identity, export its latest report, and install a compatible update. The pre-update export exactly matches the preserved code 15 JSON. Installed code 16's hash matches the reviewed APK; app-data identity and retained import were preserved. Final host audit passed **7,200 protected records**, both **521-object** builds/libraries, original input, preparation, signer and prior reports. Existing local commits/stashes and the exact **1,164-byte** owner handoff suffix remain preserved. No uninstall, data clear, save reset or reimport occurred.

**One Play: Native execution, explicit CPU vertex shaders, Vulkan 1×, Thor/Adreno 740.** The current prompt was visually confirmed. Observer-clock actions: Play completed **0.048 s**, A **91.056 s**, normal Stop **110.111 s**; Stopped observed **114.380 s**, within the 120-second bound. A/Stop were **91.008/110.063 s after Play completion**. Five heading keepalives, no extra guest input, no replay/GPU trial, zero observer errors/omissions. The full JSON was saved separately and pulled at **06:24:56 UTC**, before any restart.

Local visual review showed the opening transition, title/A prompt, then **File 1 plus two Empty slots**, with the populated lower File 1 **0:00** panel. No obvious corruption was seen in the sampled captures. This matches code 15's menu content. Only the title A input was sent; no subsequent profile-selection or reset action was issued. Both guest views use Canvas readback on the primary display. No fresh human listening assessment was supplied for this run; historical choppy/short-burst audio observations are not new observations.

Comparison: [code 15 full JSON](../2026-11-06-preview5-cpu-run-001/cpu-session.json), SHA-256 `f54f724d18d31a100038138d3a0a1a302f9e0c47bbce2d717d50adec5da39633`.

| Measurement | Code 15 | Code 16 |
| --- | ---: | ---: |
| Worker-running / core slice seconds | 103.013388 / 100.869019 | 102.730802 / 100.027735 |
| Guest cycles | 4,613,064,985 | 5,151,572,725 |
| Guest seconds / emulated speed | 17.205748 / 16.70% | 19.214267 / 18.70% |
| Frame events / image deliveries | 1,021 / 1,021 | 1,140 / 1,140 |
| Native / interpreted instructions | 1,999,652,115 / 213,211 | 2,255,283,901 / 224,422 |
| PICA command-list seconds | 58.794150 | 59.261137 |
| CPU shader / decode / placement seconds | 32.618247 / 9.983917 / 7.569679 | 30.421031 / 11.231672 / 8.528793 |
| CPU vertex inputs | 188,655,172 | 219,189,218 |
| Shader / decode ns per counted input | 172.899 / 52.922 | 138.789 / 51.242 |
| Scanout seconds | 1.269030 | 1.016723 |
| SVC seconds excluding nested PICA | 33.974630 | 33.711386 |
| Unclassified core seconds after disjoint scopes | 6.779087 | 5.992349 |
| Audio underruns / discarded input frames | 1,362 / 0 | 1,532 / 160 |

Guest duration uses **268,111,856 cycles/s** and matching worker time. Code 16 active time is **102.716413 s**; observer wall time includes opening and stop observation. Frame events are not unique game FPS. The sample is **2.00 percentage points / 11.98% relatively** faster, with **19.73% lower shader time per counted input**, but unequal work counts, changing scene mix and uncontrolled thermal/load conditions prevent causal or sustained-performance claims.

The new fixed tables retain their nesting; **do not sum parent and child rows**:

| Scope | Calls | Inclusive seconds | Nested PICA seconds |
| --- | ---: | ---: | ---: |
| All SVC | 205,882 | 92.972523 | 59.261137 |
| SVC `0x32` | 48,138 | 92.934281 | 59.261137 |
| GSP IPC | 46,796 | 92.849110 | 59.261137 |
| GSP queue-dispatch wrapper | 44,604 | 92.817511 | 59.261137 |
| Queued command lists | 10,599 | 59.277112 | 59.261137 |
| Queued display transfers | 12,706 | **26.917393** | 0 |
| Queued texture copies | 10,585 | **6.060732** | 0 |
| Queued memory fills | 10,529 | 0.531378 | 0 |
| Queued DMA | 182 | 0.002364 | 0 |

Per-SVC rows exactly partition aggregate calls/wall/nested-PICA totals. IPC, direct-GSP and queued-GSP rows are nested attribution, not additional core work. Subtracting PICA, scanout and each disjoint parent `(wall − nested PICA)` leaves **5.992349 s**, including execution/scheduling/guards/memory synchronization rather than native execution alone. Frame/audio parent scopes are **0.002067/0.044073 s**, with no nested PICA. CPU shader work remains **30.41% of core**; display transfer plus texture copy is **32.97%**. Other PICA command work is **9.079641 s**. These are wall scopes, not GPU/CPU utilization or proven copy bandwidth costs.

Rendering: **10,599 command lists**, **713,881 draw calls**, **495,636,492 vertex references**, **709,909 placed/recorded draws**, **13,004 submissions**. CPU/decode/placement batches: **713,881** each; geometry **0**; parallel-threshold selections **40,872 (5.73%)**, not an active-worker count. GPU-vertex draws, software fallback, draw/compiler errors and resource-limit events are zero; pipeline-failure fields are null. **Nine retained surfaces** counts cache entries, not bytes or a leak. Native dispatches/slices/yields: **545,281/8,893/7,753**; callback-interpreted instructions **0**. Final PC **`0x0011894C`**; guest allocation **64 MiB**, memory-fault pages **0**, sample **null**. Runtime errors, first blocker and diagnostic fault are null; fatal errors, prefetch aborts and unsupported services/SVCs are zero. Outer status is stopped; the nested running snapshot precedes closure.

Audio generated **627,040 PCM frames**, **451,358 nonzero**; **626,880** input frames were resampled and **160 discarded**. All **919,389 converted frames were written**; dropped, flushed and remaining queued frames are zero. **1,532 underruns**, one playback start, five partial writes, four zero writes and **302.962 ms** maximum PCM-submission gap remain recorded. Counters do not establish audible quality or the reason for the discarded tail.

**Next concrete performance work:** inspect the generic queued display-transfer and texture-copy paths, then use bounded authored fixtures to separate synchronization/readback from format conversion/copy costs before choosing a correction. These inclusive scopes can include surface reconciliation, submission waits/readback and interrupt delivery; texture copy synchronizes both ranges before CPU copying. Measure hardware-transfer acceptance and disjoint wait/writeback versus conversion/copy phases with authored pixel, alias and stride fixtures. The current counters do not identify the dominant subphase. Preserve transfer semantics, nested timing and CPU/Vulkan correctness; no additional unchanged Thor run or GPU retry is needed. No application fix was authored in this repackaging batch. Gameplay, reliable save/load, sustained speed and reliable audio remain unqualified.

The original and reviewed JSON are byte-identical: **8,595 bytes**, SHA-256 **`071d4f1296521ee7fb6c4139a7e0f4b306a08ef86cfbd54a705d3cb15ff2144d`**. All fields, including new fixed attribution tables and zero/null values, are retained; **no redactions**. No new runtime failure required a driver-log excerpt. Only this summary and full JSON are shared; raw captures and private game/build/signing files remain local.
