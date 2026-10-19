"""CodexAstraUlt: Mutated dependency evidence must fail the source-pin gate."""

import copy
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest import mock

# CodexAstraUlt: Permit this test file to run alone now that the build gate
# imports the shared versioned report contract from its sibling tool.
sys.path.insert(0, str(Path(__file__).parents[1]))

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


class VendoredRuntimePinTests(SourcePinTests):
    """CodexAstraUlt: Reject a relocated, substituted or unqualified runtime graph."""

    def setUp(self):
        super().setUp()
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.addCleanup(mock.patch.stopall)
        mock.patch.object(RUNNER, "ROOT", self.root).start()
        self.pins["vendored_runtime"] = {
            **self.pins["runtime"], "directory": "vendor/zakuro",
            "packages": ["zakuro-core", "zakuro-fs", "zakuro-gpu"]}
        vendor = self.root / "vendor/zakuro"
        vendor.mkdir(parents=True)
        import json
        (vendor / "UPSTREAM.json").write_text(json.dumps({
            "schema": 1, "repository": self.pins["runtime"]["repository"],
            "revision": self.pins["runtime"]["revision"],
            "files": {str(index): "0" * 64 for index in range(132)}}))
        for name in self.pins["vendored_runtime"]["packages"]:
            self.metadata["packages"].append({
                "id": name, "name": name, "source": None, "version": "0.2.27",
                "license": "MIT", "manifest_path": str(vendor / "crates" / name / "Cargo.toml")})
            self.metadata["resolve"]["nodes"].append({
                "id": name, "features": ["vulkan"] if name == "zakuro-gpu" else [], "deps": []})
            self.metadata["resolve"]["nodes"][0]["deps"].append({"pkg": name})

    # CodexAstraUlt: The inherited pin mutations also run with the full runtime;
    # only these two expected graph-size observations differ from CPU-only tests.
    def test_selected_exact_pins_pass(self):
        self.assertEqual(len(RUNNER.validate_graph(self.metadata, self.pins)), 7)

    def test_unrelated_inactive_package_does_not_change_used_graph(self):
        self.metadata["packages"].append({"id": "unused", "name": "zakuro-gpu", "source": None})
        self.metadata["resolve"]["nodes"].append({"id": "unused", "features": [], "deps": []})
        self.assertEqual(len(RUNNER.validate_graph(self.metadata, self.pins)), 7)

    def test_missing_resolved_node_fails(self):
        self.metadata["resolve"]["nodes"].pop()
        with self.assertRaisesRegex(ValueError, "Missing resolved"):
            RUNNER.validate_graph(self.metadata, self.pins)

    def test_substituted_vendor_location_or_license_fails(self):
        package = self.metadata["packages"][-1]
        for key, value in (("manifest_path", "/tmp/unreviewed/Cargo.toml"),
                           ("source", "git+https://example.test/unreviewed"),
                           ("license", "unknown"), ("version", "0.2.28")):
            original = package[key]
            package[key] = value
            with self.subTest(key=key), self.assertRaisesRegex(ValueError, "identity"):
                RUNNER.validate_graph(self.metadata, self.pins)
            package[key] = original

    def test_unqualified_gpu_features_fail(self):
        gpu = self.metadata["resolve"]["nodes"][-1]
        for features in ([], ["vulkan", "jit"], ["vulkan", "opengl"]):
            gpu["features"] = features
            with self.subTest(features=features), self.assertRaisesRegex(ValueError, "Vulkan"):
                RUNNER.validate_graph(self.metadata, self.pins)

    def test_changed_vendor_origin_fails(self):
        self.pins["vendored_runtime"]["revision"] = "c" * 40
        with self.assertRaisesRegex(ValueError, "provenance"):
            RUNNER.validate_graph(self.metadata, self.pins)


