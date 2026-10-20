//! CodexAstraUlt: A single-thread owner advances the actual guest machine. Only
//! its HID samples, framebuffer readback and mixed PCM cross the frontend API.

use super::{fixture, Frame, InputState, AUDIO_SAMPLE_RATE};
use crate::require;
use serde_json::{json, Value};
use std::{
    fs,
    path::{Path, PathBuf},
    time::{Duration, Instant},
};
use zakuro_common::Screen;
use zakuro_core::{loader, services::hid, Config, StepOutcome, System, CYCLES_PER_FRAME};
use zakuro_cpu::Bus;

const TEXT_BYTES: usize = fixture::TEXT_BYTES as usize;
const MAX_FRAME_STEPS: u64 = 250_000;
const MAX_FRAME_WALL: Duration = Duration::from_secs(15);
const OWNERSHIP: &[u8] = b"DroidDS original visible homebrew v1\n";

// CodexAstraUlt: The fixed scratch namespace owns no saves, caches or user
// content. Interrupted runs reuse one file; normal teardown removes that file.
struct Scratch(PathBuf);

impl Scratch {
    fn prepare(directory: &Path) -> Result<Self, String> {
        require(
            directory.is_absolute(),
            "homebrew scratch must be an absolute path",
        )?;
        if directory.exists() {
            let meta = fs::symlink_metadata(directory).map_err(|error| error.to_string())?;
            require(
                meta.is_dir() && !meta.file_type().is_symlink(),
                "homebrew scratch is not an ordinary directory",
            )?;
        } else {
            fs::create_dir_all(directory).map_err(|error| error.to_string())?;
        }
        for entry in fs::read_dir(directory).map_err(|error| error.to_string())? {
            let entry = entry.map_err(|error| error.to_string())?;
            require(
                entry.file_name() == "droidds-homebrew-owner.txt"
                    || entry.file_name() == "homebrew-fixture.cxi",
                "homebrew scratch contains unrelated files",
            )?;
            require(
                entry
                    .file_type()
                    .map_err(|error| error.to_string())?
                    .is_file(),
                "homebrew scratch contains a nonordinary file",
            )?;
        }
        let owner = directory.join("droidds-homebrew-owner.txt");
        if owner.exists() {
            require(
                fs::read(&owner).map_err(|error| error.to_string())? == OWNERSHIP,
                "homebrew scratch ownership differs",
            )?;
        } else {
            require(
                !directory.join("homebrew-fixture.cxi").exists(),
                "homebrew scratch contains an unowned fixture",
            )?;
            fs::write(&owner, OWNERSHIP).map_err(|error| error.to_string())?;
        }
        Ok(Self(directory.to_path_buf()))
    }

    fn image_path(&self) -> PathBuf {
        self.0.join("homebrew-fixture.cxi")
    }
}

impl Drop for Scratch {
    fn drop(&mut self) {
        let path = self.image_path();
        if fs::symlink_metadata(&path)
            .is_ok_and(|meta| meta.is_file() && !meta.file_type().is_symlink())
        {
            let _ = fs::remove_file(path);
        }
    }
}

// CodexAstraUlt: This API deliberately makes no Send guarantee. JNI keeps it in
// its emulation thread's registry, and no audio or UI callback touches System.
pub struct Session {
    system: System,
    _scratch: Scratch,
    text: Vec<u8>,
    guard: Vec<u8>,
    native: bool,
    hardware: bool,
    device: Option<String>,
    paused: bool,
    pause_count: u64,
    resume_count: u64,
    steps: u64,
    pcm_samples: u64,
    pcm_nonzero_samples: u64,
    pcm_peak: u16,
    observed_buttons: u32,
    observed_touch_updates: u64,
    last_guest_serial: u32,
    frames_delivered: u64,
    failure: Option<String>,
}

