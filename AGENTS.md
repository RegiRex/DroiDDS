# DroiDDS working instructions

<!-- CodexAstraUlt: Use the owner's renamed GitHub repository for current links
and publication; preserve existing artifact identities in historical evidence. -->
- The repository is `RegiRex/DroiDDS`. Use that spelling in current GitHub links.

<!-- CodexAstraUlt: Preserve the owner's explicit connection boundary separately
from authorization to continue cloud development and verified publication. -->
- Before any new Thor/ADB connection or device-work batch, signal the owner and
  STOP until explicit approval. This includes device discovery, report export,
  installation and testing. “Signal me before connecting” means wait for the
  owner's answer; notification alone, an available cable/device or an earlier
  batch does not authorize the next one. Cloud coding, builds, source review and
  uploaded-report analysis may continue. Prepare and verify the compatible
  package before requesting connection approval when possible; use existing
  build/installation records rather than querying the Thor in advance.

<!-- CodexAstraUlt: The owner has completed the private Android build and first
interactive menus; advance to audio/playability work without repeating setup. -->
- Read docs/device-tests/0.0.7-dark-moon-thor-menu.md. The owner reports all
  521 Android objects and the APK completed, followed by Native title/file
  menus on Thor, a responding A button and normal stop with no reported runtime
  faults. This achieves the central 0.0.7 owned-game boot objective. Preserve
  the 1,361/2,889 underruns and reported crackling/slow frame progression; no
  playable segment, reliable audio or sustained speed is yet qualified. Both
  uploaded JSON reports bind the same input/manifest/native library and show
  zero PCM drops with all converted samples written. Core work advances only
  21.255/34.140 guest seconds in 100.010/201.650 seconds. Slow production is
  established; Java queue loss is not evidenced in these runs. Do not request
  another unchanged boot merely to obtain already supplied counters.
<!-- CodexAstraUlt: Keep the overwritten bounded run separate from the surviving
restart summary, and progress from completed code 11 testing into route analysis. -->
- Read docs/device-tests/0.0.8-preview1-dark-moon-thor.md. The owner reports code 11
  packaging passed with the existing library and signer preserved, then a
  110-second Native test reached file selection and stopped normally with severe
  slowdown/crackling. A later manual restart replaced that run's JSON. Only the
  separate restart JSON is now supplied: 43.117 seconds of worker execution,
  40.408 seconds of core work, 23.290 seconds of command processing (57.64% of
  core), 0.411 seconds scanout, 568 audio underruns and zero reported PCM loss.
  Its matching cycle/worker duration gives 23.35% emulated speed. Do not join
  these results to the 110-second run or claim improvement against unlike tests.
  Reviewed JSON copies are linked from the evidence record. The starting-only
  pre-update JSON is not a completed test; launcher XML is not game evidence.
  No unchanged run is needed. The owner's reported intentional save deletion is
  historical, not permission to repeat it.
<!-- CodexAstraUlt: The owner requests direct diagnostic delivery so local
exports become retrievable evidence instead of another attachment-only handoff. -->
- Follow docs/DEVICE_REPORT_HANDOFF.md after local testing. Preserve raw originals
  outside Git; upload reviewed diagnostic JSON, a short summary and needed failure
  excerpts to docs/device-tests/reports/<date>-<build>-<batch>/ in RegiRex/DroiDDS.
  Keep complete runtime/timing/audio fields and run identities; exclude private
  game/build/signing data, personal paths, serials and unrelated device captures.
  Use targeted staging and existing GitHub access, verify remote bytes, and return
  commit/file links. A local download or rename is not an upload. If transfer is
  actually blocked, identify the reason and exact reviewed attachment paths;
  preserve results without repeating tests or claiming the cloud received them.
<!-- CodexAstraUlt: The code 12 device comparison is complete; use its first
pipeline failure and measured CPU subset instead of requesting a longer run. -->
- Read docs/device-tests/0.0.8-preview2-dark-moon-thor.md and the reviewed reports
  uploaded in 22f14e0. Native/CPU vertices reached file selection at 17.72%
  emulated speed, with 1,426 underruns and zero reported PCM loss. CPU vertex
  work consumed 33.446 seconds: 33.42% of core / 54.42% of command processing.
  Native/GPU failed during pipeline creation before any GPU-vertex draw or
  Vulkan submission. It supplies no usable performance comparison. Later
  Interpreter observations have no supplied JSON and remain separate. Do not
  infer a regression from unlike code 11/12 runs, or treat guest allocation as
  process/driver memory. Do not repeat the failed code 12 GPU launch.
