//! CodexAstraUlt: Opt-in, bounded scheduler/SVC metadata for local diagnostic
//! tools. No guest strings, memory reads, instruction bytes or per-frame logs
//! enter this trace; ordinary frontends allocate no trace storage.

use std::collections::VecDeque;

use serde::Serialize;

use crate::kernel::{
    object::{KObject, ObjectId},
    thread::{Thread, ThreadId, ThreadStatus, WaitResult, WaitSyscall},
};
use crate::System;

pub const PREFIX_CAPACITY: usize = 64;
pub const TAIL_CAPACITY: usize = 128;
pub const THREAD_CAPACITY: usize = 64;
pub const WAIT_OBJECT_CAPACITY: usize = 8;
pub const PENDING_CAPACITY: usize = 64;
const SVC_COUNT_CAPACITY: usize = 128;

// CodexAstraUlt: Return registers are scalar ABI observations, not uniformly
// ResultCodes: for example GetSystemTick returns a value and blocked calls have
// no observed return until the originating thread resumes.
#[derive(Debug, Clone, Serialize, PartialEq, Eq)]
#[serde(tag = "kind", rename_all = "snake_case")]
pub enum TraceEventKind {
    Svc {
        entry_cycle: u64,
        thread: Option<ThreadId>,
        pc: Option<u32>,
        number: u32,
        args: [u32; 6],
        returns: Option<[u32; 4]>,
        outcome: &'static str,
        wakeup_at: Option<u64>,
    },
    Schedule {
        previous_thread: Option<ThreadId>,
        next_thread: Option<ThreadId>,
    },
    WaitResume {
        thread: ThreadId,
        guest_id: u32,
        number: u32,
        svc_pc: Option<u32>,
        return_pc: u32,
        returns: [u32; 4],
        wait_result: &'static str,
        signaled_index: Option<usize>,
    },
}

#[derive(Debug, Clone, Serialize, PartialEq, Eq)]
pub struct TraceEvent {
    pub sequence: u64,
    pub cycle: u64,
    #[serde(flatten)]
    pub detail: TraceEventKind,
}

#[derive(Debug, Clone, Serialize)]
pub struct SvcCount {
    pub number: u32,
    pub count: u64,
}

#[derive(Debug, Clone, Serialize)]
pub struct WaitObjectSnapshot {
    pub id: u32,
    pub kind: &'static str,
    pub signaled: bool,
    pub owner: Option<ThreadId>,
    pub count: Option<i64>,
    pub deadline: Option<u64>,
}

#[derive(Debug, Clone, Serialize)]
pub struct ThreadSnapshot {
    pub id: ThreadId,
    pub guest_id: u32,
    pub status: &'static str,
    pub pc: u32,
    pub priority: u32,
    pub wakeup_at: Option<u64>,
    pub wait_all: bool,
    pub wait_address: Option<u32>,
    pub wait_syscall: Option<u32>,
    pub wait_objects_total: usize,
    pub wait_objects_truncated: usize,
    pub wait_objects: Vec<WaitObjectSnapshot>,
}

// CodexAstraUlt: These are observed scheduler fields, including its cached
// all_blocked flag and pending-reschedule state, never a deadlock verdict.
#[derive(Debug, Clone, Serialize)]
pub struct SchedulerSnapshot {
    pub cycle: u64,
    pub current_thread: Option<ThreadId>,
    pub live_pc: u32,
    pub reschedule_pending: bool,
    pub all_blocked: bool,
    pub next_kernel_event: Option<u64>,
    pub threads_total: usize,
    pub threads_truncated: usize,
    pub threads: Vec<ThreadSnapshot>,
}

#[derive(Debug, Clone, Serialize)]
pub struct DiagnosticTraceSnapshot {
    pub schema_version: u32,
    pub prefix_capacity: usize,
    pub tail_capacity: usize,
    pub thread_capacity: usize,
    pub wait_object_capacity: usize,
    pub pending_capacity: usize,
    pub events_seen: u64,
    pub events_omitted: u64,
    pub svc_counts: Vec<SvcCount>,
    pub other_svc_calls: u64,
    pub pending_dropped: u64,
    pub prefix: Vec<TraceEvent>,
    pub tail: Vec<TraceEvent>,
    pub scheduler: SchedulerSnapshot,
}

#[derive(Clone, Copy)]
struct PendingCall {
    thread: ThreadId,
    guest_id: u32,
    number: u32,
    pc: Option<u32>,
}

