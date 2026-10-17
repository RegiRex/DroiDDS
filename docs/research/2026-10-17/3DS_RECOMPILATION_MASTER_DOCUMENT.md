# 3DS Native Recompilation Runtime — Complete Research, SPEC, and Codex Pack

**Prepared:** 2026-10-17  
**Primary target:** Native Android ARM64 handhelds, with Linux as the reference/debug host  
**Document type:** Combined convenience edition; the source pack also includes each part as a separate Markdown file.

## Contents

1. **Orientation and architecture decision** — `00_README.md`
2. **Technical overview** — `01_3DS_RECOMPILATION_TECHNICAL_OVERVIEW.md`
3. **Formal architecture SPEC** — `02_SPEC_3DS_NATIVE_RECOMP_RUNTIME.md`
4. **Existing projects and gap matrix** — `03_EXISTING_PROJECTS_AND_GAP_MATRIX.md`
5. **Annotated references** — `04_REFERENCES.md`
6. **Codex prompt pack** — `05_CODEX_PROMPT_PACK.md`
7. **Implementation backlog** — `06_IMPLEMENTATION_BACKLOG.md`
8. **Uberhar relationship and migration decision** — `07_UBERHAR_RELATIONSHIP_AND_MIGRATION.md`

---

# Part 1 — Orientation and architecture decision

> Source file: `00_README.md`

# 3DS Native Recompilation Runtime — Research and Codex Pack

**Prepared:** 2026-10-17  
**Status:** Research-backed architecture draft  
**Primary target:** Native Android ARM64 handhelds, with Linux desktop as the reference/debug host  
**Working product name:** **3DS Native Recompilation Runtime (3DS-NRR)**

## Purpose

This pack turns the 3DS static-recompilation concept into an implementation-oriented body of work suitable for use with Codex or another coding agent. It separates:

1. what is already implemented in existing projects;
2. what remains to be integrated or created;
3. the recommended architecture;
4. concrete requirements and acceptance tests;
5. source references and licensing constraints; and
6. staged prompts that keep an autonomous coding effort bounded and reviewable.

## Central conclusion

The proposed system should **not** be built from scratch.

As of October 2026, most of the difficult conceptual pieces already exist:

- **`3dsrecomp`** discovers Nintendo 3DS ARM/Thumb/VFP code, emits C, compiles it into a native shared library, handles CRO modules, exposes a host ABI, falls back to an interpreter for uncovered code, and includes differential verification.
- **Zakuro** supplies a general 3DS HLE runtime for kernel/services/filesystem/audio/GPU behavior and already consumes `3dsrecomp` output.
- Zakuro’s Vulkan renderer already implements the most important anti-stutter graphics design proposed in the earlier discussion: a **generic dynamic PICA fragment path renders immediately while a specialized pipeline compiles asynchronously**, then the specialized pipeline replaces it. It also keeps a Vulkan pipeline cache on disk.
- Experimental efforts already demonstrate AArch64/Linux operation on Android through PRoot, native-recompiled 3DS titles on low-end ARM Linux handhelds, and early Android-native packaging efforts.

The high-value project is therefore an **integration and productization effort**, not a new emulator core:

> Fork and pin `3dsrecomp` + Zakuro, establish a deterministic desktop reference harness, add a native Android frontend and Android-NDK cross-compilation path, package locally generated per-title native code safely, preserve the interpreter and generic-GPU fallbacks, and build a rigorous regression/performance system around them.

## Files in this pack

| File | Purpose |
|---|---|
| [`01_3DS_RECOMPILATION_TECHNICAL_OVERVIEW.md`](01_3DS_RECOMPILATION_TECHNICAL_OVERVIEW.md) | Explains the CPU, HLE, GPU, shader, Android, and packaging model; corrects common assumptions; compares architectural options. |
| [`02_SPEC_3DS_NATIVE_RECOMP_RUNTIME.md`](02_SPEC_3DS_NATIVE_RECOMP_RUNTIME.md) | Formal product and engineering specification with requirement IDs, architecture, interfaces, data models, test strategy, milestones, risks, and acceptance criteria. |
| [`03_EXISTING_PROJECTS_AND_GAP_MATRIX.md`](03_EXISTING_PROJECTS_AND_GAP_MATRIX.md) | Maps every major subsystem to existing 3DS projects and analogous work on other systems; identifies reusable code, missing pieces, and license constraints. |
| [`04_REFERENCES.md`](04_REFERENCES.md) | Annotated, source-mapped bibliography with repository pins, direct links, claim coverage, and confidence notes. |
| [`05_CODEX_PROMPT_PACK.md`](05_CODEX_PROMPT_PACK.md) | A master Codex prompt plus small, ordered implementation prompts designed to avoid an unreviewable “build everything” attempt. |
| [`06_IMPLEMENTATION_BACKLOG.md`](06_IMPLEMENTATION_BACKLOG.md) | Epics, tickets, dependencies, deliverables, and acceptance tests suitable for GitHub Issues or agent task queues. |
| [`07_UBERHAR_RELATIONSHIP_AND_MIGRATION.md`](07_UBERHAR_RELATIONSHIP_AND_MIGRATION.md) | Recommends how to keep the new Zakuro/3dsrecomp architecture separate from Uberhar while reusing its testing, logging, device, and release lessons. |

## Recommended development route

### Recommended: Zakuro-first general runtime

Use Zakuro as the HLE/GPU/audio/filesystem runtime and `3dsrecomp` as the AOT CPU producer. Add Android as a first-class host platform without replacing the working generic runtime.

This is the shortest route to a broad-title system because it preserves:

- the existing `recomp-abi` contract;
- interpreter fallback;
- CRO loading and relocation behavior;
- code-origin validation for modified titles;
- existing HLE services;
- PICA200 software and Vulkan paths;
- the dynamic fallback/specialization rendering design;
- persistent pipeline caching; and
- an existing compatibility base.

### Secondary option: integrate `3dsrecomp` as an Azahar CPU backend

Azahar has a mature Android frontend and broad Citra-derived compatibility. An optional `3dsrecomp` CPU backend could eventually combine that maturity with AOT execution. This is attractive but is a larger cross-language and architectural integration effort than Android-enabling Zakuro.

### Narrowest option: game-specific native ports

A game-specific port can deliver the best result fastest for one title, as demonstrated by N64 recompilation projects, TriAevum, Nebby, and Android Xbox 360 recompilation work. It does not satisfy the general-runtime goal and should be treated as a validation track, not the primary architecture.

## How to use this pack with Codex

1. Read the overview and SPEC first.
2. Give Codex the **reconnaissance prompt** from `05_CODEX_PROMPT_PACK.md`; do not begin with the master implementation prompt alone.
3. Require Codex to pin upstream commits and produce a repository map before editing code.
4. Execute one milestone prompt at a time.
5. Require every task to report:
   - files changed;
   - commands run;
   - tests passed/failed;
   - unresolved assumptions;
   - performance or correctness evidence; and
   - the smallest next task.
6. Keep generated game-derived code, ROM data, keys, firmware, and assets outside source control.

## First implementation objective

The first meaningful deliverable should be deliberately modest:

> On Linux desktop, launch one legally dumped, known-compatible 3DS title through pinned Zakuro + a pinned `3dsrecomp` library, prove that native code is being used, prove that interpreter fallback remains functional, collect a deterministic trace, and verify that the generic GPU fallback renders while specialized Vulkan pipelines compile without blocking the emulation thread.

Only after that reference path is reproducible should Android work begin.

## Android distribution decision

For the first release, use **locally built, sideloaded, per-title APKs** or a locally built runtime APK containing the title-specific `.so` under `lib/arm64-v8a/`.

This is preferred because:

- Android’s package manager has a well-defined path for native libraries packaged in an APK;
- the generated native library is derived from the user’s own dump and should not be distributed;
- Google Play restricts downloading executable `.so` files outside Play;
- loading arbitrary generated libraries at runtime increases security, linker-namespace, support, and policy complexity; and
- a local builder can hash-check the input and bind an APK to one exact title/revision.

A universal Play-distributed launcher with downloadable title-native code is explicitly outside the initial scope.

## Non-negotiable legal and safety boundary

The project must not include or distribute:

- retail game code or recompiled retail code;
- ROMs, CIA/CCI/NCCH contents, firmware, keys, or copyrighted assets;
- links or automation for obtaining those materials;
- title-generated `.so` files built from somebody else’s dump; or
- code intended to bypass access controls on software the user does not own.

The build flow should require a user-provided, legally dumped, supported input and should keep all derived title code local.

## Terminology

- **AOT / static recompilation:** Analyze guest machine code before launch and emit host-compilable source or object code.
- **HLE runtime:** Reimplement the guest operating-system services and hardware-facing APIs at a higher level.
- **Fallback interpreter:** Correctly executes instructions or modified code that the static analysis did not cover.
- **Generic PICA pipeline / ubershader:** A preavailable host shader/pipeline that interprets PICA state dynamically so rendering need not pause for a specialized pipeline.
- **Specialized pipeline:** A host pipeline compiled for a particular normalized PICA state combination for better steady-state performance.
- **Pipeline journal:** Portable records of guest graphics states encountered, used to prewarm or rebuild device-specific pipelines.
- **Driver pipeline cache:** Opaque, device/driver-specific cache data created by Vulkan; never assumed portable across devices or driver versions.

## Accuracy note

This pack distinguishes verified current behavior from proposed behavior. Project status changes quickly. The reference file records the exact access date and, for the two central repositories, commit pins observed during research.

---

# Part 2 — Technical overview

> Source file: `01_3DS_RECOMPILATION_TECHNICAL_OVERVIEW.md`

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

---

# Part 3 — Formal architecture SPEC

> Source file: `02_SPEC_3DS_NATIVE_RECOMP_RUNTIME.md`

# SPEC-3DS-NRR-001: 3DS Native Recompilation Runtime

**Status:** Draft for implementation  
**Version:** 0.1  
**Date:** 2026-10-17  
**Primary platform:** Android ARM64 (`arm64-v8a`)  
**Reference platform:** Linux x86-64  
**Working name:** 3DS-NRR  
**Primary upstream foundations:** `fearkov/3dsrecomp` and `fearkov/zakuro`

---

## 1. Normative language

The terms **MUST**, **MUST NOT**, **SHOULD**, **SHOULD NOT**, and **MAY** are used as requirement levels.

- **MUST/MUST NOT:** required for the architecture or release.
- **SHOULD/SHOULD NOT:** expected unless a documented technical reason justifies deviation.
- **MAY:** optional or future-facing.

---

## 2. Product definition

3DS-NRR is a hybrid native-recompilation and high-level-emulation runtime for user-owned Nintendo 3DS software.

It combines:

1. ahead-of-time conversion of guest ARM/Thumb/VFP code into native host code;
2. an interpreter fallback for undiscovered, unsupported, or modified guest code;
3. a reusable 3DS HLE runtime for kernel, services, memory, filesystem, audio, input, timing, and graphics;
4. a PICA200-to-Vulkan renderer with an always-available generic path and asynchronously compiled specialized pipelines; and
5. a desktop build tool that creates a locally signed, per-title Android package from a user-provided dump.

3DS-NRR is not a source decompilation project and is not a conventional all-JIT emulator. It is not intended to distribute games, firmware, keys, or title-derived native libraries.

---

## 3. Problem statement

Current Android 3DS emulation can deliver strong performance, but it still faces some combination of:

- runtime CPU translation;
- first-use shader/pipeline work;
- driver variability;
- limited static validation;
- broad platform overhead;
- uneven low-end performance;
- difficult title-specific optimization; and
- weak separation between portable guest-state caches and device-specific driver caches.

Existing AOT work proves that most executed guest instructions can be moved into native libraries while retaining interpreter fallback. Existing Zakuro work proves that a general HLE runtime and hybrid graphics specialization model can support many titles.

The unsolved product problem is to turn those pieces into a reproducible Android ARM64 system with safe packaging, robust lifecycle behavior, deterministic validation, and a manageable user workflow.

---

## 4. Goals

### G-001 — General title runtime

The system MUST be a reusable runtime rather than a one-title port. Per-title data, manifests, hints, and optional overrides MAY exist, but the kernel/services/GPU/audio/filesystem core MUST remain shared.

### G-002 — Native CPU execution

For supported title code discovered by `3dsrecomp`, the runtime MUST execute AOT-generated native code through the upstream recompilation ABI.

### G-003 — Correct fallback

The runtime MUST retain an interpreter for:

- unknown entry points;
- unsupported instructions;
- stale or modified code;
- dynamic/indirect paths not present in the native entry map;
- failed native-module loads; and
- debug verification.

A missing native entry MUST NOT be treated as a fatal error by default.

### G-004 — First-use graphics continuity

The renderer MUST NOT intentionally block the emulation/render thread waiting for a newly requested specialized PICA graphics pipeline after gameplay begins. A correct generic path MUST render while specialization occurs asynchronously.

### G-005 — Native Android application

The runtime MUST operate as an Android/Bionic application without requiring PRoot, X11, VirGL, a desktop root filesystem, or desktop audio/windowing libraries.

### G-006 — Local derivation

Title-derived native code MUST be generated locally from a user-provided input and MUST NOT be committed or distributed by the project.

### G-007 — Deterministic validation

Every major optimization MUST have a reference/fallback path and an automated way to compare behavior.

### G-008 — Lean runtime

Correctness and performance features MUST avoid unnecessary background services, platform dependencies, unbounded logs, or mandatory vendor-specific Android APIs.

### G-009 — Device portability

Correctness MUST not depend on a particular Snapdragon generation, proprietary Qualcomm driver, or OEM performance service. Device-specific integrations MAY improve performance but MUST remain optional.

---

## 5. Non-goals

### NG-001 — Game acquisition

The project MUST NOT obtain, distribute, link to, or automate acquisition of retail game data, firmware, keys, or copyrighted assets.

### NG-002 — Play Store release for v1

A Google Play distribution model is outside v1 scope. In particular, v1 MUST NOT depend on downloading executable `.so` title modules into a Play-distributed app.

### NG-003 — Elimination of all emulation

The runtime is not required to replace HLE, PICA translation, DSP behavior, or system-service emulation with native Android equivalents.

### NG-004 — Removal of fallback paths

The interpreter, generic graphics path, and validation modes MUST NOT be removed merely because a reference title works without them.

### NG-005 — Full low-level/cycle accuracy

Cycle-accurate 3DS hardware emulation is not a v1 requirement. Timing-sensitive behavior MUST be handled to the degree needed for supported titles and validated against existing runtime behavior.

### NG-006 — Universal enhancement framework

Widescreen, high frame rate, texture replacement, ray tracing, and game-specific native rendering are future layers, not prerequisites for v1.

### NG-007 — On-device compilation for v1

The primary v1 workflow MUST use an off-device desktop builder. On-device compilation MAY be investigated later.

---

## 6. Foundational implementation decision

### DEC-001 — Zakuro-first architecture

The implementation MUST begin from pinned versions of:

- `fearkov/3dsrecomp`; and
- `fearkov/zakuro`.

The project MUST NOT start by implementing a new ARM11 interpreter, a new 3DS HLE kernel, or a new PICA200 renderer.

### DEC-002 — Upstream preservation

Upstream code SHOULD remain in clearly identifiable modules, submodules, or subtree imports. Local changes SHOULD be isolated behind host/platform abstractions where practical.

### DEC-003 — Linux reference before Android

Every Android milestone MUST have an equivalent or narrower Linux reference test. Android-specific bugs MUST be distinguishable from guest-runtime bugs.

### DEC-004 — Per-title APK for v1

The v1 builder MUST produce a locally signed, per-title APK containing the generated native library under the normal Android native-library path.

Alternative plugin models MAY be explored only after v1 stability.

### DEC-005 — Existing hybrid PICA path

The implementation MUST preserve Zakuro’s current dynamic generic pipeline and asynchronous specialization behavior. Any renderer restructuring MUST prove equal or better correctness and frame pacing before replacing it.

---

## 7. High-level architecture

```text
┌────────────────────────────────────────────────────────────────────┐
│ Desktop Builder                                                    │
│                                                                    │
│  Input validator ── ROM parser ── 3dsrecomp ── NDK compiler       │
│         │                             │               │             │
│         └── title manifest            └── generated C └── .so      │
│                                                                    │
│  APK template + runtime libraries + title .so + manifest + signer │
└─────────────────────────────────────┬──────────────────────────────┘
                                      │ locally installed APK
                                      ▼
┌────────────────────────────────────────────────────────────────────┐
│ Android App                                                        │
│                                                                    │
│ Kotlin shell                                                       │
│   lifecycle / SAF / settings / input / touch / diagnostics        │
│             │ JNI                                                  │
│             ▼                                                      │
│ Native runtime                                                     │
│   title loader ── recomp ABI ── HLE core ── DSP/audio             │
│        │              │            │                               │
│        │       native / fallback   │                               │
│        │              │            ▼                               │
│        │              └────── PICA runtime                         │
│        │                         │                                  │
│        │             generic pipeline + async specialization       │
│        │                         │                                  │
│        └─────────────────────────┴────── Vulkan / AAudio / input   │
└────────────────────────────────────────────────────────────────────┘
```

---

## 8. Repository organization

The target workspace SHOULD use the following logical layout. Exact names MAY differ if upstream integration requires it.

```text
3ds-nrr/
  README.md
  LICENSES/
  THIRD_PARTY_NOTICES.md
  docs/
    architecture/
    legal/
    testing/
    devices/
  upstream/
    3dsrecomp/             # pinned
    zakuro/                # pinned or workspace dependency
  builder/
    cli/
    title-manifest/
    android-packager/
    toolchain/
    signing/
  runtime/
    core/                  # thin integration around Zakuro core
    recomp-loader/
    platform/
      desktop/
      android/
    telemetry/
  android/
    app/
    native/
    gradle/
    templates/
  tests/
    unit/
    differential/
    gpu-state/
    trace-replay/
    android-instrumented/
    fixtures-homebrew/
  tools/
    trace/
    cache-inspector/
    manifest-inspector/
    device-runner/
  titles-private/          # gitignored; generated/local only
  out/                     # gitignored
```

### REP-001

The repository MUST include `.gitignore` rules covering:

- ROMs and extracted title data;
- generated C/C++ from retail titles;
- title-derived objects and libraries;
- APKs containing title-derived code;
- firmware and key files;
- save data and crash dumps containing guest memory; and
- local signing keys.

### REP-002

CI MUST use homebrew, synthetic fixtures, or source-generated test code only. CI MUST NOT require retail title content.

---

## 9. Desktop builder requirements

### 9.1 Builder command model

A canonical command SHOULD resemble:

```bash
nrr build-android \
  --input /path/to/user_dump.3ds \
  --profile android-arm64-release \
  --runtime-pin pins/runtime.lock \
  --out out/title.apk
```

The builder MAY also expose separate stages:

```bash
nrr inspect INPUT
nrr recompile INPUT --target android-arm64
nrr package-android BUILD_DIR
nrr verify BUILD_DIR
nrr install BUILD_DIR/title.apk
```

### BL-001 — Input ownership boundary

The builder MUST accept only a local user-provided path or document. It MUST NOT provide download/search functionality for game content.

### BL-002 — Format support

Initial supported input SHOULD match the pinned upstream parser. Every accepted format MUST be validated before code generation.

### BL-003 — Identity manifest

The builder MUST compute and store a manifest containing at least:

```yaml
title_id: "..."
product_code: "..."
region: "..."
revision: "..."
input_sha256: "..."
executable_sha256: "..."
recompiler_commit: "..."
runtime_commit: "..."
recomp_abi_version: 4
builder_version: "..."
target_abi: "arm64-v8a"
android_min_sdk: 29
compiler_identity: "..."
compiler_flags_hash: "..."
created_utc: "..."
```

The exact schema MUST be versioned.

### BL-004 — Exact input binding

Generated native code MUST be bound to the executable bytes used during analysis. At runtime, origin validation MUST prevent stale functions from executing against modified guest code.

### BL-005 — Reproducible pins

The build MUST record exact upstream commits, toolchain version, Android NDK version, and compiler flags.

### BL-006 — Generated-source handling

Generated title source and objects MUST be written only to local, gitignored build directories.

### BL-007 — Compiler target

The builder MUST support Android NDK Clang for `arm64-v8a`. It MUST set:

- position-independent code;
- correct Android API target;
- `-ffp-contract=off` or the exact upstream-required equivalent;
- no unsafe fast-math flags;
- hidden symbol visibility except required ABI exports;
- deterministic or documented build-id behavior; and
- suitable debug-symbol generation for local crash diagnosis.

### BL-008 — Host compiler abstraction

`3dsrecomp` compiler invocation SHOULD be extended through a structured toolchain configuration rather than shell-string concatenation.

A proposed configuration:

```toml
[target.android-arm64]
cc = "/.../aarch64-linux-android29-clang"
ar = "/.../llvm-ar"
strip = "/.../llvm-strip"
cflags = [
  "-O3",
  "-fPIC",
  "-ffp-contract=off",
  "-fvisibility=hidden"
]
ldflags = ["-shared"]
output_suffix = ".so"
```

### BL-009 — Cross-compile smoke test

Before processing a full title, the builder MUST compile and load a synthetic ABI fixture for the selected target.

### BL-010 — Local signing

The builder MUST support a local debug signing key and MAY support a user-supplied release key. Keys MUST NOT be checked into the repository or uploaded.

### BL-011 — Build report

Every build MUST emit a machine-readable and human-readable report including:

- code discovery counts;
- generated functions/basic blocks;
- unsupported instruction counts;
- CRO modules found;
- compiler warnings/errors;
- library size;
- symbols exported;
- exact hashes;
- APK package ID/version;
- expected input at first run; and
- known profile-specific overrides.

---

## 10. Android packaging requirements

### AP-001 — Package identity

A per-title APK SHOULD use a deterministic package name derived from the project namespace and title ID, for example:

```text
org.example.nrr.t0004000000123400
```

Package naming MUST NOT imply affiliation with Nintendo or the title publisher.

### AP-002 — Native library placement

The APK MUST package runtime and title native libraries under the standard path:

```text
/lib/arm64-v8a/libnrr_runtime.so
/lib/arm64-v8a/libnrr_title.so
```

The runtime MAY statically link common components if that simplifies loading, but title-derived code MUST remain distinguishable for legal, debugging, and invalidation purposes.

### AP-003 — No title-derived code in public release artifacts

Public CI/release jobs MUST build only the generic runtime and synthetic fixtures. A real title APK MUST be generated locally.

### AP-004 — Game data import

At first run, the application SHOULD use Android’s Storage Access Framework to let the user select the same supported dump or an approved extracted-data directory.

The app MUST:

- compute/verify the expected hash;
- reject mismatched title/revision data for native execution;
- explain the mismatch without exposing copyrighted content;
- store persistent URI access where possible; and
- copy only data needed for reliable runtime behavior into app-private storage.