<!-- CodexAstraUlt: Replace the completed code 13 test request with the owner's
Native/CPU priority and require fresh cloud gates before the next private run. -->
- Read docs/device-tests/0.0.8-preview3-dark-moon-thor.md and the reports uploaded
  in 67038f9. Published 0.0.8-preview.3/code 13 reached file selection with
  Native/CPU vertices at 18.12% speed; no clear gain is established. CPU vertex
  work used 34.80% of core time and other command work another 28.45%. Retain
  1,471 underruns, 235 flushed frames and the owner's short-burst/gap observation.
  GPU failed before useful output; metadata identifies the attempted public
  interpreted-vertex/generic-fragment pipeline, not the faulty shader stage.
  Further Thor GPU tests and audio-perfection work are deferred.
<!-- CodexAstraUlt: Replace the completed code 14 handoff with its separate menu
and intro evidence, then finish cloud changes before requesting another run. -->
- Read docs/device-tests/0.0.8-preview4-dark-moon-thor.md and the full reports
  uploaded in ed8ebef and a09289a. Code 14's bounded Native/CPU menu run reaches
  file selection at 17.31% emulated speed with choppy audio. The separate owner
  intro run advances at 16.66%; the owner reports no graphical glitches and the
  report records no runtime/rendering errors. Its input timing was not observed
  independently. Do not treat the intro as a controlled menu comparison, infer
  a speed gain, or qualify gameplay from the observed intro. Audio underruns
  remain 1,382 and 2,793 respectively; no new intro audio observation was supplied.
- Previous CPU candidate 0.0.8-preview.4/code 14 passed local correctness/runtime,
  retained-library APK and independent bundle checks at implementation
  a77a85e895461f6f62b9fa868c5bab5a82a64b44. Hosted main checks passed there;
  tag build/publication and independent public-download verification passed at
  documentation-only release source 62eb45e0c9958d588a06b279f19fcbbd6f9196d6.
  Its two Thor reports are now available; no handheld speed gain is established.
  Preserve docs/builds/0.0.8-cpu-work-followup.md and those artifact identities.
<!-- CodexAstraUlt: Advance from the completed code 15 run using precise timer
scope, while preserving the published artifact history and new access boundary. -->
- Published 0.0.8-preview.5/code 15 passed local correctness/runtime,
  retained-library APK and independent bundle checks at implementation
  f6879110dace4d47edd3796ab4b85acc69effcb0. Hosted main checks passed there;
  tag build/publication and independent public-download verification passed at
  release source 365c1a0ffa3fce8d7001f625a0c42e399ea5b1aa. Preserve
  docs/builds/0.0.8-cpu-decode-followup.md and those source/artifact identities.
- Read docs/device-tests/0.0.8-preview5-dark-moon-thor.md and report commit
  7670dc3. The code 15 Native/CPU menu run reached file selection and stopped
  normally at 16.70% speed, with no reported runtime/rendering errors and 1,362
  audio underruns. No new listening observation or performance gain is
  established. A populated File 1 panel differs from the earlier empty menu;
  preserve that save state rather than trying to manufacture an identical run.
  SVC handling accounts for 33.975 seconds outside the PICA command-list timer,
  not necessarily outside rendering/GPU work. Transfers, fills, DMA and GPU
  synchronization can occur in that scope. The remaining unclassified core time
  is 6.779 seconds; do not label it native execution time alone.

<!-- CodexAstraUlt: Publish only after source-bound cloud and download gates;
keep host component measurements separate from the unperformed Thor check. -->

- Published 0.0.8-preview.6/code 16 passed local correctness/runtime,
  retained-library APK and independent bundle checks at implementation
  64f1404ed0a357cf9325568a2376137079b120ad. Hosted main checks passed there;
  tag build/publication and independent public-download verification passed at
  release source 2354ed0f516926ff11fd613d95333141040cc3af. Read
  docs/builds/0.0.8-service-projection-followup.md for exact gates and identities.
  The ordinary CPU vertex route projects completed shader outputs directly into
  compact raster vertices; fixed SVC/service/GSP tables identify nested work.
  Authored x86-64 component benchmarks improve, but no new Thor result or
  handheld speed gain is established. Do not repeat the unchanged code 15 run.
  Reuse working tools, preparation, both completed 521-object builds/libraries
  and the owner signer. Prepare a compatible update with a code above the last
  verified installation and at least 16, using existing records before
  connection approval. Then signal the owner and STOP until explicit approval
  before any Thor/ADB connection, discovery, export, install or test. Preserve
  imports, saves and previous reports.
  The eventual approved test keeps Native execution, CPU vertex shaders and
  Vulkan 1×, with A around 91 seconds if ready and normal Stop around 110 seconds,
  bounded by 120 wall seconds. Export the full JSON before restart and upload
  reviewed evidence with verified links. Further Thor GPU tests and
  audio-perfection work remain deferred. Do not add shader dumps, growing logs
  or optional JIT; no separate public diagnostic APK installation is required.

