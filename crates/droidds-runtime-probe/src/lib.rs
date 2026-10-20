//! CodexAstraUlt: Original guest execution through the actual loader, HLE kernel,
//! services and PICA path. This bounded probe is not a retail compatibility test.

pub mod fixture;
// CodexAstraUlt: The visible original guest has a persistent session while the
// frozen 0.0.5 fixture and its exact instruction/pixel gates remain unchanged.
pub mod homebrew;
#[cfg(feature = "producer")]
pub mod producer;

use serde_json::{json, Value};
use std::{
    fs,
    path::Path,
    time::{Duration, Instant},
};
use zakuro_common::memory_map::{CONFIG_MEM_VADDR, PAGE_SIZE, SHARED_PAGE_VADDR};
use zakuro_core::memory::MemoryRegion;
use zakuro_core::{loader, Config, StepOutcome, System};
use zakuro_cpu::Bus;

const MAX_STEPS: u64 = 100_000;
const MAX_CYCLES: u64 = 100_000;
const MAX_WALL: Duration = Duration::from_secs(90);
// CodexAstraUlt: The fixed guest route executes 606 ARM instructions, including
// two instructions in the deliberately uncompiled helper. Exact accounting
// catches the conditional-backedge compiler defect reproduced during integration.
const EXPECTED_INSTRUCTIONS: u64 = 606;

// CodexAstraUlt: Every dispatch checks the exact immutable fixture page. No CRO,
// remapping, code-changing callbacks or concurrent writers occur in this fixture.
// This restriction does not qualify general dynamic-module lifecycle safety.
struct FrozenText(Vec<u8>);

impl FrozenText {
    fn capture(system: &mut System) -> Self {
        let mut bytes = vec![0; PAGE_SIZE as usize];
        system.memory.read_bytes(fixture::TEXT, &mut bytes);
        Self(bytes)
    }
    fn verify(&self, system: &mut System) -> Result<(), String> {
        // CodexAstraUlt: Repeated dispatch guards reuse bounded stack storage.
        let mut bytes = [0; PAGE_SIZE as usize];
        system.memory.read_bytes(fixture::TEXT, &mut bytes);
        if self.0.as_slice() != bytes {
            Err("immutable fixture code changed before or during dispatch".into())
        } else {
            Ok(())
        }
    }
    fn step(&self, system: &mut System) -> Result<StepOutcome, String> {
        self.verify(system)?;
        let outcome = system.step(Some(system.cpu.cycles.saturating_add(4096).min(MAX_CYCLES)));
        self.verify(system)?;
        Ok(outcome)
    }
}

fn require(condition: bool, message: impl Into<String>) -> Result<(), String> {
    if condition {
        Ok(())
    } else {
        Err(message.into())
    }
}

// CodexAstraUlt: Only the marker and original fixture belong in this dedicated
// scratch directory. Reject foreign files/symlinks and preserve their contents.
fn prepare_scratch(directory: &Path) -> Result<(), String> {
    if directory.exists() {
        let metadata = fs::symlink_metadata(directory).map_err(|error| error.to_string())?;
        require(
            metadata.is_dir() && !metadata.file_type().is_symlink(),
            "runtime scratch is not an ordinary directory",
        )?;
    } else {
        fs::create_dir_all(directory).map_err(|error| error.to_string())?;
    }
    let owner = directory.join("droidds-runtime-owner.txt");
    for entry in fs::read_dir(directory).map_err(|error| error.to_string())? {
        let entry = entry.map_err(|error| error.to_string())?;
        let name = entry.file_name();
        require(
            name == "droidds-runtime-owner.txt" || name == "runtime-fixture.cxi",
            "runtime scratch contains unrelated files",
        )?;
        require(
            entry
                .file_type()
                .map_err(|error| error.to_string())?
                .is_file(),
            "runtime scratch file is not ordinary",
        )?;
    }
    if owner.exists() {
        require(
            fs::read(&owner).map_err(|error| error.to_string())?
                == b"DroidDS original runtime probe v1\n",
            "runtime scratch ownership marker differs",
        )?;
    } else {
        require(
            !directory.join("runtime-fixture.cxi").exists(),
            "unowned runtime fixture exists",
        )?;
        fs::write(&owner, b"DroidDS original runtime probe v1\n")
            .map_err(|error| error.to_string())?;
    }
    Ok(())
}

