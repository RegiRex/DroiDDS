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
