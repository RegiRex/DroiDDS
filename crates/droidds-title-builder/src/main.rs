//! CodexAstraUlt: The preparation worker is supervised by the Python coordinator;
//! it never compiles/loads guest libraries, signs packages or executes a title.

use std::{collections::BTreeSet, path::PathBuf};

// CodexAstraUlt: A small explicit CLI excludes mods, updates and implicit inputs.
fn parse() -> Result<(PathBuf, PathBuf, u64), String> {
    let mut args = std::env::args_os().skip(1);
    if args.next().as_deref() != Some(std::ffi::OsStr::new("prepare")) {
        return Err("usage: droidds-prepare-title prepare --input SNAPSHOT --output NEWDIR [--output-limit-bytes N]".into());
    }
    let (mut input, mut output) = (None, None);
    let mut limit = droidds_title_builder::DEFAULT_OUTPUT_LIMIT;
    let mut seen = BTreeSet::new();
    while let Some(flag) = args.next() {
        if !seen.insert(flag.clone()) {
            return Err("duplicate option".into());
        }
        let value = args.next().ok_or("missing option value")?;
        match flag.to_str() {
            Some("--input") => input = Some(value.into()),
            Some("--output") => output = Some(value.into()),
            // CodexAstraUlt: Explicit per-run output admission is finite and
            // parsed before touching input/output, independently of host limits.
            Some("--output-limit-bytes") => {
                limit = value
                    .to_str()
                    .filter(|text| !text.is_empty() && text.bytes().all(|b| b.is_ascii_digit()))
                    .and_then(|text| text.parse::<u64>().ok())
                    .filter(|limit| *limit > 0 && *limit <= droidds_title_builder::MAX_OUTPUT_LIMIT)
                    .ok_or("output limit must be between 1 byte and 1 GiB")?;
            }
            _ => return Err("unknown preparation option".into()),
        }
    }
    Ok((
        input.ok_or("--input required")?,
        output.ok_or("--output required")?,
        limit,
    ))
}

// CodexAstraUlt: A parser panic or incomplete generation cannot create a success
// manifest; the coordinator preserves partial output and distinguishes failure.
fn main() {
    let (input, output, limit) = parse().unwrap_or_else(|error| {
        eprintln!("{error}");
        std::process::exit(64)
    });
    std::panic::set_hook(Box::new(|_| {}));
    let result = std::panic::catch_unwind(|| {
        droidds_title_builder::prepare_with_limit(&input, &output, limit)
    });
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