fn load_fixture(
    directory: &Path,
    old: u8,
    new: u8,
    platform: bool,
    force_new: bool,
) -> Result<System, String> {
    let path = directory.join("runtime-fixture.cxi");
    fs::write(&path, fixture::image(old, new, platform))
        .map_err(|error| format!("write original fixture: {error}"))?;
    loader::load(
        &path,
        Config {
            new3ds: force_new,
            clock: Some(4_000_000_000_000),
            data_dir: Some(directory.to_path_buf()),
            texture_packs: false,
            skip_idle_loops: false,
            ..Config::default()
        },
    )
    .map_err(|error| format!("actual fixture loader: {error}"))
}

// CodexAstraUlt: Missing/stale origins are errors before the real ABI bridge is
// installed; silently interpreting everything cannot satisfy this native gate.
fn install_native(system: &mut System, library: &Path) -> Result<(), String> {
    let mut raw = recomp_abi::Library::open(library)?;
    require(
        raw.generation() == recomp_abi::GENERATION,
        "runtime native ABI generation differs",
    )?;
    require(
        raw.origins(0)
            .is_some_and(|origin| !origin.pieces().is_empty() && !origin.functions().is_empty()),
        "runtime native origin metadata missing",
    )?;
    let mut outside = false;
    let text_end = fixture::TEXT + fixture::native_text().len() as u32;
    let stale = raw.check(0, 0, |address, out| {
        if address < fixture::TEXT
            || address
                .checked_add(out.len() as u32)
                .is_none_or(|end| end > text_end)
        {
            outside = true;
            out.fill(0);
        } else {
            system.memory.read_bytes(address, out);
        }
    });
    require(
        !outside && stale == 0 && raw.lookup(fixture::TEXT).is_some(),
        "runtime native origins stale, out of range, or entry missing",
    )?;
    require(
        raw.lookup(fixture::FALLBACK).is_none(),
        "deliberate interpreter helper unexpectedly has native code",
    )?;
    let mut native = zakuro_core::recompiled::Library::open(library)?;
    require(
        native.check(&mut system.memory) == 0 && native.has_code(fixture::TEXT),
        "runtime bridge origin check failed",
    )?;
    system.recompiled = Some(native);
    Ok(())
}

fn read_pixels(system: &mut System) -> Vec<[u8; 4]> {
    system.sync_gpu(fixture::COLOR, 8 * 8 * 4);
    (0..64)
        .map(|i| {
            let mut pixel = [0; 4];
            // CodexAstraUlt: Independently decode one 8x8 PICA tile: interleave
            // three x/y bits and reverse its ABGR bytes. Sharing the production
            // format/layout helper could hide a renderer bug from this oracle.
            let (x, y) = (i % 8, i / 8);
            let offset = (0..3).fold(0, |at, bit| {
                at | ((x >> bit) & 1) << (2 * bit) | ((y >> bit) & 1) << (2 * bit + 1)
            }) * 4;
            system
                .memory
                .read_bytes(fixture::COLOR + offset, &mut pixel);
            [pixel[3], pixel[2], pixel[1], pixel[0]]
        })
        .collect()
}

fn pixel_mismatches(pixels: &[[u8; 4]]) -> usize {
    let expected = fixture::expected_pixels();
    if pixels.len() != expected.len() {
        return expected.len();
    }
    pixels
        .iter()
        .zip(expected)
        .filter(|(actual, expected)| **actual != *expected)
        .count()
}

fn execute(system: &mut System) -> Result<u64, String> {
    let frozen = FrozenText::capture(system);
    let start = Instant::now();
    for step in 1..=MAX_STEPS {
        require(
            system.cpu.cycles < MAX_CYCLES && start.elapsed() < MAX_WALL,
            "runtime guest budget or wall deadline exceeded",
        )?;
        match frozen.step(system)? {
            StepOutcome::Ran => {}
            StepOutcome::Exited => return Ok(step),
            StepOutcome::Faulted => {
                return Err(format!(
                    "runtime guest fault at {:08x}",
                    system.cpu.regs[15]
                ))
            }
        }
    }
    Err("runtime outer dispatch limit exceeded".into())
}

