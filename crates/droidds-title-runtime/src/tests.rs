//! CodexAstraUlt: Authored containers and real generated libraries exercise the
//! generic runtime; no private game inputs or device-performance claims enter CI.

use super::*;
use droidds_runtime_probe::{fixture, homebrew};
use sha2::{Digest, Sha256};
use std::{
    fs,
    path::PathBuf,
    process::Command,
    sync::{
        atomic::{AtomicU64, Ordering},
        Mutex,
    },
};
use zakuro_cpu::Bus;

// CodexAstraUlt: Authored guest FS IPC checks reuse the exact admitted fixture
// builder while exercising saves through the CPU/service path, not host writes.
#[path = "save_tests.rs"]
mod save_tests;

// CodexAstraUlt: Yielded host work must preserve real guest HID transitions.
#[path = "hid_tests.rs"]
mod hid_tests;

static NEXT: AtomicU64 = AtomicU64::new(0);
static SERIAL: Mutex<()> = Mutex::new(());

fn digest(bytes: &[u8]) -> String {
    format!("{:x}", Sha256::digest(bytes))
}

struct Fixture {
    root: PathBuf,
    input: PathBuf,
    native: PathBuf,
    data: PathBuf,
    manifest: Value,
}

impl Fixture {
    // CodexAstraUlt: The expected manifest is assembled independently from the
    // parser-visible original bytes; every component has a real SHA-256 identity.
    fn new(image: Vec<u8>, compile: bool) -> Self {
        let root = std::env::temp_dir().join(format!(
            "droidds-title-runtime-{}-{}",
            std::process::id(),
            NEXT.fetch_add(1, Ordering::Relaxed)
        ));
        fs::create_dir(&root).unwrap();
        let input = root.join("owned-original.cxi");
        let native = root.join("installer");
        let data = root.join("runtime");
        fs::create_dir(&native).unwrap();
        fs::create_dir(&data).unwrap();
        fs::write(&input, &image).unwrap();
        fs::write(
            data.join("save-sentinel.bin"),
            b"preserve existing save bytes",
        )
        .unwrap();
        let library = native.join("libdroidds_title.so");
        if compile {
            let generated = root.join("generated");
            let report = droidds_title_builder::prepare(&input, &generated).unwrap();
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
                .arg(&library)
                .arg("-I")
                .arg(generated.join("generated"));
            for source in report["sources"].as_array().unwrap() {
                command.arg(generated.join(source.as_str().unwrap()));
            }
            let result = command.arg("-lm").output().unwrap();
            assert!(
                result.status.success(),
                "{}",
                String::from_utf8_lossy(&result.stderr)
            );
        } else {
            fs::write(&library, b"original unused interpreter-only marker").unwrap();
        }
        let title = zakuro_fs::Title::load(&input).unwrap();
        let code = title.code().unwrap();
        let components: Vec<_> = [
            ("ncch_header", "identity/ncch-header.bin", &image[..512]),
            ("exheader", "identity/exheader.bin", title.exheader_bytes()),
            ("decompressed_code", "identity/code.bin", code.as_slice()),
        ]
        .into_iter()
        .map(|(kind, path, bytes)| {
            json!({"kind":kind,"path":path,
            "bytes":bytes.len(),"sha256":digest(bytes)})
        })
        .collect();
        let mut offset = 0;
        let segments: Vec<_> = [
            title.exheader.text,
            title.exheader.rodata,
            title.exheader.data,
        ]
        .into_iter()
        .zip(["text", "rodata", "data"])
        .map(|(segment, name)| {
            let bytes = &code[offset..offset + segment.size as usize];
            let value = json!({"name":name,"address":segment.address,"offset":offset,
                    "size":segment.size,"mapped_bytes":u64::from(segment.num_pages)*4096,
                    "sha256":digest(bytes),"hash_scope":"logical_segment_bytes"});
            offset += segment.num_pages as usize * 4096;
            value
        })
        .collect();
        let library = fs::read(library).unwrap();
        let manifest = json!({"schema_version":1,"kind":"droidds_android_title",
            "program_id":format!("{:016x}",title.program_id()),"abi":4,"generation":3,
            "input":{"bytes":image.len(),"sha256":digest(&image)},
            "native":{"file":"libdroidds_title.so","bytes":library.len(),"sha256":digest(&library)},
            "prepared":{"container":"ncch","ncch_format_version":title.ncch.version,
                "remaster_version":title.exheader.remaster_version,"cia_title_version":null,
                "bss_size":title.exheader.bss_size,"segments":segments,"components":components}});
        Self {
            root,
            input,
            native,
            data,
            manifest,
        }
    }

