//! CodexAstraUlt: Original ARM containers exercise the actual loader and HLE
//! path. Every failure-control places ExitProcess after its blocker, proving
//! the worker stops before the guest can run past a fabricated success reply.

use droidds_runtime_probe::fixture;
use droidds_title_tools::{run, Options};
use serde_json::Value;
use std::{
    fs,
    path::PathBuf,
    sync::{
        atomic::{AtomicU64, Ordering},
        Mutex,
    },
};

// CodexAstraUlt: Each runtime allocates real console RAM. Serialize these
// integration cases while keeping their directories uniquely owned and private.
static RUNTIME_TEST: Mutex<()> = Mutex::new(());
static NEXT: AtomicU64 = AtomicU64::new(0);
struct Case {
    root: PathBuf,
    options: Options,
}
impl Case {
    fn new(image: &[u8]) -> Self {
        let root = std::env::temp_dir().join(format!(
            "droidds-title-test-{}-{}",
            std::process::id(),
            NEXT.fetch_add(1, Ordering::Relaxed)
        ));
        fs::create_dir(&root).unwrap();
        let input = root.join("original.cxi");
        fs::write(&input, image).unwrap();
        let options = Options {
            input,
            data_dir: root.join("runtime-data"),
            max_steps: 100_000,
            max_cycles: 100_000,
            max_frames: 2,
            max_seconds: 30,
            new_model: false,
            trace_scheduler: false,
            trace_cpu_progress: false,
        };
        Self { root, options }
    }
    fn execute(&self) -> Value {
        run(&self.options)
    }
}
impl Drop for Case {
    fn drop(&mut self) {
        fs::remove_dir_all(&self.root).unwrap();
    }
}

// CodexAstraUlt: These instruction encodings are independently authored tests,
// not extracted from any game. Stack and page declarations match loader input.
fn small_guest(words: &[u32]) -> Vec<u8> {
    let code: Vec<_> = words.iter().flat_map(|word| word.to_le_bytes()).collect();
    let mut image = zakuro_fs::testing::ncch(0x0004_0000_0D5D_0007, Some(&code), &[]);
    image[0x21c..0x220].copy_from_slice(&0x1000u32.to_le_bytes());
    image
}

#[test]
fn original_loader_hle_and_pica_fixture_exits_with_exact_accounting() {
    let _lock = RUNTIME_TEST.lock().unwrap();
    let case = Case::new(&fixture::image(0, 0, false));
    let before = fs::read(&case.options.input).unwrap();
    let report = case.execute();
    assert_eq!(report["status"], "guest_exited", "{report:#}");
    assert_eq!(report["observed"]["steps"], 606);
    assert_eq!(report["observed"]["interpreted_instructions"], 606);
    assert_eq!(report["observed"]["recompiled_instructions"], 0);
    assert_eq!(report["observed"]["command_lists"], 1);
    assert_eq!(report["observed"]["draw_calls"], 2);
    assert_eq!(report["observed"]["guest_exited"], true);
    assert_eq!(
        report["input"]["program_id"],
        format!("{:016X}", fixture::PROGRAM_ID)
    );
    assert_eq!(fs::read(&case.options.input).unwrap(), before);
    assert!(report.to_string().len() < 16 * 1024);
}

#[test]
fn new_only_original_container_resolves_new_model_and_commitment() {
    let _lock = RUNTIME_TEST.lock().unwrap();
    let case = Case::new(&fixture::image(0, 2, true));
    let report = case.execute();
    assert_eq!(report["status"], "guest_exited", "{report:#}");
    assert_eq!(report["configuration"]["model_requested"], "old");
    assert_eq!(report["configuration"]["model_resolved"], "new");
    assert_eq!(
        report["input"]["guest_region_limit_bytes"][0],
        178 * 1024 * 1024
    );
}

