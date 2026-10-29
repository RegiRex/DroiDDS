//! running code that 3dsrecomp turned into a library ahead of time. the
//! library's functions work on a context holding the registers and reach
//! memory through the same page tables the interpreter uses, calling back
//! here for anything else. whatever the library has no code for stays with
//! the interpreter.

use std::cell::Cell;
use std::ffi::c_void;
use std::path::Path;

use recomp_abi::{Code, Context, Host, EXIT_BUDGET, EXIT_SVC, EXIT_UNWIND};
use zakuro_cpu::{Bus, Cpu, Exit};

use crate::memory::Memory;

pub use recomp_abi::Linked;

/// the library 3dsrecomp build installed for a title, if there is one.
pub fn installed(program_id: u64) -> Option<std::path::PathBuf> {
    recomp_abi::installed(program_id)
}

/// recompiled code, and how much of its work it handed back.
pub struct Library {
    code: recomp_abi::Library,
    /// instructions the code handed to the interpreter one at a time.
    fallbacks: Cell<u64>,
    /// the code found for addresses lately, each in a slot its address
    /// picks. a jump through a register looks its target up, which is a
    /// search through every function otherwise.
    found: Box<[Found]>,
    // CodexAstraUlt: An isolated immutable-base diagnostic never places CRO
    // native units and requires an active physical code fence before execution.
    executable_only: bool,
}

/// a slot of Library::found, an address and the code found for it.
type Found = Cell<(u32, Option<Code>)>;

/// slots of Library::found, a power of two.
const FOUND: usize = 65536;

/// the slot of Library::found an address goes in, the top bits of the
/// address times the golden ratio. ARM addresses step by four and Thumb ones
/// by two with bit 0 set, and taking low bits would leave half the slots to
/// one of them.
fn slot(address: u32) -> usize {
    (address.wrapping_mul(0x9E37_79B1) >> (32 - FOUND.trailing_zeros())) as usize
}

/// why a run of recompiled code ended.
pub enum Stop {
    /// an svc, the cpu is already past it.
    Svc(u32),
    /// the interpreter stopped on an instruction the code handed it.
    Exit(Exit),
    /// the budget ran out, or execution left for code the library does not
    /// have.
    Left,
    // CodexAstraUlt: The opted-in code fence is absent or its mapping changed;
    // no guest instruction was executed by this declined native dispatch.
    CodeFence,
}

/// what the callbacks reach through the context.
struct Machine<'a> {
    cpu: &'a mut Cpu,
    memory: &'a mut Memory,
    library: &'a Library,
    /// what the interpreter stopped with inside a callback.
    pending: Option<Exit>,
}

/// # Safety
///
/// ctx has to be a context run set up, whose user field points at a live
/// Machine.
unsafe fn machine<'a>(ctx: *mut Context) -> &'a mut Machine<'a> {
    unsafe { &mut *((*ctx).user as *mut Machine) }
}

unsafe extern "C" fn read8(ctx: *mut Context, address: u32) -> u8 {
    unsafe { machine(ctx).memory.read8(address) }
}

unsafe extern "C" fn read16(ctx: *mut Context, address: u32) -> u16 {
    unsafe { machine(ctx).memory.read16(address) }
}

unsafe extern "C" fn read32(ctx: *mut Context, address: u32) -> u32 {
    unsafe { machine(ctx).memory.read32(address) }
}

unsafe extern "C" fn write8(ctx: *mut Context, address: u32, value: u8) {
    unsafe { machine(ctx).memory.write8(address, value) }
}

unsafe extern "C" fn write16(ctx: *mut Context, address: u32, value: u16) {
    unsafe { machine(ctx).memory.write16(address, value) }
}

unsafe extern "C" fn write32(ctx: *mut Context, address: u32, value: u32) {
    unsafe { machine(ctx).memory.write32(address, value) }
}

