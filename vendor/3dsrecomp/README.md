# Selected 3dsrecomp compiler source

<!-- CodexAstraUlt: Document the exact import and the measured reason for its
local patch without inventing upstream authorship or a missing license file. -->

Imported from `https://github.com/fearkov/3dsrecomp` at
`c3f21f94ba50d688025febc8974ff348d471b587`: `src/` and `hints.txt`.
`UPSTREAM.json` records original source hashes. `UPSTREAM-Cargo.toml` preserves
the exact upstream manifest, which declares **MIT**; this revision provides no
standalone license file. See the project's third-party notices for license terms.

The adapted manifest keeps the original package identity, pins the existing
external `recomp-abi`, and pins the optional verification interpreter. This is
a host-only compiler; it is not an additional Android runtime dependency.

Local patch: discovery now starts a new budget block at the fallthrough of a
conditional control transfer. Previously a backward conditional branch could
charge instructions from its exit path on every loop iteration. The original
DroidDS runtime fixture performed 598 interpreted instructions but was charged
1,598 native-path cycles. ARM/Thumb discovery and code-generation regressions
cover the corrected boundaries; the actual native/interpreter runtime fixture
must also agree before publication.

The private title-building and package-template facilities are imported as source
dependencies, not claimed tested or ready by this diagnostic release.
