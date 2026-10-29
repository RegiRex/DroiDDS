#!/usr/bin/env python3
"""CodexAstraUlt: Admit a retained native build and compare bounded host routes.

Historical preparation/compilation artifacts remain immutable. Only this new
Linux diagnostic path loads the trusted locally built library, after static
pointer-table validation and sealing its exact bytes against replacement.
"""

import argparse
from contextlib import ExitStack
import fcntl
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import platform
import re
import signal
import sys


# CodexAstraUlt: Keep all six historical compile-contract helpers unchanged;
# these new tools consume that contract without rebuilding any title objects.
ROOT = Path(__file__).resolve().parents[1]


def helper(name):
    spec = importlib.util.spec_from_file_location(name, ROOT / "tools" / (name + ".py"))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


COMPILE = helper("compile_private_title")
COMMON = COMPILE.COMMON
PREP = COMPILE.PREP
INPUTS = helper("private_runtime_inputs")
ELF = helper("private_runtime_elf")
PROCESS = helper("private_runtime_process")
Rejected = COMMON.Rejected
MIB = 1024**2
MAX_REQUEST = 8 * MIB
MAX_BUNDLE = 320 * MIB + 1536
MAX_REPORT = 4 * MIB
# CodexAstraUlt: Some Python builds omit the Linux constants even when the
# running kernel implements sealing. These are the documented Linux UAPI values.
ADD_SEALS = getattr(fcntl, "F_ADD_SEALS", 1033)
GET_SEALS = getattr(fcntl, "F_GET_SEALS", 1034)
SEALS = 0x000F  # F_SEAL_SEAL | F_SEAL_SHRINK | F_SEAL_GROW | F_SEAL_WRITE.
PREPARED_FIELDS = ("program_id", "segments", "bss_size", "ncch_format_version",
                   "remaster_version", "container", "cia_title_version")


def require(condition, reason):
    """CodexAstraUlt: An unsupported or inconsistent admission is a rejection."""
    if not condition:
        raise Rejected(reason)


def write_all(fd, data):
    """CodexAstraUlt: Handle short writes without silently sealing partial bytes."""
    view = memoryview(data)
    while view:
        written = os.write(fd, view)
        require(written > 0, "sealed_input_short_write")
        view = view[written:]


def seal_parts(stack, name, parts, ceiling):
    """CodexAstraUlt: Stream verified components into one immutable inherited fd.

Each part is either literal bytes or (path, expected identity). Rehashing the
actual copied bytes binds sealing to admission even if a source is replaced.
"""
    fd = os.memfd_create(name, os.MFD_CLOEXEC | os.MFD_ALLOW_SEALING)
    stack.callback(os.close, fd)
    digest, total = hashlib.sha256(), 0
    for part in parts:
        if isinstance(part, bytes):
            require(total + len(part) <= ceiling, "sealed_input_exceeds_bound")
            write_all(fd, part)
            digest.update(part)
            total += len(part)
            continue
        path, expected = part
        stream, before = COMMON.open_regular(path, ceiling)
        actual, count = hashlib.sha256(), 0
        with stream:
            while chunk := stream.read(MIB):
                require(total + len(chunk) <= ceiling, "sealed_input_exceeds_bound")
                write_all(fd, chunk)
                digest.update(chunk)
                actual.update(chunk)
                count += len(chunk)
                total += len(chunk)
            require({"bytes": count, "sha256": actual.hexdigest()} == expected,
                    "sealed_component_identity_mismatch")
            require(COMMON.unchanged(path, stream, before, actual.hexdigest(), ceiling),
                    "sealed_component_changed")
    os.fchmod(fd, 0o400)
    fcntl.fcntl(fd, ADD_SEALS, SEALS)
    require(fcntl.fcntl(fd, GET_SEALS) & SEALS == SEALS,
            "sealed_input_protection_failed")
    os.lseek(fd, 0, os.SEEK_SET)
    return {"descriptor": fd, "bytes": total, "sha256": digest.hexdigest()}


def seal_inputs(stack, admitted, audit):
    """CodexAstraUlt: Seal only code/identity inputs, without another game copy."""
    expected = {key: admitted["compiled_manifest"]["library"][key] for key in ("bytes", "sha256")}
    require(audit.get("library_sha256") == expected["sha256"], "audited_library_identity_mismatch")
    library = seal_parts(stack, "droidds-native-library", [(admitted["library_path"], expected)], 512 * MIB)
    records, parts, offset = [], [], 0
    for component in admitted["components"]:
        record = {key: value for key, value in component.items() if key != "full_path"}
        record["offset"] = offset
        records.append(record)
        parts.append((component["full_path"], {key: component[key] for key in ("bytes", "sha256")}))
        offset += component["bytes"]
    bundle = seal_parts(stack, "droidds-native-identity", parts, MAX_BUNDLE)
    bundle["components"] = records
    return library, bundle


