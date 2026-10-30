# Build an Android title candidate

<!-- CodexAstraUlt: Reuse the completed preparation while keeping host and
Android artifacts, signing identity and qualification evidence distinct. -->
The title candidate is version **0.0.7-preview.2**, with explicit install code
**9** for the reviewed original homebrew candidate. It uses a separate application
ID, `org.droidds.title.t<program_id>`. Read the
[manifest/runtime contract](ANDROID_TITLE_CONTRACT.md) for admission and storage
rules. This candidate does not complete the 0.0.7 owned-game boot milestone.

An existing successful preparation supplies the same generated C and headers to
both compilers. Reuse it without regenerating title code. The completed Linux
library and its objects remain intact; Android requires a separate ARM64/Bionic
compilation directory. A Linux object or library cannot be installed on the Thor.

## Required installed tools

<!-- CodexAstraUlt: State concrete prerequisites without making an installation
or permission change part of a title-build command. -->
Run from the `RegiRex/DroiDDS` checkout on Linux x86-64 with Python 3.11 or newer,
pinned Rust/Cargo 1.95.0, its `aarch64-linux-android` target, and the locked offline
dependencies. The SDK must contain NDK **27.3.13750724**, Android platform **35**,
build tools **35.0.0**, and the NDK's `shader-tools/linux-x86_64/glslc` and
`spirv-val`. Supply the existing JDK with `javac` and `keytool` explicitly.
Missing tools or offline dependencies are a reported prerequisite blocker.

Use private directories outside Git whose parents already exist. Set these to
the actual retained preparation and new output locations:

```bash
DROIDDS_SDK=/absolute/path/to/android-sdk
DROIDDS_JAVA=/absolute/path/to/jdk
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
  --version-code 9 \
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
The included candidate uses the original interactive homebrew guest from 0.0.6.
Its program ID is `000400000d5d0006`; the emitted input is 30,720 bytes with SHA-256
`efbf68988056b7973f14b934d792d87af430a15e7549cdf3a022e261b9aecbfd`.
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
  --version-code 9 \
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

## One consolidated local build task

<!-- CodexAstraUlt: A finite preparation-to-APK task replaces repeated isolated
trace handoffs while preserving failures and the completed host compilation. -->
Give the local agent the retained preparation, installed SDK/JDK, owner signing
profile and fresh output locations once. The following is the build task:

```text
Use the current RegiRex/DroiDDS checkout, preserving existing work.
Read docs/ANDROID_TITLE_BUILD.md and docs/ANDROID_TITLE_CONTRACT.md.
Reuse the successful private preparation; preserve the completed Linux library.

Compile that preparation into a separate ARM64 Android output with the pinned
installed NDK and default limits. Allow at most four default compilation batches
in this task, including the initial batch. Resume only incomplete / batch_budget
with unchanged identities and a strictly increasing validated-object count.
Stop on any other failure, zero progress, interruption or the fourth batch.

If compilation finishes, build the title APK in a fresh private output using
the supplied owner signing profile, explicit version code and installed tools.
Serialize the shared Cargo target and hold build sources stable. Do not install
new tools, change permissions, regenerate title C, repeat host traces or upload
private artifacts. Missing prerequisites or a missing signing profile are
reported blockers, not reasons to substitute diagnostic signing.

Return one short android-title-build-summary.md outside the managed build
directories: source/tool identities, each batch's reused/new/remaining counts,
final library and APK hashes, package/version/public certificate identity,
passed or failed gates, and the local APK/report paths. Preserve prior outputs.
Device installation and playability evidence are a separate next gate.
```

The four batch ceilings cover at most two hours of compiler/linker wall budgets;
verification and the separate APK build add time. One consolidated report is
sufficient whether the result is a completed APK or a concrete build blocker.