impl Session {
    pub fn create(
        native_directory: &Path,
        scratch_directory: &Path,
        native: bool,
        hardware: bool,
    ) -> Result<Self, String> {
        require(
            native_directory.is_absolute() && native_directory.is_dir(),
            "homebrew native directory must exist and be absolute",
        )?;
        let scratch = Scratch::prepare(scratch_directory)?;
        fs::write(scratch.image_path(), fixture::image())
            .map_err(|error| format!("write original homebrew: {error}"))?;
        let mut system = loader::load(
            scratch.image_path(),
            Config {
                clock: Some(4_000_000_000_000),
                data_dir: Some(scratch_directory.to_path_buf()),
                find_recompiled: false,
                texture_packs: false,
                skip_idle_loops: false,
                ..Config::default()
            },
        )
        .map_err(|error| format!("load original homebrew: {error}"))?;
        if native {
            install_native(&mut system, &native_directory.join(fixture::LIBRARY))?;
        }
        // CodexAstraUlt: A requested hardware route must initialize explicitly;
        // the loader's compatibility fallback cannot qualify this diagnostic.
        let device = if hardware {
            Some(system.gpu.enable_hardware_renderer(1, None, None)?)
        } else {
            None
        };
        let mut text = vec![0; TEXT_BYTES];
        system.memory.read_bytes(fixture::TEXT, &mut text);
        Ok(Self {
            system,
            _scratch: scratch,
            text,
            guard: vec![0; TEXT_BYTES],
            native,
            hardware,
            device,
            paused: false,
            pause_count: 0,
            resume_count: 0,
            steps: 0,
            pcm_samples: 0,
            pcm_nonzero_samples: 0,
            pcm_peak: 0,
            observed_buttons: 0,
            observed_touch_updates: 0,
            last_guest_serial: 0,
            frames_delivered: 0,
            failure: None,
        })
    }

    pub fn frame(&mut self, input: InputState) -> Result<Frame, String> {
        self.frame_with_budget(input, MAX_FRAME_STEPS)
    }

    // CodexAstraUlt: Pause retains the guest and releases held controls. It does
    // not advance the machine or invent samples to keep an audio sink occupied.
    pub fn pause(&mut self) {
        if !self.paused {
            self.paused = true;
            self.pause_count += 1;
        }
        self.system.set_input(InputState::default());
    }

    pub fn resume(&mut self) {
        if self.paused {
            self.paused = false;
            self.resume_count += 1;
        }
    }

    fn check_code(&mut self) -> Result<(), String> {
        self.system
            .memory
            .read_bytes(fixture::TEXT, &mut self.guard);
        require(
            self.guard == self.text,
            "homebrew immutable executable text changed",
        )
    }

    fn frame_with_budget(&mut self, input: InputState, step_limit: u64) -> Result<Frame, String> {
        if self.paused {
            return Err("homebrew session is paused".into());
        }
        if let Some(error) = &self.failure {
            return Err(error.clone());
        }
        if self.system.exited {
            return Err("homebrew guest has exited".into());
        }
        let result = self.advance(input, step_limit);
        if let Err(error) = &result {
            self.failure = Some(error.clone());
        }
        result
    }

