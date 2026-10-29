//! CodexAstraUlt: Original ARM and ABI fixtures qualify route-independent
//! scheduling, including deadlines that do not coincide with preemption ticks.

use super::*;
use kernel::thread::ThreadStatus;
use recomp_abi::{Context, Entry, EXIT_BUDGET, EXIT_SVC};
use zakuro_cpu::Bus;

const BASE: u32 = 0x0010_0000;
const CREATE_PC: u32 = BASE + 100_000 * 4;

// CodexAstraUlt: This authored ABI stub implements only ARM B-to-self: every
// consumed instruction leaves all CPU state unchanged, including its PC.
unsafe extern "C" fn spin(ctx: *mut Context) {
    unsafe {
        (*ctx).budget = 0;
        (*ctx).exit = EXIT_BUDGET;
    }
}

// CodexAstraUlt: A long original NOP sequence ends in SVC CreateThread. Keeping
// its syscall inside one native dispatch catches retroactive preempt requests.
unsafe extern "C" fn create_after_nops(ctx: *mut Context) {
    unsafe {
        let ctx = &mut *ctx;
        let nops = ((CREATE_PC - ctx.r[15]) / 4).min(ctx.budget as u32);
        ctx.r[15] += nops * 4;
        ctx.budget -= nops as i32;
        if ctx.budget > 0 {
            ctx.r[15] += 4;
            ctx.budget -= 1;
            ctx.svc = 8;
            ctx.exit = EXIT_SVC;
        } else {
            ctx.exit = EXIT_BUDGET;
        }
    }
}

static SPIN: [Entry; 1] = [Entry { address: BASE, code: spin }];
static CREATE: [Entry; 2] = [Entry { address: BASE, code: create_after_nops },
    Entry { address: CREATE_PC, code: create_after_nops }];

// CodexAstraUlt: Static fixture tables outlive each library. Neither optional
// diagnostic protection nor private runtime admission is bypassed by this core
// scheduling test: it deliberately uses the ordinary unrestricted core route.
fn system(native: bool, create: bool) -> System {
    let mut system = System::new(Config { skip_idle_loops: false, ..Config::default() });
    let bytes = if create { 0x63000 } else { 0x1000 };
    let block = system.memory.phys.allocate(memory::MemoryRegion::Application, bytes).unwrap();
    system.memory.map(BASE, block.addr, bytes, Permission::RW | Permission::EXECUTE, MemoryState::Code);
    if create {
        for pc in (BASE..CREATE_PC).step_by(4) {
            system.memory.write32(pc, 0xE1A0_0000); // MOV r0,r0 / NOP.
        }
        system.memory.write32(CREATE_PC, 0xEF00_0008);
    } else {
        system.memory.write32(BASE, 0xEAFF_FFFE);
    }
    let thread = system.kernel.create_thread("original-main", BASE, BASE + 0xF00, 0, 0x30, 0);
    system.map_tls_page(thread);
    system.kernel.schedule(&mut system.cpu, 0);
    system.kernel.reschedule_pending = false;
    if native {
        let entries = if create { &CREATE[..] } else { &SPIN[..] };
        // SAFETY: Static original entries use the expected ABI; no module
        // records exist, and their required empty pointer remains aligned.
        let linked = unsafe { recompiled::Linked::new(0, recomp_abi::ABI,
            entries.as_ptr().cast(), entries.len() as u32,
            std::ptr::NonNull::<recomp_abi::Module>::dangling().as_ptr().cast(), 0) };
        system.recompiled = Some(recompiled::Library::linked(&linked).unwrap());
    }
    system
}

// CodexAstraUlt: The limit is an exact guest-cycle boundary, not an equal number
// of host dispatches. Every assertion also rejects an accidental zero-work loop.
fn run_to(system: &mut System, cycle: u64) -> usize {
    let mut steps = 0;
    while system.cpu.cycles < cycle {
        assert_eq!(system.step(Some(cycle)), StepOutcome::Ran);
        steps += 1;
        assert!(steps <= cycle as usize + 1);
    }
    assert_eq!(system.cpu.cycles, cycle);
    steps
}

#[test]
fn single_thread_keeps_cadence_without_empty_native_unwinds() {
    for native in [false, true] {
        let mut system = system(native, false);
        let steps = run_to(&mut system, 100_000);
        assert!(!system.kernel.reschedule_pending, "native={native}");
        assert_eq!(system.next_preempt, 106_496, "native={native}");
        assert_eq!(system.cpu.regs[15], BASE);
        assert_eq!(steps, if native { 1 } else { 100_000 });
    }
}

// CodexAstraUlt: Deadline completion queues a switch without executing even one
// extra old-thread instruction; the next call selects the higher-priority wake.
#[test]
fn sleeping_thread_wakes_at_the_same_exact_cycle_on_both_routes() {
    for native in [false, true] {
        let mut system = system(native, false);
        let sleeper = system.kernel.create_thread("original-sleeper", BASE, BASE + 0xE00, 7, 0x20, 0);
        system.map_tls_page(sleeper);
        let thread = system.kernel.thread_mut(sleeper);
        thread.status = ThreadStatus::Sleeping;
        thread.wakeup_at = Some(20_000);
        system.kernel.reschedule_pending = false;
        run_to(&mut system, 20_000);
        assert_eq!(system.kernel.current_thread, Some(0));
        assert!(system.kernel.reschedule_pending, "native={native}");
        assert_eq!(system.next_preempt, 24_576);
        run_to(&mut system, 20_001);
        assert_eq!(system.kernel.current_thread, Some(sleeper), "native={native}");
        assert_eq!(system.cpu.regs[0], 7);
        assert_eq!(system.kernel.next_event(), None);
    }
}

