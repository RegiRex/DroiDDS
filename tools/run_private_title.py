#!/usr/bin/env python3
"""CodexAstraUlt: Preserve bounded, local interpreter evidence for one base title.

This coordinator never builds, uploads, signs, loads native guest libraries, or
qualifies game compatibility. Every run uses a new directory outside Git and a
read-only input snapshot; failed runs remain available to their owner.
"""

import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import re
import resource
import shutil
import signal
import stat
import subprocess
import sys
import threading
import time
import tomllib


# CodexAstraUlt: Bounds apply before allocation/copy and are reported separately
# from guest counters. The worker is a trusted local executable, not an OS sandbox.
ROOT = Path(__file__).resolve().parents[1]
RUNTIME_REVISION = "412900a5a020301da15c1cc382585e05a489a535"
MAX_INPUT_BYTES = 8 * 1024**3
MAX_WORKER_BYTES = 512 * 1024**2
MAX_REPORT_BYTES = 1024**2
LOG_BYTES = 64 * 1024
CHUNK_BYTES = 1024**2
RESERVE_BYTES = 64 * 1024**2
LIMITS = {"max_steps": (1_000_000, 1_000_000_000),
          "max_cycles": (268_111_856, 26_811_185_600),
          "max_frames": (120, 6000), "max_seconds": (30, 300)}
SUCCESS_STATUSES = {"guest_exited", "budget_exhausted", "blocked"}
FAULT_COUNTERS = ("unsupported_svc_count", "unsupported_service_count", "memory_fault_addresses",
                  "prefetch_abort_addresses", "fatal_error_count")
BLOCKER_KINDS = {"undefined_instruction", "breakpoint", "unsupported_svc", "unsupported_service",
                 "prefetch_abort", "memory_fault", "fatal_guest_error", "guest_fault"}


class Rejected(ValueError):
    """CodexAstraUlt: A predictable preflight/report failure with a stable reason."""


def absolute_plain(path):
    """CodexAstraUlt: Reject symlinks at every existing component before use."""
    path = Path(os.path.abspath(os.fspath(path)))
    for part in [*reversed(path.parents), path]:
        try:
            info = part.lstat()
        except FileNotFoundError:
            continue
        if stat.S_ISLNK(info.st_mode):
            raise Rejected("symlink_path_rejected")
    return path


def outside_git(path):
    """CodexAstraUlt: A worktree .git file and a bare repository also count."""
    for directory in [path, *path.parents]:
        marker = directory / ".git"
        # Empty .git mount placeholders used by a sandbox are not repositories.
        if marker.is_file() or marker.is_symlink() or any(
                (marker / name).exists() for name in ("HEAD", "config", "objects")) or (
                (directory / "HEAD").is_file() and
                (directory / "objects").is_dir() and
                (directory / "refs").is_dir()):
            raise Rejected("output_must_be_outside_git")


def fingerprint(info):
    return (info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns, info.st_ctime_ns)


def open_regular(path, ceiling):
    """CodexAstraUlt: O_NONBLOCK prevents a substituted FIFO from hanging open."""
    path = absolute_plain(path)
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    stream = os.fdopen(fd, "rb")
    info = os.fstat(fd)
    if not stat.S_ISREG(info.st_mode) or not 0 < info.st_size <= ceiling:
        stream.close()
        raise Rejected("file_must_be_nonempty_regular_and_within_bound")
    return stream, info


def stream_digest(stream, ceiling):
    """CodexAstraUlt: Hash bounded chunks without reading a title into Python RAM."""
    stream.seek(0)
    digest, count = hashlib.sha256(), 0
    while chunk := stream.read(CHUNK_BYTES):
        count += len(chunk)
        if count > ceiling:
            raise Rejected("file_grew_beyond_bound")
        digest.update(chunk)
    return digest.hexdigest(), count