#[test]
fn unsupported_svc_stops_at_its_exact_instruction_before_exit() {
    let _lock = RUNTIME_TEST.lock().unwrap();
    let case = Case::new(&small_guest(&[0xef00_007f, 0xef00_0003]));
    let report = case.execute();
    assert_eq!(report["status"], "blocked", "{report:#}");
    assert_eq!(report["blocker"]["kind"], "unsupported_svc");
    assert_eq!(report["blocker"]["number"], 0x7f);
    assert_eq!(report["blocker"]["pc"], 0x0010_0000);
    assert_eq!(report["observed"]["steps"], 1);
    assert_eq!(report["observed"]["guest_exited"], false);
}

#[test]
fn unsupported_service_reply_is_not_consumed_by_guest() {
    let _lock = RUNTIME_TEST.lock().unwrap();
    let mut image = fixture::image(0, 0, false);
    // CodexAstraUlt: Mutate only our fixture's cfg:u GetSystemModel command
    // literal; service registration still executes through the real IPC path.
    let positions: Vec<_> = image[0x800..0x1000]
        .chunks_exact(4)
        .enumerate()
        .filter(|(_, bytes)| *bytes == 0x0005_0000u32.to_le_bytes())
        .map(|(at, _)| 0x800 + at * 4)
        .collect();
    assert_eq!(positions.len(), 1);
    image[positions[0]..positions[0] + 4].copy_from_slice(&0xffff_0000u32.to_le_bytes());
    let case = Case::new(&image);
    let report = case.execute();
    assert_eq!(report["status"], "blocked", "{report:#}");
    assert_eq!(report["blocker"]["kind"], "unsupported_service");
    assert_eq!(report["blocker"]["service"], "cfg:u");
    assert_eq!(report["blocker"]["command"], 0xffff);
    assert_eq!(report["observed"]["guest_exited"], false);
    assert_eq!(report["observed"]["draw_calls"], 0);
}

#[test]
fn undefined_instruction_and_breakpoint_are_explicit_blockers() {
    let _lock = RUNTIME_TEST.lock().unwrap();
    for (instruction, kind) in [
        (0xe7f0_00f0, "undefined_instruction"),
        (0xe120_0070, "breakpoint"),
    ] {
        let case = Case::new(&small_guest(&[instruction, 0xef00_0003]));
        let report = case.execute();
        assert_eq!(report["status"], "blocked", "{report:#}");
        assert_eq!(report["blocker"]["kind"], kind);
        assert_eq!(report["blocker"]["pc"], 0x0010_0000);
        assert_eq!(report["observed"]["steps"], 1);
        assert_eq!(report["observed"]["guest_exited"], false);
    }
}

#[test]
fn memory_and_prefetch_faults_stop_without_later_guest_execution() {
    let _lock = RUNTIME_TEST.lock().unwrap();
    for (words, kind, steps) in [
        (
            vec![0xe3a0_0000, 0xe590_1000, 0xef00_0003],
            "memory_fault",
            2,
        ),
        (
            vec![0xe3a0_0000, 0xe12f_ff10, 0xef00_0003],
            "prefetch_abort",
            3,
        ),
    ] {
        let case = Case::new(&small_guest(&words));
        let report = case.execute();
        assert_eq!(report["status"], "blocked", "{report:#}");
        assert_eq!(report["blocker"]["kind"], kind);
        assert_eq!(report["blocker"]["address"], 0);
        assert_eq!(report["observed"]["steps"], steps);
        assert_eq!(report["observed"]["guest_exited"], false);
    }
}

#[test]
fn loop_stops_at_step_and_cycle_limits_without_claiming_success() {
    let _lock = RUNTIME_TEST.lock().unwrap();
    for reason in ["step_budget", "cycle_budget"] {
        let mut case = Case::new(&small_guest(&[0xeaff_fffe]));
        if reason == "step_budget" {
            case.options.max_steps = 7;
        } else {
            case.options.max_cycles = 7;
        }
        let report = case.execute();
        assert_eq!(report["status"], "budget_exhausted", "{report:#}");
        assert_eq!(report["reason"], reason);
        assert_eq!(report["observed"]["steps"], 7);
        assert_eq!(report["observed"]["cycles"], 7);
        assert_eq!(report["observed"]["guest_exited"], false);
    }
}

