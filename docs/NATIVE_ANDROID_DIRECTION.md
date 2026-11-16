# Native Android direction

<!-- CodexAstraUlt: Compare exact source versions, distinguish implemented
behavior from proposed architecture, and preserve the existing private builds. -->

DroiDDS already builds a game's translated CPU code into a native ARM64 Android
APK. The useful change of direction is to reduce the graphics and service work
around that code. The recommendation is to retain the existing ahead-of-time
compiler and move more graphics work through a correct, bounded Vulkan resource
path. Peanuts Native provides useful examples of high-level graphics interception
and preparation; its CPU shortcut does not directly apply to 3DS code.

This source review uses DroiDDS
[`cfa8a70701160709f834b4bf9b59d9d1d5446914`](https://github.com/RegiRex/DroiDDS/tree/cfa8a70701160709f834b4bf9b59d9d1d5446914)
and Peanuts Native tag **v0.1.3-1**, resolved to
[`0552f848679f3cdb149b7611541cd02e1c161cca`](https://github.com/igawa6/peanuts-native/tree/0552f848679f3cdb149b7611541cd02e1c161cca).
Peanuts was inspected as source, not built or run. The measured performance below
comes from the owner's uploaded DroiDDS code 17 run; it is not a benchmark of
Peanuts or proof of either project's performance on other titles.

## What is already native

| Boundary | Peanuts Native at the inspected tag | DroiDDS at the inspected commit |
| --- | --- | --- |
| Guest CPU | Selected AArch64 instructions and call sites are rewritten; ordinary compatible AArch64 instructions execute directly on the Android CPU. | ARMv6K/Thumb code is translated into C, then compiled by the Android NDK into AArch64 machine code. Unknown paths retain interpreter fallback. |
| Console services | Host implementations replace the needed Horizon services and other intercepted functions. | The Zakuro runtime retains 3DS scheduling, SVC/service behavior, guest memory and DSP handling around native CPU execution. |
| Graphics | Intercepts the NVN API, records graphics operations and implements them through Vulkan on Android. | Decodes GSP/PICA operations, constructs draw state and uses Vulkan; the tested route still performs vertex shading and related processing on the CPU. |
| Game preparation | Rewritten module packs, translated shader libraries and title/build profiles are consumed by the launcher. | A validated per-title native library is packaged with the shared player/JNI code in a per-title APK. |
| Compatibility | Profiles, supported calls, shader translation and driver behavior constrain individual games and revisions. | Native-code admission, service/PICA accuracy, title revision, shader coverage and driver behavior constrain individual games and revisions. |

Neither design makes the console's operating system and graphics semantics
disappear. A native Android APK describes the host package and machine code;
it does not mean that every graphics operation becomes an efficient native draw.

DroiDDS's existing path is concrete:

1. [Generate C from the resolved title](https://github.com/RegiRex/DroiDDS/blob/cfa8a70701160709f834b4bf9b59d9d1d5446914/crates/droidds-title-builder/src/lib.rs#L291).
   The [code generator](https://github.com/RegiRex/DroiDDS/blob/cfa8a70701160709f834b4bf9b59d9d1d5446914/vendor/3dsrecomp/src/codegen/mod.rs#L1)
   translates guest functions and returns control to the host for SVCs, unknown
   targets and execution budgets.
2. [Compile for `aarch64-linux-android`](https://github.com/RegiRex/DroiDDS/blob/cfa8a70701160709f834b4bf9b59d9d1d5446914/tools/compile_android_title.py#L25)
   with the pinned NDK. [APK packaging](https://github.com/RegiRex/DroiDDS/blob/cfa8a70701160709f834b4bf9b59d9d1d5446914/tools/build_android_title.py#L422)
   copies the admitted `libdroidds_title.so`, builds the shared player/JNI and
   places those libraries under `lib/arm64-v8a/`.
3. [Admit the library against the original mapped code](https://github.com/RegiRex/DroiDDS/blob/cfa8a70701160709f834b4bf9b59d9d1d5446914/crates/droidds-title-runtime/src/admission.rs#L130).
   Native functions use the runtime's register context and page tables, with
   [interpreter fallback](https://github.com/RegiRex/DroiDDS/blob/cfa8a70701160709f834b4bf9b59d9d1d5446914/vendor/zakuro/crates/zakuro-core/src/recompiled.rs#L1).
   The admitted native scope is the immutable executable;
   [movable CRO modules remain interpreted](https://github.com/RegiRex/DroiDDS/blob/cfa8a70701160709f834b4bf9b59d9d1d5446914/vendor/zakuro/crates/zakuro-core/src/recompiled.rs#L171).

This is a translated native executable with a compatibility runtime, not a
reconstruction of the game's original source or an Android engine port.

## What Peanuts actually changes

The [rewriter](https://github.com/igawa6/peanuts-native/blob/0552f848679f3cdb149b7611541cd02e1c161cca/dm/tools/patch_nso.py#L1)
handles AArch64 register/thread-local conventions, SVCs, timers and selected
other sites. The [loader](https://github.com/igawa6/peanuts-native/blob/0552f848679f3cdb149b7611541cd02e1c161cca/dm/host/loader.c#L948)
maps rewritten images executable, and the [thread entry](https://github.com/igawa6/peanuts-native/blob/0552f848679f3cdb149b7611541cd02e1c161cca/dm/host/entry.S#L161)
branches into the guest's machine code. This works because the supported guest
and Android host use the same instruction set. Its
[new-game guide explicitly rejects 32-bit games](https://github.com/igawa6/peanuts-native/blob/0552f848679f3cdb149b7611541cd02e1c161cca/peanuts/docs/NEW-GAME.md#L55).
The [3DS ARMv6K/Thumb-1 input](https://github.com/RegiRex/DroiDDS/blob/cfa8a70701160709f834b4bf9b59d9d1d5446914/vendor/3dsrecomp/src/thumb.rs#L1)
requires a different translation step for our portable ARM64 Android target.
Reusing the Switch patcher would not remove that requirement.

The more relevant boundary is
[`nvnBootstrapLoader` interception](https://github.com/igawa6/peanuts-native/blob/0552f848679f3cdb149b7611541cd02e1c161cca/dm/gfx/nvn/hle_nvn.c#L111).
Its [NVN layer](https://github.com/igawa6/peanuts-native/blob/0552f848679f3cdb149b7611541cd02e1c161cca/dm/gfx/nvn/hle_nvn.c#L1)
bypasses the guest NVN driver and implements graphics API semantics directly.
This avoids reproducing every lower-level action that the original driver would
have performed. DroiDDS should look for similarly justified boundaries without
assuming that statically linked 3DS SDK code exposes an equivalent universal API.

The release's default Peanuts configuration uses
[one generic host/launcher](https://github.com/igawa6/peanuts-native/blob/0552f848679f3cdb149b7611541cd02e1c161cca/android/app/build.gradle#L15)
and [per-title runtime profile assets](https://github.com/igawa6/peanuts-native/blob/0552f848679f3cdb149b7611541cd02e1c161cca/android/app/build.gradle#L471).
Preparing a game is therefore not the same operation as compiling a new C/NDK
application for each title. Unknown games still need profiles and bring-up;
the [guide warns this can take days](https://github.com/igawa6/peanuts-native/blob/0552f848679f3cdb149b7611541cd02e1c161cca/peanuts/docs/NEW-GAME.md#L3).

Offline shader translation also does not imply that every possible shader or
driver pipeline is precompiled. The runtime still calls
[`vkCreateGraphicsPipelines`](https://github.com/igawa6/peanuts-native/blob/0552f848679f3cdb149b7611541cd02e1c161cca/dm/gfx/vk_android/vka_pso.c#L529),
including work on the frame path. Some unsupported mesh-derived shader failures
explicitly [skip draws](https://github.com/igawa6/peanuts-native/blob/0552f848679f3cdb149b7611541cd02e1c161cca/dm/gfx/vk_android/vka_memu.c#L64).
That behavior is not suitable for DroiDDS's correctness goal. This source is not
evidence of universal compatibility, zero cold-run stutter or guaranteed speed.

## What code 17 says about the bottleneck

The [full report](https://github.com/RegiRex/DroiDDS/blob/cfa8a70701160709f834b4bf9b59d9d1d5446914/docs/device-tests/reports/2026-11-09-preview7-cpu-run-001/cpu-session.json)
and [reviewed summary](https://github.com/RegiRex/DroiDDS/blob/cfa8a70701160709f834b4bf9b59d9d1d5446914/docs/device-tests/reports/2026-11-09-preview7-cpu-run-001/android-title-build-summary.md#L48)
show 18.66% emulated speed in the Native/CPU/Vulkan 1× menu test. Its counted
guest instructions are **2,249,770,374 native and 225,964 interpreted**:
**99.989957% native by instruction count**. This is not a time percentage,
full-title coverage claim or proof that translated CPU code has no overhead.

These measured parent scopes are disjoint:

| Work | Wall time within core work |
| --- | ---: |
| PICA command-list processing | 59.2141 s |
| Queued display transfers | 27.0627 s |
| Queued texture copies | 6.1356 s |
| Runtime screen readback/conversion | 0.9960 s |
| Total of those scopes | **93.4084 s / 100.0895 s core time: 93.32%** |

Within command-list processing, CPU vertex shaders cost 30.3929 seconds, input
decoding 11.3129 seconds and placement 8.4079 seconds. These approximately 50.11
seconds are nested work: **do not add them to the parent table**. Likewise,
23.9797 seconds of hardware-transfer attempts and 5.9064 seconds of texture-copy
synchronization are nested transfer measurements. An attempt timer includes
host reconciliation, waits and possible declined work; it is not pure GPU time.
The remaining unclassified core work includes execution, scheduling and guards,
not just translated CPU execution.

This evidence prioritizes graphics translation and synchronization ahead of a
replacement game-CPU compiler. It does not promise that eliminating any one
timer produces an equal speed gain: work can move between scopes or expose new
bottlenecks. The runtime scanout timer is only about 1% of core time and excludes
Android UI work, so direct presentation alone is not an evidenced solution to
the roughly fivefold slowdown.

## Recommended staged direction

<!-- CodexAstraUlt: The first stage names the current candidate explicitly;
later stages are architectural proposals, not completed or approved device tests. -->

### Current candidate: specialize presentation for the native readback consumer

**Implemented; local correctness, benchmark and Android package checks pass.**
Hosted publication and a new private device result remain pending. Code 17's
tiled-output optimization did not engage: all 7,674 accepted hardware transfers
had linear output. Treating every linear transfer as immediate presentation work
is a poor fit for a player that consumes guest framebuffer readback itself.

The current candidate introduces a `NativeReadback` presentation specialization
for that consumer. Its goal is to avoid unnecessary presentation work while
retaining guest transfer results, visibility, ordering and correct screen
selection. This is a focused renderer/runtime change, not GPU-only guest memory
or a new direct Android swapchain. Historical presentation consumers must retain
their existing behavior. Cloud correctness, retained-library packaging and
independent review must pass before claiming readiness; a measured Thor gain
remains a separate gate.

This candidate must reuse the existing preparation, all 521 Android objects and
the completed private native library, with the same package and signing
identity. Preserve the separate Linux build, imports, saves and prior reports.
These reuse guarantees apply to this runtime-only candidate; future compiler or
hook changes require an explicit compatibility decision.

### Next architecture: GPU resource ownership and visibility

**Proposed follow-up, driven by the transfer measurements.** Extend the existing
resource model to express which CPU/GPU consumer needs which version of a
surface, and materialize bytes only at required visibility boundaries. Preserve
guest address aliasing, overlap, pitch, format conversion, ordering, interrupts
and presentation semantics. Bound retained bytes, pending work and staging
allocations; retire them using actual fence completion.

This must be more than deleting readbacks. At the inspected commit, the
[CPU-read callback synchronizes depth](https://github.com/RegiRex/DroiDDS/blob/cfa8a70701160709f834b4bf9b59d9d1d5446914/vendor/zakuro/crates/zakuro-core/src/lib.rs#L1391),
whereas the write callback uses broader memory synchronization. That does not
establish a general contract for leaving arbitrary color/texture copy results
only on the GPU. Extend and prove the visibility contract before making that
change. Original fixtures should test CPU reads after GPU writes, aliases,
strided/overlapping copies, chained transfers, rejected fast paths and eviction
with in-flight work.

Use the existing [typed GSP commands](https://github.com/RegiRex/DroiDDS/blob/cfa8a70701160709f834b4bf9b59d9d1d5446914/vendor/zakuro/crates/zakuro-core/src/services/gsp.rs#L44)
and [draw-state boundary](https://github.com/RegiRex/DroiDDS/blob/cfa8a70701160709f834b4bf9b59d9d1d5446914/vendor/zakuro/crates/zakuro-gpu/src/raster.rs#L1895).
There is already a representation between PICA state and hardware draws; this
plan does not call for a duplicate generic intermediate representation.

### High-speed path: correct GPU vertex work and prepared PICA shaders

**Essential investigation for the speed target; not currently qualified.**
DroiDDS already has a [hardware vertex-shading route](https://github.com/RegiRex/DroiDDS/blob/cfa8a70701160709f834b4bf9b59d9d1d5446914/vendor/zakuro/crates/zakuro-gpu/src/raster.rs#L2651).
The prior Thor pipeline failure must be explained and covered by cloud shader,
pipeline and CPU/GPU parity tests before proposing another device GPU test.
Further Thor GPU testing remains deferred. Keep the accurate CPU route as the
reference and correctness fallback while reducing its measured costs.

Investigate prepared PICA shader translations with identities covering guest
shader bytes, semantic state, translator version and required features. Bound
admission, compilation and cache memory. A prepared shader pack can reduce
translation work, but the driver may still create pipelines and unseen variants
must remain correct. Do not skip draws. The previously disabled
[CPU shader JIT](https://github.com/RegiRex/DroiDDS/blob/cfa8a70701160709f834b4bf9b59d9d1d5446914/vendor/zakuro/crates/zakuro-gpu/Cargo.toml#L10)
would require separate correctness and retention qualification before any future
use. Shader coverage, cold execution and correct images are separate gates from
instruction coverage.

### Optional specialization: proven SDK/function replacements

**Proposed research after the resource boundaries are sound.** For a supported
title revision, an identified SDK graphics/copy routine could call a host
implementation instead of executing translated SDK code and rebuilding the
same lower-level commands. This is the closest transferable idea to the NVN
boundary, but there is no demonstrated universal 3DS equivalent in this review.

Require exact title/build identity, complete function and ABI identification,
input/output and side-effect equivalence, scheduling/order preservation and a
reliable fallback. A numerical address alone is insufficient. Test replacement
and reference behavior on original fixtures and the authorized private title;
unknown revisions must use the existing route. Compiler integration or new
generated code may be needed, so do not promise reuse of the present 521 objects
for such a future change. No title-specific hook is implemented by this review.

### Later: direct Android presentation and simpler packaging

**Proposed after graphics ownership is stable.** The current runtime
[reads both guest screens](https://github.com/RegiRex/DroiDDS/blob/cfa8a70701160709f834b4bf9b59d9d1d5446914/crates/droidds-title-runtime/src/lib.rs#L256)
and Android [copies a Bitmap into Canvas](https://github.com/RegiRex/DroiDDS/blob/cfa8a70701160709f834b4bf9b59d9d1d5446914/android/probe/java/org/droidds/probe/ScreenView.java#L40).
Direct Vulkan presentation through Android native surfaces can avoid copies and
support explicit physical-display routing. It requires lifecycle, resize,
pause/resume, synchronization and both-screen correctness work. Measure the UI
cost first; the recorded scanout cost alone does not justify making this the
first performance rewrite.

A generic launcher with validated title packs is a possible later usability
change. It does not itself accelerate graphics or CPU execution. An on-device
builder would also add compiler/toolchain storage and thermal costs. Keep the
working desktop preparation and compatible per-title APK updates while the
runtime becomes playable; neither packaging change is required for 0.1.0.

## Acceptance and reuse boundaries

Each stage needs a concrete correctness and performance result: original-fixture
parity, bounded memory/resource lifetime, a compatible APK using retained private
artifacts where applicable, and then one approved device comparison. Track
process/driver memory separately from guest allocation. Record emulated speed,
observed images, audio continuity and sustained behavior; frame events alone
are not unique displayed FPS or gameplay qualification. Cloud builds cannot
establish Thor/Retroid GPU performance or guarantee 100% speed at 2×/4×.

No Peanuts code was copied in this review. Its
[README](https://github.com/igawa6/peanuts-native/blob/0552f848679f3cdb149b7611541cd02e1c161cca/README.md#L139)
declares GPL-3.0-or-later for the project as a whole and credits MIT nxnative and
nx2android components. The [Android notice](https://github.com/igawa6/peanuts-native/blob/0552f848679f3cdb149b7611541cd02e1c161cca/android/NOTICE.md#L3)
separately identifies GPL shader-translation, mesh-emulation and frame-generation
components; a top-level MIT file is not sufficient permission to treat the
whole Android stack as MIT. Any future code reuse needs a per-file provenance
and combined-license review, retained notices and applicable source obligations.
The architectural recommendations here require no wholesale code import.