### AP-005 — Save isolation

Each package/title/profile MUST use an isolated save root. Importing saves MUST be explicit and MUST NOT overwrite existing saves without backup.

### AP-006 — APK size

The builder SHOULD avoid packaging duplicate title assets if the app can securely reference/import the user’s dump. The runtime SHOULD remain independent of title data.

### AP-007 — Sideload scope

The generated APK MUST be labeled as a local/private build. The documentation MUST explain that generated native title code is not suitable for redistribution.

---

## 11. Runtime CPU architecture

### CPU-001 — Upstream ABI compatibility

The runtime MUST implement the pinned `recomp-abi` version exactly. ABI changes MUST be gated through explicit version negotiation.

### CPU-002 — Context ownership

The host runtime MUST own the guest CPU context and supply it to native entry functions. Context lifetime MUST remain stable while native code executes.

### CPU-003 — Entry lookup

The runtime MUST support:

- executable entry lookup;
- basic-block/return-point lookup as provided by upstream;
- ARM/Thumb state distinction;
- CRO-relative entries;
- module base registration; and
- fallback when lookup fails.

### CPU-004 — Memory model

The host MUST implement the page-table and callback model expected by the ABI:

- direct pointers for ordinary mapped guest RAM where safe;
- callbacks for unmapped, watched, I/O, or special pages;
- read/write size and alignment semantics matching the guest;
- permission checks where required; and
- bounded behavior on invalid access.

### CPU-005 — SVC exits

Native code MUST return control to the HLE runtime for SVC handling. SVC behavior MUST match interpreter mode.

### CPU-006 — Execution budget

Native execution MUST honor a host-controlled instruction/cycle budget or equivalent scheduling boundary. It MUST not monopolize the process and bypass guest scheduler behavior.

### CPU-007 — Nested calls and unwind

The runtime MUST honor upstream call-depth/unwind semantics. Deep or abnormal guest call behavior MUST fail back to the host rather than corrupt the native stack.

### CPU-008 — Unsupported instructions

The ABI callback for unsupported instruction execution MUST invoke the reference interpreter for exactly the required guest operation and resume safely when possible.

### CPU-009 — Unknown targets

Unknown indirect targets MUST be logged through a bounded counter and executed through the interpreter. A debug mode MAY promote the event to an assertion.

### CPU-010 — Origin validation

Before invoking a native function, the runtime MUST ensure that its origin bytes still match the recompiled origin metadata or use an equivalent upstream validity mechanism.

### CPU-011 — Mods and patches

A mod that changes code MUST cause affected native functions to become stale. The user MAY choose to rebuild the title package to recompile modified code.

### CPU-012 — Floating-point correctness

The runtime and generated code MUST avoid host optimizations that change guest-visible floating-point behavior. Differential tests MUST cover VFP edge cases, NaNs, denormals, conversion, rounding, and flags to the extent represented by upstream.

### CPU-013 — Native coverage metric

The runtime MUST expose counters for:

- native instructions/blocks/functions executed;
- interpreter instructions executed;
- unsupported-instruction callbacks;
- unknown-entry fallbacks;
- stale-origin fallbacks; and
- time spent in each mode.

Counters MUST be optional in release mode and low-overhead when disabled.

### CPU-014 — Reference mode

A command-line/config option MUST force interpreter-only execution for correctness comparison.

### CPU-015 — Dual-run verification mode

Desktop debug builds SHOULD support function-level differential verification against the interpreter using upstream infrastructure.

---

## 12. HLE kernel and service architecture

### HLE-001 — Reuse Zakuro core

Kernel, service, filesystem, and scheduling behavior MUST initially come from the pinned Zakuro implementation.

### HLE-002 — Platform isolation

Host-specific operations MUST be behind platform traits/interfaces. Core 3DS behavior MUST NOT call Android framework APIs directly.

### HLE-003 — Deterministic mode

The desktop runtime SHOULD offer a deterministic mode controlling:

- host time input;
- random seeds where guest-visible;
- scheduler ordering where practical;
- asynchronous worker completion points; and
- trace timestamps.

### HLE-004 — Handle/IPC validation

Malformed guest messages or invalid handles MUST produce guest-visible errors or controlled termination, not host memory corruption.

### HLE-005 — Filesystem

The runtime MUST support the existing title filesystem and savedata paths needed by the reference titles. Host paths MUST be canonicalized and sandboxed under app-private or explicitly granted locations.

### HLE-006 — Update/DLC/mod layering

Layer order MUST be explicit and deterministic, for example:

```text
base title → update → DLC → user mod overlay
```

The runtime MUST include the effective content-layer identity in compatibility and cache keys when executable or shader behavior can change.

### HLE-007 — System data

The project MUST document which user-provided system data is required. It MUST NOT bundle proprietary system files.

### HLE-008 — New 3DS features

New 3DS-specific services and CPU behavior MAY be phased in. A title profile MUST declare whether it requires New 3DS behavior.

---

## 13. PICA200 graphics architecture

### GPU-001 — Reuse current Zakuro renderer

The initial Vulkan implementation MUST reuse the pinned Zakuro GPU core and its software/reference paths.

### GPU-002 — Command-list fidelity

PICA command-list parsing and register writes MUST remain guest-order correct. Optimization MUST NOT reorder guest-visible memory effects or synchronization.

### GPU-003 — Surface tracking

The renderer MUST track ownership/coherency between guest memory and host images, including:

- render targets;
- depth/stencil surfaces;
- textures sourced from prior render targets;
- display transfers;
- fills/copies;
- CPU reads/writes; and
- overlapping guest memory regions.

### GPU-004 — Generic dynamic pipeline

A generic pipeline MUST exist for every supported render-target/depth-format family and feature combination necessary to represent PICA behavior.

The generic path MUST be created or validated before gameplay.

### GPU-005 — No compile wait in gameplay

When a specialized pipeline is absent, rendering MUST proceed through the generic path. Pipeline compilation MUST be queued to a background worker.

No code path MAY call a blocking pipeline compile on the main emulation thread after the gameplay-ready state, except in an explicit debug mode.

### GPU-006 — Specialization

Specialized pipelines SHOULD use constant/specialization information to compile away unused TEV stages, lighting paths, procedural texture paths, or tests where safe.

### GPU-007 — Canonical pipeline key

A versioned canonical key MUST represent all behaviorally relevant state.

Proposed logical schema:

```rust
struct PicaPipelineKeyV1 {
    vertex_program_hash: [u8; 16],
    geometry_program_hash: Option<[u8; 16]>,
    semantic_layout_hash: [u8; 8],
    tev_state_hash: [u8; 16],
    texture_state_class: u64,
    lighting_state_class: u64,
    proctex_state_class: u64,
    fog_state_class: u32,
    alpha_test_class: u16,
    depth_stencil_class: u32,
    blend_logic_class: u32,
    color_write_mask: u8,
    color_format: u16,
    depth_format: u16,
    depth_mode: u8,
    renderer_workarounds: u64,
    schema_version: u16,
}
```

This is a proposed abstraction, not a replacement for upstream internal keys.

### GPU-008 — Key correctness tests

For every field omitted from a key, tests MUST prove that the field is supplied dynamically without changing pipeline structure/behavior.

### GPU-009 — Dynamic versus specialized equivalence

The project MUST include automated image/state tests that render the same synthetic PICA draw through generic and specialized paths and compare output within defined exactness/tolerance rules.

### GPU-010 — Pipeline publication

A completed pipeline MUST be published thread-safely. In-flight command buffers MUST continue using the pipeline they recorded.

### GPU-011 — Compile failure

A failed specialized pipeline MUST:

- retain generic rendering;
- record a bounded diagnostic;
- avoid retry loops during the same session;
- expose the failure in a debug report; and
- not cause a black frame by default.

### GPU-012 — Software/reference renderer

A software or known-correct reference path MUST remain available for targeted debugging and conformance tests, even if too slow for normal play.

### GPU-013 — Optional direct/compute paths

Alternative renderers MAY be added only behind feature flags and parity tests. They MUST NOT replace the generic correctness path until proven.

---

## 14. Shader and pipeline cache architecture

### CACHE-001 — Cache layers

The runtime MUST distinguish at least four cache types:

1. portable guest-state/pipeline recipe journal;
2. portable translated shader representation, where available;
3. process-memory specialized pipeline map; and
4. opaque device/driver Vulkan pipeline cache.

### CACHE-002 — Cache root

Each cache root MUST include:

- title ID and executable/content hash;
- runtime build ID;
- renderer schema version;
- translator version;
- enabled compatibility/workaround set; and
- where relevant, GPU/driver fingerprint.

### CACHE-003 — Portable journal

The portable journal SHOULD store normalized state keys and use counts/timestamps, not copyrighted shader binaries copied from distribution packages unless legally and technically appropriate.

### CACHE-004 — Opaque cache fingerprint

Opaque Vulkan cache data MUST be invalidated when any relevant fingerprint changes, including the Vulkan pipeline cache UUID.

### CACHE-005 — Atomic writes

Cache updates MUST use atomic replace or journaling so a process crash cannot leave the only cache copy corrupt.

### CACHE-006 — Size limits

Each cache type MUST have configurable size limits and eviction behavior. The runtime MUST not create unbounded session bundles or duplicate logs/caches.

### CACHE-007 — Prewarm

At launch, a low-priority worker MAY rebuild high-value pipelines from the portable journal. Prewarming MUST not delay title boot unless the user explicitly enables “compile before start.”

### CACHE-008 — Thermal awareness

On Android, prewarming SHOULD pause or reduce concurrency under thermal pressure, battery saver, or foreground responsiveness constraints.

### CACHE-009 — User controls

The UI MUST provide:

- clear title shader/pipeline cache;
- clear all runtime caches;
- disable prewarm;
- display cache size; and
- export a cache diagnostic manifest without exporting copyrighted game data.

### CACHE-010 — Version migration

Cache schema changes MUST either migrate safely or invalidate explicitly. Silent interpretation under a new schema is forbidden.

---

## 15. Audio/DSP requirements

### AUD-001 — Existing behavior first

Initial DSP/audio behavior MUST reuse Zakuro’s implementation.

### AUD-002 — Android backend

Android output SHOULD use AAudio or Oboe with a native callback/ring-buffer design.

### AUD-003 — Nonblocking

Guest execution MUST NOT block on host audio writes.

### AUD-004 — Clocking

The runtime MUST define which clock is authoritative and how small drift is corrected. Large corrections SHOULD avoid audible pitch jumps.

### AUD-005 — Telemetry

Debug metrics SHOULD include underruns, buffer depth, callback jitter, and resampling ratio.

### AUD-006 — Lifecycle

Pause, focus loss, Bluetooth route change, and output-device change MUST not corrupt DSP state or deadlock the runtime.

---

## 16. Android frontend requirements

### AND-001 — Minimum API

The project MUST declare and document a minimum Android API. Initial recommendation: API 29 or later, subject to upstream/native dependency verification.

### AND-002 — Architecture

V1 MUST target `arm64-v8a`. Additional ABIs MAY be added later.

### AND-003 — Surface lifecycle

The native runtime MUST tolerate surface destruction/recreation independent of process lifetime.

### AND-004 — Activity lifecycle

On pause/background:

- guest execution SHOULD pause promptly;
- audio MUST stop or drain safely;
- saves/cache metadata SHOULD flush safely;
- background compile workers SHOULD quiesce or reduce priority; and
- no Android UI thread wait may deadlock on the emulation thread.

### AND-005 — Input

The frontend MUST support Android gamepad key and axis events, touch, and configurable layouts. Physical controllers MUST not require a vendor SDK.

### AND-006 — Dual-screen layout

The UI MUST provide at least:

- stacked;
- side-by-side;
- top only;
- bottom only; and
- large top with small bottom.

Touch-coordinate mapping MUST follow the visible bottom-screen viewport.

### AND-007 — External display

External-display support MAY be added after v1, but the layout/render abstraction MUST not hard-code one physical panel.

### AND-008 — Settings persistence

Settings MUST be split into:

- global defaults;
- per-title overrides;
- per-device/GPU workarounds; and
- session-only debug flags.

### AND-009 — SAF

The app SHOULD use Storage Access Framework URIs instead of broad filesystem permissions.

### AND-010 — Crash recovery

After an unclean exit, the app MUST offer to share/view a bounded crash report and SHOULD disable only the last-known failing optional feature, not silently reset all settings.

### AND-011 — No mandatory services

The app MUST not require a persistent background service, account login, analytics SDK, cloud backend, or network connection to run a local title.

### AND-012 — Stripped Android compatibility

Core operation MUST not depend on Google Play Services. This supports AOSP-derived and stripped gaming operating systems.

---

## 17. Runtime threading model

A recommended initial model:

```text
Android UI thread
  └── lifecycle/input/config only

Emulation thread
  ├── guest scheduler
  ├── native/interpreter CPU execution
  ├── HLE services
  └── PICA command submission

Render submission thread (optional, if upstream separation supports it)
  └── Vulkan command recording/submission/presentation

Pipeline worker pool
  └── specialized shader/pipeline compilation

Audio callback/thread
  └── consume ring buffer; never call emulator locks

I/O worker
  └── asynchronous host file operations where guest semantics permit
```

### THR-001

Lock ordering MUST be documented.

### THR-002

Pipeline workers MUST NOT hold guest scheduler locks while compiling.

### THR-003

Audio callbacks MUST NOT allocate unbounded memory or acquire high-contention locks.

### THR-004

Thread counts MUST be bounded and configurable. Mobile defaults SHOULD be conservative.

### THR-005

A deterministic single-thread/debug mode SHOULD be available on desktop for diagnosis.

---

## 18. Proposed title manifest

A title package MUST include a signed or integrity-checked manifest. Proposed structure:

```json
{
  "schema": 1,
  "title": {
    "title_id": "0004000000000000",
    "product_code": "CTR-P-XXXX",
    "region": "USA",
    "revision": "0",
    "input_sha256": "...",
    "executable_sha256": "..."
  },
  "recompilation": {
    "abi_version": 4,
    "recompiler_commit": "c3f21f...",
    "compiler": "Android NDK clang ...",
    "target": "aarch64-linux-android29",
    "flags_hash": "...",
    "native_library": "libnrr_title.so"
  },
  "runtime": {
    "zakuro_commit": "412900...",
    "nrr_build_id": "...",
    "minimum_runtime_schema": 1
  },
  "features": {
    "new_3ds": false,
    "requires_system_font": false,
    "stereo": true
  },
  "profiles": {
    "default_renderer": "vulkan-hybrid",
    "known_workarounds": []
  }
}
```

The commit examples reflect the research snapshot and MUST not be hard-coded forever.

---

## 19. Proposed host integration interfaces

These are conceptual interfaces intended to guide implementation. The actual upstream ABI remains authoritative.

### 19.1 Recompiled title loader

```rust
pub trait RecompiledTitle {
    fn abi_version(&self) -> u32;
    fn identity(&self) -> &TitleIdentity;
    fn register_modules(&self, host: &mut dyn RecompHost) -> Result<()>;
    fn lookup(&self, guest_pc: u32, thumb: bool) -> Option<NativeEntry>;
    fn origin_valid(&self, guest_pc: u32, memory: &GuestMemory) -> bool;
}
```

### 19.2 Host callbacks

```rust
pub trait RecompHost {
    fn read8(&mut self, address: u32) -> u8;
    fn read16(&mut self, address: u32) -> u16;
    fn read32(&mut self, address: u32) -> u32;
    fn read64(&mut self, address: u32) -> u64;
    fn write8(&mut self, address: u32, value: u8);
    fn write16(&mut self, address: u32, value: u16);
    fn write32(&mut self, address: u32, value: u32);
    fn write64(&mut self, address: u32, value: u64);
    fn interpret_one(&mut self, ctx: &mut GuestContext) -> ExitReason;
    fn lookup_code(&mut self, pc: u32, thumb: bool) -> Option<NativeEntry>;
    fn on_svc(&mut self, svc: u32, ctx: &mut GuestContext) -> ExitReason;
}
```

### 19.3 Pipeline provider

```rust
pub trait PicaPipelineProvider {
    fn select(
        &self,
        key: &PicaPipelineKey,
        dynamic_family: DynamicPipelineFamily,
    ) -> PipelineSelection;
}

pub enum PipelineSelection {
    Specialized(Arc<Pipeline>),
    Generic {
        pipeline: Arc<Pipeline>,
        specialization_queued: bool,
    },
}
```

The actual implementation SHOULD adapt existing Zakuro structures rather than introduce redundant abstractions solely to match this document.

---

## 20. Observability and logging

### OBS-001 — Bounded logs

Logs MUST be size-bounded and rotated. The application MUST NOT generate redundant per-session bundles that grow without limit.

### OBS-002 — Default privacy

Logs MUST avoid:

- full guest memory dumps;
- raw copyrighted assets;
- host personal paths where avoidable;
- document-provider tokens;
- account identifiers; and
- controller/device serial information.

### OBS-003 — Structured events

Debug builds SHOULD emit structured events for:

- native entry/fallback reason;
- SVC/service calls;
- PICA pipeline request;
- generic fallback use;
- specialized compile start/end/failure;
- cache hit/miss;
- frame time;
- audio underrun;
- surface recreation; and
- thermal/performance-mode change.

### OBS-004 — Performance HUD

An optional HUD SHOULD show:

- emulated FPS/speed;
- frame time percentiles;
- CPU native coverage;
- generic versus specialized draw counts;
- pipeline queue depth;
- shader/pipeline cache hits;
- audio underruns;
- host CPU/GPU timing where available; and
- device temperature/power only through safe, available APIs.

### OBS-005 — Crash marker

A minimal crash-safe marker SHOULD record the last subsystem/event IDs without dumping large state. A full report can be assembled on next launch.

### OBS-006 — Export

The user MUST explicitly choose to export/share logs. No automatic upload is required.

---

## 21. Configuration model

Proposed layers, lowest to highest precedence:

1. runtime defaults;
2. device/GPU compatibility profile;
3. global user settings;
4. per-title profile;
5. per-title user overrides;
6. session/debug override.

### CFG-001

Every setting MUST declare:

- scope;
- default;
- whether restart is required;
- whether it affects cache identity;
- whether it can reduce accuracy; and
- whether it is safe for ordinary users.

### CFG-002

Compatibility workarounds MUST be data-driven where practical and tied to runtime/GPU/title conditions.

### CFG-003

“Most compatible” mode SHOULD disable optional speed hacks and force conservative synchronization without disabling required generic fallback behavior.

---

## 22. Security requirements

### SEC-001 — Input parsing

All title/container parsing MUST be bounds-checked. Malformed inputs MUST fail safely.

### SEC-002 — Generated code identity

The runtime MUST load only the packaged title library expected by the manifest and APK. It MUST NOT scan arbitrary shared libraries from public storage.

### SEC-003 — Host filesystem sandbox

Guest paths MUST map only to controlled roots. `..`, symlink, document-provider, or archive traversal MUST NOT escape the sandbox.

### SEC-004 — Memory safety

Unsafe Rust/C/C++ boundaries MUST be documented and fuzzed where practical. Guest-controlled lengths and addresses MUST be validated before host memory use.

### SEC-005 — Cache trust

Cache files MUST be treated as untrusted. Parsing MUST validate lengths, versions, hashes, and checksums. Corrupt caches MUST be discardable.

### SEC-006 — Network

No network access is required for title execution. Any future online feature MUST be opt-in and separately threat-modeled.

### SEC-007 — Signing

The builder MUST never upload or transmit the user’s signing key. Debug keys MAY be generated locally.

### SEC-008 — Dependency review

Third-party dependencies MUST be pinned and license/security reviewed. Automatic unpinned Git dependencies SHOULD be avoided in reproducible releases.

---

## 23. Legal/compliance requirements

### LEG-001

The repository and public build artifacts MUST contain only original code, compatible open-source dependencies, metadata/facts, and synthetic/homebrew fixtures.

### LEG-002

Retail-derived generated source, object code, native libraries, extracted assets, and ROM content MUST remain local to the user.

### LEG-003

The documentation MUST require users to supply their own legally obtained dumps and system data where required.

### LEG-004

No instruction in official documentation may direct users to piracy sources or access-control circumvention services.

### LEG-005

License notices for every reused project MUST be preserved. GPL components MUST NOT be combined into a distributed binary under incompatible terms.

### LEG-006

The initial recommended core (`3dsrecomp` + Zakuro) is MIT-licensed at the observed research snapshot, but every dependency and copied component MUST be checked independently.

### LEG-007

Game/title names MAY be used for factual compatibility reporting, accompanied by non-affiliation notices.

---

## 24. Performance requirements

Numbers below are engineering targets, not promises for every game/device.

### PERF-001 — No intentional pipeline stall

After gameplay begins, the 99th percentile time spent by the emulation thread requesting a pipeline SHOULD remain below 1 ms on the reference Android devices because cache misses return a generic pipeline and queue work.

### PERF-002 — Native coverage

For a selected vertical-slice title already known to work with upstream recompilation, native instruction coverage SHOULD be at least 99% during the measured scenario, unless a documented correctness reason requires more fallback.

### PERF-003 — Frame pacing

Cold first-play frame-time spikes attributable solely to specialized pipeline compilation SHOULD be eliminated in the reference scenario. Generic-path GPU cost MAY lower performance but MUST not introduce compilation waits.

### PERF-004 — Warm launch

A second launch on the same device/driver SHOULD show fewer specialization jobs before the measured scenario because of persistent caches/journal prewarm.

### PERF-005 — Memory

The runtime MUST expose memory accounting for:

- guest RAM;
- title data;
- host surface cache;
- shader/pipeline caches;
- generated title library mappings;
- audio buffers; and
- logging/trace buffers.

Hard limits SHOULD be configurable for mobile devices.

### PERF-006 — Worker bounds

Default pipeline compilation concurrency SHOULD not exceed a conservative function of available cores and thermal profile. It MUST be user/configurable.

### PERF-007 — Startup

The app SHOULD present a responsive UI during title validation, extraction, and cache prewarm. Long work MUST provide progress and cancellation.

---

## 25. Correctness and test strategy

### 25.1 Test pyramid

```text
             device/title regression
          Android instrumented tests
        trace replay and image comparison
      CPU differential and GPU equivalence
    unit/property/fuzz tests for parsers and keys
```

### TEST-001 — CPU instruction tests

Use synthetic guest instruction sequences covering ARM, Thumb, VFP, flags, branches, load/store, unaligned behavior, and exception exits.

### TEST-002 — Differential function tests

For supported functions, compare native output against interpreter output for:

- registers;
- CPSR/FPSCR-related state;
- memory writes;
- exit reason;
- next PC/state; and
- observable callbacks.

