//! CodexAstraUlt: Exported ownership/lifecycle checks use authored containers.
//! Private game data, existing saves and native title libraries are never inputs.

use super::*;
use droidds_runtime_probe::fixture;
use sha2::{Digest, Sha256};
use std::{fs, os::unix::fs::PermissionsExt, path::PathBuf};

static SERIAL: Mutex<()> = Mutex::new(());
static NEXT_FIXTURE: AtomicU64 = AtomicU64::new(0);

fn hash(bytes: &[u8]) -> String {
    format!("{:x}", Sha256::digest(bytes))
}

// CodexAstraUlt: Build an independently hashed manifest around one original
// image. The placeholder library is identified honestly and never loaded by
// these interpreter-only FFI tests; native admission belongs to runtime tests.
struct Fixture {
    root: PathBuf,
    input: PathBuf,
    libraries: PathBuf,
    runtime: PathBuf,
    bytes: Vec<u8>,
    manifest: Vec<u8>,
}

impl Fixture {
    fn new(spin: bool) -> Self {
        let root = std::env::temp_dir().join(format!(
            "droidds-title-ffi-{}-{}",
            std::process::id(),
            NEXT_FIXTURE.fetch_add(1, Ordering::Relaxed)
        ));
        fs::create_dir(&root).unwrap();
        let input = root.join("original.cxi");
        let libraries = root.join("libraries");
        let runtime = root.join("runtime");
        fs::create_dir(&libraries).unwrap();
        fs::create_dir(&runtime).unwrap();
        fs::write(
            runtime.join("owner-save"),
            b"preserve original save sentinel",
        )
        .unwrap();
        let mut bytes = fixture::image(0, 0, false);
        if spin {
            bytes[0x800..0x804].copy_from_slice(&0xeaff_fffeu32.to_le_bytes());
        }
        fs::write(&input, &bytes).unwrap();
        fs::set_permissions(&input, fs::Permissions::from_mode(0o400)).unwrap();
        let title = zakuro_fs::Title::load(&input).unwrap();
        let code = title.code().unwrap();
        let mut offset = 0usize;
        let segments: Vec<_> = [title.exheader.text, title.exheader.rodata, title.exheader.data]
            .into_iter().zip(["text", "rodata", "data"]).map(|(info, name)| {
                let value = json!({"name":name,"address":info.address,"offset":offset,
                    "size":info.size,"mapped_bytes":u64::from(info.num_pages)*4096,
                    "sha256":hash(&code[offset..offset+info.size as usize]),"hash_scope":"logical_segment_bytes"});
                offset += info.num_pages as usize * 4096;
                value
            }).collect();
        let components: Vec<_> = [
            ("ncch_header", "identity/ncch-header.bin", &bytes[..512]),
            ("exheader", "identity/exheader.bin", title.exheader_bytes()),
            ("decompressed_code", "identity/code.bin", code.as_slice()),
        ]
        .into_iter()
        .map(|(kind, path, content)| {
            json!({"kind":kind,"path":path,
            "bytes":content.len(),"sha256":hash(content)})
        })
        .collect();
        let native_bytes = b"original unloaded FFI placeholder";
        fs::write(libraries.join("libdroidds_title.so"), native_bytes).unwrap();
        let manifest = serde_json::to_vec(&json!({"schema_version":1,"kind":"droidds_android_title",
            "program_id":format!("{:016x}",title.program_id()),
            "input":{"bytes":bytes.len(),"sha256":hash(&bytes)},
            "native":{"file":"libdroidds_title.so","bytes":native_bytes.len(),"sha256":hash(native_bytes)},
            "abi":4,"generation":3,"prepared":{"container":"ncch",
                "ncch_format_version":title.ncch.version,"remaster_version":title.exheader.remaster_version,
                "cia_title_version":null,"bss_size":title.exheader.bss_size,
                "segments":segments,"components":components}})).unwrap();
        Self {
            root,
            input,
            libraries,
            runtime,
            bytes,
            manifest,
        }
    }

    fn open(&self) -> (u64, Value) {
        let input = CString::new(self.input.to_str().unwrap()).unwrap();
        let libraries = CString::new(self.libraries.to_str().unwrap()).unwrap();
        let runtime = CString::new(self.runtime.to_str().unwrap()).unwrap();
        let mut token = 0;
        // SAFETY: All pointers are backed by live distinct strings/bytes/u64.
        let report = unsafe {
            decode(droidds_title_open(
                self.manifest.as_ptr(),
                self.manifest.len(),
                input.as_ptr(),
                libraries.as_ptr(),
                runtime.as_ptr(),
                0,
                0,
                &mut token,
            ))
        };
        (token, report)
    }

    fn preserved(&self) {
        assert_eq!(fs::read(&self.input).unwrap(), self.bytes);
        assert_eq!(
            fs::read(self.runtime.join("owner-save")).unwrap(),
            b"preserve original save sentinel"
        );
    }
}

