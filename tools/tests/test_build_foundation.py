"""CodexAstraUlt: Mutated dependency evidence must fail the source-pin gate."""

import copy
import importlib.util
from pathlib import Path
import sys
import tempfile
import unittest

SPEC = importlib.util.spec_from_file_location(
    "build_foundation", Path(__file__).parents[1] / "build_foundation.py")
RUNNER = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(RUNNER)


class SourcePinTests(unittest.TestCase):
    """CodexAstraUlt: Exercise drift, hidden verifier and incomplete graph failures."""

    def setUp(self):
        self.pins = {
            "schema": 1,
            "verification": {"upstream_verify_feature": False,
                             "oracle": "strict-synthetic-known-output"},
            "recompiler": {"repository": "https://example.test/recompiler",
                           "revision": "a" * 40, "packages": ["recomp3ds", "recomp-abi"]},
            "runtime": {"repository": "https://example.test/runtime",
                        "revision": "b" * 40, "packages": ["zakuro-cpu", "zakuro-common"]},
        }
        packages = [{"id": "root", "name": "droidds-foundation", "source": None}]
        nodes = [{"id": "root", "features": [], "deps": []}]
        for pin in (self.pins["recompiler"], self.pins["runtime"]):
            for name in pin["packages"]:
                source = f"git+{pin['repository']}?rev={pin['revision']}#{pin['revision']}"
                packages.append({"id": name, "name": name, "source": source, "version": "0.1.0"})
                nodes.append({"id": name, "features": [], "deps": []})
                nodes[0]["deps"].append({"pkg": name})
        self.metadata = {"packages": packages, "resolve": {"nodes": nodes},
                         "workspace_members": ["root"]}

    def test_selected_exact_pins_pass(self):
        self.assertEqual(len(RUNNER.validate_graph(self.metadata, self.pins)), 4)

    def test_changed_verification_policy_fails(self):
        self.pins["verification"]["upstream_verify_feature"] = True
        with self.assertRaisesRegex(ValueError, "verification policy"):
            RUNNER.validate_graph(self.metadata, self.pins)

    def test_resolved_revision_drift_fails(self):
        self.metadata["packages"][1]["source"] = self.metadata["packages"][1]["source"].split("#")[0] + "#" + "c" * 40
        with self.assertRaisesRegex(ValueError, "pin mismatch"):
            RUNNER.validate_graph(self.metadata, self.pins)

    def test_floating_ref_even_at_same_commit_fails(self):
        self.metadata["packages"][1]["source"] = "git+https://example.test/recompiler#" + "a" * 40
        with self.assertRaisesRegex(ValueError, "pin mismatch"):
            RUNNER.validate_graph(self.metadata, self.pins)

    def test_upstream_permissive_verifier_fails(self):
        self.metadata["resolve"]["nodes"][1]["features"] = ["verify"]
        with self.assertRaisesRegex(ValueError, "verifier"):
            RUNNER.validate_graph(self.metadata, self.pins)

    def test_missing_resolved_node_fails(self):
        self.metadata["resolve"]["nodes"].pop()
        with self.assertRaisesRegex(ValueError, "Missing resolved"):
            RUNNER.validate_graph(self.metadata, self.pins)

    def test_duplicate_active_cpu_fails(self):
        duplicate = copy.deepcopy(self.metadata["packages"][3])
        duplicate["id"] = "other-cpu"
        self.metadata["packages"].append(duplicate)
        self.metadata["resolve"]["nodes"].append({"id": "other-cpu", "features": [], "deps": []})
        self.metadata["resolve"]["nodes"][0]["deps"].append({"pkg": "other-cpu"})
        with self.assertRaisesRegex(ValueError, "Expected one active zakuro-cpu"):
            RUNNER.validate_graph(self.metadata, self.pins)

    def test_unrelated_inactive_package_does_not_change_used_graph(self):
        self.metadata["packages"].append({"id": "unused", "name": "zakuro-gpu", "source": None})
        self.metadata["resolve"]["nodes"].append({"id": "unused", "features": [], "deps": []})
        self.assertEqual(len(RUNNER.validate_graph(self.metadata, self.pins)), 4)

    def test_accidental_frontend_in_used_graph_fails(self):
        self.metadata["packages"].append({"id": "gui", "name": "zakuro", "source": None})
        self.metadata["resolve"]["nodes"].append({"id": "gui", "features": [], "deps": []})
        self.metadata["resolve"]["nodes"][0]["deps"].append({"pkg": "gui"})
        with self.assertRaisesRegex(ValueError, "unexpectedly includes"):
            RUNNER.validate_graph(self.metadata, self.pins)