#[test]
fn idle_scheduler_respects_cycle_and_frame_budgets_without_a_live_thread() {
    let _lock = RUNTIME_TEST.lock().unwrap();
    // CodexAstraUlt: ExitThread removes the only runnable thread without calling
    // ExitProcess. Deadlines must still bound scheduler time, and a frame count
    // alone must not be misclassified as a successful title boot or game exit.
    for reason in ["cycle_budget", "frame_budget"] {
        let mut case = Case::new(&small_guest(&[0xef00_0009]));
        if reason == "cycle_budget" {
            case.options.max_cycles = 7;
        } else {
            case.options.max_cycles = zakuro_core::CYCLES_PER_FRAME * 3;
            case.options.max_frames = 1;
        }
        let report = case.execute();
        assert_eq!(report["status"], "budget_exhausted", "{report:#}");
        assert_eq!(report["reason"], reason);
        assert_eq!(report["observed"]["guest_exited"], false);
        assert!(report["observed"]["cycles"].as_u64().unwrap() <= case.options.max_cycles);
        assert!(report["observed"]["frames"].as_u64().unwrap() <= case.options.max_frames);
        assert_eq!(report["observed"]["interpreted_instructions"], 1);
    }
}

#[test]
fn system_tick_svc_preserves_its_actual_cooperative_cycle_overshoot() {
    let _lock = RUNTIME_TEST.lock().unwrap();
    // CodexAstraUlt: Actual HLE GetSystemTick adds 150 cycles to its one
    // interpreted instruction. A cooperative deadline reports all 151 cycles,
    // never clamps them to the request or executes the following ExitProcess.
    // This example does not establish a maximum for every HLE service path.
    for budget in [1, 7] {
        let mut case = Case::new(&small_guest(&[0xef00_0028, 0xef00_0003]));
        case.options.max_cycles = budget;
        let report = case.execute();
        assert_eq!(report["status"], "budget_exhausted", "{report:#}");
        assert_eq!(report["reason"], "cycle_budget");
        assert_eq!(report["observed"]["steps"], 1);
        assert_eq!(report["observed"]["cycles"], 151);
        assert_eq!(report["observed"]["cycles_after_budget"], 151 - budget);
        assert_eq!(report["observed"]["guest_exited"], false);
        assert_eq!(
            report["configuration"]["budget_boundary"]["cycles"],
            "after_system_step"
        );
    }
}

#[test]
fn malformed_container_and_parser_panic_never_become_execution_success() {
    let _lock = RUNTIME_TEST.lock().unwrap();
    let case = Case::new(b"not an executable");
    let report = case.execute();
    assert_eq!(report["status"], "load_error");
    assert_eq!(report["observed"]["steps"], 0);
    let mut truncated = vec![0; 0x200];
    truncated[0x100..0x104].copy_from_slice(b"NCCH");
    truncated[0x18f] = 4;
    let case = Case::new(&truncated);
    let report = case.execute();
    assert!(matches!(
        report["status"].as_str(),
        Some("internal_error" | "load_error")
    ));
    assert_eq!(report["observed"]["steps"], 0);
}

#[test]
fn existing_runtime_directory_is_preserved_and_refused() {
    let _lock = RUNTIME_TEST.lock().unwrap();
    let case = Case::new(&small_guest(&[0xef00_0003]));
    fs::create_dir(&case.options.data_dir).unwrap();
    let save = case.options.data_dir.join("owner-save.bin");
    fs::write(&save, b"keep me").unwrap();
    let report = case.execute();
    assert_eq!(report["status"], "load_error");
    assert_eq!(report["observed"]["steps"], 0);
    assert_eq!(fs::read(save).unwrap(), b"keep me");
}

#[test]
fn standalone_update_and_dlc_titles_never_execute_as_a_base_game() {
    let _lock = RUNTIME_TEST.lock().unwrap();
    for (prefix, reason) in [
        (0x0004_000eu64, "update_input_requires_a_base_title"),
        (0x0004_008cu64, "dlc_input_requires_a_base_title"),
    ] {
        let mut image = small_guest(&[0xef00_0003]);
        let program = (prefix << 32) | 0x0d5d_0007;
        image[0x118..0x120].copy_from_slice(&program.to_le_bytes());
        let case = Case::new(&image);
        let report = case.execute();
        assert_eq!(report["status"], "load_error", "{report:#}");
        assert_eq!(report["reason"], reason);
        assert_eq!(report["observed"]["steps"], 0);
        assert_eq!(report["input"]["program_id"], format!("{program:016X}"));
    }
}

