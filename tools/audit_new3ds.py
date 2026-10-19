#!/usr/bin/env python3
"""CodexAstraUlt: Execute pinned parser/allocator code without a retail title."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess

from build_foundation import ROOT, run_logged

REVISION = "412900a5a020301da15c1cc382585e05a489a535"
FILES = {
    "reader": "crates/zakuro-fs/src/reader.rs",
    "ncch": "crates/zakuro-fs/src/ncch.rs",
    "ncsd": "crates/zakuro-fs/src/ncsd.rs",
    "physical": "crates/zakuro-core/src/memory/physical.rs",
    "loader": "crates/zakuro-core/src/loader.rs",
}


def verified_sources(checkout: Path) -> tuple[dict[str, str], dict[str, str]]:
    """CodexAstraUlt: Reject dirty/wrong source instead of auditing a moving tree."""
    identity = subprocess.check_output(
        ["git", "-C", str(checkout), "rev-parse", "HEAD"], timeout=10, text=True
    ).strip()
    if identity != REVISION:
        raise ValueError("The audit requires the reviewed Zakuro revision")
    sources, hashes = {}, {}
    for name, relative in FILES.items():
        original = subprocess.check_output(
            ["git", "-C", str(checkout), "show", f"{REVISION}:{relative}"], timeout=10
        )
        if (checkout / relative).read_bytes() != original:
            raise ValueError(f"Modified audited source: {relative}")
        sources[name] = original.decode("utf-8")
        hashes[relative] = hashlib.sha256(original).hexdigest()
    return sources, hashes


def harness(checkout: Path, sources: dict[str, str]) -> str:
    """CodexAstraUlt: Compile real modules; isolate only their surrounding types."""
    assignments = re.findall(r"let app_bytes = [^;]+;", sources["loader"])
    if assignments != ["let app_bytes = exheader.system_mode.application_memory();"]:
        raise ValueError("Loader changed; review this intentionally narrow extraction")
    media = re.findall(r"pub const MEDIA_UNIT: u64 = [^;]+;", sources["ncsd"])
    if len(media) != 1:
        raise ValueError("Cannot isolate the actual NCSD media-unit constant")
    paths = "\n".join(
        f"#[path = {json.dumps(str(checkout / FILES[name]))}] mod {name};"
        for name in ("reader", "ncch", "physical")
    )
    return """// CodexAstraUlt: Original synthetic fixtures, no retail code/data.
