# Automatic encrypted-title import

<!-- CodexAstraUlt: Record the owner's request for automatic decryption as an
import feature, with a concrete design and gates separate from native boot. -->
Status: planned; encrypted-title import is not implemented. DroiDDS currently
requires a decrypted base image. Automatic import can remove the owner's manual
decryption step when the required keys and title-specific seeds are available.
It does not remove those cryptographic requirements or establish game compatibility.
The existing Dark Moon preparation and compilation do not need to be repeated.

## Reference and current boundary

<!-- CodexAstraUlt: Pin inspected reference code without importing its source,
key material, or licensing assumptions into this project's implementation. -->
Source inspection of the AzaharPlus tree at
[`6c7f6baa15122ab0758d5cdf15c4271ddaffafae`](https://github.com/3sadas/azaharplus/tree/6c7f6baa15122ab0758d5cdf15c4271ddaffafae)
confirms NCCH decryption and explicit missing-key errors in
[`ncch_container.cpp`](https://github.com/3sadas/azaharplus/blob/6c7f6baa15122ab0758d5cdf15c4271ddaffafae/src/core/file_sys/ncch_container.cpp).
Its [`key.cpp`](https://github.com/3sadas/azaharplus/blob/6c7f6baa15122ab0758d5cdf15c4271ddaffafae/src/core/hw/aes/key.cpp)
loads key configuration and boot-ROM material. These files carry GPL-2.0-or-later
notices. This is a source review, not a tested AzaharPlus binary or a complete
license/dependency audit. No code, keys, boot ROM, or other system data was copied.
Any direct reuse requires the component review described in
[the reuse policy](REUSE_CANDIDATES.md) and [third-party notices](../THIRD_PARTY_NOTICES.md).

DroiDDS's compiler (`vendor/3dsrecomp/src/rom.rs`) and runtime
(`vendor/zakuro/crates/zakuro-fs/src/lib.rs`) both read plaintext containers.
Neither currently provides the necessary decryption layer. Supporting a `.3ds`
extension alone does not establish support for encrypted content inside it.
NCCH crypto method zero is the original encryption method; only the no-crypto
flag declares plaintext. Fixed-key encryption, including a zero-valued AES key,
still requires decryption. Encrypted inputs must fail before executable parsing
until a validated import stage is available.

<!-- CodexAstraUlt: Keep strict header admission distinct from detecting or
repairing a third-party image that was decrypted without updating its flags. -->
Externally decrypted images whose headers still declare encryption also reject;
the loaders do not guess that arbitrary payload bytes are already plaintext or
repair headers in place. No private Dark Moon header was available in this review.
The retained preparation and current compilation use their recorded input/tool
identities and do not require regeneration for this declaration check.

<!-- CodexAstraUlt: Record the implemented admission correction separately from
the future decryptor and report executed original-fixture evidence precisely. -->
The method-zero exceptions have been removed from compiler loading, runtime
title/update loading, and DLC RomFS access. Six new tests exercise declarations
on original plaintext fixtures: three rejection tests fail before the correction
and pass afterward, and three no-crypto precedence controls continue passing.
These are admission tests, not AES tests. Using pinned Rust 1.95.0, these commands
pass **145 non-overlapping tests** with no skips:

```bash
cargo test --offline --locked -p recomp3ds --lib -- --test-threads=1
cargo test --offline --locked -p zakuro-fs -p droidds-title-builder -p droidds-title-tools -- --test-threads=1
```

Counts are compiler 85, filesystem 28, builder 13, and title tools 19. An initial
combined compiler/filesystem package selection failed before executing tests;
the separate compiler command above resolves the intended dependency package.
This correction adds no cryptographic dependency, changes no APK version, and
does not establish encrypted-game support or private-title compatibility.

## Shared import design

<!-- CodexAstraUlt: Keep cryptography outside emulation and preserve the existing
compiler/runtime identity contract through one normalized immutable input. -->
1. Inspect the container and selected executable using bounded metadata reads.
   Detect encryption separately for the CIA content layer and each relevant NCCH
   region; preserve the current base-title, format, size, and module restrictions.
2. Resolve an explicitly configured local key provider and, where required, a
   title seed. Report missing material by category without printing secret values.
   Do not silently search unrelated directories or download keys/system files.
3. Use a reviewed cryptographic library for NCCH AES-CTR and CIA content AES-CBC.
   Treat method/key selection, seed derivation, region-specific keys/counters,
   byte order, padding, and random-access offsets as separate tested operations.
   Handle fixed-key variants explicitly; reject unsupported variants precisely.
4. Write a bounded temporary decrypted snapshot, leaving the original untouched.
   Verify the applicable original content and region hashes before admission;
   never replace an expected hash with a computed value just to accept a result.
   Preserve original metadata needed to establish how normalization changed flags
   or headers. Hash agreement alone does not establish a valid Nintendo signature.
5. Atomically admit the immutable snapshot and feed those same bytes to both the
   compiler and runtime. Preserve their independent executable, exheader, segment,
   RomFS, and module agreement checks. Avoid separate compiler/runtime decryptors.
6. Bind the original encrypted input, normalized plaintext, normalizer version,
   and verification results in the preparation contract. Extend runtime manifest
   consumption before claiming encrypted input can safely select a native library.
   Never put key values or reversible encodings of them in manifests or reports.

The normalized snapshot should serve the existing private snapshot role.
Account for temporary coexistence of original and decoded data, but do not create
another permanent full-title cache or decrypt during frame processing. Import
needs space checks, bounded memory/logging, cancellation, and atomic failure
handling. Decrypted inputs retain the existing direct preparation route.

## Implementation gates

<!-- CodexAstraUlt: Require original encrypted fixtures and negative controls
before claiming that private encrypted games are supported. -->
- Select the library/key-provider interface and review any reused source/license.
- Encrypt original NCCH/NCSD/CIA fixtures using test-only keys; test both layers
  separately and together, including content indexes and mixed encryption states.
- Cover original and newer NCCH methods, fixed-key and seed cases, region and
  counter/block boundaries, and explicit no-crypto precedence.
- Reject missing/wrong keys or seeds, corrupt hashes, unsupported methods,
  truncated/overlapping regions, excessive sizes, and interrupted imports without
  publishing a successful manifest or overwriting prior data.
- Require decoded-byte equality and identical compiler/runtime interpretation
  against each fixture's known plaintext. Test that diagnostics contain no keys.
- Qualify one owner-provided encrypted title against its matching decrypted
  revision, then separately qualify Android import and native-library binding.

This is DDS-017, an import usability task. It is not a prerequisite for the current
decrypted Dark Moon build and does not fix its CPU, renderer, or audio behavior.
Full encrypted-title support must remain unclaimed until these gates execute.
