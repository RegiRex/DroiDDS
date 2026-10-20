# Android runtime probe and interactive homebrew

<!-- CodexAstraUlt: Advance to broader CPU/code safety and the selected renderer's
capability contract without promoting the original fixtures to PICA/game proof. -->

Version **0.0.4 passes the owner's Thor report**, including all eight CPU cases,
three code-safety controls and Vulkan graphics/compute requirements. Read
[the device evidence](device-tests/0.0.4-thor-runtime-probe.md). The Thor reports
no optional dynamic blend/logic-state support, so the runtime integration explicitly
tests the static pipeline path. The owner need not repeat automated Linux tests.

<!-- CodexAstraUlt: Advance the passed runtime device gate and completed local
interactive validation while keeping release/device evidence separate. -->
**0.0.5 is published and its [Thor report](device-tests/0.0.5-thor-runtime.md)
passes.** It retains the 0.0.4 checks and executes an original NCCH guest through
the real loader, HLE services and PICA renderer. Its hardware route uses CPU
vertex shading and static-state Vulkan rasterization with no software raster
fallback. The uploaded JSON does not independently verify the installed APK.

**[0.0.6 correction 2 is published](https://github.com/RegiRex/DroidDS/releases/tag/v0.0.6-probe.2); local/main/tag CI gates pass and its four
public assets are independently verified. Thor interactive qualification
remains pending.** It retains every
previous gate and adds an original interactive NCCH guest, automatic image/PCM
checks, and an Android screen/input/audio frontend. No retail game or 3DSX loader
is included. Automatic success alone cannot qualify visible or audible output.

<!-- CodexAstraUlt: Preserve the received automatic pass and human display
clarification while directing remaining work to the frontend correction. -->
The [first 0.0.6 Thor report](device-tests/0.0.6-thor-homebrew.md) now passes all
automatic gates. The owner confirms both guest views were visible on the top
physical display. The report records 197 audio underruns, zero guest-consumed
touch and no view recreation. The [0.0.6 correction](builds/0.0.6-frontend-correction.md)
addresses pacing and test clarity; its focused device gate is still required.

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

<!-- CodexAstraUlt: Provide the independently verified interactive APK
while retaining diagnostic signing and manual-device qualification. -->

Download [DroidDS-0.0.6-android-arm64.apk](https://github.com/RegiRex/DroidDS/releases/download/v0.0.6-probe.2/DroidDS-0.0.6-android-arm64.apk) from the
[0.0.6 prerelease](https://github.com/RegiRex/DroidDS/releases/tag/v0.0.6-probe.2). All required local/main/tag CI gates pass;
the public APK, `BUILD_REPORT.json`, `SHA256SUMS` and
`THIRD_PARTY_NOTICES.txt` are independently verified. See the
[correction/release record](builds/0.0.6-frontend-correction.md) for source,
signature, alignment and download evidence. The 0.0.5 Thor runtime report
passes; the new 0.0.6 interactive test below remains pending. The app
requires ARM64 Android 10/API 29 or newer. Passing the new graphics checks also
requires the Vulkan 1.3 features listed below; a reported API version alone is
insufficient. Unsupported capabilities are recorded as a failed qualification,
not an automatic game-compatibility or hardware verdict.

Public diagnostic builds use one-off CI signing keys. A new public diagnostic APK
can have a different signer and therefore fail to update an earlier one in place. Save any report you
still need, explicitly uninstall **DroidDS Probe** in Android Settings, then
install the new APK if Android reports a signing conflict. This removes only
that app's private probe data. The owner's 0.0.2–0.0.5 exports have already
been received and summarized above. Uberhar is a separate package and is
unaffected. Automation never uninstalls an app to resolve a signing conflict.
Stable product signing remains separate work.

1. Open **DroidDS Probe**; the version's automatic checks start.
2. Wait for the completed result. **Run again** repeats the checks.
3. Tap **Save report**, choose a location such as Downloads and save
   `droidds-latest-probe.json`. Completed failure reports can also be saved.
4. Attach that JSON when reporting results. No game file is needed. The 0.0.5
   offscreen checks need no visual judgment; **0.0.6 also needs the manual
   interactive test below** before its visible/input/audio milestone can pass.

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

## 0.0.6 guest, presentation and audio contract

<!-- CodexAstraUlt: Document actual guest/HLE work and the deliberate presentation
and audio conversion boundaries before recording manual device qualification. -->

The new fixture is `droidds-original-homebrew-v1`, packaged as generated native
code in `libdroidds_fixture_homebrew.so` alongside the earlier runtime fixture.
Its original ARM NCCH program obtains `hid:USER`, `gsp::Gpu` and `dsp::DSP`, reads
mapped HID state, submits PICA draws/display transfers and drives the HLE DSP
path with original PCM16 samples. The input and tone changes come from the guest,
not a replacement Android animation or host-generated tone.

Automatic `interactive_probe` checks run interpreter/software, native/software
and native/Vulkan routes through idle, A + right + up, touch and released-input
stages. Independent oracles compare every 400×240 top and 320×240 bottom pixel
and the guest's PCM response. They require real consumed-input and native/fallback
evidence, reject changed pixels/samples and insufficient dispatch budgets, and
check pause/no-progress, resume and actual guest exit. All prior CPU, Vulkan,
8×8 runtime, code-safety and memory-layout checks remain required.

Manual presentation uses **CPU readback into Bitmap/Canvas**, with both guest
views stacked on **one Android display**. PICA rasterization remains Vulkan;
the CPU vertex path is reported independently. This is not direct Vulkan
swapchain presentation, physical dual-display support or a performance design
qualified for retail games. A working readback oracle does not prove that Android
actually showed the images to the owner.

The HLE DSP mixer produces stereo PCM at **32728.498046875 Hz**. Android's audio
path performs stateful linear resampling to **48000 Hz** for playback rather
than relabeling the guest samples with a new rate. Holding A changes the guest
tone rate. Measured generated/converted/written/playback counters and user
confirmation of audible sound answer different questions. This fixture does
not qualify DSP firmware execution, arbitrary codecs or complete game audio.

One session-owner thread performs native open/frame/pause/resume/report/close.
The frontend releases held input and pauses audio/execution when backgrounded;
Activity recreation reattaches to the process session instead of starting another
runtime. A bounded `interactive_session` result is merged into the same
`files/latest-probe.json`, bound to its latest automatic run. CPU, graphics,
runtime and automatic homebrew evidence remain intact; manual observations do
not turn an automated failure into a pass. Pending/interrupted manual sessions
remain distinguishable from completed ones.

## 0.0.6 manual Thor test

<!-- CodexAstraUlt: Require explicit human observations alongside guest and
Android counters; a checked box is a report of experience, not an automatic oracle. -->

Install the [verified 0.0.6 APK](https://github.com/RegiRex/DroidDS/releases/download/v0.0.6-probe.2/DroidDS-0.0.6-android-arm64.apk), then perform these checks.
Use **0.0.6 · correction 2** (Android install code **7**) for this focused
retest. The first 0.0.6 result passes automation and confirms both views, but
measured touch, view recreation and corrected audio continuity remain open.

<!-- CodexAstraUlt: Explain the implemented diagnostic limit so automatic return
to the probe is distinguishable from a crash or an unlimited play session. -->
The session automatically stops and saves at 6,000 delivered frames or two
minutes in the foreground, whichever comes first. Complete the brief checks and
confirm the screen/audio observations before that limit. Background time is
excluded; this is not a sustained-performance test.

1. Let the automatic checks finish, then tap **Test original homebrew**.
2. Confirm both labeled 3DS guest views appear on the **same Android display**.
   The Thor's separate lower physical display is not used by 0.0.6.
   Use the Thor's physical D-pad and A button;
   check that the guest image changes and A changes the audible tone. Try the
   on-screen arrows/A separately; they do not establish physical-controller input.
3. Hold and drag inside the **colored lower guest image**, then release.
   The black letterbox is outside its touch area. Confirm
   its marker responds and does not remain stuck after release or backgrounding.
4. Briefly switch to another app and return. The guest should pause while away,
   clear held input and recover its image, controls and audio on return. In
   correction 2, tap **Recreate view** and check recovery again. Earlier builds
   require rotation if enabled; otherwise record recreation as untested.
5. Check **I can see both 3DS views here** (previously **I can see both guest
   screens**) and **I heard the guest's tone** only
   if those statements are true. Leave them unchecked for a missing/corrupt view
   or inaudible tone; explain input, audio or lifecycle problems with the report.
6. Tap **Stop and save session** and wait to return to the probe. This requests
   normal session close and saves observations before returning. Select + Start
   separately requests exit through the guest. Tap **Save report**,
   save `droidds-latest-probe.json` and share it with the observed results.

The report retains automatic and manual sections in one file. A failed or
unfinished session is useful diagnostic evidence, not a passing manual gate.
Visible output, hardware/touch response, audible audio, pause/resume, view
replacement and normal exit must all be accounted for before 0.0.7 promotion;
an automatic pass or a nonzero presentation/playback counter cannot replace
missing observations.

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

<!-- CodexAstraUlt: Preserve the earlier libraries and audit the new guest
library explicitly rather than accepting an arbitrary APK native inventory. -->
Version 0.0.6 requires exactly **twelve ARM64 libraries**: eight CPU fixture
libraries, the previous runtime fixture, the new homebrew fixture, the Rust
runtime and the JNI bridge. Existing report and library gates are not replaced
by the interactive frontend.

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
pixels, code-safety controls and loader memory cases. Version 0.0.6 also requires
the three-route automatic homebrew image/input/PCM and lifecycle contract. A
passing automatic ADB run does not establish human-visible or audible behavior;
complete and record the manual device checklist separately. A hang, crash, missing/stale result, wrong
version or unavailable Vulkan fails the run.

Only `org.droidds.probe` is installed/updated and stopped. Its latest report is
replaced; no automatic uninstall, app-data clearing, Uberhar changes or uploads
occur. A manually saved report is useful but lacks the external request/APK
binding of a full ADB run.

One worker serializes automatic native execution and report IO off the UI thread;
the manual session has one separate runtime-owner thread and cannot overlap an
automatic rerun. Activity recreation observes the existing run/session. The app atomically replaces one private
report, writes a running marker before native loading and checks saved bytes
before displaying success. Native crashes/hangs can leave incomplete evidence;
the ADB runner supplies the external deadline. This is not a native sandbox.

## Remaining gates

<!-- CodexAstraUlt: Retain full renderer, lifecycle, memory and game acceptance
criteria beyond the bounded CPU and offscreen output fixture. -->

The owner's 0.0.5 report qualifies its bounded actual-runtime scope. The next
device gate is 0.0.6's **automatic checks plus manual visible/input/audio/lifecycle
observations**, required before 0.0.7 promotion. Local/main/tag CI gates and
public-download verification pass; the new frontend's Thor result remains
pending. Android picker and
16 KiB-page execution remain separate checks. The implemented New 3DS layouts
do not establish Xenoblade boot compatibility, and the HLE tone does not qualify
all audio behavior. Broader CPU/VFP/modules, first-use compilation, long-run
memory and retail games remain open. Private Dark Moon, Xenoblade and Sonic
inputs are absent here. No Dark Moon visual correction or game-performance
improvement is established by this diagnostic.
