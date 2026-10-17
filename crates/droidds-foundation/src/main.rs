//! CodexAstraUlt: First Linux CPU foundation build. Generate real C from public
//! synthetic ARM/Thumb inputs, load it through recomp-abi and require evidence.

mod fixtures;
mod memory;
mod runner;

use std::fs::{self, OpenOptions};
use std::io::Write;
use std::path::Path;
use std::process::{Command, ExitCode, ExitStatus, Stdio};
use std::sync::atomic::{AtomicBool, Ordering};
use std::time::{Duration, Instant};

use recomp3ds::{codegen, compile, discover, image::Segment};
use serde_json::{json, Value};

// CodexAstraUlt: The public command creates a fresh output directory and a
// bounded worker process. It never deletes/reuses a previous result directory.
fn main() -> ExitCode {
    match command() {
        Ok(()) => ExitCode::SUCCESS,
        Err(error) => {
            eprintln!("DroidDS foundation FAILED: {error}");
            ExitCode::FAILURE
        }
    }
}

fn command() -> Result<(), String> {
    if !cfg!(target_os = "linux") {
        return Err("this initial foundation runner requires Linux".to_owned());
    }
    let arguments: Vec<_> = std::env::args_os().skip(1).collect();
    if arguments
        .first()
        .is_some_and(|arg| arg == "--watchdog-probe")
        && arguments.len() == 1
    {
        std::thread::sleep(Duration::from_secs(60));
        return Err("watchdog probe was not terminated".to_owned());
    }
    if arguments.first().is_some_and(|arg| arg == "--worker") && arguments.len() == 2 {
        return suite(Path::new(&arguments[1]));
    }
    if arguments.len() != 1 || arguments[0].to_string_lossy().starts_with('-') {
        return Err("usage: droidds-foundation <new-output-directory>".to_owned());
    }
    let directory = std::path::absolute(&arguments[0]).map_err(|error| error.to_string())?;
    if let Some(parent) = directory.parent() {
        fs::create_dir_all(parent).map_err(|error| format!("create output parent: {error}"))?;
    }
    fs::create_dir(&directory).map_err(|error| {
        format!(
            "create {}: {error}; choose a new directory, existing results are preserved",
            directory.display()
        )
    })?;
    let mut worker = Command::new(std::env::current_exe().map_err(|error| error.to_string())?);
    worker.arg("--worker").arg(&directory);
    install_stop_handlers()?;
    match bounded(worker, Duration::from_secs(180), ProcessScope::WorkerGroup)? {
        ChildOutcome::Exited(status) if status.success() => {
            let report_path = directory.join("report.json");
            let report: Value =
                serde_json::from_slice(&fs::read(&report_path).map_err(|error| error.to_string())?)
                    .map_err(|error| error.to_string())?;
            if report["status"] != "passed" {
                return Err("worker did not write a passing report".to_owned());
            }
            println!(
                "DroidDS foundation passed; report: {}",
                report_path.display()
            );
            Ok(())
        }
        ChildOutcome::Exited(status) => Err(format!("fixture worker failed ({status})")),
        ChildOutcome::TimedOut => {
            Err("fixture worker exceeded 180 seconds; process group terminated".to_owned())
        }
        ChildOutcome::Interrupted => {
            Err("interrupted; fixture worker process group terminated".to_owned())
        }
    }
}

enum ChildOutcome {
    Exited(ExitStatus),
    TimedOut,
    Interrupted,
}

// CodexAstraUlt: A probe has no descendants and stays in its worker's group.
// Only the real worker owns another group, which its supervisor must terminate.
enum ProcessScope {
    WorkerGroup,
    ProbeOnly,
}

// CodexAstraUlt: The outer build runner can interrupt this supervisor. Atomic
// signal notification keeps the handler allocation-free; normal Rust code then
// terminates and reaps the isolated worker instead of orphaning its compilers.
static STOP_REQUESTED: AtomicBool = AtomicBool::new(false);

extern "C" fn request_stop(_: libc::c_int) {
    STOP_REQUESTED.store(true, Ordering::Relaxed);
}

fn install_stop_handlers() -> Result<(), String> {
    for signal in [libc::SIGINT, libc::SIGTERM] {
        // CodexAstraUlt: SAFETY: The handler only stores a lock-free AtomicBool;
        // it does not allocate, unwind, lock, or invoke other Rust runtime work.
        if unsafe { libc::signal(signal, request_stop as *const () as libc::sighandler_t) }
            == libc::SIG_ERR
        {
            return Err(format!(
                "install stop handler: {}",
                std::io::Error::last_os_error()
            ));
        }
    }
    Ok(())
}

// CodexAstraUlt: Kill the worker's complete private group on timeout/interruption.
// A leaf probe is killed alone so it cannot escape its worker's cleanup boundary.
fn terminate(child: &mut std::process::Child, scope: &ProcessScope) -> Result<(), String> {
    let pid = child.id() as i32;
    let target = match scope {
        ProcessScope::WorkerGroup => -pid,
        ProcessScope::ProbeOnly => pid,
    };
    // CodexAstraUlt: SAFETY: The child is unreaped, preventing PID reuse; its
    // group was explicitly set at spawn when the negative target is selected.
    if unsafe { libc::kill(target, libc::SIGKILL) } != 0 {
        let error = std::io::Error::last_os_error();
        if error.raw_os_error() != Some(libc::ESRCH) {
            let _ = child.kill();
            let _ = child.wait();
            return Err(format!("terminate worker: {error}"));
        }
    }
    child
        .wait()
        .map_err(|error| format!("reap terminated worker: {error}"))?;
    Ok(())
}

