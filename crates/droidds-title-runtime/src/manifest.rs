//! CodexAstraUlt: A bounded installer manifest binds input and native code to
//! the same prepared title. Neither filenames nor title IDs alone admit code.

use serde::Deserialize;
use sha2::{Digest, Sha256};
use std::collections::BTreeSet;

pub(crate) const MAX_MANIFEST: usize = 1024 * 1024;
pub(crate) const MAX_COMPONENT: u64 = 64 * 1024 * 1024;

#[derive(Debug, Deserialize)]
#[serde(deny_unknown_fields)]
pub(crate) struct Identity {
    pub bytes: u64,
    pub sha256: String,
}

#[derive(Debug, Deserialize)]
#[serde(deny_unknown_fields)]
pub(crate) struct Native {
    pub file: String,
    pub bytes: u64,
    pub sha256: String,
}

#[derive(Debug, Deserialize)]
#[serde(deny_unknown_fields)]
pub(crate) struct Segment {
    pub name: String,
    pub address: u32,
    pub offset: u64,
    pub size: u64,
    pub mapped_bytes: u64,
    pub sha256: String,
    pub hash_scope: String,
}

#[derive(Debug, Deserialize)]
#[serde(deny_unknown_fields)]
pub(crate) struct Component {
    pub kind: String,
    pub path: String,
    pub source_path: Option<String>,
    pub module_name: Option<String>,
    pub bytes: u64,
    pub sha256: String,
}

#[derive(Debug, Deserialize)]
#[serde(deny_unknown_fields)]
pub(crate) struct Prepared {
    pub container: String,
    pub ncch_format_version: u16,
    pub remaster_version: u16,
    pub cia_title_version: Option<u16>,
    pub bss_size: u32,
    pub segments: Vec<Segment>,
    pub components: Vec<Component>,
}

#[derive(Debug, Deserialize)]
#[serde(deny_unknown_fields)]
pub(crate) struct Manifest {
    pub schema_version: u32,
    pub kind: String,
    pub program_id: String,
    pub input: Identity,
    pub native: Native,
    pub abi: u32,
    pub generation: u32,
    pub prepared: Prepared,
}

pub(crate) fn sha256(bytes: &[u8]) -> String {
    format!("{:x}", Sha256::digest(bytes))
}

fn hex(value: &str, length: usize) -> bool {
    value.len() == length
        && value
            .bytes()
            .all(|byte| byte.is_ascii_digit() || (b'a'..=b'f').contains(&byte))
}

fn relative(value: &str) -> bool {
    !value.is_empty()
        && value.len() <= 4096
        && !value.contains(['\\', '\0'])
        && value
            .split('/')
            .all(|part| !matches!(part, "" | "." | ".."))
}

impl Manifest {
    // CodexAstraUlt: Exact typed records reject duplicate/unknown fields before
    // any filesystem or native operation; finite lengths bound component work.
    pub fn parse(bytes: &[u8]) -> Result<Self, String> {
        if bytes.is_empty() || bytes.len() > MAX_MANIFEST {
            return Err("title_manifest_size_invalid".into());
        }
        let manifest: Self =
            serde_json::from_slice(bytes).map_err(|_| "title_manifest_invalid_json")?;
        manifest.validate()?;
        Ok(manifest)
    }

    fn validate(&self) -> Result<(), String> {
        if self.schema_version != 1
            || self.kind != "droidds_android_title"
            || self.abi != recomp_abi::ABI
            || self.generation != recomp_abi::GENERATION
            || !hex(&self.program_id, 16)
            || matches!(&self.program_id[..8], "0004000e" | "0004008c")
            || !(1..=8 * 1024 * 1024 * 1024).contains(&self.input.bytes)
            || !hex(&self.input.sha256, 64)
            || self.native.file != "libdroidds_title.so"
            || !(1..=512 * 1024 * 1024).contains(&self.native.bytes)
            || !hex(&self.native.sha256, 64)
        {
            return Err("title_manifest_identity_invalid".into());
        }
        let prepared = &self.prepared;
        if !matches!(prepared.container.as_str(), "ncch" | "ncsd" | "cia")
            || (prepared.container == "cia") != prepared.cia_title_version.is_some()
            || prepared.segments.len() != 3
            || !(3..=4099).contains(&prepared.components.len())
        {
            return Err("title_manifest_layout_invalid".into());
        }
        let mut offset = 0;
        for (segment, name) in prepared.segments.iter().zip(["text", "rodata", "data"]) {
            if segment.name != name
                || segment.offset != offset
                || segment.mapped_bytes > MAX_COMPONENT
                || segment.mapped_bytes % 4096 != 0
                || segment.address % 4096 != 0
                || segment.size > segment.mapped_bytes
                || u64::from(segment.address) + segment.mapped_bytes > 1u64 << 32
                || !hex(&segment.sha256, 64)
                || segment.hash_scope != "logical_segment_bytes"
            {
                return Err("title_manifest_segment_invalid".into());
            }
            offset += segment.mapped_bytes;
        }
        if prepared.segments[0].size == 0 {
            return Err("title_manifest_text_missing".into());
        }
        let (mut paths, mut names, mut required) =
            (BTreeSet::new(), BTreeSet::new(), BTreeSet::new());
        let mut module_bytes = 0;
        for component in &prepared.components {
            if !(1..=MAX_COMPONENT).contains(&component.bytes)
                || !hex(&component.sha256, 64)
                || !relative(&component.path)
                || !component.path.starts_with("identity/")
                || !paths.insert(&component.path)
            {
                return Err("title_manifest_component_invalid".into());
            }
            match component.kind.as_str() {
                "ncch_header" | "exheader" | "decompressed_code" => {
                    let (path, size) = match component.kind.as_str() {
                        "ncch_header" => ("identity/ncch-header.bin", Some(512)),
                        "exheader" => ("identity/exheader.bin", Some(1024)),
                        _ => ("identity/code.bin", None),
                    };
                    if component.path != path
                        || size.is_some_and(|size| component.bytes != size)
                        || component.source_path.is_some()
                        || component.module_name.is_some()
                        || !required.insert(component.kind.as_str())
                    {
                        return Err("title_manifest_base_component_invalid".into());
                    }
                }
                "cro" | "static_crs" => {
                    if !component.source_path.as_deref().is_some_and(relative)
                        || !component.module_name.as_deref().is_some_and(|name| {
                            !name.is_empty() && name.len() <= 4096 && !name.contains('\0')
                        })
                        || !names.insert(component.module_name.as_deref().unwrap())
                    {
                        return Err("title_manifest_module_invalid".into());
                    }
                    module_bytes += component.bytes;
                }
                _ => return Err("title_manifest_component_kind_invalid".into()),
            }
        }
        if required.len() != 3 || module_bytes > 256 * 1024 * 1024 {
            return Err("title_manifest_component_coverage_invalid".into());
        }
        Ok(())
    }
}
