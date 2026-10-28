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
Run-004's bounded trace identifies repeated one-millisecond sleeps with working
wake deadlines. Run-005 clears that wait after the
[shared-page readiness correction](builds/0.0.7-shared-page-ready.md), reaches
five services and 80 IPC calls, then exhausts its dispatch budget at `0x003B4FD8`.
Run-006's CPU sampling preserves those counters and shows a repeated 12-address
ARM pattern, but its sparse registers do not measure individual loop iterations.
The subsequent local batch reports that loop clears and fixes a later offline
`IsChild` blocker in `8c15ce2`. Its post-fix run reaches 100 million steps at
`0x0018806C`, with 268 command lists, zero draws and silent PCM. Runs 010–012
confirm table/stream/checksum progress and no draw requests in those
setup lists. Batch-003 then observes resource completion, followed by 95,458 draws
before run-014 stops at 500 million steps. Batch-004 then inspects a preparation
panel and a dark scene with a brightening window; bottom captures remain black.
Its partial audio checkpoint shows mixer updates but no consumed voice settings
or source samples. Both runs were killed. Run-016's accounted CPU time exceeds
the configured 131-second hard limit, consistent with CPU-limit enforcement but
without kernel attribution. The current [voice-publication investigation](LOCAL_DARK_MOON_DSP_HANDOFF.md)
follows guest writes through DSP bank publication/consumption with an explicit
CPU allowance. Earlier failures and all private evidence remain preserved.
This does not generate native title code, produce a
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
cargo build --offline --locked --release -p droidds-title-tools --bin droidds-private-title
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
| `--cpu-seconds` | `ceil(timeout) + 1` CPU seconds | 311 |
| `--memory-mib` | 4,096 MiB | 16,384 MiB |

Guest budgets are checked at dispatch boundaries. Cycle/frame work inside a
`System::step` can pass a requested boundary; the actual cycle overrun is
reported. This is not an instruction-by-instruction hard cycle limit.
`--timeout` bounds the worker process, including loading and a stuck dispatch;
snapshot preparation is separate. `--memory-mib` limits worker virtual address
space, not measured RSS or guest RAM, and its minimum is 256 MiB.

<!-- CodexAstraUlt: CPU time accumulates across threads independently of wall
time; make the optional parent-only allowance and its legacy default explicit. -->
`--cpu-seconds` sets both soft and hard process CPU limits, counting all threads
in each process. It is independent of the parent wall deadline and is not a
combined descendant-tree budget. Omitting it preserves the prior derived cap;
for `--timeout 130`, that remains 131 CPU seconds. The resolved value appears in
`requested.cpu_seconds`, and successful child setup records launch soft/hard limits
in `process.cpu_limit`. This option is not forwarded to the Rust worker and does
not change its guest budgets or validation. A SIGKILL remains `worker_signal_9`;
the cap's presence alone cannot identify why a process was killed. See the
[correction and verification record](builds/0.0.7-cpu-budget.md).

The supervisor also limits each worker-created file to 64 MiB and retained log bytes. The per-file cap is
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
`--trace-scheduler` enables a host-only measurement without changing the run's
strict fault policy or scheduling responses. The ordinary worker default and
Android frontends leave tracing disabled. No additional dependency or toolchain
version is required. The completed run-006 also enabled CPU progress sampling
as described below. This command records that experiment; the current task is
the [local investigation batch](LOCAL_DARK_MOON_INVESTIGATION.md).

```bash
python3 tools/run_private_title.py \
  --input /home/OWNER/DroidDS-private/dark-moon-base.cci \
  --output /home/OWNER/DroidDS-private/dark-moon-run-006 \
  --worker target/release/droidds-private-title \
  --max-steps 10000000 --max-cycles 2681118560 --max-frames 1200 \
  --max-seconds 120 --timeout 130 --trace-scheduler --trace-cpu-progress
```

For a new experiment, use the actual authorized private paths and an absent
output directory. Preserve the input identity and record any rebuilt worker's
new hash. Run-006 compared counters against run-005 to check that sampling
preserved execution. Follow the current batch's bounds for subsequent runs;
do not increase limits to work around a repeated wait or unsupported operation.

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

Run-005 already clears the repeated sleep at `0x004B23A4`. Continue reporting
the stop/blocker, final PC, service activity, draws/audio, execution counters
and sampled memory. `services_seen` counts acquired service handles rather than
all earlier kernel/IPC activity. Report a concrete
error or repeated wait without calling a lone PC or cached scheduler flag a
deadlock. The trace has no guest save/restore support; this tool uses a fresh
process. Its storage is bounded, and it does add diagnostic work when enabled;
trace timings are not performance benchmarks.

## Opt-in CPU progress sampling

<!-- CodexAstraUlt: Observe scalar CPU progress at bounded intervals while
leaving emulated execution, private game content and normal frontends alone. -->
`--trace-cpu-progress` is independent of `--trace-scheduler`; both may be enabled
for the same run. The new `cpu_progress` report section contains an initial
state and one periodic state every 65,521 **dispatch steps**, retaining the
first 16 and latest 112 without overlap. `samples_seen` and `samples_omitted`
account for discarded periodic states. A separate `final` state is always
retained after completed execution, even if it stops before the first interval.
Early loader failures have no CPU progress snapshot.

Each state records steps, cycles, interpreted-instruction count, live registers
r0-r15, CPSR, current thread ID/guest ID and scheduler flags. The final
`recent_dispatches` array contains at most 64 dispatch addresses, oldest first,
with ARM/Thumb mode decoded separately. These are addresses, not instruction
bytes. The sampler reads no guest memory, enables no unbounded profiler and
writes no continuous log. Normal Android frontends do not include this host tool.

Live r15 is the post-dispatch CPU PC, not necessarily the instruction just
executed. Thread metadata describes the current scheduler state; it does not
attribute every recent dispatch to that thread. Idle dispatches can retain old
registers, so compare interpreted-instruction counts as well. Trace activity
adds host overhead; its wall time is not a performance benchmark.
Periodic samples precede the worker's per-frame input update; that update can
change scheduler flags before the final snapshot at the same dispatch count.

Run-006 used the command above. Its result is recorded in
[the host evidence](host-tests/dark-moon-2026-10-22.md#owner-reported-run-006-cpu-progress);
do not repeat it unchanged as the next task. When interpreting progress traces,
compare recurring PCs and changes in registers across the retained
states near `0x003B4FD8`. Return the final recent address pattern and a compact
table of the last relevant snapshots: steps/instructions/cycles, thread identity,
PC, and registers that change. A changing pointer or count supports active work;
neither that change nor an unchanged sampled state proves correct completion or
a deadlock. The local agent may still need a focused follow-up to identify the
operation. Keep raw reports and any private instruction analysis local.
