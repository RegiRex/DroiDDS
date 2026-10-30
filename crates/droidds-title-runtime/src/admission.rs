//! CodexAstraUlt: Installer-owned manifest/library and app-private game bytes
//! are checked before native loading. This is not an arbitrary plugin sandbox.

use crate::{
    manifest::{sha256, Manifest},
    OpenOptions,
};
use sha2::{Digest, Sha256};
use std::{
    fs::{self, File},
    io::Read,
    path::{Component, Path},
};
use zakuro_core::{loader, Config, System};

// CodexAstraUlt: Reject symlinks/navigation instead of resolving a caller's
// selected file into an unrelated directory. Missing data directories may be
// created, but existing data is never removed or rewritten by session admission.
fn plain(path: &Path, missing: bool) -> Result<(), String> {
    if !path.is_absolute() {
        return Err("title_path_must_be_absolute".into());
    }
    let mut prefix = std::path::PathBuf::new();
    for part in path.components() {
        if matches!(part, Component::ParentDir | Component::CurDir) {
            return Err("title_path_navigation_rejected".into());
        }
        prefix.push(part);
        match fs::symlink_metadata(&prefix) {
            Ok(metadata) if metadata.file_type().is_symlink() => {
                return Err("title_path_symlink_rejected".into())
            }
            Ok(_) => {}
            Err(error) if missing && error.kind() == std::io::ErrorKind::NotFound => {}
            Err(_) => return Err("title_path_unavailable".into()),
        }
    }
    Ok(())
}

fn file_identity(path: &Path, bytes: u64, digest: &str) -> Result<(), String> {
    plain(path, false)?;
    let mut file = File::open(path).map_err(|_| "title_file_unavailable")?;
    let before = file
        .metadata()
        .map_err(|_| "title_file_metadata_unavailable")?;
    if !before.is_file() || before.len() != bytes {
        return Err("title_file_size_mismatch".into());
    }
    let mut hash = Sha256::new();
    let mut buffer = [0u8; 64 * 1024];
    let mut read = 0;
    loop {
        let count = file
            .read(&mut buffer)
            .map_err(|_| "title_file_read_failed")?;
        if count == 0 {
            break;
        }
        read += count as u64;
        if read > bytes {
            return Err("title_file_changed_during_admission".into());
        }
        hash.update(&buffer[..count]);
    }
    let after = file
        .metadata()
        .map_err(|_| "title_file_metadata_unavailable")?;
    if read != bytes
        || before.len() != after.len()
        || before.modified().ok() != after.modified().ok()
        || format!("{:x}", hash.finalize()) != digest
    {
        return Err("title_file_identity_mismatch".into());
    }
    Ok(())
}

