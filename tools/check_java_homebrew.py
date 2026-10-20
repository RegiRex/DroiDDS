#!/usr/bin/env python3
"""CodexAstraUlt: Run actual pure Java frontend logic, without Android mocks."""

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
    sources = [root / "android/probe/java/org/droidds/probe" / name
               for name in ("PcmResampler.java", "ScreenGeometry.java", "FramePacer.java", "AudioStartup.java")]
    sources.append(root / "tools/java-tests/org/droidds/probe/HomebrewLogicTest.java")
    subprocess.run([str(java / "javac"), "--release", "8", "-Xlint:all", "-Werror", "-d", str(args.output),
                    *map(str, sources)], check=True, timeout=60)
    result = subprocess.run([str(java / "java"), "-cp", str(args.output), "org.droidds.probe.HomebrewLogicTest"],
                            check=True, timeout=30, text=True, capture_output=True)
    report = json.loads(result.stdout)
    if report != {"schema": 1, "kind": "droidds-java-homebrew-logic", "status": "passed", "controls": [
            "time_based_pcm_oracle", "chunk_and_pause_continuity", "full_scale_and_invalid_pcm",
            "letterbox_touch_and_resize", "absolute_deadline_jitter_and_overload",
            "pause_resets_frame_timeline", "guest_pcm_prefill_and_partial_writes"]}:
        raise ValueError("Required frontend math controls did not execute")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
