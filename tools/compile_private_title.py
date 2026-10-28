#!/usr/bin/env python3
"""CodexAstraUlt: Compile a validated preparation into a local host library.

Compilation is serial, bounded and resumable. This tool never loads its library,
executes guest code, signs an APK or modifies the original preparation.
"""

import argparse
import fcntl
import hashlib
import importlib.util
import json
import math
import os
from pathlib import Path
import re
import shutil
import signal
import stat
import subprocess
import sys
import time
import uuid


# CodexAstraUlt: Import neighboring helpers explicitly for both CLI and isolated
# test loaders; the installed Python standard library is the only dependency.
ROOT = Path(__file__).resolve().parents[1]


def helper(name):
    spec = importlib.util.spec_from_file_location(name, ROOT / "tools" / (name + ".py"))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


PREP = helper("prepare_private_title")
COMMON = PREP.COMMON
INPUTS = helper("private_compile_inputs")
PROCESS = helper("private_compile_process")
ELF = helper("private_compile_elf")
Rejected = COMMON.Rejected
MIB = 1024**2
MAX_JSON = 8 * MIB
REPORT_RESERVE = MAX_JSON
OBJECT_BYTES = 128 * MIB
LIBRARY_BYTES = 512 * MIB
SONAME = "libdroidds_title.so"
COMPILE_FLAGS = ["-O2", "-ffp-contract=off", "-fno-math-errno", "-fPIC", "-fvisibility=hidden", "-w"]
GCC_FLAGS = ["--param", "ggc-min-expand=20", "--param", "ggc-min-heapsize=65536"]
LINK_FLAGS = ["-shared", "-Wl,-z,relro", "-Wl,-z,now", "-Wl,--no-undefined", "-Wl,-soname," + SONAME]


def digest_bytes(value):
    """CodexAstraUlt: Canonical identities exclude elapsed time and batch limits."""
    return hashlib.sha256(value).hexdigest()


def identity(path, ceiling):
    """CodexAstraUlt: Refuse links, changing files, special files and oversize data."""
    stream, info = COMMON.open_regular(path, ceiling)
    with stream:
        digest, size = COMMON.stream_digest(stream, ceiling)
        if not COMMON.unchanged(path, stream, info, digest, ceiling):
            raise Rejected("compile_artifact_changed")
    return {"sha256": digest, "bytes": size}


def publish(path, value, root=None, ceiling=None):
    """CodexAstraUlt: Only fully synced, canonical bytes become a new receipt."""
    data = PREP.canonical(value)
    if len(data) > MAX_JSON:
        raise Rejected("compile_metadata_exceeds_bound")
    # CodexAstraUlt: Reserve the bounded final run report as well as this new
    # metadata before publication; success must fit after its descriptor grows.
    if root is not None and output_size(root, ceiling) + len(data) + REPORT_RESERVE > ceiling:
        raise Rejected("compile_metadata_exceeds_output_allowance")
    temporary = path.with_name("." + path.name + ".pending-" + uuid.uuid4().hex)
    COMMON.write_new(temporary, data)
    os.link(temporary, path, follow_symlinks=False)
    temporary.unlink()


def read_canonical(path):
    """CodexAstraUlt: Receipts and plans cannot admit duplicate keys or rewrites."""
    value = PREP.read_json(path, MAX_JSON)
    stream, _ = COMMON.open_regular(path, MAX_JSON)
    with stream:
        if stream.read(MAX_JSON + 1) != PREP.canonical(value):
            raise Rejected("noncanonical_compile_metadata")
    return value


def coordinator_identity():
    """CodexAstraUlt: Resume depends on actual tool code, not unrelated doc commits."""
    names = ["compile_private_title", "private_compile_inputs", "private_compile_process",
             "private_compile_elf", "prepare_private_title", "run_private_title"]
    return {name + ".py": identity(ROOT / "tools" / (name + ".py"), MAX_JSON)["sha256"] for name in names}


def binding_source(preparation_sha256, contract_sha256):
    """CodexAstraUlt: Embed exact preparation/compile identities as static exports."""
    return ("/* CodexAstraUlt: Identity binding only; no constructor or guest execution. */\n"
            "#define EXPORT __attribute__((visibility(\"default\")))\n"
            f'EXPORT const char droidds_preparation_sha256[65] = "{preparation_sha256}";\n'
            f'EXPORT const char droidds_compile_contract_sha256[65] = "{contract_sha256}";\n').encode()


