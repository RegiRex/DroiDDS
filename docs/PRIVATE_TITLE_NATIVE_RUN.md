# Guarded Linux native comparison

<!-- CodexAstraUlt: Advance the completed private library to a bounded host
execution gate without rebuilding its generated code or promoting Android boot. -->
Dark Moon now has **521/521 validated objects** and a linked, statically validated
Linux library. The owner reports that it has never been loaded or executed.
See the [compilation record](host-tests/dark-moon-compilation-2026-10-28.md).
The next local task is one guarded interpreter/native comparison using that
existing preparation and compilation. No new title source generation or title
compilation is required. The public APK remains 0.0.6/code 7.
Read the [implementation and executed original-fixture record](builds/0.0.7-native-host-comparison.md).

## Local procedure

<!-- CodexAstraUlt: Build only the new host worker from the pinned cached
toolchain, then consume the already completed private compilation unchanged. -->
Safely obtain current `RegiRex/DroiDDS` main, preserving existing work. Build the
new host diagnostic worker with the installed pinned Rust 1.95.0 and cached,
locked dependencies; no new external dependency versions are introduced:

```bash
cargo build --offline --locked --release -p droidds-native-title-tools
cargo test --offline --locked -p droidds-native-title-tools -- --test-threads=1
```

Use the successful preparation run-002 and the **original compilation run-001
directory**, whose `attempts/` now contains the successful resumes. The separate
resume summary directory is not the compilation input. Choose a new output
directory under an existing private parent, outside Git:

```bash
python3 tools/run_compiled_title.py \
  --preparation /path/to/dark-moon-preparation-20261028-run-002 \
  --compilation /path/to/dark-moon-compilation-20261028-run-001 \
  --output /path/outside-git/new-dark-moon-native-comparison
```

Run exactly once with defaults. Stop on the first rejected admission, runtime
blocker, process failure, comparison result, or budget. Preserve every old output
and the new failure/success evidence. Do not bypass a guard, raise a limit, change
the library, regenerate sources, or silently substitute an interpreter-only
result for native execution. No USB or device operation is part of this test.

Return one `dark-moon-native-comparison-summary.md` in a new report location,
including source/worker/input/library identities, admission outcome, each route's
status/reason and counters, exact matched checkpoints, mismatching field names or
the first blocker, configured limits, and the preservation result. Include whether
native instructions actually ran. Keep private inputs, code, objects, raw reports,
and libraries outside Git; omit personal paths and private content from the summary.

## What the new path validates

<!-- CodexAstraUlt: Old artifacts remain historical evidence; runtime admission
adds a new record instead of rewriting earlier false execution/binding flags. -->
The parent revalidates the original preparation, compile contract, every object
receipt, and completed library. It uses the recorded compiler identity; the C
compiler does not run or need to be rediscovered. The six historical Python
compilation-contract files remain unchanged, so existing receipts stay usable.

A new ELF audit follows every entry/module/origin table and pointer, checks
relocations, permissions, indexes, initial mutable metadata and origin hashes
against prepared code. The hash comes from the actual audited bytes. The parent
then copies that exact library and the raw identity components into sealed Linux
memory files. The worker checks seals/lengths and uses the immutable library
descriptor, avoiding a later filename-replacement race. SHA-256 identities are
checked by the trusted parent; the worker independently compares actual loaded
NCCH, exheader, full code, mapped segments and CRO/static bytes with the sealed
components. The input snapshot is read-only filesystem data, rehashed afterward;
this is not a filesystem sandbox or a binary/source attestation.

Native loading happens only after those gates. This route consumes trusted
locally generated libraries; ordinary CRT initialization is permitted. It is not
an untrusted native-plugin sandbox.

## Execution scope and limits

<!-- CodexAstraUlt: A fail-stop immutable-base fence preserves this existing
ABI without pretending to implement safe mutable-code deoptimization. -->
The first native diagnostic supports **Linux with 4 KiB host pages**, on the same
architecture as the library. Before any guest execution, it relocates FCRAM into
an owned page-aligned mapping, rebases all CPU memory tables and makes the main
executable's text pages read-only. Mapping/guard changes are verified before
guest work and native dispatch. State restoration rejects while fenced.

Native execution is restricted to the main executable; dynamic modules continue
in the interpreter. Missing native entries retain interpreter fallback. A write
through an alias, cached native pointer or physical/GPU access cannot silently
modify the protected backing. A mapping violation stops explicitly; a protection
fault can terminate the worker. **SIGSEGV alone remains an unattributed process
failure**, not proof of a code write, leak or memory exhaustion. This diagnostic
does not provide transparent deoptimization or general mutable native code.

The interpreter and native routes run sequentially with fresh separate data
directories, neutral input, a fixed clock, software rendering, strict fault
reporting, and no overlays or native discovery. Defaults per route are:

| Limit | Default |
| --- | --- |
| Outer dispatches | 10,000,000 |
| Guest cycles | 2,000,000 |
| Frame events | 120 |
| Cooperative wall time | 60 seconds |
| Parent worker timeout | 70 seconds |
| CPU per process, summed across its threads | 120 seconds |
| Virtual address space per process | 4096 MiB |
| Individual worker output file | 64 MiB |
| Retained process log tail | 64 KiB |

CPU limits are not summed across descendants; process groups are cleaned up.
Input verification and ELF auditing have separate bounded input/count allowances
and can extend total elapsed time. The file limit is not an aggregate disk quota.
No additional full game copy is created.

Comparison uses exact guest-cycle checkpoints at 100,000, 500,000, 1,000,000 and
2,000,000 where reached, or matching guest-exit cycles. Equal outer dispatch counts
are not equivalent work. Checkpoint data covers active CPU state, selected
scheduler fields, physical-memory/allocation fingerprints, graphics counts and
audio fingerprints; it does not serialize every saved thread or HLE object.
FNV fingerprints are noncryptographic diagnostic observations. A match covers
only that bounded observation, and requires positive native instruction counts.
A difference needs investigation; it does not by itself identify a compiler bug.

`compared / matched`, `different`, and `inconclusive` are diagnostic outcomes,
not successful game boot. A blocked or killed route cannot qualify comparison.
No result here measures Thor/Vulkan performance or closes the Android 0.0.7 gate.
