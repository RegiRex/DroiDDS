#!/usr/bin/env python3
"""CodexAstraUlt: Coordinator fault controls plus explicit real-loader integration.

Normal discovery needs no built binary. Running this file with both --worker and
--fixture additionally requires actual bounded execution of an original CXI;
missing evidence fails rather than becoming a skipped or zero-test pass.
"""

import copy
import importlib.util
import json
import os
from pathlib import Path
import signal
import stat
import subprocess
import sys
import tempfile
import time
import unittest
from unittest import mock


# CodexAstraUlt: Import the implementation directly, without altering source or
# sharing a user run directory. All disposable artifacts belong to these tests.
SPEC = importlib.util.spec_from_file_location(
    "private_title", Path(__file__).resolve().parents[1] / "run_private_title.py")
RUNNER = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(RUNNER)
REAL_WORKER = None
REAL_FIXTURE = None


def worker_result(size=512):
    """CodexAstraUlt: Synthetic worker envelopes exercise coordinator gates only."""
    return {
        "schema_version": 1, "tool_version": "0.0.1",
        "kind": "droidds_private_title_interpreter_reconnaissance",
        "runtime_revision": RUNNER.RUNTIME_REVISION, "runtime_has_local_patches": True,
        "status": "guest_exited", "reason": "guest_called_exit_process", "blocker": None,
        "configuration": {
            "model_requested": "old", "model_resolved": "old", "execution": "interpreter",
            "renderer": "software", "strict_diagnostics": True, "native_discovery": False,
            "updates": False, "dlc": False, "texture_packs": False, "enhancements": False,
            "mods_and_cheats": "absent_in_fresh_private_data_directory",
            "idle_loop_skipping": False, "input_events": "neutral", "scanout_captured": False,
            "budget_boundary": {"steps": "before_dispatch_hard", "cycles": "after_system_step",
                                "frames": "after_system_step", "wall": "between_loader_and_steps_parent_hard_timeout"}},
        "limits": {key: value[0] for key, value in RUNNER.LIMITS.items()},
        "input": {"program_id": "000400000FFDD100", "title_name": "TEST", "product_code": "CTR-P-TEST",
                  "container_bytes": size, "ncch_offset": 0, "entry_point": 1048576,
                  "text": {"address": 1048576, "pages": 1, "size": 16},
                  "rodata": {"address": 1052672, "pages": 0, "size": 0},
                  "data": {"address": 1052672, "pages": 0, "size": 0}},
        "observed": {"steps": 4, "cycles": 4, "cycles_after_budget": 0, "frames": 0, "interpreted_instructions": 4,
                     "recompiled_instructions": 0, "elapsed_seconds": 0.01, "guest_exited": True,
                     **{key: 0 for key in RUNNER.FAULT_COUNTERS}}}