### TEST-003 — Unknown entry test

Invoke an address absent from the native map and assert controlled interpreter fallback.

### TEST-004 — Stale origin test

Modify bytes covered by a native origin and assert that the function is not executed natively.

### TEST-005 — CRO relocation test

Load a synthetic relocatable module at multiple bases and confirm native entry resolution and memory behavior.

### TEST-006 — Generic/specialized GPU parity

Generate synthetic PICA states and compare generic versus specialized output. Include TEV, lighting, fog, proctex, depth, stencil, blend, and texture edge cases.

### TEST-007 — Compile failure resilience

Force pipeline compilation failure and prove rendering continues through generic fallback with one bounded diagnostic.

### TEST-008 — Cache invalidation

Change GPU fingerprint, runtime build ID, translator version, or key schema and assert correct cache invalidation.

### TEST-009 — Surface lifecycle

Destroy and recreate the Android surface repeatedly during title execution. No host crash, deadlock, or permanent black screen is allowed.

### TEST-010 — Audio route change

Change output route/pause/resume during a synthetic audio workload and assert no deadlock or runaway buffer.

### TEST-011 — Save safety

Interrupt writes and assert atomic save/backup behavior. Existing valid saves MUST remain recoverable.

### TEST-012 — Parser fuzzing

Fuzz title container, manifest, cache, and trace parsers with malformed inputs.

### TEST-013 — Deterministic checkpoints

A reference scenario SHOULD emit periodic hashes of selected guest state. Desktop interpreter, desktop native, and Android native runs should agree where host timing does not intentionally differ.

### TEST-014 — Cold/warm benchmark

Each reference title run MUST distinguish:

- clean cache;
- populated portable journal only;
- populated SPIR-V/translated cache;
- populated driver cache; and
- after runtime/driver version change.

### TEST-015 — No-retail CI

All public CI tests MUST run without retail game data.

---

## 26. Reference device matrix

The initial device plan SHOULD include:

| Class | Example | Purpose |
|---|---|---|
| Primary Android handheld | AYN Thor / Snapdragon 8 Gen 2 | Real target, Adreno 740, active cooling, representative mature Turnip ecosystem. |
| Newer flagship handheld | Odin 3 / 8 Elite-class device | CPU/GPU headroom and newer Adreno behavior. |
| Older/low-end Adreno | Adreno 6xx device where available | Vulkan 1.1/driver fallback and memory pressure. |
| Non-Adreno Android | Mali or Xclipse device | Prevent hard-coding Qualcomm assumptions. |
| Linux x86-64 | Mesa Vulkan workstation/laptop | Golden harness and debugging. |
| Optional ARM Linux | ARM64 handheld/SBC | Prove runtime core portability outside Android. |

The exact devices MAY change. Test reports MUST record SoC, GPU, OS, driver, Vulkan version, runtime commit, and title manifest hash.

---

## 27. Milestones

## M0 — Legal/repository scaffold

Deliverables:

- workspace skeleton;
- upstream pin file;
- dependency/license inventory;
- gitignore and private-data policy;
- synthetic fixture pipeline;
- architecture decision records.

Exit criteria:

- clean clone builds generic tooling without retail data;
- no title-derived artifacts enter source control;
- exact upstream pins are recorded.

## M1 — Desktop golden harness

Deliverables:

- pinned Zakuro + `3dsrecomp` build;
- interpreter-only run;
- native-library run;
- coverage counters;
- differential test command;
- trace capture/replay baseline.

Exit criteria:

- one approved private reference title boots in both modes;
- unknown/stale code falls back correctly;
- native coverage report is reproducible.

## M2 — Graphics no-stall validation

Deliverables:

- instrumentation for generic/specialized draws;
- pipeline compile queue metrics;
- disk cache inspection;
- synthetic generic/specialized parity tests;
- forced cache-miss benchmark.

Exit criteria:

- no blocking compile on emulation thread in measured scenario;
- failed specialization retains correct generic rendering;
- cache survives restart on same device/driver.

## M3 — Android native shell

Deliverables:

- Gradle/NDK project;
- native runtime library loads;
- Vulkan surface presents a test frame;
- gamepad/touch event bridge;
- AAudio/Oboe test tone;
- lifecycle stress test.

Exit criteria:

- app runs without PRoot/X11/Google Play Services;
- surface recreation and pause/resume pass tests.

## M4 — Android AOT title fixture

Deliverables:

- NDK toolchain support in builder;
- synthetic recompiled title `.so`;
- APK packaging/signing;
- ABI/version/identity validation;
- crash symbols.

Exit criteria:

- synthetic guest fixture executes native ARM64 code on device;
- unsupported path falls back to interpreter.

## M5 — First 3DS title vertical slice

Deliverables:

- local per-title APK generation;
- title data import/hash verification;
- boot/gameplay/input/audio/save path;
- cold/warm pipeline report;
- device report for primary handheld.

Exit criteria:

- selected scenario is playable and save-safe;
- no compilation-related first-use stalls in the measured path;
- all derived code remains local.

## M6 — Compatibility hardening

Deliverables:

- multiple titles;
- per-title profiles;
- bounded crash report;
- cache controls;
- broader device matrix;
- regression automation.

Exit criteria:

- predefined compatibility set passes repeated tests;
- no device-specific correctness dependency.

## M7 — Builder UX

Deliverables:

- guided desktop UI or polished CLI;
- toolchain setup diagnostics;
- progress/cancellation;
- safe local signing;
- manifest viewer;
- one-command build/install.

Exit criteria:

- a technically competent user can create a local package without editing source code.

---

## 28. Acceptance criteria for v1

V1 is complete only when all criteria below are met.

### AC-001

A clean public checkout builds the generic Linux runtime, Android shell, builder, and synthetic fixtures without retail content.

### AC-002

The desktop builder accepts a supported user-owned title input, verifies identity, generates native code, cross-compiles it with the Android NDK, and creates a locally signed per-title APK.

### AC-003

The Android APK validates/imports the matching title data and rejects mismatched input for native execution.

### AC-004

At least one private reference title reaches sustained gameplay with input, audio, graphics, and save/load on the primary Android handheld.

### AC-005

The runtime reports native versus interpreter coverage and demonstrates fallback for unknown and stale code.

### AC-006

A clean-cache test demonstrates that missing specialized PICA pipelines render through the generic path while compilation occurs asynchronously.

### AC-007

A warm-cache test demonstrates safe cache reuse and lower specialization work without relying on a cache copied from another device.

### AC-008

Generic and specialized GPU paths pass the defined synthetic parity suite.

### AC-009

Android pause/resume, surface recreation, controller reconnect, and audio route changes do not deadlock or corrupt saves.

### AC-010

Logs and caches remain within configured limits over repeated sessions.

### AC-011

No public artifact contains title-derived native code, game data, firmware, or keys.

### AC-012

Third-party licenses and notices are complete for distributed generic binaries.

---

## 29. Risk register

| ID | Risk | Likelihood | Impact | Mitigation |
|---|---|---:|---:|---|
| R-001 | `3dsrecomp` host assumptions prevent clean Android cross-link | Medium | High | Add explicit toolchain model; synthetic ABI fixture; isolate libc/loader assumptions. |
| R-002 | Zakuro desktop frontend dependencies leak into core | Medium | Medium | Compile core crates separately; introduce narrow Android platform traits. |
| R-003 | Android Vulkan driver compiles generic pipeline slowly at startup | Medium | Medium | Precreate at splash; ship validated SPIR-V; cache device-specific pipeline; conservative variants. |
| R-004 | Generic path differs subtly from specialization | Medium | High | Automated parity suite; generic path as reference; state-key audits. |
| R-005 | CRO/indirect target gaps cause frequent fallback | Medium | Medium | Trace-driven discovery, hints, coverage report, preserve interpreter. |
| R-006 | Generated library is too large or link command exceeds platform limits | Medium | Medium | Object grouping/archives, response files, upstream Windows improvements, size reports. |
| R-007 | Title code uses behavior changed by host compiler | Low–medium | High | Strict flags, no fast-math, differential tests, helper semantics. |
| R-008 | APK/plugin design conflicts with Android loader namespaces | Medium | High | Per-title APK with standard `/lib/<abi>/`; defer plugin architecture. |
| R-009 | Google Play policy blocks intended distribution | High for Play | Medium | Sideload/local-build scope; do not download native code. |
| R-010 | Legal concerns around generated code distribution | High if mishandled | High | Never distribute title-derived output; local-only builder; clear policy. |
| R-011 | Upstream changes break integration | High over time | Medium | Pin commits; compatibility layer; scheduled upstream rebases with regression suite. |
| R-012 | AI/Codex makes broad unreviewed rewrites | Medium | High | Small prompts, tests first, no subsystem rewrite, diff/command report required. |
| R-013 | Logs/caches create storage bloat | Medium | Medium | Quotas, rotation, per-title deduplication, explicit clear controls. |
| R-014 | Thermal throttling masks performance results | High | Medium | sustained tests, temperature/power context, conservative worker counts. |
| R-015 | Device-specific Turnip features become correctness requirement | Medium | High | standard Vulkan correctness path; optional driver adapters only. |

---

## 30. Architecture decision records to create

The implementation repository SHOULD create ADRs for at least:

1. Zakuro-first versus Azahar integration.
2. Per-title APK versus plugin package.
3. Minimum Android API.
4. Rust/JNI boundary.
5. Vulkan surface ownership.
6. Audio backend.
7. Pipeline-key schema.
8. Portable journal format.
9. Driver cache fingerprint.
10. Title data import/storage model.
11. Save atomicity/backup policy.
12. Upstream pin/update process.
13. Telemetry/logging limits.
14. License composition.

---

## 31. Open questions requiring experiments

1. What exact changes are required for current `3dsrecomp` compiler invocation to target Bionic/NDK reliably?
2. Can the generated library use the upstream ABI without any host-libc assumptions on Android?
3. Which Zakuro crates currently depend on desktop-only window/audio/input crates?
4. Does the generic dynamic pipeline compile reliably on proprietary Adreno, Turnip, Mali, and Xclipse drivers?
5. What percentage of cold first-play draws use generic fallback in representative titles?
6. Is the current Vulkan pipeline cache saved atomically and fingerprinted sufficiently for Android driver updates?
7. Which shader/state data can be safely stored as a portable journal without storing title-derived copyrighted content?
8. How much CPU/GPU/power overhead does the generic fragment path add on an 8 Gen 2 handheld?
9. Should Android package one combined native library or separate runtime/title libraries?
10. Can title data remain in a document-provider URI with sufficient random-access performance, or must it be copied/extracted?
11. Which DSP/audio path offers the best Android latency without changing guest timing?
12. How does Android process death during backgrounding affect save/cache atomicity?
13. Which title/revision should be the private vertical-slice benchmark, and what repeatable route should be recorded?
14. What is the minimum homebrew/synthetic fixture set needed to test services without retail software?
15. What parts of Android support can be upstreamed cleanly to Zakuro?

---

## 32. Definition of done for each Codex task

No Codex task is complete unless its response and commit include:

- the issue/requirement IDs addressed;
- files changed;
- rationale tied to the existing architecture;
- commands run;
- test output;
- supported/unsupported platforms;
- known assumptions;
- any new unsafe code and its invariants;
- license implications;
- performance impact if relevant;
- documentation updates; and
- one bounded next task.

A task that only compiles but lacks a test or observable result is incomplete unless it is explicitly a scaffolding task.

---

## 33. Final implementation directive

The project MUST optimize for **reuse, correctness fallback, and measurable integration**, not novelty.

The first question for every subsystem is:

> “Does pinned `3dsrecomp`, Zakuro, Azahar, or another mature project already implement this behavior?”

Only missing platform/product layers should be created. Existing CPU semantics, HLE services, PICA behavior, and shader translation should be wrapped, tested, and incrementally extended rather than rewritten by an agent without a demonstrated need.

---

# Part 4 — Existing projects and gap matrix

> Source file: `03_EXISTING_PROJECTS_AND_GAP_MATRIX.md`

# Existing Projects, Prior Art, and Gap Matrix

**Prepared:** 2026-10-17  
**Purpose:** Identify which parts of SPEC-3DS-NRR-001 already exist, what can be reused, and what still needs implementation.

---

## 1. Executive assessment

The proposed architecture is approximately:

- **CPU AOT and fallback:** already implemented in `3dsrecomp` + Zakuro.
- **General 3DS HLE runtime:** substantially implemented in Zakuro; mature alternative/reference in Azahar; additional independent reference in Panda3DS.
- **PICA dynamic fallback while specialization compiles:** already implemented in current Zakuro source.
- **Disk-backed Vulkan pipeline cache:** already present in Zakuro; mature cache/worker concepts also exist in Azahar.
- **Native Android application:** partially demonstrated, not complete in the central upstream pair.
- **Android NDK cross-compilation of title-derived AOT code:** conceptually straightforward and demonstrated in analogous projects, but not yet a polished generic `3dsrecomp` workflow.
- **Per-title APK builder:** not implemented as a mature general 3DS tool.
- **Portable pipeline journal/prewarm:** partly represented by other systems; not clearly complete in Zakuro.
- **Production validation/device matrix:** not complete.

The correct implementation strategy is therefore to integrate and harden, not re-create.

---

## 2. Status legend

| Symbol | Meaning |
|---|---|
| **Implemented** | Present in a usable upstream form. Integration/testing may still be required. |
| **Partial** | Prototype, limited scope, or missing production hardening. |
| **Reference** | Useful design or semantics source, but not a direct drop-in. |
| **Missing** | No identified implementation meeting the SPEC. |
| **Game-specific** | Works only for one/few titles and cannot satisfy a general runtime alone. |

---

# Part I — Existing 3DS projects

## 3. `fearkov/3dsrecomp`

### Role

Static recompilation toolkit for Nintendo 3DS title code.

### What it already provides

| Capability | Status | Notes |
|---|---|---|
| Parse title executable/code | **Implemented** | Reads game code and discovers executable regions/functions. |
| ARM instruction conversion | **Implemented** | Emits C semantics for guest ARM instructions. |
| Thumb conversion | **Implemented** | Separate Thumb code-generation support. |
| VFP conversion | **Implemented** | Host code generation includes VFP behavior. |
| Main executable discovery | **Implemented** | Uses entry points, direct calls/targets, pointers, and heuristics. |
| CRO module analysis | **Implemented** | Supports relocatable CRO modules and module-relative entries. |
| Shared native library output | **Implemented** | Outputs `.so`, `.dll`, or `.dylib` through a runtime-neutral ABI. |
| Interpreter fallback | **Implemented through ABI/runtime** | Unknown/unsupported behavior can return to Zakuro’s interpreter. |
| Unsupported instruction callback | **Implemented** | Host callback can interpret an instruction not emitted natively. |
| Origin/code validation | **Implemented** | Runtime can detect changed code and avoid stale native output. |
| Manual overrides | **Implemented** | Selected guest functions can be replaced with C implementations. |
| Differential verification | **Implemented** | Compares recompiled function effects against Zakuro interpreter. |
| Standalone port mode | **Implemented** | Can link generated code with Zakuro runtime into a standalone program. |
| Portable host ABI | **Implemented** | `recomp.h` / Rust ABI crate defines context, entries, modules, exits, callbacks. |
| Android NDK target configuration | **Partial/Missing product layer** | AArch64 is possible; polished NDK/Bionic toolchain profile is not the normal documented path. |
| Android APK packaging | **Missing** | Out of scope for upstream tool today. |

### Important implementation details

- The generated library is intended to remain independent of a particular frontend.
- Entry tables cover control-flow resumption points, including post-call/post-SVC locations.
- Module entries can remain relative until the runtime supplies a CRO load base.
- A large page table enables direct host access for ordinary guest RAM and callbacks for special pages.
- The compiler must avoid transformations such as fused multiply-add that can change guest rounding behavior.
- Generated code is title-derived and should remain local.

### Recommended reuse decision

**Use directly and pin.** Do not implement a second 3DS static recompiler unless a concrete, tested limitation requires upstream changes.

### Changes likely required

1. structured cross-compilation toolchain configuration;
2. Android NDK Clang/LLVM `ar` support;
3. Android target smoke tests;
4. output/install metadata for APK packaging;
5. reproducible toolchain/flag recording; and
6. possibly response-file/archive handling for very large generated builds.

### License at research snapshot

MIT, as declared in `Cargo.toml`.

---

## 4. `fearkov/zakuro`

### Role

General HLE Nintendo 3DS emulator/runtime in Rust, designed to use `3dsrecomp` output.

### What it already provides

| Capability | Status | Notes |
|---|---|---|
| 3DS HLE runtime | **Implemented/active** | Kernel, services, memory, filesystem, scheduler, and other platform behavior. |
| ARM11 interpreter | **Implemented** | Correctness and fallback engine. |
| `3dsrecomp` loader | **Implemented** | Loads/reuses recompiled native libraries. |
| CRO/module runtime | **Implemented** | Supports dynamic title modules. |
| Broad title compatibility | **Implemented but evolving** | Compatibility list includes many playable commercial titles. |
| PICA register/command processing | **Implemented** | General graphics runtime. |
| Software/reference graphics paths | **Implemented** | Useful for correctness/debugging. |
| Vulkan hardware renderer | **Implemented** | Tracks surfaces, draws, synchronization, and host resources. |
| Dynamic generic fragment path | **Implemented** | Reads PICA state dynamically and renders while specialization compiles. |
| Asynchronous specialization | **Implemented** | Specialized pipeline can compile while drawing continues. |
| Disk-backed Vulkan pipeline cache | **Implemented** | Keeps prior pipeline cache between runs. |
| OpenGL backend | **Implemented** | Provides portability/fallback and enabled Linux handheld forks. |
| Updates/mods/texture-related behavior | **Partial/Implemented** | Exact coverage varies by feature/title. |
| Desktop UI/frontend | **Implemented** | Windows/Linux x86-64 releases. |
| Native Android frontend | **Missing/experimental elsewhere** | No polished upstream APK path identified. |
| Android lifecycle/audio/input | **Missing product layer** | Must be added or adapted. |
| Android ARM64 official release | **Missing** | Current releases observed are desktop x86-64. |
| Portable pipeline recipe journal | **Partial/unclear** | Driver cache exists; a clearly portable title-state journal should be added/verified. |

### Critical source finding: the “theoretical” ubershader already exists

Current Zakuro fragment source uses specialization constants for optimized variants and a `DYNAMIC` path that reads values from draw registers. The source comments describe the generic path as the pipeline used while the state-specific pipeline compiles. Renderer code reports pipeline compilation while drawing continues.

This directly satisfies the core anti-stutter architecture requirement more closely than a new renderer proposal would.

### Recommended reuse decision

**Use as the primary runtime and GPU foundation.** The Android project should isolate frontend/platform work rather than fork/rewrite HLE and rendering behavior wholesale.

### Changes likely required

1. clean separation of core crates from desktop frontend assumptions;
2. Android/Bionic build target;
3. `ANativeWindow`/Vulkan surface layer;
4. AAudio/Oboe backend;
5. Android gamepad/touch/sensor bridge;
6. lifecycle and process-death handling;
7. device-fingerprinted cache paths;
8. portable pipeline journal and prewarm metrics;
9. Android crash-safe diagnostics; and
10. mobile performance/thermal tuning.

### License at research snapshot

MIT, declared at the workspace level.

---

## 5. Azahar

### Role

Mature Citra-derived HLE 3DS emulator with desktop and Android support.

### Relevant implemented work

| Capability | Status | Relevance |
|---|---|---|
| Mature Android application | **Implemented** | Strong reference or possible future host for AOT backend. |
| Broad HLE/service compatibility | **Implemented** | Mature semantics/reference. |
| Dynarmic CPU backend | **Implemented** | Conventional dynamic translation path. |
| Vulkan renderer | **Implemented** | Alternative PICA implementation. |
| Vulkan shader disk cache | **Implemented** | Stores/reuses shader representations and pipeline configurations. |
| Background shader workers | **Implemented** | Compiles vertex/fragment/geometry work off main flow. |
| Direct SPIR-V generation | **Implemented** | Useful reference for PICA state-to-SPIR-V. |
| Android input/camera/microphone/layout | **Implemented** | Valuable frontend reference. |
| `3dsrecomp` ABI backend | **Missing** | Would require significant integration. |

### Architectural value

Azahar is the strongest alternative for:

- Android UX and lifecycle;
- mature service behavior;
- per-title settings;
- content installation;
- controller/touch/camera/microphone handling;
- Vulkan cache design; and
- compatibility debugging.

### Why it is not the first implementation target

Integrating a Rust-generated `recomp-abi` into Azahar’s C++ memory, scheduler, and CPU architecture is a larger project than Android-enabling Zakuro, which already consumes the ABI.

### Recommended reuse decision

**Reference and later integration candidate.** Use its Android and cache patterns for comparison. Do not copy GPL code into an MIT-distributed binary without following GPL obligations.

### License

GPL family, inherited from Citra/Azahar project terms. Verify exact repository license before reuse.

---

## 6. Panda3DS

### Role

Independent C++ HLE 3DS emulator with Android ARM64 builds and experimental architecture ideas.

### Relevant work

- Android APK build pipeline.
- HLE 3DS core and PICA implementation.
- Vulkan/OpenGL options.
- Dynarmic CPU backend.
- Explicit interest in ARM virtualization/KVM for low-end hardware.
- Lua scripting, debugging, and reverse-engineering features.

### Relevance

Panda3DS provides an independent reference for:

- Android frontend/build integration;
- PICA behavior;
- service semantics;
- device portability; and
- potential virtualization research.

### Gap relative to SPEC

It does not provide the `3dsrecomp` AOT/library model or the exact Zakuro hybrid pipeline architecture.

### Recommended reuse decision

**Reference, not base.** Compare Android build and input/frontend patterns; preserve license boundaries.

---

## 7. `ZenixX-dev/zakuro-android`

### Role

Experimental patches/scripts to run Zakuro and `3dsrecomp` inside Android through Termux + PRoot Debian + Termux-X11.

### Accomplished

- Compiles `3dsrecomp` and Zakuro natively for `aarch64-unknown-linux-gnu` on an Android phone.
- Opens the graphical interface through X11/VirGL.
- Adds AArch64 compiler flags and scripts.
- Demonstrates the current core can build on ARM64.

### Not accomplished

- Android/Bionic target;
- APK packaging;
- direct Vulkan/Turnip path;
- native Android input/touch;
- lifecycle handling;
- long gameplay validation;
- stable audio; and
- in-phone full recompilation validation.

### Recommended reuse decision

**Use as an experiment record only.** Do not make PRoot/X11 a product dependency.

---

## 8. Pocket Native

### Role

Fork of Zakuro + `3dsrecomp` for low-cost ARM Linux handhelds such as the R36S.

### Accomplished

