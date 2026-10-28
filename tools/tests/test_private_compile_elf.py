#!/usr/bin/env python3
"""CodexAstraUlt: Original compiled ELF fixtures and corrupted copies stay local."""

import hashlib
import importlib.util
from pathlib import Path
import platform
import shutil
import struct
import subprocess
import tempfile
import unittest


SPEC = importlib.util.spec_from_file_location("private_compile_elf", Path(__file__).resolve().parents[1] / "private_compile_elf.py")
AUDIT = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(AUDIT)
PREPARATION = "1" * 64
CONTRACT = "2" * 64


def original_c(marker):
    """CodexAstraUlt: Known ABI-shaped tables contain only a returning fixture."""
    return r'''
#include <stdint.h>
#include <stdio.h>
#define E __attribute__((visibility("default")))
typedef struct { uint32_t address; void (*code)(void *); } Entry;
typedef struct { const char *name; uint32_t *base; uint32_t size, count; const Entry *entries; } Module;
typedef struct { uint32_t start,end; uint64_t hash; } Piece;
typedef struct { uint32_t first,count,start; } Origin;
typedef struct { uint32_t first,end; } Run;
typedef struct { uint32_t count,piece_count; const Piece *pieces; const Origin *functions;
 const Run *runs; const uint32_t *owners; uint8_t *stale; uint32_t *starts; } Origins;
static void guest(void *ctx) { (void)ctx; }
E const uint32_t recomp_abi=4, recomp_generation=3, recomp_entry_count=1, recomp_module_count=0;
E const Entry recomp_entries[]={{0x100000,guest}};
E const Module recomp_modules[]={};
static const Piece pieces[]={{0x100000,0x100004,1}};
static const Origin functions[]={{0,1,0x100000}};
static const Run runs[]={{0,1}};
static const uint32_t owners[]={0};
static uint8_t stale[1]; static uint32_t starts[]={0x100000};
E const Origins recomp_origins[]={{1,1,pieces,functions,runs,owners,stale,starts}};
E const char droidds_preparation_sha256[65]="PREPARATION";
E const char droidds_compile_contract_sha256[65]="CONTRACT";
__attribute__((constructor)) static void unexpected_load(void) {
 FILE *file=fopen("MARKER","w"); if(file) { fputs("loaded",file); fclose(file); }
}
'''.replace("PREPARATION", PREPARATION).replace("CONTRACT", CONTRACT).replace("MARKER", str(marker))


def sections(data):
    """CodexAstraUlt: Mutation helpers locate bytes using the standard ELF layout."""
    offset = struct.unpack_from("<Q", data, 40)[0]
    size, count = struct.unpack_from("<HH", data, 58)
    return [struct.unpack_from("<IIQQQQIIQQ", data, offset + i * size) for i in range(count)]


def symbol(data, wanted):
    """CodexAstraUlt: Find an original export for corruption without loading it."""
    table = sections(data)
    for section in table:
        if section[1] != 11:
            continue
        strings = table[section[6]]
        for at in range(section[4], section[4] + section[5], 24):
            name, _, _, _, value, size = struct.unpack_from("<IBBHQQ", data, at)
            begin = strings[4] + name
            end = data.index(0, begin)
            if data[begin:end].decode() == wanted:
                return at, value, size
    raise AssertionError(wanted)


def programs(data):
    """CodexAstraUlt: Locate program metadata for deterministic negative controls."""
    offset = struct.unpack_from("<Q", data, 32)[0]
    size, count = struct.unpack_from("<HH", data, 54)
    return [(offset + i * size, struct.unpack_from("<IIQQQQQQ", data, offset + i * size)) for i in range(count)]


def file_offset(data, address):
    for _, p in programs(data):
        if p[0] == 1 and p[3] <= address < p[3] + p[5]:
            return p[2] + address - p[3]
    raise AssertionError(hex(address))


def dynamic(data):
    for _, p in programs(data):
        if p[0] == 2:
            result = []
            for at in range(p[2], p[2] + p[5], 16):
                tag, value = struct.unpack_from("<qQ", data, at)
                if tag == 0:
                    return result
                result.append((at, tag, value))
    raise AssertionError("dynamic")


