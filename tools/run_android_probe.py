#!/usr/bin/env python3
"""CodexAstraUlt: Run only the synthetic DroidDS probe on an explicitly selected device."""

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
import struct
import subprocess
import sys
import time
import uuid
import zipfile

PACKAGE = "org.droidds.probe"
REPORT_PATH = "files/latest-probe.json"
# CodexAstraUlt: Bound the original CPU report plus the new native Vulkan report
# and Android shell metadata without permitting an unbounded device read.
MAX_REPORT_BYTES = 1024 * 1024 + 64 * 1024 + 16 * 1024
CASES = {
    "arm_integer_memory": (11, 0, 0, 11),
    "thumb_integer_memory": (7, 0, 0, 7),
    "arm_missing_entry_fallback": (2, 3, 0, 5),
    "arm_to_thumb_native": (5, 0, 1, 5),
}
CONTROLS = {"nan_shaped_integer_register_mismatch", "nan_shaped_integer_memory_mismatch"}


def case_counters(work: int, fallback: int, lookup: int, interpreted: int,
                  calls: int = 1) -> dict[str, int]:
    """CodexAstraUlt: Share exact fixture accounting with build and release inventories."""
    return {"checkpoint_svc": 42, "native_calls": calls, "native_lookup_hits": lookup,
            "native_budget_charged": work, "fallback_steps": fallback,
            "instruction_callbacks": 0, "interpreter_steps": interpreted,
            "memory_bytes_compared": 65536}


# CodexAstraUlt: Version 0.0.4 exercises reverse interworking, narrow finite VFP,
# flags/shifts and a budget-too-small exit that must still make exact progress.
CASES_004 = {
    **{name: {**case_counters(*counts), "budget_exits": 0} for name, counts in CASES.items()},
    "arm_flags_shifts": {**case_counters(8, 0, 0, 8), "budget_exits": 0},
    "thumb_to_arm_native": {**case_counters(5, 0, 1, 5), "budget_exits": 0},
    "arm_vfp_finite": {**case_counters(7, 0, 0, 7), "budget_exits": 0},
    "arm_tiny_budget_progress": {**case_counters(1, 2, 0, 3, calls=2), "budget_exits": 1},
}


def cases_for_version(version: str) -> dict[str, dict[str, int]]:
    """CodexAstraUlt: Future APKs cannot silently inherit historical proof requirements."""
    if version == "0.0.4":
        return {name: dict(counters) for name, counters in CASES_004.items()}
    if version in ("0.0.2", "0.0.3"):
        return {name: case_counters(*counts) for name, counts in CASES.items()}
    raise ValueError("Unsupported Android probe report version")


def utc_now() -> str:
    """CodexAstraUlt: Keep host timestamps distinct from Android's own clock."""
    return datetime.now(timezone.utc).isoformat()


def integer(value: object, minimum: int = 0) -> bool:
    """CodexAstraUlt: JSON booleans must not qualify as measured integers."""
    return type(value) is int and value >= minimum


