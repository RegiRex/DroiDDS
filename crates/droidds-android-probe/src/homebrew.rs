//! CodexAstraUlt: Thread-owned sessions for the original interactive guest.
//! Tokens are generations, not pointers. JNI owns all transient frame buffers.

use super::RUN_LOCK;
use droidds_runtime_probe::homebrew::{self, InputState, PadState, Session, AUDIO_SAMPLE_RATE};
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
        MutexGuard,
    },
};

const TOP_BYTES: usize = 400 * 240 * 4;
const BOTTOM_BYTES: usize = 320 * 240 * 4;
const PCM_SAMPLES: usize = 4096 * 2;
const REPORT_LIMIT: usize = 256 * 1024;
static NEXT_TOKEN: AtomicU64 = AtomicU64::new(1);

// CodexAstraUlt: Keep the library/System on its creating worker, and retain the
// execution lock for its lifetime. An automatic probe cannot mutate origin
// metadata while a manual session is alive. System drops before the guard.
struct Slot {
    session: Session,
    token: u64,
    paused: bool,
    error: Option<String>,
    _guard: MutexGuard<'static, ()>,
}

thread_local! {
    static SESSION: RefCell<Option<Slot>> = const { RefCell::new(None) };
}

// CodexAstraUlt: Match DdsHomebrewMetrics in homebrew_api.h without pointer,
// platform-size or packed-layout fields. Counts describe actual returned data.
#[repr(C)]
pub struct Metrics {
    frame_index: u64,
    guest_serial: u64,
    pcm_frames: u64,
    exited: u64,
}

fn failure(error: impl AsRef<str>) -> Value {
    json!({"status":"failed", "error":error.as_ref()})
}

fn owned_json(operation: impl FnOnce() -> Value) -> *mut c_char {
    let value = catch_unwind(AssertUnwindSafe(operation))
        .unwrap_or_else(|_| failure("Rust panic in homebrew boundary"));
    let mut encoded = value.to_string();
    if encoded.len() > REPORT_LIMIT {
        encoded = failure("homebrew report exceeds 256 KiB").to_string();
    }
    CString::new(encoded).expect("JSON escapes NUL").into_raw()
}

// CodexAstraUlt: Only the caller's live installer/app-private strings are read;
// UTF-8/absolute-path validation precedes loader or scratch access.
unsafe fn paths<'a>(
    libraries: *const c_char,
    scratch: *const c_char,
) -> Result<(&'a Path, &'a Path), String> {
    if libraries.is_null() || scratch.is_null() {
        return Err("homebrew paths must not be null".into());
    }
    // CodexAstraUlt: SAFETY: The exported caller contract supplies live C strings.
    let libraries = unsafe { CStr::from_ptr(libraries) }
        .to_str()
        .map_err(|_| "invalid library path UTF-8")?;
    // CodexAstraUlt: SAFETY: The same borrowed-string contract applies to scratch.
    let scratch = unsafe { CStr::from_ptr(scratch) }
        .to_str()
        .map_err(|_| "invalid scratch path UTF-8")?;
    let (libraries, scratch) = (Path::new(libraries), Path::new(scratch));
    if !libraries.is_absolute() || !scratch.is_absolute() {
        return Err("homebrew paths must be absolute".into());
    }
    Ok((libraries, scratch))
}

/// CodexAstraUlt: Run the bounded automatic original-guest suite.
///
/// # Safety
/// Paths must be null or live NUL-terminated UTF-8 strings. They must identify
/// matching installer-owned libraries and dedicated private scratch storage.
/// Free the returned JSON exactly once with `droidds_probe_free`.
#[no_mangle]
pub unsafe extern "C" fn droidds_homebrew_probe(
    libraries: *const c_char,
    scratch: *const c_char,
) -> *mut c_char {
    owned_json(|| {
        // CodexAstraUlt: SAFETY: Borrowed paths are decoded only during this call.
        let (libraries, scratch) = match unsafe { paths(libraries, scratch) } {
            Ok(value) => value,
            Err(error) => return failure(error),
        };
        let Ok(_guard) = RUN_LOCK.try_lock() else {
            return failure("another native probe/session is active or its lock is poisoned");
        };
        homebrew::run_probe(libraries, scratch)
    })
}

