//! CodexAstraUlt: Thread-owned generic title sessions cross a bounded C ABI.
//! Tokens are generations, not pointers; all transient buffers stay caller-owned.

use droidds_title_runtime::{
    InputState, OpenOptions, PadState, Session, AUDIO_SAMPLE_RATE, MAX_PCM_FRAMES,
};
use serde_json::{json, Value};
use std::{
    cell::RefCell,
    ffi::{CStr, CString},
    os::raw::c_char,
    panic::{catch_unwind, AssertUnwindSafe},
    path::Path,
    ptr,
    sync::{
        atomic::{AtomicU64, Ordering},
        Mutex, MutexGuard,
    },
};

pub const TOP_BYTES: usize = 400 * 240 * 4;
pub const BOTTOM_BYTES: usize = 320 * 240 * 4;
pub const PCM_SAMPLES: usize = MAX_PCM_FRAMES * 2;
const MANIFEST_LIMIT: usize = 1024 * 1024;
const REPORT_LIMIT: usize = 256 * 1024;
static NEXT_TOKEN: AtomicU64 = AtomicU64::new(1);

// CodexAstraUlt: Origin checks mutate the loaded image's control metadata.
// Retain one global lock throughout the session, including pause, so another
// thread cannot open/check the same native image while this session can run it.
static RUN_LOCK: Mutex<()> = Mutex::new(());
struct Slot {
    session: Session,
    token: u64,
    paused: bool,
    error: Option<String>,
    // CodexAstraUlt: Fields drop in order: runtime and libraries go first.
    _guard: MutexGuard<'static, ()>,
}

thread_local! {
    static SESSION: RefCell<Option<Slot>> = const { RefCell::new(None) };
}

// CodexAstraUlt: Keep this layout identical to DdsTitleMetrics. Output flags
// distinguish a normal cooperative yield from fresh pixels or actual guest exit.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
#[repr(C)]
pub struct Metrics {
    pub frames: u64,
    pub cycles: u64,
    pub pcm_frames: u64,
    pub exited: u64,
    pub ready_mask: u64,
}

fn failure(error: impl AsRef<str>) -> Value {
    json!({"schema_version":1,"kind":"droidds-title-player","status":"failed","error":error.as_ref()})
}

// CodexAstraUlt: Every returned string uses one allocator and an explicit free
// operation. Catch Rust unwinds, not native faults, hung code or invalid pointers.
fn owned_json(operation: impl FnOnce() -> Value) -> *mut c_char {
    let value = catch_unwind(AssertUnwindSafe(operation))
        .unwrap_or_else(|_| failure("Rust panic in title boundary"));
    let mut encoded = value.to_string();
    if encoded.len() > REPORT_LIMIT {
        encoded = failure("title report exceeds 256 KiB").to_string();
    }
    CString::new(encoded)
        .expect("JSON escapes NUL bytes")
        .into_raw()
}

// CodexAstraUlt: Null and malformed paths reject before runtime/filesystem work;
// JNI supplies borrowed installer/app-private paths and retains no Rust pointer.
unsafe fn path<'a>(value: *const c_char) -> Result<&'a Path, String> {
    if value.is_null() {
        return Err("title paths must not be null".into());
    }
    // SAFETY: The exported API requires a live NUL-terminated input string.
    let text = unsafe { CStr::from_ptr(value) }
        .to_str()
        .map_err(|_| "title path is not UTF-8")?;
    let path = Path::new(text);
    if !path.is_absolute() {
        return Err("title paths must be absolute".into());
    }
    Ok(path)
}

