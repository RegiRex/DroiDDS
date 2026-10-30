//! CodexAstraUlt: Bounded native/interpreter host observations consume a sealed
//! coordinator admission. This is not an untrusted native-plugin sandbox or a
//! claim of private-title boot, native parity, or handheld performance.

pub mod request;
mod state;

use request::{Request, SealedFile};
use serde_json::{json, Value};
use std::{fs, path::Path, time::Instant};
use zakuro_common::ConsoleModel;
use zakuro_core::{loader, services::hid, Config, DiagnosticFault, StepOutcome, System};

pub const KIND: &str = "droidds_private_native_run";
const CHECKPOINTS: [u64; 4] = [100_000, 500_000, 1_000_000, 2_000_000];

// CodexAstraUlt: Every sampled state carries the work already completed there.
// Native execution after an earlier interpreter-only sample cannot qualify it.
fn instruction_counts(system: &System) -> Value {
    json!({"interpreted":system.interpreted_instructions,
        "recompiled":system.recompiled_instructions,
        "callback_interpreted":system.recompiled.as_ref().map_or(0, |library| library.fallbacks())})
}

// CodexAstraUlt: A report is allocated before admission so an ordinary rejection
// cannot be mistaken for a silent worker or zero-counter successful game run.
fn envelope(request: Option<&Request>) -> Value {
    let mut value = json!({
        "schema_version":1,"kind":KIND,"tool_version":env!("CARGO_PKG_VERSION"),
        "status":"load_error","reason":"request_not_admitted","blocker":null,
        "route":null,"preparation_sha256":null,"contract_sha256":null,"library_sha256":null,
        "limits":null,"checkpoints":[],"synchronized_checkpoints":[],"observed":{},"library_loaded":false,"library_load_attempted":false,
        "runtime_binding_enforced":false,"guest_execution_performed":false,"guest_execution_attempted":false,
        "configuration":{
            "renderer":"software","native_discovery":false,"strict_diagnostics":true,
            "clock_ms_since_1900":4_000_000_000_000u64,"input_events":"neutral",
            "updates":false,"dlc":false,"mods":false,"texture_packs":false,
            "native_scope":"immutable_base_executable_only_modules_interpreted",
            "parent_admission":"sealed_local_coordinator_request_not_plugin_sandbox",
            "state_fingerprint":"noncryptographic_fnv1a64_diagnostic_only",
            "checkpoint_schedule":CHECKPOINTS,"private_images_or_audio_exported":false,
            "synchronized_checkpoint_policy":"first_post_svc_at_or_after_pending_cycle_no_budget_extension",
            "failed_attempt_counters_may_be_incomplete":true
        }
    });
    if let Some(request) = request {
        value["route"] = json!(request.route);
        value["preparation_sha256"] = json!(request.preparation_sha256);
        value["contract_sha256"] = json!(request.contract_sha256);
        value["library_sha256"] = json!(request.library.sha256);
        value["limits"] = json!({"max_steps":request.limits.max_steps,"max_cycles":request.limits.max_cycles,
            "max_frames":request.limits.max_frames,"max_seconds":request.limits.max_seconds});
        value["configuration"]["model_requested"] = json!(request.model);
    }
    value
}

// CodexAstraUlt: Parent components are checked as ordinary paths; no symlink may
// redirect the private input or fresh runtime data directory after admission.
fn plain_path(path: &Path, missing_leaf: bool) -> Result<(), String> {
    if !path.is_absolute() {
        return Err("worker_paths_must_be_absolute".into());
    }
    let mut walked = std::path::PathBuf::new();
    for part in path.components() {
        if matches!(
            part,
            std::path::Component::ParentDir | std::path::Component::CurDir
        ) {
            return Err("worker_path_contains_navigation".into());
        }
        walked.push(part);
        match fs::symlink_metadata(&walked) {
            Ok(metadata) if metadata.file_type().is_symlink() => {
                return Err("worker_path_contains_symlink".into())
            }
            Ok(_) => {}
            Err(error)
                if error.kind() == std::io::ErrorKind::NotFound
                    && missing_leaf
                    && walked == path => {}
            Err(_) => return Err("worker_path_unavailable".into()),
        }
    }
    Ok(())
}

