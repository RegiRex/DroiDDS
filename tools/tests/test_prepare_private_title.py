#!/usr/bin/env python3
"""CodexAstraUlt: Preparation identity/process controls with optional real generation.

Default discovery uses original synthetic output fixtures. Explicit --worker and
--fixture add real strict resolution/emission without executing any guest code.
"""

import copy
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import stat
import sys
import tempfile
import unittest
from unittest import mock


# CodexAstraUlt: Load the exact coordinator without modifying shared import state.
SPEC = importlib.util.spec_from_file_location("prepare_title", Path(__file__).resolve().parents[1] / "prepare_private_title.py")
RUNNER = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(RUNNER)
REAL_WORKER = None
REAL_FIXTURE = None


def fixture():
    """CodexAstraUlt: Original bytes bind scalar identities and logical segment hashes."""
    header, exheader = bytearray(512), bytearray(1024)
    header[0x100:0x104] = b"NCCH"
    header[0x112:0x114] = (2).to_bytes(2, "little")
    header[0x118:0x120] = (0x000400000FFDD100).to_bytes(8, "little")
    exheader[0x10:0x1C] = b"".join(value.to_bytes(4, "little") for value in (0x100000, 1, 16))
    exheader[0x20:0x24] = exheader[0x30:0x34] = (0x101000).to_bytes(4, "little")
    blobs = {"identity/exheader.bin": bytes(exheader), "identity/ncch-header.bin": bytes(header),
             "identity/code.bin": bytes(range(16)), "generated/program.c": b"int original(void) { return 17; }\n",
             "generated/recomp.h": b"/* original fixture */\n"}
    report = {"schema_version": 1, "kind": "droidds_title_preparation", "status": "prepared",
              "container": "ncch", "program_id": "000400000ffdd100", "ncch_format_version": 2,
              "remaster_version": 0, "cia_title_version": None, "abi": 4, "generation": 3,
              "hints": "disabled", "overlays": [], "runtime_resolution_checked": True,
              "runtime_binding_enforced": False, "bss_size": 0,
              "components": [{"path": path, "kind": kind, "bytes": len(blobs[path])} for path, kind in
                             (("identity/exheader.bin", "exheader"), ("identity/ncch-header.bin", "ncch_header"),
                              ("identity/code.bin", "decompressed_code"))],
              "segments": [{"name": "text", "address": 0x100000, "offset": 0, "size": 16, "mapped_bytes": 4096},
                           {"name": "rodata", "address": 0x101000, "offset": 4096, "size": 0, "mapped_bytes": 0},
                           {"name": "data", "address": 0x101000, "offset": 4096, "size": 0, "mapped_bytes": 0}],
              "artifacts": [{"path": path, "bytes": len(blobs[path])} for path in blobs if path.startswith("generated/")],
              "sources": ["generated/program.c"]}
    return report, blobs


def original_ncch():
    """CodexAstraUlt: A minimal original ARM return is container input, not a retail title."""
    image = bytearray(0x1000)
    image[0x100:0x104] = b"NCCH"
    image[0x104:0x108] = (8).to_bytes(4, "little")
    image[0x112:0x114] = (2).to_bytes(2, "little")
    image[0x118:0x120] = (0x000400000FFDD100).to_bytes(8, "little")
    image[0x180:0x184] = (0x400).to_bytes(4, "little")
    image[0x18F] = 0x04
    image[0x1A0:0x1A4] = (3).to_bytes(4, "little")
    image[0x1A4:0x1A8] = (2).to_bytes(4, "little")
    image[0x210:0x21C] = b"".join(value.to_bytes(4, "little") for value in (0x100000, 1, 4))
    image[0x600:0x608] = b".code\0\0\0"
    image[0x60C:0x610] = (4).to_bytes(4, "little")
    image[0x800:0x804] = (0xE12FFF1E).to_bytes(4, "little")
    return bytes(image)