/// runs one instruction the code left to the interpreter.
unsafe extern "C" fn interpret(ctx: *mut Context, address: u32, _opcode: u32) {
    unsafe {
        let machine = machine(ctx);
        machine.library.fallbacks.set(machine.library.fallbacks.get() + 1);
        let ctx = &mut *ctx;
        load(ctx, machine.cpu);
        machine.cpu.regs[15] = address;
        let exit = machine.cpu.step(machine.memory);
        store(machine.cpu, ctx);
        let step = if ctx.thumb != 0 { 2 } else { 4 };
        if exit.is_some() || ctx.r[15] != address.wrapping_add(step) {
            machine.pending = exit;
            ctx.exit = EXIT_UNWIND;
        }
    }
}

unsafe extern "C" fn lookup(ctx: *mut Context, address: u32) -> Option<Code> {
    unsafe { machine(ctx).library.lookup(address) }
}

static HOST: Host = Host { read8, read16, read32, write8, write16, write32, interpret, lookup };

fn load(ctx: &Context, cpu: &mut Cpu) {
    cpu.regs = ctx.r;
    cpu.cpsr.n = ctx.n != 0;
    cpu.cpsr.z = ctx.z != 0;
    cpu.cpsr.c = ctx.c != 0;
    cpu.cpsr.v = ctx.v != 0;
    cpu.cpsr.q = ctx.q != 0;
    cpu.cpsr.ge = ctx.ge;
    cpu.cpsr.thumb = ctx.thumb != 0;
    cpu.exclusive_addr = (ctx.exclusive != 0).then_some(ctx.exclusive_address);
}

fn store(cpu: &Cpu, ctx: &mut Context) {
    ctx.r = cpu.regs;
    ctx.n = cpu.cpsr.n as u8;
    ctx.z = cpu.cpsr.z as u8;
    ctx.c = cpu.cpsr.c as u8;
    ctx.v = cpu.cpsr.v as u8;
    ctx.q = cpu.cpsr.q as u8;
    ctx.ge = cpu.cpsr.ge;
    ctx.thumb = cpu.cpsr.thumb as u8;
    ctx.exclusive = cpu.exclusive_addr.is_some() as u8;
    ctx.exclusive_address = cpu.exclusive_addr.unwrap_or(0);
    ctx.tls = cpu.cp15.thread_id_ro;
}

impl Library {
    /// a library 3dsrecomp built.
    pub fn open(path: &Path) -> Result<Library, String> {
        recomp_abi::Library::open(path).map(Library::new)
    }

    /// the code linked into the program.
    pub fn linked(linked: &Linked) -> Result<Library, String> {
        recomp_abi::Library::linked(linked).map(Library::new)
    }

    fn new(code: recomp_abi::Library) -> Library {
        Library { code, fallbacks: Cell::new(0), found: Library::nothing_found(), executable_only: false }
    }

    /// CodexAstraUlt: Retain ABI4 generated code but keep movable CRO units in
    /// the interpreter. This is a fail-stop diagnostic, not mutable-code support.
    pub fn restrict_to_executable(&mut self) {
        for index in 0..self.code.modules().len() {
            self.code.place(index, 0);
        }
        self.found = Library::nothing_found();
        self.executable_only = true;
    }

    pub fn executable_only(&self) -> bool { self.executable_only }

    /// every slot of found empty, an address no code starts at in each.
    fn nothing_found() -> Box<[Found]> {
        (0..FOUND).map(|_| Cell::new((u32::MAX, None))).collect()
    }

    /// whether the code came from an older 3dsrecomp than the one this
    /// build has, so that recompiling the game again makes it better.
    pub fn outdated(&self) -> bool {
        self.code.generation() < recomp_abi::GENERATION
    }

    /// whether the code can tell the functions whose code changed in
    /// memory, which it can from generation 2 on.
    pub fn checks_itself(&self) -> bool {
        self.code.origins(0).is_some()
    }

    /// how many instructions the code has handed to the interpreter.
    pub fn fallbacks(&self) -> u64 {
        self.fallbacks.get()
    }

    /// how many functions and modules there is code for.
    pub fn describe(&self) -> String {
        self.code.describe()
    }

    /// the code that can run from address, bit 0 set for Thumb, in the
    /// executable or in a module that is loaded.
    fn lookup(&self, address: u32) -> Option<Code> {
        let slot = &self.found[slot(address)];
        match slot.get() {
            (seen, code) if seen == address => code,
            _ => {
                let code = self.code.lookup(address);
                slot.set((address, code));
                code
            }
        }
    }

