//! CodexAstraUlt: The cross-build interface must produce original source without
//! invoking a compiler, executing a target library or overwriting old evidence.

#![cfg(target_os = "linux")]

use serde_json::Value;
use std::fs;
use std::process::Command;

#[test]
fn public_emit_sources_needs_no_compiler_and_preserves_existing_output() {
    let directory =
        std::env::temp_dir().join(format!("droidds source emission {}", std::process::id()));
    let output = Command::new(env!("CARGO_BIN_EXE_droidds-foundation"))
        .arg("--emit-sources")
        .arg(&directory)
        .env("CC", "/no/compiler/may/be/invoked/by/source/emission")
        .output()
        .unwrap();
    assert!(output.status.success(), "{output:?}");
    let manifest_bytes = fs::read(directory.join("manifest.json")).unwrap();
    let manifest: Value = serde_json::from_slice(&manifest_bytes).unwrap();
    assert_eq!(manifest["kind"], "droidds-original-fixture-sources");
    assert_eq!(manifest["abi"], recomp_abi::ABI);
    assert_eq!(manifest["generation"], recomp_abi::GENERATION);
    let cases = manifest["cases"].as_array().unwrap();
    assert_eq!(cases.len(), 8);
    for case in cases {
        let case_directory = directory.join(case["directory"].as_str().unwrap());
        let sources = case["sources"].as_array().unwrap();
        assert!(!sources.is_empty());
        for source in sources {
            assert!(case_directory.join(source.as_str().unwrap()).is_file());
        }
        assert!(case_directory.join("guest-code.bin").is_file());
        assert!(!case_directory
            .join(case["library"].as_str().unwrap())
            .exists());
    }
    assert!(!directory.join("report.json").exists());
    let repeat = Command::new(env!("CARGO_BIN_EXE_droidds-foundation"))
        .arg("--emit-sources")
        .arg(&directory)
        .output()
        .unwrap();
    assert!(!repeat.status.success());
    assert_eq!(
        fs::read(directory.join("manifest.json")).unwrap(),
        manifest_bytes
    );
    fs::remove_dir_all(directory).unwrap();
}