fn run_case(
    directory: &Path,
    library: &Path,
    name: &str,
    native: bool,
    hardware: bool,
) -> Result<(Value, Vec<[u8; 4]>), String> {
    let mut system = load_fixture(directory, 0, 0, false, false)?;
    if native {
        install_native(&mut system, library)?;
    }
    // CodexAstraUlt: Propagate required renderer initialization errors, unlike the
    // loader's compatibility fallback; this fixture has no persistent GPU cache.
    let device = if hardware {
        Some(system.gpu.enable_hardware_renderer(1, None, None)?)
    } else {
        None
    };
    let execution = execute(&mut system);
    let steps = execution.as_ref().copied().unwrap_or(0);
    let pixels = read_pixels(&mut system);
    let mismatch = pixel_mismatches(&pixels);
    let checkpoint = system.memory.read32(fixture::DATA);
    let fallback = system.memory.read32(fixture::DATA + 4);
    let model = system.memory.read32(fixture::DATA + 8);
    let gpu = system.gpu.hardware_diagnostics();
    let shader_words = system
        .gpu
        .vertex_shader
        .program
        .iter()
        .filter(|&&word| word != 0)
        .count();
    // CodexAstraUlt: Failed output keeps its bounded counters and first few
    // differing pixels, so a device failure can be diagnosed from one report.
    let differing: Vec<Value> = pixels.iter().zip(fixture::expected_pixels()).enumerate()
        .filter(|(_, (actual, expected))| **actual != *expected).take(4)
        .map(|(index,(actual,expected))|json!({"index":index,"actual":actual,"expected":expected})).collect();
    let validation = (|| -> Result<(), String> {
        execution?;
        require(
            checkpoint == fixture::CHECKPOINT && fallback == 1 && model == 0,
            format!("{name}: guest result words differ: {checkpoint:08x}/{fallback}/{model}"),
        )?;
        require(
            system.gpu.command_lists == 1
                && system.gpu.draw_calls == 2
                && system.gpu.vertices_drawn == 6,
            format!(
                "{name}: PICA route differs: {}/{}/{}",
                system.gpu.command_lists, system.gpu.draw_calls, system.gpu.vertices_drawn
            ),
        )?;
        require(
            mismatch == 0,
            format!("{name}: {mismatch} PICA pixels differ"),
        )?;
        require(
            system.unimplemented_svcs.is_empty()
                && system.services.unimplemented.is_empty()
                && system.memory.fault_summary().is_empty()
                && system.prefetch_aborts.is_empty()
                && system.fatal_errors.is_empty(),
            format!("{name}: unsupported call, memory fault or fatal guest error"),
        )?;
        require(
            system.services_seen.contains("gsp::Gpu") && system.services_seen.contains("cfg:u"),
            "guest did not obtain its actual services",
        )?;
        // CodexAstraUlt: Missing native entries return to outer CPU dispatch;
        // they are distinct from instructions interpreted by an ABI callback.
        require(
            system.cpu.cycles == EXPECTED_INSTRUCTIONS
                && system.interpreted_instructions
                    == if native { 2 } else { EXPECTED_INSTRUCTIONS }
                && system.recompiled_instructions
                    == if native { EXPECTED_INSTRUCTIONS - 2 } else { 0 }
                && steps == if native { 10 } else { EXPECTED_INSTRUCTIONS }
                && system
                    .recompiled
                    .as_ref()
                    .map_or(0, |library| library.fallbacks())
                    == 0,
            format!("{name}: exact native/interpreter progress or budget accounting differs"),
        )?;
        require(
            shader_words == 3
                && system.gpu.vertex_shader.program[..3]
                    == [0x13 << 26, (0x13 << 26) | (1 << 21) | (1 << 12), 0x22 << 26],
            "actual uploaded PICA shader program differs",
        )?;
        if let Some(gpu) = &gpu {
            require(
                gpu.recorded_draws == 2
                    && gpu.submissions > 0
                    && gpu.draw_errors == 0
                    && gpu.software_raster_fallbacks == 0
                    && gpu.resource_limit_events == 0
                    && gpu.last_error.is_none(),
                format!("{name}: hardware route/fallback diagnostic rejected"),
            )?;
        }
        require(
            gpu.is_some() == hardware,
            "hardware activation differs from requested route",
        )?;
        Ok(())
    })();
    let error = validation.err();
    Ok((
        json!({"name":name,"status":if error.is_none(){"passed"}else{"failed"},"error":error,
        "first_pixel_mismatches":differing,"guest_exited":system.exited,
        "checkpoint":checkpoint,"fallback_checkpoint":fallback,"guest_model":model,
        "command_lists":system.gpu.command_lists,"draw_calls":system.gpu.draw_calls,"vertices_drawn":system.gpu.vertices_drawn,
        "pixels_checked":pixels.len(),"mismatched_pixels":mismatch,
        "interpreted_instructions":system.interpreted_instructions,"recompiled_instructions":system.recompiled_instructions,
        "native_fallback_instructions":system.recompiled.as_ref().map_or(0,|library| library.fallbacks()),
        "svc_unimplemented":system.unimplemented_svcs.len(),"service_unimplemented":system.services.unimplemented.len(),
        "memory_faults":system.memory.fault_summary().len(),"shader_program_words":shader_words,"hardware":gpu,
        "hardware_device":device,"steps":steps,"cycles":system.cpu.cycles,"services_seen":system.services_seen}),
        pixels,
    ))
}

