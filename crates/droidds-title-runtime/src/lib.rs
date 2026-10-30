//! CodexAstraUlt: An admitted, thread-owned title runtime keeps private imports
//! and durable saves separate. Cooperative slices yield without inventing frames.

mod admission;
mod manifest;

use manifest::Manifest;
use serde_json::{json, Value};
use std::{
    marker::PhantomData,
    path::Path,
    rc::Rc,
    time::{Duration, Instant},
};
use zakuro_common::Screen;
pub use zakuro_core::services::hid::{InputState, PadState};
use zakuro_core::{services::hid, StepOutcome, System, CYCLES_PER_FRAME};

pub const AUDIO_SAMPLE_RATE: f64 = zakuro_core::AUDIO_SAMPLE_RATE;
pub const MAX_PCM_FRAMES: usize = 4096;
const SLICE_STEPS: u64 = 50_000;
const SLICE_WALL: Duration = Duration::from_millis(8);
const DISPATCH_CYCLES: u64 = 65_536;

pub struct OpenOptions<'a> {
    pub manifest_json: &'a [u8],
    pub input: &'a Path,
    pub native_directory: &'a Path,
    pub data_directory: &'a Path,
    pub native: bool,
    pub hardware: bool,
}

// CodexAstraUlt: A missing screen buffer means no new guest frame completed.
// PCM is drained independently on every slice so slow startup cannot accumulate it.
pub struct Slice {
    pub top: Option<Vec<u8>>,
    pub bottom: Option<Vec<u8>>,
    pub pcm: Vec<[i16; 2]>,
    pub frames: u64,
    pub cycles: u64,
    pub exited: bool,
}

pub struct Session {
    system: System,
    manifest: Manifest,
    manifest_sha256: String,
    native: bool,
    hardware: bool,
    device: Option<String>,
    paused: bool,
    failure: Option<String>,
    slices: u64,
    yielded: u64,
    dispatches: u64,
    delivered_frames: u64,
    pcm_frames: u64,
    pcm_nonzero_frames: u64,
    pause_count: u64,
    resume_count: u64,
    debug_bytes_discarded: u64,
    slice_wall: Duration,
    // CodexAstraUlt: Core/native state belongs to one emulation owner. Tokens
    // may cross JNI, but the actual session cannot move to another Rust thread.
    _thread_owned: PhantomData<Rc<()>>,
}

impl Session {
    pub fn open(options: OpenOptions<'_>) -> Result<Self, String> {
        let manifest = Manifest::parse(options.manifest_json)?;
        let mut system = admission::load(&manifest, &options)?;
        let device = if options.hardware {
            Some(
                system
                    .gpu
                    .enable_hardware_renderer(1, None, None)
                    .map_err(|_| "title_vulkan_initialization_failed")?,
            )
        } else {
            None
        };
        let session = Self {
            system,
            manifest,
            manifest_sha256: manifest::sha256(options.manifest_json),
            native: options.native,
            hardware: options.hardware,
            device,
            paused: false,
            failure: None,
            slices: 0,
            yielded: 0,
            dispatches: 0,
            delivered_frames: 0,
            pcm_frames: 0,
            pcm_nonzero_frames: 0,
            pause_count: 0,
            resume_count: 0,
            debug_bytes_discarded: 0,
            slice_wall: Duration::ZERO,
            _thread_owned: PhantomData,
        };
        session.check_machine()?;
        Ok(session)
    }

    // CodexAstraUlt: Pausing releases held controls without advancing guest
    // execution or deleting runtime storage. Resume retains the same machine.
    pub fn pause(&mut self) {
        if !self.paused {
            self.pause_count += 1;
        }
        self.paused = true;
        self.system.set_input(InputState::default());
        hid::update(&mut self.system, InputState::default());
    }

    pub fn resume(&mut self) {
        if self.paused {
            self.resume_count += 1;
        }
        self.paused = false;
    }

    pub fn slice(&mut self, input: InputState) -> Result<Slice, String> {
        if let Some(failure) = &self.failure {
            return Err(failure.clone());
        }
        if self.paused {
            return Err("title_session_paused".into());
        }
        let started = Instant::now();
        let result = self.advance(input, SLICE_STEPS, SLICE_WALL);
        self.slice_wall += started.elapsed();
        if let Err(failure) = &result {
            self.failure = Some(failure.clone());
        }
        result
    }

