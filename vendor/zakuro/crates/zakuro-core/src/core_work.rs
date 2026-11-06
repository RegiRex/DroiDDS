//! CodexAstraUlt: Fixed host timing for natural coarse core events. These totals
//! do not clock individual CPU instructions, retain traces or alter guest time.

use std::time::Duration;

/// CodexAstraUlt: One lifetime scope; nested command work is already in `wall`.
/// Wall duration includes host waits and is not processor utilization.
#[derive(Debug, Default, Clone, Copy, PartialEq, Eq)]
pub struct CoreWorkTiming {
    pub calls: u64,
    pub wall: Duration,
    pub nested_command_wall: Duration,
}

impl CoreWorkTiming {
    // CodexAstraUlt: Saturation preserves bounded monotonic observations even
    // for pathological session lengths; recording never affects guest state.
    pub(crate) fn record(&mut self, wall: Duration, nested_command_wall: Duration) {
        self.calls = self.calls.saturating_add(1);
        self.wall = self.wall.saturating_add(wall);
        self.nested_command_wall = self.nested_command_wall.saturating_add(nested_command_wall);
    }
}

/// CodexAstraUlt: These scopes do not overlap each other. SVC and frame work can
/// execute command lists; subtract each nested subset before comparing with
/// core time outside command processing and frontend scanout. The residual is
/// still unclassified CPU, scheduling, memory synchronization and guard work.
#[derive(Debug, Default, Clone, Copy, PartialEq, Eq)]
pub struct CoreWorkDiagnostics {
    /// CPU-dispatched HLE call only, excluding trace/scheduler bookkeeping.
    pub svc: CoreWorkTiming,
    /// Clock, renderer boundary, GSP refresh/interrupts and optional pacing.
    pub frame: CoreWorkTiming,
    /// DSP advance/semaphore and IR, camera, wireless and Download Play ticks.
    pub audio: CoreWorkTiming,
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::{memory, Config, FrameOutcome, StepOutcome, System, CYCLES_PER_FRAME};
    use zakuro_cpu::Bus;

    // CodexAstraUlt: This tiny authored ARM guest reads the emulated tick,
    // performs ordinary CPU work and exits; it contains no private title code.
    fn original_tick_guest() -> System {
        let mut system = System::new(Config { skip_idle_loops: false, ..Config::default() });
        let block = system.memory.phys.allocate(memory::MemoryRegion::Application, 0x1000).unwrap();
        system.memory.map(0x0010_0000, block.addr, 0x1000,
            memory::Permission::RW | memory::Permission::EXECUTE, memory::MemoryState::Code);
        for (index, word) in [0xEF00_0028, 0xE3A0_2007, 0xEF00_0003].iter().enumerate() {
            system.memory.write32(0x0010_0000 + index as u32 * 4, *word);
        }
        let thread = system.kernel.create_thread("timing-original", 0x0010_0000, 0x0010_0F00, 0, 0x30, 0);
        system.map_tls_page(thread);
        system.kernel.schedule(&mut system.cpu, 0);
        system
    }

    // CodexAstraUlt: Due frame/audio work still precedes the actual SVC, whose
    // tick charge and instruction boundary remain unchanged. An ordinary MOV
    // adds no timing event, and a stopped machine adds no further observations.
    #[test]
    fn coarse_work_tracks_real_events_without_changing_guest_cycles() {
        let mut system = original_tick_guest();
        assert_eq!(*system.core_work_diagnostics(), CoreWorkDiagnostics::default());
        system.gpu.busy = Duration::from_secs(3);
        system.cpu.cycles = CYCLES_PER_FRAME;
        assert_eq!(system.step(Some(CYCLES_PER_FRAME + 1)), StepOutcome::Ran);
        assert_eq!(system.frames, 1);
        assert_eq!(system.cpu.regs[0] as u64, CYCLES_PER_FRAME + 1);
        assert_eq!(system.cpu.regs[1], 0);
        assert_eq!(system.cpu.cycles, CYCLES_PER_FRAME + 151);
        assert_eq!(system.cpu.regs[15], 0x0010_0004);
        let timings = *system.core_work_diagnostics();
        assert_eq!((timings.svc.calls, timings.frame.calls, timings.audio.calls), (1, 1, 1));
        for timing in [timings.svc, timings.frame, timings.audio] {
            assert_eq!(timing.nested_command_wall, Duration::ZERO, "earlier commands are not charged again");
        }
        assert_eq!(system.step(None), StepOutcome::Ran);
        assert_eq!(system.cpu.regs[2], 7);
        assert_eq!(system.cpu.cycles, CYCLES_PER_FRAME + 152);
        assert_eq!(*system.core_work_diagnostics(), timings);
        assert_eq!(system.step(None), StepOutcome::Exited);
        assert_eq!(system.cpu.cycles, CYCLES_PER_FRAME + 153);
        assert_eq!(system.interpreted_instructions, 3);
        assert_eq!(system.core_work_diagnostics().svc.calls, 2);
        let stopped = *system.core_work_diagnostics();
        assert_eq!(system.step(None), StepOutcome::Exited);
        assert_eq!(*system.core_work_diagnostics(), stopped);
    }

    // CodexAstraUlt: The full-frame frontend calls end_frame outside step; it
    // must contribute once, without creating a fictitious SVC/audio event.
    #[test]
    fn coarse_work_includes_the_full_frame_frontend_boundary() {
        let mut system = System::new(Config::default());
        assert_eq!(system.run_frame(), FrameOutcome::Completed);
        assert_eq!(system.cpu.cycles, CYCLES_PER_FRAME);
        assert_eq!(system.frames, 1);
        let timings = system.core_work_diagnostics();
        assert_eq!((timings.svc.calls, timings.frame.calls, timings.audio.calls), (0, 1, 0));
        assert_eq!(timings.frame.nested_command_wall, Duration::ZERO);
    }

    // CodexAstraUlt: Deterministic durations qualify subset accounting and
    // overflow without timing thresholds or a long-running benchmark.
    #[test]
    fn coarse_work_keeps_nested_totals_and_saturates() {
        let mut timing = CoreWorkTiming::default();
        timing.record(Duration::from_secs(10), Duration::from_secs(7));
        timing.record(Duration::from_secs(4), Duration::from_secs(1));
        assert_eq!(timing.calls, 2);
        assert_eq!(timing.wall, Duration::from_secs(14));
        assert_eq!(timing.nested_command_wall, Duration::from_secs(8));
        timing.calls = u64::MAX;
        timing.record(Duration::MAX, Duration::MAX);
        assert_eq!(timing.calls, u64::MAX);
        assert_eq!(timing.wall, Duration::MAX);
        assert_eq!(timing.nested_command_wall, Duration::MAX);
        timing.record(Duration::from_secs(1), Duration::from_secs(1));
        assert_eq!(timing.calls, u64::MAX);
        assert_eq!(timing.wall, Duration::MAX);
        assert_eq!(timing.nested_command_wall, Duration::MAX);
    }
}
