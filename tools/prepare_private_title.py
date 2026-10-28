#!/usr/bin/env python3
"""CodexAstraUlt: Prepare identity-bound native sources without executing a title.

Inputs, generated C and module bytes remain in a fresh private directory outside
Git. A prepared manifest is neither an APK nor an enforced runtime binding.
"""

import argparse
import hashlib
import importlib.util
import json
import math
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import signal
import stat
import subprocess
import sys
import time


# CodexAstraUlt: Reuse the established snapshot file checks and process supervisor
# without changing the interpreter worker's interface or evidence schema.
ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("droidds_private_common", ROOT / "tools/run_private_title.py")
COMMON = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(COMMON)
Rejected = COMMON.Rejected
MAX_FILES = 8192
MAX_PREPARED_BYTES = 512 * 1024**2
MAX_FILE_BYTES = COMMON.RESERVE_BYTES
EXPECTED_FIELDS = {
    "schema_version", "kind", "status", "container", "program_id", "ncch_format_version",
    "remaster_version", "cia_title_version", "abi", "generation", "hints", "overlays",
    "runtime_resolution_checked", "runtime_binding_enforced", "components", "segments",
    "bss_size", "artifacts", "sources",
}


def canonical(value):
    """CodexAstraUlt: Stable bytes exclude run timing, host paths and formatting choices."""
    return (json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False) + "\n").encode()


def publish_manifest(directory, encoded):
    """CodexAstraUlt: Publish complete fsynced bytes atomically without replacing a file."""
    temporary = directory / ".manifest.json.tmp"
    COMMON.write_new(temporary, encoded)
    # CodexAstraUlt: Same-directory linking is atomic and refuses an existing
    # final path. A write/fsync failure leaves only the private partial temporary.
    os.link(temporary, directory / "manifest.json", follow_symlinks=False)
    try:
        temporary.unlink()
    except OSError:
        # CodexAstraUlt: The fully written final file is already published;
        # an unsuccessful cleanup may leave its extra link, not partial evidence.
        pass