    // CodexAstraUlt: Guest cycles and dispatches cap useful work; wall checks
    // are cooperative between core calls, not a preemptive native-code watchdog.
    fn advance(
        &mut self,
        input: InputState,
        max_steps: u64,
        wall: Duration,
    ) -> Result<Slice, String> {
        if input.touch.is_some_and(|(x, y)| x >= 320 || y >= 240)
            || ![
                input.circle_x,
                input.circle_y,
                input.c_stick_x,
                input.c_stick_y,
                input.tilt[0],
                input.tilt[1],
            ]
            .into_iter()
            .all(f32::is_finite)
        {
            return Err("title_input_invalid".into());
        }
        self.system.set_input(input);
        hid::update(&mut self.system, input);
        let frame = self.system.frames;
        let deadline = self.system.cpu.cycles.saturating_add(CYCLES_PER_FRAME);
        let started = Instant::now();
        self.check_machine()?;
        for _ in 0..max_steps {
            if self.system.exited
                || self.system.frames > frame
                || self.system.cpu.cycles >= deadline
                || started.elapsed() >= wall
            {
                break;
            }
            let limit = self
                .system
                .cpu
                .cycles
                .saturating_add(DISPATCH_CYCLES)
                .min(deadline);
            let outcome = self.system.step(Some(limit));
            self.dispatches += 1;
            self.debug_bytes_discarded += self.system.debug_output.len() as u64;
            self.system.debug_output.clear();
            if outcome == StepOutcome::Faulted {
                return Err("title_guest_fault".into());
            }
            self.check_machine()?;
        }
        self.slices += 1;
        let complete = self.system.frames > frame;
        if !complete && !self.system.exited {
            self.yielded += 1;
        }
        let (top, bottom) = if complete {
            let top = self.system.read_screen(Screen::Top);
            let bottom = self.system.read_screen(Screen::Bottom);
            if top.len() != 400 * 240 * 4 || bottom.len() != 320 * 240 * 4 {
                return Err("title_scanout_size_invalid".into());
            }
            self.delivered_frames += 1;
            (Some(top), Some(bottom))
        } else {
            (None, None)
        };
        let pcm = self.system.take_audio();
        if pcm.len() > MAX_PCM_FRAMES {
            return Err("title_audio_slice_capacity_exceeded".into());
        }
        self.pcm_frames += pcm.len() as u64;
        self.pcm_nonzero_frames += pcm.iter().filter(|sample| **sample != [0, 0]).count() as u64;
        self.check_machine()?;
        Ok(Slice {
            top,
            bottom,
            pcm,
            frames: self.system.frames,
            cycles: self.system.cpu.cycles,
            exited: self.system.exited,
        })
    }

    // CodexAstraUlt: Unsupported execution and failed draws stop explicitly.
    // Accurate renderer fallback/resource admission stays visible in the report
    // and never silently qualifies a pure hardware rendering claim.
    fn check_machine(&self) -> Result<(), String> {
        if self.system.diagnostic_fault().is_some()
            || !self.system.unimplemented_svcs.is_empty()
            || !self.system.services.unimplemented.is_empty()
            || !self.system.memory.fault_summary().is_empty()
            || !self.system.prefetch_aborts.is_empty()
            || !self.system.fatal_errors.is_empty()
        {
            return Err("title_runtime_blocker".into());
        }
        let diagnostics = self.system.gpu.hardware_diagnostics();
        if diagnostics.is_some() != self.hardware {
            return Err("title_renderer_route_changed".into());
        }
        if diagnostics.is_some_and(|gpu| gpu.draw_errors != 0 || gpu.last_error.is_some()) {
            return Err("title_renderer_draw_failed".into());
        }
        self.system.memory.verify_base_code_fence()
    }

