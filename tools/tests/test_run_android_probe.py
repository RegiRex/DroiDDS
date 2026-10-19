"""CodexAstraUlt: Reject misleading Android proof and unsafe device-run contracts."""

import copy
import importlib.util
import json
import os
from pathlib import Path
import shlex
import signal
import struct
import sys
import tempfile
import time
import unittest
from unittest import mock
import uuid
import zipfile

SPEC = importlib.util.spec_from_file_location(
    "run_android_probe", Path(__file__).parents[1] / "run_android_probe.py")
RUNNER = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(RUNNER)
REQUEST = "038443d8-40e4-4e83-a991-501702b37836"
MANIFEST = {"package": "org.droidds.probe", "version_code": 2, "version_name": "0.0.2",
            "debuggable": True, "test_only": True}


def report():
    """CodexAstraUlt: Protocol examples are unit-test inputs, never device evidence."""
    values = [("arm_integer_memory", 11, 0, 0, 11),
              ("thumb_integer_memory", 7, 0, 0, 7),
              ("arm_missing_entry_fallback", 2, 3, 0, 5),
              ("arm_to_thumb_native", 5, 0, 1, 5)]
    return {
        "schema": 1, "kind": "droidds-android-cpu-probe", "status": "passed",
        "version": "0.0.2", "host_arch": "aarch64", "host_os": "android", "pointer_bits": 64,
        "host_page_size": 4096, "abi": 4, "generation": 3,
        "android_shell": {"schema_version": 1, "request_id": REQUEST,
                          "run_id": "f8d9dc64-03a2-422d-a017-2f7849eeeb20", "process_id": 123,
                          "started_at_epoch_ms": 100, "finished_at_epoch_ms": 110,
                          "app_version_name": "0.0.2", "app_version_code": 2},
        "cases": [{"name": name, "library": f"libdds_fixture_{name}.so", "status": "passed",
                   "checkpoint_svc": 42, "native_calls": 1, "native_lookup_hits": lookup,
                   "native_budget_charged": work, "fallback_steps": fallback,
                   "instruction_callbacks": 0, "interpreter_steps": interpreted,
                   "memory_bytes_compared": 65536, "strict_expected_match": True,
                   "strict_interpreter_match": True, "route_counts_match": True}
                  for name, work, fallback, lookup, interpreted in values],
        "negative_controls": [{"name": name, "status": "passed", "rejection": "actual mismatch"}
                              for name in ("nan_shaped_integer_register_mismatch",
                                           "nan_shaped_integer_memory_mismatch")],
    }


def graphics_report():
    """CodexAstraUlt: Synthetic protocol values test validation, not GPU execution."""
    return {"schema": 1, "kind": "droidds-vulkan-probe", "status": "passed",
            "width": 16, "height": 16, "required_cycles": 3, "cycles_completed": 3,
            "pipeline_creation_count": 3, "draw_count": 12, "error": None,
            "device": {"name": "Protocol fixture device", "type": 1,
                       "api_version": 1 << 22, "driver_version": 1,
                       "vendor_id": 0x1234, "device_id": 0x5678},
            "cases": [{"name": name, "status": "passed", "cycles_completed": 3,
                       "pixels_checked": 768, "mismatched_pixels": 0}
                      for name in ("solid_red", "solid_green", "split_red_green")],
            "negative_controls": {"pixel_mutation_rejected": True,
                                  "checks_completed": 9, "required_checks": 9}}


def combined_report():
    """CodexAstraUlt: Version 0.0.3 must satisfy both existing CPU and new GPU gates."""
    value = report()
    value.update(version="0.0.3", cpu_status="passed", graphics_probe=graphics_report())
    value["android_shell"].update(app_version_name="0.0.3", app_version_code=3,
                                  manufacturer="Protocol fixture", model="Model fixture",
                                  android_api=29, android_release="10", elapsed_realtime_ms=0)
    manifest = dict(MANIFEST, version_name="0.0.3", version_code=3)
    return value, manifest


def renderer_report():
    """CodexAstraUlt: Explicit protocol fixtures cannot substitute for driver evidence."""
    return {"schema": 1, "kind": "droidds-renderer-probe", "contract": "zakuro-412900a",
            "status": "passed", "width": 16, "height": 16,
            "pipeline_creation_count": 2, "draw_count": 5, "dispatch_count": 1,
            "readbacks_completed": 2, "pixels_checked": 512, "mismatched_pixels": 0,
            "compute_words_checked": 16, "compute_word_mismatches": 0,
            "negative_checks_completed": 3, "negative_controls_passed": True, "error": None,
            "required": {"vulkan_1_3": True, "graphics_compute_queue": True,
                         "push_descriptor": True, "depth_clamp": True,
                         "d24s8_attachment": True, "rgba8_color_sample_transfer": True,
                         "dynamic_rendering": True, "synchronization2": True,
                         "pipeline_creation_cache_control": True, "push_descriptor_limit": True},
            "missing_required": [],
            "optional": {"logic_op": False, "pipeline_statistics_query": False,
                         "dynamic_blend": False, "dynamic_logic_op": False},
            "queue_family": 0, "max_push_descriptors": 8,
            "instance_api_version": 1 << 22 | 3 << 12,
            "physical_api_version": 1 << 22 | 3 << 12,
            "cases": [{"name": name, "status": "passed", "pixels_checked": 256,
                       "mismatched_pixels": 0, "draw_count": draws}
                      for name, draws in (("textured_depth_stencil", 4), ("depth_clamp", 1))]}


def renderer_graphics_report():
    """CodexAstraUlt: Schema 2 retains the old draws and adds independently checked work."""
    value = graphics_report()
    value.update(schema=2, renderer_probe=renderer_report())
    value["device"]["api_version"] = 1 << 22 | 3 << 12
    return value


def code_safety_report():
    """CodexAstraUlt: These synthetic proof values test rejection, never guest execution."""
    return {"status": "passed", "policy": "immutable_fixture_text", "controls": [
        {"name": "stale_origin_rejected", "status": "passed", "rejection": "origin mismatch"},
        {"name": "changed_code_before_dispatch_rejected", "status": "passed", "native_calls": 0,
         "fallback_steps": 0, "guest_memory_unchanged": True},
        {"name": "guest_executable_write_rejected", "status": "passed", "native_calls": 1,
         "rejected_writes": 2, "guest_memory_unchanged": True}],
        "limitations": ["Immutable synthetic fixture policy; dynamic code is not supported."]}


def current_report():
    """CodexAstraUlt: Independently state all 0.0.4 routes so counter drift fails tests."""
    value, _ = combined_report()
    value.update(version="0.0.4", graphics_probe=renderer_graphics_report(),
                 code_safety=code_safety_report())
    value["android_shell"].update(app_version_name="0.0.4", app_version_code=4)
    for case in value["cases"]:
        case["budget_exits"] = 0
    for name, calls, lookup, work, fallback, interpreted, budget_exits in (
            ("arm_flags_shifts", 1, 0, 8, 0, 8, 0),
            ("thumb_to_arm_native", 1, 1, 5, 0, 5, 0),
            ("arm_vfp_finite", 1, 0, 7, 0, 7, 0),
            ("arm_tiny_budget_progress", 2, 0, 1, 2, 3, 1)):
        value["cases"].append({"name": name, "library": f"libdds_fixture_{name}.so",
                               "status": "passed", "checkpoint_svc": 42,
                               "native_calls": calls, "native_lookup_hits": lookup,
                               "native_budget_charged": work, "fallback_steps": fallback,
                               "instruction_callbacks": 0, "interpreter_steps": interpreted,
                               "memory_bytes_compared": 65536, "budget_exits": budget_exits,
                               "strict_expected_match": True, "strict_interpreter_match": True,
                               "route_counts_match": True})
    return value, dict(MANIFEST, version_name="0.0.4", version_code=4)


def runtime_hardware_report():
    """CodexAstraUlt: Mutatable protocol input never substitutes for a Vulkan run."""
    return {"recorded_draws": 2, "submissions": 1, "draw_errors": 0,
            "software_raster_fallbacks": 0, "compiler_outstanding": 0, "compiler_peak": 16,
            "compiler_deferred": 3, "compiler_failures": 0, "retained_translations": 1,
            "retained_modules": 1, "retained_pipelines": 1, "retained_shader_bytes": 64,
            "max_compiler_outstanding": 16, "max_translations": 256,
            "max_shader_bytes": 8388608, "max_specialization_requests": 512,
            "max_pipelines": 512, "specialization_requests": 1, "resource_limit_events": 0,
            "dynamic_blend": False, "dynamic_logic_op": False,
            "vertex_shading_on_gpu": False, "last_error": None}


