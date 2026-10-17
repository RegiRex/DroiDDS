# Annotated References

**Research date:** 2026-10-17  
**Scope:** 3DS static recompilation, HLE runtimes, PICA rendering, shader/pipeline stutter mitigation, Android ARM64 packaging, and analogous compatibility/recompilation projects.

---

## 1. How to use this reference file

References are assigned stable IDs (`R01`, `R02`, …) used throughout this pack. Each entry records:

- source type;
- direct location;
- what the source supports;
- confidence/limitations; and
- where useful, the observed commit or version.

Priority order for technical claims:

1. source code and project-owned technical documentation;
2. official platform documentation;
3. official project README/release notes;
4. independent technical analysis;
5. community reports only when no stronger source exists.

Repository behavior can change quickly. The two central projects are pinned below to the commits observed during research; a real implementation must create its own lock file.

---

# Core 3DS recompilation sources

## R01 — `3dsrecomp` repository README

- **Project:** fearkov/3dsrecomp
- **URL:** https://github.com/fearkov/3dsrecomp
- **Direct README:** https://github.com/fearkov/3dsrecomp/blob/main/README.md
- **Type:** Primary project documentation
- **Observed main commit:** `c3f21f94ba50d688025febc8974ff348d471b587` (2026-10-09)
- **Supports:**
  - 3DS ARM/Thumb/VFP static recompilation to C;
  - function/code discovery;
  - executable and CRO coverage;
  - interpreter fallback through Zakuro;
  - reported ~99.8% native executed-instruction coverage in tested titles;
  - differential verification;
  - local-only handling of title-derived code.
- **Limitations:** Work in progress; reported coverage is title/scenario-specific.

## R02 — `3dsrecomp` host interface documentation

- **URL:** https://github.com/fearkov/3dsrecomp/blob/main/docs/interface.md
- **Type:** Primary technical specification
- **Supports:**
  - ABI versioning;
  - shared-library outputs;
  - entries/modules/origins;
  - guest CPU context;
  - page-table and host callbacks;
  - unsupported-instruction interpretation;
  - code lookup;
  - SVC/budget/unwind exits;
  - CRO base handling;
  - origin validation;
  - `-ffp-contract=off` requirement.
- **Importance:** Authoritative source for integrating a host runtime. The implementation should follow this document rather than inventing a parallel ABI.

## R03 — `3dsrecomp` standalone port documentation

- **URL:** https://github.com/fearkov/3dsrecomp/blob/main/docs/port.md
- **Type:** Primary technical documentation
- **Supports:**
  - difference between building a library and a standalone port;
  - linking recompiled code with Zakuro runtime;
  - continued need for user-provided title data;
  - local-only treatment of generated code.

## R04 — `3dsrecomp` override documentation

- **URL:** https://github.com/fearkov/3dsrecomp/blob/main/docs/overrides.md
- **Type:** Primary technical documentation
- **Supports:**
  - hand-written C replacement functions;
  - executable and CRO-relative function replacement;
  - calling original generated functions;
  - patch/mod/performance use cases;
  - verification behavior when an override deliberately changes output.

## R05 — `3dsrecomp` source tree and ABI header

- **Repository tree:** https://github.com/fearkov/3dsrecomp/tree/main
- **ABI header:** https://github.com/fearkov/3dsrecomp/blob/main/abi/recomp.h
- **Key source areas:**
  - `src/codegen/arm.rs`
  - `src/codegen/thumb.rs`
  - `src/codegen/vfp.rs`
  - `src/discover.rs`
  - `src/cro.rs`
  - `src/verify.rs`
  - `src/compile.rs`
- **Type:** Primary source code
- **Supports:** Concrete implementation of the architecture summarized by R01–R04.

## R06 — `3dsrecomp` package/license declaration

- **URL:** https://github.com/fearkov/3dsrecomp/blob/main/Cargo.toml
- **Type:** Primary package manifest
- **Observed:** package `recomp3ds`, version `0.1.0`, MIT license, Rust 1.88 minimum at research snapshot.
- **Supports:** License and feature/dependency claims.

---

# Zakuro runtime and graphics sources

## R07 — Zakuro README

- **Project:** fearkov/zakuro
- **URL:** https://github.com/fearkov/zakuro
- **Direct README:** https://github.com/fearkov/zakuro/blob/main/README.md
- **Type:** Primary project documentation
- **Observed main commit:** `412900a5a020301da15c1cc382585e05a489a535` (2026-10-15)
- **Observed workspace/release version:** `0.2.27`
- **Supports:**
  - Rust HLE 3DS emulator;
  - AOT/recompiled-code workflow;
  - interpreter fallback;
  - Windows/Linux desktop support;
  - title import/update/mod/texture behavior;
  - local recompilation workflow.