fn safety(directory: &Path, library: &Path) -> Result<Value, String> {
    let mut controls = Vec::new();
    {
        let mut system = load_fixture(directory, 0, 0, false, false)?;
        require(
            system.memory.write32_privileged(fixture::TEXT, 0),
            "control could not mutate code",
        )?;
        let rejected = install_native(&mut system, library)
            .err()
            .ok_or("stale runtime origins were accepted")?;
        require(
            rejected.contains("origins stale"),
            format!("stale control failed for unrelated reason: {rejected}"),
        )?;
        controls.push(json!({"name":"stale_origin_rejected","status":"passed","rejection":rejected,"native_instructions":0}));
    }
    {
        let mut system = load_fixture(directory, 0, 0, false, false)?;
        install_native(&mut system, library)?;
        let frozen = FrozenText::capture(&mut system);
        require(
            system.memory.write32_privileged(fixture::TEXT, 0),
            "control could not mutate code",
        )?;
        let rejected = frozen
            .step(&mut system)
            .err()
            .ok_or("changed runtime code reached dispatch")?;
        require(
            system.cpu.cycles == 0
                && system.recompiled_instructions == 0
                && system.interpreted_instructions == 0,
            "changed code control executed guest work",
        )?;
        controls.push(json!({"name":"changed_code_before_dispatch_rejected","status":"passed","rejection":rejected,"native_instructions":0,"interpreted_instructions":0}));
    }
    {
        let mut system = load_fixture(directory, 0, 0, false, false)?;
        install_native(&mut system, library)?;
        let frozen = FrozenText::capture(&mut system);
        system.memory.write32(fixture::DATA + 16, 1);
        for _ in 0..100 {
            frozen.step(&mut system)?;
            if !system.memory.fault_summary().is_empty() {
                break;
            }
        }
        require(
            system.recompiled_instructions > 0
                && system.memory.fault_summary() == vec![(fixture::TEXT, 1)],
            format!(
                "native code-write control failed: {:?}",
                system.memory.fault_summary()
            ),
        )?;
        frozen.verify(&mut system)?;
        controls.push(json!({"name":"executable_guest_store_rejected","status":"passed","native_instructions":system.recompiled_instructions,"rejected_writes":1,"code_unchanged":true}));
    }
    Ok(json!({"policy":"immutable_single_thread_fixture","status":"passed","controls":controls}))
}

