//! CodexAstraUlt: Authored fixtures exercise exact runtime state, native fallback,
//! and sealed admission controls. No retail input or private library is used.

use super::*;
use droidds_runtime_probe::fixture;
use std::{
    fs::File,
    io::Write,
    os::fd::{AsRawFd, FromRawFd},
    os::unix::fs::PermissionsExt,
    path::PathBuf,
    process::Command,
    sync::{
        atomic::{AtomicU64, Ordering},
        Mutex,
    },
};
use zakuro_cpu::Bus;

static SERIAL: Mutex<()> = Mutex::new(());
static NEXT: AtomicU64 = AtomicU64::new(0);

// CodexAstraUlt: Additional generated CPU cases cover mode changes and actual
// callback interpretation through this same admitted worker and sealed library.
mod cpu_coverage;

// CodexAstraUlt: Each fixture owns its temporary directory and cleanup. These
// directories contain only synthetic data; private outputs are never touched.
struct Fixture {
    root: PathBuf,
    input: PathBuf,
    bundle: Vec<u8>,
    request: Value,
}

impl Fixture {
    fn new() -> Self {
        Self::from_image(fixture::image(0, 0, false))
    }

    // CodexAstraUlt: Alternate authored instruction streams reuse the same
    // independently generated container and sealed identity arrangement.
    fn from_image(image: Vec<u8>) -> Self {
        let root = std::env::temp_dir().join(format!(
            "droidds-native-worker-{}-{}",
            std::process::id(),
            NEXT.fetch_add(1, Ordering::Relaxed)
        ));
        fs::create_dir(&root).unwrap();
        let input = root.join("original.cxi");
        fs::write(&input, &image).unwrap();
        fs::set_permissions(&input, fs::Permissions::from_mode(0o400)).unwrap();
        let title = zakuro_fs::Title::load(&input).unwrap();
        let code = title.code().unwrap();
        let mut bundle = Vec::new();
        let mut components = Vec::new();
        for (kind, path, bytes) in [
            ("ncch_header", "identity/ncch-header.bin", &image[..512]),
            ("exheader", "identity/exheader.bin", title.exheader_bytes()),
            ("decompressed_code", "identity/code.bin", code.as_slice()),
        ] {
            components.push(json!({"kind":kind,"path":path,"bytes":bytes.len(),"sha256":"0".repeat(64),"offset":bundle.len()}));
            bundle.extend_from_slice(bytes);
        }
        let segments:Vec<_> = [title.exheader.text,title.exheader.rodata,title.exheader.data]
            .into_iter().zip(["text","rodata","data"]).enumerate().map(|(index,(segment,name))|json!({
                "name":name,"address":segment.address,"offset":index*4096,"size":segment.size,
                "mapped_bytes":u64::from(segment.num_pages)*4096,"sha256":"0".repeat(64),"hash_scope":"logical_segment_bytes"
            })).collect();
        // CodexAstraUlt: This is the trusted-parent worker unit boundary. Dummy
        // hashes test typed metadata; the separate Python pipeline tests bind
        // actual SHA-256 and ELF tables before constructing sealed requests.
        let request = json!({
            "schema_version":1,"kind":"droidds_private_native_run_request","abi":4,"generation":3,
            "preparation_sha256":"1".repeat(64),"contract_sha256":"2".repeat(64),
            "input":{"bytes":image.len(),"sha256":"3".repeat(64),"snapshot_path":input},
            "library":{"bytes":1,"sha256":"4".repeat(64),"descriptor":100},
            "identity_bundle":{"bytes":bundle.len(),"sha256":"5".repeat(64),"descriptor":101,"components":components},
            "prepared":{"program_id":format!("{:016x}",title.program_id()),"segments":segments,
                "bss_size":title.exheader.bss_size,"ncch_format_version":title.ncch.version,
                "remaster_version":title.exheader.remaster_version,"container":"ncch","cia_title_version":null},
            "route":"interpreter","limits":{"max_steps":100000,"max_cycles":100000,"max_frames":2,"max_seconds":90},
            "model":"old","static_table_audit":{"runtime_tables_validated":true,"library_loaded":false}
        });
        Self {
            root,
            input,
            bundle,
            request,
        }
    }