<!-- CodexAstraUlt: Continue the owner's requested cloud product development
before another isolated local trace; candidate publication does not close boot. -->
- The 0.0.7-preview.2 generic per-title Android player candidate is published;
  host/main/tag CI and independent public-download verification pass. Read
  docs/builds/0.0.7-android-title-candidate.md for exact source/artifact scope.
  Read docs/ANDROID_TITLE_CONTRACT.md and docs/ANDROID_TITLE_BUILD.md. Keep the
  original-fixture candidate distinct from qualified owned-game boot and the
  roadmap's 0.1.0 limited beta. Complete cloud implementation/testing first and
  consolidate private compilation/device validation into one local batch.
  Preserve the completed Linux and Android objects/libraries and prepared C.
  Their separate target artifacts remain reusable by updated APK packaging.
  The six historical host compilation-contract helpers remain byte-identical
  to 857ff47; use the separate Android adapter. New title signing identity is
  explicit and separate from the probe. Preserve keys outside source/release
  bundles. Public title releases admit only the exact authored homebrew guest.
  The candidate now has an owner-supplied Thor original-title result; read
  docs/device-tests/0.0.7-preview2-thor-title.md. Its artifact identities and
  counters agree, with native/Vulkan execution and no reported runtime errors.
  The owner confirms both images, D-pad/A, touch, pause/resume and steady sound;
  the three measured underruns are retained. That original-fixture report does
  not itself qualify an owned title; the later private menu result is above.
  Its public report
  binds release source 97e60e0; later main test-only hardening 795b8cc accepts
  Linux ESRCH when an already-dead child disappears during a proc read. That
  main change passes 549 Python tests and both hosted workflows, with no APK
  runtime or process-limit change.
<!-- CodexAstraUlt: Use bounded actionable failure evidence in the upcoming
private APK; no new tracing or generated-title compilation contract is needed. -->
- Read docs/builds/0.0.7-device-followup.md for the current cloud follow-up.
  Admitted session slice failures now retain first_blocker and bounded
  memory_faults metadata. Keep guard errors/priority and raw evidence intact;
  samples are sorted-key observations, not claimed chronological traces.
  Main CI also exercises the generic title runtime/player and Vulkan oracle.
<!-- CodexAstraUlt: Continue independent runtime fixes while private title
compilation runs elsewhere; retain prepared/generated artifact compatibility. -->
- Read docs/builds/0.0.7-input-save-corrections.md for the input/save follow-up.
  Generic HID publication and queued transitions follow guest frames, not host
  yields. Keep joystick samples atomic and explicit pause release immediate.
  Save-file errors/permissions, requested synchronization and linked handles
  have original guest coverage; do not infer private save compatibility or
  transactional/crash-atomic archive behavior. Legacy emulator snapshots reopen
  host handles read-only because the old record lacks access metadata; ordinary
  save files are unchanged. Preserve all compilation/coordinator helper identities
  so ongoing private title compilation can finish with its existing checkout.
<!-- CodexAstraUlt: Resolve missing Android build prerequisites in one isolated
setup and continue the authorized build, without global installation changes. -->
- Read docs/ANDROID_TITLE_TOOL_SETUP.md if Android tools or offline dependencies
  are missing. The tested setup owns one directory outside Git and never edits
  system packages, shell profiles or existing Rust installations. Source env.sh
  and continue the consolidated task; do not return another tool-only handoff.
  The previous preview.3 development candidate introduced authored homebrew-v2 to fix
  startup pitch updates clearing pending DSP flags. Historical v1 reports and
  published preview.2 remain unchanged; private generated title C is unaffected.