/// CodexAstraUlt: Open a persistent title with a newly owned token.
///
/// # Safety
/// Manifest is null or readable for manifest_bytes; paths are null or live
/// NUL-terminated UTF-8 strings. opened_token is null or a writable aligned u64,
/// disjoint from inputs. All later operations use this same native thread.
/// Caller closes a nonzero token if transfer fails, and frees JSON exactly once.
#[no_mangle]
pub unsafe extern "C" fn droidds_title_open(
    manifest: *const u8,
    manifest_bytes: usize,
    input: *const c_char,
    native_directory: *const c_char,
    data_directory: *const c_char,
    native_mode: u32,
    hardware: u32,
    opened_token: *mut u64,
) -> *mut c_char {
    if opened_token.is_null() {
        return owned_json(|| failure("open requires a token ownership output"));
    }
    // SAFETY: The caller supplies the writable u64 promised above.
    unsafe { opened_token.write(0) };
    owned_json(|| {
        if manifest.is_null()
            || manifest_bytes == 0
            || manifest_bytes > MANIFEST_LIMIT
            || native_mode > 1
            || hardware > 1
        {
            return failure("invalid title manifest length or route options");
        }
        // SAFETY: Input lengths and nulls were checked; remaining pointer
        // validity belongs to the C caller's explicit borrow contract.
        let options = unsafe { (path(input), path(native_directory), path(data_directory)) };
        let (input, native_directory, data_directory) = match options {
            (Ok(input), Ok(native_directory), Ok(data_directory)) => {
                (input, native_directory, data_directory)
            }
            (Err(error), _, _) | (_, Err(error), _) | (_, _, Err(error)) => return failure(error),
        };
        SESSION.with(|cell| {
            let Ok(mut slot) = cell.try_borrow_mut() else {
                return failure("reentrant title open");
            };
            if slot.is_some() {
                return failure("title session already exists on this worker");
            }
            let Ok(guard) = RUN_LOCK.try_lock() else {
                return failure("another title session is active or its lock is poisoned");
            };
            let token =
                match NEXT_TOKEN.fetch_update(Ordering::Relaxed, Ordering::Relaxed, |value| {
                    value.checked_add(1).filter(|next| *next <= i64::MAX as u64)
                }) {
                    Ok(token) => token,
                    Err(_) => return failure("title session token space exhausted"),
                };
            // SAFETY: The manifest remains borrowed for open only; the runtime
            // owns its parsed identity and does not retain caller storage.
            let manifest_json = unsafe { std::slice::from_raw_parts(manifest, manifest_bytes) };
            let session = match Session::open(OpenOptions {
                manifest_json,
                input,
                native_directory,
                data_directory,
                native: native_mode == 1,
                hardware: hardware == 1,
            }) {
                Ok(session) => session,
                Err(error) => return failure(error),
            };
            *slot = Some(Slot {
                session,
                token,
                paused: false,
                error: None,
                _guard: guard,
            });
            // SAFETY: Publish ownership only after this exact session exists.
            unsafe { opened_token.write(token) };
            json!({"schema_version":1,"kind":"droidds-title-session-open","status":"opened",
                "token":token,"sample_rate":AUDIO_SAMPLE_RATE,"version":env!("CARGO_PKG_VERSION")})
        })
    })
}

fn with_session<T>(
    token: u64,
    operation: impl FnOnce(&mut Slot) -> Result<T, String>,
) -> Result<T, String> {
    SESSION.with(|cell| {
        let mut slot = cell.try_borrow_mut().map_err(|_| "reentrant title call")?;
        let slot = slot
            .as_mut()
            .filter(|slot| slot.token == token && token != 0)
            .ok_or("unknown/stale title token or wrong worker thread")?;
        operation(slot)
    })
}

fn failed_session(token: u64, error: String) {
    let _ = with_session(token, |slot| {
        slot.error = Some(error);
        Ok(())
    });
}

// CodexAstraUlt: Reject arithmetic overflow, misalignment and caller-buffer
// overlap before guest execution. Pointer accessibility is still a C obligation;
// validating extents prevents one accepted output from overwriting another.
fn disjoint_outputs(top: *mut u8, bottom: *mut u8, pcm: *mut i16, metrics: *mut Metrics) -> bool {
    if !(pcm as usize).is_multiple_of(std::mem::align_of::<i16>())
        || !(metrics as usize).is_multiple_of(std::mem::align_of::<Metrics>())
    {
        return false;
    }
    let mut ranges = [(0, 0); 4];
    for (index, (start, bytes)) in [
        (top as usize, TOP_BYTES),
        (bottom as usize, BOTTOM_BYTES),
        (pcm as usize, PCM_SAMPLES * std::mem::size_of::<i16>()),
        (metrics as usize, std::mem::size_of::<Metrics>()),
    ]
    .into_iter()
    .enumerate()
    {
        let Some(end) = start.checked_add(bytes) else {
            return false;
        };
        if start == 0 {
            return false;
        }
        if ranges[..index]
            .iter()
            .any(|&(other_start, other_end)| start < other_end && other_start < end)
        {
            return false;
        }
        ranges[index] = (start, end);
    }
    true
}