    fn typed(&self) -> Request {
        let value: Request = serde_json::from_value(self.request.clone()).unwrap();
        value.validate(102).unwrap();
        value
    }

    fn native_library(&self) -> File {
        let source = self.root.join("generated");
        let generated = droidds_runtime_probe::producer::emit(&source).unwrap();
        self.compile_library(&source, &source, &generated["sources"])
    }

    // CodexAstraUlt: A custom original instruction stream goes through the
    // production compiler, retaining real liveness/budget synchronization.
    fn prepared_native_library(&self) -> File {
        let prepared = self.root.join("prepared");
        let generated = droidds_title_builder::prepare(&self.input, &prepared).unwrap();
        self.compile_library(
            &prepared,
            &prepared.join("generated"),
            &generated["sources"],
        )
    }

    // CodexAstraUlt: Share the same native compile flags for both authored
    // fixtures. Only fresh test output is linked and sealed for the worker.
    fn compile_library(&self, source: &Path, include: &Path, sources: &Value) -> File {
        let output = self.root.join("original.so");
        let mut command = Command::new("cc");
        command
            .args([
                "-O2",
                "-ffp-contract=off",
                "-fno-math-errno",
                "-fPIC",
                "-shared",
                "-Wl,--no-undefined",
                "-o",
            ])
            .arg(&output)
            .arg("-I")
            .arg(include);
        for name in sources.as_array().unwrap() {
            command.arg(source.join(name.as_str().unwrap()));
        }
        let result = command
            .arg("-lm")
            .output()
            .expect("installed C compiler required");
        assert!(
            result.status.success(),
            "{}",
            String::from_utf8_lossy(&result.stderr)
        );
        sealed(&fs::read(output).unwrap())
    }
}

impl Drop for Fixture {
    fn drop(&mut self) {
        fs::remove_dir_all(&self.root).unwrap();
    }
}

// CodexAstraUlt: The same kernel sealing flags as the parent are used in tests;
// failures are hard test failures, never a skipped host capability check.
fn memory_file(bytes: &[u8], seal: bool) -> File {
    let name = std::ffi::CString::new("droidds-original-worker-test").unwrap();
    let fd =
        unsafe { libc::memfd_create(name.as_ptr(), libc::MFD_CLOEXEC | libc::MFD_ALLOW_SEALING) };
    assert!(fd >= 0, "Linux memfd required");
    let mut file = unsafe { File::from_raw_fd(fd) };
    file.write_all(bytes).unwrap();
    if seal {
        let flags =
            libc::F_SEAL_WRITE | libc::F_SEAL_GROW | libc::F_SEAL_SHRINK | libc::F_SEAL_SEAL;
        assert_eq!(unsafe { libc::fcntl(fd, libc::F_ADD_SEALS, flags) }, 0);
    }
    file
}
fn sealed(bytes: &[u8]) -> File {
    memory_file(bytes, true)
}

#[test]
fn sealed_admission_requires_all_seals_and_exact_nonempty_size() {
    let file = sealed(b"original");
    let accepted = SealedFile::open(file.as_raw_fd(), 8, Some(8)).unwrap();
    assert_eq!(&accepted.map().unwrap()[..], b"original");
    for (maximum, exact) in [(7, None), (8, Some(7)), (8, Some(9))] {
        assert!(SealedFile::open(file.as_raw_fd(), maximum, exact).is_err());
    }
    assert!(SealedFile::open(0, 8, None).is_err());
    let empty = sealed(b"");
    assert!(SealedFile::open(empty.as_raw_fd(), 8, None).is_err());
    let mutable = memory_file(b"original", false);
    assert!(SealedFile::open(mutable.as_raw_fd(), 8, None).is_err());
}

#[test]
fn typed_requests_reject_unknown_duplicate_and_wrong_types() {
    let fixture = Fixture::new();
    fixture.typed();
    for key in ["route", "abi", "limits", "input"] {
        let mut value = fixture.request.clone();
        value[key] = json!(true);
        assert!(serde_json::from_value::<Request>(value).is_err());
    }
    let mut value = fixture.request.clone();
    value["unexpected_option"] = json!(1);
    assert!(serde_json::from_value::<Request>(value).is_err());
    let text = serde_json::to_string(&fixture.request).unwrap();
    let duplicated = text.replacen('{', "{\"abi\":4,", 1);
    assert!(serde_json::from_str::<Request>(&duplicated).is_err());
}