def runtime_report():
    """CodexAstraUlt: Independent protocol examples exercise gates, not emulator behavior."""
    records = []
    for name, new3ds, old_mode, new_mode, regions, limit, selector, model in (
            ("old3ds_64", False, 0, 0, [64, 44, 20], 64, 0, 0),
            ("old3ds_96", False, 2, 0, [96, 12, 20], 96, 2, 0),
            ("new3ds_legacy64", True, 0, 0, [124, 100, 32], 64, 6, 3),
            ("new3ds_124", True, 0, 1, [124, 100, 32], 124, 6, 3),
            ("new3ds_178", True, 0, 2, [178, 46, 32], 178, 7, 3)):
        records.append({"name": name, "status": "passed", "new3ds": new3ds,
                        "old_mode": old_mode, "new_mode": new_mode,
                        "physical_regions_bytes": [value * 1048576 for value in regions],
                        "application_limit_bytes": limit * 1048576,
                        "config_words": [selector, limit * 1048576,
                                         regions[1] * 1048576, regions[2] * 1048576],
                        "guest_model": model, "allocation_boundary_rejected": True,
                        "allocation_free_restored": True, "base_allocation_passed": True,
                        "guest_exited": True, "steps": 606})
    return {
        "schema": 1, "kind": "droidds-runtime-probe", "contract": "zakuro-412900a-runtime-v1",
        "status": "passed", "error": None, "fixture": "droidds-original-pica-ipc-v1",
        "native_library": "libdroidds_fixture_runtime.so", "pixel_comparisons": 2,
        "pixel_mutation_controls": 1, "memory_layouts": records,
        "cases": [{"name": name, "status": "passed", "guest_exited": True,
                   "error": None, "first_pixel_mismatches": [],
                   "checkpoint": 0x44534435, "fallback_checkpoint": 1, "guest_model": 0,
                   "command_lists": 1,
                   "draw_calls": 2, "vertices_drawn": 6, "pixels_checked": 64,
                   "mismatched_pixels": 0,
                   "interpreted_instructions": 606 if name == "interpreter_software" else 2,
                   "recompiled_instructions": 0 if name == "interpreter_software" else 604,
                   "native_fallback_instructions": 0,
                   "svc_unimplemented": 0, "service_unimplemented": 0, "memory_faults": 0,
                   "shader_program_words": 3,
                   "steps": 606 if name == "interpreter_software" else 10, "cycles": 606,
                   "services_seen": ["cfg:u", "gsp::Gpu"],
                   "hardware": runtime_hardware_report() if name == "native_vulkan" else None,
                   "hardware_device": "Protocol device at 1x" if name == "native_vulkan" else None}
                  for name in ("interpreter_software", "native_software", "native_vulkan")],
        "code_safety": {"status": "passed", "policy": "immutable_single_thread_fixture",
                        "controls": [
                            {"name": "stale_origin_rejected", "status": "passed",
                             "rejection": "origin mismatch", "native_instructions": 0},
                            {"name": "changed_code_before_dispatch_rejected", "status": "passed",
                             "rejection": "text mismatch", "native_instructions": 0,
                             "interpreted_instructions": 0},
                            {"name": "executable_guest_store_rejected", "status": "passed",
                             "native_instructions": 5, "rejected_writes": 1,
                             "code_unchanged": True}]},
        "limitations": ["Original bounded homebrew fixture; no retail execution evidence."],
    }


def integrated_report():
    """CodexAstraUlt: The 0.0.5 protocol retains every historical gate and adds runtime proof."""
    value, _ = current_report()
    value.update(version="0.0.5", runtime_probe=runtime_report())
    value["android_shell"].update(app_version_name="0.0.5", app_version_code=5)
    return value, dict(MANIFEST, version_name="0.0.5", version_code=5)


