<!-- CodexAstraUlt: Preserve the successful CPU menu observation and failed GPU attempt as separate reports; no performance gain is inferred from the short failed run. -->

**CPU reached file selection and stopped normally, with persistent audible crackling. GPU failed before the title screen while creating a Vulkan pipeline.** Both JSON reports were exported separately before any subsequent launch. There was one actual guest run per vertex policy; no failed GPU replay or title recompilation occurred.

Test date: **2026-11-04** (America/New_York). Source: `RegiRex/DroiDDS` main at `65e11642e9c5b433cd4e634216b722d3fe08aa50`. The prior branch and local handoff preference were preserved; the preference remains an unstaged documentation change. Followed the current repackaging/comparison procedure and report-transfer instructions.

Reused preparation run-002, the completed 521-object ARM64 library and existing owner signing profile. Repackaging rebuilt only the shared runtime/frontend, using installed Rust/Cargo 1.95.0, NDK r27d/27.3.13750724, SDK/build-tools 35/35.0.0 and JDK 17.0.20.1 with offline/locked dependencies. All 61 packaging commands passed, including **107 JVM logic/selection/timing checks and 76 audio checks**, shader, manifest, library, alignment and signature audits. Independent review confirmed all 310 source hashes and unchanged embedded title library/manifest. The prerequisite cloud CPU/GPU original-fixture gates were already recorded as passing.

| Artifact | Identity |
| --- | --- |
| Package | `org.droidds.title.t0004000000055f00` |
| Installed version | `0.0.8-preview.2`, code 12; compatible update from code 11 |
| APK | 287,613,802 bytes; SHA-256 `fc869f2a4dd8b2e80e301f03c1e96e97003f7cd3d4d6e3d399dc9c5e8123ca44` |
| Retained ARM64 library SHA-256 | `44219eb7d1b769464639351dfca200d35ca74224cb9909040855835a428c5c2b` |
| Public owner certificate SHA-256 | `a2aabf473b0c308ef2624e403231db947ebf1e64a6004d856962a8d139f94f0f` |
| Input SHA-256 | `e1c69aa34aa8fe4d95ca1a174f9ceb0485f596775cdba94205559c6de809a07a` |
| Title manifest SHA-256 | `c601dff93c6e69d339715c8f5bc802eb8fe6dd99dcd14358209c76eb24762557` |

Installed APK bytes match the reviewed artifact. The same certificate, app-data identity and ready import were retained. Device: **AYN Thor, Android 13/API 33, ARM64, 4 KiB pages, Adreno 740, driver 0676.53**, shader compiler E031.41.03.47. Both runs requested **Native guest execution, Vulkan rasterization, scale 1**. Only vertex policy changed from CPU to GPU; dynamic blend and dynamic logic-op flags were false in both. The owner selected GPU after the CPU report was preserved.

CPU started at **22:18:29.942 UTC**. A was sent at +91.058 s, normal Stop at about +110 s, and Stopped observed at +114.476 s. Both guest views showed the title and then three empty file slots; no profile was created or selected. The owner heard persistent crackling and confirmed it stopped with the run. The CPU report was saved before changing policy or starting GPU.

GPU started at **22:26:06.991 UTC** and automatically stopped on failure. The first sampled error screen was at **+12.331 s**, including startup; measured worker execution was **2.043 s**. No recognizable title/menu appeared, and the owner heard no sound. An earlier GPU readiness check failed before sending Play and is preserved as an unstarted observer attempt. The observation helper later missed the error text and was interrupted at +81.592 s, after the app had already stopped; that observation duration is not guest execution time. No scheduled A or second GPU Play was sent. The failure JSON was exported before any restart. Observer event omissions were zero.

| Measurement | CPU vertices | GPU vertices, failed early |
| --- | ---: | ---: |
| Status / first blocker | stopped / none | failed / renderer_draw_failed |
| Actual native / interpreted instructions | 2,119,450,712 / 217,193 | 125,781,911 / 6,527 |
| Runtime cycles | 4,879,436,163 | 378,557,019 |
| Successful slices / native calls | 8,613 / 8,613 | 145 / 146 |
| Guest frame events / delivered images | 1,080 / 1,080 | 84 / 84 |
| Worker running time | 102.699 s | 2.043 s |
| Core slice time | 100.092 s | 1.323 s |
| Command processing | 61.458 s | 0.636 s |
| CPU vertex processing | 33.446 s | 0.000010365 s |
| Scanout | 1.003 s | 0.040 s |
| CPU batches / vertex inputs | 656,450 / 203,648,359 | 1 / 4 |
| Recorded GPU / placed draws | 0 / 652,739 | 0 / 1 |
| Vulkan submissions | 12,157 | 0 |
| Guest PCM / nonzero PCM frames | 593,760 / 418,078 | 44,320 / 0 |
| Converted / written output PCM frames | 870,814 / 870,814 | 64,999 / 64,999 |
| Audio underruns | 1,426 | 4 |
| Maximum producer PCM submission gap | 313.101 ms | 645.440 ms |

