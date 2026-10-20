"""CodexAstraUlt: Mutate original-homebrew proof without treating fixtures as device runs."""

import copy
import json
from pathlib import Path
import tempfile
import unittest

from test_run_android_probe import FakeAdb, REQUEST, RUNNER, integrated_report, runtime_hardware_report


def homebrew_report():
    """CodexAstraUlt: Explicit protocol values are independent of production validators."""
    cases = []
    for name in ("interpreter_software", "native_software", "native_vulkan"):
        stages = []
        for index, (stage, buttons, touch, top, bottom, rate) in enumerate((
                ("idle", 0, (0, 0, 0), (184, 104), (144, 104), 1),
                ("buttons", 81, (0, 0, 0), (328, 24), (144, 104), 2),
                ("touch", 0, (247, 181, 1), (184, 104), (231, 165), 1),
                ("release", 0, (0, 0, 0), (184, 104), (144, 104), 1))):
            stages.append({
                "name": stage, "status": "passed", "frames": (index + 1) * 4,
                "guest": {"checkpoint": 0x44534436, "serial": (index + 1) * 4 + 1,
                          "fallback_count": (index + 1) * 4 + 1, "buttons": buttons,
                          "touch_x": touch[0], "touch_y": touch[1], "touch_valid": touch[2],
                          "top_x": top[0], "top_y": top[1], "bottom_x": bottom[0],
                          "bottom_y": bottom[1], "tone_rate_bits": 1073741824 if rate == 2 else 1065353216,
                          "service_error_stage": 0, "exit_requested": 0, "progress_stage": 8,
                          "dsp_enabled": 1, "dsp_position": 0, "dsp_buffer_id": 0},
                "top": {"width": 400, "height": 240, "pixels_checked": 96000,
                        "mismatched_pixels": 0, "first_mismatches": []},
                "bottom": {"width": 320, "height": 240, "pixels_checked": 76800,
                           "mismatched_pixels": 0, "first_mismatches": []},
                "audio": {"samples_checked": (480, 640, 640, 480)[index], "mismatched_samples": 0, "channels": 2,
                          "rate_multiplier": rate, "first_samples": [[2000, 2000] for _ in range(4)]},
            })
        hardware = runtime_hardware_report() if name == "native_vulkan" else None
        if hardware is not None:
            hardware.update(recorded_draws=108, submissions=36)
        native = name != "interpreter_software"
        guest = dict(stages[-1]["guest"], serial=18, fallback_count=18, buttons=12,
                     exit_requested=1, progress_stage=9)
        session = {
            "schema": 1, "kind": "droidds-homebrew-session", "fixture": "droidds-original-homebrew-v1",
            "status": "exited", "error": None, "native": native,
            "renderer": "vulkan" if hardware else "software", "presentation": "rgba_readback",
            "audio_sample_rate": 32728.498046875, "frames": 17, "frames_delivered": 18,
            "guest": guest, "steps": 19851 if native else 28728, "cycles": 80442631,
            "interpreted_instructions": 36 if native else 9073,
            "recompiled_instructions": 9037 if native else 0, "native_fallback_instructions": 0,
            "pcm_samples": 9760, "pcm_nonzero_samples": 9600, "pcm_peak": 2000,
            "pause_count": 1, "resume_count": 1, "svc_unimplemented": 0,
            "service_unimplemented": 0, "memory_faults": 0,
            "services_seen": ["dsp::DSP", "gsp::Gpu", "hid:USER"],
            "command_lists": 36, "draw_calls": 108, "vertices_drawn": 324,
            "hardware": hardware, "hardware_device": "Protocol Vulkan device" if hardware else None,
            "dsp_running": False, "guest_exited": True,
            "guest_observed_buttons": 81, "guest_observed_touch_updates": 4,
        }
        cases.append({"name": name, "status": "passed", "error": None, "stages": stages,
                      "lifecycle": {"pause_rejected_frame": True, "pause_no_progress": True,
                                    "resume_progress": True, "guest_exit": True}, "session": session})
    return {
        "schema": 1, "kind": "droidds-homebrew-probe", "fixture": "droidds-original-homebrew-v1",
        "status": "passed", "error": None, "audio_sample_rate": 32728.498046875,
        "presentation": "rgba_readback", "cases": cases, "route_comparisons": 2,
        "controls": [{"name": "pixel_mutation_rejected", "status": "passed", "mismatches": 1},
                     {"name": "audio_mutation_rejected", "status": "passed", "mismatches": 1},
                     {"name": "frame_budget_rejected", "status": "passed", "steps": 1,
                      "rejection": "homebrew outer dispatch budget exceeded"},
                     {"name": "recreate_starts_clean", "status": "passed", "initial_cycles": 0,
                      "initial_guest_serial": 0},
                     {"name": "changed_code_before_dispatch_rejected", "status": "passed",
                      "rejection": "homebrew immutable executable text changed", "steps": 0,
                      "cycles": 0, "native_instructions": 0, "interpreted_instructions": 0}],
        "limitations": ["Original bounded homebrew; no audible or visible device qualification."],
    }


