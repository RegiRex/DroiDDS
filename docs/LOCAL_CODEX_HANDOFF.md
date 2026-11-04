# Local Dark Moon update handoff

<!-- CodexAstraUlt: Replace the completed setup/compilation/first-boot task with
repackaging and one matched audio test, retaining all successful title artifacts. -->
Current task, **2026-11-03**: repackage the completed private Android library with
the **0.0.8-preview.1** audio/timing development candidate, then run one bounded
Native menu comparison. Use `RegiRex/DroiDDS` and preserve local work.
Read [AGENTS.md](../AGENTS.md), the [title contract](ANDROID_TITLE_CONTRACT.md) and
the [current repackaging procedure](ANDROID_TITLE_BUILD.md#current-dark-moon-repackaging-and-audio-test).
The [local implementation and original APK gates](builds/0.0.8-audio-performance-followup.md)
pass, including repackaging an existing title compilation and verifying the
sanitized bundle. Hosted main CI and the release workflow remain pending;
a candidate version does not qualify a playable game segment.

## Completed and preserved

<!-- CodexAstraUlt: Credit the reported interactive menu result and supplied
JSON while keeping untested gameplay distinct from the observed boot. -->
The owner has completed the preparation, **521/521 Linux objects and library**,
**521/521 Android objects and library**, and a private APK. The subsequent
[Thor test](device-tests/0.0.7-dark-moon-thor-menu.md) reached Dark Moon's title and
file-selection menus in Native mode; A responded and the bounded test stopped
normally with no reported runtime faults. This achieves the central **0.0.7 boot
objective**. The app is stopped; the previous device-access and setup blockers
are superseded. No permission change or tool reinstallation follows from them.

The supplied JSON reports retain **1,361 and 2,889 audio underruns**. They advance
21.255 and 34.140 guest seconds in 100.010 and 201.650 seconds of core work,
with zero reported PCM drops and all converted samples written. This establishes
slow sample production, consistent with the owner's crackling/slow-frame
observation. Read the analysis linked above; do not repeat an unchanged boot
test for counters already supplied. Gameplay, reliable audio, saving/loading
and sustained speed remain unqualified.

The [857ff47 comparison](host-tests/dark-moon-native-2026-11-02.md) and all earlier
reports remain historical evidence. Preserve its raw CPSR differences and
bounded synchronized match. No repeated host trace, source regeneration or
Linux/Android title compilation is part of this update.

## Repackage and test

<!-- CodexAstraUlt: Save the previous single-file report before a new session,
and reuse the existing signer for an update that retains the app's data. -->
Preserve the prior build/device summaries and both exported title JSON reports.
If the app has the only copy of its latest report, export it before starting another session:
`files/latest-title-report.json` is replaced by later sessions.

Use the successful build's existing tool environment, validated preparation,
completed ARM64 directory containing `compiled-manifest.json`, and owner signing
profile. Source its environment in each build shell. Rebuild only the shared
player/frontend APK into a fresh private output with the same package/certificate
and an install code **greater than the installed code and at least 11**. Preserve
the retained title objects/library, imported game and saves. No new signing key
or reinstall is needed for a compatible update.

Only one session operates the Thor. Run the same Native title/file-menu route
for at most **120 wall seconds** or until its first failure, then stop normally.
Record audible gaps/crackling, visible progression, controls, duration, PCM/queue
and timing/pacing counters, native/fallback work and any first blocker separately.
Export the new JSON to fresh evidence. Use an Interpreter comparison only when
a new Native failure needs classification.

## Suggested task for local Codex

<!-- CodexAstraUlt: Keep the prompt limited to the current update and test;
completed setup, title compilation and permission work must not restart. -->
```text
Safely update RegiRex/DroiDDS to current main, preserving local work.
Follow the current Dark Moon repackaging section in docs/ANDROID_TITLE_BUILD.md.
Preserve the existing title JSON before any new session overwrites it.
Reuse the successful tool environment, validated preparation, completed ARM64
compilation and existing owner signing profile. Build a fresh APK only, with
the same package/certificate and a version code above the installed one,
at least 11. Install a compatible update retaining the import and saves.

Run one matched Native title/file-menu audio test for at most 120 wall seconds,
then stop normally and export its report. Use Interpreter only if a new Native
failure needs classification. Return android-title-build-summary.md with the
build/device identities, timing/audio observations, counters and preservation.
Do not repeat setup, preparation, title compilation, host traces or permission
configuration. Keep private game data, APKs and signing files local.
```

The [roadmap](ROADMAP.md) now moves toward 0.0.8's first playable segment. A menu
comparison measures this correction; it does not by itself qualify gameplay,
save/resume, graphics throughout a scene or the sustained 0.1.0 beta requirements.
