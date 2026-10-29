//! CodexAstraUlt: A bounded, local interpreter reconnaissance worker. A clean
//! guest exit or exhausted budget is evidence about this execution only, never
//! a retail boot, rendering correctness, performance, or native-code milestone.

use serde_json::{json, Value};
use std::{fs, path::PathBuf, time::Instant};
use zakuro_common::ConsoleModel;
use zakuro_core::{
    loader, memory::MemoryRegion, services::hid, Config, DiagnosticFault, StepOutcome, System,
};

// CodexAstraUlt: CPU progress metadata belongs to this explicit host diagnostic,
// leaving the shared core and Android runtime free of another tracing mode.
mod cpu_progress;

pub const KIND: &str = "droidds_private_title_interpreter_reconnaissance";
pub const RUNTIME_REVISION: &str = "412900a5a020301da15c1cc382585e05a489a535";
const REGIONS: [MemoryRegion; 3] = [
    MemoryRegion::Application,
    MemoryRegion::System,
    MemoryRegion::Base,
];

// CodexAstraUlt: Separate dispatch, emulated-time, frame and wall budgets make a
// busy guest and an idle scheduler independently bounded. A parent process must
// still enforce hard time/memory ceilings around loader or single-step stalls.
#[derive(Clone, Debug)]
pub struct Options {
    pub input: PathBuf,
    pub data_dir: PathBuf,
    pub max_steps: u64,
    pub max_cycles: u64,
    pub max_frames: u64,
    pub max_seconds: u64,
    pub new_model: bool,
    // CodexAstraUlt: Explicit local diagnostics only; ordinary runtime and
    // baseline execution retain the disabled trace path.
    pub trace_scheduler: bool,
    // CodexAstraUlt: Sparse live CPU snapshots, independently opt-in from SVCs.
    pub trace_cpu_progress: bool,
}

impl Options {
    pub fn validate(&self) -> Result<(), String> {
        for (name, value, ceiling) in [
            ("max-steps", self.max_steps, 1_000_000_000),
            ("max-cycles", self.max_cycles, 26_811_185_600),
            ("max-frames", self.max_frames, 6000),
            ("max-seconds", self.max_seconds, 300),
        ] {
            if value == 0 || value > ceiling {
                return Err(format!("{name} must be between 1 and {ceiling}"));
            }
        }
        Ok(())
    }
}

// CodexAstraUlt: Reports contain bounded metadata/counters rather than guest
// strings, RAM, images, audio or code. The coordinator binds this result to its
// snapshot and worker SHA-256 values; this crate does not claim to authenticate
// the source revision from which an arbitrary executable was built.
fn envelope(options: &Options) -> Value {
    json!({
        "schema_version": 1, "tool_version": env!("CARGO_PKG_VERSION"), "kind": KIND,
        "runtime_revision": RUNTIME_REVISION, "runtime_has_local_patches": true,
        "status": "internal_error", "reason": "worker_incomplete", "blocker": null,
        "input": null, "diagnostic_trace": null, "cpu_progress": null, "configuration": {
            "model_requested": if options.new_model { "new" } else { "old" },
            "model_resolved": null, "execution": "interpreter", "renderer": "software",
            "strict_diagnostics": true, "native_discovery": false, "updates": false,
            "scheduler_trace": options.trace_scheduler,
            "cpu_progress_trace": options.trace_cpu_progress,
            "dlc": false, "texture_packs": false, "enhancements": false,
            "mods_and_cheats": "absent_in_fresh_private_data_directory",
            "idle_loop_skipping": false, "clock_ms_since_1900": 4_000_000_000_000u64,
            "input_events": "neutral", "scanout_captured": false,
            "budget_boundary": {"steps":"before_dispatch_hard", "cycles":"after_system_step",
                "frames":"after_system_step", "wall":"between_loader_and_steps_parent_hard_timeout"}
        },
        "limits": {"max_steps": options.max_steps, "max_cycles": options.max_cycles,
            "max_frames": options.max_frames, "max_seconds": options.max_seconds},
        "observed": {"steps": 0, "cycles": 0, "cycles_after_budget": 0, "frames": 0,
            "interpreted_instructions": 0, "recompiled_instructions": 0,
            "elapsed_seconds": 0.0},
        "limitations": [
            "Interpreter/software-renderer reconnaissance; not a playable-game or hardware-performance result.",
            "Stops on observed unsupported operations; implemented HLE paths can still be incomplete.",
            "Faults are inspected after each full System::step; frame/audio event hooks may precede one instruction within that step.",
            "Cycle/frame budgets are cooperative dispatch boundaries; service work inside a step may exceed the requested cycle budget, and actual overshoot is reported without a universal maximum claim.",
            "No native compilation/loading, updates, DLC, mods, prior saves, shader cache or private captures.",
            "Guest region accounting is not host or whole-renderer memory accounting.",
            "Hard loader/single-step wall and host-resource limits are the parent coordinator's responsibility."
        ]
    })
}

