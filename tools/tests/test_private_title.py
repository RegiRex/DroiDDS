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

from process_assertions import assert_process_stopped


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
            "scheduler_trace": False, "cpu_progress_trace": False,
            "updates": False, "dlc": False, "texture_packs": False, "enhancements": False,
            "mods_and_cheats": "absent_in_fresh_private_data_directory",
            "idle_loop_skipping": False, "input_events": "neutral", "scanout_captured": False,
            "budget_boundary": {"steps": "before_dispatch_hard", "cycles": "after_system_step",
                                "frames": "after_system_step", "wall": "between_loader_and_steps_parent_hard_timeout"}},
        "diagnostic_trace": None, "cpu_progress": None,
        "limits": {key: value[0] for key, value in RUNNER.LIMITS.items()},
        "input": {"program_id": "000400000FFDD100", "title_name": "TEST", "product_code": "CTR-P-TEST",
                  "container_bytes": size, "ncch_offset": 0, "entry_point": 1048576,
                  "text": {"address": 1048576, "pages": 1, "size": 16},
                  "rodata": {"address": 1052672, "pages": 0, "size": 0},
                  "data": {"address": 1052672, "pages": 0, "size": 0}},
        "observed": {"steps": 4, "cycles": 4, "cycles_after_budget": 0, "frames": 0, "interpreted_instructions": 4,
                     "recompiled_instructions": 0, "elapsed_seconds": 0.01, "guest_exited": True,
                     **{key: 0 for key in RUNNER.FAULT_COUNTERS}}}


def traced_result():
    """CodexAstraUlt: A bounded metadata fixture, never a simulated game pass."""
    result = worker_result()
    result["configuration"]["scheduler_trace"] = True
    result["diagnostic_trace"] = {
        "schema_version": 1, "prefix_capacity": 64, "tail_capacity": 128,
        "thread_capacity": 64, "wait_object_capacity": 8, "pending_capacity": 64,
        "events_seen": 1, "events_omitted": 0, "svc_counts": [{"number": 0x28, "count": 1}],
        "other_svc_calls": 0, "pending_dropped": 0,
        "prefix": [{"sequence": 1, "cycle": 4, "kind": "svc", "entry_cycle": 3,
                    "thread": 0, "pc": 0x100000, "number": 0x28, "args": [0, 0, 0, 0, 0, 0],
                    "returns": [4, 0, 0, 0], "outcome": "returned", "wakeup_at": None}],
        "tail": [], "scheduler": {
            "cycle": 4, "current_thread": 0, "live_pc": 0x100010,
            "reschedule_pending": False, "all_blocked": False, "next_kernel_event": None,
            "threads_total": 1, "threads_truncated": 0,
            "threads": [{"id": 0, "guest_id": 1, "status": "running", "pc": 0x100010,
                         "priority": 0x30, "wakeup_at": None, "wait_all": False,
                         "wait_address": None, "wait_syscall": None,
                         "wait_objects_total": 0, "wait_objects_truncated": 0, "wait_objects": []}]}}
    return result


