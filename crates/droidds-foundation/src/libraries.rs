//! CodexAstraUlt: One origin/entry gate serves both freshly compiled Linux
//! fixtures and packaged Android fixtures. Native libraries remain trusted code;
//! metadata checks do not sandbox arbitrary or hostile shared libraries.

use crate::fixtures::Fixture;
use crate::memory;
use recomp_abi::Library;
use std::path::Path;

pub fn open_fixture(fixture: &Fixture, path: &Path) -> Result<Library, String> {
    let mut library = Library::open(path)?;
    if library.generation() != recomp_abi::GENERATION || library.origins(0).is_none() {
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
    Ok(library)
}