// CodexAstraUlt: Never reuse a runtime directory containing saves, cheats or
// mods. The worker creates one absent directory and leaves all generated files
// for its owner; it never deletes or replaces user data.
fn prepare(options: &Options) -> Result<(), String> {
    options.validate()?;
    let metadata = fs::symlink_metadata(&options.input).map_err(|_| "input_unreadable")?;
    if !metadata.is_file() || metadata.file_type().is_symlink() {
        return Err("input_not_regular_file".into());
    }
    #[cfg(unix)]
    {
        use std::os::unix::fs::DirBuilderExt;
        fs::DirBuilder::new()
            .mode(0o700)
            .create(&options.data_dir)
            .map_err(|_| "data_directory_must_be_new_with_existing_parent")?;
    }
    #[cfg(not(unix))]
    fs::create_dir(&options.data_dir)
        .map_err(|_| "data_directory_must_be_new_with_existing_parent")?;
    Ok(())
}

// CodexAstraUlt: Legacy parser panics become an explicit failed worker report.
// Aborts, OOM and a stuck parser remain distinguishable parent-process failures;
// catch_unwind is not a replacement for parser hardening or process ceilings.
pub fn run(options: &Options) -> Value {
    let started = Instant::now();
    let mut report = envelope(options);
    let result = std::panic::catch_unwind(std::panic::AssertUnwindSafe(|| {
        execute(options, &mut report, started)
    }));
    match result {
        Ok(Ok(())) => {}
        Ok(Err(reason)) => {
            report["status"] = json!("load_error");
            report["reason"] = json!(reason);
        }
        Err(_) => {
            report["status"] = json!("internal_error");
            report["reason"] = json!("worker_panicked");
        }
    }
    report["observed"]["elapsed_seconds"] = json!(started.elapsed().as_secs_f64());
    report
}