def requested(args):
    """CodexAstraUlt: Cycle checkpoints are shared; outer dispatch counts are not."""
    return {name: getattr(args, name) for name in ("max_steps", "max_cycles", "max_frames", "max_seconds")}


def make_request(args, admitted, audit, library, bundle, route):
    """CodexAstraUlt: The worker rechecks actual loaded title bytes before native install."""
    return {"schema_version": 1, "kind": "droidds_private_native_run_request",
            "abi": 4, "generation": 3,
            "preparation_sha256": admitted["plan"]["contract"]["preparation_sha256"],
            "contract_sha256": admitted["plan"]["contract_sha256"],
            "input": {**admitted["loaded"]["manifest"]["input"],
                      "snapshot_path": str(admitted["snapshot_path"])},
            "library": library, "identity_bundle": bundle,
            "prepared": {key: admitted["prepared"][key] for key in PREPARED_FIELDS},
            "route": route, "limits": requested(args), "model": args.model,
            "static_table_audit": audit}


def uint(value, name, maximum=2**64 - 1):
    """CodexAstraUlt: Boolean aliases and invalid counters cannot qualify a run."""
    require(type(value) is int and 0 <= value <= maximum, "invalid_worker_" + name)
    return value


def validate_state(state):
    """CodexAstraUlt: Empty or loosely typed observations cannot establish parity."""
    fields = {"cycles", "frames", "guest_exited", "registers", "cpsr", "vfp_registers",
              "fpscr", "fpexc", "tls", "exclusive_address", "current_thread", "thread_guest_id",
              "reschedule_pending", "all_blocked", "next_kernel_event", "memory", "graphics", "audio"}
    require(isinstance(state, dict) and set(state) == fields, "invalid_worker_state_fields")
    for name in ("cycles", "frames"):
        uint(state[name], name)
    for name in ("guest_exited", "reschedule_pending", "all_blocked"):
        require(type(state[name]) is bool, "invalid_worker_" + name)
    for name, count in (("registers", 16), ("vfp_registers", 32)):
        values = state[name]
        require(isinstance(values, list) and len(values) == count, "invalid_worker_" + name)
        for value in values:
            uint(value, name, 2**32 - 1)
    for name in ("cpsr", "fpscr", "fpexc", "tls"):
        uint(state[name], name, 2**32 - 1)
    for name in ("exclusive_address", "current_thread", "thread_guest_id", "next_kernel_event"):
        if state[name] is not None:
            uint(state[name], name, 2**64 - 1 if name == "next_kernel_event" else 2**32 - 1)
    memory = state["memory"]
    hashes = {"fcram_fnv1a64", "vram_fnv1a64", "dsp_ram_fnv1a64", "axi_wram_fnv1a64",
              "mapping_fnv1a64", "allocation_fnv1a64"}
    require(isinstance(memory, dict) and set(memory) == hashes | {"allocation_regions", "region_used_bytes"},
            "invalid_worker_memory_state")
    for name in hashes:
        require(isinstance(memory[name], str) and re.fullmatch(r"[0-9a-f]{16}", memory[name]) is not None,
                "invalid_worker_memory_fingerprint")
    require(isinstance(memory["region_used_bytes"], list) and len(memory["region_used_bytes"]) == 3,
            "invalid_worker_memory_regions")
    for value in memory["region_used_bytes"]:
        uint(value, "region_used_bytes", 2**32 - 1)
    regions = memory["allocation_regions"]
    require(isinstance(regions, list) and len(regions) == 3, "invalid_worker_allocation_regions")
    for region in regions:
        require(isinstance(region, list) and len(region) == 2, "invalid_worker_allocation_region")
        for value in region:
            uint(value, "allocation_region", 2**32 - 1)
    graphics = state["graphics"]
    require(isinstance(graphics, dict) and set(graphics) == {"command_lists", "draw_calls", "vertices_drawn"},
            "invalid_worker_graphics_state")
    for name, value in graphics.items():
        uint(value, name)
    audio = state["audio"]
    require(isinstance(audio, dict) and set(audio) == {"pcm_pairs", "nonzero_pairs", "pcm_fnv1a64"},
            "invalid_worker_audio_state")
    pairs = uint(audio["pcm_pairs"], "pcm_pairs")
    uint(audio["nonzero_pairs"], "nonzero_pairs", pairs)
    require(isinstance(audio["pcm_fnv1a64"], str) and re.fullmatch(r"[0-9a-f]{16}", audio["pcm_fnv1a64"]) is not None,
            "invalid_worker_audio_fingerprint")
    return state


