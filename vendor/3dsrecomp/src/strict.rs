//! CodexAstraUlt: Explicit base-title compiler inputs with complete module
//! admission. No hints, mods, code discovery or filesystem output occurs here.

use std::{collections::BTreeSet, path::Path};

use crate::{
    cro,
    discover::Program,
    image::Image,
    rom::{CodeSetInfo, Error, Title},
};

// CodexAstraUlt: Bound private preparation independently of any game's claimed
// lengths. Exceeding a limit is an explicit admission failure, not an omission.
pub const MAX_CODE_BYTES: usize = 64 * 1024 * 1024;
pub const MAX_MODULE_BYTES: usize = 64 * 1024 * 1024;
pub const MAX_TOTAL_MODULE_BYTES: usize = 256 * 1024 * 1024;
pub const MAX_MODULES: usize = 4096;
// CodexAstraUlt: Aliased symbol tables can expand beyond their source file;
// bound estimated retained metadata before the legacy parser allocates it.
const MAX_MODULE_METADATA: usize = 64 * 1024 * 1024;
const MAX_TOTAL_MODULE_METADATA: usize = 256 * 1024 * 1024;

/// CodexAstraUlt: Preserve the source path and complete raw module payload so
/// callers can bind the manifest to both compiled CROs and the static descriptor.
pub struct ModuleSource {
    pub path: String,
    pub name: String,
    pub bytes: Vec<u8>,
    pub is_static: bool,
}

/// CodexAstraUlt: Code and headers are the exact bytes used for resolution;
/// callers need not reopen a mutable source to construct its compiler identity.
pub struct ResolvedTitle {
    pub title: Title,
    pub programs: Vec<(String, Program)>,
    pub modules: Vec<ModuleSource>,
    pub exheader_bytes: Vec<u8>,
    pub ncch_header: Vec<u8>,
    pub code: Vec<u8>,
}

/// CodexAstraUlt: Resolve a base executable and all declared CROs once. Legacy
/// permissive APIs remain available, but this route never drops a failed module.
pub fn resolve(path: impl AsRef<Path>) -> Result<ResolvedTitle, Error> {
    let title = Title::load_strict(path)?;
    let code = title.code()?;
    if code.len() > MAX_CODE_BYTES {
        return Err(Error::invalid("strict executable exceeds the code limit"));
    }
    validate_segments(&title, &code)?;
    let entries = match &title.romfs {
        Some(romfs) => romfs.strict_files()?,
        None => Vec::new(),
    };
    let mut modules = Vec::new();
    let mut paths = Vec::new();
    let mut static_module = None;
    let mut total = 0usize;
    let mut metadata = 0usize;
    let mut names = BTreeSet::from(["executable".to_owned()]);
    for (path, file) in entries {
        let is_static = path.eq_ignore_ascii_case("static.crs");
        if !is_static && !path.to_ascii_lowercase().ends_with(".cro") {
            continue;
        }
        if modules.len() + usize::from(static_module.is_some()) >= MAX_MODULES {
            return Err(Error::invalid("strict module count exceeds the limit"));
        }
        let size = usize::try_from(file.data_size)
            .map_err(|_| Error::invalid("strict module size cannot be represented"))?;
        total = total
            .checked_add(size)
            .ok_or_else(|| Error::invalid("strict module bytes overflow"))?;
        if size > MAX_MODULE_BYTES || total > MAX_TOTAL_MODULE_BYTES {
            return Err(Error::invalid("strict module payload exceeds the limit"));
        }
        let bytes = title
            .read_romfs(&file, 0, size)
            .filter(|bytes| bytes.len() == size)
            .ok_or_else(|| Error::invalid(format!("cannot read the declared module {path}")))?;
        let expanded = preflight_module(&bytes).map_err(|error| {
            Error::invalid(format!("cannot parse the declared module {path}: {error}"))
        })?;
        metadata = metadata
            .checked_add(expanded)
            .ok_or_else(|| Error::invalid("strict module metadata overflows"))?;
        if metadata > MAX_TOTAL_MODULE_METADATA {
            return Err(Error::invalid(
                "strict total module metadata exceeds the limit",
            ));
        }
        let module = cro::parse(&bytes)
            .ok_or_else(|| Error::invalid(format!("cannot parse the declared module {path}")))?;
        validate_name(&module.name)?;
        if !names.insert(module.name.clone()) {
            return Err(Error::invalid("strict module names must be unique"));
        }
        validate_module(&module, &bytes, is_static)?;
        if is_static {
            static_module = Some((path, module, bytes));
        } else {
            paths.push(path);
            modules.push((module, bytes));
        }
    }

    let crs = static_module.as_ref().map(|(_, module, _)| module);
    let exports = crs.map(cro::Module::code_exports).unwrap_or_default();
    let imports = crs
        .map(|module| crate::imported(&modules, crs, module))
        .unwrap_or_default();
    let mut programs = vec![(
        "executable".to_owned(),
        Image::from_code(&title.exheader, &code).into_program(&exports, &imports),
    )];
    for (module, bytes) in &modules {
        let program = module
            .program(bytes, &crate::imported(&modules, crs, module))
            .ok_or_else(|| {
                Error::invalid(format!(
                    "module {} has no supported compilable code segment",
                    module.name
                ))
            })?;
        programs.push((module.name.clone(), program));
    }
    let mut sources: Vec<ModuleSource> = paths
        .into_iter()
        .zip(modules)
        .map(|(path, (module, bytes))| ModuleSource {
            path,
            name: module.name,
            bytes,
            is_static: false,
        })
        .collect();
    if let Some((path, module, bytes)) = static_module {
        sources.push(ModuleSource {
            path,
            name: module.name,
            bytes,
            is_static: true,
        });
    }
    sources.sort_by(|a, b| a.path.cmp(&b.path));
    Ok(ResolvedTitle {
        exheader_bytes: title.raw_exheader().to_vec(),
        ncch_header: title.raw_ncch_header().to_vec(),
        title,
        programs,
        modules: sources,
        code,
    })
}