class RuntimeReportTests(unittest.TestCase):
    """CodexAstraUlt: Missing integration work cannot hide behind an overall pass label."""

    def test_complete_host_and_android_contracts_require_all_three_execution_routes(self):
        RUNNER.validate_runtime_report(runtime_report())
        value, manifest = integrated_report()
        RUNNER.validate_report(value, REQUEST, manifest)
        self.assertEqual(RUNNER.cases_for_version("0.0.5"), RUNNER.cases_for_version("0.0.4"))

    def test_android_runtime_gate_is_mandatory_without_weakening_retained_gates(self):
        for key in ("runtime_probe", "graphics_probe", "code_safety", "cpu_status"):
            value, manifest = integrated_report()
            del value[key]
            with self.subTest(missing=key), self.assertRaises(ValueError):
                RUNNER.validate_report(value, REQUEST, manifest)
        value, manifest = integrated_report()
        value["cases"] = report()["cases"]
        with self.assertRaisesRegex(ValueError, "CPU cases"):
            RUNNER.validate_report(value, REQUEST, manifest)
        value, manifest = integrated_report()
        value["graphics_probe"] = graphics_report()
        with self.assertRaisesRegex(ValueError, "schema differs"):
            RUNNER.validate_report(value, REQUEST, manifest)

    def test_exact_runtime_identity_counts_and_completed_status_are_required(self):
        for key in ("schema", "kind", "contract", "status", "fixture", "native_library",
                    "pixel_comparisons", "pixel_mutation_controls"):
            value = runtime_report()
            del value[key]
            with self.subTest(missing=key), self.assertRaisesRegex(ValueError, "runtime proof"):
                RUNNER.validate_runtime_report(value)
            value = runtime_report()
            value[key] = True if type(value[key]) is int else "not_run"
            with self.subTest(changed=key), self.assertRaisesRegex(ValueError, "runtime proof"):
                RUNNER.validate_runtime_report(value)
        for value in (None, {}, []):
            with self.subTest(value=value), self.assertRaises(ValueError):
                RUNNER.validate_runtime_report(value)

    def test_all_known_cases_must_execute_once_without_unknown_replacements(self):
        for cases in (None, [], [None] * 3, runtime_report()["cases"][:-1]):
            value = runtime_report()
            value["cases"] = cases
            with self.subTest(cases=cases), self.assertRaisesRegex(ValueError, "execution cases"):
                RUNNER.validate_runtime_report(value)
        for replacement in ("native_vulkan", "mock_vulkan"):
            value = runtime_report()
            value["cases"][0]["name"] = replacement
            with self.subTest(name=replacement), self.assertRaisesRegex(ValueError, "execution cases"):
                RUNNER.validate_runtime_report(value)

    def test_exact_render_hle_fault_and_checkpoint_counters_are_mandatory(self):
        for index in range(3):
            for key in ("checkpoint", "fallback_checkpoint", "guest_model", "command_lists", "draw_calls",
                        "vertices_drawn", "pixels_checked", "mismatched_pixels", "svc_unimplemented",
                        "service_unimplemented", "memory_faults", "shader_program_words"):
                for invalid in (None, True, runtime_report()["cases"][index][key] + 1):
                    value = runtime_report()
                    value["cases"][index][key] = invalid
                    with self.subTest(index=index, key=key, invalid=invalid), self.assertRaises(ValueError):
                        RUNNER.validate_runtime_report(value)
            for key, invalid in (("status", "not_run"), ("guest_exited", False), ("guest_exited", 1)):
                value = runtime_report()
                value["cases"][index][key] = invalid
                with self.subTest(index=index, key=key), self.assertRaises(ValueError):
                    RUNNER.validate_runtime_report(value)

    def test_native_interpreter_and_missing_entry_fallback_routes_are_observed(self):
        for index in range(3):
            for key in ("steps", "cycles", "interpreted_instructions",
                        "recompiled_instructions", "native_fallback_instructions"):
                requires_zero = key == "native_fallback_instructions" or (
                    index == 0 and key == "recompiled_instructions")
                invalid_values = (None, True, -1, 1) if requires_zero else (None, True, 0, -1, 100001)
                for invalid in invalid_values:
                    value = runtime_report()
                    value["cases"][index][key] = invalid
                    with self.subTest(index=index, key=key, invalid=invalid), self.assertRaises(ValueError):
                        RUNNER.validate_runtime_report(value)

    def test_fixed_guest_route_rejects_positive_counter_drift_and_budget_overcharge(self):
        for index, case in enumerate(runtime_report()["cases"]):
            for key in ("steps", "cycles", "interpreted_instructions", "recompiled_instructions"):
                value = runtime_report()
                value["cases"][index][key] = case[key] + 1
                with self.subTest(index=index, key=key), self.assertRaisesRegex(ValueError, "route proof"):
                    RUNNER.validate_runtime_report(value)
        value = runtime_report()
        value["cases"][1].update(cycles=1606, recompiled_instructions=1604)
        with self.assertRaisesRegex(ValueError, "route proof"):
            RUNNER.validate_runtime_report(value)
        for index in range(5):
            value = runtime_report()
            value["memory_layouts"][index]["steps"] = 605
            with self.subTest(layout=index), self.assertRaisesRegex(ValueError, "memory proof"):
                RUNNER.validate_runtime_report(value)

    def test_software_and_hardware_routes_cannot_substitute_for_each_other(self):
        value = runtime_report()
        value["cases"][2]["hardware"] = None
        with self.assertRaisesRegex(ValueError, "hardware diagnostics"):
            RUNNER.validate_runtime_report(value)
        for index in (0, 1):
            value = runtime_report()
            value["cases"][index]["hardware"] = runtime_hardware_report()
            with self.subTest(index=index), self.assertRaisesRegex(ValueError, "unexpected hardware"):
                RUNNER.validate_runtime_report(value)

    def test_required_services_gpu_identity_and_both_gpu_draws_are_observed(self):
        for services in (None, [], ["cfg:u", "cfg:u"], ["cfg:u", "mock"], ["cfg:u", 1]):
            for index in range(3):
                value = runtime_report()
                value["cases"][index]["services_seen"] = services
                with self.subTest(index=index, services=services), self.assertRaisesRegex(ValueError, "services"):
                    RUNNER.validate_runtime_report(value)
        for device in (None, "", " ", "x" * 1024, True):
            value = runtime_report()
            value["cases"][2]["hardware_device"] = device
            with self.subTest(device=device), self.assertRaisesRegex(ValueError, "device identity"):
                RUNNER.validate_runtime_report(value)
        for draws in (1, 3):
            value = runtime_report()
            value["cases"][2]["hardware"]["recorded_draws"] = draws
            with self.subTest(draws=draws), self.assertRaisesRegex(ValueError, "both fixture draws"):
                RUNNER.validate_runtime_report(value)

    def test_execution_error_and_narrow_proof_limitations_cannot_be_hidden(self):
        for invalid in ({}, False, "runtime panic"):
            value = runtime_report()
            value["error"] = invalid
            with self.subTest(error=invalid), self.assertRaisesRegex(ValueError, "execution error"):
                RUNNER.validate_runtime_report(value)
        value = runtime_report()
        del value["error"]
        with self.assertRaisesRegex(ValueError, "execution error"):
            RUNNER.validate_runtime_report(value)
        for invalid in (None, [], [""], [True], "complete support"):
            value = runtime_report()
            value["limitations"] = invalid
            with self.subTest(limitations=invalid), self.assertRaisesRegex(ValueError, "limitations"):
                RUNNER.validate_runtime_report(value)

    def test_each_runtime_case_has_no_error_or_sampled_pixel_differences(self):
        for index in range(3):
            for key in ("error", "first_pixel_mismatches"):
                value = runtime_report()
                del value["cases"][index][key]
                with self.subTest(index=index, missing=key), self.assertRaises(ValueError):
                    RUNNER.validate_runtime_report(value)
            for key, invalid in (("error", False), ("error", "device lost"),
                                 ("first_pixel_mismatches", None), ("first_pixel_mismatches", {}),
                                 ("first_pixel_mismatches", [{"index": 0}])):
                value = runtime_report()
                value["cases"][index][key] = invalid
                with self.subTest(index=index, key=key), self.assertRaises(ValueError):
                    RUNNER.validate_runtime_report(value)
    def test_runtime_guards_need_real_rejection_and_native_store_execution(self):
        for invalid in (None, {}, [], dict(runtime_report()["code_safety"], policy="all_dynamic_code")):
            value = runtime_report()
            value["code_safety"] = invalid
            with self.subTest(guards=invalid), self.assertRaisesRegex(ValueError, "code safety"):
                RUNNER.validate_runtime_report(value)
        for index in range(3):
            for key, original in runtime_report()["code_safety"]["controls"][index].items():
                value = runtime_report()
                del value["code_safety"]["controls"][index][key]
                with self.subTest(index=index, missing=key), self.assertRaises(ValueError):
                    RUNNER.validate_runtime_report(value)
                invalid = True if type(original) is int else "" if type(original) is str else 1
                value = runtime_report()
                value["code_safety"]["controls"][index][key] = invalid
                with self.subTest(index=index, key=key), self.assertRaises(ValueError):
                    RUNNER.validate_runtime_report(value)
        value = runtime_report()
        value["code_safety"]["controls"][2]["native_instructions"] = 0
        with self.assertRaisesRegex(ValueError, "did not execute native"):
            RUNNER.validate_runtime_report(value)

    def test_every_actual_loader_memory_layout_and_its_allocation_controls_are_required(self):
        for invalid in (None, [], [None] * 5, runtime_report()["memory_layouts"][:-1]):
            value = runtime_report()
            value["memory_layouts"] = invalid
            with self.subTest(layouts=invalid), self.assertRaisesRegex(ValueError, "memory layout"):
                RUNNER.validate_runtime_report(value)
        for index, original in enumerate(runtime_report()["memory_layouts"]):
            for key in original:
                value = runtime_report()
                del value["memory_layouts"][index][key]
                with self.subTest(index=index, missing=key), self.assertRaises(ValueError):
                    RUNNER.validate_runtime_report(value)
                if isinstance(original[key], list):
                    invalid = original[key][:-1]
                elif type(original[key]) is bool:
                    invalid = int(original[key])
                elif type(original[key]) is int:
                    invalid = True
                else:
                    invalid = "unexecuted"
                value = runtime_report()
                value["memory_layouts"][index][key] = invalid
                with self.subTest(index=index, key=key), self.assertRaises(ValueError):
                    RUNNER.validate_runtime_report(value)
        value = runtime_report()
        value["memory_layouts"][4] = copy.deepcopy(value["memory_layouts"][3])
        with self.assertRaisesRegex(ValueError, "memory layouts"):
            RUNNER.validate_runtime_report(value)

    def test_new3ds_legacy_commit_cap_is_distinct_from_the_physical_application_region(self):
        value = runtime_report()
        legacy = value["memory_layouts"][2]
        self.assertEqual(legacy["physical_regions_bytes"], [124 << 20, 100 << 20, 32 << 20])
        self.assertEqual(legacy["config_words"], [6, 64 << 20, 100 << 20, 32 << 20])
        RUNNER.validate_runtime_report(value)
        for key in ("application_limit_bytes", "config_words"):
            value = runtime_report()
            if key == "application_limit_bytes":
                value["memory_layouts"][2][key] = 124 << 20
            else:
                value["memory_layouts"][2][key][1] = 124 << 20
            with self.subTest(key=key), self.assertRaisesRegex(ValueError, "memory proof"):
                RUNNER.validate_runtime_report(value)


