<!-- CodexAstraUlt: Record the single code14 Native/CPU run, preserve measured costs and limitations, and keep GPU testing deferred. -->

**Code 14 reached file selection and stopped normally. Severe slowdown and owner-observed choppy audio remain. This run measured 17.31% emulated speed versus 18.12% for code 13; it establishes no overall performance improvement. GPU testing remained deferred.**

Test date: **2026-11-05**, America/New_York. Full reviewed [CPU report](cpu-session.json). Source **`ce09834b4eca63aeafef7102571690ad1efc90fd`**, implementation `a77a85e895461f6f62b9fa868c5bab5a82a64b44`. The documented original-fixture/cloud/publication gates passed before this private batch.

Repackaged the retained ARM64 title library using Rust/Cargo **1.95.0**, NDK **27.3.13750724/r27d**, SDK/build-tools **35/35.0.0**, JDK **17.0.20.1**, and the existing owner signing profile. Packaging completed in **48.489 seconds**; all **61 commands**, **107 title JVM + 76 audio checks**, source/library/shader/manifest/signature/alignment gates passed. Independently verified all **310 source hashes** and the installed APK identity. Package `org.droidds.title.t0004000000055f00`, **0.0.8-preview.4/code 14**, min/target API **29/35**. No title generation, title-object compilation or tool setup was repeated.

| Identity | SHA-256 |
| --- | --- |
| Private APK, 287,687,530 bytes | `b328d26c208b4737ee4088cc0727c313263a6e6f617d707bc25a44ab8dc6fdde` |
| Existing public signing certificate | `a2aabf473b0c308ef2624e403231db947ebf1e64a6004d856962a8d139f94f0f` |
| Retained ARM64 title library | `44219eb7d1b769464639351dfca200d35ca74224cb9909040855835a428c5c2b` |
| Base input, 1,073,741,824 bytes | `e1c69aa34aa8fe4d95ca1a174f9ceb0485f596775cdba94205559c6de809a07a` |
| Title manifest | `c601dff93c6e69d339715c8f5bc802eb8fe6dd99dcd14358209c76eb24762557` |

The compatible update preserved app-data identity and the retained import. The previous latest report was exported before installation and matches the preserved code 13 GPU failure byte-for-byte; it was not rerun. Both completed **521-object** target builds/libraries, preparation, original input, signer and previous reports remain intact: **6,433 protected file records unchanged**. Local changes and stashes were preserved. No uninstall, data clear, save reset or reimport occurred.

**One actual Play**, Native guest execution, explicit **CPU vertex shaders**, **Vulkan 1×**, Thor/Adreno 740. Dynamic blend and logic-operation flags were false. A single A input was sent at **91.054 seconds** after visually confirming the title prompt. The game progressed to three Empty file slots and Empty Profile; no profile was created. Normal Stop was sent at **110.057 seconds**; Stopped was observed at **114.278 seconds**, within the 120-second bound. No obvious corruption appeared in reviewed captures. Both guest views appeared on the primary physical display through Canvas readback. Fresh screenshots and cropped status OCR were used because accessibility dumps returned a null root. There were **zero observer errors/omissions**, no replay and no GPU trial. The full JSON was exported before any restart.

Comparison uses the preserved [code 13 CPU report](../2026-11-04-preview3-pipeline-run-001/cpu-session.json), SHA-256 `706133028ea3d527f8e71c98bcdc03833a7d7e982b5b57acd1c62f7aa32e9569`.