def validate_graphics_report(report: object) -> None:
    """CodexAstraUlt: Require measured Vulkan output; unavailable never means passed."""
    if not isinstance(report, dict):
        raise ValueError("Vulkan report must be an object")
    # CodexAstraUlt: Schema 2 extends the original pixel test with the pinned
    # renderer contract. Historical schema 1 remains independently reviewable.
    if type(report.get("schema")) is not int or report["schema"] not in (1, 2):
        raise ValueError("Missing or incorrect Vulkan proof: schema")
    required = {"kind": "droidds-vulkan-probe", "status": "passed",
                "width": 16, "height": 16, "required_cycles": 3, "cycles_completed": 3,
                "pipeline_creation_count": 3, "draw_count": 12}
    for key, expected in required.items():
        if type(report.get(key)) is not type(expected) or report[key] != expected:
            raise ValueError(f"Missing or incorrect Vulkan proof: {key}")
    if "error" not in report or report["error"] is not None:
        raise ValueError("Vulkan passed report must have no execution error")
    device = report.get("device")
    if not isinstance(device, dict):
        raise ValueError("Missing Vulkan physical device")
    name = device.get("name")
    if not isinstance(name, str) or not name.strip() or len(name.encode("utf-8")) >= 256:
        raise ValueError("Invalid Vulkan physical device name")
    for key in ("type", "api_version", "driver_version", "vendor_id", "device_id"):
        if not integer(device.get(key)) or device[key] > 0xffffffff:
            raise ValueError(f"Invalid Vulkan physical device field: {key}")
    # CodexAstraUlt: Accept actual hardware and software Vulkan devices so the
    # same output gate serves handheld and host tests; neither identifies a Thor.
    api = device["api_version"]
    if device["type"] > 4 or api >> 29 or ((api >> 22) & 0x7f) != 1:
        raise ValueError("Invalid Vulkan physical device type or API version")
    cases = report.get("cases")
    names = {"solid_red", "solid_green", "split_red_green"}
    if not isinstance(cases, list) or len(cases) != len(names):
        raise ValueError("Missing Vulkan output cases")
    actual_names = [case.get("name") if isinstance(case, dict) else None for case in cases]
    if any(not isinstance(name, str) for name in actual_names) or set(actual_names) != names:
        raise ValueError("Missing, duplicate or unknown Vulkan output cases")
    for case in cases:
        if case.get("status") != "passed":
            raise ValueError(f"Vulkan output case did not pass: {case['name']}")
        for key, expected in (("cycles_completed", 3), ("pixels_checked", 768),
                              ("mismatched_pixels", 0)):
            if type(case.get(key)) is not int or case[key] != expected:
                raise ValueError(f"Missing or incorrect Vulkan output proof: {case['name']}/{key}")
    controls = report.get("negative_controls")
    if not isinstance(controls, dict) or controls.get("pixel_mutation_rejected") is not True:
        raise ValueError("Vulkan pixel mutation did not prove comparator rejection")
    for key in ("checks_completed", "required_checks"):
        if type(controls.get(key)) is not int or controls[key] != 9:
            raise ValueError(f"Missing or incorrect Vulkan comparator control: {key}")
    if report["schema"] == 2:
        validate_renderer_report(report.get("renderer_probe"), device["api_version"])


