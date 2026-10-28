#!/usr/bin/env python3
"""CodexAstraUlt: Consume prepared source identity without executing private code.

These checks bind local files to the retained preparation record. They do not
attest the preparer binary, sandbox generated C, or enforce a runtime identity.
"""

import hashlib
import importlib.util
import os
from pathlib import Path
import re


# CodexAstraUlt: Reuse the preparation validator, including descriptor/segment
# consistency, instead of inventing a weaker compiler-only artifact inventory.
SPEC = importlib.util.spec_from_file_location(
    "droidds_compile_preparation", Path(__file__).with_name("prepare_private_title.py"))
PREP = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(PREP)
COMMON = PREP.COMMON
Rejected = PREP.Rejected
MAX_MANIFEST_BYTES = 8 * 1024**2
MANIFEST_FIELDS = {
    "schema_version", "kind", "stage", "input", "worker", "prepared",
    "runtime_binding_enforced", "guest_execution_performed",
}


def _sha256(value):
    """CodexAstraUlt: Only a complete lowercase digest can bind retained data."""
    return isinstance(value, str) and re.fullmatch(r"[0-9a-f]{64}", value) is not None


def _unchanged_stat(path, stream, before):
    """CodexAstraUlt: Bound reads detect replacement and edits without a second full read."""
    COMMON.absolute_plain(path)
    if (COMMON.fingerprint(path.lstat()) != COMMON.fingerprint(before)
            or COMMON.fingerprint(os.fstat(stream.fileno())) != COMMON.fingerprint(before)):
        raise Rejected("preparation_input_changed")


def _file_identity(path, ceiling):
    """CodexAstraUlt: Stream large snapshots and sources with stable file identity."""
    stream, info = COMMON.open_regular(path, ceiling)
    with stream:
        digest, size = COMMON.stream_digest(stream, ceiling)
        _unchanged_stat(path, stream, info)
    return {"sha256": digest, "bytes": size}


def _json_record(path, ceiling, canonical=False):
    """CodexAstraUlt: Retain canonical identity while rejecting duplicate/nonfinite JSON."""
    stream, info = COMMON.open_regular(path, ceiling)
    with stream:
        raw = stream.read(ceiling + 1)
        if len(raw) > ceiling:
            raise Rejected("preparation_json_exceeds_bound")
        value = PREP.read_json(path, ceiling)
        digest = hashlib.sha256(raw).hexdigest()
        if not COMMON.unchanged(path, stream, info, digest, ceiling):
            raise Rejected("preparation_input_changed")
    if canonical and raw != PREP.canonical(value):
        raise Rejected("preparation_manifest_not_canonical")
    return value, digest, COMMON.fingerprint(info)


def _worker_identity(worker):
    """CodexAstraUlt: Preserve recorded source provenance without requiring today's checkout."""
    if (not isinstance(worker, dict) or set(worker) != {"sha256", "bytes", "source"}
            or not _sha256(worker["sha256"])):
        raise Rejected("invalid_preparation_worker_identity")
    if not 0 < PREP.integer(worker["bytes"], "worker_bytes", COMMON.MAX_WORKER_BYTES):
        raise Rejected("invalid_preparation_worker_identity")
    source = worker["source"]
    if (not isinstance(source, dict) or source.get("binary_source_attested") is not False
            or not isinstance(source.get("checkout_commit"), str)
            or re.fullmatch(r"[0-9a-f]{40}", source["checkout_commit"]) is None
            or type(source.get("checkout_dirty")) is not bool):
        raise Rejected("invalid_preparation_source_identity")
    hashes = source.get("files_sha256")
    if not isinstance(hashes, dict) or not 1 <= len(hashes) <= 8192:
        raise Rejected("invalid_preparation_source_hashes")
    for name, digest in hashes.items():
        if (not isinstance(name, str) or not 0 < len(name) <= 4096
                or name.startswith("/") or ".." in Path(name).parts
                or not _sha256(digest)):
            raise Rejected("invalid_preparation_source_hashes")