def unchanged(path, stream, original, expected_hash, ceiling):
    """CodexAstraUlt: Detect content edits and name replacement without repairing it."""
    try:
        absolute_plain(path)
        if fingerprint(path.lstat()) != fingerprint(original):
            return False
        if fingerprint(os.fstat(stream.fileno())) != fingerprint(original):
            return False
        digest, count = stream_digest(stream, ceiling)
        return (digest == expected_hash and count == original.st_size and
                fingerprint(path.lstat()) == fingerprint(original) and
                fingerprint(os.fstat(stream.fileno())) == fingerprint(original))
    except (OSError, Rejected):
        return False


def write_new(path, content):
    """CodexAstraUlt: Never overwrite an existing worker/user artifact."""
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    with os.fdopen(fd, "wb") as stream:
        stream.write(content)
        stream.flush()
        os.fsync(stream.fileno())


def save_report(directory, report):
    """CodexAstraUlt: Replace only this coordinator's report, preserving other data."""
    temporary = directory / ".report.json.tmp"
    write_new(temporary, (json.dumps(report, indent=2, sort_keys=True) + "\n").encode())
    os.replace(temporary, directory / "report.json")


def source_identity():
    """CodexAstraUlt: Record source context without claiming binary/source attestation."""
    pins = tomllib.loads((ROOT / "upstream.lock.toml").read_text())
    if pins["runtime"]["revision"] != RUNTIME_REVISION:
        raise Rejected("coordinator_runtime_pin_mismatch")
    identity = {"runtime_revision": RUNTIME_REVISION,
                "runtime_has_local_patches": True,
                "binary_source_attested": False, "files_sha256": {}}
    for name in ("Cargo.lock", "upstream.lock.toml", "crates/droidds-title-tools/Cargo.toml",
                 "crates/droidds-title-tools/src/main.rs", "crates/droidds-title-tools/src/lib.rs",
                 "tools/run_private_title.py", "vendor/zakuro/crates/zakuro-core/src/lib.rs"):
        with (ROOT / name).open("rb") as stream:
            identity["files_sha256"][name] = stream_digest(stream, MAX_WORKER_BYTES)[0]
    for key, command in (("checkout_commit", ["git", "rev-parse", "HEAD"]),
                         ("checkout_dirty", ["git", "status", "--porcelain", "--untracked-files=no"])):
        result = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, timeout=10)
        if result.returncode:
            raise Rejected("source_identity_unavailable")
        identity[key] = bool(result.stdout) if key == "checkout_dirty" else result.stdout.strip()
    return identity


def integer(value, name, low=0, high=2**64 - 1):
    if type(value) is not int or not low <= value <= high:
        raise Rejected("invalid_worker_" + name)
    return value