def validate_renderer_report(report: object, api_version: int) -> None:
    """CodexAstraUlt: Feature discovery alone cannot qualify an unexecuted renderer."""
    if not isinstance(report, dict):
        raise ValueError("Missing renderer probe")
    required = {"schema": 1, "kind": "droidds-renderer-probe", "contract": "zakuro-412900a",
                "status": "passed", "width": 16, "height": 16,
                "pipeline_creation_count": 2, "draw_count": 5, "dispatch_count": 1,
                "readbacks_completed": 2, "pixels_checked": 512, "mismatched_pixels": 0,
                "compute_words_checked": 16, "compute_word_mismatches": 0,
                "negative_checks_completed": 3, "negative_controls_passed": True}
    for key, expected in required.items():
        if type(report.get(key)) is not type(expected) or report[key] != expected:
            raise ValueError(f"Missing or incorrect renderer proof: {key}")
    if "error" not in report or report["error"] is not None:
        raise ValueError("Renderer passed report must have no execution error")
    for key in ("instance_api_version", "physical_api_version"):
        value = report.get(key)
        if (not integer(value) or value > 0xffffffff or value >> 29 or
                ((value >> 22) & 0x7f) != 1 or value < (1 << 22 | 3 << 12)):
            raise ValueError(f"Renderer requires the measured Vulkan 1.3 API: {key}")
    if report["physical_api_version"] != api_version:
        raise ValueError("Renderer API differs from the measured Vulkan physical device")
    features = report.get("required")
    feature_names = {"vulkan_1_3", "graphics_compute_queue", "push_descriptor", "depth_clamp",
                     "d24s8_attachment", "rgba8_color_sample_transfer", "dynamic_rendering",
                     "synchronization2", "pipeline_creation_cache_control", "push_descriptor_limit"}
    if (not isinstance(features, dict) or set(features) != feature_names or
            any(value is not True for value in features.values())):
        raise ValueError("Missing or unsupported required renderer capability")
    if type(report.get("missing_required")) is not list or report["missing_required"]:
        raise ValueError("Renderer required capability list must be present and empty")
    optional = report.get("optional")
    optional_names = {"logic_op", "pipeline_statistics_query", "dynamic_blend", "dynamic_logic_op"}
    if (not isinstance(optional, dict) or set(optional) != optional_names or
            any(type(value) is not bool for value in optional.values())):
        raise ValueError("Missing or invalid optional renderer capability")
    for key, minimum, maximum in (("queue_family", 0, 0xfffffffe),
                                  ("max_push_descriptors", 8, 0xffffffff)):
        if not integer(report.get(key), minimum) or report[key] > maximum:
            raise ValueError(f"Invalid measured renderer capability: {key}")
    # CodexAstraUlt: Aggregate draw/readback counts cannot conceal one skipped
    # depth/stencil or depth-clamp case; each output has its own strict oracle.
    cases = report.get("cases")
    expected_cases = {"textured_depth_stencil": 4, "depth_clamp": 1}
    if not isinstance(cases, list) or len(cases) != len(expected_cases):
        raise ValueError("Missing renderer output cases")
    names = [case.get("name") if isinstance(case, dict) else None for case in cases]
    if any(not isinstance(name, str) for name in names) or set(names) != set(expected_cases):
        raise ValueError("Missing, duplicate or unknown renderer output cases")
    for case in cases:
        if case.get("status") != "passed":
            raise ValueError(f"Renderer output case did not pass: {case['name']}")
        for key, expected in (("pixels_checked", 256), ("mismatched_pixels", 0),
                              ("draw_count", expected_cases[case["name"]])):
            if type(case.get(key)) is not int or case[key] != expected:
                raise ValueError(f"Missing or incorrect renderer output proof: {case['name']}/{key}")


def validate_code_safety(report: object) -> None:
    """CodexAstraUlt: Immutable fixture code is enforced, not a claim of CRO invalidation."""
    if (not isinstance(report, dict) or report.get("status") != "passed" or
            report.get("policy") != "immutable_fixture_text"):
        raise ValueError("Missing or incorrect code safety policy proof")
    controls = report.get("controls")
    expected_controls = {
        "stale_origin_rejected": {},
        "changed_code_before_dispatch_rejected": {
            "native_calls": 0, "fallback_steps": 0, "guest_memory_unchanged": True},
        "guest_executable_write_rejected": {
            "native_calls": 1, "rejected_writes": 2, "guest_memory_unchanged": True},
    }
    if not isinstance(controls, list) or len(controls) != len(expected_controls):
        raise ValueError("Missing code safety controls")
    names = [item.get("name") if isinstance(item, dict) else None for item in controls]
    if any(not isinstance(name, str) for name in names) or set(names) != set(expected_controls):
        raise ValueError("Missing, duplicate or unknown code safety controls")
    for control in controls:
        name = control["name"]
        if control.get("status") != "passed":
            raise ValueError(f"Code safety control did not pass: {name}")
        for key, expected in expected_controls[name].items():
            if type(control.get(key)) is not type(expected) or control[key] != expected:
                raise ValueError(f"Missing or incorrect code safety control: {name}/{key}")
        if name == "stale_origin_rejected" and (
                not isinstance(control.get("rejection"), str) or not control["rejection"].strip()):
            raise ValueError("Stale code origin control did not prove rejection")
    limitations = report.get("limitations")
    if (not isinstance(limitations, list) or not limitations or
            any(not isinstance(item, str) or not item.strip() for item in limitations)):
        raise ValueError("Code safety proof must state its bounded fixture limitations")


