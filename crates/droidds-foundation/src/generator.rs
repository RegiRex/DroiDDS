//! CodexAstraUlt: Produce the same original fixture C on the host for native
//! Linux builds or NDK cross-compilation; this module never runs on Android.

use crate::{fixtures, memory};
use recomp3ds::{codegen, discover, image::Segment};
use serde_json::{json, Value};
use std::fs;
use std::path::Path;

pub fn emit(fixture: &fixtures::Fixture, directory: &Path) -> Result<Vec<String>, String> {
    fs::create_dir(directory).map_err(|error| format!("create fixture output: {error}"))?;
    let program = discover::Program {
        text: Segment {
            base: memory::START,
            bytes: fixture.text.clone(),
        },
        seeds: fixture
            .seeds
            .iter()
            .map(|&address| (address, discover::Source::Entry))
            .collect(),
        slots: Some(Default::default()),
    };
    let analysis = discover::analyze(&program);
    if analysis.functions.is_empty() {
        return Err(format!("{}: discovery found no functions", fixture.name));
    }
    let unit = codegen::Unit {
        module: None,
        program: &program,
        analysis: &analysis,
    };
    let mut sources = Vec::new();
    for (name, contents) in codegen::generate(&[unit], &[]) {
        fs::write(directory.join(&name), contents)
            .map_err(|error| format!("write {name}: {error}"))?;
        if name.ends_with(".c") {
            sources.push(name);
        }
    }
    sources.sort();
    fs::write(directory.join("guest-code.bin"), &fixture.text)
        .map_err(|error| error.to_string())?;
    Ok(sources)
}

// CodexAstraUlt: The caller creates a new top-level directory. A manifest is
// returned only after all sources are emitted; this is generation, not a pass
// claim, native execution, a compilation step or retail title conversion.
pub fn emit_suite(directory: &Path) -> Result<Value, String> {
    let mut cases = Vec::new();
    for fixture in fixtures::fixtures() {
        let sources = emit(&fixture, &directory.join(fixture.name))?;
        cases.push(json!({
            "name": fixture.name,
            "directory": fixture.name,
            "library": format!("libdds_fixture_{}.so", fixture.name),
            "sources": sources,
            "guest_code_hex": fixture.text.iter().map(|byte| format!("{byte:02x}")).collect::<String>(),
        }));
    }
    Ok(json!({
        "schema": 1,
        "kind": "droidds-original-fixture-sources",
        "abi": recomp_abi::ABI,
        "generation": recomp_abi::GENERATION,
        "cases": cases,
    }))
}
