# Third-party source and notice record

<!-- CodexAstraUlt: Replace the earlier source-only notice record with an
artifact notice collector now that the owner authorizes an Android prerelease.
Preserve attribution without inventing missing upstream copyright notices. -->

DroidDS obtains its upstream components through full-commit Cargo Git dependencies.
The 0.0.4 Android CPU/Vulkan probe uses the same pinned ABI/interpreter components
as the Linux foundation. Its original Java/JNI/Rust shell and GLSL fixtures add no
registry dependency. Vulkan API declarations and the offline shader tools come
from the same pinned Android NDK; their supplied notices remain in the bundle.
The owner has authorized a downloadable Android probe prerelease.

`tools/collect_android_notices.py` assembles `THIRD_PARTY_NOTICES.txt` from the
actual locked package sources and pinned toolchain, for inclusion in the APK and
beside its download. It preserves complete supplied license files and their byte
hashes, the explicit 3dsrecomp MIT declarations and standard terms, Rust's runtime
copyright record, and NDK support notices. This Markdown file documents that
process; the generated text is the distribution notice bundle.

See [the integration decisions](docs/UPSTREAM_INTEGRATION.md) and `Cargo.lock` for
the selected source and resolved dependency graph.

## 3dsrecomp and recomp-abi

<!-- CodexAstraUlt: Preserve the manifest's MIT declaration without fabricating a copyright holder or substituting another project's notice. -->

Source: <https://github.com/fearkov/3dsrecomp>

Selected commit: `c3f21f94ba50d688025febc8974ff348d471b587`.

Both `Cargo.toml` (`recomp3ds` 0.1.0) and `abi/Cargo.toml` (`recomp-abi` 0.1.0)
declare `license = "MIT"`. No LICENSE, NOTICE or COPYING file is present in the
selected Git tree, and no supplied copyright notice was found in the inspected
source. No copyright notice has been inferred from author identities or from
Zakuro's separate license.

<!-- CodexAstraUlt: The earlier blanket redistribution hold was more conservative
than the evidence required. The explicit upstream MIT declarations supply the
license choice; retain standard terms and document the missing supplied notice. -->

An inspection of the upstream's full reachable history on 2026-10-18 found no
additional LICENSE/NOTICE/COPYING file; current HEAD still equals the pinned
revision. The missing standalone file does not erase the explicit MIT license
declarations. The prerelease relies on those upstream declarations and includes
both original manifests plus the standard MIT permission, condition and warranty
text. That text is labeled as reconstructed from the SPDX declaration, not as an
upstream-supplied license file. No copyright holder or year is invented, and
Zakuro's separate copyright notice is not applied to 3dsrecomp.

This resolves the earlier self-imposed blanket hold for the current probe. Future
dependency revisions must be reviewed again; if upstream supplies a copyright or
notice file later, retain it. `recomp-abi` links into the probe. `recomp3ds` runs on
the build host and emits support code for the original synthetic fixtures; its
host executable is not bundled into the APK.

## Zakuro

<!-- CodexAstraUlt: Preserve the exact notice supplied in the pinned Zakuro root LICENSE; it applies to the selected CPU/common components without asserting provenance for unrelated projects. -->

Source: <https://github.com/fearkov/zakuro>

Selected commit: `412900a5a020301da15c1cc382585e05a489a535`.

Selected components: `zakuro-cpu` and `zakuro-common` 0.2.27. Their manifests inherit
the workspace's MIT declaration. The following is the exact text of the root
`LICENSE` at that commit:

```text
MIT License

Copyright (c) 2026 fearkov

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```

## Resolved registry inventory

<!-- CodexAstraUlt: Inventory the actual resolved registry package declarations and supplied files; retain compound licenses rather than flattening every dependency to MIT. -->

Observed from the resolved Cargo metadata and fetched registry package contents
on 2026-10-17. Inventory lockfile SHA-256:
`42d085a4249ec3490496bbb30f727c187849966cf33594dd1a94f847671324cb`.
All 19 registry packages have license files at the relative paths below. License
expressions are transcribed from their package metadata, not inferred from another
dependency. The lockfile supplies each registry package's source and checksum.