def validate_report(report: object, request_id: str, manifest: dict) -> None:
    """CodexAstraUlt: Reject host/mock, stale, incomplete and unexercised execution proof."""
    if not isinstance(report, dict):
        raise ValueError("Probe report must be an object")
    required = {"schema": 1, "kind": "droidds-android-cpu-probe", "status": "passed",
                "host_arch": "aarch64", "host_os": "android", "pointer_bits": 64,
                "abi": 4, "generation": 3}
    for key, value in required.items():
        if type(report.get(key)) is not type(value) or report[key] != value:
            raise ValueError(f"Android probe identity/status mismatch: {key}")
    page_size = report.get("host_page_size")
    if not integer(page_size, 4096) or page_size > 65536 or page_size & (page_size - 1):
        raise ValueError("Missing or invalid actual Android page size")
    shell = report.get("android_shell")
    if not isinstance(shell, dict) or shell.get("request_id") != request_id:
        raise ValueError("Probe request_id is stale or missing")
    if type(shell.get("schema_version")) is not int or shell["schema_version"] != 1:
        raise ValueError("Unknown Android shell schema")
    try:
        if str(uuid.UUID(shell.get("run_id", ""))) != shell["run_id"]:
            raise ValueError("noncanonical UUID")
    except (ValueError, AttributeError, TypeError) as exc:
        raise ValueError("Invalid Android run_id") from exc
    for key in ("started_at_epoch_ms", "finished_at_epoch_ms", "process_id"):
        if not integer(shell.get(key), 1):
            raise ValueError(f"Missing Android execution identity: {key}")
    if shell["finished_at_epoch_ms"] < shell["started_at_epoch_ms"]:
        raise ValueError("Android execution timestamps are reversed")
    if (type(shell.get("app_version_code")) is not int or
            shell["app_version_code"] != manifest["version_code"] or
            shell.get("app_version_name") != manifest["version_name"] or
            report.get("version") != manifest["version_name"]):
        raise ValueError("Android report version differs from the installed APK")
    # CodexAstraUlt: Preserve historical CPU-only evidence without letting future
    # versions silently inherit an obsolete proof contract or omit the GPU run.
    expected_cases = cases_for_version(report["version"])
    if report["version"] in ("0.0.3", "0.0.4"):
        if report.get("cpu_status") != "passed":
            raise ValueError("Android CPU status did not pass")
        for key in ("manufacturer", "model", "android_release"):
            if not isinstance(shell.get(key), str) or not shell[key].strip():
                raise ValueError(f"Missing Android device identity: {key}")
        if not integer(shell.get("android_api"), 29):
            raise ValueError("Missing or unsupported Android API")
        if not integer(shell.get("elapsed_realtime_ms")):
            raise ValueError("Missing Android elapsed execution duration")
        graphics = report.get("graphics_probe")
        graphics_schema = 2 if report["version"] == "0.0.4" else 1
        if (not isinstance(graphics, dict) or type(graphics.get("schema")) is not int or
                graphics["schema"] != graphics_schema):
            raise ValueError("Vulkan report schema differs from the Android probe version")
        validate_graphics_report(graphics)
    cases = report.get("cases")
    if not isinstance(cases, list) or len(cases) != len(expected_cases):
        raise ValueError("Missing or unknown CPU cases")
    names = [case.get("name") if isinstance(case, dict) else None for case in cases]
    if any(not isinstance(name, str) for name in names) or set(names) != set(expected_cases):
        raise ValueError("Missing, duplicate or unknown CPU cases")
    for case in cases:
        counters = expected_cases[case["name"]]
        if case.get("status") != "passed":
            raise ValueError(f"CPU case failed: {case['name']}")
        if case.get("library") != f"libdds_fixture_{case['name']}.so":
            raise ValueError("CPU proof names an unexpected fixture library")
        for key, expected in counters.items():
            if type(case.get(key)) is not int or case[key] != expected:
                raise ValueError(f"Missing or incorrect CPU proof counter: {case['name']}/{key}")
        for key in ("strict_expected_match", "strict_interpreter_match", "route_counts_match"):
            if case.get(key) is not True:
                raise ValueError(f"Missing strict CPU proof: {case['name']}/{key}")
    if report["version"] == "0.0.4":
        validate_code_safety(report.get("code_safety"))
    controls = report.get("negative_controls")
    if not isinstance(controls, list) or len(controls) != len(CONTROLS):
        raise ValueError("Missing negative controls")
    names = [item.get("name") if isinstance(item, dict) else None for item in controls]
    if any(not isinstance(name, str) for name in names) or set(names) != CONTROLS:
        raise ValueError("Missing, duplicate or unknown negative controls")
    if any(item.get("status") != "passed" or not isinstance(item.get("rejection"), str)
           or not item["rejection"].strip() for item in controls):
        raise ValueError("Negative control did not prove rejection")


