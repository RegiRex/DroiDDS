//! physical memory and the FCRAM page allocator.

use zakuro_common::memory_map::*;
use super::layout::MemoryLayout;
// CodexAstraUlt: Retain heap storage by default; isolated host diagnostics may
// replace FCRAM with owned aligned pages before any guest execution.
use super::fence::FcramBacking;

/// which of the kernel's three FCRAM regions an allocation comes from.
#[derive(Debug, Clone, Copy, PartialEq, Eq, serde::Serialize, serde::Deserialize)]
pub enum MemoryRegion {
    Application,
    System,
    Base,
}

/// a contiguous run of physical pages.
#[derive(Debug, Clone, Copy, PartialEq, Eq, serde::Serialize, serde::Deserialize)]
pub struct PhysicalBlock {
    pub addr: u32,
    pub size: u32,
}

/// backing store for every physical memory the CPU can reach.
pub struct PhysicalMemory {
    pub fcram: FcramBacking,
    pub vram: Box<[u8]>,
    pub dsp_ram: Box<[u8]>,
    /// AXI WRAM.
    pub axi_wram: Box<[u8]>,

    /// one bit per FCRAM page, set when allocated.
    allocated: Vec<bool>,
    /// region boundaries as page indices into allocated.
    regions: [(u32, u32); 3],
    // CodexAstraUlt: Commitment differs from physical geometry for New-model
    // legacy titles. Account in O(1), without rescanning RAM on every allocation.
    limits: [u32; 3],
    used: [u32; 3],
}

impl PhysicalMemory {
    /// CodexAstraUlt: Compatibility constructor for explicit-size unit fixtures.
    /// The loader uses with_layout with the fully resolved title configuration.
    pub fn new(new3ds: bool, app_bytes: u32) -> PhysicalMemory {
        Self::with_layout(MemoryLayout::for_application(new3ds, app_bytes))
    }

    pub fn with_layout(layout: MemoryLayout) -> PhysicalMemory {
        let total = layout.total_bytes();
        let [app, system, base] = layout.regions;

        let pages = (total / PAGE_SIZE) as usize;
        let app_pages = app / PAGE_SIZE;
        let system_pages = system / PAGE_SIZE;
        let base_pages = base / PAGE_SIZE;

        PhysicalMemory {
            fcram: FcramBacking::new(total as usize),
            vram: vec![0; VRAM_SIZE as usize].into_boxed_slice(),
            dsp_ram: vec![0; DSP_RAM_SIZE as usize].into_boxed_slice(),
            axi_wram: vec![0; AXI_WRAM_SIZE as usize].into_boxed_slice(),
            allocated: vec![false; pages],
            regions: [
                (0, app_pages),
                (app_pages, system_pages),
                (app_pages + system_pages, base_pages),
            ],
            limits: [layout.application_limit, system, base],
            used: [0; 3],
        }
    }

    /// the kernel's read-only configuration page, at the start of AXI WRAM.
    pub fn config_mem_mut(&mut self) -> &mut [u8] {
        let offset = (CONFIG_MEM_VADDR - AXI_WRAM_PADDR) as usize;
        &mut self.axi_wram[offset..offset + CONFIG_MEM_SIZE as usize]
    }

    /// the page the kernel keeps updating with time, battery and wifi state.
    pub fn shared_page_mut(&mut self) -> &mut [u8] {
        let offset = (SHARED_PAGE_VADDR - AXI_WRAM_PADDR) as usize;
        &mut self.axi_wram[offset..offset + SHARED_PAGE_SIZE as usize]
    }

    fn region_pages(&self, region: MemoryRegion) -> (u32, u32) {
        self.regions[Self::index(region)]
    }

    fn index(region: MemoryRegion) -> usize {
        match region {
            MemoryRegion::Application => 0,
            MemoryRegion::System => 1,
            MemoryRegion::Base => 2,
        }
    }

    pub fn region_size(&self, region: MemoryRegion) -> u32 {
        self.region_pages(region).1 * PAGE_SIZE
    }

    pub fn region_used(&self, region: MemoryRegion) -> u32 {
        self.used[Self::index(region)]
    }

    /// CodexAstraUlt: A process cannot commit every physical application page
    /// when PM restricts a legacy title to its Old-model compatibility budget.
    pub fn region_limit(&self, region: MemoryRegion) -> u32 {
        self.limits[Self::index(region)]
    }

    pub fn region_free(&self, region: MemoryRegion) -> u32 {
        self.region_limit(region) - self.region_used(region)
    }

    /// allocates size bytes of physically contiguous FCRAM.
    pub fn allocate(&mut self, region: MemoryRegion, size: u32) -> Option<PhysicalBlock> {
        self.allocate_below(region, size, FCRAM_PADDR + self.fcram.len() as u32)
    }