pub(crate) fn load(manifest: &Manifest, options: &OpenOptions<'_>) -> Result<System, String> {
    file_identity(options.input, manifest.input.bytes, &manifest.input.sha256)?;
    preflight_code(options.input, manifest)?;
    plain(options.data_directory, true)?;
    plain(options.native_directory, false)?;
    if !options.native_directory.is_dir()
        || options.data_directory == options.native_directory
        || options.data_directory.starts_with(options.native_directory)
        || options.input.starts_with(options.data_directory)
        || options.native_directory.starts_with(options.data_directory)
    {
        return Err("title_storage_layout_invalid".into());
    }
    // CodexAstraUlt: The base-only package does not silently discover a local
    // code, RomFS or cheat overlay while reusing durable save storage.
    for name in ["mods", "cheats"] {
        if fs::symlink_metadata(options.data_directory.join(name)).is_ok() {
            return Err("title_runtime_overlays_not_supported".into());
        }
    }
    let native = options.native_directory.join(&manifest.native.file);
    if options.native {
        file_identity(&native, manifest.native.bytes, &manifest.native.sha256)?;
    }
    fs::create_dir_all(options.data_directory).map_err(|_| "title_data_directory_unavailable")?;
    plain(options.data_directory, false)?;
    let mut system = loader::load(
        options.input,
        Config {
            data_dir: Some(options.data_directory.to_path_buf()),
            find_recompiled: false,
            recompiled: None,
            linked: None,
            hardware_renderer: false,
            texture_packs: false,
            skip_idle_loops: false,
            strict_diagnostics: true,
            ..Config::default()
        },
    )
    .map_err(|_| "title_loader_rejected")?;
    if system.recompiled.is_some()
        || system.hints.is_some()
        || !system.dlc.is_empty()
        || system.cheats.iter().any(|cheat| cheat.enabled)
        || system.cpu.cycles != 0
        || system.frames != 0
    {
        return Err("title_unexpected_runtime_option".into());
    }
    bind(&mut system, manifest)?;
    if options.native {
        let text = &manifest.prepared.segments[0];
        system
            .memory
            .install_base_code_fence(text.address, text.mapped_bytes as u32)?;
        // CodexAstraUlt: Native code comes only from the immutable package's
        // installer directory. It was statically audited by the title builder;
        // the runtime rechecks bytes before load and origins against mapped RAM.
        file_identity(&native, manifest.native.bytes, &manifest.native.sha256)?;
        let mut library = zakuro_core::recompiled::Library::open(&native)
            .map_err(|_| "title_native_library_rejected")?;
        library.restrict_to_executable();
        if library.outdated()
            || !library.checks_itself()
            || library.check(&mut system.memory) != 0
            || !library.has_code(text.address)
        {
            return Err("title_native_origins_or_entry_mismatch".into());
        }
        system.memory.verify_base_code_fence()?;
        system.recompiled = Some(library);
    }
    Ok(system)
}

// CodexAstraUlt: Read the actual BLZ expansion size before the loader allocates
// a decompressed image. Manifest declarations alone cannot bound malformed but
// identity-matching input, and this preflight performs no decompression itself.
fn preflight_code(input: &Path, manifest: &Manifest) -> Result<(), String> {
    let title = zakuro_fs::Title::load(input).map_err(|_| "title_preflight_loader_rejected")?;
    let raw = title
        .exefs_file(".code")
        .ok_or("title_preflight_code_missing")?;
    let bytes = if title.exheader.compress_code {
        zakuro_fs::lz77::decompressed_size(raw)
            .map_err(|_| "title_preflight_compression_invalid")?
    } else {
        raw.len()
    };
    let expected = manifest
        .prepared
        .components
        .iter()
        .find(|component| component.kind == "decompressed_code")
        .ok_or("title_preflight_code_identity_missing")?;
    if raw.len() as u64 > crate::manifest::MAX_COMPONENT
        || bytes as u64 > crate::manifest::MAX_COMPONENT
        || bytes as u64 != expected.bytes
    {
        return Err("title_preflight_code_size_rejected".into());
    }
    for (expected, actual) in manifest.prepared.segments.iter().zip([
        title.exheader.text,
        title.exheader.rodata,
        title.exheader.data,
    ]) {
        if expected.address != actual.address
            || expected.size != u64::from(actual.size)
            || expected.mapped_bytes != u64::from(actual.num_pages) * 4096
        {
            return Err("title_preflight_segment_layout_mismatch".into());
        }
    }
    if title.exheader.bss_size != manifest.prepared.bss_size
        || u64::from(title.exheader.bss_size) > 256 * 1024 * 1024
        || u64::from(title.exheader.stack_size) > 64 * 1024 * 1024
    {
        return Err("title_preflight_memory_request_rejected".into());
    }
    Ok(())
}