- PC-side per-title build flow.
- Native-recompiled code deployed to ARM handheld.
- OpenGL ES 3.1 renderer tuned for Mali-G31.
- KMS display path.
- evdev controller input.
- ALSA audio.
- device-native menu, layout, performance profiles, and per-title settings.
- title probe mode.
- local-only game dump model.

### Importance to this SPEC

Pocket Native validates the proposed split:

```text
desktop builder → title-native output → constrained ARM handheld runtime
```

It also shows that a general Zakuro-based runtime can be adapted to a non-desktop device without rewriting the CPU/HLE core.

### Limitations

- Linux/ArkOS, not Android.
- OpenGL ES path, not the target Vulkan path.
- only a narrow tested title set.
- upstream Android app and Vulkan renderer are intentionally absent from the fork.

### Recommended reuse decision

**Study build/package separation, frontend design, and low-resource device controls.** Port concepts, not necessarily code, depending on license and divergence.

---

## 9. Nebby

### Role

Experimental launcher/recompiler/mod manager for native-recompiled 3DS Pokémon titles.

### Reported accomplishments

- Uses `3dsrecomp` for native code.
- Provides a Zakuro compatibility backend for experimental titles.
- Has a native runtime for Pokémon Moon with gameplay and save/load reported working.
- Integrates Vulkan through TriAevum/NRI-derived architecture.
- Includes filesystem, input, save, audio, GSP/PICA, services, kernel/scheduler, and mod infrastructure.
- ARM64/Android support is in development.

### Relevance

Nebby demonstrates a spectrum between general runtime and per-title native port. It is useful for:

- launcher/build UX;
- per-title profiles;
- mod management;
- separating native runtime from compatibility backend; and
- planning Android-prepared ARM64 builds without compiling on the phone.

### Limitations

- very experimental;
- narrow title focus;
- Android gameplay not yet verified in the observed README;
- title-specific native runtime work can diverge from general behavior.

### Recommended reuse decision

**Reference for UX and title-profile concepts.** Validate every claimed subsystem before adopting code.

---

## 10. TriAevum / Echoes of Time

### Role

Game-specific AOT native PC project for Ocarina of Time 3D with a modern Vulkan/NRI renderer and enhancements.

### Accomplished/claimed

- AOT native title execution.
- native Vulkan rendering;
- single-screen UI;
- high-frame-rate visual interpolation;
- widescreen/FOV/effects;
- custom textures;
- shader preparation during setup and later cache use;
- Forge-style user-owned ROM preparation.

### Relevance

TriAevum is evidence for the high ceiling of title-specific work after a general AOT/runtime foundation exists.

It also provides a caution: title-specific rendering can consume substantial engineering effort and releases may be fragile. Its README notes withdrawn builds and alpha-level testing.

### Recommended reuse decision

**Reference/game-specific track.** Do not make a custom renderer a prerequisite for the general Android runtime.

---

# Part II — Similar work on other systems

## 11. N64: Recompiled

### Core idea

Statically translates N64 MIPS binaries into portable C and expects a runtime to implement guest behavior. It handles direct calls, branches, jump tables, overlays, relocations, and patch workflows.

### Lessons for 3DS-NRR

1. Generated C can be portable across host architectures.
2. Generated code and runtime should be separate.
3. Overlay/relocation metadata belongs in the runtime contract.
4. A patch layer can replace recompiled functions without rebuilding all generated code.
5. A normal host compiler can optimize literal guest semantics effectively.
6. Game data should remain user-provided.

### Directly reusable?

No; guest ISA/runtime differ. Architectural patterns are highly reusable.

---

## 12. Zelda 64: Recompiled

### Role

A polished game-specific native port built with N64: Recompiled and RT64.

### Lessons

- user supplies the original game;
- native ports can add high frame rates, widescreen, mods, gyro, and low-latency UI;
- ARM64 builds are practical;
- runtime graphics can preserve original behavior and add enhancements;
- a title-specific port is not an emulator and should clearly state scope.

### Caution for Codex use

The project’s contribution policy explicitly bans generative-AI contributions. It can be studied as public prior art, but Codex-generated work must not be submitted to that upstream project in violation of its policy.

---

## 13. AnyPS5

### Core idea

Transforms/relinks PS5 executables into native host formats and reimplements system libraries. Graphics commands and RDNA shaders are translated to Vulkan/SPIR-V.

### Relevant graphics architecture

- shader decoder;
- control-flow reconstruction;
- intermediate representation;
- optimization;
- SPIR-V generation;
- in-memory and disk shader caches;
- prebuilt shader packs;
- pipeline journals;
- background shader preparation;
- device fingerprinting; and
- graphics pipeline library support where available.

### Lessons for 3DS-NRR

1. Native CPU-format execution does not remove GPU translation.
2. Separate portable pipeline recipes from opaque device caches.
3. Start compilation when shaders/states are registered, not only at first draw.
4. Replay prior pipeline recipes while the title loads.
5. Let an unexpected draw build/fall back safely rather than assuming prewarm is complete.

### Directly reusable?

No; guest APIs and shader ISA differ. Design patterns are directly relevant.

---

## 14. Dolphin hybrid/exclusive ubershaders

### Core idea

GameCube/Wii fixed-function GPU behavior creates many host shader variants. Dolphin offers:

- specialized shaders for best steady-state performance;
- hybrid ubershaders that render unknown states immediately and compile specializations in the background;
- exclusive ubershaders for full no-stutter coverage at higher GPU cost;
- precompile-cached-shaders-on-start; and
- skip-drawing as an alternate compromise.

### Lessons

This is the closest established conceptual match to Zakuro’s PICA `DYNAMIC` path.

The preferred hierarchy is:

```text
specialized ready → use specialized
specialized absent → use generic/ubershader and compile in background
compile fails      → retain generic
```

### Directly reusable?

No code should be assumed portable to PICA without license/architecture review. The design is strongly validated prior art.

---

## 15. Vita3K

### Core idea

General PlayStation Vita emulator on desktop and Android. It provides ARM guest execution, system-service HLE, and a Vita GPU shader recompiler.

### Lessons

- mature emulator shader compilers can be reused by thinner translation layers;
- Android driver quality and custom Adreno drivers materially affect results;
- HLE and shader translation remain necessary even for another mobile ARM platform.

### Relevance to SPEC

Reference for Android-native emulator architecture and GPU translation. Not a direct component.

---

## 16. vita2hos

### Core idea

Runs Vita ARMv7 executables natively in AArch32 mode on Nintendo Switch ARMv8 and redirects imported Vita modules to Horizon OS/native routines. It describes itself as a translation layer rather than an emulator.

### Lessons

1. Same-family CPU architecture can eliminate much instruction emulation.
2. Imported system modules can be redirected to compatible host services.
3. Graphics still require translation; vita2hos reuses Vita3K shader work.
4. CPU-native execution and GPU translation should be designed independently.

### Difference from Android 3DS-NRR

Modern Android ARM64 environments may not expose a compatible AArch32 execution mode or 3DS ABI, so AOT-to-AArch64 remains the safer general path.

---

## 17. shadPS4

### Core idea

Runs PS4 x86-64 executables on x86-64 hosts while reimplementing system libraries and translating AMD graphics behavior.

### Lessons

- native/same-ISA CPU execution can coexist with extensive HLE;
- shader compilers remain a primary complexity center;
- game compatibility is governed by OS/GPU semantics, not CPU ISA alone;
- a general runtime needs per-title workarounds and robust diagnostics.

---

## 18. FEX-Emu

### Core idea

Runs x86/x86-64 applications on ARM64 Linux, can pair with Wine/Proton, forwards graphics API calls to native host libraries, and uses code caching/per-app settings.

### Lessons

- call forwarding avoids emulating the entire graphics stack;
- persistent code caches can reduce translation stutter;
- per-app compatibility profiles are necessary;
- ARM gaming becomes practical when CPU translation, API forwarding, and host drivers are treated as separate layers.

### Relevance

FEX is not needed for native 3DS AOT, but its cache and per-application configuration patterns are useful.

---

## 19. Xbox 360 static recompilation and Rayman Origins Recompiled

### Core idea

XenonRecomp-style systems translate PowerPC Xbox 360 code to C/C++, pair it with a shared runtime, and compile to host native code.

Rayman Origins Recompiled reports:

- native ARM64 game code on Android;
- NDK/Vulkan application packaging;
- touch/gamepad input;
- a native renderer;
- 60 FPS on a Galaxy S23; and
- local-only title-derived code/assets.

### Lessons

This is especially relevant proof for the proposed Android workflow:

```text
user-owned console dump
    → desktop/static analysis
    → generated portable source
    → Android ARM64 native code
    → native Android app/runtime
```

It also demonstrates that a custom native renderer may eventually outperform generic GPU emulation for one game—but that is a later, game-specific optimization.

---

# Part III — Subsystem gap matrix

## 20. Full SPEC coverage matrix

| SPEC subsystem | 3dsrecomp | Zakuro | Azahar | Other evidence | Remaining work |
|---|---|---|---|---|---|
| ARM/Thumb/VFP AOT | **Implemented** | Consumer | No | N64/Xenon patterns | Android cross-target hardening. |
| Native ABI/shared library | **Implemented** | **Implemented host** | No | N64Recomp | Android package/load tests. |
| Entry discovery | **Implemented** | Uses output | Dynarmic runtime discovery | Xenon jump-table tools | Trace-driven improvements and reports. |
| CRO modules | **Implemented** | **Implemented** | **Implemented runtime** | — | Android regression tests. |
| Interpreter fallback | ABI support | **Implemented** | **Implemented** | — | Coverage metrics/UX. |
| Origin invalidation | **Implemented** | Integrates | JIT invalidation model | — | Mod/rebuild workflow. |
| Differential verifier | **Implemented** | Reference interpreter | Separate tests | — | CI fixture expansion. |
| HLE kernel/services | No | **Implemented** | **Implemented/mature** | Panda3DS reference | Android integration and missing-service work. |
| Filesystem/saves | No | **Implemented/partial** | **Implemented/mature** | Pocket Native | SAF/app-private mapping, atomic backups. |
| DSP/audio | No | **Implemented/partial** | **Implemented** | Vita3K/Pocket Native | AAudio/Oboe backend and lifecycle. |
| PICA command processing | No | **Implemented** | **Implemented** | Panda3DS | Preserve and test. |
| Generic GPU fallback | No | **Implemented** | Different cache/async model | Dolphin | Android driver validation. |
| Async specialization | No | **Implemented** | **Implemented workers** | AnyPS5/Dolphin | Queue metrics, failure handling. |
| Driver pipeline cache | No | **Implemented** | **Implemented** | AnyPS5 | Fingerprint/atomicity audit. |
| Portable pipeline journal | No | **Partial/unclear** | Pipeline configs cached | AnyPS5 | Define schema and prewarm. |
| Native Android UI | No | **Missing** | **Implemented** | Panda3DS/Vita3K | Build in Zakuro-first project. |
| Android ARM64 runtime | Compiler output possible | **Missing official** | **Implemented** | PRoot prototype | Bionic build and frontend. |
| Per-title Android APK | No | No | No | Rayman Origins Recomp | Builder/template/signing. |
| Touch/gamepad/layout | No | Desktop features | **Implemented** | Pocket Native/Panda3DS | Android bridge and profiles. |
| Thermal/power profiles | No | Limited/desktop | Android settings | Pocket Native | Generic Android controls/metrics. |
| Legal local-build model | Documented | User dump | User dump | N64/Xenon projects | Enforce in tooling/CI. |
| Bounded crash-safe logs | No | Partial | Mature logs | User requirements | Add lean structured diagnostics. |
| Device test farm | No | No | Community testing | — | Build automated matrix. |

---

## 21. What should be copied, wrapped, or only studied?

| Component | Action | Reason |
|---|---|---|
| `3dsrecomp` code generator and ABI | **Use/pin/extend upstream** | Direct fit and MIT license. |
| Zakuro CPU interpreter and HLE core | **Use/pin/wrap** | Already integrated and general. |
| Zakuro Vulkan renderer | **Use/pin/instrument** | Contains desired generic/specialized path. |
| Zakuro pipeline cache | **Use and audit** | Existing device cache tier; add fingerprints/journal if needed. |
| Azahar Android UI | **Study; do not blindly copy** | Mature reference; GPL obligations and different architecture. |
| Azahar shader disk cache | **Study and compare** | Useful mature implementation patterns. |
| Panda3DS Android build | **Study** | Independent Android reference. |
| Pocket Native builder/frontend | **Study and selectively adapt** | Strong off-device/device split; different OS/backend. |
| Nebby/TriAevum native runtime | **Study cautiously** | Experimental and title-specific. |
| Dolphin ubershaders | **Study design** | Validates hybrid fallback model. |
| AnyPS5 pipeline journal | **Study design** | Portable recipe/prewarm model. |
| Rayman Origins Android recomp | **Study packaging/build** | Strong analogous Android AOT proof. |
| N64Recomp | **Study generated-code/runtime split** | Proven static-recomp architecture. |

---

# Part IV — Licensing and contribution constraints

## 22. License matrix

This is a research summary, not legal advice. Verify current repository licenses before distribution.

| Project | Observed license/constraint | Implication |
|---|---|---|
| `3dsrecomp` | MIT declared in Cargo manifest | Suitable for direct integration with notice preservation. |
| Zakuro | MIT declared in workspace manifest | Suitable for direct integration with notice preservation. |
| Azahar | GPL-family | Linking/copying code can impose GPL distribution obligations. |
| Panda3DS | GPL-2.0-or-later observed in repo | Treat as reference unless willing to comply with GPL for combined binary. |
| Vita3K | GPLv2 | Reference or GPL-compliant reuse only. |
| shadPS4 | GPL-2.0-or-later | Reference or GPL-compliant reuse only. |
| N64Recomp | Check current repository license | Architectural reference; verify before copying. |
| Zelda64Recomp | Open source plus explicit no-AI contribution rule | Do not submit AI-generated work upstream; study only. |
| Rayman Origins Recomp | GPL-3.0 observed | Study Android patterns; copied code affects licensing. |
| AnyPS5 | Verify repository license/component licenses | Prefer design reference unless license review approves reuse. |
| Dolphin | GPL-2.0-or-later | Study design or comply with GPL for code reuse. |
| FEX | Verify current license and component boundaries | Design reference unless reviewed. |

### LIC-001

A Codex agent MUST inspect `LICENSE`, package manifests, and third-party notices before copying code.

### LIC-002

“Publicly visible source” does not mean “freely copyable under any license.”

### LIC-003

AI-agent use MUST respect project-specific contribution policies, including repositories that prohibit AI-generated contributions.

---

# Part V — Recommended implementation decomposition

## 23. Reuse plan by phase

### Phase A — Prove existing desktop stack

Use without redesign:

- `3dsrecomp` CLI/library;
- `recomp-abi`;
- Zakuro interpreter;
- Zakuro HLE core;
- Zakuro Vulkan renderer;
- Zakuro generic/specialized pipelines;
- Zakuro driver pipeline cache.

Add only:

- pinning;
- build scripts;
- metrics;
- tests;
- trace capture; and
- documentation.

### Phase B — Cross-compile synthetic library

Extend:

- `3dsrecomp` compiler abstraction;
- NDK toolchain configuration;
- ABI fixture;
- symbol/loader tests.

No retail title needed.

### Phase C — Android host

Create:

- Gradle app;
- JNI/native bridge;
- `ANativeWindow` Vulkan surface;
- AAudio/Oboe backend;
- input/touch bridge;
- lifecycle adapter;
- app-private path provider; and
- settings/log export UI.

Wrap existing Zakuro core instead of modifying guest semantics.

### Phase D — Per-title builder/package

Create:

- manifest;
- title identity validation;
- NDK native title build;
- APK template;
- signing/install; and
- local data import.

### Phase E — Cache and mobile hardening

Audit/extend:

- pipeline cache fingerprint;
- portable recipe journal;
- atomic cache writes;
- size quotas;
- mobile worker limits;
- thermal response;
- generic/specialized parity tests.

---

## 24. Missing work ranked by value

| Rank | Missing capability | Why it matters |
|---:|---|---|
| 1 | Native Android/Bionic Zakuro runtime | Converts proof-of-concept into the target product. |
| 2 | NDK cross-compile path for generated title library | Enables native ARM64 execution in APK. |
| 3 | Local per-title APK builder | Solves loading, policy, identity, and user workflow. |
| 4 | Android lifecycle/input/audio integration | Required for an actual handheld experience. |
| 5 | Generic/specialized pipeline instrumentation/parity tests | Verifies no-stutter claims and prevents graphics regressions. |
| 6 | Portable pipeline journal/prewarm | Improves warm starts and survives driver-cache invalidation. |
| 7 | Device-fingerprinted atomic caches | Prevents crashes/corruption after driver/runtime changes. |
| 8 | Lean crash-safe telemetry | Makes device/title failures diagnosable without log bloat. |
| 9 | Automated device regression | Maintains compatibility across Adreno/Mali/Android variants. |
| 10 | User-facing builder UX | Makes the system practical outside developer machines. |

---

## 25. Research claims that must not be overgeneralized

1. A project listing a title as playable does not prove complete playthrough compatibility.
2. A PRoot AArch64 build does not prove native Android/Bionic compatibility.
3. A generic pipeline eliminating compilation stalls does not guarantee full speed; it may be GPU-expensive.
4. Pipeline cache persistence does not imply portability across devices/drivers.
5. AOT CPU coverage near 99.8% in tested titles does not guarantee the same for every game.
6. A game-specific native renderer does not prove a general renderer can achieve the same performance.
7. Android ARM64 support in development does not mean an APK is usable today.
8. A synthetic or homebrew test cannot replace retail-title regression for private validation.
9. Similar architecture does not mean code can be copied without license review.
10. Same-family ARM guest/host does not mean guest binaries can execute directly under the Android ABI.

---

## 26. Final gap statement

The remaining project is not “invent a 3DS native recompiler and shader-stutter solution.” Those exist in meaningful form.

The remaining project is:

> **Create a production-quality Android host and local package builder around the existing `3dsrecomp` + Zakuro stack; prove the existing hybrid PICA renderer on mobile drivers; add portable cache/prewarm and rigorous validation; and preserve all correctness fallbacks while making the workflow accessible.**

---

# Part 5 — Annotated references

> Source file: `04_REFERENCES.md`

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

---

# Part 6 — Codex prompt pack

> Source file: `05_CODEX_PROMPT_PACK.md`

# Codex Prompt Pack: 3DS Native Recompilation Runtime

**Purpose:** Provide bounded prompts for building the architecture in `SPEC-3DS-NRR-001` without asking Codex to rewrite solved emulator subsystems.

---

## 1. Operating model

Do **not** begin by asking Codex to “build the whole emulator.”

Use this sequence:

1. Repository reconnaissance.
2. Reproducible upstream pinning.
3. Desktop golden harness.
4. CPU fallback/coverage instrumentation.
5. Graphics no-stall validation.
6. Android native shell.
7. Android NDK title-library fixture.
8. Per-title APK builder.
9. First private vertical slice.
10. Compatibility and performance hardening.

Each prompt below is designed to create a reviewable change with tests and a clear exit condition.

---

## 2. Files to provide to Codex

Place these documents in the repository or attach them to the Codex task:

- `00_README.md`
- `01_3DS_RECOMPILATION_TECHNICAL_OVERVIEW.md`
- `02_SPEC_3DS_NATIVE_RECOMP_RUNTIME.md`
- `03_EXISTING_PROJECTS_AND_GAP_MATRIX.md`
- `04_REFERENCES.md`
- `06_IMPLEMENTATION_BACKLOG.md`
- `07_UBERHAR_RELATIONSHIP_AND_MIGRATION.md`

Tell Codex that the SPEC is normative and the overview/gap matrix are explanatory.

---

## 3. Global instructions to prepend to every Codex task

Copy this block into every implementation prompt.

```text
You are working on 3DS-NRR, a clean-room, open-source integration project that combines the existing fearkov/3dsrecomp AOT toolchain with the existing fearkov/zakuro HLE runtime and graphics stack. Read SPEC-3DS-NRR-001 and the repository's architecture/reference documents before editing code.

Non-negotiable constraints:

1. Do not implement a new ARM11 interpreter, HLE kernel, PICA renderer, shader compiler, or static recompiler when the pinned upstream projects already provide the behavior.
2. Preserve interpreter fallback, code-origin validation, the generic PICA graphics fallback, and asynchronous specialized-pipeline compilation.
3. Do not add or request retail ROMs, CIA/CCI/NCCH contents, firmware, keys, title-derived generated source, title-derived objects/shared libraries, saves, or copyrighted assets to source control, CI, logs, or test fixtures.
4. Public tests must use synthetic code or legally distributable homebrew fixtures.
5. Do not download executable title modules at runtime. The v1 Android design is a locally built, sideloaded, per-title APK.
6. Inspect licenses before copying code. Publicly visible code is not automatically compatible. Do not submit AI-generated contributions to projects whose contribution policy disallows them.
7. Do not introduce Google Play Services, account login, analytics, cloud services, mandatory vendor APIs, PRoot, X11, VirGL, or a persistent background service as a correctness dependency.
8. Avoid broad rewrites. Make the smallest change that proves the task.
9. Add or update tests for behavior changes. If a task is scaffolding-only, explicitly state why no behavioral test is possible yet.
10. Any unsafe Rust/C/C++ code must document its invariants at the boundary.
11. Logs and caches must be bounded; do not create redundant session bundles.
12. Do not use fast-math or compiler options that can alter guest floating-point semantics. Preserve the upstream -ffp-contract=off requirement or its exact equivalent.

Before editing:
- identify the exact pinned commits and current ABI version;
- map the existing implementation relevant to the task;
- state which existing code will be reused;
- identify license implications;
- list the concrete acceptance tests.

At completion report:
- requirement/backlog IDs addressed;
- files changed;
- design decisions;
- commands run;
- test output;
- performance/correctness evidence;
- unresolved assumptions;
- any generated/private paths that must stay gitignored;
- the smallest recommended next task.

Do not claim success unless the relevant command/test actually ran. If the environment prevents a test, leave the code in a buildable state where possible and state the exact blocker.
```

---

## 4. Master context prompt

Use this once at the beginning of a new Codex session. It is context, not permission to implement every milestone at once.