// CodexAstraUlt: This original guest sleeps for one millisecond in a loop,
// reproducing the shape of an early wait without copying any private title.
// Tracing must retain the same execution, timing and memory accounting.
#[test]
fn scheduler_trace_preserves_sleep_loop_execution_and_is_disabled_by_default() {
    let _lock = RUNTIME_TEST.lock().unwrap();
    let image = small_guest(&[
        0xe59f_0008, // LDR r0, [pc, #8]: the one-millisecond literal below.
        0xe3a0_1000, // MOV r1, #0: upper half of nanoseconds.
        0xef00_000a, // SVC SleepThread.
        0xeaff_fffb, // B back to the first load after resumption.
        1_000_000,
    ]);
    let mut reports = Vec::new();
    for enabled in [false, true] {
        let mut case = Case::new(&image);
        case.options.trace_scheduler = enabled;
        case.options.max_cycles = 268_111_856;
        case.options.max_frames = 120;
        let report = case.execute();
        assert_eq!(report["status"], "budget_exhausted", "{report:#}");
        assert_eq!(report["reason"], "cycle_budget", "{report:#}");
        assert_eq!(report["configuration"]["scheduler_trace"], enabled);
        assert_eq!(report["diagnostic_trace"].is_object(), enabled);
        assert!(report.to_string().len() < 256 * 1024);
        let mut observed = report["observed"].clone();
        observed.as_object_mut().unwrap().remove("elapsed_seconds");
        reports.push(observed);
    }
    assert_eq!(reports[0], reports[1]);
}

// CodexAstraUlt: Independently authored ARM countdown and stationary branch
// expose different register progress without requiring any private game bytes.
#[test]
fn cpu_progress_distinguishes_finite_countdown_from_stationary_branch() {
    let _lock = RUNTIME_TEST.lock().unwrap();
    let mut changing = Case::new(&small_guest(&[
        0xe59f_000c, // LDR r0, [pc, #12]: iteration-count literal.
        0xe250_0001, // SUBS r0, r0, #1.
        0x1aff_fffd, // BNE back to SUBS.
        0xe3a0_102a, // MOV r1, #42: completion checkpoint.
        0xef00_0003, // SVC ExitProcess.
        150_000,
    ]));
    changing.options.trace_cpu_progress = true;
    changing.options.max_steps = 500_000;
    changing.options.max_cycles = 1_000_000;
    let report = changing.execute();
    assert_eq!(report["status"], "guest_exited", "{report:#}");
    assert_eq!(report["observed"]["steps"], 300_003);
    let trace = &report["cpu_progress"];
    assert_eq!(trace["samples_seen"], 5);
    assert_eq!(trace["samples_omitted"], 0);
    let values: Vec<_> = trace["prefix"]
        .as_array()
        .unwrap()
        .iter()
        .skip(1)
        .map(|sample| sample["registers"][0].as_u64().unwrap())
        .collect();
    assert_eq!(values[0], 117_240);
    assert!(values.windows(2).all(|pair| pair[0] > pair[1]));
    assert_eq!(trace["final"]["registers"][0], 0);
    assert_eq!(trace["final"]["registers"][1], 42);

    let mut stationary = Case::new(&small_guest(&[0xeaff_fffe]));
    stationary.options.trace_cpu_progress = true;
    stationary.options.max_steps = 200_000;
    stationary.options.max_cycles = 1_000_000;
    let report = stationary.execute();
    assert_eq!(report["status"], "budget_exhausted");
    assert_eq!(report["reason"], "step_budget");
    let trace = &report["cpu_progress"];
    assert_eq!(trace["samples_seen"], 4);
    // CodexAstraUlt: Loading queues the main thread; the live CPU has not yet
    // been selected at step zero, so its actual initial PC is zero, not entry.
    assert_eq!(trace["prefix"][0]["registers"][15], 0);
    assert!(trace["prefix"][0]["current_thread"].is_null());
    assert!(trace["prefix"][0]["thread_guest_id"].is_null());
    for sample in trace["prefix"]
        .as_array()
        .unwrap()
        .iter()
        .skip(1)
        .chain(std::iter::once(&trace["final"]))
    {
        assert_eq!(sample["registers"][0], 0);
        assert_eq!(sample["registers"][15], 0x0010_0000);
        assert_eq!(sample["current_thread"], 0);
        assert_eq!(sample["thread_guest_id"], 0);
    }
    assert_eq!(trace["recent_dispatches"].as_array().unwrap().len(), 64);
    assert!(trace["recent_dispatches"]
        .as_array()
        .unwrap()
        .iter()
        .all(|entry| entry["pc"] == 0x0010_0000 && entry["thumb"] == false));
}

