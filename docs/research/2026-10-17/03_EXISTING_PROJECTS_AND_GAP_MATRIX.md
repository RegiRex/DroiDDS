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