    fn open(&self, native: bool) -> Result<Session, String> {
        self.open_manifest(&self.manifest, native)
    }

    fn open_manifest(&self, manifest: &Value, native: bool) -> Result<Session, String> {
        Session::open(OpenOptions {
            manifest_json: &serde_json::to_vec(manifest).unwrap(),
            input: &self.input,
            native_directory: &self.native,
            data_directory: &self.data,
            native,
            hardware: false,
            vertex_shading: VertexShading::Automatic,
        })
    }

    fn preserved(&self) {
        assert_eq!(
            fs::read(self.data.join("save-sentinel.bin")).unwrap(),
            b"preserve existing save bytes"
        );
        assert_eq!(
            digest(&fs::read(&self.input).unwrap()),
            self.manifest["input"]["sha256"]
        );
    }
}

impl Drop for Fixture {
    fn drop(&mut self) {
        let _ = fs::remove_dir_all(&self.root);
    }
}

#[test]
fn manifest_rejects_unknown_duplicate_and_noncanonical_identity_fields() {
    let fixture = Fixture::new(fixture::image(0, 0, false), false);
    let original = serde_json::to_vec(&fixture.manifest).unwrap();
    Manifest::parse(&original).unwrap();
    for (key, value) in [
        ("schema_version", json!(true)),
        ("extra", json!(0)),
        ("program_id", json!("0004000E12345678")),
    ] {
        let mut bad = fixture.manifest.clone();
        bad[key] = value;
        assert!(fixture.open_manifest(&bad, false).is_err());
    }
    let repeated = String::from_utf8(original)
        .unwrap()
        .replacen('{', "{\"schema_version\":1,", 1);
    assert!(Manifest::parse(repeated.as_bytes()).is_err());
    assert!(Manifest::parse(&vec![b' '; manifest::MAX_MANIFEST + 1]).is_err());
    fixture.preserved();
}

#[test]
fn input_component_layout_and_revision_mismatches_reject_before_execution() {
    let fixture = Fixture::new(fixture::image(0, 0, false), false);
    for mutation in [
        "input", "code", "header", "segment", "revision", "program", "missing", "module",
        "filename",
    ] {
        let mut bad = fixture.manifest.clone();
        match mutation {
            "input" => bad["input"]["sha256"] = json!("0".repeat(64)),
            "code" => bad["prepared"]["components"][2]["sha256"] = json!("0".repeat(64)),
            "header" => bad["prepared"]["components"][0]["sha256"] = json!("0".repeat(64)),
            "segment" => bad["prepared"]["segments"][0]["sha256"] = json!("0".repeat(64)),
            "revision" => bad["prepared"]["remaster_version"] = json!(1),
            "program" => bad["program_id"] = json!("0004000000001234"),
            "missing" => {
                bad["prepared"]["components"].as_array_mut().unwrap().pop();
            }
            "module" => bad["prepared"]["components"]
                .as_array_mut()
                .unwrap()
                .push(json!({
                "kind":"cro","path":"identity/module-0001.bin","source_path":"../unsafe",
                "module_name":"original","bytes":1,"sha256":"0".repeat(64)})),
            _ => bad["native"]["file"] = json!("../foreign.so"),
        }
        assert!(fixture.open_manifest(&bad, false).is_err(), "{mutation}");
    }
    fixture.preserved();
}

#[test]
fn actual_compressed_expansion_is_bounded_before_runtime_allocation() {
    let fixture = Fixture::new(fixture::image(0, 0, false), false);
    let mut image = fs::read(&fixture.input).unwrap();
    let title = zakuro_fs::Title::load(&fixture.input).unwrap();
    let code_len = title.exefs_file(".code").unwrap().len();
    drop(title);
    image[0x20d] |= 1;
    image[0x800 + code_len - 4..0x800 + code_len].copy_from_slice(&0x0400_0001u32.to_le_bytes());
    fs::write(&fixture.input, &image).unwrap();
    let mut manifest = fixture.manifest.clone();
    manifest["input"]["sha256"] = json!(digest(&image));
    let error = fixture.open_manifest(&manifest, false).err().unwrap();
    assert_eq!(error, "title_preflight_code_size_rejected");
    assert_eq!(
        fs::read(fixture.data.join("save-sentinel.bin")).unwrap(),
        b"preserve existing save bytes"
    );
}