// The parser and allocator modules below are compiled unchanged from the pin.
#![allow(dead_code)]
// CodexAstraUlt: These error shapes provide the reader's surrounding ABI only;
// no filesystem, IO, title loading or service behavior is being simulated.
#[derive(Debug)]
pub enum FsError {
    Truncated { offset: usize, len: usize },
    BadMagic { expected: [u8; 4], got: [u8; 4], offset: usize },
}
""" + paths + "\nmod ncsd { " + media[0] + " }\n" + """
// CodexAstraUlt: Execute the exact loader assignment extracted above, without
// pretending this calls the complete title loader or chooses its console model.
fn loader_app_bytes(exheader: &ncch::ExHeader) -> u32 {
""" + assignments[0] + "\napp_bytes\n}\n" + r'''
fn main() {
    use physical::{MemoryRegion as Region, PhysicalMemory};
    let mut first = true;
    println!("[");
    // CodexAstraUlt: Inputs use Project_CTR's independently documented byte
    // layout. Old-mode controls separate parser errors from region selection.
    for (name, new3ds, old_mode, new_mode, flags) in [
        ("old_prod", false, 0u8, 0u8, 0u8),
        ("old_dev1", false, 2, 0, 0),
        ("old_dev2", false, 3, 0, 0),
        ("old_dev3", false, 4, 0, 0),
        ("old_dev4", false, 5, 0, 0),
        ("new_legacy", true, 0, 0, 0),
        ("new_124_plain", true, 0, 1, 0),
        ("new_124_fast_l2", true, 0, 1, 3),
        ("new_178_plain", true, 0, 2, 0),
        ("new_178_fast_l2", true, 0, 2, 3),
        ("new_legacy_l2_only", true, 0, 0, 1),
        ("new_legacy_fast_only", true, 0, 0, 2),
    ] {
        let mut bytes = vec![0u8; ncch::ExHeader::FULL_SIZE];
        bytes[0x20c] = flags;
        bytes[0x20d] = new_mode;
        bytes[0x20e] = old_mode << 4;
        let header = ncch::ExHeader::parse(&bytes).expect("original header parses");
        let app_bytes = loader_app_bytes(&header);
        let mut memory = PhysicalMemory::new(new3ds, app_bytes);
        let total = memory.fcram.len();
        let app = memory.region_size(Region::Application);
        let system = memory.region_size(Region::System);
        let base = memory.region_size(Region::Base);
        // CodexAstraUlt: Exercise allocation, exhaustion and recovery against
        // real region bookkeeping, not just duplicated arithmetic assertions.
        let block = memory.allocate(Region::Application, app)
            .expect("fresh application region can be allocated");
        let extra_rejected = memory.allocate(Region::Application, 0x1000).is_none();
        memory.free(block);
        let free_restored = memory.region_free(Region::Application) == app;
        assert!(extra_rejected && free_restored);
        assert_eq!(app as usize + system as usize + base as usize, total);
        if !first { println!(","); }
        first = false;
        print!("{{\"name\":\"{}\",\"new3ds\":{},\"old_mode\":{},\"input_new_mode\":{},\"input_cpu_l2_flags\":{},\"parsed_new_mode\":{},\"parsed_cpu_speed\":{},\"parsed_l2\":{},\"fcram_bytes\":{},\"application_bytes\":{},\"system_bytes\":{},\"base_bytes\":{},\"extra_page_rejected\":{},\"free_restored\":{}}}",
            name, new3ds, old_mode, new_mode, flags,
            header.n3ds_system_mode, header.n3ds_cpu_speed, header.enable_l2_cache,
            total, app, system, base, extra_rejected, free_restored);
    }
    println!("\n]");
}
'''


def main() -> None:
    """CodexAstraUlt: Keep audit artifacts isolated and report known gaps openly."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--zakuro", type=Path, required=True)
    parser.add_argument("--deps", type=Path, default=ROOT / "target/release/deps")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    checkout, deps, output = args.zakuro.resolve(), args.deps.resolve(), args.output.resolve()
    sources, hashes = verified_sources(checkout)
    libraries = {}
    for name in ("serde", "zakuro_common"):
        matches = list(deps.glob(f"lib{name}-*.rlib"))
        if len(matches) != 1:
            raise ValueError(f"Need exactly one host {name} artifact; run the foundation build")
        libraries[name] = matches[0]
    output.mkdir(parents=True, exist_ok=False)
    source = output / "audit.rs"
    source.write_text(harness(checkout, sources), encoding="utf-8")
    steps: list = []
    run_logged("rustc-version", ["rustc", "--version"], output, steps, timeout=30)
    command = ["rustc", "--edition=2021", "-D", "warnings", str(source),
               "-L", f"dependency={deps}", "-o", str(output / "audit")]
    for name, path in libraries.items():
        command.extend(["--extern", f"{name}={path}"])
    run_logged("compile", command, output, steps, timeout=120)
    result = run_logged("execute", [str(output / "audit")], output, steps,
                        timeout=30, separate_stderr=True)
    cases = json.loads(result)
    if len(cases) != 12 or not all(c["extra_page_rejected"] and c["free_restored"] for c in cases):
        raise ValueError("Audit did not complete every allocation control")
    findings = [c["name"] for c in cases if
                c["parsed_new_mode"] != c["input_new_mode"] or
                c["parsed_cpu_speed"] != (c["input_cpu_l2_flags"] >> 1 & 1) or
                c["parsed_l2"] != bool(c["input_cpu_l2_flags"] & 1)]
    if len(findings) != 6:
        raise ValueError("Pinned behavior changed; review the audit findings")
    if verified_sources(checkout)[1] != hashes:
        raise ValueError("Audited sources changed during execution")
    report = {
        "schema": 1, "kind": "droidds-new3ds-source-audit",
        "status": "findings_reproduced", "runtime_revision": REVISION,
        "scope": "actual parser and allocator; extracted loader assignment; no full runtime",
        "format_reference": "3DSGuy/Project_CTR@d52c2b0e788c2d085763d7c5dcc4b2edd9ffb7d8",
        "source_sha256": hashes,
        "artifact_sha256": {name: hashlib.sha256(path.read_bytes()).hexdigest()
                            for name, path in libraries.items()},
        "cases": cases, "parser_mismatch_cases": findings,
        "retail_execution": "not_run", "android_execution": "not_run", "steps": steps,
    }
    (output / "report.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"status": report["status"], "cases": len(cases),
                      "parser_mismatch_cases": findings}, indent=2))


if __name__ == "__main__":
    main()