<!-- CodexAstraUlt: Retain the owner's deferred cleanup preference separately
from the current test prompt; no removals are part of this Android build. -->
- At version 0.1.0, provide selective local cleanup guidance using
  docs/HOST_SETUP_CLEANUP.md and actual tool ownership records. The new isolated
  installation records its components in setup-state.json and receipts/. Do not
  remove preexisting/shared software or add this deferred task to test prompts.

<!-- CodexAstraUlt: The owner now authorizes development and reuse from multiple
open-source projects; continue from measured foundation results, not the old
planning-only state. -->
- Development is authorized. The first Linux CPU foundation build 0.0.1 passes;
  read docs/BUILDING.md and docs/builds/0.0.1-foundation.md. Keep Android, graphics
  and real-title claims separate. The owner has continued into Android; manual
  owner testing of the Linux build is not a prerequisite. Read
  docs/ANDROID_PROBE.md for the bounded CPU loader probe and actual device gate.
- The owner authorizes downloadable DroidDS diagnostic prereleases. Use the
  reviewed tag workflow and four-file release bundle; never publish private
  signing keys or retail-derived data. A prerelease is not device/game evidence.
<!-- CodexAstraUlt: Persist the owner's explicit automatic continuation request
so receiving a device report does not create an unnecessary approval round. -->
- Through 0.1.0, each owner-supplied report authorizes validation, necessary fixes,
  development of the next roadmap build, and its verified DroidDS prerelease.
  Continue in the same turn when possible. A failing gate requires diagnosis and
  a corrective build before promotion, not silently skipping the gate. Ask only
  for missing input or a consequential decision that actually blocks progress.
  End each build with its download and prepared next-device procedure; signal
  and wait for explicit approval before new Thor/ADB access as required above.
  Do not claim autonomous background work after the turn or proceed past
  unperformed hardware gates.
<!-- CodexAstraUlt: Preserve the measured CPU milestone and the next platform
test without treating a host Vulkan draw as a qualified PICA renderer. -->
- The owner's 0.0.2 Thor report passes the four CPU fixtures and two corruption
  controls on Android ARM64 with 4 KiB pages; read docs/device-tests/0.0.2-thor-cpu.md.
  The owner's 0.0.3 Thor CPU/Vulkan report also passes: four CPU fixtures, two CPU
  controls, nine exact GPU readbacks and nine pixel-mutation controls on Adreno
  740/Android 13. Read docs/device-tests/0.0.3-thor-cpu-vulkan.md. The GPU reports
  Vulkan 1.3.128; that result alone did not qualify full renderer features/formats,
  picker lifecycle, PICA/game, sustained memory or performance. The manual upload
  does not independently bind an installed APK or establish its export method.
<!-- CodexAstraUlt: Advance from validated 0.0.5 Android runtime evidence while
retaining separate interactive-device, lifecycle and retail-title gates. -->
- The owner's 0.0.4 Thor report passes all eight CPU cases, three code-safety
  controls and the original Vulkan capability/graphics/compute checks. Read
  docs/device-tests/0.0.4-thor-runtime-probe.md. Dynamic blend/logic state is absent
  on this driver; qualify the real renderer's static pipeline path explicitly.
- Version 0.0.5 now integrates selected vendored loader/HLE/PICA sources and an
  original NCCH guest through three CPU/rendering routes. Its host/release gates
  and downloaded public APK verification pass; read
  docs/builds/0.0.5-runtime-integration.md. The owner's strict 0.0.5 Thor report
  passes; read docs/device-tests/0.0.5-thor-runtime.md. It executes CPU vertex
  shading with Vulkan rasterization, static blend/logic state, zero software
  raster fallback, five memory layouts and the bounded runtime code guards.
  Preserve all 0.0.4 checks. Distinguish Vulkan rasterization from GPU vertex
  execution, and never qualify hardware rendering after an unnoticed software
  fallback. No 3DSX loader or retail-title result is established.
<!-- CodexAstraUlt: Keep automatic homebrew checks separate from the visible
Android qualification that must precede promotion to private-game boot work. -->
- Version 0.0.6 is published with passing local/main/tag CI gates and
  independently verified public assets; read
  docs/builds/0.0.6-interactive-homebrew.md. The combined Thor evidence below
  now supports 0.0.7 development; a private-game milestone needs its own gate.
  It adds an original NCCH guest using HID/GSP/PICA/DSP HLE and three-route image/PCM oracles,
  plus a manual two-view Android frontend. Retain every 0.0.5 regression and the
  exact twelve-library package inventory. Presentation uses CPU readback and
  Bitmap/Canvas on one Android display; do not claim direct Vulkan presentation
  or Thor physical dual-display support. Guest PCM is resampled from
  32728.498046875 Hz to Android 48000 Hz; this does not qualify DSP firmware.
  Automatic report success does not establish visible screens, controls/touch,
  audible audio or lifecycle recovery. Complete the manual 0.0.6 device gate
  before 0.0.7 promotion. Preserve session/run binding and all prior report
  sections; failed or unfinished manual work must remain distinguishable.
