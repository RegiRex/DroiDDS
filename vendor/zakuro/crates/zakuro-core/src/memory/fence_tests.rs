//! CodexAstraUlt: Original memory fixtures exercise actual kernel write denial,
//! alias rebasing and fail-stop mapping checks without private game data.

use super::*;
use crate::{Config, DiagnosticFault, StepOutcome, System};

const TEXT: u32 = 0x0010_0000;
const DATA: u32 = 0x0020_0000;
const ALIAS: u32 = 0x0030_0000;
const TEXT_BYTES: u32 = 2 * PAGE_SIZE;

fn fixture() -> (Memory, u32, u32) {
    let mut memory = Memory::new(false, 64 * 1024 * 1024);
    let block = memory.phys.allocate(MemoryRegion::Application, 6 * PAGE_SIZE).unwrap();
    let text = block.addr + 2 * PAGE_SIZE;
    let data = block.addr + 4 * PAGE_SIZE;
    memory.write_physical(text, &[0x44; 16]);
    memory.write_physical(text + PAGE_SIZE, &[0x55; 16]);
    memory.write_physical(data, &[0x66; 16]);
    memory.map(TEXT, text, TEXT_BYTES, Permission::RX, MemoryState::Code);
    memory.map(DATA, data, PAGE_SIZE, Permission::RW, MemoryState::Private);
    memory.map(ALIAS, text, PAGE_SIZE, Permission::RW, MemoryState::Alias);
    (memory, text, data)
}

#[test]
fn default_backing_keeps_existing_mutable_alias_behavior() {
    let (mut memory, _, _) = fixture();
    assert!(!memory.base_code_fence_active());
    assert!(!memory.phys.fcram.is_fenced_mapping());
    assert!(memory.verify_base_code_fence().is_ok());
    memory.write8(ALIAS, 0x77);
    assert_eq!(memory.read8(TEXT), 0x77);
}

#[test]
fn install_rebases_every_table_and_preserves_unprotected_data() {
    let (mut memory, text, data) = fixture();
    let old_start = memory.phys.fcram.as_ptr() as usize;
    let tables = memory.page_tables();
    memory.install_base_code_fence(TEXT, TEXT_BYTES).unwrap();
    assert!(memory.base_code_fence_active());
    assert!(memory.phys.fcram.is_fenced_mapping());
    assert_ne!(memory.phys.fcram.as_ptr() as usize, old_start);
    assert_eq!(memory.page_tables(), tables);
    assert_eq!(memory.phys.fcram.as_ptr() as usize % 4096, 0);
    for (address, physical, writable) in [(TEXT, text, false), (TEXT + PAGE_SIZE, text + PAGE_SIZE, false), (DATA, data, true), (ALIAS, text, true)] {
        let expected = memory.phys.fcram.as_ptr() as usize + (physical - FCRAM_PADDR) as usize;
        let page = (address >> PAGE_BITS) as usize;
        assert_eq!(memory.read_table[page] as usize, expected);
        assert_eq!(memory.cpu_read_table[page] as usize, expected);
        assert_eq!(memory.write_table[page] as usize, if writable { expected } else { 0 });
        assert_eq!(memory.cpu_write_table[page] as usize, if writable { expected } else { 0 });
    }
    assert_eq!(memory.read32(TEXT), 0x4444_4444);
    assert_eq!(memory.read32(TEXT + PAGE_SIZE), 0x5555_5555);
    memory.write32(DATA, 0x1234_5678);
    assert_eq!(memory.read32(DATA), 0x1234_5678);
    // SAFETY: This actual native fast pointer names a live unprotected data page.
    unsafe { std::ptr::write_volatile(*tables.1.add((DATA >> PAGE_BITS) as usize), 0x99) };
    assert_eq!(memory.read8(DATA), 0x99);
    assert_eq!(memory.read8(TEXT), 0x44);
    assert!(memory.verify_base_code_fence().is_ok());
    assert!(memory.install_base_code_fence(TEXT, TEXT_BYTES).is_err());
}