## R08 — Zakuro compatibility list

- **URL:** https://github.com/fearkov/zakuro/blob/main/COMPATIBILITY.md
- **Type:** Project-maintained compatibility documentation
- **Supports:** Breadth of titles reported playable/in-game in the current runtime.
- **Limitations:** A compatibility label is not proof of a complete playthrough or identical behavior on Android.

## R09 — Zakuro latest observed release

- **URL:** https://github.com/fearkov/zakuro/releases/tag/v0.2.27
- **Type:** Official release
- **Observed publication:** 2026-10-13
- **Supports:** Current release/version context at research time.

## R10 — Zakuro workspace/license manifest

- **URL:** https://github.com/fearkov/zakuro/blob/main/Cargo.toml
- **Type:** Primary package manifest
- **Observed:** MIT workspace license, version `0.2.27`, Rust 1.95 minimum, dependency on `recomp-abi`.
- **Supports:** License, component layout, and direct 3dsrecomp relationship.

## R11 — Zakuro Vulkan hardware renderer

- **URL:** https://github.com/fearkov/zakuro/blob/main/crates/zakuro-gpu/src/raster/hardware.rs
- **Pinned research URL:** https://github.com/fearkov/zakuro/blob/412900a5a020301da15c1cc382585e05a489a535/crates/zakuro-gpu/src/raster/hardware.rs
- **Type:** Primary source code
- **Supports:**
  - host-GPU rasterization;
  - surface/image tracking;
  - in-flight command behavior;
  - pipeline creation and lookup;
  - generic path use during specialization;
  - disk-backed `VkPipelineCache` state.

## R12 — Zakuro PICA fragment shader / dynamic fallback

- **URL:** https://github.com/fearkov/zakuro/blob/main/crates/zakuro-gpu/shaders/raster.frag
- **Pinned research URL:** https://github.com/fearkov/zakuro/blob/412900a5a020301da15c1cc382585e05a489a535/crates/zakuro-gpu/shaders/raster.frag
- **Type:** Primary shader source
- **Supports:**
  - PICA texture, lighting, six-combiner, and alpha-test behavior;
  - specialization constants for optimized variants;
  - `DYNAMIC` generic behavior reading state from draw registers;
  - explicit design intent to draw while a specialized combination compiles.
- **Importance:** This is the strongest evidence that the proposed hybrid-ubershader design already exists in Zakuro.

## R13 — Zakuro TEV implementation

- **URL:** https://github.com/fearkov/zakuro/blob/main/crates/zakuro-gpu/src/tev.rs
- **Type:** Primary source code
- **Supports:** PICA six-stage texture-environment/combiner decoding and behavior.

---

# Mature 3DS emulator references

## R14 — Azahar repository

- **Project:** azahar-emu/azahar
- **URL:** https://github.com/azahar-emu/azahar
- **README:** https://github.com/azahar-emu/azahar/blob/master/README.md
- **Type:** Primary project documentation/source
- **Supports:**
  - mature desktop and Android HLE 3DS emulator;
  - Citra-derived compatibility;
  - Android platform requirements and frontend;
  - mature service, input, and graphics references.

## R15 — Azahar Vulkan shader disk cache

- **URL:** https://github.com/azahar-emu/azahar/blob/master/src/video_core/renderer_vulkan/vk_shader_disk_cache.cpp
- **Type:** Primary source code
- **Supports:**
  - background shader worker queues;
  - vertex/fragment/geometry cache handling;
  - direct SPIR-V fragment generation with fallback paths;
  - persisted shader/PICA configurations;
  - recorded pipeline configurations.
- **Use:** Reference implementation for cache schemas, worker orchestration, and mature Android-capable shader handling.

## R16 — Panda3DS repository

- **Project:** wheremyfoodat/Panda3DS
- **URL:** https://github.com/wheremyfoodat/Panda3DS
- **README:** https://github.com/wheremyfoodat/Panda3DS/blob/master/readme.md
- **Type:** Primary project documentation
- **Supports:**
  - independent HLE 3DS implementation;
  - Android ARM64 APK builds;
  - Vulkan/OpenGL paths;
  - Dynarmic CPU backend;
  - experimentation with virtualization and tooling.
- **Use:** Android/build/reference source, not the recommended base.

## R17 — 3dbrew hardware and GPU documentation

