//! CodexAstraUlt: Original strict-admission fixtures exercise real NCCH,
//! RomFS and CRO parsing rather than mocking the resolver's output.

use super::*;
use crate::{cro::tests::named, rom::tests::rom};

// CodexAstraUlt: Each independent fixture owns only its newly created file;
// cleanup never reaches a user's title or another test's output.
struct Fixture(std::path::PathBuf);
impl Fixture {
    fn new(name: &str, files: &[(&str, &[u8])]) -> Self {
        Self(rom(name, &[0x1E, 0xFF, 0x2F, 0xE1], files))
    }

    fn mutate(&self, change: impl FnOnce(&mut Vec<u8>)) {
        let mut bytes = std::fs::read(&self.0).unwrap();
        change(&mut bytes);
        std::fs::write(&self.0, bytes).unwrap();
    }

    fn rejected(&self, expected: &str) {
        let error = match resolve(&self.0) {
            Ok(_) => panic!("malformed original fixture was accepted"),
            Err(error) => error,
        };
        assert!(error.to_string().contains(expected), "{error}");
    }
}
impl Drop for Fixture {
    fn drop(&mut self) {
        std::fs::remove_file(&self.0).unwrap();
    }
}

// CodexAstraUlt: Mutations identify table offsets from the independently
// constructed fixture layout, not by invoking the strict traversal under test.
fn word(bytes: &[u8], offset: usize) -> u32 {
    u32::from_le_bytes(bytes[offset..offset + 4].try_into().unwrap())
}
fn put(bytes: &mut [u8], offset: usize, value: u32) {
    bytes[offset..offset + 4].copy_from_slice(&value.to_le_bytes());
}
fn tables(bytes: &[u8]) -> (usize, usize, usize) {
    let romfs = word(bytes, 0x1B0) as usize * 0x200;
    let level3 = romfs + 0x60;
    (
        romfs,
        level3 + word(bytes, level3 + 0x0C) as usize,
        level3 + word(bytes, level3 + 0x1C) as usize,
    )
}

// CodexAstraUlt: A fixture without optional modules remains executable-only,
// retaining exact source bytes instead of only the discovery Program.text.
#[test]
fn original_executable_preserves_exact_resolved_inputs() {
    let fixture = Fixture::new("strict-executable", &[]);
    let resolved = resolve(&fixture.0).unwrap();
    assert_eq!(resolved.programs.len(), 1);
    assert_eq!(resolved.programs[0].0, "executable");
    assert_eq!(resolved.programs[0].1.text.bytes, [0x1E, 0xFF, 0x2F, 0xE1]);
    assert_eq!(resolved.code, resolved.programs[0].1.text.bytes);
    assert_eq!(resolved.exheader_bytes.len(), 0x400);
    assert_eq!(resolved.ncch_header.len(), 0x200);
    assert_eq!(&resolved.ncch_header[0x100..0x104], b"NCCH");
    assert!(resolved.modules.is_empty());
}

// CodexAstraUlt: Source paths, raw bytes and static metadata survive a complete
// nested traversal, with deterministic code-unit order independent of insertion.
#[test]
fn original_modules_are_complete_sorted_and_bound_to_sources() {
    let (z, a, crs) = (
        named("Zed", &[0xE12F_FF1E]),
        named("Alpha", &[0xE12F_FF1E]),
        named("|static|", &[]),
    );
    let fixture = Fixture::new(
        "strict-modules",
        &[("z/Zed.cro", &z), ("a/Alpha.cro", &a), ("static.crs", &crs)],
    );
    let resolved = resolve(&fixture.0).unwrap();
    assert_eq!(
        resolved
            .programs
            .iter()
            .map(|(name, _)| name.as_str())
            .collect::<Vec<_>>(),
        ["executable", "Alpha", "Zed"]
    );
    assert_eq!(
        resolved
            .modules
            .iter()
            .map(|module| module.path.as_str())
            .collect::<Vec<_>>(),
        ["a/Alpha.cro", "static.crs", "z/Zed.cro"]
    );
    assert_eq!(resolved.modules[0].bytes, a);
    assert_eq!(resolved.modules[1].bytes, crs);
    assert!(resolved.modules[1].is_static);
    assert!(!resolved.modules[2].is_static);
    assert_eq!(resolved.modules[2].bytes, z);
}

// CodexAstraUlt: A failed CRO or static descriptor must be a visible error,
// while legacy discovery retains its original permissive compatibility behavior.
#[test]
fn malformed_declared_cro_and_static_descriptor_are_rejected() {
    for (name, path) in [
        ("strict-bad-cro", "bad.cro"),
        ("strict-bad-crs", "static.crs"),
    ] {
        let fixture = Fixture::new(name, &[(path, b"not a module")]);
        fixture.rejected("cannot parse the declared module");
        let legacy = Title::load(&fixture.0).unwrap();
        assert_eq!(
            crate::programs(&legacy, crate::Mods::default())
                .unwrap()
                .len(),
            1
        );
    }
}