#[test]
fn request_contract_rejects_wrong_audit_limits_and_component_coverage() {
    let fixture = Fixture::new();
    let reject = |value: Value| {
        assert!(serde_json::from_value::<Request>(value)
            .unwrap()
            .validate(102)
            .is_err())
    };
    for key in ["abi", "generation"] {
        let mut value = fixture.request.clone();
        value[key] = json!(99);
        reject(value);
    }
    let mut value = fixture.request.clone();
    value["static_table_audit"]["runtime_tables_validated"] = json!(false);
    reject(value);
    let mut value = fixture.request.clone();
    value["limits"]["max_steps"] = json!(0);
    reject(value);
    let mut value = fixture.request.clone();
    value["library"]["descriptor"] = json!(101);
    reject(value);
    let mut value = fixture.request.clone();
    value["identity_bundle"]["components"][1]["offset"] = json!(511);
    reject(value);
    let mut value = fixture.request.clone();
    value["identity_bundle"]["components"][1]["offset"] = json!(513);
    reject(value);
    let mut value = fixture.request.clone();
    value["identity_bundle"]["components"][0]["path"] = json!("identity/../foreign");
    reject(value);
    let mut value = fixture.request.clone();
    value["prepared"]["segments"][1]["offset"] = json!(0);
    reject(value);
}

#[test]
fn sealed_request_runs_original_interpreter_and_preserves_inputs() {
    let _serial = SERIAL.lock().unwrap();
    let mut fixture = Fixture::new();
    let library = sealed(b"x");
    let bundle = sealed(&fixture.bundle);
    fixture.request["library"]["descriptor"] = json!(library.as_raw_fd());
    fixture.request["identity_bundle"]["descriptor"] = json!(bundle.as_raw_fd());
    let request = sealed(&serde_json::to_vec(&fixture.request).unwrap());
    let report = run_fd(request.as_raw_fd(), &fixture.root.join("runtime"));
    assert_eq!(report["status"], "guest_exited", "{report:#}");
    assert_eq!(report["observed"]["interpreted_instructions"], 606);
    assert_eq!(report["observed"]["recompiled_instructions"], 0);
    assert_eq!(report["observed"]["state"]["graphics"]["draw_calls"], 2);
    assert_eq!(report["library_loaded"], false);
    assert_eq!(report["runtime_binding_enforced"], true);
    assert_eq!(
        fs::read(&fixture.input).unwrap(),
        fixture::image(0, 0, false)
    );
    assert!(serde_json::to_vec(&report).unwrap().len() < 16384);
    let second = run_fd(request.as_raw_fd(), &fixture.root.join("runtime"));
    assert_eq!(second["status"], "load_error");
    assert_eq!(second["reason"], "runtime_data_directory_must_be_new");
}

#[test]
fn exact_runtime_identity_mismatches_stop_before_native_loading() {
    let _serial = SERIAL.lock().unwrap();
    let fixture = Fixture::new();
    let library = sealed(b"not a native library");
    let library = SealedFile::open(library.as_raw_fd(), 1024, None).unwrap();
    for (index, kind) in [
        (0, "ncch_header"),
        (1, "exheader"),
        (2, "decompressed_code"),
    ] {
        let mut request = fixture.typed();
        request.route = "native".into();
        let mut bundle = fixture.bundle.clone();
        let component = request
            .identity_bundle
            .components
            .iter()
            .find(|c| c.kind == kind)
            .unwrap();
        bundle[component.offset as usize] ^= 1;
        let mut report = envelope(Some(&request));
        let result = execute(
            &request,
            &library,
            &bundle,
            &fixture.root.join(format!("mismatch-{index}")),
            &mut report,
            Instant::now(),
            |_| {},
        );
        assert_eq!(
            result.unwrap_err(),
            format!("runtime_component_mismatch_{kind}")
        );
        assert_eq!(report["library_loaded"], false);
        assert_eq!(report["guest_execution_performed"], false);
    }
}

