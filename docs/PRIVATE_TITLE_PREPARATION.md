# Local native-source preparation

<!-- CodexAstraUlt: Advance beyond a repeated interpreted prefix with an actual
builder stage, preserving the separate native execution and Android boot gates. -->
This host tool prepares one owned, decrypted base title for native compilation.
It resolves the executable and modules, checks the runtime reader selects the
same bytes, generates C with the pinned compiler, and records a SHA-256 manifest.
It does not compile or execute a private title, install a library, build an APK,
or enforce the manifest in the runtime yet. The public app remains 0.0.6/code 7.
Read the [implementation and validation record](builds/0.0.7-native-preparation.md)
for actual compiler, worker and coordinator checks.

Run-019 closes the [bounded voice-activation investigation](host-tests/dark-moon-2026-10-22.md#locally-executed-voice-activation-batch-run-019).
The constructor initializes the measured flags; the manager repeatedly observes
an empty list and the selected allocation path is unobserved. No generic audio
correction is justified. Resume that diagnosis when a later phase reaches an
allocation request or populates the list; do not replay the unchanged prefix.
Native preparation is the next independent local task toward 0.0.7.

## Build and prepare

<!-- CodexAstraUlt: Reuse the installed pinned toolchain and established private
snapshot supervisor instead of installing another stack or executing game code. -->
Use current `RegiRex/DroiDDS` main, preserving existing local changes and frozen
diagnostic sources. Build with the existing Rust 1.95.0 and locked dependencies:

```bash
cargo build --offline --locked --release -p droidds-title-builder
python3 tools/tests/test_prepare_private_title.py --worker target/release/droidds-prepare-title -v
```

The second command uses original synthetic data and performs no private-title
execution. Then prepare the existing authorized Dark Moon base image once:

```bash
python3 tools/prepare_private_title.py \
  --input /path/to/owned-base.cci \
  --output /path/outside-git/new-preparation-directory
```

Local Codex should use its known input path and choose an absent output under
the existing private parent. The output parent must already exist. Do not copy
prior configuration, saves, updates, DLC or mods. No additional USB or device
readiness check is needed. The source image and old reports remain unchanged.

The coordinator creates a read-only full input snapshot and owner-only output
directory. Allow space for that copy plus 512 MiB of preparation output. Defaults
are 130 wall seconds, 260 CPU seconds summed across worker threads, and 4 GiB
virtual address space. The existing process supervisor retains bounded log tails
and kills its worker group on timeout/interruption. CPU is per process, not a
combined descendant budget. Each worker file has a 64 MiB limit; the 512 MiB
aggregate inventory limit is checked after generation, not an OS disk quota.
Do not raise limits or repeat private preparation without a concrete reason.

## What is validated

<!-- CodexAstraUlt: Bind the compiler's actual inputs and distinguish logical
segment identity from all bytes the runtime may load into padded mappings. -->
The new strict compiler route rejects declared unreadable or malformed modules,
cyclic/ambiguous RomFS paths, unsafe or duplicate module names, truncated code
segments and unsupported module layouts. Admission limits are explicit; rejection
does not prove a title is corrupt. Legacy compiler entry points retain their
existing behavior. This preparer supplies no mods, overrides or discovery hints,
including bundled and owner-local hints. Missing discovered entries remain a
future interpreter-fallback concern, never permission to skip guest work.

Both readers must agree on the NCCH header, effective first 0x400 exheader bytes,
full decompressed executable, segment layout, and each selected CRO/static.crs
path and raw bytes. The same resolved program collection feeds generation.
The coordinator then validates exact output inventory and descriptor consistency,
hashes actual files and logical segment slices, and verifies the input, snapshot,
worker and source context stayed stable.

NCCH format version, exheader remaster version and CIA title version are recorded
separately. Container type comes from bytes, not filename. Update/DLC identities
are rejected for bare partitions as well as archives. A source SHA-256 binds the
exact input revision; a program ID alone is insufficient.

## Outputs and next decision

<!-- CodexAstraUlt: Preserve a small unambiguous preparation outcome while
keeping generated sources, raw identity bytes and input snapshots private. -->
Successful output contains:

- `report.json`: outcome, resource limits, process result and preservation checks.
- `manifest.json`: canonical input/tool/source identity, component and generated
  file hashes, logical segment hashes, ABI 4/generation 3 and disabled hints.
- `prepared/`: generated C/headers, raw identity components and worker metadata.
- The full input snapshot and bounded `worker.log`.

`prepared` means source preparation succeeded. The manifest explicitly records
`runtime_binding_enforced=false` and `guest_execution_performed=false`. Recorded
source identity does not attest an arbitrary worker binary. Use the locally
built worker. Full decompressed-code hashing includes padding/tails; logical
segment hashes alone are not a complete loaded-memory image.

Failure preserves partial output and creates no success manifest. Keep it for
diagnosis; do not weaken validation or omit a module to get a result. Review any
generic correction with an original failing fixture before a matched retry.
All snapshots, generated code, module bytes, raw reports and future private
libraries stay outside Git and CI.

Return a short `dark-moon-preparation-summary.md` with source/tool/input identity,
status and first rejection if any, resolved module count, generated file/byte
counts, elapsed time/limits and the next concrete action. Omit personal paths,
module names, game bytes and generated code from the shareable summary. A pass
unblocks native compilation and a separate manifest-consumption/guarded host
comparison stage; Android packaging and Thor boot remain later gates.
