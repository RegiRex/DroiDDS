"""CodexAstraUlt: Reject skipped runtime proof, absent validation and unsafe emission."""

import copy
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest import mock

sys.path.insert(0, str(Path(__file__).parents[1]))
import build_runtime_probe as build


class RequiredSuiteTests(unittest.TestCase):
    """CodexAstraUlt: A green Cargo exit alone must not qualify an unexecuted GPU test."""

    def setUp(self):
        self.proof = "\n".join("test " + name + " ... ok" for name in sorted(build.GPU_REQUIRED_TESTS))
        self.proof += "\ntest shader::tests::batch_speed ... ignored\n"
        self.proof += "test shader::tests::compiled_speed ... ignored\n"
        self.proof += (f"test result: ok. {len(build.GPU_REQUIRED_TESTS)} passed; 0 failed; "
                       "2 ignored; 0 measured; 0 filtered out\n")

    def test_full_comparisons_and_documented_benchmarks_pass(self):
        result = build.validate_suite(self.proof, build.GPU_REQUIRED_TESTS, build.GPU_IGNORED_BENCHMARKS)
        self.assertEqual(result["passed"], len(build.GPU_REQUIRED_TESTS))
        self.assertEqual(result["ignored_benchmarks"], sorted(build.GPU_IGNORED_BENCHMARKS))

    def test_feature_disabled_suite_cannot_qualify_gpu(self):
        proof = self.proof.replace("test raster::tests::the_gpu_covers_the_same_pixels ... ok", "test unrelated ... ok")
        with self.assertRaisesRegex(ValueError, "Required tests are missing"):
            build.validate_suite(proof, build.GPU_REQUIRED_TESTS, build.GPU_IGNORED_BENCHMARKS)

    def test_zero_filtered_or_measured_suite_fails(self):
        for before, after in ((f"{len(build.GPU_REQUIRED_TESTS)} passed", "0 passed"), ("0 filtered out", "1 filtered out"),
                              ("0 measured", "1 measured")):
            with self.subTest(after=after), self.assertRaisesRegex(ValueError, "completely"):
                build.validate_suite(self.proof.replace(before, after), build.GPU_REQUIRED_TESTS,
                                     build.GPU_IGNORED_BENCHMARKS)

    def test_newly_ignored_correctness_test_is_not_a_benchmark(self):
        proof = self.proof.replace("shader::tests::batch_speed", "raster::tests::required_output")
        with self.assertRaisesRegex(ValueError, "unqualified ignored"):
            build.validate_suite(proof, build.GPU_REQUIRED_TESTS, build.GPU_IGNORED_BENCHMARKS)

    def test_hidden_ignored_summary_count_fails(self):
        with self.assertRaisesRegex(ValueError, "unqualified ignored"):
            build.validate_suite(self.proof.replace("2 ignored", "3 ignored"),
                                 build.GPU_REQUIRED_TESTS, build.GPU_IGNORED_BENCHMARKS)


class VulkanValidationTests(unittest.TestCase):
    """CodexAstraUlt: Require loaded layers, not their names in a configuration message."""

    ACTIVE = ('[Vulkan Loader] INFO | LAYER: Insert instance layer "VK_LAYER_KHRONOS_validation" (lib.so)\n'
              '[Vulkan Loader] INFO | LAYER: Inserted device layer "VK_LAYER_KHRONOS_validation" (lib.so)\n')

    def test_actual_instance_and_device_insertion_pass(self):
        self.assertTrue(build.validate_diagnostics(self.ACTIVE)["device_layer_observed"])

    def test_requested_but_unloaded_layer_fails(self):
        with self.assertRaisesRegex(ValueError, "activation was not observed"):
            build.validate_diagnostics('env var VK_INSTANCE_LAYERS defined: VK_LAYER_KHRONOS_validation')

    def test_instance_only_does_not_prove_device_validation(self):
        with self.assertRaisesRegex(ValueError, "activation was not observed"):
            build.validate_diagnostics(self.ACTIVE.splitlines()[0])

    def test_api_sync_and_loader_errors_fail_even_with_exact_pixels(self):
        for error in ("Validation Error", "VUID-draw-invalid", "SYNC-HAZARD-WRITE_AFTER_WRITE",
                      "ERROR | failed driver", "ERROR: [Loader Message] missing layer"):
            with self.subTest(error=error), self.assertRaisesRegex(ValueError, "validation/driver error"):
                build.validate_diagnostics(self.ACTIVE + error)

    def test_required_environment_preserves_selection_and_restores_on_failure(self):
        with mock.patch.dict(os.environ, {"ZAKURO_STATIC_BLEND": "owner", "VK_INSTANCE_LAYERS": "owner-layer"}, clear=True):
            environment = build.validation_environment()
            self.assertEqual(environment["VK_INSTANCE_LAYERS"], "owner-layer:VK_LAYER_KHRONOS_validation")
            self.assertEqual(environment["VK_LAYER_ENABLES"], build.SYNC_VALIDATION)
            with self.assertRaises(RuntimeError):
                with build.command_environment({"ZAKURO_STATIC_BLEND": None, "DROIDDS_REQUIRE_VULKAN_TESTS": "1"}):
                    self.assertNotIn("ZAKURO_STATIC_BLEND", os.environ)
                    raise RuntimeError("deliberate failure")
            self.assertEqual(os.environ["ZAKURO_STATIC_BLEND"], "owner")
            self.assertNotIn("DROIDDS_REQUIRE_VULKAN_TESTS", os.environ)

    def test_disabled_validation_cannot_pass_required_mode(self):
        with mock.patch.dict(os.environ, {"VK_LAYER_DISABLES": "VK_VALIDATION_FEATURE_DISABLE_ALL_EXT"}, clear=True):
            with self.assertRaisesRegex(ValueError, "conflicts"):
                build.validation_environment()


