#!/usr/bin/env python3
"""CodexAstraUlt: Validate the imported runtime SPIR-V and rebuild its public GLSL."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import struct

from build_foundation import ROOT
from build_vulkan_probe import NDK_VERSION


# CodexAstraUlt: These are upstream implementation shaders, not title-derived
# inputs. Enumerate every included variant so a new binary needs explicit review.
VARIANTS = {name: (name, ()) for name in (
    "depth.comp", "overlay.frag", "overlay.vert", "present.frag", "present.vert",
    "raster.frag", "raster.vert", "shade.vert", "transfer.comp", "upright.comp")}
VARIANTS.update({
    "present_stereo.frag": ("present.frag", ("STEREO",)),
    "raster_depth.frag": ("raster.frag", ("WRITES_DEPTH",)),
    "upright_image.comp": ("upright.comp", ("TO_IMAGE",)),
})


def validate_runtime_shaders(ndk: Path, output: Path, run) -> dict:
    """CodexAstraUlt: Keep tracked binaries immutable; record rebuild differences honestly."""
    properties = (ndk / "source.properties").read_text()
    if not any(line.strip() == f"Pkg.Revision = {NDK_VERSION}" for line in properties.splitlines()):
        raise ValueError("Runtime shaders require pinned NDK " + NDK_VERSION)
    output.mkdir(parents=True, exist_ok=False)
    base = ROOT / "vendor/zakuro"
    shaders = base / "crates/zakuro-gpu/shaders"
    provenance = json.loads((base / "UPSTREAM.json").read_text())["files"]
    if {p.name for p in shaders.glob("*.spv")} != {name + ".spv" for name in VARIANTS}:
        raise ValueError("Runtime shader binary inventory changed")
    tools = ndk / "shader-tools/linux-x86_64"
    evidence = {}
    for name, (source_name, definitions) in sorted(VARIANTS.items()):
        source, binary = shaders / source_name, shaders / (name + ".spv")
        for path in (source, binary):
            expected = provenance.get(str(path.relative_to(base)))
            if path.is_symlink() or hashlib.sha256(path.read_bytes()).hexdigest() != expected:
                raise ValueError("Imported runtime shader differs from its reviewed source: " + path.name)
        data = binary.read_bytes()
        if not 20 <= len(data) <= 1024 * 1024 or len(data) % 4 or struct.unpack_from("<I", data)[0] != 0x07230203:
            raise ValueError("Malformed imported runtime SPIR-V: " + name)
        # CodexAstraUlt: Validate the exact shipped bytes, then independently
        # compile the corresponding source/define combination with pinned tools.
        # Compiler-version differences need not reproduce byte-identical output.
        run("runtime-shader-validate-" + name,
            [tools / "spirv-val", "--target-env", "vulkan1.3", binary])
        rebuilt = output / (name + ".spv")
        run("runtime-shader-rebuild-" + name,
            [tools / "glslc", "--target-env=vulkan1.0", "--target-spv=spv1.0",
             *("-D" + definition for definition in definitions), source, "-o", rebuilt])
        run("runtime-shader-revalidate-" + name,
            [tools / "spirv-val", "--target-env", "vulkan1.3", rebuilt])
        rebuilt_data = rebuilt.read_bytes()
        evidence[name] = {
            "source": str(source.relative_to(ROOT)), "defines": list(definitions),
            "source_sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
            "shipped_sha256": hashlib.sha256(data).hexdigest(), "shipped_bytes": len(data),
            "rebuilt_sha256": hashlib.sha256(rebuilt_data).hexdigest(),
            "byte_identical_rebuild": data == rebuilt_data,
            "validation_environment": "vulkan1.3", "compiler_target": "vulkan1.0/spv1.0",
        }
    return evidence