def apk_manifest(apk: Path, allow_prerelease: bool = False) -> dict:
    """CodexAstraUlt: Inspect Android binary XML before installing anything on a device.

    Only the bounded manifest identity is decoded. This avoids requiring the full
    Android SDK on the laptop and does not trust a separate JSON asset to identify
    the package installed by Android's package manager.
    """
    with zipfile.ZipFile(apk) as archive:
        entries = [item for item in archive.infolist() if item.filename == "AndroidManifest.xml"]
        if len(entries) != 1 or entries[0].file_size > MAX_REPORT_BYTES:
            raise ValueError("APK must contain one bounded AndroidManifest.xml")
        data = archive.read(entries[0])
    if len(data) < 8 or struct.unpack_from("<HHI", data) != (3, 8, len(data)):
        raise ValueError("Unsupported binary Android manifest")
    strings = None
    manifest = None
    application = None
    offset = 8
    while offset < len(data):
        if offset + 8 > len(data):
            raise ValueError("Truncated manifest chunk")
        kind, header, size = struct.unpack_from("<HHI", data, offset)
        if size < header or header < 8 or offset + size > len(data):
            raise ValueError("Invalid manifest chunk bounds")
        chunk = data[offset:offset + size]
        if kind == 1:
            if strings is not None or header < 28:
                raise ValueError("Invalid manifest string pool")
            count, style_count, flags, start, style_start = struct.unpack_from("<IIIII", chunk, 8)
            if (count > 20000 or header + 4 * (count + style_count) > start or
                    start > size or (style_start and not start <= style_start <= size)):
                raise ValueError("Invalid manifest string table bounds")
            strings = []
            string_end = style_start or size
            for index in range(count):
                position = start + struct.unpack_from("<I", chunk, header + 4 * index)[0]
                unit = 1 if flags & 0x100 else 2

                def length(pos: int) -> tuple[int, int]:
                    if pos + unit > string_end:
                        raise ValueError("Truncated manifest string length")
                    value = int.from_bytes(chunk[pos:pos + unit], "little")
                    pos += unit
                    mask = 0x80 if unit == 1 else 0x8000
                    if value & mask:
                        if pos + unit > string_end:
                            raise ValueError("Truncated extended manifest string length")
                        value = ((value & ~mask) << (8 * unit)) | int.from_bytes(chunk[pos:pos + unit], "little")
                        pos += unit
                    return value, pos

                length_chars, position = length(position)
                if unit == 1:
                    count_bytes, position = length(position)
                else:
                    count_bytes = length_chars * 2
                end = position + count_bytes
                if end + unit > string_end or chunk[end:end + unit] != bytes(unit):
                    raise ValueError("Truncated or unterminated manifest string")
                strings.append(chunk[position:end].decode("utf-8" if unit == 1 else "utf-16le"))
        elif kind == 0x102:
            if strings is None or header < 16 or header + 20 > size:
                raise ValueError("Invalid manifest element")
            _, name, attr_start, attr_size, attr_count = struct.unpack_from("<IIHHH", chunk, header)

            def string(index: int) -> str:
                if index >= len(strings):
                    raise ValueError("Invalid manifest string index")
                return strings[index]

            element = string(name)
            start = header + attr_start
            if attr_size < 20 or start < header + 20 or start + attr_size * attr_count > size:
                raise ValueError("Invalid manifest attribute bounds")
            attrs = {}
            for index in range(attr_count):
                pos = start + index * attr_size
                namespace, name, raw, value_size, reserved, value_type, value = struct.unpack_from("<IIIHBBI", chunk, pos)
                if value_size != 8 or reserved:
                    raise ValueError("Unsupported manifest attribute value")
                attr_name = string(name)
                namespace_name = "" if namespace == 0xffffffff else string(namespace)
                key = (namespace_name, attr_name)
                if key in attrs:
                    raise ValueError("Duplicate manifest attribute")
                if value_type == 3:
                    attrs[key] = string(value)
                elif value_type in (0x10, 0x11):
                    attrs[key] = value
                elif value_type == 0x12:
                    attrs[key] = bool(value)
                elif raw != 0xffffffff:
                    attrs[key] = string(raw)
            if element == "manifest":
                if manifest is not None:
                    raise ValueError("Duplicate manifest root")
                manifest = attrs
            elif element == "application":
                if application is not None:
                    raise ValueError("Duplicate manifest application")
                application = attrs
        offset += size
    android = "http://schemas.android.com/apk/res/android"
    if not manifest or manifest.get(("", "package")) != PACKAGE:
        raise ValueError(f"Only the {PACKAGE} APK may be installed by this tool")
    version_code = manifest.get((android, "versionCode"))
    version_name = manifest.get((android, "versionName"))
    if not integer(version_code, 1) or not isinstance(version_name, str) or not version_name:
        raise ValueError("APK needs literal versionCode and versionName")
    if not application or application.get((android, "debuggable")) is not True:
        raise ValueError("Probe APK must be debuggable for bounded run-as report retrieval")
    # CodexAstraUlt: The owner authorized a browser-installable prerelease.
    # Keep the package/debug guards; accepting that mode requires explicit scope.
    if application.get((android, "testOnly")) is not True and not allow_prerelease:
        raise ValueError("Probe APK must be marked testOnly; use --allow-prerelease for the published probe")
    return {"package": PACKAGE, "version_code": version_code, "version_name": version_name,
            "debuggable": True, "test_only": application.get((android, "testOnly")) is True}


