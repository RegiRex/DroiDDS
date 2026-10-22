# Private title reconnaissance on Linux

<!-- CodexAstraUlt: Introduce the implemented bounded host diagnostic slice
without treating it as the planned native-title builder or Android milestone. -->
As of 2026-10-20 (America/New_York), `tools/run_private_title.py` runs an owned,
decrypted base title through the selected loader, interpreter and software
renderer. It uses the new `droidds-private-title` host worker. The purpose is to
find the first reproducible loader, CPU or service blocker in an actual title,
starting with Luigi's Mansion: Dark Moon. No private-title baseline has yet been
independently validated by this cloud work. The owner subsequently supplied a
[paired local execution summary](host-tests/dark-moon-2026-10-22.md): the default
and ten-second emulated-time runs both ended at `0x004B23A8` with zero draws.
The next measurement is the bounded scheduler/SVC trace below, using the same
longer limits. This does not generate native title code, produce a
0.0.7 APK or measure Thor performance. The combined Android evidence, including
the owner's steady-tone confirmation, is recorded in
[the corrected 0.0.6 report](device-tests/0.0.6-correction2-thor.md).

## Run it in the existing local Codex session

<!-- CodexAstraUlt: Let the local agent perform the commands with authorized
paths instead of requiring a game upload or manual command transcription. -->
Local Codex on the owner's Nobara laptop can build and run this tool. It needs
the actual authorized file path; no cloud upload, chat connection or USB session
is required. If that path is not known, ask the owner for it. Preserve checkout
changes and existing game saves. Read [BUILDING.md](BUILDING.md) for the host
toolchain, including Python 3.11 or newer and the pinned Rust 1.95.0.

From the DroidDS checkout, build the worker:

```bash
cargo build --locked --release -p droidds-title-tools --bin droidds-private-title
```

Use a decrypted base CXI/NCCH (`.cxi`/`.ncch`), cartridge NCSD
(`.3ds`/`.cci`) or CIA (`.cia`).
An encrypted image or an update/DLC archive is not a supported base input.
Keep the original outside Git. Choose an existing private parent directory
outside every Git checkout, then a **new, absent** run directory under it.
The coordinator rejects existing output directories and symlink paths; it
does not clear or reuse another run. Replace these example paths locally:

```bash
python3 tools/run_private_title.py \
  --input /home/OWNER/DroidDS-private/dark-moon-base.cxi \
  --output /home/OWNER/DroidDS-private/dark-moon-run-001 \
  --worker target/release/droidds-private-title
```

The explicit worker path matches the release build and the coordinator's
default. Use release optimization so debug overhead does not consume the short
diagnostic budget unnecessarily. Start with the default budgets;
retain a failed run before making one targeted change. Give every rerun a new
output directory. Do not copy existing saves, updates, DLC, mods, shader caches,
texture packs or configuration into the new run.

<!-- CodexAstraUlt: Preserve distinct title/model gates rather than inferring
New 3DS compatibility or relative speed from a selected model flag. -->
The requested model defaults to `old`; the loader can resolve a New 3DS title
to `new`, and the report records both values. For Xenoblade Chronicles 3D use
`--model new` explicitly. Test Sonic & All-Stars Racing Transformed separately;
Monster Hunter 4 Ultimate remains optional. Each needs its own authorized local
file, revision identity and result. A model choice does not qualify New 3DS
services, scheduling or a game's boot.

## Bounds and execution contract

<!-- CodexAstraUlt: State the actual coordinator/worker ceilings and fault
boundary so bounded progress cannot be mistaken for skipped unsupported work. -->
The input limit is 8 GiB. The coordinator streams a private read-only snapshot
and checks input, snapshot and worker identities before and after execution.
Allow disk space for a complete input copy plus runtime output. The report
records the worker hash and checkout/source identity; it does not attest that
an arbitrary binary was built from those sources. Build the worker locally.

| Option | Default | Maximum setting |
| --- | --- | --- |
| `--max-steps` | 1,000,000 | 1,000,000,000 |
| `--max-cycles` | 268,111,856 guest cycles | 26,811,185,600 |
| `--max-frames` | 120 | 6,000 |
| `--max-seconds` | 30 seconds | 300 |
| `--timeout` | `max-seconds + 10` seconds | 310 |
| `--memory-mib` | 4,096 MiB | 16,384 MiB |

Guest budgets are checked at dispatch boundaries. Cycle/frame work inside a
`System::step` can pass a requested boundary; the actual cycle overrun is
reported. This is not an instruction-by-instruction hard cycle limit.
`--timeout` bounds the worker process, including loading and a stuck dispatch;
snapshot preparation is separate. `--memory-mib` limits worker virtual address
space, not measured RSS or guest RAM, and its minimum is 256 MiB. The supervisor
also limits CPU time, each worker-created file to 64 MiB and retained log bytes. The per-file cap is
not an aggregate directory quota. These are resource limits, not an
operating-system sandbox for an untrusted executable.

