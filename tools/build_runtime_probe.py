#!/usr/bin/env python3
"""CodexAstraUlt: Execute the integrated runtime's host gate with real Vulkan tests."""

from __future__ import annotations

import argparse
from contextlib import contextmanager
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import signal
import subprocess
import sys
import tomllib

from build_foundation import ROOT, interrupted, run_logged, snapshot, validate_graph


# CodexAstraUlt: These existing GPU comparisons and real loader regressions must
# execute; a feature-disabled or filtered suite cannot satisfy this build gate.
GPU_REQUIRED_TESTS = {
    "raster::tests::the_gpu_covers_the_same_pixels",
    "raster::tests::the_gpu_blends_and_masks_like_the_cpu",
    "raster::tests::the_gpu_shades_like_the_cpu",
    "raster::tests::the_generic_fragment_shader_draws_like_the_specialized_ones",
    "raster::tests::translated_shaders_draw_like_the_interpreter",
    "raster::hardware::tests::compiler_admission_covers_delayed_and_failed_completions",
    "raster::hardware::tests::failed_or_over_budget_translation_settles_to_interpreter",
    "raster::hardware::tests::pipeline_budget_preserves_existing_handles",
    "raster::tests::deferred_translation_retries_without_losing_draws",
    "raster::tests::pipeline_budget_failure_keeps_software_draw_and_reports_fallback",
}
GPU_IGNORED_BENCHMARKS = {"shader::tests::batch_speed", "shader::tests::compiled_speed"}
LOADER_REQUIRED_TESTS = {
    "droidds_real_loader_reports_geometry_and_executes_every_supported_mode",
    "droidds_real_kernel_resource_limit_heap_linear_and_hid_base_allocation",
    "droidds_unsupported_modes_fail_and_next_valid_load_recovers",
    "droidds_allocation_restore_and_failed_requests_preserve_accounting",
    "droidds_heap_windows_reject_overlap_overflow_and_old_linear_excess",
    "droidds_incompatible_same_size_state_does_not_mutate_live_machine",
}
VALIDATION_LAYER = "VK_LAYER_KHRONOS_validation"
SYNC_VALIDATION = "VK_VALIDATION_FEATURE_ENABLE_SYNCHRONIZATION_VALIDATION_EXT"


@contextmanager
def command_environment(overrides: dict[str, str | None]):
    """CodexAstraUlt: Scope child settings and restore the caller even on failure."""
    previous = {name: os.environ.get(name) for name in overrides}
    try:
        for name, value in overrides.items():
            if value is None:
                os.environ.pop(name, None)
            else:
                os.environ[name] = value
        yield
    finally:
        for name, value in previous.items():
            if value is None:
                os.environ.pop(name, None)
            else:
                os.environ[name] = value


def validation_environment() -> dict[str, str]:
    """CodexAstraUlt: Require validation and synchronization checks in host runs."""
    for name in ("VK_LAYER_DISABLES", "VK_LOADER_LAYERS_DISABLE"):
        if os.environ.get(name):
            raise ValueError(f"Required Vulkan validation conflicts with {name}")
    layers = [part for part in os.environ.get("VK_INSTANCE_LAYERS", "").split(":") if part]
    if VALIDATION_LAYER not in layers:
        layers.append(VALIDATION_LAYER)
    enables = [part for part in os.environ.get("VK_LAYER_ENABLES", "").split(",") if part]
    if any("DISABLE" in item for item in enables):
        raise ValueError("Required Vulkan validation conflicts with VK_LAYER_ENABLES")
    if SYNC_VALIDATION not in enables:
        enables.append(SYNC_VALIDATION)
    return {"VK_INSTANCE_LAYERS": ":".join(layers), "VK_LAYER_ENABLES": ",".join(enables),
            "VK_LOADER_DEBUG": "layer", "DROIDDS_REQUIRE_VULKAN_TESTS": "1"}


def validate_diagnostics(diagnostics: str, require_layer: bool = True) -> dict:
    """CodexAstraUlt: A passing pixel oracle cannot hide API violations or absent layers."""
    if re.search(r"VUID-|SYNC-HAZARD|Validation Error|\bERROR(?:\s*[:|]|\s+\[)", diagnostics, re.I):
        raise ValueError("Vulkan reported a validation/driver error; inspect this step's logs")
    instance = re.search(r'Insert instance layer\s+"VK_LAYER_KHRONOS_validation"', diagnostics)
    device = re.search(r'Inserted device layer\s+"VK_LAYER_KHRONOS_validation"', diagnostics)
    if require_layer and (instance is None or device is None):
        raise ValueError("Required Khronos instance/device layer activation was not observed")
    return {"instance_layer_observed": instance is not None,
            "device_layer_observed": device is not None,
            "synchronization_validation_requested": True, "api_errors_observed": False}