#[test]
fn native_hash_rejection_and_missing_input_preserve_saves() {
    let fixture = Fixture::new(fixture::image(0, 0, false), false);
    let mut bad = fixture.manifest.clone();
    bad["native"]["sha256"] = json!("0".repeat(64));
    assert!(fixture
        .open_manifest(&bad, true)
        .err()
        .unwrap()
        .contains("identity_mismatch"));
    assert!(Session::open(OpenOptions {
        manifest_json: &serde_json::to_vec(&fixture.manifest).unwrap(),
        input: &fixture.root.join("missing"),
        native_directory: &fixture.native,
        data_directory: &fixture.data,
        native: false,
        hardware: false,
        vertex_shading: VertexShading::Automatic,
    })
    .is_err());
    fixture.preserved();
}

// CodexAstraUlt: A forced Vulkan experiment cannot be silently relabeled as a
// software run, and rejecting it must leave the imported input/save untouched.
#[test]
fn explicit_vertex_policies_require_hardware_before_title_admission() {
    let fixture = Fixture::new(fixture::image(0, 0, false), false);
    for vertex_shading in [VertexShading::Cpu, VertexShading::Gpu] {
        let result = Session::open(OpenOptions {
            manifest_json: &serde_json::to_vec(&fixture.manifest).unwrap(),
            input: &fixture.input,
            native_directory: &fixture.native,
            data_directory: &fixture.data,
            native: false,
            hardware: false,
            vertex_shading,
        });
        assert_eq!(result.err().unwrap(), "title_vertex_policy_requires_vulkan");
        fixture.preserved();
    }
    let session = fixture.open(false).unwrap();
    assert_eq!(session.report()["vertex_shading_policy"], "automatic");
    assert_eq!(session.report()["renderer"], "software");
    assert!(session.report()["gpu"]["hardware"].is_null());
    // CodexAstraUlt: No CPU dispatch occurred, so new scope evidence must be
    // present and zero rather than missing or inherited from another session.
    for name in ["svc", "frame", "audio"] {
        assert_eq!(
            session.report()["core_work"][name],
            json!({
            "calls":0,"wall_nanoseconds":0,"nested_command_wall_nanoseconds":0})
        );
    }
}

#[test]
fn optional_overlays_and_symlinked_inputs_are_rejected_without_cleanup() {
    let fixture = Fixture::new(fixture::image(0, 0, false), false);
    fs::create_dir(fixture.data.join("mods")).unwrap();
    fs::write(
        fixture.data.join("mods/keep"),
        b"unrelated existing content",
    )
    .unwrap();
    assert!(fixture.open(false).err().unwrap().contains("overlays"));
    assert_eq!(
        fs::read(fixture.data.join("mods/keep")).unwrap(),
        b"unrelated existing content"
    );
    #[cfg(unix)]
    {
        let alias = fixture.root.join("alias.cxi");
        std::os::unix::fs::symlink(&fixture.input, &alias).unwrap();
        assert!(Session::open(OpenOptions {
            manifest_json: &serde_json::to_vec(&fixture.manifest).unwrap(),
            input: &alias,
            native_directory: &fixture.native,
            data_directory: &fixture.data,
            native: false,
            hardware: false,
            vertex_shading: VertexShading::Automatic,
        })
        .err()
        .unwrap()
        .contains("symlink"));
    }
    fixture.preserved();
}

#[test]
fn progressing_slice_yields_without_invented_frames_or_fatal_budget() {
    let mut image = fixture::image(0, 0, false);
    image[0x800..0x804].copy_from_slice(&0xeaff_fffeu32.to_le_bytes());
    let fixture = Fixture::new(image, false);
    let mut session = fixture.open(false).unwrap();
    for n in 1..=3 {
        let slice = session
            .advance(InputState::default(), 7, Duration::from_secs(1))
            .unwrap();
        assert!(slice.top.is_none() && slice.bottom.is_none() && !slice.exited);
        assert_eq!(slice.cycles, n * 7);
        assert_eq!(session.report()["status"], "running");
    }
    assert_eq!(session.report()["yielded_slices"], 3);
    fixture.preserved();
}

#[test]
fn pause_resume_close_and_reopen_preserve_guest_and_durable_data() {
    let fixture = Fixture::new(homebrew::fixture::image(), false);
    let mut session = fixture.open(false).unwrap();
    session
        .advance(InputState::default(), 5, Duration::from_secs(1))
        .unwrap();
    let cycles = session.report()["cycles"].clone();
    session.pause();
    assert!(session
        .slice(InputState::default())
        .err()
        .unwrap()
        .contains("paused"));
    assert_eq!(session.report()["cycles"], cycles);
    assert_eq!(session.report()["status"], "paused");
    session.resume();
    session
        .advance(InputState::default(), 5, Duration::from_secs(1))
        .unwrap();
    assert!(session.report()["cycles"].as_u64().unwrap() > cycles.as_u64().unwrap());
    drop(session);
    fixture.preserved();
    let reopened = fixture.open(false).unwrap();
    assert_eq!(reopened.report()["cycles"], 0);
    fixture.preserved();
}