#[test]
fn invalid_fence_admission_preserves_original_backing() {
    let (mut memory, _, _) = fixture();
    let pointer = memory.phys.fcram.as_ptr();
    for (start, bytes) in [(TEXT + 1, PAGE_SIZE), (TEXT, 0), (TEXT, PAGE_SIZE + 1),
        (TEXT, 65 * 1024 * 1024), (0xFFFF_F000, 2 * PAGE_SIZE), (DATA, PAGE_SIZE)] {
        assert!(memory.install_base_code_fence(start, bytes).is_err());
        assert_eq!(memory.phys.fcram.as_ptr(), pointer);
        assert!(!memory.base_code_fence_active());
        assert_eq!(memory.read8(TEXT), 0x44);
    }
}

#[test]
fn remap_unmap_permissions_and_gpu_guards_reject_before_execution() {
    for change in 0..4 {
        let (mut memory, text, data) = fixture();
        memory.install_base_code_fence(TEXT, TEXT_BYTES).unwrap();
        match change {
            0 => memory.map(TEXT + PAGE_SIZE, data, PAGE_SIZE, Permission::RX, MemoryState::Code),
            1 => memory.unmap(TEXT, PAGE_SIZE),
            2 => memory.map(TEXT, text, PAGE_SIZE, Permission::READ, MemoryState::Code),
            3 => memory.guard_cpu_reads(TEXT, 4),
            _ => unreachable!(),
        }
        assert_eq!(memory.verify_base_code_fence().unwrap_err(), "native_base_code_fence_mapping_changed");
    }
}

#[test]
fn unrelated_mapping_changes_keep_native_fence_valid() {
    let (mut memory, _, data) = fixture();
    memory.install_base_code_fence(TEXT, TEXT_BYTES).unwrap();
    memory.map(DATA + PAGE_SIZE, data, PAGE_SIZE, Permission::RW, MemoryState::Alias);
    memory.write8(DATA + PAGE_SIZE, 0xBB);
    assert_eq!(memory.read8(DATA), 0xBB);
    assert!(memory.verify_base_code_fence().is_ok());
    memory.unmap(DATA + PAGE_SIZE, PAGE_SIZE);
    memory.guard_cpu_writes(DATA, 4);
    assert!(memory.verify_base_code_fence().is_ok());
}

// CodexAstraUlt: GPU guards can change only their virtual pages. Physical code
// aliases remain protected by the existing host mapping; unrelated guard work
// must preserve the verified epoch while actual map/unmap still invalidates it.
#[test]
fn unrelated_guards_and_aliases_keep_the_verified_fence_epoch() {
    let (mut memory, _, data) = fixture();
    memory.install_base_code_fence(TEXT, TEXT_BYTES).unwrap();
    let epoch = memory.fence_mapping_epoch;
    for address in [DATA, ALIAS] {
        memory.guard_cpu_reads(address, 4);
        memory.guard_cpu_writes(address, 4);
        assert_eq!(memory.fence_mapping_epoch, epoch);
        assert!(memory.verify_base_code_fence().is_ok());
        assert_eq!(memory.base_code_fence.as_ref().unwrap().verified_epoch.get(), epoch);
    }
    // SAFETY: The callback never dereferences its opaque pointer; it performs
    // no writes, allowing this fixture to exercise restoration without a GPU.
    unsafe { memory.set_gpu_sync(noop_sync()) };
    for address in [DATA, ALIAS] {
        memory.unguard(address, 4);
        memory.unguard_writes(address, 4);
    }
    memory.unguard(TEXT, 4); // No matching guard is an actual no-op.
    memory.unguard_writes(TEXT, 4);
    assert_eq!(memory.fence_mapping_epoch, epoch);
    assert!(memory.verify_base_code_fence().is_ok());
    assert_eq!(memory.read8(ALIAS), 0x44);
    memory.map(DATA + PAGE_SIZE, data, PAGE_SIZE, Permission::RW, MemoryState::Alias);
    assert!(memory.fence_mapping_epoch > epoch);
    let mapped_epoch = memory.fence_mapping_epoch;
    memory.unmap(DATA + PAGE_SIZE, PAGE_SIZE);
    assert!(memory.fence_mapping_epoch > mapped_epoch);
}

