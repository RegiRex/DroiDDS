//! CodexAstraUlt: Execute eight original packaged CPU fixtures through the actual
//! recomp ABI. This is an Android loader/CPU probe, not a 3DS emulator or title
//! importer. Known generated native code is trusted; this API is not a sandbox.

// CodexAstraUlt: The persistent original guest has a separate bounded FFI API;
// earlier one-shot probes and their owned-report/free contract remain intact.
mod homebrew;

use droidds_foundation::{fixtures, libraries, runner};
use serde_json::{json, Value};
use std::ffi::{CStr, CString};
use std::os::raw::c_char;
use std::panic::{catch_unwind, AssertUnwindSafe};
use std::path::Path;
use std::sync::Mutex;

// CodexAstraUlt: The upstream loader's origin check updates writable metadata in
// each loaded library. Serializing calls prevents concurrent checks/execution
// against the same dlopen image, including callers outside the Android Activity.
static RUN_LOCK: Mutex<()> = Mutex::new(());

fn envelope() -> Value {
    // CodexAstraUlt: Report the running host page size, never substitute Android's
    // guest 4 KiB page model or an ELF alignment claim for actual host evidence.
    let page_size = unsafe { libc::sysconf(libc::_SC_PAGESIZE) };
    json!({
        "schema": 1,
        "kind": "droidds-android-cpu-probe",
        "status": "failed",
        "version": env!("CARGO_PKG_VERSION"),
        "host_arch": std::env::consts::ARCH,
        "host_os": std::env::consts::OS,
        "host_page_size": page_size,
        "pointer_bits": usize::BITS,
        "abi": recomp_abi::ABI,
        "generation": recomp_abi::GENERATION,
        "cases": [],
        "negative_controls": [],
        "limitations": [
            "Eight original fixtures do not establish broad ARMv6K, game or graphics compatibility.",
            "Finite exact VFP arithmetic/conversions pass only their selected operands; NaN, subnormal and general rounding behavior remain unqualified.",
            "Immutable fixture text and small-slice progress are tested; no CRO lifetime or OS scheduler integration is established.",
            "Native instruction accounting is not elapsed time or emulation speed.",
            "Instruction budgets bound cooperative fixtures; there is no in-process wall-clock watchdog.",
            "Rust panic capture cannot catch native crashes, corrupt pointers, aborts or hung native code.",
            "Only known packaged fixture libraries are supported; no untrusted library sandbox is provided.",
            "A 4 KiB host run does not qualify execution on a 16 KiB host."
        ]
    })
}

fn failure(error: impl AsRef<str>) -> Value {
    let mut report = envelope();
    report["error"] = json!(error.as_ref());
    report
}

// CodexAstraUlt: The same strict validator must reject deliberately corrupted
// actual native output on the executing target, not just hypothetical states.
fn negative_controls(
    fixture: &fixtures::Fixture,
    reference: &runner::ResultState,
    candidate: &mut runner::ResultState,
) -> Result<Vec<Value>, String> {
    let original = candidate.state.clone();
    candidate.state.registers[6] = 0x7fc0_0002;
    let register_error = runner::validate(fixture, reference, candidate)
        .err()
        .ok_or("integer-register corruption was incorrectly accepted")?;
    candidate.state = original.clone();
    if !register_error.contains("r6:") {
        return Err(format!(
            "integer-register rejection was unrelated: {register_error}"
        ));
    }
    candidate.state.memory[droidds_foundation::memory::DATA as usize + 4] = 2;
    let memory_error = runner::validate(fixture, reference, candidate)
        .err()
        .ok_or("integer-memory corruption was incorrectly accepted")?;
    candidate.state = original;
    if !memory_error.contains("memory byte") {
        return Err(format!(
            "integer-memory rejection was unrelated: {memory_error}"
        ));
    }
    Ok(vec![
        json!({"name": "nan_shaped_integer_register_mismatch", "status": "passed", "rejection": register_error}),
        json!({"name": "nan_shaped_integer_memory_mismatch", "status": "passed", "rejection": memory_error}),
    ])
}

