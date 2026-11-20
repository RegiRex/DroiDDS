# Local DroidDS cleanup — 2026-11-20

<!-- CodexAstraUlt: Record executed cleanup separately from test results and preserve the owner's reusable-artifact exception. -->

Completed the owner's cleanup request. Removed **45,819 file entries**. The scoped file footprint fell from **69.02 GiB to 8.55 GiB**, a reduction of **60.48 GiB**. These are `du`/file-block totals; Btrfs compression/shared extents mean they are not an exact exclusive physical-space saving. Available filesystem space measured **227.24 GiB** after cleanup, versus 197.38 GiB at the protected-file inventory; unrelated filesystem activity can also affect that counter.

| Removed category | File entries | File-block GiB |
| --- | ---: | ---: |
| obsolete-host-build-cache | 5,730 | 3.961 |
| obsolete-investigation-build-cache | 25,263 | 20.849 |
| obsolete-comparison-build-cache | 7,681 | 4.692 |
| duplicate-baseline-game-snapshot | 18 | 18.000 |
| downloaded-tool-installers | 8 | 1.053 |
| completed-run-temporary-data | 7,066 | 11.919 |
| completed-tool-setup-logs | 30 | 0.001 |
| ignored-python-bytecode | 23 | 0.001 |

Removed 18 baseline game snapshots, the rejected preparation copy, obsolete investigation/comparison workers and targets, five frozen diagnostic source copies, eight private APK packaging trees, completed logs/captures/extracted game data, duplicate chat exports/receipts, installers and Python bytecode. Finished run folders now keep concise summaries only. Private raw data was deleted rather than uploaded.

**Preserved and verified:** all **5,197 protected files** matched their pre-cleanup SHA-256 hashes, including the original game, validated preparation run-002, both complete 521-object builds/libraries, signer, installed environment metadata and tracked source. Existing local commit, branches/stashes and owner handoff changes were unchanged at that check. One small working checkout remains; later documentation edits only persist this storage rule. No new checkout or Git pull was made, no packages were uninstalled, and no Thor/ADB access occurred. Saves/imports were not accessed.

Verified **17 existing report files byte-for-byte** against their local originals. Archived **four additional full reports** in [commit 000c44b](https://github.com/RegiRex/DroiDDS/commit/000c44b7872fa11777c885d20bba807ffa4680e9) and verified their remote bytes before removing local copies. See the [archive/readme and exact hashes](archived-local-reports-2026-11-20.md). Reviewed host investigation/preparation/compilation findings also remain in the existing repository documents. No counters were inferred from deleted raw data, and no tests were rerun.

The [single evolving artifact ledger](local-artifact-ledger.csv) retains eight package identities (codes 10–17), cleanup totals, report hashes/links and the explicit retained-build exception. Local storage is now the original input, reusable preparation/builds, signer, needed tools, one working source checkout, small summaries and this ledger. Old raw paths in historical summaries are intentionally retired. The most recent installed package identity remains code 17; its APK file was removed, while its hash/certificate identity is retained for compatibility checks.

For future batches, follow [HOST_SETUP_CLEANUP.md](../HOST_SETUP_CLEANUP.md): create the report, publish reviewed important data, verify remote bytes, update the compact summary/ledger, and promptly clear temporary files. Keep only necessary working data. No cleanup blocker remains.