// CodexAstraUlt: Match add_guard's zero-length and saturating endpoints at both
// text boundaries, including a one-byte overlap and an unrelated far-end range.
#[test]
fn guard_epoch_overlap_matches_page_aligned_text_boundaries() {
    let (mut memory, _, _) = fixture();
    memory.install_base_code_fence(TEXT, TEXT_BYTES).unwrap();
    let end = TEXT + TEXT_BYTES;
    for (address, len, changes) in [
        (TEXT, 0, false), (TEXT - 1, 0, false),
        (TEXT - PAGE_SIZE, PAGE_SIZE, false), (TEXT - 1, 1, false),
        (TEXT - 1, 2, true), (TEXT, 1, true),
        (end - 1, 1, true), (end - 1, 2, true),
        (end, 1, false), (0, TEXT, false), (0, TEXT + 1, true),
        (u32::MAX, 1, false), (u32::MAX - 8, 16, false),
        (TEXT - 1, u32::MAX, true),
    ] {
        let epoch = memory.fence_mapping_epoch;
        memory.fence_guard_changed(address, len);
        assert_eq!(memory.fence_mapping_epoch, epoch + u64::from(changes),
            "guard at {address:08X} + {len:08X}");
    }
    // Real read guards at the interior boundary must still reject native work.
    memory.guard_cpu_reads(TEXT - 1, 2);
    assert_eq!(memory.verify_base_code_fence().unwrap_err(), "native_base_code_fence_mapping_changed");
}

// CodexAstraUlt: Callbacks are deliberately harmless unless a fixture requests
// a remap. Their observations check invalidation occurs before reentrant work.
unsafe fn noop_guard_sync(_: *mut (), _: u32, _: &mut Memory, _: VAddr, _: u32) {}

fn noop_sync() -> GpuSync {
    GpuSync { gpu: std::ptr::null_mut(), linear_base: 0, sync: noop_guard_sync, sync_write: noop_guard_sync }
}

struct GuardObservation {
    previous_epoch: u64,
    require_invalidated: bool,
    remap_to: Option<u32>,
    seen: Vec<(u32, u32)>,
}

unsafe fn observe_guard_sync(gpu: *mut (), _: u32, memory: &mut Memory, address: VAddr, len: u32) {
    // SAFETY: The fixture owns this exact live observation until it clears sync.
    let observation = unsafe { &mut *gpu.cast::<GuardObservation>() };
    if observation.require_invalidated {
        assert!(memory.fence_mapping_epoch > observation.previous_epoch);
    }
    observation.seen.push((address, len));
    if let Some(physical) = observation.remap_to {
        memory.map(TEXT, physical, PAGE_SIZE, Permission::RX, MemoryState::Code);
    }
}

#[test]
fn releasing_merged_guards_invalidates_the_whole_restored_range() {
    for writes in [false, true] {
        let (mut memory, _, _) = fixture();
        memory.install_base_code_fence(TEXT, TEXT_BYTES).unwrap();
        let guard = if writes { Memory::guard_cpu_writes } else { Memory::guard_cpu_reads };
        guard(&mut memory, TEXT - 16, 32);
        guard(&mut memory, TEXT + 8, TEXT_BYTES + 16);
        let mut observation = GuardObservation { previous_epoch: memory.fence_mapping_epoch,
            require_invalidated: true, remap_to: None, seen: Vec::new() };
        // SAFETY: The observation stays live and exclusively accessed by this
        // synchronous callback until the stored pointer is explicitly cleared.
        unsafe { memory.set_gpu_sync(GpuSync { gpu: (&mut observation as *mut GuardObservation).cast(),
            linear_base: 0, sync: observe_guard_sync, sync_write: observe_guard_sync }) };
        // This request lies entirely outside admitted text, but releases the
        // merged guard spanning both text pages, including their table entries.
        if writes { memory.unguard_writes(TEXT - 8, 1) } else { memory.unguard(TEXT - 8, 1) }
        memory.clear_gpu_sync();
        assert_eq!(observation.seen, [(TEXT - 16, TEXT_BYTES + 40)]);
        assert!(memory.verify_base_code_fence().is_ok());
        assert_eq!(memory.read8(TEXT), 0x44);
    }
}

