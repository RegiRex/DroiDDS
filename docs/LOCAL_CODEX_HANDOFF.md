# Local Dark Moon Native/CPU performance handoff

<!-- CodexAstraUlt: Replace the completed code 14 test with one changed update;
cloud validation and publication remain prerequisites for the next private run. -->
Current candidate: **0.0.8-preview.5/code 15**, under development.
Cloud correctness, package and publication gates are pending. Read
[the build record](builds/0.0.8-cpu-decode-followup.md), [AGENTS.md](../AGENTS.md)
and [the current procedure](ANDROID_TITLE_BUILD.md#current-dark-moon-repackaging-and-audio-test).
Do not repeat the unchanged code 14 test.

## Completed evidence

<!-- CodexAstraUlt: Keep the bounded menu separate from the longer owner intro,
including visual observations and their distinct workload/timing measurements. -->
The [code 14 evidence](device-tests/0.0.8-preview4-dark-moon-thor.md) records
file selection at 17.31% speed and a separate intro at 16.66%. The owner reports
no intro glitches; neither report records runtime/rendering errors. Menu audio
remains choppy. Native/CPU performance is the priority; further Thor GPU tests
and audio-perfection work are deferred. No sustained playable segment is qualified.

The preparation, **521 Linux objects/library**, **521 ARM64 objects/library**,
imports, saves, signer and previous reports remain reusable. Preview.5 changes
only the generic runtime/renderer and packaging identity. Its input-decoder and
health-check optimizations need new hardware measurement; host component results
alone cannot establish a Thor gain.

## Suggested task for local Codex

<!-- CodexAstraUlt: Confine the handoff to compatible repackaging, one bounded
menu test and delivery of reviewed evidence after all cloud gates pass. -->
```text
Safely update RegiRex/DroiDDS to current main, preserving local work.
Follow the current Dark Moon repackaging section in docs/ANDROID_TITLE_BUILD.md.
Confirm preview.5 cloud route/package/publication gates passed before packaging.
Preserve code 14 menu/intro and all previous reports. Reuse working tools,
preparation, completed ARM64 compilation and the same owner signing profile.
Repackage only with the same package/certificate and an install code above the
installed one, at least 15. Install a compatible update preserving imports/saves.

Keep Native execution, CPU vertex shaders, Vulkan 1x and comparable menu
progression/settings. Run once: press A around 91 seconds after Play if the title
prompt is ready, then Stop around 110 seconds; never exceed 120 wall seconds.
Stop early on failure/corruption and do not extend for a late prompt. Record
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