// CodexAstraUlt: Validate every source extent before Image's permissive slicing,
// retaining page padding in the full code identity and logical segment lengths.
fn validate_segments(title: &Title, code: &[u8]) -> Result<(), Error> {
    let h = &title.exheader;
    if h.text.size == 0 {
        return Err(Error::invalid("strict executable has no text"));
    }
    let mut offset = 0usize;
    let mut ranges = Vec::new();
    for segment in [h.text, h.rodata, h.data] {
        let pages = (segment.num_pages as usize)
            .checked_mul(0x1000)
            .ok_or_else(|| Error::invalid("strict segment page size overflows"))?;
        let end = offset
            .checked_add(segment.size as usize)
            .ok_or_else(|| Error::invalid("strict segment source range overflows"))?;
        if segment.size as usize > pages
            || ((segment.size != 0 || pages != 0) && code.get(offset..end).is_none())
        {
            return Err(Error::invalid(
                "strict executable segment is truncated or exceeds mapped pages",
            ));
        }
        if pages != 0 {
            let end = u64::from(segment.address) + pages as u64;
            if segment.address & 0xFFF != 0 || end > u64::from(u32::MAX) {
                return Err(Error::invalid(
                    "strict executable segment mapping is invalid",
                ));
            }
            ranges.push((u64::from(segment.address), end));
        }
        offset = offset
            .checked_add(pages)
            .ok_or_else(|| Error::invalid("strict executable layout overflows"))?;
    }
    // CodexAstraUlt: Match the loader's extra BSS mapping after data pages;
    // an extension must not overwrite a separately mapped executable segment.
    if let Some(range) = bss_extension(h.data, h.bss_size)? {
        ranges.push(range);
    }
    ranges.sort_unstable();
    if ranges.windows(2).any(|pair| pair[0].1 > pair[1].0) {
        return Err(Error::invalid("strict executable segment mappings overlap"));
    }
    Ok(())
}

// CodexAstraUlt: Uninitialized data must also fit guest address arithmetic;
// it is not read from the executable or silently appended to source bytes.
fn bss_extension(data: CodeSetInfo, bss: u32) -> Result<Option<(u64, u64)>, Error> {
    let start = u64::from(data.address) + u64::from(data.num_pages) * 0x1000;
    let raw_end = u64::from(data.address) + u64::from(data.size) + u64::from(bss);
    if start > u64::from(u32::MAX) || raw_end > u64::from(u32::MAX) {
        return Err(Error::invalid("strict executable BSS mapping overflows"));
    }
    // CodexAstraUlt: The loader creates extra pages only for a positive tail.
    // An unused address in an absent data segment must not invent a mapping.
    if raw_end <= start {
        return Ok(None);
    }
    if start & 0xFFF != 0 {
        return Err(Error::invalid(
            "strict executable BSS extension is unaligned",
        ));
    }
    let length = (raw_end - start).next_multiple_of(0x1000);
    let end = start
        .checked_add(length)
        .filter(|&end| end <= u64::from(u32::MAX))
        .ok_or_else(|| Error::invalid("strict executable BSS mapping overflows"))?;
    Ok(Some((start, end)))
}

