# Upstream integration for the first DroidDS build

<!-- CodexAstraUlt: Record the actual reuse boundary, pinned interfaces and notice gap so the first implementation can build on upstream work without implying a complete runtime or inventing attribution. -->

Date: 2026-10-17. DroidDS starts with an original Linux correctness harness around
selected existing components. It is not a rewrite of their CPU interpreters,
recompiler or C ABI. This document records source inspection and integration
decisions; execution results belong in the build report.

## Selected source map

| Source | Exact commit | First-build use | Source license evidence |
| --- | --- | --- | --- |
| [fearkov/3dsrecomp](https://github.com/fearkov/3dsrecomp/tree/c3f21f94ba50d688025febc8974ff348d471b587) | `c3f21f94ba50d688025febc8974ff348d471b587` | `recomp3ds` 0.1.0 with `host`; existing discovery, C generation, compiler invocation and native library loading | Root and `abi/Cargo.toml` declare `MIT`; no LICENSE, NOTICE or COPYING file in this tree |
| Same 3dsrecomp tree | Same commit | `recomp-abi` 0.1.0; shared definitions and loader, with `load` enabled by `host` | Same declaration and missing notice evidence |
| [fearkov/zakuro](https://github.com/fearkov/zakuro/tree/412900a5a020301da15c1cc382585e05a489a535) | `412900a5a020301da15c1cc382585e05a489a535` | `zakuro-cpu` 0.2.27 as the interpreter, with its `zakuro-common` dependency | Workspace declares `MIT`; root LICENSE supplies the MIT text and `Copyright (c) 2026 fearkov` |

The project manifest fetches those components directly from their upstream Git
repositories using full `rev` pins. Upstream source is not vendored or copied into
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

## Dependency and verifier decision

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

The first build does not include Zakuro's desktop frontend, core/HLE services,
filesystem, audio or GPU renderer. Their transitive dependencies and runtime
behavior are outside this dependency inventory. No Uberhar/Azahar implementation
is imported. Future reuse of any of those components requires a fresh source,
dependency and license review for the actual selection.

## ABI contract and scope

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

## Reuse and distribution boundary

<!-- CodexAstraUlt: Preserve factual notices and restrict the first published deliverable to original source/build instructions while the upstream notice provenance remains unresolved. -->

The first public deliverable consists of DroidDS's original harness, original
synthetic fixtures, build/CI configuration, source pins and reports. It neither
ships upstream source copies nor attaches a compiled harness or generated shared
library. Local builds and CI fetch the declared dependencies from their original
sources. This choice lets implementation and tests proceed without treating an
incomplete attribution record as a finished binary distribution inventory.

[THIRD_PARTY_NOTICES.md](../THIRD_PARTY_NOTICES.md) records the supplied Zakuro
notice verbatim and the separate 3dsrecomp evidence gap. Do not borrow Zakuro's
copyright line for 3dsrecomp, infer one from commit authors, or label an invented
notice as upstream's. A Cargo `license = "MIT"` declaration is useful licensing
evidence but does not supply the missing copyright notice.

**Remaining distribution question:** which upstream-supplied copyright and full
license notice apply to 3dsrecomp and its ABI at the selected commit? Record an
authoritative source when available and assemble notices for the resolved target
dependency closure before publishing compiled binaries or vendoring those files.
No upstream contact or submission is part of this first build.

Generated source and libraries remain local build products in this milestone.
Even synthetic generated output can contain upstream ABI/support code. Retail
inputs and all retail-derived output remain private under the existing project
rules; a completed third-party notice inventory would not change that boundary.
