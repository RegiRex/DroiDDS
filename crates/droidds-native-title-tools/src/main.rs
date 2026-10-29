//! CodexAstraUlt: Only a sealed local admission descriptor can select native
//! input. Paths select fresh outputs, never arbitrary native-library discovery.

use std::{collections::BTreeSet, fs::OpenOptions, io::Write, path::PathBuf};

fn parse() -> Result<(i32, PathBuf, PathBuf), String> {
    let mut args = std::env::args_os().skip(1);
    let (mut descriptor, mut data, mut output) = (None, None, None);
    let mut seen = BTreeSet::new();
    while let Some(flag) = args.next() {
        let flag = flag.to_str().ok_or("option name must be UTF-8")?;
        if !seen.insert(flag.to_owned()) {
            return Err("duplicate worker option".into());
        }
        let value = args.next().ok_or("missing worker option value")?;
        match flag {
            "--request-fd" => {
                descriptor = Some(
                    value
                        .to_str()
                        .and_then(|s| s.parse::<i32>().ok())
                        .filter(|fd| *fd >= 3)
                        .ok_or("invalid request descriptor")?,
                )
            }
            "--data-dir" => data = Some(PathBuf::from(value)),
            "--output" => output = Some(PathBuf::from(value)),
            _ => return Err("unknown worker option".into()),
        }
    }
    Ok((
        descriptor.ok_or("--request-fd required")?,
        data.ok_or("--data-dir required")?,
        output.ok_or("--output required")?,
    ))
}

fn main() {
    let (descriptor, data, output) = match parse() {
        Ok(options) => options,
        Err(error) => {
            eprintln!("{error}");
            std::process::exit(64);
        }
    };
    // CodexAstraUlt: Exclusively reserve an owner-only report; no old report or
    // symlink is replaced. Parent validation owns the containing run directory.
    let mut options = OpenOptions::new();
    options.write(true).create_new(true);
    #[cfg(unix)]
    {
        use std::os::unix::fs::OpenOptionsExt;
        options.mode(0o600).custom_flags(libc::O_NOFOLLOW);
    }
    let mut file = match options.open(output) {
        Ok(file) => file,
        Err(_) => {
            eprintln!("report must be a new regular file");
            std::process::exit(64);
        }
    };
    std::panic::set_hook(Box::new(|_| {}));
    let report = droidds_native_title_tools::run_fd(descriptor, &data);
    let mut bytes = serde_json::to_vec_pretty(&report).expect("worker JSON report");
    bytes.push(b'\n');
    if bytes.len() > 4 * 1024 * 1024
        || file
            .write_all(&bytes)
            .and_then(|_| file.sync_all())
            .is_err()
    {
        eprintln!("cannot publish bounded worker report");
        std::process::exit(3);
    }
    std::process::exit(match report["status"].as_str() {
        Some("guest_exited" | "budget_exhausted" | "blocked") => 0,
        Some("load_error") => 2,
        _ => 3,
    });
}