// CodexAstraUlt: Linux worker groups include compiler descendants. SIGINT and
// SIGTERM receive the same complete cleanup as the wall-clock deadline.
#[cfg(target_os = "linux")]
fn bounded(
    mut command: Command,
    limit: Duration,
    scope: ProcessScope,
) -> Result<ChildOutcome, String> {
    use std::os::unix::process::CommandExt;
    if matches!(scope, ProcessScope::WorkerGroup) {
        command.process_group(0);
    }
    command.stdin(Stdio::null());
    let mut child = command
        .spawn()
        .map_err(|error| format!("spawn worker: {error}"))?;
    let deadline = Instant::now() + limit;
    loop {
        if STOP_REQUESTED.load(Ordering::Relaxed) {
            terminate(&mut child, &scope)?;
            return Ok(ChildOutcome::Interrupted);
        }
        match child.try_wait() {
            Ok(Some(status)) => return Ok(ChildOutcome::Exited(status)),
            Ok(None) if Instant::now() >= deadline => {
                terminate(&mut child, &scope)?;
                return Ok(ChildOutcome::TimedOut);
            }
            Ok(None) => std::thread::sleep(Duration::from_millis(10)),
            Err(error) => {
                let cleanup = terminate(&mut child, &scope);
                return Err(format!("wait worker: {error}; cleanup: {cleanup:?}"));
            }
        }
    }
}

#[cfg(not(target_os = "linux"))]
fn bounded(_: Command, _: Duration, _: ProcessScope) -> Result<ChildOutcome, String> {
    Err("process-group watchdog is only implemented on Linux".to_owned())
}

// CodexAstraUlt: Use upstream discovery/codegen/compiler APIs, without enabling
// their permissive verifier. A missing C compiler is a required-gate failure.
fn build(
    fixture: &fixtures::Fixture,
    directory: &Path,
    compiler: &compile::Compiler,
) -> Result<recomp_abi::Library, String> {
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
    let generated = codegen::generate(&[unit], &[]);
    let mut sources = Vec::new();
    for (name, contents) in generated {
        fs::write(directory.join(&name), contents)
            .map_err(|error| format!("write {name}: {error}"))?;
        if name.ends_with(".c") {
            sources.push(name);
        }
    }
    let library_path = directory.join("libfixture.so");
    compile::compile(
        compiler,
        directory,
        &sources,
        &library_path,
        &|_, _| true,
        false,
    )?;
    let mut library = recomp_abi::Library::open(&library_path)?;
    if library.generation() != recomp_abi::GENERATION || library.origins(0).is_none() {
        return Err("generated library generation/origin metadata is missing or wrong".to_owned());
    }
    let stale = library.check(0, 0, |address, destination| {
        let start = address as usize;
        destination.copy_from_slice(&fixture.memory.bytes[start..start + destination.len()]);
    });
    if stale != 0
        || library
            .lookup(fixture.cpu.regs[15] | u32::from(fixture.cpu.cpsr.thumb))
            .is_none()
    {
        return Err(format!(
            "{}: missing or stale initial native entry",
            fixture.name
        ));
    }
    if fixture
        .thumb_entry
        .is_some_and(|address| library.lookup(address).is_none())
    {
        return Err(format!(
            "{}: expected Thumb native entry is missing",
            fixture.name
        ));
    }
    if library.lookup(memory::EXTRA).is_some() {
        return Err("deliberately absent entry unexpectedly has native code".to_owned());
    }
    fs::write(directory.join("guest-code.bin"), &fixture.text)
        .map_err(|error| error.to_string())?;
    Ok(library)
}