    pub fn has_code(&self, address: u32) -> bool {
        self.lookup(address).is_some()
    }

    /// marks the executable's functions whose code in memory is not what
    /// they were recompiled from, which a mod or another version of the
    /// game does, so that the interpreter runs them. how many there are.
    pub fn check(&mut self, memory: &mut Memory) -> usize {
        let stale = self.code.check(0, 0, |address, bytes| memory.read_bytes(address, bytes));
        self.found = Library::nothing_found();
        stale
    }

    /// tells the code of the module called name where the title loaded it,
    /// zero when it unloads it, and checks the module's code once it is in
    /// memory.
    pub fn place(&mut self, name: &str, base: u32, memory: &mut Memory) {
        // CodexAstraUlt: Module load/unload still proceeds in the emulated
        // machine, but this diagnostic never exposes a CRO native entry.
        if self.executable_only { return; }
        let Some(index) = self.code.module_index(name) else { return };
        self.code.place(index, base);
        // what was found before may have moved or gone
        self.found = Library::nothing_found();
        if base == 0 {
            return;
        }
        log::info!("recompiled code for {name} runs at 0x{base:08X}");
        let stale = self.code.check(index + 1, base, |address, bytes| memory.read_bytes(address, bytes));
        if stale > 0 {
            log::warn!("{stale} functions of {name} changed since it was recompiled, they run in the interpreter");
        }
    }