fn execute(options: &Options, report: &mut Value, started: Instant) -> Result<(), String> {
    prepare(options)?;
    // CodexAstraUlt: The fresh data directory prevents the existing loader's
    // implicit mod/cheat lookup from importing unrelated owner configuration.
    // Explicitly disable all executable discovery and optional title overlays.
    let mut system = loader::load(
        &options.input,
        Config {
            model: if options.new_model {
                ConsoleModel::New3ds
            } else {
                ConsoleModel::Old3ds
            },
            new3ds: options.new_model,
            data_dir: Some(options.data_dir.clone()),
            find_recompiled: false,
            recompiled: None,
            linked: None,
            hardware_renderer: false,
            texture_packs: false,
            clock: Some(4_000_000_000_000),
            skip_idle_loops: false,
            strict_diagnostics: true,
            ..Config::default()
        },
    )
    .map_err(|error| format!("loader_rejected: {}", bounded(&error.to_string(), 512)))?;
    report["input"] = title_metadata(&system);
    report["configuration"]["model_resolved"] =
        json!(if system.config.new3ds { "new" } else { "old" });
    // CodexAstraUlt: CIA parsing already rejects update/DLC archives. Apply the
    // same base-title policy to standalone NCCHs and cartridge partitions before
    // any guest instruction; do not accidentally test an update as its base.
    match zakuro_fs::TitleKind::of(system.title.as_ref().expect("loaded title").program_id()) {
        zakuro_fs::TitleKind::Update => return Err("update_input_requires_a_base_title".into()),
        zakuro_fs::TitleKind::Dlc => return Err("dlc_input_requires_a_base_title".into()),
        _ => {}
    }
    // CodexAstraUlt: The loader adds disabled catalog enhancements even when
    // none was requested. They are harmless; only an enabled entry violates
    // this baseline's no-cheats/no-enhancements configuration.
    if system.recompiled.is_some()
        || system.hints.is_some()
        || system.cheats.iter().any(|cheat| cheat.enabled)
        || !system.dlc.is_empty()
        || system.gpu.hardware_diagnostics().is_some()
    {
        return Err("unexpected_optional_runtime_component".into());
    }

    // CodexAstraUlt: Capture only opt-in bounded scheduler/SVC metadata after
    // loading and before the first guest instruction; no continuous log writer.
    if options.trace_scheduler {
        system.enable_diagnostic_trace();
    }
    let mut steps = 0u64;
    let mut drained_pcm = 0u64;
    let mut nonzero_pcm = 0u64;
    let mut guest_debug_bytes = 0u64;
    let mut last_frame = system.frames;
    let mut sampled_region_peak = REGIONS.map(|region| system.memory.phys.region_used(region));
    let neutral = hid::InputState::default();
    system.set_input(neutral);
    hid::update(&mut system, neutral);

    // CodexAstraUlt: Capture the initial state only when requested. Subsequent
    // samples use dispatch cadence, so both CPU work and idle steps stay bounded.
    let mut cpu_progress = options
        .trace_cpu_progress
        .then(|| cpu_progress::CpuProgress::new(&system));

    // CodexAstraUlt: Inspect after each complete System::step. Unsupported
    // service replies from CPU dispatch cannot be consumed by a later guest
    // instruction; frame/audio hooks earlier in the same step are a documented
    // narrower fault boundary, not an instruction-level transactional guarantee.
    let (status, reason, blocker) = loop {
        if let Some(blocker) = first_blocker(&system) {
            break ("blocked", "runtime_blocker", blocker);
        }
        if system.exited {
            break ("guest_exited", "guest_called_exit_process", Value::Null);
        }
        let budget = if steps >= options.max_steps {
            Some("step_budget")
        } else if system.cpu.cycles >= options.max_cycles {
            Some("cycle_budget")
        } else if system.frames >= options.max_frames {
            Some("frame_budget")
        } else if started.elapsed().as_secs() >= options.max_seconds {
            Some("wall_budget")
        } else {
            None
        };
        if let Some(reason) = budget {
            break ("budget_exhausted", reason, Value::Null);
        }
        let outcome = system.step(Some(
            system
                .cpu
                .cycles
                .saturating_add(4096)
                .min(options.max_cycles),
        ));
        steps += 1;
        // CodexAstraUlt: Observe after dispatch but before a fault can stop the
        // loop; sampling neither reads guest memory nor changes its CPU state.
        if let Some(progress) = &mut cpu_progress {
            progress.after_step(&system, steps);
        }
        guest_debug_bytes = guest_debug_bytes.saturating_add(system.debug_output.len() as u64);
        system.debug_output.clear();
        if let Some(blocker) = first_blocker(&system) {
            break ("blocked", "runtime_blocker", blocker);
        }
        if outcome == StepOutcome::Faulted {
            break (
                "blocked",
                "guest_fault",
                json!({"kind":"guest_fault", "pc":system.cpu.regs[15]}),
            );
        }
        if system.frames != last_frame {
            last_frame = system.frames;
            let pcm = system.take_audio();
            drained_pcm = drained_pcm.saturating_add(pcm.len() as u64);
            nonzero_pcm = nonzero_pcm
                .saturating_add(pcm.iter().filter(|sample| **sample != [0, 0]).count() as u64);
            for (i, region) in REGIONS.iter().enumerate() {
                sampled_region_peak[i] =
                    sampled_region_peak[i].max(system.memory.phys.region_used(*region));
            }
            hid::update(&mut system, neutral);
        }
    };

    // CodexAstraUlt: Drain only aggregate audio data, and disclose the sampling
    // boundary for region peaks. No image/audio/code bytes enter the report.
    let pcm = system.take_audio();
    drained_pcm = drained_pcm.saturating_add(pcm.len() as u64);
    nonzero_pcm =
        nonzero_pcm.saturating_add(pcm.iter().filter(|sample| **sample != [0, 0]).count() as u64);
    for (i, region) in REGIONS.iter().enumerate() {
        sampled_region_peak[i] =
            sampled_region_peak[i].max(system.memory.phys.region_used(*region));
    }
    report["status"] = json!(status);
    report["reason"] = json!(reason);
    report["blocker"] = blocker;
    // CodexAstraUlt: Serialize the fixed-capacity trace and final wait snapshot
    // once, preserving pending returns and truncation as diagnostic evidence.
    report["diagnostic_trace"] = serde_json::to_value(system.diagnostic_trace_snapshot())
        .expect("diagnostic trace metadata");
    // CodexAstraUlt: Final live registers and existing dispatch history are
    // separate evidence; a live r15 must not be labeled the last executed PC.
    report["cpu_progress"] = cpu_progress
        .map(|progress| progress.finish(&system, steps))
        .unwrap_or(Value::Null);
    report["observed"] = json!({
        "steps":steps, "cycles":system.cpu.cycles, "frames":system.frames,
        "cycles_after_budget":system.cpu.cycles.saturating_sub(options.max_cycles),
        "interpreted_instructions":system.interpreted_instructions,
        "recompiled_instructions":system.recompiled_instructions,
        "guest_exited":system.exited, "final_pc":system.cpu.regs[15],
        "command_lists":system.gpu.command_lists, "draw_calls":system.gpu.draw_calls,
        "vertices_drawn":system.gpu.vertices_drawn, "pcm_samples_drained":drained_pcm,
        "pcm_nonzero_samples":nonzero_pcm, "guest_debug_bytes_discarded":guest_debug_bytes,
        "services_seen":system.services_seen.iter().take(64).map(|s| bounded(s, 32)).collect::<Vec<_>>(),
        "services_seen_count":system.services_seen.len(),
        "unsupported_svc_count":system.unimplemented_svcs.len(),
        "unsupported_service_count":system.services.unimplemented.len(),
        "memory_fault_addresses":system.memory.fault_summary().len(),
        "prefetch_abort_addresses":system.prefetch_aborts.len(),
        "fatal_error_count":system.fatal_errors.len(),
        "guest_region_order":["application","system","base"],
        "guest_region_used_bytes":REGIONS.map(|region| system.memory.phys.region_used(region)),
        "guest_region_sampled_peak_bytes":sampled_region_peak,
        "peak_sampling":"after_load_each_frame_and_stop", "elapsed_seconds":0.0
    });
    Ok(())
}

