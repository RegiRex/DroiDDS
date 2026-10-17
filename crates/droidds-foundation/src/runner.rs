//! CodexAstraUlt: Minimal single-threaded ABI host with strict checkpoint
//! comparison and observable native/fallback execution. This is not a 3DS OS.

use crate::fixtures::{Fixture, CHECKPOINT};
use crate::memory::Memory;
use recomp_abi::{Code, Context, Host, Library};
use zakuro_cpu::{Bus, Cpu, Exit};

const INSTRUCTION_LIMIT: u64 = 256;
const SLICE: i32 = 32;

// CodexAstraUlt: Capture every exposed user register/flag, VFP storage and the
// entire 64 KiB fixture image. Integer and memory comparison has no NaN exception.
#[derive(Clone, Debug, PartialEq, Eq)]
pub struct Snapshot {
    pub registers: [u32; 16],
    pub cpsr: u32,
    pub vfp: [u32; 32],
    pub fpscr: u32,
    pub fpexc: u32,
    pub exclusive: Option<u32>,
    pub tls: u32,
    pub memory: Vec<u8>,
    pub faults: u64,
}

impl Snapshot {
    pub fn capture(cpu: &Cpu, memory: &Memory) -> Self {
        Self {
            registers: cpu.regs,
            cpsr: cpu.cpsr.to_bits(),
            vfp: cpu.vfp.regs,
            fpscr: cpu.vfp.fpscr,
            fpexc: cpu.vfp.fpexc,
            exclusive: cpu.exclusive_addr,
            tls: cpu.cp15.thread_id_ro,
            memory: memory.bytes.clone(),
            faults: memory.faults,
        }
    }
}

#[derive(Debug, PartialEq, Eq)]
pub enum Stop {
    Checkpoint(u32),
    InstructionLimit,
    Unexpected(String),
}

// CodexAstraUlt: Native calls alone do not prove execution: charged native work
// must be nonzero and pure fixtures must make zero interpreter steps/callbacks.
#[derive(Default, Debug)]
pub struct Counts {
    pub native_calls: u64,
    pub native_lookup_hits: u64,
    pub native_budget_charged: u64,
    pub fallback_steps: u64,
    pub instruction_callbacks: u64,
    pub interpreter_steps: u64,
}

pub struct ResultState {
    pub stop: Stop,
    pub state: Snapshot,
    pub counts: Counts,
}

fn stopped(exit: Exit) -> Stop {
    match exit {
        Exit::Supervisor(number) => Stop::Checkpoint(number),
        other => Stop::Unexpected(format!("{other:?}")),
    }
}

// CodexAstraUlt: The pure reference engine has the same explicit instruction
// ceiling as AOT; a timeout is an inconclusive test outcome, never equality.
pub fn interpreted(fixture: &Fixture) -> ResultState {
    let mut cpu = fixture.cpu.clone();
    let mut memory = fixture.memory.clone();
    let mut counts = Counts::default();
    let mut stop = Stop::InstructionLimit;
    for _ in 0..INSTRUCTION_LIMIT {
        counts.interpreter_steps += 1;
        if let Some(exit) = cpu.step(&mut memory) {
            stop = stopped(exit);
            break;
        }
    }
    ResultState {
        stop,
        state: Snapshot::capture(&cpu, &memory),
        counts,
    }
}

// CodexAstraUlt: Run owns all callback state. It remains boxed and the Library
// remains loaded throughout every call into the generated C.
struct Run {
    cpu: Cpu,
    memory: Memory,
    library: *const Library,
    pending: Option<Exit>,
    counts: Counts,
}

// CodexAstraUlt: SAFETY: Only Context instances created by native() use HOST;
// user points at its live, exclusive Run and callbacks execute synchronously.
unsafe fn run_of<'a>(context: *mut Context) -> &'a mut Run {
    unsafe { &mut *((*context).user.cast::<Run>()) }
}

