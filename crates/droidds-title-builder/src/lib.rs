//! CodexAstraUlt: Resolve one unchanged base title before deterministic native
//! source emission. The external coordinator owns snapshot hashes and limits.

use recomp3ds::{build, rom::CodeSetInfo};
use serde_json::{json, Value};
use std::{fs, io::Write, path::Path};

const MAX_FILE: u64 = 64 * 1024 * 1024;
// CodexAstraUlt: Keep the established default while admitting a measured larger
// title only through an explicit bounded request. These are build output bytes,
// not a runtime memory or package-size allocation.
pub const DEFAULT_OUTPUT_LIMIT: u64 = 512 * 1024 * 1024;
pub const MAX_OUTPUT_LIMIT: u64 = 1024 * 1024 * 1024;
const MAX_OUTPUT_FILES: usize = 8192;
// CodexAstraUlt: Match the coordinator's bounded success JSON reader, rather
// than letting large module metadata pass the worker and fail its consumer.
const MAX_DESCRIPTOR: u64 = 1024 * 1024;

// CodexAstraUlt: Replace post-generation rejection with admission before each
// file write, counting identity, generated C/headers and the success descriptor
// together. A failed write may leave a partial file (including the descriptor),
// but cannot qualify preparation; counts cover only fully written/synced files.
struct Admission {
    limit: u64,
    files: usize,
    bytes: u64,
    stage: &'static str,
    attempted_file: Option<u64>,
    attempted_total: Option<u64>,
}

impl Admission {
    fn new(limit: u64) -> Self {
        Self {
            limit,
            files: 0,
            bytes: 0,
            stage: "identity",
            attempted_file: None,
            attempted_total: None,
        }
    }

    fn write(&mut self, root: &Path, name: &str, bytes: &[u8]) -> Result<(), String> {
        let count = bytes.len() as u64;
        self.attempted_file = Some(count);
        self.attempted_total = self.bytes.checked_add(count);
        if count > MAX_FILE {
            return Err("prepared component exceeds 64 MiB".into());
        }
        if self.stage == "metadata" && count > MAX_DESCRIPTOR {
            return Err("preparation descriptor exceeds 1 MiB".into());
        }
        if self.files >= MAX_OUTPUT_FILES {
            return Err("prepared output exceeds file count bound".into());
        }
        let total = self
            .attempted_total
            .filter(|total| *total <= self.limit)
            .ok_or("prepared output exceeds aggregate bound")?;
        write_new(root, name, bytes)?;
        self.files += 1;
        self.bytes = total;
        self.attempted_file = None;
        self.attempted_total = None;
        Ok(())
    }

    // CodexAstraUlt: Failure evidence is a small, separate diagnostic allowance;
    // it is never admitted as prepared output or sufficient for a manifest.
    // Failure to save it cannot replace the original rejection reason.
    fn record_failure(&self, output: &Path, reason: &str) {
        let reason: String = reason.chars().take(4096).collect();
        let value = json!({
            "schema_version":1,"kind":"droidds_title_preparation_failure",
            "stage":self.stage,"reason":reason,"output_limit_bytes":self.limit,
            "accepted_files":self.files,"accepted_bytes":self.bytes,
            "attempted_file_bytes":self.attempted_file,
            "attempted_total_bytes":self.attempted_total
        });
        if let Ok(mut bytes) = serde_json::to_vec_pretty(&value) {
            bytes.push(b'\n');
            if bytes.len() <= 64 * 1024 {
                let _ = write_new(output, "prepare-failure.json", &bytes);
            }
        }
    }
}

// CodexAstraUlt: A fresh private output is mandatory; neither input nor a prior
// preparation is ever replaced. The coordinator checks all parent components.
fn directory(path: &Path) -> Result<(), String> {
    let mut builder = fs::DirBuilder::new();
    #[cfg(unix)]
    {
        use std::os::unix::fs::DirBuilderExt;
        builder.mode(0o700);
    }
    builder.create(path).map_err(|error| error.to_string())
}

// CodexAstraUlt: Raw identity material stays with private generated code. Files
// have fixed tool-owned names and are never populated from title path strings.
fn write_new(root: &Path, name: &str, bytes: &[u8]) -> Result<(), String> {
    if bytes.len() as u64 > MAX_FILE {
        return Err("prepared component exceeds 64 MiB".into());
    }
    let mut options = fs::OpenOptions::new();
    options.write(true).create_new(true);
    #[cfg(unix)]
    {
        use std::os::unix::fs::OpenOptionsExt;
        options.mode(0o600);
    }
    let mut file = options.open(root.join(name)).map_err(|e| e.to_string())?;
    file.write_all(bytes)
        .and_then(|_| file.sync_all())
        .map_err(|e| e.to_string())
}