Native-library discovery, hardware rendering, updates and DLC are disabled.
A fresh `runtime-data/` directory prevents inherited configuration and saves;
controller input stays neutral and the clock is fixed. Images and audio are
not captured.
The worker stops on observed undefined instructions/breakpoints, unsupported
SVCs/services, memory faults, prefetch aborts or fatal guest errors. Diagnostics
are checked after each full `System::step`; frame/audio hooks can precede one
CPU instruction within that step. This is not a guarantee that every error
halts before any further guest work, nor proof that implemented HLE paths are
complete. Do not bypass a blocker to manufacture boot progress.

## Read the outcome and return a small summary

<!-- CodexAstraUlt: Keep diagnostic completion separate from game success and
keep snapshots, raw logs and generated runtime data on the owner's computer. -->
Each created run retains `report.json`, the coordinator's final result. A
started worker normally also produces `worker-report.json`, a bounded
`worker.log` tail (up to 64 KiB), an `input.*` snapshot retaining the accepted
input extension, and fresh `runtime-data/`. Early failures can leave fewer
files; preserve what exists.
The input snapshot is a full game copy, not a shareable diagnostic artifact.
Do not upload the run directory or commit its contents.

| Result | Interpretation |
| --- | --- |
| `blocked` | An observed runtime operation needs investigation; inspect the blocker identity and counters. |
| `budget_exhausted` | A configured bound was reached; no interactive boot or compatibility conclusion follows. |
| `guest_exited` | The guest called exit; this alone does not show a successful opening scene. |
| `load_error` / `internal_error` / `worker_failed` | Loading, the worker, or its process failed; retain the failure rather than treating zero counters as a pass. |
| `rejected` / `input_changed` | Preflight, report validation or identity checks failed; do not use the run as accepted execution evidence. |
| `timed_out` / `interrupted` | The supervisor ended or interrupted the worker; the run is incomplete. |

Exit code 0 means a validated diagnostic outcome (`blocked`, `budget_exhausted`
or `guest_exited`), **not a passed game test**. Other diagnostic failures return
1; a worker timeout returns 124 and interruption returns 130. Invalid command
syntax is also a failure. Read `status` and `reason`, not just the process code.

Local Codex should inspect the private reports and prepare a short, reviewable
summary with source/lockfile and worker identities, title/revision identity,
requested/resolved model, limits, status/reason, first blocker identifier and
PC where available, instructions/cycles/frames and any cycle overrun,
service/memory-fault counters, and the next concrete fix. Retain the full input
hash locally for rerun binding.
Omit personal paths, raw guest strings, game data, derived code, images and
audio from anything shared. Review even a small summary before publishing it.

Guest-region peaks are samples after loading, at frames and at stopping; they
are not whole-process, renderer or driver memory measurements. Interpreter and
software-renderer timings cannot predict native/Vulkan speed on the Thor.
Neutral-input execution cannot establish the opening cutscene's visuals,
controls or playability. Once the first real-title blocker is measured, fix it
with a generic regression where possible and rerun the same private baseline.
Native generation, private APK packaging and hardware validation remain in
[the private title build plan](PRIVATE_TITLE_BUILD_PLAN.md).

## Opt-in scheduler/SVC trace

<!-- CodexAstraUlt: Collect bounded early-startup evidence without enabling
continuous logging or changing the kernel behavior being investigated. -->
For the next Dark Moon run, rebuild the worker from the updated source and add
`--trace-scheduler` to the same run-003 limits. This switches on a host-only
measurement; it changes neither the run's strict fault policy nor its scheduling
or service responses. The ordinary worker default and Android frontends leave
tracing disabled. No additional dependency or toolchain version is required.

```bash
python3 tools/run_private_title.py \
  --input /home/OWNER/DroidDS-private/dark-moon-base.cci \
  --output /home/OWNER/DroidDS-private/dark-moon-run-004 \
  --worker target/release/droidds-private-title \
  --max-steps 10000000 --max-cycles 2681118560 --max-frames 1200 \
  --max-seconds 120 --timeout 130 --trace-scheduler
```

Use the actual authorized private paths and an absent output directory. The input
hash should match the earlier baseline; the rebuilt worker has a new hash. Keep
both identities in the local report. A trace-disabled run remains available for
checking identical execution counters if the enabled run behaves differently.

The report's `diagnostic_trace` retains the first 64 and last 128 nonoverlapping
events, bounded SVC counts, omission counts, and a final snapshot of up to 64
threads with at most eight wait objects each. Deferred-call correlation admits
at most 64 pending threads and reports dropped entries. Events record scalar
SVC argument registers r0-r5, returned registers r0-r3, actual interpreter call
PCs, thread selection and resumed waits. No raw guest strings, instructions,
memory dumps, images or audio are collected. A syscall's returned r0 is not
universally a result code; some calls return data. A blocked call has no observed
return until that thread resumes. Native SVC PCs are not inferred from compiled
block entry points, and native execution remains disabled in this worker.

Inspect startup queries and repeated calls leading to `0x004B23A8`, final thread
states, wake deadlines and wait-object state. `services_seen` counts acquired
service handles rather than all earlier kernel/IPC activity. Report a concrete
error or repeated wait without calling a lone PC or cached scheduler flag a
deadlock. The trace has no guest save/restore support; this tool uses a fresh
process. Its storage is bounded, and it does add diagnostic work when enabled;
trace timings are not performance benchmarks.