    fn advance(&mut self, input: InputState, step_limit: u64) -> Result<Frame, String> {
        require(
            input.touch.is_none_or(|(x, y)| x < 320 && y < 240),
            "homebrew touch lies outside the bottom screen",
        )?;
        require(
            [
                input.circle_x,
                input.circle_y,
                input.c_stick_x,
                input.c_stick_y,
                input.tilt[0],
                input.tilt[1],
            ]
            .iter()
            .all(|value| value.is_finite()),
            "homebrew input contains a nonfinite axis",
        )?;
        self.system.set_input(input);
        // CodexAstraUlt: System::run_frame normally samples HID. Our guarded
        // stepping preserves that actual service update once per host frame.
        hid::update(&mut self.system, input);
        let target = self.system.frames + 1;
        let start_cycles = self.system.cpu.cycles;
        let cycle_limit = start_cycles.saturating_add(CYCLES_PER_FRAME * 2 + 4096);
        let started = Instant::now();
        let mut completed = false;
        for _ in 0..step_limit {
            require(
                self.system.cpu.cycles < cycle_limit && started.elapsed() < MAX_FRAME_WALL,
                "homebrew frame cycle or wall budget exceeded",
            )?;
            self.check_code()?;
            let outcome = self.system.step(Some(
                self.system.cpu.cycles.saturating_add(4096).min(cycle_limit),
            ));
            self.steps += 1;
            self.check_code()?;
            match outcome {
                StepOutcome::Faulted => {
                    return Err(format!(
                        "homebrew guest fault at {:08x}",
                        self.system.cpu.regs[15]
                    ))
                }
                StepOutcome::Exited => {
                    completed = true;
                    break;
                }
                StepOutcome::Ran => {}
            }
            if self.system.frames >= target {
                completed = true;
                break;
            }
        }
        require(completed, "homebrew outer dispatch budget exceeded")?;
        self.validate_machine()?;
        let top = self.system.read_screen(Screen::Top);
        let bottom = self.system.read_screen(Screen::Bottom);
        let pcm = self.system.take_audio();
        require(
            top.len() == 400 * 240 * 4 && bottom.len() == 320 * 240 * 4,
            "homebrew scanout dimensions differ",
        )?;
        require(
            pcm.len() <= 160 * 8,
            "homebrew audio was not drained within a bounded frame",
        )?;
        self.pcm_samples += pcm.len() as u64;
        self.pcm_nonzero_samples += pcm.iter().filter(|sample| **sample != [0, 0]).count() as u64;
        self.pcm_peak = self.pcm_peak.max(
            pcm.iter()
                .flatten()
                .map(|sample| sample.unsigned_abs())
                .max()
                .unwrap_or(0),
        );
        self.frames_delivered += 1;
        self.validate_machine()?;
        let guest_serial = self.system.memory.read32(fixture::DATA + 4);
        // CodexAstraUlt: Manual input evidence comes from values the guest read
        // through HID, not from frontend event delivery or set_input calls.
        if guest_serial != self.last_guest_serial {
            self.observed_buttons |= self.system.memory.read32(fixture::DATA + 12);
            self.observed_touch_updates +=
                u64::from(self.system.memory.read32(fixture::DATA + 24) == 1);
            self.last_guest_serial = guest_serial;
        }
        Ok(Frame {
            top,
            bottom,
            pcm,
            guest_serial,
            frames: self.system.frames,
            exited: self.system.exited,
        })
    }

    fn validate_machine(&self) -> Result<(), String> {
        require(
            self.system.unimplemented_svcs.is_empty()
                && self.system.services.unimplemented.is_empty()
                && self.system.memory.fault_summary().is_empty()
                && self.system.prefetch_aborts.is_empty()
                && self.system.fatal_errors.is_empty(),
            "homebrew unsupported service/SVC, memory fault or fatal guest error",
        )?;
        let gpu = self.system.gpu.hardware_diagnostics();
        require(
            gpu.is_some() == self.hardware,
            "homebrew hardware activation differs",
        )?;
        if let Some(gpu) = gpu {
            require(
                gpu.draw_errors == 0
                    && gpu.software_raster_fallbacks == 0
                    && gpu.resource_limit_events == 0
                    && gpu.last_error.is_none(),
                "homebrew hardware error, fallback or resource limit",
            )?;
        }
        Ok(())
    }

