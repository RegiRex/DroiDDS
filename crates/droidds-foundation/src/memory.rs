//! CodexAstraUlt: A small checked guest bus used by both engines. Native accesses
//! intentionally use callbacks; direct-page optimization is outside this proof.

use zakuro_cpu::Bus;

pub const START: u32 = 0x1000;
pub const DATA: u32 = 0x4000;
pub const EXTRA: u32 = 0x8000;

#[derive(Clone)]
pub struct Memory {
    pub bytes: Vec<u8>,
    pub faults: u64,
}

// CodexAstraUlt: The shared public fixture bus has one deterministic initial
// state; Default and explicit construction must preserve identical test bytes.
impl Default for Memory {
    fn default() -> Self {
        Self::new()
    }
}

impl Memory {
    // CodexAstraUlt: Deterministic nonzero backing lets full-image comparison
    // detect unintended stores outside the expected output, including zeroing.
    pub fn new() -> Self {
        Self {
            bytes: (0..0x1_0000).map(|index| (index % 251) as u8).collect(),
            faults: 0,
        }
    }

    // CodexAstraUlt: Loading fixture bytes bypasses write permissions before
    // execution; guest writes remain limited to the data and stack windows.
    pub fn load(&mut self, address: u32, bytes: &[u8]) {
        self.bytes[address as usize..address as usize + bytes.len()].copy_from_slice(bytes);
    }
}

// CodexAstraUlt: Callbacks never panic for bad guest addresses. Any fault makes
// validation fail even if both engines encounter the same invalid access.
impl Bus for Memory {
    fn read8(&mut self, address: u32) -> u8 {
        match self.bytes.get(address as usize) {
            Some(value) => *value,
            None => {
                self.faults = self.faults.saturating_add(1);
                0
            }
        }
    }

    fn read16(&mut self, address: u32) -> u16 {
        u16::from_le_bytes(std::array::from_fn(|offset| {
            self.read8(address.wrapping_add(offset as u32))
        }))
    }

    fn read32(&mut self, address: u32) -> u32 {
        u32::from_le_bytes(std::array::from_fn(|offset| {
            self.read8(address.wrapping_add(offset as u32))
        }))
    }

    fn write8(&mut self, address: u32, value: u8) {
        if (DATA..DATA + 0x1000).contains(&address) || (0xe000..0xf000).contains(&address) {
            self.bytes[address as usize] = value;
        } else {
            self.faults = self.faults.saturating_add(1);
        }
    }

    fn write16(&mut self, address: u32, value: u16) {
        for (offset, byte) in value.to_le_bytes().into_iter().enumerate() {
            self.write8(address.wrapping_add(offset as u32), byte);
        }
    }

    fn write32(&mut self, address: u32, value: u32) {
        for (offset, byte) in value.to_le_bytes().into_iter().enumerate() {
            self.write8(address.wrapping_add(offset as u32), byte);
        }
    }
}
