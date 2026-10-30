#!/usr/bin/env python3
"""CodexAstraUlt: Exercise actual original preparation, compilation and native admission.

Only authored PICA and CPU-loop fixtures are accepted here. Private games belong in the
separate bounded coordinator; this gate supplies no private title compatibility.
"""

import argparse
import importlib.util
import json
from pathlib import Path


# CodexAstraUlt: Reuse the production path so CI cannot substitute hand-written
# ABI tables or a mocked worker for actual generated native execution.
SPEC = importlib.util.spec_from_file_location("native_pipeline", Path(__file__).with_name("run_compiled_title.py"))
RUN = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(RUN)


def run_title(source, root, args):
    """CodexAstraUlt: Both authored workloads use the identical production chain."""
    code, prepared = RUN.PREP.run(RUN.PREP.parse_args([
        "--input", str(source), "--output", str(root / "preparation"), "--worker", str(args.preparer)]))
    RUN.require(code == 0 and prepared["status"] == "prepared", "original_preparation_failed")
    code, compiled = RUN.COMPILE.run(RUN.COMPILE.parse_args([
        "--preparation", str(root / "preparation"), "--output", str(root / "compilation"),
        "--batch-seconds", "120", "--command-seconds", "30", "--cpu-seconds", "30",
        "--memory-mib", "1024", "--output-mib", "64"]))
    RUN.require(code == 0 and compiled["status"] == "compiled", "original_compilation_failed")
    code, report = RUN.run(RUN.parse_args([
        "--preparation", str(root / "preparation"), "--compilation", str(root / "compilation"),
        "--output", str(root / "comparison"), "--worker", str(args.worker)]))
    RUN.require(code == 0 and report["status"] == "compared", "original_routes_did_not_complete")
    return report


def check(args):
    root = RUN.COMMON.absolute_plain(args.output)
    RUN.COMMON.outside_git(root)
    root.mkdir(mode=0o700)
    producer = RUN.COMMON.absolute_plain(args.producer)
    result = RUN.COMPILE.PROCESS.run_command(
        [str(producer), "emit", "--output", str(root / "fixture")], root,
        timeout=30, cpu_seconds=30, memory_mib=1024, file_bytes=64 * RUN.MIB)
    RUN.require(result["outcome"] == "completed" and result["exit_code"] == 0, "original_fixture_producer_failed")
    source = root / "fixture/runtime-fixture.cxi"
    report = run_title(source, root, args)
    RUN.require(report["reason"] == "matched",
                "original_native_comparison_failed")
    RUN.require(report["comparison"]["guest_exit_match"] is True and report["preserved_inputs_verified"] is True,
                "original_native_exit_or_preservation_failed")
    for route in ("interpreter", "native"):
        worker = report["routes"][route]["worker_report"]
        observed = worker["observed"]
        RUN.require(worker["status"] == "guest_exited" and observed["cycles"] == 606
                    and observed["interpreted_instructions"] + observed["recompiled_instructions"] == 606
                    and observed["state"]["graphics"] == {"command_lists": 1, "draw_calls": 2, "vertices_drawn": 6},
                    "original_native_execution_oracle_failed")
    # CodexAstraUlt: A second authored guest crosses a real budget checkpoint
    # before GetSystemTick/ExitProcess. This exercises the parent comparison's
    # positive post-SVC gate, which the short two-draw guest never reaches.
    loop_root = root / "synchronized-loop"
    loop_root.mkdir(mode=0o700)
    original = bytearray(source.read_bytes())
    words = [0xe59f1028, 0xe1a00000, 0xe1a00000, 0xe1a00000, 0xe1a00000,
             0xe2800001, 0xe1500001, 0xe1a00000, 0xe1a00000, 0x1afffffa,
             0xef000028, 0xef000003, 40000]
    # ldr r1,40000; four NOPs; ADD/CMP/NOP/NOP/BNE loop; two original SVCs.
    RUN.require(len(original) >= 0x800 + 4 * len(words), "original_loop_template_too_short")
    for index, word in enumerate(words):
        original[0x800 + index * 4:0x804 + index * 4] = word.to_bytes(4, "little")
    loop_input = loop_root / "original-loop.cxi"
    RUN.COMMON.write_new(loop_input, original)
    loop = run_title(loop_input, loop_root, args)
    raw, synchronized = loop["comparison"], loop["synchronized_comparison"]
    RUN.require(loop["reason"] == "different" and raw["guest_exit_match"] is True
                and raw["mismatches"] == [{"cycle": 100000, "different_fields": ["cpsr"]}]
                and synchronized["status"] == "matched" and not synchronized["mismatches"]
                and loop["preserved_inputs_verified"] is True, "original_synchronized_comparison_failed")
    matched = synchronized["matched_boundaries"]
    RUN.require(len(matched) == 1 and matched[0]["requested_cycle"] == 100000
                and matched[0]["cycle"] == 200156
                and matched[0]["native_instructions_observed"] == 200006,
                "original_synchronized_native_oracle_failed")
    for route in ("interpreter", "native"):
        observed = loop["routes"][route]["worker_report"]["observed"]
        RUN.require(observed["cycles"] == 200157
                    and observed["interpreted_instructions"] + observed["recompiled_instructions"] == 200007
                    and observed["state"]["graphics"] == {"command_lists": 0, "draw_calls": 0, "vertices_drawn": 0},
                    "original_loop_execution_oracle_failed")
    return {"status": "passed", "fixture": "droidds-original-pica-ipc-v1",
            "guest_instructions_each_route": 606, "draws_each_route": 2,
            "native_instructions": report["comparison"]["native_instructions_observed"],
            "library": report["admission"]["library"], "comparison_report": str(root / "comparison/report.json"),
            "synchronized_loop": {"raw_status": raw["status"], "synchronized_status": synchronized["status"],
                "matched_boundaries": matched, "library": loop["admission"]["library"],
                "comparison_report": str(loop_root / "comparison/report.json")}}


def main():
    parser = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--producer", type=Path, default=RUN.ROOT / "target/release/droidds-runtime-probe")
    parser.add_argument("--preparer", type=Path, default=RUN.ROOT / "target/release/droidds-prepare-title")
    parser.add_argument("--worker", type=Path, default=RUN.ROOT / "target/release/droidds-native-title")
    print(json.dumps(check(parser.parse_args()), indent=2))


if __name__ == "__main__":
    main()
