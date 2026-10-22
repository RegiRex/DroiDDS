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
                 # CodexAstraUlt: Bind the optional host-only CPU sampler to
                 # the same local source record as the worker and coordinator.
                 "crates/droidds-title-tools/src/cpu_progress.rs",
                 "tools/run_private_title.py", "vendor/zakuro/crates/zakuro-core/src/lib.rs",
                 # CodexAstraUlt: Bind the new trace and the scheduler/syscall
                 # source context used to interpret its bounded metadata.
                 "vendor/zakuro/crates/zakuro-core/src/diagnostics.rs",
                 "vendor/zakuro/crates/zakuro-core/src/kernel/svc.rs",
                 "vendor/zakuro/crates/zakuro-core/src/kernel/mod.rs",
                 "vendor/zakuro/crates/zakuro-core/src/kernel/thread.rs",
                 "vendor/zakuro/crates/zakuro-core/src/kernel/object.rs",
                 # CodexAstraUlt: Bind shared-page publication fixes to the
                 # local diagnostic's source context alongside syscall behavior.
                 "vendor/zakuro/crates/zakuro-core/src/memory/config.rs"):
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


def validate_scheduler_trace(trace, observed):
    """CodexAstraUlt: Validate the fixed metadata schema before retaining it.

    The initial prefix and recent tail are disjoint. Exact capacities, sequence
    positions and omission counts distinguish a bounded trace from a complete
    execution history; arbitrary guest text or extra payloads are not accepted.
    """
    def obj(value, keys, label):
        if not isinstance(value, dict) or set(value) != set(keys.split()):
            raise Rejected("invalid_worker_trace_" + label + "_shape")
        return value

    def uint(value, label, maximum=2**64 - 1, optional=False):
        if optional and value is None:
            return None
        return integer(value, "trace_" + label, high=maximum)

    def boolean(value, label):
        if type(value) is not bool:
            raise Rejected("invalid_worker_trace_" + label)

    def choice(value, choices, label):
        if not isinstance(value, str) or value not in choices.split():
            raise Rejected("invalid_worker_trace_" + label)

    def bounded_list(value, maximum, label):
        if not isinstance(value, list) or len(value) > maximum:
            raise Rejected("invalid_worker_trace_" + label + "_bound")
        return value

    def registers(value, label, count=4):
        if not isinstance(value, list) or len(value) != count:
            raise Rejected("invalid_worker_trace_" + label)
        for item in value:
            uint(item, label, 2**32 - 1)

    obj(trace, "schema_version prefix_capacity tail_capacity thread_capacity wait_object_capacity "
        "pending_capacity events_seen events_omitted svc_counts other_svc_calls pending_dropped "
        "prefix tail scheduler", "snapshot")
    for name, expected in {"schema_version": 1, "prefix_capacity": 64, "tail_capacity": 128,
                           "thread_capacity": 64, "wait_object_capacity": 8, "pending_capacity": 64}.items():
        if type(trace[name]) is not int or trace[name] != expected:
            raise Rejected("invalid_worker_trace_" + name)
    seen = uint(trace["events_seen"], "events_seen")
    omitted = uint(trace["events_omitted"], "events_omitted")
    other = uint(trace["other_svc_calls"], "other_svc_calls")
    uint(trace["pending_dropped"], "pending_dropped", seen)
    prefix = bounded_list(trace["prefix"], 64, "prefix")
    tail = bounded_list(trace["tail"], 128, "tail")
    if (len(prefix) != min(seen, 64) or len(tail) != min(max(0, seen - 64), 128)
            or omitted != seen - len(prefix) - len(tail)):
        raise Rejected("invalid_worker_trace_retention_accounting")
    counts = {}
    previous_number = -1
    for counter in bounded_list(trace["svc_counts"], 128, "svc_counts"):
        obj(counter, "number count", "svc_counter")
        number = uint(counter["number"], "svc_number", 127)
        count = integer(counter["count"], "trace_svc_count", low=1, high=seen)
        if number <= previous_number:
            raise Rejected("invalid_worker_trace_svc_count_order")
        previous_number, counts[number] = number, count
    if sum(counts.values()) + other > seen:
        raise Rejected("invalid_worker_trace_svc_count_total")

    # CodexAstraUlt: Syscall return registers are metadata, not universally
    # ResultCodes. A parked syscall has no immediate return until wait_resume.
    previous_cycle, retained_counts = 0, {}
    for events, start in ((prefix, 1), (tail, seen - len(tail) + 1)):
        for sequence, event in enumerate(events, start):
            if not isinstance(event, dict):
                raise Rejected("invalid_worker_trace_event_shape")
            kind = event.get("kind")
            common = "sequence cycle kind "
            fields = {"svc": "entry_cycle thread pc number args returns outcome wakeup_at",
                      "schedule": "previous_thread next_thread",
                      "wait_resume": "thread guest_id number svc_pc return_pc returns wait_result signaled_index"}
            choice(kind, "svc schedule wait_resume", "event_kind")
            obj(event, common + fields[kind], "event")
            if uint(event["sequence"], "sequence") != sequence:
                raise Rejected("invalid_worker_trace_event_sequence")
            cycle = uint(event["cycle"], "cycle", observed["cycles"])
            if cycle < previous_cycle:
                raise Rejected("invalid_worker_trace_event_cycle_order")
            previous_cycle = cycle
            if kind == "svc":
                uint(event["entry_cycle"], "entry_cycle", cycle)
                uint(event["thread"], "thread", 2**32 - 1, True)
                uint(event["pc"], "pc", 2**32 - 1, True)
                number = uint(event["number"], "number", 2**32 - 1)
                registers(event["args"], "args", count=6)
                choice(event["outcome"], "returned blocked thread_exited process_exited faulted", "outcome")
                uint(event["wakeup_at"], "wakeup_at", optional=True)
                if event["outcome"] == "returned":
                    registers(event["returns"], "returns")
                elif event["returns"] is not None:
                    raise Rejected("invalid_worker_trace_unfinished_syscall_return")
                retained_counts[number] = retained_counts.get(number, 0) + 1
            elif kind == "schedule":
                uint(event["previous_thread"], "previous_thread", 2**32 - 1, True)
                uint(event["next_thread"], "next_thread", 2**32 - 1, True)
                if event["previous_thread"] == event["next_thread"]:
                    raise Rejected("invalid_worker_trace_unchanged_schedule")
            else:
                for name in ("thread", "guest_id", "number", "return_pc"):
                    uint(event[name], name, 2**32 - 1)
                uint(event["svc_pc"], "svc_pc", 2**32 - 1, True)
                registers(event["returns"], "returns")
                choice(event["wait_result"], "signaled timed_out not_recorded", "wait_result")
                uint(event["signaled_index"], "signaled_index", optional=True)
                if (event["wait_result"] == "signaled") != (event["signaled_index"] is not None):
                    raise Rejected("invalid_worker_trace_signaled_index")
    if any(count > counts.get(number, 0) for number, count in retained_counts.items() if number < 128):
        raise Rejected("invalid_worker_trace_retained_svc_counts")
    if sum(count for number, count in retained_counts.items() if number >= 128) > other:
        raise Rejected("invalid_worker_trace_retained_other_svc_counts")

    # CodexAstraUlt: Final thread/object summaries exclude names, CPU contexts
    # and arbitrary memory. Explicit truncated counts preserve their limits.
    scheduler = obj(trace["scheduler"], "cycle current_thread live_pc reschedule_pending all_blocked "
                    "next_kernel_event threads_total threads_truncated threads", "scheduler")
    if uint(scheduler["cycle"], "scheduler_cycle") != observed["cycles"]:
        raise Rejected("invalid_worker_trace_final_cycle")
    current = uint(scheduler["current_thread"], "current_thread", 2**32 - 1, True)
    uint(scheduler["live_pc"], "live_pc", 2**32 - 1)
    for name in ("reschedule_pending", "all_blocked"):
        boolean(scheduler[name], name)
    uint(scheduler["next_kernel_event"], "next_kernel_event", optional=True)
    total = uint(scheduler["threads_total"], "threads_total")
    truncated = uint(scheduler["threads_truncated"], "threads_truncated")
    threads = bounded_list(scheduler["threads"], 64, "threads")
    if len(threads) != min(total, 64) or truncated != total - len(threads):
        raise Rejected("invalid_worker_trace_thread_accounting")
    thread_ids = set()
    for thread in threads:
        obj(thread, "id guest_id status pc priority wakeup_at wait_all wait_address wait_syscall "
            "wait_objects_total wait_objects_truncated wait_objects", "thread")
        for name in ("id", "guest_id", "pc", "priority"):
            uint(thread[name], name, 2**32 - 1)
        if thread["id"] in thread_ids:
            raise Rejected("invalid_worker_trace_duplicate_thread")
        thread_ids.add(thread["id"])
        choice(thread["status"], "running ready sleeping wait_sync wait_arbiter dormant dead", "thread_status")
        uint(thread["wakeup_at"], "wakeup_at", optional=True)
        boolean(thread["wait_all"], "wait_all")
        uint(thread["wait_address"], "wait_address", 2**32 - 1, True)
        syscall = uint(thread["wait_syscall"], "wait_syscall", 2**32 - 1, True)
        if syscall not in (None, 0x24, 0x25, 0x22, 0x0A):
            raise Rejected("invalid_worker_trace_wait_syscall")
        count = uint(thread["wait_objects_total"], "wait_objects_total")
        truncated = uint(thread["wait_objects_truncated"], "wait_objects_truncated")
        objects = bounded_list(thread["wait_objects"], 8, "wait_objects")
        if len(objects) != min(count, 8) or truncated != count - len(objects):
            raise Rejected("invalid_worker_trace_wait_object_accounting")
        for item in objects:
            obj(item, "id kind signaled owner count deadline", "wait_object")
            uint(item["id"], "object_id", 2**32 - 1)
            choice(item["kind"], "Thread Event Mutex Semaphore Timer AddressArbiter SharedMemory ClientSession "
                   "ClientPort Process ResourceLimit missing", "object_kind")
            boolean(item["signaled"], "signaled")
            uint(item["owner"], "owner", 2**32 - 1, True)
            if item["count"] is not None:
                integer(item["count"], "trace_object_count", low=-(2**63), high=2**63 - 1)
            uint(item["deadline"], "deadline", optional=True)
    if current is not None and current not in thread_ids:
        raise Rejected("invalid_worker_trace_current_thread_missing")