// CodexAstraUlt: Logical segment sizes are distinct from page-sized runtime
// mappings. Full decompressed bytes separately bind padding and a possible tail.
fn segment(name: &str, info: CodeSetInfo, offset: u64) -> Value {
    json!({"name":name,"address":info.address,"offset":offset,"size":info.size,
        "mapped_bytes":u64::from(info.num_pages)*4096})
}

// CodexAstraUlt: Compare independently parsed runtime fields as well as bytes;
// successful preparation does not install a runtime identity-enforcement adapter.
fn check_runtime(
    input: &Path,
    resolved: &recomp3ds::strict::ResolvedTitle,
) -> Result<zakuro_fs::Title, String> {
    let runtime = zakuro_fs::Title::load(input).map_err(|e| e.to_string())?;
    let header = &resolved.title.exheader;
    let ncch = usize::try_from(runtime.ncch_offset()).map_err(|_| "NCCH offset overflow")?;
    if runtime.program_id() != resolved.title.program_id()
        || runtime.image().data().get(ncch..ncch + 512) != Some(resolved.ncch_header.as_slice())
        || runtime.exheader_bytes() != resolved.exheader_bytes
        || runtime.code().map_err(|e| e.to_string())? != resolved.code
        || runtime.exheader.bss_size != header.bss_size
    {
        return Err("compiler/runtime base resolution differs".into());
    }
    for (a, b) in [
        (header.text, runtime.exheader.text),
        (header.rodata, runtime.exheader.rodata),
        (header.data, runtime.exheader.data),
    ] {
        if (a.address, a.num_pages, a.size) != (b.address, b.num_pages, b.size) {
            return Err("compiler/runtime segment layout differs".into());
        }
    }
    // CodexAstraUlt: Bind module identity to the runtime's own path lookup,
    // including static.crs; matching the executable alone cannot qualify CROs.
    for module in &resolved.modules {
        let romfs = runtime
            .romfs
            .as_ref()
            .ok_or("runtime has no declared module filesystem")?;
        let file = romfs.lookup(&module.path).map_err(|e| e.to_string())?;
        if file.data_size != module.bytes.len() as u64
            || runtime.read_romfs(&file, 0, module.bytes.len()) != Some(module.bytes.as_slice())
        {
            return Err("compiler/runtime module resolution differs".into());
        }
    }
    Ok(runtime)
}

// CodexAstraUlt: One strict resolved collection feeds both identity material and
// code generation. There is no second compiler load, mod overlay or hint search.
pub fn prepare(input: &Path, output: &Path) -> Result<Value, String> {
    prepare_with_limit(input, output, DEFAULT_OUTPUT_LIMIT)
}

