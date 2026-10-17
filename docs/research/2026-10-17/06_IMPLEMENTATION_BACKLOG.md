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
