#!/usr/bin/env python3
"""CodexAstraUlt: Build and verify the public CPU foundation, preserving evidence."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import shlex
import shutil
import signal
import subprocess
import sys
import tomllib

ROOT = Path(__file__).resolve().parents[1]


def interrupted(_signal: int, _frame) -> None:
    """CodexAstraUlt: CI SIGTERM follows the same owned-child cleanup as Ctrl-C."""
    raise KeyboardInterrupt("termination requested")


def validate_report(report: dict, pins: dict) -> None:
    """CodexAstraUlt: A successful process must also prove every required route."""
    if report.get("schema") != 1 or report.get("status") != "passed":
        raise ValueError("Synthetic report is incomplete or did not pass")
    for key in ("abi", "generation"):
        if report.get(key) != pins["recompiler"][key]:
            raise ValueError(f"Synthetic {key} does not match the selected ABI")
    expected = {"arm_integer_memory", "thumb_integer_memory",
                "arm_missing_entry_fallback", "arm_to_thumb_native"}
    cases = report.get("cases", [])
    names = [case["name"] for case in cases]
    if len(names) != len(set(names)) or not expected.issubset(names):
        raise ValueError("Synthetic report is missing required CPU cases")
    for case in cases:
        if case.get("status") != "passed":
            raise ValueError(f"CPU case did not pass: {case['name']}")
        for key in ("native_calls", "native_budget_charged", "fallback_steps"):
            if type(case.get(key)) is not int or case[key] < 0:
                raise ValueError(f"Missing or invalid route counter: {key}")
        if case["native_calls"] == 0 or case["native_budget_charged"] == 0:
            raise ValueError(f"Native execution not demonstrated: {case['name']}")
        if case["name"] == "arm_missing_entry_fallback":
            if case["fallback_steps"] == 0:
                raise ValueError("Missing-entry fallback was not exercised")
        elif case["name"] in expected and case["fallback_steps"] != 0:
            raise ValueError(f"Unexpected fallback in native-only case: {case['name']}")
    controls = report.get("negative_controls", [])
    required = {"nan_shaped_integer_register_mismatch", "nan_shaped_integer_memory_mismatch",
                "guest_instruction_limit", "process_watchdog"}
    names = [control["name"] for control in controls]
    if len(names) != len(set(names)) or not required.issubset(names):
        raise ValueError("Synthetic report is missing required negative controls")
    if any(control.get("status") != "passed" for control in controls):
        raise ValueError("A synthetic negative control did not pass")


def validate_graph(metadata: dict, pins: dict) -> dict:
    """CodexAstraUlt: Check the active graph, not unused optional lock entries."""
    if pins.get("schema") != 1 or pins.get("verification") != {
        "upstream_verify_feature": False, "oracle": "strict-synthetic-known-output"
    }:
        raise ValueError("Unsupported source-lock schema or verification policy")
    packages = {p["id"]: p for p in metadata["packages"]}
    nodes = {n["id"]: n for n in metadata["resolve"]["nodes"]}
    active, pending = set(), list(metadata["workspace_members"])
    while pending:
        package_id = pending.pop()
        if package_id in active:
            continue
        if package_id not in nodes or package_id not in packages:
            raise ValueError(f"Missing resolved package: {package_id}")
        active.add(package_id)
        pending.extend(d["pkg"] for d in nodes[package_id]["deps"])
    selected = {}
    for group in ("recompiler", "runtime"):
        expected = pins[group]
        for name in expected["packages"]:
            matches = [packages[i] for i in active if packages[i]["name"] == name]
            if len(matches) != 1:
                raise ValueError(f"Expected one active {name}, found {len(matches)}")
            package = matches[0]
            source = package.get("source") or ""
            prefix = "git+" + expected["repository"] + "?rev=" + expected["revision"]
            if source != prefix + "#" + expected["revision"]:
                raise ValueError(f"Source pin mismatch for {name}: {source}")
            if name == "recomp3ds" and "verify" in nodes[package["id"]]["features"]:
                raise ValueError("The upstream permissive verifier must not be enabled")
            selected[name] = {"source": source, "version": package["version"]}
    if any(packages[i]["name"] in ("zakuro", "zakuro-gpu", "zakuro-core") for i in active):
        raise ValueError("The CPU foundation unexpectedly includes frontend/GPU/core crates")
    return selected


def terminate_group(process: subprocess.Popen) -> None:
    """CodexAstraUlt: Allow nested supervisors to reap their owned worker groups."""
    if process.poll() is None:
        try:
            os.killpg(process.pid, signal.SIGTERM)
        except ProcessLookupError:
            pass
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            try:
                os.killpg(process.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
    process.wait()


def run_logged(name: str, command: list[str], out: Path, results: list,
               timeout: int = 900, require_tests: bool = False) -> str:
    """CodexAstraUlt: Preserve command status and complete bounded command logs."""
    print(f"[{name}] {shlex.join(command)}", flush=True)
    path = out / f"{name}.log"
    with path.open("w", encoding="utf-8") as log:
        process = subprocess.Popen(command, cwd=ROOT, stdout=log,
                                   stderr=subprocess.STDOUT, start_new_session=True)
        try:
            code = process.wait(timeout=timeout)
        except (subprocess.TimeoutExpired, KeyboardInterrupt):
            terminate_group(process)
            results.append({"step": name, "command": command, "status": "inconclusive",
                            "reason": "timeout-or-interruption", "log": path.name})
            raise RuntimeError(f"{name} timed out or was interrupted") from None
    output = path.read_text(encoding="utf-8", errors="replace")
    result = {"step": name, "command": command, "exit_code": code, "log": path.name}
    results.append(result)
    if code:
        print(output[-6000:], file=sys.stderr)
        raise RuntimeError(f"{name} failed with exit code {code}; see {path}")
    if require_tests:
        # CodexAstraUlt: A zero-test run does not satisfy a required suite. Keep
        # ignored/filtered counts visible instead of treating them as passes.
        rows = re.findall(r"test result: ok\. (\d+) passed; (\d+) failed; (\d+) ignored; "
                          r"(\d+) measured; (\d+) filtered out", output)
        counts = {key: sum(int(row[i]) for row in rows) for i, key in enumerate(
            ("passed", "failed", "ignored", "measured", "filtered"))}
        result["tests"] = counts
        if "layout went unchecked" in output:
            raise RuntimeError(f"{name} silently skipped its required C ABI layout probe")
        if counts["passed"] == 0 or counts["failed"]:
            raise RuntimeError(f"{name} did not execute a passing required suite")
        print(f"[{name}] {counts}", flush=True)
    return output


def snapshot() -> dict:
    """CodexAstraUlt: Bind local results to code/lock inputs, even before commit."""
    paths = [ROOT / name for name in ("Cargo.toml", "Cargo.lock", "rust-toolchain.toml",
                                     "upstream.lock.toml")]
    paths.extend(sorted((ROOT / "tools").rglob("*.py")))
    paths.extend(sorted((ROOT / "crates").rglob("*.rs")))
    paths.extend(sorted((ROOT / "crates").rglob("Cargo.toml")))
    return {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in paths}


def main() -> int:
    # CodexAstraUlt: Fresh result directories prevent accidentally reporting a
    # previous run's success. Linux is the explicit first supported build host.
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--jobs", type=int, default=2)
    args = parser.parse_args()
    if sys.platform != "linux":
        parser.error("the first foundation build supports Linux only")
    if not 1 <= args.jobs <= 8:
        parser.error("--jobs must be between 1 and 8")
    signal.signal(signal.SIGTERM, interrupted)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S.%fZ")
    out = (args.output or ROOT / "out" / f"foundation-{stamp}").resolve()
    out.mkdir(parents=True, exist_ok=False)
    evidence = {"schema": 1, "started_utc": stamp, "status": "failed", "steps": []}
    try:
        cargo = shutil.which("cargo")
        compiler = os.environ.get("CC", "cc")
        if not cargo or not shutil.which(compiler):
            raise RuntimeError("Install pinned Rust and a C compiler; CC must name one executable")
        # CodexAstraUlt: Upstream CC accepts command words, but this reproducible
        # first runner deliberately uses a single explicit executable path.
        os.environ["CC"] = shutil.which(compiler)
        versions = {
            "rustc": run_logged("rustc-version", ["rustc", "--version", "--verbose"], out, evidence["steps"]),
            "cargo": run_logged("cargo-version", [cargo, "--version"], out, evidence["steps"]),
            "cc": run_logged("cc-version", [os.environ["CC"], "--version"], out, evidence["steps"]),
        }
        expected_rust = tomllib.loads((ROOT / "rust-toolchain.toml").read_text())["toolchain"]["channel"]
        if not versions["rustc"].startswith(f"rustc {expected_rust} "):
            raise RuntimeError("Rust version does not match rust-toolchain.toml")
        evidence["toolchains"] = versions
        evidence["cc_path"] = os.environ["CC"]
        pins = tomllib.loads((ROOT / "upstream.lock.toml").read_text())
        # CodexAstraUlt: stderr cannot contaminate Cargo's machine-readable JSON.
        meta_path = out / "cargo-metadata.json"
        meta_command = [cargo, "metadata", "--locked", "--format-version", "1"]
        meta_result = {"step": "metadata", "command": meta_command, "log": "metadata-stderr.log"}
        evidence["steps"].append(meta_result)
        with meta_path.open("w") as meta_file, (out / "metadata-stderr.log").open("w") as err:
            process = subprocess.Popen(meta_command, cwd=ROOT, stdout=meta_file,
                                       stderr=err, start_new_session=True)
            try:
                code = process.wait(timeout=600)
            except (subprocess.TimeoutExpired, KeyboardInterrupt):
                terminate_group(process)
                meta_result["status"] = "inconclusive"
                raise RuntimeError("Cargo metadata timed out or was interrupted") from None
        meta_result["exit_code"] = code
        if code:
            raise RuntimeError(f"Cargo metadata failed ({code}); see metadata-stderr.log")
        metadata = json.loads(meta_path.read_text())
        evidence["upstreams"] = validate_graph(metadata, pins)
        evidence["inputs_sha256"] = snapshot()
        evidence["base_commit"] = subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
        proof = run_logged("runner-tests", [sys.executable, "-m", "unittest", "discover",
                                           "-s", "tools/tests", "-v"], out, evidence["steps"])
        if not re.search(r"Ran [1-9]\d* tests?", proof):
            raise RuntimeError("Runner tests did not execute")
        run_logged("format", [cargo, "fmt", "--all", "--", "--check"], out, evidence["steps"])
        run_logged("clippy", [cargo, "clippy", "--locked", "--workspace", "--all-targets",
                             "-j", str(args.jobs), "--", "-D", "warnings"], out, evidence["steps"])
        for package in ("recomp3ds", "recomp-abi", "zakuro-cpu", "droidds-foundation"):
            run_logged("test-" + package,
                       [cargo, "test", "--locked", "-p", package, "-j", str(args.jobs),
                        "--", "--nocapture"],
                       out, evidence["steps"], require_tests=True)
        run_logged("build-release", [cargo, "build", "--locked", "--release", "-p",
                                     "droidds-foundation", "-j", str(args.jobs)],
                   out, evidence["steps"])
        executable = Path(metadata["target_directory"]) / "release" / "droidds-foundation"
        run_logged("synthetic-proof", [str(executable), str(out / "synthetic")],
                   out, evidence["steps"], timeout=180)
        report = out / "synthetic" / "report.json"
        if not report.is_file():
            raise RuntimeError("Foundation executable did not create this run's report.json")
        evidence["synthetic_report"] = json.loads(report.read_text())
        validate_report(evidence["synthetic_report"], pins)
        if snapshot() != evidence["inputs_sha256"]:
            raise RuntimeError("Build inputs changed during validation; rerun after edits settle")
        evidence["executable_sha256"] = hashlib.sha256(executable.read_bytes()).hexdigest()
        evidence["status"] = "passed"
        print(f"Foundation build and required checks passed: {out}")
        return 0
    except (RuntimeError, ValueError, KeyError, OSError, subprocess.SubprocessError,
            KeyboardInterrupt) as exc:
        evidence["error"] = str(exc)
        print(f"Foundation build failed: {exc}", file=sys.stderr)
        return 1
    finally:
        evidence["finished_utc"] = datetime.now(timezone.utc).isoformat()
        (out / "build-report.json").write_text(json.dumps(evidence, indent=2) + "\n")


if __name__ == "__main__":
    raise SystemExit(main())
