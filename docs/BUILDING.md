# Building DroidDS host validation

<!-- CodexAstraUlt: Document the first real, source-pinned host build without
conflating it with an Android runtime, retail title builder or graphics proof. -->

The first executable is `droidds-foundation` version **0.0.1**. It is a Linux
synthetic correctness harness. It generates and compiles original ARM/Thumb
instruction examples with 3dsrecomp, loads the resulting native library through
the upstream ABI, and compares it with the selected Zakuro interpreter and
hand-derived expected state. It does not accept retail inputs or arbitrary native
libraries. This executable remains the CPU foundation; the separate integrated
runtime gate below now exercises the loader, HLE services and PICA. Android has
its own cross-build and physical-device gate.

<!-- CodexAstraUlt: Expose the separate local-title tool without expanding this
public foundation harness to accept private input or claiming Android boot. -->
For an owned decrypted title on the Linux laptop, use the separate
[private-title reconnaissance procedure](PRIVATE_TITLE_RECONNAISSANCE.md).
Its first implementation runs a bounded interpreter/software baseline and
reports observed blockers. It does not generate native title code or an APK.

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
| Flags/shifts and Thumb to ARM | Exact carry/shift results and reverse native interworking |
| Finite VFP | Exactly representable selected addition, multiplication and conversions |
| Tiny dispatch budget | Oversized block yields, interpreter makes progress and a native checkpoint follows |
| Negative controls | NaN-shaped integer/register and memory changes fail comparison; infinite guest loop is incomplete; worker timeout is enforced |

<!-- CodexAstraUlt: Preserve the foundation's limits while recording the expanded
cases and immutable-code controls that are already implemented and device-tested. -->
Comparisons include exposed user registers/flags, VFP storage, TLS, exclusive
monitor and the full 64 KiB synthetic memory image. The finite VFP case does not
qualify general rounding, NaN or subnormal behavior. This small bus uses checked
callbacks, not direct memory pages. Stale-origin, changed-code and executable
write controls implement an immutable-fixture policy. Full CRO lifecycle,
remapping, concurrent writers and broad instruction semantics remain open.

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
component. The foundation reuses 3dsrecomp's compiler/ABI and Zakuro's CPU/common
code; the separate runtime package now adds selected Zakuro core, filesystem and
GPU sources. The root lockfile and source manifest govern both selections.

<!-- CodexAstraUlt: Android now has its own bounded build target; the Linux suite
is an automated regression gate, not a manual owner-testing prerequisite. -->
For the Android CPU loader app, use [Android probe instructions](ANDROID_PROBE.md).
It shares these fixtures and preserves this Linux suite. Android package checks
and actual Thor execution are reported separately.

## Integrated runtime host gate

<!-- CodexAstraUlt: Document the real original guest/service/PICA gate and its
strict GPU execution requirement without claiming a retail baseline or APK run. -->

Version 0.0.5 adds `droidds-runtime-probe`. Its original NCCH/CXI guest is
loaded by the real title loader, calls HLE services and submits PICA commands.
Required comparisons cover interpreter/software, native/software and
native/Vulkan routes, including deliberate CPU fallback and exact image output.
This uses the selected renderer, not just the standalone C Vulkan helper.

Install a working Vulkan loader/driver and `VK_LAYER_KHRONOS_validation`, plus
`spirv-val` from SPIRV-Tools. Mesa software Vulkan is suitable for correctness
checks. Use the same pinned Rust and C compiler prerequisites as the foundation:

```bash
python3 tools/build_runtime_probe.py --output out/runtime-host-local --jobs 2
```

Choose a fresh output directory. The tool records compiler/source identities and
runs the filesystem/core tests, actual loader regressions, runtime tests and GPU
suite. Required GPU tests must execute: missing hardware initialization, filtered
tests or unexpected ignored cases fail the gate. It runs both normal and forced
static blend/logic-state modes, requires observed validation-layer activation,
and rejects API/synchronization errors. Static state matters because the owner's
Thor report lacks the optional dynamic-state extensions.