class GeneratedFixtureTests(unittest.TestCase):
    """CodexAstraUlt: A generated manifest cannot select old, foreign or escaped sources."""

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.directory = Path(self.temp.name)
        (self.directory / "original.c").write_text("/* Original test fixture. */\n")
        (self.directory / "runtime-fixture.cxi").write_bytes(b"original unit-test placeholder")
        self.manifest = {"schema": 1, "kind": "droidds-runtime-fixture-sources",
                         "fixture": "droidds-original-pica-ipc-v1", "library": "libdroidds_fixture_runtime.so",
                         "abi": 4, "generation": 3, "sources": ["original.c"]}

    def test_original_local_source_is_selected(self):
        self.assertEqual(build.generated_sources(self.manifest, self.directory), [self.directory / "original.c"])

    def test_foreign_library_and_bool_schema_fail(self):
        for key, value in (("library", "other.so"), ("schema", True)):
            manifest = {**self.manifest, key: value}
            with self.subTest(key=key), self.assertRaisesRegex(ValueError, "identity mismatch"):
                build.generated_sources(manifest, self.directory)

    def test_escaped_duplicate_missing_and_non_c_sources_fail(self):
        for sources in (("../escape.c",), ("original.c", "original.c"), ("missing.c",), ("original.o",), ()):
            manifest = {**self.manifest, "sources": list(sources)}
            with self.subTest(sources=sources), self.assertRaises(ValueError):
                build.generated_sources(manifest, self.directory)

    def test_symlink_source_fails_even_inside_output(self):
        (self.directory / "link.c").symlink_to(self.directory / "original.c")
        manifest = copy.deepcopy(self.manifest)
        manifest["sources"] = ["link.c"]
        with self.assertRaisesRegex(ValueError, "nonlocal"):
            build.generated_sources(manifest, self.directory)

    def test_missing_ncch_fixture_fails(self):
        (self.directory / "runtime-fixture.cxi").unlink()
        with self.assertRaisesRegex(ValueError, "NCCH fixture"):
            build.generated_sources(self.manifest, self.directory)

    # CodexAstraUlt: A stale .5 source manifest/container cannot accidentally
    # satisfy the new interactive guest gate, even when its C paths are valid.
    def test_homebrew_requires_distinct_identity_and_container(self):
        with self.assertRaisesRegex(ValueError, "identity mismatch"):
            build.generated_sources(self.manifest, self.directory, homebrew=True)
        manifest = {**self.manifest, "kind": "droidds-homebrew-fixture-sources",
                    "fixture": "droidds-original-homebrew-v1", "library": "libdroidds_fixture_homebrew.so"}
        with self.assertRaisesRegex(ValueError, "NCCH fixture"):
            build.generated_sources(manifest, self.directory, homebrew=True)
        (self.directory / "runtime-fixture.cxi").rename(self.directory / "homebrew-fixture.cxi")
        self.assertEqual(build.generated_sources(manifest, self.directory, homebrew=True),
                         [self.directory / "original.c"])


class StaticRuntimePathTests(unittest.TestCase):
    """CodexAstraUlt: Forcing an environment variable is not proof of the actual selected path."""

    def test_both_static_states_reported(self):
        build.validate_static_runtime({"cases": [{"name": "native_vulkan", "hardware": {
            "dynamic_blend": False, "dynamic_logic_op": False}}]})

    def test_dynamic_missing_or_numeric_states_fail(self):
        for hardware in ({"dynamic_blend": True, "dynamic_logic_op": False},
                         {"dynamic_blend": False, "dynamic_logic_op": True},
                         {"dynamic_blend": False}, {"dynamic_blend": 0, "dynamic_logic_op": 0}, None):
            with self.subTest(hardware=hardware), self.assertRaisesRegex(ValueError, "static blend"):
                build.validate_static_runtime({"cases": [{"name": "native_vulkan", "hardware": hardware}]})


if __name__ == "__main__":
    unittest.main()