def visible_report():
    """CodexAstraUlt: Version 0.0.6 adds to every prior proof requirement."""
    value, manifest = integrated_report()
    value.update(version="0.0.6", interactive_probe=homebrew_report())
    value["android_shell"].update(app_version_name="0.0.6", app_version_code=6)
    manifest.update(version_name="0.0.6", version_code=6)
    return value, manifest


def manual_report():
    """CodexAstraUlt: Example observations test qualification, never attest to a device."""
    automatic, _ = visible_report()
    return {"schema": 1, "kind": "droidds-android-interactive-session", "status": "completed",
            "session_id": "dc10e045-5598-4775-8f17-34c4062a62d7",
            "bound_run_id": automatic["android_shell"]["run_id"],
            "native": copy.deepcopy(homebrew_report()["cases"][2]["session"]),
            "android": {"presentation": "android-canvas-rgba-readback", "top_width": 400,
                "top_height": 240, "bottom_width": 320, "bottom_height": 240,
                "frames_received": 18, "presented_frames": 17, "duration_foreground_ms": 1000,
                "view_attachments": 1, "view_replacements": 0,
                "pause_count": 1, "resume_count": 1, "foreground_frame_starts": 18,
                "background_frame_start_rejections": 0, "in_flight_frames_completed_after_pause": 0,
                "native_step_errors": 0, "stop_reason": "user_stop",
                "display_seen_by_user": "yes", "heard_by_user": "yes", "hardware_button_events": 4,
                "touch_events": 2, "virtual_button_events": 0, "other_key_events": 0, "input_queue_overflows": 0,
                "audio": {"status": "measured", "guest_sample_rate": 32728.498046875,
                    "output_sample_rate": 48000, "resampler": "stateful-linear",
                    "generated_frames": 9760, "converted_frames": 14315, "written_frames": 14000,
                    "playback_head_frames": 13900, "dropped_frames": 0, "flushed_frames": 315,
                    "partial_writes": 2, "underruns": 0, "queue_high_water_frames": 800,
                    "resampler_resets": 1, "discarded_input_frames": 0}}}


