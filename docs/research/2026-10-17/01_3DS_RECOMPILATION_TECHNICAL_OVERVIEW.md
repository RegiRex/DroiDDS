# Technical Overview: A Native 3DS Recompilation Runtime for Android and ARM Linux

**Document version:** 0.1  
**Prepared:** 2026-10-17  
**Audience:** emulator developers, systems programmers, graphics/runtime engineers, and coding agents  
**Companion documents:** formal SPEC, prior-art matrix, references, Codex prompts, implementation backlog

---

## 1. Executive conclusion

A general Nintendo 3DS “recompilation-emulator” is technically feasible, and much of it already exists.

The most practical system is not a pure native port and not a conventional emulator. It is a hybrid:

```text
User-owned 3DS executable code
        │
        ├── ahead-of-time analysis and recompilation
        │       ARM/Thumb/VFP → portable C → native host code
        │
        ├── interpreter fallback for code not safely recompiled
        │
        └── 3DS HLE runtime
                kernel, services, memory, files, saves, DSP/audio,
                input, timing, CRO loading, PICA200 graphics
```

On Android ARM64, the desired runtime looks like this:

```text
Locally generated title library: libtitle.so (AArch64)
                    │
                    ▼
          3DS host ABI / recomp loader
                    │
          ┌─────────┴───────────┐
          │                     │
          ▼                     ▼
 native recompiled code   ARM11 interpreter fallback
          │                     │
          └─────────┬───────────┘
                    ▼
          3DS HLE kernel/services
                    │
       ┌────────────┼─────────────┐
       ▼            ▼             ▼
 filesystem       DSP/audio      PICA200 runtime
                                     │
                  ┌──────────────────┴──────────────────┐
                  ▼                                     ▼
      generic dynamic Vulkan path          specialized Vulkan pipelines
       available immediately                compiled asynchronously
                  │                                     │
                  └──────────────────┬──────────────────┘
                                     ▼
                              Android Vulkan GPU
```

The central repositories already provide the core of that design:

- **`3dsrecomp`** provides static code discovery, ARM/Thumb/VFP-to-C generation, native shared libraries, CRO support, a host ABI, interpreter fallback, modification detection, overrides, and differential verification.
- **Zakuro** is a Rust HLE 3DS runtime that consumes those libraries.
- Zakuro’s current Vulkan renderer already uses a dynamic generic fragment path while specialized pipelines compile in the background, and keeps a disk-backed Vulkan pipeline cache.

Therefore, the project’s main work is:

1. pin and stabilize the upstream combination;
2. build a desktop golden-reference harness;
3. cross-compile title libraries with the Android NDK;
4. create a native Android frontend and lifecycle layer;
5. package locally generated title code safely;
6. harden pipeline prewarming/cache behavior on Android drivers;
7. automate differential, regression, and device testing; and
8. improve compatibility without removing correctness fallbacks.

---

## 2. What is being proposed?

The phrase “3DS recompilation-emulator” combines two normally separate techniques.

### 2.1 Static recompilation

Static recompilation converts machine code from the original system into code that can be built for a host system before the game begins.

For this concept:

```text
3DS ARM11 instructions
      ARM / Thumb / VFP
              ↓
        static analysis
              ↓
        generated C code
              ↓
      Clang/GCC/NDK compiler
              ↓
 native x86-64 or AArch64 library
```

This removes most per-instruction runtime translation. It does **not** automatically recreate the 3DS operating system, GPU, audio DSP, filesystem, timers, synchronization semantics, or services.

### 2.2 High-level emulation / compatibility runtime

The runtime supplies the environment the recompiled program expects:

- virtual address space and guest memory;
- threads and scheduler behavior;
- SVC handling;
- synchronization objects;
- handles and IPC;
- filesystem archives and savedata;
- title updates, DLC, and mod paths;
- HID, touch, motion, camera, microphone, networking, and system services;
- DSP/audio behavior;
- PICA200 command processing and rendering; and
- console timing and lifecycle behavior.

This is why the final product is still an emulator in the broad sense even though much of the CPU code is native.

### 2.3 Interpreter fallback

Static analysis can never safely assume it has discovered every possible code path in every title. Problems include:

- indirect calls;
- jump tables;
- dynamically loaded CRO modules;
- unusual or unsupported instructions;
- code modified by patches or mods;
- executable data the analyzer failed to classify;
- runtime-generated or relocated code; and
- ambiguous control-flow targets.

A robust general solution must preserve a fallback interpreter. This converts static recompilation from an all-or-nothing porting method into an optimization layer over a correct runtime.

The ideal behavior is:

```text
known, validated entry → native function
unknown/stale entry     → interpreter
unsupported instruction → interpreter callback
SVC                      → host HLE exit
```