def validate_worker(report, requested, snapshot_bytes, returncode):
    """CodexAstraUlt: A bounded run needs actual loaded metadata and execution.

    Loader failures retain their zero counters as failures. A blocked guest is
    useful diagnostic evidence, never a passed boot or performance measurement.
    """
    if not isinstance(report, dict):
        raise Rejected("worker_report_not_object")
    expected = {"schema_version": 1, "tool_version": "0.0.1",
                "kind": "droidds_private_title_interpreter_reconnaissance",
                "runtime_revision": RUNTIME_REVISION, "runtime_has_local_patches": True}
    for key, value in expected.items():
        if type(report.get(key)) is not type(value) or report[key] != value:
            raise Rejected("invalid_worker_" + key)
    status = report.get("status")
    expected_exit = {"guest_exited": 0, "budget_exhausted": 0, "blocked": 0,
                     "load_error": 2, "internal_error": 3}
    if status not in expected_exit or returncode != expected_exit[status]:
        raise Rejected("worker_status_exit_mismatch")
    reason = report.get("reason")
    if not isinstance(reason, str) or not 0 < len(reason) <= 1024:
        raise Rejected("invalid_worker_reason")
    expected_limits = {key: requested[key] for key in LIMITS}
    if report.get("limits") != expected_limits or any(
            type(report["limits"].get(key)) is not int for key in LIMITS):
        raise Rejected("worker_limits_mismatch")
    config = report.get("configuration", {})
    if not isinstance(config, dict):
        raise Rejected("worker_configuration_not_object")
    for key, value in {"execution": "interpreter", "renderer": "software",
                       "model_requested": requested["model"], "strict_diagnostics": True,
                       "native_discovery": False, "updates": False, "dlc": False,
                       "texture_packs": False, "enhancements": False,
                       "idle_loop_skipping": False, "input_events": "neutral",
                       "scanout_captured": False,
                       "mods_and_cheats": "absent_in_fresh_private_data_directory"}.items():
        if type(config.get(key)) is not type(value) or config[key] != value:
            raise Rejected("worker_configuration_mismatch")
    observed = report.get("observed", {})
    if not isinstance(observed, dict):
        raise Rejected("worker_observed_not_object")
    for key in ("steps", "frames"):
        integer(observed.get(key), key, high=requested["max_" + key])
    # CodexAstraUlt: Service dispatches can advance emulated time atomically.
    # The cycle threshold is cooperative; only the parent wall/resource caps
    # stop a stuck dispatch. Preserve and validate its actual overshoot.
    boundary = {"steps": "before_dispatch_hard", "cycles": "after_system_step",
                "frames": "after_system_step", "wall": "between_loader_and_steps_parent_hard_timeout"}
    if config.get("budget_boundary") != boundary:
        raise Rejected("worker_budget_boundary_mismatch")
    cycles = integer(observed.get("cycles"), "cycles")
    integer(observed.get("cycles_after_budget"), "cycles_after_budget")
    if observed["cycles_after_budget"] != max(0, cycles - requested["max_cycles"]):
        raise Rejected("worker_cycle_overshoot_mismatch")
    interpreted = integer(observed.get("interpreted_instructions"), "interpreted_instructions")
    if interpreted > observed["steps"]:
        raise Rejected("worker_instruction_dispatch_mismatch")
    integer(observed.get("recompiled_instructions"), "recompiled_instructions", high=0)
    elapsed = observed.get("elapsed_seconds")
    if type(elapsed) not in (int, float) or not math.isfinite(elapsed) or not 0 <= elapsed <= requested["timeout"] + 1:
        raise Rejected("invalid_worker_elapsed_seconds")
    if status in SUCCESS_STATUSES:
        title = report.get("input")
        if (not isinstance(title, dict) or not isinstance(title.get("program_id"), str) or
                not re.fullmatch(r"[0-9A-F]{16}", title["program_id"])):
            raise Rejected("worker_missing_loaded_title")
        # CIA extracts an NCCH subcontainer; NCSD/NCCH may retain the whole input.
        integer(title.get("container_bytes"), "container_bytes", 1, snapshot_bytes)
        integer(title.get("ncch_offset"), "ncch_offset", 0, snapshot_bytes - 1)
        entry = integer(title.get("entry_point"), "entry_point", 1, 2**32 - 1)
        if config.get("model_resolved") not in ("old", "new"):
            raise Rejected("worker_missing_resolved_model")
        if requested["model"] == "new" and config["model_resolved"] != "new":
            raise Rejected("worker_new_model_not_resolved")
        for name, maximum in (("title_name", 8), ("product_code", 16)):
            if not isinstance(title.get(name), str) or len(title[name]) > maximum:
                raise Rejected("invalid_worker_" + name)
        for segment in ("text", "rodata", "data"):
            section = title.get(segment, {})
            if not isinstance(section, dict):
                raise Rejected("invalid_worker_segment")
            for field in ("address", "pages", "size"):
                integer(section.get(field), segment + "_" + field, high=2**32 - 1)
        if title["text"]["address"] != entry or title["text"]["size"] == 0:
            raise Rejected("invalid_worker_entry_segment")
        if type(observed.get("guest_exited")) is not bool:
            raise Rejected("invalid_worker_guest_exited")
        for key in FAULT_COUNTERS:
            integer(observed.get(key), key)
            if status != "blocked" and observed[key] != 0:
                raise Rejected("worker_unreported_runtime_fault")
        if status != "blocked" and (observed["steps"] == 0 or interpreted == 0):
            raise Rejected("worker_zero_execution_not_success")
        if status == "guest_exited" and (not observed["guest_exited"] or reason != "guest_called_exit_process"):
            raise Rejected("worker_exit_not_observed")
        if status == "budget_exhausted":
            if observed["guest_exited"]:
                raise Rejected("worker_budget_after_guest_exit")
            field = {"step_budget": "steps", "cycle_budget": "cycles", "frame_budget": "frames"}.get(reason)
            if reason not in ("step_budget", "cycle_budget", "frame_budget", "wall_budget"):
                raise Rejected("worker_unknown_budget")
            if field and observed[field] < requested["max_" + field]:
                raise Rejected("worker_budget_not_reached")
            if reason == "wall_budget" and elapsed < requested["max_seconds"]:
                raise Rejected("worker_wall_budget_not_reached")
        blocker = report.get("blocker")
        if status == "blocked" and (not isinstance(blocker, dict) or blocker.get("kind") not in BLOCKER_KINDS):
            raise Rejected("worker_blocker_missing")
        if status == "blocked":
            counter = {"unsupported_svc": "unsupported_svc_count", "unsupported_service": "unsupported_service_count",
                       "prefetch_abort": "prefetch_abort_addresses", "memory_fault": "memory_fault_addresses",
                       "fatal_guest_error": "fatal_error_count"}.get(blocker["kind"])
            if counter and observed[counter] == 0:
                raise Rejected("worker_blocker_counter_missing")
        if status != "blocked" and blocker is not None:
            raise Rejected("worker_unexpected_blocker")
    return report


