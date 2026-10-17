# Building the CPU foundation

<!-- CodexAstraUlt: Document the first real, source-pinned host build without
conflating it with an Android runtime, retail title builder or graphics proof. -->

The first executable is `droidds-foundation` version **0.0.1**. It is a Linux
synthetic correctness harness. It generates and compiles original ARM/Thumb
instruction examples with 3dsrecomp, loads the resulting native library through
the upstream ABI, and compares it with the selected Zakuro interpreter and
hand-derived expected state. It does not accept retail inputs or arbitrary native
libraries. Android, HLE services and GPU rendering are not included yet.

## Prerequisites and build

Use a Linux host with Git, Python 3.11 or newer, a working C compiler and Rustup.
Install the exact Rust toolchain selected by the repository:

```bash
rustup toolchain install 1.95.0 --profile minimal --component rustfmt,clippy
cd /path/to/DroidDS
cargo fetch --locked
python3 tools/build_foundation.py --jobs 2
```

The runner records the actual C compiler and rejects a missing compiler. The first
cloud build uses Debian GCC 14.2.0. Other compilers/hosts require their own result;
the locked Rust/dependency graph does not promise identical binary bytes across
different C toolchains or system libraries. `CC` may name one compiler executable
or an absolute path. This runner deliberately does not accept shell command strings
or additional flags in `CC`.

Each invocation creates a new `out/foundation-<timestamp>/` directory. To choose a
specific **new** directory, use `--output out/my-result`. Existing results are never
cleared or reused. No server, game, firmware, Android SDK or Vulkan device is needed
for this CPU milestone.

The runner performs:

1. Rust/C compiler identity and exact active dependency-pin checks.
2. Python tests that reject changed pins, permissive-verifier activation and
   incomplete proof reports.
3. Rust formatting and Clippy checks.
4. Actual selected upstream/compiler/ABI/interpreter tests and DroidDS tests.
   A missing C-layout check is a failure, even if upstream calls it a test pass.
5. A release build and the synthetic native/interpreter proof, with a wall-clock
   watchdog and exact required-case/report checks.

Read `build-report.json`, command logs and `synthetic/report.json` in that run's
directory. The report binds results to SHA-256 hashes of the build inputs and
records the ABI, generation, compiler and dependency identities. Interrupted,
timed-out or incomplete required cases cannot qualify the build. Timing counters
are workload bookkeeping, not handheld performance measurements.

## Current proof and limits

| Case | Required behavior |
| --- | --- |
| ARM integer/memory | Arithmetic, condition flags, predication and exact stores/loads |
| Thumb integer/memory | Thumb execution and exact state/memory at an SVC checkpoint |
| Missing native entry | Native branch reaches intentionally undiscovered code; three interpreter steps complete it |
| ARM to Thumb | Real native entry lookup changes instruction state without interpreter fallback |
| Negative controls | NaN-shaped integer/register and memory changes fail comparison; infinite guest loop is incomplete; worker timeout is enforced |

Comparisons include exposed user registers/flags, VFP storage, TLS, exclusive
monitor and the full 64 KiB synthetic memory image. Preserved VFP storage is not
VFP arithmetic coverage. This small bus uses checked callbacks, not direct memory
pages. CRO lifecycle, writable executable invalidation, broad instruction
semantics, HLE, graphics and Android remain subsequent work.

The harness builds each synthetic library itself and checks generation/origin
metadata before execution. It is not a sandbox for untrusted native `.so` files.

## CI and artifacts

`.github/workflows/foundation.yml` runs the same checks on Linux for source changes.
CI success is separate from a local build result. It does not publish an APK or
compiled third-party binary. Build outputs, generated C/shared libraries and local
logs stay ignored. Public source includes the original fixtures and exact pins.

Read [upstream integration](UPSTREAM_INTEGRATION.md),
[third-party notices](../THIRD_PARTY_NOTICES.md) and
[additional reuse candidates](REUSE_CANDIDATES.md) before importing another
component. The current build reuses only 3dsrecomp's compiler/ABI and Zakuro's CPU
interpreter/common code. Android and renderer components are deliberate next steps.

## This prepared cloud workspace

The toolchain is retained outside the checkout. Activate it for each new shell:

```bash
export CARGO_HOME=/workspace/droidds-tools/cargo
export RUSTUP_HOME=/workspace/droidds-tools/rustup
export PATH=/workspace/droidds-tools/cargo/bin:$PATH
export CARGO_NET_GIT_FETCH_WITH_CLI=true
cd /workspace/DroidDS
python3 tools/build_foundation.py --jobs 2
```

Use the current existing checkout and its working changes. Do not create a new
worktree, reset another session's files or activate Uberhar's toolchain merely to
run the CPU foundation. On a laptop, ordinary Rustup installation paths are fine;
the `/workspace` exports above are specific to the prepared cloud machine.
