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