#[test]
fn unsupported_guest_instruction_stops_and_retains_a_bounded_report() {
    let mut image = fixture::image(0, 0, false);
    image[0x800..0x804].copy_from_slice(&0xe120_0070u32.to_le_bytes()); // Authored BKPT #0.
    let fixture = Fixture::new(image, false);
    let mut session = fixture.open(false).unwrap();
    assert!(session.slice(InputState::default()).is_err());
    let cycles = session.report()["cycles"].clone();
    assert_eq!(session.report()["status"], "failed");
    // CodexAstraUlt: Report the trap location without exposing its immediate,
    // instruction word or raw guest text; the first observed cause stays fixed.
    let blocker = session.report()["first_blocker"].clone();
    assert_eq!(blocker["category"], "breakpoint");
    assert_eq!(blocker["fault_pc"], 0x0010_0000);
    assert!(blocker.get("opcode").is_none() && blocker.get("imm").is_none());
    session.system.unimplemented_svcs.insert(0x7f);
    session.pause();
    session.resume();
    assert!(session.slice(InputState::default()).is_err());
    assert_eq!(session.report()["cycles"], cycles);
    assert_eq!(session.report()["first_blocker"], blocker);
    assert!(session.report().to_string().len() < 8192);
    fixture.preserved();
}

// CodexAstraUlt: Execute an authored unsupported SVC through the actual CPU
// dispatcher; preserve its number and stop before the following instruction.
#[test]
fn unsupported_svc_reports_number_without_advancing_after_failure() {
    let mut image = fixture::image(0, 0, false);
    image[0x800..0x804].copy_from_slice(&0xef00_007fu32.to_le_bytes());
    let fixture = Fixture::new(image, false);
    let mut session = fixture.open(false).unwrap();
    assert!(session.report()["first_blocker"].is_null());
    assert_eq!(session.report()["memory_faults"]["distinct_pages"], 0);
    assert_eq!(
        session.slice(InputState::default()).err().unwrap(),
        "title_runtime_blocker"
    );
    let report = session.report();
    assert_eq!(report["first_blocker"]["category"], "unsupported_svc");
    assert_eq!(report["first_blocker"]["svc"], 0x7f);
    assert_eq!(report["first_blocker"]["distinct_svcs"], 1);
    assert_eq!(report["first_blocker"]["observed_pc"], 0x0010_0004);
    assert_eq!(report["interpreted_instructions"], 1);
    assert!(session.slice(InputState::default()).is_err());
    assert_eq!(session.report(), report);
    fixture.preserved();
}

// CodexAstraUlt: A real guest LDR from unmapped memory must identify its page
// rather than leave a generic runtime_blocker with every visible count zero.
#[test]
fn guest_unmapped_read_reports_a_bounded_memory_observation() {
    let mut image = fixture::image(0, 0, false);
    // MOV r0,#0x30000000; LDR r1,[r0]; B .
    for (index, word) in [0xe3a0_0203u32, 0xe590_1000, 0xeaff_fffe]
        .into_iter()
        .enumerate()
    {
        image[0x800 + index * 4..0x804 + index * 4].copy_from_slice(&word.to_le_bytes());
    }
    let fixture = Fixture::new(image, false);
    let mut session = fixture.open(false).unwrap();
    assert_eq!(
        session.slice(InputState::default()).err().unwrap(),
        "title_runtime_blocker"
    );
    let report = session.report();
    assert_eq!(report["interpreted_instructions"], 2);
    assert_eq!(report["first_blocker"]["category"], "memory_fault");
    assert_eq!(report["first_blocker"]["observed_pc"], 0x0010_0008);
    assert_eq!(report["memory_faults"]["distinct_pages"], 1);
    assert_eq!(
        report["memory_faults"]["sample"]["page_address"],
        0x3000_0000
    );
    assert_eq!(report["memory_faults"]["sample"]["access_count"], 1);
    assert_eq!(
        report["first_blocker"]["memory_faults"],
        report["memory_faults"]
    );
    assert!(session.slice(InputState::default()).is_err());
    assert_eq!(session.report(), report);
    fixture.preserved();
}