// CodexAstraUlt: Every layout comes from actual loader state and guest CFG IPC.
// Exercise the real application commitment boundary and a service Base page.
fn layouts(directory: &Path) -> Result<Vec<Value>, String> {
    let mut reports = Vec::new();
    for (name, old, new, platform, force, app, system_bytes, base, selector, limit) in [
        ("old3ds_64", 0, 0, false, false, 64, 44, 20, 0, 64),
        ("old3ds_96", 2, 0, false, false, 96, 12, 20, 2, 96),
        ("new3ds_legacy64", 0, 0, false, true, 124, 100, 32, 6, 64),
        ("new3ds_124", 0, 1, true, false, 124, 100, 32, 6, 124),
        ("new3ds_178", 0, 2, true, false, 178, 46, 32, 7, 178),
    ] {
        let mut machine = load_fixture(directory, old, new, platform, force)?;
        let sizes = [
            MemoryRegion::Application,
            MemoryRegion::System,
            MemoryRegion::Base,
        ]
        .map(|region| machine.memory.phys.region_size(region));
        let expected = [app, system_bytes, base].map(|mib| mib * 1024 * 1024);
        require(
            sizes == expected,
            format!("{name}: physical regions differ: {sizes:?}"),
        )?;
        let config =
            [0x30, 0x40, 0x44, 0x48].map(|offset| machine.memory.read32(CONFIG_MEM_VADDR + offset));
        require(
            config
                == [
                    selector,
                    limit * 1024 * 1024,
                    system_bytes * 1024 * 1024,
                    base * 1024 * 1024,
                ],
            format!("{name}: configuration page differs: {config:?}"),
        )?;
        let new_model = platform || force;
        require(
            machine.config.new3ds == new_model
                && machine.memory.read8(SHARED_PAGE_VADDR + 5) == if new_model { 2 } else { 1 },
            format!("{name}: shared/model reporting differs"),
        )?;
        let free = machine.memory.phys.region_free(MemoryRegion::Application);
        let allocated = machine
            .memory
            .phys
            .allocate(MemoryRegion::Application, free)
            .ok_or_else(|| format!("{name}: cannot allocate remaining quota"))?;
        require(
            machine
                .memory
                .phys
                .allocate(MemoryRegion::Application, PAGE_SIZE)
                .is_none(),
            format!("{name}: allocation exceeded application limit"),
        )?;
        machine.memory.phys.free(allocated);
        require(
            machine.memory.phys.region_free(MemoryRegion::Application) == free,
            format!("{name}: allocation failed to restore quota"),
        )?;
        let base_page = machine
            .memory
            .phys
            .allocate(MemoryRegion::Base, PAGE_SIZE)
            .ok_or_else(|| format!("{name}: Base allocation unavailable"))?;
        machine.memory.phys.free(base_page);
        let steps = execute(&mut machine)?;
        require(
            steps == EXPECTED_INSTRUCTIONS && machine.cpu.cycles == EXPECTED_INSTRUCTIONS,
            format!("{name}: loader guest instruction accounting differs"),
        )?;
        let guest_model = machine.memory.read32(fixture::DATA + 8);
        require(
            guest_model == if new_model { 3 } else { 0 },
            format!("{name}: guest CFG model answer differs"),
        )?;
        require(
            machine.memory.read32(fixture::DATA) == fixture::CHECKPOINT
                && machine.services.unimplemented.is_empty()
                && machine.unimplemented_svcs.is_empty()
                && machine.memory.fault_summary().is_empty(),
            format!("{name}: loader guest did not complete cleanly"),
        )?;
        reports.push(json!({"name":name,"status":"passed","new3ds":new_model,"old_mode":old,"new_mode":new,
            "physical_regions_bytes":sizes,"application_limit_bytes":limit*1024*1024,"config_words":config,
            "guest_model":guest_model,"allocation_boundary_rejected":true,"allocation_free_restored":true,
            "base_allocation_passed":true,"guest_exited":machine.exited,"steps":steps}));
    }
    Ok(reports)
}