This is already the basic model of `3dsrecomp` and Zakuro.

---

## 3. How this differs from other approaches

### 3.1 Conventional emulator

A conventional emulator usually performs CPU interpretation or JIT/dynamic recompilation while the title runs.

```text
Guest instruction stream → JIT blocks → host instructions
```

Advantages:

- general across titles;
- reacts naturally to dynamically discovered code;
- easy to invalidate/recompile modified blocks;
- no separate per-title build step.

Costs:

- runtime code discovery and compilation;
- JIT restrictions on some platforms;
- code-cache management;
- possible first-use pauses;
- persistent complexity in hot execution paths.

### 3.2 Game-specific native port

A game-specific static recompilation project can replace large portions of the guest platform with hand-written native systems.

Advantages:

- highest optimization potential;
- easy to add widescreen, high frame rate, new renderer, mods, and native UI;
- no need to preserve every console quirk for unrelated titles.

Costs:

- substantial per-game engineering;
- version/region sensitivity;
- no general compatibility;
- title-derived output cannot be distributed freely.

### 3.3 General static-recompilation runtime

The proposed system sits between those two:

| Attribute | Conventional emulator | General recomp runtime | Game-specific port |
|---|---|---|---|
| Per-title build | No | Yes | Yes |
| General runtime | Yes | Yes | Often partly |
| Interpreter/JIT fallback | Yes | Yes | Often limited |
| Native CPU execution | JIT-generated | AOT-generated | AOT-generated |
| Per-game manual work | Low–medium | Low–medium | High |
| Compatibility ceiling | Broad | Broad if fallback is preserved | One/few titles |
| Mod/enhancement potential | Medium | High | Very high |

---

## 4. Why the 3DS is a particularly suitable target

### 4.1 Guest CPU is relatively tractable

The 3DS application CPU environment is based around 32-bit ARM11-class execution with ARM, Thumb, and VFP behavior. Modern Android handhelds are typically AArch64-only or increasingly optimized around AArch64.

A naïve statement that “both are ARM, so the guest code should run directly” is incomplete:

- ARMv6K/ARM11 code is 32-bit AArch32 code;
- many modern Android devices and Android builds do not provide a general 32-bit process environment;
- guest memory addresses, page tables, exception behavior, services, and kernel assumptions differ;
- the 3DS ABI and Android ABI are unrelated;
- direct calls into Android libraries cannot replace 3DS services; and
- floating-point and edge-case instruction semantics must match the guest.

AOT conversion to C gives a portable bridge. The generated program expresses the guest semantics using a stable context and memory ABI, then a normal compiler produces AArch64.

### 4.2 Guest CPU is much weaker than current Snapdragon CPUs

Modern Oryon-class and even older flagship mobile cores have enormous single-thread performance headroom over the 3DS CPU. That headroom can absorb:

- HLE service dispatch;
- memory checks;
- scheduler bookkeeping;
- interpreter fallback;
- synchronization translation;
- command-list processing;
- shader-state normalization; and
- debugging/validation overhead.

The main value of AOT is therefore not merely “make the 3DS CPU fast enough.” Conventional 3DS emulators already run on many devices. The higher-value goals are:

- deterministic native execution;
- lower CPU overhead on weaker ARM handhelds;
- reduced JIT dependence;
- simpler per-title patching;
- precise code-origin validation;
- easier static inspection and profiling;
- native package creation; and
- a foundation for more aggressive game-specific enhancements.

### 4.3 PICA200 is complex enough to matter but bounded enough for a generic path

PICA200 graphics are not equivalent to a modern PC shader model. The guest uses:

- programmable vertex programs;
- geometry-related behavior;
- command lists and register state;
- a configurable fragment pipeline;
- six texture-environment/combiner stages;
- texture units and tiled formats;
- fragment lighting;
- fog;
- procedural textures;
- alpha/depth/stencil tests;
- blending, logic operations, and write masks; and
- display transfers and framebuffer behavior.

A host renderer typically maps guest state to host shaders and pipelines. The combinatorial state space creates the potential for first-use pipeline compilation stutter—but the bounded, register-driven nature of the fragment pipeline also makes a universal dynamic implementation practical.

---

## 5. What `3dsrecomp` already accomplishes

The current `3dsrecomp` design is substantially more general than a simple one-title converter.

### 5.1 Code discovery

The tool scans the title executable and CRO modules and discovers functions/entry points through multiple evidence sources, including:

- executable entry points;
- direct calls and branch targets;
- exports;
- relocations;
- imports;
- pointers and known references;
- heuristics for likely function starts; and
- manual hints/overrides when static analysis is insufficient.

This is important because one of the largest static-recompilation failure modes is an unresolved indirect target. A general runtime cannot require perfect discovery; it must combine analysis with fallback execution.