def make_plan(loaded, compiler):
    """CodexAstraUlt: One recipe binds every generated file, helper and toolchain."""
    architecture = compiler["identity"]["host_arch"]
    machine = {"x86_64": 62, "aarch64": 183}[architecture]
    driver_flags = [] if compiler["identity"]["family"] == "gcc" else ["--no-default-config"]
    flags = driver_flags + COMPILE_FLAGS + (GCC_FLAGS if compiler["identity"]["family"] == "gcc" else [])
    contract = {"schema_version": 1, "kind": "droidds_native_compile_contract",
                "preparation_sha256": loaded["manifest_sha256"],
                "input": loaded["manifest"]["input"],
                "program_id": loaded["manifest"]["prepared"]["program_id"],
                "abi": 4, "generation": 3, "module_count": loaded["module_count"],
                "generated": loaded["generated"], "sources": loaded["sources"],
                "compiler": compiler["identity"], "coordinator": coordinator_identity(),
                "machine": machine, "compile_flags": flags, "link_flags": driver_flags + LINK_FLAGS,
                "link_libraries": ["-lm"], "library_name": SONAME,
                "toolchain_hermetic": False, "runtime_binding_enforced": False}
    contract_hash = digest_bytes(PREP.canonical(contract))
    binding = binding_source(loaded["manifest_sha256"], contract_hash)
    return {"schema_version": 1, "kind": "droidds_native_compile_plan",
            "contract": contract, "contract_sha256": contract_hash,
            "binding": {"path": "binding/identity.c", "bytes": len(binding),
                        "sha256": digest_bytes(binding)}}


def snapshot_records(loaded):
    """CodexAstraUlt: The build copies only flat generated C/headers, never game data."""
    return [{**item, "path": Path(item["path"]).name} for item in loaded["generated"]]


def jobs_for(plan):
    """CodexAstraUlt: Stable object numbers permit exact receipts across batches."""
    records = {item["path"]: item for item in plan["contract"]["generated"]}
    jobs = [{"index": index, "source": "source/" + Path(name).name,
             "sha256": records[name]["sha256"], "bytes": records[name]["bytes"], "role": "generated"}
            for index, name in enumerate(plan["contract"]["sources"])]
    jobs.append({"index": len(jobs), "source": plan["binding"]["path"],
                 "sha256": plan["binding"]["sha256"], "bytes": plan["binding"]["bytes"], "role": "binding"})
    return jobs


def owned_path(root, value, pattern):
    """CodexAstraUlt: Receipt paths are fixed tool-owned relative names, not commands."""
    if not isinstance(value, str) or not re.fullmatch(pattern, value):
        raise Rejected("invalid_compile_artifact_path")
    return COMMON.absolute_plain(root / value)


def validate_receipt(root, plan, job, receipt):
    """CodexAstraUlt: Existing objects qualify only with matching content and recipe."""
    if not isinstance(receipt, dict) or set(receipt) != {
            "schema_version", "kind", "contract_sha256", "job", "object", "elf"}:
        raise Rejected("invalid_object_receipt")
    if (type(receipt["schema_version"]) is not int or receipt["schema_version"] != 1 or
            receipt["kind"] != "droidds_native_object" or
            receipt["contract_sha256"] != plan["contract_sha256"] or
            PREP.canonical(receipt["job"]) != PREP.canonical(job)):
        raise Rejected("object_receipt_identity_mismatch")
    artifact = receipt["object"]
    if (not isinstance(artifact, dict) or set(artifact) != {"path", "sha256", "bytes"}
            or type(artifact["bytes"]) is not int or not 0 < artifact["bytes"] <= OBJECT_BYTES
            or not isinstance(artifact["sha256"], str)
            or re.fullmatch(r"[0-9a-f]{64}", artifact["sha256"]) is None):
        raise Rejected("invalid_object_identity")
    path = owned_path(root, artifact["path"], r"attempts/[0-9]{6}/work/[0-9]{5}/object\.o")
    if identity(path, OBJECT_BYTES) != {key: artifact[key] for key in ("sha256", "bytes")}:
        raise Rejected("compiled_object_changed")
    audit = ELF.audit_object(path, plan["contract"]["machine"])
    if PREP.canonical(audit) != PREP.canonical(receipt["elf"]):
        raise Rejected("object_audit_changed")
    if identity(path, OBJECT_BYTES) != {key: artifact[key] for key in ("sha256", "bytes")}:
        raise Rejected("compiled_object_changed_during_audit")
    return receipt