    /// runs recompiled code from the cpu's pc for about budget instructions,
    /// returning how many ran and why it stopped.
    pub fn run(&self, cpu: &mut Cpu, memory: &mut Memory, budget: u64) -> (u64, Stop) {
        // CodexAstraUlt: Protect low-level callers too. A fenced run must use
        // the immutable-base policy, and mapping checks precede every dispatch.
        if self.executable_only != memory.base_code_fence_active() || memory.verify_base_code_fence().is_err() {
            return (0, Stop::CodeFence);
        }
        let cycles = cpu.cycles;
        let (read_pages, write_pages) = memory.page_tables();
        let mut ctx = Context {
            r: [0; 16],
            n: 0,
            z: 0,
            c: 0,
            v: 0,
            q: 0,
            thumb: 0,
            ge: 0,
            exclusive: 0,
            budget: budget.min(i32::MAX as u64) as i32,
            exit: 0,
            svc: 0,
            depth: 0,
            exclusive_address: 0,
            tls: 0,
            read_pages,
            write_pages,
            vfp: std::ptr::null_mut(),
            fpscr: std::ptr::null_mut(),
            host: &HOST,
            user: std::ptr::null_mut(),
        };
        store(cpu, &mut ctx);
        let mut machine = Machine { cpu, memory, library: self, pending: None };
        // the code works on the VFP registers where they are, so the
        // interpreter sees its changes without copying them around
        ctx.vfp = machine.cpu.vfp.regs.as_mut_ptr();
        ctx.fpscr = &mut machine.cpu.vfp.fpscr;
        ctx.user = &mut machine as *mut Machine as *mut c_void;

        let stop = loop {
            if ctx.budget <= 0 {
                break Stop::Left;
            }
            let Some(code) = self.lookup(ctx.r[15] | ctx.thumb as u32) else {
                break Stop::Left;
            };
            ctx.exit = 0;
            ctx.depth = 0;
            // SAFETY: the code came from the library and ctx is set up the
            // way it expects, with user pointing at machine
            unsafe { code(&mut ctx) };
            if let Some(exit) = machine.pending.take() {
                break Stop::Exit(exit);
            }
            match ctx.exit {
                EXIT_SVC => break Stop::Svc(ctx.svc),
                EXIT_BUDGET => break Stop::Left,
                _ => {}
            }
        };

        load(&ctx, machine.cpu);
        let ran = budget.saturating_sub(ctx.budget.max(0) as u64);
        // the interpreter counted the instructions it ran for the code, which
        // the budget already has
        machine.cpu.cycles = cycles + ran;
        (ran, stop)
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    // CodexAstraUlt: This original ABI fixture tests policy only; public
    // integration tests separately qualify actual generated guest execution.
    unsafe extern "C" fn fixture_entry(ctx: *mut Context) {
        // SAFETY: Library::run owns and initializes this live context.
        unsafe {
            (*ctx).r[0] = 42;
            (*ctx).r[15] += 4;
            (*ctx).budget -= 1;
            (*ctx).exit = EXIT_BUDGET;
        }
    }

    #[test]
    fn executable_restriction_removes_existing_and_future_module_entries() {
        // CodexAstraUlt: Match the published ABI record without exposing the
        // dependency's private Rust fields or modifying its source/ABI.
        #[repr(C)]
        struct ModuleFixture {
            name: *const std::ffi::c_char,
            base: *mut u32,
            size: u32,
            count: u32,
            entries: *const recomp_abi::Entry,
        }
        let base_entries = [recomp_abi::Entry { address: 0x0010_0000, code: fixture_entry }];
        let module_entries = [recomp_abi::Entry { address: 0, code: fixture_entry }];
        let mut placed = 0u32;
        let modules = [ModuleFixture { name: c"original_fixture".as_ptr(), base: &mut placed,
            size: 16, count: 1, entries: module_entries.as_ptr() }];
        // SAFETY: These original ABI records and their referenced storage remain
        // live until after Library is dropped; the code pointers use its ABI.
        let linked = unsafe { recomp_abi::Linked::new(0, recomp_abi::ABI,
            base_entries.as_ptr().cast(), 1, modules.as_ptr().cast(), 1) };
        let mut library = Library::linked(&linked).unwrap();
        let mut memory = Memory::new(false, 64 * 1024 * 1024);
        library.place("original_fixture", 0x0020_0000, &mut memory);
        assert!(library.has_code(0x0020_0000));
        assert_eq!(placed, 0x0020_0000);
        library.restrict_to_executable();
        assert!(library.executable_only());
        assert_eq!(placed, 0);
        assert!(!library.has_code(0x0020_0000));
        assert!(library.has_code(0x0010_0000));
        library.place("original_fixture", 0x0030_0000, &mut memory);
        assert_eq!(placed, 0);
        assert!(!library.has_code(0x0030_0000));
    }

    #[test]
    fn restricted_library_declines_without_a_fence_before_running_code() {
        let entries = [recomp_abi::Entry { address: 0x0010_0000, code: fixture_entry }];
        // SAFETY: The fixture's entry remains live for the library; no module
        // table exists, and a properly aligned nonnull empty pointer is supplied.
        let linked = unsafe { recomp_abi::Linked::new(0, recomp_abi::ABI,
            entries.as_ptr().cast(), 1, std::ptr::NonNull::<recomp_abi::Module>::dangling().as_ptr().cast(), 0) };
        let mut library = Library::linked(&linked).unwrap();
        let mut memory = Memory::new(false, 64 * 1024 * 1024);
        let mut cpu = Cpu::new();
        cpu.regs[15] = 0x0010_0000;
        let (ran, _) = library.run(&mut cpu, &mut memory, 2);
        assert_eq!(ran, 1);
        assert_eq!(cpu.regs[0], 42);
        cpu.regs[15] = 0x0010_0000;
        cpu.regs[0] = 9;
        library.restrict_to_executable();
        let before = cpu.cycles;
        let (ran, stop) = library.run(&mut cpu, &mut memory, 2);
        assert_eq!(ran, 0);
        assert!(matches!(stop, Stop::CodeFence));
        assert_eq!(cpu.regs[0], 9);
        assert_eq!(cpu.cycles, before);
    }

    #[test]
    fn arm_and_thumb_code_use_every_slot() {
        let arm: std::collections::BTreeSet<usize> = (0..FOUND as u32).map(|i| slot(0x0010_0000 + 4 * i)).collect();
        let thumb: std::collections::BTreeSet<usize> = (0..FOUND as u32).map(|i| slot(0x0010_0001 + 2 * i)).collect();
        assert!(arm.len() > FOUND * 3 / 4, "{} of {FOUND}", arm.len());
        assert!(thumb.len() > FOUND * 3 / 4, "{} of {FOUND}", thumb.len());
    }
}
