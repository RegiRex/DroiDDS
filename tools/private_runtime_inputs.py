#!/usr/bin/env python3
"""CodexAstraUlt: Admit retained native-build identities without loading code.

The caller must additionally audit runtime pointer tables and seal the library
before loading it. This module never invokes a compiler, changes old manifests,
or treats a content hash as a source-to-binary attestation.
"""

from contextlib import contextmanager
import fcntl
import hashlib
import importlib.util
import os
from pathlib import Path
import platform
import re
import stat
import struct


# CodexAstraUlt: Reuse the frozen compilation/preparation validators rather than
# weakening their identities or changing the tool hashes in existing receipts.
SPEC = importlib.util.spec_from_file_location(
    "droidds_runtime_compile", Path(__file__).with_name("compile_private_title.py"))
COMPILE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(COMPILE)
PREP, COMMON, INPUTS = COMPILE.PREP, COMPILE.COMMON, COMPILE.INPUTS
Rejected = COMPILE.Rejected
MAX_COMPONENT_BYTES = 320 * 1024**2 + 1536
MAX_MODULE_BYTES = 256 * 1024**2
MAX_MODULES = 4096


def _require(condition, reason):
    """CodexAstraUlt: Admission failures remain explicit before native loading."""
    if not condition:
        raise Rejected(reason)


def _recorded_compiler(value):
    """CodexAstraUlt: Validate historical provenance without reopening its tools."""
    _require(isinstance(value, dict) and set(value) == {
        "schema_version", "family", "version", "target", "host_arch", "tools",
        "binary_source_attested"}, "invalid_recorded_compiler")
    _require(type(value["schema_version"]) is int and value["schema_version"] == 1
             and value["binary_source_attested"] is False, "invalid_recorded_compiler")
    family, host = value["family"], value["host_arch"]
    _require(family in ("gcc", "clang") and host in ("x86_64", "aarch64"),
             "unsupported_recorded_compiler")
    _require(platform.system() == "Linux" and host == platform.machine(),
             "compiled_library_host_mismatch")
    version, target = value["version"], value["target"]
    _require(isinstance(version, str) and 0 < len(version.encode()) <= 65536
             and "\0" not in version, "invalid_recorded_compiler_version")
    _require(isinstance(target, str) and 0 < len(target) <= 128
             and target.startswith(host + "-") and "linux" in target
             and re.fullmatch(r"[A-Za-z0-9_.+\-]+", target) is not None,
             "invalid_recorded_compiler_target")
    tools = value["tools"]
    expected = {"driver", "cc1", "as", "collect2", "ld"} if family == "gcc" else {"driver", "ld"}
    _require(isinstance(tools, dict) and set(tools) == expected,
             "invalid_recorded_compiler_tools")
    for record in tools.values():
        _require(isinstance(record, dict) and set(record) == {"path", "bytes", "sha256"},
                 "invalid_recorded_compiler_tool")
        _require(isinstance(record["path"], str) and record["path"].startswith("/")
                 and 0 < len(record["path"].encode()) <= 4096 and "\0" not in record["path"]
                 and type(record["bytes"]) is int and 0 < record["bytes"] <= COMPILE.PROCESS.MAX_TOOL_BYTES
                 and INPUTS._sha256(record["sha256"]), "invalid_recorded_compiler_tool")
    return {"identity": value}


def _readonly(path):
    """CodexAstraUlt: Native artifacts must retain their build-time read-only state."""
    path = COMMON.absolute_plain(path)
    info = path.lstat()
    _require(stat.S_ISREG(info.st_mode) and not info.st_mode & 0o222,
             "runtime_artifact_must_be_readonly")
    return path


def _read_component(path, record):
    """CodexAstraUlt: Materialize one bounded identity component with stable bytes."""
    stream, info = COMMON.open_regular(path, PREP.MAX_FILE_BYTES)
    with stream:
        data = stream.read(PREP.MAX_FILE_BYTES + 1)
        _require(len(data) == record["bytes"] and hashlib.sha256(data).hexdigest() == record["sha256"],
                 "runtime_component_identity_changed")
        INPUTS._unchanged_stat(path, stream, info)
    return data