// CodexAstraUlt: Hash the loader's actual mapped image/components, not a second
// filename read. Full input identity also binds data/modules absent from code.
fn bind(system: &mut System, manifest: &Manifest) -> Result<(), String> {
    let title = system.title.as_ref().ok_or("title_runtime_image_missing")?;
    let prepared = &manifest.prepared;
    let raw = title.image().data();
    if format!("{:016x}", title.program_id()) != manifest.program_id
        || title.ncch.version != prepared.ncch_format_version
        || title.exheader.remaster_version != prepared.remaster_version
        || title.exheader.bss_size != prepared.bss_size
        || title.layered.is_some()
        || raw.len() as u64 != manifest.input.bytes
        || sha256(raw) != manifest.input.sha256
    {
        return Err("title_runtime_identity_mismatch".into());
    }
    let container = if zakuro_fs::Ncsd::detect(raw) {
        "ncsd"
    } else if zakuro_fs::Cia::detect(raw) {
        "cia"
    } else if zakuro_fs::NcchHeader::detect(raw) {
        "ncch"
    } else {
        return Err("title_container_unknown".into());
    };
    if container != prepared.container {
        return Err("title_container_mismatch".into());
    }
    if container == "cia" {
        let cia = zakuro_fs::Cia::parse(raw).map_err(|_| "title_cia_invalid")?;
        if cia.title_id != title.program_id() || Some(cia.version) != prepared.cia_title_version {
            return Err("title_cia_identity_mismatch".into());
        }
    }
    let code = title
        .code()
        .map_err(|_| "title_decompressed_code_unavailable")?;
    for component in &prepared.components {
        let bytes = match component.kind.as_str() {
            "ncch_header" => {
                let offset = title.ncch_offset() as usize;
                raw.get(offset..offset + 512)
                    .ok_or("title_ncch_header_missing")?
            }
            "exheader" => title.exheader_bytes(),
            "decompressed_code" => code.as_slice(),
            "cro" | "static_crs" => {
                let file = title
                    .romfs
                    .as_ref()
                    .ok_or("title_module_filesystem_missing")?
                    .lookup(
                        component
                            .source_path
                            .as_deref()
                            .ok_or("title_module_path_missing")?,
                    )
                    .map_err(|_| "title_module_missing")?;
                if file.data_size != component.bytes {
                    return Err("title_module_size_mismatch".into());
                }
                title
                    .read_romfs(&file, 0, component.bytes as usize)
                    .ok_or("title_module_unreadable")?
            }
            _ => return Err("title_component_kind_unknown".into()),
        };
        if bytes.len() as u64 != component.bytes || sha256(bytes) != component.sha256 {
            return Err(format!("title_component_mismatch_{}", component.kind));
        }
    }
    let mut offset = 0;
    for (expected, actual) in prepared.segments.iter().zip([
        title.exheader.text,
        title.exheader.rodata,
        title.exheader.data,
    ]) {
        if expected.address != actual.address
            || expected.size != u64::from(actual.size)
            || expected.mapped_bytes != u64::from(actual.num_pages) * 4096
            || expected.offset != offset
        {
            return Err("title_segment_layout_mismatch".into());
        }
        let start = offset as usize;
        let logical = code
            .get(start..start + expected.size as usize)
            .ok_or("title_segment_truncated")?;
        if sha256(logical) != expected.sha256 {
            return Err("title_segment_hash_mismatch".into());
        }
        offset += expected.mapped_bytes;
        // CodexAstraUlt: Loader-created padding is zero, while actual code
        // bytes, including mapped padding present in the source, must agree.
        for within in (0..expected.mapped_bytes as usize).step_by(4096) {
            let address = expected
                .address
                .checked_add(within as u32)
                .ok_or("title_segment_address_overflow")?;
            if !system.memory.is_readable(address, 4096) {
                return Err("title_segment_unreadable".into());
            }
            let mut actual = [0u8; 4096];
            let mut wanted = [0u8; 4096];
            let at = start + within;
            if at < code.len() {
                let length = (code.len() - at).min(4096);
                wanted[..length].copy_from_slice(&code[at..at + length]);
            }
            system.memory.read_bytes(address, &mut actual);
            if actual != wanted {
                return Err("title_mapped_segment_mismatch".into());
            }
        }
    }
    if !system.memory.fault_summary().is_empty() {
        return Err("title_admission_memory_fault".into());
    }
    Ok(())
}