fn execute(directory: &Path) -> Result<Value, String> {
    if !directory.is_absolute() || !directory.is_dir() {
        return Err("library directory must be an existing absolute directory".to_owned());
    }
    // CodexAstraUlt: A persistent homebrew session owns this lock across frames.
    // Reject competing/reentrant probes instead of blocking its owner forever.
    let _guard = RUN_LOCK
        .try_lock()
        .map_err(|_| "another native probe/session is active or its lock is poisoned")?;
    let mut report = envelope();
    if report["host_page_size"]
        .as_i64()
        .is_none_or(|size| size <= 0)
    {
        return Err("cannot obtain the executing host page size".to_owned());
    }
    let mut cases = Vec::new();
    let mut controls = Vec::new();
    let mut code_safety = json!({"status": "failed", "error": "code-safety controls did not run"});
    for fixture in fixtures::fixtures() {
        let file_name = format!("libdds_fixture_{}.so", fixture.name);
        // CodexAstraUlt: Keep the library alive until both the final snapshot and
        // the negative controls complete. No compiler, process or network call
        // occurs here; native fixture code was compiled by the desktop builder.
        let result = (|| -> Result<Value, String> {
            let library = libraries::open_fixture(&fixture, &directory.join(&file_name))?;
            let reference = runner::interpreted(&fixture);
            let mut candidate = runner::native(&fixture, &library);
            runner::validate(&fixture, &reference, &candidate)?;
            if fixture.name == "arm_integer_memory" {
                controls = negative_controls(&fixture, &reference, &mut candidate)?;
                // CodexAstraUlt: Run the same actual stale/changed/store guards
                // as Linux against this packaged library on the Android device.
                code_safety = libraries::safety_controls(&fixture, &directory.join(&file_name))?;
            }
            Ok(json!({
                "name": fixture.name,
                "library": file_name,
                "status": "passed",
                "checkpoint_svc": fixtures::CHECKPOINT,
                "strict_expected_match": true,
                "strict_interpreter_match": true,
                "route_counts_match": true,
                "native_calls": candidate.counts.native_calls,
                "native_lookup_hits": candidate.counts.native_lookup_hits,
                "native_budget_charged": candidate.counts.native_budget_charged,
                "fallback_steps": candidate.counts.fallback_steps,
                "instruction_callbacks": candidate.counts.instruction_callbacks,
                "budget_exits": candidate.counts.budget_exits,
                "interpreter_steps": reference.counts.interpreter_steps,
                "memory_bytes_compared": candidate.state.memory.len(),
            }))
        })();
        cases.push(match result {
            Ok(case) => case,
            Err(error) => json!({"name": fixture.name, "library": file_name, "status": "failed", "error": error}),
        });
    }
    let passed = cases.len() == 8
        && cases.iter().all(|case| case["status"] == "passed")
        && controls.len() == 2
        && code_safety["status"] == "passed";
    report["status"] = json!(if passed { "passed" } else { "failed" });
    report["cases"] = json!(cases);
    report["negative_controls"] = json!(controls);
    report["code_safety"] = code_safety;
    Ok(report)
}

/// CodexAstraUlt: Return one owned UTF-8 JSON result, released exactly once with
/// `droidds_probe_free`. Null input returns failure JSON. Run from a worker thread.
///
/// # Safety
/// `library_directory` must be null or point to a readable NUL-terminated UTF-8
/// string for this call. The directory must contain only the matching trusted
/// fixture libraries. Rust panic handling does not validate arbitrary pointers
/// or recover native faults; an outer device runner supplies the deadline.
#[no_mangle]
pub unsafe extern "C" fn droidds_probe_run(library_directory: *const c_char) -> *mut c_char {
    // CodexAstraUlt: Keep pointer decoding and report encoding inside the unwind
    // boundary. CString owns the returned allocation; JNI must copy then free it.
    let result = catch_unwind(AssertUnwindSafe(|| {
        let report = if library_directory.is_null() {
            failure("library directory pointer is null")
        } else {
            // CodexAstraUlt: SAFETY: The C caller promises valid NUL-terminated
            // storage; null was handled without dereferencing it above.
            match unsafe { CStr::from_ptr(library_directory) }.to_str() {
                Ok(directory) => execute(Path::new(directory)).unwrap_or_else(failure),
                Err(_) => failure("library directory is not valid UTF-8"),
            }
        };
        // CodexAstraUlt: JSON escapes embedded NULs, so this cannot contain an
        // interior NUL even when a loader error includes unusual path bytes.
        CString::new(report.to_string())
            .expect("JSON encoding escapes NUL bytes")
            .into_raw()
    }));
    match result {
        Ok(pointer) => pointer,
        Err(_) => CString::new(failure("Rust panic during CPU probe; run is failed").to_string())
            .expect("JSON encoding escapes NUL bytes")
            .into_raw(),
    }
}