/// CodexAstraUlt: Open one worker-owned trusted guest session with a fresh token.
///
/// # Safety
/// Paths obey `droidds_homebrew_probe`'s ownership rules. Every later call for
/// the returned token must use this same native worker thread. `opened_token`
/// is null or points to one writable, aligned u64 disjoint from the paths.
/// A nonzero output belongs to this call and must be closed if the caller cannot
/// deliver the JSON/token to its owner (including Java allocation failures).
#[no_mangle]
pub unsafe extern "C" fn droidds_homebrew_open(
    libraries: *const c_char,
    scratch: *const c_char,
    opened_token: *mut u64,
) -> *mut c_char {
    // CodexAstraUlt: Return transaction ownership without requiring the JNI
    // failure path to parse JSON or allocate memory. Failed opens never identify
    // an unrelated existing session for cleanup.
    if opened_token.is_null() {
        return owned_json(|| failure("open requires a token ownership output"));
    }
    // CodexAstraUlt: SAFETY: The caller provides the writable u64 described above.
    unsafe { opened_token.write(0) };
    owned_json(|| {
        // CodexAstraUlt: SAFETY: No pointer or borrowed path is retained by TLS.
        let (libraries, scratch) = match unsafe { paths(libraries, scratch) } {
            Ok(value) => value,
            Err(error) => return failure(error),
        };
        SESSION.with(|cell| {
            let mut slot = cell.borrow_mut();
            if slot.is_some() {
                return failure("homebrew session already exists on this worker");
            }
            let Ok(guard) = RUN_LOCK.try_lock() else {
                return failure("another native probe/session is active or its lock is poisoned");
            };
            let token =
                match NEXT_TOKEN.fetch_update(Ordering::Relaxed, Ordering::Relaxed, |value| {
                    value.checked_add(1).filter(|next| *next <= i64::MAX as u64)
                }) {
                    Ok(value) => value,
                    Err(_) => return failure("homebrew session token space exhausted"),
                };
            let session = match Session::create(libraries, scratch, true, true) {
                Ok(session) => session,
                Err(error) => return failure(error),
            };
            let result = json!({"status":"opened", "token":token, "sample_rate":AUDIO_SAMPLE_RATE});
            *slot = Some(Slot {
                session,
                token,
                paused: false,
                error: None,
                _guard: guard,
            });
            // CodexAstraUlt: SAFETY: Publish only this successfully installed
            // session's token; the caller retains no pointer after this call.
            unsafe { opened_token.write(token) };
            result
        })
    })
}

fn with_session<T>(
    token: u64,
    operation: impl FnOnce(&mut Slot) -> Result<T, String>,
) -> Result<T, String> {
    SESSION.with(|cell| {
        let mut slot = cell
            .try_borrow_mut()
            .map_err(|_| "reentrant homebrew call")?;
        let slot = slot
            .as_mut()
            .filter(|slot| slot.token == token && token != 0)
            .ok_or("unknown/stale homebrew token or wrong worker thread")?;
        operation(slot)
    })
}

fn failed_session(token: u64, message: String) {
    let _ = with_session(token, |slot| {
        slot.error = Some(message);
        Ok(())
    });
}

/// CodexAstraUlt: Fill one bounded frame without retaining caller storage.
///
/// # Safety
/// Non-null output pointers must be aligned, writable, mutually disjoint buffers
/// valid for their declared lengths; metrics must point to one writable Metrics.
/// All calls use the creating worker. This boundary does not sandbox native code.
#[no_mangle]
pub unsafe extern "C" fn droidds_homebrew_frame(
    token: u64,
    buttons: u32,
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
    // CodexAstraUlt: Validate all shape/type inputs before writing even metrics.
    if top.is_null()
        || bottom.is_null()
        || pcm.is_null()
        || metrics.is_null()
        || top_bytes != TOP_BYTES
        || bottom_bytes != BOTTOM_BYTES
        || pcm_samples != PCM_SAMPLES
        || touched > 1
        || (touched == 1 && (!(0..320).contains(&touch_x) || !(0..240).contains(&touch_y)))
    {
        failed_session(
            token,
            "invalid homebrew frame buffers or touch coordinates".into(),
        );
        return -1;
    }
    let Some(buttons) = PadState::from_bits(buttons) else {
        failed_session(token, "unknown 3DS button bits".into());
        return -1;
    };
    let operation = catch_unwind(AssertUnwindSafe(|| {
        with_session(token, |slot| {
            if slot.error.is_some() {
                return Err("homebrew session is failed".into());
            }
            // CodexAstraUlt: A late frame during pause must not poison the
            // retained session; it rejects without advancing and can resume.
            if slot.paused {
                return Ok(false);
            }
            let input = InputState {
                buttons,
                touch: (touched == 1).then_some((touch_x as u16, touch_y as u16)),
                ..InputState::default()
            };
            let frame = slot.session.frame(input)?;
            if frame.top.len() != TOP_BYTES
                || frame.bottom.len() != BOTTOM_BYTES
                || frame.pcm.len() > PCM_SAMPLES / 2
            {
                return Err("homebrew frame exceeds fixed output contract".into());
            }
            // CodexAstraUlt: SAFETY: The fixed-size caller buffers were validated;
            // they are disjoint from the owned frame and remain valid for this call.
            unsafe {
                ptr::copy_nonoverlapping(frame.top.as_ptr(), top, TOP_BYTES);
                ptr::copy_nonoverlapping(frame.bottom.as_ptr(), bottom, BOTTOM_BYTES);
                for (index, sample) in frame.pcm.iter().enumerate() {
                    pcm.add(index * 2).write(sample[0]);
                    pcm.add(index * 2 + 1).write(sample[1]);
                }
                metrics.write(Metrics {
                    frame_index: frame.frames,
                    guest_serial: u64::from(frame.guest_serial),
                    pcm_frames: frame.pcm.len() as u64,
                    exited: u64::from(frame.exited),
                });
            }
            Ok(true)
        })
    }));
    match operation {
        Ok(Ok(true)) => 0,
        Ok(Ok(false)) => -2,
        Ok(Err(error)) => {
            failed_session(token, error);
            -1
        }
        Err(_) => {
            failed_session(token, "Rust panic while advancing homebrew".into());
            -1
        }
    }
}