def progress_result(steps=4):
    """CodexAstraUlt: Literal scalar snapshots test validation, never execution."""
    result = worker_result()
    result["configuration"]["cpu_progress_trace"] = True
    result["observed"].update(steps=steps, cycles=steps, interpreted_instructions=steps,
                              final_pc=0x100000)
    result["limits"]["max_steps"] = max(result["limits"]["max_steps"], steps)

    def state(at):
        return {"steps": at, "cycles": at, "interpreted_instructions": at,
                "registers": [at, *([0] * 14), 0x100000], "cpsr": 0x10,
                "current_thread": 0, "thread_guest_id": 1,
                "reschedule_pending": False, "all_blocked": False}

    seen = 1 + steps // 65521
    prefix = [state(index * 65521) for index in range(min(seen, 16))]
    tail = [state(index * 65521) for index in range(max(16, seen - 112), seen)]
    result["cpu_progress"] = {
        "schema_version": 1, "interval_steps": 65521,
        "prefix_capacity": 16, "tail_capacity": 112,
        "samples_seen": seen, "samples_omitted": seen - len(prefix) - len(tail),
        "prefix": prefix, "tail": tail, "final": state(steps),
        "recent_dispatches": [{"pc": 0x100000, "thumb": False}] * min(steps, 64)}
    return result


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
        # CodexAstraUlt: Parse the two valueless diagnostic flags separately so
        # the mock can enforce activation without corrupting paired arguments.
        source += "args = {}\noptions = iter(sys.argv[2:])\n"
        source += "for flag in options:\n args[flag] = True if flag in ('--trace-scheduler', '--trace-cpu-progress') else next(options)\n"
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

    # CodexAstraUlt: Trace selection is explicit and report-bound; merely
    # running the host coordinator must not activate scheduler instrumentation.
    def test_scheduler_trace_is_opt_in_and_boolean(self):
        self.assertFalse(self.args().trace_scheduler)
        self.assertTrue(self.args("--trace-scheduler").trace_scheduler)
        with mock.patch("sys.stderr"), self.assertRaises(SystemExit):
            self.args("--trace-scheduler=true")
        self.fake_worker("assert '--trace-scheduler' not in sys.argv")
        code, report = self.execute()
        self.assertEqual(code, 0, report)
        self.assertIs(report["requested"]["trace_scheduler"], False)
        self.assertIs(report["worker_report"]["configuration"]["scheduler_trace"], False)
        self.assertIsNone(report["worker_report"]["diagnostic_trace"])

    def test_scheduler_trace_request_must_match_worker_configuration(self):
        for requested, produced in ((True, False), (False, True), (False, 0)):
            result = worker_result()
            result["configuration"]["scheduler_trace"] = produced
            with self.subTest(requested=requested, produced=produced), self.assertRaises(RUNNER.Rejected):
                RUNNER.validate_worker(result, {**result["limits"], "model": "old", "timeout": 40,
                                               "trace_scheduler": requested}, 512, 0)

    def test_requested_trace_required_after_execution_but_not_failed_loading(self):
        result = worker_result()
        result["configuration"]["scheduler_trace"] = True
        requested = {**result["limits"], "model": "old", "timeout": 40, "trace_scheduler": True}
        with self.assertRaisesRegex(RUNNER.Rejected, "requested_scheduler_trace_missing"):
            RUNNER.validate_worker(result, requested, 512, 0)
        result.update(status="load_error", reason="loader_rejected", input=None)
        result["observed"].update(steps=0, cycles=0, interpreted_instructions=0, guest_exited=False)
        RUNNER.validate_worker(result, requested, 512, 2)

    def test_trace_absent_when_not_requested(self):
        result = worker_result()
        result["diagnostic_trace"] = {"unexpected": "must not retain this"}
        with self.assertRaisesRegex(RUNNER.Rejected, "unrequested_scheduler_trace"):
            RUNNER.validate_worker(result, {**result["limits"], "model": "old", "timeout": 40}, 512, 0)

    def test_requested_trace_is_passed_to_worker_and_retained(self):
        self.fake_worker("assert '--trace-scheduler' in sys.argv", result=traced_result())
        code, report = self.execute("--trace-scheduler")
        self.assertEqual(code, 0, report)
        self.assertIs(report["requested"]["trace_scheduler"], True)
        self.assertEqual(report["worker_report"]["diagnostic_trace"]["events_seen"], 1)

    # CodexAstraUlt: A longer trace must disclose the exact lost middle while
    # retaining the original prefix and correctly ordered recent tail.
    def test_trace_retention_and_sequence_accounting(self):
        result = traced_result()
        result["observed"].update(cycles=300, steps=300, interpreted_instructions=300)
        trace = result["diagnostic_trace"]
        event = trace["prefix"][0]
        trace.update(events_seen=300, events_omitted=108,
                     svc_counts=[{"number": 0x28, "count": 300}],
                     prefix=[{**event, "sequence": n, "cycle": n, "entry_cycle": n} for n in range(1, 65)],
                     tail=[{**event, "sequence": n, "cycle": n, "entry_cycle": n} for n in range(173, 301)])
        trace["scheduler"]["cycle"] = 300
        requested = {**result["limits"], "model": "old", "timeout": 40, "trace_scheduler": True}
        RUNNER.validate_worker(result, requested, 512, 0)
        for mutation in ("omitted", "sequence", "time", "counter"):
            changed = copy.deepcopy(result)
            trace = changed["diagnostic_trace"]
            if mutation == "omitted":
                trace["events_omitted"] += 1
            elif mutation == "sequence":
                trace["tail"][0]["sequence"] -= 1
            elif mutation == "time":
                trace["tail"][0]["cycle"] = 0
            else:
                trace["svc_counts"][0]["count"] = 1
            with self.subTest(mutation=mutation), self.assertRaises(RUNNER.Rejected):
                RUNNER.validate_worker(changed, requested, 512, 0)

    def test_trace_payload_bounds_types_and_unfinished_returns_rejected(self):
        for mutation in ("prefix", "threads", "objects", "extra", "boolean", "pc", "return", "cycle", "capacity"):
            result = traced_result()
            trace = result["diagnostic_trace"]
            if mutation == "prefix":
                trace["prefix"] *= 65
            elif mutation == "threads":
                trace["scheduler"]["threads"] *= 65
            elif mutation == "objects":
                trace["scheduler"]["threads"][0]["wait_objects"] = [{}] * 9
            elif mutation == "extra":
                trace["prefix"][0]["guest_text"] = "unreviewed payload"
            elif mutation == "boolean":
                trace["scheduler"]["all_blocked"] = 0
            elif mutation == "pc":
                trace["prefix"][0]["pc"] = 2**32
            elif mutation == "return":
                trace["prefix"][0]["outcome"] = "blocked"
            elif mutation == "cycle":
                trace["scheduler"]["cycle"] += 1
            else:
                trace["tail_capacity"] = 129
            with self.subTest(mutation=mutation), self.assertRaises(RUNNER.Rejected):
                RUNNER.validate_worker(result, {**result["limits"], "model": "old", "timeout": 40,
                                               "trace_scheduler": True}, 512, 0)

    def test_trace_wait_resume_and_final_wait_object_metadata(self):
        result = traced_result()
        trace = result["diagnostic_trace"]
        trace["events_seen"] = 3
        trace["prefix"] += [
            {"sequence": 2, "cycle": 4, "kind": "schedule", "previous_thread": None, "next_thread": 0},
            {"sequence": 3, "cycle": 4, "kind": "wait_resume", "thread": 0, "guest_id": 1,
             "number": 0x24, "svc_pc": 0x100004, "return_pc": 0x100008,
             "returns": [0x09401BFE, 0, 0, 0], "wait_result": "timed_out", "signaled_index": None}]
        thread = trace["scheduler"]["threads"][0]
        thread.update(status="wait_sync", wakeup_at=100, wait_syscall=0x24,
                      wait_objects_total=1, wait_objects=[{
                          "id": 4, "kind": "Event", "signaled": False,
                          "owner": None, "count": None, "deadline": None}])
        requested = {**result["limits"], "model": "old", "timeout": 40, "trace_scheduler": True}
        RUNNER.validate_worker(result, requested, 512, 0)
        trace["prefix"][-1]["signaled_index"] = 0
        with self.assertRaises(RUNNER.Rejected):
            RUNNER.validate_worker(result, requested, 512, 0)

    # CodexAstraUlt: Progress sampling is independently requested and report
    # bound; neither the scheduler flag nor a truthy integer can activate it.
    def test_cpu_progress_is_opt_in_and_boolean(self):
        self.assertFalse(self.args().trace_cpu_progress)
        self.assertFalse(self.args("--trace-scheduler").trace_cpu_progress)
        self.assertTrue(self.args("--trace-cpu-progress").trace_cpu_progress)
        self.assertFalse(self.args("--trace-cpu-progress").trace_scheduler)
        with mock.patch("sys.stderr"), self.assertRaises(SystemExit):
            self.args("--trace-cpu-progress=true")
        self.fake_worker("assert '--trace-cpu-progress' not in sys.argv")
        code, report = self.execute()
        self.assertEqual(code, 0, report)
        self.assertIs(report["requested"]["trace_cpu_progress"], False)
        self.assertIs(report["worker_report"]["configuration"]["cpu_progress_trace"], False)
        self.assertIsNone(report["worker_report"]["cpu_progress"])

    def test_cpu_progress_request_and_configuration_must_match(self):
        for requested, produced in ((True, False), (False, True), (False, 0), (0, False), (1, True)):
            result = worker_result()
            result["configuration"]["cpu_progress_trace"] = produced
            with self.subTest(requested=requested, produced=produced), self.assertRaises(RUNNER.Rejected):
                RUNNER.validate_worker(result, {**result["limits"], "model": "old", "timeout": 40,
                                               "trace_cpu_progress": requested}, 512, 0)

    def test_cpu_progress_required_after_execution_and_absent_when_disabled(self):
        result = worker_result()
        result["configuration"]["cpu_progress_trace"] = True
        requested = {**result["limits"], "model": "old", "timeout": 40, "trace_cpu_progress": True}
        with self.assertRaisesRegex(RUNNER.Rejected, "requested_cpu_progress_trace_missing"):
            RUNNER.validate_worker(result, requested, 512, 0)
        result.update(status="load_error", reason="loader_rejected", input=None)
        result["observed"].update(steps=0, cycles=0, interpreted_instructions=0, guest_exited=False)
        RUNNER.validate_worker(result, requested, 512, 2)
        result = worker_result()
        result["cpu_progress"] = {"unrequested": "metadata"}
        with self.assertRaisesRegex(RUNNER.Rejected, "unrequested_cpu_progress_trace"):
            RUNNER.validate_worker(result, {**result["limits"], "model": "old", "timeout": 40}, 512, 0)

    def test_cpu_progress_flag_forwarded_independently_and_with_scheduler(self):
        for scheduler in (False, True):
            result = progress_result()
            if scheduler:
                traced = traced_result()
                result["configuration"]["scheduler_trace"] = True
                result["diagnostic_trace"] = traced["diagnostic_trace"]
                result["diagnostic_trace"]["scheduler"]["live_pc"] = result["observed"]["final_pc"]
            self.output = self.root / ("both" if scheduler else "progress-only")
            self.fake_worker("assert '--trace-cpu-progress' in sys.argv\n"
                             f"assert ('--trace-scheduler' in sys.argv) is {scheduler!r}", result=result)
            flags = ["--trace-cpu-progress", *(["--trace-scheduler"] if scheduler else [])]
            code, report = self.execute(*flags)
            self.assertEqual(code, 0, report)
            self.assertIs(report["requested"]["trace_cpu_progress"], True)
            self.assertEqual(report["worker_report"]["cpu_progress"]["final"]["steps"], 4)
            self.assertIn("crates/droidds-title-tools/src/cpu_progress.rs",
                          report["worker"]["source"]["files_sha256"])

    # CodexAstraUlt: The retained middle can be absent, but its exact size and
    # sample cadence must remain verifiable through both retained segments.
    def test_cpu_progress_retention_cadence_and_counter_order(self):
        result = progress_result(10_000_000)
        requested = {**result["limits"], "model": "old", "timeout": 40, "trace_cpu_progress": True}
        RUNNER.validate_worker(result, requested, 512, 0)
        trace = result["cpu_progress"]
        self.assertEqual(trace["samples_seen"], 153)
        self.assertEqual(trace["samples_omitted"], 25)
        self.assertEqual(len(trace["prefix"]), 16)
        self.assertEqual(len(trace["tail"]), 112)
        for mutation in ("seen", "omitted", "cadence", "cycle_order", "instruction_order", "final"):
            changed = copy.deepcopy(result)
            trace = changed["cpu_progress"]
            if mutation == "seen":
                trace["samples_seen"] += 1
            elif mutation == "omitted":
                trace["samples_omitted"] -= 1
            elif mutation == "cadence":
                trace["tail"][0]["steps"] += 1
            elif mutation == "cycle_order":
                trace["tail"][0]["cycles"] = 0
            elif mutation == "instruction_order":
                trace["tail"][0]["interpreted_instructions"] = 0
            else:
                trace["final"]["cycles"] -= 1
            with self.subTest(mutation=mutation), self.assertRaises(RUNNER.Rejected):
                RUNNER.validate_worker(changed, requested, 512, 0)

    # CodexAstraUlt: On the exact cadence CPU state must match; a frame/HID hook
    # after periodic sampling can still request a reschedule before final capture.
    def test_cpu_progress_boundary_final_matches_last_retained_sample(self):
        for steps in (65521, 65521 * 140):
            result = progress_result(steps)
            requested = {**result["limits"], "model": "old", "timeout": 40, "trace_cpu_progress": True}
            RUNNER.validate_worker(result, requested, 512, 0)
            after_hook = copy.deepcopy(result)
            after_hook["cpu_progress"]["final"]["reschedule_pending"] = True
            RUNNER.validate_worker(after_hook, requested, 512, 0)
            for field in ("registers", "cpsr"):
                changed = copy.deepcopy(result)
                final = changed["cpu_progress"]["final"]
                if field == "registers":
                    final[field][0] += 1
                else:
                    final[field] += 1
                with self.subTest(steps=steps, field=field), self.assertRaisesRegex(
                        RUNNER.Rejected, "cpu_progress_final_sample_mismatch"):
                    RUNNER.validate_worker(changed, requested, 512, 0)

    def test_cpu_progress_and_scheduler_final_state_must_agree(self):
        result = progress_result()
        result["configuration"]["scheduler_trace"] = True
        result["diagnostic_trace"] = traced_result()["diagnostic_trace"]
        result["diagnostic_trace"]["scheduler"]["live_pc"] = result["observed"]["final_pc"]
        requested = {**result["limits"], "model": "old", "timeout": 40,
                     "trace_cpu_progress": True, "trace_scheduler": True}
        RUNNER.validate_worker(result, requested, 512, 0)
        for field in ("live_pc", "current_thread", "reschedule_pending", "all_blocked", "guest_id"):
            changed = copy.deepcopy(result)
            scheduler = changed["diagnostic_trace"]["scheduler"]
            if field == "live_pc":
                scheduler[field] += 4
            elif field == "current_thread":
                scheduler[field] = None
            elif field == "guest_id":
                scheduler["threads"][0][field] += 1
            else:
                scheduler[field] = True
            with self.subTest(field=field), self.assertRaisesRegex(
                    RUNNER.Rejected, "cpu_progress_scheduler"):
                RUNNER.validate_worker(changed, requested, 512, 0)

    def test_cpu_progress_payload_bounds_types_and_final_binding(self):
        for mutation in ("prefix", "tail", "history", "extra", "state_extra", "dispatch_extra",
                         "register_count", "register_type", "register_bound", "boolean", "cpsr",
                         "current_thread", "thread_pair", "pc", "thumb", "alignment", "version",
                         "interval", "capacity", "final_steps", "final_instructions", "final_pc"):
            result = progress_result()
            trace = result["cpu_progress"]
            if mutation == "prefix":
                trace["prefix"] *= 17
            elif mutation == "tail":
                trace["tail"] = trace["prefix"] * 113
            elif mutation == "history":
                trace["recent_dispatches"] *= 17
            elif mutation == "extra":
                trace["guest_bytes"] = [1, 2, 3]
            elif mutation == "state_extra":
                trace["final"]["thread_name"] = "unreviewed"
            elif mutation == "dispatch_extra":
                trace["recent_dispatches"][0]["opcode"] = 0
            elif mutation == "register_count":
                trace["final"]["registers"].pop()
            elif mutation == "register_type":
                trace["final"]["registers"][0] = True
            elif mutation == "register_bound":
                trace["final"]["registers"][0] = 2**32
            elif mutation == "boolean":
                trace["final"]["all_blocked"] = 0
            elif mutation == "cpsr":
                trace["final"]["cpsr"] = -1
            elif mutation == "current_thread":
                trace["final"]["current_thread"] = True
            elif mutation == "thread_pair":
                trace["final"]["thread_guest_id"] = None
            elif mutation == "pc":
                trace["recent_dispatches"][0]["pc"] = 2**32
            elif mutation == "thumb":
                trace["recent_dispatches"][0]["thumb"] = 0
            elif mutation == "alignment":
                trace["recent_dispatches"][0]["pc"] += 2
            elif mutation == "version":
                trace["schema_version"] = True
            elif mutation == "interval":
                trace["interval_steps"] += 1
            elif mutation == "capacity":
                trace["tail_capacity"] += 1
            elif mutation == "final_steps":
                trace["final"]["steps"] -= 1
            elif mutation == "final_instructions":
                trace["final"]["interpreted_instructions"] -= 1
            else:
                trace["final"]["registers"][15] += 4
            with self.subTest(mutation=mutation), self.assertRaises(RUNNER.Rejected):
                RUNNER.validate_worker(result, {**result["limits"], "model": "old", "timeout": 40,
                                               "trace_cpu_progress": True}, 512, 0)

    def test_cpu_progress_final_after_short_run_and_unattributed_idle_state(self):
        result = progress_result()
        trace = result["cpu_progress"]
        self.assertEqual(trace["samples_seen"], 1)
        self.assertEqual(trace["prefix"][0]["steps"], 0)
        self.assertEqual(trace["final"]["steps"], 4)
        trace["final"].update(current_thread=None, thread_guest_id=None, all_blocked=True,
                              reschedule_pending=True)
        trace["recent_dispatches"][0] = {"pc": 0x100002, "thumb": True}
        RUNNER.validate_worker(result, {**result["limits"], "model": "old", "timeout": 40,
                                       "trace_cpu_progress": True}, 512, 0)

    def test_nonfinite_zero_and_excessive_limits_rejected(self):
        for arguments in (("--timeout", "nan"), ("--max-steps", "0"),
                          ("--max-seconds", "301"), ("--memory-mib", "1")):
            with self.subTest(arguments=arguments), mock.patch("sys.stderr"), self.assertRaises(SystemExit):
                self.args(*arguments)

    # CodexAstraUlt: Existing commands retain their exact CPU cap; an explicit
    # thread-CPU allowance is independent of the worker and parent wall bounds.
    def test_cpu_budget_defaults_and_explicit_wall_independence(self):
        self.assertEqual(self.args().cpu_seconds, 41)
        for timeout, expected in (("130", 131), ("0.3", 2), ("310", 311)):
            with self.subTest(timeout=timeout):
                self.assertEqual(self.args("--timeout", timeout).cpu_seconds, expected)
                self.assertEqual(self.args("--timeout", timeout, "--cpu-seconds", "260").cpu_seconds, 260)

    def test_invalid_cpu_budgets_are_rejected_before_run_creation(self):
        for value in ("0", "-1", "1.5", "nan", "inf", "312"):
            with self.subTest(value=value), mock.patch("sys.stderr"), self.assertRaises(SystemExit):
                self.args("--cpu-seconds", value)
        self.assertFalse(self.output.exists())

    # CodexAstraUlt: Inspect kernel limits in a real child, not just a mocked
    # setrlimit call; the Rust worker must never receive this parent-only flag.
    def test_cpu_budget_is_installed_reported_and_not_forwarded(self):
        for name, flags, expected in (("default", [], 41),
                                      ("explicit", ["--timeout", "130", "--cpu-seconds", "260"], 260)):
            with self.subTest(name=name):
                self.output = self.root / ("run-" + name)
                self.fake_worker("import resource\n"
                                 "assert '--cpu-seconds' not in sys.argv\n"
                                 "pathlib.Path('observed-cpu.json').write_text(\n"
                                 "    json.dumps(resource.getrlimit(resource.RLIMIT_CPU)))")
                code, report = self.execute(*flags)
                self.assertEqual(code, 0, report)
                self.assertEqual(json.loads((self.output / "observed-cpu.json").read_text()),
                                 [expected, expected])
                self.assertEqual(report["requested"]["cpu_seconds"], expected)
                self.assertEqual(report["process"]["cpu_limit"], {
                    "soft_seconds": expected, "hard_seconds": expected,
                    "scope": "per_process_all_threads"})

    # CodexAstraUlt: A CPU-bound child reaches its independent hard limit before
    # the parent deadline, retaining partial evidence without inventing totals.
    def test_cpu_exhaustion_retains_failed_outcome_and_partial_evidence(self):
        self.fake_worker("pathlib.Path('checkpoint.txt').write_text('partial')\n"
                         "while True:\n    pass")
        code, report = self.execute("--timeout", "10", "--cpu-seconds", "1")
        self.assertNotEqual(code, 0)
        self.assertEqual(report["status"], "worker_failed")
        self.assertEqual(report["reason"], "worker_signal_9")
        self.assertIsNone(report["worker_report"])
        self.assertEqual((self.output / "checkpoint.txt").read_text(), "partial")
        self.assertEqual((self.output / "input.cxi").read_bytes(), self.source.read_bytes())
        self.assertTrue(report["input"]["stable_after_run"])

    # CodexAstraUlt: Even a plausible report cannot turn an unrelated SIGKILL
    # into completed execution or a claim that the CPU cap caused termination.
    def test_self_sigkill_never_accepts_prewritten_worker_report(self):
        self.fake_worker("pathlib.Path(args['--output']).write_text(json.dumps(" +
                         repr(worker_result()) + "))\n"
                         "os.kill(os.getpid(), 9)")
        code, report = self.execute("--cpu-seconds", "260")
        self.assertNotEqual(code, 0)
        self.assertEqual(report["status"], "worker_failed")
        self.assertEqual(report["reason"], "worker_signal_9")
        self.assertIsNone(report["worker_report"])
        self.assertEqual(json.loads((self.output / "worker-report.json").read_text()), worker_result())

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
        # CodexAstraUlt: A larger CPU allowance must not weaken the short parent
        # wall deadline or leave a sleeping descendant alive after timeout.
        code, report = self.execute("--timeout", "0.3", "--cpu-seconds", "260")
        self.assertEqual(code, 124)
        self.assertEqual(report["status"], "timed_out")
        self.assertTrue((self.output / "input.cxi").exists())
        child = int((self.output / "child.pid").read_text())
        # CodexAstraUlt: Preserve descendant-death checking while allowing the
        # normal reaper to remove /proc during this single state observation.
        assert_process_stopped(self, child)

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

    # CodexAstraUlt: An explicit parent CPU allowance must reach the real Rust
    # worker without changing its CLI, guest work, input or execution settings.
    def test_real_explicit_cpu_budget_preserves_guest_execution(self):
        reports = []
        with tempfile.TemporaryDirectory(prefix="droidds-title-cpu-") as temporary:
            for index, flags in enumerate(([], ["--cpu-seconds", "260"])):
                args = RUNNER.parse_args([
                    "--input", str(REAL_FIXTURE), "--output", str(Path(temporary) / str(index)),
                    "--worker", str(REAL_WORKER), "--max-seconds", "5", "--timeout", "10", *flags])
                code, report = RUNNER.run(args)
                self.assertEqual(code, 0, json.dumps(report, indent=2))
                self.assertEqual(report["status"], "guest_exited")
                reports.append(report)
        self.assertEqual([report["requested"]["cpu_seconds"] for report in reports], [11, 260])
        self.assertEqual(reports[0]["worker"]["sha256"], reports[1]["worker"]["sha256"])
        self.assertEqual(reports[0]["input"]["sha256"], reports[1]["input"]["sha256"])
        self.assertEqual(reports[0]["worker_report"]["configuration"],
                         reports[1]["worker_report"]["configuration"])
        observations = [{key: value for key, value in report["worker_report"]["observed"].items()
                         if key != "elapsed_seconds"} for report in reports]
        self.assertEqual(observations[0], observations[1])

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

    # CodexAstraUlt: The real original container proves trace-enabled metadata
    # passes the coordinator while execution/rendering counters stay unchanged.
    def test_real_trace_preserves_execution_and_retains_bounded_metadata(self):
        reports = []
        with tempfile.TemporaryDirectory(prefix="droidds-title-trace-") as temporary:
            for enabled in (False, True):
                argv = ["--input", str(REAL_FIXTURE), "--output", str(Path(temporary) / str(enabled)),
                        "--worker", str(REAL_WORKER), "--max-seconds", "5", "--timeout", "10"]
                if enabled:
                    argv.append("--trace-scheduler")
                code, report = RUNNER.run(RUNNER.parse_args(argv))
                self.assertEqual(code, 0, json.dumps(report, indent=2))
                self.assertEqual(report["status"], "guest_exited")
                reports.append(report)
        self.assertEqual(reports[0]["worker"]["sha256"], reports[1]["worker"]["sha256"])
        self.assertEqual(reports[0]["input"]["sha256"], reports[1]["input"]["sha256"])
        baseline, traced = [report["worker_report"] for report in reports]
        self.assertIsNone(baseline["diagnostic_trace"])
        observations = [{key: value for key, value in report["observed"].items()
                         if key != "elapsed_seconds"} for report in (baseline, traced)]
        self.assertEqual(observations[0], observations[1])
        trace = traced["diagnostic_trace"]
        self.assertGreater(trace["events_seen"], 0)
        self.assertTrue(trace["svc_counts"])
        self.assertTrue(any(event["kind"] == "svc" and event["number"] == 3
                            and event["outcome"] == "process_exited"
                            for event in trace["prefix"] + trace["tail"]))

    # CodexAstraUlt: Exercise real worker/coordinator agreement for the new
    # flag alone and alongside SVC tracing, preserving actual guest work.
    def test_real_cpu_progress_preserves_execution_with_and_without_scheduler(self):
        reports = []
        with tempfile.TemporaryDirectory(prefix="droidds-title-progress-") as temporary:
            for index, flags in enumerate(([], ["--trace-cpu-progress"],
                                           ["--trace-cpu-progress", "--trace-scheduler"])):
                argv = ["--input", str(REAL_FIXTURE), "--output", str(Path(temporary) / str(index)),
                        "--worker", str(REAL_WORKER), "--max-seconds", "5", "--timeout", "10", *flags]
                code, report = RUNNER.run(RUNNER.parse_args(argv))
                self.assertEqual(code, 0, json.dumps(report, indent=2))
                self.assertEqual(report["status"], "guest_exited")
                reports.append(report)
        self.assertEqual(len({report["worker"]["sha256"] for report in reports}), 1)
        self.assertEqual(len({report["input"]["sha256"] for report in reports}), 1)
        workers = [report["worker_report"] for report in reports]
        self.assertIsNone(workers[0]["cpu_progress"])
        observed = [{key: value for key, value in report["observed"].items()
                     if key != "elapsed_seconds"} for report in workers]
        self.assertEqual(observed[0], observed[1])
        self.assertEqual(observed[0], observed[2])
        for report in workers[1:]:
            progress = report["cpu_progress"]
            self.assertEqual(progress["samples_seen"], 1)
            self.assertEqual(progress["samples_omitted"], 0)
            self.assertEqual(progress["prefix"][0]["steps"], 0)
            self.assertEqual(progress["final"]["steps"], 606)
            self.assertEqual(len(progress["recent_dispatches"]), 64)
            self.assertEqual(progress["final"]["registers"][15], report["observed"]["final_pc"])
        self.assertEqual(workers[1]["cpu_progress"], workers[2]["cpu_progress"])
        self.assertIsNone(workers[1]["diagnostic_trace"])
        self.assertIsNotNone(workers[2]["diagnostic_trace"])

    def test_real_malformed_container_records_loader_failure(self):
        with tempfile.TemporaryDirectory(prefix="droidds-title-bad-") as temporary:
            root = Path(temporary)
            source = root / "malformed.cxi"
            source.write_bytes(b"Not an executable NCCH container" * 32)
            args = RUNNER.parse_args(["--input", str(source), "--output", str(root / "run"),
                                      "--worker", str(REAL_WORKER), "--max-seconds", "5", "--timeout", "10",
                                      "--trace-scheduler", "--trace-cpu-progress"])
            code, report = RUNNER.run(args)
            self.assertNotEqual(code, 0)
            self.assertEqual(report["status"], "load_error", report)
            self.assertEqual(report["worker_report"]["observed"]["steps"], 0)
            self.assertIsNone(report["worker_report"]["diagnostic_trace"])
            self.assertIsNone(report["worker_report"]["cpu_progress"])
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