def stop_group(process):
    """CodexAstraUlt: Reap the leader and terminate children even if it exited first."""
    for sig, delay in ((signal.SIGTERM, 0.15), (signal.SIGKILL, 0)):
        try:
            os.killpg(process.pid, sig)
        except ProcessLookupError:
            break
        if delay:
            time.sleep(delay)
    try:
        process.wait(timeout=3)
    except subprocess.TimeoutExpired:
        raise Rejected("worker_process_could_not_be_reaped")


def run_worker(command, directory, timeout, memory_mib):
    """CodexAstraUlt: Drain stdout continuously but retain only a fixed-size tail."""
    def ceilings():
        resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
        resource.setrlimit(resource.RLIMIT_AS, (memory_mib * 1024**2,) * 2)
        resource.setrlimit(resource.RLIMIT_FSIZE, (RESERVE_BYTES,) * 2)
        resource.setrlimit(resource.RLIMIT_CPU, (math.ceil(timeout) + 1,) * 2)

    process = subprocess.Popen(command, cwd=directory, stdin=subprocess.DEVNULL,
                               stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                               start_new_session=True, preexec_fn=ceilings)
    tail, total = bytearray(), [0]

    def drain():
        while chunk := process.stdout.read(8192):
            total[0] += len(chunk)
            tail.extend(chunk)
            if len(tail) > LOG_BYTES:
                del tail[:-LOG_BYTES]

    reader = threading.Thread(target=drain, daemon=True)
    reader.start()
    outcome = "completed"
    try:
        process.wait(timeout=timeout)
    except subprocess.TimeoutExpired:
        outcome = "timed_out"
    except KeyboardInterrupt:
        outcome = "interrupted"
    finally:
        stop_group(process)
        reader.join(timeout=3)
        if reader.is_alive():
            outcome = "log_pipe_not_closed"
        else:
            process.stdout.close()
        write_new(directory / "worker.log", bytes(tail))
    return {"outcome": outcome, "exit_code": process.returncode,
            "log_bytes_emitted": total[0], "log_bytes_retained": len(tail),
            "log_truncated": total[0] > len(tail)}


