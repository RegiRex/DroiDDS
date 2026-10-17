"""CodexAstraUlt: ELF evidence gates reject incompatible Android libraries."""

import sys
from pathlib import Path
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from build_android_probe import audit_elf


# CodexAstraUlt: Keep a minimal readelf-format observation and independently
# mutate the properties that would make an APK fail Android's loader contract.
ELF = """
  Class:                             ELF64
  Type:                              DYN (Shared object file)
  Machine:                           AArch64
  LOAD 0x000000 0x0000000000000000 0x0000000000000000 0x003000 0x003000 R E 0x4000
  LOAD 0x004000 0x0000000000004000 0x0000000000004000 0x001000 0x002000 RW  0x4000
  0x0000000000000001 (NEEDED) Shared library: [libc.so]
"""


class ElfAuditTests(unittest.TestCase):
    # CodexAstraUlt: Valid observations can have no libc dependency; each
    # library's dependency closure is checked against the full packaged set.
    def test_android_library(self):
        self.assertEqual(audit_elf(ELF, set())["load_alignments"], [16384, 16384])

    def test_packaged_dependency(self):
        text = ELF.replace("[libc.so]", "[libdroidds_android_probe.so]")
        audit_elf(text, {"libdroidds_android_probe.so"})
        with self.assertRaises(ValueError):
            audit_elf(text, set())

    def test_host_elf_rejected(self):
        with self.assertRaises(ValueError):
            audit_elf(ELF.replace("AArch64", "Advanced Micro Devices X86-64"), set())

    def test_host_libc_rejected(self):
        with self.assertRaises(ValueError):
            audit_elf(ELF.replace("[libc.so]", "[libc.so.6]"), set())

    def test_small_page_alignment_rejected(self):
        with self.assertRaises(ValueError):
            audit_elf(ELF.replace("0x4000", "0x1000"), set())

    def test_misaligned_segment_rejected(self):
        with self.assertRaises(ValueError):
            audit_elf(ELF.replace("LOAD 0x004000", "LOAD 0x005000"), set())

    def test_writable_executable_rejected(self):
        with self.assertRaises(ValueError):
            audit_elf(ELF.replace("R E", "RWE"), set())

    def test_text_relocations_rejected(self):
        with self.assertRaises(ValueError):
            audit_elf(ELF + " 0x16 (TEXTREL) 0x0\n", set())


if __name__ == "__main__":
    unittest.main()