| Package | Version | Declared license expression | Supplied files relative to the package root |
| --- | --- | --- | --- |
| bitflags | 2.13.2 | `MIT OR Apache-2.0` | `LICENSE-APACHE`, `LICENSE-MIT` |
| cfg-if | 1.0.5 | `MIT OR Apache-2.0` | `LICENSE-APACHE`, `LICENSE-MIT` |
| itoa | 1.0.18 | `MIT OR Apache-2.0` | `LICENSE-APACHE`, `LICENSE-MIT` |
| libc | 0.2.191 | `MIT OR Apache-2.0` | `LICENSE-APACHE`, `LICENSE-MIT` |
| libloading | 0.8.9 | `ISC` | `LICENSE` |
| log | 0.4.34 | `MIT OR Apache-2.0` | `LICENSE-APACHE`, `LICENSE-MIT` |
| memchr | 2.8.3 | `Unlicense OR MIT` | `COPYING`, `LICENSE-MIT`, `UNLICENSE` |
| proc-macro2 | 1.0.107 | `MIT OR Apache-2.0` | `LICENSE-APACHE`, `LICENSE-MIT` |
| quote | 1.0.47 | `MIT OR Apache-2.0` | `LICENSE-APACHE`, `LICENSE-MIT` |
| serde | 1.0.229 | `MIT OR Apache-2.0` | `LICENSE-APACHE`, `LICENSE-MIT` |
| serde_core | 1.0.229 | `MIT OR Apache-2.0` | `LICENSE-APACHE`, `LICENSE-MIT` |
| serde_derive | 1.0.229 | `MIT OR Apache-2.0` | `LICENSE-APACHE`, `LICENSE-MIT` |
| serde_json | 1.0.154 | `MIT OR Apache-2.0` | `LICENSE-APACHE`, `LICENSE-MIT` |
| syn | 3.0.9 | `MIT OR Apache-2.0` | `LICENSE-APACHE`, `LICENSE-MIT` |
| thiserror | 2.0.21 | `MIT OR Apache-2.0` | `LICENSE-APACHE`, `LICENSE-MIT` |
| thiserror-impl | 2.0.21 | `MIT OR Apache-2.0` | `LICENSE-APACHE`, `LICENSE-MIT` |
| unicode-ident | 1.0.27 | `(MIT OR Apache-2.0) AND Unicode-3.0` | `LICENSE-APACHE`, `LICENSE-MIT`, `LICENSE-UNICODE` |
| windows-link | 0.2.1 | `MIT OR Apache-2.0` | `license-apache-2.0`, `license-mit` |
| zmij | 1.0.23 | `MIT` | `LICENSE-MIT` |

`windows-link` is a Windows-only dependency of `libloading`; its appearance in
the cross-platform lockfile does not imply it links into the Linux executable.
Procedural-macro packages also have a build-time role that differs from the
runtime library graph. `unicode-ident` explicitly includes Unicode-3.0 obligations
in addition to its MIT/Apache alternative. Do not drop that conjunction when
assembling a distribution's notices.

## Android distribution bundle

<!-- CodexAstraUlt: Include supplied runtime/toolchain notices in addition to
Cargo declarations, and distinguish conservative attribution from actual linkage. -->

A registry checksum is an integrity identifier, not a license. The supplied
license/notice files listed above are collected verbatim. The collector deliberately
includes all 23 third-party packages in the resolved cross-platform workspace,
including host-only and procedural-macro dependencies. This keeps all supplied
notices without asserting that every package's code links into the APK.

The collector additionally preserves:

- Rust 1.95.0's `share/doc/rust/COPYRIGHT-library.html` in its original HTML form,
  including standard-library dependencies, copyright attribution and license
  exceptions. Rust provides this separate runtime-specific record; the much larger
  compiler inventory is not an APK input.
- Android NDK `27.3.13750724`'s root `NOTICE`, `NOTICE.toolchain` and
  `toolchains/llvm/prebuilt/linux-x86_64/NOTICE`. These supplied broad records
  cover CRT/compiler support and preserve LLVM exceptions and other applicable
  notices. Including the records does not bundle the NDK's compiler or tools.

Android's framework and shared system libraries are supplied by the device. The
APK's ELF audit permits only the packaged probe/fixture libraries and Android
`libc`, `libm`, `libdl`, `liblog` and `libvulkan`; it does not package a C++ standard library.
The probe does not copy Java library implementations or bundle the JDK/Android
SDK. Its Java shell is original DroidDS code.

<!-- CodexAstraUlt: Separate host-only validation tools from the Android payload;
original shaders are compiled offline and require no bundled compiler or driver. -->
Mesa/lavapipe and the Khronos validation layer are host test tools, not APK inputs.
The Android device supplies its Vulkan loader/driver. The GLSL shaders and the
offscreen test are original DroidDS code; no renderer implementation is imported
for this probe. The Android build does not enable or require validation layers.
The notice collector also preserves the actual copyright/SPDX comment blocks
from the three included Vulkan core/platform headers and seven transitive video
declaration headers, with full-header hashes. Those declarations add no video
feature; their bodies are not copied into the notice bundle. Full Apache-2.0 terms
are already retained from the supplied registry license files.

The collector fails before packaging if a required supplied file is missing or
empty, the reviewed package inventory/license expressions change, upstream Git
pins differ, or the Rust/NDK versions differ. Regression tests cover these gates,
retention of exact supplied bytes, and the Unicode license conjunction.

This record does not relicense upstream source or select a license for original
DroidDS code. No Nintendo game content or private title-derived code is included.
Any future Android/GPU/service component or Uberhar/Azahar/MMJ/AnyPS5 reuse needs
its own actual-source license review and notice update.