def validate_suite(output: str, required: set[str] | None = None,
                   allowed_ignored: set[str] | None = None) -> dict:
    """CodexAstraUlt: Reject zero, filtered, unexpectedly ignored or missing required tests."""
    rows = re.findall(r"test result: ok\. (\d+) passed; (\d+) failed; (\d+) ignored; "
                      r"(\d+) measured; (\d+) filtered out", output)
    counts = {key: sum(int(row[i]) for row in rows) for i, key in enumerate(
        ("passed", "failed", "ignored", "measured", "filtered"))}
    if counts["passed"] == 0 or any(counts[key] for key in ("failed", "measured", "filtered")):
        raise ValueError("Required suite did not execute completely and pass")
    passed = set(re.findall(r"^test ([\w:]+) \.\.\. ok$", output, re.M))
    ignored = set(re.findall(r"^test ([\w:]+) \.\.\. ignored(?:,.*)?$", output, re.M))
    if not (required or set()).issubset(passed):
        raise ValueError("Required tests are missing: " + ", ".join(sorted((required or set()) - passed)))
    if len(ignored) != counts["ignored"] or not ignored.issubset(allowed_ignored or set()):
        raise ValueError("Required suite contains an unqualified ignored test")
    return {**counts, "ignored_benchmarks": sorted(ignored), "required_tests": sorted(required or set())}


def generated_sources(manifest: object, directory: Path, *, homebrew: bool = False) -> list[Path]:
    """CodexAstraUlt: Compile only the newly generated original fixture's local C sources."""
    if not isinstance(manifest, dict):
        raise ValueError("Runtime generator did not return a source manifest")
    expected = {"schema": 1, "kind": "droidds-runtime-fixture-sources",
                "fixture": "droidds-original-pica-ipc-v1", "library": "libdroidds_fixture_runtime.so",
                "abi": 4, "generation": 3}
    # CodexAstraUlt: The interactive guest has its own identity and container;
    # retaining the .5 gate prevents a new demo from replacing earlier proof.
    if homebrew:
        expected.update(kind="droidds-homebrew-fixture-sources", fixture="droidds-original-homebrew-v1",
                        library="libdroidds_fixture_homebrew.so")
    for key, value in expected.items():
        if type(manifest.get(key)) is not type(value) or manifest[key] != value:
            raise ValueError(f"Runtime generator identity mismatch: {key}")
    sources = manifest.get("sources")
    if (not isinstance(sources, list) or not sources or len(sources) > 64
            or any(not isinstance(name, str) for name in sources)
            or len(set(sources)) != len(sources)):
        raise ValueError("Runtime generator returned an invalid C source list")
    paths = []
    for name in sources:
        path = directory / name
        if (Path(name).name != name or not name.endswith(".c") or not path.is_file()
                or path.is_symlink() or path.resolve().parent != directory.resolve()):
            raise ValueError("Runtime generator returned a nonlocal or missing C source")
        paths.append(path)
    container = directory / ("homebrew-fixture.cxi" if homebrew else "runtime-fixture.cxi")
    if not container.is_file() or container.is_symlink():
        raise ValueError("Runtime generator did not emit its original NCCH fixture")
    return paths


def validate_static_runtime(report: dict, *, homebrew: bool = False) -> None:
    """CodexAstraUlt: The host's forced static-state run must prove that path was selected."""
    cases = report.get("cases", [])
    # CodexAstraUlt: Interactive cases retain their whole persistent-session
    # report; select its actual diagnostics without weakening the .5 shape.
    hardware = [(case.get("session", {}).get("hardware") if homebrew else case.get("hardware"))
                for case in cases if isinstance(case, dict) and case.get("name") == "native_vulkan"]
    if (len(hardware) != 1 or not isinstance(hardware[0], dict)
            or any(hardware[0].get(key) is not False for key in ("dynamic_blend", "dynamic_logic_op"))):
        raise ValueError("Required static blend/logic-operation runtime path was not exercised")