/// CodexAstraUlt: Pause does not execute another guest frame; resume retains state.
#[no_mangle]
pub extern "C" fn droidds_homebrew_pause(token: u64, paused: u32) -> i32 {
    if paused > 1 {
        return -1;
    }
    match catch_unwind(AssertUnwindSafe(|| {
        with_session(token, |slot| {
            if slot.error.is_some() {
                return Err("homebrew session already failed".into());
            }
            if paused == 1 {
                slot.session.pause();
            } else {
                slot.session.resume();
            }
            slot.paused = paused == 1;
            Ok(())
        })
    })) {
        Ok(Ok(())) => 0,
        Ok(Err(error)) => {
            failed_session(token, error);
            -1
        }
        Err(_) => {
            failed_session(token, "Rust panic changing homebrew lifecycle".into());
            -1
        }
    }
}

/// CodexAstraUlt: Return bounded current evidence without consuming the session.
/// The returned allocation must be released with `droidds_probe_free`.
#[no_mangle]
pub extern "C" fn droidds_homebrew_report(token: u64) -> *mut c_char {
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

/// CodexAstraUlt: A stale/wrong-thread close cannot destroy another session.
/// Closing drops GPU work and native libraries before releasing execution ownership.
#[no_mangle]
pub extern "C" fn droidds_homebrew_close(token: u64) {
    let _ = catch_unwind(AssertUnwindSafe(|| {
        SESSION.with(|cell| {
            let mut slot = cell.borrow_mut();
            if slot
                .as_ref()
                .is_some_and(|slot| slot.token == token && token != 0)
            {
                drop(slot.take());
            }
        })
    }));
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::droidds_probe_free;

    // CodexAstraUlt: Exercise actual exported ownership and shape failures;
    // these checks must reject without dereferencing absent frame storage.
    unsafe fn decode(pointer: *mut c_char) -> Value {
        let value =
            serde_json::from_str(unsafe { CStr::from_ptr(pointer) }.to_str().unwrap()).unwrap();
        unsafe { droidds_probe_free(pointer) };
        value
    }

    #[test]
    fn invalid_open_and_probe_paths_return_owned_failures() {
        let null = ptr::null();
        let mut opened = 42;
        for pointer in [
            unsafe { droidds_homebrew_open(null, null, &mut opened) },
            unsafe { droidds_homebrew_probe(null, null) },
        ] {
            let report = unsafe { decode(pointer) };
            assert_eq!(report["status"], "failed");
            assert_eq!(report["error"], "homebrew paths must not be null");
        }
        assert_eq!(opened, 0);
        let relative = CString::new("relative").unwrap();
        let report = unsafe {
            decode(droidds_homebrew_open(
                relative.as_ptr(),
                relative.as_ptr(),
                &mut opened,
            ))
        };
        assert_eq!(report["error"], "homebrew paths must be absolute");
        assert_eq!(opened, 0);
        let report = unsafe { decode(droidds_homebrew_open(null, null, ptr::null_mut())) };
        assert_eq!(report["error"], "open requires a token ownership output");
    }

    #[test]
    fn stale_tokens_and_absent_buffers_cannot_execute_or_close_a_session() {
        assert_eq!(droidds_homebrew_pause(42, 1), -1);
        droidds_homebrew_close(42);
        let report = unsafe { decode(droidds_homebrew_report(42)) };
        assert_eq!(report["status"], "failed");
        assert_eq!(
            unsafe {
                droidds_homebrew_frame(
                    42,
                    0,
                    0,
                    0,
                    0,
                    ptr::null_mut(),
                    TOP_BYTES,
                    ptr::null_mut(),
                    BOTTOM_BYTES,
                    ptr::null_mut(),
                    PCM_SAMPLES,
                    ptr::null_mut(),
                )
            },
            -1
        );
        assert_eq!(std::mem::size_of::<Metrics>(), 32);
        assert_eq!(std::mem::align_of::<Metrics>(), 8);
    }
}