// CodexAstraUlt: Allocations happen once when enabled. Fixed admission limits
// bound event retention, counters and deferred-call correlation independently
// of how long a title polls or how many threads it creates.
pub(crate) struct TraceState {
    events_seen: u64,
    prefix: Vec<TraceEvent>,
    tail: VecDeque<TraceEvent>,
    svc_counts: [u64; SVC_COUNT_CAPACITY],
    other_svc_calls: u64,
    pending: [Option<PendingCall>; PENDING_CAPACITY],
    pending_dropped: u64,
}

impl TraceState {
    fn new() -> Self {
        Self {
            events_seen: 0,
            prefix: Vec::with_capacity(PREFIX_CAPACITY),
            tail: VecDeque::with_capacity(TAIL_CAPACITY),
            svc_counts: [0; SVC_COUNT_CAPACITY],
            other_svc_calls: 0,
            pending: [None; PENDING_CAPACITY],
            pending_dropped: 0,
        }
    }

    fn record(&mut self, cycle: u64, detail: TraceEventKind) {
        self.events_seen = self.events_seen.saturating_add(1);
        let event = TraceEvent {
            sequence: self.events_seen,
            cycle,
            detail,
        };
        if self.prefix.len() < PREFIX_CAPACITY {
            self.prefix.push(event);
        } else {
            if self.tail.len() == TAIL_CAPACITY {
                self.tail.pop_front();
            }
            self.tail.push_back(event);
        }
    }

    fn remove_pending(&mut self, thread: ThreadId) -> Option<PendingCall> {
        self.pending
            .iter_mut()
            .find(|slot| slot.is_some_and(|call| call.thread == thread))?
            .take()
    }

    fn insert_pending(&mut self, call: PendingCall) {
        self.remove_pending(call.thread);
        if let Some(slot) = self.pending.iter_mut().find(|slot| slot.is_none()) {
            *slot = Some(call);
        } else {
            self.pending_dropped = self.pending_dropped.saturating_add(1);
        }
    }
}

// CodexAstraUlt: Capture only register scalars before dispatch. The interpreter
// supplies the actual SVC address; native dispatch deliberately uses null rather
// than attributing a whole compiled block's entry to its eventual syscall.
pub(crate) struct SvcEntry {
    cycle: u64,
    thread: Option<ThreadId>,
    pc: Option<u32>,
    number: u32,
    args: [u32; 6],
}

impl System {
    /// CodexAstraUlt: Enable on a fresh diagnostic run. Calling again preserves
    /// collected evidence; tracing across a save-state restore is unsupported.
    pub fn enable_diagnostic_trace(&mut self) {
        if self.diagnostic_trace.is_none() {
            self.diagnostic_trace = Some(Box::new(TraceState::new()));
        }
    }

    /// CodexAstraUlt: Read bounded metadata without consuming waits or signals.
    pub fn diagnostic_trace_snapshot(&self) -> Option<DiagnosticTraceSnapshot> {
        let trace = self.diagnostic_trace.as_ref()?;
        Some(DiagnosticTraceSnapshot {
            schema_version: 1,
            prefix_capacity: PREFIX_CAPACITY,
            tail_capacity: TAIL_CAPACITY,
            thread_capacity: THREAD_CAPACITY,
            wait_object_capacity: WAIT_OBJECT_CAPACITY,
            pending_capacity: PENDING_CAPACITY,
            events_seen: trace.events_seen,
            events_omitted: trace
                .events_seen
                .saturating_sub((trace.prefix.len() + trace.tail.len()) as u64),
            svc_counts: trace
                .svc_counts
                .iter()
                .enumerate()
                .filter(|(_, count)| **count != 0)
                .map(|(number, &count)| SvcCount {
                    number: number as u32,
                    count,
                })
                .collect(),
            other_svc_calls: trace.other_svc_calls,
            pending_dropped: trace.pending_dropped,
            prefix: trace.prefix.clone(),
            tail: trace.tail.iter().cloned().collect(),
            scheduler: self.scheduler_snapshot(),
        })
    }

    pub(crate) fn trace_svc_entry(&self, pc: Option<u32>, number: u32) -> Option<SvcEntry> {
        self.diagnostic_trace.as_ref()?;
        Some(SvcEntry {
            cycle: self.cpu.cycles,
            thread: self.kernel.current_thread,
            pc,
            number,
            args: self.cpu.regs[..6]
                .try_into()
                .expect("six argument registers"),
        })
    }