def validate_worker(report, request, exit_code):
    """CodexAstraUlt: Bind the report to this invocation before comparing states."""
    require(isinstance(report, dict) and type(report.get("schema_version")) is int
            and report["schema_version"] == 1
            and report.get("kind") == "droidds_private_native_run", "invalid_worker_report")
    require(report.get("route") == request["route"], "worker_route_mismatch")
    for key in ("preparation_sha256", "contract_sha256"):
        require(report.get(key) == request[key], "worker_" + key + "_mismatch")
    require(report.get("library_sha256") == request["library"]["sha256"], "worker_library_mismatch")
    require(PREP.canonical(report.get("limits")) == PREP.canonical(request["limits"]), "worker_limits_mismatch")
    require(report.get("status") in ("guest_exited", "budget_exhausted", "blocked", "load_error", "internal_error"),
            "invalid_worker_status")
    good = report["status"] in ("guest_exited", "budget_exhausted", "blocked")
    require(type(exit_code) is int and (exit_code == 0) == good, "worker_exit_status_mismatch")
    for name in ("library_loaded", "runtime_binding_enforced", "guest_execution_performed",
                 "library_load_attempted", "guest_execution_attempted"):
        require(type(report.get(name)) is bool, "invalid_worker_" + name)
    require(not report["library_loaded"] or report["library_load_attempted"], "worker_load_attempt_mismatch")
    require(not report["guest_execution_performed"] or report["guest_execution_attempted"],
            "worker_execution_attempt_mismatch")
    require(isinstance(report.get("reason"), str) and len(report["reason"]) <= 4096,
            "invalid_worker_reason")
    observed = report.get("observed")
    require(isinstance(observed, dict), "invalid_worker_observed")
    if not good:
        require(observed == {}, "invalid_worker_incomplete_observations")
        checkpoints = report.get("checkpoints")
        require(isinstance(checkpoints, list) and len(checkpoints) <= 4, "invalid_worker_checkpoints")
        previous = 0
        for point in checkpoints:
            require(isinstance(point, dict), "invalid_worker_checkpoint")
            cycle = uint(point.get("requested_cycle"), "checkpoint_cycle", request["limits"]["max_cycles"])
            state = validate_state(point.get("state"))
            require(cycle in (100000, 500000, 1000000, 2000000) and cycle > previous
                    and type(point.get("exact_cycle")) is bool
                    and state["cycles"] >= cycle and point["exact_cycle"] == (state["cycles"] == cycle),
                    "worker_checkpoint_cycle_mismatch")
            previous = cycle
        return report
    observed_fields = {"steps", "cycles", "frames", "cycles_after_budget", "interpreted_instructions",
                       "recompiled_instructions", "native_callback_fallback_instructions",
                       "guest_debug_bytes_discarded", "services_seen", "state"}
    require(set(observed) == observed_fields, "invalid_worker_observed_fields")
    for name in observed_fields - {"services_seen", "state"}:
        uint(observed[name], name)
    require(observed["steps"] <= request["limits"]["max_steps"], "worker_step_budget_exceeded")
    require(observed["cycles_after_budget"] == max(0, observed["cycles"] - request["limits"]["max_cycles"]),
            "worker_cycle_overrun_mismatch")
    require(observed["native_callback_fallback_instructions"] <= observed["recompiled_instructions"],
            "worker_fallback_accounting_mismatch")
    require(isinstance(observed["services_seen"], list) and len(observed["services_seen"]) <= 64
            and all(isinstance(name, str) and len(name) <= 32 for name in observed["services_seen"]),
            "invalid_worker_services")
    final = validate_state(observed["state"])
    require((final["cycles"], final["frames"]) == (observed["cycles"], observed["frames"]),
            "worker_final_state_counter_mismatch")
    require(report["guest_execution_performed"] ==
            (observed["interpreted_instructions"] + observed["recompiled_instructions"] > 0)
            and report["runtime_binding_enforced"] is True, "worker_execution_admission_mismatch")
    require(report["library_loaded"] == (request["route"] == "native"), "worker_library_load_route_mismatch")
    if request["route"] == "interpreter":
        require(observed["recompiled_instructions"] == observed["native_callback_fallback_instructions"] == 0,
                "interpreter_reported_native_execution")
    require((report["status"] == "guest_exited") == final["guest_exited"], "worker_guest_exit_mismatch")
    checkpoints = report.get("checkpoints")
    require(isinstance(checkpoints, list) and len(checkpoints) <= 4, "invalid_worker_checkpoints")
    previous = 0
    for checkpoint in checkpoints:
        require(isinstance(checkpoint, dict), "invalid_worker_checkpoint")
        cycle = uint(checkpoint.get("requested_cycle"), "checkpoint_cycle", request["limits"]["max_cycles"])
        require(cycle in (100000, 500000, 1000000, 2000000) and cycle > previous,
                "invalid_worker_checkpoint_order")
        require(type(checkpoint.get("exact_cycle")) is bool and isinstance(checkpoint.get("state"), dict),
                "invalid_worker_checkpoint_state")
        state = validate_state(checkpoint["state"])
        require(cycle <= state["cycles"] <= observed["cycles"]
                and checkpoint["exact_cycle"] == (state["cycles"] == cycle),
                "worker_checkpoint_cycle_mismatch")
        previous = cycle
    return report


