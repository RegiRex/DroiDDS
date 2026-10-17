//! CodexAstraUlt: Exercise interruption through the public command and a fake C
//! compiler. The actual supervisor/worker/compiler/sleep tree must stop together.

#![cfg(target_os = "linux")]

use std::fs;
use std::os::unix::fs::PermissionsExt;
use std::path::{Path, PathBuf};
use std::process::{Child, Command, Stdio};
use std::thread;
use std::time::{Duration, Instant};

// CodexAstraUlt: Poll /proc rather than accepting the supervisor's exit alone;
// orphaned workers were previously able to keep compiling after that exit.
fn live(pid: i32) -> bool {
    let Ok(stat) = fs::read_to_string(format!("/proc/{pid}/stat")) else {
        return false;
    };
    !matches!(
        stat.rsplit_once(") ")
            .and_then(|(_, tail)| tail.chars().next()),
        Some('Z' | 'X')
    )
}

fn markers(directory: &Path) -> Vec<[i32; 3]> {
    fs::read_dir(directory)
        .unwrap()
        .filter_map(|entry| {
            let entry = entry.ok()?;
            if !entry.file_name().to_string_lossy().starts_with("compiler-") {
                return None;
            }
            let text = fs::read_to_string(entry.path()).ok()?;
            let fields: Vec<i32> = text
                .split_whitespace()
                .map(str::parse)
                .collect::<Result<_, _>>()
                .ok()?;
            fields.try_into().ok()
        })
        .collect()
}

// CodexAstraUlt: Even an assertion failure must stop the intentionally hung
// fake compiler tree. Marker PIDs are generated solely by this test's children.
struct Cleanup {
    child: Child,
    directory: PathBuf,
}

impl Drop for Cleanup {
    fn drop(&mut self) {
        if matches!(self.child.try_wait(), Ok(None)) {
            // CodexAstraUlt: SAFETY: Child is this test's unreaped supervisor.
            unsafe { libc::kill(self.child.id() as i32, libc::SIGTERM) };
            let deadline = Instant::now() + Duration::from_secs(2);
            while Instant::now() < deadline {
                if self.child.try_wait().ok().flatten().is_some() {
                    break;
                }
                thread::sleep(Duration::from_millis(10));
            }
        }
        for [worker, compiler, descendant] in markers(&self.directory) {
            // CodexAstraUlt: SAFETY: Live PIDs came from the private marker files;
            // the worker is the group leader created by the public supervisor.
            unsafe {
                if live(worker) {
                    libc::kill(-worker, libc::SIGKILL);
                }
                for pid in [compiler, descendant] {
                    if live(pid) {
                        libc::kill(pid, libc::SIGKILL);
                    }
                }
            }
        }
        let _ = self.child.kill();
        let _ = self.child.wait();
    }
}

// CodexAstraUlt: --version succeeds so execution reaches compile::compile.
// Every real fake-compile invocation creates a sleeping descendant and records
// worker/compiler/descendant PIDs before hanging; no production test mode exists.
fn interrupted_tree(signal: i32) {
    let directory = std::env::temp_dir().join(format!(
        "droidds-supervisor-{}-{signal}",
        std::process::id()
    ));
    fs::create_dir(&directory).unwrap();
    let compiler = directory.join("fake-cc");
    fs::write(
        &compiler,
        r#"#!/bin/sh
if [ "$1" = "--version" ]; then
    echo 'DroidDS interruption-test compiler'
    exit 0
fi
sleep 60 &
descendant=$!
printf '%s %s %s\n' "$PPID" "$$" "$descendant" > "$DROIDDS_PROCESS_MARKERS/compiler-$$"
wait "$descendant"
"#,
    )
    .unwrap();
    fs::set_permissions(&compiler, fs::Permissions::from_mode(0o700)).unwrap();
    let output = fs::File::create(directory.join("supervisor.log")).unwrap();
    let child = Command::new(env!("CARGO_BIN_EXE_droidds-foundation"))
        .arg(directory.join("result"))
        .env("CC", &compiler)
        .env("DROIDDS_PROCESS_MARKERS", &directory)
        .stdin(Stdio::null())
        .stdout(output.try_clone().unwrap())
        .stderr(output)
        .spawn()
        .unwrap();
    let mut cleanup = Cleanup {
        child,
        directory: directory.clone(),
    };
    let deadline = Instant::now() + Duration::from_secs(5);
    while markers(&directory).is_empty() && Instant::now() < deadline {
        assert!(
            cleanup.child.try_wait().unwrap().is_none(),
            "public harness exited before fake compiler started"
        );
        thread::sleep(Duration::from_millis(10));
    }
    let observed = markers(&directory);
    assert!(
        !observed.is_empty(),
        "fake compiler did not start; inspect {}",
        directory.display()
    );
    assert!(
        observed
            .iter()
            .all(|tree| tree.iter().all(|&pid| live(pid))),
        "marker must identify live processes before interruption"
    );
    // CodexAstraUlt: SAFETY: Signal is SIGINT or SIGTERM and the Child is live.
    assert_eq!(unsafe { libc::kill(cleanup.child.id() as i32, signal) }, 0);
    let deadline = Instant::now() + Duration::from_secs(5);
    let status = loop {
        if let Some(status) = cleanup.child.try_wait().unwrap() {
            break status;
        }
        assert!(Instant::now() < deadline, "supervisor ignored interruption");
        thread::sleep(Duration::from_millis(10));
    };
    assert!(!status.success(), "interrupted fixture cannot pass");
    assert!(
        !directory.join("result/report.json").exists(),
        "interrupted fixture wrote a passing report"
    );
    let deadline = Instant::now() + Duration::from_secs(2);
    loop {
        let active: Vec<i32> = markers(&directory)
            .into_iter()
            .flatten()
            .filter(|&pid| live(pid))
            .collect();
        if active.is_empty() {
            break;
        }
        assert!(
            Instant::now() < deadline,
            "orphaned worker/compiler/descendant: {active:?}"
        );
        thread::sleep(Duration::from_millis(10));
    }
    drop(cleanup);
    fs::remove_dir_all(directory).unwrap();
}

#[test]
fn sigterm_stops_worker_and_compiler_descendants() {
    interrupted_tree(libc::SIGTERM);
}

#[test]
fn sigint_stops_worker_and_compiler_descendants() {
    interrupted_tree(libc::SIGINT);
}