### 5.2 ARM, Thumb, and VFP code generation

The generator emits C representing guest instruction semantics. The host compiler performs the final optimization and code generation for x86-64, AArch64, or another supported target.

The compiler configuration must preserve guest behavior. A notable requirement in the upstream interface documentation is disabling floating-point contraction (`-ffp-contract=off`) so a host compiler does not silently fuse operations and change rounding relative to guest execution.

### 5.3 Shared-library ABI

The generated output is designed as a shared library consumed by a host runtime rather than being permanently tied to one executable frontend.

The ABI includes concepts such as:

- an ABI version;
- generation/version information;
- entry tables;
- module information;
- origin/hash information;
- guest CPU context;
- page tables and memory callbacks;
- code-address lookup;
- fallback instruction interpretation; and
- exit reasons such as SVC, budget exhaustion, or unwind.

This is exactly the separation needed for an Android runtime. The recompiler does not need to know Android UI behavior, and the Android frontend does not need to know individual guest instructions.

### 5.4 Entry-table and CRO handling

The library can expose entry points for the executable and position-independent CRO modules. The runtime supplies each loaded module’s base address and resolves entries relative to that base.

This allows a title to retain dynamic module loading while still executing most module code from native output.

### 5.5 Origin validation and modification safety

The ABI includes origin information that allows the runtime to determine whether guest code still matches what was recompiled. If a patch or mod changes code, affected native functions can be treated as stale and the runtime can fall back to interpretation instead of executing native code generated for different bytes.

This is one of the strongest architectural features for a general system because it avoids the unsafe assumption that the imported title never changes.

### 5.6 Differential verification

`3dsrecomp` can compare recompiled function behavior against Zakuro’s interpreter, including register, flag, and memory effects. This gives the project a direct correctness oracle.

A Codex-driven implementation should expand this rather than replacing it. Every optimization should preserve a differential path.

### 5.7 Hand-written overrides

The project supports replacing selected guest functions with hand-written C. This enables:

- correctness fixes;
- performance hotspots;
- game-specific enhancements;
- instrumentation;
- mod hooks; and
- replacement of functions that static translation cannot safely handle.

Overrides should remain opt-in, version-locked, testable, and separate from generic runtime behavior.

---

## 6. What Zakuro already accomplishes

Zakuro is the critical evidence that the general architecture works.

### 6.1 HLE runtime

Zakuro provides a Rust implementation of major 3DS runtime responsibilities, including code for:

- memory mapping;
- kernel objects and scheduling;
- IPC and services;
- filesystem and archives;
- CRO loading;
- input and system behavior;
- audio/DSP paths;
- PICA200 register and command behavior;
- software and hardware graphics paths;
- title updates/mod-related paths; and
- recompiled-code loading.

Its compatibility list includes a broad range of commercial titles, which means the architecture is not confined to one handcrafted game.

### 6.2 Recompiled CPU integration

Zakuro can launch with interpreter execution and use a `3dsrecomp` library when available. Upstream describes recompilation as a major performance improvement while preserving the interpreter.

This is already the proposed hybrid CPU model.

### 6.3 Vulkan PICA renderer

The hardware renderer keeps guest surfaces resident on the host GPU when possible, tracks synchronization between guest memory and host images, stages draw data, and uses multiple in-flight batches to reduce CPU/GPU waiting.

It translates guest rendering state into Vulkan operations rather than rendering the entire PICA pipeline on the CPU.

### 6.4 Generic dynamic pipeline plus async specialization

The most important discovery for this concept is that Zakuro’s current fragment shader and renderer implement a hybrid-ubershader model.

The fragment shader has:

- specialization constants describing PICA TEV stages and other state;
- specialized variants in which the driver can compile away unused branches and stages; and
- a `DYNAMIC` path that reads the state from draw uniforms instead.

The source comments explicitly describe the dynamic path as a generic pipeline used to draw while the pipeline for the exact combination compiles. The renderer logs specialized pipeline compilation continuing while drawing proceeds.

This means the proposed no-stall model is not an unimplemented theory. It exists in current Zakuro source.

### 6.5 Disk-backed Vulkan pipeline cache

Zakuro’s renderer retains a Vulkan `PipelineCache` and writes previously compiled pipeline data to disk. A previously encountered combination can therefore avoid repeating the same driver compilation work on a compatible device/driver.

The project should still add a portable recipe journal because Vulkan’s opaque cache blob is device/driver-specific. But the low-level driver-cache tier already exists.

---

## 7. Why CPU AOT does not by itself eliminate shader stutter

CPU code and GPU programs are separate domains.

A title can execute entirely from a native AArch64 library and still encounter a guest graphics state that requires a new host pipeline.

