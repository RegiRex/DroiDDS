# Upstream integration and source boundaries

<!-- CodexAstraUlt: Record the actual reuse boundary, pinned interfaces and notice gap so the first implementation can build on upstream work without implying a complete runtime or inventing attribution. -->

Updated **2026-10-19**. DroidDS builds an original Android integration around
selected existing components. It does not rewrite their CPU interpreter,
recompiler or ABI. This document records source selection and integration
decisions; exact final execution/publication results belong in build evidence.

## Current 0.0.5 integration

<!-- CodexAstraUlt: Replace the no-vendor/no-runtime summary with the maintained
source boundary, real guest proof and measured reason for the compiler patch. -->

| Component | Current selection | Boundary |
| --- | --- | --- |
| Host compiler | `vendor/3dsrecomp`, based on `c3f21f94ba50d688025febc8974ff348d471b587` | Maintained host-side compiler; generated fixture code enters the APK, the compiler executable does not |
| Shared ABI | `recomp-abi` at the same exact Git revision | ABI 4 / generation 3 remains shared; no handwritten replacement |
| CPU interpreter/common | `zakuro-cpu` / `zakuro-common` at `412900a5a020301da15c1cc382585e05a489a535` | Exact Git dependencies retained |
| Loader, HLE and PICA | `vendor/zakuro/crates/zakuro-core`, `zakuro-fs`, `zakuro-gpu`, based on that same Zakuro revision | Selected maintained sources; no desktop frontend imported |
| Integration proof | Original `droidds-runtime-probe` | Original NCCH guest, service/PICA command data and independent output expectations |

Each vendor directory's `UPSTREAM.json` records original source hashes and the
selected revision; upstream notice/manifest evidence is preserved. Adjacent
`CodexAstraUlt` comments identify local changes. The root workspace, `Cargo.lock`
and `upstream.lock.toml` govern the actual build graph. Shared Cargo caches and
upstream repositories are not modified.

The integrated guest revealed a real backward-loop/conditional-flow accounting
defect: the reference executed 598 instructions while native accounting charged
1,598 before correction. The reviewed compiler block-discovery correction and
executed regressions now pass; relaxing report counters would conceal the defect.
Vendoring the compiler permits that correction without changing the ABI pin or
patching a shared cache. These instruction counts are not gameplay-speed results.

The actual runtime proof loads an original NCCH/CXI executable, enters guest
SVC/IPC services and submits PICA commands through `gsp::Gpu`. It compares CPU
interpreter/software, native/software and native/Vulkan execution against exact
pixels and required route/service evidence. A deliberate helper remains in the
CPU interpreter. Required GPU tests cannot silently pass after initialization
failure; host qualification runs both normal and forced static blend/logic state.
Vulkan rasterization is distinguished from GPU vertex execution: the Thor may
use the accurate CPU PICA vertex interpreter with Vulkan rasterization.