impl Drop for Fixture {
    fn drop(&mut self) {
        fs::remove_dir_all(&self.root).unwrap();
    }
}

// CodexAstraUlt: Test cleanup closes only the token installed by its own open,
// including assertion unwinds; no fixture directory owns a production save.
struct OwnedToken(u64);
impl Drop for OwnedToken {
    fn drop(&mut self) {
        if self.0 != 0 {
            let _ = droidds_title_close(self.0);
        }
    }
}

unsafe fn decode(pointer: *mut c_char) -> Value {
    assert!(!pointer.is_null());
    // SAFETY: The just-returned owned JSON remains live until its matching free.
    let value = serde_json::from_str(unsafe { CStr::from_ptr(pointer) }.to_str().unwrap()).unwrap();
    unsafe { droidds_title_free(pointer) };
    value
}

fn report(token: u64) -> Value {
    // SAFETY: report returns an owned JSON allocation even for a stale token.
    unsafe { decode(droidds_title_report(token)) }
}

struct Buffers {
    top: Vec<u8>,
    bottom: Vec<u8>,
    pcm: Vec<i16>,
    metrics: Metrics,
}
impl Buffers {
    fn new() -> Self {
        Self {
            top: vec![0xa5; TOP_BYTES],
            bottom: vec![0x5a; BOTTOM_BYTES],
            pcm: vec![0x1234; PCM_SAMPLES],
            metrics: Metrics {
                frames: 91,
                cycles: 92,
                pcm_frames: 93,
                exited: 94,
                ready_mask: 95,
            },
        }
    }

    fn slice(&mut self, token: u64) -> i32 {
        // SAFETY: These owned buffers are aligned, disjoint and of exact size.
        unsafe {
            droidds_title_slice(
                token,
                0,
                0.0,
                0.0,
                0.0,
                0.0,
                0,
                0,
                0,
                self.top.as_mut_ptr(),
                self.top.len(),
                self.bottom.as_mut_ptr(),
                self.bottom.len(),
                self.pcm.as_mut_ptr(),
                self.pcm.len(),
                &mut self.metrics,
            )
        }
    }
}

#[test]
fn invalid_open_revokes_only_its_output_and_returns_owned_json() {
    let _serial = SERIAL.lock().unwrap();
    let mut token = 42;
    let manifest = b"{}";
    // SAFETY: Null path rejection precedes dereferencing any absent path.
    let value = unsafe {
        decode(droidds_title_open(
            manifest.as_ptr(),
            manifest.len(),
            ptr::null(),
            ptr::null(),
            ptr::null(),
            0,
            0,
            &mut token,
        ))
    };
    assert_eq!(value["status"], "failed");
    assert_eq!(token, 0);
    let value = unsafe {
        decode(droidds_title_open(
            ptr::null(),
            MANIFEST_LIMIT + 1,
            ptr::null(),
            ptr::null(),
            ptr::null(),
            0,
            0,
            &mut token,
        ))
    };
    assert_eq!(value["status"], "failed");
    let value = unsafe {
        decode(droidds_title_open(
            ptr::null(),
            0,
            ptr::null(),
            ptr::null(),
            ptr::null(),
            0,
            0,
            ptr::null_mut(),
        ))
    };
    assert_eq!(value["status"], "failed");
    unsafe { droidds_title_free(ptr::null_mut()) };
    assert_eq!(std::mem::size_of::<Metrics>(), 40);
    assert_eq!(std::mem::align_of::<Metrics>(), 8);
}

#[test]
fn paused_session_retains_state_and_yield_does_not_invent_pixels() {
    let _serial = SERIAL.lock().unwrap();
    let fixture = Fixture::new(true);
    let (token, opened) = fixture.open();
    assert_eq!(opened["status"], "opened", "{opened}");
    let token = OwnedToken(token);
    let mut buffers = Buffers::new();
    assert_eq!(droidds_title_pause(token.0), 0);
    let before = report(token.0);
    let untouched = buffers.metrics;
    assert_eq!(buffers.slice(token.0), -2);
    assert_eq!(buffers.metrics, untouched);
    assert_eq!(report(token.0)["cycles"], before["cycles"]);
    assert_eq!(droidds_title_resume(token.0), 0);
    assert_eq!(buffers.slice(token.0), 0);
    assert!(buffers.metrics.cycles > 0);
    assert_eq!(buffers.metrics.ready_mask, 0);
    assert_eq!(buffers.metrics.exited, 0);
    assert_eq!(buffers.metrics.pcm_frames, 0);
    assert!(buffers.top.iter().all(|byte| *byte == 0xa5));
    assert!(buffers.bottom.iter().all(|byte| *byte == 0x5a));
    assert!(buffers.pcm.iter().all(|sample| *sample == 0x1234));
    assert_eq!(report(token.0)["resume_count"], 1);
    fixture.preserved();
}

