#!/usr/bin/env python3
"""CodexAstraUlt: Inspect locally compiled ELF files without loading their code.

This bounded host audit checks the preparation/compile identity exports and ELF
container metadata. It does not validate the relocated runtime pointer tables,
attest a compiler, sandbox a library, or execute guest/native functions.
"""

from contextlib import contextmanager
import mmap
import os
from pathlib import Path
import re
import stat
import struct


# CodexAstraUlt: These are admission ceilings for the supported ELF64 host route;
# unsupported extended headers, architectures and relocation kinds reject.
MAX_BYTES = 512 * 1024**2
MAX_SYMBOLS = 2_000_000
MAX_DYNAMIC_SYMBOLS = 65536
MAX_RELOCATIONS = 2_000_000
MAX_ENTRIES = 4_000_000
MAX_MODULES = 4096
MACHINES = {62: "x86_64", 183: "aarch64"}
DEPENDENCIES = {
    "libc.so.6", "libm.so.6", "libgcc_s.so.1", "libpthread.so.0", "libdl.so.2",
    "ld-linux-x86-64.so.2", "ld-linux-aarch64.so.1",
}


def _require(condition, reason):
    """CodexAstraUlt: Malformed and unsupported files share an explicit rejection."""
    if not condition:
        raise ValueError(reason)


def _integer(value, ceiling, name):
    """CodexAstraUlt: Caller expectations cannot smuggle booleans or overflow."""
    _require(type(value) is int and 0 <= value <= ceiling, "invalid " + name)
    return value


