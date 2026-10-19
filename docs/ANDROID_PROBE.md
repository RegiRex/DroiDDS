# Android CPU and Vulkan probe

<!-- CodexAstraUlt: Advance to broader CPU/code safety and the selected renderer's
capability contract without promoting the original fixtures to PICA/game proof. -->

Version **0.0.4** expands the CPU suite to eight cases, adds three code-safety
controls, and exercises an original Vulkan 1.3 graphics/compute fixture against
the selected renderer's capability requirements. It retains 0.0.3's offscreen
color checks and **Save report**. The owner does not need to repeat automated
Linux tests manually. **0.0.4 execution on the Thor remains pending.**

The [owner-supplied 0.0.2 Thor report](device-tests/0.0.2-thor-cpu.md) passes all
four CPU cases and both corruption controls on reported Android ARM64 with 4 KiB
host pages. Its exported JSON does not independently bind the installed APK hash.
The Vulkan helper also passed Linux software Vulkan execution with the Khronos
layer and synchronization validation enabled. The
[owner's 0.0.3 Thor report](device-tests/0.0.3-thor-cpu-vulkan.md) now passes all
CPU/GPU checks on Android 13/Adreno 740, reporting Vulkan 1.3.128. This separate
device evidence covers the offscreen fixture; it does not qualify the complete
renderer. The report does not establish whether the picker or ADB exported it.

## Install and save a report

<!-- CodexAstraUlt: Record completed publication while preserving explicit
signing-conflict handling and the pending physical-device gate. -->

The published [0.0.4 prerelease](https://github.com/RegiRex/DroidDS/releases/tag/v0.0.4-probe.1)
provides `DroidDS-0.0.4-android-arm64.apk` and its verification files. The
[release workflow](https://github.com/RegiRex/DroidDS/actions/runs/39321226246)
passed all build and publication gates. The app
requires ARM64 Android 10/API 29 or newer. Passing the new graphics checks also
requires the Vulkan 1.3 features listed below; a reported API version alone is
insufficient. Unsupported capabilities are recorded as a failed qualification,
not an automatic game-compatibility or hardware verdict.

Public diagnostic builds use one-off CI signing keys. The public 0.0.4 APK has a
different signer from 0.0.3 and cannot update it in place. Save any report you
still need, explicitly uninstall **DroidDS Probe** in Android Settings, then
install the new APK if Android reports a signing conflict. This removes only
that app's private probe data. The owner's 0.0.2 and 0.0.3 exports have already
been received and summarized above. Uberhar is a separate package and is
unaffected. Automation never uninstalls an app to resolve a signing conflict.
Stable product signing remains separate work.

1. Open **DroidDS Probe**; CPU and offscreen Vulkan checks start automatically.
2. Wait for the completed CPU/Vulkan result. **Run again** repeats the checks.
3. Tap **Save report**, choose a location such as Downloads and save
   `droidds-latest-probe.json`. Completed failure reports can also be saved.
4. Attach that JSON when reporting results. No game file or visual judgment is
   needed: the offscreen patterns are compared through GPU readback.

The save action uses Android's `ACTION_CREATE_DOCUMENT` picker and writes only
to your chosen document. It requires no broad storage permission, network
permission or Google service. On systems lacking a document provider, the probe
and private report remain functional. Cancellation or export failure preserves
the private report and permits retry or ADB retrieval.

The `files` directory is private app storage, not a normal file-manager folder.
The USB-connected Linux laptop can still retrieve the report:

```bash
adb -s YOUR_THOR_SERIAL exec-out run-as org.droidds.probe \
  cat files/latest-probe.json > "$HOME/Downloads/droidds-latest-probe.json"
```

## What the tests establish

<!-- CodexAstraUlt: Describe actual route and readback gates without treating an
original Vulkan smoke fixture as PICA integration or a gameplay benchmark. -->

Pinned 3dsrecomp generates C on the build host; the NDK compiles it for Bionic.
The packaged Rust runtime compares eight native CPU cases against Zakuro's
interpreter **and hand-derived complete expected state**:

- The original ARM, Thumb, ARM-to-Thumb interworking and missing-entry fallback.
- Carry/shift flags and reverse Thumb-to-ARM interworking.
- Exactly representable finite VFP addition, multiplication and conversions.
- A one-instruction dispatch budget that rejects an oversized block, makes
  interpreter progress and reaches a native checkpoint.

Two controls still reject deliberately corrupted integer registers/memory.
Three additional `code_safety` controls reject stale origins at load, stop
changed code before native dispatch, and reject actual guest executable stores
without changing code bytes. This is a single-threaded immutable-fixture policy,
not CRO remapping/lifetime or operating-system scheduler integration. General
VFP rounding, NaN and subnormal behavior remain unqualified.

The baseline C Vulkan helper retains three **16 × 16** RGBA8 patterns: solid red,
solid green and red/green halves. It recreates the logical device, resources and
pipeline for three cycles. A pass requires **nine readbacks, 2,304 matching
pixels, nine pixel-mutation controls, three pipeline creations and twelve draws**.
These baseline counters are unchanged from 0.0.3.

The added `graphics_probe.renderer_probe` checks Zakuro revision `412900a`'s
capability contract and executes original synthetic shaders. Required support is
Vulkan 1.3, a graphics+compute queue, `VK_KHR_push_descriptor` with at least eight
push descriptors, depth clamp, dynamic rendering, synchronization2 and pipeline
creation cache control. Format checks require D24S8 depth/stencil plus transfers,
and RGBA8 color/blend, sampled/linear-filtered, storage and transfer usages.
Logic operations, pipeline statistics and extended dynamic blend/logic state are
**optional discovery fields**, not pass prerequisites.

Actual execution uses two pipelines and checks textured depth/stencil acceptance
and rejection, depth clamp, pushed descriptors and a compute storage-image/buffer
path. A pass requires **two readbacks, 512 matching pixels, five draws, one compute
dispatch, 16 matching compute words and three deliberate corruption checks**.
These are additional to the baseline counts. Missing requirements or failed
execution prevent combined success and retain useful capability/error evidence.

All shaders are original, compiled and SPIR-V-validated during the build; the APK
contains no shader compiler. This exercises representative mechanisms, **not
Zakuro's actual PICA renderer or a game**. There is no presentation surface, full
HLE or retail input. Bounded recreation/readback tests do not prove leak freedom.

CPU fields remain at the top level. `cpu_status` and `graphics_probe` fields
record each result; combined `status` passes only when both pass. Manufacturer,
model, Android API/release and non-unique GPU/device properties provide context.
No hardware serial or advertising identifier is collected; per-run/request UUIDs
still identify diagnostic runs. `elapsed_realtime_ms` uses a monotonic clock for
the whole run and is not an emulation-speed benchmark.

## Build on Linux

<!-- CodexAstraUlt: Keep portable SDK/JDK instructions and exact pins, with static
package audits explicitly separate from Android execution. -->

Use Rust 1.95.0, Python 3.11+, JDK 17, Android platform 35/build tools 35.0.0 and
NDK **27.3.13750724**. Set `ANDROID_HOME` and `JAVA_HOME` to your installed SDK and
JDK. Install official SDK packages through Android Studio or command-line tools:

```bash
rustup toolchain install 1.95.0 --profile minimal --component rustfmt,clippy
rustup target add --toolchain 1.95.0 aarch64-linux-android
"$ANDROID_HOME/cmdline-tools/latest/bin/sdkmanager" \
  'platforms;android-35' 'build-tools;35.0.0' 'ndk;27.3.13750724' 'platform-tools'
python3 tools/build_android_probe.py \
  --sdk "$ANDROID_HOME" --java-home "$JAVA_HOME" \
  --output out/android-probe-local --jobs 2
```

Use a fresh output directory. The builder preserves strict generated-C floating
point options, compiles Java 8 bytecode/D8 and uses pinned shader tools. It audits
all packaged ELF dependencies, AArch64 identity, at least 16 KiB load alignment,
absence of text relocations/writable-executable segments, APK signature,
manifest/API identity and 16 KiB ZIP alignment. The Vulkan loader is supplied by
Android rather than bundled.

Outputs include `droidds-android-probe-debug.apk`, `build-report.json` and logs.
A completed cross-build records `status: built`, **`runtime_status: not_run`**.
Static alignment does not establish execution on a 16 KiB-page host.

Preserve `build/android-probe-debug.keystore` for subsequent local updates; it is
unrelated to Uberhar's signing identity. The default build is test-only/debuggable.
`--prerelease` stages `testOnly=false` for browser/file-manager installation and
retains debugging for bounded ADB retrieval. Every APK includes the complete
[third-party notices](../THIRD_PARTY_NOTICES.md). The tag workflow publishes only
the APK, `BUILD_REPORT.json`, `SHA256SUMS` and `THIRD_PARTY_NOTICES.txt`, never the
private signing key.

## Validate the shared Vulkan helper on Linux

<!-- CodexAstraUlt: Require actual driver/layer execution, including a permitted
software ICD, and preserve the distinction from physical Android GPU results. -->

Install a Vulkan loader, a working driver/ICD and the Khronos validation layer.
Mesa software Vulkan is suitable for this correctness gate. On Nobara the loader
commonly lives at `/usr/lib64/libvulkan.so.1`; use its actual installed path:

```bash
VULKAN_LOADER=/usr/lib64/libvulkan.so.1
VK_LAYER_ENABLES=VK_VALIDATION_FEATURE_ENABLE_SYNCHRONIZATION_VALIDATION_EXT \
python3 tools/build_vulkan_probe.py \
  --ndk "$ANDROID_HOME/ndk/27.3.13750724" \
  --vulkan-library "$VULKAN_LOADER" \
  --output out/vulkan-probe-local --require-validation
```

`--require-validation` fails if the layer cannot load. Standard installations
use normal driver/layer discovery; nonstandard installations may need their own
`VK_DRIVER_FILES` or `VK_LAYER_PATH`. Review `build-report.json` and diagnostics.
The historical 0.0.3 helper passed Mesa software Vulkan with Khronos and
synchronization validation enabled. The 0.0.4 build gate requires the expanded
helper to pass the same actual execution checks; use that build's report for
its result. Host validation does not execute the Android binary or qualify the
Thor driver. 0.0.4 Android execution remains pending.

## Run from the laptop with ADB

<!-- CodexAstraUlt: Preserve external request and installed-APK binding, stronger
than a manually exported report, without automatic uninstall or device uploads. -->

Local Codex can run this against the USB-connected Thor; the cloud session cannot
automatically access that connection. Use `adb devices -l` and supply the exact
authorized serial:

```bash
python3 tools/run_android_probe.py \
  --serial YOUR_THOR_SERIAL \
  --apk out/android-probe-local/droidds-android-probe-debug.apk \
  --output out/thor-probe-local
```

For a downloaded public APK, use its path and add `--allow-prerelease`. The runner
decodes the manifest, checks the installed APK hash, issues a fresh request ID
and validates all CPU counters/output. Versioned validation preserves the
historical 0.0.2/0.0.3 contracts. For 0.0.4 it requires eight CPU cases, three
code-safety controls, all baseline Vulkan checks and the complete capability,
graphics and compute fixture. A hang, crash, missing/stale result, wrong
version or unavailable Vulkan fails the run.

Only `org.droidds.probe` is installed/updated and stopped. Its latest report is
replaced; no automatic uninstall, app-data clearing, Uberhar changes or uploads
occur. A manually saved report is useful but lacks the external request/APK
binding of a full ADB run.

One worker serializes native execution and file IO off the UI thread. Activity
recreation observes the existing run. The app atomically replaces one private
report, writes a running marker before native loading and checks saved bytes
before displaying success. Native crashes/hangs can leave incomplete evidence;
the ADB runner supplies the external deadline. This is not a native sandbox.

## Remaining gates

<!-- CodexAstraUlt: Retain full renderer, lifecycle, memory and game acceptance
criteria beyond the bounded CPU and offscreen output fixture. -->

The owner's 0.0.3 report passes the basic CPU/offscreen GPU gate. The next device
report must establish 0.0.4's expanded CPU/code-safety and renderer-contract
results. New 3DS runtime configuration is a separate source audit; this probe
does not establish Xenoblade boot compatibility. Android picker behavior,
lifecycle and 16 KiB-page execution remain separate device gates. Even a passing
0.0.4 fixture does not complete A0's actual generic PICA pipeline or M2's renderer
integration. Broader CPU/VFP/module tests, surface presentation, long-run memory
stability and games remain open. This probe establishes no Dark Moon correction
or game-performance improvement.