// CodexAstraUlt: Drive real IPC rejection using an original request, retaining
// only its service/command identity. Invalid names cannot expand the report or
// leak a request payload through the diagnostic identifier.
#[test]
fn rejected_service_reports_bounded_identifiers_without_request_payload() {
    use zakuro_core::kernel::ipc::{CommandBuffer, Header};
    use zakuro_core::services::{handle_request, Target};

    for name in ["cfg:u".to_string(), "test/\n".repeat(16_384)] {
        let mut image = fixture::image(0, 0, false);
        image[0x800..0x804].copy_from_slice(&0xeaff_fffeu32.to_le_bytes());
        let fixture = Fixture::new(image, false);
        let mut session = fixture.open(false).unwrap();
        session
            .advance(InputState::default(), 1, Duration::from_secs(1))
            .unwrap();
        let buffer = CommandBuffer::new(session.system.kernel.current().unwrap().tls);
        buffer.set(&mut session.system.memory, 0, Header::new(0xffff, 1, 0).0);
        buffer.set(&mut session.system.memory, 1, 0x7365_6372);
        handle_request(&mut session.system, Target::service(name.clone(), 0));
        let cycles = session.system.cpu.cycles;
        assert_eq!(
            session.slice(InputState::default()).err().unwrap(),
            "title_runtime_blocker"
        );
        let report = session.report();
        let blocker = &report["first_blocker"];
        assert_eq!(blocker["category"], "unsupported_service");
        assert_eq!(blocker["command"], 0xffff);
        assert_eq!(blocker["request_count"], 1);
        assert_eq!(blocker["distinct_commands"], 1);
        assert_eq!(blocker["service_truncated"], name.len() > 16);
        if name == "cfg:u" {
            assert_eq!(blocker["service"], "cfg:u");
        } else {
            assert_eq!(blocker["service"], "test??test??test");
        }
        assert_eq!(report["cycles"], cycles);
        assert!(blocker.get("args").is_none());
        assert!(report.to_string().len() < 8192);
        fixture.preserved();
    }
}

// CodexAstraUlt: Several observations from one core dispatch have no reliable
// chronological ordering. Follow the guard order and keep fatal guest strings
// out of exported reports even when no finer CPU/service metadata exists.
#[test]
fn first_blocker_uses_guard_priority_and_omits_guest_fatal_text() {
    let fixture = Fixture::new(fixture::image(0, 0, false), false);
    for with_svc in [false, true] {
        let mut session = fixture.open(false).unwrap();
        session
            .system
            .fatal_errors
            .push("PRIVATE ORIGINAL FIXTURE ERROR".repeat(4096));
        if with_svc {
            session.system.unimplemented_svcs.insert(0x80);
            session.system.unimplemented_svcs.insert(0x7f);
            session.system.memory.read32(0x3000_0000);
        }
        assert!(session.slice(InputState::default()).is_err());
        let report = session.report();
        assert_eq!(
            report["first_blocker"]["category"],
            if with_svc {
                "unsupported_svc"
            } else {
                "guest_fatal_error"
            }
        );
        if with_svc {
            assert_eq!(report["first_blocker"]["svc"], 0x7f);
            assert_eq!(report["first_blocker"]["selection"], "lowest_svc_number");
            assert_eq!(report["memory_faults"]["distinct_pages"], 1);
        } else {
            assert_eq!(report["first_blocker"]["count"], 1);
        }
        assert_eq!(report["interpreted_instructions"], 0);
        assert!(!report.to_string().contains("PRIVATE ORIGINAL"));
        assert!(report.to_string().len() < 8192);
        fixture.preserved();
    }
}

// CodexAstraUlt: A live route mismatch still stops before guest execution, and
// an existing machine blocker retains priority over it after the guard change.
#[test]
fn compact_draw_guard_preserves_route_fail_stop_and_machine_priority() {
    let fixture = Fixture::new(fixture::image(0, 0, false), false);
    for with_machine_blocker in [false, true] {
        let mut session = fixture.open(false).unwrap();
        session.hardware = true;
        if with_machine_blocker {
            session.system.unimplemented_svcs.insert(0x7f);
        }
        assert_eq!(
            session.slice(InputState::default()).err().unwrap(),
            if with_machine_blocker {
                "title_runtime_blocker"
            } else {
                "title_renderer_route_changed"
            }
        );
        let report = session.report();
        assert_eq!(
            report["first_blocker"]["category"],
            if with_machine_blocker {
                "unsupported_svc"
            } else {
                "renderer_route_changed"
            }
        );
        assert_eq!(report["interpreted_instructions"], 0);
        assert_eq!(report["native_instructions"], 0);
        fixture.preserved();
    }
}