The generated original guest library executes through the actual runtime bridge.
`runtime-report.json` records exact route, service, renderer and memory-layout
evidence. `build-report.json` binds this to source hashes and toolchains. Vulkan
rasterization and GPU vertex shading are separate fields; a passing integrated
device may use the CPU PICA vertex interpreter. No retail input is consumed, and
the fixture is NCCH, not a 3DSX loader test.

The selected runtime/compiler patches live under `vendor/`, with upstream
provenance retained. Do not edit Cargo's shared checkouts. The actual runtime
exposed a conditional-control-flow budget mismatch (598 reference instructions
versus 1,598 native charges before correction); the local compiler patch must
pass regression and integrated-route checks. This is an accounting/correctness
issue, not a performance benchmark. ABI version 4/generation 3 remain pinned.

The New 3DS regression path resolves memory before machine construction,
separates physical regions from legacy commitment caps, checks configuration
pages and real kernel/service allocations, and rejects invalid heap mappings or
incompatible saved layouts before live memory changes. These bounded checks do
not qualify Xenoblade or the wider scheduler/module lifecycle.

The optional PICA CPU JIT is disabled. Shader job/object/payload limits and safe
fallbacks are tested, but total GPU/driver bytes, sustained memory recovery and
zero-stall cold gameplay remain open. Private Dark Moon, Xenoblade and Sonic
baselines require their exact local inputs, which are absent here.

<!-- CodexAstraUlt: Link completed publication and the bounded uploaded device
result without substituting host execution for later interactive testing. -->
The [0.0.5 prerelease](https://github.com/RegiRex/DroiDDS/releases/tag/v0.0.5-probe.1)
is published, all required host/CI gates pass in
[run 39341905818](https://github.com/RegiRex/DroiDDS/actions/runs/39341905818),
and public downloads are verified. Exact results are in the
[build record](builds/0.0.5-runtime-integration.md). The owner's
[0.0.5 Thor report](device-tests/0.0.5-thor-runtime.md) now passes the runtime,
memory and code-guard contract. It uses CPU vertex shading and Vulkan
rasterization. The manual upload does not independently bind the installed APK;
neither host nor device fixture success establishes retail qualification.

## 0.0.6 interactive homebrew work

<!-- CodexAstraUlt: Document the extended runner and completed local gates while
retaining independent release/download and physical-device qualification. -->

Version 0.0.6 extends the same runtime host command above. It generates the
original `droidds-original-homebrew-v1` NCCH guest and
`libdroidds_fixture_homebrew.so`, then checks interpreter/software,
native/software and native/Vulkan execution. HID input must affect guest images
and DSP HLE PCM; pixel/sample mutation controls, pause/resume and actual guest
exit remain required. The existing CPU, Vulkan, runtime and memory-layout gates
are retained. `homebrew-report.json` records the additional automatic guest
evidence, separately from `runtime-report.json`; the source-bound
`build-report.json` covers both.

The Android builder in [Android instructions](ANDROID_PROBE.md) packages exactly
twelve ARM64 libraries, including the new generated homebrew library. Its manual
frontend presents readback pixels with Bitmap/Canvas and resamples guest PCM for
Android playback. Compiling that frontend does not establish visible images,
audible audio, input or lifecycle behavior on the Thor.

Implementation and all final local gates pass: 246 Python gate tests, 162
foundation Rust tests, the runtime/loader suites, normal/static Vulkan suites,
the automatic three-route homebrew proof, seven real-runtime FFI controls, four
JVM logic controls and the twelve-library Android audit. The local four-file
bundle is verified using a local diagnostic key; it is not the public CI APK.
See the [0.0.6 build record](builds/0.0.6-interactive-homebrew.md) for source binding,
commands and exact per-suite results. Main/tag CI gates pass, the prerelease
is published and all four public assets are independently verified. The Thor
interactive test remains **pending**. Use fresh output
directories when reproducing the recorded checks.

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