def _cro_text(data):
    """CodexAstraUlt: Resolve the one code segment supported by strict preparation."""
    _require(len(data) >= 0xD0 and data[0x80:0x84] == b"CRO0", "invalid_runtime_cro_header")
    table, count = struct.unpack_from("<II", data, 0xC8)
    _require(0 < count <= 16 and table <= len(data)
             and count * 12 <= len(data) - table, "invalid_runtime_cro_segments")
    code = None
    for index in range(count):
        offset, size, kind = struct.unpack_from("<III", data, table + index * 12)
        # CodexAstraUlt: Only code rows are materialized here. The strict
        # preparer and runtime resolver separately validate the complete module.
        if kind == 0 and size:
            _require(offset <= len(data) and size <= len(data) - offset,
                     "runtime_cro_code_outside_file")
            # CodexAstraUlt: Reject duplicate code rows before copying any
            # payload; overlapping rows cannot multiply a bounded input's RAM.
            _require(code is None, "runtime_cro_requires_one_code_segment")
            code = (offset, size)
    _require(code is not None, "runtime_cro_requires_one_code_segment")
    offset, size = code
    return offset, data[offset:offset + size]


def component_inventory(preparation, prepared):
    """CodexAstraUlt: Bind sealed-bundle offsets and ordered ABI executable units.

    Component files remain privately owned preparation data; the coordinator
    copies these exact hashes into a sealed bundle before starting its worker.
    """
    records, units, module_indices, module_total, total = [], [], [], 0, 0
    base_text = prepared["segments"][0]
    modules = []
    for item in prepared["components"]:
        path = COMMON.absolute_plain(preparation / "prepared" / item["path"])
        data = _read_component(path, item)
        total += len(data)
        _require(total <= MAX_COMPONENT_BYTES, "runtime_component_total_exceeds_bound")
        record = {**item, "full_path": path, "offset": total - len(data)}
        records.append(record)
        if item["kind"] == "decompressed_code":
            offset, size = base_text["offset"], base_text["size"]
            _require(0 < size <= len(data) and offset <= len(data) - size,
                     "runtime_base_text_outside_code")
            units.insert(0, {"name": None, "text_start": base_text["address"],
                             "text": data[offset:offset + size]})
        elif item["kind"] in ("cro", "static_crs"):
            match = re.fullmatch(r"identity/module-([0-9]{4})\.bin", item["path"])
            _require(match is not None, "invalid_runtime_module_component_path")
            index = int(match.group(1))
            module_indices.append(index)
            module_total += len(data)
            _require(module_total <= MAX_MODULE_BYTES, "runtime_module_total_exceeds_bound")
            for key in ("source_path", "module_name"):
                value = item[key]
                _require(isinstance(value, str) and 0 < len(value.encode()) <= 4096 and "\0" not in value,
                         "invalid_runtime_module_identity")
            if item["kind"] == "cro":
                text_start, text = _cro_text(data)
                modules.append((index, {"name": item["module_name"], "text_start": text_start, "text": text}))
    _require(len(units) == 1 and sorted(module_indices) == list(range(len(module_indices)))
             and len(module_indices) <= MAX_MODULES, "invalid_runtime_unit_inventory")
    units.extend(unit for _, unit in sorted(modules))
    return records, units


def _json(path):
    """CodexAstraUlt: Metadata must be canonical, bounded and stable while read."""
    return INPUTS._json_record(path, COMPILE.MAX_JSON, True)