// CodexAstraUlt: Distinct paths do not make duplicate compiler identities safe,
// and a CRO may not collide with the main executable's reserved code-unit name.
#[test]
fn duplicate_or_reserved_module_names_are_rejected() {
    let same = named("Same", &[0xE12F_FF1E]);
    let fixture = Fixture::new(
        "strict-duplicate-module",
        &[("a.cro", &same), ("b.cro", &same)],
    );
    fixture.rejected("module names must be unique");
    let executable = named("executable", &[0xE12F_FF1E]);
    let fixture = Fixture::new("strict-reserved-module", &[("main.cro", &executable)]);
    fixture.rejected("module names must be unique");
}

// CodexAstraUlt: Names interpolated into generated C must not introduce quoted
// strings, escapes, control bytes or compiler trigraphs.
#[test]
fn unsafe_module_names_are_rejected_before_codegen() {
    for (index, name) in ["bad\"name", "bad\\name", "bad??/name", "bad\nname", ""]
        .iter()
        .enumerate()
    {
        let module = named(name, &[0xE12F_FF1E]);
        let fixture = Fixture::new(&format!("strict-name-{index}"), &[("bad.cro", &module)]);
        fixture.rejected("module name is unsafe or empty");
    }
}

// CodexAstraUlt: A malformed declared filesystem is not equivalent to no
// optional filesystem; otherwise every contained module would disappear.
#[test]
fn malformed_declared_romfs_is_not_silently_absent() {
    let fixture = Fixture::new("strict-bad-romfs", &[("plain.dat", &[1])]);
    fixture.mutate(|bytes| {
        let (romfs, _, _) = tables(bytes);
        bytes[romfs] = b'X';
    });
    fixture.rejected("no IVFC header");
    assert!(Title::load(&fixture.0).unwrap().romfs.is_none());
}

// CodexAstraUlt: Cyclic links terminate with an error; successful ordinary
// file traversal cannot hide a corrupt chain just because it contains no CRO.
#[test]
fn cyclic_file_and_directory_links_are_rejected() {
    let fixture = Fixture::new("strict-file-cycle", &[("plain.dat", &[1])]);
    fixture.mutate(|bytes| {
        let (_, _, files) = tables(bytes);
        put(bytes, files + 4, 0);
    });
    fixture.rejected("repeats a file link");
    let fixture = Fixture::new("strict-directory-cycle", &[("child/plain.dat", &[1])]);
    fixture.mutate(|bytes| {
        let (_, dirs, _) = tables(bytes);
        let child = word(bytes, dirs + 8);
        put(bytes, dirs + child as usize + 4, child);
    });
    fixture.rejected("repeats a directory link");
}

// CodexAstraUlt: A dangling linked entry is an error rather than a truncated
// enumeration, and paths that collapse under the reader's case rules collide.
#[test]
fn dangling_entries_and_duplicate_paths_are_rejected() {
    let fixture = Fixture::new("strict-dangling", &[("plain.dat", &[1])]);
    fixture.mutate(|bytes| {
        let (_, dirs, _) = tables(bytes);
        put(bytes, dirs + 0x0C, 0x7FFF_FFFC);
    });
    fixture.rejected("outside its table");
    let fixture = Fixture::new(
        "strict-path-duplicate",
        &[("same.dat", &[1]), ("SAME.dat", &[2])],
    );
    fixture.rejected("duplicate sibling paths");
}

// CodexAstraUlt: A missing executable file and a shortened logical segment
// cannot become an empty discovery program and appear to prepare successfully.
#[test]
fn missing_code_and_truncated_segment_are_rejected() {
    let fixture = Fixture::new("strict-missing-code", &[]);
    fixture.mutate(|bytes| bytes[0x600..0x608].fill(0));
    fixture.rejected("ExeFS has no .code");
    let fixture = Fixture::new("strict-truncated-segment", &[]);
    fixture.mutate(|bytes| put(bytes, 0x218, 8));
    fixture.rejected("segment is truncated");
}

// CodexAstraUlt: Guest map arithmetic and source slices are validated before
// permissive helpers can wrap addresses or silently drop logical segment bytes.
#[test]
fn invalid_segment_pages_addresses_and_zero_length_backing_are_rejected() {
    let fixture = Fixture::new("strict-zero-pages", &[]);
    fixture.mutate(|bytes| put(bytes, 0x214, 0));
    fixture.rejected("exceeds mapped pages");
    let fixture = Fixture::new("strict-address-wrap", &[]);
    fixture.mutate(|bytes| put(bytes, 0x210, 0xFFFF_F000));
    fixture.rejected("mapping is invalid");
    let fixture = Fixture::new("strict-empty-backed-segment", &[]);
    fixture.mutate(|bytes| {
        put(bytes, 0x220, 0x0020_0000);
        put(bytes, 0x224, 1);
    });
    fixture.rejected("segment is truncated");
}

