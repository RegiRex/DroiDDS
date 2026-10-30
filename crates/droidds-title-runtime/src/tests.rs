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
        hardware: false
    })
    .is_err());
    fixture.preserved();
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
            hardware: false
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
    assert!(session.slice(InputState::default()).is_err());
    assert_eq!(session.report()["cycles"], cycles);
    assert!(session.report().to_string().len() < 8192);
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
    let mut session = Session::open(OpenOptions {
        manifest_json: &serde_json::to_vec(&fixture.manifest).unwrap(),
        input: &fixture.input,
        native_directory: &fixture.native,
        data_directory: &fixture.data,
        native: true,
        hardware: true,
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
    assert!(report["gpu"]["hardware"]["submissions"].as_u64().unwrap() > 0);
    assert_eq!(report["gpu"]["hardware"]["software_raster_fallbacks"], 0);
    assert_eq!(report["gpu"]["hardware"]["draw_errors"], 0);
    assert_eq!(report["gpu"]["hardware"]["resource_limit_events"], 0);
    drop(session);
    fixture.preserved();
}