A simplified flow is:

```text
native title logic
      ↓
writes PICA registers and command lists
      ↓
PICA command decoder
      ↓
normalized draw state
      ↓
find compatible host pipeline
      ↓
compile/link if missing
```

If the emulator blocks the render or emulation thread during the final step, the user sees a pause.

This is why a true “recompilation” solution must address two independent forms of translation:

1. **CPU translation:** guest instructions to host code.
2. **GPU translation:** guest shader/state behavior to host shader/pipeline behavior.

The correct GPU solution is not “precompile every theoretically possible state.” The state space can be too large, and some combinations are created dynamically. The robust solution is:

```text
pipeline requested
      │
      ├── specialized pipeline ready → use it
      │
      ├── specialized pipeline compiling → use generic pipeline
      │
      └── first encounter
              ├── enqueue specialization
              └── use generic pipeline immediately
```

Zakuro already follows this model for key PICA fragment behavior.

---

## 8. Shader/pipeline strategy for a polished product

### 8.1 Tier 0: embedded universal pipelines

At application startup, before gameplay begins, create or verify a minimal set of generic pipelines that can represent the full supported guest feature set.

These pipelines must not depend on per-game shader discovery. They are part of the runtime.

A generic path may be slower because it contains dynamic branches, lookup logic, and unused feature paths, but it must be correct enough to render every supported state without waiting.

### 8.2 Tier 1: in-memory specialized pipeline map

Normalize guest state into a stable key such as:

```text
PicaPipelineKey
  vertex-program hash
  geometry mode/program hash
  varying/semantic layout
  TEV sources/operands/functions/scales
  TEV buffer update state
  texture unit formats and sampling modes
  lighting mode and lookup usage
  procedural-texture mode
  fog mode
  alpha/depth/stencil modes
  blend/logic/write mask
  render-target formats
  depth mapping mode
  compatibility flags
```

The exact key must include every state bit that changes shader or fixed-function behavior, and exclude values that can safely remain dynamic uniforms.

### 8.3 Tier 2: portable guest-state journal

Persist normalized keys and guest shader hashes in a portable journal. This is not executable code and not an opaque driver cache. It is a list of recipes encountered for one title/revision/runtime version.

At the next launch, the runtime can:

- prioritize likely pipelines;
- rebuild specializations on background threads;
- report progress;
- avoid blocking gameplay; and
- invalidate only recipes affected by runtime changes.

### 8.4 Tier 3: portable translated shader cache

Where technically and legally appropriate, persist host-independent or host-API representations such as validated SPIR-V generated from guest shader programs.

Cache keys must include:

- title/revision hash;
- guest shader/state hash;
- translator version;
- runtime feature flags;
- SPIR-V target environment;
- known correctness workaround set; and
- schema version.

### 8.5 Tier 4: Vulkan driver pipeline cache

Store opaque `VkPipelineCache` data under a device fingerprint:

- vendor ID;
- device ID;
- driver ID/version;
- pipeline-cache UUID;
- runtime build ID; and
- relevant enabled extensions/features.

Never share or reuse this blob across incompatible fingerprints.

### 8.6 Optional graphics-pipeline libraries

On devices with suitable Vulkan extensions, split pipelines into reusable pieces and link them. This can reduce compile cost and duplication. The design must retain a conventional pipeline path because Android driver support varies.

### 8.7 Correct swap behavior

A specialized pipeline must replace the generic path only after:

- compilation succeeds;
- validation succeeds;
- descriptors/layouts match;
- it is safe to publish across threads; and
- the switch occurs at a command-recording or frame boundary that cannot invalidate in-flight work.

A failed specialized compile must not crash or black-screen the title; it should mark the key failed for that session, retain the generic path, and write a bounded diagnostic.

---

## 9. Can shaders be prepared ahead of time?

### 9.1 What can be found statically

The build process can scan the executable, CRO modules, and title data for known PICA shader programs and state objects. It can pretranslate many vertex/geometry programs and seed likely pipeline recipes.

### 9.2 What cannot be guaranteed statically

Titles can:

- upload shader words dynamically;
- construct command lists at runtime;
- choose states based on gameplay or save data;
- load modules or assets conditionally;
- modify registers incrementally;
- use code paths not reached by an offline scan; and
- combine individually known state values in previously unseen ways.

Therefore, ahead-of-time discovery is an optimization, not a correctness requirement.

### 9.3 Best combined model

```text
Build/install phase
  ├── discover known guest code
  ├── compile native CPU library
  ├── scan known PICA programs/states
  ├── validate/translate known guest shaders
  └── seed pipeline journal

Runtime
  ├── execute native CPU code
  ├── interpret uncovered/stale code
  ├── use prewarmed specialized pipelines when ready
  ├── use generic pipeline on every cache miss
  └── specialize/cache asynchronously
```