- **Main:** https://www.3dbrew.org/wiki/Main_Page
- **Hardware:** https://www.3dbrew.org/wiki/Hardware
- **GPU:** https://www.3dbrew.org/wiki/GPU
- **Shader instruction set:** https://www.3dbrew.org/wiki/GPU/Shader_Instruction_Set
- **CRO:** https://www.3dbrew.org/wiki/CRO0
- **NCCH:** https://www.3dbrew.org/wiki/NCCH
- **DSP services:** https://www.3dbrew.org/wiki/DSP_Services
- **Type:** Community reverse-engineering documentation
- **Supports:** 3DS hardware/file/service facts.
- **Limitations:** Community-maintained, not official Nintendo documentation. Cross-check critical semantics with tests and emulator source.

## R18 — ARM11 MPCore technical reference

- **Publisher:** Arm
- **URL:** https://developer.arm.com/documentation/ddi0360/latest/
- **Type:** Official architecture documentation
- **Supports:** ARM11 MPCore/ARMv6K architecture background.

---

# ARM/Linux/Android 3DS experiments

## R19 — Zakuro Android PRoot experiment

- **Project:** ZenixX-dev/zakuro-android
- **URL:** https://github.com/ZenixX-dev/zakuro-android
- **README:** https://github.com/ZenixX-dev/zakuro-android/blob/main/README.md
- **Type:** Experimental project documentation
- **Supports:**
  - AArch64 Linux compilation of Zakuro and 3dsrecomp on Android;
  - Termux/PRoot/X11/VirGL proof of concept;
  - explicit statement that native Android/Bionic is not yet provided.
- **Limitations:** Not an APK or production Android architecture.

## R20 — Pocket Native

- **Project:** whovian64/pocket-native
- **URL:** https://github.com/whovian64/pocket-native
- **README:** https://github.com/whovian64/pocket-native/blob/main/README.md
- **Type:** Primary project documentation
- **Supports:**
  - off-device recompilation and deployment to ARM Linux handheld;
  - Zakuro/3dsrecomp integration;
  - OpenGL ES 3.1 Mali renderer;
  - KMS/evdev/ALSA frontend;
  - per-title profiles and one-command local build.
- **Limitations:** Narrow tested title set; not Android; upstream Vulkan path omitted.

## R21 — Nebby

- **Project:** gradenGnostic/Nebby
- **URL:** https://github.com/gradenGnostic/Nebby
- **README:** https://github.com/gradenGnostic/Nebby/blob/main/README.md
- **Type:** Experimental project documentation
- **Supports:**
  - cross-platform launcher/recompiler/mod manager;
  - 3dsrecomp and Zakuro integration;
  - reported native Pokémon Moon runtime;
  - ARM64/Android work in progress;
  - per-title profile and mod architecture.
- **Limitations:** Highly experimental; Android gameplay not confirmed in the observed documentation.

## R22 — TriAevum / Echoes of Time

- **Project:** coccofresco/TriAevum
- **URL:** https://github.com/coccofresco/TriAevum
- **README:** https://github.com/coccofresco/TriAevum/blob/main/README.md
- **Type:** Experimental game-specific project documentation
- **Supports:**
  - AOT native Ocarina of Time 3D project;
  - modern Vulkan/NRI renderer;
  - Forge preparation flow;
  - shader preparation and later caching;
  - enhancement potential of title-specific work.
- **Limitations:** Alpha, limited testing, and withdrawn broken releases noted by project.

---

# Android platform sources

## R23 — Android NDK ABI documentation

- **Publisher:** Android Developers
- **URL:** https://developer.android.com/ndk/guides/abis
- **Type:** Official platform documentation
- **Supports:**
  - `arm64-v8a` / AArch64 target;
  - APK native library path `/lib/<abi>/lib<name>.so`;
  - package manager expectations;
  - alternative copy/`dlopen()` behavior when libraries are not packaged conventionally.

## R24 — Android CMake/NDK configuration

- **Publisher:** Android Developers
- **URL:** https://developer.android.com/studio/projects/configure-cmake
- **Type:** Official platform documentation
- **Supports:**
  - Android NDK toolchain file;
  - `ANDROID_ABI`, platform/API, Ninja, and cross-compilation configuration;
  - building native `.so` outputs.

## R25 — Google Play executable-code policy

- **Publisher:** Google Play Console Help
- **URL:** https://support.google.com/googleplay/android-developer/answer/16559646
- **Type:** Official policy documentation
- **Supports:** Google Play apps may not download executable code such as `.so`, dex, or JAR files from outside Google Play; interpreter/VM exceptions are described separately.
- **Implication:** A Play-distributed universal launcher that downloads per-title native libraries is not the recommended v1 design.

