# Build an Android title candidate

<!-- CodexAstraUlt: Replace the completed code 14 task with the new candidate;
publication must pass before another private device run. -->
The published candidate is **0.0.8-preview.4/code 14**. The next candidate,
**0.0.8-preview.5/code 15**, is under development with cloud/package/publication
checks pending. Read its [build record](builds/0.0.8-cpu-decode-followup.md).
The player retains application ID `org.droidds.title.t<program_id>` and the
[manifest/runtime contract](ANDROID_TITLE_CONTRACT.md).

The [completed code 14 tests](device-tests/0.0.8-preview4-dark-moon-thor.md)
record 17.31% menu speed and 16.66% in the separate owner intro. The owner reports
no intro glitches; neither report records runtime/rendering errors. No speed
improvement or playable segment is established. Further Thor GPU tests and
audio-perfection work remain deferred; no unchanged retry is required.

An existing preparation supplies the same generated C and headers to both target
compilers. Its completed Linux and ARM64 libraries remain intact and reusable;
this update rebuilds the shared player/frontend, not the 521 title objects.

## Current Dark Moon repackaging and audio test

<!-- CodexAstraUlt: Keep the existing anchor stable while replacing the finished
GPU diagnostic with one CPU performance test after verified publication. -->
Preview.5's local correctness/runtime/graphics/package, hosted publication and
independent public-download checks are pending. Wait for those gates before this
retained-library update and bounded Thor run;
no separate public original APK installation is required. Keep **Native guest
execution, CPU vertex shaders, Vulkan 1×** and comparable menu
progression/settings. Automatic stays the normal default.

Use one CPU-vertex menu run matching the earlier menu tests: press A around **91 seconds after
Play** if the title prompt is ready, then request normal Stop around **110
seconds**. Never exceed **120 wall seconds**. Record actual input timing and
progression; do not extend for a late prompt. Stop early on failure or visual
corruption. Further GPU testing is deferred. Record actual worker-running time
separately. Do not extend the run or replay a failure. If the app has
already failed/stopped, end observation and preserve the error instead of
counting the observer's later wait as guest execution.

Preserve code 14 menu/intro and all other prior reports before any new session.
The app keeps one `files/latest-title-report.json` and replaces it on later
sessions. **After each stop or failure, export the complete JSON immediately,
before any restart.** Capture a relevant bounded driver-log excerpt only when
needed to explain a new failure. Existing GPU evidence stays separate.

<!-- CodexAstraUlt: Report delivery remains part of the actual test task;
existing exports and GitHub access avoid new logging or another device run. -->
Follow [report transfer](DEVICE_REPORT_HANDOFF.md): review and upload the full
JSON, short summary and any relevant failure excerpt to
`RegiRex/DroiDDS`, verify the remote files, and return commit/file links.
Preserve raw originals locally. A missing upload is not grounds for another run.

Reuse the successful tool environment, private preparation, completed ARM64
compilation directory containing `compiled-manifest.json`, and owner signing
profile. Source the existing environment in each build shell. Use a fresh private
package output with a version code **greater than the installed code and at least
15**. The retained title needs only this packaging command:

```bash
python3 tools/build_android_title.py \
  --preparation "$DROIDDS_PREPARATION" \
  --compilation "$DROIDDS_ARM64" \
  --output "$DROIDDS_PACKAGE" \
  --sdk "$DROIDDS_SDK" \
  --java-home "$DROIDDS_JAVA" \
  --version-code "$DROIDDS_VERSION_CODE" \
  --signing-profile /absolute/path/to/existing-owner-title-signing.json
```

Resolve paths and install code from the successful local build and installed
package. Keep the same package and certificate for a compatible update; preserve
imports and remaining saves. Do not uninstall, clear app data, create a
replacement key, repeat tool setup, regenerate preparation, recompile either
set of title objects or reconfigure permissions.

