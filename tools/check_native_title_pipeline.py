#!/usr/bin/env python3
"""CodexAstraUlt: Exercise actual original preparation, compilation and native admission.

Only the authored PICA fixture is accepted here. Private games belong in the
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
    RUN.require(code == 0 and report["status"] == "compared" and report["reason"] == "matched",
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
    return {"status": "passed", "fixture": "droidds-original-pica-ipc-v1",
            "guest_instructions_each_route": 606, "draws_each_route": 2,
            "native_instructions": report["comparison"]["native_instructions_observed"],
            "library": report["admission"]["library"], "comparison_report": str(root / "comparison/report.json")}


def main():
    parser = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--producer", type=Path, default=RUN.ROOT / "target/release/droidds-runtime-probe")
    parser.add_argument("--preparer", type=Path, default=RUN.ROOT / "target/release/droidds-prepare-title")
    parser.add_argument("--worker", type=Path, default=RUN.ROOT / "target/release/droidds-native-title")
    print(json.dumps(check(parser.parse_args()), indent=2))


if __name__ == "__main__":
    main()