class HomebrewReportTests(unittest.TestCase):
    """CodexAstraUlt: Counter, oracle and identity mutations must fail closed."""

    def test_complete_automatic_contract_and_version_six_retain_prior_requirements(self):
        RUNNER.validate_interactive_report(homebrew_report())
        value, manifest = visible_report()
        RUNNER.validate_report(value, REQUEST, manifest)
        for key in ("interactive_probe", "runtime_probe", "graphics_probe", "code_safety", "cases"):
            changed = copy.deepcopy(value)
            del changed[key]
            with self.subTest(missing=key), self.assertRaises(ValueError):
                RUNNER.validate_report(changed, REQUEST, manifest)

    def test_identity_error_and_numeric_types_are_not_optional(self):
        for key in ("schema", "kind", "fixture", "status", "error", "audio_sample_rate",
                    "presentation", "route_comparisons"):
            value = homebrew_report()
            del value[key]
            with self.subTest(missing=key), self.assertRaises(ValueError):
                RUNNER.validate_interactive_report(value)
            value = homebrew_report()
            value[key] = True
            with self.subTest(key=key), self.assertRaises(ValueError):
                RUNNER.validate_interactive_report(value)
        for invalid in (None, [], {}):
            with self.subTest(invalid=invalid), self.assertRaises(ValueError):
                RUNNER.validate_interactive_report(invalid)

    def test_all_routes_and_script_stages_must_execute_in_order(self):
        for section in ("cases", "stages"):
            for mutation in ("missing", "duplicate", "reverse", "nonobject"):
                value = homebrew_report()
                target = value if section == "cases" else value["cases"][0]
                if mutation == "missing":
                    target[section].pop()
                elif mutation == "duplicate":
                    target[section][0] = copy.deepcopy(target[section][1])
                elif mutation == "reverse":
                    target[section].reverse()
                else:
                    target[section][0] = None
                with self.subTest(section=section, mutation=mutation), self.assertRaises(ValueError):
                    RUNNER.validate_interactive_report(value)

    def test_actual_guest_input_checkpoint_geometry_and_audio_rate_are_required(self):
        for index, stage in enumerate(homebrew_report()["cases"][0]["stages"]):
            for key, original in stage["guest"].items():
                for invalid in (None, True, original + 1):
                    if key in ("serial", "fallback_count") and invalid == original + 1:
                        continue
                    value = homebrew_report()
                    value["cases"][0]["stages"][index]["guest"][key] = invalid
                    with self.subTest(index=index, key=key, invalid=invalid), self.assertRaises(ValueError):
                        RUNNER.validate_interactive_report(value)
        value = homebrew_report()
        value["cases"][0]["stages"][2]["guest"]["serial"] = 8
        value["cases"][0]["stages"][2]["guest"]["fallback_count"] = 8
        with self.assertRaises(ValueError):
            RUNNER.validate_interactive_report(value)

    def test_both_full_scanouts_must_match_without_hidden_pixel_differences(self):
        for panel in ("top", "bottom"):
            for key in ("width", "height", "pixels_checked", "mismatched_pixels", "first_mismatches"):
                value = homebrew_report()
                del value["cases"][0]["stages"][0][panel][key]
                with self.subTest(panel=panel, missing=key), self.assertRaises(ValueError):
                    RUNNER.validate_interactive_report(value)
                value = homebrew_report()
                value["cases"][0]["stages"][0][panel][key] = [{"index": 0}] if key == "first_mismatches" else True
                with self.subTest(panel=panel, key=key), self.assertRaises(ValueError):
                    RUNNER.validate_interactive_report(value)

    def test_pcm_requires_expected_stereo_samples_and_nonempty_complete_blocks(self):
        for key, invalid in (("samples_checked", 0), ("samples_checked", 161), ("samples_checked", 1440),
                             ("samples_checked", True), ("channels", 1), ("channels", True),
                             ("rate_multiplier", 2), ("mismatched_samples", 1),
                             ("first_samples", [[2000, 2001]] * 4), ("first_samples", [[2000]] * 4),
                             ("first_samples", [[2000, 2000]] * 3), ("first_samples", [[True, 2000]] * 4)):
            value = homebrew_report()
            value["cases"][0]["stages"][0]["audio"][key] = invalid
            with self.subTest(key=key, invalid=invalid), self.assertRaises(ValueError):
                RUNNER.validate_interactive_report(value)

    def test_session_routes_faults_audio_and_observed_input_cannot_be_replaced_by_ui_claims(self):
        for key, invalid in (("recompiled_instructions", 0), ("interpreted_instructions", 0),
                             ("native_fallback_instructions", 1), ("svc_unimplemented", 1),
                             ("service_unimplemented", 1), ("memory_faults", 1),
                             ("pcm_nonzero_samples", 0), ("pcm_peak", 0),
                             ("guest_observed_buttons", 0), ("guest_observed_touch_updates", 0),
                             ("hardware", None), ("hardware_device", ""), ("status", "running"),
                             ("guest_exited", False), ("dsp_running", True), ("services_seen", [])):
            value = homebrew_report()
            value["cases"][2]["session"][key] = invalid
            with self.subTest(key=key, invalid=invalid), self.assertRaises(ValueError):
                RUNNER.validate_interactive_report(value)
        value = homebrew_report()
        value["cases"][2]["session"]["hardware"]["software_raster_fallbacks"] = 1
        with self.assertRaises(ValueError):
            RUNNER.validate_interactive_report(value)

    def test_exact_scheduling_render_audio_and_stage_totals_reject_positive_drift(self):
        keys = ("cycles", "steps", "interpreted_instructions", "recompiled_instructions",
                "frames", "frames_delivered", "pcm_samples", "pcm_nonzero_samples", "pcm_peak",
                "command_lists", "draw_calls", "vertices_drawn", "guest_observed_touch_updates")
        for index in range(3):
            for key in keys:
                value = homebrew_report()
                value["cases"][index]["session"][key] += 1
                with self.subTest(index=index, key=key), self.assertRaises(ValueError):
                    RUNNER.validate_interactive_report(value)
        for index in range(4):
            for field in ("frames", "serial", "samples_checked"):
                value = homebrew_report()
                stage = value["cases"][0]["stages"][index]
                target = stage if field == "frames" else stage["guest"] if field == "serial" else stage["audio"]
                target[field] += 1
                with self.subTest(stage=index, field=field), self.assertRaises(ValueError):
                    RUNNER.validate_interactive_report(value)

    def test_failed_homebrew_retains_all_prior_evidence_before_runner_rejection(self):
        value, manifest = visible_report()
        value["status"] = "failed"
        value["interactive_probe"].update(status="failed", error="guest PCM differs")
        with tempfile.TemporaryDirectory() as temp:
            adb = FakeAdb(Path(temp), result=value)
            evidence = {"request_id": REQUEST, "apk_sha256": "a" * 64}
            with self.assertRaisesRegex(ValueError, "identity/status"):
                RUNNER.execute_probe(adb, Path("/tmp/protocol.apk"), manifest, evidence, 5)
            self.assertEqual(evidence["android_report"], value)
            self.assertEqual(json.loads((Path(temp) / "android-probe.json").read_text()), value)
            self.assertEqual(adb.commands[-1], ("stop-after-run", ["am", "force-stop", RUNNER.PACKAGE]))

    def test_required_pause_resume_exit_and_negative_controls_prove_real_rejection(self):
        for key in homebrew_report()["cases"][0]["lifecycle"]:
            for invalid in (False, 1, None):
                value = homebrew_report()
                value["cases"][0]["lifecycle"][key] = invalid
                with self.subTest(key=key, invalid=invalid), self.assertRaises(ValueError):
                    RUNNER.validate_interactive_report(value)
        for index, control in enumerate(homebrew_report()["controls"]):
            for key in control:
                value = homebrew_report()
                del value["controls"][index][key]
                with self.subTest(index=index, missing=key), self.assertRaises(ValueError):
                    RUNNER.validate_interactive_report(value)
        value = homebrew_report()
        value["controls"][2]["rejection"] = "unrelated failure"
        with self.assertRaises(ValueError):
            RUNNER.validate_interactive_report(value)


