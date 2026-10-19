//! CodexAstraUlt: Original NCCH byte fixtures exercise the actual filesystem,
//! title loader, HLE memory syscalls and service allocator. No retail input or
//! implementation-generated expected region table is used in these tests.

use std::path::PathBuf;
use std::sync::atomic::{AtomicU64, Ordering};
use zakuro_common::memory_map::*;
use zakuro_core::kernel::{
    ipc::{CommandBuffer, Header},
    svc,
};
use zakuro_core::memory::{MemoryLayout, MemoryRegion, MemoryState, Permission, PhysicalMemory};
use zakuro_core::{loader, services, Config, StepOutcome, System};
use zakuro_cpu::Bus;
use zakuro_fs::SystemMode;

const MIB: u32 = 1 << 20;
static NEXT_FILE: AtomicU64 = AtomicU64::new(0);

struct Fixture(PathBuf);
impl Drop for Fixture {
    fn drop(&mut self) {
        let _ = std::fs::remove_file(&self.0);
    }
}

fn fixture(platform: u8, old: u8, new: u8, kernel: u16) -> Fixture {
    // CodexAstraUlt: A hand-encoded MOV r0,#42; SVC ExitProcess is sufficient
    // to prove that the parsed image actually reaches the guest interpreter.
    let mut image = vec![0u8; 0x808];
    let put32 =
        |bytes: &mut [u8], at, value: u32| bytes[at..at + 4].copy_from_slice(&value.to_le_bytes());
    image[0x100..0x104].copy_from_slice(b"NCCH");
    image[0x118..0x120].copy_from_slice(&0x0004_0000_0DD5_0005u64.to_le_bytes());
    image[0x18C] = platform;
    image[0x18D] = 2;
    image[0x18F] = 4;
    put32(&mut image, 0x180, 0x400);
    put32(&mut image, 0x1A0, 3);
    put32(&mut image, 0x1A4, 2);
    put32(&mut image, 0x210, 0x0010_0000);
    put32(&mut image, 0x214, 1);
    put32(&mut image, 0x218, 8);
    put32(&mut image, 0x21C, 0x4000);
    put32(&mut image, 0x220, 0x0010_1000);
    put32(&mut image, 0x230, 0x0010_1000);
    image[0x40C] = 3;
    image[0x40D] = new;
    image[0x40E] = old << 4;
    image[0x40F] = 0x30;
    image[0x570..0x5E0].fill(0xFF);
    put32(&mut image, 0x570, 0xFC00_0000 | u32::from(kernel));
    image[0x600..0x605].copy_from_slice(b".code");
    put32(&mut image, 0x60C, 8);
    put32(&mut image, 0x800, 0xE3A0_002A);
    put32(&mut image, 0x804, 0xEF00_0003);
    let path = std::env::temp_dir().join(format!(
        "droidds-memory-{}-{}.cxi",
        std::process::id(),
        NEXT_FILE.fetch_add(1, Ordering::Relaxed)
    ));
    std::fs::write(&path, image).unwrap();
    Fixture(path)
}

fn load(image: &Fixture, new3ds: bool) -> System {
    loader::load(
        &image.0,
        Config {
            new3ds,
            find_recompiled: false,
            hardware_renderer: false,
            clock: Some(0),
            ..Config::default()
        },
    )
    .unwrap()
}

fn allocate(system: &mut System, linear: bool, size: u32) -> (u32, u32) {
    system.cpu.regs[..5].copy_from_slice(&[if linear { 0x1_0003 } else { 3 }, 0, 0, size, 3]);
    svc::dispatch(system, 1);
    (system.cpu.regs[0], system.cpu.regs[1])
}