// CodexAstraUlt: The supervisor chooses and records one output budget, enforced
// here during emission and independently against the final exact inventory.
pub fn prepare_with_limit(input: &Path, output: &Path, limit: u64) -> Result<Value, String> {
    if limit == 0 || limit > MAX_OUTPUT_LIMIT {
        return Err("output limit must be between 1 byte and 1 GiB".into());
    }
    if output.symlink_metadata().is_ok() {
        return Err("preparation output must not exist".into());
    }
    let metadata = input.symlink_metadata().map_err(|e| e.to_string())?;
    if !metadata.is_file() || metadata.len() == 0 || metadata.len() > 8 * 1024 * 1024 * 1024 {
        return Err("input must be a bounded regular base image".into());
    }
    let resolved = recomp3ds::strict::resolve(input).map_err(|e| e.to_string())?;
    if resolved.code.len() as u64 > MAX_FILE {
        return Err("decompressed code exceeds preparation bound".into());
    }
    let runtime = check_runtime(input, &resolved)?;
    let raw = runtime.image().data();
    let container = match raw.get(0x100..0x104) {
        Some(b"NCCH") => "ncch",
        Some(b"NCSD") => "ncsd",
        _ if raw.get(..4) == Some(&0x2020u32.to_le_bytes()) => "cia",
        _ => return Err("unsupported source container".into()),
    };
    let cia_version = if container == "cia" {
        let cia = zakuro_fs::Cia::parse(raw).map_err(|e| e.to_string())?;
        if cia.title_id != runtime.program_id() {
            return Err("CIA and executable program identities differ".into());
        }
        Some(cia.version)
    } else {
        None
    };
    let header = &resolved.title.exheader;
    let segments = vec![
        segment("text", header.text, 0),
        segment(
            "rodata",
            header.rodata,
            u64::from(header.text.num_pages) * 4096,
        ),
        segment(
            "data",
            header.data,
            (u64::from(header.text.num_pages) + u64::from(header.rodata.num_pages)) * 4096,
        ),
    ];
    let mut report = json!({
        "schema_version":1,"kind":"droidds_title_preparation","status":"prepared",
        "container":container,"program_id":format!("{:016x}", runtime.program_id()),
        "ncch_format_version":runtime.ncch.version,
        "remaster_version":runtime.exheader.remaster_version,"cia_title_version":cia_version,
        "abi":recomp3ds::abi::ABI,"generation":recomp3ds::abi::GENERATION,
        "hints":"disabled","overlays":[],"runtime_resolution_checked":true,
        "runtime_binding_enforced":false,"segments":segments,"bss_size":header.bss_size,
        "components":[],"artifacts":[],"sources":[]
    });
    directory(output)?;
    let mut admission = Admission::new(limit);
    let result: Result<Value, String> = (|| {
        directory(&output.join("identity"))?;
        let mut components = Vec::new();
        for (path, kind, bytes) in [
            (
                "identity/ncch-header.bin",
                "ncch_header",
                resolved.ncch_header.as_slice(),
            ),
            (
                "identity/exheader.bin",
                "exheader",
                resolved.exheader_bytes.as_slice(),
            ),
            (
                "identity/code.bin",
                "decompressed_code",
                resolved.code.as_slice(),
            ),
        ] {
            admission.write(output, path, bytes)?;
            components.push(json!({"path":path,"kind":kind,"bytes":bytes.len()}));
        }
        for (index, module) in resolved.modules.iter().enumerate() {
            let path = format!("identity/module-{index:04}.bin");
            admission.write(output, &path, &module.bytes)?;
            components.push(json!({"path":path,
            "kind":if module.is_static {"static_crs"} else {"cro"},
            "bytes":module.bytes.len(),"source_path":module.path,"module_name":module.name}));
        }
        drop(runtime);
        admission.stage = "generation";
        directory(&output.join("generated"))?;
        // CodexAstraUlt: Consume and release each completed source file. Admission
        // stops before an overflowing file is written, rather than materializing
        // and writing the entire title before checking its inventory.
        let mut artifacts = Vec::new();
        let mut consume = |name: &str, bytes: &[u8]| {
            if name.is_empty()
                || !name
                    .bytes()
                    .all(|v| v.is_ascii_alphanumeric() || b"_.-".contains(&v))
                || !(name.ends_with(".c") || name.ends_with(".h"))
            {
                return Err("unexpected generated artifact".into());
            }
            if artifacts.len() >= 4096 {
                return Err("prepared output exceeds generated file count bound".into());
            }
            let path = format!("generated/{name}");
            admission.write(output, &path, bytes)?;
            artifacts.push(json!({"path":path,"bytes":bytes.len()}));
            Ok(())
        };
        let generated = build::generate_resolved_to(
            resolved.title,
            resolved.programs,
            output.join("generated"),
            build::HintPolicy::Disabled,
            &|_| {},
            &mut consume,
        )?;
        artifacts.sort_by(|a, b| a["path"].as_str().cmp(&b["path"].as_str()));
        let mut sources: Vec<_> = generated
            .sources
            .iter()
            .map(|s| format!("generated/{s}"))
            .collect();
        sources.sort();
        if sources.is_empty() {
            return Err("no generated C sources".into());
        }
        report["components"] = json!(components);
        report["artifacts"] = json!(artifacts);
        report["sources"] = json!(sources);
        admission.stage = "metadata";
        let mut bytes = serde_json::to_vec_pretty(&report).map_err(|e| e.to_string())?;
        bytes.push(b'\n');
        admission.write(output, "prepare-report.json", &bytes)?;
        Ok(report)
    })();
    if let Err(error) = &result {
        admission.record_failure(output, error);
    }
    result
}