// CodexAstraUlt: Callback functions preserve the upstream ABI exactly. Checked
// bus accesses record faults instead of unwinding through the C boundary.
unsafe extern "C" fn read8(context: *mut Context, address: u32) -> u8 {
    unsafe { run_of(context).memory.read8(address) }
}

unsafe extern "C" fn read16(context: *mut Context, address: u32) -> u16 {
    unsafe { run_of(context).memory.read16(address) }
}

unsafe extern "C" fn read32(context: *mut Context, address: u32) -> u32 {
    unsafe { run_of(context).memory.read32(address) }
}

unsafe extern "C" fn write8(context: *mut Context, address: u32, value: u8) {
    unsafe { run_of(context).memory.write8(address, value) }
}

unsafe extern "C" fn write16(context: *mut Context, address: u32, value: u16) {
    unsafe { run_of(context).memory.write16(address, value) }
}

unsafe extern "C" fn write32(context: *mut Context, address: u32, value: u32) {
    unsafe { run_of(context).memory.write32(address, value) }
}

// CodexAstraUlt: The ABI instruction callback uses the selected interpreter;
// branch/exception exits return to the dispatcher without skipping guest work.
unsafe extern "C" fn interpret(context: *mut Context, address: u32, _opcode: u32) {
    unsafe {
        let run = run_of(context);
        let context = &mut *context;
        load(context, &mut run.cpu);
        let instruction_size = if context.thumb != 0 { 2 } else { 4 };
        run.cpu.regs[15] = address;
        let exit = run.cpu.step(&mut run.memory);
        store(&run.cpu, context);
        run.counts.instruction_callbacks += 1;
        run.counts.fallback_steps += 1;
        if exit.is_some() || context.r[15] != address.wrapping_add(instruction_size) {
            run.pending = exit;
            context.exit = recomp_abi::EXIT_UNWIND;
        }
    }
}

unsafe extern "C" fn lookup(context: *mut Context, address: u32) -> Option<Code> {
    unsafe {
        let run = run_of(context);
        let code = (*run.library).lookup(address);
        if code.is_some() {
            run.counts.native_lookup_hits += 1;
        }
        code
    }
}

static HOST: Host = Host {
    read8,
    read16,
    read32,
    write8,
    write16,
    write32,
    interpret,
    lookup,
};

// CodexAstraUlt: Copy only the ABI-owned CPU fields at dispatch boundaries;
// VFP/FPSCR already share stable storage through Context's pointers.
fn load(context: &Context, cpu: &mut Cpu) {
    cpu.regs = context.r;
    cpu.cpsr.n = context.n != 0;
    cpu.cpsr.z = context.z != 0;
    cpu.cpsr.c = context.c != 0;
    cpu.cpsr.v = context.v != 0;
    cpu.cpsr.q = context.q != 0;
    cpu.cpsr.ge = context.ge;
    cpu.cpsr.thumb = context.thumb != 0;
    cpu.exclusive_addr = (context.exclusive != 0).then_some(context.exclusive_address);
    cpu.cp15.thread_id_ro = context.tls;
}

fn store(cpu: &Cpu, context: &mut Context) {
    context.r = cpu.regs;
    context.n = cpu.cpsr.n as u8;
    context.z = cpu.cpsr.z as u8;
    context.c = cpu.cpsr.c as u8;
    context.v = cpu.cpsr.v as u8;
    context.q = cpu.cpsr.q as u8;
    context.ge = cpu.cpsr.ge;
    context.thumb = cpu.cpsr.thumb as u8;
    context.exclusive = cpu.exclusive_addr.is_some() as u8;
    context.exclusive_address = cpu.exclusive_addr.unwrap_or(0);
    context.tls = cpu.cp15.thread_id_ro;
}