The maintained loader resolves complete Old/New physical layouts and separate
legacy commitment caps before construction. It corrects header fields and config
reporting, constrains virtual heap windows, and preflights saved geometry/quota
before replacing live memory. Original actual-loader/kernel/service regressions
are recorded in [the New 3DS correction record](NEW3DS_AUDIT.md#005-integration-corrections).
This does not establish Xenoblade execution or full New-model scheduling.

The optional Cranelift PICA CPU JIT is disabled. Vulkan remains enabled, including
runtime shader translation. Admission bounds cover queued/running/completed work,
retained translation keys/pipelines and shader payloads; accepted work is tracked
until collection. Deferred specialization preserves the generic path, and a
resource failure remains observable with accurate software fallback. Objects that
may be referenced by submitted commands are not unsafely evicted. These policies
do not bound all texture/driver memory or remove every synchronous first-use
generic-pipeline compilation; cold gameplay and sustained-memory gates remain.

The larger runtime graph receives its own complete
[notice inventory](../THIRD_PARTY_NOTICES.md), including the selected runtime
sources, shader provenance and unmodified MPL-2.0 Symphonia components with exact
source-archive availability. Registry/target/feature identity changes invalidate
the reviewed inventory rather than silently omitting notices. This review does
not authorize copying arbitrary GPL components from Azahar, MMJ or Uberhar.

<!-- CodexAstraUlt: Record verified publication separately from the still-open
Thor runtime and private-title gates; retain the fixture's precise scope. -->
The 0.0.4 Thor report passes its original diagnostic scope. The
[0.0.5 prerelease](https://github.com/RegiRex/DroidDS/releases/tag/v0.0.5-probe.1)
is published with verified public downloads and passing required host/CI gates
in [run 39341905818](https://github.com/RegiRex/DroidDS/actions/runs/39341905818).
See the [build record](builds/0.0.5-runtime-integration.md). Its Thor runtime report
remains pending. The public fixture is NCCH; no 3DSX loader, game presentation/
input/audio qualification or retail baseline is claimed. Exact private Dark Moon,
Xenoblade and Sonic inputs are absent from this environment, so their M3 baselines
remain open. Obtain the 0.0.5 Thor report, correct any failures, then proceed to
0.0.6 visible original homebrew and lifecycle integration.

## Initial 0.0.1 inventory (historical)

<!-- CodexAstraUlt: Retain first-build provenance without letting its smaller
historical dependency inventory describe the current runtime selection. -->

The sections below retain the **2026-10-17 first-build** source/ABI decisions.
Their package counts and graph describe that milestone, not the current graph.

### First-build source map

| Source | Exact commit | First-build use | Source license evidence |
| --- | --- | --- | --- |
| [fearkov/3dsrecomp](https://github.com/fearkov/3dsrecomp/tree/c3f21f94ba50d688025febc8974ff348d471b587) | `c3f21f94ba50d688025febc8974ff348d471b587` | `recomp3ds` 0.1.0 with `host`; existing discovery, C generation, compiler invocation and native library loading | Root and `abi/Cargo.toml` declare `MIT`; no LICENSE, NOTICE or COPYING file in this tree |
| Same 3dsrecomp tree | Same commit | `recomp-abi` 0.1.0; shared definitions and loader, with `load` enabled by `host` | Same declaration and missing notice evidence |
| [fearkov/zakuro](https://github.com/fearkov/zakuro/tree/412900a5a020301da15c1cc382585e05a489a535) | `412900a5a020301da15c1cc382585e05a489a535` | `zakuro-cpu` 0.2.27 as the interpreter, with its `zakuro-common` dependency | Workspace declares `MIT`; root LICENSE supplies the MIT text and `Copyright (c) 2026 fearkov` |

The first project manifest fetched those components directly from their upstream Git
repositories using full `rev` pins. It did not vendor upstream source into
the DroidDS source tree. Cargo's local checkout and generated build output remain
outside tracked source. The committed lockfile records the resolved registry
versions and checksums; locked builds must not silently select new dependencies.

The first resolved Cargo graph contains one original DroidDS package, four Git
packages at exactly the two commits above, and 19 registry packages. The resolved
features are `recomp3ds: [host]`, `recomp-abi: [load]`, and no features for
`zakuro-cpu`/`zakuro-common`; `recomp3ds/verify` is absent. Neither the old verifier's
Zakuro commit nor the desktop/GPU/core crates occur in this resolved graph.
The lockfile SHA-256 for this inventory is
`42d085a4249ec3490496bbb30f727c187849966cf33594dd1a94f847671324cb`.

The selected compiler minimum is Rust 1.95.0: 3dsrecomp declares 1.88, whereas
Zakuro's workspace declares 1.95. This is a toolchain requirement, not a statement
that every upstream crate is built or tested. Host C compilation is a separate
toolchain whose exact observed identity must be recorded by the build.
Rebuilding the locked graph is not a claim of bit-identical output across different
C compilers, operating systems or system libraries.

### First-build dependency and verifier decision

<!-- CodexAstraUlt: Avoid adopting the older upstream verifier graph as the runtime oracle; use the selected interpreter directly and make strict comparison the harness's responsibility. -->

The required dependency paths are:

```text
original DroidDS harness
  -> recomp3ds [host] @ c3f21f94...
     -> recomp-abi [load] @ c3f21f94...
        -> libloading -> cfg-if / target-specific platform support
     -> libc (Unix)
  -> recomp-abi [load] @ c3f21f94... (direct ABI use)
  -> zakuro-cpu @ 412900a5...
     -> zakuro-common @ 412900a5...
        -> bitflags [serde], log, thiserror
     -> log, serde [derive]
  -> serde_json (machine-readable original harness results)
  -> libc (host memory/process integration)
```

Serde and thiserror pull their procedural-macro dependencies; the lockfile is the
complete version inventory. The resolved registry declarations and the license
files actually present in their fetched packages are listed in
[the notice inventory](../THIRD_PARTY_NOTICES.md#resolved-registry-inventory).
A package listed in a cross-platform lockfile is not proof that it executes or
links on the Linux host: `windows-link` is included in resolution but its incoming
edge is restricted to `cfg(windows)`. Notice assembly for binary distribution must
use the actual artifact's target, enabled features and included code.

The `recomp3ds` **`verify` feature is disabled**. Its upstream lockfile selects
Zakuro `3e853d5a091dab9b7bfb3b0f41e3457d42ff4bb6`, whose CPU/common packages are
0.1.0, rather than the selected 0.2.27 tree. Dependency lockfiles are not an
instruction for the new workspace to reuse that graph. DroidDS calls the pinned
0.2.27 interpreter directly and supplies its own fixture expectations and strict
integer/memory comparisons. This addresses which interpreter is being tested; it
does not claim to repair or validate upstream's verifier.

The first build did not include Zakuro's desktop frontend, core/HLE services,
filesystem, audio or GPU renderer. Their transitive dependencies and runtime
behavior are outside this dependency inventory. No Uberhar/Azahar implementation
is imported. Future reuse of any of those components requires a fresh source,
dependency and license review for the actual selection.

### Shared ABI contract and initial scope

<!-- CodexAstraUlt: Reuse the real ABI instead of the research pack's illustrative callback interface; keep unsupported runtime work explicit. -->

The pinned ABI has **version 4 and code-generation version 3**. The C header and
Rust definitions are supplied by the same 3dsrecomp commit. DroidDS uses upstream
`recomp_abi::HEADER`, `Context`, `Host` and `Library`; it does not maintain a
parallel handwritten interface.

`Host` supplies 8/16/32-bit memory access, interpreter fallback and native-entry
lookup callbacks. A guest SVC is an execution exit with a number in the context,
not an invented service callback. The harness must observe execution routes and
exits and compare the supported fixture state at documented checkpoints. A
missing compiler, missing native entry, timeout or unexecuted required case must
not become a correctness pass.

ABI compatibility and code freshness are different checks. Generation 3 origin
metadata can validate recorded guest code pieces; it does not by itself implement
continuous invalidation for writes, title revision identity, CRO lifetime or safe
unloading. Those remain DDS-004/005 work. Native library loading executes host
code: the harness accepts only the synthetic library it has just generated, not
an arbitrary downloaded library.

### Initial reuse and distribution boundary

<!-- CodexAstraUlt: Replace the initial source-only distribution hold after the
owner's prerelease request and actual notice assembly; preserve missing-notice
provenance without inventing upstream copyright attribution. -->

The first Linux milestone published original source, synthetic fixtures, build
configuration, pins and reports without binaries. The owner subsequently
requested a downloadable Android CPU probe prerelease. That APK contains the
original synthetic fixtures and selected upstream ABI/interpreter support.

[THIRD_PARTY_NOTICES.md](../THIRD_PARTY_NOTICES.md) records the actual dependency
and toolchain notices, assembled by `tools/collect_android_notices.py`. The full
bundle is embedded in the APK and published beside it. This includes all supplied
registry and Zakuro notices, Rust runtime and NDK support notices, and both
3dsrecomp manifests with their explicit MIT declarations plus clearly labeled
standard MIT terms. The missing standalone 3dsrecomp copyright notice is recorded;
no holder is invented or borrowed from Zakuro. The explicit MIT declarations
support the current probe's distribution, resolving the earlier blanket hold.

The tag workflow verifies the signed APK and stages only its four public release
assets. The one-off diagnostic key is never uploaded or retained. Stable product
signing remains separate work, and no upstream contact or submission is implied.

Retail inputs and all retail-derived output remain private. The public release
contains only the original CPU test fixtures; Android device execution, graphics
and real-title compatibility remain separate qualification gates. Future source
reuse requires its own actual dependency and notice review.
