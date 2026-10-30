#!/usr/bin/env python3
"""CodexAstraUlt: Bound and resume ARM64 Android compilation of admitted title C.

The six historical host compilation helpers remain unchanged. A private adapter
reuses their serial jobs, locks, snapshots, receipts and resource supervision,
with a distinct pinned NDK/Bionic recipe and full static runtime-table audit.
No generated library is loaded and no private game data enters an APK here.
"""

from contextlib import contextmanager
import argparse
import hashlib
import importlib.util
import json
import math
import os
from pathlib import Path
import platform
import re
import signal
import sys


ROOT = Path(__file__).resolve().parents[1]
NDK_VERSION = "27.3.13750724"
TARGET = "aarch64-linux-android"
MINIMUM_API = 29
SONAME = "libdroidds_title.so"


def _load(name):
    spec = importlib.util.spec_from_file_location("android_compile_" + name, ROOT / "tools" / (name + ".py"))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


BASE = _load("compile_private_title")
RUNTIME_INPUTS = _load("private_runtime_inputs")
ANDROID_ELF = _load("android_title_elf")
PREP, COMMON, INPUTS, PROCESS = BASE.PREP, BASE.COMMON, BASE.INPUTS, BASE.PROCESS
Rejected, MIB = BASE.Rejected, BASE.MIB


def require(condition, reason):
    if not condition:
        raise Rejected(reason)


def _tree_identity(root):
    """CodexAstraUlt: Bind NDK headers by names and bytes without exporting them."""
    records, total = [], 0
    for path in sorted(root.rglob("*")):
        require(not path.is_symlink(), "Android NDK header symlink is unsupported")
        if path.is_dir():
            continue
        record = BASE.identity(path, 16 * MIB)
        total += record["bytes"]
        require(len(records) < 16384 and total <= 256 * MIB, "Android NDK header inventory exceeds bound")
        records.append({"path": path.relative_to(root).as_posix(), **record})
    require(records, "Android NDK header inventory is empty")
    return {"files": len(records), "bytes": total,
            "sha256": hashlib.sha256(PREP.canonical(records)).hexdigest()}


def inspect_android_compiler(path):
    """CodexAstraUlt: The pinned NDK wrapper and all direct binaries are bound."""
    require(platform.system() == "Linux" and platform.machine() == "x86_64",
            "Android compiler currently requires Linux x86_64 host")
    selected = COMMON.absolute_plain(path)
    require(selected.name == "aarch64-linux-android29-clang", "Android compiler wrapper target mismatch")
    binary = selected.parent
    llvm = binary.parent
    ndk = llvm.parents[3]
    require(llvm.name == "linux-x86_64" and ndk.name == NDK_VERSION, "Android NDK path/version mismatch")
    properties = ndk / "source.properties"
    properties_identity = BASE.identity(properties, MIB)
    with COMMON.open_regular(properties, MIB)[0] as stream:
        raw = stream.read(MIB + 1)
    require(len(raw) == properties_identity["bytes"]
            and hashlib.sha256(raw).hexdigest() == properties_identity["sha256"],
            "Android NDK properties changed during inspection")
    data = raw.decode("utf-8")
    require(re.search(r"(?m)^Pkg\.Revision\s*=\s*" + re.escape(NDK_VERSION) + r"\s*$", data),
            "Android NDK revision mismatch")
    environment = PROCESS.clean_environment()
    tools = {name: PROCESS._tool(path, environment) for name, path in
             (("wrapper", selected), ("driver", binary / "clang"), ("linker", binary / "ld.lld"))}
    for name in ("driver", "linker"):
        require(Path(tools[name]["path"]).is_relative_to(llvm), "Android compiler helper escapes pinned NDK")

    def query(*flags):
        value = PROCESS.run_command([str(selected), "--no-default-config", *flags], ROOT,
                                    10, 10, 1024, MIB, environment)
        require(value["outcome"] == "completed" and value["exit_code"] == 0
                and value["log_bytes_seen"] <= PROCESS.LOG_BYTES, "Android compiler metadata query failed")
        return value["log_tail"].strip()

    version, target = query("--version"), query("-dumpmachine")
    require("Android" in version and "clang version" in version, "selected compiler is not Android NDK clang")
    require(target == "aarch64-unknown-linux-android29", "Android compiler effective target mismatch")
    resource = Path(query("-print-resource-dir")).resolve(strict=True)
    require(resource.is_relative_to(llvm), "Android clang resources escape pinned NDK")
    sysroot = llvm / "sysroot"
    runtime_files = [sysroot / "usr/lib/aarch64-linux-android/29" / name for name in
                     ("libc.so", "libm.so", "libdl.so", "crtbegin_so.o", "crtend_so.o")]
    runtime_files.append(resource / "lib/linux/libclang_rt.builtins-aarch64-android.a")
    runtime = {path.relative_to(llvm).as_posix(): BASE.identity(path, PROCESS.MAX_TOOL_BYTES)
               for path in runtime_files}
    identity = {"schema_version": 1, "family": "clang", "version": version, "target": target,
                "host_arch": "x86_64", "ndk": NDK_VERSION, "minimum_api": MINIMUM_API,
                "tools": tools, "properties": properties_identity,
                "headers": {"sysroot": _tree_identity(sysroot / "usr/include"),
                            "clang": _tree_identity(resource / "include")},
                "runtime_files": runtime, "binary_source_attested": False}
    require(all(PROCESS._tool(record["path"], environment) == record for record in tools.values()),
            "Android compiler changed during inspection")
    return {"invocation": str(selected), "identity": identity}