    /// CodexAstraUlt: Older firmware exposes only 128 MiB through its linear
    /// virtual window, even when the selected physical application is larger.
    /// Restrict the search before mutating allocation bits or commitment.
    pub fn allocate_below(&mut self, region: MemoryRegion, size: u32, end_paddr: u32) -> Option<PhysicalBlock> {
        // CodexAstraUlt: Reject overflow and quota exhaustion before touching
        // allocation state, including sizes that round to an extra page.
        let size = size.checked_add(PAGE_MASK)? & !PAGE_MASK;
        if size > self.region_free(region) { return None; }
        let needed = (size / PAGE_SIZE) as usize;
        if needed == 0 {
            return Some(PhysicalBlock {
                addr: FCRAM_PADDR,
                size: 0,
            });
        }

        let (start, count) = self.region_pages(region);
        let end = end_paddr.checked_sub(FCRAM_PADDR)? / PAGE_SIZE;
        let count = count.min(end.saturating_sub(start));
        let (start, count) = (start as usize, count as usize);

        let mut run = 0usize;
        for i in start..start + count {
            if self.allocated[i] {
                run = 0;
                continue;
            }
            run += 1;
            if run == needed {
                let first = i + 1 - needed;
                for page in &mut self.allocated[first..first + needed] {
                    *page = true;
                }
                self.used[Self::index(region)] += size;
                return Some(PhysicalBlock {
                    addr: FCRAM_PADDR + (first as u32 * PAGE_SIZE),
                    size: needed as u32 * PAGE_SIZE,
                });
            }
        }
        None
    }

    /// allocates size bytes of physically contiguous FCRAM from the top of
    /// the region, where the kernel puts a process's code, stack and heap,
    /// keeping the bottom for the linear heap, so the linear heap gives out
    /// the addresses the console does, which cheats count on.
    pub fn allocate_top(&mut self, region: MemoryRegion, size: u32) -> Option<PhysicalBlock> {
        // CodexAstraUlt: Top-down code/heap allocation shares the same budget
        // as the linear heap; physical placement still uses the full region.
        let size = size.checked_add(PAGE_MASK)? & !PAGE_MASK;
        if size > self.region_free(region) { return None; }
        let needed = (size / PAGE_SIZE) as usize;
        if needed == 0 {
            return Some(PhysicalBlock {
                addr: FCRAM_PADDR,
                size: 0,
            });
        }

        let (start, count) = self.region_pages(region);
        let (start, count) = (start as usize, count as usize);

        let mut run = 0usize;
        for i in (start..start + count).rev() {
            if self.allocated[i] {
                run = 0;
                continue;
            }
            run += 1;
            if run == needed {
                for page in &mut self.allocated[i..i + needed] {
                    *page = true;
                }
                self.used[Self::index(region)] += size;
                return Some(PhysicalBlock {
                    addr: FCRAM_PADDR + (i as u32 * PAGE_SIZE),
                    size: needed as u32 * PAGE_SIZE,
                });
            }
        }
        None
    }

    pub fn free(&mut self, block: PhysicalBlock) {
        // CodexAstraUlt: Release exactly the allocated pages, keeping quota
        // accounting correct for partial and repeated frees without underflow.
        let Some(offset) = block.addr.checked_sub(FCRAM_PADDR) else { return; };
        if offset & PAGE_MASK != 0 || block.size & PAGE_MASK != 0 { return; }
        let first = (offset / PAGE_SIZE) as usize;
        let Some(end) = first.checked_add((block.size / PAGE_SIZE) as usize)
            .filter(|&end| end <= self.allocated.len()) else { return; };
        for index in first..end {
            if self.allocated[index] {
                self.allocated[index] = false;
                let region = self.regions.iter().position(|&(start, count)|
                    (start as usize..(start + count) as usize).contains(&index)).unwrap();
                self.used[region] -= PAGE_SIZE;
            }
        }
    }

    /// host slice backing a physical address range, if it is real memory.
    /// the physical address a host pointer into one of the memories stands
    /// for, the way the page tables hold it.
    pub fn paddr_of(&self, pointer: *const u8) -> Option<u32> {
        [
            // CodexAstraUlt: The physical-address lookup accepts either FCRAM
            // backing without exposing ownership or assuming heap allocation.
            (VRAM_PADDR, self.vram.as_ref()),
            (DSP_RAM_PADDR, self.dsp_ram.as_ref()),
            (AXI_WRAM_PADDR, self.axi_wram.as_ref()),
            (FCRAM_PADDR, self.fcram.as_ref()),
        ]
        .into_iter()
        .find_map(|(base, store)| {
            let offset = (pointer as usize).wrapping_sub(store.as_ptr() as usize);
            (offset < store.len()).then(|| base + offset as u32)
        })
    }

    /// which pages are allocated and how the regions split them, for a
    /// saved state.
    pub fn allocation(&self) -> (Vec<bool>, [(u32, u32); 3]) {
        (self.allocated.clone(), self.regions)
    }

    /// the allocation a saved state had, false when it does not fit.
    pub fn set_allocation(&mut self, allocated: Vec<bool>, regions: [(u32, u32); 3]) -> bool {
        // CodexAstraUlt: A restored bitmap must fit the already resolved title
        // geometry and quotas; reject it atomically before replacing state.
        let Some(used) = self.allocation_usage(&allocated, regions) else { return false; };
        self.allocated = allocated;
        self.used = used;
        true
    }