def read_json(path):
    """CodexAstraUlt: Duplicate keys and nonfinite numbers cannot become identity evidence."""
    def unique(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise Rejected("duplicate_preparation_json_key")
            result[key] = value
        return result

    def nonfinite(_):
        raise Rejected("nonfinite_preparation_json")

    stream, _ = COMMON.open_regular(path, COMMON.MAX_REPORT_BYTES)
    with stream:
        return json.load(stream, object_pairs_hook=unique, parse_constant=nonfinite)


def source_identity():
    """CodexAstraUlt: Bind relevant local sources without claiming binary attestation."""
    identity = COMMON.source_identity()
    paths = [ROOT / "Cargo.toml", ROOT / "rust-toolchain.toml", Path(__file__)]
    for folder in (ROOT / "crates/droidds-title-builder", ROOT / "vendor/3dsrecomp",
                   ROOT / "vendor/zakuro/crates/zakuro-fs"):
        paths += [path for path in folder.rglob("*") if path.is_file() and
                  (path.suffix in (".rs", ".h") or path.name in
                   ("Cargo.toml", "UPSTREAM.json", "hints.txt")) and "target" not in path.parts]
    for path in sorted(set(paths)):
        stream, _ = COMMON.open_regular(path, COMMON.MAX_WORKER_BYTES)
        with stream:
            identity["files_sha256"][str(path.relative_to(ROOT))] = COMMON.stream_digest(
                stream, COMMON.MAX_WORKER_BYTES)[0]
    return identity


def integer(value, name, high=2**32 - 1):
    """CodexAstraUlt: Booleans and negative/overflowing lengths are never scalar metadata."""
    if type(value) is not int or not 0 <= value <= high:
        raise Rejected("invalid_preparation_" + name)
    return value


def relative_path(value, prefix):
    """CodexAstraUlt: Only normalized flat generated/identity paths enter the manifest."""
    if not isinstance(value, str) or not re.fullmatch(prefix + r"/[A-Za-z0-9_.-]+", value):
        raise Rejected("invalid_preparation_path")
    path = PurePosixPath(value)
    if len(path.parts) != 2 or path.parts[-1] in (".", "..") or str(path) != value:
        raise Rejected("invalid_preparation_path")
    return value


def inventory(directory):
    """CodexAstraUlt: Bound every actual output and refuse hidden files, links or devices."""
    COMMON.absolute_plain(directory)
    if not directory.is_dir():
        raise Rejected("missing_preparation_directory")
    result, directories, total = {}, set(), 0
    for base, dirs, files in os.walk(directory, followlinks=False):
        if len(result) + len(directories) + len(dirs) + len(files) > MAX_FILES:
            raise Rejected("preparation_file_limit")
        for name in dirs:
            path = Path(base) / name
            info = path.lstat()
            if not stat.S_ISDIR(info.st_mode):
                raise Rejected("preparation_nonregular_output")
            directories.add(path.relative_to(directory).as_posix())
        for name in files:
            path = Path(base) / name
            info = path.lstat()
            if not stat.S_ISREG(info.st_mode) or info.st_size > MAX_FILE_BYTES:
                raise Rejected("preparation_nonregular_or_oversize_output")
            total += info.st_size
            if total > MAX_PREPARED_BYTES:
                raise Rejected("preparation_total_bytes_limit")
            result[path.relative_to(directory).as_posix()] = info.st_size
    if directories != {"identity", "generated"}:
        raise Rejected("unexpected_preparation_directories")
    return result


def file_identity(directory, item):
    """CodexAstraUlt: Hash real output bytes and verify that the descriptor stayed stable."""
    path = directory / item["path"]
    stream, info = COMMON.open_regular(path, MAX_FILE_BYTES)
    with stream:
        digest, size = COMMON.stream_digest(stream, MAX_FILE_BYTES)
        if size != item["bytes"] or not COMMON.unchanged(path, stream, info, digest, MAX_FILE_BYTES):
            raise Rejected("preparation_artifact_changed")
    return {**item, "sha256": digest}


def validate_preparation(directory, report):
    """CodexAstraUlt: Resolve exactly the reported inputs and outputs before manifest creation."""
    if not isinstance(report, dict) or set(report) != EXPECTED_FIELDS:
        raise Rejected("invalid_preparation_report_fields")
    fixed = {"schema_version": 1, "kind": "droidds_title_preparation", "status": "prepared",
             "abi": 4, "generation": 3, "hints": "disabled", "overlays": [],
             "runtime_resolution_checked": True, "runtime_binding_enforced": False}
    for key, value in fixed.items():
        if type(report[key]) is not type(value) or report[key] != value:
            raise Rejected("invalid_preparation_" + key)
    if report["container"] not in ("ncch", "ncsd", "cia") or not isinstance(report["program_id"], str) or not re.fullmatch(r"[0-9a-f]{16}", report["program_id"]):
        raise Rejected("invalid_preparation_title_identity")
    if report["program_id"][:8] in ("0004000e", "0004008c"):
        raise Rejected("preparation_requires_base_title")
    for name in ("ncch_format_version", "remaster_version"):
        integer(report[name], name, 65535)
    if report["container"] == "cia":
        integer(report["cia_title_version"], "cia_title_version", 65535)
    elif report["cia_title_version"] is not None:
        raise Rejected("invalid_preparation_cia_title_version")
    integer(report["bss_size"], "bss_size")
    components, artifacts = report["components"], report["artifacts"]
    if not isinstance(components, list) or not 3 <= len(components) <= 4099 or not isinstance(artifacts, list) or not 1 <= len(artifacts) <= MAX_FILES:
        raise Rejected("invalid_preparation_inventories")
    expected, kinds, names = {"prepare-report.json"}, {}, set()
    for item in components + artifacts:
        if not isinstance(item, dict):
            raise Rejected("invalid_preparation_artifact")
        path = relative_path(item.get("path"), "identity" if item in components else "generated")
        if path in expected:
            raise Rejected("duplicate_preparation_artifact")
        expected.add(path)
        if integer(item.get("bytes"), "artifact_bytes", MAX_FILE_BYTES) == 0:
            raise Rejected("empty_preparation_artifact")
    for item in components:
        kind = item.get("kind")
        if kind in ("exheader", "decompressed_code", "ncch_header"):
            if set(item) != {"path", "kind", "bytes"} or kind in kinds:
                raise Rejected("invalid_preparation_component")
            kinds[kind] = item
        elif kind in ("cro", "static_crs"):
            if set(item) != {"path", "kind", "bytes", "source_path", "module_name"}:
                raise Rejected("invalid_preparation_module")
            if not isinstance(item["source_path"], str) or not item["source_path"] or not isinstance(item["module_name"], str) or not item["module_name"] or item["module_name"] in names:
                raise Rejected("invalid_preparation_module_identity")
            names.add(item["module_name"])
        else:
            raise Rejected("invalid_preparation_component_kind")
    required = {"exheader": ("identity/exheader.bin", 1024),
                "ncch_header": ("identity/ncch-header.bin", 512),
                "decompressed_code": ("identity/code.bin", None)}
    if set(kinds) != set(required):
        raise Rejected("missing_preparation_component")
    for kind, (path, size) in required.items():
        if kinds[kind]["path"] != path or size is not None and kinds[kind]["bytes"] != size:
            raise Rejected("invalid_preparation_component_identity")
    for item in artifacts:
        if set(item) != {"path", "bytes"} or PurePosixPath(item["path"]).suffix not in (".c", ".h"):
            raise Rejected("invalid_preparation_generated_source")
    sources = report["sources"]
    if not isinstance(sources, list) or not sources or any(not isinstance(path, str) for path in sources) or len(set(sources)) != len(sources) or set(sources) != {item["path"] for item in artifacts if item["path"].endswith(".c")}:
        raise Rejected("invalid_preparation_sources")
    actual = inventory(directory)
    if set(actual) != expected or any(actual[item["path"]] != item["bytes"] for item in components + artifacts):
        raise Rejected("preparation_inventory_mismatch")
    resolved = dict(report)
    resolved["components"] = sorted((file_identity(directory, item) for item in components), key=lambda item: item["path"])
    resolved["artifacts"] = sorted((file_identity(directory, item) for item in artifacts), key=lambda item: item["path"])
    resolved["sources"] = sorted(sources)
    # CodexAstraUlt: Cross-check metadata against its hashed binary descriptors;
    # NCCH format version and exheader remaster version are different fields.
    def descriptor(path):
        stream, _ = COMMON.open_regular(directory / path, MAX_FILE_BYTES)
        with stream:
            data = stream.read()
        expected = next(item["sha256"] for item in resolved["components"] if item["path"] == path)
        if hashlib.sha256(data).hexdigest() != expected:
            raise Rejected("preparation_descriptor_changed")
        return data

    header = descriptor("identity/ncch-header.bin")
    exheader = descriptor("identity/exheader.bin")
    scalar = lambda data, at, width: int.from_bytes(data[at:at + width], "little")
    if header[0x100:0x104] != b"NCCH" or f"{scalar(header, 0x118, 8):016x}" != report["program_id"] or scalar(header, 0x112, 2) != report["ncch_format_version"] or scalar(exheader, 0x0E, 2) != report["remaster_version"] or scalar(exheader, 0x3C, 4) != report["bss_size"]:
        raise Rejected("preparation_descriptor_identity_mismatch")
    segments = report["segments"]
    if not isinstance(segments, list) or len(segments) != 3 or [item.get("name") if isinstance(item, dict) else None for item in segments] != ["text", "rodata", "data"]:
        raise Rejected("invalid_preparation_segments")
    resolved["segments"] = []
    code_path = directory / "identity/code.bin"
    code_stream, code_info = COMMON.open_regular(code_path, MAX_FILE_BYTES)
    with code_stream:
        offset = 0
        for index, item in enumerate(segments):
            if set(item) != {"name", "address", "offset", "size", "mapped_bytes"}:
                raise Rejected("invalid_preparation_segment_fields")
            address = integer(item["address"], "segment_address")
            start = integer(item["offset"], "segment_offset", MAX_FILE_BYTES)
            size = integer(item["size"], "segment_size", MAX_FILE_BYTES)
            mapped = integer(item["mapped_bytes"], "segment_mapped_bytes", MAX_FILE_BYTES)
            descriptor_offset = 0x10 + index * 0x10
            if (address, mapped, size) != (scalar(exheader, descriptor_offset, 4), scalar(exheader, descriptor_offset + 4, 4) * 4096, scalar(exheader, descriptor_offset + 8, 4)):
                raise Rejected("preparation_segment_descriptor_mismatch")
            if start != offset or mapped % 4096 or size > mapped or (size and start + size > kinds["decompressed_code"]["bytes"]) or address + mapped > 2**32:
                raise Rejected("invalid_preparation_segment_layout")
            code_stream.seek(start)
            digest = hashlib.sha256()
            remaining = size
            while remaining:
                block = code_stream.read(min(remaining, COMMON.CHUNK_BYTES))
                if not block:
                    raise Rejected("preparation_segment_truncated")
                digest.update(block)
                remaining -= len(block)
            resolved["segments"].append({**item, "sha256": digest.hexdigest(), "hash_scope": "logical_segment_bytes"})
            offset += mapped
        code_digest = next(item["sha256"] for item in resolved["components"] if item["kind"] == "decompressed_code")
        if not COMMON.unchanged(code_path, code_stream, code_info, code_digest, MAX_FILE_BYTES):
            raise Rejected("preparation_artifact_changed")
    return resolved


def parse_args(argv=None):
    """CodexAstraUlt: Preparation accepts only explicit base input/output and host limits."""
    parser = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--worker", type=Path, default=ROOT / "target/release/droidds-prepare-title")
    parser.add_argument("--timeout", type=float, default=130)
    parser.add_argument("--cpu-seconds", type=int, default=260)
    parser.add_argument("--memory-mib", type=int, default=4096)
    argv = sys.argv[1:] if argv is None else argv
    flags = [item.split("=", 1)[0] for item in argv if item.startswith("--")]
    if len(flags) != len(set(flags)):
        parser.error("duplicate preparation option")
    args = parser.parse_args(argv)
    if not math.isfinite(args.timeout) or not 0 < args.timeout <= 310 or not 1 <= args.cpu_seconds <= COMMON.MAX_CPU_SECONDS or not 256 <= args.memory_mib <= 16384:
        parser.error("host limits outside supported range")
    return args


def run(args):
    """CodexAstraUlt: Success is published only after process, snapshot and output validation."""
    started, directory, code = time.monotonic(), None, 1
    handles, identities = [], []
    report = {"schema_version": 1, "kind": "droidds_private_title_preparation_run", "status": "preparing", "reason": "preflight",
              "requested": {"timeout": args.timeout, "cpu_seconds": args.cpu_seconds, "memory_mib": args.memory_mib},
              "input": None, "worker": None, "process": None, "manifest_sha256": None,
              "evidence": "prepared_sources_only_no_guest_execution_or_APK"}
    try:
        source, output, worker = (COMMON.absolute_plain(path) for path in (args.input, args.output, args.worker))
        COMMON.outside_git(output)
        if source.suffix.lower() not in (".cxi", ".ncch", ".cci", ".3ds", ".cia"):
            raise Rejected("input_must_be_base_ncch_ncsd_or_cia")
        if os.path.lexists(output) or not output.parent.is_dir():
            raise Rejected("output_must_be_absent_with_existing_parent")
        for path, ceiling, label in ((source, COMMON.MAX_INPUT_BYTES, "source"), (worker, COMMON.MAX_WORKER_BYTES, "worker")):
            stream, info = COMMON.open_regular(path, ceiling)
            handles.append(stream)
            digest, _ = COMMON.stream_digest(stream, ceiling)
            identities.append((path, stream, info, digest, ceiling, label))
        if not os.access(worker, os.X_OK):
            raise Rejected("worker_not_executable_build_it_first")
        if shutil.disk_usage(output.parent).free < identities[0][2].st_size + MAX_PREPARED_BYTES:
            raise Rejected("insufficient_disk_space_for_preparation")
        output.mkdir(mode=0o700)
        directory = output
        COMMON.save_report(directory, report)
        source_context = source_identity()
        report["worker"] = {"sha256": identities[1][3], "bytes": identities[1][2].st_size, "source": source_context}
        source_stream = identities[0][1]
        source_stream.seek(0)
        snapshot = output / ("input" + source.suffix.lower())
        fd = os.open(snapshot, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
        # CodexAstraUlt: Copy bounded chunks into a new snapshot; the common
        # fingerprint/hash checks below reject growing or replaced originals.
        with os.fdopen(fd, "wb") as destination:
            count = 0
            while block := source_stream.read(COMMON.CHUNK_BYTES):
                count += len(block)
                if count > identities[0][2].st_size:
                    raise Rejected("source_changed_during_snapshot")
                destination.write(block)
            destination.flush()
            os.fsync(destination.fileno())
        snapshot.chmod(0o400)
        stream, info = COMMON.open_regular(snapshot, COMMON.MAX_INPUT_BYTES)
        handles.append(stream)
        identities.append((snapshot, stream, info, identities[0][3], COMMON.MAX_INPUT_BYTES, "snapshot"))
        report["input"] = {"sha256": identities[0][3], "bytes": identities[0][2].st_size, "snapshot": snapshot.name,
                           "snapshot_read_only": True, "stable_before_run": False, "stable_after_run": False}
        for identity in identities:
            if not COMMON.unchanged(*identity[:5]):
                raise Rejected(identity[5] + "_changed_before_run")
        report["input"]["stable_before_run"] = True
        COMMON.save_report(output, report)
        process = COMMON.run_worker([str(worker), "prepare", "--input", str(snapshot), "--output", str(output / "prepared")], output, args.timeout, args.memory_mib, args.cpu_seconds)
        report["process"] = process
        changed = [item[5] for item in identities if not COMMON.unchanged(*item[:5])]
        report["input"]["stable_after_run"] = not changed
        if changed:
            report.update(status="input_changed", reason="changed_" + "_and_".join(changed))
        elif process["outcome"] != "completed":
            report.update(status=process["outcome"], reason="parent_" + process["outcome"])
            code = 130 if process["outcome"] == "interrupted" else 124
        elif process["exit_code"] != 0:
            report.update(status="worker_failed", reason="worker_signal_" + str(-process["exit_code"]) if process["exit_code"] < 0 else "worker_exit_" + str(process["exit_code"]))
        else:
            resolved = validate_preparation(output / "prepared", read_json(output / "prepared/prepare-report.json"))
            if source_identity() != source_context:
                raise Rejected("preparation_source_changed")
            manifest = {"schema_version": 1, "kind": "droidds_private_title_preparation_manifest", "stage": "prepared",
                        "input": {"sha256": identities[0][3], "bytes": identities[0][2].st_size},
                        "worker": report["worker"], "prepared": resolved,
                        "runtime_binding_enforced": False, "guest_execution_performed": False}
            encoded = canonical(manifest)
            publish_manifest(output, encoded)
            report.update(status="prepared", reason="validated_native_sources", manifest_sha256=hashlib.sha256(encoded).hexdigest())
            code = 0
    except KeyboardInterrupt:
        report.update(status="interrupted", reason="coordinator_interrupted")
        code = 130
    except (Rejected, OSError, ValueError, KeyError, TypeError, subprocess.SubprocessError) as error:
        report.update(status="rejected", reason=str(error) if isinstance(error, Rejected) else type(error).__name__)
    finally:
        for stream in handles:
            stream.close()
        report["elapsed_seconds"] = time.monotonic() - started
        if directory is not None:
            COMMON.save_report(directory, report)
    return code, report


def main(argv=None):
    """CodexAstraUlt: Preserve interrupted preparation and print only a compact status."""
    args = parse_args(argv)
    def interrupted(_signum, _frame):
        raise KeyboardInterrupt
    previous = signal.signal(signal.SIGTERM, interrupted)
    try:
        code, report = run(args)
    finally:
        signal.signal(signal.SIGTERM, previous)
    print(json.dumps({"status": report["status"], "reason": report["reason"],
                      "report": str(args.output / "report.json") if args.output.is_dir() else None}))
    return code


if __name__ == "__main__":
    raise SystemExit(main())