    pub(crate) fn trace_svc_exit(&mut self, entry: Option<SvcEntry>) {
        let Some(entry) = entry else { return };
        let thread = entry
            .thread
            .and_then(|id| self.kernel.threads.get(id as usize));
        let outcome = if self.exited {
            "process_exited"
        } else if self.broke {
            "faulted"
        } else if thread.is_some_and(|thread| thread.status == ThreadStatus::Dead) {
            "thread_exited"
        } else if thread.is_some_and(|thread| thread.status.is_blocked()) {
            "blocked"
        } else {
            "returned"
        };
        let returns = (outcome == "returned").then(|| {
            self.cpu.regs[..4]
                .try_into()
                .expect("four return registers")
        });
        let wakeup_at = thread.and_then(|thread| thread.wakeup_at);
        let trace = self.diagnostic_trace.as_mut().expect("enabled trace entry");
        if let Some(count) = trace.svc_counts.get_mut(entry.number as usize) {
            *count = count.saturating_add(1);
        } else {
            trace.other_svc_calls = trace.other_svc_calls.saturating_add(1);
        }
        if let Some(thread) = thread {
            trace.remove_pending(thread.id);
            if outcome == "blocked" {
                trace.insert_pending(PendingCall {
                    thread: thread.id,
                    guest_id: thread.guest_id,
                    number: entry.number,
                    pc: entry.pc,
                });
            }
        }
        trace.record(
            self.cpu.cycles,
            TraceEventKind::Svc {
                entry_cycle: entry.cycle,
                thread: entry.thread,
                pc: entry.pc,
                number: entry.number,
                args: entry.args,
                returns,
                outcome,
                wakeup_at,
            },
        );
    }

    // CodexAstraUlt: Observe dispatch selection only when it changes, then
    // correlate a blocked call when its same thread incarnation actually runs
    // again, after deferred result registers have been applied. SleepThread has
    // no stored WaitResult; its observed resume is reported without inventing one.
    pub(crate) fn trace_schedule(
        &mut self,
        previous: Option<ThreadId>,
        wait_result: Option<WaitResult>,
    ) {
        let Some(trace) = self.diagnostic_trace.as_mut() else {
            return;
        };
        let current = self.kernel.current_thread;
        if previous != current {
            trace.record(
                self.cpu.cycles,
                TraceEventKind::Schedule {
                    previous_thread: previous,
                    next_thread: current,
                },
            );
        }
        let Some(id) = current else { return };
        let Some(thread) = self.kernel.threads.get(id as usize) else {
            return;
        };
        if thread.status != ThreadStatus::Running {
            return;
        }
        let Some(call) = trace.remove_pending(id) else {
            return;
        };
        if call.guest_id != thread.guest_id {
            return;
        }
        let (wait_result, signaled_index) = match wait_result {
            Some(WaitResult::Signaled(index)) => ("signaled", Some(index)),
            Some(WaitResult::TimedOut) => ("timed_out", None),
            None => ("not_recorded", None),
        };
        trace.record(
            self.cpu.cycles,
            TraceEventKind::WaitResume {
                thread: id,
                guest_id: thread.guest_id,
                number: call.number,
                svc_pc: call.pc,
                return_pc: self.cpu.regs[15],
                returns: self.cpu.regs[..4]
                    .try_into()
                    .expect("four return registers"),
                wait_result,
                signaled_index,
            },
        );
    }

    fn scheduler_snapshot(&self) -> SchedulerSnapshot {
        let current = self.kernel.current_thread;
        let is_current = |thread: &&Thread| Some(thread.id) == current;
        let threads =
            self.kernel
                .threads
                .iter()
                .filter(is_current)
                .chain(self.kernel.threads.iter().filter(|thread| {
                    Some(thread.id) != current && thread.status != ThreadStatus::Dead
                }))
                .chain(self.kernel.threads.iter().filter(|thread| {
                    Some(thread.id) != current && thread.status == ThreadStatus::Dead
                }))
                .take(THREAD_CAPACITY)
                .map(|thread| self.thread_snapshot(thread))
                .collect::<Vec<_>>();
        SchedulerSnapshot {
            cycle: self.cpu.cycles,
            current_thread: current,
            live_pc: self.cpu.regs[15],
            reschedule_pending: self.kernel.reschedule_pending,
            all_blocked: self.kernel.all_blocked,
            next_kernel_event: self.kernel.next_event(),
            threads_total: self.kernel.threads.len(),
            threads_truncated: self.kernel.threads.len().saturating_sub(threads.len()),
            threads,
        }
    }