def existing_receipts(root, plan, jobs):
    """CodexAstraUlt: Unreceipted attempts remain preserved and are never reused."""
    found = {}
    expected = {f"{job['index']:05}.json": job for job in jobs}
    for entry in sorted((root / "receipts").iterdir()):
        if entry.name not in expected:
            raise Rejected("unexpected_object_receipt")
        receipt = validate_receipt(root, plan, expected[entry.name], read_canonical(entry))
        found[expected[entry.name]["index"]] = receipt
    return found


def output_size(root, ceiling):
    """CodexAstraUlt: Check total retained output between compiler commands.

    Compiler temporary files also count. This is admission/checking, not an OS
    aggregate disk quota; each subprocess separately has a hard per-file limit.
    """
    total, count = 0, 0
    for base, dirs, files in os.walk(root, followlinks=False):
        for name in dirs:
            if not stat.S_ISDIR((Path(base) / name).lstat().st_mode):
                raise Rejected("nonregular_compile_directory")
        for name in files:
            info = (Path(base) / name).lstat()
            if not stat.S_ISREG(info.st_mode):
                raise Rejected("nonregular_compile_output")
            total += info.st_size
            count += 1
            if total > ceiling or count > 100_000:
                raise Rejected("compile_output_exceeds_bound")
    return total


def fresh_attempt(root):
    """CodexAstraUlt: Each invocation retains its own report and failed intermediates."""
    names = [item.name for item in (root / "attempts").iterdir()]
    if any(not re.fullmatch(r"[0-9]{6}", name) for name in names):
        raise Rejected("unexpected_compile_attempt")
    index = max(map(int, names), default=0) + 1
    if index > 999999:
        raise Rejected("compile_attempt_limit")
    attempt = root / "attempts" / f"{index:06}"
    attempt.mkdir(mode=0o700)
    (attempt / "work").mkdir(mode=0o700)
    return attempt


def verify_inputs(root, loaded, plan):
    """CodexAstraUlt: Check the identity source as well as copied title C/headers."""
    INPUTS.verify_snapshot(root / "source", snapshot_records(loaded))
    if identity(root / plan["binding"]["path"], MIB) != {key: plan["binding"][key] for key in ("bytes", "sha256")}:
        raise Rejected("compile_binding_changed")


def compiled_manifest(root, library, plan, loaded, receipts, jobs):
    """CodexAstraUlt: Bind static inspection to the exact unchanged library bytes."""
    library_identity = identity(library, LIBRARY_BYTES)
    audit = ELF.audit_library(library, plan["contract"]["machine"], loaded["manifest_sha256"],
                              plan["contract_sha256"], loaded["module_count"])
    if identity(library, LIBRARY_BYTES) != library_identity:
        raise Rejected("compiled_library_changed_during_audit")
    return {"schema_version": 1, "kind": "droidds_private_title_compiled_manifest", "stage": "compiled",
            "preparation_sha256": loaded["manifest_sha256"], "contract_sha256": plan["contract_sha256"],
            "input": loaded["manifest"]["input"], "abi": 4, "generation": 3,
            "host_arch": plan["contract"]["compiler"]["host_arch"],
            "objects": [receipts[job["index"]] for job in jobs],
            "library": {"path": library.relative_to(root).as_posix(), **library_identity}, "elf": audit,
            "library_loaded": False, "guest_execution_performed": False, "runtime_binding_enforced": False}


def command_result(command, directory, args, deadline, file_bytes, report):
    """CodexAstraUlt: One compiler group at a time, under both job and batch deadlines."""
    remaining = deadline - time.monotonic()
    if remaining <= 0:
        return None
    environment = PROCESS.clean_environment()
    temporary = directory / "tmp"
    temporary.mkdir(mode=0o700)
    environment.update(TMPDIR=str(temporary), TMP=str(temporary), TEMP=str(temporary))
    process = PROCESS.run_command(command, directory, min(args.command_seconds, remaining),
                                  args.cpu_seconds, args.memory_mib, file_bytes, environment)
    log = process.pop("log_tail")
    COMMON.write_new(directory / "compiler.log", log.encode("utf-8")[-COMMON.LOG_BYTES:])
    report["commands"].append({"path": directory.relative_to(args.output).as_posix(), **process})
    return process


