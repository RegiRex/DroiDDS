//! CodexAstraUlt: Fixed host observations at transfer boundaries, not guest state.

use std::time::Duration;

/// CodexAstraUlt: Hardware and software phases are subsets of `wall`; their
/// enclosing GSP/SVC timers already include this work. Hardware time includes
/// reconciliation, command recording, captures and any submission waits.
#[derive(Debug, Default, Clone, Copy, PartialEq, Eq)]
pub struct DisplayTransferDiagnostics {
    pub calls: u64,
    pub wall: Duration,
    pub hardware_attempts: u64,
    pub hardware_accepted: u64,
    /// CodexAstraUlt: Declined or errored hardware attempts that continue on
    /// the existing software route; this is not a software raster fallback.
    pub hardware_fallbacks: u64,
    /// CodexAstraUlt: Errors returned by the hardware transfer attempt only;
    /// existing sync_memory logged failures are outside this count. This does
    /// not replace the renderer's separate failure diagnostics.
    pub hardware_errors: u64,
    pub hardware_tiled: u64,
    pub hardware_linear: u64,
    pub hardware_wall: Duration,
    pub software_calls: u64,
    pub software_empty: u64,
    pub input_sync_wall: Duration,
    pub output_sync_wall: Duration,
    pub software_copy_wall: Duration,
}

/// CodexAstraUlt: Texture copying keeps its original read/write ordering.
/// Synchronization and byte-copy phases are disjoint subsets of `wall`, not
/// additional core or GPU execution time; an empty request still counts.
#[derive(Debug, Default, Clone, Copy, PartialEq, Eq)]
pub struct TextureCopyDiagnostics {
    pub calls: u64,
    pub contiguous_calls: u64,
    pub strided_calls: u64,
    pub wall: Duration,
    pub input_sync_wall: Duration,
    pub output_sync_wall: Duration,
    pub copy_wall: Duration,
}

/// CodexAstraUlt: Inline storage stays constant across requests. No addresses,
/// format histories, private data or per-pixel timing enter these observations.
#[derive(Debug, Default, Clone, Copy, PartialEq, Eq)]
pub struct TransferProcessingDiagnostics {
    pub display: DisplayTransferDiagnostics,
    pub texture: TextureCopyDiagnostics,
}