class PrivateCompileElfTests(unittest.TestCase):
    """CodexAstraUlt: Actual host C compilation is required; no silent skips."""

    @classmethod
    def setUpClass(cls):
        cls.temporary = tempfile.TemporaryDirectory(prefix="droidds-elf-original-")
        cls.root = Path(cls.temporary.name)
        cls.machine = {"x86_64": 62, "aarch64": 183}.get(platform.machine())
        if cls.machine is None or shutil.which("cc") is None:
            raise AssertionError("ELF fixture tests require a supported host C compiler")
        cls.marker = cls.root / "must-not-be-loaded"
        cls.source = cls.root / "original.c"
        cls.source.write_text(original_c(cls.marker))
        cls.obj = cls.root / "original.o"
        cls.library = cls.root / "original.so"
        subprocess.run(["cc", "-fPIC", "-fvisibility=hidden", "-c", str(cls.source), "-o", str(cls.obj)],
                       check=True, timeout=20, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        subprocess.run(["cc", "-shared", "-Wl,-z,noexecstack", "-Wl,-z,relro", str(cls.obj), "-o", str(cls.library)],
                       check=True, timeout=20, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        cls.original = cls.library.read_bytes()

    @classmethod
    def tearDownClass(cls):
        cls.temporary.cleanup()

    def audit(self, path=None, **kwargs):
        return AUDIT.audit_library(path or self.library, kwargs.get("machine", self.machine),
                                   kwargs.get("preparation", PREPARATION), kwargs.get("contract", CONTRACT),
                                   kwargs.get("modules", 0))

    def reject(self, mutate, expected=None):
        data = bytearray(self.original)
        mutate(data)
        path = self.root / (self.id().split(".")[-1] + ".so")
        path.write_bytes(data)
        with self.assertRaisesRegex(ValueError, expected or ".+"):
            self.audit(path)

    def test_original_object_and_library_are_audited_without_loading(self):
        before = hashlib.sha256(self.original).hexdigest()
        result = self.audit()
        self.assertEqual((result["abi"], result["generation"], result["entry_count"], result["module_count"]), (4, 3, 1, 0))
        self.assertEqual(result["preparation_sha256"], PREPARATION)
        self.assertEqual(result["compile_contract_sha256"], CONTRACT)
        self.assertGreater(result["relocations_checked"], 0)
        self.assertFalse(result["library_loaded"])
        self.assertFalse(result["runtime_tables_validated"])
        self.assertFalse(self.marker.exists())
        self.assertEqual(hashlib.sha256(self.library.read_bytes()).hexdigest(), before)
        obj = AUDIT.audit_object(self.obj, self.machine)
        self.assertEqual(obj["type"], "REL")
        self.assertFalse(obj["library_loaded"])

    def test_wrong_expectations_are_rejected(self):
        for values in ({"preparation": "a" * 64}, {"contract": "b" * 64}, {"modules": 1},
                       {"machine": 183 if self.machine == 62 else 62}, {"preparation": "A" * 64},
                       {"modules": True}, {"modules": 4097}):
            with self.subTest(values=values), self.assertRaises(ValueError):
                self.audit(**values)

    def test_truncated_or_wrong_format_headers_are_rejected(self):
        for size in (0, 4, 63, len(self.original) - 1):
            with self.subTest(size=size):
                self.reject(lambda data: data.__delitem__(slice(size, None)))
        for offset, value in ((0, 0), (4, 1), (5, 2), (16, 1), (52, 63)):
            with self.subTest(offset=offset):
                self.reject(lambda data: data.__setitem__(offset, value))

    def test_section_and_program_table_bounds_are_checked(self):
        for offset in (32, 40):
            with self.subTest(offset=offset):
                self.reject(lambda data: struct.pack_into("<Q", data, offset, 2**64 - 8))
        self.reject(lambda data: struct.pack_into("<H", data, 60, 0), "section table")

    def test_abi_generation_count_and_array_sizes_are_bound(self):
        for name, value in (("recomp_abi", 5), ("recomp_generation", 2),
                            ("recomp_entry_count", 0), ("recomp_entry_count", 4_000_001),
                            ("recomp_module_count", 1)):
            with self.subTest(name=name, value=value):
                self.reject(lambda data: struct.pack_into("<I", data, file_offset(data, symbol(data, name)[1]), value))
        for name in ("recomp_entries", "recomp_modules", "recomp_origins", "droidds_preparation_sha256"):
            with self.subTest(name=name):
                self.reject(lambda data: struct.pack_into("<Q", data, symbol(data, name)[0] + 16, symbol(data, name)[2] + 1), "export size")

    def test_exports_must_be_defined_objects_with_exact_identity(self):
        at, address, _ = symbol(self.original, "droidds_compile_contract_sha256")
        for offset, value in ((at + 4, 0x12), (at + 5, 2), (at + 6, 0),
                              (file_offset(self.original, address), ord("0")),
                              (file_offset(self.original, address) + 64, ord("x"))):
            with self.subTest(offset=offset):
                self.reject(lambda data: data.__setitem__(offset, value))

    def test_writable_executable_load_and_stack_are_rejected(self):
        code = next(at for at, p in programs(self.original) if p[0] == 1 and p[1] & 1)
        stack = next(at for at, p in programs(self.original) if p[0] == 0x6474E551)
        self.reject(lambda data: struct.pack_into("<I", data, code + 4, 7), "writable executable")
        self.reject(lambda data: struct.pack_into("<I", data, stack + 4, 7), "executable GNU stack")

    def test_rpath_textrel_and_unexpected_dependencies_are_rejected(self):
        init = next(at for at, tag, _ in dynamic(self.original) if tag == 12)
        for tag in (15, 29, 22):
            with self.subTest(tag=tag):
                self.reject(lambda data: struct.pack_into("<q", data, init, tag))
        self.assertIn(b"libc.so.6\0", self.original)
        self.reject(lambda data: data.__setitem__(slice(data.index(b"libc.so.6\0"), data.index(b"libc.so.6\0") + 9), b"evil.so.6"), "dependencies")

    def test_runtime_relocations_cannot_overwrite_identity_constants(self):
        rela = next(value for _, tag, value in dynamic(self.original) if tag == 7)
        _, destination, _ = symbol(self.original, "recomp_abi")
        self.reject(lambda data: struct.pack_into("<Q", data, file_offset(data, rela), destination), "protected export")

    def test_loader_visible_symbol_table_must_match_sections(self):
        at = next(at for at, tag, _ in dynamic(self.original) if tag == 6)
        self.reject(lambda data: struct.pack_into("<Q", data, at + 8, 2**64 - 1), "symbol tables differ")

    def test_gnu_hash_metadata_and_required_lookup_are_checked(self):
        address = next(value for _, tag, value in dynamic(self.original) if tag == 0x6FFFFEF5)
        offset = file_offset(self.original, address)
        buckets, _, bloom_count, _ = struct.unpack_from("<IIII", self.original, offset)
        self.reject(lambda data: struct.pack_into("<I", data, offset + 8, 0), "GNU hash counts")
        # CodexAstraUlt: The names still exist in dynsym, but a zero bloom filter
        # makes them unreachable to the loader and must fail the static audit.
        self.reject(lambda data: data.__setitem__(slice(offset + 16, offset + 16 + bloom_count * 8), bytes(bloom_count * 8)), "GNU bloom")
        bucket_base = offset + 16 + bloom_count * 8
        self.reject(lambda data: struct.pack_into("<I", data, bucket_base, 0xFFFFFFFF), "GNU bucket")

    def test_sysv_hash_libraries_are_supported_and_lookup_corruption_rejects(self):
        # CodexAstraUlt: Exercise the alternate loader hash format with actual
        # linker output rather than inventing a parser-only positive fixture.
        path = self.root / "sysv.so"
        subprocess.run(["cc", "-shared", "-Wl,--hash-style=sysv", "-Wl,-z,noexecstack", str(self.obj), "-o", str(path)],
                       check=True, timeout=20, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        result = self.audit(path)
        self.assertFalse(result["library_loaded"])
        data = bytearray(path.read_bytes())
        address = next(value for _, tag, value in dynamic(data) if tag == 4)
        offset = file_offset(data, address)
        buckets = struct.unpack_from("<I", data, offset)[0]
        data[offset + 8:offset + 8 + buckets * 4] = bytes(buckets * 4)
        path.write_bytes(data)
        with self.assertRaisesRegex(ValueError, "SysV lookup"):
            self.audit(path)
        self.assertFalse(self.marker.exists())

    def test_relocations_and_dynamic_tables_are_bounded(self):
        at = next(at for at, tag, _ in dynamic(self.original) if tag == 8)
        self.reject(lambda data: struct.pack_into("<Q", data, at + 8, 2**64 - 1), "relocation size")
        at = next(at for at, tag, _ in dynamic(self.original) if tag == 7)
        self.reject(lambda data: struct.pack_into("<Q", data, at + 8, 2**64 - 1))

    def test_file_type_size_and_object_kind_are_checked(self):
        link = self.root / "symbolic.so"
        link.symlink_to(self.library)
        with self.assertRaises(ValueError):
            self.audit(link)
        oversized = self.root / "oversized.so"
        with oversized.open("wb") as output:
            output.truncate(AUDIT.MAX_BYTES + 1)
        with self.assertRaisesRegex(ValueError, "bounded regular file"):
            self.audit(oversized)
        with self.assertRaises(ValueError):
            AUDIT.audit_object(self.library, self.machine)
        with self.assertRaises(ValueError):
            self.audit(self.obj)


if __name__ == "__main__":
    unittest.main()