class CoordinatorTests(unittest.TestCase):
    """CodexAstraUlt: Exercise failures at file, process and evidence boundaries."""

    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="droidds-title-test-")
        self.root = Path(self.temporary.name)
        self.source = self.root / "original.cxi"
        self.source.write_bytes(bytes(range(256)) * 2)
        self.worker = self.root / "worker"
        self.output = self.root / "run"
        self.fake_worker()

    def tearDown(self):
        self.temporary.cleanup()

    def fake_worker(self, body="", result=None, exit_code=0):
        # CodexAstraUlt: A trusted test executable can inject path/process faults;
        # its synthetic success never substitutes for the real integration mode.
        report = worker_result() if result is None else result
        source = "#!/usr/bin/env python3\nimport json, os, pathlib, sys, time, subprocess\n"
        source += "args = dict(zip(sys.argv[2::2], sys.argv[3::2]))\n"
        source += "pathlib.Path(args['--data-dir']).mkdir(mode=0o700)\n"
        source += body + "\n"
        source += "report = " + repr(report) + "\n"
        source += "pathlib.Path(args['--output']).write_text(json.dumps(report))\n"
        source += "raise SystemExit(" + str(exit_code) + ")\n"
        self.worker.write_text(source)
        self.worker.chmod(0o700)

    def args(self, *extra):
        return RUNNER.parse_args(["--input", str(self.source), "--output", str(self.output),
                                  "--worker", str(self.worker), *extra])

    def execute(self, *extra):
        code, report = RUNNER.run(self.args(*extra))
        if self.output.exists():
            self.assertEqual(json.loads((self.output / "report.json").read_text()), report)
        return code, report

    def test_snapshot_exact_readonly_private_and_bound(self):
        before = self.source.read_bytes()
        code, report = self.execute()
        self.assertEqual(code, 0, report)
        self.assertEqual(report["status"], "guest_exited")
        snapshot = self.output / "input.cxi"
        self.assertEqual(snapshot.read_bytes(), before)
        self.assertEqual(self.source.read_bytes(), before)
        self.assertEqual(stat.S_IMODE(snapshot.stat().st_mode), 0o400)
        self.assertEqual(stat.S_IMODE(self.output.stat().st_mode), 0o700)
        self.assertEqual(stat.S_IMODE((self.output / "report.json").stat().st_mode), 0o600)
        self.assertTrue(report["input"]["stable_before_run"])
        self.assertTrue(report["input"]["stable_after_run"])
        self.assertEqual(len(report["input"]["sha256"]), 64)
        self.assertEqual(len(report["worker"]["sha256"]), 64)
        self.assertFalse(report["worker"]["source"]["binary_source_attested"])
        self.assertNotIn(str(self.source), json.dumps(report))

    def test_existing_output_and_contents_preserved(self):
        self.output.mkdir()
        saved = self.output / "save.bin"
        saved.write_bytes(b"owner save")
        code, report = RUNNER.run(self.args())
        self.assertNotEqual(code, 0)
        self.assertEqual(report["reason"], "output_must_be_absent_with_existing_parent")
        self.assertEqual(list(self.output.iterdir()), [saved])
        self.assertEqual(saved.read_bytes(), b"owner save")

    def test_output_inside_git_directory_or_worktree_rejected(self):
        for is_file in (False, True):
            with self.subTest(worktree=is_file):
                repository = self.root / ("worktree" if is_file else "repo")
                repository.mkdir()
                marker = repository / ".git"
                marker.write_text("gitdir: elsewhere") if is_file else marker.mkdir()
                if not is_file:
                    (marker / "HEAD").write_text("ref: refs/heads/main\n")
                self.output = repository / "private"
                code, report = self.execute()
                self.assertNotEqual(code, 0)
                self.assertEqual(report["reason"], "output_must_be_outside_git")
                self.assertFalse(self.output.exists())

    def test_symlink_input_and_output_parent_rejected(self):
        link = self.root / "linked.cxi"
        link.symlink_to(self.source)
        self.source = link
        self.assertEqual(self.execute()[1]["reason"], "symlink_path_rejected")
        self.source = self.root / "original.cxi"
        link_parent = self.root / "linked-directory"
        link_parent.symlink_to(self.root, target_is_directory=True)
        self.output = link_parent / "new"
        self.assertEqual(self.execute()[1]["reason"], "symlink_path_rejected")

    def test_empty_fifo_and_bounded_input_rejected(self):
        self.source.write_bytes(b"")
        self.assertNotEqual(self.execute()[0], 0)
        self.source.unlink()
        os.mkfifo(self.source)
        self.assertNotEqual(self.execute()[0], 0)
        self.source.unlink()
        self.source.write_bytes(b"x" * 513)
        with mock.patch.object(RUNNER, "MAX_INPUT_BYTES", 512):
            self.assertNotEqual(self.execute()[0], 0)

    def test_native_input_and_unknown_flags_rejected(self):
        self.source = self.root / "native.so"
        self.source.write_bytes(b"ELF")
        self.assertEqual(self.execute()[1]["reason"], "input_must_be_base_ncch_ncsd_or_cia")
        with mock.patch("sys.stderr"), self.assertRaises(SystemExit):
            self.args("--updates", "unexpected.cia")

    def test_nonfinite_zero_and_excessive_limits_rejected(self):
        for arguments in (("--timeout", "nan"), ("--max-steps", "0"),
                          ("--max-seconds", "301"), ("--memory-mib", "1")):
            with self.subTest(arguments=arguments), mock.patch("sys.stderr"), self.assertRaises(SystemExit):
                self.args(*arguments)

    def test_disk_space_check_precedes_creation(self):
        with mock.patch.object(RUNNER.shutil, "disk_usage", return_value=mock.Mock(free=1)):
            code, report = self.execute()
        self.assertNotEqual(code, 0)
        self.assertEqual(report["reason"], "insufficient_disk_space_for_snapshot")
        self.assertFalse(self.output.exists())

    def test_snapshot_mutation_is_failure_and_preserved(self):
        self.fake_worker("snapshot = pathlib.Path(args['--input'])\nsnapshot.chmod(0o600)\nsnapshot.write_bytes(b'changed')")
        code, report = self.execute()
        self.assertNotEqual(code, 0)
        self.assertEqual(report["status"], "input_changed")
        self.assertIn("snapshot", report["reason"])
        self.assertEqual((self.output / "input.cxi").read_bytes(), b"changed")
        self.assertEqual(self.source.stat().st_size, 512)

    def test_original_mutation_is_detected_without_restoration(self):
        self.fake_worker("pathlib.Path(" + repr(str(self.source)) + ").write_bytes(b'edited externally')")
        code, report = self.execute()
        self.assertNotEqual(code, 0)
        self.assertEqual(report["status"], "input_changed")
        self.assertIn("source", report["reason"])
        self.assertEqual(self.source.read_bytes(), b"edited externally")

    def test_loader_failure_zero_counters_remains_failure(self):
        result = worker_result()
        result.update(status="load_error", reason="loader_rejected", input=None)
        result["observed"].update(steps=0, cycles=0, interpreted_instructions=0, guest_exited=False)
        self.fake_worker(result=result, exit_code=2)
        code, report = self.execute()
        self.assertNotEqual(code, 0)
        self.assertEqual(report["status"], "load_error")
        self.assertIsNotNone(report["worker_report"])
        self.assertTrue((self.output / "input.cxi").exists())

    def test_zero_execution_unknown_identity_native_counter_and_false_budget_fail(self):
        for mutation in ("zero", "pin", "native", "budget", "boolean", "exit"):
            with self.subTest(mutation=mutation):
                result = worker_result()
                if mutation == "zero":
                    result["observed"].update(steps=0, interpreted_instructions=0)
                elif mutation == "pin":
                    result["runtime_revision"] = "0" * 40
                elif mutation == "native":
                    result["observed"]["recompiled_instructions"] = 1
                elif mutation == "budget":
                    result.update(status="budget_exhausted", reason="step_budget")
                elif mutation == "boolean":
                    result["observed"]["steps"] = True
                else:
                    result["observed"]["guest_exited"] = False
                with self.assertRaises(RUNNER.Rejected):
                    RUNNER.validate_worker(result, {**result["limits"], "model": "old", "timeout": 40}, 512, 0)

    def test_invalid_shapes_and_unreported_runtime_fault_rejected(self):
        for key in ("configuration", "observed"):
            result = worker_result()
            result[key] = []
            with self.subTest(key=key), self.assertRaises(RUNNER.Rejected):
                RUNNER.validate_worker(result, {**worker_result()["limits"], "model": "old", "timeout": 40}, 512, 0)
        for key in RUNNER.FAULT_COUNTERS:
            result = worker_result()
            result["observed"][key] = 1
            with self.subTest(key=key), self.assertRaises(RUNNER.Rejected):
                RUNNER.validate_worker(result, {**result["limits"], "model": "old", "timeout": 40}, 512, 0)

    def test_atomic_cycle_overshoot_explicit_and_consistent(self):
        result = worker_result()
        result.update(status="budget_exhausted", reason="cycle_budget")
        result["limits"]["max_cycles"] = 1
        result["observed"].update(steps=1, interpreted_instructions=1, cycles=151, cycles_after_budget=150, guest_exited=False)
        requested = {**result["limits"], "model": "old", "timeout": 40}
        RUNNER.validate_worker(result, requested, 512, 0)
        result["observed"]["cycles"] = 152
        with self.assertRaises(RUNNER.Rejected):
            RUNNER.validate_worker(result, requested, 512, 0)

    def test_missing_malformed_and_symlink_reports_fail(self):
        for mutation in ("missing", "malformed", "symlink", "duplicate"):
            with self.subTest(mutation=mutation):
                self.output = self.root / ("run-" + mutation)
                body = {
                    "missing": "raise SystemExit(0)",
                    "malformed": "pathlib.Path(args['--output']).write_text('broken')\nraise SystemExit(0)",
                    "symlink": "pathlib.Path(args['--output']).symlink_to(args['--input'])\nraise SystemExit(0)",
                    "duplicate": "pathlib.Path(args['--output']).write_text('{\"x\":1,\"x\":2}')\nraise SystemExit(0)",
                }[mutation]
                self.fake_worker(body)
                code, report = self.execute()
                self.assertNotEqual(code, 0)
                self.assertEqual(report["status"], "rejected")

    def test_log_tail_is_bounded_while_pipe_is_drained(self):
        self.fake_worker("sys.stdout.write('x' * 262144)\nsys.stdout.flush()")
        code, report = self.execute()
        self.assertEqual(code, 0, report)
        self.assertEqual((self.output / "worker.log").stat().st_size, RUNNER.LOG_BYTES)
        self.assertEqual(report["process"]["log_bytes_emitted"], 262144)
        self.assertTrue(report["process"]["log_truncated"])

    def test_timeout_preserves_results_and_kills_descendant(self):
        self.fake_worker("child = subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(60)'])\n"
                         "pathlib.Path('child.pid').write_text(str(child.pid))\ntime.sleep(60)")
        code, report = self.execute("--timeout", "0.3")
        self.assertEqual(code, 124)
        self.assertEqual(report["status"], "timed_out")
        self.assertTrue((self.output / "input.cxi").exists())
        child = int((self.output / "child.pid").read_text())
        # A reparented zombie is dead but may await the container init's reap.
        proc = Path(f"/proc/{child}/stat")
        if proc.exists():
            self.assertEqual(proc.read_text().split()[2], "Z")

    def run_interrupted(self, interruption):
        self.fake_worker("pathlib.Path('started').touch()\ntime.sleep(60)")
        command = [sys.executable, str(Path(RUNNER.__file__)), "--input", str(self.source),
                   "--output", str(self.output), "--worker", str(self.worker)]
        process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        try:
            deadline = time.monotonic() + 10
            while not (self.output / "started").exists() and time.monotonic() < deadline:
                time.sleep(0.02)
            self.assertTrue((self.output / "started").exists())
            process.send_signal(interruption)
            process.communicate(timeout=10)
            self.assertEqual(process.returncode, 130)
            report = json.loads((self.output / "report.json").read_text())
            self.assertEqual(report["status"], "interrupted")
        finally:
            if process.poll() is None:
                process.kill()
                process.communicate()

    def test_interrupt_preserves_final_report(self):
        self.run_interrupted(signal.SIGINT)

    def test_sigterm_preserves_final_report(self):
        self.run_interrupted(signal.SIGTERM)


