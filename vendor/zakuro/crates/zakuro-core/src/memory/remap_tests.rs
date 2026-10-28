//! CodexAstraUlt: Original remap regressions bind allowed accesses to the new
//! backing and ensure permission revocation reaches interpreter and native tables.

use super::*;

const ADDRESS: VAddr = 0x1F00_0000;

// CodexAstraUlt: Distinct backing bytes expose stale pointers even when a new
// mapping has the same virtual address; inspect backing without guest permissions.
fn fixture() -> (Memory, u32, u32) {
    let mut memory = Memory::new(false, 0x0400_0000);
    let first = memory
        .phys
        .allocate(MemoryRegion::Application, PAGE_SIZE)
        .unwrap()
        .addr;
    let second = memory
        .phys
        .allocate(MemoryRegion::Application, PAGE_SIZE)
        .unwrap()
        .addr;
    assert!(memory.write_physical(first, &[0x11; 16]));
    assert!(memory.write_physical(second, &[0x22; 16]));
    memory.map(
        ADDRESS,
        first,
        PAGE_SIZE,
        Permission::RW,
        MemoryState::Private,
    );
    (memory, first, second)
}

// CodexAstraUlt: Verify the actual physical contents, including an old page
// that a stale virtual write pointer could otherwise corrupt unnoticed.
fn backing(memory: &mut Memory, address: u32) -> [u8; 16] {
    let mut bytes = [0; 16];
    assert!(memory.read_physical(address, &mut bytes));
    bytes
}

// CodexAstraUlt: Read exactly the ABI entries that native execution receives;
// the table storage is borrowed only while Memory is alive and unmodified here.
fn cpu_entries(memory: &Memory) -> (*mut u8, *mut u8) {
    let (reads, writes) = memory.page_tables();
    let index = (ADDRESS >> PAGE_BITS) as usize;
    // SAFETY: ADDRESS is a valid guest page index in both exported tables.
    unsafe { (*reads.add(index), *writes.add(index)) }
}

// CodexAstraUlt: Both data-only and executable read-only remaps must reject
// writes at every Bus width and in the host bulk path without touching old data.
#[test]
fn remap_read_only_rejects_every_bus_write_width_and_bulk_write() {
    for permission in [Permission::READ, Permission::RX] {
        let (mut memory, first, second) = fixture();
        memory.map(ADDRESS, second, PAGE_SIZE, permission, MemoryState::Code);

        memory.write8(ADDRESS, 0xAA);
        memory.write16(ADDRESS + 2, 0xBBBB);
        memory.write32(ADDRESS + 4, 0xCCCC_CCCC);
        memory.write_bytes(ADDRESS + 8, &[0xDD; 4]);
        assert_eq!(backing(&mut memory, first), [0x11; 16]);
        assert_eq!(backing(&mut memory, second), [0x22; 16]);
        assert_eq!(memory.read8(ADDRESS), 0x22);
        assert_eq!(memory.read16(ADDRESS), 0x2222);
        assert_eq!(memory.read32(ADDRESS), 0x2222_2222);
        assert_eq!(memory.query(ADDRESS).permission, permission.bits());
        assert!(!memory.is_writable(ADDRESS, PAGE_SIZE));
        assert_eq!(memory.fault_summary(), vec![(ADDRESS, 4)]);
        let (read, write) = cpu_entries(&memory);
        assert_eq!(memory.phys.paddr_of(read), Some(second));
        assert!(write.is_null());
    }
}

// CodexAstraUlt: Removing read permission must hide the former backing from
// every read route while allowed writes still reach the replacement page.
#[test]
fn remap_write_only_rejects_every_bus_read_width_and_bulk_read() {
    let (mut memory, first, second) = fixture();
    memory.map(
        ADDRESS,
        second,
        PAGE_SIZE,
        Permission::WRITE,
        MemoryState::Private,
    );

    assert_eq!(memory.read8(ADDRESS), 0);
    assert_eq!(memory.read16(ADDRESS), 0);
    assert_eq!(memory.read32(ADDRESS), 0);
    let mut bytes = [0xFF; 4];
    memory.read_bytes(ADDRESS, &mut bytes);
    assert_eq!(bytes, [0; 4]);
    assert!(!memory.is_readable(ADDRESS, PAGE_SIZE));
    assert_eq!(memory.fault_summary(), vec![(ADDRESS, 4)]);
    memory.write32(ADDRESS, 0x4433_2211);
    assert_eq!(
        &backing(&mut memory, second)[..4],
        &[0x11, 0x22, 0x33, 0x44]
    );
    assert_eq!(backing(&mut memory, first), [0x11; 16]);
    let (read, write) = cpu_entries(&memory);
    assert!(read.is_null());
    assert_eq!(memory.phys.paddr_of(write), Some(second));
}

