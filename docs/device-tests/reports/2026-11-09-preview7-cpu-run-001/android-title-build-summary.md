<!-- CodexAstraUlt: Preserve the single approved code17 Native/CPU result, actual route eligibility and owner audio observation without claiming unique game FPS or a causal performance change. -->

**Preview.7/code 17 reached file selection and stopped normally, with no reported runtime/rendering failure or obvious corruption in reviewed run captures. It measured 18.66% emulation speed and 11.07 frame events/s, essentially unchanged from code 16's 18.70% and 11.10 events/s. Unique displayed game FPS is not measured. The owner reports: “Audio is clipping still, very badly.” No performance improvement is established.**

The new counters explain the candidate's lack of eligible work in this menu run: **hardware-tiled accepts and deferred transfers/flushes are all zero**. All **7,674 accepted hardware display transfers are linear**; another **5,002 requests follow the software transfer path**, with zero reported hardware-attempt errors. The largest new measured scopes are **23.980 s of hardware-transfer attempts** and **5.906 s of texture-copy synchronization**. This narrows the next investigation; it does not justify a specific correction or another unchanged run.

Test date **2026-11-09**, America/New_York; execution started **08:41:02 UTC**. Full reviewed [CPU JSON](cpu-session.json). Source `3c657abfa3c1f5acde5c599fc16cc6142c711555`; implementation `92960106becc70913434f7d90ec75b89c492c528`; release `1c7fffa2a0b4ee210dc78db55bc88188d6d41857`. Later source changes are documentation only. Before packaging, [CPU main](https://github.com/RegiRex/DroiDDS/actions/runs/42581239578), [Android main](https://github.com/RegiRex/DroiDDS/actions/runs/42581239588) and [tag publication](https://github.com/RegiRex/DroiDDS/actions/runs/42581472242) passed on their expected sources: four jobs, 48 successful steps and three expected failure-reporting skips. Public asset identities match; independent download verification remains documented cloud evidence, without another local download.

Repackaged with the retained preparation, ARM64 title library and owner signer: Rust/Cargo **1.95.0**, NDK **27.3.13750724/r27d**, SDK/build-tools **35/35.0.0**, JDK **17**. Build **51.890 s**; all **61 commands**, **107 title JVM + 76 audio checks**, shader/manifest/signature/library/alignment gates passed. Independent static review matched **312 source hashes**, the actual APK certificate, its 12-entry inventory and three stored, 16-KiB-aligned ARM64 libraries. No title regeneration/recompilation, tool setup or permission changes occurred.

| Identity | Value / SHA-256 |
| --- | --- |
| Package | `org.droidds.title.t0004000000055f00`, `0.0.8-preview.7`, code **17**, API **29/35**, non-debuggable |
| Private APK | **287,720,298 bytes**; `6503682104bba0811f2ab43c22698c02508dfc273e7bfd68d370dc27479ee01b` |
| Existing public owner certificate | `a2aabf473b0c308ef2624e403231db947ebf1e64a6004d856962a8d139f94f0f` |
| Retained ARM64 title library | `44219eb7d1b769464639351dfca200d35ca74224cb9909040855835a428c5c2b` |
| Rebuilt shared player | `33f95a04d82a2f1a3142f1ad3df9b4e03e405c5e85bec9ae5a7c730b860297b5` |
| Original input | `e1c69aa34aa8fe4d95ca1a174f9ceb0485f596775cdba94205559c6de809a07a` |
| Title manifest | `c601dff93c6e69d339715c8f5bc802eb8fe6dd99dcd14358209c76eb24762557` |

Package verification preceded STOP and the explicit access request. The owner then approved exclusive operation. Actual code 16 matched its retained APK/signature identity; its latest report was exported before installation and exactly matches the preserved code 16 report. Code 17 installed compatibly; installed APK hash and app-data identity were verified. Final host audit passed all **7,585 protected records** and 312 source hashes: both **521-object** builds/libraries, preparation, original input, signer and prior reports remain preserved. Previous local commits/stashes and the exact **1,164-byte** unstaged owner suffix remain intact. No uninstall, clear, reimport or save reset occurred.

**One Play, Native execution, explicit CPU vertices, Vulkan 1×, Thor/Adreno 740.** Observer-clock Play completed at **0.044 s**, A at **91.050 s**, Stop at **110.151 s**; Stopped was observed at **114.347 s**, within the 120-second limit. A/Stop were **91.006/110.107 s after Play completion**. Five heading keepalives, no other guest input, no replay or GPU trial; zero observer errors/omissions. Only the title A input was sent; no subsequent profile-selection/reset action was issued. Captures show the title prompt, then **File 1 plus two Empty slots** and the populated lower **File 1 0:00** panel, matching code 16. Both guest views use Canvas readback on the primary display.

Export began after Stop, but the local UI guard rejected a secondary-display launcher listed before display 0. Fresh inspection showed the title still Stopped on display 0. The local guard was corrected to check display 0 explicitly; the full JSON was exported at **08:46:05 UTC before any restart**. This was an export-helper issue, not a reported runtime failure. Original helpers and raw evidence remain local.

Comparison uses [code 16 JSON](../2026-11-09-preview6-cpu-run-001/cpu-session.json), SHA-256 `071d4f1296521ee7fb6c4139a7e0f4b306a08ef86cfbd54a705d3cb15ff2144d`.

| Measurement | Code 16 | Code 17 |
| --- | ---: | ---: |
| Worker / core slice seconds | 102.730802 / 100.027735 | 102.780226 / 100.089472 |
| Guest cycles | 5,151,572,725 | 5,141,315,519 |
| Guest seconds / emulated speed | 19.214267 / 18.70% | 19.176010 / 18.66% |
| Frame events / Java image deliveries | 1,140 / 1,140 | 1,138 / 1,137 |
| Frame events per worker second | 11.097 | 11.072 |
| Native / interpreted instructions | 2,255,283,901 / 224,422 | 2,249,770,374 / 225,964 |
| PICA command-list seconds | 59.261137 | 59.214093 |
| CPU shader / decode / placement seconds | 30.421031 / 11.231672 / 8.528793 | 30.392867 / 11.312921 / 8.407909 |
| CPU vertex inputs | 219,189,218 | 218,513,560 |
| Queued display / texture seconds | 26.917393 / 6.060732 | 27.062748 / 6.135552 |
| SVC seconds outside nested PICA | 33.711386 | 33.924064 |
| Scanout / unclassified core seconds | 1.016723 / 5.992349 | 0.996011 / 5.909062 |
| Actual submissions / retained surfaces | 13,004 / 9 | 12,969 / 9 |
| Audio underruns / discarded input frames | 1,532 / 160 | 1,531 / 480 |

Guest duration uses **268,111,856 cycles/s** and matching worker time. Active time is **102.779280 s**. Java image deliveries average **11.062/s**; the runtime separately reports **1,138 frames delivered**, versus **1,137** accepted Java image deliveries. Preserve both scopes; aggregate counters do not identify the particular missing delivery or unique image count. The small speed difference is not evidence of regression or sustained improvement; scene mix and load/thermal conditions remain uncontrolled.

New transfer details are **nested subsets of existing GSP/SVC work**, not additional core time:

| New request scope | Calls / route | Seconds |
| --- | --- | ---: |
| Display requests | 12,676 | 27.053800 |
| Hardware attempts, including declines | 12,676 attempts; 7,674 accepted linear; 0 accepted tiled; 5,002 fallbacks; 0 errors | **23.979651** |
| Software display copy/conversion | 5,002 calls; 0 empty | 3.063192 |
| Software display input / output sync | Same software path | 0.002031 / 0.001072 |
| Texture requests | 10,560 strided; 0 contiguous | 6.129924 |
| Texture input / output sync | Disjoint phases | **3.769820 / 2.136552** |
| Texture byte copy | Disjoint phase | 0.218925 |

Hardware attempts account for **88.64%** of display-request time; their timing includes accepted and declined attempts, reconciliation, recording, capture and waits. It is not pure GPU execution or accepted-linear time alone. Texture synchronization accounts for **96.35%** of its request total. Phase remainders are **7.855 ms display / 4.626 ms texture**; enclosing queued-operation scopes additionally include address conversion/interrupt overhead. Transfer fallback is distinct from software raster fallback. No tiled work was accepted, so the new batching path was not exercised; this does not disprove its authored-fixture result. New fields absent from code 16 are unmeasured, not zero.

Per-SVC rows exactly partition aggregate SVC measurements. All **59.214093 s** of PICA work is nested under SVC `0x32`/GSP; parent and child tables must not be added. Subtracting disjoint parent exclusive scopes, PICA and scanout leaves **5.909062 s**, including execution, scheduling, guards and memory synchronization, not native execution alone. Frame/audio parent scopes are **0.002218/0.044023 s**; other PICA work is **9.100395 s**. These are wall-time scopes, not utilization. Nine retained surfaces is an entry count, not a byte/leak measurement.

Rendering: **10,572 command lists**, **710,400 draw calls**, **494,112,972 vertex references**, **706,444 placed/recorded draws**, **12,969 submissions**. GPU-vertex draws, software raster fallback, draw/compiler errors and resource-limit events are zero; all pipeline-failure fields are null. Native dispatches/slices/yields: **546,040/8,919/7,781**; callback-interpreted work **0**. Final PC **`0x00116C24`**. Guest allocation **64 MiB**; memory-fault pages **0**, sample **null**. Error, first-blocker and diagnostic-fault fields are null; fatal errors, prefetch aborts and unsupported services/SVCs are zero. Outer status is stopped; nested runtime status is its running snapshot.

Audio generated **625,760 PCM frames**, **450,078 nonzero**; **625,280 input frames resampled**, **480 discarded**. All **917,042 converted frames were written**; output drops, flushes and remaining queued frames are zero. **1,531 underruns**, one playback start, eight partial writes, six zero writes, maximum PCM-submission gap **297.910 ms**. The owner's severe-clipping observation is fresh for this run; no waveform measurement identifies whether the perceived distortion is amplitude clipping, gaps or another mechanism. Reliable audio remains unqualified.

**Next concrete performance work:** investigate the measured hardware-attempt path, particularly unchanged linear-transfer synchronization/capture/submission, and texture input/output synchronization with bounded authored fixtures. Separate waits/readback/coherence from actual copy/recording before choosing a generic correction; the current 23.980-second hardware-attempt aggregate does not isolate its dominant internal phase. Preserve visibility/alias/stride semantics. No further unchanged Thor run, larger budget or GPU retry is justified. No application fix was authored locally; only the private export-helper display guard changed. Gameplay, save/load and sustained speed remain unqualified.

Original and reviewed JSON are byte-identical: **9,293 bytes**, SHA-256 **`a164dbbfa4f86be87bee9bb0aac519a1f57b8db4d9109b8b356435a4a6d5bb2b`**. All new fields and zero/null values are retained; **no redactions**. No new runtime failure required a driver-log excerpt. Only this summary and full JSON are shared; raw captures and private game/build/signing files remain local.