<!-- CodexAstraUlt: Limit the local prompt to the forthcoming CPU update;
preserve original reports and deliver reviewed copies with verified links. -->
```text
Safely update RegiRex/DroiDDS to current main, preserving local work.
Follow the current Dark Moon repackaging section in docs/ANDROID_TITLE_BUILD.md.
Confirm preview.5 cloud route/package/publication gates passed before packaging.
Preserve the existing code 14 menu/intro reports and all earlier evidence.
Reuse working tools, preparation, completed ARM64 compilation and owner signing
profile. Repackage only with the same package/certificate and an install code
above the installed one, at least 15. Install a compatible update preserving
imports and saves.

Keep Native execution, CPU vertex shaders, Vulkan 1x and comparable menu
progression/settings. Run once: press A around 91 seconds after Play if the title
prompt is ready, then Stop around 110 seconds; never exceed 120 wall seconds.
Stop early on failure/corruption and do not extend for a late prompt. Record the
actual input timing and progression. Further GPU testing is deferred.
Export the complete JSON immediately after stop/failure and before any restart.
Record actual worker time, CPU processing, input/scene progression, rendering
paths and observed audio/images separately. Preserve a relevant bounded
driver-log excerpt if needed.

Follow docs/DEVICE_REPORT_HANDOFF.md to upload reviewed full reports, a short
android-title-build-summary.md and relevant failure excerpts. Verify remote
bytes and return commit/file links. Keep raw originals, both title builds and
private game/build/signing files local. Do not repeat setup, preparation, title
compilation, historical traces or permission configuration, or reset saves.
```

<!-- CodexAstraUlt: Keep diagnostic timing scopes and failed-path evidence
explicit instead of treating selected GPU policy or short failure as speed data. -->
`runtime.gpu.vertex_processing.cpu_wall_nanoseconds` is a command-processing
subset covering vertex/geometry execution, output packing and worker joins.
Attribute decoding, clipping and Vulkan work are outside it. CPU batch/input
counts, recorded GPU/placed draws and dynamic blend/logic flags identify actual
paths. A requested GPU flag does not establish submitted GPU work.

<!-- CodexAstraUlt: Keep added CPU subsets and path-selection counts distinct;
their scopes cannot be summed with parent command/core timers. -->
`input_decode_wall_nanoseconds` and `placement_wall_nanoseconds` are disjoint
from CPU shader time and from each other. Decode excludes the initial raw index
read and cached input-plan lookup; placement stops before Vulkan draw work.
`cpu_geometry_batches` counts geometry-mode selection, not completed geometry
invocations. `cpu_parallel_vertex_batches` counts batches meeting the vertex
input threshold, not geometry-stage work or active workers. The full report
retains these fixed totals without per-vertex histories.

Retain the completed GPU diagnostic as deferred evidence.
`runtime.gpu.hardware.pipeline_failures` retains first observed `foreground`,
`background` and `cache_probe` failures separately; an expected compile-required
cache miss is not a failure. Stage, static state, fragment constants and SPIR-V
size/fingerprint identify the attempted pipeline. The FNV-1a fingerprint is
diagnostic, not cryptographic. Keep the first failure and subsequent fallback
distinct. A short failed GPU
run cannot qualify performance or audio. Gameplay, saving/loading, sustained
speed and general GPU shader behavior remain unqualified. The first-title
procedure below is for titles without a completed Android library.

## Required build tools

<!-- CodexAstraUlt: Replace the prerequisite-only stop with the tested isolated
setup so missing Android tools do not cause another avoidable handoff. -->
Run from the `RegiRex/DroiDDS` checkout on Linux x86-64 with Python 3.11 or newer,
pinned Rust/Cargo 1.95.0, its `aarch64-linux-android` target, and the locked offline
dependencies. The SDK must contain NDK **27.3.13750724**, Android platform **35**,
build tools **35.0.0**, and the NDK's `shader-tools/linux-x86_64/glslc` and
`spirv-val`. Supply the existing JDK with `javac` and `keytool` explicitly.
If any prerequisite is missing, use the [isolated tool setup](ANDROID_TITLE_TOOL_SETUP.md):

```bash
python3 tools/setup_android_title_tools.py \
  --output "$HOME/droidds-android-tools-1.95.0-r27d"
source "$HOME/droidds-android-tools-1.95.0-r27d/env.sh"
```

This supplies the pinned tools and locked dependencies without system packages,
shell-profile changes or modifications to existing Rust installations. It sets
`DROIDDS_SDK` and `DROIDDS_JAVA` for the commands below. Continue the title build
after setup succeeds; do not stop merely to report that the tools are ready.

Use private directories outside Git whose parents already exist. Set these to
the actual retained preparation and new output locations:

```bash
# CodexAstraUlt: Set these two only when reusing existing tools instead of env.sh.
# DROIDDS_SDK=/absolute/path/to/android-sdk
# DROIDDS_JAVA=/absolute/path/to/jdk
DROIDDS_PREPARATION=/absolute/path/to/validated-preparation
DROIDDS_ARM64=/absolute/path/to/new-android-compilation
DROIDDS_PACKAGE=/absolute/path/to/new-android-package
```

