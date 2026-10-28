//! CodexAstraUlt: Original containers exercise preparation through both parsers
//! and real C compilation. None of these fixtures contain private game material.

use droidds_title_builder::prepare;
use serde_json::{json, Value};
use std::{
    collections::BTreeMap,
    fs,
    path::{Path, PathBuf},
    process::Command,
    sync::atomic::{AtomicUsize, Ordering},
};

const PROGRAM: u64 = 0x0004_0000_0D5D_0070;
const BASE: u32 = 0x0010_0000;

// CodexAstraUlt: Every test owns a uniquely created temporary directory; cleanup
// only removes that directory and never touches an existing fixture or user path.
struct Fixture {
    root: PathBuf,
}

impl Fixture {
    fn new(name: &str) -> Self {
        static NEXT: AtomicUsize = AtomicUsize::new(0);
        let index = NEXT.fetch_add(1, Ordering::Relaxed);
        let root = std::env::temp_dir().join(format!(
            "droidds-preparation-{name}-{}-{index}",
            std::process::id()
        ));
        fs::create_dir(&root).unwrap();
        Self { root }
    }

    fn input(&self, name: &str, bytes: &[u8]) -> PathBuf {
        let path = self.root.join(name);
        fs::write(&path, bytes).unwrap();
        path
    }
}

impl Drop for Fixture {
    fn drop(&mut self) {
        let _ = fs::remove_dir_all(&self.root);
    }
}

// CodexAstraUlt: A returning ARM function makes a small, independently known
// source program whose emitted C must compile with the installed compiler.
fn image() -> Vec<u8> {
    zakuro_fs::testing::ncch(PROGRAM, Some(&0xE12F_FF1Eu32.to_le_bytes()), &[])
}

// CodexAstraUlt: An original CRO contains one code segment and one indexed
// export at offset zero. A static descriptor uses that layout with empty code.
fn module(name: &str, words: &[u32]) -> Vec<u8> {
    let mut bytes = vec![0; 0x200 + words.len() * 4];
    for (offset, value) in [
        (0x80, u32::from_le_bytes(*b"CRO0")),
        (0xC0, 0x180),
        (0xC8, 0x138),
        (0xCC, 1),
        (0x138, 0x200),
        (0x13C, words.len() as u32 * 4),
        (0xD8, 0x150),
        (0xDC, 1),
    ] {
        bytes[offset..offset + 4].copy_from_slice(&value.to_le_bytes());
    }
    bytes[0x180..0x180 + name.len()].copy_from_slice(name.as_bytes());
    for (index, word) in words.iter().enumerate() {
        bytes[0x200 + index * 4..0x204 + index * 4].copy_from_slice(&word.to_le_bytes());
    }
    bytes
}

// CodexAstraUlt: Compare all retained file bytes, including headers and identity
// material, rather than relying on matching counts or implementation hashes.
fn files(root: &Path) -> BTreeMap<String, Vec<u8>> {
    fn visit(root: &Path, path: &Path, found: &mut BTreeMap<String, Vec<u8>>) {
        for entry in fs::read_dir(path).unwrap() {
            let entry = entry.unwrap();
            let path = entry.path();
            if path.is_dir() {
                visit(root, &path, found);
            } else {
                found.insert(
                    path.strip_prefix(root)
                        .unwrap()
                        .to_str()
                        .unwrap()
                        .to_owned(),
                    fs::read(path).unwrap(),
                );
            }
        }
    }
    let mut found = BTreeMap::new();
    visit(root, root, &mut found);
    found
}