def comparison(interpreter, native):
    """CodexAstraUlt: Compare only matched cycle checkpoints or a matched exit.

FNV fingerprints are diagnostic evidence, not collision-resistant input identity
or a proof of complete emulation correctness. Route counters never enter equality.
"""
    matches, mismatches, skipped = [], [], []
    # CodexAstraUlt: This helper also rejects fabricated states when called by
    # tests or future callers without the preceding worker-envelope validator.
    for report in (interpreter, native):
        validate_state(report["observed"]["state"])
        for name in ("interpreted_instructions", "recompiled_instructions", "native_callback_fallback_instructions"):
            uint(report["observed"].get(name), name)
        require(report["observed"]["native_callback_fallback_instructions"] <=
                report["observed"]["recompiled_instructions"], "worker_fallback_accounting_mismatch")
        for item in report["checkpoints"]:
            cycle = uint(item.get("requested_cycle"), "checkpoint_cycle")
            state = validate_state(item["state"])
            require(type(item.get("exact_cycle")) is bool and item["exact_cycle"] == (state["cycles"] == cycle)
                    and state["cycles"] >= cycle, "worker_checkpoint_cycle_mismatch")
    left = {item["requested_cycle"]: item for item in interpreter["checkpoints"]}
    right = {item["requested_cycle"]: item for item in native["checkpoints"]}
    for cycle in sorted(left.keys() | right.keys()):
        a, b = left.get(cycle), right.get(cycle)
        if a is None or b is None or not a["exact_cycle"] or not b["exact_cycle"]:
            skipped.append(cycle)
            continue
        if a["state"] == b["state"]:
            matches.append(cycle)
        else:
            mismatches.append({"cycle": cycle, "different_fields": sorted(
                key for key in a["state"].keys() | b["state"].keys() if a["state"].get(key) != b["state"].get(key))})
    exit_match = None
    if interpreter["status"] == native["status"] == "guest_exited":
        a, b = interpreter["observed"].get("state"), native["observed"].get("state")
        require(a["guest_exited"] and b["guest_exited"], "worker_guest_exit_mismatch")
        if a["cycles"] == b["cycles"]:
            exit_match = a == b
            if not exit_match:
                mismatches.append({"cycle": a.get("cycles"), "different_fields": sorted(
                    key for key in a.keys() | b.keys() if a.get(key) != b.get(key))})
    # CodexAstraUlt: The bridge counts callback-interpreted instructions inside
    # its dispatch total. An entirely interpreted callback run cannot qualify
    # generated native execution merely because it entered that bridge.
    native_dispatch = native["observed"]["recompiled_instructions"]
    callbacks = native["observed"]["native_callback_fallback_instructions"]
    native_count = native_dispatch - callbacks
    state = "different" if mismatches else "matched" if (matches or exit_match is True) and native_count > 0 else "inconclusive"
    return {"status": state, "matched_cycles": matches, "unmatched_cycles": skipped,
            "mismatches": mismatches, "guest_exit_match": exit_match,
            "native_instructions_observed": native_count,
            "compiled_dispatch_instructions": native_dispatch,
            "callback_interpreted_instructions": callbacks,
            "scope": "bounded CPU/state fingerprint comparison; not a boot or correctness proof"}


