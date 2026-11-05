<!-- CodexAstraUlt: Preserve the completed bounded code 13 tests and the owner's updated Native/CPU performance priority; keep the failed GPU prefix separate. -->

**Native/CPU reached file selection and stopped normally; performance remains severely limited. GPU failed before the loading/title screen, with no sound heard. The owner directs subsequent work toward Native execution with CPU vertex shaders and defers further GPU-vertex tests and audio-perfection work.**

Test date: **2026-11-04 America/New_York** (2026-11-05 UTC). Full reports: [CPU](cpu-session.json), [GPU](gpu-session.json); bounded [driver excerpt](gpu-failure-excerpt.txt).

Source **`52d9d89a74f4e5f57f515296bbfff191cae74dae`**, implementation `dffd8e4`; package `org.droidds.title.t0004000000055f00`, **0.0.8-preview.3/code 13**, min/target API 29/35. Reused Rust/Cargo 1.95.0, NDK 27.3.13750724/r27d, SDK/build-tools 35/35.0.0 and JDK 17.0.20.1. Repackaging completed in 48.230 seconds: 61 commands, 107 title JVM and 76 audio checks passed; all 310 source hashes, signing, manifest, shader and library/package gates verified. The installed APK hash matches the build. No title generation or title-object compilation occurred.

| Artifact | SHA-256 |
| --- | --- |
| Private APK, 287,642,474 bytes | `0b694139eb0226ae91fe73f8e1fd4ea2490fa5eb88d8036858ddd24784142d6e` |
| Existing public signing certificate | `a2aabf473b0c308ef2624e403231db947ebf1e64a6004d856962a8d139f94f0f` |
| Retained ARM64 title library | `44219eb7d1b769464639351dfca200d35ca74224cb9909040855835a428c5c2b` |
| Base input, 1,073,741,824 bytes | `e1c69aa34aa8fe4d95ca1a174f9ceb0485f596775cdba94205559c6de809a07a` |
| Title manifest | `c601dff93c6e69d339715c8f5bc802eb8fe6dd99dcd14358209c76eb24762557` |

Both trials used Native guest execution, Vulkan **1×**, Adreno 740 on Thor Android 13, driver **0676.53**, shader compiler **E031.41.03.47**. Dynamic blend/logic flags were false. Guest views use Canvas readback on the primary physical display. Input, title manifest and native-library hashes match both reports and the previous code 12 comparison.

CPU received one A input at **91.056 seconds**, matching the earlier control's input timing. It progressed from the title prompt to three Empty file slots/Empty Profile, without creating a profile. Normal Stop was sent at **110.137 seconds**; the observer confirmed Stopped at **114.304 seconds**. GPU had one actual Play and showed black guest output, then the error screen by **12.342 seconds**; observation ended immediately. A separate preflight stopped before Play because OCR missed its label; it performed no guest execution and remains preserved locally. No failed GPU launch was repeated. CPU JSON was exported before GPU Play; GPU JSON was exported before any subsequent launch. Neither observer omitted events. Accessibility dumps were unavailable; fresh visual confirmation and cropped status OCR were used.

| Measurement | Previous code 12 CPU | Code 13 CPU | Code 13 GPU failure |
| --- | ---: | ---: | ---: |
| Worker-running seconds | 102.698642 | 102.787530 | 2.143061 |
| Core seconds | 100.091566 | 100.175503 | 1.433602 |
| Command-processing seconds | 61.457546 | 63.360611 | 0.735344 |
| CPU vertex seconds | 33.446385 | 34.862520 | 0.000009896 |
| Scanout seconds | 1.002567 | 1.056185 | 0.042327 |
| Guest cycles, runtime snapshot | 4,879,436,163 | 4,993,353,419 | 378,491,483 |
| Guest frame events/image deliveries | 1,080/1,080 | 1,105/1,105 | 84/84 |
| Native instructions | 2,119,450,712 | 2,173,726,909 | 125,781,751 |
| Interpreted instructions | 217,193 | 229,060 | 6,687 |
| CPU vertex inputs | 203,648,359 | 210,211,245 | 4 |
| Command lists | 9,995 | 10,250 | 568 |
| Draw calls / vertex references | 656,450 / 460,543,239 | 679,201 / 475,369,554 | 1 / 6 |
| Actual GPU-vertex draws | 0 | 0 | 0 |
| Placed/recorded draws | 652,739 | 675,371 | 1 |
| Vulkan submissions | 12,157 | 12,514 | 0 |
| Audio underruns | 1,426 | 1,471 | 4 |

