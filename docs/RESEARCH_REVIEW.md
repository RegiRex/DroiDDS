# Research pack review and source reconnaissance

<!-- CodexAstraUlt: Preserve the uploaded research and separate independently inspected source behavior from proposals, unverified compatibility and future implementation. -->

Reviewed 2026-10-17 for RegiRex/DroidDS. The repository initially contained only
`README.md` at `7bed6324c5b27c4ae4a4e6fd400432c9ab44db01`.

<!-- CodexAstraUlt: Preserve this reconnaissance snapshot while linking the later
implementation evidence so historical untested statements are not current status. -->
This is the initial source-review record. Subsequent implementation and actual
tests are recorded in [the first build report](builds/0.0.1-foundation.md).

## Input inventory

Uploaded archive: `3ds-recomp-codex-pack.zip` (attachment path used a `1-` prefix).
Archive SHA-256:
`e1aee7a13c8bfa55f990082ae2f6c6e5ff0a5b64d73051927a217b9c4c61fa29`.
All ten entries listed in its `SHA256SUMS.txt` passed verification. The unchanged
files are retained in [research/2026-10-17](research/2026-10-17/00_README.md).

| Input | Use in DroidDS plans |
| --- | --- |
| 00 README | Starting proposal and scope, assessed against source |
| 01 technical overview | CPU/HLE/PICA separation, architecture options and limitations |
| 02 specification | Requirements and acceptance criteria, narrowed into staged gates |
| 03 projects/gap matrix | Reuse candidates; no assumption that analogies prove Android readiness |
| 04 references | Source locations and candidate commits; not every external claim was revalidated |
| 05 prompt pack | Bounded task/report format; embedded prompts were not executed |
| 06 backlog | 119-ticket reference catalog, reduced to the current 16-ticket queue |
| 07 Uberhar relationship | Separate repository, device methodology and lean-diagnostics requirements |
| Master document | Exact copies of the eight split documents plus contents/part wrappers; no unique technical requirements |
| MANIFEST / SHA256SUMS | Archive integrity and inventory |

Original research statements remain unchanged for provenance. The active
architecture, roadmap and backlog incorporate the corrections below. Pack examples
and normative language are proposals, not proof of implemented behavior or new
authorization. Uncorroborated historical game anecdotes were not adopted as facts.

## Verified candidate source pins

Both commits were fetched and inspected, and matched upstream HEAD at this review.
This is source availability evidence, not a reproducible build result.

