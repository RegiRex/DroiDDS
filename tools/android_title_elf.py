#!/usr/bin/env python3
"""CodexAstraUlt: Audit ARM64/Bionic title libraries without changing host policy."""

import importlib.util
from pathlib import Path


# CodexAstraUlt: Each adapter gets private module objects. Restricting their
# dependency policy to Bionic cannot relax the independent host ELF validator.
def _load(name):
    spec = importlib.util.spec_from_file_location("android_title_" + name, Path(__file__).with_name(name + ".py"))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


RUNTIME = _load("private_runtime_elf")
ELF = RUNTIME.ELF
ELF.DEPENDENCIES = {"libc.so", "libm.so", "libdl.so"}
ALIGNMENT = 16384


class _AndroidTables(RUNTIME._Tables):
    """CodexAstraUlt: Mutable ABI arrays must survive a 16 KiB RELRO loader."""

    def __init__(self, elf, relocations):
        super().__init__(elf, relocations)
        self.relro = [(p["address"] // ALIGNMENT * ALIGNMENT,
                       (p["address"] + p["memory_bytes"] + ALIGNMENT - 1) // ALIGNMENT * ALIGNMENT)
                      for p in elf.programs if p["type"] == 0x6474E552]


RUNTIME._Tables = _AndroidTables


def audit_object(path, machine=183):
    """CodexAstraUlt: The object pipeline accepts only the fixed ARM64 target."""
    ELF._require(type(machine) is int and machine == 183, "Android title requires AArch64")
    return ELF.audit_object(path, machine)


def audit_library(path, preparation_sha256, contract_sha256, units):
    """CodexAstraUlt: Validate exact origins, relocations, exports and alignment."""
    before = RUNTIME._fingerprint(path)
    result = RUNTIME.audit_runtime_library(path, 183, preparation_sha256, contract_sha256, units)
    with ELF._image(Path(path), 183, 3) as elf:
        ELF._require(all(segment["alignment"] >= ALIGNMENT for segment in elf.loads),
                     "Android title load alignment below 16 KiB")
        tags = ELF._dynamic(elf)
        strings = next(section for section in elf.sections if section["type"] == 11)
        strings = elf.sections[strings["link"]]
        soname = ELF._one(tags, 14)
        ELF._require(elf.string(strings["offset"], strings["size"], soname, 255) == "libdroidds_title.so",
                     "Android title SONAME mismatch")
        result.update(target="aarch64-linux-android", minimum_api=29, libc="bionic",
                      load_alignments=[segment["alignment"] for segment in elf.loads],
                      relro_page_bytes=ALIGNMENT, library_loaded=False)
    ELF._require(RUNTIME._fingerprint(path) == before, "Android title changed during alignment audit")
    return result
