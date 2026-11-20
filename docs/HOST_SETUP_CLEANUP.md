# Local storage and cleanup

<!-- CodexAstraUlt: Replace deferred cleanup with the owner's explicit 2026-11-20 immediate housekeeping requirement. -->

The owner requires a clean laptop. Keep concise summaries and one evolving CSV ledger locally; upload important reviewed diagnostics to **RegiRex/DroiDDS**, verify remote bytes, and promptly remove temporary data after the reports are complete. This supersedes the former request to wait until version 0.1.0 and older instructions to retain every raw output indefinitely.

The completed [2026-11-20 cleanup](host-tests/local-cleanup-2026-11-20.md) and [artifact ledger](host-tests/local-artifact-ledger.csv) record what was removed and retained. Historical report paths can now point to summary-only directories; deleted raw files are not missing test results and do not justify rerunning tests.

## Retain only necessary files

<!-- CodexAstraUlt: Preserve the owner's explicit reusable-build exception and irreplaceable inputs. -->

The owner explicitly chose to retain the successful Dark Moon preparation run-002, completed original Linux build run-001, and completed ARM64 build run-001. Preserve their validation metadata, 521 objects per build, and linked libraries. Also preserve the original authorized game, saves/imports, signing identity, unpublished local code and the single working checkout. Keep installed pinned tools and offline dependencies still required for packaging. A generated build cache is not the retained title library.

Keep summary Markdown and one small local droidds-storage-ledger.csv. Append useful identities, outcomes and verified GitHub links to that ledger rather than creating another raw backup directory for each step. Private game images, generated C, objects/libraries, private APKs, saves, memory/code dumps, recordings and signing secrets must never be uploaded to GitHub.

## Complete each batch with cleanup

<!-- CodexAstraUlt: Couple remote verification with immediate removal of obsolete local working data. -->

1. Export the run report before any restart and retain it temporarily outside Git.
2. Review the full diagnostic JSON, summary and only the bounded failure excerpts needed for analysis. Follow [DEVICE_REPORT_HANDOFF.md](DEVICE_REPORT_HANDOFF.md); retain counters and zero/null fields and record redactions.
3. Upload reviewed important data and read it back at the published commit. Compare exact bytes or hashes before deleting the sole local copy. If upload is blocked, retain only the minimal irreplaceable pending evidence and report the blocker.
4. Preserve necessary artifact identities in the summary/ledger. Clear completed test/build logs, screenshots/UI captures, extracted memory/code, staged game copies, obsolete APK/intermediate copies, old diagnostic targets and frozen source snapshots no longer needed. Remove downloaded installers after the installed tools are verified. Clear this task's own temporary cleanup scripts and audit files too.
5. Check the retained files, local changes and remaining disk use. Report what was removed, exceptions, verified links and any blocker.

Do not remove active work, a reusable artifact explicitly retained by the owner, or shared software whose ownership is uncertain. Inspect before deleting an unused checkout and preserve unique changes. Do not run blanket DNF undo/autoremove or remove shared Cargo/Rustup directories. This housekeeping instruction does not authorize a new Thor/ADB batch; the separate signal, STOP and explicit approval boundary still applies.