class RuntimeHardwareTests(unittest.TestCase):
    """CodexAstraUlt: A software result or unlimited cache cannot qualify Vulkan use."""

    def test_measured_static_pipeline_and_deferred_specialization_are_accepted(self):
        value = runtime_hardware_report()
        RUNNER.validate_runtime_hardware(value)
        value.update(retained_translations=0, retained_modules=0, retained_shader_bytes=0)
        RUNNER.validate_runtime_hardware(value)
        value.update(dynamic_blend=True, dynamic_logic_op=True, vertex_shading_on_gpu=True)
        RUNNER.validate_runtime_hardware(value)

    def test_draw_failure_software_fallback_and_resource_pressure_do_not_pass(self):
        for key in ("draw_errors", "software_raster_fallbacks", "compiler_failures",
                    "resource_limit_events"):
            for invalid in (None, False, 1):
                value = runtime_hardware_report()
                value[key] = invalid
                with self.subTest(key=key, invalid=invalid), self.assertRaises(ValueError):
                    RUNNER.validate_runtime_hardware(value)

    def test_admission_limits_are_fixed_instead_of_self_declared_unbounded_limits(self):
        for key in ("max_compiler_outstanding", "max_translations", "max_shader_bytes",
                    "max_specialization_requests", "max_pipelines"):
            for invalid in (None, True, 0, runtime_hardware_report()[key] + 1):
                value = runtime_hardware_report()
                value[key] = invalid
                with self.subTest(key=key, invalid=invalid), self.assertRaises(ValueError):
                    RUNNER.validate_runtime_hardware(value)

    def test_draws_submissions_and_live_pipeline_are_required(self):
        for key in ("recorded_draws", "submissions", "retained_pipelines"):
            for invalid in (None, True, 0, -1):
                value = runtime_hardware_report()
                value[key] = invalid
                with self.subTest(key=key, invalid=invalid), self.assertRaises(ValueError):
                    RUNNER.validate_runtime_hardware(value)

    def test_live_and_peak_resources_cannot_exceed_individual_or_related_bounds(self):
        for key, invalid in (("compiler_outstanding", 17), ("compiler_peak", 17),
                             ("retained_translations", 257), ("retained_modules", 2),
                             ("retained_pipelines", 513), ("retained_shader_bytes", 8388609),
                             ("specialization_requests", 513)):
            value = runtime_hardware_report()
            value[key] = invalid
            with self.subTest(key=key), self.assertRaisesRegex(ValueError, "exceeds its bound"):
                RUNNER.validate_runtime_hardware(value)
        value = runtime_hardware_report()
        value.update(compiler_peak=0, compiler_outstanding=1)
        with self.assertRaisesRegex(ValueError, "exceeds its bound"):
            RUNNER.validate_runtime_hardware(value)

    def test_every_counter_is_present_integer_and_not_negative_or_boolean(self):
        original = runtime_hardware_report()
        for key, count in original.items():
            if type(count) is not int:
                continue
            for invalid in (None, True, -1, "0"):
                value = runtime_hardware_report()
                value[key] = invalid
                with self.subTest(key=key, invalid=invalid), self.assertRaises(ValueError):
                    RUNNER.validate_runtime_hardware(value)
            value = runtime_hardware_report()
            del value[key]
            with self.subTest(missing=key), self.assertRaises(ValueError):
                RUNNER.validate_runtime_hardware(value)

    def test_optional_features_are_measured_booleans_and_error_is_present_and_null(self):
        for key in ("dynamic_blend", "dynamic_logic_op", "vertex_shading_on_gpu"):
            for invalid in (None, 0, 1, "false"):
                value = runtime_hardware_report()
                value[key] = invalid
                with self.subTest(key=key, invalid=invalid), self.assertRaises(ValueError):
                    RUNNER.validate_runtime_hardware(value)
        for invalid in ({}, "device lost", False):
            value = runtime_hardware_report()
            value["last_error"] = invalid
            with self.subTest(error=invalid), self.assertRaises(ValueError):
                RUNNER.validate_runtime_hardware(value)
        value = runtime_hardware_report()
        del value["last_error"]
        with self.assertRaisesRegex(ValueError, "execution error"):
            RUNNER.validate_runtime_hardware(value)


class ReportTests(unittest.TestCase):
    """CodexAstraUlt: Mutate proof independently so permissive acceptance is visible."""

    def reject(self, changed, message):
        with self.assertRaisesRegex(ValueError, message):
            RUNNER.validate_report(changed, REQUEST, MANIFEST)

    def test_complete_protocol_examples_qualify_only_their_observed_page_size(self):
        for size in (4096, 16384):
            value = report()
            value["host_page_size"] = size
            RUNNER.validate_report(value, REQUEST, MANIFEST)

    def test_host_reports_cannot_be_android_execution(self):
        for key, value in (("host_os", "linux"), ("host_arch", "x86_64"),
                           ("pointer_bits", 32), ("kind", "mock"), ("status", "running")):
            with self.subTest(key=key):
                changed = report()
                changed[key] = value
                self.reject(changed, "identity/status")

    def test_stale_or_missing_request_is_rejected(self):
        for value in (None, str(uuid.uuid4()), ""):
            changed = report()
            changed["android_shell"]["request_id"] = value
            self.reject(changed, "request_id")

    def test_abi_schema_and_generation_must_be_exact_integers(self):
        for key, value in (("schema", True), ("abi", 5), ("generation", "3")):
            changed = report()
            changed[key] = value
            self.reject(changed, "identity/status")

    def test_report_version_must_match_installed_apk(self):
        changed = report()
        changed["android_shell"]["app_version_code"] = 1
        self.reject(changed, "version")
        changed = report()
        changed["version"] = "0.0.1"
        self.reject(changed, "version")

    def test_unobserved_or_invalid_page_size_is_rejected(self):
        for page in (None, True, 0, 4097, 131072):
            changed = report()
            changed["host_page_size"] = page
            self.reject(changed, "page size")

    def test_partial_duplicate_and_unknown_cases_are_rejected(self):
        changed = report()
        changed["cases"].pop()
        self.reject(changed, "CPU cases")
        changed = report()
        changed["cases"][3] = copy.deepcopy(changed["cases"][0])
        self.reject(changed, "CPU cases")
        changed = report()
        changed["cases"][0]["name"] = "unvalidated_new_fixture"
        self.reject(changed, "CPU cases")

    def test_every_counter_is_required_and_native_fallback_routes_are_exact(self):
        for key in ("checkpoint_svc", "native_calls", "native_lookup_hits", "native_budget_charged",
                    "fallback_steps", "instruction_callbacks", "interpreter_steps", "memory_bytes_compared"):
            with self.subTest(counter=key):
                changed = report()
                del changed["cases"][0][key]
                self.reject(changed, "proof counter")
        for index, key, value in ((0, "native_calls", True), (0, "fallback_steps", 1),
                                  (2, "fallback_steps", 0), (3, "native_lookup_hits", 0),
                                  (1, "native_budget_charged", 0)):
            changed = report()
            changed["cases"][index][key] = value
            self.reject(changed, "proof counter")

    def test_strict_comparisons_cannot_be_missing_false_or_truthy_integers(self):
        for key in ("strict_expected_match", "strict_interpreter_match", "route_counts_match"):
            for value in (None, False, 1):
                changed = report()
                changed["cases"][0][key] = value
                self.reject(changed, "strict CPU proof")

    def test_negative_controls_must_exist_and_prove_rejection(self):
        changed = report()
        changed["negative_controls"].pop()
        self.reject(changed, "negative controls")
        changed = report()
        changed["negative_controls"][0]["rejection"] = ""
        self.reject(changed, "prove rejection")