def coordinator_identity():
    """CodexAstraUlt: Receipts bind adapter and reused audit/engine implementations."""
    names = ("compile_android_title", "android_title_elf", "compile_private_title",
             "private_compile_inputs", "private_compile_process", "private_compile_elf",
             "private_runtime_inputs", "private_runtime_elf", "prepare_private_title", "run_private_title")
    return {name + ".py": BASE.identity(ROOT / "tools" / (name + ".py"), BASE.MAX_JSON)["sha256"]
            for name in names}


def make_plan(loaded, compiler):
    """CodexAstraUlt: Cross-target receipts can never be reused as host objects."""
    identity = compiler["identity"]
    require(identity.get("ndk") == NDK_VERSION and identity.get("minimum_api") == MINIMUM_API
            and identity.get("target") == "aarch64-unknown-linux-android29", "Android compiler identity mismatch")
    flags = ["--no-default-config", *BASE.COMPILE_FLAGS]
    link = ["--no-default-config", "-fuse-ld=" + str(Path(identity["tools"]["wrapper"]["path"]).parent / "ld.lld"),
            *BASE.LINK_FLAGS, "-Wl,-z,max-page-size=16384", "-Wl,-z,common-page-size=16384",
            "-Wl,--pack-dyn-relocs=none"]
    contract = {"schema_version": 1, "kind": "droidds_android_compile_contract",
                "preparation_sha256": loaded["manifest_sha256"], "input": loaded["manifest"]["input"],
                "program_id": loaded["manifest"]["prepared"]["program_id"], "abi": 4, "generation": 3,
                "module_count": loaded["module_count"], "generated": loaded["generated"], "sources": loaded["sources"],
                "compiler": identity, "coordinator": coordinator_identity(), "machine": 183,
                "target": TARGET, "minimum_api": MINIMUM_API, "ndk": NDK_VERSION, "libc": "bionic",
                "compile_flags": flags, "link_flags": link, "link_libraries": ["-lm"], "library_name": SONAME,
                "toolchain_hermetic": False, "runtime_binding_enforced": False}
    digest = BASE.digest_bytes(PREP.canonical(contract))
    binding = BASE.binding_source(loaded["manifest_sha256"], digest)
    return {"schema_version": 1, "kind": "droidds_android_compile_plan", "contract": contract,
            "contract_sha256": digest, "binding": {"path": "binding/identity.c", "bytes": len(binding),
                                                     "sha256": BASE.digest_bytes(binding)}}