// CodexAstraUlt: Repeat the actual preparation independently, then compile a
// separate copy so C-object output cannot mutate the prepared artifact inventory.
#[test]
fn preparation_is_reproducible_and_generated_original_c_compiles() {
    let fixture = Fixture::new("reproducible");
    let bytes = image();
    let input = fixture.input("base.cxi", &bytes);
    let first = fixture.root.join("first");
    let second = fixture.root.join("second");
    let a = prepare(&input, &first).unwrap();
    let b = prepare(&input, &second).unwrap();
    assert_eq!(a, b);
    assert_eq!(files(&first), files(&second));
    assert_eq!(fs::read(&input).unwrap(), bytes);
    assert_eq!(a["status"], "prepared");
    assert_eq!(a["hints"], "disabled");
    assert_eq!(a["overlays"], json!([]));
    assert_eq!(a["abi"], 4);
    assert_eq!(a["generation"], 3);
    assert_eq!(a["runtime_resolution_checked"], true);
    assert_eq!(a["runtime_binding_enforced"], false);

    let compilation = fixture.root.join("compilation");
    fs::create_dir(&compilation).unwrap();
    for artifact in a["artifacts"].as_array().unwrap() {
        let path = Path::new(artifact["path"].as_str().unwrap());
        fs::copy(
            first.join(path),
            compilation.join(path.file_name().unwrap()),
        )
        .unwrap();
    }
    let sources: Vec<String> = a["sources"]
        .as_array()
        .unwrap()
        .iter()
        .map(|source| {
            Path::new(source.as_str().unwrap())
                .file_name()
                .unwrap()
                .to_str()
                .unwrap()
                .to_owned()
        })
        .collect();
    assert!(!sources.is_empty());
    let compiler = recomp3ds::compile::check(None).expect("a C compiler is required, not optional");
    let library = fixture.root.join("liboriginal.so");
    recomp3ds::compile::compile(
        &compiler,
        &compilation,
        &sources,
        &library,
        &|_, _| true,
        false,
    )
    .unwrap();
    assert!(fs::metadata(library).unwrap().len() > 0);
    assert_eq!(files(&first), files(&second));
}

// CodexAstraUlt: Logical sizes, page padding, and each version field have
// independent values, preventing text-only identity or conflated revisions.
#[test]
fn preparation_preserves_full_code_and_distinct_layout_and_revision_fields() {
    let fixture = Fixture::new("layout");
    let mut code = vec![0xA5; 0x3000];
    code[..4].copy_from_slice(&0xE12F_FF1Eu32.to_le_bytes());
    code[0x1000..0x1008].copy_from_slice(&[1, 2, 3, 4, 5, 6, 7, 8]);
    code[0x2000..0x200C].copy_from_slice(&[9; 12]);
    let mut bytes = zakuro_fs::testing::ncch(PROGRAM, Some(&code), &[]);
    for (at, address, size) in [
        (0x210, BASE, 4u32),
        (0x220, BASE + 0x1000, 8),
        (0x230, BASE + 0x2000, 12),
    ] {
        bytes[at..at + 12].copy_from_slice(&[address, 1, size].map(u32::to_le_bytes).concat());
    }
    bytes[0x112..0x114].copy_from_slice(&2u16.to_le_bytes());
    bytes[0x20E..0x210].copy_from_slice(&9u16.to_le_bytes());
    let input = fixture.input("base.cxi", &bytes);
    let output = fixture.root.join("prepared");
    let report = prepare(&input, &output).unwrap();
    assert_eq!(report["container"], "ncch");
    assert_eq!(report["program_id"], format!("{PROGRAM:016x}"));
    assert_eq!(report["ncch_format_version"], 2);
    assert_eq!(report["remaster_version"], 9);
    assert_eq!(report["cia_title_version"], Value::Null);
    assert_eq!(
        report["segments"],
        json!([
            {"name":"text","address":BASE,"offset":0,"size":4,"mapped_bytes":4096},
            {"name":"rodata","address":BASE+4096,"offset":4096,"size":8,"mapped_bytes":4096},
            {"name":"data","address":BASE+8192,"offset":8192,"size":12,"mapped_bytes":4096}
        ])
    );
    assert_eq!(fs::read(output.join("identity/code.bin")).unwrap(), code);
    assert_eq!(
        fs::read(output.join("identity/exheader.bin")).unwrap(),
        bytes[0x200..0x600]
    );
    assert_eq!(
        fs::read(output.join("identity/ncch-header.bin")).unwrap(),
        bytes[..0x200]
    );
}

// CodexAstraUlt: An original BLZ stream retains an ARM return prefix, then uses
// three zero literals and two backwards references to produce 28 zero bytes.
// Both parsers must agree on the complete decompressed image before generation.
#[test]
fn preparation_agrees_on_original_compressed_code_bytes() {
    let fixture = Fixture::new("compressed");
    let compressed = [
        0x1E, 0xFF, 0x2F, 0xE1, // Uncompressed ARM bx lr prefix.
        0x00, 0x40, 0x00, 0xF0, 0x00, 0x00, 0x00, 0x18, // Backward payload/control.
        0x10, 0x00, 0x00, 0x08, // Sixteen-byte span, eight-byte footer.
        0x0C, 0x00, 0x00, 0x00, // Twenty stored bytes expand to thirty-two.
    ];
    let mut bytes = zakuro_fs::testing::ncch(PROGRAM, Some(&compressed), &[]);
    bytes[0x20D] |= 1;
    bytes[0x218..0x21C].copy_from_slice(&32u32.to_le_bytes());
    let mut expected = vec![0; 32];
    expected[..4].copy_from_slice(&0xE12F_FF1Eu32.to_le_bytes());
    let input = fixture.input("base.cxi", &bytes);
    let output = fixture.root.join("prepared");
    let report = prepare(&input, &output).unwrap();
    assert_eq!(report["runtime_resolution_checked"], true);
    assert_eq!(report["segments"][0]["size"], 32);
    assert_eq!(
        fs::read(output.join("identity/code.bin")).unwrap(),
        expected
    );
    assert!(!report["sources"].as_array().unwrap().is_empty());
    assert_eq!(fs::read(input).unwrap(), bytes);
}