// CodexAstraUlt: A real interpreted loop reaches an exact cycle checkpoint and
// stops without manufacturing guest exit or rendering success from its budget.
#[test]
fn exact_cycle_checkpoint_and_budget_stop_are_separate_from_guest_exit() {
    let _serial = SERIAL.lock().unwrap();
    let mut image = fixture::image(0, 0, false);
    image[0x800..0x804].copy_from_slice(&0xeaff_fffeu32.to_le_bytes());
    let fixture = Fixture::from_image(image);
    let mut request = fixture.typed();
    request.limits.max_steps = 100_001;
    let file = sealed(b"unused interpreter library");
    let library = SealedFile::open(file.as_raw_fd(), 1024, None).unwrap();
    let mut report = envelope(Some(&request));
    execute(
        &request,
        &library,
        &fixture.bundle,
        &fixture.root.join("loop"),
        &mut report,
        Instant::now(),
        |_| {},
    )
    .unwrap();
    assert_eq!(report["status"], "budget_exhausted");
    assert_eq!(report["reason"], "cycle_budget");
    assert_eq!(report["observed"]["cycles"], 100_000);
    assert_eq!(report["observed"]["interpreted_instructions"], 100_000);
    assert_eq!(report["observed"]["state"]["guest_exited"], false);
    assert_eq!(report["checkpoints"].as_array().unwrap().len(), 1);
    assert_eq!(report["checkpoints"][0]["requested_cycle"], 100_000);
    assert_eq!(report["checkpoints"][0]["exact_cycle"], true);
    assert_eq!(
        report["checkpoints"][0]["state"],
        report["observed"]["state"]
    );
    assert_eq!(report["library_loaded"], false);
    assert!(report["synchronized_checkpoints"]
        .as_array()
        .unwrap()
        .is_empty());
}

// CodexAstraUlt: The actual generator may elide dead flags at a forced budget
// exit. Preserve that raw difference, then independently compare the materialized
// state at a later matching SVC without regenerating or changing the library.
#[test]
fn original_loop_retains_raw_flag_difference_and_matches_after_svc_sync() {
    let _serial = SERIAL.lock().unwrap();
    let mut image = fixture::image(0, 0, false);
    let words = [
        0xe59f_1028u32, // ldr r1, [pc, #40]: original 40000-iteration bound.
        0xe1a0_0000,
        0xe1a0_0000,
        0xe1a0_0000,
        0xe1a0_0000,
        0xe280_0001, // add r0, r0, #1.
        0xe150_0001, // cmp r0, r1.
        0xe1a0_0000,
        0xe1a0_0000,
        0x1aff_fffau32, // bne back to add; five instructions per iteration.
        0xef00_0028,    // GetSystemTick includes a 150-cycle service cost.
        0xef00_0003,    // ExitProcess.
        40_000,
    ];
    for (index, word) in words.into_iter().enumerate() {
        image[0x800 + index * 4..0x804 + index * 4].copy_from_slice(&word.to_le_bytes());
    }
    let fixture = Fixture::from_image(image);
    let original = fs::read(&fixture.input).unwrap();
    let file = fixture.prepared_native_library();
    let library = SealedFile::open(file.as_raw_fd(), request::LIBRARY_LIMIT, None).unwrap();
    let mut reports = Vec::new();
    for route in ["interpreter", "native"] {
        let mut request = fixture.typed();
        request.route = route.into();
        request.limits.max_steps = 500_000;
        request.limits.max_cycles = 2_000_000;
        let mut report = envelope(Some(&request));
        execute(
            &request,
            &library,
            &fixture.bundle,
            &fixture.root.join(route),
            &mut report,
            Instant::now(),
            |_| {},
        )
        .unwrap();
        assert_eq!(report["status"], "guest_exited", "{report:#}");
        assert_eq!(report["checkpoints"].as_array().unwrap().len(), 1);
        assert_eq!(
            report["synchronized_checkpoints"].as_array().unwrap().len(),
            1
        );
        reports.push(report);
    }
    assert_ne!(
        reports[0]["checkpoints"][0]["state"]["cpsr"],
        reports[1]["checkpoints"][0]["state"]["cpsr"]
    );
    for report in &reports {
        let sample = &report["synchronized_checkpoints"][0];
        assert_eq!(sample["requested_cycle"], 100_000);
        assert_eq!(sample["boundary"]["ordinal"], 1);
        assert_eq!(sample["boundary"]["cycle"], 200_156);
        assert_eq!(sample["boundary"]["cycle"], sample["state"]["cycles"]);
        assert_eq!(sample["boundary"]["number"], 0x28);
        assert_eq!(sample["boundary"]["svc_pc"], fixture::TEXT + 40);
        assert_eq!(sample["boundary"]["thread_guest_id"], 0);
        assert_eq!(sample["state"]["cpsr"], 0x6000_001f);
    }
    assert_eq!(
        reports[0]["synchronized_checkpoints"][0]["boundary"],
        reports[1]["synchronized_checkpoints"][0]["boundary"]
    );
    assert_eq!(
        reports[0]["synchronized_checkpoints"][0]["state"],
        reports[1]["synchronized_checkpoints"][0]["state"]
    );
    assert_eq!(
        reports[0]["synchronized_checkpoints"][0]["instructions"]["interpreted"],
        200_006
    );
    assert_eq!(
        reports[1]["synchronized_checkpoints"][0]["instructions"]["recompiled"],
        200_006
    );
    assert_eq!(
        reports[1]["synchronized_checkpoints"][0]["instructions"]["callback_interpreted"],
        0
    );
    assert_eq!(
        reports[0]["observed"]["state"],
        reports[1]["observed"]["state"]
    );
    assert_eq!(fs::read(&fixture.input).unwrap(), original);
}

