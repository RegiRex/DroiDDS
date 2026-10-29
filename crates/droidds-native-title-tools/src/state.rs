//! CodexAstraUlt: Finite checkpoint fingerprints compare observed guest state.
//! FNV-1a is explicitly diagnostic; SHA-256 identity remains the parent's job.

use recomp_abi::CodeHash;
use serde_json::{json, Value};
use zakuro_core::{memory::MemoryRegion, System};

#[derive(Default)]
pub(crate) struct Audio {
    pairs: u64,
    nonzero: u64,
    hash: CodeHash,
}

impl Audio {
    // CodexAstraUlt: Consume each sample once at frame/checkpoint/end boundaries;
    // cumulative hashes preserve stream order without retaining private PCM.
    pub(crate) fn drain(&mut self, system: &mut System) {
        let pcm = system.take_audio();
        self.pairs = self.pairs.saturating_add(pcm.len() as u64);
        for sample in pcm {
            self.nonzero += u64::from(sample != [0, 0]);
            self.hash.add(&sample[0].to_le_bytes());
            self.hash.add(&sample[1].to_le_bytes());
        }
    }
}

fn hash(bytes: &[u8]) -> String {
    let mut hash = CodeHash::default();
    hash.add(bytes);
    format!("{:016x}", hash.value())
}

// CodexAstraUlt: Hash mappings and allocation metadata without reading unmapped
// guest addresses or including process-dependent host pointers in equality.
fn memory_state(system: &System) -> Value {
    let mut map = CodeHash::default();
    for mapping in system.memory.mappings() {
        for word in [
            mapping.base,
            mapping.size,
            mapping.paddr,
            mapping.permission.bits(),
            mapping.state as u32,
        ] {
            map.add(&word.to_le_bytes());
        }
    }
    let (allocation, regions) = system.memory.phys.allocation();
    let mut allocated = CodeHash::default();
    for bit in allocation {
        allocated.add(&[u8::from(bit)]);
    }
    json!({
        "fcram_fnv1a64":hash(&system.memory.phys.fcram),
        "vram_fnv1a64":hash(&system.memory.phys.vram),
        "dsp_ram_fnv1a64":hash(&system.memory.phys.dsp_ram),
        "axi_wram_fnv1a64":hash(&system.memory.phys.axi_wram),
        "mapping_fnv1a64":format!("{:016x}",map.value()),
        "allocation_fnv1a64":format!("{:016x}",allocated.value()),"allocation_regions":regions,
        "region_used_bytes":([MemoryRegion::Application,MemoryRegion::System,MemoryRegion::Base]
            .map(|region|system.memory.phys.region_used(region)))
    })
}

// CodexAstraUlt: Route-dependent dispatch/instruction counters stay outside this
// state object, so equal guest-cycle checkpoints can be compared meaningfully.
pub(crate) fn capture(system: &System, audio: &Audio) -> Value {
    json!({
        "cycles":system.cpu.cycles,"frames":system.frames,"guest_exited":system.exited,
        "registers":system.cpu.regs,"cpsr":system.cpu.cpsr.to_bits(),
        "vfp_registers":system.cpu.vfp.regs,"fpscr":system.cpu.vfp.fpscr,"fpexc":system.cpu.vfp.fpexc,
        "tls":system.cpu.cp15.thread_id_ro,"exclusive_address":system.cpu.exclusive_addr,
        "current_thread":system.kernel.current_thread,
        "thread_guest_id":system.kernel.current_thread.and_then(|id|system.kernel.threads.get(id as usize).map(|thread|thread.guest_id)),
        "reschedule_pending":system.kernel.reschedule_pending,"all_blocked":system.kernel.all_blocked,
        "next_kernel_event":system.kernel.next_event(),"memory":memory_state(system),
        "graphics":{"command_lists":system.gpu.command_lists,"draw_calls":system.gpu.draw_calls,"vertices_drawn":system.gpu.vertices_drawn},
        "audio":{"pcm_pairs":audio.pairs,"nonzero_pairs":audio.nonzero,"pcm_fnv1a64":format!("{:016x}",audio.hash.value())}
    })
}