// CodexAstraUlt: A waited timer is also a scheduler deadline, even while another
// runnable thread executes continuously; periodic preemption cannot delay it.
#[test]
fn waited_timer_fires_at_the_same_exact_cycle_on_both_routes() {
    for native in [false, true] {
        let mut system = system(native, false);
        system.cpu.regs[1] = 0;
        kernel::svc::dispatch(&mut system, 0x1A);
        let timer = system.cpu.regs[1];
        system.cpu.regs[0] = timer;
        system.cpu.regs[2] = 100_000;
        system.cpu.regs[3] = 0;
        system.cpu.regs[1] = 0;
        system.cpu.regs[4] = 0;
        kernel::svc::dispatch(&mut system, 0x1B);
        let waiter = system.kernel.create_thread("original-timer-waiter", BASE, BASE + 0xE00, 9, 0x20, 0);
        system.map_tls_page(waiter);
        let object = system.kernel.resolve(timer).unwrap();
        let thread = system.kernel.thread_mut(waiter);
        thread.status = ThreadStatus::WaitSync;
        thread.wait_objects = vec![object];
        thread.wait_all = false;
        thread.wakeup_at = None;
        system.kernel.reschedule_pending = false;
        let due = kernel::thread::nanos_to_ticks(100_000);
        assert_eq!(system.kernel.next_event(), Some(due));
        run_to(&mut system, due);
        assert!(system.kernel.reschedule_pending, "native={native}");
        assert_eq!(system.kernel.current_thread, Some(0));
        run_to(&mut system, due + 1);
        assert_eq!(system.kernel.current_thread, Some(waiter));
        assert_eq!(system.cpu.regs[0], 9);
    }
}

// CodexAstraUlt: An already-ready peer still receives the periodic scheduling
// opportunity. Suppressing empty quanta must not suppress useful preemption.
#[test]
fn ready_peer_retains_the_exact_periodic_boundary() {
    for native in [false, true] {
        let mut system = system(native, false);
        let peer = system.kernel.create_thread("original-ready-peer", BASE, BASE + 0xE00, 5, 0x20, 0);
        system.map_tls_page(peer);
        system.kernel.reschedule_pending = false;
        run_to(&mut system, PREEMPT_INTERVAL);
        assert_eq!(system.kernel.current_thread, Some(0));
        assert!(system.kernel.reschedule_pending);
        assert_eq!(system.next_preempt, 2 * PREEMPT_INTERVAL);
        run_to(&mut system, PREEMPT_INTERVAL + 1);
        assert_eq!(system.kernel.current_thread, Some(peer));
        assert_eq!(system.cpu.regs[0], 5);
    }
}

// CodexAstraUlt: A syscall at a nonquantum boundary requests its own scheduling
// without moving the periodic cadence to the native dispatch's end.
#[test]
fn create_thread_after_long_native_dispatch_keeps_the_periodic_phase() {
    for native in [false, true] {
        let mut system = system(native, true);
        system.cpu.regs[0] = 0x20;
        system.cpu.regs[1] = BASE;
        system.cpu.regs[2] = 17;
        system.cpu.regs[3] = BASE + 0xE00;
        system.cpu.regs[4] = 0;
        run_to(&mut system, 100_001);
        assert_eq!(system.kernel.threads.len(), 2);
        assert!(system.kernel.reschedule_pending);
        assert_eq!(system.next_preempt, 106_496, "native={native}");
        assert_eq!(system.cpu.regs[15], CREATE_PC + 4);
        run_to(&mut system, 100_002);
        assert_eq!(system.kernel.current_thread, Some(1));
        assert_eq!(system.cpu.regs[0], 17);
    }
}

// CodexAstraUlt: Markers observe completed syscalls without changing execution,
// survive ordinary instructions unchanged, and retain the exiting thread ID.
#[test]
fn comparison_boundary_is_opt_in_and_uses_completed_svc_cycles() {
    let mut results = Vec::new();
    for enabled in [false, true] {
        let mut system = system(false, false);
        system.memory.write32(BASE, 0xEF00_0028); // GetSystemTick charges 150 cycles.
        system.memory.write32(BASE + 4, 0xE1A0_0000);
        system.memory.write32(BASE + 8, 0xEF00_0003); // ExitProcess clears current_thread.
        if enabled {
            system.enable_native_comparison_boundaries();
        }
        assert_eq!(system.native_comparison_boundary(), None);
        assert_eq!(system.step(None), StepOutcome::Ran);
        let first = system.native_comparison_boundary();
        assert_eq!(system.cpu.cycles, 151);
        if enabled {
            assert_eq!(first, Some(diagnostics::NativeComparisonBoundary { ordinal: 1, cycle: 151,
                number: 0x28, svc_pc: BASE, thread_guest_id: Some(0) }));
            system.enable_native_comparison_boundaries();
        }
        assert_eq!(system.step(None), StepOutcome::Ran);
        assert_eq!(system.native_comparison_boundary(), first);
        assert_eq!(system.step(None), StepOutcome::Exited);
        assert_eq!(system.kernel.current_thread, None);
        if enabled {
            assert_eq!(system.native_comparison_boundary(), Some(diagnostics::NativeComparisonBoundary {
                ordinal: 2, cycle: 153, number: 3, svc_pc: BASE + 8, thread_guest_id: Some(0) }));
        } else {
            assert_eq!(system.native_comparison_boundary(), None);
            assert!(system.native_comparison_boundary.is_none());
        }
        results.push((system.cpu.cycles, system.cpu.regs, system.kernel.reschedule_pending, system.next_preempt));
    }
    assert_eq!(results[0], results[1]);
}
