//! CodexAstraUlt: A sealed descriptor request is a local coordinator capability,
//! not an authentication or sandbox boundary for arbitrary native plugins.

use serde::Deserialize;
use serde_json::Value;
use std::{
    collections::BTreeSet,
    fs::File,
    io::Read,
    os::fd::{AsRawFd, FromRawFd},
    path::PathBuf,
};

pub const REQUEST_LIMIT: u64 = 8 * 1024 * 1024;
pub const LIBRARY_LIMIT: u64 = 512 * 1024 * 1024;
pub const COMPONENT_LIMIT: u64 = 64 * 1024 * 1024;
pub const BUNDLE_LIMIT: u64 = 320 * 1024 * 1024 + 1536;

// CodexAstraUlt: Typed deny-unknown records reject duplicate fields, noninteger
// numbers and unexpected options before any loader or native library executes.
#[derive(Clone, Debug, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct Input {
    pub bytes: u64,
    pub sha256: String,
    pub snapshot_path: PathBuf,
}

#[derive(Clone, Debug, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct Library {
    pub bytes: u64,
    pub sha256: String,
    pub descriptor: i32,
}

#[derive(Clone, Debug, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct Component {
    pub path: String,
    pub kind: String,
    pub bytes: u64,
    pub sha256: String,
    pub offset: u64,
    pub source_path: Option<String>,
    pub module_name: Option<String>,
}

#[derive(Clone, Debug, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct Bundle {
    pub bytes: u64,
    pub sha256: String,
    pub descriptor: i32,
    pub components: Vec<Component>,
}

#[derive(Clone, Debug, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct Segment {
    pub name: String,
    pub address: u32,
    pub offset: u64,
    pub size: u64,
    pub mapped_bytes: u64,
    pub sha256: String,
    pub hash_scope: String,
}

#[derive(Clone, Debug, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct Prepared {
    pub program_id: String,
    pub segments: Vec<Segment>,
    pub bss_size: u32,
    pub ncch_format_version: u16,
    pub remaster_version: u16,
    pub container: String,
    pub cia_title_version: Option<u16>,
}

#[derive(Clone, Debug, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct Limits {
    pub max_steps: u64,
    pub max_cycles: u64,
    pub max_frames: u64,
    pub max_seconds: u64,
}

#[derive(Clone, Debug, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct Request {
    pub schema_version: u32,
    pub kind: String,
    pub abi: u32,
    pub generation: u32,
    pub preparation_sha256: String,
    pub contract_sha256: String,
    pub input: Input,
    pub library: Library,
    pub identity_bundle: Bundle,
    pub prepared: Prepared,
    pub route: String,
    pub limits: Limits,
    pub model: String,
    pub static_table_audit: Value,
}

// CodexAstraUlt: Hashes here identify the coordinator's already checked bytes;
// the worker's independent boundary is exact runtime/identity-bundle equality.
fn hex(value: &str, count: usize) -> bool {
    value.len() == count
        && value
            .bytes()
            .all(|v| v.is_ascii_digit() || (b'a'..=b'f').contains(&v))
}

fn relative(value: &str) -> bool {
    !value.is_empty()
        && value.len() <= 4096
        && !value.starts_with('/')
        && !value.contains('\\')
        && !value.contains('\0')
        && value
            .split('/')
            .all(|part| !matches!(part, "" | "." | ".."))
}

