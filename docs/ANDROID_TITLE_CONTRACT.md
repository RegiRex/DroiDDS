# Android title candidate implementation contract

<!-- CodexAstraUlt: Implement the missing Android product path in parallel with
private diagnosis. This contract defines interfaces, not completed qualification. -->
The owner requests that cloud development continue before another isolated local
handoff. The next candidate uses a separate per-title app with the existing
loader/HLE/PICA runtime, installer-owned ARM64 native code, app-private matching
input and durable saves. Public tests and APKs contain only authored inputs.
The existing probe and its regression inventory remain separate.

## Package manifest

<!-- CodexAstraUlt: One small immutable package asset binds all admitted bytes;
provider filenames and program IDs alone never authorize native execution. -->
Asset `title-manifest.json` is JSON, at most 1 MiB, with these fields:

```json
{
  "schema_version": 1,
  "kind": "droidds_android_title",
  "program_id": "000400000ff3ff00",
  "input": {"bytes": 1, "sha256": "64 lowercase hex characters"},
  "native": {"file": "libdroidds_title.so", "bytes": 1, "sha256": "64 lowercase hex characters"},
  "abi": 4,
  "generation": 3,
  "prepared": {
    "container": "ncch",
    "ncch_format_version": 2,
    "remaster_version": 0,
    "cia_title_version": null,
    "bss_size": 0,
    "segments": [],
    "components": []
  }
}
```

The sample values are placeholders, not an accepted title. `segments` uses the
preparation manifest's text/rodata/data objects (name, address, offset, size,
mapped_bytes, sha256, hash_scope). `components` uses its component records
(kind, path, source_path where present, bytes, sha256), without runtime offsets
or filesystem paths. The runtime hashes the actual input, decompressed code,
headers and raw modules, validates layout/model/revision, then checks mapped text
and native origins. The library filename is fixed, and only the Android
installer's native directory supplies it. No picker-selected library is loaded.

## Runtime and FFI

<!-- CodexAstraUlt: A bounded slice yields rather than treating slow but
progressing startup as a fatal frame-budget error. -->
New `droidds-title-runtime` owns a thread-confined `Session`. Its interface is:

```rust,ignore
pub struct OpenOptions<'a> {
    pub manifest_json: &'a [u8],
    pub input: &'a std::path::Path,
    pub native_directory: &'a std::path::Path,
    pub data_directory: &'a std::path::Path,
    pub native: bool,
    pub hardware: bool,
}
Session::open(OpenOptions) -> Result<Session, String>;
Session::slice(&mut self, input: InputState) -> Result<Slice, String>;
Session::pause(&mut self);
Session::resume(&mut self);
Session::report(&self) -> serde_json::Value;
```

`InputState` is the existing HID type. `Slice` contains `top`/`bottom` optional
RGBA buffers, `pcm: Vec<[i16;2]>`, cumulative `frames`/`cycles`, and `exited`.
No completed frame means a cooperative yield, not invented pixels or failure.
Bound each slice by guest dispatch/cycle and wall work; drain PCM each slice.
Native execution uses immutable base text and interpreted modules. Explicitly
port the existing page-aligned fence to Android 4 KiB; reject unsupported native
page sizes. Vulkan must activate explicitly and its fallback/error counts remain
visible. The interpreter route is an explicit diagnostic choice.

`droidds-title-player` is a separate cdylib/FFI wrapper. Export thread-owned token
operations open, slice, pause, resume, report, close and free. C/JNI will share
`android/title/jni/title_api.h`; JNI arrays and metrics have explicit capacities.
Use `TitleNative` in Java package `org.droidds.probe` to reuse existing plain Java
screen/audio helpers without copying them. The installed application ID remains
`org.droidds.title.t<program_id>`; it does not replace the probe application.

## Import, frontend and persistence

<!-- CodexAstraUlt: Keep imported inputs, runtime saves and diagnostic reports
separate, with atomic publication and no cleanup of uncertain prior content. -->
SAF import copies into a unique staging file under `files/imports/`, incrementally
hashes and verifies the exact expected length, checks available space, supports
cancellation and deletes only its own incomplete staging file. Publish the
validated copy atomically as `files/imports/<input-sha256>.bin`; reject or verify
an existing destination without truncating it. Recheck at runtime admission.
Never install from or execute the mutable provider stream.

Runtime storage is `files/runtime/`, separate from imports and disposable files.
Do not clear saves on import, open, failure, stop or upgrade. Keep one bounded
`files/latest-title-report.json`, written atomically on stop/error, with export.
Frontend supplies stacked screens, touch, buttons, Circle Pad/C-stick, audio,
pause/resume/stop, and explicit native/interpreter route selection. Slow startup
remains cancellable between bounded native slices. Physical dual-display support
and direct Vulkan presentation remain outside this candidate.

## Build and qualification

<!-- CodexAstraUlt: Reuse prepared C while binding a distinct Bionic target;
the owner's completed x86-64 library remains untouched and cannot run on Thor. -->
Separate Android compilation tooling consumes the existing preparation manifest
and sources, using NDK 27.3.13750724, ARM64/API29, the existing floating-point
contract, bounded resumable jobs and identity receipts. Do not modify the six
historical host compilation-contract helpers. Package the new player runtime,
JNI bridge and exactly one audited title library, with a separate inventory,
16 KiB ELF/ZIP alignment, manifest asset and required notices.

A stable per-title package and an explicitly selected owner-local signing profile
permit upgrades without clearing data. Public original-fixture candidates use a
separate diagnostic identity. Record only public certificate fingerprints.
No private sources, game data, native artifacts or signing secrets go to CI.

The first cloud gate is the actual generic session/import/package path exercised
with original inputs, host pixel/audio/control oracles, malformed identity and
cancel/restart/preservation tests, ARM64 cross-build and package audits. Device
execution, private boot, save retention across actual installation, sustained
playability and Thor performance remain separate unperformed gates. A candidate
version is not completion of the roadmap's 0.0.7 owned-game boot milestone.