pub fn run(native_library_directory: &Path, writable_scratch_directory: &Path) -> Value {
    let started = Instant::now();
    let mut report = json!({"schema":1,"kind":"droidds-runtime-probe","contract":"zakuro-412900a-runtime-v1",
        "fixture":fixture::IDENTITY,"native_library":fixture::LIBRARY,"status":"failed","error":null,
        "cases":[],"code_safety":null,"memory_layouts":[],"pixel_comparisons":0,"pixel_mutation_controls":0,
        "limitations":["Original bounded homebrew only; no retail game, presentation, input or audio qualification.",
          "Immutable single-thread fixture text; no CRO unloading, executable remapping or concurrent writer qualification.",
          "Two PICA draws do not establish instruction coverage, sustained memory stability or game performance."]});
    let mut owned = false;
    let result = (|| -> Result<(), String> {
        prepare_scratch(writable_scratch_directory)?;
        owned = true;
        let library = native_library_directory.join(fixture::LIBRARY);
        let mut reference = None;
        for (name, native, hardware) in [
            ("interpreter_software", false, false),
            ("native_software", true, false),
            ("native_vulkan", true, true),
        ] {
            let (case, pixels) =
                run_case(writable_scratch_directory, &library, name, native, hardware)?;
            let failed = case["error"].as_str().map(str::to_owned);
            report["cases"].as_array_mut().unwrap().push(case);
            if let Some(error) = failed {
                return Err(error);
            }
            if let Some(expected) = &reference {
                require(
                    expected == &pixels,
                    format!("{name}: software/interpreter image differs"),
                )?;
                report["pixel_comparisons"] =
                    json!(report["pixel_comparisons"].as_u64().unwrap() + 1);
            } else {
                reference = Some(pixels);
            }
        }
        let mut changed = reference.unwrap();
        changed[17][0] ^= 1;
        require(
            pixel_mismatches(&changed) == 1,
            "pixel oracle did not reject one changed channel",
        )?;
        report["pixel_mutation_controls"] = json!(1);
        report["code_safety"] = safety(writable_scratch_directory, &library)?;
        report["memory_layouts"] = json!(layouts(writable_scratch_directory)?);
        report["status"] = json!("passed");
        Ok(())
    })();
    if let Err(error) = result {
        report["error"] = json!(error);
    }
    // CodexAstraUlt: Keep one reusable ownership marker and remove only our
    // original fixture after success or failure, never unowned user contents.
    if owned {
        let path = writable_scratch_directory.join("runtime-fixture.cxi");
        if fs::symlink_metadata(&path)
            .is_ok_and(|meta| meta.is_file() && !meta.file_type().is_symlink())
        {
            if let Err(error) = fs::remove_file(&path) {
                report["status"] = json!("failed");
                report["error"] = json!(format!("remove owned runtime fixture: {error}"));
            }
        }
    }
    report["elapsed_ms"] = json!(started.elapsed().as_millis());
    report
}

#[cfg(test)]
mod tests {
    use super::*;
    #[test]
    fn original_image_has_actual_parser_visible_segments_and_modes() {
        let bytes = fixture::image(2, 1, true);
        let header = zakuro_fs::ncch::ExHeader::parse(&bytes[0x200..0x600]).unwrap();
        assert_eq!(header.text.address, fixture::TEXT);
        assert_eq!(header.rodata.address, fixture::RODATA);
        assert_eq!(header.data.address, fixture::DATA);
        assert_eq!(header.n3ds_system_mode, 1);
        assert_eq!(header.n3ds_cpu_speed, 1);
        assert!(header.enable_l2_cache);
    }
    #[test]
    fn strict_pixel_oracle_rejects_size_color_and_position_changes() {
        let expected = fixture::expected_pixels();
        assert_eq!(pixel_mismatches(&expected), 0);
        assert_ne!(pixel_mismatches(&expected[..63]), 0);
        let mut modified = expected.clone();
        modified.swap(0, 4);
        assert_eq!(pixel_mismatches(&modified), 2);
        modified = expected.clone();
        modified.swap(4, 60);
        assert_eq!(pixel_mismatches(&modified), 2);
        modified = expected;
        modified[0][3] ^= 1;
        assert_eq!(pixel_mismatches(&modified), 1);
    }
}