impl Request {
    // CodexAstraUlt: Explicit finite admission preserves the parent's recorded
    // limits and prevents a changed request from creating an unbounded worker.
    pub fn validate(&self, request_descriptor: i32) -> Result<(), String> {
        if self.schema_version != 1
            || self.kind != "droidds_private_native_run_request"
            || self.abi != recomp_abi::ABI
            || self.generation != recomp_abi::GENERATION
            || !hex(&self.preparation_sha256, 64)
            || !hex(&self.contract_sha256, 64)
            || !hex(&self.input.sha256, 64)
            || !hex(&self.library.sha256, 64)
            || !hex(&self.identity_bundle.sha256, 64)
            || !matches!(self.route.as_str(), "native" | "interpreter")
            || !matches!(self.model.as_str(), "old" | "new")
        {
            return Err("invalid_native_request_identity".into());
        }
        if !(1..=8 * 1024 * 1024 * 1024).contains(&self.input.bytes)
            || !self.input.snapshot_path.is_absolute()
            || !(1..=LIBRARY_LIMIT).contains(&self.library.bytes)
            || !(1..=BUNDLE_LIMIT).contains(&self.identity_bundle.bytes)
            || request_descriptor < 3
            || self.library.descriptor < 3
            || self.identity_bundle.descriptor < 3
            || BTreeSet::from([
                request_descriptor,
                self.library.descriptor,
                self.identity_bundle.descriptor,
            ])
            .len()
                != 3
        {
            return Err("invalid_native_request_descriptors".into());
        }
        for (name, value, maximum) in [
            ("steps", self.limits.max_steps, 1_000_000_000),
            ("cycles", self.limits.max_cycles, 26_811_185_600),
            ("frames", self.limits.max_frames, 6000),
            ("seconds", self.limits.max_seconds, 300),
        ] {
            if value == 0 || value > maximum {
                return Err(format!("invalid_native_limit_{name}"));
            }
        }
        if !self.static_table_audit.is_object()
            || self.static_table_audit.get("runtime_tables_validated") != Some(&Value::Bool(true))
            || self.static_table_audit.get("library_loaded") != Some(&Value::Bool(false))
        {
            return Err("missing_parent_static_table_admission".into());
        }
        let prepared = &self.prepared;
        if !hex(&prepared.program_id, 16)
            || matches!(&prepared.program_id[..8], "0004000e" | "0004008c")
            || !matches!(prepared.container.as_str(), "ncch" | "ncsd" | "cia")
            || (prepared.container == "cia") != prepared.cia_title_version.is_some()
            || prepared.segments.len() != 3
        {
            return Err("invalid_prepared_title_identity".into());
        }
        let mut segment_offset = 0;
        for (segment, name) in prepared.segments.iter().zip(["text", "rodata", "data"]) {
            if segment.name != name
                || segment.offset != segment_offset
                || segment.mapped_bytes > COMPONENT_LIMIT
                || segment.mapped_bytes % 4096 != 0
                || segment.size > segment.mapped_bytes
                || !hex(&segment.sha256, 64)
                || segment.hash_scope != "logical_segment_bytes"
                || u64::from(segment.address) + segment.mapped_bytes > 1u64 << 32
            {
                return Err("invalid_prepared_segment".into());
            }
            segment_offset += segment.mapped_bytes;
        }
        if prepared.segments[0].mapped_bytes == 0 {
            return Err("missing_executable_segment".into());
        }
        if !(3..=4099).contains(&self.identity_bundle.components.len()) {
            return Err("invalid_identity_component_count".into());
        }
        let mut ranges = Vec::new();
        let (mut paths, mut names, mut required) =
            (BTreeSet::new(), BTreeSet::new(), BTreeSet::new());
        let mut module_bytes = 0u64;
        for component in &self.identity_bundle.components {
            if !(1..=COMPONENT_LIMIT).contains(&component.bytes)
                || !hex(&component.sha256, 64)
                || !relative(&component.path)
                || !component.path.starts_with("identity/")
                || !paths.insert(&component.path)
            {
                return Err("invalid_identity_component".into());
            }
            let end = component
                .offset
                .checked_add(component.bytes)
                .ok_or("identity_component_overflow")?;
            if end > self.identity_bundle.bytes {
                return Err("identity_component_out_of_bounds".into());
            }
            ranges.push((component.offset, end));
            match component.kind.as_str() {
                "ncch_header" | "exheader" | "decompressed_code" => {
                    let (path, length) = match component.kind.as_str() {
                        "ncch_header" => ("identity/ncch-header.bin", Some(512)),
                        "exheader" => ("identity/exheader.bin", Some(1024)),
                        _ => ("identity/code.bin", None),
                    };
                    if component.path != path
                        || length.is_some_and(|n| component.bytes != n)
                        || component.source_path.is_some()
                        || component.module_name.is_some()
                        || !required.insert(component.kind.as_str())
                    {
                        return Err("invalid_base_identity_component".into());
                    }
                }
                "cro" | "static_crs" => {
                    if !component.source_path.as_deref().is_some_and(relative)
                        || !component.module_name.as_deref().is_some_and(|name| {
                            !name.is_empty() && name.len() <= 4096 && !name.contains('\0')
                        })
                        || !names.insert(component.module_name.as_deref().unwrap())
                    {
                        return Err("invalid_module_identity_component".into());
                    }
                    module_bytes += component.bytes;
                }
                _ => return Err("unknown_identity_component_kind".into()),
            }
        }
        ranges.sort_unstable();
        let mut end = 0;
        for (start, next) in ranges {
            if start != end {
                return Err("identity_component_gap_or_overlap".into());
            }
            end = next;
        }
        if end != self.identity_bundle.bytes
            || required.len() != 3
            || module_bytes > 256 * 1024 * 1024
        {
            return Err("invalid_identity_bundle_coverage".into());
        }
        Ok(())
    }
}