def terminate_group(process: subprocess.Popen) -> None:
    """CodexAstraUlt: Timeouts and interruption reap the owned local ADB client tree."""
    try:
        os.killpg(process.pid, signal.SIGTERM)
    except ProcessLookupError:
        pass
    try:
        process.communicate(timeout=2)
    except subprocess.TimeoutExpired:
        try:
            os.killpg(process.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        process.communicate()


class Adb:
    """CodexAstraUlt: Every operation has an explicit serial, timeout and evidence."""

    def __init__(self, executable: str, serial: str, output: Path, steps: list):
        if not serial or any(char.isspace() or ord(char) < 32 for char in serial):
            raise ValueError("ADB serial must be one nonempty device identifier")
        self.prefix = [executable, "-s", serial]
        self.output = output
        self.steps = steps

    def run(self, name: str, args: list[str], timeout: float = 15,
            allow_failure: bool = False) -> str:
        command = self.prefix + args
        step = {"name": name, "command": command, "started_utc": utc_now(), "status": "failed"}
        self.steps.append(step)
        process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                   start_new_session=True)
        try:
            stdout, stderr = process.communicate(timeout=max(0.01, timeout))
        except (subprocess.TimeoutExpired, KeyboardInterrupt):
            terminate_group(process)
            step["status"] = "inconclusive"
            step["reason"] = "command timeout or interruption"
            raise RuntimeError(f"ADB {name} timed out or was interrupted") from None
        finally:
            step["finished_utc"] = utc_now()
        step["exit_code"] = process.returncode
        step["status"] = "passed" if process.returncode == 0 else "failed"
        # CodexAstraUlt: Only these fixed probe operations are captured; no general
        # logcat, screenshots, application directories or unrelated device logs.
        if len(stdout) > MAX_REPORT_BYTES or len(stderr) > MAX_REPORT_BYTES:
            raise RuntimeError(f"ADB {name} returned an oversized response")
        text = stdout.decode("utf-8", errors="strict")
        error = stderr.decode("utf-8", errors="replace")
        index = len(self.steps)
        log = self.output / f"{index:03d}-{name}.log"
        log.write_text(text + ("\n[stderr]\n" + error if error else ""), encoding="utf-8")
        step["log"] = log.name
        if process.returncode and not allow_failure:
            raise RuntimeError(f"ADB {name} failed ({process.returncode}); see {log.name}")
        return text if process.returncode == 0 else ""

    def remote(self, name: str, words: list[str], *, output: bool = False,
               timeout: float = 15, allow_failure: bool = False) -> str:
        # CodexAstraUlt: ADB invokes a remote shell even when the local process
        # uses argv. Quote every remote token instead of interpolating shell text.
        return self.run(name, ["exec-out" if output else "shell", shlex.join(words)],
                        timeout=timeout, allow_failure=allow_failure)