class GraphicsReportTests(unittest.TestCase):
    """CodexAstraUlt: No skipped GPU, zero-work draw or broken oracle can qualify."""

    def test_complete_hardware_and_software_protocol_examples_are_accepted(self):
        for device_type in range(5):
            value = graphics_report()
            value["device"]["type"] = device_type
            RUNNER.validate_graphics_report(value)

    def test_missing_report_unavailable_failed_and_wrong_identity_are_rejected(self):
        for value in (None, [], {}):
            with self.subTest(value=value), self.assertRaises(ValueError):
                RUNNER.validate_graphics_report(value)
        for key, value in (("schema", True), ("schema", 3), ("kind", "mock"),
                           ("status", "unavailable"), ("status", "failed")):
            changed = graphics_report()
            changed[key] = value
            with self.subTest(key=key, value=value), self.assertRaisesRegex(ValueError, "Vulkan proof"):
                RUNNER.validate_graphics_report(changed)

    def test_every_work_counter_is_exact_and_cannot_be_a_boolean(self):
        for key in ("width", "height", "required_cycles", "cycles_completed",
                    "pipeline_creation_count", "draw_count"):
            for invalid in (None, True, 0, 10000):
                changed = graphics_report()
                changed[key] = invalid
                with self.subTest(key=key, invalid=invalid), self.assertRaisesRegex(ValueError, "Vulkan proof"):
                    RUNNER.validate_graphics_report(changed)
            changed = graphics_report()
            del changed[key]
            with self.subTest(missing=key), self.assertRaises(ValueError):
                RUNNER.validate_graphics_report(changed)

    def test_pass_cannot_coexist_with_missing_or_present_execution_error(self):
        changed = graphics_report()
        del changed["error"]
        with self.assertRaisesRegex(ValueError, "execution error"):
            RUNNER.validate_graphics_report(changed)
        for error in ({"step": "vkQueueSubmit", "vk_result": -4}, {}, False):
            changed = graphics_report()
            changed["error"] = error
            with self.subTest(error=error), self.assertRaisesRegex(ValueError, "execution error"):
                RUNNER.validate_graphics_report(changed)

    def test_actual_device_fields_are_required_and_bounded(self):
        changed = graphics_report()
        changed["device"] = None
        with self.assertRaisesRegex(ValueError, "physical device"):
            RUNNER.validate_graphics_report(changed)
        for name in (None, "", "   ", "x" * 256, "é" * 128):
            changed = graphics_report()
            changed["device"]["name"] = name
            with self.subTest(name=name), self.assertRaisesRegex(ValueError, "device name"):
                RUNNER.validate_graphics_report(changed)
        for key in ("type", "api_version", "driver_version", "vendor_id", "device_id"):
            for invalid in (None, True, -1, 0x100000000, "1"):
                changed = graphics_report()
                changed["device"][key] = invalid
                with self.subTest(key=key, invalid=invalid), self.assertRaisesRegex(ValueError, "device field"):
                    RUNNER.validate_graphics_report(changed)
        for key, value in (("type", 5), ("api_version", 0), ("api_version", (1 << 22) - 1),
                           ("api_version", (1 << 29) | (1 << 22)), ("api_version", 2 << 22)):
            changed = graphics_report()
            changed["device"][key] = value
            with self.subTest(key=key, value=value), self.assertRaisesRegex(ValueError, "type or API"):
                RUNNER.validate_graphics_report(changed)

    def test_missing_unknown_and_duplicate_output_cases_are_rejected(self):
        variants = [[], [None] * 3, graphics_report()["cases"][:-1]]
        duplicate = graphics_report()["cases"]
        duplicate[2] = copy.deepcopy(duplicate[0])
        variants.append(duplicate)
        unknown = graphics_report()["cases"]
        unknown[0]["name"] = "unmeasured_texture_case"
        variants.append(unknown)
        for cases in variants:
            changed = graphics_report()
            changed["cases"] = cases
            with self.subTest(cases=cases), self.assertRaisesRegex(ValueError, "output cases"):
                RUNNER.validate_graphics_report(changed)

    def test_each_pattern_requires_all_pixels_and_cycles_and_zero_mismatches(self):
        for case_index in range(3):
            for key, value in (("cycles_completed", 0), ("cycles_completed", True),
                               ("pixels_checked", 0), ("pixels_checked", 767),
                               ("mismatched_pixels", False), ("mismatched_pixels", 1)):
                changed = graphics_report()
                changed["cases"][case_index][key] = value
                with self.subTest(case=case_index, key=key, value=value), \
                        self.assertRaisesRegex(ValueError, "Vulkan output proof"):
                    RUNNER.validate_graphics_report(changed)
            for key in ("status", "cycles_completed", "pixels_checked", "mismatched_pixels"):
                changed = graphics_report()
                del changed["cases"][case_index][key]
                with self.subTest(case=case_index, missing=key), self.assertRaises(ValueError):
                    RUNNER.validate_graphics_report(changed)
            for status in ("failed", "incomplete"):
                changed = graphics_report()
                changed["cases"][case_index]["status"] = status
                with self.subTest(case=case_index, status=status), self.assertRaises(ValueError):
                    RUNNER.validate_graphics_report(changed)

    def test_comparator_must_reject_real_pixel_mutations_in_every_pattern_and_cycle(self):
        for controls in (None, [], {}, {"pixel_mutation_rejected": True}):
            changed = graphics_report()
            changed["negative_controls"] = controls
            with self.subTest(controls=controls), self.assertRaises(ValueError):
                RUNNER.validate_graphics_report(changed)
        for key, value in (("pixel_mutation_rejected", False), ("pixel_mutation_rejected", 1),
                           ("checks_completed", 8), ("checks_completed", True),
                           ("required_checks", 0), ("required_checks", "9")):
            changed = graphics_report()
            changed["negative_controls"][key] = value
            with self.subTest(key=key, value=value), self.assertRaisesRegex(ValueError, "comparator"):
                RUNNER.validate_graphics_report(changed)

    def test_combined_version_requires_both_cpu_and_vulkan_and_identified_android(self):
        value, manifest = combined_report()
        RUNNER.validate_report(value, REQUEST, manifest)
        for key in ("cpu_status", "graphics_probe"):
            changed, manifest = combined_report()
            del changed[key]
            with self.subTest(missing=key), self.assertRaises(ValueError):
                RUNNER.validate_report(changed, REQUEST, manifest)
        for key, invalid in (("manufacturer", ""), ("model", None), ("android_release", " "),
                             ("android_api", 28), ("android_api", True),
                             ("elapsed_realtime_ms", -1), ("elapsed_realtime_ms", True)):
            changed, manifest = combined_report()
            changed["android_shell"][key] = invalid
            with self.subTest(key=key, invalid=invalid), self.assertRaises(ValueError):
                RUNNER.validate_report(changed, REQUEST, manifest)
        changed, manifest = combined_report()
        changed["cases"][0]["strict_expected_match"] = False
        with self.assertRaisesRegex(ValueError, "strict CPU proof"):
            RUNNER.validate_report(changed, REQUEST, manifest)

    def test_unknown_version_does_not_silently_reuse_historical_cpu_only_contract(self):
        changed = report()
        changed["version"] = "0.0.6"
        changed["android_shell"].update(app_version_name="0.0.6", app_version_code=6)
        manifest = dict(MANIFEST, version_name="0.0.6", version_code=6)
        with self.assertRaisesRegex(ValueError, "Unsupported Android probe report version"):
            RUNNER.validate_report(changed, REQUEST, manifest)


