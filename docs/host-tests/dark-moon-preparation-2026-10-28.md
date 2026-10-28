# Dark Moon native-source preparation

<!-- CodexAstraUlt: Preserve the owner's local result separately from cloud
fixture validation and from unperformed native execution or Android testing. -->
Reported by the owner on 2026-10-28 (America/New_York), from source `5c73453`.
The local summary remains in the owner's preparation run-001 directory; neither
the complete report nor generated code was uploaded to this cloud checkout.

- The local original-fixture checks reportedly passed all 111 checks.
- Exactly one private preparation rejected: `prepared output exceeds aggregate bound`.
- Retained generated output: **522 files**, comprising **520 C files and two
  headers**, totaling **679,996,925 bytes** (about 648.5 MiB).
- The configured aggregate allowance was 512 MiB. Output was unvalidated and
  **no success manifest** existed. No retry or allowance increase occurred.
- The owner reports the original game, existing work and frozen diagnostics
  were preserved. No guest execution, native library or APK is established.

<!-- CodexAstraUlt: State what source inspection proves without treating a C
expansion ratio or file count as private-title semantic validation. -->
Source review finds the old generator retained every C file in memory, wrote the
whole set, then checked the worker's output allowance. Thus retained files could
exceed the reserved output budget before rejection. That is a tooling defect;
this report does not demonstrate a game/runtime memory leak. The generator
already writes declarations into shared headers and splits code into roughly
5,000-instruction source chunks. The reported size is plausible expansion into C,
but the private output was not available here to rule out all redundant code.

The correction streams completed files through a bounded writer, includes the
success descriptor in admission, and removes a redundant local-register analysis
pass used only to discover interpreter resume points. It preserves generated
code semantics and keeps the default 512 MiB allowance. The measured size
justifies one explicit 1024 MiB preparation attempt under the unchanged CPU,
wall-time and memory limits. The [local procedure](../PRIVATE_TITLE_PREPARATION.md)
is the next task; native compilation and runtime binding remain later gates.

## Successful second attempt

<!-- CodexAstraUlt: Advance from the owner's successful local preparation without
claiming independent possession of its private manifest or binary equivalence. -->
The owner subsequently reports success on `67525ef`, with `--prepared-mib 1024`:

- **522 generated files**, totaling **679,996,925 bytes**.
- Largest generated file: **23,183,997 bytes**.
- No rejection; a validated preparation manifest was created.
- All **127 original-fixture checks** reportedly passed.
- Other limits, previous outputs and frozen sources were preserved. No private
  game execution occurred. The local summary remains in preparation run-002.

The file count and aggregate size match run-001. Per-file old/new hashes were not
supplied, so that agreement is size evidence, not an independent private-output
byte comparison. The cloud's original-fixture byte comparison is recorded
[separately](../builds/0.0.7-preparation-streaming.md).

This closes the private source-preparation gate. The next task is
[bounded host native compilation](../PRIVATE_TITLE_COMPILATION.md), using the
existing successful preparation rather than generating or copying the game again.
Runtime identity enforcement, code freshness, native execution and Android boot
remain separate gates.