def execute_probe(adb: Adb, apk: Path, manifest: dict, evidence: dict,
                  timeout: float) -> dict:
    """CodexAstraUlt: Bind one nonce-tagged Android run to the exact installed APK."""
    if adb.run("device-state", ["get-state"]).strip() != "device":
        raise RuntimeError("Selected Android device is not connected and authorized")
    properties = {}
    for prop in ("ro.product.manufacturer", "ro.product.model", "ro.product.cpu.abi",
                 "ro.build.version.release", "ro.build.version.sdk", "ro.build.fingerprint"):
        properties[prop] = adb.remote("property-" + prop, ["getprop", prop]).strip()
    evidence["device_properties"] = properties
    if properties["ro.product.cpu.abi"] != "arm64-v8a":
        raise RuntimeError("This Android probe requires an actual arm64-v8a device")
    install = ["install", "-r"] + (["-t"] if manifest["test_only"] else []) + [str(apk)]
    try:
        result = adb.run("install", install, timeout=120)
        if not re.search(r"(?m)^Success\s*$", result):
            raise RuntimeError("ADB install did not report Success")
    except RuntimeError as exc:
        raise RuntimeError(f"{exc}. Do not uninstall or clear data automatically; "
                           "keep the existing signing identity and investigate the install error.") from exc
    paths = adb.remote("installed-apk-path", ["pm", "path", PACKAGE]).strip().splitlines()
    if len(paths) != 1 or not paths[0].startswith("package:/"):
        raise RuntimeError("Expected exactly one installed probe APK")
    installed = paths[0][len("package:"):]
    digest = adb.remote("installed-apk-sha256", ["sha256sum", installed], output=True).split()
    if not digest or not re.fullmatch(r"[a-fA-F0-9]{64}", digest[0]):
        raise RuntimeError("Cannot verify the installed probe APK SHA-256")
    evidence["installed_apk_sha256"] = digest[0].lower()
    if evidence["installed_apk_sha256"] != evidence["apk_sha256"]:
        raise RuntimeError("Installed APK SHA-256 differs from the supplied APK")
    claimed = False
    try:
        adb.remote("stop-before-run", ["am", "force-stop", PACKAGE])
        claimed = True
        adb.remote("remove-stale-report", ["run-as", PACKAGE, "rm", "-f", REPORT_PATH])
        evidence["launch_utc"] = utc_now()
        deadline = time.monotonic() + timeout
        adb.remote("launch", ["am", "start", "-W", "-n", PACKAGE + "/.ProbeActivity",
                              "--es", "request_id", evidence["request_id"]],
                   timeout=min(20, max(0.01, deadline - time.monotonic())))
        while time.monotonic() < deadline:
            raw = adb.remote("read-report", ["run-as", PACKAGE, "head", "-c",
                                            str(MAX_REPORT_BYTES + 1), REPORT_PATH], output=True,
                             timeout=min(5, max(0.01, deadline - time.monotonic())),
                             allow_failure=True)
            if raw:
                report = json.loads(raw)
                (adb.output / "android-probe.json").write_text(raw, encoding="utf-8")
                if not isinstance(report, dict):
                    raise ValueError("Android report is not an object")
                if report.get("android_shell", {}).get("request_id") != evidence["request_id"]:
                    raise ValueError("Android report has a stale or missing request_id")
                if report.get("status") != "running":
                    evidence["android_report"] = report
                    validate_report(report, evidence["request_id"], manifest)
                    return report
            time.sleep(min(0.5, max(0, deadline - time.monotonic())))
        raise RuntimeError("Android probe timed out without a complete passing report")
    finally:
        if claimed:
            adb.remote("stop-after-run", ["am", "force-stop", PACKAGE])