// CodexAstraUlt: Prefer explicit fault records over broad stopped-state flags;
// addresses and bounded operation identifiers help local follow-up reproduce
// the first unsupported path without exporting guest memory or instructions.
fn first_blocker(system: &System) -> Option<Value> {
    // CodexAstraUlt: CPU current_pc models a fetch pipeline, so after dispatch
    // use the actual recorded instruction rather than subtracting its pipeline
    // bias from the already advanced register (which misattributes SVC faults).
    let executed_pc = || system.recent_instructions().last().map(|pc| pc & !1);
    if let Some(fault) = system.diagnostic_fault() {
        return Some(match fault {
            DiagnosticFault::UndefinedInstruction {
                pc,
                opcode: _,
                thumb,
            } => json!({"kind":"undefined_instruction", "pc":pc, "thumb":thumb}),
            DiagnosticFault::Breakpoint { pc, imm } => {
                json!({"kind":"breakpoint", "pc":pc, "immediate":imm})
            }
            // CodexAstraUlt: Preserve exhaustive diagnostics while the ordinary
            // interpreter worker leaves this native-only fence disabled.
            DiagnosticFault::NativeCodeFence { pc } => {
                json!({"kind":"native_code_fence", "pc":pc})
            }
        });
    }
    if let Some(number) = system.unimplemented_svcs.first() {
        return Some(json!({"kind":"unsupported_svc", "number":number, "pc":executed_pc()}));
    }
    if let Some(((service, command), _)) = system.services.unimplemented.first_key_value() {
        return Some(
            json!({"kind":"unsupported_service", "service":bounded(service, 32),
            "command":command, "pc":executed_pc()}),
        );
    }
    if let Some((address, _)) = system.prefetch_aborts.first_key_value() {
        return Some(json!({"kind":"prefetch_abort", "address":address, "pc":system.cpu.regs[15]}));
    }
    if let Some((address, count)) = system.memory.fault_summary().first() {
        return Some(
            json!({"kind":"memory_fault", "address":address, "count":count, "pc":executed_pc()}),
        );
    }
    if !system.fatal_errors.is_empty() {
        return Some(
            json!({"kind":"fatal_guest_error", "count":system.fatal_errors.len(), "pc":executed_pc()}),
        );
    }
    None
}

fn bounded(value: &str, count: usize) -> String {
    value.chars().take(count).collect()
}

// CodexAstraUlt: Record the layout the actual loader resolved rather than
// inferring executable identity or New 3DS support from a filename.
fn title_metadata(system: &System) -> Value {
    let title = system.title.as_ref().expect("loader installs title");
    let exheader = &title.exheader;
    let segment = |value: &zakuro_fs::ncch::CodeSetInfo| {
        json!({
            "address":value.address,"pages":value.num_pages,"size":value.size
        })
    };
    json!({
        "program_id":format!("{:016X}", title.program_id()),
        "title_name":bounded(&exheader.title, 8), "product_code":bounded(&title.ncch.product_code, 16),
        "container_bytes":title.image().len(), "ncch_offset":title.ncch_offset(),
        "entry_point":exheader.text.address, "compressed_code":exheader.compress_code,
        "text":segment(&exheader.text), "rodata":segment(&exheader.rodata), "data":segment(&exheader.data),
        "bss_bytes":exheader.bss_size, "stack_bytes":exheader.stack_size,
        "old_memory_mode":exheader.system_mode.raw(), "new_memory_mode":exheader.n3ds_system_mode,
        "ncch_platform":title.ncch.platform(), "has_romfs":title.romfs.is_some(),
        "guest_region_order":["application","system","base"],
        "guest_region_bytes":REGIONS.map(|region| system.memory.phys.region_size(region)),
        "guest_region_limit_bytes":REGIONS.map(|region| system.memory.phys.region_limit(region))
    })
}