// CodexAstraUlt: Invalid input is rejected before machine guards, so an
// unrelated existing diagnostic counter must not replace the actual cause.
#[test]
fn direct_input_guard_keeps_its_cause_despite_existing_machine_counters() {
    let fixture = Fixture::new(fixture::image(0, 0, false), false);
    let mut session = fixture.open(false).unwrap();
    session.system.unimplemented_svcs.insert(0x7f);
    let invalid = InputState {
        touch: Some((320, 0)),
        ..InputState::default()
    };
    assert_eq!(session.slice(invalid).err().unwrap(), "title_input_invalid");
    let report = session.report();
    assert_eq!(report["first_blocker"]["category"], "invalid_input");
    assert_eq!(report["unsupported_svcs"], 1);
    assert_eq!(report["interpreted_instructions"], 0);
    fixture.preserved();
}

#[test]
fn actual_generated_native_title_executes_and_exits_without_fabricated_frame() {
    let _serial = SERIAL.lock().unwrap();
    let fixture = Fixture::new(fixture::image(0, 0, false), true);
    let mut session = fixture.open(true).unwrap();
    let mut exited = false;
    for _ in 0..100 {
        let slice = session.slice(InputState::default()).unwrap();
        assert!(slice.top.is_none() && slice.bottom.is_none());
        if slice.exited {
            exited = true;
            break;
        }
    }
    assert!(exited);
    let report = session.report();
    assert_eq!(report["cycles"], 606);
    assert_eq!(report["native_instructions"], 606);
    assert_eq!(report["gpu"]["draw_calls"], 2);
    assert_eq!(report["frames_delivered"], 0);
    assert!(session.system.memory.base_code_fence_active());
    drop(session);
    fixture.preserved();
}

// CodexAstraUlt: Settle four actual guest frames for each input and compare all
// pixels against independently authored geometry plus actual nonzero guest PCM.
fn four_frames(session: &mut Session, input: InputState) -> Slice {
    let target = session.system.frames + 4;
    let mut settled_pcm = Vec::new();
    for _ in 0..10_000 {
        let before = session.system.frames;
        let mut slice = session.slice(input).unwrap();
        if before >= target - 2 {
            settled_pcm.extend_from_slice(&slice.pcm);
        }
        if slice.frames >= target && slice.top.is_some() {
            slice.pcm = settled_pcm;
            return slice;
        }
    }
    panic!("original interactive guest did not reach four bounded frames");
}

// CodexAstraUlt: Allow an arbitrary slice phase but require real stereo samples,
// exact amplitude and every complete sign run's independent expected period.
fn tone(samples: &[[i16; 2]], period: usize) {
    assert!(samples.len() >= 160);
    assert!(samples
        .iter()
        .all(|sample| sample[0] == sample[1] && sample[0].unsigned_abs() == 2000));
    let changes: Vec<_> = samples
        .windows(2)
        .enumerate()
        .filter_map(|(index, pair)| (pair[0][0] != pair[1][0]).then_some(index + 1))
        .collect();
    assert!(changes.len() >= 3);
    assert!(changes.windows(2).all(|pair| pair[1] - pair[0] == period));
}

// CodexAstraUlt: Actual original guest calls, frames and audio exercise all
// fixed scopes. Validate the exported nesting without treating command time as
// disjoint from its enclosing service/frame/audio work or requiring host speed.
fn assert_core_work_report(report: &Value) {
    let work = report["core_work"].as_object().unwrap();
    assert_eq!(work.len(), 3);
    let mut nested_commands = 0;
    for name in ["svc", "frame", "audio"] {
        let scope = work[name].as_object().unwrap();
        assert_eq!(scope.len(), 3);
        assert!(scope["calls"].as_u64().unwrap() > 0, "missing {name} calls");
        let wall = scope["wall_nanoseconds"].as_u64().unwrap();
        let nested = scope["nested_command_wall_nanoseconds"].as_u64().unwrap();
        assert!(wall > 0, "missing {name} wall time");
        assert!(nested <= wall, "{name} nested work exceeds enclosing scope");
        nested_commands += nested;
    }
    assert_eq!(work["frame"]["calls"], report["frames"]);
    // CodexAstraUlt: This authored guest submits real commands through GSP;
    // an accidentally unrecorded nested subset must fail the oracle too.
    assert!(
        nested_commands > 0,
        "original guest commands were not attributed"
    );
    assert!(
        nested_commands
            <= report["gpu"]["command_processing_wall_nanoseconds"]
                .as_u64()
                .unwrap()
    );
}

