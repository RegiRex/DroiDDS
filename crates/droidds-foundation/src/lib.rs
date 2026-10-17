//! CodexAstraUlt: Share the same small synthetic CPU oracle between Linux and
//! Android. This library has no title parser, HLE, renderer or Android compiler.

pub mod fixtures;
pub mod libraries;
pub mod memory;
pub mod runner;

// CodexAstraUlt: Production of C sources is a host-only dependency; target
// runtime builds must select default-features = false.
#[cfg(feature = "host")]
pub mod generator;
