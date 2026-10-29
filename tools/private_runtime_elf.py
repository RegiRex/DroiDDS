#!/usr/bin/env python3
"""CodexAstraUlt: Qualify generated ABI tables without loading native code.

This is admission for a trusted, locally compiled title, not an ELF sandbox.
Ordinary compiler CRT constructors remain permitted. The caller must bind the
library to its preparation/compile manifests and prevent replacement before
loading (for example, by passing a sealed memfd). No existing compile-contract
helper is changed by this additional runtime check.

``units`` is an ordered list of dictionaries with exactly ``name``,
``text_start`` and ``text``. The executable comes first with name=None; CROs
follow in generation order. ``text`` is immutable bytes and ``text_start`` is
the guest executable address or CRO code-segment file offset. Only the single
nonempty CRO kind-0 segment is supported. Original relocation slots are data,
not instruction-origin pieces; a piece hash mismatch rejects admission.
"""

import bisect
import hashlib
import importlib.util
import os
from pathlib import Path
import struct


# CodexAstraUlt: Reuse the unchanged compilation auditor; only this module owns
# stricter runtime table semantics, so old compiled contracts remain valid.
_SPEC = importlib.util.spec_from_file_location(
    "_droidds_compile_elf_runtime", Path(__file__).with_name("private_compile_elf.py"))
ELF = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(ELF)
MAX_COUNT = 4_000_000
MAX_ELEMENTS = 16_000_000
MAX_TEXT_BYTES = 64 * 1024**2
MAX_TOTAL_TEXT_BYTES = 320 * 1024**2
MAX_NAME_BYTES = 4096
_U32 = 0xFFFFFFFF


def _require(condition, reason):
    """CodexAstraUlt: Stable categories never include private source contents."""
    if not condition:
        raise ValueError("runtime_" + reason)


def _units(values):
    """CodexAstraUlt: Validate caller expectations before reading ELF tables."""
    _require(isinstance(values, list) and 1 <= len(values) <= ELF.MAX_MODULES + 1,
             "invalid_units")
    seen, total = set(), 0
    for index, item in enumerate(values):
        _require(isinstance(item, dict) and set(item) == {"name", "text_start", "text"},
                 "invalid_unit_fields")
        name, start, text = item["name"], item["text_start"], item["text"]
        _require(name is None if index == 0 else isinstance(name, str) and bool(name),
                 "invalid_unit_name")
        if name is not None:
            try:
                encoded = name.encode("utf-8")
            except UnicodeError as error:
                raise ValueError("runtime_invalid_unit_name") from error
            _require(b"\0" not in encoded and len(encoded) <= MAX_NAME_BYTES and name not in seen,
                     "invalid_unit_name")
            seen.add(name)
        _require(type(start) is int and 0 <= start <= _U32 and start % 2 == 0,
                 "invalid_text_address")
        _require(type(text) is bytes and 0 < len(text) <= MAX_TEXT_BYTES
                 and start + len(text) <= 2**32, "invalid_text_bytes")
        total += len(text)
        _require(total <= MAX_TOTAL_TEXT_BYTES, "text_total_exceeds_bound")


def _fingerprint(path):
    """CodexAstraUlt: Detect replacement between the two independent audits."""
    info = os.stat(path, follow_symlinks=False)
    return (info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns, info.st_ctime_ns)


