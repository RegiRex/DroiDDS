//! CodexAstraUlt: The preparation worker is supervised by the Python coordinator;
//! it never compiles/loads guest libraries, signs packages or executes a title.

use std::{collections::BTreeSet, path::PathBuf};

// CodexAstraUlt: A small explicit CLI excludes mods, updates and implicit inputs.
fn parse() -> Result<(PathBuf, PathBuf), String> {
    let mut args = std::env::args_os().skip(1);
    if args.next().as_deref() != Some(std::ffi::OsStr::new("prepare")) {
        return Err("usage: droidds-prepare-title prepare --input SNAPSHOT --output NEWDIR".into());
    }
    let (mut input, mut output) = (None, None);
    let mut seen = BTreeSet::new();
    while let Some(flag) = args.next() {
        if !seen.insert(flag.clone()) {
            return Err("duplicate option".into());
        }
        let value = args.next().ok_or("missing option value")?;
        match flag.to_str() {
            Some("--input") => input = Some(value.into()),
            Some("--output") => output = Some(value.into()),
            _ => return Err("unknown preparation option".into()),
        }
    }
    Ok((
        input.ok_or("--input required")?,
        output.ok_or("--output required")?,
    ))
}

// CodexAstraUlt: A parser panic or incomplete generation cannot create a success
// manifest; the coordinator preserves partial output and distinguishes failure.
fn main() {
    let (input, output) = parse().unwrap_or_else(|error| {
        eprintln!("{error}");
        std::process::exit(64)
    });
    std::panic::set_hook(Box::new(|_| {}));
    let result = std::panic::catch_unwind(|| droidds_title_builder::prepare(&input, &output));
    match result {
        Ok(Ok(_)) => {}
        Ok(Err(error)) => {
            eprintln!("preparation rejected: {error}");
            std::process::exit(2);
        }
        Err(_) => {
            eprintln!("preparation failed: parser or generator panic");
            std::process::exit(3);
        }
    }
}
