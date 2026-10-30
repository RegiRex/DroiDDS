//! CodexAstraUlt: Bounded original workload for scheduler costs on this host.
//! The native ABI spin is a control for dispatch overhead, not guest throughput.

use std::time::Instant;
use zakuro_core::{Config, System, StepOutcome, memory::{MemoryRegion, Permission, MemoryState},
    kernel::{thread::ThreadStatus, object::KObject, sync::{Timer, ResetType}}, recompiled};
use zakuro_cpu::Bus;
use recomp_abi::{Context, Entry, EXIT_BUDGET};

const BASE: u32 = 0x0010_0000;
unsafe extern "C" fn spin(ctx: *mut Context) {
    unsafe { (*ctx).budget = 0; (*ctx).exit = EXIT_BUDGET; }
}
static ENTRIES: [Entry; 1] = [Entry { address: BASE, code: spin }];

fn setup(native: bool, kind: &str, count: usize) -> System {
    let mut system = System::new(Config { skip_idle_loops: false, ..Config::default() });
    let block = system.memory.phys.allocate(MemoryRegion::Application, 4096).unwrap();
    system.memory.map(BASE, block.addr, 4096, Permission::RW | Permission::EXECUTE, MemoryState::Code);
    system.memory.write32(BASE, 0xEAFF_FFFE);
    let main = system.kernel.create_thread("original-main", BASE, BASE+0xF00, 0, 0x20, 0);
    system.map_tls_page(main);
    system.kernel.schedule(&mut system.cpu, 0);
    for index in 0..count {
        let id = system.kernel.create_thread("original-waiter", BASE, BASE+0xE00, index as u32, 0x30, 0);
        if kind.starts_with("timers") {
            let timer = system.kernel.objects.insert(KObject::Timer(Timer {
                name: "original-timer".into(), reset_type: ResetType::OneShot,
                signaled: false, fire_at: Some(1_000_000_000 + index as u64), interval: 0,
            }));
            system.kernel.timers.push(timer);
            let thread = system.kernel.thread_mut(id);
            thread.status = ThreadStatus::WaitSync;
            thread.wait_objects = vec![timer];
        } else {
            let thread = system.kernel.thread_mut(id);
            thread.status = ThreadStatus::Sleeping;
            thread.wakeup_at = Some(1_000_000_000 + index as u64);
        }
    }
    if kind == "timers-reversed" {
        system.kernel.timers.reverse();
    }
    system.kernel.reschedule_pending = false;
    if native {
        // CodexAstraUlt: Authored permanent tables implement exactly B-to-self.
        let linked = unsafe { recompiled::Linked::new(0, recomp_abi::ABI,
            ENTRIES.as_ptr().cast(), 1,
            std::ptr::NonNull::<recomp_abi::Module>::dangling().as_ptr().cast(), 0) };
        system.recompiled = Some(recompiled::Library::linked(&linked).unwrap());
    }
    system
}

fn main() {
    let args: Vec<_> = std::env::args().collect();
    assert!(!cfg!(debug_assertions), "scheduler cost observations require --release");
    assert_eq!(args.len(), 4, "usage: scheduler_cost interpreter|native sleepers|timers|timers-reversed 0..64");
    let route = &args[1];
    let kind = &args[2];
    let count: usize = args[3].parse().unwrap();
    assert!(count <= 64 && ["interpreter", "native"].contains(&route.as_str()));
    assert!(["sleepers", "timers", "timers-reversed"].contains(&kind.as_str()));
    let native = route == "native";
    let mut system = setup(native, kind, count);
    // CodexAstraUlt: Warm once, then retain five fixed-size measured samples.
    for sample in 0..6 {
        // CodexAstraUlt: Six samples stay below the first video frame, which
        // otherwise rebuilds timer registration and changes the order control.
        let instructions = 200_000;
        let mut dispatches = 0;
        let start_cycle = system.cpu.cycles;
        let start_interpreted = system.interpreted_instructions;
        let start_native = system.recompiled_instructions;
        let start = Instant::now();
        while system.cpu.cycles < start_cycle + instructions {
            let deadline = (system.cpu.cycles + if native { 100 } else { 1 }).min(start_cycle + instructions);
            assert_eq!(system.step(Some(deadline)), StepOutcome::Ran);
            dispatches += 1;
        }
        let elapsed = start.elapsed().as_secs_f64();
        assert_eq!(system.cpu.cycles - start_cycle, instructions);
        assert_eq!(system.cpu.regs[15], BASE);
        assert_eq!(system.kernel.current_thread, Some(0));
        assert_eq!(system.frames, 0);
        assert_eq!(system.interpreted_instructions - start_interpreted, if native { 0 } else { instructions });
        assert_eq!(system.recompiled_instructions - start_native, if native { instructions } else { 0 });
        if sample != 0 {
            println!("{route},{kind},{count},{sample},{instructions},{dispatches},{elapsed:.9}");
        }
    }
}