    fn thread_snapshot(&self, thread: &Thread) -> ThreadSnapshot {
        let wait_objects = thread
            .wait_objects
            .iter()
            .take(WAIT_OBJECT_CAPACITY)
            .map(|&object| self.wait_object_snapshot(object, thread.id))
            .collect::<Vec<_>>();
        ThreadSnapshot {
            id: thread.id,
            guest_id: thread.guest_id,
            status: match thread.status {
                ThreadStatus::Running => "running",
                ThreadStatus::Ready => "ready",
                ThreadStatus::Sleeping => "sleeping",
                ThreadStatus::WaitSync => "wait_sync",
                ThreadStatus::WaitArbiter => "wait_arbiter",
                ThreadStatus::Dormant => "dormant",
                ThreadStatus::Dead => "dead",
            },
            pc: if Some(thread.id) == self.kernel.current_thread {
                self.cpu.regs[15]
            } else {
                thread.context.regs[15]
            },
            priority: thread.priority,
            wakeup_at: thread.wakeup_at,
            wait_all: thread.wait_all,
            wait_address: thread.wait_address,
            wait_syscall: thread.wait_syscall.map(|call| match call {
                WaitSyscall::WaitSynchronization1 => 0x24,
                WaitSyscall::WaitSynchronizationN => 0x25,
                WaitSyscall::ArbitrateAddress => 0x22,
                WaitSyscall::SleepThread => 0x0a,
            }),
            wait_objects_total: thread.wait_objects.len(),
            wait_objects_truncated: thread.wait_objects.len().saturating_sub(wait_objects.len()),
            wait_objects,
        }
    }