class _Relocations:
    """CodexAstraUlt: Model loader writes, resolving only local relative pointers."""

    def __init__(self, elf, tags, symbols):
        self.elf, self.items = elf, []
        relative = 8 if elf.machine == 62 else 1027
        widths = ({1: 8, 6: 8, 7: 8, 8: 8, 16: 8, 17: 8, 18: 8, 36: 16}
                  if elf.machine == 62 else
                  {257: 8, 1025: 8, 1026: 8, 1027: 8, 1028: 8,
                   1029: 8, 1030: 8, 1031: 16})

        def add(destination, width, pointer):
            _require(len(self.items) < ELF.MAX_RELOCATIONS, "relocation_count_exceeds_bound")
            _, segment = elf.mapped(destination, width, file_backed=False)
            _require(segment["flags"] & 2, "relocation_destination_not_writable")
            self.items.append((destination, destination + width, pointer))

        def table(address, size, rela):
            width = 24 if rela else 16
            _require(size % width == 0, "invalid_relocation_width")
            offset, _ = elf.mapped(address, size)
            for at in range(offset, offset + size, width):
                destination, info = elf.unpack("<QQ", at)
                symbol, kind = info >> 32, info & _U32
                _require(symbol < len(symbols), "relocation_symbol_out_of_range")
                if kind == 0:
                    continue
                _require(kind not in (37, 1032), "ifunc_relocation_unsupported")
                _require(kind in widths, "relocation_kind_unsupported")
                pointer = None
                if kind == relative:
                    _require(symbol == 0, "relative_relocation_has_symbol")
                    if rela:
                        pointer = elf.unpack("<q", at + 16)[0]
                    else:
                        source, _ = elf.mapped(destination, 8)
                        pointer = elf.unpack("<Q", source)[0]
                    _require(pointer >= 0, "negative_relative_pointer")
                add(destination, widths[kind], pointer)

        for pointer, size, entry, rela in ((7, 8, 9, True), (17, 18, 19, False)):
            if pointer in tags or size in tags:
                _require(ELF._one(tags, entry) == (24 if rela else 16), "relocation_entry_width")
                table(ELF._one(tags, pointer), ELF._one(tags, size), rela)
        if 23 in tags or 2 in tags:
            kind = ELF._one(tags, 20)
            _require(kind in (7, 17), "plt_relocation_kind")
            table(ELF._one(tags, 23), ELF._one(tags, 2), kind == 7)
        if any(tag in tags for tag in (36, 35, 37)):
            size = ELF._one(tags, 35)
            _require(ELF._one(tags, 37) == 8 and size % 8 == 0, "relr_entry_width")
            offset, _ = elf.mapped(ELF._one(tags, 36), size)
            base = None
            for at in range(offset, offset + size, 8):
                value = elf.unpack("<Q", at)[0]
                if value & 1 == 0:
                    _require(value % 8 == 0, "relr_alignment")
                    destinations, base = (value,), value + 8
                else:
                    _require(base is not None, "relr_missing_base")
                    destinations = (base + (bit - 1) * 8 for bit in range(1, 64) if value & (1 << bit))
                    old_base = base
                    # Consume the generator before changing the base it closes over.
                    destinations = tuple(destinations)
                    base = old_base + 63 * 8
                _require(base <= 2**64, "relr_address_overflow")
                for destination in destinations:
                    source, _ = elf.mapped(destination, 8)
                    add(destination, 8, elf.unpack("<Q", source)[0])
        self.items.sort(key=lambda item: (item[0], item[1]))
        for before, after in zip(self.items, self.items[1:]):
            _require(before[1] <= after[0], "overlapping_relocations")
        self.starts = [item[0] for item in self.items]

    def overlaps(self, address, size):
        if size == 0:
            return []
        index = max(0, bisect.bisect_right(self.starts, address) - 1)
        result = []
        while index < len(self.items) and self.items[index][0] < address + size:
            item = self.items[index]
            if item[1] > address:
                result.append(item)
            index += 1
        return result

    def plain(self, address, size):
        _require(not self.overlaps(address, size), "relocation_overwrites_scalar_array")

    def pointer(self, address):
        _require(address % 8 == 0, "unaligned_pointer_slot")
        offset, _ = self.elf.mapped(address, 8)
        items = self.overlaps(address, 8)
        if not items:
            _require(self.elf.unpack("<Q", offset)[0] == 0, "pointer_missing_relative_relocation")
            return None
        _require(len(items) == 1 and items[0][:2] == (address, address + 8)
                 and items[0][2] is not None, "pointer_relocation_not_local_relative")
        return items[0][2]