<!-- CodexAstraUlt: Preserve the first .6 device result and the correction's
identity instead of mistaking install code 7 for completion of milestone .7. -->
- The first 0.0.6 Thor report passes every automatic gate; read
  docs/device-tests/0.0.6-thor-homebrew.md. The owner confirms both guest views
  were visible on the top physical display. Touch consumption was not measured,
  Activity recreation was untested, and 197 audio underruns need correction.
  The corrective v0.0.6-probe.2 keeps version name 0.0.6 with install code 7.
  Local/main/tag CI and independent public-download verification pass; read
  docs/builds/0.0.6-frontend-correction.md for the exact correction artifact.
  Require the focused corrected-device gate before 0.0.7 promotion; preserve
  the original report and supplemental human observation separately.
<!-- CodexAstraUlt: Preserve corrected touch/recreation evidence without
rewriting its missing A observation or qualifying private games from a fixture. -->
- The corrected 0.0.6/code7 report passes strict automatic validation; read
  docs/device-tests/0.0.6-correction2-thor.md. Touch consumption is 42/42,
  six view replacements succeed, and both views/sound are confirmed. The new
  standalone manual qualifier is pending for omitted A; carry historical A
  evidence only as an explicit unchanged-path assessment. Audio has 11
  underruns; on 2026-10-20 the owner confirmed the tone “Sounded steady” between
  intentional pauses. This closes the audible-quality observation for this run.
  The combined .6 evidence supports .7 development without rewriting the JSON
  or claiming zero underruns or a fresh A observation. Do not require another
  full run solely for omitted A, or call this report a private-title pass.
- Generic bounded local title reconnaissance is independent preparatory work;
  read docs/PRIVATE_TITLE_RECONNAISSANCE.md. Keep its inputs, fresh snapshots,
  saves and reports outside Git. A host interpreter/software outcome is neither
  native qualification nor an Android 0.0.7 boot milestone. Stop at the first
  unsupported runtime behavior; never qualify progress by silently skipping it.
<!-- CodexAstraUlt: Preserve the completed private build and the restricted
native admission path instead of reopening compilation or using legacy loading. -->
- Dark Moon's owner-reported host compilation now completes 521/521 objects and
  a linked/static-validated library. Read docs/PRIVATE_TITLE_NATIVE_RUN.md and
  docs/builds/0.0.7-native-host-comparison.md for the retained host evidence.
  Reuse its preparation/library; do not regenerate or recompile title code.
  The new host-only path admits manifests and full ELF pointer tables, seals
  library bytes and binds actual runtime components before loading. Its Linux
  4 KiB fence permits immutable base native execution while CROs stay interpreted.
  It fails closed on code writes/remaps; general mutable-code deoptimization and
  Android qualification remain open. A signal alone does not establish cause.
  Compare exact guest-cycle checkpoints, subtract callback-interpreted work from
  compiled-dispatch totals, and never qualify a native run with zero native work.
<!-- CodexAstraUlt: Retain the owner's actual native mismatch and the corrected
scheduler/materialized observation path without turning raw differences into a pass. -->
- The first private comparison on `b61a986` reports 1,999,970 native instructions
  and differences in CPSR/reschedule_pending at 100,000 cycles. Read
  docs/host-tests/dark-moon-native-2026-10-29.md and
  docs/builds/0.0.7-native-boundaries.md. New shared scheduling fixes deadline/phase
  differences. Generation-3 budget exits can omit dead locals; retain raw results
  and compare supplemental post-SVC samples by complete event identity with
  positive native work before each qualifying sample. Do not mask flags, extend
  budgets for missing samples, or claim general native parity from convergence.