    // CodexAstraUlt: A fixed-size aggregate replaces per-frame logs. It carries
    // identities and progress, never raw title bytes, pixels, PCM or local paths.
    pub fn report(&self) -> Value {
        // CodexAstraUlt: Identify a CPU blocker without exporting its original
        // instruction word or an arbitrary guest-provided debug string.
        let fault = self.system.diagnostic_fault().map(|fault| match fault {
            zakuro_core::DiagnosticFault::UndefinedInstruction { pc, thumb, .. } => {
                json!({"kind":"undefined_instruction","pc":pc,"thumb":thumb})
            }
            zakuro_core::DiagnosticFault::Breakpoint { pc, .. } => {
                json!({"kind":"breakpoint","pc":pc})
            }
            zakuro_core::DiagnosticFault::NativeCodeFence { pc } => {
                json!({"kind":"native_code_fence","pc":pc})
            }
        });
        let callbacks = self
            .system
            .recompiled
            .as_ref()
            .map_or(0, |library| library.fallbacks());
        let hardware = self.system.gpu.hardware_diagnostics().map(|gpu| json!({
            "recorded_draws":gpu.recorded_draws,"submissions":gpu.submissions,
            "draw_errors":gpu.draw_errors,"software_raster_fallbacks":gpu.software_raster_fallbacks,
            "resource_limit_events":gpu.resource_limit_events,"compiler_outstanding":gpu.compiler_outstanding,
            "compiler_peak":gpu.compiler_peak,"compiler_deferred":gpu.compiler_deferred,
            "compiler_failures":gpu.compiler_failures,"retained_shader_bytes":gpu.retained_shader_bytes,
            "retained_translations":gpu.retained_translations,"retained_modules":gpu.retained_modules,
            "retained_pipelines":gpu.retained_pipelines,"vertex_shading_on_gpu":gpu.vertex_shading_on_gpu,
            "last_error":gpu.last_error.as_ref().map(|value|value.chars().take(256).collect::<String>())}));
        json!({"schema_version":1,"kind":"droidds_title_session","program_id":self.manifest.program_id,
            "manifest_sha256":self.manifest_sha256,"input_sha256":self.manifest.input.sha256,
            "native_sha256":self.manifest.native.sha256,
            "status":if self.failure.is_some(){"failed"}else if self.system.exited{"exited"}else if self.paused{"paused"}else{"running"},
            "error":self.failure,"native":self.native,"native_scope":"immutable_base_modules_interpreted",
            "renderer":if self.hardware{"vulkan"}else{"software"},"device":self.device,
            "model":if self.system.config.new3ds{"new"}else{"old"},"resolution_scale":1,
            "sample_rate":AUDIO_SAMPLE_RATE,"slices":self.slices,"yielded_slices":self.yielded,
            "dispatches":self.dispatches,"cycles":self.system.cpu.cycles,"frames":self.system.frames,
            "frames_delivered":self.delivered_frames,"interpreted_instructions":self.system.interpreted_instructions,
            "compiled_dispatch_instructions":self.system.recompiled_instructions,
            "callback_interpreted_instructions":callbacks,
            "native_instructions":self.system.recompiled_instructions.saturating_sub(callbacks),
            "pcm_frames":self.pcm_frames,"pcm_nonzero_frames":self.pcm_nonzero_frames,
            "pause_count":self.pause_count,"resume_count":self.resume_count,
            "debug_bytes_discarded":self.debug_bytes_discarded,
            "slice_wall_nanoseconds":self.slice_wall.as_nanos().min(u64::MAX as u128) as u64,
            "gpu":{"command_lists":self.system.gpu.command_lists,"draw_calls":self.system.gpu.draw_calls,
                "vertices_drawn":self.system.gpu.vertices_drawn,"hardware":hardware},
            "memory_used_bytes":self.system.memory.phys.region_used(zakuro_core::memory::MemoryRegion::Application),
            "diagnostic_fault":fault,
            "live_pc":self.system.cpu.regs[15],"unsupported_svcs":self.system.unimplemented_svcs.len(),
            "unsupported_services":self.system.services.unimplemented.len(),"prefetch_aborts":self.system.prefetch_aborts.len(),
            "fatal_errors":self.system.fatal_errors.len(),"cooperative_slice_wall_limit_ms":8})
    }
}

#[cfg(test)]
mod tests;