    pub fn guest(&mut self) -> Value {
        let words = (0..18)
            .map(|i| self.system.memory.read32(fixture::DATA + i * 4))
            .collect::<Vec<_>>();
        json!({"checkpoint":words[0],"serial":words[1],"fallback_count":words[2],"buttons":words[3],
            "touch_x":words[4],"touch_y":words[5],"touch_valid":words[6],"top_x":words[7],"top_y":words[8],
            "bottom_x":words[9],"bottom_y":words[10],"tone_rate_bits":words[11],"service_error_stage":words[12],"exit_requested":words[13],
            "progress_stage":words[14],"dsp_enabled":words[15],"dsp_position":words[16],"dsp_buffer_id":words[17]})
    }

    pub fn report(&mut self) -> Value {
        let guest = self.guest();
        json!({"schema":1,"kind":"droidds-homebrew-session","fixture":fixture::IDENTITY,
            "status":if self.failure.is_some(){"failed"}else if self.system.exited{"exited"}else if self.paused{"paused"}else{"running"},
            "error":self.failure,"native":self.native,"renderer":if self.hardware{"vulkan"}else{"software"},
            "presentation":"rgba_readback","audio_sample_rate":AUDIO_SAMPLE_RATE,
            "frames":self.system.frames,"frames_delivered":self.frames_delivered,"guest":guest,
            "steps":self.steps,"cycles":self.system.cpu.cycles,"interpreted_instructions":self.system.interpreted_instructions,
            "recompiled_instructions":self.system.recompiled_instructions,
            "native_fallback_instructions":self.system.recompiled.as_ref().map_or(0,|library|library.fallbacks()),
            "pcm_samples":self.pcm_samples,"pcm_nonzero_samples":self.pcm_nonzero_samples,"pcm_peak":self.pcm_peak,
            "guest_observed_buttons":self.observed_buttons,"guest_observed_touch_updates":self.observed_touch_updates,
            "pause_count":self.pause_count,"resume_count":self.resume_count,
            "svc_unimplemented":self.system.unimplemented_svcs.len(),"service_unimplemented":self.system.services.unimplemented.len(),
            "memory_faults":self.system.memory.fault_summary().len(),"services_seen":self.system.services_seen,
            "command_lists":self.system.gpu.command_lists,"draw_calls":self.system.gpu.draw_calls,"vertices_drawn":self.system.gpu.vertices_drawn,
            "hardware":self.system.gpu.hardware_diagnostics(),"hardware_device":self.device,
            "dsp_running":self.system.services.dsp.running,"guest_exited":self.system.exited})
    }

    pub(super) fn budget_control(&mut self) -> Result<String, String> {
        self.frame_with_budget(InputState::default(), 1)
            .err()
            .filter(|error| error.contains("dispatch budget"))
            .ok_or_else(|| "homebrew one-step budget was not rejected".into())
    }

    pub(super) fn changed_code_control(&mut self) -> Result<String, String> {
        require(
            self.system.memory.write32_privileged(fixture::TEXT, 0),
            "homebrew code control could not mutate its private machine",
        )?;
        let error = self
            .frame(InputState::default())
            .err()
            .filter(|error| error.contains("immutable executable text"))
            .ok_or("homebrew modified code reached dispatch")?;
        require(
            self.steps == 0
                && self.system.cpu.cycles == 0
                && self.system.interpreted_instructions == 0
                && self.system.recompiled_instructions == 0,
            "homebrew changed code executed before rejection",
        )?;
        Ok(error)
    }
}