def load_preparation(directory):
    """CodexAstraUlt: Revalidate a successful preparation and its unchanged input snapshot."""
    directory = COMMON.absolute_plain(directory)
    COMMON.outside_git(directory)
    if not directory.is_dir():
        raise Rejected("missing_preparation_directory")
    manifest, digest, manifest_stat = _json_record(directory / "manifest.json", MAX_MANIFEST_BYTES, True)
    if (not isinstance(manifest, dict) or set(manifest) != MANIFEST_FIELDS
            or type(manifest["schema_version"]) is not int or manifest["schema_version"] != 1
            or manifest["kind"] != "droidds_private_title_preparation_manifest"
            or manifest["stage"] != "prepared"
            or manifest["runtime_binding_enforced"] is not False
            or manifest["guest_execution_performed"] is not False):
        raise Rejected("invalid_preparation_manifest_contract")
    source = manifest["input"]
    if (not isinstance(source, dict) or set(source) != {"sha256", "bytes"}
            or not _sha256(source["sha256"])
            or not 0 < PREP.integer(source["bytes"], "input_bytes", COMMON.MAX_INPUT_BYTES)):
        raise Rejected("invalid_preparation_input_identity")
    _worker_identity(manifest["worker"])
    report, _, report_stat = _json_record(directory / "report.json", COMMON.MAX_REPORT_BYTES)
    if (not isinstance(report, dict) or type(report.get("schema_version")) is not int
            or report["schema_version"] != 1
            or report.get("kind") != "droidds_private_title_preparation_run"
            or report.get("status") != "prepared" or report.get("reason") != "validated_native_sources"
            or report.get("manifest_sha256") != digest
            or PREP.canonical(report.get("worker")) != PREP.canonical(manifest["worker"])):
        raise Rejected("preparation_success_record_mismatch")
    process = report.get("process")
    if (not isinstance(process, dict) or process.get("outcome") != "completed"
            or type(process.get("exit_code")) is not int or process["exit_code"] != 0):
        raise Rejected("preparation_worker_did_not_complete")
    recorded_input = report.get("input")
    if (not isinstance(recorded_input, dict)
            or type(recorded_input.get("bytes")) is not int
            or any(recorded_input.get(key) != source[key] for key in ("sha256", "bytes"))
            or any(recorded_input.get(key) is not True for key in
                   ("snapshot_read_only", "stable_before_run", "stable_after_run"))):
        raise Rejected("preparation_snapshot_record_mismatch")
    snapshot = recorded_input.get("snapshot")
    if not isinstance(snapshot, str) or re.fullmatch(r"input\.(?:cxi|ncch|cci|3ds|cia)", snapshot) is None:
        raise Rejected("invalid_preparation_snapshot_path")
    # CodexAstraUlt: Current preparations record the selected cap; historical
    # records before the explicit allowance used a fixed 512 MiB ceiling.
    requested_limits = report.get("requested")
    if not isinstance(requested_limits, dict):
        raise Rejected("invalid_preparation_requested_limits")
    limits = report.get("output_limits")
    if limits is None:
        if "prepared_mib" in requested_limits:
            raise Rejected("missing_preparation_output_limit")
        limit = PREP.MAX_PREPARED_BYTES
    else:
        if (not isinstance(limits, dict)
                or set(limits) != {"prepared_bytes", "failure_diagnostic_bytes"}
                or type(limits["failure_diagnostic_bytes"]) is not int
                or limits["failure_diagnostic_bytes"] != PREP.MAX_FAILURE_BYTES):
            raise Rejected("invalid_preparation_output_limit")
        limit = PREP.integer(limits["prepared_bytes"], "output_limit", PREP.MAX_PREPARED_MIB * 1024**2)
        requested = requested_limits.get("prepared_mib")
        if type(requested) is not int or not 1 <= requested <= PREP.MAX_PREPARED_MIB or limit != requested * 1024**2:
            raise Rejected("preparation_output_limit_mismatch")
    descriptor_path = directory / "prepared/prepare-report.json"
    descriptor, _, descriptor_stat = _json_record(descriptor_path, COMMON.MAX_REPORT_BYTES)
    resolved = PREP.validate_preparation(directory / "prepared", descriptor, limit)
    if PREP.canonical(resolved) != PREP.canonical(manifest["prepared"]):
        raise Rejected("preparation_manifest_artifacts_mismatch")
    snapshot_path = directory / snapshot
    if snapshot_path.lstat().st_mode & 0o222:
        raise Rejected("preparation_snapshot_is_writable")
    if _file_identity(snapshot_path, COMMON.MAX_INPUT_BYTES) != source:
        raise Rejected("preparation_snapshot_hash_mismatch")
    # CodexAstraUlt: Later lengthy snapshot hashing cannot hide metadata changes
    # made after the source inventory was checked.
    for path, expected in ((directory / "manifest.json", manifest_stat),
                           (directory / "report.json", report_stat),
                           (descriptor_path, descriptor_stat)):
        COMMON.absolute_plain(path)
        if COMMON.fingerprint(path.lstat()) != expected:
            raise Rejected("preparation_input_changed")
    return {"manifest": manifest, "manifest_sha256": digest,
            "generated": resolved["artifacts"], "sources": resolved["sources"],
            "module_count": sum(item["kind"] == "cro" for item in resolved["components"]),
            "generated_bytes": sum(item["bytes"] for item in resolved["artifacts"]),
            "output_limit_bytes": limit}


