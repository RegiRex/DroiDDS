#!/usr/bin/env python3
"""CodexAstraUlt: Compile original shaders and execute the shared probe on host Vulkan."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import signal
import struct
import subprocess
import sys

from build_foundation import ROOT, interrupted, run_logged
from run_android_probe import validate_graphics_report

NDK_VERSION = "27.3.13750724"


def generate_shaders(ndk: Path, output: Path, run) -> dict:
    """CodexAstraUlt: Use the pinned NDK's compiler and validator, never runtime GLSL."""
    properties = (ndk / "source.properties").read_text()
    if not any(line.strip() == f"Pkg.Revision = {NDK_VERSION}" for line in properties.splitlines()):
        raise ValueError("Shader tools require pinned NDK " + NDK_VERSION)
    output.mkdir(parents=True, exist_ok=False)
    tools = ndk / "shader-tools/linux-x86_64"
    header = ["/* CodexAstraUlt: Generated from original DroidDS GLSL; do not edit. */\n",
              "#ifndef DROIDDS_PROBE_SHADERS_H\n#define DROIDDS_PROBE_SHADERS_H\n#include <stdint.h>\n"]
    evidence = {}
    for stage in ("vert", "frag"):
        source = ROOT / "android/probe/shaders" / ("probe." + stage)
        binary = output / ("probe." + stage + ".spv")
        run("shader-" + stage, [tools / "glslc", "--target-env=vulkan1.0", "-O",
                                source, "-o", binary])
        run("validate-shader-" + stage, [tools / "spirv-val", "--target-env", "vulkan1.0", binary])
        data = binary.read_bytes()
        if len(data) < 20 or len(data) > 1024 * 1024 or len(data) % 4:
            raise ValueError("Invalid compiled SPIR-V size")
        words = struct.unpack("<" + "I" * (len(data) // 4), data)
        if words[0] != 0x07230203:
            raise ValueError("Compiled shader has no SPIR-V magic")
        header.append(f"static const uint32_t droidds_probe_{stage}_spv[] = {{\n")
        for offset in range(0, len(words), 8):
            header.append("    " + ", ".join(f"0x{word:08x}U" for word in words[offset:offset + 8]) + ",\n")
        header.append("};\n")
        evidence[stage] = {"source_sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
                           "spirv_sha256": hashlib.sha256(data).hexdigest(), "bytes": len(data)}
    header.append("#endif\n")
    (output / "droidds_probe_shaders.h").write_text("".join(header))
    return evidence


def main() -> int:
    """CodexAstraUlt: Host Vulkan execution is explicit and never counted as Thor evidence."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ndk", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--vulkan-library", type=Path,
                        default=Path("/usr/lib/x86_64-linux-gnu/libvulkan.so.1"))
    parser.add_argument("--require-validation", action="store_true",
                        help="require the Khronos validation layer in this host-only build")
    args = parser.parse_args()
    if sys.platform != "linux":
        parser.error("This host validation runner supports Linux only")
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=False)
    signal.signal(signal.SIGTERM, interrupted)
    evidence = {"schema": 1, "kind": "droidds-host-vulkan-build", "status": "failed",
                "android_execution": "not_run", "steps": []}

    def run(name, argv, machine=False):
        return run_logged(name, [str(arg) for arg in argv], output, evidence["steps"],
                          timeout=120, separate_stderr=machine)

    try:
        ndk = args.ndk.resolve()
        evidence["shaders"] = generate_shaders(ndk, output / "shaders", run)
        # CodexAstraUlt: Expose only Khronos headers to the host compiler. Adding
        # the complete Android sysroot would silently replace host libc headers.
        includes = output / "headers"
        includes.mkdir()
        ndk_headers = ndk / "toolchains/llvm/prebuilt/linux-x86_64/sysroot/usr/include"
        for name in ("vulkan", "vk_video"):
            (includes / name).symlink_to(ndk_headers / name, target_is_directory=True)
        native = ROOT / "android/probe/jni"
        source_files = [native / "vulkan_probe.c", native / "vulkan_probe.h",
                        ROOT / "tools/vulkan_probe_host.c"]
        evidence["source_sha256"] = {str(path.relative_to(ROOT)): hashlib.sha256(path.read_bytes()).hexdigest()
                                     for path in source_files}
        executable = output / "vulkan-probe"
        compiler = os.environ.get("CC", "cc")
        evidence["compiler"] = run("compiler-version", [compiler, "--version"])
        run("compile", [compiler, "-std=c11", "-O2", "-Wall", "-Wextra", "-Werror",
                        *(["-DDROIDDS_VK_VALIDATION=1"] if args.require_validation else []),
                        "-I", includes, "-I", native, "-I", output / "shaders",
                        native / "vulkan_probe.c", ROOT / "tools/vulkan_probe_host.c",
                        args.vulkan_library.resolve(), "-o", executable])
        report = json.loads(run("execute", [executable], machine=True))
        validate_graphics_report(report)
        # CodexAstraUlt: A missing validation layer or reported API violation
        # cannot pass the explicit validation run merely because pixels matched.
        if args.require_validation and report.get("validation_layer_enabled") is not True:
            raise ValueError("Required Vulkan validation layer was not enabled")
        diagnostics = (output / "execute-stderr.log").read_text(errors="replace")
        if "Validation Error" in diagnostics or "VUID-" in diagnostics:
            raise ValueError("Vulkan validation reported an API violation; see execute-stderr.log")
        if any(hashlib.sha256((ROOT / path).read_bytes()).hexdigest() != value
               for path, value in evidence["source_sha256"].items()):
            raise ValueError("Vulkan sources changed during validation")
        evidence.update(status="passed", graphics_report=report)
        print("Host Vulkan draw/readback passed; Android Vulkan execution remains untested")
        return 0
    except (OSError, ValueError, RuntimeError, KeyError, subprocess.SubprocessError) as error:
        evidence["error"] = str(error)
        print("Host Vulkan validation failed: " + str(error), file=sys.stderr)
        return 1
    finally:
        (output / "build-report.json").write_text(json.dumps(evidence, indent=2) + "\n")


if __name__ == "__main__":
    raise SystemExit(main())