// CodexAstraUlt: Validate immutable source provenance before installing the real
// native bridge, retaining a deliberately missing helper for interpreter proof.
fn install_native(system: &mut System, path: &Path) -> Result<(), String> {
    let mut library = recomp_abi::Library::open(path)?;
    require(
        library.generation() == recomp_abi::GENERATION,
        "homebrew native ABI generation differs",
    )?;
    require(
        library
            .origins(0)
            .is_some_and(|origin| !origin.pieces().is_empty() && !origin.functions().is_empty()),
        "homebrew native origins missing",
    )?;
    let end = fixture::TEXT + fixture::native_text().len() as u32;
    let mut outside = false;
    let stale = library.check(0, 0, |address, out| {
        if address < fixture::TEXT
            || address
                .checked_add(out.len() as u32)
                .is_none_or(|last| last > end)
        {
            outside = true;
            out.fill(0);
        } else {
            system.memory.read_bytes(address, out);
        }
    });
    require(
        !outside && stale == 0 && library.lookup(fixture::TEXT).is_some(),
        "homebrew native origins stale or entry missing",
    )?;
    require(
        library.lookup(fixture::FALLBACK).is_none(),
        "homebrew interpreter helper unexpectedly compiled",
    )?;
    let mut native = zakuro_core::recompiled::Library::open(path)?;
    require(
        native.check(&mut system.memory) == 0 && native.has_code(fixture::TEXT),
        "homebrew native bridge origin validation failed",
    )?;
    system.recompiled = Some(native);
    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::sync::atomic::{AtomicU64, Ordering};
    static NEXT: AtomicU64 = AtomicU64::new(0);

    // CodexAstraUlt: Tests own fresh temporary roots; no existing user or prior
    // test directory is removed to manufacture a clean lifecycle result.
    struct Directory(PathBuf);
    impl Directory {
        fn new() -> Self {
            let path = std::env::temp_dir().join(format!(
                "droidds-homebrew-session-{}-{}-{}",
                std::process::id(),
                std::time::SystemTime::now()
                    .duration_since(std::time::UNIX_EPOCH)
                    .unwrap()
                    .as_nanos(),
                NEXT.fetch_add(1, Ordering::Relaxed)
            ));
            fs::create_dir(&path).unwrap();
            Self(path)
        }
    }
    impl Drop for Directory {
        fn drop(&mut self) {
            let _ = fs::remove_dir_all(&self.0);
        }
    }

    #[test]
    fn pause_and_budget_rejection_preserve_the_machine_and_cleanup_owned_fixture() {
        let directory = Directory::new();
        let scratch = directory.0.join("scratch");
        {
            let mut session = Session::create(&directory.0, &scratch, false, false).unwrap();
            session.pause();
            assert!(session
                .frame(InputState::default())
                .unwrap_err()
                .contains("paused"));
            assert_eq!(session.report()["cycles"], 0);
            session.resume();
            assert!(session
                .budget_control()
                .unwrap()
                .contains("dispatch budget"));
            assert_eq!(session.report()["steps"], 1);
            assert_eq!(session.report()["status"], "failed");
            assert!(scratch.join("homebrew-fixture.cxi").is_file());
        }
        assert!(!scratch.join("homebrew-fixture.cxi").exists());
        assert!(scratch.join("droidds-homebrew-owner.txt").is_file());
        let fresh = Session::create(&directory.0, &scratch, false, false).unwrap();
        assert_eq!(fresh.system.cpu.cycles, 0);
    }

    #[test]
    fn full_text_guard_rejects_changed_second_page_without_dispatch() {
        let directory = Directory::new();
        let mut session =
            Session::create(&directory.0, &directory.0.join("scratch"), false, false).unwrap();
        assert!(session
            .system
            .memory
            .write32_privileged(fixture::FALLBACK, 0));
        assert!(session
            .frame(InputState::default())
            .unwrap_err()
            .contains("immutable executable text"));
        assert_eq!(session.steps, 0);
        assert_eq!(session.system.cpu.cycles, 0);
    }

    #[test]
    fn foreign_scratch_is_preserved_and_rejected() {
        let directory = Directory::new();
        let scratch = directory.0.join("scratch");
        fs::create_dir(&scratch).unwrap();
        fs::write(scratch.join("save.dat"), b"preserve this user file").unwrap();
        assert!(Session::create(&directory.0, &scratch, false, false).is_err());
        assert_eq!(
            fs::read(scratch.join("save.dat")).unwrap(),
            b"preserve this user file"
        );
        assert!(!scratch.join("droidds-homebrew-owner.txt").exists());
    }
}