def interrupted(_signal: int, _frame) -> None:
    """CodexAstraUlt: Termination follows the same bounded cleanup as Ctrl-C."""
    raise KeyboardInterrupt("termination requested")


def main() -> int:
    """CodexAstraUlt: Keep all evidence local and refuse to overwrite earlier runs."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--serial", required=True, help="explicit serial from adb devices")
    parser.add_argument("--apk", type=Path, required=True, help="locally built synthetic probe APK")
    parser.add_argument("--output", type=Path, required=True, help="new local evidence directory")
    parser.add_argument("--allow-prerelease", action="store_true",
                        help="accept the browser-installable org.droidds.probe diagnostic APK")
    parser.add_argument("--timeout", type=float, default=60, help="probe deadline, 5–120 seconds")
    args = parser.parse_args()
    if sys.platform != "linux":
        parser.error("the local probe runner currently supports Linux")
    if not 5 <= args.timeout <= 120:
        parser.error("--timeout must be between 5 and 120 seconds")
    output = args.output.resolve()
    try:
        output.mkdir(parents=True, exist_ok=False)
    except OSError as exc:
        parser.error(f"--output must be a new writable directory: {exc}")
    signal.signal(signal.SIGTERM, interrupted)
    evidence = {"schema": 1, "kind": "droidds-android-device-run", "status": "failed",
                "started_utc": utc_now(), "request_id": str(uuid.uuid4()),
                "device_serial": args.serial, "steps": [], "device_execution_verified": False}
    try:
        source_apk = args.apk.resolve(strict=True)
        evidence["apk_path"] = str(source_apk)
        # CodexAstraUlt: Install the exact private snapshot we inspect and hash;
        # rebuilding the source APK concurrently cannot swap package identities.
        apk = output / "probe-under-test.apk"
        shutil.copyfile(source_apk, apk)
        with apk.open("rb") as artifact:
            evidence["apk_sha256"] = hashlib.file_digest(artifact, "sha256").hexdigest()
        manifest = apk_manifest(apk, allow_prerelease=args.allow_prerelease)
        evidence["apk_manifest"] = manifest
        executable = shutil.which("adb")
        if not executable:
            raise RuntimeError("Install Android platform-tools/adb on the connected Linux computer")
        adb = Adb(executable, args.serial, output, evidence["steps"])
        execute_probe(adb, apk, manifest, evidence, args.timeout)
        evidence["device_execution_verified"] = True
        evidence["status"] = "passed"
        print(f"Android probe passed on the selected device; evidence: {output}")
        return 0
    except (OSError, RuntimeError, ValueError, KeyError, TypeError, AttributeError,
            UnicodeError, zipfile.BadZipFile, struct.error, KeyboardInterrupt) as exc:
        evidence["error"] = str(exc)
        print(f"Android probe did not pass: {exc}", file=sys.stderr)
        return 1
    finally:
        evidence["finished_utc"] = utc_now()
        (output / "device-run.json").write_text(json.dumps(evidence, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    raise SystemExit(main())
