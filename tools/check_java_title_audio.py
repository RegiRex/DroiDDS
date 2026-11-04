#!/usr/bin/env python3
"""CodexAstraUlt: Exercise actual title audio logic with deterministic platform stubs."""

import argparse
import json
from pathlib import Path
import subprocess


CONTROLS = ["backpressure_preserves_pcm_order", "bounded_partial_zero_write_queue",
            "invalid_writes_preserve_accounting", "startup_pause_resume_preserves_ownership",
            "cleanup_failures_release_once"]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--java-home", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    args.output.mkdir(parents=True, exist_ok=False)
    java = args.java_home / "bin"
    # CodexAstraUlt: Stubs supply only unavailable platform calls; production
    # queue, resampling, prefill, adapter and cleanup code execute unchanged.
    sources = [root / "android/title/java/org/droidds/probe" / name
               for name in ("TitleAudio.java", "TitlePcmQueue.java")]
    sources += [root / "android/probe/java/org/droidds/probe" / name
                for name in ("PcmResampler.java", "AudioStartup.java")]
    sources += sorted((root / "tools/java-tests/audio-stubs").rglob("*.java"))
    sources.append(root / "tools/java-tests/org/droidds/probe/TitleAudioTest.java")
    subprocess.run([str(java / "javac"), "--release", "8", "-Xlint:all", "-Werror", "-d", str(args.output),
                    *map(str, sources)], check=True, timeout=60)
    result = subprocess.run([str(java / "java"), "-cp", str(args.output), "org.droidds.probe.TitleAudioTest"],
                            check=True, timeout=30, text=True, capture_output=True)
    report = json.loads(result.stdout)
    if (report.get("schema") != 1 or report.get("kind") != "droidds-java-title-audio"
            or report.get("status") != "passed" or report.get("checks", 0) < 50
            or report.get("controls") != CONTROLS):
        raise ValueError("Required title audio controls did not execute")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