class _Elf:
    """CodexAstraUlt: Read only bounded slices of one already opened ELF image."""

    def __init__(self, data, machine, kind):
        self.data = data
        self.length = len(data)
        self.machine = machine
        _require(type(machine) is int and machine in MACHINES, "unsupported expected ELF machine")
        _require(self.length >= 64, "truncated ELF header")
        header = self.unpack("<16sHHIQQQIHHHHHH", 0)
        ident, etype, actual_machine, version, entry, phoff, shoff, flags, ehsize, phsize, phnum, shsize, shnum, shstr = header
        _require(ident[:7] == b"\x7fELF\x02\x01\x01", "expected ELF64 little-endian version 1")
        _require(etype == kind and actual_machine == machine and version == 1, "ELF type or machine mismatch")
        _require(ehsize == 64 and entry == 0 and flags == 0, "unsupported ELF entry/header flags")
        _require(0 < shnum < 0xFF00 and shsize == 64 and shstr < shnum, "unsupported ELF section table")
        self.span(shoff, shnum * shsize)
        self.sections = []
        for index in range(shnum):
            values = self.unpack("<IIQQQQIIQQ", shoff + index * shsize)
            name, stype, sflags, addr, offset, size, link, info, align, entsize = values
            _require(align == 0 or align & (align - 1) == 0, "invalid ELF section alignment")
            _require(addr + size <= 2**64, "ELF section address overflow")
            _require(link < shnum, "ELF section link outside table")
            if stype != 8:  # SHT_NOBITS has memory size but no file payload.
                self.span(offset, size)
            _require(not (sflags & 1 and sflags & 4), "writable executable ELF section")
            self.sections.append({"name": name, "type": stype, "flags": sflags, "address": addr,
                                  "offset": offset, "size": size, "link": link, "info": info,
                                  "alignment": align, "entry_size": entsize})
        _require(self.sections[0]["type"] == 0, "missing ELF null section")
        _require(self.sections[shstr]["type"] == 3, "invalid ELF section-name table")
        names = self.sections[shstr]
        for section in self.sections:
            section["label"] = self.string(names["offset"], names["size"], section["name"])
        self.programs = []
        if kind == 1:
            _require(phnum == 0, "relocatable ELF unexpectedly has program segments")
        else:
            _require(0 < phnum < 0xFFFF and phsize == 56, "unsupported ELF program table")
            self.span(phoff, phnum * phsize)
            for index in range(phnum):
                ptype, pflags, offset, addr, _, filesz, memsz, align = self.unpack("<IIQQQQQQ", phoff + index * phsize)
                _require(pflags & ~7 == 0, "invalid ELF segment flags")
                _require(filesz <= memsz and addr + memsz <= 2**64, "invalid ELF segment sizes")
                self.span(offset, filesz)
                _require(align in (0, 1) or align & (align - 1) == 0, "invalid ELF segment alignment")
                if align > 1:
                    _require(offset % align == addr % align, "ELF load address/offset alignment differs")
                self.programs.append({"type": ptype, "flags": pflags, "offset": offset, "address": addr,
                                      "file_bytes": filesz, "memory_bytes": memsz, "alignment": align})
        self.loads = [p for p in self.programs if p["type"] == 1]
        for before, after in zip(sorted(self.loads, key=lambda p: p["address"]), sorted(self.loads, key=lambda p: p["address"])[1:]):
            _require(before["address"] + before["memory_bytes"] <= after["address"], "overlapping ELF load segments")

    def span(self, offset, size):
        _require(0 <= offset <= self.length and 0 <= size <= self.length - offset, "ELF range outside file")
        return offset

    def unpack(self, form, offset):
        self.span(offset, struct.calcsize(form))
        return struct.unpack_from(form, self.data, offset)

    def string(self, offset, size, index, ceiling=4096):
        self.span(offset, size)
        _require(0 <= index < size, "ELF string outside table")
        start = offset + index
        end = self.data.find(b"\0", start, min(offset + size, start + ceiling + 1))
        _require(end >= start, "unterminated or oversized ELF string")
        try:
            return self.data[start:end].decode("ascii")
        except UnicodeDecodeError as error:
            raise ValueError("non-ASCII ELF metadata string") from error

    def mapped(self, address, size, file_backed=True):
        _require(address + size <= 2**64, "ELF virtual range overflow")
        matches = [p for p in self.loads if p["address"] <= address
                   and address + size <= p["address"] + p["file_bytes" if file_backed else "memory_bytes"]]
        # CodexAstraUlt: Zero-sized arrays still need an unambiguous start in a
        # load segment, but a one-past segment boundary may otherwise match two.
        if size == 0:
            matches = [p for p in matches if address < p["address"] + p["memory_bytes"]]
        _require(len(matches) == 1, "ELF virtual range is not uniquely mapped")
        segment = matches[0]
        offset = segment["offset"] + address - segment["address"]
        if file_backed:
            self.span(offset, size)
        return offset, segment

    def symbols(self, section, collect=True):
        _require(section["entry_size"] == 24 and section["size"] % 24 == 0, "invalid ELF symbol entry size")
        count = section["size"] // 24
        _require(0 < count <= MAX_SYMBOLS, "ELF symbol count exceeds bound")
        _require(section["type"] != 11 or count <= MAX_DYNAMIC_SYMBOLS, "ELF dynamic symbol count exceeds bound")
        strings = self.sections[section["link"]]
        _require(strings["type"] == 3, "ELF symbols do not reference a string table")
        result = []
        for index in range(count):
            name, info, other, ndx, value, size = self.unpack("<IBBHQQ", section["offset"] + index * 24)
            _require(ndx == 0 or ndx < len(self.sections) or ndx in (0xFFF1, 0xFFF2), "unsupported ELF symbol section")
            name = self.string(strings["offset"], strings["size"], name)
            if collect:
                result.append({"name": name, "binding": info >> 4, "type": info & 15, "visibility": other,
                               "section": ndx, "address": value, "size": size})
        return result if collect else count