def result_failure(process, deadline):
    """CodexAstraUlt: A killed compiler is reported as observed, not guessed to be OOM."""
    if process is None or process["outcome"] == "timeout" and time.monotonic() >= deadline:
        return "incomplete", "batch_budget"
    if process["outcome"] == "interrupted":
        return "interrupted", "compiler_interrupted"
    if process["outcome"] != "completed":
        return "blocked", "compiler_" + process["outcome"]
    if process["exit_code"] != 0:
        code = process["exit_code"]
        return "blocked", "compiler_signal_" + str(-code) if code < 0 else "compiler_exit_" + str(code)
    return None


def parse_args(argv=None):
    """CodexAstraUlt: Host-only serial compilation accepts no implicit compiler flags."""
    parser = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    parser.add_argument("--preparation", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--cc", type=Path)
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--batch-seconds", type=float, default=1800)
    parser.add_argument("--command-seconds", type=float, default=300)
    parser.add_argument("--cpu-seconds", type=int, default=260)
    parser.add_argument("--memory-mib", type=int, default=4096)
    parser.add_argument("--output-mib", type=int, default=4096)
    values = sys.argv[1:] if argv is None else argv
    flags = [value.split("=", 1)[0] for value in values if value.startswith("--")]
    if len(flags) != len(set(flags)):
        parser.error("duplicate compilation option")
    args = parser.parse_args(values)
    if (not math.isfinite(args.batch_seconds) or not 0 < args.batch_seconds <= 7200 or
            not math.isfinite(args.command_seconds) or not 0 < args.command_seconds <= 1800 or
            not 1 <= args.cpu_seconds <= 1800 or not 256 <= args.memory_mib <= 16384 or
            not 64 <= args.output_mib <= 8192):
        parser.error("compilation limits outside supported range")
    return args


def run(args):
    """CodexAstraUlt: Compile only verified sources; publish success after static audit."""
    started = time.monotonic()
    deadline = started + args.batch_seconds
    report = {"schema_version": 1, "kind": "droidds_private_title_compile_run",
              "status": "rejected", "reason": "preflight", "stage": "preflight",
              "limits": {"batch_seconds": args.batch_seconds, "command_seconds": args.command_seconds,
                         "cpu_seconds_per_process": args.cpu_seconds, "memory_mib_per_process": args.memory_mib,
                         "output_bytes": args.output_mib * MIB, "jobs": 1,
                         "object_file_bytes": OBJECT_BYTES, "library_file_bytes": LIBRARY_BYTES},
              "generated_sources": 0, "objects_total": 0, "objects_reused": 0, "objects_compiled": 0,
              "objects_ready": 0, "commands": [], "library_loaded": False,
              "guest_execution_performed": False, "runtime_binding_enforced": False}
    attempt, lock, code = None, None, 1
    try:
        preparation, output = (COMMON.absolute_plain(path) for path in (args.preparation, args.output))
        args.output = output
        COMMON.outside_git(output)
        if output == preparation or output in preparation.parents or preparation in output.parents:
            raise Rejected("compilation_and_preparation_must_be_separate")
        if not output.parent.is_dir():
            raise Rejected("compilation_output_parent_missing")
        if args.resume:
            if not output.is_dir():
                raise Rejected("resume_requires_existing_compile_directory")
        else:
            if os.path.lexists(output):
                raise Rejected("compilation_output_must_be_absent")
            output.mkdir(mode=0o700)
        lock = os.open(output / ".compile.lock", os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW | os.O_NONBLOCK, 0o600)
        if not stat.S_ISREG(os.fstat(lock).st_mode):
            raise Rejected("invalid_compile_lock")
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as error:
            raise Rejected("compile_directory_in_use") from error
        if not args.resume:
            (output / "attempts").mkdir(mode=0o700)
            (output / "receipts").mkdir(mode=0o700)
        attempt = fresh_attempt(output)
        COMMON.save_report(attempt, report)
        loaded = INPUTS.load_preparation(preparation)
        compiler = PROCESS.inspect_compiler(args.cc)
        plan = make_plan(loaded, compiler)
        report.update(preparation_sha256=loaded["manifest_sha256"], contract_sha256=plan["contract_sha256"])
        ceiling = args.output_mib * MIB
        used = output_size(output, ceiling)
        if shutil.disk_usage(output).free < ceiling - used:
            raise Rejected("insufficient_disk_space_for_compilation")
        if args.resume:
            if PREP.canonical(read_canonical(output / "compile-plan.json")) != PREP.canonical(plan):
                raise Rejected("compile_plan_changed_use_a_new_output")
        else:
            if used + loaded["generated_bytes"] + 2 * MAX_JSON > ceiling:
                raise Rejected("compile_sources_exceed_output_allowance")
            INPUTS.snapshot_generated(preparation, loaded, output / "source")
            (output / "binding").mkdir(mode=0o700)
            COMMON.write_new(output / plan["binding"]["path"], binding_source(loaded["manifest_sha256"], plan["contract_sha256"]))
            (output / plan["binding"]["path"]).chmod(0o400)
            publish(output / "compile-plan.json", plan, output, ceiling)
        verify_inputs(output, loaded, plan)
        jobs = jobs_for(plan)
        receipts = existing_receipts(output, plan, jobs)
        report.update(generated_sources=len(jobs) - 1, objects_total=len(jobs),
                      objects_reused=len(receipts), objects_ready=len(receipts), stage="compile")
        # CodexAstraUlt: Rechecking a completed build must not relink or replace
        # its manifest. Every receipt and the actual library still must match.
        if (output / "compiled-manifest.json").exists():
            if len(receipts) != len(jobs):
                raise Rejected("completed_compile_missing_objects")
            previous = read_canonical(output / "compiled-manifest.json")
            library = owned_path(output, previous["library"]["path"],
                                 r"attempts/[0-9]{6}/link/libdroidds_title\.so")
            actual = compiled_manifest(output, library, plan, loaded, receipts, jobs)
            if PREP.canonical(previous) != PREP.canonical(actual):
                raise Rejected("compiled_manifest_changed")
            if output_size(output, ceiling) + REPORT_RESERVE > ceiling:
                raise Rejected("compile_report_exceeds_output_allowance")
            report.update(status="compiled", reason="verified_existing_host_library", library=actual["library"],
                          compiled_manifest_sha256=digest_bytes(PREP.canonical(actual)), stage="complete")
            return 0, report
        # CodexAstraUlt: Largest-first admission tests the costly source before
        # spending a whole batch on smaller translation units. No parallel jobs.
        for job in sorted(jobs, key=lambda item: (-item["bytes"], item["index"])):
            if job["index"] in receipts:
                continue
            report["current_job"] = {"index": job["index"], "role": job["role"], "source_bytes": job["bytes"]}
            if time.monotonic() >= deadline:
                report.update(status="incomplete", reason="batch_budget")
                return 2, report
            if identity(output / job["source"], PREP.MAX_FILE_BYTES) != {key: job[key] for key in ("sha256", "bytes")}:
                raise Rejected("compile_source_changed")
            directory = attempt / "work" / f"{job['index']:05}"
            directory.mkdir(mode=0o700)
            command = [compiler["invocation"], *plan["contract"]["compile_flags"], "-I", str(output / "source"),
                       "-c", str(output / job["source"]), "-o", "object.o"]
            COMMON.save_report(attempt, report)
            process = command_result(command, directory, args, deadline, OBJECT_BYTES, report)
            failure = result_failure(process, deadline)
            if failure:
                report.update(status=failure[0], reason=failure[1])
                return (130 if failure[0] == "interrupted" else 2), report
            output_size(output, ceiling)
            # CodexAstraUlt: Recheck compiler inputs before publishing the object
            # receipt; the same full snapshot is checked again before final link.
            if identity(output / job["source"], PREP.MAX_FILE_BYTES) != {key: job[key] for key in ("sha256", "bytes")}:
                raise Rejected("compile_source_changed")
            for item in snapshot_records(loaded):
                if item["path"].endswith(".h") and identity(output / "source" / item["path"], PREP.MAX_FILE_BYTES) != {key: item[key] for key in ("sha256", "bytes")}:
                    raise Rejected("compile_header_changed")
            artifact = directory / "object.o"
            receipt = {"schema_version": 1, "kind": "droidds_native_object", "contract_sha256": plan["contract_sha256"],
                       "job": job, "object": {"path": artifact.relative_to(output).as_posix(), **identity(artifact, OBJECT_BYTES)},
                       "elf": ELF.audit_object(artifact, plan["contract"]["machine"])}
            if identity(artifact, OBJECT_BYTES) != {key: receipt["object"][key] for key in ("sha256", "bytes")}:
                raise Rejected("compiled_object_changed_during_audit")
            artifact.chmod(0o400)
            publish(output / "receipts" / f"{job['index']:05}.json", receipt, output, ceiling)
            receipts[job["index"]] = receipt
            report["objects_compiled"] += 1
            report["objects_ready"] = len(receipts)
            COMMON.save_report(attempt, report)
            print(json.dumps({"stage": "compile", "ready": len(receipts), "total": len(jobs)}), flush=True)
        report["stage"] = "link"
        verify_inputs(output, loaded, plan)
        if PROCESS.inspect_compiler(args.cc) != compiler or coordinator_identity() != plan["contract"]["coordinator"]:
            raise Rejected("compile_toolchain_or_coordinator_changed")
        receipts = existing_receipts(output, plan, jobs)
        if len(receipts) != len(jobs):
            raise Rejected("missing_compiled_objects")
        if time.monotonic() >= deadline:
            report.update(status="incomplete", reason="batch_budget")
            return 2, report
        link = attempt / "link"
        link.mkdir(mode=0o700)
        # CodexAstraUlt: A response file avoids argv size limits, with literal
        # quoting for spaces, apostrophes and backslashes in local directory names.
        object_paths = [str(output / receipts[job["index"]]["object"]["path"]) for job in jobs]
        response = "\n".join('"' + path.replace("\\", "\\\\").replace('"', '\\"') + '"' for path in object_paths) + "\n"
        COMMON.write_new(link / "objects.rsp", response.encode())
        process = command_result([compiler["invocation"], *plan["contract"]["link_flags"], "@objects.rsp", "-o", SONAME, "-lm"],
                                 link, args, deadline, LIBRARY_BYTES, report)
        failure = result_failure(process, deadline)
        if failure:
            report.update(status=failure[0], reason=failure[1])
            return (130 if failure[0] == "interrupted" else 2), report
        report["stage"] = "audit"
        output_size(output, ceiling)
        library = link / SONAME
        # CodexAstraUlt: Verify preparation and every claimed input/output again
        # before final publication; metadata is a binding, not binary attestation.
        if INPUTS.load_preparation(preparation) != loaded:
            raise Rejected("original_preparation_changed")
        verify_inputs(output, loaded, plan)
        if PROCESS.inspect_compiler(args.cc) != compiler or coordinator_identity() != plan["contract"]["coordinator"]:
            raise Rejected("compile_toolchain_or_coordinator_changed")
        if existing_receipts(output, plan, jobs) != receipts:
            raise Rejected("object_receipts_changed_during_link")
        manifest = compiled_manifest(output, library, plan, loaded, receipts, jobs)
        library.chmod(0o400)
        publish(output / "compiled-manifest.json", manifest, output, ceiling)
        report.update(status="compiled", reason="validated_host_library", library=manifest["library"],
                      compiled_manifest_sha256=digest_bytes(PREP.canonical(manifest)), stage="complete")
        code = 0
    except KeyboardInterrupt:
        report.update(status="interrupted", reason="coordinator_interrupted")
        code = 130
    except (ValueError, OSError, KeyError, TypeError, RuntimeError, subprocess.SubprocessError) as error:
        report.update(status="rejected", reason=str(error) if isinstance(error, (ValueError, RuntimeError)) else type(error).__name__)
    finally:
        report["elapsed_seconds"] = time.monotonic() - started
        if attempt is not None:
            COMMON.save_report(attempt, report)
            report["report_path"] = str(attempt / "report.json")
        if lock is not None:
            os.close(lock)
    return code, report


def main(argv=None):
    """CodexAstraUlt: Cancellation preserves artifacts and reports a bounded outcome."""
    args = parse_args(argv)
    def interrupted(_signum, _frame):
        raise KeyboardInterrupt
    previous = signal.signal(signal.SIGTERM, interrupted)
    try:
        code, report = run(args)
    finally:
        signal.signal(signal.SIGTERM, previous)
    print(json.dumps({key: report.get(key) for key in
                      ("status", "reason", "objects_ready", "objects_total", "report_path")}))
    return code


if __name__ == "__main__":
    raise SystemExit(main())
