# Additional source reuse candidates

<!-- CodexAstraUlt: Record the owner's expanded reuse scope, inspect concrete source boundaries, and distinguish useful designs from code selected for integration. No upstream source is copied by this document. -->

Reviewed 2026-10-17. DroidDS is an integration project: the initial CPU foundation
uses 3dsrecomp and Zakuro, while Android hosting, graphics correctness, resource
management and testing can draw on other projects. It need not become a simple
rebranding of either upstream. The first build should prove the CPU boundary
before importing another emulator's renderer or services.

This reconnaissance inspected selected source files and licenses. It did **not**
build or run these four candidates, benchmark them, or verify every dependency.
No implementation from them was imported during this review. The existing
[research review](RESEARCH_REVIEW.md) covers 3dsrecomp and Zakuro; this document
extends the source map rather than replacing their initial role.

## Exact source identities

<!-- CodexAstraUlt: Pin the inspected trees and distinguish the retained Uberhar checkout from potentially newer work performed by the local development session. -->

| Candidate | Inspected source | License evidence and scope |
| --- | --- | --- |
| [AnyPS5](https://github.com/boykopovar/AnyPS5/tree/66702f1cffd3646f2d674ed093fde0a85a70761f) | `66702f1cffd3646f2d674ed093fde0a85a70761f`, upstream `main` HEAD at inspection | README explicitly says GPL-2.0-only; root LICENSE contains GPLv2. Dependency licenses still require a separate inventory. |
| [Azahar](https://github.com/azahar-emu/azahar/tree/1f5760f3a33b518563a9212775feeb2a8b425e5c) | `1f5760f3a33b518563a9212775feeb2a8b425e5c`, upstream `master` HEAD at inspection | Root LICENSE.txt is GPLv3. NativeLibrary.kt declares GPL-3.0-or-later; inspected FileUtil, Android input/window and Vulkan pool files retain GPL-2.0-or-later notices. Inspect each proposed file and its dependencies. |
| [Citra MMJ](https://github.com/weihuoya/citra/tree/302b0c3bc4312bc96489c11584a97664894b343f) | `302b0c3bc4312bc96489c11584a97664894b343f`, upstream `master` HEAD at inspection | README declares GPL-2.0-or-later; root license.txt includes GPLv2 and additional asset notices. Some Android files lack adjacent notices; retain repository attribution and investigate history before copying them. |
| [Uberhar](https://github.com/RegiRex/uberhar/tree/814de4d604cab08e01a199a259ea2f3109ba62a4) | `814de4d604cab08e01a199a259ea2f3109ba62a4`, existing cloud checkout, not claimed as current remote HEAD | Root license.txt is GPLv2; inspected custom pipeline/logging files explicitly declare GPL-2.0-or-later. Preserve Citra, Azahar, Uberhar and individual source attribution. |

The MMJ identity was checked against the repository's
[20251112 release](https://github.com/weihuoya/citra/releases/tag/20251112), whose
assets include `Citra_MMJ_20251112.apk`. That release is identity evidence, **not**
evidence that its APK was built from the newer source pin inspected here.
Uberhar was read without fetching, editing or changing its working tree.

## Component decisions

<!-- CodexAstraUlt: Identify small interfaces that can improve DroidDS without adding a second CPU/HLE/renderer stack to the first foundation milestone. -->

| Area | Candidate and practical boundary | Initial disposition | Relevant task |
| --- | --- | --- | --- |
| Android surface and lifecycle | Azahar's primary/secondary surface callbacks, pause/resume/stop interface and ANativeWindow-backed Vulkan window | Use to design the Kotlin-to-Rust host contract; assess small source reuse when that host is implemented | DDS-010/012 |
| Android storage and input | Azahar URI-to-owned-file-descriptor bridge and input event mapping; MMJ controller normalization and JNI storage adapter | Reuse standard platform patterns; require explicit ownership, error and seek/read semantics before transplanting source | DDS-010/012 |
| Vulkan object lifetime | Azahar GPU-tick-based resource reuse and semaphore completion | Adapt the lifetime model to Zakuro's ownership; add actual capacity/admission bounds | DDS-006/008 |
| Shader/cache identity | AnyPS5 request keys include ABI and semantic state; disk encoding validates versions and payloads | Independent implementation and tests fitted to PICA/Zakuro; no RDNA translator import | DDS-006/009 |
| Graphics diagnostics and fallback | Uberhar's pipeline success/failure selection tests, bounded diagnostics and readiness records | Reuse lessons and independently written cases first; inspect a specific GPL component if direct reuse would materially help | DDS-007/008/015 |
| Device automation | Uberhar's bounded read-only local ADB probe and single-device-operator workflow | Adapt device workflow for DroidDS's eventual package identity; no assumption of cloud USB access | DDS-010/014 |
| Guest CPU, OS services and renderer replacement | AnyPS5 relinker/PS5 libraries, complete Azahar/MMJ/Uberhar cores | No wholesale import in the foundation batch; select a specific missing capability only after a failing measured gate | Later architecture review |

### AnyPS5: useful compiler infrastructure ideas, different guest architecture

The [architecture](https://github.com/boykopovar/AnyPS5/blob/66702f1cffd3646f2d674ed093fde0a85a70761f/docs/dev/ARCHITECTURE.md)
describes executable relinking to Linux/Windows and native implementations of PS5
system libraries. Its shader pipeline decodes RDNA and emits SPIR-V. These are not
an ARM11-to-ARM64 compiler, 3DS HLE services, or a PICA shader implementation.
Importing that relinker would not replace the current 3dsrecomp CPU work.

Specific useful references:

- [CacheKey.hpp](https://github.com/boykopovar/AnyPS5/blob/66702f1cffd3646f2d674ed093fde0a85a70761f/core/shader/recompiler/CacheKey.hpp)
  incorporates runtime ABI, shader stage/code and interface state, including
  floating-point controls and target properties. DroidDS needs its own PICA and
  driver/compiler identity fields; copying a PS5 key structure is insufficient.
- [ShaderDiskCache.cpp](https://github.com/boykopovar/AnyPS5/blob/66702f1cffd3646f2d674ed093fde0a85a70761f/core/shader/recompiler/ShaderDiskCache.cpp#L1298)
  rejects magic, format and compiler source-version mismatches. Its decoder checks
  remaining input lengths and complete consumption. These are useful independent
  corruption/truncation test requirements for Zakuro's existing cache layer.
- [CacheFileReadTests.cpp](https://github.com/boykopovar/AnyPS5/blob/66702f1cffd3646f2d674ed093fde0a85a70761f/core/shader/recompiler/tests/CacheFileReadTests.cpp)
  deliberately injects allocation failure and verifies that a failed read leaves
  no partial result. This review read the tests; it did not execute them.
- The [hardware-oracle method](https://github.com/boykopovar/AnyPS5/blob/66702f1cffd3646f2d674ed093fde0a85a70761f/docs/dev/HW_ORACLE.md)
  records exact hardware and floating-point controls for discriminating synthetic
  cases. Apply that methodology to 3DS/PICA references where available. Its AMD
  RDNA runner cannot serve as a 3DS or Adreno correctness oracle.

Do not copy desktop thread counts, pipeline-journal defaults or large worker
stacks into a handheld runtime. AnyPS5's documented warm-run replay also permits
a draw to build a pipeline if replay has not completed; it is not evidence of
universal cold-run zero-compilation behavior.

### Azahar: strongest candidate for Android boundaries and 3DS reference cases

The inspected [NativeLibrary.kt](https://github.com/azahar-emu/azahar/blob/1f5760f3a33b518563a9212775feeb2a8b425e5c/src/android/app/src/main/java/org/citra/citra_emu/NativeLibrary.kt#L177)
defines primary/secondary surface events and pause/resume/stop entry points.
[EmuWindow_Android_Vulkan](https://github.com/azahar-emu/azahar/blob/1f5760f3a33b518563a9212775feeb2a8b425e5c/src/android/app/src/main/jni/emu_window/emu_window_vk.cpp)
maps an Android native window into the Vulkan frontend. These establish relevant
platform boundaries, but the objects reference Azahar's C++ frontend/core and
cannot be linked into Zakuro unchanged. DroidDS needs one explicit runtime owner,
surface generation/lifetime rules, and callbacks suitable for its Rust core.

[FileUtil.openContentUri](https://github.com/azahar-emu/azahar/blob/1f5760f3a33b518563a9212775feeb2a8b425e5c/src/android/app/src/main/java/org/citra/citra_emu/utils/FileUtil.kt#L102)
opens a document through ContentResolver and transfers descriptor ownership with
`detachFd()`. This is a useful Android storage boundary. A DroidDS adapter must
close descriptors exactly once, reject unsupported random access, handle revoked
permissions and keep private generated libraries out of arbitrary document paths.

The [Vulkan resource pool](https://github.com/azahar-emu/azahar/blob/1f5760f3a33b518563a9212775feeb2a8b425e5c/src/video_core/renderer_vulkan/vk_resource_pool.cpp#L21)
reuses resources only when the GPU completion tick permits it. However,
`ManageOverflow()` grows the pool; this is **not** itself a memory budget. If that
model informs DDS-008, couple it to bounded admission and fence-aware retirement,
without blocking optional specialization on a full queue.

Future PICA/HLE comparisons should minimize a failing case and locate the exact
implementation before choosing a port. No claim that all Azahar behavior is an
independent hardware oracle follows from this source review.

### Citra MMJ: mobile experience, with correctness-sensitive shortcuts to exclude

The inspected source provides Android
[controller normalization](https://github.com/weihuoya/citra/blob/302b0c3bc4312bc96489c11584a97664894b343f/src/android/jni/input_manager.cpp),
[surface/lifecycle JNI](https://github.com/weihuoya/citra/blob/302b0c3bc4312bc96489c11584a97664894b343f/src/android/jni/main_android.cpp#L340),
and [storage adapters](https://github.com/weihuoya/citra/blob/302b0c3bc4312bc96489c11584a97664894b343f/src/android/jni/saf_handler.cpp).
These can inform a small mobile host; they depend on the Citra frontend model and
are not drop-in Rust runtime components.

The storage adapter warrants contract tests before reuse: its SAF read/write
methods return POSIX byte counts, while its stdio methods return element counts;
the two seek methods also use opposite success expressions. These are source
observations, not a demonstrated MMJ device failure. DroidDS should define a
single byte-oriented, explicit-result storage interface and test short reads,
errors, zero-length operations and seekability.

The inspected tree contains an OpenGL renderer rather than a Vulkan backend.
Its [display-transfer path](https://github.com/weihuoya/citra/blob/302b0c3bc4312bc96489c11584a97664894b343f/src/video_core/renderer_opengl/gl_rasterizer.cpp#L1322)
contains a title/address-specific adjustment, and its
[texture-copy path](https://github.com/weihuoya/citra/blob/302b0c3bc4312bc96489c11584a97664894b343f/src/video_core/renderer_opengl/gl_rasterizer.cpp#L1415)
can return `skip_texture_copy` when the source surface is absent. Its Android
build also supplies `-Ofast`. Do not inherit these as general optimization
defaults: DroidDS's initial correctness gate requires complete guest work and
controlled floating-point semantics. Any useful optimization must survive the
same reference tests before it is adopted.

### Uberhar: concrete failure tests and low-overhead diagnostic policy

At the inspected retained revision,
[diagnostic_queue.h](https://github.com/RegiRex/uberhar/blob/814de4d604cab08e01a199a259ea2f3109ba62a4/src/common/logging/diagnostic_queue.h)
uses nonwaiting admission for optional diagnostic entries and an omission counter
reported by the existing consumer. Reliable lifecycle/error entries retain a
separate delivery policy; formatting occurs before admission. Adopt the
distinction and measure producer costs, rather than claiming every log operation
is nonblocking or adding another writer.

[Pipeline selection tests](https://github.com/RegiRex/uberhar/blob/814de4d604cab08e01a199a259ea2f3109ba62a4/tools/uberhar/test_pipeline_policy.cpp)
exercise completed-versus-usable state, failed alternatives, terminal failure and
bounded expanded geometry. These are useful scenarios for DroidDS's own fallback
and queue tests. Their C++ selection implementation can still wait when no usable
pipeline exists; copying it would not satisfy the ready-fallback gate by itself.

The [device probe](https://github.com/RegiRex/uberhar/blob/814de4d604cab08e01a199a259ea2f3109ba62a4/tools/uberhar/device_testing/README.md)
provides a narrow local-ADB readiness workflow, not a game runner or a bridge from
this cloud session to the Thor. Use its bounded-request and one-operator lessons
when DroidDS has an Android fixture. No phone is required for this first Linux
foundation build.

Historical Uberhar evidence must stay precise: the owner's correction is that
Native has no observed moon flashing while Combo flashes moon segments. Ghost
corruption is a separate target. Static frames do not establish temporal parity;
successful teardown does not prove gameplay memory is bounded. These are test
requirements, not evidence that Zakuro or DroidDS has the same defect.

## Import and validation rules

<!-- CodexAstraUlt: Make source reuse an explicit, reviewable integration decision while preserving compatible licensing and attribution. -->

1. Select a concrete missing capability or measured defect, identify the smallest
   relevant files and dependencies, and preserve their exact commit/provenance.
2. Record whether the change copies/adapts code or independently implements an
   interface/test idea. Rewriting GPL code in Rust does not automatically remove
   its licensing obligations. Preserve original notices and add adjacent
   `CodexAstraUlt` commentary describing DroidDS's changes.
3. Review the combined dependency licenses before distribution. GPL-2.0-only
   AnyPS5 code cannot simply be combined into one derived program with
   GPL-3.0-or-later source. GPL-2.0-or-later files may permit a compatible
   version choice, but the full dependency graph still matters. Neither an FFI
   boundary nor a separate shared-library filename automatically resolves this.
   Do not describe all of DroidDS as MIT because some foundations use MIT.
4. GPL components remain legitimate candidates when the resulting obligations
   are accepted and fulfilled: retain notices, provide the applicable license,
   track modifications and supply required corresponding source/build material
   with covered distribution. There is no blanket rejection of GPL reuse here.
5. Test the adapted boundary using public synthetic cases first. Then measure
   correctness, memory and speed on the actual target. A source inspection, test
   read, desktop result or another emulator's reputation is not a DroidDS
   handheld performance result.

The first integration decision remains the 3dsrecomp/Zakuro CPU fixture. The next
reuse review should focus on Android ownership/storage for DDS-010 and Vulkan
lifetime/admission for DDS-006/008, rather than adding several complete emulators
to the build at once.