// CodexAstraUlt: Native fixture generation intentionally excludes the authored
// helper, proving that protected native dispatch still executes genuine fallback.
// The parent Python integration separately covers strict preparation's full text.
#[test]
fn admitted_original_native_execution_matches_interpreter_pixels_memory_and_fallback() {
    let _serial = SERIAL.lock().unwrap();
    let fixture = Fixture::new();
    let file = fixture.native_library();
    let library = SealedFile::open(file.as_raw_fd(), request::LIBRARY_LIMIT, None).unwrap();
    let mut reports = Vec::new();
    for route in ["interpreter", "native"] {
        let mut request = fixture.typed();
        request.route = route.into();
        let mut report = envelope(Some(&request));
        execute(
            &request,
            &library,
            &fixture.bundle,
            &fixture.root.join(route),
            &mut report,
            Instant::now(),
            |system| {
                assert_eq!(system.cpu.cycles, 606);
                assert_eq!(system.memory.read32(fixture::DATA), fixture::CHECKPOINT);
                assert_eq!(system.memory.read32(fixture::DATA + 4), 1);
                assert_eq!(system.gpu.draw_calls, 2);
                assert_eq!(system.gpu.vertices_drawn, 6);
                // CodexAstraUlt: Independently decode the original 8x8 ABGR tile;
                // the expected colors do not come from the production rasterizer.
                let expected = fixture::expected_pixels();
                for (index, expected) in expected.iter().enumerate() {
                    let (x, y) = (index % 8, index / 8);
                    let offset = (0..3).fold(0, |at, bit| {
                        at | ((x >> bit) & 1) << (2 * bit) | ((y >> bit) & 1) << (2 * bit + 1)
                    }) * 4;
                    let mut pixel = [0u8; 4];
                    system
                        .memory
                        .read_bytes(fixture::COLOR + offset as u32, &mut pixel);
                    assert_eq!([pixel[3], pixel[2], pixel[1], pixel[0]], *expected);
                }
            },
        )
        .unwrap();
        assert_eq!(report["status"], "guest_exited", "{report:#}");
        reports.push(report);
    }
    assert_eq!(
        reports[0]["observed"]["state"],
        reports[1]["observed"]["state"]
    );
    assert_eq!(reports[0]["observed"]["interpreted_instructions"], 606);
    assert_eq!(reports[1]["observed"]["interpreted_instructions"], 2);
    assert_eq!(reports[1]["observed"]["recompiled_instructions"], 604);
    assert_eq!(
        reports[1]["observed"]["native_callback_fallback_instructions"],
        0
    );
    assert_eq!(reports[1]["library_loaded"], true);
}