class PreparationTests(unittest.TestCase):
    """CodexAstraUlt: Public fixtures exercise output honesty and preserve failed evidence."""

    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="droidds-prepare-test-")
        self.root = Path(self.temporary.name)
        self.input = self.root / "original.cxi"
        self.input.write_bytes(bytes(range(256)) * 2)
        self.worker = self.root / "worker"
        self.output = self.root / "first"
        # CodexAstraUlt: Unrelated concurrent source edits are irrelevant to
        # these process-control fixtures; real integrations use actual identity.
        self.identity = mock.patch.object(RUNNER, "source_identity", return_value={
            "checkout_commit": "1" * 40, "checkout_dirty": False, "binary_source_attested": False,
            "files_sha256": {"Cargo.lock": "2" * 64}})
        self.identity.start()
        self.addCleanup(self.identity.stop)
        self.addCleanup(self.temporary.cleanup)
        self.fake_worker()

    def fake_worker(self, before="", after="", report=None, blobs=None, exit_code=0):
        """CodexAstraUlt: Failure injection is test-only and never represents a game result."""
        expected, contents = fixture()
        report = expected if report is None else report
        blobs = contents if blobs is None else blobs
        source = "#!/usr/bin/env python3\nimport json, os, pathlib, sys, time\n"
        source += "args = dict(zip(sys.argv[2::2], sys.argv[3::2]))\n"
        source += "out = pathlib.Path(args['--output'])\nout.mkdir(mode=0o700)\n"
        source += before + "\n"
        source += "blobs = " + repr(blobs) + "\n"
        source += "for path, data in blobs.items():\n target = out / path\n target.parent.mkdir(exist_ok=True)\n target.write_bytes(data)\n"
        source += "report = " + repr(report) + "\n(out / 'prepare-report.json').write_text(json.dumps(report))\n"
        source += after + "\nraise SystemExit(" + str(exit_code) + ")\n"
        self.worker.write_text(source)
        self.worker.chmod(0o700)

    def args(self, *extra):
        return RUNNER.parse_args(["--input", str(self.input), "--output", str(self.output), "--worker", str(self.worker), *extra])

    def execute(self, *extra):
        code, report = RUNNER.run(self.args(*extra))
        if self.output.is_dir():
            self.assertEqual(json.loads((self.output / "report.json").read_text()), report)
        if code:
            self.assertFalse((self.output / "manifest.json").exists(), report)
        return code, report

    def test_snapshot_manifest_and_artifacts_bind_actual_bytes(self):
        original = self.input.read_bytes()
        code, report = self.execute()
        self.assertEqual(code, 0, report)
        manifest_bytes = (self.output / "manifest.json").read_bytes()
        manifest = json.loads(manifest_bytes)
        self.assertEqual(manifest_bytes, RUNNER.canonical(manifest))
        self.assertEqual(report["manifest_sha256"], hashlib.sha256(manifest_bytes).hexdigest())
        self.assertEqual(manifest["stage"], "prepared")
        self.assertFalse(manifest["runtime_binding_enforced"])
        self.assertFalse(manifest["guest_execution_performed"])
        self.assertEqual(manifest["input"]["sha256"], hashlib.sha256(original).hexdigest())
        self.assertEqual(manifest["worker"]["sha256"], hashlib.sha256(self.worker.read_bytes()).hexdigest())
        for item in manifest["prepared"]["components"] + manifest["prepared"]["artifacts"]:
            self.assertEqual(item["sha256"], hashlib.sha256((self.output / "prepared" / item["path"]).read_bytes()).hexdigest())
        self.assertEqual(manifest["prepared"]["segments"][0]["sha256"], hashlib.sha256(bytes(range(16))).hexdigest())
        self.assertEqual(manifest["prepared"]["segments"][1]["sha256"], hashlib.sha256(b"").hexdigest())
        self.assertEqual(self.input.read_bytes(), original)
        self.assertEqual((self.output / "input.cxi").read_bytes(), original)
        self.assertEqual(stat.S_IMODE((self.output / "input.cxi").stat().st_mode), 0o400)
        self.assertEqual(stat.S_IMODE((self.output / "manifest.json").stat().st_mode), 0o600)
        self.assertEqual(stat.S_IMODE(self.output.stat().st_mode), 0o700)
        self.assertNotIn(str(self.root), manifest_bytes.decode())
        self.assertTrue(report["input"]["stable_before_run"] and report["input"]["stable_after_run"])

    def test_two_fresh_preparations_have_identical_manifests(self):
        self.assertEqual(self.execute()[0], 0)
        first = (self.output / "manifest.json").read_bytes()
        self.output = self.root / "second"
        self.assertEqual(self.execute()[0], 0)
        self.assertEqual((self.output / "manifest.json").read_bytes(), first)

    def test_failed_worker_does_not_publish_plausible_manifest(self):
        self.fake_worker(exit_code=2)
        code, report = self.execute()
        self.assertNotEqual(code, 0)
        self.assertEqual(report["reason"], "worker_exit_2")
        self.assertTrue((self.output / "prepared/prepare-report.json").exists())

    def test_sigkill_retains_failed_outcome_and_partial_artifacts(self):
        self.fake_worker(after="os.kill(os.getpid(), 9)")
        self.assertEqual(self.execute()[1]["reason"], "worker_signal_9")
        self.assertTrue((self.output / "prepared/identity/code.bin").exists())

    def test_timeout_retains_partial_output(self):
        self.fake_worker(after="time.sleep(5)")
        code, report = self.execute("--timeout", "0.1")
        self.assertEqual(code, 124)
        self.assertEqual(report["status"], "timed_out")
        self.assertTrue((self.output / "prepared/prepare-report.json").exists())

    def test_host_limits_are_installed_without_worker_flags(self):
        self.fake_worker(after="import resource\nassert resource.getrlimit(resource.RLIMIT_CPU) == (260, 260)\nassert len(args) == 2\n")
        code, report = self.execute()
        self.assertEqual(code, 0, report)
        self.assertEqual(report["process"]["cpu_limit"]["hard_seconds"], 260)

    def test_existing_output_is_not_changed(self):
        self.output.mkdir()
        marker = self.output / "owner-save"
        marker.write_bytes(b"preserve")
        code, report = RUNNER.run(self.args())
        self.assertNotEqual(code, 0)
        self.assertEqual(report["reason"], "output_must_be_absent_with_existing_parent")
        self.assertEqual(list(self.output.iterdir()), [marker])
        self.assertEqual(marker.read_bytes(), b"preserve")

    def test_git_and_symlink_destinations_are_rejected(self):
        repo = self.root / "repository"
        repo.mkdir()
        (repo / ".git").write_text("gitdir: some-existing-worktree")
        self.output = repo / "run"
        self.assertEqual(self.execute()[1]["reason"], "output_must_be_outside_git")
        linked = self.root / "linked"
        linked.symlink_to(self.root, target_is_directory=True)
        self.output = linked / "run"
        self.assertEqual(self.execute()[1]["reason"], "symlink_path_rejected")

    def test_source_and_worker_mutation_are_rejected(self):
        self.fake_worker(after="source = pathlib.Path(args['--input'])\nsource.chmod(0o600)\nsource.write_bytes(b'changed snapshot')")
        self.assertEqual(self.execute()[1]["status"], "input_changed")
        self.assertEqual(self.input.read_bytes(), bytes(range(256)) * 2)
        self.assertEqual((self.output / "input.cxi").read_bytes(), b"changed snapshot")
        self.output = self.root / "changed-worker"
        self.fake_worker(after="pathlib.Path(sys.argv[0]).write_text('# changed')")
        self.assertEqual(self.execute()[1]["status"], "input_changed")

    def test_nonregular_or_symlink_output_is_rejected(self):
        for index, command in enumerate(("target.symlink_to(out / 'identity/code.bin')", "os.mkfifo(target)")):
            with self.subTest(command=command):
                self.output = self.root / str(index)
                self.fake_worker(after="target = out / 'generated/program.c'\ntarget.unlink()\n" + command)
                self.assertEqual(self.execute()[1]["status"], "rejected")

    def test_extra_missing_and_wrong_size_outputs_are_rejected(self):
        cases = ("(out / 'extra').write_bytes(b'unreported')", "(out / 'empty-extra').mkdir()",
                 "(out / 'identity/code.bin').unlink()", "(out / 'generated/program.c').write_bytes(b'wrong length')")
        for index, command in enumerate(cases):
            with self.subTest(command=command):
                self.output = self.root / str(index)
                self.fake_worker(after=command)
                self.assertEqual(self.execute()[1]["status"], "rejected")

    def test_duplicate_or_escaping_inventory_paths_are_rejected(self):
        for index, bad in enumerate(("../other.c", "/absolute.c", "generated/../escape.c", "generated//a.c", "generated/..", "generated/program.c")):
            with self.subTest(path=bad):
                report, _ = fixture()
                report["artifacts"].append({"path": bad, "bytes": 1})
                self.fake_worker(report=report)
                self.output = self.root / str(index)
                self.assertEqual(self.execute()[1]["status"], "rejected")

    def test_invalid_contract_and_unclaimed_native_execution_are_rejected(self):
        mutations = ({"runtime_binding_enforced": True}, {"runtime_resolution_checked": False}, {"abi": 3},
                     {"hints": "ambient"}, {"overlays": ["update"]}, {"program_id": "0004000e0ffdd100"},
                     {"program_id": "0004008c0ffdd100"}, {"schema_version": True}, {"container": "cia"},
                     {"unexpected": "field"}, {"sources": []}, {"cia_title_version": 1})
        for index, mutation in enumerate(mutations):
            with self.subTest(mutation=mutation):
                report, _ = fixture()
                report.update(mutation)
                self.fake_worker(report=report)
                self.output = self.root / str(index)
                self.assertEqual(self.execute()[1]["status"], "rejected")

    def test_malformed_json_duplicate_keys_and_nonfinite_rejected(self):
        for index, data in enumerate(("{", '{"schema_version":1,"schema_version":1}', '{"x":NaN}')):
            with self.subTest(data=data):
                self.output = self.root / str(index)
                self.fake_worker(after="(out / 'prepare-report.json').write_text(" + repr(data) + ")")
                self.assertEqual(self.execute()[1]["status"], "rejected")

    def test_report_component_and_segment_bounds_rejected(self):
        changes = (("size", 17), ("mapped_bytes", 1), ("offset", 1), ("address", 2**32 - 1), ("size", True))
        for index, (field, value) in enumerate(changes):
            with self.subTest(field=field, value=value):
                report, _ = fixture()
                report["segments"][0][field] = value
                self.fake_worker(report=report)
                self.output = self.root / str(index)
                self.assertEqual(self.execute()[1]["status"], "rejected")

    def test_valid_shaped_descriptor_disagreements_are_rejected(self):
        for index, mutation in enumerate(({"program_id": "000400000ffdd101"}, {"ncch_format_version": 1},
                                          {"remaster_version": 1}, {"bss_size": 4})):
            with self.subTest(mutation=mutation):
                report, _ = fixture()
                report.update(mutation)
                self.fake_worker(report=report)
                self.output = self.root / str(index)
                self.assertEqual(self.execute()[1]["reason"], "preparation_descriptor_identity_mismatch")

    def test_output_admission_limits_are_enforced(self):
        for field, ceiling in (("MAX_FILES", 4), ("MAX_PREPARED_BYTES", 1), ("MAX_FILE_BYTES", 10)):
            with self.subTest(field=field):
                self.output = self.root / field
                with mock.patch.object(RUNNER, field, ceiling):
                    self.assertEqual(self.execute()[1]["status"], "rejected")

    def test_source_context_change_blocks_publication(self):
        with mock.patch.object(RUNNER, "source_identity", side_effect=[{"source": 1}, {"source": 2}]):
            self.assertEqual(self.execute()[1]["reason"], "preparation_source_changed")

    def test_partial_or_interrupted_manifest_write_has_no_final_name(self):
        # CodexAstraUlt: A partial write or failed fsync must not expose the
        # success filename, while the owned incomplete temporary is preserved.
        original_write = RUNNER.COMMON.write_new
        for index, error in enumerate((OSError("disk full"), KeyboardInterrupt())):
            with self.subTest(error=type(error).__name__):
                self.output = self.root / str(index)

                def interrupted_write(path, content):
                    if path.name == ".manifest.json.tmp":
                        original_write(path, content[:17])
                        raise error
                    return original_write(path, content)

                with mock.patch.object(RUNNER.COMMON, "write_new", side_effect=interrupted_write):
                    code, report = self.execute()
                self.assertNotEqual(code, 0, report)
                self.assertEqual((self.output / ".manifest.json.tmp").stat().st_size, 17)
                self.assertFalse((self.output / "manifest.json").exists())

    def test_manifest_publication_refuses_existing_file_or_symlink(self):
        # CodexAstraUlt: A final-path collision preserves the prior object;
        # atomic publication must never replace it with the prepared manifest.
        for index, symlink in enumerate((False, True)):
            with self.subTest(symlink=symlink):
                directory = self.root / str(index)
                directory.mkdir()
                target = directory / "preserved"
                target.write_bytes(b"existing owner data")
                final = directory / "manifest.json"
                if symlink:
                    final.symlink_to(target)
                else:
                    final.write_bytes(b"existing final")
                with self.assertRaises(FileExistsError):
                    RUNNER.publish_manifest(directory, b"new valid manifest\n")
                self.assertEqual(target.read_bytes(), b"existing owner data")
                self.assertEqual(final.read_bytes(), b"existing owner data" if symlink else b"existing final")
                self.assertEqual(final.is_symlink(), symlink)
                self.assertEqual((directory / ".manifest.json.tmp").read_bytes(), b"new valid manifest\n")

    def test_descriptor_changed_after_hash_is_rejected(self):
        # CodexAstraUlt: Mutate otherwise uninterpreted bytes after the first
        # component hash; parsed fields alone would still appear consistent.
        original_identity = RUNNER.file_identity
        for index, filename in enumerate(("identity/ncch-header.bin", "identity/exheader.bin")):
            with self.subTest(filename=filename):
                self.output = self.root / str(index)

                def changed_descriptor(directory, item):
                    identity = original_identity(directory, item)
                    if item["path"] == filename:
                        path = directory / filename
                        data = bytearray(path.read_bytes())
                        data[-1] ^= 1
                        path.write_bytes(data)
                    return identity

                with mock.patch.object(RUNNER, "file_identity", side_effect=changed_descriptor):
                    self.assertEqual(self.execute()[1]["reason"], "preparation_descriptor_changed")

    def test_invalid_arguments_reject_before_output_creation(self):
        for flags in (("--timeout", "nan"), ("--timeout", "0"), ("--timeout", "311"),
                      ("--cpu-seconds", "0"), ("--cpu-seconds", "312"), ("--memory-mib", "255"),
                      ("--updates", "unknown"), ("--timeout", "1", "--timeout", "2")):
            with self.subTest(flags=flags), self.assertRaises(SystemExit):
                self.args(*flags)
        self.assertFalse(self.output.exists())