<!-- CodexAstraUlt: The requested private follow-up has arrived; do not send
the owner back through an unchanged comparison before the Android build. -->
- The owner's `857ff47` comparison is complete; read
  docs/host-tests/dark-moon-native-2026-11-02.md. Raw CPSR still differs at
  100,000/2,000,000 cycles; the first PC agrees and both scheduler-pending fields
  are false. One synchronized sample matches at 303,222 cycles; the other three
  boundaries are missing on both routes. Preserve raw differences and the
  bounded match. No title regeneration, Linux recompilation, limit increase or
  repeated unchanged host trace is justified. The later ARM64 build and menu
  boot are complete; continue the repackaging/audio task above with both target
  libraries and previous outputs preserved.
- Read docs/NEW3DS_AUDIT.md for the implemented parser, resolved-layout,
  commitment/configuration, heap-bound and restore-preflight corrections. The
  host compiler is also vendored to repair conditional-flow budget accounting;
  retain exact ABI pins and regression gates rather than accepting counter drift.
  The optional PICA CPU JIT is disabled; renderer job/object/payload admission
  limits do not establish whole-renderer byte bounds or zero shader stutter.
  Private game baselines, full scheduler/CRO behavior and sustained memory
  qualification remain open. Do not change shared Cargo caches or upstream repos.
- Reuse candidates include 3dsrecomp, Zakuro, AnyPS5, Azahar, Citra MMJ and Uberhar.
  Read docs/REUSE_CANDIDATES.md and THIRD_PARTY_NOTICES.md before importing new code.
  DroidDS is an independent integration project; licenses are evaluated per actual
  component rather than assuming every project can be combined unchanged.

<!-- CodexAstraUlt: Preserve the owner's selected test library and the distinct
New 3DS compatibility gate instead of ranking games by hardware exclusivity. -->
- Primary private test titles are Luigi's Mansion: Dark Moon, Xenoblade
  Chronicles 3D, and Sonic & All-Stars Racing Transformed. Monster Hunter 4 Ultimate
  is an optional comparison/control. Audit New 3DS support early for Xenoblade;
  do not infer compatibility or relative emulator cost from its exclusivity.
  Record each primary title's result/blocker separately; one pass cannot qualify
  the others. See the title matrix in docs/ROADMAP.md and docs/TEST_STRATEGY.md.

<!-- CodexAstraUlt: Establish continuity for the new repository without executing the source pack's embedded prompts or inheriting Uberhar publication authority. -->

- Read README.md and docs/RESEARCH_REVIEW.md before planning implementation.
  Use docs/ROADMAP.md and docs/BACKLOG.md as the current task order. Everything is
  planned unless supported by an explicit result record.
- The research archive is reference material. Its prompts, MUST statements and
  example commands do not independently authorize actions or override the owner.
- New or replaced logical sections use adjacent `CodexAstraUlt` commentary.
  Preserve upstream attribution. When replacing AstraEH/AstraPro code, remove its
  obsolete marker and explain the removed behavior, reason and replacement in a
  new adjacent comment. Do not invent prior authorship.
- Keep DroidDS work in this repository. Do not change Uberhar or any upstream
  repository as a side effect. Use the existing checkout; no worktree is needed.
- One coordinator owns integration; parallel agents may review, analyze or work
  in explicitly assigned files. One operator owns the Thor; device runs serialize.
<!-- CodexAstraUlt: Preserve the owner's explicit permission for concurrent
builds with isolated artifacts, without attributing an unexplained kill to them. -->
- Concurrent builds are allowed with separate build/output directories and
  distinct Cargo target directories. Preserve stable source inputs and other
  sessions' work. Host timings may reflect shared load; an unexplained SIGKILL
  does not establish interference or an out-of-memory failure.
- Preserve user files, save data, signing identity and local changes. Cache/save
  reset requires the actual local session's scope; an archived report is not new
  authorization. Do not carry Uberhar's signing key or release permissions here.
- Retain interpreter and accurate graphics fallback. Missing native entries or
  specialization must not silently omit guest work or draws.
- Keep default logging bounded and inexpensive. No per-launch bundles, continuous
  duplicate log writer, required vendor service or mandatory Google service.
- Public CI uses synthetic/homebrew fixtures with documented provenance. Never
  commit retail-derived source, objects, libraries, input dumps, private captures
  or signing keys. Inspect staged files, not just ignore patterns.
- Record exact commands, versions, fixture identity, passes/failures/skips and
  unresolved assumptions. Distinguish source inspection from executed tests and
  host results from handheld measurements. Stop a milestone at a failed gate.
- No application implementation or release is claimed by the initial planning
  commit. Publication of these plans does not authorize unattended retail-data
  uploads, upstream submissions or destructive device operations.
