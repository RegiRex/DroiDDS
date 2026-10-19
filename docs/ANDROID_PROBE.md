# Android CPU, Vulkan and runtime probe

<!-- CodexAstraUlt: Advance to broader CPU/code safety and the selected renderer's
capability contract without promoting the original fixtures to PICA/game proof. -->

Version **0.0.4 passes the owner's Thor report**, including all eight CPU cases,
three code-safety controls and Vulkan graphics/compute requirements. Read
[the device evidence](device-tests/0.0.4-thor-runtime-probe.md). The Thor reports
no optional dynamic blend/logic-state support, so the runtime integration explicitly
tests the static pipeline path. The owner need not repeat automated Linux tests.

<!-- CodexAstraUlt: Record verified runtime publication without promoting host
and CI results to an actual Thor run or retail compatibility. -->
**0.0.5 is published with verified downloads and passing host/CI gates; its Thor
execution remains pending.** It retains the 0.0.4 CPU/Vulkan checks and adds an original NCCH
guest through the actual loader, HLE services and PICA renderer. It still runs
offscreen and exports one report; no retail game, display/input/audio frontend
or 3DSX loader is included in this diagnostic.

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

The [0.0.5 prerelease](https://github.com/RegiRex/DroidDS/releases/tag/v0.0.5-probe.1)
provides `DroidDS-0.0.5-android-arm64.apk` and its verification files. The
[release workflow](https://github.com/RegiRex/DroidDS/actions/runs/39341905818)
passed all required host, Android-package and publication gates; public downloads
were verified against the release evidence. See the
[build record](builds/0.0.5-runtime-integration.md). Its Thor runtime report remains
the next device gate. The app
requires ARM64 Android 10/API 29 or newer. Passing the new graphics checks also
requires the Vulkan 1.3 features listed below; a reported API version alone is
insufficient. Unsupported capabilities are recorded as a failed qualification,
not an automatic game-compatibility or hardware verdict.

Public diagnostic builds use one-off CI signing keys. A new public diagnostic APK
can have a different signer and therefore fail to update an earlier one in place. Save any report you
still need, explicitly uninstall **DroidDS Probe** in Android Settings, then
install the new APK if Android reports a signing conflict. This removes only
that app's private probe data. The owner's 0.0.2–0.0.4 exports have already
been received and summarized above. Uberhar is a separate package and is
unaffected. Automation never uninstalls an app to resolve a signing conflict.
Stable product signing remains separate work.

1. Open **DroidDS Probe**; the version's CPU, GPU and runtime checks start automatically.
2. Wait for the completed result. **Run again** repeats the checks.
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

## Retained CPU and backend checks

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

The shaders in these C backend fixtures are original, compiled and SPIR-V-validated
during the build. These particular checks exercise representative mechanisms,
**not actual PICA execution**. They remain separate from the new integrated runtime
described below. Bounded recreation/readback tests do not prove leak freedom.

CPU fields remain at the top level. `cpu_status` and `graphics_probe` fields
record each result; 0.0.5 additionally requires `runtime_probe` to pass. Manufacturer,
model, Android API/release and non-unique GPU/device properties provide context.
No hardware serial or advertising identifier is collected; per-run/request UUIDs
still identify diagnostic runs. `elapsed_realtime_ms` uses a monotonic clock for
the whole run and is not an emulation-speed benchmark.

## 0.0.5 integrated guest checks

<!-- CodexAstraUlt: Explain the actual execution chain and qualification limits,
including CPU vertex interpretation inside a successful Vulkan draw path. -->

The original NCCH/CXI executable contains hand-authored ARM code, PICA commands
and shader inputs. It runs through the real filesystem/title loader, guest SVCs,
`srv:` and `gsp::Gpu` requests, then the PICA command decoder and renderer. The
fixture performs two draws and compares every pixel of an 8×8 result against an
independent expected image. It is neither a direct host Vulkan triangle nor a
retail-derived test.

Three routes are required:

| Report case | Guest CPU | PICA rasterization |
| --- | --- | --- |
| `interpreter_software` | Selected Zakuro interpreter | Software |
| `native_software` | Generated native code with a deliberate interpreter helper | Software |
| `native_vulkan` | Generated native code with the same helper | Vulkan, with activation/submission evidence |

`vertex_shading_on_gpu` records a separate choice. An integrated GPU such as the
Thor's can use the CPU PICA vertex interpreter while Vulkan performs rasterization.
That is reported explicitly; it is not mislabeled as GPU vertex execution.
Unexpected software raster fallback cannot qualify the Vulkan route. The host
gate also forces static blend/logic state to exercise the Thor-compatible path.

The report checks actual service/counter evidence, exact pixels, a changed-pixel
negative control and integrated immutable-code controls. Original New/Old-model
NCCH variants additionally check parsed modes, real allocation boundaries,
configuration/shared pages, commitment, Base memory and guest exit. Host kernel
regressions cover heap windows and rejected-state nonmutation as well. These are
bounded original programs, not full scheduling, CRO or arbitrary native-plugin
safety qualification.

The optional CPU PICA JIT is disabled. The actual GPU renderer still includes its
runtime shader translation machinery; the host-only 3dsrecomp CPU compiler is not
packaged in the APK. Shader work has admission limits covering queued, running
and completed-but-uncollected work, with separate retained-object and shader
payload limits. Saturation preserves the accurate fallback and remains visible
in diagnostics. These limits do not bound all driver/texture memory, establish
leak freedom, or remove synchronous first-use generic-pipeline compilation.

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
Thor driver. The owner's 0.0.4 report separately passes its Android checks.
For the actual loader/HLE/PICA gate use
[`tools/build_runtime_probe.py`](../tools/build_runtime_probe.py), documented in
[Building](BUILDING.md#integrated-runtime-host-gate); it requires real Vulkan
tests and observed host validation-layer activation.

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
graphics and compute fixture. Version 0.0.5 retains those checks and additionally
requires the actual runtime's three routes, service/native/fallback evidence,
pixels, code-safety controls and loader memory cases. A hang, crash, missing/stale result, wrong
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

The owner's 0.0.4 report qualifies its expanded diagnostic scope. The next device
report must establish the added 0.0.5 runtime checks. The implemented New 3DS
loader/memory corrections do not establish Xenoblade boot compatibility. Android
picker behavior, lifecycle, presentation and 16 KiB-page execution remain separate
device gates. Broader CPU/VFP/module tests, first-use compilation, long-run memory
stability, controls/audio and games remain open. No private retail inputs are
present in this environment, so Dark Moon, Xenoblade and Sonic baselines remain
explicitly untested. This probe establishes no Dark Moon visual correction or
game-performance improvement. After a passing 0.0.5 Thor report, the next target
is 0.0.6: visible interactive original 3DS homebrew and Android lifecycle work.
