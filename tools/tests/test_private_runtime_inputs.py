#!/usr/bin/env python3
"""CodexAstraUlt: Admit original compiled identities without executing libraries.

The borrowed compiler fixtures contain deliberately invalid runtime pointer
tables. These tests qualify input admission only; a separate ELF graph audit
must reject those tables before any native loader is allowed to see them.
"""

import copy
import fcntl
import hashlib
import importlib.util
import os
from pathlib import Path
import struct
import unittest
from unittest import mock


# CodexAstraUlt: Explicit loading avoids a dependency on unittest discovery order.
TOOLS = Path(__file__).resolve().parents[1]


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


INPUTS = load("runtime_input_admission_test", TOOLS / "private_runtime_inputs.py")
FIXTURES = load("runtime_input_compiler_fixtures", TOOLS / "tests/test_compile_private_title.py")


class RuntimeInputTests(unittest.TestCase):
    """CodexAstraUlt: Real compilation supports graph/tamper tests, never dlopen."""

    @classmethod
    def setUpClass(cls):
        FIXTURES.CompileCoordinatorTests.setUpClass()

    def setUp(self):
        self.fixture = FIXTURES.CompileCoordinatorTests(
            "test_compiles_real_objects_and_library_without_loading_or_mutating_preparation")
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)
        self.preparation, self.compilation = self.fixture.preparation, self.fixture.output
        # CodexAstraUlt: The old tests normally replace tool identity with a tiny
        # fake. Runtime admission instead binds all six actual frozen helpers.
        with mock.patch.object(FIXTURES.RUNNER, "coordinator_identity",
                               return_value=INPUTS.COMPILE.coordinator_identity()):
            code, report = self.fixture.execute()
        self.assertEqual(code, 0, report)
        self.manifest_path = self.compilation / "compiled-manifest.json"
        self.plan_path = self.compilation / "compile-plan.json"
        self.manifest = INPUTS.COMPILE.read_canonical(self.manifest_path)
        self.library = self.compilation / self.manifest["library"]["path"]

    def admit(self):
        return INPUTS.load_compiled(self.preparation, self.compilation)

    def write_json(self, path, value):
        path.write_bytes(INPUTS.PREP.canonical(value))

    def test_completed_original_admission_preserves_all_historical_outputs(self):
        before = FIXTURES.tree_bytes(self.fixture.root)
        with INPUTS.admitted_inputs(self.preparation, self.compilation) as result:
            self.assertEqual(result["library_path"], self.library)
            self.assertEqual(result["snapshot_path"], self.preparation / "input.cxi")
            self.assertEqual(result["units"], [{"name": None, "text_start": 0x100000,
                                                "text": bytes(range(16))}])
            self.assertEqual(len(result["components"]), 3)
            cursor = 0
            for component in result["components"]:
                self.assertEqual(component["offset"], cursor)
                cursor += component["bytes"]
                self.assertEqual(component["full_path"].read_bytes(),
                                 self.fixture.fixture.blobs[component["path"]])
            for name in ("runtime_binding_enforced", "library_loaded", "guest_execution_performed"):
                self.assertIs(result["compiled_manifest"][name], False)
            self.assertTrue(INPUTS.verify_unchanged(result))
        self.assertEqual(FIXTURES.tree_bytes(self.fixture.root), before)

    def test_admission_never_discovers_or_runs_current_compiler(self):
        with mock.patch.object(INPUTS.COMPILE.PROCESS, "inspect_compiler",
                               side_effect=AssertionError("historical compiler is not needed")), \
                mock.patch.object(INPUTS.COMPILE.PROCESS, "run_command",
                                  side_effect=AssertionError("admission cannot execute commands")):
            self.assertEqual(self.admit()["compiled_manifest"], self.manifest)
        identity = copy.deepcopy(self.fixture.compiler["identity"])
        for name, tool in identity["tools"].items():
            tool["path"] = "/nonexistent/old-installed-compiler/" + name
        self.assertEqual(INPUTS._recorded_compiler(identity), {"identity": identity})

    def test_missing_final_manifest_is_not_complete_compilation(self):
        self.manifest_path.unlink()
        with self.assertRaises((ValueError, OSError)):
            self.admit()

    def test_missing_receipt_cannot_be_recovered_from_object_or_manifest(self):
        next((self.compilation / "receipts").iterdir()).unlink()
        with self.assertRaisesRegex(ValueError, "runtime_compile_missing_objects"):
            self.admit()

    def test_contract_recipe_types_hashes_and_source_identity_must_match(self):
        original = INPUTS.COMPILE.read_canonical(self.plan_path)
        for mutation in ("schema", "flags", "hash", "coordinator", "extra"):
            with self.subTest(mutation=mutation):
                plan = copy.deepcopy(original)
                if mutation == "schema":
                    plan["schema_version"] = True
                elif mutation == "flags":
                    plan["contract"]["compile_flags"].append("-Ofast")
                elif mutation == "hash":
                    plan["contract_sha256"] = "0" * 64
                elif mutation == "coordinator":
                    plan["contract"]["coordinator"]["compile_private_title.py"] = "0" * 64
                else:
                    plan["extra"] = None
                self.write_json(self.plan_path, plan)
                with self.assertRaises(ValueError):
                    self.admit()
        self.write_json(self.plan_path, original)

    def test_compiled_manifest_bool_aliases_and_extra_claims_are_rejected(self):
        for mutation in ({"library_loaded": 0}, {"runtime_binding_enforced": True},
                         {"schema_version": True}, {"extra": False}, {"objects": []}):
            with self.subTest(mutation=mutation):
                self.write_json(self.manifest_path, {**copy.deepcopy(self.manifest), **mutation})
                with self.assertRaisesRegex(ValueError, "runtime_compiled_manifest_mismatch"):
                    self.admit()
        self.write_json(self.manifest_path, self.manifest)

    def test_metadata_must_be_canonical_and_duplicate_key_free(self):
        old = self.manifest_path.read_bytes()
        for data in (b" " + old, b'{"schema_version":1,"schema_version":1}'):
            with self.subTest(data=data[:40]):
                self.manifest_path.write_bytes(data)
                with self.assertRaises(ValueError):
                    self.admit()
        self.manifest_path.write_bytes(old)

    def test_changed_library_and_receipted_objects_are_rejected(self):
        receipt = INPUTS.COMPILE.read_canonical(next((self.compilation / "receipts").iterdir()))
        for path in (self.library, self.compilation / receipt["object"]["path"]):
            with self.subTest(path=path.name):
                original = path.read_bytes()
                self.fixture.mutate(path)
                with self.assertRaises(ValueError):
                    self.admit()
                path.chmod(0o600)
                path.write_bytes(original)
                path.chmod(0o400)

    def test_native_artifacts_must_remain_readonly(self):
        receipt = INPUTS.COMPILE.read_canonical(next((self.compilation / "receipts").iterdir()))
        for path in (self.library, self.compilation / receipt["object"]["path"],
                     self.compilation / "binding/identity.c"):
            with self.subTest(path=path.name):
                path.chmod(0o600)
                with self.assertRaisesRegex(ValueError, "runtime_artifact_must_be_readonly"):
                    self.admit()
                path.chmod(0o400)

    def test_prepared_component_mutation_does_not_rebind_compilation(self):
        path = self.preparation / "prepared/identity/code.bin"
        self.fixture.mutate(path)
        with self.assertRaises(ValueError):
            self.admit()

    def test_changed_success_record_snapshot_selector_is_rejected(self):
        original = INPUTS.INPUTS.load_preparation
        def replace_record(path):
            loaded = original(path)
            report_path = self.preparation / "report.json"
            report = INPUTS.PREP.read_json(report_path)
            report["input"]["snapshot"] = "../input.cxi"
            self.write_json(report_path, report)
            return loaded
        with mock.patch.object(INPUTS.INPUTS, "load_preparation", side_effect=replace_record):
            with self.assertRaisesRegex(ValueError, "runtime_compile_metadata_changed"):
                self.admit()

    def test_compile_lock_blocks_admission_while_compiler_owns_it(self):
        with (self.compilation / ".compile.lock").open("rb") as lock:
            fcntl.flock(lock.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            with self.assertRaisesRegex(ValueError, "compile_directory_in_use"):
                with INPUTS.admitted_inputs(self.preparation, self.compilation):
                    self.fail("admission unexpectedly obtained a busy lock")

    def test_shared_lock_prevents_resume_until_context_exits(self):
        with (self.compilation / ".compile.lock").open("rb") as other:
            with INPUTS.admitted_inputs(self.preparation, self.compilation):
                with self.assertRaises(BlockingIOError):
                    fcntl.flock(other.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            fcntl.flock(other.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)

    def test_replacing_lock_during_use_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "runtime_compile_lock_changed"):
            with INPUTS.admitted_inputs(self.preparation, self.compilation):
                path = self.compilation / ".compile.lock"
                path.unlink()
                path.write_bytes(b"replacement")

    def test_symlink_library_is_rejected(self):
        preserved = self.library.with_name("original-library.so")
        self.library.rename(preserved)
        self.library.symlink_to(preserved.name)
        with self.assertRaisesRegex(ValueError, "symlink_path_rejected"):
            self.admit()

    def test_changed_metadata_after_admission_is_rejected(self):
        with INPUTS.admitted_inputs(self.preparation, self.compilation) as admitted:
            self.write_json(self.manifest_path, {**self.manifest, "runtime_binding_enforced": True})
            with self.assertRaises(ValueError):
                INPUTS.verify_unchanged(admitted)

    def test_recorded_compiler_rejects_wrong_architecture_and_scalar_aliases(self):
        identity = copy.deepcopy(self.fixture.compiler["identity"])
        for mutation in ({"schema_version": True}, {"binary_source_attested": 0},
                         {"host_arch": "other"}, {"target": "invalid target"}, {"tools": {}}):
            with self.subTest(mutation=mutation):
                with self.assertRaises(ValueError):
                    INPUTS._recorded_compiler({**copy.deepcopy(identity), **mutation})


class RuntimeComponentTests(unittest.TestCase):
    """CodexAstraUlt: Original CRO-shaped bytes check bounded unit extraction."""

    @staticmethod
    def cro():
        data = bytearray(0x200)
        data[0x80:0x84] = b"CRO0"
        struct.pack_into("<II", data, 0xC8, 0x140, 2)
        struct.pack_into("<III", data, 0x140, 0x180, 16, 0)
        struct.pack_into("<III", data, 0x14C, 0x190, 8, 1)
        data[0x180:0x190] = bytes(range(16))
        return data

    def test_original_single_code_segment_resolves_exact_raw_bytes(self):
        self.assertEqual(INPUTS._cro_text(self.cro()), (0x180, bytes(range(16))))

    def test_corrupt_cro_extents_and_multiple_code_segments_reject(self):
        cases = []
        data = self.cro(); data[0x80:0x84] = b"BAD!"; cases.append(data)
        data = self.cro(); struct.pack_into("<II", data, 0xC8, 0x1FC, 2); cases.append(data)
        data = self.cro(); struct.pack_into("<I", data, 0xCC, 17); cases.append(data)
        data = self.cro(); struct.pack_into("<I", data, 0x140, 0x1FC); cases.append(data)
        data = self.cro(); struct.pack_into("<I", data, 0x154, 0); cases.append(data)
        data = self.cro(); struct.pack_into("<I", data, 0x148, 1); cases.append(data)
        for data in cases:
            with self.subTest(data=hashlib.sha256(data).hexdigest()):
                with self.assertRaises(ValueError):
                    INPUTS._cro_text(data)

    def test_duplicate_code_rows_reject_before_copying_payload(self):
        # CodexAstraUlt: Instrument only slice reads of the large code payload;
        # header inspection and bounded struct reads remain ordinary byte access.
        class Observed(bytearray):
            payload_slices = 0
            def __getitem__(self, key):
                if isinstance(key, slice) and key.start == 0x180:
                    self.payload_slices += 1
                return super().__getitem__(key)
        data = Observed(self.cro())
        struct.pack_into("<III", data, 0x14C, 0x180, 16, 0)
        with self.assertRaisesRegex(ValueError, "runtime_cro_requires_one_code_segment"):
            INPUTS._cro_text(data)
        self.assertEqual(data.payload_slices, 0)

    def test_inventory_orders_modules_and_excludes_static_code_unit(self):
        fixture = FIXTURES.INPUT_FIXTURES.CompileInputTests(
            "test_valid_preparation_copies_only_readonly_generated_sources")
        fixture.setUp()
        self.addCleanup(fixture.doCleanups)
        prepared = copy.deepcopy(fixture.manifest["prepared"])
        for index, kind in ((2, "cro"), (0, "static_crs"), (1, "cro")):
            blob = bytes(self.cro())
            path = f"identity/module-{index:04}.bin"
            (fixture.run / "prepared" / path).write_bytes(blob)
            prepared["components"].append({"path": path, "kind": kind, "bytes": len(blob),
                "sha256": hashlib.sha256(blob).hexdigest(), "module_name": f"Original{index}",
                "source_path": f"/original{index}.cro"})
        records, units = INPUTS.component_inventory(fixture.run, prepared)
        self.assertEqual(len(records), 6)
        self.assertEqual([unit["name"] for unit in units], [None, "Original1", "Original2"])
        prepared["components"] = [item for item in prepared["components"]
                                  if item.get("module_name") != "Original1"]
        with self.assertRaisesRegex(ValueError, "invalid_runtime_unit_inventory"):
            INPUTS.component_inventory(fixture.run, prepared)


if __name__ == "__main__":
    unittest.main()
