#!/usr/bin/env python3
"""CodexAstraUlt: Real original ELF tables exercise pre-load runtime admission."""

import copy
import hashlib
import importlib.util
from pathlib import Path
import platform
import shutil
import struct
import subprocess
import tempfile
import unittest
from unittest import mock


SPEC = importlib.util.spec_from_file_location("private_runtime_elf", Path(__file__).resolve().parents[1] / "private_runtime_elf.py")
AUDIT = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(AUDIT)
PREPARATION, CONTRACT = "1" * 64, "2" * 64
UNITS = [{"name": None, "text_start": 0x100000, "text": bytes(range(1, 9))},
         {"name": "unit.cro", "text_start": 0x200, "text": bytes(range(9, 13))}]


def original_c(marker, empty=False):
    """CodexAstraUlt: Hash constants cover known original bytes, never a title."""
    source = r'''
#include <stdint.h>
#include <stdio.h>
#define E __attribute__((visibility("default")))
typedef struct {uint32_t address; void (*code)(void *);} Entry;
typedef struct {const char *name; uint32_t *base; uint32_t size,count; const Entry *entries;} Module;
typedef struct {uint32_t start,end; uint64_t hash;} Piece;
typedef struct {uint32_t first,count,start;} Origin;
typedef struct {uint32_t first,end;} Run;
typedef struct {uint32_t count,piece_count; const Piece *pieces; const Origin *functions;
 const Run *runs; const uint32_t *owners; uint8_t *stale; uint32_t *starts;} Origins;
static void guest0(void *ctx) {(void)ctx;}
static void guest1(void *ctx) {(void)ctx;}
static void module_guest(void *ctx) {(void)ctx;}
E const uint32_t recomp_abi=4,recomp_generation=3,recomp_entry_count=2,recomp_module_count=1;
E const Entry recomp_entries[]={{0x100000,guest0},{0x100004,guest1}};
static const Entry module_entries[]={{0x200,module_guest}};
static uint32_t module_base;
E const Module recomp_modules[]={{"unit.cro",&module_base,0x204,1,module_entries}};
static const Piece pieces[]={{0x100000,0x100004,0xbe7a5e775165785dULL},{0x100004,0x100008,0x614326560c39f905ULL}};
static const Origin functions[]={{0,1,0x100000},{1,1,0x100004}};
static const Run runs[]={{0,1},{1,2}};
static const uint32_t owners[]={0,1};
static uint8_t stale[2] __attribute__((aligned(4))); static uint32_t starts[]={0x100000,0x100004};
static const Piece module_pieces[]={{0x200,0x204,0x03806eba2a3c468dULL}};
static const Origin module_functions[]={{0,1,0x200}};
static const Run module_runs[]={{0,1}};
static const uint32_t module_owners[]={0};
static uint8_t module_stale[1]; static uint32_t module_starts[]={0x200};
E const Origins recomp_origins[]={
 {2,2,pieces,functions,runs,owners,stale,starts},
 {1,1,module_pieces,module_functions,module_runs,module_owners,module_stale,module_starts}};
E const char droidds_preparation_sha256[65]="PREPARATION";
E const char droidds_compile_contract_sha256[65]="CONTRACT";
__attribute__((constructor)) static void must_not_run(void) {
 FILE *f=fopen("MARKER","w"); if(f) {fputs("loaded",f);fclose(f);}
}
'''
    if empty:
        source = source.replace('module_entries[]={{0x200,module_guest}}', 'module_entries[]={}')
        source = source.replace('0x204,1,module_entries', '0x204,0,module_entries')
        source = source.replace('module_starts[]={0x200}', 'module_starts[]={0}')
        source = source.replace('{1,1,module_pieces,module_functions,module_runs,module_owners,module_stale,module_starts}',
                                '{0,0,0,0,0,0,module_stale,module_starts}')
    return source.replace('PREPARATION', PREPARATION).replace('CONTRACT', CONTRACT).replace('MARKER', str(marker))


def sections(data):
    """CodexAstraUlt: Locate mutations independently through standard ELF fields."""
    offset = struct.unpack_from("<Q", data, 40)[0]
    size, count = struct.unpack_from("<HH", data, 58)
    return [struct.unpack_from("<IIQQQQIIQQ", data, offset + i * size) for i in range(count)]


