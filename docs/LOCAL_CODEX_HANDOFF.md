# Local Dark Moon Native/CPU performance handoff

<!-- CodexAstraUlt: Replace the completed code 16 test with pending cloud work;
finish a reviewable package before requesting the next explicit device approval. -->
Next candidate: **0.0.8-preview.7/code 17**, under cloud development. The transfer
prototype defers tiled captures/submissions with a 32-transfer batch cap and
surface revalidation at each transfer boundary. The previous linear route stays
unchanged. Fixed route/subphase metrics are being evaluated. Correctness, benchmark, package and
publication gates remain pending. Do not repeat code 16 or begin a new Thor
batch now. Read [AGENTS.md](../AGENTS.md) and
[the current procedure](ANDROID_TITLE_BUILD.md#current-dark-moon-repackaging-and-audio-test).

Published **[preview.6/code 16](https://github.com/RegiRex/DroiDDS/releases/tag/v0.0.8-preview.6)**
passed local correctness/runtime, retained-library APK, independent bundle and
hosted main checks at `64f1404`; tag publication and independent public-download
verification pass at `2354ed0`. Its
[build record](builds/0.0.8-service-projection-followup.md) preserves those identities.
Historical [code 15](builds/0.0.8-cpu-decode-followup.md) preserves its separate
implementation `f687911` and release `365c1a0` identities.

## Completed evidence

<!-- CodexAstraUlt: Preserve the single faster sample and unresolved subphases;
transfer wall time and endpoint retention do not prove a particular cause. -->
The [code 16 report](device-tests/0.0.8-preview6-dark-moon-thor.md) reached file
selection at **18.70% speed**, versus code 15's 16.70%, with no reported runtime/
rendering errors or visible corruption. A/Stop occurred at 91.056/110.111 seconds.
A sustained or causal improvement remains unproven. Display transfers
(**26.917 s**) and texture copies (**6.061 s**) account for 97.82% of SVC time
outside PICA lists; their wait/readback versus conversion/copy costs remain
unseparated. Retain 1,532 underruns and 160 discarded input frames, without a
fresh listening assessment. Nine retained surfaces is an entry count, not bytes
or a leak test. File 1/save state remains preserved.

The preparation, **521 Linux objects/library**, **521 ARM64 objects/library**,
imports, saves, signer and prior reports remain reusable. Native/CPU performance
is the priority; further Thor GPU tests and audio-perfection work are deferred.

## Connection approval

<!-- CodexAstraUlt: This is the owner's explicit instruction, not an inferred
approval policy or a requirement to pause independent cloud development. -->
**“Signal me before connecting” means stop and wait for explicit approval.**
Before any new Thor/ADB connection or device-work batch, including discovery,
report export, installation or testing, signal the owner and wait for that
approval. Notification alone, an available device or an earlier batch does not
authorize access. Cloud coding/building and review of already uploaded reports
may continue. Prepare the compatible package first when possible, using existing
build/installation records without querying the device in advance.

## Suggested task for local Codex after cloud gates pass

<!-- CodexAstraUlt: Make the package reviewable before asking for access; the
remaining device procedure is conditional on the owner's actual answer. -->
```text
Safely update RegiRex/DroiDDS to current main, preserving local work.
Follow the current Dark Moon repackaging section in docs/ANDROID_TITLE_BUILD.md.
Confirm preview.7 cloud route/package/publication gates passed before packaging.
Preserve code 16 and all previous reports. Reuse recorded tools, preparation,
completed ARM64 compilation and the same owner signing profile. Repackage only
with the same package/certificate and a code above the last verified installed
code, at least 17. Use prior build/installation records; do not query the Thor.
Preserve imports, saves and both completed title builds.

Finish package verification, then signal me and STOP for explicit approval before
any Thor/ADB connection or device work, including discovery, export, installation
or testing. Notification alone is not approval. Do not infer approval from an
available device or a previous session.

After approval, confirm exclusive device operation and package compatibility.
Preserve the latest report before installing the compatible update. Keep Native
execution, CPU vertex shaders, Vulkan 1x and comparable menu progression/settings.
Run once: press A around 91 seconds after Play if the title prompt is ready, then
Stop around 110 seconds; never exceed 120 wall seconds. Stop early on failure or
corruption and do not extend for a late prompt. Record actual input timing and
progression. Further GPU testing is deferred.

Export the full JSON immediately after stop/failure and before any restart.
Record worker time, CPU processing, scene progression, rendering paths and actual
audio/visual observations separately. Follow docs/DEVICE_REPORT_HANDOFF.md to
upload reviewed reports, a short summary and relevant bounded failure excerpts.
Verify remote bytes and return commit/file links. Keep raw originals and private
game/build/signing files local. Do not repeat setup, preparation, title compilation,
historical traces or permission configuration, or reset saves.
```
