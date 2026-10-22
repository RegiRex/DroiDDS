//! CodexAstraUlt: Sparse host-worker snapshots distinguish changing CPU state
//! from a repeated wait without reading guest memory or enabling the profiler.
//! Live registers belong to the post-dispatch machine state; the final history
//! separately lists recent dispatch addresses, which can include a faulting one.

use serde_json::{json, Value};
use std::collections::VecDeque;
use zakuro_core::System;

const INTERVAL_STEPS: u64 = 65_521;
const PREFIX_CAPACITY: usize = 16;
const TAIL_CAPACITY: usize = 112;

// CodexAstraUlt: Store fixed-size scalars while running, and serialize only at
// the end. Thread slots may be reused, so retain the guest identity too. A null
// current thread leaves live registers unattributed rather than inventing one.
struct State {
    steps: u64,
    cycles: u64,
    interpreted_instructions: u64,
    registers: [u32; 16],
    cpsr: u32,
    current_thread: Option<u32>,
    thread_guest_id: Option<u32>,
    reschedule_pending: bool,
    all_blocked: bool,
}

impl State {
    fn capture(system: &System, steps: u64) -> Self {
        Self {
            steps,
            cycles: system.cpu.cycles,
            interpreted_instructions: system.interpreted_instructions,
            registers: system.cpu.regs,
            cpsr: system.cpu.cpsr.to_bits(),
            current_thread: system.kernel.current_thread,
            thread_guest_id: system
                .kernel
                .current_thread
                .and_then(|id| system.kernel.threads.get(id as usize).map(|t| t.guest_id)),
            reschedule_pending: system.kernel.reschedule_pending,
            all_blocked: system.kernel.all_blocked,
        }
    }

    fn json(&self) -> Value {
        json!({
            "steps": self.steps, "cycles": self.cycles,
            "interpreted_instructions": self.interpreted_instructions,
            "registers": self.registers, "cpsr": self.cpsr,
            "current_thread": self.current_thread, "thread_guest_id": self.thread_guest_id,
            "reschedule_pending": self.reschedule_pending, "all_blocked": self.all_blocked
        })
    }
}

// CodexAstraUlt: A nonoverlapping prefix/tail never retains more than 128
// samples, irrespective of the requested run length. This type is constructed
// only for --trace-cpu-progress; normal workers allocate no sampling storage.
pub(crate) struct CpuProgress {
    prefix: Vec<State>,
    tail: VecDeque<State>,
    samples_seen: u64,
}

impl CpuProgress {
    pub(crate) fn new(system: &System) -> Self {
        let mut result = Self {
            prefix: Vec::with_capacity(PREFIX_CAPACITY),
            tail: VecDeque::with_capacity(TAIL_CAPACITY),
            samples_seen: 0,
        };
        result.push(State::capture(system, 0));
        result
    }

    fn push(&mut self, state: State) {
        self.samples_seen += 1;
        if self.prefix.len() < PREFIX_CAPACITY {
            self.prefix.push(state);
        } else {
            if self.tail.len() == TAIL_CAPACITY {
                self.tail.pop_front();
            }
            self.tail.push_back(state);
        }
    }

    pub(crate) fn after_step(&mut self, system: &System, steps: u64) {
        if steps.is_multiple_of(INTERVAL_STEPS) {
            self.push(State::capture(system, steps));
        }
    }

    // CodexAstraUlt: The terminal snapshot is independent of the periodic
    // cadence, so a short run or fault still has exact stopping registers.
    // Existing history is global across threads and oldest-first. Its low bit
    // encodes Thumb mode, not an address bit; no opcode or memory load is made.
    pub(crate) fn finish(self, system: &System, steps: u64) -> Value {
        let recent: Vec<_> = system
            .recent_instructions()
            .into_iter()
            .map(|entry| json!({"pc": entry & !1, "thumb": entry & 1 != 0}))
            .collect();
        json!({
            "schema_version": 1, "interval_steps": INTERVAL_STEPS,
            "prefix_capacity": PREFIX_CAPACITY, "tail_capacity": TAIL_CAPACITY,
            "samples_seen": self.samples_seen,
            "samples_omitted": self.samples_seen - (self.prefix.len() + self.tail.len()) as u64,
            "prefix": self.prefix.iter().map(State::json).collect::<Vec<_>>(),
            "tail": self.tail.iter().map(State::json).collect::<Vec<_>>(),
            "final": State::capture(system, steps).json(), "recent_dispatches": recent
        })
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    // CodexAstraUlt: Exercise admission/eviction at the maximum worker cadence
    // without spending a billion interpreter dispatches on a retention test.
    #[test]
    fn cpu_progress_retention_is_bounded_and_preserves_nonoverlapping_order() {
        let system = System::new(zakuro_core::Config::default());
        let mut progress = CpuProgress::new(&system);
        let final_steps = 1_000_000_000;
        let samples = 1 + final_steps / INTERVAL_STEPS;
        for sample in 1..samples {
            progress.push(State::capture(&system, sample * INTERVAL_STEPS));
        }
        assert_eq!(progress.prefix.len(), PREFIX_CAPACITY);
        assert_eq!(progress.tail.len(), TAIL_CAPACITY);
        assert_eq!(progress.samples_seen, samples);
        for (sample, state) in progress.prefix.iter().enumerate() {
            assert_eq!(state.steps, sample as u64 * INTERVAL_STEPS);
        }
        for (index, state) in progress.tail.iter().enumerate() {
            assert_eq!(
                state.steps,
                (samples - TAIL_CAPACITY as u64 + index as u64) * INTERVAL_STEPS
            );
        }
        let report = progress.finish(&system, final_steps);
        assert_eq!(report["samples_omitted"], samples - 128);
        assert_eq!(report["final"]["steps"], final_steps);
        assert_eq!(report["recent_dispatches"].as_array().unwrap().len(), 0);
        assert!(report.to_string().len() < 64 * 1024);
    }
}