| Component | Pin and inspected metadata |
| --- | --- |
| [3dsrecomp](https://github.com/fearkov/3dsrecomp/tree/c3f21f94ba50d688025febc8974ff348d471b587) | `c3f21f94ba50d688025febc8974ff348d471b587`; package 0.1.0; declared Rust minimum 1.88; ABI 4, generation 3 |
| [Zakuro](https://github.com/fearkov/zakuro/tree/412900a5a020301da15c1cc382585e05a489a535) | `412900a5a020301da15c1cc382585e05a489a535`; workspace 0.2.27; declared Rust minimum 1.95 |
| [Verifier's Zakuro dependency](https://github.com/fearkov/3dsrecomp/blob/c3f21f94ba50d688025febc8974ff348d471b587/Cargo.lock#L119) | `3e853d5a091dab9b7bfb3b0f41e3457d42ff4bb6`; differs from runtime candidate |

Rust minimums are source declarations. Installed toolchains, dependency resolution,
NDK version and actual build success remain M0 work. Pin exact tools and lockfiles;
do not use a moving `stable` label as the sole reproducibility record.

## Source findings that change the plan

| Finding and evidence | Consequence |
| --- | --- |
| Existing generated-C loader/ABI and interpreter fallback are real: [ABI header](https://github.com/fearkov/3dsrecomp/blob/c3f21f94ba50d688025febc8974ff348d471b587/abi/recomp.h#L10), [interface](https://github.com/fearkov/3dsrecomp/blob/c3f21f94ba50d688025febc8974ff348d471b587/docs/interface.md) | Reuse actual ABI. The pack's conceptual callback trait is not the binary contract; SVC is an execution exit, not its invented callback. |
| Structured compiler invocation already exists: [compile.rs](https://github.com/fearkov/3dsrecomp/blob/c3f21f94ba50d688025febc8974ff348d471b587/src/compile.rs#L37) | Extend `Compiler { program, leading }` for explicit NDK targets; preserve semantic flags and inspect generated ELF. |
| Explicit origin checking uses fast per-piece hashes; static linked library lacks origins: [ABI loading](https://github.com/fearkov/3dsrecomp/blob/c3f21f94ba50d688025febc8974ff348d471b587/abi/src/lib.rs#L325), [check](https://github.com/fearkov/3dsrecomp/blob/c3f21f94ba50d688025febc8974ff348d471b587/abi/src/lib.rs#L395) | Do not equate load-time checks with continuous code-write protection. Require origin metadata and an executable-mutation policy; package SHA-256 is separate. |
| Verifier masks some NaN-shaped differences and skips comparison at instruction limits: [NaN comparison](https://github.com/fearkov/3dsrecomp/blob/c3f21f94ba50d688025febc8974ff348d471b587/src/verify.rs#L77), [register/memory comparison](https://github.com/fearkov/3dsrecomp/blob/c3f21f94ba50d688025febc8974ff348d471b587/src/verify.rs#L360), [limit handling](https://github.com/fearkov/3dsrecomp/blob/c3f21f94ba50d688025febc8974ff348d471b587/src/verify.rs#L555) | Establish strict integer/memory oracle, justified float policy and explicit inconclusive outcomes before trusting differential results. |
| Budget exits permit stale dead state and work in basic blocks: [interface budget contract](https://github.com/fearkov/3dsrecomp/blob/c3f21f94ba50d688025febc8974ff348d471b587/docs/interface.md#L293) | Define comparison checkpoints and test tiny-budget progress; instruction budgets are not timing accuracy. |
| A missing generic pipeline is compiled synchronously: [startup](https://github.com/fearkov/zakuro/blob/412900a5a020301da15c1cc382585e05a489a535/crates/zakuro-gpu/src/raster/hardware.rs#L1735), [pipeline lookup](https://github.com/fearkov/zakuro/blob/412900a5a020301da15c1cc382585e05a489a535/crates/zakuro-gpu/src/raster/hardware.rs#L2816) | Generic+async architecture exists, but universal no-gameplay-compile behavior is not established. Audit ready fallback coverage before claiming it. |
| No-worker paths can compile synchronously; helper compute pipelines are lazy: [translation request](https://github.com/fearkov/zakuro/blob/412900a5a020301da15c1cc382585e05a489a535/crates/zakuro-gpu/src/raster/hardware.rs#L3211), [helper pipelines](https://github.com/fearkov/zakuro/blob/412900a5a020301da15c1cc382585e05a489a535/crates/zakuro-gpu/src/raster/hardware.rs#L4649) | Include worker failure and non-fragment creation in cold-render tests; no narrow specialization-only claim of zero stutter. |
| Vulkan workers cap at 1–3 but job/result storage and retained pipelines lack corresponding admission bounds: [queues](https://github.com/fearkov/zakuro/blob/412900a5a020301da15c1cc382585e05a489a535/crates/zakuro-gpu/src/raster/hardware.rs#L1011), [workers](https://github.com/fearkov/zakuro/blob/412900a5a020301da15c1cc382585e05a489a535/crates/zakuro-gpu/src/raster/hardware.rs#L1058), [retention](https://github.com/fearkov/zakuro/blob/412900a5a020301da15c1cc382585e05a489a535/crates/zakuro-gpu/src/raster/hardware.rs#L1409) | Move resource limits and teardown tests to the first renderer milestone; this is a design risk, not a measured DroidDS leak. |
| Separate default PICA CPU JIT spawns per unseen program; clearing its map is not a job bound: [feature default](https://github.com/fearkov/zakuro/blob/412900a5a020301da15c1cc382585e05a489a535/crates/zakuro-gpu/Cargo.toml#L8), [JIT cache/jobs](https://github.com/fearkov/zakuro/blob/412900a5a020301da15c1cc382585e05a489a535/crates/zakuro-gpu/src/shader/jit.rs#L252) | Track and bound both compiler families. Game AOT does not eliminate PICA shader processing. |
| Current backend requires Vulkan 1.3, depth clamp, push descriptors, D24S8 and other selected features: [capabilities](https://github.com/fearkov/zakuro/blob/412900a5a020301da15c1cc382585e05a489a535/crates/zakuro-gpu/src/raster/hardware.rs#L5326) | API level alone is insufficient. Vulkan 1.1 compatibility is not implemented by this plan. Qualify actual Thor features. |
| Cache writes already use a temporary file and rename; 64 MiB limit is read-side and names are title-based: [cache persistence](https://github.com/fearkov/zakuro/blob/412900a5a020301da15c1cc382585e05a489a535/crates/zakuro-gpu/src/raster/hardware.rs#L540) | Preserve atomic replacement; add identity/fingerprint, write limits and mobile paths rather than reimplementing persistence wholesale. |
| Existing 180-state GPU parity test can return early if Vulkan init fails: [test](https://github.com/fearkov/zakuro/blob/412900a5a020301da15c1cc382585e05a489a535/crates/zakuro-gpu/src/raster.rs#L4614); C layout test can also skip missing compiler: [layout test](https://github.com/fearkov/3dsrecomp/blob/c3f21f94ba50d688025febc8974ff348d471b587/abi/src/lib.rs#L552) | Extend useful tests; make required execution explicit. Successful test command alone does not establish either backend ran. |
| Desktop frontend bundles desktop-oriented window/dialog/input/audio dependencies: [frontend manifest](https://github.com/fearkov/zakuro/blob/412900a5a020301da15c1cc382585e05a489a535/crates/zakuro/Cargo.toml#L22) | Build a native host around core crates; prioritize a small Bionic/loader probe before full frontend work. |

Zakuro's [compatibility list](https://github.com/fearkov/zakuro/blob/412900a5a020301da15c1cc382585e05a489a535/COMPATIBILITY.md)
reports several relevant control candidates, including Monster Hunter 4 Ultimate.
It lists Sonic Generations, not Sonic All-Star Racing Transformed. Dark Moon is
not listed. Neither absence nor another game's entry establishes DroidDS behavior.

## Provenance and distribution status

Zakuro includes an [MIT license notice](https://github.com/fearkov/zakuro/blob/412900a5a020301da15c1cc382585e05a489a535/LICENSE).
The inspected 3dsrecomp main/ABI manifests declare MIT, but the pinned tree contains
no LICENSE/NOTICE file. Record that gap and resolve required notice provenance
before redistributing source/binaries; do not manufacture attribution. Transitive
dependency licensing still needs an inventory. No upstream implementation was
imported into DroidDS by this planning work.

Uberhar/Azahar code must not be silently relicensed into the new project. Reuse of
code requires a specific license decision; test methodology and independently
written fixtures can be shared without transplanting the renderer. No submissions
to upstream projects or messages to their maintainers were made.

## What this review does not establish

No compiler/runtime build, synthetic execution, Android ABI test, private game run,
memory benchmark or performance improvement was performed. No claim about every
third-party reference was independently verified. The source audit identifies
credible reusable components and concrete proof obligations, not a ready emulator.