    // CodexAstraUlt: State loading checks compatibility before replacing live
    // RAM. Keep one validator for preflight and the eventual bitmap update.
    fn allocation_usage(&self, allocated: &[bool], regions: [(u32, u32); 3]) -> Option<[u32; 3]> {
        if allocated.len() != self.allocated.len() || regions != self.regions { return None; }
        let used = regions.map(|(start, count)|
            allocated[start as usize..(start + count) as usize].iter().filter(|&&page| page).count() as u32 * PAGE_SIZE);
        (!used.iter().zip(self.limits).any(|(&used, limit)| used > limit)).then_some(used)
    }

    pub fn allocation_fits(&self, allocated: &[bool], regions: [(u32, u32); 3]) -> bool {
        self.allocation_usage(allocated, regions).is_some()
    }

    pub fn contains_range(&self, paddr: u32, size: u32) -> bool {
        let end = u64::from(paddr) + u64::from(size);
        [(VRAM_PADDR, self.vram.len()), (DSP_RAM_PADDR, self.dsp_ram.len()),
            (AXI_WRAM_PADDR, self.axi_wram.len()), (FCRAM_PADDR, self.fcram.len())]
            .into_iter().any(|(base, len)| paddr >= base && end <= u64::from(base) + len as u64)
    }

    pub fn host_slice_mut(&mut self, paddr: u32, size: u32) -> Option<&mut [u8]> {
        // CodexAstraUlt: Both heap and fenced FCRAM expose the same bounded
        // slice; the kernel still protects fenced bytes from physical aliases.
        let (base, store): (u32, &mut [u8]) = match paddr {
            p if (VRAM_PADDR..VRAM_PADDR + VRAM_SIZE).contains(&p) => (VRAM_PADDR, &mut self.vram),
            p if (DSP_RAM_PADDR..DSP_RAM_PADDR + DSP_RAM_SIZE).contains(&p) => {
                (DSP_RAM_PADDR, &mut self.dsp_ram)
            }
            p if (AXI_WRAM_PADDR..AXI_WRAM_PADDR + AXI_WRAM_SIZE).contains(&p) => {
                (AXI_WRAM_PADDR, &mut self.axi_wram)
            }
            p if p >= FCRAM_PADDR => (FCRAM_PADDR, &mut self.fcram),
            _ => return None,
        };
        let offset = (paddr - base) as usize;
        let end = offset.checked_add(size as usize)?;
        store.get_mut(offset..end)
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn allocates_contiguously_and_frees() {
        let mut phys = PhysicalMemory::new(false, 64 * 1024 * 1024);
        let a = phys.allocate(MemoryRegion::Application, 0x4000).unwrap();
        let b = phys.allocate(MemoryRegion::Application, 0x1000).unwrap();
        assert_eq!(a.addr, FCRAM_PADDR);
        assert_eq!(a.size, 0x4000);
        assert_eq!(b.addr, FCRAM_PADDR + 0x4000);

        assert_eq!(phys.region_used(MemoryRegion::Application), 0x5000);
        phys.free(a);
        assert_eq!(phys.region_used(MemoryRegion::Application), 0x1000);

        // the freed hole is reused.
        let c = phys.allocate(MemoryRegion::Application, 0x2000).unwrap();
        assert_eq!(c.addr, FCRAM_PADDR);
    }

    #[test]
    fn the_top_and_the_bottom_fill_toward_each_other() {
        let mut phys = PhysicalMemory::new(false, 0x8000);
        let code = phys.allocate_top(MemoryRegion::Application, 0x2000).unwrap();
        let heap = phys.allocate_top(MemoryRegion::Application, 0x3000).unwrap();
        assert_eq!(code.addr, FCRAM_PADDR + 0x6000);
        assert_eq!(heap.addr, FCRAM_PADDR + 0x3000);
        // the linear heap still starts where the region does
        let linear = phys.allocate(MemoryRegion::Application, 0x1000).unwrap();
        assert_eq!(linear.addr, FCRAM_PADDR);
        assert!(phys.allocate_top(MemoryRegion::Application, 0x3000).is_none());
        assert_eq!(phys.allocate_top(MemoryRegion::Application, 0x2000).unwrap().addr, FCRAM_PADDR + 0x1000);
    }

    #[test]
    fn refuses_to_overcommit() {
        let mut phys = PhysicalMemory::new(false, 0x4000);
        assert!(phys.allocate(MemoryRegion::Application, 0x4000).is_some());
        assert!(phys.allocate(MemoryRegion::Application, 0x1000).is_none());
    }

    #[test]
    fn regions_do_not_overlap() {
        let phys = PhysicalMemory::new(false, 64 * 1024 * 1024);
        assert_eq!(phys.region_size(MemoryRegion::Application), 64 << 20);
        // CodexAstraUlt: Production Old-model geometry reserves a 20 MiB Base.
        assert_eq!(phys.region_size(MemoryRegion::System), 44 << 20);
        assert_eq!(phys.region_size(MemoryRegion::Base), 20 << 20);
    }
}