// CodexAstraUlt: Duplicate inherited descriptors so ownership is explicit. Every
// fd must be a regular, fully sealed Linux memfd with the exact admitted length.
pub struct SealedFile(pub File);

impl SealedFile {
    pub fn open(descriptor: i32, maximum: u64, exact: Option<u64>) -> Result<Self, String> {
        if descriptor < 3 {
            return Err("descriptor_must_not_be_stdio".into());
        }
        #[cfg(not(target_os = "linux"))]
        {
            let _ = (maximum, exact);
            Err("sealed_native_worker_requires_linux".into())
        }
        #[cfg(target_os = "linux")]
        {
            // SAFETY: fcntl duplicates a caller-owned descriptor; the returned
            // descriptor is uniquely owned by File and closed on every path.
            let fd = unsafe { libc::fcntl(descriptor, libc::F_DUPFD_CLOEXEC, 3) };
            if fd < 0 {
                return Err("cannot_duplicate_sealed_descriptor".into());
            }
            let file = unsafe { File::from_raw_fd(fd) };
            let metadata = file
                .metadata()
                .map_err(|_| "sealed_descriptor_stat_failed")?;
            let needed =
                libc::F_SEAL_WRITE | libc::F_SEAL_GROW | libc::F_SEAL_SHRINK | libc::F_SEAL_SEAL;
            // SAFETY: this read-only command inspects the valid owned fd.
            let seals = unsafe { libc::fcntl(fd, libc::F_GET_SEALS) };
            if !metadata.is_file()
                || metadata.len() == 0
                || metadata.len() > maximum
                || exact.is_some_and(|expected| expected != metadata.len())
                || seals < 0
                || seals & needed != needed
            {
                return Err("descriptor_not_fully_sealed_or_wrong_size".into());
            }
            Ok(Self(file))
        }
    }

    pub fn path(&self) -> PathBuf {
        PathBuf::from(format!("/proc/self/fd/{}", self.0.as_raw_fd()))
    }

    pub fn map(&self) -> Result<memmap2::Mmap, String> {
        // SAFETY: complete WRITE/GROW/SHRINK seals prohibit modification or
        // truncation for the lifetime of this readonly map and owned descriptor.
        unsafe { memmap2::Mmap::map(&self.0) }.map_err(|_| "sealed_mapping_failed".into())
    }
}

// CodexAstraUlt: JSON size is bounded by the sealed request before allocation;
// serde's recursive depth guard and typed records remain enabled.
pub fn read(descriptor: i32) -> Result<Request, String> {
    let mut sealed = SealedFile::open(descriptor, REQUEST_LIMIT, None)?;
    use std::io::{Seek, SeekFrom};
    sealed
        .0
        .seek(SeekFrom::Start(0))
        .map_err(|_| "request_seek_failed")?;
    let mut bytes = Vec::new();
    sealed
        .0
        .read_to_end(&mut bytes)
        .map_err(|_| "request_read_failed")?;
    let request: Request =
        serde_json::from_slice(&bytes).map_err(|_| "invalid_native_request_json")?;
    request.validate(descriptor)?;
    Ok(request)
}
