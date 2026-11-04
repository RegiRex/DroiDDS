# Transfer local device evidence to cloud development

<!-- CodexAstraUlt: The owner requests delivery of needed reports after local
tests; distinguish reviewed diagnostic evidence from private game/build data. -->
Report delivery is part of the local test task. Use the existing GitHub access
to publish reviewed diagnostic copies in **`RegiRex/DroiDDS`**. This lets the cloud
session read them without asking the owner to find and attach files. The owner's
instruction authorizes this diagnostic transfer; no separate confirmation is
needed for the reviewed files described here.

## Capture once, preserve each run

<!-- CodexAstraUlt: Preserve the app's replaceable latest report immediately;
missing uploads must not trigger another unchanged device run. -->
After each run stops, export its full JSON **before any restart** and save it
under a distinct local filename recording build, route and run. Preserve the
original outside Git. Keep CPU/GPU comparisons and later manual restarts as
separate reports; filenames alone do not establish their package or session.
For an already completed test, use the existing files. Do not rerun the test
merely because a report was not uploaded.

For the current comparison, deliver both CPU and GPU JSON reports, one short
`android-title-build-summary.md`, and a bounded failure log only if needed to
explain an error. Include a failed or incomplete report as such; do not replace
it with a later successful run. Routine UI XML, screenshots, video and broad
system logs are not needed for timing analysis.

## Prepare reviewed diagnostic copies

<!-- CodexAstraUlt: Preserve useful machine-readable measurements while keeping
personal information and private title content out of the public repository. -->
Review file contents before copying them into Git. Preserve the full diagnostic
structure, including `app`, `runtime`, `timing`, `audio`, requested/selected/actual
rendering paths, counters, errors and input/manifest/library/APK hashes. Retain
public package/version/source identities, device model/driver and public signing
certificate fingerprint. These allow comparison; an abbreviated audio-only
summary cannot replace the full session JSON. Preserve zero/null values and
starting, pending, failed or stopped states; missing data is not a measured zero.
Review new or unfamiliar fields too, rather than blindly copying a directory.

Remove personal filesystem paths, usernames, device serials, credentials,
tokens, unrelated notifications and other private information from the copies.
Keep JSON valid and record every redacted field in the summary. Do not alter
numeric measurements or silently drop failed checks. Keep original and reviewed
SHA-256 identities in the summary so byte-identical copies and redacted copies
can be distinguished. If no redaction is needed, copy the file unchanged.

Never include game images, generated game C, objects/libraries, private APKs,
saves, memory/code dumps, private screenshots/video or signing keys/passwords.
For a failure log, retain only the bounded relevant diagnostic section after
review as a `.txt` excerpt; `.log` files are intentionally ignored by Git. Do not
broaden ignore rules or force-add private directories. Keep the complete raw log
locally. If essential evidence cannot be made suitable for the repository,
describe what remains local instead of publishing it.

## Upload and verify

<!-- CodexAstraUlt: A verified remote commit closes the handoff; local extraction
or a claimed upload without readable remote files cannot substitute for it. -->
Use a new directory such as
`docs/device-tests/reports/<date>-<build>-<batch>/`, with separately named
`cpu-session.json`, `gpu-session.json` and `android-title-build-summary.md`.
Use the actual test date/build/batch; do not overwrite a prior directory. Keep
the summary short: artifact identities, test conditions, separate run outcomes,
observed audio/images, failures, redactions and remaining limitations.

1. Check repository status and remote identity. Preserve unrelated local work
   and concurrent changes; use a separate checkout if needed.
2. Stage only the explicitly reviewed diagnostic files. Inspect the staged
   diff and file list before committing. Do not stage a whole private output
   directory or use a broad `git add .`.
3. Commit and push the report change to `RegiRex/DroiDDS` using the existing
   access. Use `main` when it can be advanced safely. If concurrent changes
   prevent that, preserve the report commit on a distinct report branch and
   return its links. Do not force-push, reset, discard work or rewrite another
   session's commits to deliver reports.
4. Read the files back at the pushed commit using Git or the GitHub connector
   and verify their bytes/hashes. A successful local commit is not an upload.
5. Return the commit URL and direct file URLs pinned to that commit, along with
   the concise findings. Include local original paths only in the local reply,
   not the public summary.

If GitHub access or an actual session policy prevents uploading, state the exact
failure and leave the reviewed files ready. Return their exact local paths for
the owner to attach to the cloud chat. Do not claim an upload, request another
test, or install new tools solely to move these small reports. This procedure
uses the existing exports; it adds no application logging, monitor or log bundle.