```text
Project goal:

Create a native Android ARM64 product around fearkov/3dsrecomp and fearkov/zakuro. A desktop builder validates a user-owned supported 3DS dump, uses 3dsrecomp to produce C, cross-compiles the generated code with Android NDK Clang into libnrr_title.so, packages that library with a generic runtime into a locally signed per-title APK, and imports/validates the matching title data at first run. At runtime, native AOT code executes through the upstream recomp-abi; unknown, unsupported, or modified code falls back to Zakuro's interpreter. Zakuro supplies the HLE kernel/services/filesystem/audio/PICA runtime. The existing Zakuro dynamic PICA pipeline must render immediately while specialized Vulkan pipelines compile asynchronously.

Primary architectural decision:
- Zakuro-first; do not begin by integrating into Azahar.
- Linux desktop is the golden/reference host.
- Android/Bionic is the primary deployment target.
- v1 produces a per-title local APK and does not target Google Play.

Expected upstream research pins:
- 3dsrecomp: c3f21f94ba50d688025febc8974ff348d471b587
- Zakuro: 412900a5a020301da15c1cc382585e05a489a535
Verify these before relying on them.

Read and obey:
- 02_SPEC_3DS_NATIVE_RECOMP_RUNTIME.md
- 03_EXISTING_PROJECTS_AND_GAP_MATRIX.md
- 04_REFERENCES.md
- 06_IMPLEMENTATION_BACKLOG.md
- 07_UBERHAR_RELATIONSHIP_AND_MIGRATION.md (when working in the RegiRex project context)

Your first response must not edit code. Produce:
1. repository/workspace map;
2. current upstream commit and ABI verification;
3. build dependency map;
4. relevant files/functions for CPU loading, interpreter fallback, PICA dynamic/specialized pipelines, pipeline cache, frontend/windowing, input, and audio;
5. Android portability blockers;
6. license inventory;
7. testable milestone plan;
8. the single smallest first code change.
```

---

# Prompt sequence

## Prompt 0 — Repository reconnaissance and implementation map

```text
Task: Perform repository reconnaissance only. Do not modify code.

Inspect the checked-out/pinned 3dsrecomp and Zakuro source trees and produce docs/reconnaissance-YYYY-MM-DD.md with:

1. exact commit SHAs, branches, and dirty status;
2. exact recomp-abi version and exported symbols;
3. 3dsrecomp flow from input parsing through code discovery, C generation, object compilation, shared-library linking, and verification;
4. Zakuro flow from title boot through CPU dispatch, native-entry lookup, interpreter fallback, SVC exit, CRO loading, and scheduler return;
5. exact files/functions implementing the dynamic PICA fallback, specialized pipeline creation, background compilation, and disk pipeline cache;
6. all desktop-only dependencies in Zakuro, grouped by windowing, input, audio, filesystem, process/loading, and Vulkan surface creation;
7. crates/modules that can compile without a desktop frontend;
8. current tests and missing tests relevant to the SPEC;
9. current licenses and third-party dependencies;
10. a dependency graph for a minimal headless runtime;
11. concrete Android blockers ranked by difficulty; and
12. the smallest next task that can be completed with synthetic fixtures only.

Acceptance criteria:
- Every architectural statement points to an exact source file and symbol.
- No unsupported claim is presented as fact.
- No code is changed.
- The document distinguishes observed behavior from recommendations.
```

## Prompt 1 — Workspace scaffold and pinned upstreams

```text
Task: Create the reproducible project scaffold described by M0 / EPIC-00.

Implement only:
- top-level workspace/build files;
- upstream pin mechanism (submodules, locked fetch script, or another documented reproducible method);
- pins/runtime.lock containing exact SHAs and ABI expectations;
- LICENSES and THIRD_PARTY_NOTICES scaffolding;
- private/generated artifact .gitignore rules;
- a public synthetic-fixture directory;
- a script/command that verifies upstream SHAs and fails if they drift;
- a CI job that builds generic tools without retail title data.

Do not add Android UI or change guest behavior.

Acceptance tests:
1. clean clone + documented initialization obtains the exact upstream commits;
2. pin verification passes on the expected commits and fails after a simulated mismatch;
3. repository scan confirms common retail/generated extensions and local signing keys are ignored;
4. CI does not need ROMs, firmware, keys, or network downloads beyond declared dependencies;
5. license report names every directly distributed component.
```

## Prompt 2 — Desktop golden harness

```text
Task: Build a Linux desktop golden harness around the pinned upstream stack using only synthetic/homebrew fixtures in automated tests.

Deliver:
- a headless or minimal frontend command that can initialize Zakuro core;
- a synthetic recomp-abi shared library generated by 3dsrecomp or a purpose-built legal fixture;
- native-entry execution through the actual ABI;
- interpreter-only mode;
- forced unknown-entry fallback;
- forced unsupported-instruction callback;
- forced SVC exit;
- machine-readable execution counters;
- deterministic checkpoint output for the synthetic fixture.

Do not build Android yet.

Acceptance tests:
- native and interpreter modes reach identical final fixture state;
- an unknown entry uses the interpreter without crashing;
- an unsupported instruction uses the host callback and resumes or exits as expected;
- SVC returns to HLE host control;
- coverage counters distinguish native and interpreter execution;
- no retail data is used.
```

## Prompt 3 — Origin invalidation and CRO fixture

```text
Task: Add regression tests for code-origin validation and relocatable CRO-style modules.

Use the real upstream ABI mechanisms. Do not invent a separate invalidation system.

Deliver:
- a synthetic module with relative entries loaded at two guest base addresses;
- a test proving native entry lookup works at both bases;
- a test modifying origin bytes and proving native code is rejected/falls back;
- bounded structured events for fallback reason;
- documentation of the upstream metadata used.

Acceptance tests:
- both module bases produce identical guest-visible output;
- stale bytes never execute the old native function;
- fallback reason is visible in counters/logs;
- release mode can disable verbose event payloads without changing behavior.
```

## Prompt 4 — Graphics no-stall instrumentation

```text
Task: Instrument the existing Zakuro Vulkan renderer to prove and measure its generic-dynamic-pipeline plus asynchronous-specialization behavior. Do not rewrite the renderer.

Deliver:
- counters for specialized hit, generic fallback, compile queued, compile completed, compile failed, and driver-cache hit where observable;
- timestamps/durations for compile jobs in debug/performance builds;
- a debug option to force all specialized pipelines cold while keeping the generic path available;
- a synthetic PICA state sequence that triggers multiple specialization keys;
- a test/assertion that the emulation thread does not wait for the compile worker;
- bounded log output;
- documentation pointing to the existing DYNAMIC shader path.

Acceptance criteria:
- a cold synthetic run draws through the generic path while jobs are outstanding;
- specialized pipelines are used after completion;
- forced compile failure retains generic rendering;
- no unbounded retries occur;
- all instrumentation can be disabled or sampled in release builds.
```

## Prompt 5 — Generic versus specialized parity tests

```text
Task: Create a GPU conformance suite comparing Zakuro's generic PICA fragment path against its specialized path.

Cover a bounded but extensible matrix:
- all six TEV stages and buffer updates;
- source/operand/combine/scale variants;
- texture units and representative formats/sampling modes;
- fragment lighting enable/disable and representative LUT paths;
- fog;
- alpha test;
- depth/stencil;
- blend and logic operation;
- write masks;
- representative render-target/depth formats.

Use synthetic, legally distributable inputs. Prefer offscreen rendering and image/hash comparison.

Acceptance criteria:
- test vectors are deterministic;
- tolerances are documented per format/path;
- every mismatch prints the normalized PICA state/key needed to reproduce it;
- the test can run generic-only and specialized-only;
- failures do not silently update golden output.
```

## Prompt 6 — Audit and harden pipeline cache

```text
Task: Audit the existing Zakuro Vulkan pipeline-cache implementation against CACHE-001 through CACHE-010.

First document current behavior. Then implement only missing safety needed for:
- device/driver fingerprinting including pipeline cache UUID;
- runtime/key-schema versioning;
- atomic writes;
- corruption recovery;
- size quota;
- explicit clear command;
- human-readable cache manifest.

Do not claim the opaque Vulkan cache is portable.

Acceptance tests:
- same fingerprint reloads a valid cache;
- changed UUID/driver/runtime schema invalidates it;
- truncated/corrupt cache is discarded without crash;
- simulated crash during write preserves either old or new valid state;
- quota/clear operations work;
- no game data or raw guest memory is included in the manifest.
```

## Prompt 7 — Portable pipeline journal

```text
Task: Add a portable, versioned pipeline recipe journal distinct from VkPipelineCache.

The journal should record normalized PICA pipeline keys, usage counts, and enough non-opaque metadata to request specialization again. It must not assume device-specific pipeline binary portability.

Requirements:
- title/content/runtime/translator identity in header;
- bounded, checksummed records;
- atomic updates;
- schema version;
- no raw copyrighted assets;
- prewarm ordering by observed frequency/recency;
- background-only prewarm by default;
- cancel/pause under app background or thermal policy;
- metrics for requested/completed/failed prewarm jobs.

Acceptance tests:
- cold run creates journal;
- second run replays keys without blocking title boot;
- schema/content identity change invalidates or migrates safely;
- corrupt records are skipped/discarded safely;
- generic fallback remains available during prewarm.
```

## Prompt 8 — Android native shell skeleton

```text
Task: Create the minimal native Android shell for the generic runtime. Do not import a retail title and do not integrate the full emulator in one change.

Deliver:
- Gradle project targeting arm64-v8a;
- documented minimum SDK decision;
- JNI or NativeActivity boundary with a small versioned API;
- Vulkan instance/device/surface creation using SurfaceView/ANativeWindow;
- clear-frame or synthetic renderer;
- Activity pause/resume and surface destroy/recreate handling;
- Android gamepad event bridge;
- touch coordinate bridge;
- AAudio or Oboe test-tone/ring-buffer path;
- app-private directories for config/cache/log/save test data;
- no Google Play Services dependency.

Acceptance tests:
- APK builds and installs;
- presents frames on a physical/emulated ARM64 Android environment;
- repeated rotation/surface recreation does not crash;
- pause/resume does not deadlock;
- controller/touch events arrive in native test code;
- audio starts/stops safely;
- app works offline.
```

## Prompt 9 — Android build of Zakuro core

```text
Task: Build the pinned Zakuro core and required GPU/runtime crates for Android/Bionic behind the Android shell.

Do not start title execution yet.

Work method:
1. identify and isolate desktop-only dependencies;
2. introduce platform traits/adapters rather than Android checks throughout guest code;
3. compile the core for aarch64-linux-android;
4. initialize guest memory, kernel core, GPU core, and cache paths using a synthetic boot fixture;
5. render a synthetic PICA frame through the actual Zakuro Vulkan backend if feasible.

Acceptance criteria:
- Android build uses the same core code as desktop;
- no PRoot/X11/VirGL/ALSA dependency;
- surface and app lifecycle are owned by the Android adapter;
- desktop build and tests remain green;
- synthetic fixture presents through the Zakuro renderer or the exact remaining blocker is isolated in one subsystem.
```

## Prompt 10 — Android NDK cross-compile fixture for `3dsrecomp`

```text
Task: Add an explicit Android-NDK toolchain mode to the local 3dsrecomp integration and generate a synthetic libnrr_title.so.

Requirements:
- configurable NDK path/version and API level;
- aarch64-linux-android Clang and llvm-ar discovery;
- PIC/shared-library output;
- -ffp-contract=off;
- no fast-math;
- hidden visibility except required ABI exports;
- build report with compiler/flags/hashes;
- symbol validation;
- Android loader smoke test.

Do not use a retail title.

Acceptance tests:
- synthetic generated C compiles to an arm64-v8a ELF shared object;
- readelf/llvm-readobj confirms expected architecture and exported ABI;
- Android test app loads it and executes a known entry;
- interpreter callback and SVC exit cross the JNI/native runtime correctly;
- invalid ABI version is rejected with a clear error.
```

## Prompt 11 — Per-title APK template and local builder

```text
Task: Implement the local per-title APK packaging pipeline using the synthetic title library first.

Deliver:
- versioned TitleManifest schema;
- deterministic package ID derived from title ID for real builds and fixture ID for tests;
- packaging under lib/arm64-v8a/;
- local debug signing and optional user key;
- build report;
- ADB install helper;
- first-run input-selection/identity-validation UI using Storage Access Framework;
- mismatch rejection;
- gitignore/private output enforcement.

Acceptance tests:
- synthetic fixture produces a signed installable APK;
- APK contains only declared generic runtime and fixture native libraries;
- manifest mismatch prevents native execution;
- signing key remains local;
- no executable code is downloaded at runtime;
- public CI builds fixture APK only.
```

## Prompt 12 — Full runtime vertical slice with private user data

```text
Task: Prepare the code path for a privately supplied, legally dumped, upstream-supported 3DS title. Do not commit, upload, print, or embed any title-derived data or generated code.

The human operator will provide local paths through environment/config values outside source control.

Deliver:
- builder import/validation using upstream-supported input formats;
- 3dsrecomp code generation and NDK compile;
- per-title APK packaging;
- first-run matching-data import;
- runtime native library load;
- interpreter fallback counters;
- input/audio/save/graphics path;
- cold/warm pipeline report;
- crash-safe bounded log.

Acceptance evidence must contain only hashes, counts, timings, and non-copyrighted diagnostics. Do not include disassembly, generated C, shader binaries, asset names beyond what is necessary, screenshots without human approval, or memory dumps.

Exit criteria:
- reaches a predefined gameplay checkpoint;
- saves and reloads;
- reports native coverage;
- demonstrates generic fallback on cold pipeline misses;
- demonstrates safe cache reuse on warm run;
- survives pause/resume;
- generated outputs remain in ignored private paths.
```

## Prompt 13 — Android device matrix runner

```text
Task: Build a local device-runner tool for repeatable Android tests.

Input:
- APK path;
- device serial;
- scenario ID;
- cache state (clean, journal-only, warm);
- duration/checkpoint;
- optional performance profile.

Collect only:
- runtime/build/title hashes;
- device model/SoC/GPU/OS/Vulkan/driver identifiers;
- frame-time aggregates/percentiles;
- native/interpreter coverage;
- generic/specialized draw counts;
- compile queue metrics;
- audio underruns;
- memory totals;
- thermal status through standard APIs where available;
- crash/exit status.

Acceptance criteria:
- does not require vendor-specific tools for basic operation;
- outputs JSON and a concise Markdown report;
- distinguishes cold and warm cache states;
- redacts personal device paths/identifiers;
- cleans only project-owned data when requested.
```

## Prompt 14 — Lean crash diagnostics

```text
Task: Implement bounded crash-safe diagnostics consistent with OBS-001 through OBS-006.

Deliver:
- fixed-size ring of subsystem/event IDs and monotonic timestamps;
- last native PC/guest PC/fallback reason where safe;
- last pipeline key hash, not raw copyrighted shader data;
- last lifecycle/audio/surface events;
- atomic minimal crash marker;
- next-launch human-readable report assembly;
- explicit user export/share action;
- size rotation/quota.

Do not create automatic per-session bundles. Do not upload anything.

Acceptance tests:
- forced crash leaves a parseable marker;
- marker is bounded and contains no guest memory or title assets;
- normal launch clears/archives according to policy;
- repeated crashes do not grow storage without bound.
```

## Prompt 15 — Upstream rebase procedure

```text
Task: Document and automate a controlled rebase/update of pinned 3dsrecomp and Zakuro.

Deliver:
- command that fetches candidate SHAs without changing lock;
- ABI/source change report;
- license/dependency diff;
- build/test matrix;
- cache-schema impact check;
- explicit lock update only after tests pass;
- rollback path.

Acceptance criteria:
- candidate update cannot silently alter pins;
- ABI mismatch is detected;
- desktop synthetic suite, GPU parity suite, Android fixture, and private-title tests are listed as gates;
- generated/private artifacts remain untouched.
```

---

## 5. Optional future prompts

These should not be used until v1 acceptance criteria are met.

### Optional A — Azahar AOT backend feasibility

```text
Perform a feasibility study only for adding 3dsrecomp/recomp-abi as an optional CPU backend to Azahar. Do not write integration code yet.

Map:
- Azahar CPU state and memory interfaces;
- Dynarmic/interpreter dispatch;
- SVC/scheduler boundaries;
- CRO loading;
- code invalidation;
- Android native loader;
- Rust/C++ ABI options;
- GPL/license implications;
- expected maintenance cost.

Produce a go/no-go ADR and a minimal proof plan.
```

### Optional B — Game-specific native renderer

```text
For one privately supplied title, profile the general PICA renderer and identify whether a native game-specific renderer is justified. Do not implement it until the report identifies measurable bottlenecks and a bounded draw/API mapping.

Compare:
- general generic path;
- specialized PICA path;
- potential AOT shader/state extraction;
- title rendering architecture;
- expected portability and maintenance cost;
- legal boundaries for local generated data.
```

### Optional C — On-device builder

```text
Study, but do not initially implement, a sideload-only on-device AOT builder. Evaluate toolchain size, build duration, RAM, heat, storage, Android executable-code restrictions, linker behavior, and recovery UX. Compare it against the desktop builder and recommend whether it should exist.
```

---

## 6. Task template for ordinary tickets

```text
Task ID: <BACKLOG-ID>
SPEC requirements: <IDs>
Goal: <one bounded outcome>

Existing implementation to inspect:
- <repo/file/symbol>

Changes allowed:
- <specific modules>

Changes forbidden:
- no guest semantic rewrite outside the named behavior
- no removal of fallback paths
- no retail/private artifacts
- no unbounded logging/cache

Required tests:
1. ...
2. ...
3. ...

Required evidence:
- commands/output
- before/after behavior or metric
- license review if code moved/copied

Done when:
- ...
```

---

## 7. Review prompt after every Codex change

Use a separate review pass, preferably a fresh agent/context.

```text
Review this change against SPEC-3DS-NRR-001. Do not make edits in the first response.

Check:
1. Did it reuse existing upstream behavior or unnecessarily reimplement it?
2. Does it preserve interpreter and generic GPU fallbacks?
3. Could it execute stale generated code?
4. Could it block the emulation thread on pipeline compilation?
5. Are cache identities and writes safe?
6. Are Android lifecycle and thread boundaries safe?
7. Is any guest-controlled length/address used unsafely?
8. Did any title-derived/private material enter the diff, fixtures, logs, or artifacts?
9. Are licenses compatible and notices preserved?
10. Are tests meaningful and actually run?
11. Are claims supported by output?
12. Is the change smaller than necessary or broader than the ticket?

Return:
- blocking findings;
- nonblocking findings;
- missing tests;
- exact files/lines involved;
- approve/reject recommendation.
```

---

## 8. Debugging prompt format

```text
Investigate this failure without first changing code.

Observed environment:
- runtime SHA:
- 3dsrecomp SHA:
- recomp ABI:
- Android/device/GPU/driver:
- title manifest hash (no title content):
- cache state:
- execution mode:

Observed behavior:
- exact error/event IDs:
- first bad checkpoint:
- native/interpreter coverage:
- generic/specialized counts:

Tasks:
1. classify as CPU AOT, interpreter/HLE, memory, CRO, PICA state, shader/pipeline, surface/lifecycle, audio, filesystem, or packaging;
2. identify the smallest trace or synthetic reproduction;
3. compare native and interpreter modes;
4. compare generic and specialized GPU paths;
5. identify whether clearing only the relevant cache changes behavior;
6. propose one diagnostic patch, not a speculative rewrite.

Do not request or print game code/assets. Use hashes, event IDs, register/state summaries, and bounded traces.
```

---

## 9. Codex anti-patterns to reject

Reject or redirect a Codex response that proposes any of the following without strong evidence:

- “Rewrite Zakuro in C++ for Android.”
- “Replace the existing PICA renderer with a new renderer.”
- “Remove the interpreter because AOT coverage is high.”
- “Compile every possible shader/pipeline ahead of time.”
- “Download the generated `.so` from a server.”
- “Bundle a test ROM/firmware/key in CI.”
- “Use PRoot/X11 as the final Android product.”
- “Depend on an AYN/Qualcomm private performance API for correctness.”
- “Disable synchronization/accuracy globally to improve speed.”
- “Use fast-math.”
- “Store only the opaque Vulkan cache and call it portable.”
- “Log full guest memory or generated shader binaries.”
- “Make one huge change touching CPU, GPU, frontend, and builder at once.”
- “Claim success from compilation alone when runtime behavior is the task.”

---

## 10. Best first prompt to run

After placing this pack in a repository, use exactly this:

```text
Read 00_README.md through 06_IMPLEMENTATION_BACKLOG.md. Follow the Global Instructions in 05_CODEX_PROMPT_PACK.md.

Perform Prompt 0 — Repository reconnaissance and implementation map. Do not modify code. Verify the expected upstream pins, locate the actual recomp ABI and Zakuro generic/specialized pipeline implementation, identify Android portability blockers, and write docs/reconnaissance-2026-10-17.md. Finish by proposing only the smallest synthetic-fixture task from EPIC-00 or EPIC-01.
```

That prompt forces Codex to understand the existing solution before it begins coding.

---

# Part 7 — Implementation backlog

> Source file: `06_IMPLEMENTATION_BACKLOG.md`

# 3DS Native Recompilation Runtime — Implementation Backlog

**Prepared:** 2026-10-17  
**Applies to:** `3DS-NRR` architecture in `02_SPEC_3DS_NATIVE_RECOMP_RUNTIME.md`  
**Primary route:** pinned `3dsrecomp` + pinned Zakuro, Linux reference host first, Android ARM64 second  
**Initial distribution:** locally built, sideloaded, per-title APK

## 1. How to use this backlog

This backlog is intended to be copied into GitHub Issues, a project board, or an agent task queue. Each ticket is deliberately narrower than a milestone. Codex should receive one ticket at a time, together with:

- the relevant SPEC requirement IDs;
- the exact upstream commit pins;
- the repository map produced during reconnaissance;
- the current test report;
- the legal boundary that no retail game material or generated retail title code may enter source control or CI; and
- an instruction to stop after the stated acceptance criteria are met.

### Priority labels

| Label | Meaning |
|---|---|
| `P0` | Blocks every later milestone or protects correctness/legal safety. |
| `P1` | Required for the first playable Android vertical slice. |
| `P2` | Required for v1 quality, compatibility, or maintainability. |
| `P3` | Post-v1 enhancement or exploratory optimization. |

### Work-type labels

`research`, `build`, `cpu`, `hle`, `gpu`, `cache`, `android`, `audio`, `input`, `tooling`, `testing`, `security`, `legal`, `performance`, `documentation`, `release`

### Ticket completion report

Every ticket must end with a machine-readable or Markdown report containing:

1. upstream commit pins used;
2. files added, removed, and modified;
3. commands run;
4. tests passed and failed;
5. artifacts generated;
6. measured behavior before and after, when applicable;
7. assumptions that remain unverified;
8. legal or licensing implications;
9. regressions or known limitations; and
10. the smallest safe next ticket.

A ticket is not complete merely because the code compiles.

---

# EPIC 00 — Governance, legal boundary, and repository scaffold

**Goal:** Create a repository that can be developed publicly without committing copyrighted title material, generated retail code, keys, firmware, or opaque unreviewed binaries.

