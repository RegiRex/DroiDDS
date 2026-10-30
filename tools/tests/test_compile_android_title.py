#!/usr/bin/env python3
"""CodexAstraUlt: Android recipe controls and opt-in real NDK fixture compilation.

Pass --sdk and --worker for actual original NCCH preparation, ARM64 compilation,
resume and static-audit controls. Default discovery tests metadata without claiming
that an SDK or cross-compiled library was exercised. No generated code is loaded.
"""

import argparse
import contextlib
import copy
import fcntl
import importlib.util
import io
import json
import os
from pathlib import Path
import shutil
import struct
import tempfile
import unittest
from unittest import mock


TOOLS = Path(__file__).resolve().parents[1]


def load(name):
    spec = importlib.util.spec_from_file_location("android_tests_" + name, TOOLS / (name + ".py"))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


RUN = load("compile_android_title")
FIXTURES = load("tests/test_prepare_private_title")
REAL_SDK, REAL_WORKER = None, None


def recorded_compiler():
    """CodexAstraUlt: Authored metadata tests schema rules, not actual provenance."""
    record = {"bytes": 32, "sha256": "1" * 64}
    runtime = {"sysroot/usr/lib/aarch64-linux-android/29/" + name: dict(record) for name in
               ("libc.so", "libm.so", "libdl.so", "crtbegin_so.o", "crtend_so.o")}
    runtime["lib/clang/18/lib/linux/libclang_rt.builtins-aarch64-android.a"] = dict(record)
    return {"schema_version": 1, "family": "clang", "version": "Android clang version 18.0",
            "target": "aarch64-unknown-linux-android29", "host_arch": "x86_64", "ndk": RUN.NDK_VERSION,
            "minimum_api": 29, "tools": {name: {"path": "/original/bin/" + name, **record}
                for name in ("wrapper", "driver", "linker")}, "properties": dict(record),
            "headers": {name: {"files": 1, **record} for name in ("sysroot", "clang")},
            "runtime_files": runtime, "binary_source_attested": False}


class AndroidRecipeTests(unittest.TestCase):
    """CodexAstraUlt: Target/toolchain policies are distinct from native host builds."""

    def test_recorded_compiler_metadata_is_strict_and_does_not_run_tools(self):
        value = recorded_compiler()
        with mock.patch.object(RUN.PROCESS, "run_command", side_effect=AssertionError("no tool execution")):
            self.assertEqual(RUN._recorded_compiler(value), {"identity": value})
        for field, mutation in (("schema_version", True), ("minimum_api", True), ("ndk", "27.0"),
                                ("target", "x86_64-linux-gnu"), ("tools", None), ("headers", []),
                                ("runtime_files", {}), ("binary_source_attested", True)):
            bad = copy.deepcopy(value)
            bad[field] = mutation
            with self.subTest(field=field), self.assertRaises(ValueError):
                RUN._recorded_compiler(bad)

    def test_header_and_tool_content_identities_cannot_be_omitted(self):
        for field in ("tools", "headers", "runtime_files"):
            value = recorded_compiler()
            first = next(iter(value[field].values()))
            first["sha256"] = "not-a-digest"
            with self.subTest(field=field), self.assertRaises(ValueError):
                RUN._recorded_compiler(value)

    def test_recipe_binds_target_headers_flags_and_has_no_fast_math(self):
        loaded = {"manifest_sha256": "2" * 64, "manifest": {"input": {"bytes": 8, "sha256": "3" * 64},
                  "prepared": {"program_id": "000400000d5d0005"}}, "module_count": 0,
                  "generated": [{"path": "generated/a.c", "bytes": 1, "sha256": "4" * 64}],
                  "sources": ["generated/a.c"]}
        plan = RUN.make_plan(loaded, {"identity": recorded_compiler()})
        contract = plan["contract"]
        self.assertEqual((contract["target"], contract["minimum_api"], contract["machine"], contract["libc"]),
                         ("aarch64-linux-android", 29, 183, "bionic"))
        self.assertIn("-ffp-contract=off", contract["compile_flags"])
        self.assertIn("-O2", contract["compile_flags"])
        self.assertNotIn("-ffast-math", contract["compile_flags"])
        self.assertIn("-Wl,-z,max-page-size=16384", contract["link_flags"])
        changed = recorded_compiler()
        changed["headers"]["sysroot"]["sha256"] = "f" * 64
        self.assertNotEqual(RUN.make_plan(loaded, {"identity": changed})["contract_sha256"], plan["contract_sha256"])

    def test_android_dependency_policy_does_not_mutate_host_validator(self):
        self.assertIn("libm.so.6", RUN.BASE.ELF.DEPENDENCIES)
        self.assertNotIn("libm.so", RUN.BASE.ELF.DEPENDENCIES)
        self.assertEqual(RUN.ANDROID_ELF.ELF.DEPENDENCIES, {"libc.so", "libm.so", "libdl.so"})
        with self.assertRaises(ValueError):
            RUN.ANDROID_ELF.audit_object(Path("missing"), 62)

    def test_options_reject_duplicate_unbounded_and_implicit_sdk(self):
        base = ["--preparation", "/tmp/original", "--output", "/tmp/new", "--sdk", "/tmp/sdk"]
        for bad in (["--batch-seconds", "nan"], ["--cpu-seconds", "0"], ["--resume", "--resume"],
                    ["--memory-mib", "255"], ["--output-mib", "8193"], ["--cc", "/tmp/foreign"]):
            with self.subTest(bad=bad), contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
                RUN.parse_args(base + bad)