def symbol(data, wanted, dynamic_only=False):
    table = sections(data)
    for section in table:
        if section[1] not in ((11,) if dynamic_only else (2, 11)):
            continue
        strings = table[section[6]]
        for at in range(section[4], section[4] + section[5], 24):
            name, _, _, _, value, size = struct.unpack_from("<IBBHQQ", data, at)
            begin = strings[4] + name
            if data[begin:data.index(0, begin)].decode() == wanted:
                return value, size, at
    raise AssertionError(wanted)


def offset(data, address):
    phoff = struct.unpack_from("<Q", data, 32)[0]
    phsize, phcount = struct.unpack_from("<HH", data, 54)
    for i in range(phcount):
        p = struct.unpack_from("<IIQQQQQQ", data, phoff + i * phsize)
        if p[0] == 1 and p[3] <= address < p[3] + p[5]:
            return p[2] + address - p[3]
    raise AssertionError(hex(address))


def relocation(data, address):
    for section in sections(data):
        if section[1] != 4:
            continue
        for at in range(section[4], section[4] + section[5], 24):
            if struct.unpack_from("<Q", data, at)[0] == address:
                return at
    raise AssertionError(hex(address))


class RuntimeElfTests(unittest.TestCase):
    """CodexAstraUlt: Compilation is required; none of these libraries is loaded."""

    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory(prefix="droidds-runtime-elf-original-")
        cls.root = Path(cls.tmp.name)
        cls.machine = {"x86_64": 62, "aarch64": 183}.get(platform.machine())
        if cls.machine is None or shutil.which("cc") is None:
            raise AssertionError("runtime ELF tests require a supported host C compiler")
        cls.marker = cls.root / "must-not-be-loaded"
        cls.libraries = {}
        for kind, extra, empty in (("ordinary", [], False),
                                   ("relr", ["-Wl,-z,pack-relative-relocs"], False),
                                   ("empty", [], True)):
            src, lib = cls.root / (kind + ".c"), cls.root / (kind + ".so")
            src.write_text(original_c(cls.marker, empty))
            subprocess.run(["cc", "-fPIC", "-fvisibility=hidden", "-shared", "-Wl,-z,relro",
                            "-Wl,-z,now", *extra, str(src), "-o", str(lib)],
                           check=True, timeout=30, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            cls.libraries[kind] = lib
        cls.original = cls.libraries["ordinary"].read_bytes()

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def tearDown(self):
        self.assertFalse(self.marker.exists(), "the static auditor executed a constructor")

    def audit(self, data=None, units=None, kind="ordinary"):
        if data is None:
            path = self.libraries[kind]
        else:
            path = self.root / (self._testMethodName + ".so")
            path.write_bytes(data)
        return AUDIT.audit_runtime_library(path, self.machine, PREPARATION, CONTRACT,
                                           UNITS if units is None else units)

    def mutate_word(self, name, displacement, value):
        data = bytearray(self.original)
        address = symbol(data, name)[0]
        struct.pack_into("<I", data, offset(data, address) + displacement, value)
        return data

    def mutate_pointer(self, name, displacement, target):
        data = bytearray(self.original)
        address = symbol(data, name)[0]
        at = relocation(data, address + displacement)
        struct.pack_into("<q", data, at + 16, target)
        return data

    def test_original_base_and_module_tables_admit_without_loading(self):
        result = self.audit()
        self.assertTrue(result["runtime_tables_validated"])
        self.assertFalse(result["library_loaded"])
        self.assertFalse(result["code_freshness_validated"])
        self.assertEqual(result["library_sha256"], hashlib.sha256(self.original).hexdigest())
        self.assertEqual([u["entry_count"] for u in result["units"]], [2, 1])
        self.assertEqual([u["name"] for u in result["units"]], [None, "unit.cro"])

    def test_relr_library_admits_without_loading(self):
        result = self.audit(kind="relr")
        self.assertTrue(result["runtime_tables_validated"])
        self.assertEqual([u["function_count"] for u in result["units"]], [2, 1])

    def test_empty_generated_module_is_valid(self):
        result = self.audit(kind="empty")
        self.assertEqual(result["units"][1]["function_count"], 0)
        self.assertEqual(result["units"][1]["entry_count"], 0)

    def test_expected_identity_and_unit_validation(self):
        for changed in ({"name": "wrong.cro"}, {"text_start": 0x204}, {"text": b"bad!"}):
            units = copy.deepcopy(UNITS)
            units[1].update(changed)
            with self.subTest(changed=changed), self.assertRaises(ValueError):
                self.audit(units=units)
        units = copy.deepcopy(UNITS)
        units[0]["text_start"] = True
        with self.assertRaisesRegex(ValueError, "invalid_text_address"):
            self.audit(units=units)
        with self.assertRaises(ValueError):
            AUDIT.audit_runtime_library(self.libraries["ordinary"], self.machine, "3" * 64, CONTRACT, UNITS)

    def test_excessive_origin_count_rejects_before_array_reads(self):
        with self.assertRaisesRegex(ValueError, "table_count_exceeds_bound"):
            self.audit(self.mutate_word("recomp_origins", 0, 4_000_001))

    def test_origin_run_overflow_rejects(self):
        with self.assertRaisesRegex(ValueError, "origin_function_run_range"):
            self.audit(self.mutate_word("functions", 4, 0xFFFFFFFF))

    def test_out_of_range_run_piece_rejects(self):
        with self.assertRaisesRegex(ValueError, "origin_run_piece_range"):
            self.audit(self.mutate_word("runs", 4, 3))

    def test_owner_out_of_range_and_no_origin_reject(self):
        for owner in (2, 0xFFFFFFFF):
            with self.subTest(owner=owner), self.assertRaisesRegex(ValueError, "entry_owner_out_of_range"):
                self.audit(self.mutate_word("owners", 0, owner))

    def test_unsorted_duplicate_guest_entries_reject(self):
        with self.assertRaisesRegex(ValueError, "invalid_or_unsorted_entry"):
            self.audit(self.mutate_word("recomp_entries", 16, 0x100000))

    def test_missing_function_start_entry_rejects(self):
        with self.assertRaisesRegex(ValueError, "function_missing_start_entry"):
            self.audit(self.mutate_word("recomp_entries", 0, 0x100003))

    def test_piece_hash_and_range_corruption_reject(self):
        with self.assertRaisesRegex(ValueError, "origin_piece_hash_mismatch"):
            self.audit(self.mutate_word("pieces", 8, 0))
        with self.assertRaisesRegex(ValueError, "origin_piece_range"):
            self.audit(self.mutate_word("pieces", 16, 0x100002))

    def test_origin_start_initial_value_rejects(self):
        with self.assertRaisesRegex(ValueError, "origin_start_initial_value"):
            self.audit(self.mutate_word("starts", 0, 0x100004))

    def test_module_extent_and_initial_base_reject(self):
        with self.assertRaisesRegex(ValueError, "module_text_extent_mismatch"):
            self.audit(self.mutate_word("recomp_modules", 16, 0x208))
        target = symbol(self.original, "starts")[0]
        with self.assertRaisesRegex(ValueError, "module_base_not_zero"):
            self.audit(self.mutate_pointer("recomp_modules", 8, target))

    def test_pointer_outside_image_rejects(self):
        with self.assertRaises(ValueError):
            self.audit(self.mutate_pointer("recomp_origins", 8, 0x7FFFFFFF))

    def test_unaligned_origin_array_rejects(self):
        target = symbol(self.original, "functions")[0] + 1
        with self.assertRaisesRegex(ValueError, "missing_or_unaligned_table"):
            self.audit(self.mutate_pointer("recomp_origins", 16, target))

    def test_code_pointer_to_nonexecutable_data_rejects(self):
        target = symbol(self.original, "pieces")[0]
        with self.assertRaisesRegex(ValueError, "entry_code_permissions"):
            self.audit(self.mutate_pointer("recomp_entries", 8, target))

    def test_mutable_pointer_into_relro_rejects(self):
        target = symbol(self.original, "recomp_origins")[0]
        with self.assertRaisesRegex(ValueError, "mutable_table_overlaps_relro"):
            self.audit(self.mutate_pointer("recomp_origins", 40, target))

    def test_mutable_metadata_alias_rejects(self):
        target = symbol(self.original, "stale")[0]
        with self.assertRaisesRegex(ValueError, "mutable_metadata_alias"):
            self.audit(self.mutate_pointer("recomp_modules", 8, target))

    def test_missing_relative_pointer_rejects(self):
        data = bytearray(self.original)
        address = symbol(data, "recomp_origins")[0] + 8
        at = relocation(data, address)
        struct.pack_into("<Q", data, at + 8, 0)
        with self.assertRaisesRegex(ValueError, "pointer_missing_relative_relocation"):
            self.audit(data)

    def test_symbol_interposed_metadata_pointer_rejects(self):
        data = bytearray(self.original)
        address = symbol(data, "recomp_origins")[0] + 8
        at = relocation(data, address)
        kind = 6 if self.machine == 62 else 1025
        struct.pack_into("<Q", data, at + 8, (1 << 32) | kind)
        with self.assertRaisesRegex(ValueError, "pointer_relocation_not_local_relative"):
            self.audit(data)

    def test_overlapping_relocations_reject(self):
        data = bytearray(self.original)
        address = symbol(data, "recomp_origins")[0]
        at = relocation(data, address + 16)
        struct.pack_into("<Q", data, at, address + 8)
        with self.assertRaisesRegex(ValueError, "overlapping_relocations"):
            self.audit(data)

    def test_overlapping_local_and_symbol_relocations_reject(self):
        data = bytearray(self.original)
        address = symbol(data, "recomp_origins")[0]
        at = relocation(data, address + 16)
        struct.pack_into("<Q", data, at, address + 8)
        kind = 6 if self.machine == 62 else 1025
        struct.pack_into("<Q", data, at + 8, (1 << 32) | kind)
        with self.assertRaisesRegex(ValueError, "overlapping_relocations"):
            self.audit(data)

    def test_one_function_cannot_mix_arm_and_thumb_entries(self):
        data = self.mutate_word("recomp_origins", 0, 1)
        struct.pack_into("<I", data, offset(data, symbol(data, "functions")[0]) + 4, 2)
        struct.pack_into("<I", data, offset(data, symbol(data, "owners")[0]) + 4, 0)
        entries = symbol(data, "recomp_entries")[0]
        struct.pack_into("<I", data, offset(data, entries) + 16, 0x100005)
        first = relocation(data, entries + 8)
        second = relocation(data, entries + 24)
        struct.pack_into("<q", data, second + 16, struct.unpack_from("<q", data, first + 16)[0])
        with self.assertRaisesRegex(ValueError, "owner_has_mixed_guest_modes"):
            self.audit(data)

    def test_relocation_overwriting_table_scalar_rejects(self):
        data = bytearray(self.original)
        address = symbol(data, "recomp_entries")[0]
        at = relocation(data, address + 8)
        struct.pack_into("<Q", data, at, address)
        with self.assertRaisesRegex(ValueError, "relocation_overwrites_scalar_array"):
            self.audit(data)

    def test_ifunc_symbol_and_irelative_reject(self):
        data = bytearray(self.original)
        _, _, at = symbol(data, "fopen", dynamic_only=True)
        data[at + 4] = (data[at + 4] & 0xF0) | 10
        with self.assertRaisesRegex(ValueError, "ifunc_symbol_unsupported"):
            self.audit(data)
        data = bytearray(self.original)
        at = relocation(data, symbol(data, "recomp_entries")[0] + 8)
        struct.pack_into("<Q", data, at + 8, 37 if self.machine == 62 else 1032)
        with self.assertRaisesRegex(ValueError, "ifunc_relocation_unsupported"):
            self.audit(data)

    def test_changed_library_between_audits_rejects(self):
        path = self.root / "between-audits.so"
        path.write_bytes(self.original)
        original = AUDIT.ELF.audit_library
        def replace(*args, **kwargs):
            result = original(*args, **kwargs)
            path.write_bytes(path.read_bytes() + b"changed")
            return result
        with mock.patch.object(AUDIT.ELF, "audit_library", side_effect=replace):
            with self.assertRaisesRegex(ValueError, "library_changed_between_audits"):
                AUDIT.audit_runtime_library(path, self.machine, PREPARATION, CONTRACT, UNITS)


if __name__ == "__main__":
    unittest.main()