## R26 — Android dynamic feature delivery

- **Publisher:** Android Developers
- **URL:** https://developer.android.com/guide/playcore/feature-delivery/on-demand
- **Type:** Official platform documentation
- **Use:** Future research for Play-delivered modules; not a solution for locally generated title-derived code without further legal/policy analysis.

---

# Analogous static recompilation projects

## R27 — N64: Recompiled

- **Project:** N64Recomp/N64Recomp
- **URL:** https://github.com/N64Recomp/N64Recomp
- **README:** https://github.com/N64Recomp/N64Recomp/blob/main/README.md
- **Type:** Primary project documentation/source
- **Supports:**
  - N64 MIPS binary to C static recompilation;
  - literal instruction semantics;
  - host runtime separation;
  - overlays, relocations, jump tables;
  - patch workflow;
  - portable host compilation.

## R28 — Zelda 64: Recompiled

- **Project:** Zelda64Recomp/Zelda64Recomp
- **URL:** https://github.com/Zelda64Recomp/Zelda64Recomp
- **README:** https://github.com/Zelda64Recomp/Zelda64Recomp/blob/dev/README.md
- **Type:** Primary project documentation
- **Supports:**
  - polished static-recompilation game port;
  - ARM64 support;
  - mod/enhancement/runtime separation;
  - user-owned ROM input model.
- **Contribution constraint:** README/CONTRIBUTING states a no-generative-AI contribution policy. Do not submit Codex-generated changes to this upstream project.

## R29 — XenonRecomp / Rayman Origins Recompiled

- **Project:** XDanfr/RaymanOriginsRecomp
- **URL:** https://github.com/XDanfr/RaymanOriginsRecomp
- **README:** https://github.com/XDanfr/RaymanOriginsRecomp/blob/main/README.md
- **Type:** Primary project documentation
- **Supports:**
  - Xbox 360 PowerPC static recompilation to native code;
  - native ARM64 Android build;
  - NDK/Vulkan packaging;
  - touch/controller support;
  - local-only title-derived code/assets;
  - custom native renderer and shader conversion ahead of time.
- **Importance:** Strong analogous proof for an off-device AOT-to-Android workflow.

---

# Graphics translation and shader-stutter references

## R30 — Dolphin performance guide: hybrid/exclusive ubershaders

- **Publisher:** Dolphin Emulator project
- **URL:** https://dolphin-emu.org/docs/guides/performance-guide/
- **Type:** Project technical/user documentation
- **Supports:**
  - specialized shader first-use stutter;
  - hybrid ubershader fallback while specialization compiles in background;
  - exclusive ubershader tradeoffs;
  - compile cached shaders before start;
  - skip-drawing compromise.
- **Use:** Established design validation for the Zakuro dynamic/specialized PICA path.

## R31 — AnyPS5 README

- **Project:** boykopovar/AnyPS5
- **URL:** https://github.com/boykopovar/AnyPS5
- **README:** https://github.com/boykopovar/AnyPS5/blob/main/README.md
- **Type:** Primary project documentation
- **Supports:**
  - executable transformation/relinking;
  - system library reimplementation;
  - shader recompilation to SPIR-V;
  - distinction between native CPU process and translated graphics.

## R32 — AnyPS5 architecture documentation

- **URL:** https://github.com/boykopovar/AnyPS5/blob/main/docs/dev/ARCHITECTURE.md
- **Type:** Primary technical architecture document
- **Supports:**
  - PM4/state decoding;
  - shader IR and SPIR-V translation;
  - shader disk cache;
  - prebuilt packs;
  - pipeline journal;
  - background pipeline replay/preparation;
  - device fingerprinting;
  - graphics pipeline library approach.
- **Use:** Primary design reference for portable recipe journals and prewarm.

---

# Related translation/HLE systems

## R33 — Vita3K

- **Project:** Vita3K/Vita3K
- **URL:** https://github.com/Vita3K/Vita3K
- **README:** https://github.com/Vita3K/Vita3K/blob/master/README.md
- **Type:** Primary project documentation
- **Supports:**
  - desktop/Android Vita emulation;
  - system HLE and shader translation context;
  - Android driver considerations.

## R34 — vita2hos

- **Project:** xerpi/vita2hos
- **URL:** https://github.com/xerpi/vita2hos
- **README:** https://github.com/xerpi/vita2hos/blob/master/README.md
- **Type:** Primary project documentation
- **Supports:**
  - native ARMv7 Vita execution on ARMv8/AArch32 Switch;
  - module-import redirection to native Horizon OS services;
  - reuse of Vita3K’s shader recompiler;
  - translation-layer versus emulator distinction.