`DROIDDS_PREPARATION` contains `manifest.json`, `report.json`, `prepared/` and the
retained input snapshot. The two output paths must be absent for their initial
commands. Keep game data, preparation, generated code, receipts, libraries and
private APKs local. None of those private artifacts belongs in Git, CI or a
public release.

## Compile retained C for ARM64

<!-- CodexAstraUlt: Use a separate pinned target contract and preserve every
validated receipt across bounded batches. -->
```bash
python3 tools/compile_android_title.py \
  --preparation "$DROIDDS_PREPARATION" \
  --output "$DROIDDS_ARM64" \
  --sdk "$DROIDDS_SDK"
```

The tool selects `aarch64-linux-android29-clang` from the pinned NDK. It runs one
compiler command at a time with `-O2`, `-ffp-contract=off`, `-fno-math-errno`, PIC
and hidden visibility. It does not enable fast math. Default limits are:

| Limit | Default |
| --- | --- |
| Compiler/linker batch | 1800 wall seconds |
| Individual command | 300 wall seconds |
| CPU per process, including its threads | 260 seconds |
| Address space per process | 4096 MiB |
| Retained build-directory allowance | 4096 MiB |
| Individual object/temporary file | 128 MiB |
| Individual linked-library/temporary file | 512 MiB |
| Retained command log tail | 64 KiB |

The compiler process group has a wall deadline; child processes inherit CPU and
address-space bounds separately. Verification/auditing/reporting can extend the
elapsed time beyond a batch deadline. The retained directory allowance is checked
between commands; it is not an aggregate filesystem quota.

Receipts bind source/header hashes, preparation identity, generated-code ABI
4/generation 3, exact compiler/linker binary hashes, NDK header/runtime inventories,
target/API, options and the generated identity unit. The SDK inventories do not
attest the provenance of the compiler binaries. The six historical host
compilation helpers remain unchanged.

Each attempt preserves its report and completed objects. Continue only an
`incomplete / batch_budget` result with increasing validated-object count:

```bash
python3 tools/compile_android_title.py \
  --preparation "$DROIDDS_PREPARATION" \
  --output "$DROIDDS_ARM64" \
  --sdk "$DROIDDS_SDK" \
  --resume
```

Resume uses the same output directory and revalidates all retained identities.
Stop on a failed command, rejection, interruption or zero progress; do not change
flags, skip sources, discard receipts or increase limits to obtain a pass.
`compiled-manifest.json` exists only after every object and the linked library
validate. Static admission checks AArch64/Bionic dependencies, 16 KiB ELF
alignment, SONAME, ABI exports, relocation tables and exact entry/origin bytes.
It never loads or executes the title library.

## Owner signing and private packaging

<!-- CodexAstraUlt: An explicit owner-local profile preserves upgrade identity;
password values never become command arguments or build-report fields. -->
Use an owner-selected keystore outside Git. Keep a backup under the owner's
control. The same per-title application ID and signing certificate are needed
for an update that retains Android app data. Do not uninstall or clear app data
to bypass a signing mismatch.

<!-- CodexAstraUlt: A first private build needs a persistent owner key, rather
than another handoff solely because no previous title profile exists. -->
For a first title with no existing installation or selected key, the local agent
may create a new key and profile in a dedicated owner-private signing directory
using the installed JDK. Generate a random password, keep its local file at mode
0600 and the directory at 0700, and pass it through the profile's environment
variable names. Preserve the key/profile/password together for owner backup;
report only the public fingerprint and their local locations. Existing keys
must not be replaced. An installed title whose signer cannot be matched remains
a blocker; creating a new key cannot make that installation safely updatable.

Create a local JSON profile using the existing key's absolute path, alias and
public SHA-256 certificate fingerprint. The placeholder below must be replaced
with the actual 64 lowercase hexadecimal digits:

```json
{
  "schema_version": 1,
  "kind": "droidds_android_signing_profile",
  "keystore": "/absolute/path/to/owner-title.keystore",
  "alias": "owner-title",
  "store_password_env": "DROIDDS_TITLE_STORE_PASSWORD",
  "key_password_env": "DROIDDS_TITLE_KEY_PASSWORD",
  "certificate_sha256": "REPLACE_WITH_64_LOWERCASE_HEX_DIGITS"
}
```