class ManualQualificationTests(unittest.TestCase):
    """CodexAstraUlt: Host automation and frontend counters cannot supply human observations."""

    def qualify(self, value):
        return RUNNER.manual_qualification(value, manual_report()["bound_run_id"])

    def test_completed_observed_device_contract_is_distinct_from_automatic_status(self):
        manual = manual_report()
        self.assertEqual(self.qualify(manual)["status"], "passed")
        automatic, manifest = visible_report()
        automatic["interactive_session"] = manual
        RUNNER.validate_report(automatic, REQUEST, manifest)
        manual["android"]["heard_by_user"] = "no"
        RUNNER.validate_report(automatic, REQUEST, manifest)
        self.assertEqual(self.qualify(manual)["status"], "failed")
        self.assertEqual(automatic["status"], "passed")

    def test_absent_running_and_interrupted_manual_sessions_leave_device_gate_pending(self):
        self.assertEqual(self.qualify(None)["status"], "pending")
        for state in ("running", "interrupted", "failed"):
            value = manual_report()
            value["status"] = state
            if state == "running":
                del value["native"], value["android"]
            else:
                value["native"], value["android"] = {"status": state}, {}
            expected = "failed" if state == "failed" else "pending"
            self.assertEqual(self.qualify(value)["status"], expected)

    def test_manual_session_cannot_bind_another_run_or_use_an_invalid_identity(self):
        for key, invalid in (("bound_run_id", "dc10e045-5598-4775-8f17-34c4062a62d7"),
                             ("session_id", "wrong"), ("session_id", None),
                             ("schema", True), ("status", "passed")):
            value = manual_report()
            value[key] = invalid
            with self.subTest(key=key), self.assertRaises(ValueError):
                self.qualify(value)

    def test_hearing_and_display_confirmation_are_explicit_not_inferred_from_counters(self):
        for key in ("heard_by_user", "display_seen_by_user"):
            value = manual_report()
            value["android"][key] = "not_confirmed"
            with self.subTest(key=key):
                self.assertEqual(self.qualify(value)["status"], "pending")
            value["android"][key] = "no"
            self.assertEqual(self.qualify(value)["status"], "failed")
            value["android"][key] = True
            with self.assertRaises(ValueError):
                self.qualify(value)

    def test_physical_and_touch_events_need_guest_consumption_and_native_pause_resume(self):
        for source, key in (("android", "hardware_button_events"), ("android", "touch_events"),
                            ("android", "pause_count"), ("android", "resume_count"),
                            ("native", "guest_observed_buttons"), ("native", "guest_observed_touch_updates"),
                            ("native", "pause_count"), ("native", "resume_count")):
            value = manual_report()
            value[source][key] = 0
            with self.subTest(source=source, key=key):
                self.assertEqual(self.qualify(value)["status"], "pending")
        value = manual_report()
        value["android"].update(hardware_button_events=0, virtual_button_events=20)
        self.assertEqual(self.qualify(value)["status"], "pending")

    def test_errors_overflow_and_fallback_do_not_qualify(self):
        for key in ("native_step_errors", "input_queue_overflows"):
            value = manual_report()
            value["android"][key] = 1
            with self.subTest(key=key):
                self.assertEqual(self.qualify(value)["status"], "failed")
        value = manual_report()
        value["native"]["hardware"]["software_raster_fallbacks"] = 1
        self.assertEqual(self.qualify(value)["status"], "failed")

    def test_rejected_background_starts_and_one_inflight_completion_are_not_hidden(self):
        value = manual_report()
        value["android"].update(background_frame_start_rejections=1,
                                in_flight_frames_completed_after_pause=1)
        self.assertEqual(self.qualify(value)["status"], "passed")
        value["android"]["foreground_frame_starts"] = 17
        with self.assertRaises(ValueError):
            self.qualify(value)

    def test_audio_counts_do_not_replace_real_guest_pcm_or_confirmed_playback(self):
        for key in ("written_frames", "playback_head_frames"):
            value = manual_report()
            value["android"]["audio"][key] = 0
            if key == "written_frames":
                value["android"]["audio"]["playback_head_frames"] = 0
            self.assertEqual(self.qualify(value)["status"], "pending")
        value = manual_report()
        value["android"]["audio"] = {"status": "not_started"}
        self.assertEqual(self.qualify(value)["status"], "pending")
        value = manual_report()
        value["native"]["pcm_nonzero_samples"] = 0
        self.assertEqual(self.qualify(value)["status"], "failed")
        value = manual_report()
        value["android"]["audio"]["generated_frames"] = 9761
        self.assertEqual(self.qualify(value)["status"], "failed")

    def test_all_completed_android_counts_are_present_bounded_integers(self):
        for section in ("android", "audio"):
            original = manual_report()["android"]
            if section == "audio":
                original = original["audio"]
            for key, expected in original.items():
                if type(expected) is not int:
                    continue
                for invalid in (True, -1, 1 << 53):
                    value = manual_report()
                    target = value["android"] if section == "android" else value["android"]["audio"]
                    target[key] = invalid
                    with self.subTest(section=section, key=key, invalid=invalid), self.assertRaises(ValueError):
                        self.qualify(value)
        for key, invalid in (("frames_received", 6001), ("presented_frames", 19),
                             ("duration_foreground_ms", 180001)):
            value = manual_report()
            value["android"][key] = invalid
            with self.subTest(key=key), self.assertRaises(ValueError):
                self.qualify(value)

    def test_audio_accounting_quality_observations_remain_visible(self):
        value = manual_report()
        value["android"]["audio"].update(dropped_frames=10, underruns=2)
        verdict = self.qualify(value)
        self.assertEqual(verdict["status"], "passed")
        self.assertEqual(sum(note.startswith("Audio ") for note in verdict["notes"]), 2)
        for key, invalid in (("queue_high_water_frames", 8193), ("playback_head_frames", 14001),
                             ("written_frames", 14316)):
            value = manual_report()
            value["android"]["audio"][key] = invalid
            with self.subTest(key=key), self.assertRaises(ValueError):
                self.qualify(value)

    def test_view_recreation_is_measured_separately_from_ordinary_pause_resume(self):
        value = manual_report()
        self.assertTrue(any("recreation was not exercised" in note for note in self.qualify(value)["notes"]))
        value["android"].update(view_attachments=2, view_replacements=1)
        self.assertEqual(self.qualify(value)["status"], "passed")
        self.assertFalse(any("recreation was not exercised" in note for note in self.qualify(value)["notes"]))
        value["android"]["view_replacements"] = 2
        with self.assertRaises(ValueError):
            self.qualify(value)


if __name__ == "__main__":
    unittest.main()