## R35 — shadPS4

- **Project:** shadps4-emu/shadPS4
- **URL:** https://github.com/shadps4-emu/shadPS4
- **README:** https://github.com/shadps4-emu/shadPS4/blob/main/README.md
- **Type:** Primary project documentation/source
- **Supports:**
  - same-ISA/native PS4 executable execution concepts;
  - HLE system libraries;
  - modern GPU shader translation;
  - title-specific compatibility reality.

## R36 — FEX-Emu

- **Project:** FEX-Emu/FEX
- **URL:** https://github.com/FEX-Emu/FEX
- **README:** https://github.com/FEX-Emu/FEX/blob/main/Readme.md
- **Type:** Primary project documentation
- **Supports:**
  - x86/x86-64 execution on ARM64 Linux;
  - Wine/Proton use;
  - forwarding OpenGL/Vulkan calls to native libraries;
  - experimental code cache to reduce stutter;
  - per-app performance settings.

---

# Additional technical references to consult during implementation

## R37 — Vulkan specification and pipeline cache

- **Publisher:** Khronos Group
- **Vulkan specification:** https://registry.khronos.org/vulkan/specs/1.3-extensions/html/
- **Type:** Official API specification
- **Use:** Pipeline cache validity, UUID/fingerprint rules, synchronization, pipeline creation, specialization constants, and optional graphics pipeline library extensions.

## R38 — Khronos SPIR-V specification

- **Publisher:** Khronos Group
- **URL:** https://registry.khronos.org/SPIR-V/
- **Type:** Official IR specification
- **Use:** Validating any portable translated-shader cache and target-environment/version behavior.

## R39 — Android native app lifecycle and `ANativeWindow`

- **Publisher:** Android Developers / NDK reference
- **Native app glue:** https://developer.android.com/ndk/reference/group/native-activity
- **ANativeWindow:** https://developer.android.com/ndk/reference/group/a-native-window
- **Type:** Official platform documentation
- **Use:** Surface/lifecycle integration.

## R40 — AAudio / Oboe

- **AAudio:** https://developer.android.com/ndk/guides/audio/aaudio/aaudio
- **Oboe:** https://github.com/google/oboe
- **Type:** Official Android documentation and Google open-source library
- **Use:** Low-latency Android audio backend.

## R41 — Android Storage Access Framework

- **Publisher:** Android Developers
- **URL:** https://developer.android.com/guide/topics/providers/document-provider
- **Type:** Official platform documentation
- **Use:** User-selected title data without broad storage permissions.

---

## 2. Recommended initial upstream pins

These pins reflect the observed research state and are intended for the first reproducibility experiment, not permanent release policy.

```toml
[upstream]
3dsrecomp = "c3f21f94ba50d688025febc8974ff348d471b587"
zakuro = "412900a5a020301da15c1cc382585e05a489a535"

[observed]
zakuro_version = "0.2.27"
research_date = "2026-10-17"
```

Before using these pins, verify that both commits remain fetchable and that their dependency graph can be built reproducibly.

---

## 3. Claims requiring local confirmation before coding decisions

The following must be measured or inspected in a checked-out source tree rather than assumed from summaries:

1. Exact `recomp-abi` version and binary layout at the pinned commits.
2. Whether Zakuro’s pipeline-cache file includes sufficient device/driver fingerprinting and atomic writes.
3. Which Zakuro crates depend on desktop-only window, input, or audio libraries.
4. Whether all generated C is freestanding enough for Android/Bionic without code changes.
5. How current compiler discovery accepts cross-compilers, sysroots, response files, and Android linker flags.
6. Whether the generic PICA path covers every pipeline family or only common fragment-state combinations.
7. Whether background compilation can ever fall back to a synchronous path in current source.
8. What state key is used for pipeline specialization and whether it is complete.
9. Exact filesystem/system-data requirements for selected private reference titles.
10. Android device behavior with proprietary Qualcomm drivers versus Turnip.
11. Runtime and generated-library symbol visibility and loader assumptions.
12. License of every transitive dependency included in the Android binary.

---

## 4. Source-use rules for Codex

When a Codex task uses these references, it should:

1. cite the exact file and commit it inspected;
2. avoid copying code across incompatible licenses;
3. preserve attribution and notices;
4. avoid submitting generated work to upstream projects with no-AI contribution policies;
5. never add game-derived artifacts to the repository;
6. prefer an upstream patch when the change is generally useful;
7. describe any behavior inferred from code rather than documented explicitly; and
8. add a test before changing guest semantics.