def parse_args(argv=None):
    """CodexAstraUlt: Unknown flags cannot silently enable overlays/native loading."""
    parser = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    parser.add_argument("--input", required=True, type=Path, help="Owned decrypted base .cxi/.ncch, .3ds/.cci or .cia file")
    parser.add_argument("--output", required=True, type=Path, help="Absent run directory outside every Git checkout")
    parser.add_argument("--worker", type=Path, default=ROOT / "target/release/droidds-private-title")
    parser.add_argument("--model", choices=("old", "new"), default="old")
    for key, (default, ceiling) in LIMITS.items():
        parser.add_argument("--" + key.replace("_", "-"), type=int, default=default,
                            help=f"Positive limit, default {default}, maximum {ceiling}")
    parser.add_argument("--timeout", type=float, default=None,
                        help="Parent wall deadline in seconds (default max-seconds+10, maximum310)")
    parser.add_argument("--memory-mib", type=int, default=4096,
                        help="Worker address-space ceiling, default4096, range256..16384MiB")
    args = parser.parse_args(argv)
    for key, (_, ceiling) in LIMITS.items():
        if not 1 <= getattr(args, key) <= ceiling:
            parser.error(f"--{key.replace('_', '-')} must be between1 and {ceiling}")
    if args.timeout is None:
        args.timeout = args.max_seconds + 10
    if not math.isfinite(args.timeout) or not 0 < args.timeout <= 310:
        parser.error("--timeout must be positive and at most310 seconds")
    if not 256 <= args.memory_mib <= 16384:
        parser.error("--memory-mib must be between256 and16384")
    return args