@contextmanager
def _image(path, machine, kind):
    """CodexAstraUlt: Audit one regular unchanged file; never load or execute it."""
    descriptor = None
    try:
        descriptor = os.open(Path(path), os.O_RDONLY | os.O_CLOEXEC | os.O_NOFOLLOW)
        before = os.fstat(descriptor)
        _require(stat.S_ISREG(before.st_mode) and 0 < before.st_size <= MAX_BYTES, "ELF must be a bounded regular file")
        with mmap.mmap(descriptor, 0, access=mmap.ACCESS_READ) as data:
            yield _Elf(data, machine, kind)
            after = os.fstat(descriptor)
            path_after = os.stat(path, follow_symlinks=False)
            identity = lambda info: (info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns, info.st_ctime_ns)
            _require(identity(before) == identity(after) == identity(path_after), "ELF changed during audit")
    except (OSError, struct.error, OverflowError) as error:
        raise ValueError("ELF could not be audited: " + type(error).__name__) from error
    finally:
        if descriptor is not None:
            os.close(descriptor)


def audit_object(path: Path, machine: int) -> dict:
    """CodexAstraUlt: Reject wrong-host or malformed objects before receipt reuse."""
    with _image(path, machine, 1) as elf:
        symbols = 0
        for section in elf.sections:
            if section["type"] in (2, 11):
                # CodexAstraUlt: Objects may have many hidden local symbols;
                # validate them in place instead of retaining every dictionary.
                symbols += elf.symbols(section, collect=False)
            if section["type"] in (4, 9):
                expected = 24 if section["type"] == 4 else 16
                _require(section["entry_size"] == expected and section["size"] % expected == 0,
                         "invalid object relocation table")
                _require(section["info"] < len(elf.sections) and section["link"] < len(elf.sections)
                         and elf.sections[section["link"]]["type"] in (2, 11), "invalid object relocation target")
            if section["label"] == ".note.GNU-stack":
                _require(not section["flags"] & 4, "object requests an executable stack")
        _require(symbols > 0, "object has no symbol table")
        return {"class": "ELF64", "endian": "little", "type": "REL", "machine": MACHINES[machine],
                "bytes": elf.length, "sections": len(elf.sections), "library_loaded": False}


def _dynamic(elf):
    """CodexAstraUlt: Follow loader-visible metadata instead of trusting section names."""
    segments = [p for p in elf.programs if p["type"] == 2]
    _require(len(segments) == 1, "expected one ELF dynamic segment")
    segment = segments[0]
    _require(0 < segment["file_bytes"] <= 1024**2 and segment["file_bytes"] % 16 == 0, "invalid ELF dynamic segment")
    _require(elf.mapped(segment["address"], segment["file_bytes"])[0] == segment["offset"], "dynamic file mapping mismatch")
    tags, terminated = {}, False
    for offset in range(segment["offset"], segment["offset"] + segment["file_bytes"], 16):
        tag, value = elf.unpack("<qQ", offset)
        if terminated:
            _require(tag == 0 and value == 0, "nonzero dynamic entries after terminator")
            continue
        if tag == 0:
            terminated = True
        else:
            tags.setdefault(tag, []).append(value)
    _require(terminated, "unterminated ELF dynamic segment")
    _require(not any(tag in tags for tag in (15, 29)), "ELF contains RPATH or RUNPATH")
    _require(22 not in tags and not any(value & 4 for value in tags.get(30, [])), "ELF contains text relocations")
    _require(not any(value & 0x08000000 for value in tags.get(0x6FFFFFFB, [])), "ELF is a PIE executable")
    for tag, values in tags.items():
        _require(tag == 1 or len(values) == 1, "duplicate ELF dynamic tag")
    return tags


def _one(tags, tag):
    _require(tag in tags and len(tags[tag]) == 1, "missing ELF dynamic table field")
    return tags[tag][0]


