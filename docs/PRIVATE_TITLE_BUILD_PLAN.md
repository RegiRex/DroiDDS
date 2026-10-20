# Planned 0.0.7 private title build and boot

<!-- CodexAstraUlt: Ground the next milestone in the existing compiler/loader
contracts without treating planning or public fixtures as private-title proof. -->

Design prepared **2026-10-20** (America/New_York). This is implementation planning,
not a completed 0.0.7 build or acceptance result. Promotion remains blocked on the
[0.0.6 interactive gate](device-tests/0.0.6-thor-homebrew.md). The intended result
is a reproducible, locally signed APK that boots one exact owned title into an
interactive menu or identified opening scene on the Thor. It does not establish
sustained playability, Dark Moon correctness or universal ROM loading.

Continue the [existing architecture](ARCHITECTURE.md) and
[versioned roadmap](ROADMAP.md#versioned-path-to-010): reuse the pinned compiler,
ABI, loader, interpreter and PICA runtime. Public releases provide generic tools
and original-fixture packages. Retail inputs, generated C/libraries, private
APKs and captures stay on the owner's Linux computer.

<!-- CodexAstraUlt: Implement the bounded baseline first, before compiler and
native module work can turn an unknown runtime gap into an ambiguous failure. -->
The first implementation slice is the [local reconnaissance tool](PRIVATE_TITLE_RECONNAISSANCE.md):
a stable private input snapshot, strict interpreter/software run, exact metadata
and bounded first-blocker report. It reuses the actual loader and HLE runtime.
It does not yet implement the native compiler/package steps below. Actual local
title evidence is needed before selecting and fixing the first game blocker;
public original fixtures validate the tool, not game compatibility.

## One resolved title identity

<!-- CodexAstraUlt: Prevent compiler/runtime disagreement about the executable,
especially when an update changes code while preserving the base program ID. -->

Introduce one local resolved-title manifest consumed by both the builder and
runtime adapter. It records container type, program ID and revision; source
size/SHA-256; the effective exheader and decompressed executable segment hashes
with their mapped addresses; and each compiled CRO/static module's path and
hash. Bind the generated library to that manifest, exact DroidDS source/lockfile,
compiler options, ABI **4 / generation 3**, toolchain and target. A program ID or
filename alone cannot identify compatible executable bytes. The compiler's
[FNV code hash](../vendor/3dsrecomp/src/build.rs) selects discovery hints; use
SHA-256 for the package's input/artifact identity.

There is a concrete update mismatch to resolve:
[3dsrecomp's reader](../vendor/3dsrecomp/src/rom.rs) rejects update CIAs, while
[the runtime loader](../vendor/zakuro/crates/zakuro-core/src/loader.rs) can attach
an update before mapping code. That loader currently logs an invalid update and
continues without it. **The first private builder should explicitly reject update,
DLC and mod configurations** until a shared resolution path supplies the same
effective code, exheader and module/data overlays to compilation and execution.
Do not compile the base and independently enable an update at runtime, silently
ignore a requested update, or claim support by accepting its filename. If a target
requires an update, record the blocker and implement that resolver before testing
the updated revision.

## Builder, package and data import

<!-- CodexAstraUlt: Reuse code emission and Android packaging primitives while
keeping arbitrary imported data out of the native-library trust boundary. -->

The generic Linux builder should use
[`build::generate`](../vendor/3dsrecomp/src/build.rs) in an explicit, private,
revision-keyed output directory. Generate from the validated resolved input,
compile the emitted sources with the pinned NDK for Android ARM64, retain the
existing floating-point contract, and package an audited title library alongside
the runtime. Reuse the ELF/dependency/alignment and APK audits from
[the probe builder](../tools/build_android_probe.py), with an explicit per-title
inventory rather than weakening the probe's twelve-library rule. Record a local
build report and signed-APK hash. Cancellation or failure must leave the previous
working APK, input and saves intact.

<!-- CodexAstraUlt: Preserve source-review findings as explicit native-builder
work, not as proven runtime failures or completed fixes in reconnaissance. -->
Before enabling this builder, bind or explicitly disable the compiler's automatic
hint inputs; its current `apply_hints` reads owner-local information in addition
to bundled hints. Module discovery must report parse failures instead of dropping
them from the manifest. Neither behavior is exercised by the interpreter-only
reconnaissance tool. Also add a focused executable-remap regression: the current
`Memory::map` sets fast read/write pointers when a permission is present, without
clearing disallowed pointers on a narrower remap. This is a source-review concern,
not a reproduced title failure; test and correct it before general native module
execution. Keep these tasks separate from the first measured private-title blocker.

The APK carries its expected manifest and generated native library in standard
installer-owned native-library storage. Android lets the owner select matching
game data through SAF. Initially, use a cancellable, space-checked import into a
dedicated app-private staging area; validate bounded container structure and
identity, then atomically publish the completed import. Execute against that
validated copy, not a provider file that can change after verification. Selecting
a different revision must produce a clear mismatch result before native
execution. Data import must never load an arbitrary `.so` from the picker.

Packaged generated native code is trusted application code; origin hashes do
not sandbox native plugins. Keep ABI/origin validation and interpreter fallback
for missing compiled entries. The existing
[homebrew native guard](../crates/droidds-runtime-probe/src/homebrew/session.rs)
is deliberately fixture-specific. Generalize protection against executable
writes/remapping and module replacement before enabling affected native paths.
[Runtime CRO placement checks](../vendor/zakuro/crates/zakuro-core/src/recompiled.rs)
alone do not qualify unload/reload, stale lookup or concurrent writers. An
unsupported path needs an accurate interpreter route or explicit stop; it must
not continue with stale native code or omit guest work.

## Durable package, signing and saves

<!-- CodexAstraUlt: Establish owner-controlled upgrade identity before private
save data exists; diagnostic CI signing must not become the product identity. -->

Keep an owner-local signing profile outside Git and build scratch, with a
recoverable local backup. Reuse that keystore on every upgrade; record only its
public certificate fingerprint in build evidence. Do not reuse Uberhar's key or
the public probe's temporary CI signer. A missing key or package/signature
mismatch stops installation without uninstalling or clearing application data.

Choose a stable package per base title/region, for example
`org.droidds.title.t<16-lowercase-hex-program-id>`, and persist its increasing
Android version code independently of build-cache cleanup. Revisions change the
expected input manifest, not the package identity. Bind
[`Config.data_dir`](../vendor/zakuro/crates/zakuro-core/src/lib.rs) to durable
app-private `files/runtime/`, separate from imported inputs and disposable caches.
The current [archive implementation](../vendor/zakuro/crates/zakuro-core/src/services/host_archive.rs)
then places saves under `savedata/<PROGRAM_ID>` and extdata under its own IDs.
Prove upgrade retention with original fixtures before using private saves;
provide explicit backup/export and recoverable migration, never automatic reset.

## Implementation and evidence order

<!-- CodexAstraUlt: Separate public regression work from the private host/Thor
dependency, and keep each selected title's actual blocker independently visible. -->

First implement the shared manifest, validation and local packaging route with
original containers. Public tests should reject wrong revisions/modules,
malformed or truncated data, unsupported updates and stale native code; exercise
cancelled imports and a same-key package upgrade retaining fixture saves. Keep
all existing CPU, Vulkan, homebrew, lifecycle and alignment gates.

Then local Codex runs an exact private host baseline through interpreter and
native paths, records the first reproducible checkpoint or blocker, and builds
the corresponding ARM64 APK. On the explicitly selected Thor, verify installed
APK identity, measured native/fallback execution, actual rendering route,
interactive output/input/audio, normal close and replacement-build data
retention. Initial qualification is **1×**. One owner controls device execution;
review/build agents may work in parallel but benchmarks and installs serialize.
Keep one bounded latest diagnostic report with stage/error and aggregate CPU,
GPU, audio and memory evidence. Do not upload private derived artifacts to CI.

Dark Moon remains the priority reconnaissance target. Also record separate
results for Sonic & All-Stars Racing Transformed and Xenoblade Chronicles 3D;
the latter needs its New 3DS configuration and service/scheduler path checked.
Select the first control title from actual host boot evidence. Another title's
success cannot clear a Dark Moon blocker or imply New 3DS compatibility.

When the 0.0.6 gate passes, local Codex needs the current DroidDS checkout/commit
and local changes; authorized local paths to the exact decrypted title inputs
and any separate updates; title/region/revision metadata derived locally; the
available Linux toolchain, disk space and memory; the owner-local signing
profile's location/public fingerprint; and the Thor's explicit authorized ADB
serial, Android/driver state and repeatable starting scene. It should inspect
existing files and credentials locally, preserve originals, and report missing
inputs or concrete boot blockers. No game upload or secret-key transfer to this
chat is needed, and this plan does not create a cloud-to-device session bridge.