// CodexAstraUlt: Both container readers must find the same static descriptor
// and nested CRO bytes. The identity inventory and emitted entry table must
// retain every compilable module, while the static descriptor is not a CRO unit.
#[test]
fn preparation_binds_nested_modules_and_static_descriptor_to_generated_units() {
    let fixture = Fixture::new("modules");
    let first = module("First", &[0xE12F_FF1E]);
    let second = module("Second", &[0xE3A0_002A, 0xE12F_FF1E]);
    let descriptor = module("|static|", &[]);
    let expected = BTreeMap::from([
        ("audio/First.cro", ("First", "cro", first.as_slice())),
        (
            "scene/nested/Second.cro",
            ("Second", "cro", second.as_slice()),
        ),
        (
            "static.crs",
            ("|static|", "static_crs", descriptor.as_slice()),
        ),
    ]);
    let bytes = zakuro_fs::testing::ncch(
        PROGRAM,
        Some(&0xE12F_FF1Eu32.to_le_bytes()),
        &[
            ("scene/nested/Second.cro", &second),
            ("static.crs", &descriptor),
            ("audio/First.cro", &first),
        ],
    );
    let input = fixture.input("base.cxi", &bytes);
    let output = fixture.root.join("prepared");
    let report = prepare(&input, &output).unwrap();
    assert_eq!(report["runtime_resolution_checked"], true);
    let components: Vec<_> = report["components"]
        .as_array()
        .unwrap()
        .iter()
        .filter(|component| component.get("source_path").is_some())
        .collect();
    assert_eq!(components.len(), expected.len());
    for component in components {
        let source = component["source_path"].as_str().unwrap();
        let (name, kind, payload) = expected[source];
        assert_eq!(component["module_name"], name);
        assert_eq!(component["kind"], kind);
        assert_eq!(component["bytes"], payload.len());
        let path = component["path"].as_str().unwrap();
        assert_eq!(fs::read(output.join(path)).unwrap(), payload);
    }
    let entries = fs::read_to_string(output.join("generated/entries.c")).unwrap();
    assert!(entries.contains("recomp_module_count = 2;"));
    assert!(entries.contains("{\"First\", &m001_base"));
    assert!(entries.contains("{\"Second\", &m002_base"));
    assert!(report["sources"]
        .as_array()
        .unwrap()
        .contains(&json!("generated/entries.c")));
    assert!(report["sources"]
        .as_array()
        .unwrap()
        .iter()
        .any(|source| source.as_str().unwrap().starts_with("generated/code")));
    assert_eq!(fs::read(input).unwrap(), bytes);
}

// CodexAstraUlt: Reject damaged inputs before creating a success directory while
// preserving source bytes. Explicitly exercise missing .code and truncation.
#[test]
fn damaged_or_incomplete_input_never_becomes_prepared_output() {
    let fixture = Fixture::new("damaged");
    let mut truncated_code = image();
    truncated_code[0x60C..0x610].copy_from_slice(&0x1000u32.to_le_bytes());
    let mut missing_code = image();
    missing_code[0x600..0x608].fill(0);
    for (index, bytes) in [
        vec![0; 0x800],
        image()[..0x210].to_vec(),
        truncated_code,
        missing_code,
    ]
    .into_iter()
    .enumerate()
    {
        let input = fixture.input(&format!("bad-{index}.cxi"), &bytes);
        let output = fixture.root.join(format!("out-{index}"));
        assert!(prepare(&input, &output).is_err());
        assert!(!output.exists());
        assert_eq!(fs::read(input).unwrap(), bytes);
    }
}