This architecture gives fast cold behavior without pretending static discovery is complete.

---

## 10. Native Android is possible, but packaging matters

### 10.1 Android native target

The Android NDK can produce `arm64-v8a` shared libraries. A generated title library can be compiled by the NDK Clang toolchain and linked into or packaged beside the runtime.

A first-class Android build should use Android/Bionic directly rather than relying on:

- PRoot Debian;
- X11;
- VirGL;
- desktop ALSA;
- desktop windowing; or
- a generic Linux root filesystem.

The PRoot effort is useful proof that the AArch64 code path works. It is not the desired product architecture.

### 10.2 Recommended first packaging model: one locally built title APK

A desktop builder should:

1. validate the user’s input;
2. run `3dsrecomp`;
3. compile the generated C with the Android NDK;
4. build the pinned runtime core for `arm64-v8a`;
5. package the title library under the standard APK native-library path;
6. generate a title/revision manifest;
7. sign the APK with a local development key; and
8. install through ADB or hand the APK to the user.

The APK should not need to contain all copyrighted game data. The first run can ask the user to select the original dump through Android’s Storage Access Framework, verify it, and read/extract runtime data into app-private storage.

Advantages:

- normal Android loader behavior;
- no arbitrary runtime native-code download;
- straightforward per-title isolation;
- exact title/revision binding;
- predictable crash symbols;
- easy uninstall/cleanup;
- independent save/config directories; and
- lower linker-namespace complexity.

### 10.3 Universal runtime plus title plugin APKs

A future design could use:

- one common runtime package; and
- separately installed, locally generated title packages containing native code and manifests.

This reduces duplication but introduces package-to-package code loading, signature coordination, version matching, and Android linker namespace concerns. It should not be the first milestone.

### 10.4 Runtime compilation on the handheld

Compiling hundreds of generated C units on an Android handheld is possible in principle but poor as a primary workflow:

- toolchain size;
- memory pressure;
- build time;
- heat and battery drain;
- complex error recovery;
- storage churn;
- executable-code policy concerns; and
- inconsistent OEM environments.

A desktop builder is more reliable. Later, an optional local-device builder could be explored for sideload-only users.

### 10.5 Google Play constraint

Google Play policy restricts apps from downloading executable code such as `.so` files from sources outside Play. A universal launcher that downloads generated native title modules is therefore a poor Play Store design.

The initial product should be explicitly sideload/local-build oriented. A Play-distributed version would likely need a different execution model, such as interpretation/JIT within policy bounds or Play-delivered modules, and would still face copyright/distribution complications.

---

## 11. Proposed Android host architecture

### 11.1 Managed shell

A small Kotlin/Java shell should handle:

- Activity lifecycle;
- permission-free Storage Access Framework document selection;
- persistent URI permissions;
- controller enumeration and key/motion events;
- touch overlay configuration;
- settings UI;
- notification/error presentation;
- crash-recovery UX;
- import progress; and
- safe sharing of logs.

### 11.2 Native runtime

The Rust/C++ native layer should own:

- emulation threads;
- `3dsrecomp` ABI loading;
- guest memory;
- HLE kernel/services;
- PICA processing;
- Vulkan objects;
- audio mixing;
- frame scheduling;
- save flushing;
- performance counters; and
- bounded diagnostic logs.

JNI should expose a narrow, versioned boundary rather than mirror every emulator class.

### 11.3 Rendering surface

Use `SurfaceView`/`ANativeWindow` with Vulkan. The runtime must handle:

- surface creation/destruction;
- Activity pause/resume;
- orientation/window resizing;
- display refresh changes;
- dual-screen layouts;
- foldable/dual-display arrangements where available;
- external displays; and
- recreation after Android destroys the surface without killing the process.

### 11.4 Audio

Use a low-latency Android audio path such as AAudio or Oboe, with:

- a bounded ring buffer;
- clock drift handling;
- underrun telemetry;
- pause/resume semantics;
- Bluetooth-latency awareness; and
- no emulator-thread blocking on audio I/O.

### 11.5 Input

Support:

- Android game controllers;
- built-in handheld controls exposed as Android input devices;
- touch screen;
- virtual touch cursor;
- motion sensors;
- keyboard/mouse where present; and
- per-device mapping profiles.

### 11.6 Thermal and power behavior

Mobile performance must be treated as a sustained workload. Expose profiles such as:

- Efficient;
- Balanced;
- Performance; and
- Device/default.

Avoid relying on vendor-specific APIs for correctness. Vendor APIs can be optional adapters. The core must function on stripped-down Android variants and generic AOSP-derived systems.

---