def tree_bytes(directory):
    return {path.relative_to(directory).as_posix(): path.read_bytes()
            for path in directory.rglob("*") if path.is_file()}


class RealAndroidCompilationTests(unittest.TestCase):
    """CodexAstraUlt: Explicit SDK gate uses real original generated ARM64 code."""

    @classmethod
    def setUpClass(cls):
        cls.temporary = tempfile.TemporaryDirectory(prefix="droidds-android-compiler-original-")
        cls.root = Path(cls.temporary.name)
        cls.input = cls.root / "original.cxi"
        cls.input.write_bytes(FIXTURES.original_ncch())
        cls.preparation = cls.root / "preparation"
        args = RUN.PREP.parse_args(["--input", str(cls.input), "--output", str(cls.preparation), "--worker", str(REAL_WORKER)])
        code, report = RUN.PREP.run(args)
        if code != 0:
            raise AssertionError(report)
        cls.compiler = RUN.inspect_android_compiler(REAL_SDK / "ndk" / RUN.NDK_VERSION /
            "toolchains/llvm/prebuilt/linux-x86_64/bin/aarch64-linux-android29-clang")

    @classmethod
    def tearDownClass(cls):
        cls.temporary.cleanup()

    def setUp(self):
        self.case = self.root / self._testMethodName
        self.case.mkdir()
        self.prep = self.case / "preparation"
        shutil.copytree(self.preparation, self.prep)
        self.output = self.case / "Android output with owner's apostrophe"
        self.before = tree_bytes(self.prep)
        # CodexAstraUlt: Discovery was genuinely run above; repeated coordinator
        # controls retain that identity and actual executable invocation.
        patch = mock.patch.object(RUN, "inspect_android_compiler", return_value=copy.deepcopy(self.compiler))
        patch.start()
        self.addCleanup(patch.stop)

    def args(self, *extra):
        return RUN.parse_args(["--preparation", str(self.prep), "--output", str(self.output),
            "--sdk", str(REAL_SDK), "--batch-seconds", "120", "--command-seconds", "30",
            "--cpu-seconds", "30", "--memory-mib", "2048", "--output-mib", "64", *extra])

    def execute(self, *extra):
        with contextlib.redirect_stdout(io.StringIO()):
            return RUN.run(self.args(*extra))

    def build(self):
        code, report = self.execute()
        self.assertEqual(code, 0, report)
        self.assertEqual(report["status"], "compiled")
        self.assertEqual(tree_bytes(self.prep), self.before)
        return RUN.BASE.read_canonical(self.output / "compiled-manifest.json")

    def test_real_bionic_compile_full_table_audit_and_manifest_binding(self):
        manifest = self.build()
        self.assertEqual(manifest["target"], RUN.TARGET)
        self.assertTrue(manifest["elf"]["runtime_tables_validated"])
        self.assertEqual(set(manifest["elf"]["load_alignments"]), {16384})
        self.assertFalse(manifest["library_loaded"])
        self.assertFalse(manifest["guest_execution_performed"])
        with RUN.admitted_android_inputs(self.prep, self.output) as admitted:
            asset = RUN.title_manifest(admitted)
            self.assertEqual(asset["input"], manifest["input"])
            self.assertEqual(asset["native"]["sha256"], manifest["library"]["sha256"])
            self.assertEqual(asset["native"]["file"], "libdroidds_title.so")
            self.assertTrue(RUN.verify_unchanged(admitted))
        self.assertEqual(self.input.read_bytes(), FIXTURES.original_ncch())

    def test_resume_reuses_verified_objects_and_preserves_prior_reports(self):
        original_factory = RUN._engine
        def limited_engine(preparation):
            engine = original_factory(preparation)
            command = engine.command_result
            count = 0
            def one(*args):
                nonlocal count
                count += 1
                return command(*args) if count == 1 else None
            engine.command_result = one
            return engine
        with mock.patch.object(RUN, "_engine", side_effect=limited_engine):
            code, first = self.execute()
        self.assertEqual((code, first["reason"], first["objects_ready"]), (2, "batch_budget", 1))
        old_report = Path(first["report_path"]).read_bytes()
        old_receipts = tree_bytes(self.output / "receipts")
        code, resumed = self.execute("--resume")
        self.assertEqual(code, 0, resumed)
        self.assertEqual(resumed["objects_reused"], 1)
        self.assertEqual(Path(first["report_path"]).read_bytes(), old_report)
        for name, data in old_receipts.items():
            self.assertEqual((self.output / "receipts" / name).read_bytes(), data)

    def test_completed_resume_performs_no_compilation(self):
        manifest = self.build()
        before = tree_bytes(self.output / "receipts")
        code, report = self.execute("--resume")
        self.assertEqual(code, 0, report)
        self.assertEqual(report["commands"], [])
        self.assertEqual(report["objects_compiled"], 0)
        self.assertEqual(tree_bytes(self.output / "receipts"), before)
        self.assertEqual(RUN.BASE.read_canonical(self.output / "compiled-manifest.json"), manifest)

    def test_corrupt_object_rejects_resume_without_replacing_it(self):
        manifest = self.build()
        object_path = self.output / manifest["objects"][0]["object"]["path"]
        object_path.chmod(0o600)
        object_path.write_bytes(b"broken original object")
        object_path.chmod(0o400)
        code, report = self.execute("--resume")
        self.assertNotEqual(code, 0)
        self.assertEqual(report["reason"], "compiled_object_changed")
        self.assertEqual(object_path.read_bytes(), b"broken original object")

    def test_changed_preparation_rejects_before_compiler_discovery(self):
        path = next((self.prep / "prepared/generated").glob("*.h"))
        path.chmod(0o600)
        path.write_bytes(path.read_bytes() + b"/* changed original control */")
        with mock.patch.object(RUN, "inspect_android_compiler", side_effect=AssertionError("no tool execution")):
            code, report = self.execute()
        self.assertNotEqual(code, 0, report)
        self.assertFalse((self.output / "compiled-manifest.json").exists())

    def test_alignment_origin_and_dependency_mutations_reject(self):
        manifest = self.build()
        with RUN.admitted_android_inputs(self.prep, self.output) as admitted:
            library = admitted["library_path"]
            arguments = (admitted["plan"]["contract"]["preparation_sha256"],
                         admitted["plan"]["contract_sha256"], admitted["units"])
            original = library.read_bytes()
            for mutation in ("alignment", "dependency", "origin"):
                data = bytearray(original)
                units = copy.deepcopy(arguments[2])
                if mutation == "alignment":
                    start = struct.unpack_from("<Q", data, 32)[0]
                    width, count = struct.unpack_from("<HH", data, 54)
                    for index in range(count):
                        offset = start + index * width
                        if struct.unpack_from("<I", data, offset)[0] == 1:
                            struct.pack_into("<Q", data, offset + 48, 4096)
                elif mutation == "dependency":
                    offset = data.index(b"libm.so\0")
                    data[offset:offset + 7] = b"libx.so"
                else:
                    units[0]["text"] = bytes([units[0]["text"][0] ^ 1]) + units[0]["text"][1:]
                changed = self.case / (mutation + ".so")
                changed.write_bytes(data)
                with self.subTest(mutation=mutation), self.assertRaises(ValueError):
                    RUN.ANDROID_ELF.audit_library(changed, arguments[0], arguments[1], units)

    def test_shared_admission_lock_rejects_compile_writer(self):
        self.build()
        with RUN.admitted_android_inputs(self.prep, self.output):
            code, report = self.execute("--resume")
            self.assertNotEqual(code, 0)
            self.assertEqual(report["reason"], "compile_directory_in_use")

    def test_recorded_host_contract_cannot_admit_as_android(self):
        self.build()
        path = self.output / "compile-plan.json"
        plan = RUN.BASE.read_canonical(path)
        plan["contract"]["compiler"]["target"] = "x86_64-linux-gnu"
        path.chmod(0o600)
        path.write_bytes(RUN.PREP.canonical(plan))
        with self.assertRaises(ValueError):
            with RUN.admitted_android_inputs(self.prep, self.output):
                self.fail("host target admitted as Android")


def load_tests(loader, tests, pattern):
    suite = loader.loadTestsFromTestCase(AndroidRecipeTests)
    if REAL_SDK is not None and REAL_WORKER is not None:
        suite.addTests(loader.loadTestsFromTestCase(RealAndroidCompilationTests))
    return suite


if __name__ == "__main__":
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("--sdk", type=Path)
    parser.add_argument("--worker", type=Path)
    args, remaining = parser.parse_known_args()
    if bool(args.sdk) != bool(args.worker):
        parser.error("real Android integration requires both --sdk and --worker")
    if args.sdk:
        REAL_SDK, REAL_WORKER = args.sdk.resolve(strict=True), args.worker.resolve(strict=True)
    unittest.main(argv=[__file__, *remaining])
