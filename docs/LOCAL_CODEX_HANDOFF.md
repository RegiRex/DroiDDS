# Local Dark Moon Native/CPU performance handoff

<!-- CodexAstraUlt: Replace the completed code 15 batch with pending cloud work
and the owner's explicit stop before any new Thor connection or device action. -->
Next candidate: **0.0.8-preview.6/code 16**, under cloud development. A
shader-output projection prototype and detailed fixed SVC/service/GSP attribution
are being evaluated. Benchmarks, correctness, package and publication gates
remain pending. Do not repeat the unchanged code 15 test or start a new Thor
batch now. Read [AGENTS.md](../AGENTS.md) and
[the current procedure](ANDROID_TITLE_BUILD.md#current-dark-moon-repackaging-and-audio-test).

Published [preview.5/code 15](https://github.com/RegiRex/DroiDDS/releases/tag/v0.0.8-preview.5)
passed local/runtime/package and hosted main checks at `f687911`, with publication
and independent public-download verification at `365c1a0`. Its
[build record](builds/0.0.8-cpu-decode-followup.md) retains those identities.

## Completed evidence

<!-- CodexAstraUlt: Keep the measured system-call scope precise and preserve
scene state instead of requesting another unchanged or artificially reset run. -->
The [code 15 report](device-tests/0.0.8-preview5-dark-moon-thor.md) reached file
selection at **16.70% speed**, with no reported runtime/rendering errors. No gain
is established. It attributes **33.975 seconds to SVC handling outside the PICA
command-list timer**; transfers and GPU synchronization can still occur there.
The remaining 6.779 seconds is unclassified. The populated File 1 panel differs
from the earlier empty menu, and no new audio observation was supplied.

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
Confirm preview.6 cloud route/package/publication gates passed before packaging.
Preserve code 15 and all previous reports. Reuse working tools, preparation,
completed ARM64 compilation and the same owner signing profile. Repackage only
with the same package/certificate and a code above the last verified installed
code, at least 16. Use prior build/installation records; do not query the Thor.
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