Supply the two passwords through the named environment variables, without
putting their values in shell history:

```bash
read -r -s -p "Keystore password: " DROIDDS_TITLE_STORE_PASSWORD
read -r -s -p "Key password: " DROIDDS_TITLE_KEY_PASSWORD
export DROIDDS_TITLE_STORE_PASSWORD DROIDDS_TITLE_KEY_PASSWORD
```

After compilation completes:

```bash
python3 tools/build_android_title.py \
  --preparation "$DROIDDS_PREPARATION" \
  --compilation "$DROIDDS_ARM64" \
  --output "$DROIDDS_PACKAGE" \
  --sdk "$DROIDDS_SDK" \
  --java-home "$DROIDDS_JAVA" \
  --version-code 11 \
  --signing-profile /absolute/path/to/owner-title-signing.json
```

Select a higher version code for a later update of the same application ID.
The builder uses the checkout's shared Cargo target directory: serialize it with
other Cargo jobs using that directory and hold source files stable during the
build. Its default Cargo job count is two. It does not modify the selected SDK,
JDK, preparation, compilation or owner keystore.

Packaging holds the compilation's shared lock, repeats static admission and
copies exactly `libdroidds_title.so`, `libdroidds_title_player.so` and
`libdroidds_title_jni.so`. It checks the dependency graph, reviewed shader assets,
Java controls, notices, ELF dependencies/alignment, binary APK manifest, signed
ZIP inventory/alignment and signing fingerprint. Source hashes and preserved
inputs must still match at the end. The package includes the manifest metadata;
a private game is imported separately in the app and must match the exact bound
input bytes.

Success produces `droidds-title.apk` and `build-report.json` with `status: built`.
Retain failure reports and use a fresh package output after correcting a failed
gate. ELF/ZIP 16 KiB alignment is a packaging property; native execution currently
requires Android **4 KiB** pages and rejects unsupported native page sizes.

## Reproduce the public original candidate

<!-- CodexAstraUlt: Public signing is restricted to byte-verified authored
fixtures; a program ID or filename cannot make private content publishable. -->
The included candidate uses revision 2 of the authored interactive homebrew guest.
It preserves pending DSP initialization when A is held at startup; the original
0.0.6 and 0.0.7-preview.2 fixtures remain revision 1 in historical evidence.
Its program ID is `000400000d5d0006`; the emitted input is 30,720 bytes with SHA-256
`09cf47cc188f140a8bd0e146efce5d9ef63ff10bbaa035c8c557fac32e4a8003`.
Generate a fresh original input/preparation with the existing pinned tools:

```bash
cargo build --offline --locked --release -p droidds-runtime-probe --features producer
cargo build --offline --locked --release -p droidds-title-builder
target/release/droidds-runtime-probe emit-homebrew \
  --output /absolute/path/to/new-original-homebrew
python3 tools/prepare_private_title.py \
  --input /absolute/path/to/new-original-homebrew/homebrew-fixture.cxi \
  --output /absolute/path/to/new-original-preparation
```

Set `DROIDDS_PREPARATION` to that original preparation, choose fresh ARM64/package
outputs, and run the ARM64 compilation command above. Package the original:

```bash
python3 tools/build_android_title.py \
  --preparation "$DROIDDS_PREPARATION" \
  --compilation "$DROIDDS_ARM64" \
  --output "$DROIDDS_PACKAGE" \
  --sdk "$DROIDDS_SDK" \
  --java-home "$DROIDDS_JAVA" \
  --version-code 15 \
  --diagnostic-signing --diagnostic-fixture homebrew
```

The diagnostic builder independently emits the current original fixture and
requires its complete byte identity to match before including
`assets/original-title.cxi`. It creates an isolated diagnostic key in the fresh
package directory. Preserve that key and recorded public fingerprint for later
updates; it is separate from the existing probe signer. Never publish the key,
passwords or the whole build directory. The diagnostic flag does not accept a
private title. The owner-signing path does not include any input asset.

On the Thor, choose **Load included test**, then **Native** and **Play**. Check
both guest screens, image markers, D-pad movement, lower-view touch, and the
steady tone whose pitch changes while A is held. Both guest screens currently
appear within one physical Android display. Test Pause/Resume, a brief background
transition and Stop, then **Save report**. Repeat with the explicit Interpreter
route as a separate comparison. Record visible/audible observations separately
from counters. These original controls do not establish private-game boot,
physical dual-display support, direct Vulkan presentation or sustained Thor
performance.