def _manifest(preparation, root, library, plan, loaded, receipts, jobs):
    """CodexAstraUlt: Full pointer/origin validation precedes Android success."""
    before = BASE.identity(library, BASE.LIBRARY_BYTES)
    _, units = RUNTIME_INPUTS.component_inventory(preparation, loaded["manifest"]["prepared"])
    audit = ANDROID_ELF.audit_library(library, loaded["manifest_sha256"], plan["contract_sha256"], units)
    require(BASE.identity(library, BASE.LIBRARY_BYTES) == before
            and audit["library_sha256"] == before["sha256"], "Android library changed during static audit")
    return {"schema_version": 1, "kind": "droidds_android_title_compiled_manifest", "stage": "compiled",
            "preparation_sha256": loaded["manifest_sha256"], "contract_sha256": plan["contract_sha256"],
            "input": loaded["manifest"]["input"], "abi": 4, "generation": 3, "target": TARGET,
            "minimum_api": MINIMUM_API, "ndk": NDK_VERSION,
            "objects": [receipts[job["index"]] for job in jobs],
            "library": {"path": library.relative_to(root).as_posix(), **before}, "elf": audit,
            "library_loaded": False, "guest_execution_performed": False, "runtime_binding_enforced": False}


def _engine(preparation):
    """CodexAstraUlt: Adapt a private engine instance; host imports stay untouched."""
    engine = _load("compile_private_title")
    engine.PROCESS.inspect_compiler = inspect_android_compiler
    engine.ELF = ANDROID_ELF
    engine.make_plan = make_plan
    engine.coordinator_identity = coordinator_identity
    engine.compiled_manifest = lambda root, library, plan, loaded, receipts, jobs: _manifest(
        preparation, root, library, plan, loaded, receipts, jobs)
    return engine


def _recorded_compiler(value):
    """CodexAstraUlt: Package admission consumes provenance without running NDK."""
    required = {"schema_version", "family", "version", "target", "host_arch", "ndk", "minimum_api",
                "tools", "properties", "headers", "runtime_files", "binary_source_attested"}
    require(isinstance(value, dict) and set(value) == required and type(value["schema_version"]) is int
            and value["schema_version"] == 1 and value["family"] == "clang"
            and value["host_arch"] == "x86_64" and value["ndk"] == NDK_VERSION
            and type(value["minimum_api"]) is int and value["minimum_api"] == MINIMUM_API
            and value["target"] == "aarch64-unknown-linux-android29"
            and value["binary_source_attested"] is False, "invalid recorded Android compiler")
    require(isinstance(value["version"], str) and 0 < len(value["version"]) <= 65536
            and "\0" not in value["version"], "invalid recorded Android compiler version")
    require(isinstance(value["tools"], dict) and set(value["tools"]) == {"wrapper", "driver", "linker"},
            "invalid Android tool inventory")
    runtime_names = {"sysroot/usr/lib/aarch64-linux-android/29/" + name for name in
                     ("libc.so", "libm.so", "libdl.so", "crtbegin_so.o", "crtend_so.o")}
    runtime_names.add("lib/clang/18/lib/linux/libclang_rt.builtins-aarch64-android.a")
    require(isinstance(value["runtime_files"], dict) and set(value["runtime_files"]) == runtime_names,
            "invalid Android runtime file inventory")
    require(isinstance(value["headers"], dict) and set(value["headers"]) == {"sysroot", "clang"},
            "invalid Android header inventory")
    for record in [value["properties"], *value["runtime_files"].values()]:
        require(isinstance(record, dict) and set(record) == {"bytes", "sha256"}
                and type(record["bytes"]) is int and 0 < record["bytes"] <= PROCESS.MAX_TOOL_BYTES
                and INPUTS._sha256(record["sha256"]), "invalid recorded Android support bytes")
    for record in value["tools"].values():
        require(isinstance(record, dict) and set(record) in ({"bytes", "sha256"}, {"path", "bytes", "sha256"})
                and type(record["bytes"]) is int and 0 < record["bytes"] <= PROCESS.MAX_TOOL_BYTES
                and INPUTS._sha256(record["sha256"]), "invalid recorded Android tool bytes")
        require(isinstance(record.get("path"), str) and record["path"].startswith("/")
                and len(record["path"]) <= 4096 and "\0" not in record["path"], "invalid recorded Android tool path")
    for record in value["headers"].values():
        require(isinstance(record, dict) and set(record) == {"files", "bytes", "sha256"}
                and type(record["files"]) is int and 0 < record["files"] <= 16384
                and type(record["bytes"]) is int and 0 < record["bytes"] <= 256 * MIB
                and INPUTS._sha256(record["sha256"]), "invalid recorded Android headers")
    return {"identity": value}


