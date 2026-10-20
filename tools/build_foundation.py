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

from run_android_probe import cases_for_version, validate_code_safety

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
    # CodexAstraUlt: Host and Android execute the same eight fixtures. Require
    # the full current contract, including deliberate tiny-budget fallback.
    expected = cases_for_version("0.0.4")
    cases = report.get("cases", [])
    names = [case["name"] for case in cases]
    if len(names) != len(set(names)) or set(names) != set(expected):
        raise ValueError("Synthetic report is missing required CPU cases")
    for case in cases:
        if case.get("status") != "passed":
            raise ValueError(f"CPU case did not pass: {case['name']}")
        for key, value in expected[case["name"]].items():
            if type(case.get(key)) is not int or case[key] != value:
                raise ValueError(f"Incorrect fixture route counter: {case['name']}/{key}")
    validate_code_safety(report.get("code_safety"))
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
            # CodexAstraUlt: Keep the ABI pinned while admitting only our reviewed
            # compiler copy, required to fix conditional-branch budget accounting.
            compiler = pins.get("vendored_recompiler") if name == "recomp3ds" else None
            if compiler:
                if (compiler.get("repository") != expected["repository"]
                        or compiler.get("revision") != expected["revision"]
                        or compiler.get("directory") != "vendor/3dsrecomp"
                        or compiler.get("packages") != ["recomp3ds"]):
                    raise ValueError("Unsupported vendored compiler provenance")
                directory = ROOT / compiler["directory"]
                provenance = json.loads((directory / "UPSTREAM.json").read_text())
                if (provenance.get("schema") != 1
                        or provenance.get("repository") != compiler["repository"]
                        or provenance.get("revision") != compiler["revision"]
                        or not isinstance(provenance.get("files"), dict)
                        or len(provenance["files"]) < 10):
                    raise ValueError("Vendored compiler original-source inventory changed")
                if (package.get("source") is not None or package.get("version") != "0.1.0"
                        or package.get("license") != "MIT"
                        or Path(package.get("manifest_path", "")).resolve()
                        != (directory / "Cargo.toml").resolve()):
                    raise ValueError("Changed vendored compiler identity")
                source = "vendored:vendor/3dsrecomp/Cargo.toml"
            elif source != prefix + "#" + expected["revision"]:
                raise ValueError(f"Source pin mismatch for {name}: {source}")
            if name == "recomp3ds" and "verify" in nodes[package["id"]]["features"]:
                raise ValueError("The upstream permissive verifier must not be enabled")
            selected[name] = {"source": source, "version": package["version"]}
    # CodexAstraUlt: Permit only the named local runtime integration, retaining
    # its original source identity and explicit no-desktop/no-CPU-shader-JIT policy.
    vendor = pins.get("vendored_runtime")
    allowed = set()
    if vendor:
        if (vendor.get("repository") != pins["runtime"]["repository"]
                or vendor.get("revision") != pins["runtime"]["revision"]
                or vendor.get("directory") != "vendor/zakuro"
                or vendor.get("packages") != ["zakuro-core", "zakuro-fs", "zakuro-gpu"]):
            raise ValueError("Unsupported vendored runtime provenance")
        directory = ROOT / vendor["directory"]
        provenance = json.loads((directory / "UPSTREAM.json").read_text())
        if (provenance.get("schema") != 1 or provenance.get("repository") != vendor["repository"]
                or provenance.get("revision") != vendor["revision"]
                or not isinstance(provenance.get("files"), dict)
                or len(provenance["files"]) < 100):
            raise ValueError("Vendored runtime original-source inventory is missing or changed")
        for name in vendor["packages"]:
            matches = [packages[i] for i in active if packages[i]["name"] == name]
            if len(matches) != 1:
                raise ValueError(f"Expected one active vendored {name}")
            package = matches[0]
            expected = directory / "crates" / name / "Cargo.toml"
            if (package.get("source") is not None or package.get("version") != "0.2.27"
                    or Path(package.get("manifest_path", "")).resolve() != expected.resolve()
                    or package.get("license") != "MIT"):
                raise ValueError(f"Changed vendored runtime identity: {name}")
            features = set(nodes[package["id"]]["features"])
            if name == "zakuro-gpu" and ("vulkan" not in features or features & {"jit", "opengl"}):
                raise ValueError("Runtime GPU must use Vulkan and the qualified PICA interpreter")
            selected[name] = {"source": "vendored:" + str(expected.relative_to(ROOT)),
                              "upstream_revision": vendor["revision"], "version": "0.2.27"}
            allowed.add(name)
    if any(packages[i]["name"] in {"zakuro", "zakuro-gpu", "zakuro-core", "zakuro-fs"} - allowed
           for i in active):
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
               timeout: int = 900, require_tests: bool = False,
               separate_stderr: bool = False) -> str:
    """CodexAstraUlt: Preserve command status and complete bounded command logs."""
    print(f"[{name}] {shlex.join(command)}", flush=True)
    path = out / f"{name}.log"
    # CodexAstraUlt: Rustup may install/sync a pinned component on first use.
    # Its stderr diagnostics must not alter the compiler's stdout version string.
    error_path = out / f"{name}-stderr.log"
    with path.open("w", encoding="utf-8") as log, error_path.open("w", encoding="utf-8") as errors:
        process = subprocess.Popen(command, cwd=ROOT, stdout=log,
                                   stderr=errors if separate_stderr else subprocess.STDOUT,
                                   start_new_session=True)
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
        diagnostic = output + error_path.read_text(encoding="utf-8", errors="replace")
        print(diagnostic[-6000:], file=sys.stderr)
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
    # CodexAstraUlt: The executed Java frontend-math oracle is a build input,
    # even though its classes stay outside the shipped Android source tree.
    paths.extend(sorted((ROOT / "tools/java-tests").rglob("*.java")))
    # CodexAstraUlt: Reviewed notice inventories and supplemental upstream license
    # texts are artifact inputs even though they are not executable Python.
    notice_inventory = ROOT / "tools/android_registry_notices.json"
    if notice_inventory.exists():
        paths.append(notice_inventory)
    paths.extend(sorted(p for p in (ROOT / "tools/notices").rglob("*") if p.is_file()))
    paths.extend(sorted((ROOT / "crates").rglob("*.rs")))
    paths.extend(sorted((ROOT / "crates").rglob("Cargo.toml")))
    # CodexAstraUlt: Imported shader binaries and all patched runtime sources
    # participate in the build snapshot; an upstream pin alone cannot bind edits.
    vendor = ROOT / "vendor"
    if vendor.exists():
        paths.extend(sorted(p for p in vendor.rglob("*")
                            if p.is_file() and "target" not in p.relative_to(vendor).parts))
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
            "rustc": run_logged("rustc-version", ["rustc", "--version", "--verbose"], out, evidence["steps"], separate_stderr=True),
            "cargo": run_logged("cargo-version", [cargo, "--version"], out, evidence["steps"], separate_stderr=True),
            "cc": run_logged("cc-version", [os.environ["CC"], "--version"], out, evidence["steps"]),
        }
        expected_rust = tomllib.loads((ROOT / "rust-toolchain.toml").read_text())["toolchain"]["channel"]
        if not versions["rustc"].startswith(f"rustc {expected_rust} "):
            raise RuntimeError(f"Rust version does not match rust-toolchain.toml; observed {versions['rustc']!r}")
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
        run_logged("format", [cargo, "fmt", "-p", "droidds-foundation", "-p", "droidds-android-probe", "-p", "droidds-runtime-probe", "--", "--check"], out, evidence["steps"])
        run_logged("clippy", [cargo, "clippy", "--locked", "-p", "droidds-foundation", "-p", "droidds-android-probe", "-p", "droidds-runtime-probe", "--all-targets", "--no-deps",
                             "-j", str(args.jobs), "--", "-D", "warnings"], out, evidence["steps"])
        # CodexAstraUlt: Include the Android bridge's host-executable FFI tests;
        # these validate ownership/error paths, never actual Android execution.
        for package in ("recomp3ds", "recomp-abi", "zakuro-cpu", "droidds-foundation",
                        "droidds-android-probe"):
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
