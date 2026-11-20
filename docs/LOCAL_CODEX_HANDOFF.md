# Local Dark Moon Native/CPU performance handoff

<!-- CodexAstraUlt: Point future batches to verified remote evidence and the owner's completed local cleanup. -->
**Storage update, 2026-11-20:** [cleanup is complete](host-tests/local-cleanup-2026-11-20.md). Local run directories retain summaries; obsolete raw data, chat exports, diagnostic targets and private APK copies were removed. Use the [verified report archive](host-tests/archived-local-reports-2026-11-20.md) and [package identity ledger](host-tests/local-artifact-ledger.csv). The owner retained preparation and both completed title builds for reuse. Follow [the immediate cleanup policy](HOST_SETUP_CLEANUP.md) after future batches.

<!-- CodexAstraUlt: Point a resumed session to the owner-requested local save locations and completed code17 evidence before the historical packaging handoff below. -->
**Continuation update, 2026-11-09:** code 17 testing and verified report publication are complete. Start with [the saved local session locator](LOCAL_SESSION_CONTINUATION.md) for the retained resume summary. Do not repeat completed code 17 packaging/testing merely to resume. The code 18 handoff below is a separate new batch. Every new Thor/ADB batch still requires fresh explicit owner approval.

<!-- CodexAstraUlt: Hand off verified code 18 cloud work while preserving
completed code 17 evidence and the unperformed new private device qualification. -->
Published **[preview.7/code 17](https://github.com/RegiRex/DroiDDS/releases/tag/v0.0.8-preview.7)**
passed local/runtime/package and hosted main checks at `9296010`, with tag
publication and independent download verification at `1c7fffa`. Preserve its
[build record](builds/0.0.8-transfer-followup.md) and completed device report.

Current candidate: **[preview.8/code 18](https://github.com/RegiRex/DroiDDS/releases/tag/v0.0.8-preview.8)**,
published and independently verified. Its immutable NativeReadback profile
removes unused upright/screen captures for the title frontend's native-byte
consumer, retaining native capture/sync/submission and default scaled/direct
modes. Fixed capture/phase/readback metrics are included. Local correctness/
runtime, retained-library APK, independent bundle and hosted main checks pass at
`0e3f211`; tag publication and independent public-download verification
pass at `d1d70ac`. Read the
[verified build record](builds/0.0.8-native-readback-followup.md).
The new Thor check is **unperformed**, with no handheld gain established.
Repackage the retained ARM64 library and prepare a compatible update before
requesting the owner's explicit approval for any Thor/ADB access. The
[native Android architecture investigation](NATIVE_ANDROID_DIRECTION.md) stages
GPU resource/graphics work while preserving AOT, title ABI and completed libraries.

Published **[preview.6/code 16](https://github.com/RegiRex/DroiDDS/releases/tag/v0.0.8-preview.6)**
passed local correctness/runtime, retained-library APK, independent bundle and
hosted main checks at `64f1404`; tag publication and independent public-download
verification pass at `2354ed0`. Its
[build record](builds/0.0.8-service-projection-followup.md) preserves those identities.
Historical [code 15](builds/0.0.8-cpu-decode-followup.md) preserves its separate
implementation `f687911` and release `365c1a0` identities.

## Completed evidence

<!-- CodexAstraUlt: Preserve the actual inactive route and fresh audio report;
newly planned native-readback work has no device performance result yet. -->
The [code 17 report](device-tests/0.0.8-preview7-dark-moon-thor.md) reached file
selection and stopped normally at **18.66% speed**, essentially unchanged from
code 16's 18.70%. Tiled accepts/deferred counters are zero. Hardware-transfer
attempts take **23.980 s** and texture synchronization **5.906 s**. Retain
**1,531 underruns**, 480 discarded input frames and the owner's fresh severe
clipping observation; waveform clipping is not measured. Frame events are not
unique game FPS. Existing File 1/save state remains preserved.

The preparation, **521 Linux objects/library**, **521 ARM64 objects/library**,
imports, saves, signer, prior reports and local handoff suffix remain reusable.
Further Thor GPU tests and audio-perfection work remain deferred.

## Connection approval

<!-- CodexAstraUlt: This is the owner's explicit instruction, separate from
authorization to continue cloud coding, builds and uploaded-report review. -->
**“Signal me before connecting” means stop and wait for explicit approval.**
Before any new Thor/ADB connection or device-work batch, including discovery,
report export, installation or testing, signal the owner and wait. Notification
alone, an available device or an earlier batch does not authorize access.
Prepare the compatible package first, using prior verified build/installation
records without querying the device in advance.

## Suggested task for local Codex

<!-- CodexAstraUlt: Keep the future task limited to compatible repackaging,
approved bounded testing and direct diagnostic delivery. -->
```text
Safely update RegiRex/DroiDDS to current main, preserving local work.
Follow “Current Dark Moon repackaging and audio test” in docs/ANDROID_TITLE_BUILD.md.
Read the verified preview.8 build record before repackaging.
Reuse recorded tools, preparation, completed ARM64 compilation and owner signing
profile. Repackage only, keeping the same package/certificate and a code above
the last verified installation, at least 18. Use prior records before connecting.
Preserve imports, saves, both completed title builds, local continuation files
and all previous reports.

Verify the package, then signal me and STOP for explicit approval before any
Thor/ADB connection or device work, including discovery, export, install or test.
After approval, confirm exclusive device operation and package compatibility.
Preserve the latest report before installing the compatible update.

Run once with Native execution, CPU vertex shaders and Vulkan 1x. Press A around
91 seconds after Play if ready, then normal Stop around 110 seconds; never exceed
120 wall seconds. Stop early on failure/corruption and do not extend for a late
prompt. Record actual input timing, progression and audible/visual observations.

Export the full JSON after stop/failure and before restart. Follow
docs/DEVICE_REPORT_HANDOFF.md to upload reviewed reports, the short summary and
any relevant bounded failure excerpt; verify remote bytes and return links.
Keep private game/build/signing data and raw captures local. Do not repeat
preparation or title compilation, reset saves, or perform further GPU trials.
```
