# Local Dark Moon Native/CPU performance handoff

<!-- CodexAstraUlt: Replace the completed code 13 comparison with the owner's
Native/CPU priority and the newly verified retained-library update. -->
Current task, **2026-11-04** (America/New_York): repackage the retained private
ARM64 library with published **0.0.8-preview.4/code 14**, using Native execution with CPU vertex
shaders. Local correctness/runtime, retained-library APK and independent bundle
checks pass at `a77a85e`; hosted main checks pass there. Tag build/publication and
independent public-download verification pass at documentation-only release
source `62eb45e`. New Thor checks remain unperformed; no speed gain is established.
Further Thor GPU tests and audio-perfection work are deferred. Read
[the candidate build record](builds/0.0.8-cpu-work-followup.md),
[AGENTS.md](../AGENTS.md), the
[code 13 device evidence](device-tests/0.0.8-preview3-dark-moon-thor.md) and the
[current procedure](ANDROID_TITLE_BUILD.md#current-dark-moon-repackaging-and-audio-test).

## Completed evidence

<!-- CodexAstraUlt: Separate the measured Native routes, the earlier restart
and unsupplied Interpreter reports; preserve data instead of repeating tests. -->
The owner has completed the preparation, **521 Linux objects/library** and
**521 Android objects/library**. Code 13 was packaged with the same retained
library and signer, preserving imports, saves and earlier reports.

Native/CPU vertices reached file selection and stopped normally at **18.12%
emulated speed**, with **1,471 underruns**, 235 flushed frames and audible short
bursts/gaps. No clear speed gain is established. CPU vertex work consumed
**34.80% of core time** and other command processing another **28.45%**.
Native/GPU failed before useful output; the report identifies an attempted
public interpreted-vertex/generic-fragment pipeline, not the faulty stage.
The uploaded code 13 reports are remotely verified in commit `67038f9`.

The code 11 110-second test and later 43.117-second restart remain separate
historical evidence. No unchanged CPU/GPU run is needed to recover existing
reports. Preserve the owner's remaining saves and all prior output.

## Current update

<!-- CodexAstraUlt: Require new cloud correctness/package gates while retaining
the already compiled title, compatible signer and short observable test bounds. -->
Preview.4 reduces repeated vertex-output work and full-TEXT verification after
unrelated GPU guards while retaining mapping/backing/code protection checks.
Its fixed decode/placement timers and geometry-mode/parallel-vertex batch counts
help separate remaining CPU costs. Host component timings do not establish
handheld improvement.

Preview.4's required cloud/publication checks pass. Reuse successful tools,
preparation, ARM64 directory with
`compiled-manifest.json`, and existing owner signing profile.
Package a compatible update with the same package/certificate and a version
code above the installed one, **at least 14**. No title C or either set of 521
objects needs recompilation; no separate public original APK installation is
required.

Keep **Native guest execution, CPU vertex shaders, Vulkan 1×** and comparable
menu progression/settings. Match code 13 with A around **91 seconds after Play**
if the title prompt is ready, and normal Stop around **110 seconds**. Keep the
absolute **120-wall-second** bound and stop early on failure or visual corruption.
Do not extend for a late prompt; record actual input/progression and worker time
separately. Further GPU tests are deferred.

Export each full JSON immediately after stop/failure and **before any restart**.
Keep actual audio/visual observations separate from counters.
Follow [report transfer](DEVICE_REPORT_HANDOFF.md): upload reviewed reports,
summary and needed bounded driver-log excerpts, verify remote bytes and return
commit/file links. Raw originals and private game/build/signing data stay local.

## Suggested task for local Codex

<!-- CodexAstraUlt: Keep the prompt confined to this compatible update and
bounded evidence collection; transfer is part of finishing the actual test. -->
```text
Safely update RegiRex/DroiDDS to current main, preserving local work.
Follow the current Dark Moon repackaging section in docs/ANDROID_TITLE_BUILD.md.
Confirm preview.4 cloud route/package/publication gates passed before packaging.
Preserve existing code 11/code 12/code 13 reports and earlier evidence. Reuse working
tools, preparation, completed ARM64 compilation and the same owner signing
profile. Repackage only with the same package/certificate and an install code
above the installed one, at least 14. Preserve imports and saves.

Keep Native execution, CPU vertex shaders, Vulkan 1x and comparable menu
progression/settings. Run once: press A around 91 seconds after Play if the title
prompt is ready, then Stop around 110 seconds; never exceed 120 wall seconds.
Stop early on failure/corruption and do not extend for a late prompt. Record the
actual input timing and progression. Further GPU testing is deferred.
Export the complete JSON after stop/failure and before any restart. Record
actual worker time, CPU processing, input/scene progression, rendering paths
and actual audio/visual observations separately.

Follow docs/DEVICE_REPORT_HANDOFF.md to upload reviewed full reports, a short
android-title-build-summary.md and any needed bounded driver-log excerpt.
Verify remote files and return commit/file links. Preserve raw originals and
both title builds. Do not repeat setup, preparation, title compilation,
historical traces or permission configuration, reset saves, or publish private
shader/game/build/signing files.
```

This batch does not establish a playable segment, reliable saving/loading,
sustained performance or the 0.1.0 limited-beta requirements.