class ReportGateTests(unittest.TestCase):
    """CodexAstraUlt: Reject stale, partial or incorrectly claimed proof reports."""

    def setUp(self):
        self.pins = {"recompiler": {"abi": 4, "generation": 3}}
        names = ("arm_integer_memory", "thumb_integer_memory",
                 "arm_missing_entry_fallback", "arm_to_thumb_native")
        controls = ("nan_shaped_integer_register_mismatch", "nan_shaped_integer_memory_mismatch",
                    "guest_instruction_limit", "process_watchdog")
        self.report = {"schema": 1, "status": "passed", "abi": 4, "generation": 3,
                       "cases": [{"name": name, "status": "passed", "native_calls": 1,
                                  "native_budget_charged": 3,
                                  "fallback_steps": int(name == "arm_missing_entry_fallback")}
                                 for name in names],
                       "negative_controls": [{"name": name, "status": "passed"} for name in controls]}

    def test_complete_report_passes(self):
        RUNNER.validate_report(self.report, self.pins)

    def test_abi_mismatch_fails(self):
        self.report["abi"] = 5
        with self.assertRaisesRegex(ValueError, "ABI"):
            RUNNER.validate_report(self.report, self.pins)

    def test_missing_case_fails(self):
        self.report["cases"].pop()
        with self.assertRaisesRegex(ValueError, "required CPU cases"):
            RUNNER.validate_report(self.report, self.pins)

    def test_unexercised_fallback_fails(self):
        self.report["cases"][2]["fallback_steps"] = 0
        with self.assertRaisesRegex(ValueError, "not exercised"):
            RUNNER.validate_report(self.report, self.pins)

    def test_no_native_work_fails(self):
        self.report["cases"][0]["native_budget_charged"] = 0
        with self.assertRaisesRegex(ValueError, "not demonstrated"):
            RUNNER.validate_report(self.report, self.pins)

    def test_missing_timeout_control_fails(self):
        self.report["negative_controls"].pop()
        with self.assertRaisesRegex(ValueError, "negative controls"):
            RUNNER.validate_report(self.report, self.pins)


class MachineOutputTests(unittest.TestCase):
    """CodexAstraUlt: First-use diagnostics cannot contaminate required tool output."""

    def test_stderr_kept_separate_from_machine_output(self):
        with tempfile.TemporaryDirectory() as directory:
            out = Path(directory)
            steps = []
            text = RUNNER.run_logged("probe", [sys.executable, "-c",
                "import sys; print('tool 1.2.3'); print('initializing', file=sys.stderr)"],
                out, steps, separate_stderr=True)
            self.assertEqual(text, "tool 1.2.3\n")
            self.assertEqual((out / "probe-stderr.log").read_text(), "initializing\n")
            self.assertEqual(steps[0]["exit_code"], 0)

    def test_valid_stdout_cannot_hide_failed_process(self):
        with tempfile.TemporaryDirectory() as directory:
            steps = []
            with self.assertRaisesRegex(RuntimeError, "exit code 7"):
                RUNNER.run_logged("probe", [sys.executable, "-c",
                    "import sys; print('tool 1.2.3'); sys.exit(7)"],
                    Path(directory), steps, separate_stderr=True)
            self.assertEqual(steps[0]["exit_code"], 7)


if __name__ == "__main__":
    unittest.main()
