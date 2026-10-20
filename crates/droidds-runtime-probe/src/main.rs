//! CodexAstraUlt: The host tool emits fixture sources or executes the same suite
//! that Android calls; C compilation remains an explicit host build operation.

use std::path::PathBuf;

fn main() {
    let args: Vec<String> = std::env::args().skip(1).collect();
    let value = match args.as_slice() {
        [command, option, path] if command == "emit" && option == "--output" => emit(&PathBuf::from(path)),
        // CodexAstraUlt: Keep the interactive guest's sources/runtime separate
        // from the frozen exact-output 0.0.5 regression fixture.
        [command, option, path] if command == "emit-homebrew" && option == "--output" => emit_homebrew(&PathBuf::from(path)),
        [command, native_option, native, scratch_option, scratch]
            if command == "run" && native_option == "--native-dir" && scratch_option == "--scratch-dir" =>
            Ok(droidds_runtime_probe::run(&PathBuf::from(native), &PathBuf::from(scratch))),
        [command, native_option, native, scratch_option, scratch]
            if command == "run-homebrew" && native_option == "--native-dir" && scratch_option == "--scratch-dir" =>
            Ok(droidds_runtime_probe::homebrew::run_probe(&PathBuf::from(native), &PathBuf::from(scratch))),
        _ => Err("usage: droidds-runtime-probe emit|emit-homebrew --output NEW_DIRECTORY | run|run-homebrew --native-dir DIRECTORY --scratch-dir DIRECTORY".into()),
    };
    match value {
        Ok(value) => {
            println!("{}", serde_json::to_string_pretty(&value).unwrap());
            if value.get("status").and_then(serde_json::Value::as_str) == Some("failed") {
                std::process::exit(1);
            }
        }
        Err(error) => {
            eprintln!("{error}");
            std::process::exit(1);
        }
    }
}

#[cfg(feature = "producer")]
fn emit(path: &std::path::Path) -> Result<serde_json::Value, String> {
    droidds_runtime_probe::producer::emit(path)
}

#[cfg(not(feature = "producer"))]
fn emit(_: &std::path::Path) -> Result<serde_json::Value, String> {
    Err("emission requires the host producer feature".into())
}

#[cfg(feature = "producer")]
fn emit_homebrew(path: &std::path::Path) -> Result<serde_json::Value, String> {
    droidds_runtime_probe::homebrew::producer::emit(path)
}

#[cfg(not(feature = "producer"))]
fn emit_homebrew(_: &std::path::Path) -> Result<serde_json::Value, String> {
    Err("homebrew emission requires the host producer feature".into())
}