// CodexAstraUlt: A module code extent outside the raw file is rejected instead
// of being omitted by Module::program's Option-returning legacy interface.
#[test]
fn missing_module_code_extent_is_rejected() {
    let mut module = named("Bad", &[0xE12F_FF1E]);
    put(&mut module, 0x138, 0xFFFF_FF00);
    let fixture = Fixture::new("strict-module-extent", &[("bad.cro", &module)]);
    fixture.rejected("segment is outside its payload");
}

// CodexAstraUlt: A parsed CRO with no nonempty code is an explicit unsupported
// preparation case, not an invisible omission from the module inventory.
#[test]
fn module_without_compilable_code_is_explicitly_rejected() {
    let module = named("DataOnly", &[]);
    let fixture = Fixture::new("strict-data-module", &[("data.cro", &module)]);
    fixture.rejected("no supported compilable code segment");
}

// CodexAstraUlt: Declared module reads have checked arithmetic and independent
// byte admission; a short or overflowing file extent cannot return partial data.
#[test]
fn unreadable_and_oversized_module_payloads_are_rejected() {
    let module = named("Valid", &[0xE12F_FF1E]);
    let fixture = Fixture::new("strict-unreadable-module", &[("bad.cro", &module)]);
    fixture.mutate(|bytes| {
        let (_, _, files) = tables(bytes);
        bytes[files + 8..files + 16].copy_from_slice(&u64::MAX.to_le_bytes());
    });
    fixture.rejected("cannot read the declared module");
    let fixture = Fixture::new("strict-huge-module", &[("bad.cro", &module)]);
    fixture.mutate(|bytes| {
        let (_, _, files) = tables(bytes);
        bytes[files + 16..files + 24].copy_from_slice(&(MAX_MODULE_BYTES as u64 + 1).to_le_bytes());
    });
    fixture.rejected("payload exceeds the limit");
}

// CodexAstraUlt: Compression admission checks the footer before allocating the
// requested output; the container's small input does not imply small output.
#[test]
fn oversized_decompression_is_rejected_before_allocation() {
    let fixture = Fixture::new("strict-decompression", &[]);
    fixture.mutate(|bytes| {
        bytes[0x20D] = 1;
        put(bytes, 0x800, u32::MAX);
    });
    fixture.rejected("decompressed code exceeds the allocation limit");
}

// CodexAstraUlt: Update/DLC rejection is based on the title identity even when
// the executable is presented as bare NCCH rather than in a CIA wrapper.
#[test]
fn bare_update_and_dlc_identities_are_rejected() {
    for (index, high) in [0x0004_000Eu64, 0x0004_008C].iter().enumerate() {
        let fixture = Fixture::new(&format!("strict-base-only-{index}"), &[]);
        fixture.mutate(|bytes| bytes[0x118..0x120].copy_from_slice(&(high << 32).to_le_bytes()));
        fixture.rejected("accepts base titles");
    }
}

// CodexAstraUlt: An undersized TMD must return an error before field decoding,
// so corrupt CIA input is not accepted or converted into a parser panic.
#[test]
fn truncated_cia_tmd_is_rejected_without_panic() {
    let fixture = Fixture::new("strict-cia-tmd", &[]);
    fixture.mutate(|bytes| {
        bytes.resize(0x2041, 0);
        bytes[..0x200].fill(0);
        put(bytes, 0, 0x2020);
        put(bytes, 0x10, 1);
    });
    fixture.rejected("TMD is truncated");
}

// CodexAstraUlt: One CRO can declare more code than the current extractor
// returns. Treat that as an unsupported preparation shape, never partial code.
#[test]
fn multiple_nonempty_module_code_segments_are_explicitly_rejected() {
    let mut module = named("TwoCode", &[0xE12F_FF1E]);
    module.extend_from_slice(&0xE12F_FF1Eu32.to_le_bytes());
    put(&mut module, 0xCC, 2);
    put(&mut module, 0x144, 0x204);
    put(&mut module, 0x148, 4);
    put(&mut module, 0x14C, 0);
    let parsed = cro::parse(&module).unwrap();
    assert_eq!(parsed.program(&module, &[]).unwrap().text.bytes.len(), 4);
    let fixture = Fixture::new("strict-two-code-segments", &[("two.cro", &module)]);
    fixture.rejected("does not support multiple nonempty module code segments");
}