Actual instruction counts exclude callback-interpreted work; callbacks were zero. GPU outer cycles remain **378,549,864**, 7,155 below the runtime snapshot because the failed call did not publish successful frontend metrics. Preserve both values. GPU requested/selected policy was GPU, but **zero GPU-vertex draws and zero submissions** mean no submitted GPU-vertex workload or speed advantage was demonstrated. The early failure prevents the intended same-menu performance comparison; its low underrun count is not an audio improvement.

CPU advanced **18.199 guest seconds in 102.699 worker seconds (17.72%)**. CPU vertex work consumed **54.42% of command time / 33.42% of core time**. That timer is a command-processing subset, not an extra additive phase; it includes geometry, packing and joins. Screen readback was about 1% of core time. Native instruction share does not measure shader cost. Both audio reports show zero dropped, discarded or flushed frames, one playback start, queue high-water 1,300/8,192 frames, five partial writes including four zero writes. Slow production with fixed-rate playback is consistent with gaps, but neither counters nor hearing establish it as the sole cause of crackling. Producer submission gaps are not measured audible-gap durations.

**First concrete GPU blocker:** `renderer_draw_failed`, observed PC **0x0011894C**, runtime cycle **378,557,019**. Runtime error is `title_renderer_draw_failed`; hardware records two draw errors and a pipeline-creation unknown error. The bounded [driver excerpt](gpu-failure-excerpt.txt) reports shader linking and `shaderType: 0` compilation failures. Runtime `compiler_failures=0` measures a different stage and does not negate these driver messages. The observed PC is a detection location, not an identified faulting guest instruction. Neither application nor driver responsibility is isolated yet.

Next: privately validate the actual generated shader, stage interfaces and static-state pipeline parameters, then reproduce the failure with an original fixture before a generic correction and another GPU trial. Preserve CPU as the working comparison path. No new application fix was made in this batch. Both runs have zero fatal/prefetch/unsupported-service/SVC/memory-fault counters and zero software-raster fallbacks; GPU's draw error remains a failure. The 64 MiB memory value is guest allocation, not process RSS. This batch does not qualify gameplay, save/load correctness, reliable audio or sustained performance.

Preservation passed for **5,542 protected metadata records**, both 521-object Linux/ARM64 builds and libraries, original input/preparation, signer and previous reports. The prior latest report was exported before installation. No uninstall, data clear, save reset, tool setup, permission reconfiguration or generated-title compilation occurred. The app is stopped. Raw originals, private captures, game data and build/signing artifacts remain local.

Reviewed diagnostic JSON copies are **byte-identical** to their local originals; no fields were redacted:

- [CPU report](cpu-session.json), 4,414 bytes: SHA-256 `f12f8a8ce95793b0f6fe612fd02ad8628d92f4a01074b0687d5b26e8dd7aa82c`.
- [GPU failure report](gpu-session.json), 4,506 bytes: SHA-256 `d71adc650a43221fc414b074362d292ebd2b8a9b1f3466ee57bd0f4a101f55bb`.
- [Reviewed driver excerpt](gpu-failure-excerpt.txt): SHA-256 `7838e19d59c443924e7a81e5d1f4cce97598ebd71680a3a72bbdd6ee2cf48687`. Only relevant driver error lines and context were retained; process IDs were removed. The complete 2,290-byte raw process log stays local, SHA-256 `cd1b6b0f56d4fbbc4db38f37c748e4cb97f8a20535a7eaf53bf6b971e447ee42`.

After the bounded batch, the owner independently reported trying Interpreter: GPU did not load, and CPU vertex mode performed visibly much worse than the Native run. No corresponding Interpreter JSON was supplied for this handoff; these manual observations are separate from both uploaded Native reports and do not establish an identical GPU failure cause.
