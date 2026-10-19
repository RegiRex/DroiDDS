//! CodexAstraUlt: Resolve guest memory geometry and application commitment before
//! allocating the machine. Region sizes are format/runtime facts corroborated in
//! the integration audit; no Citra/Azahar or Luma implementation is imported.

use zakuro_common::memory_map::{fcram_size, PAGE_SIZE};
use zakuro_fs::SystemMode;

const MIB: u32 = 1024 * 1024;

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub struct MemoryLayout {
    pub(crate) regions: [u32; 3],
    pub(crate) application_limit: u32,
    pub(crate) reported_mode: u32,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, thiserror::Error)]
pub enum LayoutError {
    #[error("unsupported Old 3DS memory mode {0}")]
    OldMode(u8),
    #[error("unsupported New 3DS memory mode {0}")]
    NewMode(u8),
    #[error("Old 3DS memory mode {0} is not supported for a New 3DS legacy application")]
    LegacyMode(u8),
}

impl MemoryLayout {
    /// CodexAstraUlt: New-model legacy applications keep the production physical
    /// split, with the separate PM commitment limit. Modes 4/5 are not silently
    /// treated as working New-model application configurations: the independent
    /// Luma PM reference assigns them zero, so integration rejects them clearly.
    pub fn resolve(new3ds: bool, old: SystemMode, new: u8) -> Result<Self, LayoutError> {
        let old_app = old
            .application_memory()
            .ok_or(LayoutError::OldMode(old.raw()))?;
        if !new3ds {
            return Ok(Self {
                regions: [old_app, 108 * MIB - old_app, 20 * MIB],
                application_limit: old_app,
                reported_mode: u32::from(old.raw()),
            });
        }
        let (regions, application_limit, reported_mode) = match new {
            0 => {
                if !matches!(old, SystemMode::Prod | SystemMode::Dev1 | SystemMode::Dev2) {
                    return Err(LayoutError::LegacyMode(old.raw()));
                }
                ([124 * MIB, 100 * MIB, 32 * MIB], old_app, 6)
            }
            1 => ([124 * MIB, 100 * MIB, 32 * MIB], 124 * MIB, 6),
            2 => ([178 * MIB, 46 * MIB, 32 * MIB], 178 * MIB, 7),
            value => return Err(LayoutError::NewMode(value)),
        };
        Ok(Self {
            regions,
            application_limit,
            reported_mode,
        })
    }

    /// CodexAstraUlt: Retain the existing explicit-size constructors for unit
    /// fixtures. Production title loading uses resolve, never this inference.
    pub(crate) fn for_application(new3ds: bool, application: u32) -> Self {
        assert_eq!(
            application % PAGE_SIZE,
            0,
            "application memory must be page aligned"
        );
        let base = if new3ds { 32 * MIB } else { 20 * MIB };
        let total = fcram_size(new3ds);
        assert!(
            application <= total - base,
            "application memory leaves no base region"
        );
        Self {
            regions: [application, total - application - base, base],
            application_limit: application,
            reported_mode: if new3ds { 6 } else { 0 },
        }
    }

    pub fn total_bytes(self) -> u32 {
        self.regions.iter().sum()
    }
    pub fn application_limit(self) -> u32 {
        self.application_limit
    }
    pub fn reported_mode(self) -> u32 {
        self.reported_mode
    }
}