#[test]
fn generic_session_delivers_original_pixels_audio_and_input_on_both_cpu_routes() {
    let _serial = SERIAL.lock().unwrap();
    let fixture = Fixture::new(homebrew::fixture::image(), true);
    let mut final_states = Vec::new();
    for native in [false, true] {
        let mut session = fixture.open(native).unwrap();
        let idle = four_frames(&mut session, InputState::default());
        tone(&idle.pcm, 40);
        assert_eq!(
            idle.top.unwrap(),
            homebrew::pica::expected_pixels(
                homebrew::pica::Panel::Top,
                homebrew::pica::VisualState {
                    x: 184,
                    y: 104,
                    active: false
                }
            )
        );
        assert_eq!(
            idle.bottom.unwrap(),
            homebrew::pica::expected_pixels(
                homebrew::pica::Panel::Bottom,
                homebrew::pica::VisualState {
                    x: 144,
                    y: 104,
                    active: false
                }
            )
        );
        let input = InputState {
            buttons: PadState::A | PadState::RIGHT | PadState::UP,
            touch: Some((247, 181)),
            ..InputState::default()
        };
        let active = four_frames(&mut session, input);
        tone(&active.pcm, 20);
        assert_eq!(
            active.top.unwrap(),
            homebrew::pica::expected_pixels(
                homebrew::pica::Panel::Top,
                homebrew::pica::VisualState {
                    x: 328,
                    y: 24,
                    active: true
                }
            )
        );
        assert_eq!(
            active.bottom.unwrap(),
            homebrew::pica::expected_pixels(
                homebrew::pica::Panel::Bottom,
                homebrew::pica::VisualState {
                    x: 231,
                    y: 165,
                    active: true
                }
            )
        );
        assert_eq!(
            session
                .system
                .memory
                .read32(homebrew::fixture::DATA + homebrew::fixture::BUTTONS_OFFSET),
            input.buttons.bits()
        );
        assert_eq!(
            session
                .system
                .memory
                .read32(homebrew::fixture::DATA + homebrew::fixture::TOUCH_X_OFFSET),
            247
        );
        assert!(session.pcm_nonzero_frames > 0);
        assert_core_work_report(&session.report());
        if native {
            assert!(session.report()["native_instructions"].as_u64().unwrap() > 0);
        }
        final_states.push(session.system.memory.read32(homebrew::fixture::DATA));
        drop(session);
        fixture.preserved();
    }
    assert_eq!(final_states, vec![homebrew::fixture::CHECKPOINT; 2]);
}

// CodexAstraUlt: Explicit opt-in makes actual Vulkan execution mandatory when
// selected; no absent ICD or software raster fallback is treated as a GPU pass.
#[cfg(feature = "vulkan-tests")]
#[test]
fn generic_native_vulkan_session_matches_original_image_and_audio_oracles() {
    let _serial = SERIAL.lock().unwrap();
    let fixture = Fixture::new(homebrew::fixture::image(), true);
    // CodexAstraUlt: Keep the automatic-route regression while explicitly
    // qualifying both vertex paths with the same independent pixel/PCM oracle.
    // Selection is per instance, so no process-global environment is changed.
    for vertex_shading in [
        VertexShading::Automatic,
        VertexShading::Cpu,
        VertexShading::Gpu,
    ] {
        native_vulkan_oracle(&fixture, vertex_shading);
    }
    fixture.preserved();
}