class RendererReportTests(unittest.TestCase):
    """CodexAstraUlt: Reject advertised support without exact representative execution."""

    def reject(self, value, message="renderer|Renderer"):
        with self.assertRaisesRegex(ValueError, message):
            RUNNER.validate_graphics_report(value)

    def test_complete_renderer_contract_accepts_missing_optional_capabilities(self):
        for optional_support in (False, True):
            value = renderer_graphics_report()
            value["renderer_probe"]["optional"] = dict.fromkeys(
                value["renderer_probe"]["optional"], optional_support)
            RUNNER.validate_graphics_report(value)

    def test_new_graphics_schema_requires_actual_renderer_report(self):
        value = renderer_graphics_report()
        del value["renderer_probe"]
        self.reject(value)
        for missing in (None, {}, []):
            value = renderer_graphics_report()
            value["renderer_probe"] = missing
            self.reject(value)

    def test_identity_and_passing_status_are_exact(self):
        for key, invalid in (("schema", True), ("schema", 2), ("kind", "mock"),
                             ("contract", "unreviewed"), ("status", "unsupported"),
                             ("status", "failed"), ("status", "not_run")):
            value = renderer_graphics_report()
            value["renderer_probe"][key] = invalid
            with self.subTest(key=key, invalid=invalid):
                self.reject(value, "renderer proof")

    def test_required_capabilities_cannot_be_omitted_false_or_truthy(self):
        for key in renderer_report()["required"]:
            value = renderer_graphics_report()
            del value["renderer_probe"]["required"][key]
            with self.subTest(missing=key):
                self.reject(value, "required renderer capability")
            for invalid in (None, False, 1, "true"):
                value = renderer_graphics_report()
                value["renderer_probe"]["required"][key] = invalid
                with self.subTest(key=key, invalid=invalid):
                    self.reject(value, "required renderer capability")
        value = renderer_graphics_report()
        value["renderer_probe"]["required"]["unreviewed_feature"] = True
        self.reject(value, "required renderer capability")

    def test_missing_requirement_inventory_is_required_and_empty(self):
        for invalid in (None, {}, "", ["depth_clamp"]):
            value = renderer_graphics_report()
            value["renderer_probe"]["missing_required"] = invalid
            with self.subTest(invalid=invalid):
                self.reject(value, "capability list")
        value = renderer_graphics_report()
        del value["renderer_probe"]["missing_required"]
        self.reject(value, "capability list")

    def test_optional_capabilities_need_observed_booleans_without_being_required(self):
        for key in renderer_report()["optional"]:
            value = renderer_graphics_report()
            del value["renderer_probe"]["optional"][key]
            with self.subTest(missing=key):
                self.reject(value, "optional renderer capability")
            for invalid in (None, 0, "false"):
                value = renderer_graphics_report()
                value["renderer_probe"]["optional"][key] = invalid
                with self.subTest(key=key, invalid=invalid):
                    self.reject(value, "optional renderer capability")

    def test_measured_api_descriptor_limit_and_queue_cannot_contradict_support(self):
        value = renderer_graphics_report()
        value["device"]["api_version"] = 1 << 22 | 2 << 12
        self.reject(value, "API differs")
        for key in ("instance_api_version", "physical_api_version"):
            for invalid in (None, True, 1 << 22 | 2 << 12, 2 << 22, 1 << 29 | 1 << 22 | 3 << 12):
                value = renderer_graphics_report()
                value["renderer_probe"][key] = invalid
                with self.subTest(key=key, invalid=invalid):
                    self.reject(value, "Vulkan 1.3")
        for key, invalid in (("queue_family", True), ("queue_family", -1),
                             ("queue_family", 0xffffffff), ("max_push_descriptors", 7),
                             ("max_push_descriptors", True), ("max_push_descriptors", 1 << 32)):
            value = renderer_graphics_report()
            value["renderer_probe"][key] = invalid
            with self.subTest(key=key, invalid=invalid):
                self.reject(value, "measured renderer capability")

    def test_each_work_counter_is_exact_and_cannot_be_missing_or_a_boolean(self):
        keys = ("width", "height", "pipeline_creation_count", "draw_count", "dispatch_count",
                "readbacks_completed", "pixels_checked", "mismatched_pixels",
                "compute_words_checked", "compute_word_mismatches", "negative_checks_completed")
        for key in keys:
            value = renderer_graphics_report()
            del value["renderer_probe"][key]
            with self.subTest(missing=key):
                self.reject(value, "renderer proof")
            for invalid in (None, True, renderer_report()[key] + 1):
                value = renderer_graphics_report()
                value["renderer_probe"][key] = invalid
                with self.subTest(key=key, invalid=invalid):
                    self.reject(value, "renderer proof")

    def test_error_and_negative_controls_cannot_hide_behind_passed_status(self):
        for invalid in (None, False, 1, "true"):
            value = renderer_graphics_report()
            value["renderer_probe"]["negative_controls_passed"] = invalid
            with self.subTest(control=invalid):
                self.reject(value, "renderer proof")
        value = renderer_graphics_report()
        del value["renderer_probe"]["error"]
        self.reject(value, "execution error")
        for error in ({"step": "vkCreateGraphicsPipelines", "vk_result": -4}, {}, False):
            value = renderer_graphics_report()
            value["renderer_probe"]["error"] = error
            with self.subTest(error=error):
                self.reject(value, "execution error")


    def test_unknown_duplicate_missing_and_unexecuted_renderer_cases_are_rejected(self):
        variants = [[], [None, None], renderer_report()["cases"][:-1]]
        duplicate = renderer_report()["cases"]
        duplicate[1] = copy.deepcopy(duplicate[0])
        variants.append(duplicate)
        unknown = renderer_report()["cases"]
        unknown[0]["name"] = "unvalidated_new_case"
        variants.append(unknown)
        for cases in variants:
            value = renderer_graphics_report()
            value["renderer_probe"]["cases"] = cases
            with self.subTest(cases=cases):
                self.reject(value, "renderer output cases")
        for case_index in range(2):
            for key in ("status", "pixels_checked", "mismatched_pixels", "draw_count"):
                value = renderer_graphics_report()
                del value["renderer_probe"]["cases"][case_index][key]
                with self.subTest(case=case_index, missing=key):
                    self.reject(value)
            for key, invalid in (("status", "not_run"), ("pixels_checked", 255),
                                 ("pixels_checked", True), ("mismatched_pixels", 1),
                                 ("mismatched_pixels", False), ("draw_count", 0)):
                value = renderer_graphics_report()
                value["renderer_probe"]["cases"][case_index][key] = invalid
                with self.subTest(case=case_index, key=key, invalid=invalid):
                    self.reject(value)


class CurrentReportTests(unittest.TestCase):
    """CodexAstraUlt: Expanded CPU and renderer gates are mandatory only for 0.0.4."""

    def reject(self, value, message):
        _, manifest = current_report()
        with self.assertRaisesRegex(ValueError, message):
            RUNNER.validate_report(value, REQUEST, manifest)

    def test_complete_current_protocol_passes_all_eight_routes_and_three_safety_controls(self):
        value, manifest = current_report()
        RUNNER.validate_report(value, REQUEST, manifest)
        self.assertEqual(len(value["cases"]), 8)
        self.assertEqual(len(value["code_safety"]["controls"]), 3)

    def test_historical_cpu_cases_or_graphics_schema_cannot_qualify_current_build(self):
        value, _ = current_report()
        value["cases"] = report()["cases"]
        self.reject(value, "CPU cases")
        value, _ = current_report()
        value["graphics_probe"] = graphics_report()
        self.reject(value, "schema differs")
        value, manifest = combined_report()
        value["graphics_probe"] = renderer_graphics_report()
        with self.assertRaisesRegex(ValueError, "schema differs"):
            RUNNER.validate_report(value, REQUEST, manifest)

    def test_each_case_requires_exact_route_and_budget_counters(self):
        for index, original in enumerate(current_report()[0]["cases"]):
            for key in ("native_calls", "native_lookup_hits", "native_budget_charged",
                        "fallback_steps", "instruction_callbacks", "interpreter_steps",
                        "memory_bytes_compared", "budget_exits"):
                for invalid in (True, original[key] + 1, None):
                    value, _ = current_report()
                    value["cases"][index][key] = invalid
                    with self.subTest(case=original["name"], key=key, invalid=invalid):
                        self.reject(value, "CPU proof counter")
                value, _ = current_report()
                del value["cases"][index][key]
                with self.subTest(case=original["name"], missing=key):
                    self.reject(value, "CPU proof counter")

    def test_duplicate_unknown_and_incomplete_new_cpu_cases_do_not_pass(self):
        value, _ = current_report()
        value["cases"].pop()
        self.reject(value, "CPU cases")
        value, _ = current_report()
        value["cases"][7] = copy.deepcopy(value["cases"][6])
        self.reject(value, "CPU cases")
        value, _ = current_report()
        value["cases"][7]["name"] = "unreviewed_budget_route"
        self.reject(value, "CPU cases")
        for index in range(4, 8):
            for key in ("strict_expected_match", "strict_interpreter_match", "route_counts_match"):
                value, _ = current_report()
                value["cases"][index][key] = 1
                with self.subTest(case=index, key=key):
                    self.reject(value, "strict CPU proof")

    def test_fixture_inventory_is_version_specific_and_caller_cannot_mutate_shared_contract(self):
        self.assertEqual(set(RUNNER.cases_for_version("0.0.2")), set(RUNNER.CASES))
        self.assertEqual(set(RUNNER.cases_for_version("0.0.3")), set(RUNNER.CASES))
        current = RUNNER.cases_for_version("0.0.4")
        self.assertEqual(set(current), {item["name"] for item in current_report()[0]["cases"]})
        current["arm_tiny_budget_progress"]["native_calls"] = 99
        self.assertEqual(RUNNER.cases_for_version("0.0.4")["arm_tiny_budget_progress"]["native_calls"], 2)
        with self.assertRaisesRegex(ValueError, "Unsupported Android probe"):
            RUNNER.cases_for_version("0.0.6")

    def test_missing_failed_or_unreviewed_code_policy_does_not_pass(self):
        value, _ = current_report()
        del value["code_safety"]
        self.reject(value, "code safety policy")
        for key, invalid in (("status", "failed"), ("policy", "dynamic_code_supported")):
            value, _ = current_report()
            value["code_safety"][key] = invalid
            with self.subTest(key=key):
                self.reject(value, "code safety policy")

    def test_code_safety_requires_every_exact_control_and_rejection(self):
        variants = [[], [None] * 3, code_safety_report()["controls"][:-1]]
        duplicate = code_safety_report()["controls"]
        duplicate[2] = copy.deepcopy(duplicate[1])
        variants.append(duplicate)
        unknown = code_safety_report()["controls"]
        unknown[0]["name"] = "unvalidated_code_mutation"
        variants.append(unknown)
        for controls in variants:
            value, _ = current_report()
            value["code_safety"]["controls"] = controls
            with self.subTest(controls=controls):
                self.reject(value, "code safety controls")
        for invalid in (None, "", " ", True):
            value, _ = current_report()
            value["code_safety"]["controls"][0]["rejection"] = invalid
            with self.subTest(rejection=invalid):
                self.reject(value, "prove rejection")

    def test_code_safety_counters_and_memory_preservation_cannot_be_omitted_or_faked(self):
        for index in range(3):
            value, _ = current_report()
            value["code_safety"]["controls"][index]["status"] = "failed"
            self.reject(value, "did not pass")
        for index, keys in ((1, ("native_calls", "fallback_steps", "guest_memory_unchanged")),
                            (2, ("native_calls", "rejected_writes", "guest_memory_unchanged"))):
            for key in keys:
                value, _ = current_report()
                del value["code_safety"]["controls"][index][key]
                with self.subTest(control=index, missing=key):
                    self.reject(value, "code safety control")
                original = code_safety_report()["controls"][index][key]
                invalid_values = (None, 1, False) if type(original) is bool else (None, True, original + 1)
                for invalid in invalid_values:
                    value, _ = current_report()
                    value["code_safety"]["controls"][index][key] = invalid
                    with self.subTest(control=index, key=key, invalid=invalid):
                        self.reject(value, "code safety control")

    def test_code_safety_limitations_remain_part_of_its_narrow_proof(self):
        for invalid in (None, [], "supported", [""], [True]):
            value, _ = current_report()
            value["code_safety"]["limitations"] = invalid
            with self.subTest(limitations=invalid):
                self.reject(value, "bounded fixture limitations")