def validate_cpu_progress(trace, observed):
    """CodexAstraUlt: Accept only bounded scalar progress snapshots, not dumps.

    Cadence is in System::step dispatches, which can include idle periods; live
    post-dispatch registers do not identify the owner of a recent instruction.
    The initial prefix, retained tail and separate final state are explicit.
    """
    def obj(value, keys, label):
        if not isinstance(value, dict) or set(value) != set(keys.split()):
            raise Rejected("invalid_worker_cpu_progress_" + label + "_shape")
        return value

    def uint(value, label, maximum=2**64 - 1, optional=False):
        if optional and value is None:
            return None
        return integer(value, "cpu_progress_" + label, high=maximum)

    def boolean(value, label):
        if type(value) is not bool:
            raise Rejected("invalid_worker_cpu_progress_" + label)

    def bounded_list(value, maximum, label):
        if not isinstance(value, list) or len(value) > maximum:
            raise Rejected("invalid_worker_cpu_progress_" + label + "_bound")
        return value

    obj(trace, "schema_version interval_steps prefix_capacity tail_capacity samples_seen "
        "samples_omitted prefix tail final recent_dispatches", "snapshot")
    for name, expected in {"schema_version": 1, "interval_steps": 65521,
                           "prefix_capacity": 16, "tail_capacity": 112}.items():
        if type(trace[name]) is not int or trace[name] != expected:
            raise Rejected("invalid_worker_cpu_progress_" + name)
    seen = uint(trace["samples_seen"], "samples_seen")
    omitted = uint(trace["samples_omitted"], "samples_omitted")
    prefix = bounded_list(trace["prefix"], 16, "prefix")
    tail = bounded_list(trace["tail"], 112, "tail")
    if (seen != 1 + observed["steps"] // 65521 or len(prefix) != min(seen, 16)
            or len(tail) != min(max(0, seen - 16), 112)
            or omitted != seen - len(prefix) - len(tail)):
        raise Rejected("invalid_worker_cpu_progress_retention_accounting")

    def state(value, expected_steps):
        obj(value, "steps cycles interpreted_instructions registers cpsr current_thread "
            "thread_guest_id reschedule_pending all_blocked", "state")
        steps = uint(value["steps"], "steps", observed["steps"])
        if steps != expected_steps:
            raise Rejected("invalid_worker_cpu_progress_sample_cadence")
        cycles = uint(value["cycles"], "cycles", observed["cycles"])
        instructions = uint(value["interpreted_instructions"], "interpreted_instructions",
                            min(steps, observed["interpreted_instructions"]))
        registers = bounded_list(value["registers"], 16, "registers")
        if len(registers) != 16:
            raise Rejected("invalid_worker_cpu_progress_register_count")
        for register in registers:
            uint(register, "register", 2**32 - 1)
        uint(value["cpsr"], "cpsr", 2**32 - 1)
        current = uint(value["current_thread"], "current_thread", 2**32 - 1, True)
        guest_id = uint(value["thread_guest_id"], "thread_guest_id", 2**32 - 1, True)
        if (current is None) != (guest_id is None):
            raise Rejected("invalid_worker_cpu_progress_thread_identity")
        for name in ("reschedule_pending", "all_blocked"):
            boolean(value[name], name)
        return cycles, instructions

    previous_cycles, previous_instructions = 0, 0
    for samples, start in ((prefix, 0), (tail, seen - len(tail))):
        for index, sample in enumerate(samples, start):
            cycles, instructions = state(sample, index * 65521)
            if cycles < previous_cycles or instructions < previous_instructions:
                raise Rejected("invalid_worker_cpu_progress_counter_order")
            previous_cycles, previous_instructions = cycles, instructions
    final = trace["final"]
    cycles, instructions = state(final, observed["steps"])
    if (cycles != observed["cycles"] or instructions != observed["interpreted_instructions"]
            or final["registers"][15] != uint(observed.get("final_pc"), "final_pc", 2**32 - 1)):
        raise Rejected("invalid_worker_cpu_progress_final_state")
    # CodexAstraUlt: At a sampling boundary no later guest instruction changes
    # CPU state. A subsequent HID hook can legitimately change scheduler flags.
    if observed["steps"] % 65521 == 0:
        last = (tail or prefix)[-1]
        if any(final[name] != last[name] for name in
               ("steps", "cycles", "interpreted_instructions", "registers", "cpsr")):
            raise Rejected("invalid_worker_cpu_progress_final_sample_mismatch")
    # CodexAstraUlt: Recent dispatch addresses are separate from live r15 and
    # carry their instruction mode, without code bytes or a fabricated owner.
    for dispatch in bounded_list(trace["recent_dispatches"], 64, "recent_dispatches"):
        obj(dispatch, "pc thumb", "dispatch")
        pc = uint(dispatch["pc"], "dispatch_pc", 2**32 - 1)
        boolean(dispatch["thumb"], "dispatch_thumb")
        if pc % (2 if dispatch["thumb"] else 4):
            raise Rejected("invalid_worker_cpu_progress_dispatch_alignment")


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
    # CodexAstraUlt: Bind the opt-in boolean independently of Python's numeric
    # equality so a malformed request cannot turn an integer into trace consent.
    trace_requested = requested.get("trace_scheduler", False)
    if type(trace_requested) is not bool:
        raise Rejected("invalid_scheduler_trace_request")
    # CodexAstraUlt: CPU progress has independent opt-in consent and must not
    # be silently activated by the scheduler trace or a numeric truthy value.
    progress_requested = requested.get("trace_cpu_progress", False)
    if type(progress_requested) is not bool:
        raise Rejected("invalid_cpu_progress_trace_request")
    for key, value in {"execution": "interpreter", "renderer": "software",
                       "model_requested": requested["model"], "strict_diagnostics": True,
                       "native_discovery": False, "updates": False, "dlc": False,
                       "texture_packs": False, "enhancements": False,
                       "scheduler_trace": trace_requested,
                       "cpu_progress_trace": progress_requested,
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
    # CodexAstraUlt: An early loader failure has no initialized runtime to trace.
    # Completed diagnostic execution must retain its requested bounded snapshot.
    trace = report.get("diagnostic_trace")
    if not trace_requested:
        if trace is not None:
            raise Rejected("worker_unrequested_scheduler_trace")
    elif trace is None:
        if status in SUCCESS_STATUSES:
            raise Rejected("worker_requested_scheduler_trace_missing")
    else:
        validate_scheduler_trace(trace, observed)
    progress = report.get("cpu_progress")
    if not progress_requested:
        if progress is not None:
            raise Rejected("worker_unrequested_cpu_progress_trace")
    elif progress is None:
        if status in SUCCESS_STATUSES:
            raise Rejected("worker_requested_cpu_progress_trace_missing")
    else:
        validate_cpu_progress(progress, observed)
    # CodexAstraUlt: Independently valid traces must also describe one final
    # machine, including the current thread incarnation rather than ID alone.
    if trace is not None and progress is not None:
        scheduler, final = trace["scheduler"], progress["final"]
        if (final["cycles"] != scheduler["cycle"]
                or final["registers"][15] != scheduler["live_pc"]
                or any(final[name] != scheduler[name] for name in
                       ("current_thread", "reschedule_pending", "all_blocked"))):
            raise Rejected("worker_cpu_progress_scheduler_mismatch")
        if final["current_thread"] is not None:
            thread = next(item for item in scheduler["threads"] if item["id"] == final["current_thread"])
            if final["thread_guest_id"] != thread["guest_id"]:
                raise Rejected("worker_cpu_progress_scheduler_thread_identity_mismatch")
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
    # CodexAstraUlt: Only this explicit diagnostic option enables the bounded
    # syscall/scheduler metadata; ordinary baseline runs retain no trace.
    parser.add_argument("--trace-scheduler", action="store_true",
                        help="Retain a bounded scheduler/SVC diagnostic trace")
    # CodexAstraUlt: Sparse register snapshots are a separate local diagnostic;
    # no profiler, guest-memory inspection or default tracing is enabled.
    parser.add_argument("--trace-cpu-progress", action="store_true",
                        help="Retain bounded CPU register progress and recent dispatch addresses")
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
    requested.update(model=args.model, timeout=args.timeout, memory_mib=args.memory_mib,
                     trace_scheduler=args.trace_scheduler, trace_cpu_progress=args.trace_cpu_progress)
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
        # CodexAstraUlt: A disabled trace is not passed as a worker option;
        # requested/report binding below prevents silent activation or omission.
        if args.trace_scheduler:
            command.append("--trace-scheduler")
        if args.trace_cpu_progress:
            command.append("--trace-cpu-progress")
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