def run(args):
    """CodexAstraUlt: Every created run ends in one honest report, including failures."""
    started, directory = time.monotonic(), None
    handles, identities = [], []
    requested = {key: getattr(args, key) for key in LIMITS}
    requested.update(model=args.model, timeout=args.timeout, memory_mib=args.memory_mib)
    report = {"schema_version": 1, "kind": "droidds_private_title_local_run",
              "tool_version": "0.0.1", "status": "preparing", "reason": "preflight",
              "requested": requested, "input": None, "worker": None, "process": None,
              "worker_report": None, "evidence": "not_a_game_compatibility_or_performance_pass",
              "limitations": ["Interpreter and software renderer with neutral input only.",
                              "Binary hash binds bytes; source identity is recorded, not attested.",
                              "No native generation, APK, upload, signing, existing saves or overlays."]}
    code = 1
    try:
        source, output, worker = (absolute_plain(value) for value in (args.input, args.output, args.worker))
        outside_git(output)
        if source.suffix.lower() not in (".cxi", ".ncch", ".3ds", ".cci", ".cia"):
            raise Rejected("input_must_be_base_ncch_ncsd_or_cia")
        if os.path.lexists(output) or not output.parent.is_dir():
            raise Rejected("output_must_be_absent_with_existing_parent")
        source_stream, source_info = open_regular(source, MAX_INPUT_BYTES)
        handles.append(source_stream)
        worker_stream, worker_info = open_regular(worker, MAX_WORKER_BYTES)
        handles.append(worker_stream)
        if not os.access(worker, os.X_OK):
            raise Rejected("worker_not_executable_build_it_first")
        if shutil.disk_usage(output.parent).free < source_info.st_size + RESERVE_BYTES:
            raise Rejected("insufficient_disk_space_for_snapshot")
        output.mkdir(mode=0o700)
        directory = output
        save_report(directory, report)
        identity = source_identity()
        worker_hash, _ = stream_digest(worker_stream, MAX_WORKER_BYTES)
        report["worker"] = {"sha256": worker_hash, "bytes": worker_info.st_size, "source": identity}
        identities.append((worker, worker_stream, worker_info, worker_hash, MAX_WORKER_BYTES, "worker"))
        snapshot = directory / ("input" + source.suffix.lower())
        snapshot_fd = os.open(snapshot, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
        digest, count = hashlib.sha256(), 0
        with os.fdopen(snapshot_fd, "wb") as destination:
            while chunk := source_stream.read(CHUNK_BYTES):
                count += len(chunk)
                if count > MAX_INPUT_BYTES or count > source_info.st_size:
                    raise Rejected("source_changed_during_snapshot")
                digest.update(chunk)
                destination.write(chunk)
            destination.flush()
            os.fsync(destination.fileno())
        snapshot.chmod(0o400)
        input_hash = digest.hexdigest()
        report["input"] = {"sha256": input_hash, "bytes": count, "snapshot_read_only": True,
                           "stable_before_run": False, "stable_after_run": False}
        identities.append((source, source_stream, source_info, input_hash, MAX_INPUT_BYTES, "source"))
        if count != source_info.st_size or not unchanged(source, source_stream, source_info, input_hash, MAX_INPUT_BYTES):
            raise Rejected("source_changed_during_snapshot")
        snapshot_stream, snapshot_info = open_regular(snapshot, MAX_INPUT_BYTES)
        handles.append(snapshot_stream)
        identities.append((snapshot, snapshot_stream, snapshot_info, input_hash, MAX_INPUT_BYTES, "snapshot"))
        for path, stream, original, digest, ceiling, label in identities:
            if not unchanged(path, stream, original, digest, ceiling):
                raise Rejected(label + "_changed_before_run")
        report["input"]["stable_before_run"] = True
        save_report(directory, report)
        command = [str(worker), "inspect-run", "--input", str(snapshot), "--data-dir",
                   str(directory / "runtime-data"), "--output", str(directory / "worker-report.json"),
                   "--model", args.model]
        for key in LIMITS:
            command += ["--" + key.replace("_", "-"), str(getattr(args, key))]
        process = run_worker(command, directory, args.timeout, args.memory_mib)
        report["process"] = process
        changed = [label for path, stream, original, digest, ceiling, label in identities
                   if not unchanged(path, stream, original, digest, ceiling)]
        report["input"]["stable_after_run"] = not changed
        if changed:
            report.update(status="input_changed", reason="changed_" + "_and_".join(changed))
        elif process["outcome"] != "completed":
            report.update(status=process["outcome"], reason="parent_" + process["outcome"])
            code = 130 if process["outcome"] == "interrupted" else 124
        elif process["exit_code"] not in (0, 2, 3):
            report.update(status="worker_failed", reason="worker_signal_" + str(-process["exit_code"])
                          if process["exit_code"] < 0 else "worker_exit_" + str(process["exit_code"]))
        else:
            raw, _ = open_regular(directory / "worker-report.json", MAX_REPORT_BYTES)
            with raw:
                # Duplicate object keys and nonfinite JSON numbers are not evidence.
                def unique(pairs):
                    result = {}
                    for key, value in pairs:
                        if key in result:
                            raise Rejected("duplicate_worker_json_key")
                        result[key] = value
                    return result
                def nonfinite(value):
                    raise Rejected("nonfinite_worker_json")
                worker_report = json.load(raw, object_pairs_hook=unique, parse_constant=nonfinite)
            validate_worker(worker_report, requested, count, process["exit_code"])
            report["worker_report"] = worker_report
            report.update(status=worker_report["status"], reason=worker_report["reason"])
            code = 0 if report["status"] in SUCCESS_STATUSES else 1
    except KeyboardInterrupt:
        report.update(status="interrupted", reason="coordinator_interrupted")
        code = 130
    except (Rejected, OSError, ValueError, KeyError, TypeError, subprocess.SubprocessError) as error:
        # Paths or guest-provided exception payloads stay in private raw artifacts;
        # this status records the stable local failure category only.
        report.update(status="rejected", reason=str(error) if isinstance(error, Rejected) else type(error).__name__)
    finally:
        for stream in handles:
            stream.close()
        report["elapsed_seconds"] = time.monotonic() - started
        if directory is not None:
            save_report(directory, report)
    return code, report


def main(argv=None):
    args = parse_args(argv)
    # CodexAstraUlt: Build runners use SIGTERM for their deadlines; route it
    # through the same preservation/group cleanup as a user interruption.
    def interrupted(signum, frame):
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