def snapshot_generated(preparation_path, loaded, output_source_dir):
    """CodexAstraUlt: Copy only admitted C/headers into new read-only build inputs."""
    preparation_path = COMMON.absolute_plain(preparation_path)
    COMMON.outside_git(preparation_path)
    output_source_dir = COMMON.absolute_plain(output_source_dir)
    COMMON.outside_git(output_source_dir)
    if os.path.lexists(output_source_dir) or not output_source_dir.parent.is_dir():
        raise Rejected("source_snapshot_must_be_absent_with_existing_parent")
    manifest = loaded["manifest"]
    encoded = PREP.canonical(manifest)
    if (hashlib.sha256(encoded).hexdigest() != loaded["manifest_sha256"]
            or loaded["generated"] != manifest["prepared"]["artifacts"]
            or _file_identity(preparation_path / "manifest.json", MAX_MANIFEST_BYTES)
            != {"sha256": loaded["manifest_sha256"], "bytes": len(encoded)}):
        raise Rejected("preparation_changed_before_source_snapshot")
    output_source_dir.mkdir(mode=0o700)
    copied = []
    for item in loaded["generated"]:
        source_path = preparation_path / "prepared" / item["path"]
        name = Path(item["path"]).name
        target = output_source_dir / name
        stream, before = COMMON.open_regular(source_path, PREP.MAX_FILE_BYTES)
        with stream:
            fd = os.open(target, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
            with os.fdopen(fd, "wb") as destination:
                digest, size = hashlib.sha256(), 0
                while block := stream.read(COMMON.CHUNK_BYTES):
                    size += len(block)
                    if size > item["bytes"]:
                        raise Rejected("generated_source_changed_during_snapshot")
                    digest.update(block)
                    destination.write(block)
                destination.flush()
                os.fsync(destination.fileno())
            _unchanged_stat(source_path, stream, before)
        if size != item["bytes"] or digest.hexdigest() != item["sha256"]:
            raise Rejected("generated_source_changed_during_snapshot")
        target.chmod(0o400)
        copied.append({"path": name, "bytes": size, "sha256": digest.hexdigest()})
    verify_snapshot(output_source_dir, copied)
    return copied


def verify_snapshot(directory, records):
    """CodexAstraUlt: Require exactly the retained flat read-only source inventory."""
    directory = COMMON.absolute_plain(directory)
    if (not directory.is_dir() or not isinstance(records, list)
            or not 1 <= len(records) <= PREP.MAX_ARTIFACTS):
        raise Rejected("invalid_compile_source_snapshot")
    expected, total = set(), 0
    for item in records:
        if (not isinstance(item, dict) or set(item) != {"path", "bytes", "sha256"}
                or not isinstance(item["path"], str)
                or re.fullmatch(r"[A-Za-z0-9_.-]+\.(?:c|h)", item["path"]) is None
                or not _sha256(item["sha256"]) or item["path"] in expected):
            raise Rejected("invalid_compile_source_record")
        size = PREP.integer(item["bytes"], "compile_source_bytes", PREP.MAX_FILE_BYTES)
        if not size:
            raise Rejected("empty_compile_source")
        total += size
        if total > PREP.MAX_PREPARED_MIB * 1024**2:
            raise Rejected("compile_source_total_exceeds_bound")
        expected.add(item["path"])
        path = directory / item["path"]
        if path.lstat().st_mode & 0o222:
            raise Rejected("compile_source_snapshot_is_writable")
        if _file_identity(path, PREP.MAX_FILE_BYTES) != {"bytes": size, "sha256": item["sha256"]}:
            raise Rejected("compile_source_snapshot_hash_mismatch")
    if {entry.name for entry in directory.iterdir()} != expected:
        raise Rejected("compile_source_snapshot_inventory_mismatch")
    return {"files": len(expected), "bytes": total}
