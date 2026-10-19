//! CodexAstraUlt: One origin/entry gate serves both freshly compiled Linux
//! fixtures and packaged Android fixtures. Native libraries remain trusted code;
//! metadata checks do not sandbox arbitrary or hostile shared libraries.

use crate::fixtures::Fixture;
use crate::memory;
use recomp_abi::{Code, Library};
use std::path::Path;

// CodexAstraUlt: Only this origin-checked owner exposes entry lookup. The raw
// native handle cannot escape into a dispatcher that omits freshness checks.
// This deliberately small immutable-text policy is not a CRO lifetime manager.
pub struct CheckedLibrary {
    library: Library,
    text: Vec<u8>,
}

impl CheckedLibrary {
    // CodexAstraUlt: Protection follows the load-verified owner, not mutable
    // fixture metadata supplied later to a dispatch call.
    pub fn protect(&self, memory: &mut memory::Memory) {
        memory.protect_text(self.text.len());
    }

    pub fn unchanged(&self, memory: &memory::Memory) -> bool {
        let start = memory::START as usize;
        memory.bytes.get(start..start + self.text.len()) == Some(self.text.as_slice())
    }

    pub fn lookup(&self, memory: &memory::Memory, address: u32) -> Option<Code> {
        self.unchanged(memory)
            .then(|| self.library.lookup(address))
            .flatten()
    }
}

pub fn open_fixture(fixture: &Fixture, path: &Path) -> Result<CheckedLibrary, String> {
    let mut library = Library::open(path)?;
    if library.generation() != recomp_abi::GENERATION
        || library
            .origins(0)
            .is_none_or(|origins| origins.pieces().is_empty() || origins.functions().is_empty())
    {
        return Err("generated library generation/origin metadata is missing or wrong".to_owned());
    }
    // CodexAstraUlt: A malformed origin extent cannot index outside our bounded
    // fixture image. The loader's own native metadata contract still requires a
    // library built from our known sources, not an untrusted plugin.
    let mut invalid_origin = false;
    let stale = library.check(0, 0, |address, destination| {
        let start = address as usize;
        let source = start
            .checked_add(destination.len())
            .and_then(|end| fixture.memory.bytes.get(start..end));
        if let Some(source) = source {
            destination.copy_from_slice(source);
        } else {
            invalid_origin = true;
            destination.fill(0);
        }
    });
    if invalid_origin
        || stale != 0
        || library
            .lookup(fixture.cpu.regs[15] | u32::from(fixture.cpu.cpsr.thumb))
            .is_none()
    {
        return Err(format!(
            "{}: invalid origin, missing or stale initial native entry",
            fixture.name
        ));
    }
    if fixture
        .thumb_entry
        .is_some_and(|address| library.lookup(address).is_none())
    {
        return Err(format!(
            "{}: expected Thumb native entry is missing",
            fixture.name
        ));
    }
    if library.lookup(memory::EXTRA).is_some() {
        return Err("deliberately absent entry unexpectedly has native code".to_owned());
    }
    if fixture
        .memory
        .bytes
        .get(memory::START as usize..memory::START as usize + fixture.text.len())
        != Some(fixture.text.as_slice())
    {
        return Err("fixture text differs from its original source bytes".to_owned());
    }
    Ok(CheckedLibrary {
        library,
        text: fixture.text.clone(),
    })
}

// CodexAstraUlt: Execute real negative paths against the packaged original
// library. A changed origin fails loading, a post-load change cannot call native
// code, and a guest store into executable text leaves it immutable and fails.
pub fn safety_controls(fixture: &Fixture, path: &Path) -> Result<serde_json::Value, String> {
    use crate::runner::{native, Stop};
    use serde_json::json;
    let mut stale = fixture.clone();
    stale.memory.bytes[memory::START as usize] ^= 1;
    let rejection = match open_fixture(&stale, path) {
        Ok(_) => return Err("stale source origin unexpectedly loaded".to_owned()),
        Err(error) if error.contains("stale initial native entry") => error,
        Err(error) => {
            return Err(format!(
                "stale origin rejected for unrelated reason: {error}"
            ))
        }
    };
    let library = open_fixture(fixture, path)?;
    let changed = native(&stale, &library);
    if changed.stop != Stop::CodeChanged
        || changed.counts.native_calls != 0
        || changed.counts.fallback_steps != 0
        || changed.state.memory != stale.memory.bytes
    {
        return Err(
            "post-load executable change reached execution or failed for another reason".to_owned(),
        );
    }
    let mut write_attempt = fixture.clone();
    write_attempt.cpu.regs[4] = memory::START;
    let blocked = native(&write_attempt, &library);
    if blocked.stop != Stop::CodeWriteRejected
        || blocked.counts.native_calls != 1
        || blocked.counts.code_write_rejections != 2
        || blocked.state.memory != fixture.memory.bytes
    {
        return Err(format!(
            "guest executable-write policy did not stop safely: {:?}, {:?}",
            blocked.stop, blocked.counts
        ));
    }
    Ok(json!({
        "status": "passed",
        "policy": "immutable_fixture_text",
        "controls": [
            {"name": "stale_origin_rejected", "status": "passed", "rejection": rejection},
            {"name": "changed_code_before_dispatch_rejected", "status": "passed", "native_calls": 0,
             "fallback_steps": 0, "guest_memory_unchanged": true},
            {"name": "guest_executable_write_rejected", "status": "passed", "native_calls": 1,
             "rejected_writes": 2, "guest_memory_unchanged": true}
        ],
        "limitations": ["Single-threaded immutable fixture text only; no CRO unloading, remapping or concurrent writer support.",
                        "Trusted native libraries only; origin hashes do not sandbox native plugins."]
    }))
}