| Measurement | Code 13 CPU | Code 14 CPU |
| --- | ---: | ---: |
| Worker-running seconds | 102.787530 | 102.612507 |
| Core slice seconds | 100.175503 | 100.000786 |
| Guest cycles | 4,993,353,419 | 4,762,726,240 |
| Guest seconds / emulated speed | 18.624143 / 18.12% | 17.763952 / 17.31% |
| Frame events / image deliveries | 1,105 / 1,105 | 1,054 / 1,054 |
| Native / interpreted instructions | 2,173,726,909 / 229,060 | 2,064,824,389 / 213,733 |
| Command-processing seconds | 63.360611 | 58.268575 |
| CPU vertex seconds | 34.862520 | 31.175055 |
| CPU vertex inputs | 210,211,245 | 197,133,760 |
| CPU vertex ns per counted input | 165.845 | 158.142 |
| Command milliseconds per frame event | 57.340 | 55.283 |
| Scanout seconds | 1.056185 | 1.012470 |
| Core seconds outside command + scanout | 35.758706 | 40.719741 |
| Audio underruns / flushed frames | 1,471 / 235 | 1,382 / 0 |

Guest duration uses **268,111,856 cycles/second** and the matching worker-running denominator; frame events are not unique game FPS. The aggregate vertex cost per counted input is lower, while achieved guest progress is lower overall. Work counts and scene exposure differ, with uncontrolled device/load/thermal variation. One run cannot establish a causal speed regression or partition changes among vertex-output work and native-fence verification. The fence-cache change has no runtime hit/miss or scan-frequency counter in this report.

Code 14's new disjoint CPU timings provide a more specific breakdown:

| Work | Seconds | Share of core |
| --- | ---: | ---: |
| CPU vertex/shader processing | 31.175055 | 31.17% |
| Input decoding | 10.760378 | 10.76% |
| Placement: assembly/clipping/culling/screen placement | 7.750576 | 7.75% |
| Remaining command processing | 8.582566 | 8.58% |
| Scanout | 1.012470 | 1.01% |
| Core outside command processing and scanout | 40.719741 | 40.72% |

These are wall-time scopes, not hardware utilization. Shader/decode/placement are subsets of command time; do not add them again to parent totals. Decode excludes the initial raw index read and cached input-plan lookup; placement excludes Vulkan draw work. There were **634,729 CPU, decode and placement batches**, **zero geometry-mode selections**, and **36,762 parallel-threshold selections (5.79% of CPU batches)**. The latter counts eligible input batches, not active workers or geometry-stage work. Code 13 lacked these new fields; their earlier values are unmeasured.

Rendering recorded **9,741 command lists**, **634,729 draw calls**, **445,827,396 vertex references**, **631,171 placed/recorded draws**, and **11,803 submissions**. Actual GPU-vertex draws and software raster fallbacks were zero. Callback-interpreted instructions were zero. Final observed PC was **`0x0011894C`**. Error/first-blocker fields are null; fatal errors, prefetch aborts, unsupported services/SVCs, GPU draw/compiler errors and resource-limit events are zero. All three pipeline-failure slots are null. Memory-fault pages are zero with sample null; **64 MiB** denotes guest allocation, not process/driver memory. The outer state is stopped; the nested running snapshot was captured before closing and does not indicate a failed stop.

Audio produced **579,520 PCM frames, 403,838 nonzero**; all **849,930 converted frames were written**. Reported drops, discarded input, flushes and queued frames are zero. There were **1,382 underruns**, one playback start and a **306.136 ms** maximum PCM-submission gap. The owner reports **“choppy audio still.”** Fewer underruns over different guest progress do not establish an audible improvement. Audio perfection remains secondary to Native/CPU performance.

**Next diagnostic:** identify the **40.720 seconds of core work outside command processing and scanout**, while continuing to profile the **31.175-second CPU shader path**. Use bounded profiling or fixed counters with authored-fixture correctness checks to locate the remaining cost before another changed private build. The current measurements do not justify a specific native-fence or shader correction, a longer unchanged run or renewed GPU testing. No new application fix was authored locally in this repackaging batch. Gameplay, reliable save/load, sustained speed and reliable audio remain unqualified.

The reviewed JSON is **4,693 bytes**, identical to its original, with **no redactions**. Original/reviewed SHA-256: **`78dd8b128fb9a8ba41889b7165c36c3a65c3e46e18557d5bc86959cc521c0cf2`**. No new failure required a driver-log capture. Private game/build/signing data and captures remain local; only this summary and the full reviewed JSON are shared.