Code 13 CPU advances **18.624143 guest seconds / 102.787530 worker seconds = 18.12%** of real time, versus 17.72% previously. This small descriptive difference does not establish a packing-change speed gain: scene exposure/work counts differ, and vertex cost per counted input is **165.845 ns versus 164.236 ns**. Frame events are not unique game FPS. CPU vertex work accounts for **34.80% of core / 55.02% of command processing**; other command work is another **28.45% of core**. These overlapping scopes must not be added twice. One run cannot isolate thermal/load variance or establish a regression.

CPU produced **607,680 PCM frames, 431,998 nonzero**; all **891,230 converted frames were written**, with zero reported drops/discarded input but **235 flushed frames**. Maximum PCM submission gap was **307.438 ms**. The owner describes choppy, short sound bursts apparently finishing before the next frame's audio arrives. That subjective timing is not measured frame synchronization or confirmed waveform clipping. GPU produced **44,320 PCM frames, all zero**, and wrote 64,999 converted frames; the owner heard no sound before failure. Its four underruns and short silent prefix do not establish audio improvement.

GPU's concrete blocker is **`title_renderer_draw_failed` / `renderer_draw_failed`**, observed at **`0x0011894C`**, cycle **378,491,483**. The outer successful-slice cycle counter is 378,484,328, retaining a 7,155-cycle failed-call tail difference. This PC is where failure was observed, not an identified faulty guest instruction. The first recorded foreground pipeline failure reports **Vulkan result -13**, vertex stage **`interpreted`**, generic fragment mode with rasterized depth:

- Vertex SPIR-V: **50,320 bytes**, FNV-1a64 **`245d2186970be2f0`**, matching public `shade.vert.spv`.
- Fragment SPIR-V: **96,856 bytes**, FNV-1a64 **`8431ed93c93708e0`**, matching public `raster.frag.spv`.
- Static blend **`0x76760000`**, color format **37**, mask **7**; no depth attachment, depth format/creation flags **0**, logic operation null. Fragment specialization has 30 values: 29 zeroes followed by 1.
- Background/cache-probe failure slots are null. Draw errors **2**, compiler failures **0**, with two compiler jobs outstanding. One placed draw was recorded after fallback, but **no Vulkan submission or GPU-vertex draw occurred**.

The driver excerpt retains shader-link, shader-type-0 compilation and pipeline-creation errors. These lines do not identify which stage caused the link failure or isolate application versus driver responsibility. FNV fingerprints are diagnostic identities, not cryptographic hashes; the attempted interpreted vertex stage is a GPU shader choice, distinct from Native guest-CPU execution. CPU has no runtime blocker and all three pipeline slots are null. Both reports show zero fatal/prefetch/unsupported-service/SVC faults, zero sampled fault pages (sample null), and zero software raster fallback/resource-limit events. Their 64 MiB field is guest allocation, not process/driver memory.

**Next work:** prioritize profiling and optimizing Native plus CPU vertex processing and the remaining command-processing costs, with representative authored fixtures and output-equivalence checks before another private performance test. The measured packing change has no demonstrated speed benefit here. Preserve GPU's built-in pipeline failure as a deferred issue; do not schedule more GPU trials under this handoff. No new application fix was authored in this repackaging batch.

The compatible update retained app-data identity/import, owner signer and remaining saves; no uninstall, data clear or save reset occurred. Both completed 521-object builds, libraries, preparation and earlier reports remain preserved. The later code 12 Interpreter report was separately exported before installation and is not part of this comparison. Local work/stashes were retained. Only reviewed diagnostics are shared; all private game/build/signing artifacts and captures remain local.

Both JSON copies require **no redaction** and preserve every original byte and field:

| Report | Bytes | Original and reviewed SHA-256 |
| --- | ---: | --- |
| CPU | 4,492 | `706133028ea3d527f8e71c98bcdc03833a7d7e982b5b57acd1c62f7aa32e9569` |
| GPU | 5,074 | `445292cbd989a99c31abcba9e38f76c78fe287e39f2d58539be7a7595f68059d` |

The driver excerpt selects **10 error lines (raw lines 32–41)**, strips process IDs and omits the other **31 raw lines**, retaining only normalized public driver context. The local raw log is **2,655 bytes**, SHA-256 `cfd17d10d7183ea0f4bc7b394f5e0179d6812b87d6e78ce95672b8492253effc`; the reviewed excerpt is **863 bytes**, SHA-256 `213fd9348887c4199a71387a866be447e554bd5f4042f69cd3712561141a7237`. Repeated messages are not counts of unique failed attempts. Gameplay, save/load, sustained speed and reliable audio remain unqualified.