## 12. Three viable implementation strategies

## 12.1 Strategy A — Zakuro-first Android runtime (recommended)

### Method

- Fork/pin Zakuro and `3dsrecomp`.
- Add an Android frontend crate/module.
- Make the Zakuro runtime build against Android/Bionic.
- Cross-compile generated title libraries with NDK Clang.
- Package one locally generated per-title APK.
- Preserve all CPU/GPU fallbacks.

### Strengths

- closest to the desired architecture;
- both central projects are MIT-licensed;
- existing recompiler ABI;
- existing HLE runtime;
- existing broad compatibility;
- existing hybrid graphics fallback;
- clean Rust modularity;
- low conceptual duplication.

### Weaknesses

- Android UI, lifecycle, audio, and packaging are incomplete;
- Android GPU-driver testing is limited;
- compatibility and UX are younger than Azahar;
- the NDK cross-target path needs production hardening; and
- current releases focus on desktop x86-64.

### Recommendation

Use this for the main project.

## 12.2 Strategy B — Add AOT execution to Azahar

### Method

- Keep Azahar’s Android frontend, services, and graphics stack.
- Add a `3dsrecomp` library loader as an optional CPU backend.
- Bridge the upstream `recomp-abi` to Azahar’s memory, scheduler, SVC, and code lookup.
- Fall back to Dynarmic/interpreter when native entries are unavailable.

### Strengths

- mature Android app and user workflows;
- broad Citra-derived compatibility;
- existing Vulkan shader disk cache and worker infrastructure;
- established controller, layout, camera, microphone, save, update, and DLC paths.

### Weaknesses

- significant Rust/C++/ABI integration work;
- CPU state and scheduler interfaces may not map cleanly;
- license obligations are more restrictive;
- higher risk of maintaining a large downstream fork;
- potential duplication of Zakuro work; and
- harder to upstream if project goals diverge.

### Recommendation

Treat as a later integration experiment after the ABI is proven on Android.

## 12.3 Strategy C — Game-specific native ports

### Method

- Use `3dsrecomp port`, hand-written overrides, and a game-specific runtime/renderer.
- Build a dedicated Android application for one title.

### Strengths

- fastest route to exceptional performance and presentation for one game;
- easier full shader AOT and pipeline enumeration;
- easier widescreen/high-FPS/native UI mods;
- less need for generic compatibility.

### Weaknesses

- high per-title effort;
- no general 3DS library support;
- region/version sensitivity;
- game-specific reverse engineering; and
- derived code remains local-only.

### Recommendation

Use for a showcase or to validate Android AOT packaging, but not as the primary general solution.

---

## 13. Existing Android and ARM evidence

### 13.1 Zakuro on Android through PRoot

An experimental project has compiled `3dsrecomp` and Zakuro natively for AArch64 Linux inside Android using Termux, PRoot Debian, X11, and VirGL. This demonstrates that the codebase can compile and open its graphical frontend on an ARM Android device.

It does **not** demonstrate a production Android APK, direct Turnip/Vulkan use, long gameplay stability, native input, or Android lifecycle handling.

### 13.2 Pocket Native

Pocket Native forks Zakuro and `3dsrecomp` for inexpensive ARM Linux handhelds. It adds:

- an OpenGL ES 3.1 renderer for Mali hardware;
- KMS display output;
- evdev input;
- ALSA audio;
- per-game profiles;
- a device UI; and
- a PC-side one-command build that creates a portable per-title package.

This is strong evidence for the off-device-build/device-runtime split proposed here.

### 13.3 Nebby and TriAevum

These experimental projects demonstrate game-specific/native-runtime directions, including native Vulkan rendering, mod management, launcher workflows, and ARM64/Android aspirations. They are useful references but should not be treated as mature general infrastructure.

### 13.4 Rayman Origins Recompiled on Android

An Xbox 360 static-recompilation project now reports native ARM64 game code, Android NDK/Vulkan packaging, touch/controller input, and gameplay on multiple Android devices. Its guest architecture and runtime are different, but it is valuable proof that locally derived AOT game code plus a native Android compatibility runtime is a viable delivery pattern.

---

## 14. Main technical risks

### 14.1 Static discovery gaps

Risk: a title reaches a valid code target not present in the native entry table.

Mitigation:

- interpreter fallback;
- code-address lookup instrumentation;
- trace-driven discovery;
- jump-table and pointer analysis;
- per-title hints;
- no-crash unknown-entry behavior; and
- differential validation.

### 14.2 Guest/host floating-point differences

Risk: compiler transformations alter rounding, exceptions, NaN behavior, or fused operations.

Mitigation:

- required compiler flags;
- explicit helper functions for edge cases;
- differential tests;
- avoid fast-math;
- architecture-specific conformance suite; and
- title-specific override only as a last resort.

