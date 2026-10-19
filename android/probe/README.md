# Android CPU and Vulkan probe shell

<!-- CodexAstraUlt: Document the original 0.0.4 Java/JNI/Vulkan and export
contracts while separating source, host and actual Android execution evidence. -->

This platform-only shell runs eight synthetic CPU fixtures, three code-safety
controls, the original Vulkan color tests, and a Vulkan 1.3 renderer-contract
fixture with graphics and compute readback. It has no title loader, PICA renderer, presentation
surface, networking or mandatory Google/vendor service. Optional document export
uses one user-selected URI without broad storage permission.

| Setting | Value |
| --- | --- |
| Application ID | `org.droidds.probe` |
| Launch component | `org.droidds.probe/.ProbeActivity` |
| Version | `0.0.4` / version code `4` |
| Android minimum / target | API 29 / 35 |
| Packaged ABI | `arm64-v8a` |
| Result | `files/latest-probe.json`, in private app storage |
| Default build | Test-only and debuggable |
| Prerelease build | Normal-install manifest; still debuggable |

See [build and device instructions](../../docs/ANDROID_PROBE.md). The
[owner's 0.0.2 CPU report](../../docs/device-tests/0.0.2-thor-cpu.md) passes.
The shared graphics helper passed Linux software Vulkan with Khronos and
synchronization validation. The separate
[0.0.3 Thor report](../../docs/device-tests/0.0.3-thor-cpu-vulkan.md) now passes
all CPU and offscreen GPU checks on Adreno 740/Android 13. Picker/lifecycle
behavior remains unqualified; the uploaded JSON does not identify its export route.
**0.0.4 Thor execution remains pending.** When published, the
[0.0.4 release entry](https://github.com/RegiRex/DroidDS/releases/tag/v0.0.4-probe.1)
will provide `DroidDS-0.0.4-android-arm64.apk`. Its one-off CI signer differs from
0.0.3: preserve any needed report, then manually uninstall only **DroidDS Probe**
if required to install it. No automation clears app data or removes other apps.

## Native interfaces

<!-- CodexAstraUlt: Retain installer-owned library loading and strict bounded
UTF-8 transfers, matching each allocation with its owning runtime's release. -->

The manifest enables native-library extraction. Java loads
`libdroidds_probe_jni.so` through `System.loadLibrary`. The same process worker
calls:

```java
private static native byte[] nativeRun(String libraryDirectory);
private static native byte[] nativeVulkan();
```

`nativeRun` receives `ApplicationInfo.nativeLibraryDir`. Its JNI bridge links
`libdroidds_android_probe.so` and calls:

```c
char *droidds_probe_run(const char *library_directory);
void droidds_probe_free(char *report);
```

Rust owns the returned NUL-terminated UTF-8 JSON. JNI copies at most 1 MiB into a
Java byte array and releases every non-null allocation with the matching Rust
function, including error paths. The loader accepts only known packaged
`libdds_fixture_<fixture_name>.so` libraries in the installer-owned directory.

`nativeVulkan` allocates a 64 KiB C buffer and calls
`dds_vk_probe_run(char *json, size_t capacity)`, then releases its allocation after
copying the report. The helper uses Android's Vulkan loader. Neither interface
uses JNI's modified-UTF-8 `NewStringUTF` for report JSON. Java requires strict
UTF-8, an object and an allowed terminal status.

## CPU and immutable-code contract

<!-- CodexAstraUlt: Report exact finite arithmetic and bounded dispatch evidence
without claiming complete ARM/VFP, CRO or operating-system integration. -->

The eight cases compare every exposed CPU/VFP field and the whole 64 KiB fixture
memory with both an interpreter run and independent expected results. They cover
the previous four integer/interworking/fallback cases, carry/shifts, Thumb-to-ARM,
finite exactly representable VFP arithmetic/conversion, and progress under a
one-instruction slice. The latter has two native entry calls, one charged native
instruction, two fallback instructions and one budget exit; it is not an OS
scheduler test. Two deliberate integer/memory corruptions must still be rejected.

`code_safety` requires three real controls: stale-origin load rejection, changed
text rejected before any native or fallback instruction, and two native stores
to executable text rejected while every guest byte remains unchanged. Load-checked
text ownership guards outer and callback lookups; one shared bus protects native
and interpreter stores. This is immutable synthetic text in a single-threaded
runner, not support for CRO unload/remap or concurrent code mutation.

## Offscreen output contract

<!-- CodexAstraUlt: Make real draws, readbacks and mutation controls observable
without presenting original test shaders as PICA or game rendering. -->

The retained Vulkan 1.0 baseline uses a graphics queue and 16 × 16 RGBA8 image. Original
shaders are compiled and SPIR-V-validated with the pinned NDK during the build;
no shader compiler is in the APK. One pipeline draws solid red, solid green and
scissored red/green halves. Each of three cycles creates and destroys a logical
device, resource set and pipeline on one selected physical device. These are
three lifecycle cycles, not three different GPUs.

A passing baseline requires:

- Three cycles, three pipeline creations and twelve draw calls.
- `solid_red`, `solid_green` and `split_red_green` each passing three cycles,
  checking 768 pixels with zero mismatches per case.
- Nine readbacks and nine controls that mutate one pixel, prove comparator
  rejection and restore the original content.
- A selected-device record and no execution error.

<!-- CodexAstraUlt: Separate required renderer mechanisms from optional
capabilities and keep the added graphics/compute oracle separate from baseline. -->

`graphics_probe` schema 2 additionally requires `renderer_probe` schema 1 with
contract `zakuro-412900a`. Required discovery covers Vulkan 1.3, one graphics+compute
queue, `VK_KHR_push_descriptor`/at least eight push descriptors, depth clamp,
dynamic rendering, synchronization2 and pipeline creation cache control. D24S8
must support depth/stencil plus transfers; RGBA8 must support color/blend,
sampled/linear-filtered, storage and transfers. Optional logic operations,
pipeline statistics, dynamic blend and dynamic logic operations are recorded
without making absent support a failure.

Original shaders exercise textured depth/stencil acceptance/rejection and depth
clamp through dynamic rendering, pushed descriptors, and a compute storage-image
and buffer path. Required exact results are:

- Two pipeline creations, five draws and one compute dispatch.
- Two 16 × 16 readbacks: `textured_depth_stencil` (four draws) and `depth_clamp`
  (one draw), each 256 pixels with zero mismatches; 512 total pixels.
- Sixteen compute words with zero mismatches.
- Three actual readback-corruption rejection controls.

These counts are additional to the unchanged baseline. Required capabilities
are enabled explicitly, and missing support remains in `missing_required`.
An advanced `unsupported`/`failed` result prevents combined success even if the
baseline passed. Enumeration/allocation bounds and teardown remain explicit.
This finite test does not establish leak freedom. It exercises original
representative mechanisms, not Zakuro's actual generic PICA pipeline, a swapchain
or a game. The APK does not compile shaders at runtime.

## Run ownership and combined report

<!-- CodexAstraUlt: Preserve CPU evidence, require both execution paths to pass
and serialize work around one bounded latest report rather than launch bundles. -->

One process worker serializes native calls and file writes off the UI thread.
Activity recreation/backgrounding observes the existing run through a weak
observer. First launch runs once; **Run again** requests a sequential rerun. A
new process starts a new run.

Automation supplies a unique `request_id` launch extra after force-stopping the
prior process. The shell echoes it under `android_shell.request_id`; normal
launches generate a UUID. The external runner matches its request, installed APK
hash and required evidence. A manually exported JSON cannot prove these external
bindings by itself.

CPU fields, including `cases`, remain at the top level. The shell copies the CPU
status to `cpu_status`, adds `graphics_probe`, and sets combined `status` to
`passed` only if both statuses pass. Vulkan failure retains completed CPU
results. Java/loading/persistence errors can produce a top-level structured
failure instead.

`android_shell` retains schema version 1 and records:

| Field | Meaning |
| --- | --- |
| `run_id`, `request_id` | Per-run identifiers, not hardware identifiers |
| `started_at_epoch_ms`, `finished_at_epoch_ms` | Device wall-clock milliseconds; finish exists after completion |
| `elapsed_realtime_ms` | Whole-run monotonic duration, not a speed benchmark |
| `process_id` | Process executing this run |
| `app_version_name`, `app_version_code` | Self-reported package version, `0.0.4` / `4` |
| `manufacturer`, `model` | Non-unique Android device descriptions |
| `android_api`, `android_release` | Android API level and release |

`graphics_probe.device` contains Vulkan name, physical-device type, API version,
driver version, vendor ID and device ID. No hardware serial, Android ID,
advertising identifier or GPU UUID is collected. Per-run identifiers remain for
stale-result checks.

Before native loading, the shell atomically replaces the old report with a
`running` marker. The combined size limit is 1 MiB + 64 KiB + 16 KiB. Saved bytes
are read back and compared before displaying success. Only one latest report and
AtomicFile's transient replacement/recovery files are retained. A failed save
removes obsolete results and displays failure. Native crashes, process death or
hangs may leave incomplete evidence; the external runner owns the deadline.
Java does not attempt unsafe termination of a native thread.

## Save report

<!-- CodexAstraUlt: Pin exact completed bytes to a user-selected document and
keep the provider optional, with no broad permissions or file IO on the UI thread. -->

**Save report** becomes available after successful persistence, including a
completed failure report. `ACTION_CREATE_DOCUMENT` uses MIME type
`application/json` and suggests `droidds-latest-probe.json`. Android grants access
only to the chosen document; no broad storage or persistent URI permission is
requested.

The controller pins the exact saved report bytes with an opaque export token.
The same worker writes and closes the document stream. Reruns cannot silently
redirect an old selection to a new report, and stale picker results are ignored.
Activity recreation retains only tokens/request codes, not a report-sized
Bundle. Process death safely expires the selection. Cancellation, a missing
provider or an export failure preserves the private report and permits retry or
ADB retrieval. The picker is optional even on stripped-down Android systems.

```bash
adb -s YOUR_THOR_SERIAL exec-out run-as org.droidds.probe \
  cat files/latest-probe.json > droidds-latest-probe.json
```

## Validation boundary

<!-- CodexAstraUlt: Keep strict compile/host checks and reported device readbacks
separate from unexecuted lifecycle, picker and full-renderer acceptance criteria. -->

Java compiles against SDK 35 with Java 8 language/API compatibility and strict
warnings. JNI/Vulkan C uses NDK 27.3.13750724 for AArch64/API 29 with
`-std=c11 -Wall -Wextra -Werror`. The host helper uses the same C and shaders;
`tools/build_vulkan_probe.py --require-validation` requires a real host driver
and Khronos layer. `validate_graphics_report` independently validates output.

The host checks do not execute the Android picker, lifecycle or physical GPU.
The owner's separate 0.0.3 Thor report supplies passing evidence for the earlier
physical-GPU baseline. The expanded 0.0.4 device checks remain pending. Passing
these fixtures does not qualify PICA accuracy, Dark Moon, Xenoblade, Sonic, game
speed, sustained memory behavior or 16 KiB-page hosts.