// CodexAstraUlt: Run both engines and hand-derived expectations. Record actual
// dispatch, fallback and strict-oracle evidence; these are not game benchmarks.
fn suite(directory: &Path) -> Result<(), String> {
    let compiler = compile::check(None)?;
    let version = Command::new(&compiler.program)
        .args(&compiler.leading)
        .arg("--version")
        .output()
        .map_err(|error| format!("read compiler version: {error}"))?;
    if !version.status.success() {
        return Err("C compiler version command failed".to_owned());
    }
    let mut results = Vec::new();
    for fixture in fixtures::fixtures() {
        let library = build(&fixture, &directory.join(fixture.name), &compiler)?;
        let reference = runner::interpreted(&fixture);
        let candidate = runner::native(&fixture, &library);
        runner::validate(&fixture, &reference, &candidate)
            .map_err(|error| format!("{}: {error}", fixture.name))?;
        results.push(json!({
            "name": fixture.name,
            "status": "passed",
            "checkpoint_svc": fixtures::CHECKPOINT,
            "native_calls": candidate.counts.native_calls,
            "native_lookup_hits": candidate.counts.native_lookup_hits,
            "native_budget_charged": candidate.counts.native_budget_charged,
            "fallback_steps": candidate.counts.fallback_steps,
            "instruction_callbacks": candidate.counts.instruction_callbacks,
            "interpreter_steps": reference.counts.interpreter_steps,
            "memory_bytes_compared": candidate.state.memory.len(),
            "guest_code_hex": fixture.text.iter().map(|byte| format!("{byte:02x}")).collect::<String>(),
        }));
        println!(
            "PASS {}: native calls {}, fallback steps {}, strict full-state match",
            fixture.name, candidate.counts.native_calls, candidate.counts.fallback_steps
        );
    }

    // CodexAstraUlt: Inject bad results into otherwise valid checkpoint runs.
    // Exercise the same validation gate used above, not a separate test oracle.
    let control = fixtures::fixtures().remove(0);
    let library = recomp_abi::Library::open(&directory.join(control.name).join("libfixture.so"))?;
    let reference = runner::interpreted(&control);
    let mut corrupted = runner::native(&control, &library);
    corrupted.state.registers[6] = 0x7fc0_0002;
    let register_error = runner::validate(&control, &reference, &corrupted)
        .expect_err("CodexAstraUlt: integer-register mutation must be rejected");
    if !register_error.contains("r6:") {
        return Err(format!(
            "register negative control failed for wrong reason: {register_error}"
        ));
    }
    let mut corrupted = runner::native(&control, &library);
    corrupted.state.memory[memory::DATA as usize + 4] = 2;
    let memory_error = runner::validate(&control, &reference, &corrupted)
        .expect_err("CodexAstraUlt: integer-memory mutation must be rejected");
    if !memory_error.contains("memory byte") {
        return Err(format!(
            "memory negative control failed for wrong reason: {memory_error}"
        ));
    }

    let endless = fixtures::endless();
    let library = build(&endless, &directory.join(endless.name), &compiler)?;
    let reference = runner::interpreted(&endless);
    let candidate = runner::native(&endless, &library);
    if reference.stop != runner::Stop::InstructionLimit
        || candidate.stop != runner::Stop::InstructionLimit
        || candidate.counts.native_calls == 0
        || candidate.counts.native_budget_charged == 0
    {
        return Err("instruction-limit negative control did not exercise both engines".to_owned());
    }
    if runner::validate(&endless, &reference, &candidate).is_ok() {
        return Err("instruction-limit negative control was incorrectly accepted".to_owned());
    }
    let mut probe = Command::new(std::env::current_exe().map_err(|error| error.to_string())?);
    probe.arg("--watchdog-probe");
    if !matches!(
        bounded(probe, Duration::from_millis(150), ProcessScope::ProbeOnly)?,
        ChildOutcome::TimedOut
    ) {
        return Err("wall-clock watchdog negative control did not time out".to_owned());
    }
    println!("PASS negative controls: integer-register corruption, integer-memory corruption, guest instruction limit, process watchdog");

    let report = json!({
        "schema": 1,
        "status": "passed",
        "scope": "Linux synthetic CPU foundation; not a complete M1 or an Android emulator",
        "abi": recomp_abi::ABI,
        "generation": recomp_abi::GENERATION,
        "host_arch": std::env::consts::ARCH,
        "host_os": std::env::consts::OS,
        "compiler": compiler.describe(),
        "compiler_version": String::from_utf8_lossy(&version.stdout).trim(),
        "cases": results,
        "negative_controls": [
            {"name": "nan_shaped_integer_register_mismatch", "status": "passed", "rejection": register_error},
            {"name": "nan_shaped_integer_memory_mismatch", "status": "passed", "rejection": memory_error},
            {"name": "guest_instruction_limit", "status": "passed", "accepted_as_completed": false,
                "native_calls": candidate.counts.native_calls, "native_budget_charged": candidate.counts.native_budget_charged,
                "interpreter_steps": reference.counts.interpreter_steps},
            {"name": "process_watchdog", "status": "passed", "limit_ms": 150, "terminated": true}
        ],
        "limitations": [
            "Four tiny original integer fixtures are not broad ARMv6K compatibility.",
            "VFP storage preservation is checked; no floating-point instruction is executed.",
            "No CRO lifetime, executable-write policy, SVC service implementation, scheduler or graphics test.",
            "Native memory uses checked host callbacks; direct page mappings are not exercised.",
            "Host correctness and instruction accounting provide no handheld speed or memory measurement."
        ]
    });
    write_report(&directory.join("report.json"), &report)
}

// CodexAstraUlt: Create a final report once, only after every required execution
// and negative control passes. Failure leaves evidence but no passing report.
fn write_report(path: &Path, report: &Value) -> Result<(), String> {
    let mut output = OpenOptions::new()
        .write(true)
        .create_new(true)
        .open(path)
        .map_err(|error| error.to_string())?;
    let encoded = serde_json::to_vec_pretty(report).map_err(|error| error.to_string())?;
    output
        .write_all(&encoded)
        .and_then(|()| output.write_all(b"\n"))
        .map_err(|error| error.to_string())
}
