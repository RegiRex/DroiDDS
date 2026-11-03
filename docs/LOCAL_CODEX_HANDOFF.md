# Local Android title build handoff

<!-- CodexAstraUlt: Replace completed reconnaissance/comparison instructions
with the actual next task, so local agents do not replay old tests or stop on
prerequisites that the isolated setup now supplies. Historical evidence stays
in linked result records instead of competing with current instructions. -->
Current task, **2026-11-03**: build Dark Moon for Android from its retained,
validated preparation, then perform the first bounded title test on the Thor.
Use `RegiRex/DroiDDS` and preserve the local checkout's existing work.
Read [AGENTS.md](../AGENTS.md), the [Android title contract](ANDROID_TITLE_CONTRACT.md)
and the [consolidated build/device task](ANDROID_TITLE_BUILD.md#one-consolidated-local-build-and-device-task).

## Completed evidence

<!-- CodexAstraUlt: Preserve measured results without requiring another host
trace or projecting original-title evidence onto a private game. -->
- The owner reports a successful private preparation and **521/521 Linux
  objects plus a linked library**. Reuse the preparation; Android needs separate
  ARM64 objects. Preserve the Linux objects, library, manifests and reports.
- The [857ff47 host comparison](host-tests/dark-moon-native-2026-11-02.md) is
  complete. Raw CPSR differences remain; one synchronized sample agrees and
  three later boundaries are missing on both routes. Do not repeat this test
  unchanged, increase its limits or treat the bounded match as full parity.
- The [preview.2 Thor result](device-tests/0.0.7-preview2-thor-title.md) passes
  its original-title checks. The owner confirms both images, controls, touch,
  pause/resume and steady sound. This does not establish Dark Moon boot.
- The [first Android attempt](host-tests/dark-moon-android-prerequisites-2026-11-03.md)
  stopped before compilation at `2d55dc7`: Rust's Android target, SDK/NDK, Java
  and an offline dependency were missing. No private Android compilation or
  device test occurred in that attempt.
- The follow-up on `e76f5d5` failed twice resolving the pinned NDK download
  hostname. No `env.sh`, Android compilation or device result was produced.
  Follow the [name-resolution guidance](ANDROID_TITLE_TOOL_SETUP.md#download-name-resolution-failures)
  instead of repeating the same setup in the same failing network context.

## Continue setup and compilation

<!-- CodexAstraUlt: A tested owned tool directory resolves missing prerequisites
without global installs, source regeneration or another tool-only handoff. -->
Use the [isolated Android tool setup](ANDROID_TITLE_TOOL_SETUP.md) when any
prerequisite is missing. It supplies Rust 1.95.0 and the Android target, pinned
SDK/NDK, JDK 17 and locked dependencies in one directory outside Git. Source its
`env.sh`, then continue the consolidated task immediately. Normal permitted
network access is needed for initial downloads; no system packages, shell
profiles or existing Rust installations are modified.

The [input/save corrections](builds/0.0.7-input-save-corrections.md) are tested
shared-runtime improvements. They preserve private preparation and compiler
helper identities. If another compilation is already running, finish it with
its existing checkout; updated APK packaging can consume those completed Android
objects afterward. Use separate output directories for concurrent builds, and
serialize jobs sharing one Cargo target directory.

Keep game data, generated C, title libraries, private APKs, captures and signing
keys local. Use a persistent owner signing profile for the private title. The
documented first-install procedure may create a new dedicated key if none exists;
it must never replace a prior key or bypass an installed app's signature check.
Only one session operates the Thor at a time. Preserve existing app data and
return the exact unperformed step if device access is unavailable.

## Suggested task for local Codex

<!-- CodexAstraUlt: Limit this prompt to the current build and device test;
deferred project preferences do not belong in its execution instructions. -->
```text
Safely update RegiRex/DroiDDS to current main, preserving local work.
Read docs/ANDROID_TITLE_TOOL_SETUP.md and docs/ANDROID_TITLE_BUILD.md.
Run the isolated setup for missing prerequisites, then source its env.sh.
Continue the consolidated Android compilation, packaging and device task in
docs/ANDROID_TITLE_BUILD.md without stopping after setup succeeds.
Reuse the validated Dark Moon preparation and preserve all 521 Linux objects,
their library and prior reports. Return android-title-build-summary.md.
```

<!-- CodexAstraUlt: Keep practical limits explicit without turning source or
original-fixture results into playable-beta qualification. -->
The consolidated task specifies at most four default compilation batches, only
resuming a progressing `incomplete / batch_budget` result, then fresh private
APK packaging and one bounded Native opening test. A bounded Interpreter
comparison may classify a Native failure. Report actual images, controls,
audio, execution/rendering counters and the first blocker separately.

The cloud session does not share the laptop's private files or Thor connection.
A successful build is not a game-boot result; an opening scene is not sustained
playability. Follow the [roadmap](ROADMAP.md) and [title matrix](TEST_STRATEGY.md#primary-title-matrix)
for subsequent qualification of Dark Moon, Xenoblade Chronicles 3D and Sonic &
All-Stars Racing Transformed. Roadmap 0.0.7's owned-game boot gate and the
0.1.0 beta gates remain open.