/// CodexAstraUlt: Execute the original full-runtime fixture separately so a
/// runtime failure does not erase completed CPU/Vulkan platform evidence.
///
/// # Safety
/// Both pointers must be null or readable NUL-terminated UTF-8 strings for the
/// call. Native libraries must be the matching installer-owned public fixtures;
/// the scratch path is a dedicated app-private directory, never a title/save path.
#[no_mangle]
pub unsafe extern "C" fn droidds_runtime_run(
    library_directory: *const c_char,
    scratch_directory: *const c_char,
) -> *mut c_char {
    let failed = |error: &str| {
        json!({"schema": 1, "kind": "droidds-runtime-probe",
                                    "status": "failed", "error": error})
    };
    let result = catch_unwind(AssertUnwindSafe(|| {
        if library_directory.is_null() || scratch_directory.is_null() {
            return failed("runtime paths must not be null");
        }
        // CodexAstraUlt: SAFETY: JNI supplies live, borrowed installer/private
        // ASCII paths. Null checks precede dereferencing either borrowed string.
        let directories = unsafe {
            (
                CStr::from_ptr(library_directory).to_str(),
                CStr::from_ptr(scratch_directory).to_str(),
            )
        };
        let (Ok(libraries), Ok(scratch)) = directories else {
            return failed("runtime paths must be valid UTF-8");
        };
        // CodexAstraUlt: Never wait on the calling worker's persistent session.
        let Ok(_guard) = RUN_LOCK.try_lock() else {
            return failed("another native probe/session is active or its lock is poisoned");
        };
        droidds_runtime_probe::run(Path::new(libraries), Path::new(scratch))
    }));
    let mut bytes = result
        .unwrap_or_else(|_| failed("Rust panic during runtime probe"))
        .to_string();
    // CodexAstraUlt: Bound this independent evidence channel before crossing
    // JNI. The existing Rust free function owns every returned allocation.
    if bytes.len() > 256 * 1024 {
        bytes = failed("runtime report exceeds 256 KiB").to_string();
    }
    CString::new(bytes)
        .expect("JSON encoding escapes NUL bytes")
        .into_raw()
}

/// CodexAstraUlt: Release a result from either exported probe function once.
///
/// # Safety
/// `report` must be null or the unmodified, live pointer returned by this library.
/// Passing another allocation or freeing a result twice is undefined behavior.
#[no_mangle]
pub unsafe extern "C" fn droidds_probe_free(report: *mut c_char) {
    if !report.is_null() {
        // CodexAstraUlt: SAFETY: Ownership is returned by the caller under the
        // exported API contract; no allocation crosses a mismatched allocator.
        drop(unsafe { CString::from_raw(report) });
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    // CodexAstraUlt: Exercise the real exported ownership boundary for invalid
    // inputs; these must return failure JSON rather than dereference or succeed.
    fn invoke(directory: *const c_char) -> Value {
        let pointer = unsafe { droidds_probe_run(directory) };
        assert!(!pointer.is_null());
        let report = unsafe { CStr::from_ptr(pointer) }.to_str().unwrap();
        let value = serde_json::from_str(report).unwrap();
        unsafe { droidds_probe_free(pointer) };
        value
    }

    // CodexAstraUlt: Null runtime arguments fail before library or scratch access.
    #[test]
    fn null_runtime_paths_return_owned_failure() {
        let pointer = unsafe { droidds_runtime_run(std::ptr::null(), std::ptr::null()) };
        assert!(!pointer.is_null());
        let value: Value =
            serde_json::from_str(unsafe { CStr::from_ptr(pointer) }.to_str().unwrap()).unwrap();
        unsafe { droidds_probe_free(pointer) };
        assert_eq!(value["status"], "failed");
        assert_eq!(value["error"], "runtime paths must not be null");
    }

    #[test]
    fn null_directory_is_a_failed_owned_report() {
        let report = invoke(std::ptr::null());
        assert_eq!(report["status"], "failed");
        assert_eq!(report["error"], "library directory pointer is null");
        assert_eq!(report["cases"], json!([]));
        assert!(report["host_page_size"].as_i64().unwrap() > 0);
        unsafe { droidds_probe_free(std::ptr::null_mut()) };
    }

    #[test]
    fn invalid_utf8_directory_is_rejected() {
        let directory = CString::new(vec![0xff]).unwrap();
        let report = invoke(directory.as_ptr());
        assert_eq!(report["status"], "failed");
        assert_eq!(report["error"], "library directory is not valid UTF-8");
    }

    #[test]
    fn relative_directory_cannot_load_fixtures() {
        let directory = CString::new(".").unwrap();
        let report = invoke(directory.as_ptr());
        assert_eq!(report["status"], "failed");
        assert_eq!(report["cases"], json!([]));
    }
}