class _Tables:
    """CodexAstraUlt: Bound the entire ABI graph before any unsafe host slices."""

    def __init__(self, elf, relocations):
        self.elf, self.relocations = elf, relocations
        self.ranges, self.elements = [], 0
        # CodexAstraUlt: The loader protects pages, not arbitrary byte ranges;
        # conservatively reject mutable arrays sharing any declared RELRO page.
        page = os.sysconf("SC_PAGE_SIZE")
        _require(type(page) is int and 4096 <= page <= 65536 and page & (page - 1) == 0,
                 "unsupported_host_page_size")
        self.relro = [(p["address"] // page * page,
                       (p["address"] + p["memory_bytes"] + page - 1) // page * page)
                      for p in elf.programs if p["type"] == 0x6474E552]

    def count(self, value):
        _require(0 <= value <= MAX_COUNT, "table_count_exceeds_bound")
        self.elements += value
        _require(self.elements <= MAX_ELEMENTS, "table_elements_exceed_bound")
        return value

    def region(self, address, size, alignment=1, mutable=False, plain=True):
        _require(address is not None and address % alignment == 0, "missing_or_unaligned_table")
        offset, segment = self.elf.mapped(address, size, file_backed=not mutable)
        _require(segment["flags"] & 4 and not segment["flags"] & 1, "table_permissions")
        if mutable:
            _require(segment["flags"] & 2, "mutable_table_not_writable")
            _require(not any(address < end and start < address + size for start, end in self.relro),
                     "mutable_table_overlaps_relro")
        if plain:
            self.relocations.plain(address, size)
        if size:
            self.ranges.append((address, address + size, mutable))
        return offset

    def memory(self, address, size):
        """CodexAstraUlt: Include loader-created zero-fill when checking .bss."""
        offset, segment = self.elf.mapped(address, size, file_backed=False)
        available = max(0, min(size, segment["address"] + segment["file_bytes"] - address))
        return bytes(self.elf.data[offset:offset + available]) + bytes(size - available)

    def string(self, address):
        _require(address is not None, "null_module_name")
        offset, segment = self.elf.mapped(address, 1)
        size = min(MAX_NAME_BYTES + 1, segment["address"] + segment["file_bytes"] - address)
        end = self.elf.data.find(b"\0", offset, offset + size)
        _require(end > offset, "invalid_module_name_string")
        self.region(address, end - offset + 1)
        try:
            return self.elf.data[offset:end].decode("utf-8")
        except UnicodeError as error:
            raise ValueError("runtime_invalid_module_name_encoding") from error

    def finish(self):
        """CodexAstraUlt: No host-writable control array may alias other metadata."""
        mutable_end = immutable_end = 0
        for start, end, mutable in sorted(self.ranges):
            if mutable:
                _require(start >= max(mutable_end, immutable_end), "mutable_metadata_alias")
                mutable_end = max(mutable_end, end)
            else:
                _require(start >= mutable_end, "mutable_metadata_alias")
                immutable_end = max(immutable_end, end)


def _fnv(data):
    """CodexAstraUlt: Match ABI CodeHash exactly; this is not authentication."""
    value = 0xCBF29CE484222325
    for byte in data:
        value = ((value ^ byte) * 0x100000001B3) & 0xFFFFFFFFFFFFFFFF
    return value


def _unit(tables, expected, entries_address, entry_count, origin_address, base_address):
    """CodexAstraUlt: Validate origin ownership and every reachable pointer."""
    elf, rel = tables.elf, tables.relocations
    start, text = expected["text_start"], expected["text"]
    end = start + len(text)
    entry_count = tables.count(entry_count)
    entry_offset = tables.region(entries_address, entry_count * 16, 8, plain=False)
    origin_offset = tables.region(origin_address, 56, 8, plain=False)
    rel.plain(origin_address, 8)
    count, piece_count = elf.unpack("<II", origin_offset)
    count, piece_count = tables.count(count), tables.count(piece_count)
    pieces, functions, runs, owners, stale, starts = [rel.pointer(origin_address + at)
                                                    for at in (8, 16, 24, 32, 40, 48)]
    tables.region(stale, max(count, 1), mutable=True)
    tables.region(starts, max(count, 1) * 4, 4, mutable=True)
    _require(not any(tables.memory(stale, max(count, 1))), "stale_flags_not_zero")
    initial_starts = tables.memory(starts, max(count, 1) * 4)
    if base_address is not None:
        tables.region(base_address, 4, 4, mutable=True)
        _require(tables.memory(base_address, 4) == bytes(4), "module_base_not_zero")
    if count == 0:
        _require(piece_count == entry_count == 0 and all(v is None for v in (pieces, functions, runs, owners))
                 and initial_starts == bytes(4), "invalid_empty_origin_unit")
        return {"name": expected["name"], "text_start": start, "text_bytes": len(text),
                "entry_count": 0, "function_count": 0, "piece_count": 0,
                "entries_address": entries_address, "origins_address": origin_address,
                "stale_address": stale, "starts_address": starts, "base_address": base_address}
    _require(piece_count > 0 and entry_count > 0, "missing_origin_data")
    piece_offset = tables.region(pieces, piece_count * 16, 8)
    function_offset = tables.region(functions, count * 12, 4)
    owner_offset = tables.region(owners, entry_count * 4, 4)
    tables.count(entry_count)
    previous_end = start
    piece_ranges, gaps_before = [], [0]
    for index in range(piece_count):
        first, last, hashed = elf.unpack("<IIQ", piece_offset + index * 16)
        _require(start <= first < last <= end and first >= previous_end, "origin_piece_range")
        _require(_fnv(memoryview(text)[first - start:last - start]) == hashed,
                 "origin_piece_hash_mismatch")
        piece_ranges.append((first, last))
        gaps_before.append(gaps_before[-1] + int(index > 0 and first != previous_end))
        previous_end = last
    functions_data, run_count, previous_start = [], 0, -1
    for index in range(count):
        first, number, address = elf.unpack("<III", function_offset + index * 12)
        _require(first == run_count and number > 0 and number <= MAX_COUNT - run_count,
                 "origin_function_run_range")
        _require(start <= address < end and address % 2 == 0 and address > previous_start,
                 "origin_function_start")
        _require(struct.unpack_from("<I", initial_starts, index * 4)[0] == address,
                 "origin_start_initial_value")
        functions_data.append((first, number, address))
        run_count += number
        previous_start = address
    tables.count(run_count)
    run_offset = tables.region(runs, run_count * 8, 4)
    run_ranges = []
    for index in range(run_count):
        first, last = elf.unpack("<II", run_offset + index * 8)
        _require(first < last <= piece_count, "origin_run_piece_range")
        _require(gaps_before[last] == gaps_before[first + 1], "origin_run_crosses_piece_gap")
        run_ranges.append((first, last))
    # CodexAstraUlt: Check membership with sorted function spans. Generated
    # starts and resume entries must actually belong to their declared owner.
    function_spans = []
    for first, number, address in functions_data:
        spans, previous_piece = [], 0
        for pfirst, plast in run_ranges[first:first + number]:
            _require(not spans or pfirst >= previous_piece, "origin_function_runs_overlap")
            spans.append((piece_ranges[pfirst][0], piece_ranges[plast - 1][1]))
            previous_piece = plast
        span_starts = [a for a, _ in spans]
        position = bisect.bisect_right(span_starts, address) - 1
        _require(position >= 0 and address < spans[position][1], "function_start_outside_origin")
        function_spans.append((spans, span_starts))
    owner_codes, owner_modes, owner_starts = [None] * count, [None] * count, [False] * count
    previous_address = -1
    for index in range(entry_count):
        rel.plain(entries_address + index * 16, 8)
        address, padding = elf.unpack("<II", entry_offset + index * 16)
        _require(padding == 0 and address > previous_address and start <= (address & ~1) < end,
                 "invalid_or_unsorted_entry")
        _require(address & 1 or address % 4 == 0, "unaligned_guest_entry")
        code = rel.pointer(entries_address + index * 16 + 8)
        _require(code is not None, "null_entry_code")
        _, segment = elf.mapped(code, 1)
        _require(segment["flags"] & 1 and not segment["flags"] & 2
                 and (elf.machine != 183 or code % 4 == 0), "entry_code_permissions_or_alignment")
        owner = elf.unpack("<I", owner_offset + index * 4)[0]
        _require(owner < count, "entry_owner_out_of_range")
        spans, span_starts = function_spans[owner]
        position = bisect.bisect_right(span_starts, address & ~1) - 1
        _require(position >= 0 and (address & ~1) < spans[position][1],
                 "entry_outside_owner_origin")
        _require(owner_codes[owner] is None or owner_codes[owner] == code, "owner_has_different_code_pointers")
        _require(owner_modes[owner] is None or owner_modes[owner] == address & 1,
                 "owner_has_mixed_guest_modes")
        owner_codes[owner] = code
        owner_modes[owner] = address & 1
        owner_starts[owner] |= (address & ~1) == functions_data[owner][2]
        previous_address = address
    _require(all(owner_starts), "function_missing_start_entry")
    return {"name": expected["name"], "text_start": start, "text_bytes": len(text),
            "entry_count": entry_count, "function_count": count, "piece_count": piece_count,
            "entries_address": entries_address, "origins_address": origin_address,
            "stale_address": stale, "starts_address": starts, "base_address": base_address}


def audit_runtime_library(path, machine, preparation_sha256, contract_sha256, units):
    """CodexAstraUlt: Return bounded evidence; no code or dynamic loader runs."""
    _units(units)
    path = Path(path)
    before = _fingerprint(path)
    result = ELF.audit_library(path, machine, preparation_sha256, contract_sha256, len(units) - 1)
    _require(_fingerprint(path) == before, "library_changed_between_audits")
    with ELF._image(path, machine, 3) as elf:
        tags = ELF._dynamic(elf)
        symbols = elf.symbols(next(s for s in elf.sections if s["type"] == 11))
        _require(not any(symbol["type"] == 10 for symbol in symbols), "ifunc_symbol_unsupported")
        by_name = {symbol["name"]: symbol for symbol in symbols}
        relocations = _Relocations(elf, tags, symbols)
        tables = _Tables(elf, relocations)
        counts = []
        entries = by_name["recomp_entries"]["address"]
        modules = by_name["recomp_modules"]["address"]
        origins = by_name["recomp_origins"]["address"]
        module_offset = tables.region(modules, (len(units) - 1) * 32, 8, plain=False)
        for index, unit in enumerate(units):
            base = None
            if index == 0:
                entry_count = result["entry_count"]
            else:
                address = modules + (index - 1) * 32
                at = module_offset + (index - 1) * 32
                name = tables.string(relocations.pointer(address))
                _require(name == unit["name"], "module_name_or_order_mismatch")
                base = relocations.pointer(address + 8)
                _require(base is not None, "null_module_base")
                relocations.plain(address + 16, 8)
                size, entry_count = elf.unpack("<II", at + 16)
                _require(size == unit["text_start"] + len(unit["text"]), "module_text_extent_mismatch")
                entries = relocations.pointer(address + 24)
            counts.append(_unit(tables, unit, entries, entry_count, origins + index * 56, base))
        tables.finish()
        result.update(runtime_tables_validated=True, library_sha256=hashlib.sha256(elf.data).hexdigest(),
                      units=counts, metadata_elements=tables.elements,
                      guest_execution_performed=False, code_freshness_validated=False,
                      trusted_local_build_required=True)
    _require(_fingerprint(path) == before, "library_changed_between_audits")
    return result