/// CodexAstraUlt: Advance one bounded slice; images can be absent on a yield.
///
/// # Safety
/// Output pointers are null or aligned writable, mutually disjoint buffers for
/// their declared lengths. Metrics points to one disjoint writable Metrics.
/// No borrowed pointer is retained; this is not an untrusted native-code sandbox.
#[no_mangle]
pub unsafe extern "C" fn droidds_title_slice(
    token: u64,
    buttons: u32,
    circle_x: f32,
    circle_y: f32,
    c_stick_x: f32,
    c_stick_y: f32,
    touch_x: i32,
    touch_y: i32,
    touched: u32,
    top: *mut u8,
    top_bytes: usize,
    bottom: *mut u8,
    bottom_bytes: usize,
    pcm: *mut i16,
    pcm_samples: usize,
    metrics: *mut Metrics,
) -> i32 {
    // CodexAstraUlt: Caller mistakes reject without changing guest state or
    // poisoning a valid session; no output, including metrics, is written yet.
    if top.is_null()
        || bottom.is_null()
        || pcm.is_null()
        || metrics.is_null()
        || top_bytes != TOP_BYTES
        || bottom_bytes != BOTTOM_BYTES
        || pcm_samples != PCM_SAMPLES
        || !disjoint_outputs(top, bottom, pcm, metrics)
        || touched > 1
        || (touched == 1 && (!(0..320).contains(&touch_x) || !(0..240).contains(&touch_y)))
        || [circle_x, circle_y, c_stick_x, c_stick_y]
            .into_iter()
            .any(|axis| !axis.is_finite() || !(-1.0..=1.0).contains(&axis))
    {
        return -1;
    }
    let Some(buttons) = PadState::from_bits(buttons) else {
        return -1;
    };
    let input = InputState {
        buttons,
        circle_x,
        circle_y,
        c_stick_x,
        c_stick_y,
        touch: (touched == 1).then_some((touch_x as u16, touch_y as u16)),
        ..InputState::default()
    };
    let result = catch_unwind(AssertUnwindSafe(|| {
        with_session(token, |slot| {
            if slot.error.is_some() {
                return Err("title session already failed".into());
            }
            if slot.paused {
                return Ok(false);
            }
            let slice = slot.session.slice(input)?;
            if slice
                .top
                .as_ref()
                .is_some_and(|pixels| pixels.len() != TOP_BYTES)
                || slice
                    .bottom
                    .as_ref()
                    .is_some_and(|pixels| pixels.len() != BOTTOM_BYTES)
                || slice.pcm.len() > MAX_PCM_FRAMES
            {
                return Err("title slice exceeds the output contract".into());
            }
            let mut ready_mask = 0;
            // SAFETY: Output shapes were checked before advancing, and each owned
            // result buffer remains separate from the caller's borrowed storage.
            unsafe {
                if let Some(pixels) = &slice.top {
                    ptr::copy_nonoverlapping(pixels.as_ptr(), top, TOP_BYTES);
                    ready_mask |= 1;
                }
                if let Some(pixels) = &slice.bottom {
                    ptr::copy_nonoverlapping(pixels.as_ptr(), bottom, BOTTOM_BYTES);
                    ready_mask |= 2;
                }
                for (index, sample) in slice.pcm.iter().enumerate() {
                    pcm.add(index * 2).write(sample[0]);
                    pcm.add(index * 2 + 1).write(sample[1]);
                }
                metrics.write(Metrics {
                    frames: slice.frames,
                    cycles: slice.cycles,
                    pcm_frames: slice.pcm.len() as u64,
                    exited: u64::from(slice.exited),
                    ready_mask,
                });
            }
            Ok(true)
        })
    }));
    match result {
        Ok(Ok(true)) => 0,
        Ok(Ok(false)) => -2,
        Ok(Err(error)) => {
            failed_session(token, error);
            -1
        }
        Err(_) => {
            failed_session(token, "Rust panic while advancing title".into());
            -1
        }
    }
}

// CodexAstraUlt: Pause/resume never advances a guest and keeps runtime/save
// ownership on the original worker. Failed sessions remain reportable/closable.
fn set_paused(token: u64, paused: bool) -> i32 {
    match catch_unwind(AssertUnwindSafe(|| {
        with_session(token, |slot| {
            if slot.error.is_some() {
                return Err("title session already failed".into());
            }
            if paused {
                slot.session.pause();
            } else {
                slot.session.resume();
            }
            slot.paused = paused;
            Ok(())
        })
    })) {
        Ok(Ok(())) => 0,
        Ok(Err(error)) => {
            failed_session(token, error);
            -1
        }
        Err(_) => {
            failed_session(token, "Rust panic changing title lifecycle".into());
            -1
        }
    }
}

#[no_mangle]
pub extern "C" fn droidds_title_pause(token: u64) -> i32 {
    set_paused(token, true)
}

#[no_mangle]
pub extern "C" fn droidds_title_resume(token: u64) -> i32 {
    set_paused(token, false)
}

/// CodexAstraUlt: Return one owned bounded JSON report without consuming state.
#[no_mangle]
pub extern "C" fn droidds_title_report(token: u64) -> *mut c_char {
    owned_json(|| {
        with_session(token, |slot| {
            let mut report = slot.session.report();
            if let Some(error) = &slot.error {
                report["status"] = json!("failed");
                report["error"] = json!(error);
            }
            Ok(report)
        })
        .unwrap_or_else(failure)
    })
}

/// CodexAstraUlt: A stale or wrong-thread close cannot destroy another session.
/// Runtime teardown precedes releasing the single active-execution lock.
#[no_mangle]
pub extern "C" fn droidds_title_close(token: u64) -> i32 {
    match catch_unwind(AssertUnwindSafe(|| {
        SESSION.with(|cell| {
            let mut slot = cell.try_borrow_mut().map_err(|_| ())?;
            if !slot
                .as_ref()
                .is_some_and(|slot| slot.token == token && token != 0)
            {
                return Err(());
            }
            drop(slot.take());
            Ok(())
        })
    })) {
        Ok(Ok(())) => 0,
        _ => -1,
    }
}

/// CodexAstraUlt: Return JSON ownership to the allocating library exactly once.
///
/// # Safety
/// Pointer must be null or the unmodified live allocation from open/report.
#[no_mangle]
pub unsafe extern "C" fn droidds_title_free(report: *mut c_char) {
    if !report.is_null() {
        // SAFETY: The caller returns an allocation from this library once.
        drop(unsafe { CString::from_raw(report) });
    }
}

#[cfg(test)]
mod tests;