def source_identity():
    """CodexAstraUlt: Extend historical provenance with the actual native worker/fence sources."""
    result = COMMON.source_identity()
    names = ["Cargo.toml", "crates/droidds-native-title-tools/Cargo.toml",
             "vendor/zakuro/crates/zakuro-core/Cargo.toml",
             "vendor/zakuro/crates/zakuro-core/src/recompiled.rs",
             "vendor/zakuro/crates/zakuro-core/src/memory/mod.rs",
             "vendor/zakuro/crates/zakuro-core/src/memory/physical.rs",
             "vendor/zakuro/crates/zakuro-core/src/memory/fence.rs",
             "vendor/zakuro/crates/zakuro-core/src/state/mod.rs"]
    names.extend(path.relative_to(ROOT).as_posix()
                 for path in sorted((ROOT / "crates/droidds-native-title-tools/src").rglob("*.rs")))
    for name in names:
        result["files_sha256"][name] = COMPILE.identity(ROOT / name, MAX_REQUEST)["sha256"]
    return result


def parse_args(argv=None):
    """CodexAstraUlt: One fresh paired test with explicit private artifact paths."""
    parser = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    parser.add_argument("--preparation", type=Path, required=True)
    parser.add_argument("--compilation", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--worker", type=Path, default=ROOT / "target/release/droidds-native-title")
    parser.add_argument("--model", choices=("old", "new"), default="old")
    parser.add_argument("--max-steps", type=int, default=10_000_000)
    parser.add_argument("--max-cycles", type=int, default=2_000_000)
    parser.add_argument("--max-frames", type=int, default=120)
    parser.add_argument("--max-seconds", type=int, default=60)
    parser.add_argument("--timeout", type=int, default=70)
    parser.add_argument("--cpu-seconds", type=int, default=120)
    parser.add_argument("--memory-mib", type=int, default=4096)
    values = sys.argv[1:] if argv is None else argv
    flags = [word.split("=", 1)[0] for word in values if word.startswith("--")]
    if len(flags) != len(set(flags)):
        parser.error("duplicate native-run option")
    args = parser.parse_args(values)
    for key, low, high in (("max_steps", 1, 1_000_000_000), ("max_cycles", 1, 26_811_185_600),
                           ("max_frames", 1, 6000), ("max_seconds", 1, 300), ("timeout", 1, 310),
                           ("cpu_seconds", 1, 311), ("memory_mib", 256, 16384)):
        if not low <= getattr(args, key) <= high:
            parser.error(key + " outside supported range")
    if args.timeout <= args.max_seconds:
        parser.error("timeout must exceed the cooperative worker wall limit")
    return args


def run(args):
    """CodexAstraUlt: Failed admission cannot fall through to a native load."""
    report = {"schema_version": 1, "kind": "droidds_private_native_comparison",
              "status": "rejected", "reason": "preflight", "routes": {}, "comparison": None,
              "limitations": ["Linux host base-code diagnostic fence; dynamic modules stay interpreted.",
                              "SIGSEGV alone does not identify a code write or its cause.",
                              "No Android/Thor performance or interactive boot qualification.",
                              "Trusted local native build; not an untrusted-library sandbox."]}
    output, created = None, False
    try:
        require(platform.system() == "Linux" and os.sysconf("SC_PAGE_SIZE") == 4096,
                "native_diagnostic_requires_linux_4k_pages")
        output, worker = (COMMON.absolute_plain(value) for value in (args.output, args.worker))
        COMMON.outside_git(output)
        require(not os.path.lexists(output) and output.parent.is_dir(), "output_must_be_new_with_existing_parent")
        for source in (COMMON.absolute_plain(args.preparation), COMMON.absolute_plain(args.compilation)):
            require(output != source and output not in source.parents and source not in output.parents,
                    "native_output_must_be_separate")
        worker_identity = COMPILE.identity(worker, COMMON.MAX_WORKER_BYTES)
        require(os.access(worker, os.X_OK), "native_worker_is_not_executable")
        output.mkdir(mode=0o700)
        created = True
        report["worker"] = worker_identity
        report["source"] = source_identity()
        report["coordinator"] = {name: COMPILE.identity(ROOT / "tools" / name, MAX_REQUEST)["sha256"]
                                 for name in ("run_compiled_title.py", "private_runtime_inputs.py",
                                              "private_runtime_elf.py", "private_runtime_process.py")}
        COMMON.save_report(output, report)
        with INPUTS.admitted_inputs(args.preparation, args.compilation) as admitted, ExitStack() as stack:
            plan = admitted["plan"]
            audit = ELF.audit_runtime_library(admitted["library_path"], plan["contract"]["machine"],
                plan["contract"]["preparation_sha256"], plan["contract_sha256"], admitted["units"])
            require(audit.get("runtime_tables_validated") is True and audit.get("library_loaded") is False,
                    "runtime_table_audit_incomplete")
            library, bundle = seal_inputs(stack, admitted, audit)
            report["admission"] = {"preparation_sha256": plan["contract"]["preparation_sha256"],
                "contract_sha256": plan["contract_sha256"],
                "compiled_manifest_sha256": admitted["compiled_manifest_sha256"],
                "input": admitted["loaded"]["manifest"]["input"],
                "library": {key: library[key] for key in ("bytes", "sha256")},
                "identity_bundle": {key: bundle[key] for key in ("bytes", "sha256")}, "static_audit": audit}
            for route in ("interpreter", "native"):
                directory = output / route
                directory.mkdir(mode=0o700)
                request = make_request(args, admitted, audit, library, bundle, route)
                request_bytes = PREP.canonical(request)
                sealed_request = seal_parts(stack, "droidds-native-request", [request_bytes], MAX_REQUEST)
                command = [str(worker), "--request-fd", str(sealed_request["descriptor"]),
                           "--data-dir", str(directory / "runtime-data"), "--output", str(directory / "worker-report.json")]
                process = PROCESS.run_worker(command, directory, args.timeout, args.cpu_seconds,
                    args.memory_mib, pass_fds=(sealed_request["descriptor"], library["descriptor"], bundle["descriptor"]))
                tail = process.pop("log_tail")
                COMMON.write_new(directory / "worker.log", tail.encode() if isinstance(tail, str) else tail)
                result = {"process": process, "request_sha256": sealed_request["sha256"], "worker_report": None}
                report["routes"][route] = result
                report["status"], report["reason"] = "incomplete", "worker_did_not_complete"
                COMMON.save_report(output, report)
                if process["outcome"] != "completed" or process["exit_code"] < 0:
                    report["reason"] = ("worker_signal_" + str(-process["exit_code"]) if process["exit_code"] < 0
                                        else "worker_" + process["outcome"])
                    break
                value = PREP.read_json(directory / "worker-report.json", MAX_REPORT)
                result["worker_report"] = validate_worker(value, request, process["exit_code"])
                if value["status"] in ("load_error", "internal_error", "blocked"):
                    report["status"], report["reason"] = "blocked", route + "_" + value["status"]
                    break
                require(COMPILE.identity(worker, COMMON.MAX_WORKER_BYTES) == worker_identity, "native_worker_changed")
            else:
                report["comparison"] = comparison(report["routes"]["interpreter"]["worker_report"],
                                                   report["routes"]["native"]["worker_report"])
                report["status"], report["reason"] = "compared", report["comparison"]["status"]
            INPUTS.verify_unchanged(admitted)
            require(COMPILE.identity(worker, COMMON.MAX_WORKER_BYTES) == worker_identity, "native_worker_changed")
            require(source_identity()["files_sha256"] == report["source"]["files_sha256"], "native_runtime_source_changed")
            for name, digest in report["coordinator"].items():
                require(COMPILE.identity(ROOT / "tools" / name, MAX_REQUEST)["sha256"] == digest,
                        "native_run_coordinator_changed")
            report["preserved_inputs_verified"] = True
    except KeyboardInterrupt:
        report["status"], report["reason"] = "interrupted", "coordinator_interrupted"
    except (ValueError, OSError, KeyError, TypeError, RuntimeError) as error:
        report["status"], report["reason"] = "rejected", str(error) if isinstance(error, (ValueError, RuntimeError)) else type(error).__name__
    finally:
        if created:
            COMMON.save_report(output, report)
    return (0 if report["status"] == "compared" else 1), report


def main(argv=None):
    """CodexAstraUlt: SIGTERM preserves the same bounded cancellation path as Ctrl-C."""
    def interrupt(_signum, _frame):
        raise KeyboardInterrupt
    previous = signal.signal(signal.SIGTERM, interrupt)
    try:
        code, report = run(parse_args(argv))
    finally:
        signal.signal(signal.SIGTERM, previous)
    print(json.dumps({"status": report["status"], "reason": report["reason"]}))
    return code


if __name__ == "__main__":
    raise SystemExit(main())