// CodexAstraUlt: Basic-block budgets are not wall-clock timing. An outer process
// watchdog bounds buggy generated native code that fails to honor its budget.
pub fn native(fixture: &Fixture, library: &Library) -> ResultState {
    let mut run = Box::new(Run {
        cpu: fixture.cpu.clone(),
        memory: fixture.memory.clone(),
        library,
        pending: None,
        counts: Counts::default(),
    });
    let pages = vec![std::ptr::null_mut::<u8>(); 1 << 20];
    let mut context = Context {
        r: [0; 16],
        n: 0,
        z: 0,
        c: 0,
        v: 0,
        q: 0,
        thumb: 0,
        ge: 0,
        exclusive: 0,
        budget: 0,
        exit: recomp_abi::EXIT_NONE,
        svc: 0,
        depth: 0,
        exclusive_address: 0,
        tls: 0,
        read_pages: pages.as_ptr(),
        write_pages: pages.as_ptr(),
        vfp: run.cpu.vfp.regs.as_mut_ptr(),
        fpscr: &mut run.cpu.vfp.fpscr,
        host: &HOST,
        user: (&mut *run as *mut Run).cast(),
    };
    store(&run.cpu, &mut context);
    let mut remaining = INSTRUCTION_LIMIT;
    let mut dispatches = 0;
    let stop = loop {
        if remaining == 0 || dispatches >= INSTRUCTION_LIMIT * 2 {
            break Stop::InstructionLimit;
        }
        dispatches += 1;
        if let Some(code) = library.lookup(context.r[15] | u32::from(context.thumb)) {
            let budget = SLICE.min(remaining as i32);
            context.budget = budget;
            context.exit = recomp_abi::EXIT_NONE;
            context.depth = 0;
            run.counts.native_calls += 1;
            // CodexAstraUlt: SAFETY: The library was generated by this fixture
            // sources; Context, HOST, page tables and boxed Run are all live.
            unsafe { code(&mut context) };
            let spent = i64::from(budget) - i64::from(context.budget);
            if !(0..=i64::from(budget)).contains(&spent) {
                break Stop::Unexpected(format!("invalid native budget delta {spent}"));
            }
            remaining -= spent as u64;
            run.counts.native_budget_charged += spent as u64;
            if let Some(exit) = run.pending.take() {
                break stopped(exit);
            }
            match context.exit {
                recomp_abi::EXIT_SVC => break Stop::Checkpoint(context.svc),
                recomp_abi::EXIT_BUDGET if spent == 0 => {}
                recomp_abi::EXIT_NONE | recomp_abi::EXIT_UNWIND | recomp_abi::EXIT_BUDGET => {
                    continue
                }
                other => break Stop::Unexpected(format!("unknown ABI exit {other}")),
            }
        }
        // CodexAstraUlt: No native entry (or a block too large for its slice)
        // executes one real interpreter instruction, then retries dispatch.
        load(&context, &mut run.cpu);
        let Run { cpu, memory, .. } = &mut *run;
        let exit = cpu.step(memory);
        store(&run.cpu, &mut context);
        run.counts.fallback_steps += 1;
        remaining -= 1;
        if let Some(exit) = exit {
            break stopped(exit);
        }
    };
    load(&context, &mut run.cpu);
    ResultState {
        stop,
        state: Snapshot::capture(&run.cpu, &run.memory),
        counts: run.counts,
    }
}