// CodexAstraUlt: Existing saves/configuration never enter the baseline. Creation
// is exclusive and never clears an existing directory, even after a failed run.
fn fresh_data_directory(path: &Path) -> Result<(), String> {
    plain_path(path, true)?;
    let mut builder = fs::DirBuilder::new();
    #[cfg(unix)]
    {
        use std::os::unix::fs::DirBuilderExt;
        builder.mode(0o700);
    }
    builder
        .create(path)
        .map_err(|_| "runtime_data_directory_must_be_new".into())
}

// CodexAstraUlt: Independently resolve the running title against the sealed raw
// identity components. Full decompressed bytes include segment padding/tails;
// a title ID or a match of just the logical text bytes is insufficient.
fn bind_runtime(system: &mut System, request: &Request, bundle: &[u8]) -> Result<(), String> {
    let title = system.title.as_ref().ok_or("runtime_title_missing")?;
    let prepared = &request.prepared;
    if matches!(
        zakuro_fs::TitleKind::of(title.program_id()),
        zakuro_fs::TitleKind::Update | zakuro_fs::TitleKind::Dlc
    ) || format!("{:016x}", title.program_id()) != prepared.program_id
        || title.ncch.version != prepared.ncch_format_version
        || title.exheader.remaster_version != prepared.remaster_version
        || title.exheader.bss_size != prepared.bss_size
        || title.image().len() as u64 != request.input.bytes
    {
        return Err("runtime_title_identity_mismatch".into());
    }
    let image = title.image();
    let raw = image.data();
    let container = if zakuro_fs::Ncsd::detect(raw) {
        "ncsd"
    } else if zakuro_fs::Cia::detect(raw) {
        "cia"
    } else if zakuro_fs::NcchHeader::detect(raw) {
        "ncch"
    } else {
        return Err("runtime_container_unknown".into());
    };
    if container != prepared.container {
        return Err("runtime_container_mismatch".into());
    }
    if container == "cia" {
        let cia = zakuro_fs::Cia::parse(raw).map_err(|_| "runtime_cia_rejected")?;
        if cia.title_id != title.program_id() || Some(cia.version) != prepared.cia_title_version {
            return Err("runtime_cia_identity_mismatch".into());
        }
    }
    let code = title
        .code()
        .map_err(|_| "runtime_decompressed_code_unavailable")?;
    let mut code_component = None;
    for component in &request.identity_bundle.components {
        let start = usize::try_from(component.offset).map_err(|_| "component_offset_overflow")?;
        let end = usize::try_from(component.offset + component.bytes)
            .map_err(|_| "component_end_overflow")?;
        let expected = bundle.get(start..end).ok_or("component_out_of_bundle")?;
        let agrees = match component.kind.as_str() {
            "ncch_header" => {
                let at = usize::try_from(title.ncch_offset())
                    .map_err(|_| "runtime_ncch_offset_overflow")?;
                raw.get(at..at + 512) == Some(expected)
            }
            "exheader" => title.exheader_bytes() == expected,
            "decompressed_code" => {
                code_component = Some(expected);
                code.as_slice() == expected
            }
            "cro" | "static_crs" => {
                let romfs = title
                    .romfs
                    .as_ref()
                    .ok_or("runtime_module_filesystem_missing")?;
                let file = romfs
                    .lookup(
                        component
                            .source_path
                            .as_deref()
                            .ok_or("module_path_missing")?,
                    )
                    .map_err(|_| "runtime_module_missing")?;
                file.data_size == component.bytes
                    && title.read_romfs(&file, 0, expected.len()) == Some(expected)
            }
            _ => return Err("unexpected_identity_component_kind".into()),
        };
        if !agrees {
            return Err(format!("runtime_component_mismatch_{}", component.kind));
        }
    }
    let mut offset = 0u64;
    for (expected, actual) in prepared.segments.iter().zip([
        title.exheader.text,
        title.exheader.rodata,
        title.exheader.data,
    ]) {
        if expected.address != actual.address
            || expected.mapped_bytes != u64::from(actual.num_pages) * 4096
            || expected.size != u64::from(actual.size)
            || expected.offset != offset
        {
            return Err("runtime_segment_layout_mismatch".into());
        }
        offset += expected.mapped_bytes;
    }
    // CodexAstraUlt: Verify the pages actually mapped by the loader before
    // arming protection. This catches unintended overlays and mapping defects.
    let expected_code = code_component.ok_or("runtime_code_identity_missing")?;
    for segment in &prepared.segments {
        for within in (0..segment.mapped_bytes as usize).step_by(4096) {
            let mut actual = [0u8; 4096];
            let mut expected = [0u8; 4096];
            let source_at = segment.offset as usize + within;
            if source_at < expected_code.len() {
                let length = (expected_code.len() - source_at).min(4096);
                expected[..length].copy_from_slice(&expected_code[source_at..source_at + length]);
            }
            let address = segment
                .address
                .checked_add(within as u32)
                .ok_or("runtime_segment_address_overflow")?;
            if !system.memory.is_readable(address, 4096) {
                return Err("runtime_segment_unreadable".into());
            }
            system.memory.read_bytes(address, &mut actual);
            if actual != expected {
                return Err("loaded_segment_bytes_mismatch".into());
            }
        }
    }
    if !system.memory.fault_summary().is_empty() {
        return Err("runtime_binding_memory_fault".into());
    }
    Ok(())
}