#[test]
fn unrelated_guard_callbacks_remapping_text_still_reject_native_work() {
    for writes in [false, true] {
        let (mut memory, _, data) = fixture();
        memory.install_base_code_fence(TEXT, TEXT_BYTES).unwrap();
        let guard = if writes { Memory::guard_cpu_writes } else { Memory::guard_cpu_reads };
        guard(&mut memory, DATA, 4);
        let mut observation = GuardObservation { previous_epoch: memory.fence_mapping_epoch,
            require_invalidated: false, remap_to: Some(data), seen: Vec::new() };
        // SAFETY: As above, this callback only uses the live fixture observation.
        unsafe { memory.set_gpu_sync(GpuSync { gpu: (&mut observation as *mut GuardObservation).cast(),
            linear_base: 0, sync: observe_guard_sync, sync_write: observe_guard_sync }) };
        if writes { memory.unguard_writes(DATA, 4) } else { memory.unguard(DATA, 4) }
        memory.clear_gpu_sync();
        assert_eq!(observation.seen, [(DATA, 4)]);
        assert!(memory.fence_mapping_epoch > observation.previous_epoch);
        assert_eq!(memory.verify_base_code_fence().unwrap_err(), "native_base_code_fence_mapping_changed");
    }
}

// CodexAstraUlt: This authored 16 MiB text control checks the cached path by
// epoch, then contrasts it with forced global invalidation in the same process.
// At most 96 guard/verify pairs run. Timings are printed, never used as a pass
// threshold or extrapolated into private-title/Thor performance claims.
#[test]
fn unrelated_guards_avoid_full_text_revalidation_control() {
    let mut memory = Memory::new(false, 64 * 1024 * 1024);
    let bytes = 16 * 1024 * 1024;
    let block = memory.phys.allocate(MemoryRegion::Application, bytes + PAGE_SIZE).unwrap();
    let data = 0x0200_0000;
    memory.map(TEXT, block.addr, bytes, Permission::RX, MemoryState::Code);
    memory.map(data, block.addr + bytes, PAGE_SIZE, Permission::RW, MemoryState::Private);
    memory.install_base_code_fence(TEXT, bytes).unwrap();
    let mut samples = Vec::new();
    for round in 0..3 {
        for forced in if round % 2 == 0 { [false, true] } else { [true, false] } {
            let epoch = memory.fence_mapping_epoch;
            let started = std::time::Instant::now();
            for _ in 0..16 {
                memory.guard_cpu_writes(data, 4);
                if forced { memory.fence_mapping_changed(); }
                assert!(memory.verify_base_code_fence().is_ok());
            }
            samples.push((forced, started.elapsed()));
            assert_eq!(memory.fence_mapping_epoch, epoch + if forced { 16 } else { 0 });
            assert_eq!(memory.base_code_fence.as_ref().unwrap().verified_epoch.get(), memory.fence_mapping_epoch);
        }
    }
    eprintln!("16 MiB fence, 16 unrelated guard/verify pairs per sample, forced global epoch vs cached: {samples:?}");
}