def _admission(preparation):
    module = _load("private_runtime_inputs")
    module.COMPILE = _engine(COMMON.absolute_plain(preparation))
    module._recorded_compiler = _recorded_compiler
    return module


@contextmanager
def admitted_android_inputs(preparation, compilation):
    """CodexAstraUlt: Hold the unchanged serial engine's shared artifact lock."""
    with _admission(preparation).admitted_inputs(preparation, compilation) as admitted:
        yield admitted


def verify_unchanged(admitted):
    return _admission(admitted["preparation_path"]).verify_unchanged(admitted)


def title_manifest(admitted):
    """CodexAstraUlt: Only bounded identity metadata is packaged, never game bytes."""
    prepared = admitted["prepared"]
    library = admitted["compiled_manifest"]["library"]
    value = {"schema_version": 1, "kind": "droidds_android_title", "program_id": prepared["program_id"],
             "input": admitted["loaded"]["manifest"]["input"],
             "native": {"file": SONAME, "bytes": library["bytes"], "sha256": library["sha256"]},
             "abi": 4, "generation": 3, "prepared": {name: prepared[name] for name in
                ("container", "ncch_format_version", "remaster_version", "cia_title_version",
                 "bss_size", "segments", "components")}}
    require(len(PREP.canonical(value)) <= MIB, "Android title manifest exceeds bound")
    return value


def parse_args(argv=None):
    """CodexAstraUlt: Pin target/toolchain while preserving existing batch limits."""
    parser = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    parser.add_argument("--preparation", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--sdk", type=Path, default=os.environ.get("ANDROID_HOME"))
    parser.add_argument("--resume", action="store_true")
    for name, kind, default in (("batch-seconds", float, 1800), ("command-seconds", float, 300),
                                ("cpu-seconds", int, 260), ("memory-mib", int, 4096), ("output-mib", int, 4096)):
        parser.add_argument("--" + name, type=kind, default=default)
    values = sys.argv[1:] if argv is None else argv
    flags = [word.split("=", 1)[0] for word in values if word.startswith("--")]
    if len(flags) != len(set(flags)):
        parser.error("duplicate Android compile option")
    args = parser.parse_args(values)
    if args.sdk is None:
        parser.error("--sdk or ANDROID_HOME is required")
    if (not math.isfinite(args.batch_seconds) or not 0 < args.batch_seconds <= 7200
            or not math.isfinite(args.command_seconds) or not 0 < args.command_seconds <= 1800
            or not 1 <= args.cpu_seconds <= 1800 or not 256 <= args.memory_mib <= 16384
            or not 64 <= args.output_mib <= 8192):
        parser.error("Android compilation limits outside supported range")
    args.cc = args.sdk / "ndk" / NDK_VERSION / "toolchains/llvm/prebuilt/linux-x86_64/bin/aarch64-linux-android29-clang"
    return args


def run(args):
    engine = _engine(COMMON.absolute_plain(args.preparation))
    code, report = engine.run(args)
    report.update(kind="droidds_android_title_compile_run", target=TARGET, minimum_api=MINIMUM_API, ndk=NDK_VERSION)
    if report["reason"] in ("validated_host_library", "verified_existing_host_library"):
        report["reason"] = report["reason"].replace("host_library", "Android_library")
    if "report_path" in report:
        COMMON.save_report(Path(report["report_path"]).parent, report)
    return code, report


def main(argv=None):
    args = parse_args(argv)
    def interrupted(_number, _frame):
        raise KeyboardInterrupt
    previous = signal.signal(signal.SIGTERM, interrupted)
    try:
        code, report = run(args)
    finally:
        signal.signal(signal.SIGTERM, previous)
    print(json.dumps({key: report.get(key) for key in
                      ("status", "reason", "objects_ready", "objects_total", "report_path", "target")}))
    return code


if __name__ == "__main__":
    raise SystemExit(main())
