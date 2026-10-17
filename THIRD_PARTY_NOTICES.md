# Third-party source and notice record

<!-- CodexAstraUlt: Record only supplied attribution; distinguish direct source dependencies from copied code and from a complete redistribution notice bundle. -->

DroidDS's first Linux harness obtains its upstream components directly through
full-commit Cargo Git dependencies. This repository does not vendor their source
or distribute the resulting binaries. This is the source/provenance record for
that integration, not a complete notice bundle for a future APK or native binary.
<!-- CodexAstraUlt: The first Android probe adds original integration code and
uses the same registry/upstream dependencies; it is locally built, not released. -->
The 0.0.2 Android CPU probe uses the same pinned ABI/interpreter dependencies.
Its original Java/JNI/Rust shell adds no registry dependency. A local debug APK
can be built for development; public CI audits it without uploading binaries.
The notice gap below remains open before binary redistribution.
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

The complete upstream notice provenance remains unresolved. Resolve it before
distributing compiled artifacts containing this code or copying its implementation
into DroidDS. The first public build workflow publishes original harness source,
configuration and test records rather than binary artifacts.

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

## Distribution follow-up

<!-- CodexAstraUlt: Keep the resolved source inventory distinct from a completed artifact-specific notice bundle and from the missing upstream 3dsrecomp notice. -->

A registry checksum is an integrity identifier, not a license. The supplied
license/notice files must be retained and assembled for a distributed artifact's
target and enabled features. This first source release does not copy registry
implementation or claim that a complete binary notice bundle has been assembled.
The registry inventory does not resolve the separate 3dsrecomp notice gap above.

Compiler runtimes, C support code, target-specific dependencies and any future
Android/GPU/service dependencies must be included when qualifying that artifact.
This record does not relicense upstream source or cover Nintendo game content,
private title-derived code, or future Uberhar/Azahar code reuse.