#[test]
fn droidds_real_loader_reports_geometry_and_executes_every_supported_mode() {
    // CodexAstraUlt: Expected physical splits and reported commitment are
    // literal external contracts, independent of the resolver implementation.
    let cases = [
        (false, 0, 0, 0, 64, 44, 20, 64),
        (false, 2, 0, 2, 96, 12, 20, 96),
        (false, 3, 0, 3, 80, 28, 20, 80),
        (false, 4, 0, 4, 72, 36, 20, 72),
        (false, 5, 0, 5, 32, 76, 20, 32),
        (true, 0, 0, 6, 124, 100, 32, 64),
        (true, 2, 0, 6, 124, 100, 32, 96),
        (true, 3, 0, 6, 124, 100, 32, 80),
        (true, 0, 1, 6, 124, 100, 32, 124),
        (true, 0, 2, 7, 178, 46, 32, 178),
    ];
    for (new3ds, old, new, mode, app, system_bytes, base, limit) in cases {
        let image = fixture(if new3ds { 2 } else { 1 }, old, new, 0x22C);
        // Platform 2 must select the New model even with default configuration.
        let mut system = load(&image, false);
        assert_eq!(system.config.new3ds, new3ds);
        assert_eq!(system.config.model.is_new3ds(), new3ds);
        assert_eq!(
            system.memory.phys.fcram.len(),
            if new3ds { 256 * MIB } else { 128 * MIB } as usize
        );
        for (region, expected) in [
            (MemoryRegion::Application, app),
            (MemoryRegion::System, system_bytes),
            (MemoryRegion::Base, base),
        ] {
            assert_eq!(system.memory.phys.region_size(region), expected * MIB);
        }
        assert_eq!(
            system.memory.phys.region_limit(MemoryRegion::Application),
            limit * MIB
        );
        for (offset, expected) in [
            (0x30, mode),
            (0x40, limit * MIB),
            (0x44, system_bytes * MIB),
            (0x48, base * MIB),
        ] {
            assert_eq!(
                system.memory.read32(CONFIG_MEM_VADDR + offset),
                expected,
                "mode {old}/{new} offset {offset:X}"
            );
        }
        assert!(matches!(system.step(Some(64)), StepOutcome::Ran));
        assert_eq!(system.cpu.regs[0], 42);
        assert!(matches!(system.step(Some(64)), StepOutcome::Exited));
        assert_eq!(system.interpreted_instructions, 2);
    }
}

#[test]
fn droidds_real_kernel_resource_limit_heap_linear_and_hid_base_allocation() {
    for (new3ds, old, new, limit) in [
        (false, 2, 0, 96),
        (true, 0, 0, 64),
        (true, 0, 1, 124),
        (true, 0, 2, 178),
    ] {
        for kernel in [0x22B, 0x22C] {
            let image = fixture(if new3ds { 2 } else { 1 }, old, new, kernel);
            let mut system = load(&image, false);
            let (result, heap) = allocate(&mut system, false, PAGE_SIZE);
            assert_eq!((result, heap), (0, HEAP_VADDR));
            system.memory.write32(heap, 1); // RESLIMIT_COMMIT
            system.cpu.regs[..4].copy_from_slice(&[heap + 8, 0, heap, 1]);
            svc::dispatch(&mut system, 0x39);
            assert_eq!(system.cpu.regs[0], 0);
            assert_eq!(system.memory.read32(heap + 8), limit * MIB);
            assert_eq!(system.memory.read32(heap + 12), 0);
            let (result, linear) = allocate(&mut system, true, PAGE_SIZE);
            assert_eq!(result, 0);
            assert_eq!(
                linear,
                if kernel < 0x22C {
                    0x1400_0000
                } else {
                    0x3000_0000
                }
            );
            let mapping = system.memory.mapping_at(linear).unwrap();
            assert_eq!(mapping.paddr, FCRAM_PADDR);
            assert!(mapping.paddr + mapping.size <= system.memory.mapping_at(heap).unwrap().paddr);

            // Actual service dispatch allocates HID shared memory from Base;
            // Old mode 2 previously left this region empty and could panic.
            assert!(matches!(system.step(Some(64)), StepOutcome::Ran));
            let tls = system.kernel.current().unwrap().tls;
            let buffer = CommandBuffer::new(tls);
            buffer.set(&mut system.memory, 0, Header::new(0xA, 0, 0).0);
            let before = system.memory.phys.region_used(MemoryRegion::Base);
            services::handle_request(&mut system, services::Target::service("hid:USER".into(), 0));
            assert!(system.services.hid.shared_memory_handle.is_some());
            assert!(system.memory.phys.region_used(MemoryRegion::Base) > before);
            assert!(system.services.unimplemented.is_empty());

            let used = system.memory.phys.region_used(MemoryRegion::Application);
            let free = system.memory.phys.region_free(MemoryRegion::Application);
            let rest = system
                .memory
                .phys
                .allocate(MemoryRegion::Application, free)
                .unwrap();
            assert_eq!(
                system.memory.phys.region_used(MemoryRegion::Application),
                limit * MIB
            );
            assert_eq!(
                allocate(&mut system, false, PAGE_SIZE).0,
                zakuro_common::result::errors::OUT_OF_MEMORY.0
            );
            assert_eq!(
                system.memory.phys.region_used(MemoryRegion::Application),
                limit * MIB
            );
            system.memory.phys.free(rest);
            assert_eq!(
                system.memory.phys.region_used(MemoryRegion::Application),
                used
            );
            let again = system
                .memory
                .phys
                .allocate(MemoryRegion::Application, free)
                .unwrap();
            assert_eq!(again, rest);
            system.memory.phys.free(again);
        }
    }
}