def binary_manifest(package="org.droidds.probe", debuggable=True, test_only=True, utf8=True,
                    version_name="0.0.2", version_code=2):
    """CodexAstraUlt: Minimal original binary XML exercises actual package decoding."""
    strings = ["manifest", "application", "package", package,
               "http://schemas.android.com/apk/res/android", "versionCode", "versionName",
               version_name, "debuggable", "testOnly"]
    data = bytearray()
    offsets = []
    for text in strings:
        offsets.append(len(data))
        encoded = text.encode("utf-8" if utf8 else "utf-16le")
        if utf8:
            data.extend(bytes([len(text), len(encoded)]) + encoded + b"\x00")
        else:
            data.extend(struct.pack("<H", len(text)) + encoded + b"\x00\x00")
    data.extend(b"\x00" * (-len(data) % 4))
    start = 28 + 4 * len(strings)
    pool = struct.pack("<HHIIIIII", 1, 28, start + len(data), len(strings), 0,
                       0x100 if utf8 else 0, start, 0)
    pool += struct.pack("<" + "I" * len(offsets), *offsets) + data

    def element(name, attrs):
        result = struct.pack("<HHIII", 0x102, 16, 36 + len(attrs) * 20, 1, 0xffffffff)
        result += struct.pack("<IIHHHHHH", 0xffffffff, name, 20, 20, len(attrs), 0, 0, 0)
        for namespace, name, value_type, value in attrs:
            result += struct.pack("<IIIHBBI", namespace, name, 0xffffffff, 8, 0, value_type, value)
        return result

    # CodexAstraUlt: Release tests can bind the actual binary manifest version
    # without replacing the historical 0.0.2 package-decoding fixture.
    contents = pool + element(0, [(0xffffffff, 2, 3, 3), (4, 5, 0x10, version_code), (4, 6, 3, 7)])
    contents += element(1, [(4, 8, 0x12, int(debuggable)), (4, 9, 0x12, int(test_only))])
    return struct.pack("<HHI", 3, 8, 8 + len(contents)) + contents


class ManifestTests(unittest.TestCase):
    """CodexAstraUlt: Package restrictions apply before any device mutation."""

    def decode(self, content, allow_prerelease=False):
        with tempfile.TemporaryDirectory() as temp:
            apk = Path(temp) / "fixture.apk"
            with zipfile.ZipFile(apk, "w") as archive:
                archive.writestr("AndroidManifest.xml", content)
            return RUNNER.apk_manifest(apk, allow_prerelease=allow_prerelease)

    def test_utf8_and_utf16_android_string_pools(self):
        for utf8 in (True, False):
            self.assertEqual(self.decode(binary_manifest(utf8=utf8)), MANIFEST)

    def test_another_package_cannot_be_installed(self):
        with self.assertRaisesRegex(ValueError, "Only the org.droidds.probe"):
            self.decode(binary_manifest(package="org.example.private"))

    def test_non_debug_and_non_test_apks_are_rejected(self):
        for options in ({"debuggable": False}, {"test_only": False}):
            with self.assertRaisesRegex(ValueError, "debuggable|testOnly"):
                self.decode(binary_manifest(**options))

    def test_published_probe_requires_explicit_prerelease_scope(self):
        decoded = self.decode(binary_manifest(test_only=False), allow_prerelease=True)
        self.assertFalse(decoded["test_only"])
        self.assertEqual(decoded["package"], "org.droidds.probe")
        self.assertTrue(decoded["debuggable"])
        for options in ({"package": "another.app"}, {"debuggable": False}):
            with self.assertRaises(ValueError):
                self.decode(binary_manifest(test_only=False, **options), allow_prerelease=True)

    def test_truncated_and_malformed_manifests_are_rejected(self):
        good = binary_manifest()
        malformed = bytearray(good)
        struct.pack_into("<I", malformed, 12, 0xffffffff)
        for content in (good[:-1], b"<manifest package='org.droidds.probe'/>", malformed):
            with self.subTest(length=len(content)), self.assertRaises(ValueError):
                self.decode(content)


class FakeAdb:
    """CodexAstraUlt: Record a simulated command boundary without touching a device."""

    def __init__(self, output, result=None, installed_sha="a" * 64, install_failure=False):
        self.output = output
        self.commands = []
        self.result = result or report()
        self.installed_sha = installed_sha
        self.install_failure = install_failure

    def run(self, name, args, **kwargs):
        self.commands.append((name, args))
        if name == "device-state":
            return "device\n"
        if name == "install":
            if self.install_failure:
                raise RuntimeError("INSTALL_FAILED_UPDATE_INCOMPATIBLE")
            return "Success\n"
        raise AssertionError(name)

    def remote(self, name, words, **kwargs):
        self.commands.append((name, words))
        if name.startswith("property-"):
            return "arm64-v8a\n" if words[-1] == "ro.product.cpu.abi" else "test-protocol\n"
        if name == "installed-apk-path":
            return "package:/data/app/synthetic/base.apk\n"
        if name == "installed-apk-sha256":
            return self.installed_sha + "  /data/app/synthetic/base.apk\n"
        if name in ("stop-before-run", "remove-stale-report", "launch", "stop-after-run"):
            return ""
        if name == "read-report":
            return json.dumps(self.result)
        raise AssertionError(name)