**SPEC coverage:** `M0`, `REP-001`, `REP-002`, `SEC-007`, `SEC-008`, `LEG-001` through `LEG-007`, `TEST-015`

## NRR-0001 — Create repository layout

**Priority:** P0  
**Type:** `build`, `documentation`

Create the directory structure from SPEC section 8, or document any justified variation in an ADR.

**Deliverables**

- `upstream/3dsrecomp/` or an equivalent pinned dependency mechanism;
- `upstream/zakuro/` or equivalent;
- `host/linux/`;
- `host/android/`;
- `builder/`;
- `tests/`;
- `docs/adr/`;
- `tools/`;
- `third_party/` or a generated dependency-notice workflow;
- `private/` and `generated/` paths excluded from source control.

**Acceptance criteria**

- A clean clone contains no game-derived files.
- The top-level README explains which directories may contain private local artifacts.
- A fresh contributor can identify where Linux, Android, builder, shared runtime, and tests live.

## NRR-0002 — Pin upstream repositories and record provenance

**Priority:** P0  
**Type:** `build`, `documentation`, `security`

Pin the two central repositories to reviewed commits. Initial research pins are:

- `3dsrecomp`: `c3f21f94ba50d688025febc8974ff348d471b587`
- Zakuro: `412900a5a020301da15c1cc382585e05a489a535`

**Deliverables**

- immutable pin mechanism;
- `UPSTREAM_PINS.md` with repository, commit, date, license, local patches, and update procedure;
- script that verifies the checked-out commit IDs;
- patch directories separated by upstream project.

**Acceptance criteria**

- CI fails if an upstream checkout differs from the declared pin.
- Local patches apply cleanly from a fresh clone.
- No vendored changes are left unattributed.

## NRR-0003 — Add legal and contribution policy

**Priority:** P0  
**Type:** `legal`, `documentation`

**Deliverables**

- `LEGAL.md`;
- `CONTRIBUTING.md`;
- issue/PR templates warning against attaching ROMs, keys, firmware, save states with embedded code, generated retail source, generated title libraries, or copyrighted assets;
- takedown/removal procedure for accidental uploads;
- instructions for legally dumping and using material limited to neutral ownership language, without acquisition links or circumvention instructions.

**Acceptance criteria**

- The policy distinguishes project source from locally generated title artifacts.
- The policy says generated title `.c`, `.o`, `.so`, APK, extracted assets, and traces containing code bytes must not be uploaded.
- Contribution templates require submitters to confirm their changes contain no prohibited material.

## NRR-0004 — Create deny rules for private/generated material

**Priority:** P0  
**Type:** `legal`, `security`, `testing`

**Deliverables**

- comprehensive `.gitignore`;
- pre-commit scanner for known private directories, ROM/container extensions, keys, generated shared libraries, APKs, dumps, and large unexplained binaries;
- CI scanner using allowlists for intentional fixtures;
- test proving the scanner rejects seeded prohibited examples.

**Acceptance criteria**

- CI implements `TEST-015`.
- False-positive exceptions require an explicit, reviewed allowlist entry.
- Scanner output identifies the offending path without printing private file contents.

## NRR-0005 — Produce third-party license inventory

**Priority:** P0  
**Type:** `legal`, `build`, `documentation`

**Deliverables**

- license inventory for Zakuro, `3dsrecomp`, Rust crates, Android dependencies, shader tools, and copied/reference code;
- generated `THIRD_PARTY_NOTICES.md` where feasible;
- license compatibility note for every planned source reuse;
- distinction between reading a project as a behavioral reference and copying its code.

**Acceptance criteria**

- Every vendored or linked component has a source URL, version/pin, and license.
- GPL components are not silently copied into an MIT-only subtree.
- Release packaging includes required notices.

## NRR-0006 — Establish ADR framework

**Priority:** P1  
**Type:** `documentation`

Create ADRs for at least:

1. Zakuro-first architecture;
2. Linux-first reference path;
3. per-title APK distribution;
4. upstream pinning and patch policy;
5. CPU AOT plus interpreter fallback;
6. dynamic PICA fallback plus specialization;
7. portable recipe journal versus device-specific Vulkan cache;
8. Android process and native-library loading model.

**Acceptance criteria**

- Each ADR states context, decision, alternatives, consequences, and reversal trigger.
- Later code changes cite the applicable ADR when changing architecture.

---

# EPIC 01 — Reproducible build system and source map

**Goal:** Make the pinned upstream stack build reproducibly and give Codex a reliable map of subsystem ownership before feature work.

**SPEC coverage:** `DEC-002`, `DEC-003`, `REP-001`, `REP-002`, `BL-005`, `BL-008`, `PERF-007`, `M1`

## NRR-0101 — Generate repository reconnaissance report

**Priority:** P0  
**Type:** `research`, `documentation`

Run the reconnaissance prompt from `05_CODEX_PROMPT_PACK.md` against the actual checkout.

**Deliverables**

- source map for CPU execution, HLE, memory, CRO, GPU, pipeline cache, audio, input, frontend, logging, and build code;
- call-flow diagrams for title launch and first draw;
- inventory of existing tests;
- inventory of platform assumptions that block Android/Bionic;
- exact locations of upstream dynamic fallback and specialized pipeline logic.

**Acceptance criteria**

- Every subsystem has an owner directory/file list.
- The report identifies where `recomp-abi` is loaded and where interpreter fallback occurs.
- No implementation changes are included in this ticket.

## NRR-0102 — Create hermetic developer bootstrap

**Priority:** P0  
**Type:** `build`, `tooling`

**Deliverables**

- pinned Rust toolchain setup;
- supported C/C++ compiler checks;
- CMake/Ninja/SDK checks where needed;
- one bootstrap command for Linux;
- optional container/devcontainer that contains no proprietary SDK or game material;
- version report saved with build artifacts.

**Acceptance criteria**

- A clean supported Linux environment can build the public source without private material.
- Tool versions are printed and captured.
- Missing dependencies produce actionable errors.

## NRR-0103 — Build pinned `3dsrecomp`

**Priority:** P0  
**Type:** `build`, `cpu`

**Acceptance criteria**

- Debug and release builds succeed.
- Unit tests succeed.
- `--help` or equivalent smoke invocation succeeds.
- Build output records the source commit and compiler versions.

## NRR-0104 — Build pinned Zakuro

**Priority:** P0  
**Type:** `build`, `hle`, `gpu`

**Acceptance criteria**

- Debug and release builds succeed on Linux.
- Existing test suite succeeds or every existing failure is documented as pre-existing.
- Vulkan and software/reference renderer build options are identified.
- Build output records the source commit and dependency lock state.

## NRR-0105 — Add top-level build orchestration

**Priority:** P0  
**Type:** `build`, `tooling`

Provide a single command interface such as:

```text
./nrr configure
./nrr build --host linux --profile release
./nrr test --suite public
./nrr doctor
```

**Acceptance criteria**

- Commands delegate to upstream build systems rather than duplicating them unnecessarily.
- `doctor` checks host, compiler, Vulkan loader, writable paths, and upstream pins.
- Failure preserves complete logs in a predictable location.

## NRR-0106 — Create public synthetic/homebrew fixtures

**Priority:** P0  
**Type:** `testing`, `cpu`, `hle`, `gpu`

Create or select redistributable fixtures that exercise:

- ARM and Thumb control flow;
- VFP arithmetic and edge cases;
- SVC transition;
- indirect branch/lookup;
- CRO-like loading where legally practical;
- PICA command submission;
- at least two TEV combinations;
- texture upload;
- audio callback;
- save/file I/O.

**Acceptance criteria**

- Fixture licenses permit inclusion.
- Expected outputs are deterministic.
- No Nintendo SDK or retail-derived content is included.

## NRR-0107 — Add build provenance manifest

**Priority:** P1  
**Type:** `build`, `security`, `documentation`

**Deliverables**

- JSON manifest containing repository pins, dirty state, compiler versions, flags, target ABI, dependency lock hashes, and build timestamp policy;
- embed a short build ID into Linux and Android hosts;
- command to print full provenance.

**Acceptance criteria**

- A bug report can identify the exact source and toolchain used.
- Dirty builds are visibly marked.

---

# EPIC 02 — Linux golden reference harness

**Goal:** Prove the architecture on the most observable host before Android work and establish deterministic correctness/performance baselines.

**SPEC coverage:** `DEC-003`, `CPU-001` through `CPU-015`, `HLE-003`, `OBS-001` through `OBS-006`, `TEST-001` through `TEST-014`, `M1`

## NRR-0201 — Implement title identity inspection

**Priority:** P0  
**Type:** `tooling`, `security`

Inspect a user-provided title locally and emit the manifest fields from SPEC section 18 without retaining or uploading title bytes.

**Acceptance criteria**

- Computes cryptographic hashes for the complete input and relevant executable/modules.
- Reports title ID, format, region/revision where available, and encryption/decryption status.
- Refuses unsupported or malformed input with bounded parsing and clear errors.
- Does not print keys or raw executable bytes.

## NRR-0202 — Build one private known-compatible title locally

**Priority:** P0  
**Type:** `cpu`, `build`, `testing`

This is a local-only validation task. No generated output may enter Git, CI, issue attachments, or release artifacts.

**Acceptance criteria**

- `3dsrecomp` creates a native shared library.
- The library exposes the expected `recomp-abi` symbols.
- Origin hashes match the input used to create it.
- Build report records native coverage and fallback sites.
- Generated material remains under an ignored private directory.

## NRR-0203 — Instrument native versus interpreter execution

**Priority:** P0  
**Type:** `cpu`, `observability`

Add bounded counters and optional traces for:

- native entry invocations;
- interpreted instructions;
- lookup misses;
- stale-origin fallback;
- SVC exits;
- budget exits;
- unwind/depth exits.

**Acceptance criteria**

- Default mode records aggregate counts with negligible overhead.
- Detailed tracing is opt-in and bounded.
- A private title run proves both native execution and fallback execution.
- Metrics satisfy `CPU-013` and do not expose title code bytes by default.

## NRR-0204 — Create deterministic execution mode

**Priority:** P0  
**Type:** `cpu`, `hle`, `testing`

Control or virtualize time, random seeds, thread scheduling inputs, and nondeterministic host data enough to reproduce defined checkpoints.

**Acceptance criteria**

- Public fixture reaches identical checkpoint hashes across at least three runs.
- Deterministic mode is clearly separate from normal real-time mode.
- Sources of remaining nondeterminism are enumerated.

## NRR-0205 — Add CPU differential verification command

**Priority:** P0  
**Type:** `cpu`, `testing`

Wrap or extend `3dsrecomp verify`/Zakuro comparison so a developer can verify selected functions, ranges, or checkpoints.

**Acceptance criteria**

- Compares registers, flags, VFP state, memory effects, exit reason, and next PC.
- Mismatch report gives the smallest useful location without dumping copyrighted blocks by default.
- Public fixture has a passing verification test.

## NRR-0206 — Add stale-origin and modified-code test

**Priority:** P0  
**Type:** `cpu`, `testing`, `security`

**Acceptance criteria**

- Mutating a fixture code piece causes the corresponding generated function to be marked stale.
- Lookup skips stale generated entries.
- Interpreter path executes the modified region.
- Unmodified functions remain native.

## NRR-0207 — Add CRO load/unload/relocation test

**Priority:** P0  
**Type:** `cpu`, `hle`, `testing`

**Acceptance criteria**

- A module can be loaded at more than one valid base in separate runs.
- Relative entry lookup works.
- Cross-module calls work.
- Unload clears the module base and invalidates lookups.
- Re-load does not retain stale state.

## NRR-0208 — Create deterministic trace format

**Priority:** P1  
**Type:** `observability`, `testing`

Define a versioned trace/checkpoint format containing only the state needed for regression comparison.

**Acceptance criteria**

- Schema version and build provenance are included.
- Trace is bounded and can be redacted/exported.
- Comparison tool highlights first divergence.
- Retail instruction bytes are excluded unless a user explicitly enables a private local diagnostic mode.

## NRR-0209 — Establish cold/warm performance benchmark

**Priority:** P1  
**Type:** `performance`, `testing`

Measure:

- launch to first frame;
- frame-time percentiles;
- native coverage;
- interpreter count;
- generic-pipeline draw count;
- specialization completion times;
- pipeline cache hits/misses;
- CPU/GPU wait times;
- memory high-water mark.

**Acceptance criteria**

- Benchmark distinguishes cold, second-run, and warmed-cache states.
- Results include host/device fingerprint and build ID.
- No benchmark result is accepted without raw sample count and run conditions.

## NRR-0210 — Add crash-safe session log

**Priority:** P1  
**Type:** `observability`, `testing`

Follow the lean logging philosophy already established for Uberhar: normal logs remain bounded; a crash marker and compact crash-only record may be written without creating redundant in-app bundles.

**Acceptance criteria**

- Current and previous incomplete sessions can be distinguished.
- Log finalization is atomic.
- Crash record contains build, title hash, last bounded events, renderer path, and cache state.
- No automatic upload or mandatory network service exists.

---

# EPIC 03 — CPU AOT portability and Android cross-target

**Goal:** Preserve upstream CPU semantics while producing Android-compatible ARM64 native libraries from locally owned inputs.

**SPEC coverage:** `BL-006` through `BL-009`, `CPU-001` through `CPU-015`, `SEC-002`, `M4`

## NRR-0301 — Audit generated C for target assumptions

**Priority:** P0  
**Type:** `cpu`, `research`, `security`

Audit signedness, alignment, integer widths, endianness, calling convention, TLS, atomics, floating point, symbol visibility, dynamic loading, and libc assumptions.

**Acceptance criteria**

- Findings are linked to exact generator/runtime locations.
- Every target-dependent behavior has a test or documented mitigation.
- No code changes are made until the report is reviewed.

## NRR-0302 — Define Android compiler target contract

**Priority:** P0  
**Type:** `build`, `cpu`, `android`

Define supported Android ABI/API and flags, initially:

- `arm64-v8a`;
- Android API level chosen by `AND-001`;
- Clang/LLVM from the pinned NDK;
- position-independent shared library;
- hidden-by-default symbols except `recomp-abi` exports;
- floating-point flags preserving guest semantics, including no unintended FMA contraction where required.

**Acceptance criteria**

- Contract is documented and encoded in tests.
- Compiler rejects accidental host-target output.

## NRR-0303 — Add cross-compiler abstraction to builder

**Priority:** P0  
**Type:** `build`, `cpu`, `android`

**Acceptance criteria**

- Builder can select host Linux or Android ARM64 output.
- NDK toolchain discovery is deterministic.
- Command lines are captured in the build report.
- Paths with spaces and long object lists are tested.

## NRR-0304 — Cross-compile public generated fixture to Android `.so`

**Priority:** P0  
**Type:** `build`, `cpu`, `android`, `testing`

**Acceptance criteria**

- ELF reports AArch64 Android-compatible shared object.
- Required exported symbols are present.
- No unexpected host glibc dependency exists.
- Android loader smoke test can `dlopen` and query ABI metadata.

## NRR-0305 — Validate floating-point behavior on AArch64/Bionic

**Priority:** P0  
**Type:** `cpu`, `testing`

Test VFP rounding modes, NaNs, signed zero, infinities, conversions, fused operations, exception/status flags as exposed by the ABI, and denormal behavior.

**Acceptance criteria**

- Differential results match the reference for the supported instruction set.
- Compiler flags preventing semantic drift are enforced.
- Any intentionally approximated behavior is documented and isolated.

## NRR-0306 — Validate direct-memory page table model on Android

**Priority:** P0  
**Type:** `cpu`, `security`, `android`

**Acceptance criteria**

- 32-bit guest address-space page tables allocate safely.
- Direct pages and callback pages behave identically to Linux reference.
- Cross-page and unaligned accesses use callbacks correctly.
- Guarded/unmapped access cannot escape host-managed memory.

## NRR-0307 — Implement generated-library identity verification

**Priority:** P0  
**Type:** `cpu`, `security`

Before loading a title library, verify:

- ABI version;
- generator generation;
- expected title/input hashes;
- exact program/module origin metadata;
- target architecture;
- build schema version.

**Acceptance criteria**

- Mismatched title/library is refused before guest execution.
- Error names the mismatching identity field without exposing game data.

## NRR-0308 — Android CPU execution fixture

**Priority:** P0  
**Type:** `cpu`, `android`, `testing`

**Acceptance criteria**

- Native generated fixture executes inside an Android process.
- Interpreter fallback executes for an uncovered site.
- SVC and unwind exits round-trip to host correctly.
- Output checkpoint matches Linux reference.

## NRR-0309 — Optimize only after profiling

**Priority:** P2  
**Type:** `cpu`, `performance`

Potential work includes hot function overrides, lookup acceleration, page-table locality, call-depth behavior, and reduced context spill. No optimization should be accepted without a profile and correctness comparison.

**Acceptance criteria**

- Before/after profile attached.
- Differential tests pass.
- No fallback path is removed.

---

# EPIC 04 — PICA200 no-stall rendering and cache hardening

**Goal:** Preserve and validate Zakuro’s existing generic dynamic pipeline plus asynchronous specialization, then make its cache lifecycle portable and reliable on Android.

**SPEC coverage:** `GPU-001` through `GPU-013`, `CACHE-001` through `CACHE-010`, `PERF-001`, `TEST-006` through `TEST-008`, `M2`

## NRR-0401 — Document current Zakuro graphics flow

**Priority:** P0  
**Type:** `gpu`, `research`, `documentation`

Map command list → PICA state → surfaces/textures → generic/specialized pipelines → submit/present.

**Acceptance criteria**

- Diagram identifies the dynamic fragment specialization constant/path.
- Diagram identifies pipeline worker thread(s), publication mechanism, and disk cache.
- All relevant source files and synchronization points are listed.

## NRR-0402 — Add generic-path usage telemetry

**Priority:** P0  
**Type:** `gpu`, `observability`

Record per-state-key:

- first encounter;
- generic draw count;
- specialization queued/start/end;
- compile duration;
- publication;
- specialized draw count;
- failure/fallback permanence.

**Acceptance criteria**

- Telemetry is bounded and hash-based.
- It does not serialize or export proprietary shader code by default.

## NRR-0403 — Prove gameplay thread never waits for specialization

**Priority:** P0  
**Type:** `gpu`, `performance`, `testing`

Instrument waits and deliberately slow the compiler worker.

**Acceptance criteria**

- Frames continue through the generic pipeline while specialization is delayed.
- No wait on a compile future occurs in draw submission.
- Any unavoidable Vulkan object creation cost is measured and documented.

## NRR-0404 — Generic/specialized differential image tests

**Priority:** P0  
**Type:** `gpu`, `testing`

Create a state corpus covering TEV, texture units, alpha/depth/stencil, blending, lighting, fog, procedural textures, and depth modes.

**Acceptance criteria**

- Generic and specialized paths render equivalent output within explicitly defined tolerances.
- First differing pixel/state is reported.
- Corpus includes known edge cases and future regression additions.

## NRR-0405 — Validate canonical pipeline key completeness

**Priority:** P0  
**Type:** `gpu`, `testing`, `security`

Mutation-test each state field expected to affect code generation or pipeline compatibility.

**Acceptance criteria**

- Relevant mutations change the key.
- Irrelevant state does not create needless key explosion.
- Key schema has an explicit version.

## NRR-0406 — Harden specialization publication

**Priority:** P0  
**Type:** `gpu`, `threading`, `testing`

**Acceptance criteria**

- Generic pipeline remains valid until complete specialized pipeline publication.
- Publication is atomic from render-thread perspective.
- Duplicate compile requests coalesce.
- Shutdown cancels or drains workers without use-after-free.

## NRR-0407 — Compile-failure resilience

**Priority:** P0  
**Type:** `gpu`, `testing`

**Acceptance criteria**

- Injected compiler/pipeline failure does not crash gameplay.
- State remains on generic path.
- Failure is logged once with retry policy.
- Corrupt cache entry is quarantined or discarded.

## NRR-0408 — Separate portable recipe journal from Vulkan cache blob

**Priority:** P1  
**Type:** `gpu`, `cache`

Implement or formalize:

1. a portable, versioned journal of normalized PICA/pipeline recipes; and
2. an opaque driver pipeline cache keyed to device/driver/build fingerprint.

**Acceptance criteria**

- Recipe journal survives compatible app updates.
- Vulkan blob is invalidated on device/driver/build mismatch.
- Neither cache is treated as trusted input without validation.

## NRR-0409 — Atomic and bounded cache writes

**Priority:** P1  
**Type:** `cache`, `security`, `testing`

**Acceptance criteria**

- Temp-write + fsync/close + atomic rename pattern or platform-appropriate equivalent.
- Interrupted write leaves last valid cache intact.
- Size and entry limits prevent unbounded growth.
- LRU/age policy does not delete active writes.

## NRR-0410 — Prewarm scheduler

**Priority:** P1  
**Type:** `cache`, `performance`, `android`

Use the portable journal to enqueue specialization before gameplay, subject to thermal, battery, memory, and worker limits.

**Acceptance criteria**

- Prewarm can be disabled.
- UI remains responsive.
- Gameplay work takes priority.
- Progress is visible without blocking launch indefinitely.

## NRR-0411 — Android Vulkan capability matrix

**Priority:** P1  
**Type:** `gpu`, `android`, `testing`

Record relevant extensions/features/limits for Adreno 7xx/8xx, Mali, and other reference devices.

**Acceptance criteria**

- Renderer selects a safe path from queried capabilities, not model-name guesses alone.
- Missing optional feature has a tested fallback.

## NRR-0412 — Driver replacement/version compatibility

**Priority:** P2  
**Type:** `gpu`, `cache`, `android`

Support fingerprint changes caused by OTA updates or user-selected Turnip driver versions.

**Acceptance criteria**

- Old device-specific blobs are not loaded under a new incompatible driver.
- Portable recipe journal remains usable where schema-compatible.
- Cache-clearing controls identify exactly what is being removed.

## NRR-0413 — Optional AOT shader-state harvesting experiment

**Priority:** P3  
**Type:** `gpu`, `research`

Investigate static extraction of PICA shader programs/state recipes from title binaries/assets. Do not make this a v1 dependency.

**Acceptance criteria**

- Report distinguishes statically discoverable state from runtime-generated state.
- False-positive/coverage rates are measured on private local samples.
- Runtime generic fallback remains mandatory.

---

# EPIC 05 — Android native shell

**Goal:** Build a first-class native Android ARM64 host with correct surface, lifecycle, input, audio, storage, and configuration behavior before introducing private title code.

**SPEC coverage:** `AND-001` through `AND-012`, `AP-001` through `AP-007`, `AUD-002` through `AUD-006`, `TEST-009`, `TEST-010`, `M3`

## NRR-0501 — Create minimal Android project