class RealWorkerIntegration(unittest.TestCase):
    """CodexAstraUlt: Real original-fixture loader/execution and malformed control."""

    def test_real_original_fixture_executes_and_hashes(self):
        self.assertTrue(REAL_WORKER.is_file(), "Build the real worker before integration")
        self.assertTrue(REAL_FIXTURE.is_file(), "Emit the original runtime fixture before integration")
        with tempfile.TemporaryDirectory(prefix="droidds-title-real-") as temporary:
            output = Path(temporary) / "run"
            args = RUNNER.parse_args(["--input", str(REAL_FIXTURE), "--output", str(output),
                                      "--worker", str(REAL_WORKER), "--max-seconds", "5", "--timeout", "10"])
            code, report = RUNNER.run(args)
            self.assertEqual(code, 0, json.dumps(report, indent=2))
            self.assertEqual(report["status"], "guest_exited", report)
            observed = report["worker_report"]["observed"]
            self.assertGreater(observed["interpreted_instructions"], 0)
            self.assertTrue(observed["guest_exited"])
            self.assertEqual(observed["recompiled_instructions"], 0)
            self.assertTrue(report["input"]["stable_after_run"])
            self.assertEqual(report["worker_report"]["input"]["program_id"], "000400000D5D0005")

    def test_real_malformed_container_records_loader_failure(self):
        with tempfile.TemporaryDirectory(prefix="droidds-title-bad-") as temporary:
            root = Path(temporary)
            source = root / "malformed.cxi"
            source.write_bytes(b"Not an executable NCCH container" * 32)
            args = RUNNER.parse_args(["--input", str(source), "--output", str(root / "run"),
                                      "--worker", str(REAL_WORKER), "--max-seconds", "5", "--timeout", "10"])
            code, report = RUNNER.run(args)
            self.assertNotEqual(code, 0)
            self.assertEqual(report["status"], "load_error", report)
            self.assertEqual(report["worker_report"]["observed"]["steps"], 0)
            self.assertTrue((root / "run" / "input.cxi").exists())


def load_tests(loader, tests, pattern):
    # CodexAstraUlt: Discovery is intentionally host-only; real integration is an
    # explicit required build gate, never a skip concealed in the normal count.
    suite = loader.loadTestsFromTestCase(CoordinatorTests)
    if REAL_WORKER is not None:
        suite.addTests(loader.loadTestsFromTestCase(RealWorkerIntegration))
    return suite


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    parser.add_argument("--worker", type=Path)
    parser.add_argument("--fixture", type=Path)
    options, remaining = parser.parse_known_args()
    if bool(options.worker) != bool(options.fixture):
        parser.error("--worker and --fixture are required together")
    if options.worker is not None:
        REAL_WORKER, REAL_FIXTURE = options.worker.resolve(), options.fixture.resolve()
    unittest.main(argv=[sys.argv[0], *remaining])