// CodexAstraUlt: Check every table the existing CRO parser materializes and
// account repeated strings/anonymous imports before it follows aliased tables.
// This is allocation admission, not full validation of CRO relocation semantics.
fn preflight_module(bytes: &[u8]) -> Result<usize, Error> {
    let word = |at: usize| -> Result<usize, Error> {
        let raw = bytes
            .get(at..at.saturating_add(4))
            .ok_or_else(|| Error::invalid("module header/table is truncated"))?;
        Ok(u32::from_le_bytes(raw.try_into().unwrap()) as usize)
    };
    let table = |offset: usize, count: usize, stride: usize| -> Result<(), Error> {
        let length = count
            .checked_mul(stride)
            .ok_or_else(|| Error::invalid("module table size overflows"))?;
        let end = offset
            .checked_add(length)
            .ok_or_else(|| Error::invalid("module table range overflows"))?;
        if count > 1_000_000 || (count != 0 && bytes.get(offset..end).is_none()) {
            return Err(Error::invalid(
                "module table is outside its payload or entry limit",
            ));
        }
        Ok(())
    };
    let string = |offset: usize, max: usize| -> Result<usize, Error> {
        let tail = bytes
            .get(offset..)
            .ok_or_else(|| Error::invalid("module name offset is invalid"))?;
        let length = tail
            .iter()
            .take(max + 1)
            .position(|&byte| byte == 0)
            .ok_or_else(|| Error::invalid("module string is unterminated or exceeds its limit"))?;
        std::str::from_utf8(&tail[..length])
            .map_err(|_| Error::invalid("module string is invalid UTF-8"))?;
        Ok(length)
    };
    let mut cost = 0usize;
    let account = |cost: &mut usize, amount: usize| -> Result<(), Error> {
        *cost = cost
            .checked_add(amount)
            .ok_or_else(|| Error::invalid("module metadata size overflows"))?;
        if *cost > MAX_MODULE_METADATA {
            return Err(Error::invalid("module expanded metadata exceeds its limit"));
        }
        Ok(())
    };
    if bytes.get(0x80..0x84) != Some(b"CRO0") {
        return Err(Error::invalid("module has no CRO header"));
    }
    for (at, count_at, stride) in [
        (0xC8, 0xCC, 12),
        (0xD0, 0xD4, 8),
        (0xD8, 0xDC, 4),
        (0x128, 0x12C, 12),
        (0xF8, 0xFC, 12),
        (0xF0, 0xF4, 20),
    ] {
        let count = word(count_at)?;
        table(word(at)?, count, stride)?;
        account(&mut cost, count * 64)?;
    }
    account(&mut cost, string(word(0xC0)?, 255)? + 64)?;
    for i in 0..word(0xD4)? {
        account(&mut cost, string(word(word(0xD0)? + i * 8)?, 4096)?)?;
    }
    for i in 0..word(0xF4)? {
        let at = word(0xF0)? + i * 20;
        let length = string(word(at)?, 255)?;
        let count = word(at + 16)?;
        table(word(at + 12)?, count, 8)?;
        let expanded = count
            .checked_mul(length + 64)
            .ok_or_else(|| Error::invalid("anonymous imports overflow metadata"))?;
        account(&mut cost, expanded + length)?;
    }
    Ok(cost)
}

// CodexAstraUlt: Module names enter generated C string literals. Reject names
// requiring escaping and ambiguous identities rather than emitting invalid C.
fn validate_name(name: &str) -> Result<(), Error> {
    if name.is_empty()
        || name.len() > 255
        || !name
            .bytes()
            .all(|b| (0x20..=0x7E).contains(&b) && !matches!(b, b'"' | b'\\' | b'?'))
    {
        return Err(Error::invalid("strict module name is unsafe or empty"));
    }
    Ok(())
}

// CodexAstraUlt: Validate ranges used by permissive CRO helpers before they
// perform address addition, relocation patching or program extraction.
fn validate_module(module: &cro::Module, bytes: &[u8], is_static: bool) -> Result<(), Error> {
    if module.segments.len() > 16 {
        return Err(Error::invalid("strict module has too many tagged segments"));
    }
    // CodexAstraUlt: The extractor selects one code segment. Reject a second
    // nonempty code segment explicitly instead of silently omitting it.
    if !is_static
        && module
            .segments
            .iter()
            .filter(|segment| segment.kind == 0 && segment.size > 0)
            .count()
            > 1
    {
        return Err(Error::invalid(
            "strict preparation does not support multiple nonempty module code segments",
        ));
    }
    for segment in &module.segments {
        let end = segment
            .offset
            .checked_add(segment.size)
            .ok_or_else(|| Error::invalid("strict module segment overflows"))?;
        if segment.kind > 3 || (!is_static && segment.kind != 3 && end as usize > bytes.len()) {
            return Err(Error::invalid(
                "strict module segment is outside its payload",
            ));
        }
    }
    for relocation in module.relocations.iter().chain(&module.imports) {
        let target = module
            .segments
            .get((relocation.target & 0xF) as usize)
            .ok_or_else(|| Error::invalid("strict module relocation has no target segment"))?;
        if (relocation.target >> 4)
            .checked_add(4)
            .is_none_or(|end| end > target.size)
        {
            return Err(Error::invalid(
                "strict module relocation target is outside its segment",
            ));
        }
    }
    for relocation in &module.relocations {
        let source = module
            .segments
            .get(relocation.segment as usize)
            .ok_or_else(|| Error::invalid("strict module relocation has no source segment"))?;
        if source.offset.checked_add(relocation.addend).is_none() {
            return Err(Error::invalid("strict module relocation value overflows"));
        }
    }
    Ok(())
}

// CodexAstraUlt: All regressions construct original containers/modules; no
// private title bytes or analysis are included in the compiler source tree.
#[cfg(test)]
mod tests;