**Priority:** P0  
**Type:** `android`, `build`

**Deliverables**

- Gradle project;
- pinned Android Gradle Plugin, Gradle wrapper, NDK, CMake if used;
- `arm64-v8a` only for v1;
- minimal Activity and native bridge;
- no mandatory Google Play Services.

**Acceptance criteria**

- Builds from command line.
- Installs and launches on a reference device.
- Prints build provenance and Vulkan device info.

## NRR-0502 — Native lifecycle state machine

**Priority:** P0  
**Type:** `android`, `threading`, `testing`

Handle create/start/resume/pause/stop/destroy, configuration changes, process recreation, and surface replacement.

**Acceptance criteria**

- Repeated background/foreground cycles do not crash.
- Emulation pauses before invalid resources are used.
- Shutdown is idempotent.
- State transitions are testable without a retail title.

## NRR-0503 — Vulkan surface and swapchain lifecycle

**Priority:** P0  
**Type:** `android`, `gpu`, `testing`

**Acceptance criteria**

- Handles rotation, resize, fold/unfold where applicable, surface loss, minimize/background, and external display changes.
- No stale `ANativeWindow` reference survives replacement.
- Swapchain recreation does not lose core runtime state.

## NRR-0504 — Android input abstraction

**Priority:** P0  
**Type:** `android`, `input`

Support:

- built-in handheld controls reported as Android gamepad/joystick events;
- external controllers;
- touch;
- keyboard;
- motion sensors where available;
- configurable mappings and dead zones.

**Acceptance criteria**

- Event normalization is device-independent.
- Mapping is testable with a diagnostic screen.
- Controller disconnect/reconnect works.

## NRR-0505 — Dual-screen layout engine

**Priority:** P1  
**Type:** `android`, `input`, `gpu`

Implement stacked, side-by-side, large-top, top-only, bottom-only, screen swap, integer/aspect-correct scaling, touch remapping, and optional widescreen top shape.

**Acceptance criteria**

- Touch coordinates map correctly under every layout.
- Layout persists per title.
- No unnecessary render-target recreation occurs for UI-only layout changes where avoidable.

## NRR-0506 — Storage Access Framework import

**Priority:** P0  
**Type:** `android`, `security`

Import user-selected game data/package into app-private storage or retain a persisted URI where appropriate.

**Acceptance criteria**

- No broad storage permission is required.
- Interrupted import is recoverable.
- Hash is verified after copy.
- Original user file is not modified.

## NRR-0507 — Save/config directory isolation

**Priority:** P0  
**Type:** `android`, `hle`, `security`, `testing`

**Acceptance criteria**

- Saves are isolated by title ID and input revision/hash policy.
- Cache deletion never deletes saves.
- Uninstall behavior is clearly documented.
- Export/import can be added without exposing internal paths to guest software.

## NRR-0508 — Android audio backend

**Priority:** P0  
**Type:** `android`, `audio`, `threading`

Use an appropriate low-latency backend such as AAudio/Oboe while keeping audio code platform-isolated.

**Acceptance criteria**

- Callback does not block on emulator locks or file I/O.
- Route changes and Bluetooth connect/disconnect recover.
- Pause/resume does not leave a runaway callback.
- Underrun/overrun counters are observable.

## NRR-0509 — Settings persistence and schema migration

**Priority:** P1  
**Type:** `android`, `configuration`

**Acceptance criteria**

- Global and per-title settings are separated.
- Config schema is versioned.
- Unknown/old fields are migrated or safely ignored.
- Reset options distinguish settings, shaders/recipes, driver cache, logs, and saves.

## NRR-0510 — Crash marker and recovery UI

**Priority:** P1  
**Type:** `android`, `observability`

**Acceptance criteria**

- Next launch detects incomplete prior session.
- User may export a compact diagnostic report.
- No redundant “session bundles” are created in normal use.
- Repeated crash loop offers safe-mode settings without deleting saves.

## NRR-0511 — Stripped-Android compatibility audit

**Priority:** P1  
**Type:** `android`, `testing`

Validate no hard dependency on Play Services, vendor game services, OEM performance APIs, cloud login, analytics, or background schedulers.

**Acceptance criteria**

- App launches on a stripped Android/GammaOS-like environment within available test coverage.
- Optional vendor integrations are behind runtime capability checks and build flags.

## NRR-0512 — Android public fixture app

**Priority:** P0  
**Type:** `android`, `testing`, `release`

Package public synthetic/homebrew fixtures to exercise CPU, graphics, input, audio, files, lifecycle, and cache logic.

**Acceptance criteria**

- APK is redistributable.
- Automated Android tests can run without private material.
- Test app exposes diagnostics needed before private-title integration.

---

# EPIC 06 — Integrate Zakuro runtime into Android

**Goal:** Run the shared HLE/GPU/audio runtime under Android without maintaining a separate emulator implementation.

**SPEC coverage:** `HLE-001` through `HLE-008`, `AND-001` through `AND-012`, `THR-001` through `THR-005`, `M4`

## NRR-0601 — Define platform abstraction boundary

**Priority:** P0  
**Type:** `hle`, `android`, `architecture`

Create explicit interfaces for:

- window/surface;
- event/input;
- audio sink;
- filesystem roots and SAF import;
- clocks and sleep;
- thread naming/priority;
- clipboard/file dialogs only if needed;
- logging;
- crash markers.

**Acceptance criteria**

- Core crates do not call desktop windowing APIs directly.
- Linux host continues to use the same core through its adapter.

## NRR-0602 — Make shared core compile for Android target

**Priority:** P0  
**Type:** `hle`, `android`, `build`

**Acceptance criteria**

- Core crates compile for the Android ARM64 target.
- Desktop-only dependencies are feature-gated or replaced at the host boundary.
- No PRoot, X11, VirGL, or glibc compatibility layer is required.

## NRR-0603 — Connect Android Vulkan device to Zakuro GPU

**Priority:** P0  
**Type:** `gpu`, `android`

**Acceptance criteria**

- Renderer uses Android Vulkan loader/surface.
- Public graphics fixture displays correctly.
- Generic and specialized pipeline paths both execute.
- Pipeline cache root is app-private.

## NRR-0604 — Connect Android input to 3DS HID services

**Priority:** P0  
**Type:** `hle`, `android`, `input`

**Acceptance criteria**

- Buttons, circle pad, C-stick where applicable, triggers, touch, and motion reach guest-visible state.
- Input sampling timing matches Linux reference closely enough for fixture checkpoints.

## NRR-0605 — Connect Android audio to DSP/runtime

**Priority:** P0  
**Type:** `hle`, `android`, `audio`

**Acceptance criteria**

- Public audio fixture plays continuously.
- Timing remains stable during background/foreground transitions.
- Audio thread never owns GPU or main HLE locks.

## NRR-0606 — Connect app-private filesystem to FS services

**Priority:** P0  
**Type:** `hle`, `android`, `security`

**Acceptance criteria**

- Guest sees only mapped title/system/save roots.
- Path traversal and symlink escape tests fail safely.
- Save writes are crash-safe.

## NRR-0607 — Android scheduler and thread-policy integration

**Priority:** P1  
**Type:** `hle`, `android`, `threading`, `performance`

**Acceptance criteria**

- Emulation, GPU submission, compiler workers, audio, and UI have explicit roles and bounded worker counts.
- Thread priorities use standard APIs and do not require vendor-specific services.
- Thermal throttling does not cause unbounded job buildup.

## NRR-0608 — Lifecycle suspend/resume integration

**Priority:** P0  
**Type:** `hle`, `android`, `testing`

**Acceptance criteria**

- Pause at a safe scheduler boundary.
- Audio and presentation stop before surfaces disappear.
- Resume reconstructs host resources and continues fixture execution.
- Process death does not corrupt saves or caches.

## NRR-0609 — New 3DS mode capability model

**Priority:** P2  
**Type:** `hle`, `cpu`, `configuration`

Preserve title-driven hardware model behavior and avoid blindly forcing extra CPU/cache features.

**Acceptance criteria**

- Hardware model is selected by title/configuration with documented overrides.
- Old 3DS titles do not silently receive incompatible New 3DS behavior.

---

# EPIC 07 — Local per-title Android builder and packaging

**Goal:** Turn a user-owned, exact supported input into a signed, sideloadable APK containing locally generated native code, without distributing that code through the public project.

**SPEC coverage:** `BL-001` through `BL-011`, `AP-001` through `AP-007`, `SEC-001`, `SEC-002`, `SEC-007`, `LEG-001` through `LEG-007`, `M7`

## NRR-0701 — Define builder CLI and state machine

**Priority:** P0  
**Type:** `builder`, `tooling`

Proposed commands:

```text
nrr-builder inspect <input>
nrr-builder prepare <input> --work <dir>
nrr-builder build-title <input> --target android-arm64
nrr-builder package-apk <manifest>
nrr-builder verify <apk-or-build-dir>
nrr-builder clean --derived-only
```

**Acceptance criteria**

- Every command supports `--json` reporting.
- Commands are restartable/idempotent where practical.
- Private work paths are explicit.

## NRR-0702 — Exact input/version binding

**Priority:** P0  
**Type:** `builder`, `security`

**Acceptance criteria**

- Manifest binds the package to full input hash and executable/module origin hashes.
- Unsupported region/revision fails early.
- No filename-only matching.

## NRR-0703 — Local decryption/import boundary

**Priority:** P0  
**Type:** `builder`, `legal`, `security`

Use existing lawful user-provided key interfaces only where required by supported upstream tooling. Never ship keys or fetch them.

**Acceptance criteria**

- Key material is never logged.
- Key files are not copied into output packages.
- Decrypted intermediate files stay in ignored private workspace and can be securely cleaned on request.

## NRR-0704 — Generate title AOT library

**Priority:** P0  
**Type:** `builder`, `cpu`, `android`

**Acceptance criteria**

- Produces `libnrr_title.so` or equivalent for `arm64-v8a`.
- Exports only required ABI symbols.
- Build report includes coverage, unresolved sites, module list, compiler flags, and provenance.

## NRR-0705 — Assemble per-title APK

**Priority:** P0  
**Type:** `builder`, `android`, `release`

**Acceptance criteria**

- Native library is packaged under the correct `lib/arm64-v8a/` location.
- Package ID is deterministic and collision-safe for title/revision/build channel.
- Title data is imported or packaged only according to documented local policy.
- APK contains no developer keys or unrelated private inputs.

## NRR-0706 — Local APK signing

**Priority:** P0  
**Type:** `builder`, `security`, `release`

**Acceptance criteria**

- Default workflow creates or uses a user-owned local signing key.
- Secret never enters logs or project tree.
- Rebuild/update behavior is documented.
- Signature verification is part of `verify`.

## NRR-0707 — APK content audit

**Priority:** P0  
**Type:** `builder`, `legal`, `security`, `testing`

**Acceptance criteria**

- Lists files, native ABIs, signatures, manifest permissions, and size contributors.
- Flags unexpected keys, source dumps, debug logs, or unsupported ABIs.
- Confirms title/native library identity manifest is present.

## NRR-0708 — Reproducible public runtime APK

**Priority:** P1  
**Type:** `builder`, `release`

The public shell/fixture APK should be reproducible where feasible; private per-title APKs may differ because of local signing and private input.

**Acceptance criteria**

- Public build excludes title-derived code.
- Reproducibility variance is documented.

## NRR-0709 — Builder GUI wrapper

**Priority:** P2  
**Type:** `builder`, `ux`

Create a desktop UI only after CLI is stable.

**Acceptance criteria**

- UI calls the same tested builder API/CLI.
- Progress maps to explicit build stages.
- Errors expose logs without exposing private code by default.

## NRR-0710 — Upgrade/migration policy

**Priority:** P2  
**Type:** `builder`, `release`

Define how runtime updates, regenerated title libraries, signing identity, saves, settings, and caches interact.

**Acceptance criteria**

- Updating runtime does not overwrite saves.
- ABI/schema mismatch requires controlled rebuild, not undefined loading.

---

# EPIC 08 — First private-title Android vertical slice

**Goal:** Demonstrate one legally owned, known-compatible title running through native AOT code and the Zakuro runtime in a native Android APK.

**SPEC coverage:** `M5`, `AC-001` through `AC-012`

## NRR-0801 — Select and document private validation title

**Priority:** P0  
**Type:** `testing`, `documentation`

Selection criteria:

- already compatible with Zakuro/`3dsrecomp`;
- exercises dual screens, audio, save I/O, PICA state variety, and CRO if possible;
- legally owned/dumped by the tester;
- exact revision recorded privately.

**Acceptance criteria**

- Public documentation names only the validation methodology unless the title name can be discussed without distributing derived material.
- No private files enter the repository.

## NRR-0802 — Produce Linux baseline for the title

**Priority:** P0  
**Type:** `testing`, `performance`

**Acceptance criteria**

- Boot checkpoint, first interactive frame, save/load, representative gameplay, and shutdown tested.
- Cold/warm traces and frame-time data captured privately.
- Native/fallback coverage captured.

## NRR-0803 — Build per-title Android APK

**Priority:** P0  
**Type:** `builder`, `android`, `cpu`

**Acceptance criteria**

- APK installs and verifies identity.
- Generated native title code is used.
- Mismatched title data is refused.

## NRR-0804 — Reach first rendered frame

**Priority:** P0  
**Type:** `android`, `gpu`, `hle`

**Acceptance criteria**

- Both screens render or an explicit known limitation is isolated.
- Generic pipeline handles cold states without compile-induced pause.
- Logs contain no fatal unsupported service at first frame.

## NRR-0805 — Reach interactive gameplay

**Priority:** P0  
**Type:** `android`, `input`, `audio`, `hle`

**Acceptance criteria**

- Controls, touch, audio, timing, and display layout function.
- Ten-minute continuous session without crash.
- Background/foreground once during session recovers.

## NRR-0806 — Save/load safety test

**Priority:** P0  
**Type:** `hle`, `android`, `testing`

**Acceptance criteria**

- New save, load, app restart, and controlled forced-stop paths tested.
- Save hash/structure remains valid.
- Cache clearing leaves save intact.

## NRR-0807 — Cold versus warm shader behavior

**Priority:** P0  
**Type:** `gpu`, `cache`, `performance`

**Acceptance criteria**

- Cold run reports generic draws and specialization times.
- Warm run demonstrates recipe/cache reuse.
- No compile wait appears in frame-thread instrumentation.

## NRR-0808 — Compare Linux and Android checkpoints

**Priority:** P0  
**Type:** `testing`, `correctness`

**Acceptance criteria**

- Defined CPU/HLE checkpoints match.
- Expected graphics differences are documented with images/hashes stored privately.
- First divergence can be located from traces.

## NRR-0809 — Device sweep: Thor and newer Snapdragon target

**Priority:** P1  
**Type:** `android`, `performance`, `testing`

At minimum test the user’s AYN Thor (Snapdragon 8 Gen 2) and a newer Adreno generation when available.

**Acceptance criteria**

- Device/driver fingerprint, power mode, resolution, thermals, battery state, and run duration recorded.
- No vendor API is required to run.
- Driver-specific faults are separated from core correctness faults.

## NRR-0810 — Vertical-slice completion review

**Priority:** P0  
**Type:** `documentation`, `release`

Review all v1 acceptance criteria and classify each as pass, fail, partial, or not tested.

**Acceptance criteria**

- No “works” claim without attached evidence.
- Remaining blockers become individual tickets.

---

# EPIC 09 — Compatibility and correctness hardening

**Goal:** Move from one title to a maintainable general runtime without using unsafe title-specific hacks as the default solution.

**SPEC coverage:** `M6`, `TEST-001` through `TEST-015`, `CPU-010`, `CPU-011`, `HLE-004` through `HLE-008`, `GPU-008` through `GPU-012`

## NRR-0901 — Compatibility database schema

**Priority:** P1  
**Type:** `testing`, `tooling`

Track exact title revision/hash family, build ID, device/driver, stage reached, CPU coverage, services used, renderer path, known issues, and evidence.

**Acceptance criteria**

- Database contains no copyrighted files or code-derived blobs.
- Reports are reproducible and versioned.

## NRR-0902 — Automated boot/probe mode

**Priority:** P1  
**Type:** `testing`, `hle`, `gpu`

**Acceptance criteria**

- Runs unattended to configured checkpoint/time limit.
- Produces bounded structured report.
- Detects crash, hang, unsupported service, graphics failure, and successful checkpoint.

## NRR-0903 — Service coverage dashboard

**Priority:** P2  
**Type:** `hle`, `observability`

**Acceptance criteria**

- Aggregates implemented, stubbed, unsupported, and faulting service calls.
- Does not conflate “function exists” with correct behavior.

## NRR-0904 — Unknown-instruction and unknown-target corpus

**Priority:** P1  
**Type:** `cpu`, `testing`

**Acceptance criteria**

- Every observed fallback site can be reproduced or classified.
- Adding native coverage requires differential proof.
- Interpreter fallback remains the default safety net.

## NRR-0905 — Renderer state corpus expansion

**Priority:** P1  
**Type:** `gpu`, `testing`

Add states discovered by additional titles to the generic/specialized parity suite before changing specialization logic.

**Acceptance criteria**

- Every fixed graphics bug has a regression fixture or private reproducible trace reference.

## NRR-0906 — Save compatibility matrix

**Priority:** P1  
**Type:** `hle`, `testing`

Test archive types, secure values, extdata, shared extdata where applicable, update/DLC layering, and revision migration.

**Acceptance criteria**

- Destructive tests run on copies.
- Failure never silently replaces a valid save.

## NRR-0907 — New 3DS titles and hardware model

**Priority:** P2  
**Type:** `cpu`, `hle`, `testing`

**Acceptance criteria**

- New 3DS service/CPU behavior is enabled only when appropriate.
- Known L2/cache or timing-sensitive titles have regression coverage.

## NRR-0908 — Fuzz container and cache parsers

**Priority:** P1  
**Type:** `security`, `testing`

Targets include title metadata, CRO, manifests, recipe journal, pipeline cache headers, settings, logs, and save import metadata.

**Acceptance criteria**

- Sanitizer/fuzzer runs are automated on public inputs.
- Crashes produce minimized fixtures.

## NRR-0909 — Long-session stability test

**Priority:** P1  
**Type:** `testing`, `performance`

**Acceptance criteria**

- Multi-hour session on at least one Android handheld.
- Tracks memory, worker queue depth, cache growth, thermals, frame pacing, and audio errors.
- No monotonic resource leak above defined tolerance.

## NRR-0910 — Suspend/resume stress test

**Priority:** P1  
**Type:** `android`, `testing`

**Acceptance criteria**

- Repeated 25-cycle background/foreground test.
- Surface recreation, audio route change, controller reconnect, and low-memory callback included.
- Save/cache consistency verified afterwards.

## NRR-0911 — Driver issue isolation workflow

**Priority:** P2  
**Type:** `gpu`, `android`, `documentation`

**Acceptance criteria**

- Reproduce against stock driver and supported Turnip driver where legal/available.
- Capture Vulkan validation or RenderDoc-like evidence only when compatible with Android setup.
- Workarounds are fingerprint-scoped, not globally applied.

---

# EPIC 10 — Performance, power, and handheld usability

**Goal:** Optimize only measured bottlenecks while preserving correctness and low-power operation.

**SPEC coverage:** `PERF-001` through `PERF-007`, `CACHE-008`, `THR-001` through `THR-005`, `M6`

## NRR-1001 — Standard benchmark scene protocol

**Priority:** P1  
**Type:** `performance`, `testing`

Define exact cold/warm run sequence, duration, input script/checkpoints, resolution, device mode, ambient condition notes, and reported percentiles.

**Acceptance criteria**

- Another tester can reproduce the run.
- Results never rely on peak FPS alone.

## NRR-1002 — Frame-time attribution

**Priority:** P1  
**Type:** `performance`, `observability`

Attribute frame cost to guest CPU/native, interpreter, HLE/scheduler, GPU command processing, shader/pipeline work, Vulkan submission, present wait, and audio.

**Acceptance criteria**

- Overhead of instrumentation is measured.
- Attribution identifies at least 90% of measured wall time in benchmark mode or documents gaps.

## NRR-1003 — Worker-pool bounds and backpressure

**Priority:** P1  
**Type:** `threading`, `performance`

**Acceptance criteria**

- Compile/prewarm queue is bounded.
- Duplicate work coalesces.
- Thermal throttling cannot cause runaway backlog.
- Core count is not blindly saturated on big.LITTLE devices.

## NRR-1004 — Thermal-aware prewarm policy

**Priority:** P2  
**Type:** `performance`, `android`, `cache`

Use standard Android thermal/battery signals where available, with graceful absence on stripped systems.

**Acceptance criteria**

- Prewarm pauses or scales down under thermal pressure.
- Gameplay remains prioritized.
- Feature works without vendor SDK.

## NRR-1005 — Memory budget enforcement

**Priority:** P1  
**Type:** `performance`, `security`

Set budgets for guest memory, surfaces, staging rings, decoded textures, shader modules, pipeline objects, journals, logs, and compiler workers.

**Acceptance criteria**

- High-water metrics visible.
- Eviction never discards dirty save data.
- Low-memory conditions degrade safely.

## NRR-1006 — Resolution-scaling performance study

**Priority:** P2  
**Type:** `gpu`, `performance`

Measure 1×, 2×, 3×, 4× where supported and separate GPU-bound from CPU/emulator-bound behavior.

**Acceptance criteria**

- Results include frame-time percentiles and power/thermal context.
- No claim that resolution reduction fixes compatibility failures.

## NRR-1007 — Power measurement protocol

**Priority:** P2  
**Type:** `performance`, `android`

Estimate whole-device and, where possible, SoC power using reproducible battery/USB telemetry methods, clearly labeling their limitations.

**Acceptance criteria**

- Idle/display baseline is recorded.
- Run duration is long enough to reach steady state.
- Thermal throttling is noted.

## NRR-1008 — Thor profile

**Priority:** P1  
**Type:** `performance`, `android`

Create a conservative profile for Snapdragon 8 Gen 2/Adreno 740 with active cooling.

**Acceptance criteria**

- Profile does not rely heavily on AYN-specific Android services.
- Defaults balance stability, power, and latency.
- User can override all tuning.

## NRR-1009 — Modern Adreno profile

**Priority:** P2  
**Type:** `performance`, `android`

Validate newer Snapdragon/Dragonwing devices while keeping feature selection capability-based.

**Acceptance criteria**

- No code assumes one chip family is universally faster or more correct.

---

# EPIC 11 — User experience, diagnostics, and release engineering

**Goal:** Make the system understandable and recoverable without hiding its experimental status or generating log bloat.

**SPEC coverage:** `OBS-001` through `OBS-006`, `CFG-001` through `CFG-003`, `M7`, `AC-001` through `AC-012`

