# Third-party source and notice record

<!-- CodexAstraUlt: Replace the earlier source-only notice record with an
artifact notice collector now that the owner authorizes an Android prerelease.
Preserve attribution without inventing missing upstream copyright notices. -->

DroidDS pins its upstream Git components to full commits. The 0.0.5 Android
runtime probe adds maintained copies of Zakuro core, filesystem and GPU code to
the previously selected CPU/common and ABI components. It also maintains the host
3dsrecomp compiler to fix a measured backward-loop discovery error. These copies
live under `vendor/zakuro` and `vendor/3dsrecomp`; each `UPSTREAM.json` records the
original file hashes, and adjacent
`CodexAstraUlt` comments identify integration changes. The desktop frontend is not
included. The original Java/JNI/Rust shell and graphics fixtures remain DroidDS
code. Vulkan declarations and offline shader tools come from the pinned Android
NDK. The owner authorizes downloadable diagnostic prereleases.

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

<!-- CodexAstraUlt: A measured native loop accounting defect needs a narrow local
compiler correction; preserve its original license declaration independently. -->
In 0.0.5, `vendor/3dsrecomp` holds the maintained host compiler sources. Its
`UPSTREAM-Cargo.toml` preserves the exact original manifest, while `UPSTREAM.json`
records the selected revision and original source/manifest hashes. The collector
checks this provenance and includes the original manifest verbatim. Integration
comments identify the local backward-loop discovery correction. `recomp-abi`
remains the exact Git dependency; no duplicate ABI or compiler executable is
shipped in the APK. Generated support code remains covered by the upstream MIT
declaration and included terms.

This resolves the earlier self-imposed blanket hold for the current probe. Future
dependency revisions must be reviewed again; if upstream supplies a copyright or
notice file later, retain it. `recomp-abi` links into the probe. `recomp3ds` runs on
the build host and emits support code for the original synthetic fixtures; its
host executable is not bundled into the APK.

## Zakuro

<!-- CodexAstraUlt: Preserve the exact notice supplied in the pinned Zakuro root LICENSE; it applies to the selected CPU/common components without asserting provenance for unrelated projects. -->

Source: <https://github.com/fearkov/zakuro>

Selected commit: `412900a5a020301da15c1cc382585e05a489a535`.

Selected components: `zakuro-cpu` and `zakuro-common` 0.2.27 remain exact Git
dependencies. The 0.0.5 integration also maintains `zakuro-core`, `zakuro-fs` and
`zakuro-gpu` 0.2.27 under `vendor/zakuro`. All five declare MIT. Vendored code,
GLSL and prebuilt SPIR-V retain their upstream origin; these are emulator sources
and shaders, not Nintendo game content. The original root `LICENSE` is preserved
at `vendor/zakuro/LICENSE` and emitted once for all five components. Its exact text:


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

The selected 0.0.5 workspace metadata resolves **155 registry package versions**.
The complete reviewed inventory is
[`tools/android_registry_notices.json`](tools/android_registry_notices.json),
including each package's exact version, declared license, archive checksum,
supplied notice paths and hashes, and additional inline-attribution source hashes.
Multiple versions of a package are separate records. `Cargo.lock` also contains
optional dependencies that are disabled; enabling one changes the metadata graph
and requires a notice review before packaging.

<!-- CodexAstraUlt: The larger runtime introduces compound and file-specific
notices; preserve their supplied terms rather than treating metadata as a license. -->
The collection includes MIT/Apache alternatives, BSD, ISC, Zlib, Unicode terms,
Unlicense alternatives and Mozilla Public License 2.0 components. It preserves
all supplied license/notice files in the reviewed sources, including
`cfg_aliases/NOTICES.md`, the Unicode data license in `regex-syntax`, and
`unicode-ident`'s explicit `(MIT OR Apache-2.0) AND Unicode-3.0` conjunction.
Inline copyright/permission comments are retained verbatim where supplied,
including libm's Sun, BSD and Arm attributions. Conservative inclusion of source
and test notices does not mean every associated source file is part of the APK.

Three registry archives need explicit handling:

- `block` 0.1.6 and `malloc_buf` 0.0.6 declare MIT but omit standalone license
  and copyright notices. Their original manifests and standard MIT terms are
  included, clearly labeled as declaration-based terms with no invented holder.
  They enter through Apple-only dependencies and do not link into Android.
- `spirv` 0.4.0+sdk-1.4.341.0 declares Apache-2.0 but omits its license file. Its
  `.cargo_vcs_info.json` identifies upstream commit
  `8afc3d0ac8e158128cd1410bb2e4b4c26ab11bb4`; the original root LICENSE from that
  exact revision is stored in `tools/notices/rspirv-8afc3d0-LICENSE`, with source URL
  and byte hash in the inventory.

`cityhasher` explicitly describes a direct Rust port of Google CityHash v1.1.
The Rust archive's notices are retained, and Google's original MIT attribution
is additionally included from the exact recorded source URL in the inventory.
That supplementary notice does not claim the referenced Google commit generated
the Rust crate. No copyright line is inferred from author metadata.

<!-- CodexAstraUlt: Identify the actual MPL-covered sources and a usable source
retrieval path for binary recipients, without relicensing unrelated DroidDS files. -->
Symphonia's AAC/core/common/metadata 0.6.1 crates are used without modifications
under **MPL-2.0**. Their complete original LICENSE files and inline attribution
are included. The generated notices tell recipients that the complete unmodified
Source Code Form is available at each exact, free crates.io archive URL, with the
Cargo checksum. For example:
<https://static.crates.io/crates/symphonia-core/symphonia-core-0.6.1.crate>.
These source archives contain the covered files and their notices. Any future
modification to those covered files must also preserve source availability; this
record does not apply MPL to unrelated original DroidDS code.

## Android distribution bundle

<!-- CodexAstraUlt: Include supplied runtime/toolchain notices in addition to
Cargo declarations, and distinguish conservative attribution from actual linkage. -->

A registry checksum is an integrity identifier, not a license. The supplied
license/notice files listed above are collected verbatim. The collector deliberately
includes all **162 third-party records** in the selected cross-platform workspace
metadata: 155 registry versions, three Git packages, three maintained Zakuro
crates and the maintained host compiler. Host-only, other-target and procedural-macro records are included. This keeps all supplied
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
The Android device supplies its Vulkan loader/driver. The original offscreen probe and its GLSL fixtures remain DroidDS code. Version
0.0.5 also integrates Zakuro's renderer implementation and shaders, covered by
the preserved Zakuro MIT notice. Cranelift GPU JIT and the desktop frontend are
not enabled in the Android runtime probe. The Android build does not enable or require validation layers.
The notice collector also preserves the actual copyright/SPDX comment blocks
from the three included Vulkan core/platform headers and seven transitive video
declaration headers, with full-header hashes. Those declarations add no video
feature; their bodies are not copied into the notice bundle. Full Apache-2.0 terms
are already retained from the supplied registry license files.

The collector fails before packaging if a required supplied file is missing or
empty or modified, the reviewed package identities/license expressions or archive
checksums change, upstream Git pins or vendor origins differ, or Rust/NDK versions
differ. Regression tests cover these gates, simultaneous package versions, MPL
source identification, exact inline-attribution retention, and the Unicode
license conjunction.

This record does not relicense upstream source or select a license for original
DroidDS code. No Nintendo game content or private title-derived code is included.
Any further component or Uberhar/Azahar/MMJ/AnyPS5 reuse needs its own actual-source
license review and notice update.