def main() -> int:
    """CodexAstraUlt: Preserve fresh host-only evidence and fail rather than skip a gate."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--jobs", type=int, default=2)
    args = parser.parse_args()
    if sys.platform != "linux":
        parser.error("This executed runtime gate currently supports Linux hosts only")
    if not 1 <= args.jobs <= 8:
        parser.error("--jobs must be between 1 and 8")
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=False)
    signal.signal(signal.SIGTERM, interrupted)
    evidence = {"schema": 1, "kind": "droidds-host-runtime-build", "status": "failed",
                "android_execution": "not_run", "retail_execution": "not_run",
                "started_utc": datetime.now(timezone.utc).isoformat(), "steps": []}

    def run(name, argv, *, timeout=900, machine=False, tests=False):
        return run_logged(name, [str(arg) for arg in argv], output, evidence["steps"],
                          timeout=timeout, separate_stderr=machine, require_tests=tests)

    try:
        # CodexAstraUlt: Share the same strict runtime-result contract as the
        # Android runner, without duplicating or weakening its route counters.
        from run_android_probe import validate_runtime_report, validate_interactive_report

        cargo = shutil.which("cargo")
        compiler = shutil.which(os.environ.get("CC", "cc"))
        spirv_validator = shutil.which("spirv-val")
        if not cargo or not compiler or not spirv_validator:
            raise RuntimeError("Install pinned Rust, a C compiler and spirv-val before this required GPU gate")
        evidence["inputs_sha256"] = snapshot()
        evidence["base_commit"] = run("source-commit", ["git", "rev-parse", "HEAD"], machine=True).strip()
        evidence["toolchains"] = {
            "rustc": run("rustc-version", ["rustc", "--version", "--verbose"], machine=True),
            "cargo": run("cargo-version", [cargo, "--version"], machine=True),
            "cc": run("cc-version", [compiler, "--version"]),
            "spirv-val": run("spirv-val-version", [spirv_validator, "--version"]),
        }
        expected_rust = tomllib.loads((ROOT / "rust-toolchain.toml").read_text())["toolchain"]["channel"]
        if not evidence["toolchains"]["rustc"].startswith(f"rustc {expected_rust} "):
            raise ValueError("Runtime gate compiler differs from rust-toolchain.toml")
        metadata = json.loads(run("metadata", [cargo, "metadata", "--locked", "--format-version", "1"], machine=True))
        evidence["sources"] = validate_graph(metadata, tomllib.loads((ROOT / "upstream.lock.toml").read_text()))
        run("format-runtime", [cargo, "fmt", "-p", "droidds-runtime-probe", "--", "--check"])
        run("clippy-runtime", [cargo, "clippy", "--locked", "-p", "droidds-runtime-probe",
                              "--features", "producer", "--all-targets", "--no-deps", "-j", args.jobs,
                              "--", "-D", "warnings"])
        # CodexAstraUlt: The private-title worker must pass public original-fixture
        # gates before local users trust its bounded first-blocker reports.
        run("format-title-tools", [cargo, "fmt", "-p", "droidds-title-tools", "--", "--check"])
        run("clippy-title-tools", [cargo, "clippy", "--locked", "-p", "droidds-title-tools",
                                  "--all-targets", "--no-deps", "-j", args.jobs,
                                  "--", "-D", "warnings"])
        evidence["suites"] = {}
        for package in ("zakuro-fs", "zakuro-core", "droidds-runtime-probe"):
            command = [cargo, "test", "--locked", "-p", package, "--lib", "-j", args.jobs]
            if package == "droidds-runtime-probe":
                command += ["--features", "producer"]
            command += ["--", "--test-threads=1"]
            proof = run("test-" + package, command, timeout=1800, machine=True, tests=True)
            evidence["suites"][package] = validate_suite(proof)
        title_proof = run("test-title-tools", [cargo, "test", "--locked", "-p", "droidds-title-tools",
                          "-j", args.jobs, "--", "--test-threads=1"], machine=True, tests=True)
        evidence["suites"]["droidds-title-tools"] = validate_suite(title_proof)
        run("build-title-tools", [cargo, "build", "--locked", "--release", "-p", "droidds-title-tools",
                                 "-j", args.jobs], timeout=1800)
        title_worker = Path(metadata["target_directory"]) / "release/droidds-private-title"
        proof = run("test-loader-memory", [cargo, "test", "--locked", "-p", "zakuro-core",
                    "--test", "droidds_memory_layout", "-j", args.jobs, "--", "--test-threads=1"],
                    timeout=1800, machine=True, tests=True)
        evidence["suites"]["loader-memory"] = validate_suite(proof, LOADER_REQUIRED_TESTS)
        environment = validation_environment()
        evidence["validation_environment"] = environment
        # CodexAstraUlt: Preserve only Vulkan selection settings; never dump the
        # process environment, credentials or unrelated filesystem configuration.
        evidence["vulkan_selection"] = {key: os.environ[key] for key in (
            "VK_DRIVER_FILES", "VK_ICD_FILENAMES", "VK_LAYER_PATH") if key in os.environ}
        with command_environment(environment):
            for mode, static in (("normal", None), ("static", "1")):
                name = "test-gpu-" + mode
                with command_environment({"ZAKURO_STATIC_BLEND": static}):
                    proof = run(name, [cargo, "test", "--locked", "-p", "zakuro-gpu",
                                "--no-default-features", "--features", "vulkan", "--lib", "-j", args.jobs,
                                "--", "--test-threads=1"], timeout=2400, machine=True, tests=True)
                diagnostics = (output / (name + "-stderr.log")).read_text(errors="replace")
                validation = validate_diagnostics(proof + "\n" + diagnostics)
                evidence["suites"][name] = validate_suite(proof, GPU_REQUIRED_TESTS, GPU_IGNORED_BENCHMARKS)
                evidence["suites"][name]["validation"] = validation
            run("build-runtime", [cargo, "build", "--locked", "--release", "-p", "droidds-runtime-probe",
                                  "--features", "producer", "--bin", "droidds-runtime-probe", "-j", args.jobs], timeout=1800)
            executable = Path(metadata["target_directory"]) / "release/droidds-runtime-probe"
            generated = output / "generated"
            manifest = json.loads(run("emit-runtime", [executable, "emit", "--output", generated], machine=True))
            sources = generated_sources(manifest, generated)
            # CodexAstraUlt: The integration test creates disposable private-style
            # output outside Git and exercises the real worker, never retail data.
            run("private-title-integration", [sys.executable, ROOT / "tools/tests/test_private_title.py",
                "--worker", title_worker, "--fixture", generated / "runtime-fixture.cxi"],
                timeout=180, tests=True)
            libraries = output / "libraries"
            libraries.mkdir()
            library = libraries / manifest["library"]
            # CodexAstraUlt: Retain upstream floating-point semantics and use a
            # host compiler only for this Linux proof, never for an Android APK.
            run("compile-runtime", [compiler, "-O2", "-ffp-contract=off", "-fno-math-errno",
                    "-fPIC", "-fvisibility=hidden", "-shared", "-Wl,-z,relro", "-Wl,-z,now",
                    "-Wl,--no-undefined", "-Wl,-soname," + library.name, "-I", generated,
                    *sources, "-o", library, "-lm"])
            with command_environment({"ZAKURO_STATIC_BLEND": "1"}):
                raw_report = run("execute-runtime", [executable, "run", "--native-dir", libraries,
                                 "--scratch-dir", output / "runtime-scratch"], timeout=180, machine=True)
            # CodexAstraUlt: Validation can write directly to stdout, bypassing
            # the fixture's JSON writer. Diagnose that failure before decoding.
            evidence["runtime_validation"] = validate_diagnostics(raw_report + "\n" +
                (output / "execute-runtime-stderr.log").read_text(errors="replace"))
            report = json.loads(raw_report)
            (output / "runtime-report.json").write_text(json.dumps(report, indent=2) + "\n")
            validate_runtime_report(report)
            validate_static_runtime(report)
            evidence["runtime_report"] = report
            evidence["generated_manifest"] = manifest
            evidence["artifacts_sha256"] = {
                "runtime_executable": hashlib.sha256(executable.read_bytes()).hexdigest(),
                "native_fixture": hashlib.sha256(library.read_bytes()).hexdigest(),
                "original_ncch_fixture": hashlib.sha256((generated / "runtime-fixture.cxi").read_bytes()).hexdigest(),
            }
            # CodexAstraUlt: Execute the actual interactive guest through all
            # required CPU/rendering paths, real HID/DSP and scanout. The static
            # Vulkan path matches the Thor's capability report, with validation.
            homebrew = output / "homebrew-generated"
            homebrew_manifest = json.loads(run("emit-homebrew", [executable, "emit-homebrew",
                                         "--output", homebrew], machine=True))
            homebrew_sources = generated_sources(homebrew_manifest, homebrew, homebrew=True)
            homebrew_library = libraries / homebrew_manifest["library"]
            run("compile-homebrew", [compiler, "-O2", "-ffp-contract=off", "-fno-math-errno",
                    "-fPIC", "-fvisibility=hidden", "-shared", "-Wl,-z,relro", "-Wl,-z,now",
                    "-Wl,--no-undefined", "-Wl,-soname," + homebrew_library.name, "-I", homebrew,
                    *homebrew_sources, "-o", homebrew_library, "-lm"])
            with command_environment({"ZAKURO_STATIC_BLEND": "1"}):
                homebrew_raw = run("execute-homebrew", [executable, "run-homebrew", "--native-dir", libraries,
                                   "--scratch-dir", output / "homebrew-scratch"], timeout=300, machine=True)
            evidence["homebrew_validation"] = validate_diagnostics(homebrew_raw + "\n" +
                (output / "execute-homebrew-stderr.log").read_text(errors="replace"))
            homebrew_report = json.loads(homebrew_raw)
            (output / "homebrew-report.json").write_text(json.dumps(homebrew_report, indent=2) + "\n")
            validate_interactive_report(homebrew_report)
            validate_static_runtime(homebrew_report, homebrew=True)
            evidence["homebrew_report"] = homebrew_report
            evidence["homebrew_manifest"] = homebrew_manifest
            evidence["artifacts_sha256"].update(
                homebrew_library=hashlib.sha256(homebrew_library.read_bytes()).hexdigest(),
                homebrew_original_ncch=hashlib.sha256((homebrew / "homebrew-fixture.cxi").read_bytes()).hexdigest())
            # CodexAstraUlt: A real exported session must reject reentrant,
            # wrong-thread/stale-token and invalid-buffer calls, and remain
            # resumable after a paused-frame rejection. Process timeout catches
            # a regression to blocking on the session owner's own mutex.
            run("build-host-ffi", [cargo, "build", "--locked", "--release", "-p",
                                  "droidds-android-probe", "-j", args.jobs], timeout=1800)
            host_ffi = Path(metadata["target_directory"]) / "release/libdroidds_android_probe.so"
            with command_environment({"ZAKURO_STATIC_BLEND": "1"}):
                ffi_raw = run("execute-homebrew-ffi", [sys.executable, ROOT / "tools/check_homebrew_ffi.py",
                    "--library", host_ffi, "--native-dir", libraries,
                    "--scratch-dir", output / "ffi-scratch"], timeout=120, machine=True)
            evidence["ffi_validation"] = validate_diagnostics(ffi_raw + "\n" +
                (output / "execute-homebrew-ffi-stderr.log").read_text(errors="replace"))
            ffi_report = json.loads(ffi_raw)
            required_ffi = ["actual_native_frame_and_metrics", "live_session_reentrant_probes_rejected",
                "wrong_worker_preserves_live_session", "pause_rejection_preserves_resumability",
                "stale_token_preserves_replacement", "invalid_capacity_preserves_output_and_fails_closed",
                "normal_and_failed_teardown_release_ownership"]
            if (ffi_report.get("status") != "passed" or ffi_report.get("schema") != 1
                    or ffi_report.get("kind") != "droidds-homebrew-ffi-proof"
                    or ffi_report.get("controls") != required_ffi):
                raise ValueError("Required exported homebrew session controls did not pass")
            evidence["ffi_report"] = ffi_report
            evidence["artifacts_sha256"]["host_ffi"] = hashlib.sha256(host_ffi.read_bytes()).hexdigest()
        if snapshot() != evidence["inputs_sha256"]:
            raise RuntimeError("Runtime build inputs changed during validation; rerun after edits settle")
        evidence["status"] = "passed"
        print(f"Integrated runtime host gate passed: {output}; Android/game execution is not established")
        return 0
    except (RuntimeError, ValueError, KeyError, OSError, subprocess.SubprocessError, KeyboardInterrupt) as error:
        evidence["error"] = str(error)
        print("Runtime host gate failed: " + str(error), file=sys.stderr)
        return 1
    finally:
        evidence["finished_utc"] = datetime.now(timezone.utc).isoformat()
        (output / "build-report.json").write_text(json.dumps(evidence, indent=2) + "\n")


if __name__ == "__main__":
    raise SystemExit(main())