class RealPreparationTests(unittest.TestCase):
    """CodexAstraUlt: Explicit integration requires actual original-fixture C generation."""

    def test_real_fixture_prepares_twice_with_identical_manifest(self):
        with tempfile.TemporaryDirectory(prefix="droidds-real-prepare-") as temporary:
            source = REAL_FIXTURE or Path(temporary) / "original.cxi"
            if REAL_FIXTURE is None:
                source.write_bytes(original_ncch())
            outputs = []
            for index in range(2):
                output = Path(temporary) / str(index)
                args = RUNNER.parse_args(["--input", str(source), "--worker", str(REAL_WORKER), "--output", str(output)])
                code, report = RUNNER.run(args)
                self.assertEqual(code, 0, report)
                outputs.append((output / "manifest.json").read_bytes())
            self.assertEqual(outputs[0], outputs[1])
            manifest = json.loads(outputs[0])
            self.assertEqual(manifest["prepared"]["abi"], 4)
            self.assertTrue(manifest["prepared"]["sources"])
            self.assertFalse(manifest["guest_execution_performed"])

    def test_real_malformed_input_cannot_publish_manifest(self):
        with tempfile.TemporaryDirectory(prefix="droidds-real-prepare-bad-") as temporary:
            root = Path(temporary)
            source = root / "bad.cxi"
            source.write_bytes(bytes(512))
            args = RUNNER.parse_args(["--input", str(source), "--worker", str(REAL_WORKER), "--output", str(root / "run")])
            code, report = RUNNER.run(args)
            self.assertNotEqual(code, 0, report)
            self.assertFalse((root / "run/manifest.json").exists())
            self.assertEqual(source.read_bytes(), bytes(512))


def load_tests(loader, tests, pattern):
    """CodexAstraUlt: Missing binaries are not silent integration passes or skipped tests."""
    suite = loader.loadTestsFromTestCase(PreparationTests)
    if REAL_WORKER is not None:
        suite.addTests(loader.loadTestsFromTestCase(RealPreparationTests))
    return suite


if __name__ == "__main__":
    # CodexAstraUlt: Real integration is opt-in; its default input is created
    # from the original fixture above, with an optional explicit fixture path.
    import argparse
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("--worker", type=Path)
    parser.add_argument("--fixture", type=Path)
    args, remaining = parser.parse_known_args()
    if args.fixture and not args.worker:
        parser.error("--fixture requires --worker")
    if args.worker:
        REAL_WORKER = args.worker.resolve(strict=True)
        REAL_FIXTURE = args.fixture.resolve(strict=True) if args.fixture else None
    unittest.main(argv=[sys.argv[0], *remaining])