// CodexAstraUlt: Return a concise exact mismatch instead of dumping private
// memory. This fixture is public, but future inputs should retain that boundary.
pub fn compare(expected: &Snapshot, actual: &Snapshot) -> Result<(), String> {
    for (index, (&want, &got)) in expected.registers.iter().zip(&actual.registers).enumerate() {
        if want != got {
            return Err(format!("r{index}: expected {want:08x}, got {got:08x}"));
        }
    }
    if expected.cpsr != actual.cpsr {
        return Err(format!(
            "CPSR: expected {:08x}, got {:08x}",
            expected.cpsr, actual.cpsr
        ));
    }
    if expected.vfp != actual.vfp
        || expected.fpscr != actual.fpscr
        || expected.fpexc != actual.fpexc
    {
        return Err("VFP register bits or control storage differ".to_owned());
    }
    if expected.exclusive != actual.exclusive || expected.tls != actual.tls {
        return Err("exclusive monitor or TLS differs".to_owned());
    }
    if expected.memory.len() != actual.memory.len() {
        return Err("memory image lengths differ".to_owned());
    }
    if let Some(address) = expected
        .memory
        .iter()
        .zip(&actual.memory)
        .position(|(a, b)| a != b)
    {
        return Err(format!("memory byte {address:08x} differs"));
    }
    if expected.faults != actual.faults {
        return Err("memory fault counts differ".to_owned());
    }
    Ok(())
}

// CodexAstraUlt: Completion and zero-fault gates precede comparison; matching
// partial states or two identical faults cannot turn a bad run into a pass.
pub fn validate(
    fixture: &Fixture,
    reference: &ResultState,
    candidate: &ResultState,
) -> Result<(), String> {
    for (name, result) in [("interpreter", reference), ("native", candidate)] {
        if result.stop != Stop::Checkpoint(CHECKPOINT) {
            return Err(format!("{name} did not complete: {:?}", result.stop));
        }
        if result.state.faults != 0 {
            return Err(format!(
                "{name} encountered {} memory faults",
                result.state.faults
            ));
        }
        compare(&fixture.expected, &result.state).map_err(|error| format!("{name}: {error}"))?;
    }
    compare(&reference.state, &candidate.state)?;
    if candidate.counts.native_calls == 0 || candidate.counts.native_budget_charged == 0 {
        return Err("native execution was not demonstrated".to_owned());
    }
    // CodexAstraUlt: The Android port retains the exact dispatch route proven on
    // Linux, including the real Thumb lookup and three-step missing-entry path.
    if candidate.counts.native_calls != 1
        || candidate.counts.native_budget_charged != fixture.native_budget
        || candidate.counts.native_lookup_hits != fixture.native_lookups
        || candidate.counts.fallback_steps != fixture.fallback_steps
        || candidate.counts.instruction_callbacks != 0
    {
        return Err(format!(
            "unexpected native/fallback route counts: {:?}",
            candidate.counts
        ));
    }
    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;

    // CodexAstraUlt: These adversarial oracle checks target the inherited
    // verifier's integer/memory NaN masking and limit handling, not its internals.
    #[test]
    fn rejects_nan_shaped_integer_register_difference() {
        let expected = crate::fixtures::fixtures().remove(0).expected;
        let mut actual = expected.clone();
        actual.registers[6] = 0x7fc0_0002;
        assert!(compare(&expected, &actual).unwrap_err().starts_with("r6:"));
    }

    #[test]
    fn rejects_nan_shaped_integer_memory_difference() {
        let expected = crate::fixtures::fixtures().remove(0).expected;
        let mut actual = expected.clone();
        actual.memory[crate::memory::DATA as usize + 4] = 2;
        assert!(compare(&expected, &actual)
            .unwrap_err()
            .starts_with("memory byte"));
    }

    #[test]
    fn rejects_identical_unfinished_states() {
        let fixture = crate::fixtures::endless();
        let reference = interpreted(&fixture);
        assert_eq!(reference.stop, Stop::InstructionLimit);
        assert!(validate(&fixture, &reference, &reference)
            .unwrap_err()
            .contains("did not complete"));
    }

    #[test]
    fn rejects_matching_faults_even_at_checkpoint() {
        let fixture = crate::fixtures::fixtures().remove(0);
        let mut reference = interpreted(&fixture);
        reference.state.faults = 1;
        assert!(validate(&fixture, &reference, &reference)
            .unwrap_err()
            .contains("memory faults"));
    }
}