def _hashes(elf, tags, symbols, required):
    """CodexAstraUlt: Required names must be reachable through loader hash tables.

    A dynamic-symbol record alone is insufficient if a damaged bucket or bloom
    filter hides it from dlsym. These lookups remain file reads, never loading.
    """
    _require(4 in tags or 0x6FFFFEF5 in tags, "ELF has no supported dynamic hash table")
    count = len(symbols)
    if 4 in tags:
        offset, _ = elf.mapped(_one(tags, 4), 8)
        buckets, chains = elf.unpack("<II", offset)
        _require(0 < buckets <= MAX_DYNAMIC_SYMBOLS and chains == count, "invalid ELF SysV hash counts")
        elf.mapped(_one(tags, 4), 8 + 4 * (buckets + chains))
        bucket = lambda index: elf.unpack("<I", offset + 8 + index * 4)[0]
        chain = lambda index: elf.unpack("<I", offset + 8 + buckets * 4 + index * 4)[0]
        _require(all(bucket(i) < count for i in range(buckets)) and all(chain(i) < count for i in range(chains)),
                 "ELF SysV hash index outside symbols")
        for name in required:
            hashed = 0
            for byte in name.encode("ascii"):
                hashed = ((hashed << 4) + byte) & 0xFFFFFFFF
                upper = hashed & 0xF0000000
                hashed = (hashed ^ (upper >> 24)) & ~upper
            index = bucket(hashed % buckets)
            visited = set()
            while index and symbols[index]["name"] != name:
                _require(index not in visited, "cyclic ELF SysV lookup")
                visited.add(index)
                index = chain(index)
            _require(index != 0, "required export absent from ELF SysV lookup")
    if 0x6FFFFEF5 in tags:
        address = _one(tags, 0x6FFFFEF5)
        offset, _ = elf.mapped(address, 16)
        buckets, first, bloom_count, shift = elf.unpack("<IIII", offset)
        _require(0 < buckets <= MAX_DYNAMIC_SYMBOLS and 0 < first <= count
                 and 0 < bloom_count <= MAX_DYNAMIC_SYMBOLS and bloom_count & (bloom_count - 1) == 0
                 and shift < 32, "invalid ELF GNU hash counts")
        bloom = offset + 16
        bucket_base = bloom + bloom_count * 8
        chains = bucket_base + buckets * 4
        elf.mapped(address, chains - offset + (count - first) * 4)
        values = [elf.unpack("<I", bucket_base + i * 4)[0] for i in range(buckets)]
        _require(all(value == 0 or first <= value < count for value in values), "ELF GNU bucket outside symbols")
        # CodexAstraUlt: All nonempty buckets need a terminator before the symbol
        # table ends; bound traversal even when the queried names are absent.
        terminal = None
        valid = bytearray(count - first)
        for index in range(count - 1, first - 1, -1):
            if elf.unpack("<I", chains + (index - first) * 4)[0] & 1:
                terminal = index
            valid[index - first] = terminal is not None
        _require(all(value == 0 or valid[value - first] for value in values), "unterminated ELF GNU hash chain")
        for name in required:
            hashed = 5381
            for byte in name.encode("ascii"):
                hashed = (hashed * 33 + byte) & 0xFFFFFFFF
            word = elf.unpack("<Q", bloom + ((hashed // 64) % bloom_count) * 8)[0]
            mask = (1 << (hashed % 64)) | (1 << ((hashed >> shift) % 64))
            _require(word & mask == mask, "required export absent from ELF GNU bloom")
            index = values[hashed % buckets]
            found = False
            while index:
                _require(first <= index < count, "ELF GNU lookup outside symbols")
                value = elf.unpack("<I", chains + (index - first) * 4)[0]
                if value & ~1 == hashed & ~1 and symbols[index]["name"] == name:
                    found = True
                    break
                if value & 1:
                    break
                index += 1
            _require(found, "required export absent from ELF GNU lookup")


def _relocations(elf, tags, symbols, protected):
    """CodexAstraUlt: Check runtime relocation extents and protect constant identities.

    Relocated function/origin pointers are not dereferenced or semantically
    qualified here. Supported target widths only establish bounded destinations.
    """
    count = 0

    def target(address, width):
        nonlocal count
        count += 1
        _require(count <= MAX_RELOCATIONS, "ELF relocation count exceeds bound")
        _require(not any(address < end and start < address + width for start, end in protected),
                 "ELF relocation overlaps a protected export")
        _, segment = elf.mapped(address, width, file_backed=False)
        _require(segment["flags"] & 2, "ELF relocation targets a nonwritable segment")

    def table(address, size, rela):
        width = 24 if rela else 16
        _require(size % width == 0 and size // width <= MAX_RELOCATIONS, "invalid ELF relocation size")
        offset, _ = elf.mapped(address, size)
        for at in range(offset, offset + size, width):
            destination, info = elf.unpack("<QQ", at)
            symbol, kind = info >> 32, info & 0xFFFFFFFF
            _require(symbol < len(symbols), "ELF relocation symbol outside table")
            if kind == 0:
                continue
            if elf.machine == 62:
                widths = {1: 8, 2: 4, 4: 4, 6: 8, 7: 8, 8: 8, 10: 4, 11: 4,
                          12: 2, 13: 2, 14: 1, 15: 1, 16: 8, 17: 8, 18: 8,
                          24: 8, 32: 4, 36: 16, 37: 8, 38: 8}
                copy = 5
            else:
                widths = {257: 8, 258: 4, 259: 2, 260: 8, 261: 4, 262: 2,
                          1025: 8, 1026: 8, 1027: 8, 1028: 8, 1029: 8,
                          1030: 8, 1031: 16, 1032: 8}
                copy = 1024
            if kind == copy:
                target(destination, max(1, symbols[symbol]["size"]))
            else:
                _require(kind in widths, "unsupported ELF dynamic relocation kind")
                target(destination, widths[kind])

    for pointer, size_tag, entry_tag, rela in ((7, 8, 9, True), (17, 18, 19, False)):
        if any(tag in tags for tag in (pointer, size_tag)):
            _require(_one(tags, entry_tag) == (24 if rela else 16), "invalid ELF relocation entry width")
            table(_one(tags, pointer), _one(tags, size_tag), rela)
    if any(tag in tags for tag in (23, 2)):
        kind = _one(tags, 20)
        _require(kind in (7, 17), "unsupported ELF PLT relocation type")
        table(_one(tags, 23), _one(tags, 2), kind == 7)
    if any(tag in tags for tag in (36, 35, 37)):
        size = _one(tags, 35)
        _require(_one(tags, 37) == 8 and size % 8 == 0 and size // 8 <= MAX_RELOCATIONS,
                 "invalid ELF RELR table")
        offset, _ = elf.mapped(_one(tags, 36), size)
        base = None
        for at in range(offset, offset + size, 8):
            value = elf.unpack("<Q", at)[0]
            if value & 1 == 0:
                _require(value % 8 == 0, "unaligned ELF RELR address")
                target(value, 8)
                base = value + 8
            else:
                _require(base is not None, "ELF RELR bitmap has no base")
                for bit in range(1, 64):
                    if value & (1 << bit):
                        target(base + (bit - 1) * 8, 8)
                base += 63 * 8
                _require(base <= 2**64, "ELF RELR address overflow")
    return count


def audit_library(path: Path, machine: int, preparation_sha256: str,
                  contract_sha256: str, module_count: int) -> dict:
    """CodexAstraUlt: Bind a host library statically; this never performs dlopen."""
    for value in (preparation_sha256, contract_sha256):
        _require(isinstance(value, str) and re.fullmatch(r"[0-9a-f]{64}", value) is not None,
                 "invalid expected library identity")
    _integer(module_count, MAX_MODULES, "expected module count")
    with _image(path, machine, 3) as elf:
        _require(elf.loads and any(p["flags"] & 1 for p in elf.loads), "ELF has no executable load segment")
        _require(not any(p["flags"] & 1 and p["flags"] & 2 for p in elf.loads), "writable executable ELF load segment")
        _require(not any(p["type"] == 3 for p in elf.programs), "ELF library has an interpreter segment")
        stacks = [p for p in elf.programs if p["type"] == 0x6474E551]
        _require(len(stacks) == 1 and not stacks[0]["flags"] & 1, "missing or executable GNU stack")
        tags = _dynamic(elf)
        dynsyms = [s for s in elf.sections if s["type"] == 11]
        _require(len(dynsyms) == 1, "expected one dynamic symbol table")
        section = dynsyms[0]
        strings = elf.sections[section["link"]]
        _require(_one(tags, 6) == section["address"] and _one(tags, 11) == 24,
                 "loader and section symbol tables differ")
        _require(_one(tags, 5) == strings["address"] and _one(tags, 10) == strings["size"],
                 "loader and section string tables differ")
        for item in (section, strings):
            _require(elf.mapped(item["address"], item["size"])[0] == item["offset"], "ELF section/load mapping mismatch")
        symbols = elf.symbols(section)
        dependencies = [elf.string(strings["offset"], strings["size"], index, 255) for index in tags.get(1, [])]
        _require(len(set(dependencies)) == len(dependencies) and set(dependencies) <= DEPENDENCIES,
                 "unexpected ELF host dependencies")
        protected, required = [], []

        def exported(name, expected_size, constant=False):
            required.append(name)
            found = [symbol for symbol in symbols if symbol["name"] == name]
            _require(len(found) == 1, "missing or duplicate required ELF export: " + name)
            symbol = found[0]
            _require(symbol["binding"] == 1 and symbol["type"] == 1 and symbol["visibility"] == 0
                     and 0 < symbol["section"] < len(elf.sections), "invalid ELF export type: " + name)
            _require(symbol["size"] == expected_size, "ELF export size mismatch: " + name)
            owner = elf.sections[symbol["section"]]
            _require(owner["type"] != 8 and owner["flags"] & 2 and owner["address"] <= symbol["address"]
                     and symbol["address"] + expected_size <= owner["address"] + owner["size"],
                     "ELF export outside file-backed section: " + name)
            offset, load = elf.mapped(symbol["address"], expected_size)
            _require(offset == owner["offset"] + symbol["address"] - owner["address"],
                     "ELF export section/load mapping mismatch: " + name)
            if constant:
                _require(not load["flags"] & 2 and not owner["flags"] & 1, "writable ELF identity/count export")
                protected.append((symbol["address"], symbol["address"] + expected_size))
            return offset

        def scalar(name):
            return elf.unpack("<I", exported(name, 4, True))[0]

        _require(scalar("recomp_abi") == 4 and scalar("recomp_generation") == 3, "native ABI/generation mismatch")
        entries = scalar("recomp_entry_count")
        _require(0 < entries <= MAX_ENTRIES, "native entry count outside bound")
        _require(scalar("recomp_module_count") == module_count, "native module count mismatch")
        exported("recomp_entries", entries * 16)
        exported("recomp_modules", module_count * 32)
        exported("recomp_origins", (module_count + 1) * 56)
        for name, expected in (("droidds_preparation_sha256", preparation_sha256),
                               ("droidds_compile_contract_sha256", contract_sha256)):
            offset = exported(name, 65, True)
            _require(elf.data[offset:offset + 65] == expected.encode("ascii") + b"\0", "native identity export mismatch")
        _hashes(elf, tags, symbols, required)
        relocations = _relocations(elf, tags, symbols, protected)
        return {"class": "ELF64", "endian": "little", "type": "DYN", "machine": MACHINES[machine],
                "bytes": elf.length, "abi": 4, "generation": 3, "entry_count": entries,
                "module_count": module_count, "needed": dependencies,
                "preparation_sha256": preparation_sha256, "compile_contract_sha256": contract_sha256,
                "relocations_checked": relocations, "text_relocations": False,
                "executable_stack": False, "runtime_tables_validated": False, "library_loaded": False}