    fn wait_object_snapshot(&self, id: ObjectId, waiter: ThreadId) -> WaitObjectSnapshot {
        let object = self.kernel.objects.get(id);
        let (owner, count, deadline) = match object {
            Some(KObject::Mutex(mutex)) => (mutex.owner, Some(i64::from(mutex.lock_count)), None),
            Some(KObject::Semaphore(semaphore)) => (None, Some(i64::from(semaphore.count)), None),
            Some(KObject::Timer(timer)) => (None, None, timer.fire_at),
            _ => (None, None, None),
        };
        WaitObjectSnapshot {
            id: id.0,
            kind: object.map_or("missing", KObject::type_name),
            signaled: self.kernel.is_signaled(id, waiter),
            owner,
            count,
            deadline,
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::{
        memory::{MemoryRegion, MemoryState, Permission},
        Config, StepOutcome,
    };
    use zakuro_cpu::Bus;

    // CodexAstraUlt: These original ARM programs exercise actual CPU/SVC and
    // scheduler paths; no private game bytes or assumed title addresses occur.
    fn guest(words: &[u32]) -> System {
        let mut system = System::new(Config {
            skip_idle_loops: false,
            strict_diagnostics: true,
            clock: Some(0),
            ..Config::default()
        });
        let block = system
            .memory
            .phys
            .allocate(MemoryRegion::Application, 0x1000)
            .unwrap();
        system.memory.map(
            0x0010_0000,
            block.addr,
            0x1000,
            Permission::RW | Permission::EXECUTE,
            MemoryState::Code,
        );
        for (index, word) in words.iter().enumerate() {
            system.memory.write32(0x0010_0000 + index as u32 * 4, *word);
        }
        let thread = system.kernel.create_thread(
            "private-name-not-in-trace",
            0x0010_0000,
            0x0010_0f00,
            0,
            0x30,
            0,
        );
        system.map_tls_page(thread);
        system.kernel.schedule(&mut system.cpu, 0);
        system
    }

    fn events(snapshot: &DiagnosticTraceSnapshot) -> impl Iterator<Item = &TraceEvent> {
        snapshot.prefix.iter().chain(&snapshot.tail)
    }

    fn run_to_exit(system: &mut System) {
        for _ in 0..1000 {
            if system.step(Some(system.cpu.cycles + 4096)) == StepOutcome::Exited {
                return;
            }
        }
        panic!("original bounded guest did not exit");
    }

    #[test]
    fn trace_sleep_resume_preserves_execution_and_actual_return_registers() {
        // mov r0,#1000; mov r1,#0; svc SleepThread; svc ExitProcess.
        let words = [0xe3a0_0ffa, 0xe3a0_1000, 0xef00_000a, 0xef00_0003];
        let mut plain = guest(&words);
        assert!(plain.diagnostic_trace_snapshot().is_none());
        run_to_exit(&mut plain);
        let expected = (
            plain.cpu.cycles,
            plain.interpreted_instructions,
            plain.cpu.regs,
        );
        drop(plain);
        let mut traced = guest(&words);
        traced.enable_diagnostic_trace();
        run_to_exit(&mut traced);
        assert_eq!(
            (
                traced.cpu.cycles,
                traced.interpreted_instructions,
                traced.cpu.regs
            ),
            expected
        );
        let snapshot = traced.diagnostic_trace_snapshot().unwrap();
        assert!(events(&snapshot).any(|event| matches!(&event.detail, TraceEventKind::Svc {
            number: 0x0a, pc: Some(0x0010_0008), args, returns: None, outcome: "blocked", wakeup_at: Some(_), ..
        } if args[0] == 1000 && args[1] == 0)));
        assert!(events(&snapshot).any(
            |event| matches!(&event.detail, TraceEventKind::WaitResume {
            number: 0x0a, svc_pc: Some(0x0010_0008), return_pc: 0x0010_000c,
            returns, wait_result: "not_recorded", ..
        } if returns[0] == 0)
        ));
    }

    #[test]
    fn trace_wait_timeout_is_deferred_until_the_correct_thread_resumes() {
        let mut system = guest(&[0xef00_0024, 0xef00_0003]);
        let (_, handle) = system.kernel.create_event(
            crate::kernel::sync::ResetType::OneShot,
            "private-event-name",
        );
        system.cpu.regs[0] = handle;
        system.cpu.regs[2] = 1000;
        system.cpu.regs[3] = 0;
        system.enable_diagnostic_trace();
        system.step(Some(4096));
        let blocked = system.diagnostic_trace_snapshot().unwrap();
        let thread = &blocked.scheduler.threads[0];
        assert_eq!(thread.status, "wait_sync");
        assert_eq!(thread.wait_syscall, Some(0x24));
        assert_eq!(thread.wait_objects[0].kind, "Event");
        assert!(!thread.wait_objects[0].signaled);
        assert!(thread.wakeup_at.is_some());
        assert!(events(&blocked)
            .all(|event| !matches!(event.detail, TraceEventKind::WaitResume { .. })));
        run_to_exit(&mut system);
        let snapshot = system.diagnostic_trace_snapshot().unwrap();
        assert!(events(&snapshot).any(
            |event| matches!(&event.detail, TraceEventKind::WaitResume {
            number: 0x24, svc_pc: Some(0x0010_0000), wait_result: "timed_out", returns,
            signaled_index: None, ..
        } if returns[0] == zakuro_common::result::errors::TIMEOUT.0)
        ));
    }

    #[test]
    fn trace_immediate_return_has_exact_pc_and_value_registers_not_a_fake_result_code() {
        let mut system = guest(&[0xef00_0028, 0xef00_0003]);
        system.enable_diagnostic_trace();
        run_to_exit(&mut system);
        let snapshot = system.diagnostic_trace_snapshot().unwrap();
        assert!(
            events(&snapshot).any(|event| matches!(&event.detail, TraceEventKind::Svc {
            number: 0x28, pc: Some(0x0010_0000), outcome: "returned", returns: Some(registers), ..
        } if registers[0] != 0))
        );
        assert_eq!(
            snapshot
                .svc_counts
                .iter()
                .find(|entry| entry.number == 0x28)
                .unwrap()
                .count,
            1
        );
    }

    // CodexAstraUlt: A diagnostic snapshot must not consume a one-shot event;
    // only the real scheduler may acquire it and return success to the waiter.
    #[test]
    fn trace_signaled_wait_snapshot_is_read_only_and_resume_has_real_success() {
        let mut system = guest(&[0xef00_0024, 0xef00_0003]);
        let (object, handle) = system.kernel.create_event(
            crate::kernel::sync::ResetType::OneShot,
            "private-event-name",
        );
        system.cpu.regs[0] = handle;
        system.cpu.regs[2] = u32::MAX;
        system.cpu.regs[3] = u32::MAX;
        system.enable_diagnostic_trace();
        system.step(Some(4096));
        system.kernel.signal_event(object);
        for _ in 0..2 {
            let snapshot = system.diagnostic_trace_snapshot().unwrap();
            assert!(snapshot.scheduler.threads[0].wait_objects[0].signaled);
            assert_eq!(snapshot.scheduler.threads[0].status, "wait_sync");
        }
        run_to_exit(&mut system);
        let snapshot = system.diagnostic_trace_snapshot().unwrap();
        assert!(events(&snapshot).any(
            |event| matches!(&event.detail, TraceEventKind::WaitResume {
            number: 0x24, svc_pc: Some(0x0010_0000), wait_result: "signaled", returns,
            signaled_index: Some(0), ..
        } if returns[0] == 0)
        ));
        assert!(
            matches!(system.kernel.objects.get(object), Some(KObject::Event(event)) if !event.signaled)
        );
    }

    // CodexAstraUlt: Advancing an idle scheduler is not progress or a new
    // transition; a trace must not retain one event for every empty dispatch.
    #[test]
    fn trace_empty_scheduler_does_not_flood_events() {
        let mut system = guest(&[0xef00_0009]);
        system.enable_diagnostic_trace();
        system.step(Some(4096));
        system.step(Some(4096));
        let events_before = system.diagnostic_trace_snapshot().unwrap().events_seen;
        for _ in 0..100 {
            system.step(Some(system.cpu.cycles + 4096));
        }
        assert_eq!(
            system.diagnostic_trace_snapshot().unwrap().events_seen,
            events_before
        );
    }

    #[test]
    fn trace_retention_preserves_prefix_and_recent_tail_with_exact_omission_count() {
        let mut trace = TraceState::new();
        let total = PREFIX_CAPACITY + TAIL_CAPACITY + 17;
        for cycle in 0..total {
            trace.record(
                cycle as u64,
                TraceEventKind::Schedule {
                    previous_thread: Some(0),
                    next_thread: Some(1),
                },
            );
        }
        assert_eq!(trace.prefix.len(), PREFIX_CAPACITY);
        assert_eq!(trace.tail.len(), TAIL_CAPACITY);
        assert_eq!(trace.prefix.first().unwrap().sequence, 1);
        assert_eq!(
            trace.prefix.last().unwrap().sequence,
            PREFIX_CAPACITY as u64
        );
        assert_eq!(
            trace.tail.front().unwrap().sequence,
            (PREFIX_CAPACITY + 18) as u64
        );
        assert_eq!(trace.tail.back().unwrap().sequence, total as u64);
        assert_eq!(
            trace.events_seen - (trace.prefix.len() + trace.tail.len()) as u64,
            17
        );
    }

    #[test]
    fn trace_pending_and_snapshot_admission_are_bounded_and_current_thread_is_retained() {
        let mut trace = TraceState::new();
        for thread in 0..PENDING_CAPACITY as u32 + 1 {
            trace.insert_pending(PendingCall {
                thread,
                guest_id: thread,
                number: 0x0a,
                pc: Some(0x100000),
            });
        }
        assert_eq!(trace.pending.iter().flatten().count(), PENDING_CAPACITY);
        assert_eq!(trace.pending_dropped, 1);
        let mut system = guest(&[0xeaff_fffe]);
        for _ in 0..THREAD_CAPACITY + 5 {
            system.kernel.create_thread(
                "omitted-private-thread-name",
                0x100000,
                0x100f00,
                0,
                0x30,
                0,
            );
        }
        let current = system.kernel.threads.last().unwrap().id;
        system.kernel.current_thread = Some(current);
        system.kernel.thread_mut(current).wait_objects =
            (0..WAIT_OBJECT_CAPACITY as u32 + 3).map(ObjectId).collect();
        system.enable_diagnostic_trace();
        let snapshot = system.diagnostic_trace_snapshot().unwrap();
        assert_eq!(snapshot.scheduler.threads.len(), THREAD_CAPACITY);
        assert_eq!(snapshot.scheduler.threads_truncated, 6);
        assert_eq!(snapshot.scheduler.threads[0].id, current);
        assert_eq!(
            snapshot.scheduler.threads[0].wait_objects.len(),
            WAIT_OBJECT_CAPACITY
        );
        assert_eq!(snapshot.scheduler.threads[0].wait_objects_truncated, 3);
    }
}