#[test]
fn droidds_unsupported_modes_fail_and_next_valid_load_recovers() {
    for (old, new) in [(1, 0), (0, 3), (0, 15), (4, 0), (5, 0)] {
        let image = fixture(2, old, new, 0x22C);
        assert!(matches!(
            loader::load(&image.0, Config::default()),
            Err(loader::LoadError::MemoryLayout(_))
        ));
    }
    let image = fixture(1, 0, 1, 0x22C);
    let old = load(&image, false);
    assert_eq!(
        old.memory.phys.region_limit(MemoryRegion::Application),
        64 * MIB
    );
    drop(old);
    let new = load(&image, true);
    assert_eq!(
        new.memory.phys.region_limit(MemoryRegion::Application),
        124 * MIB
    );
}

#[test]
fn droidds_allocation_restore_and_failed_requests_preserve_accounting() {
    let layout = MemoryLayout::resolve(true, SystemMode::Prod, 0).unwrap();
    let mut memory = PhysicalMemory::with_layout(layout);
    let top = memory
        .allocate_top(MemoryRegion::Application, PAGE_SIZE)
        .unwrap();
    assert_eq!(top.addr, FCRAM_PADDR + 124 * MIB - PAGE_SIZE);
    let (bits, regions) = memory.allocation();
    memory.free(top);
    memory.free(top);
    assert_eq!(memory.region_used(MemoryRegion::Application), 0);
    assert!(memory.set_allocation(bits.clone(), regions));
    assert_eq!(memory.region_used(MemoryRegion::Application), PAGE_SIZE);
    assert!(memory
        .allocate(MemoryRegion::Application, u32::MAX)
        .is_none());
    let mut invalid_regions = regions;
    invalid_regions[1].0 = 0;
    assert!(!memory.set_allocation(bits.clone(), invalid_regions));
    let mut overcommitted = bits;
    overcommitted[..(65 * MIB / PAGE_SIZE) as usize].fill(true);
    assert!(!memory.set_allocation(overcommitted, regions));
    assert_eq!(memory.region_used(MemoryRegion::Application), PAGE_SIZE);
}

