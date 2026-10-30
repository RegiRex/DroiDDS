#!/usr/bin/env python3
"""CodexAstraUlt: Execute actual title import/input logic with original data."""

import argparse
import json
from pathlib import Path
import subprocess


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--java-home", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    args.output.mkdir(parents=True, exist_ok=False)
    java = args.java_home / "bin"
    sources = [root / "android/title/java/org/droidds/probe" / name
               for name in ("TitleImport.java", "TitleInput.java", "TitleLoop.java")]
    sources.append(root / "tools/java-tests/org/droidds/probe/TitleLogicTest.java")
    subprocess.run([str(java / "javac"), "--release", "8", "-Xlint:all", "-Werror", "-d", str(args.output),
                    *map(str, sources)], check=True, timeout=60)
    result = subprocess.run([str(java / "java"), "-cp", str(args.output), "org.droidds.probe.TitleLogicTest"],
                            check=True, timeout=30, text=True, capture_output=True)
    report = json.loads(result.stdout)
    if (report.get("schema") != 1 or report.get("kind") != "droidds-java-title-logic"
            or report.get("status") != "passed" or report.get("checks", 0) < 40
            or report.get("controls") != ["verified_import_reuse_preservation", "rejection_cancel_io_cleanup",
                 "atomic_publication_races", "symlink_and_atomic_report_preservation", "input_edges_axes_release",
                 "pause_resume_retires_delayed_callbacks"]):
        raise ValueError("Required title frontend controls did not execute")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