// CodexAstraUlt: Both optional traces, separately and together, must preserve
// the real guest's CPU/rendering/memory counters and remain absent by default.
#[test]
fn cpu_progress_and_scheduler_switches_preserve_original_guest_execution() {
    let _lock = RUNTIME_TEST.lock().unwrap();
    let mut observations = Vec::new();
    for cpu_enabled in [false, true] {
        for scheduler_enabled in [false, true] {
            let mut case = Case::new(&fixture::image(0, 0, false));
            case.options.trace_cpu_progress = cpu_enabled;
            case.options.trace_scheduler = scheduler_enabled;
            let report = case.execute();
            assert_eq!(report["status"], "guest_exited", "{report:#}");
            assert_eq!(report["configuration"]["cpu_progress_trace"], cpu_enabled);
            assert_eq!(report["cpu_progress"].is_object(), cpu_enabled);
            assert_eq!(report["diagnostic_trace"].is_object(), scheduler_enabled);
            if cpu_enabled {
                let trace = &report["cpu_progress"];
                assert_eq!(trace["samples_seen"], 1);
                assert_eq!(trace["samples_omitted"], 0);
                assert_eq!(trace["prefix"][0]["steps"], 0);
                assert!(trace["tail"].as_array().unwrap().is_empty());
                assert_eq!(trace["final"]["steps"], 606);
                assert_eq!(trace["final"]["cycles"], report["observed"]["cycles"]);
                assert_eq!(
                    trace["final"]["registers"][15],
                    report["observed"]["final_pc"]
                );
                assert_eq!(trace["recent_dispatches"].as_array().unwrap().len(), 64);
            }
            let mut observed = report["observed"].clone();
            observed.as_object_mut().unwrap().remove("elapsed_seconds");
            observations.push(observed);
        }
    }
    assert!(observations.windows(2).all(|pair| pair[0] == pair[1]));
}

// CodexAstraUlt: A fault exactly on the periodic boundary must retain that
// sample and stop before the following exit, without consuming a fake success.
#[test]
fn cpu_progress_retains_fault_boundary_and_does_not_trace_loader_failure() {
    let _lock = RUNTIME_TEST.lock().unwrap();
    let mut case = Case::new(&small_guest(&[
        0xe59f_0010, // LDR r0, [pc, #16]: count literal after the unused exit.
        0xe250_0001, // SUBS r0, r0, #1.
        0x1aff_fffd, // BNE back to SUBS.
        0xe3a0_102a, // MOV r1, #42.
        0xef00_007f, // Unsupported SVC at dispatch 65,521.
        0xef00_0003, // Must never run past the blocker.
        32_759,
    ]));
    case.options.trace_cpu_progress = true;
    case.options.trace_scheduler = true;
    let report = case.execute();
    assert_eq!(report["status"], "blocked", "{report:#}");
    assert_eq!(report["blocker"]["kind"], "unsupported_svc");
    assert_eq!(report["blocker"]["pc"], 0x0010_0010);
    assert_eq!(report["observed"]["steps"], 65_521);
    assert_eq!(report["observed"]["guest_exited"], false);
    let trace = &report["cpu_progress"];
    assert_eq!(trace["samples_seen"], 2);
    assert_eq!(trace["prefix"][1]["steps"], 65_521);
    assert_eq!(trace["prefix"][1], trace["final"]);
    let last = trace["recent_dispatches"]
        .as_array()
        .unwrap()
        .last()
        .unwrap();
    assert_eq!(last["pc"], 0x0010_0010);
    assert_eq!(last["thumb"], false);

    let mut bad = Case::new(b"not an executable");
    bad.options.trace_cpu_progress = true;
    let report = bad.execute();
    assert_eq!(report["status"], "load_error");
    assert_eq!(report["configuration"]["cpu_progress_trace"], true);
    assert!(report["cpu_progress"].is_null());
}