// CodexAstraUlt: Repeated outer records can alias one inner import array and
// multiply its allocated names. Admission counts expanded metadata first.
#[test]
fn aliased_anonymous_import_tables_are_bounded_before_parsing() {
    let mut module = named("Expansion", &[0xE12F_FF1E]);
    let inner = 0x1000;
    let count = 100_000;
    module.resize(inner + count * 8, 0);
    module[0x300..0x300 + 255].fill(b'X');
    put(&mut module, 0xF0, 0x500);
    put(&mut module, 0xF4, 3);
    for i in 0..3 {
        let at = 0x500 + i * 20;
        put(&mut module, at, 0x300);
        put(&mut module, at + 12, inner as u32);
        put(&mut module, at + 16, count as u32);
    }
    let fixture = Fixture::new("strict-import-expansion", &[("expanded.cro", &module)]);
    fixture.rejected("expanded metadata exceeds its limit");
}

// CodexAstraUlt: Data below text is valid until its effective BSS extension
// overwrites text. Check that extra mapping in the same overlap admission.
#[test]
fn effective_bss_extension_cannot_overlap_another_segment() {
    let fixture = Fixture::new("strict-bss-overlap", &[]);
    fixture.mutate(|bytes| {
        bytes.resize(0x800 + 0x1004, 0);
        put(bytes, 0x60C, 0x1004);
        put(bytes, 0x210, 0x0020_0000);
        put(bytes, 0x230, 0x0010_0000);
        put(bytes, 0x234, 1);
        put(bytes, 0x238, 4);
        put(bytes, 0x23C, 0x0010_1000);
    });
    fixture.rejected("segment mappings overlap");
    // A smaller BSS stops before text and preserves the same legal code image.
    fixture.mutate(|bytes| put(bytes, 0x23C, 0x2000));
    assert!(resolve(&fixture.0).is_ok());
}

// CodexAstraUlt: Absent data does not map its unused address, while a positive
// BSS tail at the same unaligned address is an explicitly unsupported layout.
#[test]
fn absent_data_does_not_invent_an_unaligned_bss_extension() {
    let fixture = Fixture::new("strict-unused-data-address", &[]);
    for address in [0x0010_0001, u32::MAX] {
        fixture.mutate(|bytes| put(bytes, 0x230, address));
        assert!(resolve(&fixture.0).is_ok());
    }
    fixture.mutate(|bytes| {
        put(bytes, 0x230, 0x0010_0001);
        put(bytes, 0x23C, 1);
    });
    fixture.rejected("BSS extension is unaligned");
}

// CodexAstraUlt: A complete backwards stream preserves its four-byte original
// prefix and fills every byte of the declared expansion through real tokens.
#[test]
fn valid_compressed_code_preserves_prefix_and_complete_output() {
    let compressed = [
        0x1E, 0xFF, 0x2F, 0xE1, 0, 0x40, 0, 0xF0, 0, 0, 0, 0x18, 0x10, 0, 0, 8, 12, 0, 0, 0,
    ];
    let fixture = Fixture::new("strict-valid-compressed", &[]);
    fixture.mutate(|bytes| {
        bytes.truncate(0x800);
        bytes.extend_from_slice(&compressed);
        bytes[0x20D] = 1;
        put(bytes, 0x218, 32);
        put(bytes, 0x60C, compressed.len() as u32);
    });
    let resolved = resolve(&fixture.0).unwrap();
    let mut expected = vec![0; 32];
    expected[..4].copy_from_slice(&compressed[..4]);
    assert_eq!(resolved.code, expected);
    assert_eq!(resolved.programs[0].1.text.bytes, expected);
}

// CodexAstraUlt: A footer alone and a cut-short token cannot manufacture the
// zero-filled tail that permissive decoding previously exposed as code bytes.
#[test]
fn incomplete_compressed_streams_are_rejected() {
    for (name, compressed, output, expected) in [
        (
            "strict-footer-only",
            vec![8, 0, 0, 8, 4, 0, 0, 0],
            12,
            "did not complete",
        ),
        (
            "strict-cut-reference",
            vec![0x1E, 0xFF, 0x2F, 0xE1, 0, 0x80, 10, 0, 0, 8, 4, 0, 0, 0],
            18,
            "cut-short back reference",
        ),
        (
            "strict-short-footer",
            vec![0, 0, 0, 0, 4, 0, 0, 0],
            12,
            "invalid footer/span",
        ),
    ] {
        let fixture = Fixture::new(name, &[]);
        fixture.mutate(|bytes| {
            bytes.truncate(0x800);
            bytes.extend_from_slice(&compressed);
            bytes[0x20D] = 1;
            put(bytes, 0x218, output);
            put(bytes, 0x60C, compressed.len() as u32);
        });
        fixture.rejected(expected);
    }
}