// CodexAstraUlt: The newly available 178 MiB commitment must never expand a
// private/old-linear virtual window or replace the main stack and other maps.
#[test]
fn droidds_heap_windows_reject_overlap_overflow_and_old_linear_excess() {
    for kernel in [0x22B, 0x22C] {
        let image = fixture(2, 0, 2, kernel);
        let mut system = load(&image, false);
        let original = system.memory.phys.region_used(MemoryRegion::Application);
        let stack = SHARED_MEMORY_VADDR - PAGE_SIZE;
        system.memory.write32(stack, 0xC0DE_1234);
        // CodexAstraUlt: A prior alias can occupy the linear destination while
        // the candidate physical page is free. Rejection releases that candidate.
        let linear_base = system.kernel.linear_base;
        let code_page = system.memory.mapping_at(PROCESS_IMAGE_VADDR).unwrap().paddr;
        system.memory.map(
            linear_base,
            code_page,
            PAGE_SIZE,
            Permission::READ,
            MemoryState::Alias,
        );
        assert_ne!(allocate(&mut system, true, PAGE_SIZE).0, 0);
        assert_eq!(
            system.memory.phys.region_used(MemoryRegion::Application),
            original
        );
        assert_eq!(
            system.memory.mapping_at(linear_base).unwrap().paddr,
            code_page
        );
        system.memory.unmap(linear_base, PAGE_SIZE);
        for (base, size) in [
            (HEAP_VADDR, 129 * MIB),
            (HEAP_VADDR, HEAP_SIZE),
            (SHARED_MEMORY_VADDR - 4 * PAGE_SIZE, 4 * PAGE_SIZE),
            (SHARED_MEMORY_VADDR, PAGE_SIZE),
            (0xFFFF_F000, 2 * PAGE_SIZE),
            (HEAP_VADDR + 1, PAGE_SIZE),
        ] {
            system.cpu.regs[..5].copy_from_slice(&[3, base, 0, size, 3]);
            svc::dispatch(&mut system, 1);
            assert_ne!(system.cpu.regs[0], 0, "accepted {base:X}+{size:X}");
            assert_eq!(
                system.memory.phys.region_used(MemoryRegion::Application),
                original
            );
            assert_eq!(system.memory.read32(stack), 0xC0DE_1234);
        }
        let (result, address) = allocate(&mut system, true, 129 * MIB);
        if kernel < 0x22C {
            assert_eq!(result, zakuro_common::result::errors::OUT_OF_MEMORY.0);
            assert_eq!(
                system.memory.phys.region_used(MemoryRegion::Application),
                original
            );
        } else {
            assert_eq!((result, address), (0, LINEAR_HEAP_VADDR_NEW3DS));
            assert_eq!(system.memory.mapping_at(address).unwrap().size, 129 * MIB);
        }
        let (result, heap) = allocate(&mut system, false, PAGE_SIZE);
        assert_eq!(result, 0);
        system.memory.write32(heap, 0x1234_ABCD);
        let used = system.memory.phys.region_used(MemoryRegion::Application);
        system.cpu.regs[..5].copy_from_slice(&[3, heap, 0, PAGE_SIZE, 3]);
        svc::dispatch(&mut system, 1);
        assert_ne!(system.cpu.regs[0], 0);
        assert_eq!(
            system.memory.phys.region_used(MemoryRegion::Application),
            used
        );
        assert_eq!(system.memory.read32(heap), 0x1234_ABCD);
    }
}

// CodexAstraUlt: A state can have exactly the same RAM byte count and package
// version but incompatible geometry or a larger commitment. Rejection must
// preserve live RAM, mappings, CPU values and quota accounting.
#[test]
fn droidds_incompatible_same_size_state_does_not_mutate_live_machine() {
    for (new3ds, source_mode, source_new, target_mode, target_new, source_bytes) in [
        (false, SystemMode::Dev1, 0, SystemMode::Prod, 0, PAGE_SIZE),
        (true, SystemMode::Prod, 1, SystemMode::Prod, 0, 65 * MIB),
    ] {
        let source_layout = MemoryLayout::resolve(new3ds, source_mode, source_new).unwrap();
        let mut source = System::with_memory_layout(Config::default(), source_layout);
        let block = source
            .memory
            .phys
            .allocate(MemoryRegion::Application, source_bytes)
            .unwrap();
        source.memory.map(
            HEAP_VADDR,
            block.addr,
            PAGE_SIZE,
            Permission::RW,
            MemoryState::Private,
        );
        source.memory.write32(HEAP_VADDR, 0xDEAD_BEEF);
        let state = source.save_state().unwrap();
        drop(source);
        let target_layout = MemoryLayout::resolve(new3ds, target_mode, target_new).unwrap();
        let mut target = System::with_memory_layout(Config::default(), target_layout);
        let block = target
            .memory
            .phys
            .allocate(MemoryRegion::Application, PAGE_SIZE)
            .unwrap();
        target.memory.map(
            HEAP_VADDR,
            block.addr,
            PAGE_SIZE,
            Permission::RW,
            MemoryState::Private,
        );
        target.memory.write32(HEAP_VADDR, 0x1234_ABCD);
        target.cpu.regs[3] = 99;
        assert!(target.load_state(&state).is_err());
        assert_eq!(target.memory.read32(HEAP_VADDR), 0x1234_ABCD);
        assert_eq!(
            target.memory.mapping_at(HEAP_VADDR).unwrap().paddr,
            block.addr
        );
        assert_eq!(target.cpu.regs[3], 99);
        assert_eq!(
            target.memory.phys.region_used(MemoryRegion::Application),
            PAGE_SIZE
        );
        assert_eq!(
            target.memory.phys.region_limit(MemoryRegion::Application),
            64 * MIB
        );
    }
}
