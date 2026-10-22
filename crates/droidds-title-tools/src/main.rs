//! CodexAstraUlt: Narrow worker command interface. The Python coordinator owns
//! private snapshots, identity hashes, external resource caps and upload policy.

use droidds_title_tools::{run, Options};
use std::{collections::BTreeSet, fs::OpenOptions, io::Write, path::PathBuf};

// CodexAstraUlt: Reject duplicate/unknown options and nonpositive limits before
// opening input. No shell interpolation, default input discovery or network use.
fn parse() -> Result<(Options, PathBuf), String> {
    let mut args = std::env::args_os().skip(1);
    if args.next().as_deref() != Some(std::ffi::OsStr::new("inspect-run")) {
        return Err("usage: droidds-private-title inspect-run --input SNAPSHOT --data-dir NEWDIR --output NEW_REPORT [--max-steps N --max-cycles N --max-frames N --max-seconds N --model old|new --trace-scheduler]".into());
    }
    let mut options = Options {
        input: PathBuf::new(),
        data_dir: PathBuf::new(),
        max_steps: 1_000_000,
        max_cycles: 268_111_856,
        max_frames: 120,
        max_seconds: 30,
        new_model: false,
        trace_scheduler: false,
    };
    let mut output = None;
    let mut seen = BTreeSet::new();
    while let Some(flag) = args.next() {
        let flag = flag.to_str().ok_or("option name must be UTF-8")?;
        if !seen.insert(flag.to_owned()) {
            return Err(format!("duplicate option {flag}"));
        }
        // CodexAstraUlt: This opt-in switch takes no value and never enables
        // profiler allocation or diagnostics in the normal Android frontend.
        if flag == "--trace-scheduler" {
            options.trace_scheduler = true;
            continue;
        }
        let value = args
            .next()
            .ok_or_else(|| format!("missing value for {flag}"))?;
        match flag {
            "--input" => options.input = value.into(),
            "--data-dir" => options.data_dir = value.into(),
            "--output" => output = Some(PathBuf::from(value)),
            "--model" => {
                options.new_model = match value.to_str() {
                    Some("new") => true,
                    Some("old") => false,
                    _ => return Err("model must be old or new".into()),
                }
            }
            "--max-steps" | "--max-cycles" | "--max-frames" | "--max-seconds" => {
                let number = value
                    .to_str()
                    .and_then(|v| v.parse::<u64>().ok())
                    .ok_or_else(|| format!("{flag} requires a positive integer"))?;
                match flag {
                    "--max-steps" => options.max_steps = number,
                    "--max-cycles" => options.max_cycles = number,
                    "--max-frames" => options.max_frames = number,
                    _ => options.max_seconds = number,
                }
            }
            _ => return Err(format!("unknown option {flag}")),
        }
    }
    if options.input.as_os_str().is_empty() || options.data_dir.as_os_str().is_empty() {
        return Err("--input and --data-dir are required".into());
    }
    options.validate()?;
    Ok((options, output.ok_or("--output is required")?))
}

fn main() {
    let (options, output) = match parse() {
        Ok(value) => value,
        Err(error) => {
            eprintln!("{error}");
            std::process::exit(64);
        }
    };
    // CodexAstraUlt: Reserve a new owner-only report before running. Existing
    // reports and symlinks are refused, and the worker never rewrites input.
    let mut open = OpenOptions::new();
    open.write(true).create_new(true);
    #[cfg(unix)]
    {
        use std::os::unix::fs::OpenOptionsExt;
        open.mode(0o600);
    }
    let mut file = match open.open(output) {
        Ok(file) => file,
        Err(_) => {
            eprintln!("report must be a new file with an existing writable parent");
            std::process::exit(64);
        }
    };
    // CodexAstraUlt: Private parser panic payloads are intentionally omitted;
    // the bounded report still distinguishes a panic from a rejected input.
    std::panic::set_hook(Box::new(|_| {}));
    let report = run(&options);
    let mut bytes = serde_json::to_vec_pretty(&report).expect("JSON report serialization");
    bytes.push(b'\n');
    if file
        .write_all(&bytes)
        .and_then(|_| file.sync_all())
        .is_err()
    {
        eprintln!("cannot finish private worker report");
        std::process::exit(3);
    }
    std::process::exit(match report["status"].as_str() {
        Some("guest_exited" | "budget_exhausted" | "blocked") => 0,
        Some("load_error") => 2,
        _ => 3,
    });
}