class VendoredCompilerPinTests(unittest.TestCase):
    """CodexAstraUlt: A compiler patch must not relax ABI pins or provenance."""

    def setUp(self):
        SourcePinTests.setUp(self)
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.addCleanup(mock.patch.stopall)
        mock.patch.object(RUNNER, "ROOT", self.root).start()
        self.pins["vendored_recompiler"] = {
            **self.pins["recompiler"], "directory": "vendor/3dsrecomp", "packages": ["recomp3ds"]}
        self.directory = self.root / "vendor/3dsrecomp"
        self.directory.mkdir(parents=True)
        self.origin = {"schema": 1, "repository": self.pins["recompiler"]["repository"],
                       "revision": self.pins["recompiler"]["revision"],
                       "files": {str(i): "0" * 64 for i in range(20)}}
        (self.directory / "UPSTREAM.json").write_text(json.dumps(self.origin))
        self.compiler = self.metadata["packages"][1]
        self.compiler.update(source=None, license="MIT",
                             manifest_path=str(self.directory / "Cargo.toml"))

    def test_exact_local_compiler_preserves_git_abi(self):
        selected = RUNNER.validate_graph(self.metadata, self.pins)
        self.assertEqual(selected["recomp3ds"]["source"], "vendored:vendor/3dsrecomp/Cargo.toml")
        self.assertTrue(selected["recomp-abi"]["source"].startswith("git+"))

    def test_unreviewed_compiler_origin_is_rejected(self):
        self.origin["revision"] = "c" * 40
        (self.directory / "UPSTREAM.json").write_text(json.dumps(self.origin))
        with self.assertRaisesRegex(ValueError, "compiler original-source"):
            RUNNER.validate_graph(self.metadata, self.pins)

    def test_compiler_cannot_move_or_change_license(self):
        for key, value in (("manifest_path", "/tmp/other/Cargo.toml"), ("license", "unknown"),
                           ("version", "0.2.0"), ("source", "git+https://other.test")):
            before = self.compiler[key]
            self.compiler[key] = value
            with self.subTest(key=key), self.assertRaisesRegex(ValueError, "compiler identity"):
                RUNNER.validate_graph(self.metadata, self.pins)
            self.compiler[key] = before

    def test_abi_drift_and_permissive_verifier_remain_rejected(self):
        abi = self.metadata["packages"][2]
        original = abi["source"]
        abi["source"] = original.split("#")[0] + "#" + "c" * 40
        with self.assertRaisesRegex(ValueError, "pin mismatch"):
            RUNNER.validate_graph(self.metadata, self.pins)
        abi["source"] = original
        self.metadata["resolve"]["nodes"][1]["features"] = ["verify"]
        with self.assertRaisesRegex(ValueError, "verifier"):
            RUNNER.validate_graph(self.metadata, self.pins)


class ReportGateTests(unittest.TestCase):
    """CodexAstraUlt: Reject stale, partial or incorrectly claimed proof reports."""

    def setUp(self):
        self.pins = {"recompiler": {"abi": 4, "generation": 3}}
        names = RUNNER.cases_for_version("0.0.4")
        controls = ("nan_shaped_integer_register_mismatch", "nan_shaped_integer_memory_mismatch",
                    "guest_instruction_limit", "process_watchdog")
        self.report = {"schema": 1, "status": "passed", "abi": 4, "generation": 3,
                       "cases": [{"name": name, "status": "passed", **counters}
                                 for name, counters in names.items()],
                       "code_safety": {
                           "policy": "immutable_fixture_text", "status": "passed",
                           "limitations": ["Original unit-test evidence only"],
                           "controls": [
                               {"name": "stale_origin_rejected", "status": "passed",
                                "rejection": "Unit-test stale origin"},
                               {"name": "changed_code_before_dispatch_rejected", "status": "passed",
                                "native_calls": 0, "fallback_steps": 0, "guest_memory_unchanged": True},
                               {"name": "guest_executable_write_rejected", "status": "passed",
                                "native_calls": 1, "rejected_writes": 2, "guest_memory_unchanged": True}]},
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
        with self.assertRaisesRegex(ValueError, "route counter"):
            RUNNER.validate_report(self.report, self.pins)

    def test_no_native_work_fails(self):
        self.report["cases"][0]["native_budget_charged"] = 0
        with self.assertRaisesRegex(ValueError, "route counter"):
            RUNNER.validate_report(self.report, self.pins)

    def test_missing_timeout_control_fails(self):
        self.report["negative_controls"].pop()
        with self.assertRaisesRegex(ValueError, "negative controls"):
            RUNNER.validate_report(self.report, self.pins)

    # CodexAstraUlt: A former four-case report and an unchecked code mutation
    # cannot satisfy the expanded host milestone merely by claiming passed.
    def test_old_case_set_and_missing_code_guard_fail(self):
        current = self.report["cases"]
        self.report["cases"] = current[:4]
        with self.assertRaisesRegex(ValueError, "required CPU cases"):
            RUNNER.validate_report(self.report, self.pins)
        self.report["cases"] = current
        del self.report["code_safety"]
        with self.assertRaisesRegex(ValueError, "code safety"):
            RUNNER.validate_report(self.report, self.pins)

    def test_tiny_budget_must_prove_exit_and_fallback(self):
        case = self.report["cases"][-1]
        case["budget_exits"] = 0
        with self.assertRaisesRegex(ValueError, "route counter"):
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
