# Android CPU loader probe

<!-- CodexAstraUlt: Start Android development from the verified CPU fixtures;
separate cross-build/package evidence from actual device execution. -->

The owner does **not** need to manually test the Linux foundation before Android
development. Its automated checks remain the CPU regression gate. This first
Android slice, version **0.0.2**, packages the same four original ARM/Thumb fixtures
in a small ARM64 app. It is a partial DDS-010/A0 implementation, not a game player.

The host uses pinned 3dsrecomp to generate C, then the Android NDK compiles each
fixture for Bionic. The app loads a small Rust runtime, which opens those packaged
libraries and checks their output against both Zakuro's interpreter and the known
expected results. No compiler, full HLE runtime, GPU backend or retail input is
included in the Android dependency graph. The platform Java shell and narrow C
JNI bridge are original DroidDS code; Kotlin/frontend dependencies are unnecessary
for this bounded diagnostic app.

## Build on Linux

Use Rust 1.95.0, Python 3.11+, JDK 17, Android platform 35, build tools 35.0.0 and
NDK **27.3.13750724**. SDK Manager installs official SDK packages with its normal
verification. Use an existing licensed Android SDK or install it through Android
Studio/official command-line tools. Nothing needs to be installed on the Thor yet.

```bash
rustup toolchain install 1.95.0 --profile minimal --component rustfmt,clippy
rustup target add --toolchain 1.95.0 aarch64-linux-android
"$ANDROID_HOME/cmdline-tools/latest/bin/sdkmanager" \
  'platforms;android-35' 'build-tools;35.0.0' 'ndk;27.3.13750724' 'platform-tools'
python3 tools/build_android_probe.py \
  --sdk "$ANDROID_HOME" --java-home "$JAVA_HOME" \
  --output out/android-probe-local --jobs 2
```

Choose a fresh output directory each time; previous evidence is preserved.
The builder compiles Java to Java 8 bytecode and uses D8 for Android desugaring.
All generated-C compilation preserves upstream's strict floating-point options.
The Rust runtime excludes the host compiler. Every packaged ELF must be AArch64,
have load alignment of at least 16 KiB, contain no writable-executable segment or
text relocations, and depend only on packaged libraries or selected Android system
libraries. APK signature, package/API identity and 16 KiB ZIP alignment are checked.

Output is `droidds-android-probe-debug.apk` plus `build-report.json`, command logs,
generated original fixture code and native libraries. A completed build records
`status: built` and **`runtime_status: not_run`**. Compilation never marks Android
execution passed.

The separate local debug key lives at `build/android-probe-debug.keystore`; keep it
to allow subsequent test updates. Its conventional password is not a production
secret. The tool never reuses Uberhar's key. The package is test-only/debuggable,
has no network/storage permissions and retains one private latest-report file.
Do not publish the APK as a release: the [upstream notice inventory](../THIRD_PARTY_NOTICES.md)
and product signing policy remain separate work. Source, scripts and CI are public;
the APK is built locally for development.

## Run the probe from the laptop

Local Codex can build and run this on Nobara with the already USB-connected Thor.
The cloud session cannot access that USB connection automatically. Install Android
platform tools locally, use `adb devices -l` to identify the authorized device,
and supply its exact serial explicitly:

```bash
python3 tools/run_android_probe.py \
  --serial YOUR_THOR_SERIAL \
  --apk out/android-probe-local/droidds-android-probe-debug.apk \
  --output out/thor-probe-local
```

The runner inspects the real APK manifest before installation, verifies the
installed APK hash, launches with a fresh request ID, and requires the matching
report from the current run. It checks all four cases, exact route counters,
strict state comparisons and both deliberate corruption rejections. It records
the device's actual OS/properties and reported host page size. A hang, crash,
missing/stale report, wrong installed version or incomplete case fails the run.

Only `org.droidds.probe` is installed/updated and stopped. Its prior latest report
is replaced; the runner never uninstalls an app, clears app data or touches Uberhar
saves/settings. A signing mismatch requires diagnosis rather than an automatic
uninstall. The local report stays private unless deliberately shared; no capture
or device report is uploaded by this tool.

For a normal manual launch, the app also runs once and displays the result. The
button explicitly reruns it. Activity recreation observes the same process worker
instead of starting another. Native execution and file writes stay off the UI
thread. The one result file is replaced atomically, with a running marker written
before native loading. A Rust panic can become a failure report, but native aborts
and hangs require the external runner's deadline; this is not a native sandbox.

## What remains after the first device result

Actual Android execution, lifecycle behavior and 16 KiB-page device execution
must be reported separately from static checks. A Thor result only qualifies its
observed OS/page size. Vulkan capability discovery and a representative pipeline
draw are still required to complete A0. Wrong-ABI/generation negative loader
fixtures, broader CPU transitions/VFP semantics, module invalidation and the full
graphics/runtime integration also remain open. No game compatibility, Dark Moon
fix or performance improvement follows from this small loader test.

The next useful owner/device task is this short automatic Android probe, not a
manual Linux test or another game benchmark. Further CPU and renderer development
can continue independently while a Thor result is pending.

## Prepared cloud workspace

<!-- CodexAstraUlt: Reuse installed SDK tool binaries read-only, without running
Uberhar activation/build scripts or importing its configuration/signing files. -->

```bash
export CARGO_HOME=/workspace/droidds-tools/cargo
export RUSTUP_HOME=/workspace/droidds-tools/rustup
export PATH=/workspace/droidds-tools/cargo/bin:$PATH
export CARGO_NET_GIT_FETCH_WITH_CLI=true
cd /workspace/DroidDS
python3 tools/build_android_probe.py \
  --sdk /workspace/uberhar-android/sdk \
  --java-home /workspace/uberhar-android/jdk \
  --output out/android-probe-new --jobs 2
```

These SDK paths are specific to the cloud workspace; use ordinary local SDK/JDK
paths on Nobara. No service is needed for cross-compilation. There is no attached
Thor or configured Android emulator in this cloud build environment.