#[test]
fn invalid_capacities_overlap_and_input_reject_without_advancing_or_poisoning() {
    let _serial = SERIAL.lock().unwrap();
    let fixture = Fixture::new(true);
    let (token, opened) = fixture.open();
    assert_eq!(opened["status"], "opened", "{opened}");
    let token = OwnedToken(token);
    let mut b = Buffers::new();
    let before = report(token.0);
    let sentinel = b.metrics;
    for kind in [
        "capacity",
        "overlap",
        "axis",
        "touch",
        "buttons",
        "alignment",
    ] {
        let bottom = if kind == "overlap" {
            b.top.as_mut_ptr()
        } else {
            b.bottom.as_mut_ptr()
        };
        let metrics = if kind == "alignment" {
            (b.top.as_mut_ptr().wrapping_add(1)).cast()
        } else {
            &mut b.metrics
        };
        // SAFETY: Invalid shape/alignment is rejected before any write or guest
        // step; otherwise every buffer is a distinct live owned allocation.
        let status = unsafe {
            droidds_title_slice(
                token.0,
                if kind == "buttons" { 1 << 13 } else { 0 },
                if kind == "axis" { f32::NAN } else { 0.0 },
                0.0,
                0.0,
                0.0,
                320,
                0,
                u32::from(kind == "touch"),
                b.top.as_mut_ptr(),
                TOP_BYTES - usize::from(kind == "capacity"),
                bottom,
                BOTTOM_BYTES,
                b.pcm.as_mut_ptr(),
                PCM_SAMPLES,
                metrics,
            )
        };
        assert_eq!(status, -1, "{kind}");
        assert_eq!(b.metrics, sentinel);
        assert_eq!(report(token.0)["cycles"], before["cycles"]);
        assert_eq!(report(token.0)["status"], "running");
    }
    assert_eq!(b.slice(token.0), 0);
    fixture.preserved();
}

#[test]
fn stale_wrong_thread_and_competing_open_cannot_take_session_ownership() {
    let _serial = SERIAL.lock().unwrap();
    let fixture = Fixture::new(true);
    let (token, opened) = fixture.open();
    assert_eq!(opened["status"], "opened", "{opened}");
    let mut owned = OwnedToken(token);
    assert_eq!(droidds_title_close(token + 1), -1);
    assert_eq!(droidds_title_pause(token + 1), -1);
    let (other_token, rejected) = fixture.open();
    assert_eq!(other_token, 0);
    assert_eq!(rejected["status"], "failed");
    let input = fixture.input.clone();
    let libraries = fixture.libraries.clone();
    let runtime = fixture.root.join("competing-runtime");
    let runtime_check = runtime.clone();
    let manifest = fixture.manifest.clone();
    std::thread::spawn(move || {
        assert_eq!(report(token)["status"], "failed");
        assert_eq!(droidds_title_close(token), -1);
        assert_eq!(droidds_title_pause(token), -1);
        let input = CString::new(input.to_str().unwrap()).unwrap();
        let libraries = CString::new(libraries.to_str().unwrap()).unwrap();
        let runtime = CString::new(runtime.to_str().unwrap()).unwrap();
        let mut other_token = 99;
        let result = unsafe {
            decode(droidds_title_open(
                manifest.as_ptr(),
                manifest.len(),
                input.as_ptr(),
                libraries.as_ptr(),
                runtime.as_ptr(),
                0,
                0,
                &mut other_token,
            ))
        };
        assert_eq!(result["status"], "failed");
        assert_eq!(other_token, 0);
    })
    .join()
    .unwrap();
    assert!(!runtime_check.exists());
    assert_eq!(Buffers::new().slice(token), 0);
    assert_eq!(droidds_title_close(token), 0);
    owned.0 = 0;
    assert_eq!(report(token)["status"], "failed");
    assert_eq!(Buffers::new().slice(token), -1);
    let (new_token, reopened) = fixture.open();
    assert_eq!(reopened["status"], "opened", "{reopened}");
    let _new_owned = OwnedToken(new_token);
    assert_ne!(token, new_token);
    fixture.preserved();
}

#[test]
fn original_guest_exit_is_reported_and_close_preserves_input_and_save() {
    let _serial = SERIAL.lock().unwrap();
    let fixture = Fixture::new(false);
    let (token, opened) = fixture.open();
    assert_eq!(opened["status"], "opened", "{opened}");
    let mut token = OwnedToken(token);
    let mut b = Buffers::new();
    for _ in 0..16 {
        assert_eq!(b.slice(token.0), 0);
        if b.metrics.exited == 1 {
            break;
        }
    }
    assert_eq!(b.metrics.exited, 1);
    assert_eq!(b.metrics.cycles, 606);
    assert_eq!(b.metrics.ready_mask, 0);
    let result = report(token.0);
    assert_eq!(result["status"], "exited");
    assert_eq!(result["interpreted_instructions"], 606);
    assert_eq!(result["gpu"]["draw_calls"], 2);
    assert_eq!(droidds_title_close(token.0), 0);
    token.0 = 0;
    fixture.preserved();
}