#[cfg(feature = "vulkan-tests")]
fn native_vulkan_oracle(fixture: &Fixture, vertex_shading: VertexShading) {
    let mut session = Session::open(OpenOptions {
        manifest_json: &serde_json::to_vec(&fixture.manifest).unwrap(),
        input: &fixture.input,
        native_directory: &fixture.native,
        data_directory: &fixture.data,
        native: true,
        hardware: true,
        vertex_shading,
    })
    .unwrap();
    let input = InputState {
        buttons: PadState::A | PadState::LEFT | PadState::DOWN,
        touch: Some((33, 44)),
        ..InputState::default()
    };
    let frame = four_frames(&mut session, input);
    assert_eq!(
        frame.top.unwrap(),
        homebrew::pica::expected_pixels(
            homebrew::pica::Panel::Top,
            homebrew::pica::VisualState {
                x: 40,
                y: 184,
                active: true
            }
        )
    );
    assert_eq!(
        frame.bottom.unwrap(),
        homebrew::pica::expected_pixels(
            homebrew::pica::Panel::Bottom,
            homebrew::pica::VisualState {
                x: 17,
                y: 28,
                active: true
            }
        )
    );
    tone(&frame.pcm, 20);
    let report = session.report();
    assert!(report["native_instructions"].as_u64().unwrap() > 0);
    assert_core_work_report(&report);
    assert!(report["gpu"]["hardware"]["submissions"].as_u64().unwrap() > 0);
    assert_eq!(report["gpu"]["hardware"]["software_raster_fallbacks"], 0);
    assert_eq!(report["gpu"]["hardware"]["draw_errors"], 0);
    assert_eq!(report["gpu"]["hardware"]["resource_limit_events"], 0);
    // CodexAstraUlt: A policy flag alone does not prove that its vertex path
    // recorded a draw. Placed vertices are already transformed, not a count of
    // individual CPU shader invocations or a software raster fallback.
    assert_eq!(report["vertex_shading_policy"], vertex_shading.as_str());
    let gpu = &report["gpu"]["hardware"];
    assert_eq!(gpu["vertex_shading_policy"], vertex_shading.as_str());
    // CodexAstraUlt: Successful authored routes must expose the complete
    // pipeline-failure schema with no failed foreground, worker or cache attempt.
    // An absent field cannot pass this object comparison as an implicit null.
    assert_eq!(
        gpu["pipeline_failures"],
        json!({"foreground":null,"background":null,"cache_probe":null})
    );
    // CodexAstraUlt: The required static variant matches Thor's unavailable
    // dynamic blend/logic state, rather than silently exercising host features.
    if std::env::var_os("ZAKURO_STATIC_BLEND").is_some() {
        assert_eq!(gpu["dynamic_blend"], false);
        assert_eq!(gpu["dynamic_logic_op"], false);
    }
    assert_eq!(
        gpu["recorded_draws"].as_u64().unwrap(),
        gpu["gpu_vertex_draws"].as_u64().unwrap() + gpu["placed_vertex_draws"].as_u64().unwrap()
    );
    match vertex_shading {
        VertexShading::Cpu => {
            assert_eq!(gpu["vertex_shading_on_gpu"], false);
            assert_eq!(gpu["gpu_vertex_draws"], 0);
            assert!(gpu["placed_vertex_draws"].as_u64().unwrap() > 0);
            // CodexAstraUlt: The original guest's small immediate draw must
            // actually decode and place on CPU, with no geometry/parallel work.
            let work = &report["gpu"]["vertex_processing"];
            assert_eq!(work["cpu_geometry_batches"], 0);
            assert_eq!(work["cpu_parallel_vertex_batches"], 0);
            for counter in [
                "input_decode_batches",
                "input_decode_wall_nanoseconds",
                "placement_batches",
                "placement_wall_nanoseconds",
            ] {
                assert!(
                    work[counter].as_u64().unwrap() > 0,
                    "missing CPU stage: {counter}"
                );
            }
            assert!(
                report["gpu"]["vertex_processing"]["cpu_batches"]
                    .as_u64()
                    .unwrap()
                    > 0
            );
            assert!(
                report["gpu"]["vertex_processing"]["cpu_vertex_inputs"]
                    .as_u64()
                    .unwrap()
                    > 0
            );
            assert!(
                report["gpu"]["vertex_processing"]["cpu_wall_nanoseconds"]
                    .as_u64()
                    .unwrap()
                    > 0
            );
        }
        VertexShading::Gpu => {
            assert_eq!(gpu["vertex_shading_on_gpu"], true);
            assert!(gpu["gpu_vertex_draws"].as_u64().unwrap() > 0);
            // CodexAstraUlt: The authored guest sends immediate attributes;
            // CPU input mapping still precedes successful GPU vertex shading.
            assert_eq!(report["gpu"]["vertex_processing"]["cpu_batches"], 0);
            // CodexAstraUlt: Each immediate draw maps inputs exactly once, but
            // its successful GPU route must avoid CPU shading and placement.
            let work = &report["gpu"]["vertex_processing"];
            assert_eq!(work["input_decode_batches"], gpu["gpu_vertex_draws"]);
            assert!(work["input_decode_wall_nanoseconds"].as_u64().unwrap() > 0);
            for counter in [
                "cpu_geometry_batches",
                "cpu_parallel_vertex_batches",
                "placement_batches",
                "placement_wall_nanoseconds",
            ] {
                assert_eq!(work[counter], 0, "unexpected CPU stage: {counter}");
            }
        }
        VertexShading::Automatic => {}
    }
    println!(
        "DroiDDS vertex oracle: requested={}, GPU selected={}, GPU draws={}, placed draws={}",
        vertex_shading.as_str(),
        gpu["vertex_shading_on_gpu"],
        gpu["gpu_vertex_draws"],
        gpu["placed_vertex_draws"]
    );
    drop(session);
    fixture.preserved();
}