#[test]
fn state_restore_and_map_restore_reject_while_fenced() {
    let (mut memory, _, _) = fixture();
    let map = memory.save_map();
    memory.install_base_code_fence(TEXT, TEXT_BYTES).unwrap();
    assert_eq!(memory.load_map(map).unwrap_err(), "native_base_code_fence_disallows_state_restore");
    let mut system = System::new(Config::default());
    system.memory = memory;
    assert_eq!(system.load_state(&[]).unwrap_err(), "native_base_code_fence_disallows_state_restore");
    assert!(system.memory.verify_base_code_fence().is_ok());
    assert_eq!(system.memory.read8(TEXT), 0x44);
}

#[test]
fn changed_mapping_stops_system_before_guest_instruction() {
    let (mut memory, _, data) = fixture();
    memory.install_base_code_fence(TEXT, TEXT_BYTES).unwrap();
    let mut system = System::new(Config::default());
    system.memory = memory;
    system.cpu.regs[15] = TEXT;
    system.memory.map(TEXT, data, PAGE_SIZE, Permission::RX, MemoryState::Code);
    assert_eq!(system.step(None), StepOutcome::Faulted);
    assert_eq!(system.diagnostic_fault(), Some(&DiagnosticFault::NativeCodeFence { pc: TEXT }));
    assert_eq!(system.cpu.cycles, 0);
    assert_eq!(system.interpreted_instructions, 0);
    assert_eq!(system.recompiled_instructions, 0);
    assert_eq!(system.step(None), StepOutcome::Faulted);
}

// CodexAstraUlt: A separate process exercises writes that would crash this test
// runner. A signal is asserted only for these controlled known-pointer fixtures;
// a private worker signal must remain an unclassified incomplete run.
#[test]
fn fenced_writes_terminate_subprocess() {
    use std::os::unix::process::ExitStatusExt;
    const CHILD: &str = "DROIDDS_FENCE_WRITE_FIXTURE";
    if let Ok(mode) = std::env::var(CHILD) {
        // SAFETY: Disable crash dump files only in the isolated test child.
        unsafe { libc::setrlimit(libc::RLIMIT_CORE, &libc::rlimit { rlim_cur: 0, rlim_max: 0 }) };
        let (mut memory, text, _) = fixture();
        memory.install_base_code_fence(TEXT, TEXT_BYTES).unwrap();
        match mode.as_str() {
            "native_alias" => {
                let writes = memory.page_tables().1;
                // SAFETY: The pointer names live RAM, deliberately protected by
                // Linux; this diagnostic child must stop before the write lands.
                unsafe { std::ptr::write_volatile(*writes.add((ALIAS >> PAGE_BITS) as usize), 0xAA) };
            }
            "bus_alias" => memory.write8(ALIAS, 0xAA),
            "bulk_alias" => memory.write_bytes(ALIAS, &[0xAA]),
            "privileged" => { memory.write32_privileged(TEXT, 0xAABB_CCDD); },
            "physical" => { memory.write_physical(text, &[0xAA]); },
            "gpu_slice" => {
                let bytes = memory.phys.host_slice_mut(text, 1).unwrap();
                // SAFETY: The GPU's physical slice points at the same protected
                // page; a volatile access ensures the test performs the write.
                unsafe { std::ptr::write_volatile(bytes.as_mut_ptr(), 0xAA) };
            }
            _ => panic!("unknown original fence fixture"),
        }
        std::hint::black_box(memory.read8(TEXT));
        std::process::exit(42);
    }
    for mode in ["native_alias", "bus_alias", "bulk_alias", "privileged", "physical", "gpu_slice"] {
        let output = std::process::Command::new(std::env::current_exe().unwrap())
            .args(["--exact", "memory::fence_tests::fenced_writes_terminate_subprocess", "--nocapture", "--test-threads=1"])
            .env(CHILD, mode).output().unwrap();
        assert_eq!(output.status.signal(), Some(libc::SIGSEGV),
            "{mode} unexpectedly returned {}: {}", output.status, String::from_utf8_lossy(&output.stderr));
    }
}