### 14.3 Dynamic code or modifications

Risk: native output no longer matches guest bytes.

Mitigation:

- origin hashes;
- per-function invalidation;
- interpreter fallback;
- strict title/revision manifest;
- mod-aware rebuild option; and
- never execute stale generated code.

### 14.4 Android linker and packaging

Risk: generated libraries cannot be loaded reliably across Android versions/OEMs.

Mitigation:

- package libraries under the standard APK ABI path;
- one per-title APK for v1;
- avoid arbitrary external `.so` loading;
- target a clear minimum Android API;
- use NDK stable APIs; and
- test on stock and stripped-down Android variants.

### 14.5 Vulkan driver variability

Risk: Turnip, Qualcomm proprietary drivers, Mali, and other drivers compile or execute pipelines differently.

Mitigation:

- generic fallback;
- optional driver selection where supported;
- robust feature probing;
- no dependence on optional extensions for correctness;
- device-fingerprinted caches;
- GPU conformance captures; and
- automatic safe-mode fallback.

### 14.6 Pipeline-key incompleteness

Risk: two materially different guest states map to the same key, causing incorrect graphics.

Mitigation:

- canonical key unit tests;
- dynamic vs specialized image comparison;
- register-diff diagnostics;
- hash all behaviorally relevant state;
- version the key schema; and
- treat generic path as the correctness oracle.

### 14.7 Threading and timing

Risk: native execution changes timing enough to expose race conditions or service bugs.

Mitigation:

- deterministic scheduler modes;
- instruction/cycle budgets;
- trace/replay;
- runtime pacing separate from host wall clock;
- synchronization-object tests; and
- compare interpreter and native modes.

### 14.8 Scope expansion

Risk: the project attempts Android UI, new emulator core, new renderer, compatibility, enhancements, and per-game ports simultaneously.

Mitigation:

- pin upstream;
- preserve existing paths;
- desktop golden harness first;
- one vertical-slice title;
- one milestone at a time; and
- no renderer rewrite until metrics show a concrete need.

---

## 15. What performance improvements should be expected?

### 15.1 CPU

For titles with high native coverage, AOT should reduce CPU translation overhead and may improve efficiency on lower-end ARM devices. The exact gain depends on:

- prior interpreter/JIT performance;
- memory-access model;
- host compiler quality;
- service overhead;
- scheduler behavior;
- fallback frequency; and
- title CPU intensity.

AOT should not be marketed as an automatic large FPS increase for GPU-bound games.

### 15.2 Frame pacing

The stronger benefit may be consistency:

- no CPU JIT block compilation;
- no executable-memory/JIT permission path;
- generic GPU fallback on first-use states;
- asynchronous specialization;
- persistent caches; and
- prewarming from prior state journals.

### 15.3 Cold versus warm play

The target should be:

- **cold run:** correct rendering through generic pipelines; no intentional shader compile stall;
- **warm run:** more specialized pipelines ready earlier; lower generic-path GPU cost;
- **subsequent runtime version:** portable recipes rebuild safely; opaque driver caches invalidate if fingerprints differ.

### 15.4 Power

AOT may reduce CPU power, but total device power depends on the host GPU path. A generic fragment pipeline can be more expensive than a specialized one, so background specialization remains important even if it eliminates stutter.

---

## 16. Why a generic fallback is preferable to “skip drawing”

Some emulators avoid shader compilation stalls by temporarily not drawing an object. That preserves simulation speed but produces missing graphics and can break effects that depend on framebuffer copies or precise draw timing.

A generic PICA pipeline is preferable because it attempts correct rendering immediately. It trades temporary GPU efficiency for visual continuity.

The hierarchy should be:

1. ready specialized pipeline;
2. correct generic pipeline;
3. software/reference renderer for debugging or unsupported features;
4. skip draw only as an explicit unsafe option, not default behavior.

---

## 17. Relationship to AnyPS5 and other compatibility layers

The AnyPS5 comparison is conceptually useful but not identical.

### AnyPS5-style model

A PS5 title already contains x86-64 code, so a host x86-64 environment can often relink/transform executable formats and reimplement imported system APIs without translating every CPU instruction to a different ISA.

Its graphics still require major translation:

```text
PS5 commands/shaders → decoded state/IR → SPIR-V → Vulkan
```

It uses shader caches, prebuilt packs, asynchronous preparation, and a pipeline journal.

### 3DS model

The 3DS guest CPU ISA is not the native Android AArch64 ABI. It needs AOT semantic translation or a runtime translator. The OS services and PICA graphics still require HLE/translation.

The shared lesson is architectural separation:

- transformed/native executable code;
- reimplemented guest system APIs;
- graphics command/shader translation;
- persistent portable recipes;
- device-specific pipeline caches; and
- background preparation without blocking first use.

---

## 18. What similar systems teach

### N64: Recompiled / Zelda 64: Recompiled

Lesson: literal guest-instruction-to-C generation plus a runtime can produce portable native builds and enable patches, enhancements, and ARM64 support. Runtime and generated title code should remain separate.

### Dolphin hybrid ubershaders

Lesson: use a generic shader immediately and compile optimized specialized shaders in the background. This is the closest established model to the desired PICA behavior and is already reflected in Zakuro.

### vita2hos

Lesson: when guest and host architectures are closely related, redirecting guest imports to native host services can remove much CPU emulation. Graphics translation remains necessary and can reuse a mature emulator’s shader compiler.

### Vita3K / shadPS4

Lesson: an API/HLE layer can run native-format executables while translating guest graphics and system libraries. Same-ISA or related-ISA CPU execution does not eliminate GPU/OS work.

### FEX

Lesson: forwarding graphics APIs to native host libraries and maintaining persistent code caches can make translated gaming practical on ARM. Per-application compatibility controls matter.

### Xbox 360 recompilation on Android

Lesson: a desktop/off-device AOT toolchain can generate native ARM64 code, package it with an Android runtime, and deliver good mobile performance—provided the runtime, renderer, input, and asset-import flow are deliberately designed for Android.

---

## 19. Recommended project boundaries

### In scope for v1

- Linux x86-64 reference host;
- Android ARM64 target;
- pinned `3dsrecomp` and Zakuro integration;
- per-title local build;
- interpreter fallback;
- existing Zakuro PICA generic/specialized renderer;
- Vulkan on Android;
- gamepad and touch;
- audio;
- saves;
- bounded logs;
- cold/warm pipeline metrics;
- one to three validated titles plus homebrew conformance tests.

### Explicitly out of scope for v1

- Play Store distribution;
- downloadable native title plugins;
- replacing Zakuro’s renderer wholesale;
- removing the interpreter;
- universal zero-configuration compatibility;
- online-service reimplementation;
- multiplayer guarantees;
- custom firmware distribution;
- automatic acquisition of keys or copyrighted data;
- every New 3DS hardware feature;
- broad visual enhancements; and
- publishing title-derived generated code.

---

## 20. Recommended first vertical slice

The first vertical slice should prove the entire architecture with minimal novelty:

1. Pin exact `3dsrecomp` and Zakuro commits.
2. Build both on Linux.
3. Run a known-compatible, legally dumped title in interpreter mode.
4. Generate and load the AOT library.
5. Measure native dynamic-instruction coverage.
6. Deliberately invalidate one function and prove interpreter fallback.
7. Record PICA pipeline misses.
8. Prove the generic dynamic pipeline renders those misses.
9. Prove specialized pipelines compile asynchronously.
10. Restart and prove pipeline-cache reuse.
11. Cross-compile the title library with Android NDK Clang.
12. Load it in a minimal Android native test app.
13. Add the full Zakuro runtime and present one frame.
14. Add input/audio/saves.
15. Compare desktop and Android deterministic checkpoints.

Anything beyond this should be postponed until the vertical slice is repeatable.

---

## 21. Final feasibility assessment

### Feasible now

- general AOT conversion of a substantial portion of 3DS title code;
- native shared-library execution;
- interpreter fallback;
- CRO integration;
- broad HLE runtime behavior;
- Vulkan PICA rendering;
- generic graphics fallback during async pipeline specialization;
- persistent driver pipeline caching;
- AArch64 Linux builds; and
- local Android NDK packaging in principle.

### Requires integration and hardening

- first-class Android/Bionic Zakuro build;
- production Android UI/lifecycle/input/audio;
- automated per-title APK generation;
- device-fingerprinted cache management;
- portable pipeline journal/prewarm;
- extensive Adreno/Turnip/Mali testing;
- compatibility regression farm;
- crash-safe logging;
- title/revision manifests; and
- user-friendly local builder.

### Longer-term research

- universal runtime plus plugin packages;
- Android-local compilation;
- integration with Azahar;
- offline PICA state extraction beyond observed traces;
- fully portable precompiled shader packs;
- Vulkan graphics-pipeline-library optimization;
- title-specific native renderers; and
- broad enhancement/mod SDK.

## Bottom line

The concept has moved beyond “could this exist?” The core CPU/runtime/rendering pattern exists in open source. The credible project is now:

> **Turn the current `3dsrecomp` + Zakuro technology into a reproducible, native Android ARM64 product, retain its correctness fallbacks, formalize the anti-stutter graphics pipeline, and build the tooling/testing needed for ordinary users to generate title-specific packages from their own dumps.**