// CodexAstraUlt: CIA package version differs from the executable header fields;
// an archive naming another title must fail even when its NCCH is valid.
#[test]
fn cia_identity_and_versions_are_bound_to_the_executable() {
    let fixture = Fixture::new("cia");
    let mut ncch = image();
    ncch[0x112..0x114].copy_from_slice(&3u16.to_le_bytes());
    ncch[0x20E..0x210].copy_from_slice(&7u16.to_le_bytes());
    let archive = zakuro_fs::testing::cia(PROGRAM, 0x123, &[(0, Some(&ncch))]);
    let input = fixture.input("base.cia", &archive);
    let output = fixture.root.join("prepared");
    let report = prepare(&input, &output).unwrap();
    assert_eq!(report["container"], "cia");
    assert_eq!(report["ncch_format_version"], 3);
    assert_eq!(report["remaster_version"], 7);
    assert_eq!(report["cia_title_version"], 0x123);

    let mismatched = zakuro_fs::testing::cia(PROGRAM + 1, 0x123, &[(0, Some(&ncch))]);
    let input = fixture.input("mismatch.cia", &mismatched);
    let output = fixture.root.join("mismatch");
    assert!(prepare(&input, &output).is_err());
    assert!(!output.exists());
    assert_eq!(fs::read(input).unwrap(), mismatched);
}

// CodexAstraUlt: Cartridge identity comes from NCSD bytes and the selected
// executable partition, not a filename suffix or a bare-NCCH assumption.
#[test]
fn cartridge_preparation_selects_the_executable_partition() {
    let fixture = Fixture::new("cartridge");
    let ncch = image();
    let mut cartridge = vec![0; 0x400];
    cartridge[0x100..0x104].copy_from_slice(b"NCSD");
    cartridge[0x120..0x124].copy_from_slice(&2u32.to_le_bytes());
    cartridge[0x124..0x128].copy_from_slice(&(ncch.len().div_ceil(0x200) as u32).to_le_bytes());
    cartridge.extend_from_slice(&ncch);
    let input = fixture.input("cartridge.cxi", &cartridge);
    let output = fixture.root.join("prepared");
    let report = prepare(&input, &output).unwrap();
    assert_eq!(report["container"], "ncsd");
    assert_eq!(report["program_id"], format!("{PROGRAM:016x}"));
    assert_eq!(report["cia_title_version"], Value::Null);
    assert_eq!(
        fs::read(output.join("identity/ncch-header.bin")).unwrap(),
        ncch[..0x200]
    );
    assert_eq!(fs::read(input).unwrap(), cartridge);
}

// CodexAstraUlt: Reject both container-level update/DLC identities and bare
// executable variants; changing the filename cannot promote them to base titles.
#[test]
fn update_and_dlc_inputs_are_rejected_in_bare_and_archive_forms() {
    let fixture = Fixture::new("overlays");
    for (kind, high) in [("update", 0x0004_000Eu64), ("dlc", 0x0004_008C)] {
        let id = (high << 32) | (PROGRAM & 0xFFFF_FFFF);
        let bare = zakuro_fs::testing::ncch(id, Some(&0xE12F_FF1Eu32.to_le_bytes()), &[]);
        let cia = zakuro_fs::testing::cia(id, 1, &[(0, Some(&image()))]);
        for (form, bytes) in [("bare", bare), ("cia", cia)] {
            let input = fixture.input(&format!("{kind}-{form}.cxi"), &bytes);
            let output = fixture.root.join(format!("{kind}-{form}"));
            assert!(prepare(&input, &output).is_err());
            assert!(!output.exists());
            assert_eq!(fs::read(input).unwrap(), bytes);
        }
    }
}

// CodexAstraUlt: A rejected second preparation must preserve every prior byte;
// the worker CLI must reject duplicate/unknown options before touching output.
#[test]
fn previous_preparation_and_cli_option_errors_are_preserved() {
    let fixture = Fixture::new("preserve");
    let input = fixture.input("base.cxi", &image());
    let output = fixture.root.join("prepared");
    prepare(&input, &output).unwrap();
    let before = files(&output);
    assert!(prepare(&input, &output).is_err());
    assert_eq!(files(&output), before);

    let binary = env!("CARGO_BIN_EXE_droidds-prepare-title");
    for extra in [["--input", "extra.cxi"], ["--update", "extra.cia"]] {
        let fresh = fixture.root.join("must-not-exist");
        let status = Command::new(binary)
            .arg("prepare")
            .arg("--input")
            .arg(&input)
            .arg("--output")
            .arg(&fresh)
            .args(extra)
            .output()
            .unwrap();
        assert_eq!(status.status.code(), Some(64));
        assert!(!fresh.exists());
        assert_eq!(files(&output), before);
    }
}