## One consolidated local build and device task

<!-- CodexAstraUlt: A finite preparation-to-APK task replaces repeated isolated
trace handoffs while preserving failures and the completed host compilation. -->
This is the **first-title** procedure for a preparation without a completed
Android compilation. Dark Moon has completed it; use the
[current repackaging task](#current-dark-moon-repackaging-and-audio-test) above.
Give the local agent the retained preparation, selected signing
location and fresh output locations once. The following is the integrated task:

<!-- CodexAstraUlt: The fulfilled host comparison is evidence, not a request
to rerun it; move directly to the separate Android artifact. -->
The owner's `857ff47` Linux comparison is complete. Use current main for this
Android task; preserve the existing host library and all earlier evidence.

<!-- CodexAstraUlt: The owner may already be compiling in a separate local
session. Runtime fixes can enter packaging without discarding its title objects. -->
If a compilation is already running, finish it with that checkout and its
recorded identities. The [input/save corrections](builds/0.0.7-input-save-corrections.md)
change the runtime/frontend, not the generated title code or compilation
contract. After compilation finishes, a fresh APK packaging attempt from the
updated checkout can reuse the completed Android compilation.

```text
Use the current RegiRex/DroiDDS checkout, preserving existing work.
Read docs/ANDROID_TITLE_BUILD.md and docs/ANDROID_TITLE_CONTRACT.md.
Reuse the successful private preparation; preserve the completed Linux library.
If Android build prerequisites are missing, follow docs/ANDROID_TITLE_TOOL_SETUP.md:
run tools/setup_android_title_tools.py into its dedicated directory outside Git,
then source its env.sh. Use normal permitted network access for this setup and
locked dependency fetch. Do not install system packages or change shell profiles.
Verify tools, offline dependencies and output/signing locations, then continue
directly into compilation in this task.

Compile that preparation into a separate ARM64 Android output with the pinned
installed NDK and default limits. Allow at most four default compilation batches
in this task, including the initial batch. Resume only incomplete / batch_budget
with unchanged identities and a strictly increasing validated-object count.
Stop on any other failure, zero progress, interruption or the fourth batch.

If compilation finishes, build the title APK in a fresh private output using
the owner signing profile, explicit version code and installed tools. If this
is a first private installation and no key/profile exists, create and preserve
a dedicated owner-local key/profile/password as documented above. Never replace
an existing key or use the disposable public diagnostic signer for this game.
Serialize the shared Cargo target and hold build sources stable. Do not alter
sandbox/device access, regenerate title C, repeat host traces or upload private
artifacts. Report a failed setup with its precise error and local log, or an
unresolved existing signing identity, as a concrete blocker.

If the Thor is available and no other session is operating it, record the exact
APK/package/version/certificate and device/driver identity. Install only a new
package or a compatible update preserving app data; never uninstall, clear data,
or bypass a signature/version mismatch. Import the exact matching base input
through the app without overwriting the original or another app's files.

Run one Native opening test for at most 120 wall seconds or until its first
failure, then stop normally. Keep bounded device logs, observations and the
original exported title report local; publish reviewed diagnostic copies using
docs/DEVICE_REPORT_HANDOFF.md. If Native fails and the same import remains valid,
one equally bounded Interpreter comparison may classify the difference. Record
screens, controls, audio, native/fallback work, rendering activity and the first
blocker separately. An opening scene or frame counter is not playable-beta or
speed qualification. If device access or UI automation is unavailable, return
the validated APK and the exact unperformed device step without repeating builds.

Return one short android-title-build-summary.md outside the managed build
directories: source/tool identities, each batch's reused/new/remaining counts,
final library and APK hashes, package/version/public certificate identity,
passed or failed gates, device result or unperformed step, and local APK/report
paths. Preserve prior outputs. Omit raw game content and personal paths from any
shareable summary; never publish the private input, generated code or APK.
Upload the reviewed diagnostic reports, summary and needed failure logs using
docs/DEVICE_REPORT_HANDOFF.md; verify them remotely and return commit/file links.
```

The four batch ceilings cover at most two hours of compiler/linker wall budgets;
verification and the separate APK build add time. One consolidated report is
sufficient whether the result is a completed APK or a concrete build blocker.
Device execution is a distinct qualification within that task; it is never
inferred from compilation, package validation or a successful original fixture.