// CodexAstraUlt: Installing the base fence precedes dlopen and all guest steps.
// The coordinator has statically audited the sealed library's complete table
// graph; these runtime checks then bind its origins to the actual loaded bytes.
fn install_native(
    system: &mut System,
    request: &Request,
    library_file: &SealedFile,
    report: &mut Value,
) -> Result<(), String> {
    if system.cpu.cycles != 0
        || system.frames != 0
        || system.recompiled.is_some()
        || system.memory.base_code_fence_active()
    {
        return Err("native_install_requires_fresh_runtime".into());
    }
    let text = &request.prepared.segments[0];
    system
        .memory
        .install_base_code_fence(text.address, text.mapped_bytes as u32)?;
    // CodexAstraUlt: A failed dlopen/symbol-validation attempt can already have
    // executed library initialization; distinguish attempted from admitted load.
    report["library_load_attempted"] = json!(true);
    let mut native = zakuro_core::recompiled::Library::open(&library_file.path())
        .map_err(|_| "admitted_library_load_failed")?;
    report["library_loaded"] = json!(true);
    native.restrict_to_executable();
    if native.outdated()
        || !native.checks_itself()
        || native.check(&mut system.memory) != 0
        || !native.has_code(text.address)
    {
        return Err("admitted_library_runtime_origins_or_entry_mismatch".into());
    }
    system.memory.verify_base_code_fence()?;
    system.recompiled = Some(native);
    Ok(())
}

// CodexAstraUlt: Bounded operation identifiers identify the first observed fault;
// guest debug strings, instructions, images and raw memory stay out of reports.
fn blocker(system: &System) -> Option<Value> {
    if let Some(fault) = system.diagnostic_fault() {
        return Some(match fault {
            DiagnosticFault::UndefinedInstruction { pc, thumb, .. } => {
                json!({"kind":"undefined_instruction","pc":pc,"thumb":thumb})
            }
            DiagnosticFault::Breakpoint { pc, imm } => {
                json!({"kind":"breakpoint","pc":pc,"immediate":imm})
            }
            DiagnosticFault::NativeCodeFence { pc } => {
                json!({"kind":"native_code_fence_violation","pc":pc})
            }
        });
    }
    if let Some(number) = system.unimplemented_svcs.first() {
        return Some(json!({"kind":"unsupported_svc","number":number}));
    }
    if let Some(((service, command), _)) = system.services.unimplemented.first_key_value() {
        return Some(
            json!({"kind":"unsupported_service","service":service.chars().take(32).collect::<String>(),"command":command}),
        );
    }
    if let Some((address, _)) = system.prefetch_aborts.first_key_value() {
        return Some(json!({"kind":"prefetch_abort","address":address}));
    }
    if let Some((address, count)) = system.memory.fault_summary().first() {
        return Some(json!({"kind":"memory_fault","address":address,"count":count}));
    }
    if !system.fatal_errors.is_empty() {
        return Some(json!({"kind":"fatal_guest_error","count":system.fatal_errors.len()}));
    }
    None
}

