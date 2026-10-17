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