class DeviceContractTests(unittest.TestCase):
    """CodexAstraUlt: Prove data-preserving scope and cleanup with a fake boundary."""

    def run_fake(self, directory, **kwargs):
        adb = FakeAdb(Path(directory), **kwargs)
        evidence = {"request_id": REQUEST, "apk_sha256": "a" * 64}
        RUNNER.execute_probe(adb, Path("/tmp/fixture.apk"), MANIFEST, evidence, 5)
        return adb

    def test_only_probe_package_is_launched_once_without_destructive_operations(self):
        with tempfile.TemporaryDirectory() as temp:
            adb = self.run_fake(temp)
        install = next(args for name, args in adb.commands if name == "install")
        self.assertEqual(install, ["install", "-r", "-t", "/tmp/fixture.apk"])
        self.assertEqual([args for name, args in adb.commands if name == "launch"],
                         [["am", "start", "-W", "-n", "org.droidds.probe/.ProbeActivity",
                           "--es", "request_id", REQUEST]])
        self.assertEqual([args for name, args in adb.commands if name == "remove-stale-report"],
                         [["run-as", "org.droidds.probe", "rm", "-f", "files/latest-probe.json"]])
        stops = [args for _, args in adb.commands if "force-stop" in args]
        self.assertEqual(stops, [["am", "force-stop", "org.droidds.probe"]] * 2)
        for _, args in adb.commands:
            self.assertTrue(set(args).isdisjoint({"uninstall", "clear", "root", "reboot", "logcat"}))

    def test_failed_report_still_force_stops_only_owned_probe(self):
        with tempfile.TemporaryDirectory() as temp:
            failed = report()
            failed["status"] = "failed"
            adb = FakeAdb(Path(temp), result=failed)
            with self.assertRaisesRegex(ValueError, "identity/status"):
                RUNNER.execute_probe(adb, Path("/tmp/fixture.apk"), MANIFEST,
                                     {"request_id": REQUEST, "apk_sha256": "a" * 64}, 5)
            self.assertEqual(adb.commands[-1], ("stop-after-run", ["am", "force-stop", RUNNER.PACKAGE]))
            self.assertTrue((Path(temp) / "android-probe.json").is_file())

    def test_unsupported_renderer_retains_complete_json_without_qualifying_the_run(self):
        # CodexAstraUlt: A capability failure is useful device evidence. Preserve
        # it before the passing-only validator rejects the qualification gate.
        for renderer_status in ("unsupported", "failed"):
            with self.subTest(status=renderer_status), tempfile.TemporaryDirectory() as temp:
                failed, manifest = current_report()
                failed["status"] = "failed"
                graphics = failed["graphics_probe"]
                graphics["status"] = "failed"
                graphics["renderer_probe"]["status"] = renderer_status
                if renderer_status == "unsupported":
                    graphics["renderer_probe"]["required"]["depth_clamp"] = False
                    graphics["renderer_probe"]["missing_required"] = ["depth_clamp"]
                adb = FakeAdb(Path(temp), result=failed)
                evidence = {"request_id": REQUEST, "apk_sha256": "a" * 64}
                with self.assertRaisesRegex(ValueError, "identity/status"):
                    RUNNER.execute_probe(adb, Path("/tmp/fixture.apk"), manifest, evidence, 5)
                self.assertEqual(evidence["android_report"], failed)
                self.assertEqual(json.loads((Path(temp) / "android-probe.json").read_text()), failed)
                self.assertEqual(adb.commands[-1], ("stop-after-run", ["am", "force-stop", RUNNER.PACKAGE]))

    def test_failed_runtime_preserves_cpu_gpu_and_runtime_evidence_before_rejection(self):
        # CodexAstraUlt: A failing integrated renderer remains actionable device
        # evidence; neither its detailed report nor earlier successful gates vanish.
        with tempfile.TemporaryDirectory() as temp:
            failed, manifest = integrated_report()
            failed["status"] = "failed"
            failed["runtime_probe"].update(status="failed", error="hardware activation failed")
            adb = FakeAdb(Path(temp), result=failed)
            evidence = {"request_id": REQUEST, "apk_sha256": "a" * 64}
            with self.assertRaisesRegex(ValueError, "identity/status"):
                RUNNER.execute_probe(adb, Path("/tmp/fixture.apk"), manifest, evidence, 5)
            self.assertEqual(evidence["android_report"], failed)
            self.assertEqual(json.loads((Path(temp) / "android-probe.json").read_text()), failed)
            self.assertEqual(adb.commands[-1], ("stop-after-run", ["am", "force-stop", RUNNER.PACKAGE]))
            read = next(words for name, words in adb.commands if name == "read-report")
            self.assertEqual(read, ["run-as", RUNNER.PACKAGE, "head", "-c",
                                    str(1024 * 1024 + 64 * 1024 + 256 * 1024 + 16 * 1024 + 1),
                                    RUNNER.REPORT_PATH])

    def test_apk_hash_mismatch_prevents_launch(self):
        with tempfile.TemporaryDirectory() as temp:
            adb = FakeAdb(Path(temp), installed_sha="b" * 64)
            with self.assertRaisesRegex(RuntimeError, "SHA-256 differs"):
                RUNNER.execute_probe(adb, Path("/tmp/fixture.apk"), MANIFEST,
                                     {"request_id": REQUEST, "apk_sha256": "a" * 64}, 5)
            self.assertNotIn("launch", [name for name, _ in adb.commands])

    def test_running_marker_cannot_pass_and_deadline_stops_owned_probe(self):
        with tempfile.TemporaryDirectory() as temp:
            running = report()
            running["status"] = "running"
            adb = FakeAdb(Path(temp), result=running)
            with mock.patch.object(RUNNER.time, "monotonic", side_effect=[0, 0, 0, 0, 6, 6]), \
                    mock.patch.object(RUNNER.time, "sleep"), \
                    self.assertRaisesRegex(RuntimeError, "timed out without a complete"):
                RUNNER.execute_probe(adb, Path("/tmp/fixture.apk"), MANIFEST,
                                     {"request_id": REQUEST, "apk_sha256": "a" * 64}, 5)
            self.assertEqual(adb.commands[-1], ("stop-after-run", ["am", "force-stop", RUNNER.PACKAGE]))

    def test_signing_failure_never_triggers_uninstall(self):
        with tempfile.TemporaryDirectory() as temp:
            adb = FakeAdb(Path(temp), install_failure=True)
            with self.assertRaisesRegex(RuntimeError, "Do not uninstall or clear data"):
                RUNNER.execute_probe(adb, Path("/tmp/fixture.apk"), MANIFEST,
                                     {"request_id": REQUEST, "apk_sha256": "a" * 64}, 5)
            self.assertEqual(adb.commands[-1][0], "install")

    def test_remote_argv_quotes_shell_metacharacters_as_literal_words(self):
        with tempfile.TemporaryDirectory() as temp:
            adb = RUNNER.Adb("/usr/bin/adb", "literal-serial", Path(temp), [])
            words = ["sha256sum", "/data/app/space ' ; $(false) `false`/base.apk"]
            with mock.patch.object(adb, "run", return_value="") as run:
                adb.remote("hash", words, output=True)
                args = run.call_args.args[1]
                self.assertEqual(args[0], "exec-out")
                self.assertEqual(shlex.split(args[1]), words)

    def test_timeout_stops_actual_local_client_and_its_descendant(self):
        # CodexAstraUlt: This is a real process-tree regression, not an Android
        # execution claim. Wait for the child to exist before starting the short
        # command deadline; slow CI process startup is not a cleanup failure.
        # The parent only reaps its child, so group termination must stop both.
        with tempfile.TemporaryDirectory() as temp:
            directory = Path(temp)
            script = directory / "fake-adb"
            pid_file = directory / "child.pid"
            script.write_text(f"#!{sys.executable}\nimport signal,subprocess,sys,time\n"
                              "child=subprocess.Popen(['sleep','30'])\n"
                              "def reap_child(*_):\n"
                              "    child.wait(timeout=5)\n"
                              "    sys.exit(0)\n"
                              "signal.signal(signal.SIGTERM,reap_child)\n"
                              f"with open({str(pid_file)!r},'w') as output:\n"
                              "    output.write(str(child.pid))\n"
                              "time.sleep(30)\n")
            script.chmod(0o700)
            adb = RUNNER.Adb(str(script), "synthetic", directory, [])
            popen = RUNNER.subprocess.Popen
            processes = []

            def started_process(*args, **kwargs):
                process = popen(*args, **kwargs)
                processes.append(process)
                deadline = time.monotonic() + 10
                while time.monotonic() < deadline:
                    try:
                        child_pid = int(pid_file.read_text())
                    except (FileNotFoundError, ValueError):
                        self.assertIsNone(process.poll(), "Fixture exited before its startup handshake")
                        time.sleep(0.01)
                        continue
                    self.assertEqual(os.getpgid(child_pid), process.pid)
                    return process
                self.fail("Fixture did not create its child within the startup deadline")

            try:
                with mock.patch.object(RUNNER.subprocess, "Popen", side_effect=started_process), \
                        self.assertRaisesRegex(RuntimeError, "timed out"):
                    adb.run("timeout", ["get-state"], timeout=0.2)
                pid = int(pid_file.read_text())
                self.assertIsNotNone(processes[0].returncode, "Local client was not reaped")
                # CodexAstraUlt: A descendant zombie is not accepted as cleanup:
                # the fixture's parent must reap it before communicate returns.
                self.assertFalse(Path(f"/proc/{pid}").exists(),
                                 "ADB client's descendant survived or was not reaped")
            finally:
                # CodexAstraUlt: Failed assertions must not leak the test fixture.
                for process in processes:
                    try:
                        os.killpg(process.pid, signal.SIGKILL)
                    except ProcessLookupError:
                        pass
                    process.communicate()


if __name__ == "__main__":
    unittest.main()