## NRR-1101 — First-run setup flow

**Priority:** P2  
**Type:** `ux`, `android`

**Acceptance criteria**

- Explains local ownership/import model.
- Verifies package/title identity.
- Selects safe defaults based on queried capabilities.
- Does not require account creation or network access.

## NRR-1102 — Diagnostics screen

**Priority:** P1  
**Type:** `observability`, `android`

Display build ID, title hash prefix, ABI/generator versions, native coverage, renderer path, Vulkan device/driver, cache counts, audio status, frame timing, and thermal state when available.

**Acceptance criteria**

- Sensitive paths and full hashes are hidden or user-controlled.
- Copy/export output is bounded.

## NRR-1103 — Cache management UI

**Priority:** P2  
**Type:** `cache`, `ux`

Separate controls for:

- portable pipeline recipes;
- device-specific Vulkan cache;
- texture cache, if any;
- logs;
- generated title library rebuild request;
- saves (never grouped under ordinary cache clear).

**Acceptance criteria**

- Destructive actions state exact scope.
- Save deletion requires distinct confirmation.

## NRR-1104 — Safe mode

**Priority:** P2  
**Type:** `android`, `gpu`, `configuration`

Safe mode may force generic graphics path, disable enhancements/prewarm, use conservative worker counts, and reset only volatile caches.

**Acceptance criteria**

- Triggered manually or after repeated startup crashes.
- Does not delete saves or title import.

## NRR-1105 — Exportable bug report

**Priority:** P1  
**Type:** `observability`, `documentation`

**Acceptance criteria**

- Contains provenance, settings, bounded logs, counters, device/driver, and session result.
- Excludes ROMs, generated code, keys, save contents, and raw private memory by default.
- User reviews before sharing.

## NRR-1106 — Public fixture release pipeline

**Priority:** P1  
**Type:** `release`, `testing`, `legal`

**Acceptance criteria**

- Builds Linux and Android public fixture artifacts.
- Runs no-retail scan.
- Generates checksums, SBOM/notices, provenance, and test summary.
- Never builds a retail-derived title in hosted CI.

## NRR-1107 — Versioning policy

**Priority:** P2  
**Type:** `release`, `documentation`

Version runtime, builder, recomp ABI, generator generation, manifest schema, recipe journal, settings, and crash-report schema independently where needed.

**Acceptance criteria**

- Compatibility matrix and migration behavior documented.
- Version mismatch fails explicitly.

## NRR-1108 — Upstream synchronization procedure

**Priority:** P2  
**Type:** `build`, `documentation`

**Acceptance criteria**

- Update occurs on a branch with changelog review.
- Local patches are rebased and categorized.
- Golden tests run before pin change.
- Upstreamable patches are identified.

---

# EPIC 12 — Optional alternate integration tracks

These are research branches, not prerequisites for the Zakuro-first v1.

## NRR-1201 — Azahar AOT CPU backend feasibility study

**Priority:** P3  
**Type:** `research`, `cpu`, `android`

Investigate loading `recomp-abi` libraries as an optional Azahar CPU backend while retaining Dynarmic/interpreter fallback.

**Acceptance criteria**

- Maps memory, scheduler, SVC, exception, TLS, and CRO integration points.
- Estimates maintenance cost and license implications.
- No claim that this is easier than Zakuro-first without evidence.

## NRR-1202 — Game-specific native-port template

**Priority:** P3  
**Type:** `tooling`, `cpu`, `gpu`

Create an optional template for title-specific overrides, native renderer work, mods, and enhancements, inspired by N64Recomp/TriAevum/Nebby/RaymanOriginsRecomp.

**Acceptance criteria**

- Clearly separate from general runtime.
- Generated retail code remains local.

## NRR-1203 — Direct Android dynamic loading experiment

**Priority:** P3  
**Type:** `research`, `android`, `security`

Test whether a universal sideloaded launcher can safely load a locally generated title `.so` from app-private storage under Android linker/security constraints.

**Acceptance criteria**

- Threat model and policy implications documented.
- Does not become Play Store architecture.
- Per-title APK remains the fallback/recommended v1 path.

## NRR-1204 — On-device compilation experiment

**Priority:** P3  
**Type:** `research`, `builder`, `android`

Evaluate compile time, memory, storage, thermal load, compiler distribution size/licensing, and security.

**Acceptance criteria**

- No v1 dependency.
- Report compares desktop build plus sideload against on-device build.

## NRR-1205 — Shader/pipeline pack portability study

**Priority:** P3  
**Type:** `gpu`, `cache`, `research`

Determine which PICA-derived artifacts can be portable across GPUs and which Vulkan artifacts must remain driver-specific.

**Acceptance criteria**

- Never distribute game-derived shader material without legal review.
- Technical format is content-addressed and versioned.

---

# 13. Milestone issue bundles

## Milestone M0 — Repository is safe to develop

Required tickets:

- NRR-0001 through NRR-0005
- NRR-0102
- NRR-0106

**Exit gate**

- Public CI passes no-retail scanning.
- Dependency licenses and pins are recorded.
- Public fixture exists.

## Milestone M1 — Linux golden harness

Required tickets:

- NRR-0101 through NRR-0107
- NRR-0201 through NRR-0210
- NRR-0301

**Exit gate**

- One private title runs with provable AOT usage and fallback.
- Deterministic checkpoints and cold/warm benchmark exist.

## Milestone M2 — No-stall graphics validated

Required tickets:

- NRR-0401 through NRR-0409

**Exit gate**

- Generic path renders during deliberately delayed compilation.
- Generic/specialized parity corpus passes.
- Cache corruption/invalidation tests pass.

## Milestone M3 — Android shell

Required tickets:

- NRR-0501 through NRR-0512

**Exit gate**

- Public fixture APK survives lifecycle/input/audio/storage tests.

## Milestone M4 — Android shared runtime and AOT fixture

Required tickets:

- NRR-0302 through NRR-0308
- NRR-0601 through NRR-0608

**Exit gate**

- Public generated ARM64 fixture executes natively in Android with interpreter fallback and GPU output.

## Milestone M5 — Private-title vertical slice

Required tickets:

- NRR-0701 through NRR-0707
- NRR-0801 through NRR-0810

**Exit gate**

- Locally built per-title APK reaches stable interactive gameplay and save/load on Android.

## Milestone M6 — Compatibility and performance hardening

Required tickets:

- NRR-0901 through NRR-0911
- NRR-1001 through NRR-1009

**Exit gate**

- Multiple titles/devices have evidence-backed results.
- Long-session, suspend/resume, cache, and parser tests pass.

## Milestone M7 — Usable experimental release

Required tickets:

- NRR-0708 through NRR-0710
- NRR-1101 through NRR-1108

**Exit gate**

- Builder, diagnostics, safe mode, release notices, and update policy are complete.

---

# 14. Critical path

The shortest credible critical path is:

```text
NRR-0001..0005
  → NRR-0101..0107
  → NRR-0201..0209
  → NRR-0401..0409
  → NRR-0501..0512
  → NRR-0302..0308
  → NRR-0601..0608
  → NRR-0701..0707
  → NRR-0801..0810
```

Do not start with Android retail-title packaging. The Linux golden path and public Android fixture exist specifically to keep platform bugs, title bugs, generator bugs, renderer bugs, and packaging bugs separable.

---

# 15. Codex ticket prompt template

Use this template for each individual ticket:

```markdown
You are working on ticket <ID>: <title> in the 3DS-NRR repository.

Read first:
- 00_README.md
- the relevant sections of 02_SPEC_3DS_NATIVE_RECOMP_RUNTIME.md
- 03_EXISTING_PROJECTS_AND_GAP_MATRIX.md
- 04_REFERENCES.md
- the repository reconnaissance report
- applicable ADRs

Hard constraints:
- Do not add ROMs, firmware, keys, copyrighted assets, retail-derived source,
  generated retail title libraries, or private traces to the repository.
- Preserve interpreter/reference fallbacks.
- Do not replace the existing generic PICA fallback unless this ticket explicitly
  calls for a reviewed alternative.
- Do not make unrelated refactors.
- Do not claim completion from compilation alone.
- Keep Android functionality independent of Google Play Services and vendor APIs.

Task:
<copy this ticket's goal, deliverables, and acceptance criteria>

Before editing:
1. Locate the exact existing implementation points.
2. State the smallest file set you expect to change.
3. Identify tests that should fail before the change and pass after it.
4. Call out any conflict between the ticket and current upstream behavior.

Implement the smallest correct change.

Validation:
- run formatting/linting;
- run focused unit/integration tests;
- run applicable public fixture tests;
- report commands and outputs;
- report performance evidence when this is a performance ticket;
- report any unverified behavior instead of guessing.

End with:
- files changed;
- behavioral result;
- tests passed/failed;
- artifacts created;
- risks/limitations;
- exact next recommended ticket.
```

---

# 16. Backlog anti-patterns

Reject or split a ticket when it asks Codex to:

- “build the whole emulator” in one pass;
- replace Zakuro or `3dsrecomp` without a measured deficiency;
- remove interpreter fallback for speed;
- precompile only known shaders and assume no runtime state exists;
- treat Vulkan pipeline-cache blobs as portable;
- package generated retail title code in public releases;
- target Android before the Linux golden path is reproducible;
- fix compatibility through silent title-specific hacks without regression tests;
- use vendor performance APIs as required dependencies;
- store unbounded logs/session bundles;
- declare a GPU path correct because one game scene looks right;
- optimize without before/after profiling;
- disable correctness checks to meet a benchmark; or
- merge a large upstream sync together with new feature work.

---

# 17. Definition of project-ready

The project is ready for sustained Codex implementation when all of the following are true:

1. Upstream pins and licenses are fixed and recorded.
2. Public fixtures cover CPU, HLE, GPU, audio, input, files, and lifecycle.
3. Linux builds and tests from one documented command.
4. A private title proves native CPU execution plus safe fallback.
5. Generic/specialized PICA parity and no-wait behavior are instrumented.
6. Android shell passes lifecycle and fixture tests without private material.
7. Builder can cross-compile a public generated fixture to Android ARM64.
8. CI rejects retail/private artifacts.
9. Codex prompts are issued as individual tickets, not as an unconstrained whole-project request.

---

# Part 8 — Uberhar relationship and migration decision

> Source file: `07_UBERHAR_RELATIONSHIP_AND_MIGRATION.md`

# Relationship to Uberhar: Repository and Migration Decision

**Prepared for:** Tanner / RegiRex  
**Existing project:** Uberhar, an Azahar-derived Android 3DS emulator fork  
**Recommended new project:** 3DS Native Recompilation Runtime (3DS-NRR), based on pinned `3dsrecomp` + Zakuro

## 1. Decision summary

Do **not** initially turn Uberhar into this recompilation runtime by replacing its core.

Create a separate repository for 3DS-NRR and treat Uberhar as:

- a source of test methodology;
- a source of device/performance observations;
- a mature Android-emulator UX reference;
- a source of requirements for logs, cache controls, and renderer comparisons; and
- a possible future host for an experimental `recomp-abi` CPU backend.

The recommended separation is architectural rather than cosmetic:

| Uberhar | 3DS-NRR |
|---|---|
| Azahar/Citra-derived C++ emulator | Zakuro Rust HLE runtime + `3dsrecomp` AOT libraries |
| General JIT/interpreter emulator architecture | AOT-first CPU execution with interpreter fallback |
| Existing Android frontend | Android frontend still to be productized |
| Existing Uberhar renderer experiments | Existing Zakuro software/Vulkan PICA paths and dynamic specialization |
| Existing repository history and APK releases | New architecture, dependency graph, licenses, and build pipeline |

Trying to replace Uberhar’s CPU, HLE, renderer, and build architecture simultaneously would create a difficult-to-review hybrid and would make it harder to determine whether failures came from Azahar, Zakuro, `3dsrecomp`, Android integration, or local changes.

## 2. What should be reused from Uberhar

### 2.1 Test methodology

Uberhar already established useful empirical practices:

- cold versus warm runs;
- explicit speed-up toggles to mark gameplay intervals;
- per-title scene notes;
- native versus combo/hybrid comparisons;
- resolution scaling at 1×, 2×, and 4×;
- crash reproduction in Luigi’s Mansion;
- thermal-throttling observations in Kid Icarus;
- coastline/inland scene comparison in LEGO City;
- lap markers in Sonic;
- device-performance headroom goals; and
- preference for real frame-time behavior over peak FPS alone.

These methods should become 3DS-NRR benchmark protocols and structured test manifests. They are more valuable than copying implementation code.

### 2.2 Lean logging requirements

Carry forward these requirements:

- ordinary logs remain bounded;
- no redundant in-app session bundles;
- a crash-safe last-session record is acceptable;
- crash-only data may live in a segregated file;
- log export should be explicit;
- renderer and cold/warm markers should be machine-readable;
- logs should identify title, build, driver, renderer path, and device without exposing private title code; and
- Android system services should not be required for correctness.

The 3DS-NRR SPEC and backlog already encode these constraints.

### 2.3 Device matrix

Uberhar’s current and planned targets are directly useful:

- AYN Thor / Snapdragon 8 Gen 2 / Adreno 740;
- Retroid Duo when available;
- stripped Android distributions such as GammaOS;
- future current-generation Adreno devices; and
- dual-screen devices where frame synchronization matters.

Retain the same device-report fields across both projects so results can be compared:

```text
device_model
soc
gpu
driver_name
driver_version
android_version
performance_mode
cooling_mode
battery_state
thermal_state
screen_layout
resolution_scale
build_id
title_hash_prefix
scene_id
run_type = cold | warm
```

### 2.4 Release discipline

Reuse the established release habits:

- ARM64 APK artifacts;
- semantic prerelease tags;
- reproducible build notes;
- explicit test requests per build;
- title-specific regressions recorded by version; and
- no release claim without actual device evidence.

### 2.5 User-facing controls

Conceptually reusable controls include:

- clear graphics cache;
- export log;
- select renderer policy;
- force conservative fallback;
- choose resolution scale;
- performance/compatibility presets; and
- crash recovery/safe mode.

The exact implementation should be native to 3DS-NRR rather than copied blindly from Uberhar.

## 3. What should not be copied automatically

### 3.1 Azahar source code

Uberhar inherits the Azahar/Citra codebase and its license obligations. Zakuro and `3dsrecomp` currently use MIT licensing. Copying Azahar implementation into an MIT-oriented project may change the distribution obligations of the combined work.

Before copying any code:

1. identify the exact source file and license;
2. determine whether the new binary would form a combined/derivative work;
3. preserve notices and source obligations;
4. prefer clean-room behavioral reimplementation when appropriate; and
5. record the decision in `THIRD_PARTY_NOTICES.md` and an ADR.

Studying behavior, test cases, or public API concepts is not the same as copying code.

### 3.2 Uberhar’s renderer branches as a direct base

Uberhar’s native/compute/combo experiments were developed inside Azahar’s renderer architecture. Zakuro already has its own PICA implementation, Vulkan path, software/reference path, generic dynamic fragment pipeline, asynchronous specialization, surface tracking, and disk pipeline cache.

The first 3DS-NRR graphics task should be to validate and harden Zakuro’s existing design, not transplant Uberhar’s renderer wholesale.

Specific Uberhar discoveries may still become regression cases, for example:

- Luigi’s Mansion ghost and half-screen anomalies;
- Fire Emblem ghosting at increased resolution;
- Kid Icarus dual-screen latency;
- Sonic performance differences between paths; and
- thermal sensitivity under sustained speed-up.

### 3.3 Existing session-bundle design

The user explicitly found the proliferation of empty/no-game session bundles undesirable. Do not port that behavior. The new runtime should use:

- one bounded current log;
- one prior incomplete/crash marker;
- optional per-title aggregate metrics; and
- explicit export on demand.

### 3.4 Android-specific shortcuts

Do not make correctness depend on:

- proprietary AYN services;
- Google Play Services;
- OEM game-mode APIs;
- a full stock Android environment;
- background upload services; or
- aggressive system-level privileges.

3DS-NRR should remain usable on stripped Android distributions.

## 4. Three integration strategies

## Strategy A — Separate Zakuro-first project

**Recommendation:** Use now.

```text
RegiRex/3ds-nrr
  ├─ pinned fearkov/3dsrecomp
  ├─ pinned fearkov/zakuro
  ├─ Linux golden harness
  ├─ Android native host
  ├─ local per-title builder
  └─ shared test/benchmark definitions
```

### Advantages

- Existing AOT ABI is already integrated with Zakuro.
- Smallest conceptual path to a general recompilation runtime.
- Clean provenance and licensing.
- Failures are easier to localize.
- Upstream synchronization is manageable.
- Uberhar remains functional during experimentation.

### Disadvantages

- Android frontend must be built/productized.
- Zakuro compatibility and UX are younger than Azahar.
- Some work may be duplicated at the frontend level.

## Strategy B — Add `3dsrecomp` backend to Uberhar/Azahar

**Recommendation:** Feasibility study after 3DS-NRR’s Linux and Android fixture milestones.

Concept:

```text
Uberhar/Azahar HLE + Android frontend + renderer
                  ↑
       optional recomp-abi CPU backend
                  ↑
      local per-title 3dsrecomp library
```

### Advantages

- Retains mature Android UI and broad Citra/Azahar compatibility.
- Reuses Uberhar’s existing release and testing infrastructure.
- Could offer JIT and AOT modes in one app.

### Disadvantages

- Requires bridging Rust-generated ABI into C++ memory/scheduler/SVC/CRO machinery.
- Must reconcile different CPU state, memory maps, exception behavior, and module loaders.
- Larger licensing and maintenance surface.
- Much harder first project than using Zakuro, which already consumes `recomp-abi`.

### Required proof before implementation

- exact mapping of `recomp-abi::Context` to Azahar CPU state;
- memory page table integration;
- SVC and exception handoff;
- scheduler budget semantics;
- CRO module base updates;
- code-origin validation;
- interpreter/JIT fallback;
- floating-point equivalence;
- Android dynamic-library loading; and
- build/license review.

## Strategy C — Fold all work into Uberhar immediately

**Recommendation:** Reject.

This would combine:

- an Azahar fork;
- unfinished renderer experiments;
- a new Rust AOT generator/runtime;
- a second HLE stack;
- Android native packaging;
- local title recompilation; and
- a new shader/pipeline strategy.

The result would be difficult for a human or Codex agent to reason about and nearly impossible to validate incrementally.

## 5. Shared artifacts between the projects

The two projects can share data formats and testing infrastructure without sharing emulator-core code.

### 5.1 Title test manifest

```yaml
title_test:
  id: fea-opening-cold
  title_family: fire-emblem-awakening
  private_input_hash_prefix: '<local-only>'
  scene: opening-to-first-interactive-frame
  duration_seconds: 180
  markers:
    - launch
    - title_screen
    - gameplay_start
  checks:
    - no_crash
    - audio_continuity
    - top_bottom_sync
    - frame_time_percentiles
    - renderer_anomalies
```

The public repository should contain scene descriptions and expected categories, not game data, memory captures containing code, or copyrighted screenshots unless distribution is lawful.

### 5.2 Performance result schema

Use one schema for Uberhar and 3DS-NRR:

```json
{
  "project": "uberhar-or-3ds-nrr",
  "build_id": "...",
  "device": "...",
  "soc": "...",
  "gpu_driver": "...",
  "title_test_id": "...",
  "cold": true,
  "resolution_scale": 2,
  "frame_time_ms": {
    "p50": 0,
    "p95": 0,
    "p99": 0,
    "max": 0
  },
  "power_w_estimate": null,
  "thermal_notes": "...",
  "renderer_path": "...",
  "fallback_counts": {},
  "anomalies": []
}
```

### 5.3 Issue taxonomy

Use common labels:

- `cpu-correctness`;
- `hle-service`;
- `gpu-state`;
- `shader-specialization`;
- `pipeline-cache`;
- `surface-sync`;
- `dual-screen-sync`;
- `audio-timing`;
- `android-lifecycle`;
- `driver-specific`;
- `thermal/performance`; and
- `title-specific`.

### 5.4 Crash record schema

Both projects can adopt a compact crash record with:

- build ID;
- device/driver;
- title hash prefix;
- last scene/marker;
- renderer path;
- cache status;
- last bounded events;
- exception/signal;
- native/interpreter counts; and
- whether the prior session closed cleanly.

## 6. Recommended repository organization for RegiRex

```text
RegiRex/
  uberhar/                    # Existing Azahar-derived emulator fork
  3ds-nrr/                    # New Zakuro + 3dsrecomp integration
  3ds-handheld-test-specs/    # Optional public test descriptions/schemas
```

A separate test-spec repository is optional. Keeping test definitions in 3DS-NRR initially is simpler; extract them only when both projects actively consume the same schemas.

## 7. Suggested first Codex prompt tailored to the existing situation

```text
I maintain RegiRex/uberhar, an Azahar-derived Android 3DS emulator fork, but this task is for a separate clean repository implementing the 3DS-NRR architecture. Do not modify Uberhar and do not copy Azahar/Uberhar code into the new repository without an explicit license review.

Use the attached 3DS-NRR research pack. Begin with reconnaissance only. Verify the pinned fearkov/3dsrecomp and fearkov/zakuro commits, map their current CPU/HLE/GPU/cache architecture, and create the repository scaffold and ADR plan described by NRR-0001, NRR-0002, and NRR-0101. Reuse concepts from Uberhar only as requirements/test methodology: cold-versus-warm runs, bounded crash-safe logging, ARM64 APK release discipline, device matrices, and title-scene benchmark definitions.

Do not implement Android, do not ingest a retail game, and do not rewrite any emulator subsystem in this task. End with the exact smallest code change needed for the Linux public-fixture harness.
```

## 8. Migration gates

Do not reconsider merging the projects until all of these are true:

1. 3DS-NRR Linux golden harness runs a public fixture and one private title.
2. Native CPU execution and interpreter fallback are proven.
3. Generic/specialized PICA parity tests pass.
4. Android public fixture APK survives lifecycle testing.
5. Android AOT fixture executes through `recomp-abi`.
6. One private per-title APK reaches interactive gameplay.
7. An Azahar-backend feasibility report demonstrates a clear benefit over maintaining separate projects.
8. License implications of any shared binary/source are understood.

Even then, a shared organization and test infrastructure may be better than one combined codebase.

## 9. Final recommendation

Use Uberhar to continue testing and improving the mature Azahar-derived emulation path. Build 3DS-NRR separately to explore the AOT-first path. Let measured results determine whether the long-term outcome is:

- two complementary projects;
- shared benchmark/logging infrastructure;
- an optional AOT backend in Uberhar; or
- title-specific native ports using the same recompiler/runtime foundations.

This separation preserves progress, reduces risk, and gives Codex tasks clear architectural boundaries.

---

