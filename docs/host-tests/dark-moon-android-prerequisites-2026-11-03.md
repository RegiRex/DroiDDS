# Dark Moon Android build: prerequisite stop

<!-- CodexAstraUlt: Record the actual local preflight result; missing build
tools are distinct from a game/compiler failure or an Android device result. -->
Reported **2026-11-03** (America/New_York). The local session safely updated to
`2d55dc7` and stopped before Android compilation because it could not find:

- The Rust Android target.
- The required Android SDK/NDK at the checked locations.
- `javac`.
- The locked `sha2` dependency for offline Cargo use.

The owner reports that the validated preparation and all **521 Linux objects plus
their library** are preserved. No Android title compilation or Thor test started.
The cloud session has the summary, not an independent inventory of that laptop.

<!-- CodexAstraUlt: Connect the reported stop to the implemented remedy without
claiming that the owner's laptop or private Android compilation has been tested. -->
The [dedicated tool setup](../ANDROID_TITLE_TOOL_SETUP.md) now supplies all four
missing prerequisites in a directory outside Git. Fresh installation, offline
reuse and an actual offline Android player build pass in the cloud. The updated
[consolidated task](../ANDROID_TITLE_BUILD.md#one-consolidated-local-build-and-device-task)
runs this setup and then continues compilation without another tool-only handoff.
It preserves the successful private preparation and Linux build. The owner's
local setup, Android compilation and Thor result remain unperformed here.