def load_compiled(preparation, compilation):
    """CodexAstraUlt: Revalidate completed compilation without compiler discovery.

    Call admitted_inputs for a shared compilation lock through sealing/running.
    Returned units contain private original text and must never enter reports.
    """
    preparation, compilation = (COMMON.absolute_plain(path) for path in (preparation, compilation))
    COMMON.outside_git(preparation)
    COMMON.outside_git(compilation)
    _require(preparation.is_dir() and compilation.is_dir()
             and preparation != compilation and preparation not in compilation.parents
             and compilation not in preparation.parents, "invalid_runtime_input_directories")
    # CodexAstraUlt: Retain the success record's exact snapshot selector before
    # lengthy validation, rather than trusting a later reread of mutable JSON.
    report, _, report_stat = INPUTS._json_record(preparation / "report.json", COMMON.MAX_REPORT_BYTES)
    _, preparation_sha256, preparation_stat = _json(preparation / "manifest.json")
    loaded = INPUTS.load_preparation(preparation)
    _require(loaded["manifest_sha256"] == preparation_sha256,
             "runtime_preparation_changed_during_admission")
    prepared = loaded["manifest"]["prepared"]
    plan, plan_sha256, plan_stat = _json(compilation / "compile-plan.json")
    _require(isinstance(plan, dict) and set(plan) == {"schema_version", "kind", "contract", "contract_sha256", "binding"}
             and isinstance(plan.get("contract"), dict), "invalid_runtime_compile_plan")
    compiler = _recorded_compiler(plan["contract"].get("compiler"))
    expected_plan = COMPILE.make_plan(loaded, compiler)
    _require(PREP.canonical(plan) == PREP.canonical(expected_plan), "runtime_compile_plan_mismatch")
    COMPILE.verify_inputs(compilation, loaded, plan)
    _readonly(compilation / plan["binding"]["path"])
    jobs = COMPILE.jobs_for(plan)
    receipts = COMPILE.existing_receipts(compilation, plan, jobs)
    _require(len(receipts) == len(jobs), "runtime_compile_missing_objects")
    for receipt in receipts.values():
        _readonly(compilation / receipt["object"]["path"])
    manifest, manifest_sha256, manifest_stat = _json(compilation / "compiled-manifest.json")
    _require(isinstance(manifest, dict) and isinstance(manifest.get("library"), dict)
             and isinstance(manifest["library"].get("path"), str), "invalid_runtime_compiled_manifest")
    library = COMPILE.owned_path(compilation, manifest["library"]["path"],
                                 r"attempts/[0-9]{6}/link/libdroidds_title\.so")
    _readonly(library)
    actual = COMPILE.compiled_manifest(compilation, library, plan, loaded, receipts, jobs)
    _require(PREP.canonical(manifest) == PREP.canonical(actual), "runtime_compiled_manifest_mismatch")
    snapshot_name = report.get("input", {}).get("snapshot") if isinstance(report, dict) else None
    _require(isinstance(snapshot_name, str) and re.fullmatch(r"input\.(?:cxi|ncch|cci|3ds|cia)", snapshot_name) is not None,
             "invalid_runtime_snapshot_path")
    snapshot = _readonly(preparation / snapshot_name)
    _require(INPUTS._file_identity(snapshot, COMMON.MAX_INPUT_BYTES) == loaded["manifest"]["input"],
             "runtime_snapshot_identity_changed")
    components, units = component_inventory(preparation, prepared)
    _require(len(units) == loaded["module_count"] + 1, "runtime_module_count_mismatch")
    for path, fingerprint in ((compilation / "compile-plan.json", plan_stat),
                              (compilation / "compiled-manifest.json", manifest_stat),
                              (preparation / "report.json", report_stat),
                              (preparation / "manifest.json", preparation_stat)):
        _require(COMMON.fingerprint(COMMON.absolute_plain(path).lstat()) == fingerprint,
                 "runtime_compile_metadata_changed")
    return {"preparation_path": preparation, "compilation_path": compilation,
            "loaded": loaded, "plan": plan, "plan_sha256": plan_sha256,
            "compiled_manifest": manifest, "compiled_manifest_sha256": manifest_sha256,
            "library_path": library, "snapshot_path": snapshot, "prepared": prepared,
            "components": components, "units": units}


def verify_unchanged(admitted):
    """CodexAstraUlt: A later run cannot silently qualify edited retained evidence."""
    current = load_compiled(admitted["preparation_path"], admitted["compilation_path"])
    for name in ("plan_sha256", "compiled_manifest_sha256"):
        _require(current[name] == admitted[name], "runtime_inputs_changed_after_admission")
    _require(current["loaded"]["manifest_sha256"] == admitted["loaded"]["manifest_sha256"],
             "runtime_preparation_changed_after_admission")
    return True


@contextmanager
def admitted_inputs(preparation, compilation):
    """CodexAstraUlt: Prevent a normal compile/resume from modifying an active run."""
    compilation = COMMON.absolute_plain(compilation)
    COMMON.outside_git(compilation)
    lock_path = COMMON.absolute_plain(compilation / ".compile.lock")
    descriptor = None
    try:
        descriptor = os.open(lock_path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK | os.O_CLOEXEC)
        before = os.fstat(descriptor)
        _require(stat.S_ISREG(before.st_mode), "invalid_runtime_compile_lock")
        try:
            fcntl.flock(descriptor, fcntl.LOCK_SH | fcntl.LOCK_NB)
        except BlockingIOError as error:
            raise Rejected("compile_directory_in_use") from error
        admitted = load_compiled(preparation, compilation)
        _require(COMMON.fingerprint(lock_path.lstat()) == COMMON.fingerprint(before),
                 "runtime_compile_lock_changed")
        yield admitted
        _require(COMMON.fingerprint(lock_path.lstat()) == COMMON.fingerprint(before),
                 "runtime_compile_lock_changed")
    finally:
        if descriptor is not None:
            os.close(descriptor)