// CodexAstraUlt: Revoking both data permissions must clear both exported paths,
// including when a mapping retains its separate execute flag.
#[test]
fn remap_without_data_permissions_clears_both_access_paths() {
    let (mut memory, first, second) = fixture();
    // CodexAstraUlt: This checks data access for both masks; it does not claim
    // separate execute-bit enforcement, which the current fetch path lacks.
    for permission in [Permission::empty(), Permission::EXECUTE] {
        memory.map(
            ADDRESS,
            first,
            PAGE_SIZE,
            Permission::RW,
            MemoryState::Private,
        );
        memory.map(ADDRESS, second, PAGE_SIZE, permission, MemoryState::Code);
        memory.write32(ADDRESS, 0xAABB_CCDD);
        assert_eq!(memory.read32(ADDRESS), 0);
        assert_eq!(backing(&mut memory, first), [0x11; 16]);
        assert_eq!(backing(&mut memory, second), [0x22; 16]);
        let (read, write) = cpu_entries(&memory);
        assert!(read.is_null() && write.is_null());
    }
}

// CodexAstraUlt: Native callers retain the page-table arrays across remapping;
// restored entries must target current backing and agree with interpreter access.
#[test]
fn remap_restoring_permissions_updates_existing_native_table_views() {
    let (mut memory, first, second) = fixture();
    let tables = memory.page_tables();
    memory.map(ADDRESS, first, PAGE_SIZE, Permission::RX, MemoryState::Code);
    assert!(cpu_entries(&memory).1.is_null());
    memory.map(
        ADDRESS,
        second,
        PAGE_SIZE,
        Permission::RW,
        MemoryState::Private,
    );
    assert_eq!(memory.page_tables(), tables);
    let (read, write) = cpu_entries(&memory);
    assert_eq!(memory.phys.paddr_of(read), Some(second));
    assert_eq!(memory.phys.paddr_of(write), Some(second));
    // CodexAstraUlt: Exercise the exported native fast path and observe its
    // result through the Bus, then reverse direction without stale backing.
    // SAFETY: The mapped page is live, writable, and owned exclusively here.
    unsafe { *write = 0xAB };
    assert_eq!(memory.read8(ADDRESS), 0xAB);
    memory.write8(ADDRESS + 1, 0xCD);
    // SAFETY: The same live mapped page is readable through its exported entry.
    assert_eq!(unsafe { *read.add(1) }, 0xCD);
    assert_eq!(backing(&mut memory, first), [0x11; 16]);
    assert!(memory.fault_summary().is_empty());
}

// CodexAstraUlt: The callback attempts a real backing write, as GPU writeback
// does. Its attempt must not restore CPU write permission removed by a remap.
unsafe fn guarded_writeback(gpu: *mut (), _: u32, memory: &mut Memory, address: VAddr, len: u32) {
    // SAFETY: The test owns this counter until clear_gpu_sync after all accesses.
    unsafe { *(gpu as *mut u32) += 1 };
    memory.write_bytes(address, &vec![0xAB; len as usize]);
}

// CodexAstraUlt: A guard flush must preserve revoked permissions, and enabling
// writes again must still synchronize a newly guarded range exactly once.
#[test]
fn remap_preserves_gpu_guards_without_reviving_revoked_permissions() {
    let (mut memory, first, second) = fixture();
    memory.guard_cpu_reads(ADDRESS, 4);
    memory.guard_cpu_writes(ADDRESS, 4);
    memory.map(
        ADDRESS,
        second,
        PAGE_SIZE,
        Permission::RX,
        MemoryState::Code,
    );
    let (read, write) = cpu_entries(&memory);
    assert!(read.is_null() && write.is_null());

    let mut callbacks = 0u32;
    // SAFETY: The counter remains live and exclusively accessed by the callback
    // during these operations; the callback is cleared before leaving the test.
    unsafe {
        memory.set_gpu_sync(GpuSync {
            gpu: &mut callbacks as *mut u32 as *mut (),
            linear_base: 0,
            sync: guarded_writeback,
            sync_write: guarded_writeback,
        });
    }
    memory.write32(ADDRESS, 0xCCCC_CCCC);
    assert_eq!(callbacks, 1);
    assert!(cpu_entries(&memory).1.is_null());
    assert_eq!(backing(&mut memory, first), [0x11; 16]);
    assert_eq!(backing(&mut memory, second), [0x22; 16]);
    assert_eq!(memory.read32(ADDRESS), 0x2222_2222);
    assert_eq!(callbacks, 2);
    let (read, write) = cpu_entries(&memory);
    assert_eq!(memory.phys.paddr_of(read), Some(second));
    assert!(write.is_null());

    // CodexAstraUlt: Re-enabling writes must still honor a pending writeback;
    // its first write flushes once and later writes use the current backing.
    memory.guard_cpu_writes(ADDRESS, 4);
    memory.map(
        ADDRESS,
        second,
        PAGE_SIZE,
        Permission::RW,
        MemoryState::Private,
    );
    assert!(cpu_entries(&memory).1.is_null());
    memory.write8(ADDRESS, 0xCD);
    assert_eq!(callbacks, 3);
    assert_eq!(memory.read32(ADDRESS), 0xABAB_ABCD);
    memory.write8(ADDRESS + 1, 0xEF);
    assert_eq!(callbacks, 3);
    assert_eq!(memory.read32(ADDRESS), 0xABAB_EFCD);
    assert_eq!(backing(&mut memory, first), [0x11; 16]);
    memory.clear_gpu_sync();
}