// CodexAstraUlt: Observer is only used by original Rust regression tests; the
// production caller supplies a no-op and exports bounded fingerprints alone.
fn execute(
    request: &Request,
    library_file: &SealedFile,
    bundle: &[u8],
    data_dir: &Path,
    report: &mut Value,
    started: Instant,
    observer: impl FnOnce(&mut System),
) -> Result<(), String> {
    plain_path(&request.input.snapshot_path, false)?;
    let input = fs::symlink_metadata(&request.input.snapshot_path)
        .map_err(|_| "runtime_input_unavailable")?;
    if !input.is_file() || input.len() != request.input.bytes {
        return Err("runtime_input_size_mismatch".into());
    }
    #[cfg(unix)]
    {
        use std::os::unix::fs::PermissionsExt;
        if input.permissions().mode() & 0o222 != 0 {
            return Err("runtime_input_must_be_readonly".into());
        }
    }
    fresh_data_directory(data_dir)?;
    let mut system = loader::load(
        &request.input.snapshot_path,
        Config {
            model: if request.model == "new" {
                ConsoleModel::New3ds
            } else {
                ConsoleModel::Old3ds
            },
            new3ds: request.model == "new",
            data_dir: Some(data_dir.to_path_buf()),
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
    .map_err(|_| "runtime_loader_rejected")?;
    if system.recompiled.is_some()
        || system.hints.is_some()
        || system.cheats.iter().any(|c| c.enabled)
        || !system.dlc.is_empty()
        || system.gpu.hardware_diagnostics().is_some()
        || system.cpu.cycles != 0
        || system.frames != 0
    {
        return Err("unexpected_optional_or_started_runtime".into());
    }
    bind_runtime(&mut system, request, bundle)?;
    report["runtime_binding_enforced"] = json!(true);
    report["configuration"]["model_resolved"] =
        json!(if system.config.new3ds { "new" } else { "old" });
    if request.route == "native" {
        install_native(&mut system, request, library_file, report)?;
    }
    // CodexAstraUlt: Generated code materializes modified locals before an SVC.
    // Observe that existing boundary without altering guest code, replacing raw
    // budget observations, or extending the configured execution budget.
    system.enable_native_comparison_boundaries();
    let neutral = hid::InputState::default();
    system.set_input(neutral);
    hid::update(&mut system, neutral);
    let mut audio = state::Audio::default();
    let mut steps = 0;
    let mut frame = system.frames;
    let mut debug_bytes = 0u64;
    let mut execution_recorded = false;
    let schedule: Vec<_> = CHECKPOINTS
        .into_iter()
        .filter(|cycle| *cycle <= request.limits.max_cycles)
        .collect();
    let mut next_checkpoint = 0;
    let mut next_synchronized_checkpoint = 0;
    let mut last_svc_ordinal = 0;
    let (status, reason, fault) = loop {
        if let Some(fault) = blocker(&system) {
            break ("blocked", "runtime_blocker", fault);
        }
        if system.exited {
            break ("guest_exited", "guest_called_exit_process", Value::Null);
        }
        let reason = if steps >= request.limits.max_steps {
            Some("step_budget")
        } else if system.cpu.cycles >= request.limits.max_cycles {
            Some("cycle_budget")
        } else if system.frames >= request.limits.max_frames {
            Some("frame_budget")
        } else if started.elapsed().as_secs() >= request.limits.max_seconds {
            Some("wall_budget")
        } else {
            None
        };
        if let Some(reason) = reason {
            break ("budget_exhausted", reason, Value::Null);
        }
        if let Err(reason) = system.memory.verify_base_code_fence() {
            break (
                "blocked",
                "native_code_fence",
                json!({"kind":"native_code_fence_violation","reason":reason}),
            );
        }
        let until = schedule
            .get(next_checkpoint)
            .copied()
            .unwrap_or(request.limits.max_cycles);
        if steps == 0 {
            report["guest_execution_attempted"] = json!(true);
        }
        let outcome = system.step(Some(until.min(request.limits.max_cycles)));
        steps += 1;
        // CodexAstraUlt: Publish the first observed execution once; the hot loop
        // does not repeatedly rebuild JSON for an already established boolean.
        if !execution_recorded
            && (system.interpreted_instructions != 0 || system.recompiled_instructions != 0)
        {
            execution_recorded = true;
            report["guest_execution_performed"] = json!(true);
        }
        debug_bytes = debug_bytes.saturating_add(system.debug_output.len() as u64);
        system.debug_output.clear();
        if system.frames != frame {
            frame = system.frames;
            audio.drain(&mut system);
            hid::update(&mut system, neutral);
        }
        if let Some(fault) = blocker(&system) {
            break ("blocked", "runtime_blocker", fault);
        }
        if outcome == StepOutcome::Faulted {
            break (
                "blocked",
                "guest_fault",
                json!({"kind":"guest_fault","live_pc":system.cpu.regs[15]}),
            );
        }
        while let Some(cycle) = schedule
            .get(next_checkpoint)
            .copied()
            .filter(|cycle| system.cpu.cycles >= *cycle)
        {
            audio.drain(&mut system);
            let captured = state::capture(&system, &audio);
            report["checkpoints"]
                .as_array_mut()
                .expect("checkpoint envelope")
                .push(json!({
                "requested_cycle":cycle,"exact_cycle":system.cpu.cycles == cycle,
                "instructions":instruction_counts(&system),"state":captured}));
            next_checkpoint += 1;
        }
        // CodexAstraUlt: Retain at most one full fingerprint for a newly seen
        // SVC, even when it crosses several pending thresholds. Keep its actual
        // cycle and dispatch identity; missing boundaries remain missing.
        if let Some(boundary) = system
            .native_comparison_boundary()
            .filter(|boundary| boundary.ordinal != last_svc_ordinal)
        {
            last_svc_ordinal = boundary.ordinal;
            if let Some(requested_cycle) = schedule
                .get(next_synchronized_checkpoint)
                .copied()
                .filter(|cycle| boundary.cycle >= *cycle)
            {
                audio.drain(&mut system);
                report["synchronized_checkpoints"]
                    .as_array_mut()
                    .expect("synchronized checkpoint envelope")
                    .push(json!({
                        "requested_cycle":requested_cycle,
                        "boundary":{"ordinal":boundary.ordinal,"cycle":boundary.cycle,
                            "number":boundary.number,"svc_pc":boundary.svc_pc,
                            "thread_guest_id":boundary.thread_guest_id},
                        "instructions":instruction_counts(&system),
                        "state":state::capture(&system,&audio)
                    }));
                while schedule
                    .get(next_synchronized_checkpoint)
                    .is_some_and(|cycle| *cycle <= boundary.cycle)
                {
                    next_synchronized_checkpoint += 1;
                }
            }
        }
    };
    audio.drain(&mut system);
    report["status"] = json!(status);
    report["reason"] = json!(reason);
    report["blocker"] = fault;
    report["observed"] = json!({"steps":steps,"cycles":system.cpu.cycles,"frames":system.frames,
        "cycles_after_budget":system.cpu.cycles.saturating_sub(request.limits.max_cycles),
        "interpreted_instructions":system.interpreted_instructions,
        "recompiled_instructions":system.recompiled_instructions,
        "native_callback_fallback_instructions":system.recompiled.as_ref().map_or(0, |library| library.fallbacks()),
        "guest_debug_bytes_discarded":debug_bytes,
        "services_seen":system.services_seen.iter().take(64).map(|s|s.chars().take(32).collect::<String>()).collect::<Vec<_>>(),
        "state":state::capture(&system, &audio)});
    observer(&mut system);
    Ok(())
}

// CodexAstraUlt: Parent hard limits contain parser, native, and blocking-step
// failures. Catching an unwind preserves ordinary diagnostics but cannot turn
// SIGSEGV, SIGKILL, abort or an incomplete process into accepted execution.
pub fn run_fd(descriptor: i32, data_dir: &Path) -> Value {
    let started = Instant::now();
    let request = match request::read(descriptor) {
        Ok(request) => request,
        Err(reason) => {
            let mut report = envelope(None);
            report["reason"] = json!(reason);
            return report;
        }
    };
    let mut report = envelope(Some(&request));
    let result =
        std::panic::catch_unwind(std::panic::AssertUnwindSafe(|| -> Result<(), String> {
            let library = SealedFile::open(
                request.library.descriptor,
                request::LIBRARY_LIMIT,
                Some(request.library.bytes),
            )?;
            let identity = SealedFile::open(
                request.identity_bundle.descriptor,
                request::BUNDLE_LIMIT,
                Some(request.identity_bundle.bytes),
            )?;
            let bundle = identity.map()?;
            execute(
                &request,
                &library,
                &bundle,
                data_dir,
                &mut report,
                started,
                |_| {},
            )
        }));
    match result {
        Ok(Ok(())) => {}
        Ok(Err(reason)) => {
            report["status"] = json!("load_error");
            report["reason"] = json!(reason);
        }
        Err(_) => {
            report["status"] = json!("internal_error");
            report["reason"] = json!("native_worker_panicked");
        }
    }
    report["elapsed_seconds"] = json!(started.elapsed().as_secs_f64());
    report
}

#[cfg(test)]
mod tests;
