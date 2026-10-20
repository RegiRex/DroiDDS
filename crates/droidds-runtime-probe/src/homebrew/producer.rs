//! CodexAstraUlt: Emit native C for only the original interactive NCCH guest.

use super::fixture;
use recomp3ds::{codegen, discover, image::Segment};
use serde_json::{json, Value};
use std::{fs, path::Path};

pub fn emit(directory: &Path) -> Result<Value, String> {
    fs::create_dir(directory).map_err(|error| format!("create homebrew source output: {error}"))?;
    let program = discover::Program {
        text: Segment {
            base: fixture::TEXT,
            bytes: fixture::native_text(),
        },
        seeds: [(fixture::TEXT, discover::Source::Entry)]
            .into_iter()
            .collect(),
        slots: Some(Default::default()),
    };
    let analysis = discover::analyze(&program);
    if analysis.functions.is_empty() {
        return Err("original homebrew has no native functions".into());
    }
    let unit = codegen::Unit {
        module: None,
        program: &program,
        analysis: &analysis,
    };
    let mut sources = Vec::new();
    for (name, contents) in codegen::generate(&[unit], &[]) {
        fs::write(directory.join(&name), contents)
            .map_err(|error| format!("write homebrew source {name}: {error}"))?;
        if name.ends_with(".c") {
            sources.push(name);
        }
    }
    sources.sort();
    fs::write(directory.join("homebrew-fixture.cxi"), fixture::image())
        .map_err(|error| error.to_string())?;
    Ok(
        json!({"schema":1,"kind":"droidds-homebrew-fixture-sources","fixture":fixture::IDENTITY,
        "library":fixture::LIBRARY,"abi":recomp_abi::ABI,"generation":recomp_abi::GENERATION,
        "sources":sources,"native_text_bytes":program.text.bytes.len(),"fallback_entry":fixture::FALLBACK}),
    )
}
