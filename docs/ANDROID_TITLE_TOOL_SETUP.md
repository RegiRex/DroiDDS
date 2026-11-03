# Isolated Android build tools

<!-- CodexAstraUlt: Resolve the owner's missing Android prerequisites in one
owned directory without modifying the system or an existing Rust installation. -->
Use this setup when the Android title build reports a missing Rust Android
target, SDK/NDK, `javac`, or locked Cargo dependencies. It installs the required
tools in one directory outside Git. It does not use `sudo`, install system
packages, change shell profiles or Rust defaults, or build/run a private title.
Existing preparations, Linux objects, libraries, saves and signing files are
not inputs to setup.

Run from the current `RegiRex/DroiDDS` checkout on **Linux x86-64**, with
Python **3.11+** and the existing host `cc`, `git` and `sh`. Normal permitted
network access is required for the first run. If network access is unavailable,
setup records the failure; it does not change permissions or network settings.

```bash
python3 tools/setup_android_title_tools.py \
  --output "$HOME/droidds-android-tools-1.95.0-r27d"
source "$HOME/droidds-android-tools-1.95.0-r27d/env.sh"
```

The output directory must be absent or belong to this exact setup manifest.
Choose a different absent directory if the suggested name is already occupied
by unrelated files. Its parent must exist. Sourcing `env.sh` selects the tools
for the current shell and sets `DROIDDS_SDK` and `DROIDDS_JAVA` for the existing
[Android title build commands](ANDROID_TITLE_BUILD.md). Continue that build with
the retained preparation and a separate Android compilation directory; setup
does not regenerate title C or convert the completed Linux objects.

## Installed contents

<!-- CodexAstraUlt: List exact installed components and retained local inventory,
including the dependency cache needed by the existing offline packager. -->
| Component | Version | Location under the output directory |
| --- | --- | --- |
| Rust compiler, Cargo, host standard library | 1.95.0 | `rust/` |
| Rust Android standard library | `aarch64-linux-android`, 1.95.0 | `rust/lib/rustlib/` |
| Android NDK | 27.3.13750724 (r27d) | `sdk/ndk/` |
| Android build tools | 35.0.0 | `sdk/build-tools/` |
| Android platform | API 35, revision 2 | `sdk/platforms/` |
| Temurin JDK | 17.0.20.1+1 | `jdk/` |
| Locked Cargo dependencies | Current `Cargo.lock` | `cargo/` |
| Verified archives and file inventories | Pinned manifest | `archives/`, `receipts/` |
| Setup status and process logs | This installation | `setup-state.json`, `logs/` |

The eight archives total about **1.13 GB**; installed tools occupy about
**3.4 GB**, plus the Cargo cache (about **265 MiB** in the cloud validation),
retained archives and later build outputs. Setup requires at least **6 GiB**
free before extraction. Android compilation needs additional space. It omits
Android Studio, an Android emulator, ADB/platform-tools, Rust documentation,
rustfmt and Clippy. Official archive notices remain with their components.

Downloads come directly from Google, Rust and Eclipse Adoptium's official
release locations. `tools/android_title_toolchains.json` pins archive URLs,
sizes and SHA-256 hashes. The Google archives were also checked against their
official SDK repository metadata; Rust and JDK hashes match official release
metadata. Setup rejects a checksum mismatch before extraction or execution.

## Reuse and verification

<!-- CodexAstraUlt: Make repeat setup bounded and read-only for existing tools;
do not mistake installation checks for game execution or device qualification. -->
Repeating the setup command validates installed component bytes/modes and
refreshes only this installation's locked dependency cache. Successful setup
requires an actual ARM64 Android shared-library link, matching tool versions,
and `cargo metadata --offline --locked`. `setup-state.json` reports `ready`
only after those checks pass. A failed run retains completed components and
logs; rerunning the same command can resume their reuse. Changed component bytes
are rejected instead of silently repaired.

For a previously completed setup, `--offline` prevents network fetching:

```bash
python3 tools/setup_android_title_tools.py \
  --output "$HOME/droidds-android-tools-1.95.0-r27d" \
  --offline
```

Optional `--reuse-sdk /absolute/sdk` and
`--reuse-java-home /absolute/jdk17` select existing tools read-only. The SDK
must already contain every required component in the table; the JDK must be
version 17. Omit these options for an isolated complete installation. An
optional `--archive-cache /absolute/cache` reads verified official archives
without copying them into `archives/`; it never modifies that cache.

The installer records which SDK/JDK it selected, their version output, the
Cargo lock hash and whether each was reused. Keep the same selection when
resuming an existing Android compilation, whose receipts bind the compiler and
SDK contents. These setup checks establish build prerequisites; they do not
establish game boot, graphics correctness, sound or Thor performance.

## Cloud validation

<!-- CodexAstraUlt: Preserve executed setup evidence separately from authored
fixtures and the owner's still-pending private Android compilation. -->
On 2026-11-03, a fresh owned directory installed every component above from
verified official archives, using neither an existing SDK nor JDK. Locked
dependencies were fetched into its new Cargo cache. An offline repeat verified
all installed component receipts, linked the original Android test library and
completed locked offline Cargo metadata successfully. The same isolated tools
then built `droidds-title-player` for `aarch64-linux-android` in release mode with
`--offline --locked`, using a separate Cargo target directory. No private game
or device execution was involved. All **37** focused fixture tests pass,
covering rejected paths/archives, receipt tampering, safe reuse and process
output/time bounds; the main workflow discovers them with the other
`tools/tests/test_*.py` files.

<!-- CodexAstraUlt: Confirm the installer supports the complete existing build
path, including notices, Java, shaders, packaging and signed-asset verification. -->
The same fresh tools then completed the full original-title compilation and APK
path at source `ac42b38`: all three authored ARM64 objects, the offline generic
runtime, Java checks and signed APK audits passed. The four original-only assets
also passed independent bundle verification. See the
[integration evidence](builds/0.0.7-input-save-corrections.md#final-cloud-integration-checks).
This closes the cloud tool-setup check; the private title compilation remains
the local session's next task.