// CodexAstraUlt: Original ARM-to-Thumb code proves that recorded mode bits are
// separated from instruction addresses, including the final dispatched SVC.
#[test]
fn cpu_progress_recent_dispatches_preserve_arm_thumb_order_and_terminal_state() {
    let _lock = RUNTIME_TEST.lock().unwrap();
    let mut case = Case::new(&small_guest(&[
        0xe28f_0001, // ADD r0, pc, #1: address 0x100009 selects Thumb at +8.
        0xe12f_ff10, // BX r0.
        0xdf03_222a, // Thumb MOVS r2,#42; SVC ExitProcess.
    ]));
    case.options.trace_cpu_progress = true;
    let report = case.execute();
    assert_eq!(report["status"], "guest_exited", "{report:#}");
    let trace = &report["cpu_progress"];
    assert_eq!(trace["samples_seen"], 1);
    assert_eq!(trace["final"]["steps"], 4);
    assert_eq!(trace["final"]["registers"][2], 42);
    assert_eq!(trace["final"]["cpsr"].as_u64().unwrap() & 0x20, 0x20);
    let expected = serde_json::json!([
        {"pc": 0x0010_0000, "thumb": false},
        {"pc": 0x0010_0004, "thumb": false},
        {"pc": 0x0010_0008, "thumb": true},
        {"pc": 0x0010_000a, "thumb": true}
    ]);
    assert_eq!(trace["recent_dispatches"], expected);
    assert_ne!(
        trace["recent_dispatches"][3]["pc"],
        trace["final"]["registers"][15]
    );
}

// CodexAstraUlt: Dispatch cadence also observes an idle scheduler. A repeated
// live register set without additional interpreted instructions must not be
// attributed to a live thread or labeled another executed guest instruction.
#[test]
fn cpu_progress_idle_dispatches_keep_registers_unattributed_and_execution_unchanged() {
    let _lock = RUNTIME_TEST.lock().unwrap();
    let mut observations = Vec::new();
    for enabled in [false, true] {
        let mut case = Case::new(&small_guest(&[0xef00_0009]));
        case.options.trace_cpu_progress = enabled;
        case.options.max_steps = 65_522;
        case.options.max_cycles = 1_000_000_000;
        case.options.max_frames = 1200;
        let report = case.execute();
        assert_eq!(report["status"], "budget_exhausted", "{report:#}");
        assert_eq!(report["reason"], "step_budget");
        assert_eq!(report["observed"]["interpreted_instructions"], 1);
        if enabled {
            let trace = &report["cpu_progress"];
            assert_eq!(trace["samples_seen"], 2);
            let periodic = &trace["prefix"][1];
            let terminal = &trace["final"];
            assert_eq!(periodic["steps"], 65_521);
            assert_eq!(terminal["steps"], 65_522);
            assert_eq!(periodic["registers"], terminal["registers"]);
            for state in [periodic, terminal] {
                assert_eq!(state["interpreted_instructions"], 1);
                assert!(state["current_thread"].is_null());
                assert!(state["thread_guest_id"].is_null());
                assert_eq!(state["all_blocked"], true);
            }
            assert_eq!(trace["recent_dispatches"].as_array().unwrap().len(), 1);
            assert_eq!(trace["recent_dispatches"][0]["pc"], 0x0010_0000);
        }
        let mut observed = report["observed"].clone();
        observed.as_object_mut().unwrap().remove("elapsed_seconds");
        observations.push(observed);
    }
    assert_eq!(observations[0], observations[1]);
}
