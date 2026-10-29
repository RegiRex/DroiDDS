#!/usr/bin/env python3
"""CodexAstraUlt: Coordinator admission and comparisons use authored inputs only.

The C fixture is genuinely compiled and statically audited, but never loaded.
Worker boundary outcomes are injected so these tests cannot qualify native guest
execution, private-game progress or performance.
"""

import contextlib
import copy
import fcntl
import hashlib
import importlib.util
import io
import json
import os
from pathlib import Path
import signal
import tempfile
import unittest
from unittest import mock


# CodexAstraUlt: Explicit local imports preserve discovery independence and the
# six historical compilation helper files' content identities.
TOOLS = Path(__file__).resolve().parents[1]


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


RUNNER = load("native_run_coordinator_test", TOOLS / "run_compiled_title.py")
FIXTURES = load("native_run_compile_fixtures", TOOLS / "tests/test_compile_private_title.py")


def identity(data):
    """CodexAstraUlt: Expected identity comes from the actual authored byte string."""
    return {"bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()}


def state(cycles=100000, exited=False):
    """CodexAstraUlt: Complete synthetic fingerprint follows the worker schema."""
    return {
        "cycles": cycles, "frames": 0, "guest_exited": exited,
        "registers": [0] * 15 + [0x100000], "cpsr": 0x10,
        "vfp_registers": [0] * 32, "fpscr": 0, "fpexc": 0,
        "tls": 0, "exclusive_address": None, "current_thread": 0,
        "thread_guest_id": 0, "reschedule_pending": False, "all_blocked": False,
        "next_kernel_event": None,
        "memory": {
            **{name + "_fnv1a64": "0123456789abcdef" for name in
               ("fcram", "vram", "dsp_ram", "axi_wram", "mapping", "allocation")},
            "allocation_regions": [[0, 16384], [16384, 16383], [32767, 1]],
            "region_used_bytes": [4096, 0, 4096]},
        "graphics": {"command_lists": 0, "draw_calls": 0, "vertices_drawn": 0},
        "audio": {"pcm_pairs": 0, "nonzero_pairs": 0, "pcm_fnv1a64": "cbf29ce484222325"}}


def request(route="native"):
    """CodexAstraUlt: Report checks use independently specified invocation IDs."""
    return {"route": route, "preparation_sha256": "1" * 64, "contract_sha256": "2" * 64,
            "library": {"sha256": "3" * 64}, "model": "old",
            "limits": {"max_steps": 10000000, "max_cycles": 2000000,
                       "max_frames": 120, "max_seconds": 60}}


def worker_report(req=None, status="budget_exhausted"):
    """CodexAstraUlt: A well-formed boundary result is never a real worker claim."""
    req = request() if req is None else req
    native = req["route"] == "native"
    exited = status == "guest_exited"
    final = state(2000000, exited)
    return {
        "schema_version": 1, "kind": "droidds_private_native_run", "tool_version": "0.0.7",
        "status": status, "reason": "guest_called_exit_process" if exited else "cycle_budget",
        "blocker": None, "route": req["route"],
        "preparation_sha256": req["preparation_sha256"], "contract_sha256": req["contract_sha256"],
        "library_sha256": req["library"]["sha256"], "limits": copy.deepcopy(req["limits"]),
        "library_loaded": native, "library_load_attempted": native,
        "runtime_binding_enforced": True, "guest_execution_performed": True,
        "guest_execution_attempted": True, "elapsed_seconds": 0.01,
        "configuration": {
            "renderer": "software", "native_discovery": False, "strict_diagnostics": True,
            "clock_ms_since_1900": 4000000000000, "input_events": "neutral", "updates": False,
            "dlc": False, "mods": False, "texture_packs": False,
            "native_scope": "immutable_base_executable_only_modules_interpreted",
            "parent_admission": "sealed_local_coordinator_request_not_plugin_sandbox",
            "state_fingerprint": "noncryptographic_fnv1a64_diagnostic_only",
            "checkpoint_schedule": [100000, 500000, 1000000, 2000000],
            "private_images_or_audio_exported": False,
            "model_requested": req["model"], "model_resolved": req["model"]},
        "checkpoints": [{"requested_cycle": 100000, "exact_cycle": True, "state": state()}],
        "synchronized_checkpoints": [],
        "observed": {"steps": 100 if native else 1000, "cycles": 2000000, "frames": 0,
            "cycles_after_budget": 0, "interpreted_instructions": 10 if native else 1000,
            "recompiled_instructions": 990 if native else 0,
            "native_callback_fallback_instructions": 0, "guest_debug_bytes_discarded": 0,
            "services_seen": [], "state": final}}


# CodexAstraUlt: Synthetic post-SVC data lets negative controls independently
# vary boundary identity, CPU flags and native work before the sampled event.
def synchronized_point(cycle=100100, requested=100000, ordinal=3, native=False):
    return {"requested_cycle": requested,
            "boundary": {"ordinal": ordinal, "cycle": cycle, "number": 0x28,
                         "svc_pc": 0x100080, "thread_guest_id": 0},
            "instructions": {"interpreted": 10 if native else 1000,
                             "recompiled": 900 if native else 0, "callback_interpreted": 0},
            "state": state(cycle)}


class SynchronizedComparisonTests(unittest.TestCase):
    """CodexAstraUlt: Raw differences survive supplemental fully saved samples."""

    def pair(self):
        left, right = worker_report(request("interpreter")), worker_report()
        left["synchronized_checkpoints"] = [synchronized_point()]
        right["synchronized_checkpoints"] = [synchronized_point(native=True)]
        return left, right

    def test_matching_svc_sample_admits_both_reports(self):
        left, right = self.pair()
        for report in (left, right):
            RUNNER.validate_worker(report, request(report["route"]), 0)
        result = RUNNER.synchronized_comparison(left, right)
        self.assertEqual(result["status"], "matched")
        self.assertEqual(result["matched_boundaries"][0]["native_instructions_observed"], 900)
        self.assertEqual(len(result["missing_boundaries"]), 3)

    def test_raw_cpsr_difference_is_retained_after_synchronized_match(self):
        left, right = self.pair()
        right["checkpoints"][0]["state"]["cpsr"] ^= 1 << 29
        self.assertEqual(RUNNER.comparison(left, right)["status"], "different")
        self.assertEqual(RUNNER.synchronized_comparison(left, right)["status"], "matched")
        self.assertEqual(RUNNER.comparison(left, right)["mismatches"][0]["different_fields"], ["cpsr"])

    def test_real_flag_memory_or_scheduler_difference_at_svc_cannot_match(self):
        for field, value in (("cpsr", 0x20000010), ("reschedule_pending", True),
                             ("memory", {**state()["memory"], "fcram_fnv1a64": "f" * 16})):
            left, right = self.pair()
            right["synchronized_checkpoints"][0]["state"][field] = value
            with self.subTest(field=field):
                result = RUNNER.synchronized_comparison(left, right)
                self.assertEqual(result["status"], "different")
                self.assertEqual(result["mismatches"][0]["different_fields"], [field])

    def test_event_identity_difference_is_not_aligned_away(self):
        for field, value in (("ordinal", 4), ("cycle", 100101), ("number", 0x29),
                             ("svc_pc", 0x100084), ("thread_guest_id", 1)):
            left, right = self.pair()
            point = right["synchronized_checkpoints"][0]
            point["boundary"][field] = value
            if field == "cycle":
                point["state"]["cycles"] = value
            with self.subTest(field=field):
                result = RUNNER.synchronized_comparison(left, right)
                self.assertEqual(result["status"], "different")
                self.assertEqual(result["mismatches"][0]["reason"], "boundary_identity_differs")

    def test_native_work_after_a_sample_cannot_qualify_that_sample(self):
        for compiled, callbacks in ((0, 0), (900, 900)):
            left, right = self.pair()
            right["synchronized_checkpoints"][0]["instructions"].update(
                recompiled=compiled, callback_interpreted=callbacks)
            right["observed"]["native_callback_fallback_instructions"] = callbacks
            self.assertGreater(right["observed"]["recompiled_instructions"] - callbacks, 0)
            result = RUNNER.synchronized_comparison(left, right)
            self.assertEqual(result["status"], "inconclusive")
            self.assertEqual(result["zero_native_work_boundaries"], [100000])

    def test_absent_boundaries_do_not_qualify(self):
        left, right = self.pair()
        for report in (left, right):
            report["synchronized_checkpoints"] = []
        result = RUNNER.synchronized_comparison(left, right)
        self.assertEqual(result["status"], "inconclusive")
        self.assertEqual(len(result["missing_boundaries"]), 4)
        right["synchronized_checkpoints"] = [synchronized_point(native=True)]
        result = RUNNER.synchronized_comparison(left, right)
        self.assertEqual(result["status"], "inconclusive")
        self.assertFalse(result["missing_boundaries"][0]["interpreter_observed"])
        self.assertTrue(result["missing_boundaries"][0]["native_observed"])

    def test_partial_routes_cannot_qualify(self):
        left, right = self.pair()
        for status in ("blocked", "internal_error", "load_error"):
            right["status"] = status
            with self.subTest(status=status), self.assertRaises(ValueError):
                RUNNER.synchronized_comparison(left, right)

    def test_partial_failure_preserves_a_completed_syscall_overrun(self):
        # CodexAstraUlt: HLE can charge extra cycles before a panic leaves the
        # final envelope empty; preserve that event without treating it as a pass.
        _, right = self.pair()
        right["limits"]["max_cycles"] = 100000
        right.update(status="internal_error", reason="native_worker_panicked", observed={})
        req = request()
        req["limits"]["max_cycles"] = 100000
        self.assertEqual(RUNNER.validate_worker(right, req, 1), right)

    def test_malformed_or_unbound_samples_reject(self):
        for mutation in ("missing", "five", "cycle", "bool", "empty", "threshold", "pc", "counts", "fallback"):
            _, right = self.pair()
            point = right["synchronized_checkpoints"][0]
            if mutation == "missing":
                del right["synchronized_checkpoints"]
            elif mutation == "five":
                right["synchronized_checkpoints"] *= 5
            elif mutation == "cycle":
                point["state"]["cycles"] += 1
            elif mutation == "bool":
                point["boundary"]["ordinal"] = True
            elif mutation == "empty":
                point["state"] = {}
            elif mutation == "threshold":
                point["requested_cycle"] = 500000
            elif mutation == "pc":
                point["boundary"]["svc_pc"] += 1
            elif mutation == "counts":
                point["instructions"]["recompiled"] = 991
            else:
                point["instructions"]["callback_interpreted"] = 901
            with self.subTest(mutation=mutation), self.assertRaises(ValueError):
                RUNNER.validate_worker(right, request(), 0)

    def test_stale_boundary_or_reversed_counts_reject(self):
        for mutation in ("ordinal", "counts", "cycle"):
            _, right = self.pair()
            second = synchronized_point(500100, 500000, 4, True)
            right["synchronized_checkpoints"].append(second)
            if mutation == "ordinal":
                second["boundary"]["ordinal"] = 3
            elif mutation == "counts":
                second["instructions"]["recompiled"] = 899
            else:
                second["boundary"]["cycle"] = 100100
                second["state"]["cycles"] = 100100
            with self.subTest(mutation=mutation), self.assertRaises(ValueError):
                RUNNER.validate_worker(right, request(), 0)


class SealedInputTests(unittest.TestCase):
    """CodexAstraUlt: Real memfds bind copy identity and protect caller originals."""

    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix="droidds-native-sealing-")
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.path = self.root / "owner's source.bin"
        self.original = b"original source bytes\0\xff"
        self.path.write_bytes(self.original)

    def test_sealed_parts_exact_bytes_hash_seals_and_preserved_original(self):
        before = self.path.stat()
        with contextlib.ExitStack() as stack:
            sealed = RUNNER.seal_parts(stack, "authored-sealed-input",
                [b"prefix", (self.path, identity(self.original)), b"suffix"], 4096)
            descriptor = sealed["descriptor"]
            actual = os.pread(descriptor, 4096, 0)
            self.assertEqual(actual, b"prefix" + self.original + b"suffix")
            self.assertEqual({key: sealed[key] for key in ("bytes", "sha256")}, identity(actual))
            self.assertEqual(fcntl.fcntl(descriptor, RUNNER.GET_SEALS) & RUNNER.SEALS, RUNNER.SEALS)
            for operation in (lambda: os.write(descriptor, b"mutation"),
                              lambda: os.ftruncate(descriptor, 1),
                              lambda: os.ftruncate(descriptor, 8192)):
                with self.assertRaises(OSError):
                    operation()
            self.assertEqual(self.path.read_bytes(), self.original)
            self.assertEqual((self.path.stat().st_ino, self.path.stat().st_mtime_ns),
                             (before.st_ino, before.st_mtime_ns))
        with self.assertRaises(OSError):
            os.fstat(descriptor)

    def test_source_hash_or_size_mismatch_rejects_copy(self):
        for expected in ({**identity(self.original), "sha256": "0" * 64},
                         {**identity(self.original), "bytes": len(self.original) + 1}):
            with self.subTest(expected=expected), contextlib.ExitStack() as stack:
                with self.assertRaisesRegex(ValueError, "sealed_component_identity_mismatch"):
                    RUNNER.seal_parts(stack, "wrong-identity", [(self.path, expected)], 4096)
        self.assertEqual(self.path.read_bytes(), self.original)

    def test_aggregate_bound_rejects_before_extra_bytes_are_written(self):
        with contextlib.ExitStack() as stack:
            with self.assertRaisesRegex(ValueError, "sealed_input_exceeds_bound"):
                RUNNER.seal_parts(stack, "bounded", [b"1234", b"5"], 4)

    def test_component_symlink_is_rejected(self):
        alias = self.root / "alias"
        alias.symlink_to(self.path)
        with contextlib.ExitStack() as stack:
            with self.assertRaisesRegex(ValueError, "symlink"):
                RUNNER.seal_parts(stack, "no-alias", [(alias, identity(self.original))], 4096)


class WorkerReportTests(unittest.TestCase):
    """CodexAstraUlt: Empty or internally contradictory evidence cannot pass."""

    def test_complete_report_admits_for_each_route(self):
        for route in ("interpreter", "native"):
            req = request(route)
            value = worker_report(req)
            self.assertEqual(RUNNER.validate_worker(value, req, 0), value)

    def test_missing_boolean_or_negative_counters_are_rejected(self):
        for counter in ("steps", "cycles", "frames", "interpreted_instructions",
                        "recompiled_instructions", "native_callback_fallback_instructions",
                        "cycles_after_budget", "guest_debug_bytes_discarded"):
            for mutation in (None, True, -1):
                value = worker_report()
                if mutation is None:
                    del value["observed"][counter]
                else:
                    value["observed"][counter] = mutation
                with self.subTest(counter=counter, mutation=mutation), self.assertRaises(ValueError):
                    RUNNER.validate_worker(value, request(), 0)

    def test_empty_or_malformed_state_is_rejected(self):
        malformed = ({}, {"cycles": 100000}, {**state(), "registers": [0] * 15},
                     {**state(), "cycles": True}, {**state(), "unknown": 0},
                     {**state(), "memory": {}}, {**state(), "audio": {}})
        for bad in malformed:
            for location in ("checkpoint", "observed"):
                value = worker_report()
                if location == "checkpoint":
                    value["checkpoints"][0]["state"] = bad
                else:
                    value["observed"]["state"] = bad
                with self.subTest(state=bad, location=location), self.assertRaises(ValueError):
                    RUNNER.validate_worker(value, request(), 0)

    def test_exact_cycle_flag_must_match_captured_cycle(self):
        for actual, exact in ((100001, True), (100000, False), (99999, False)):
            value = worker_report()
            value["checkpoints"][0].update(exact_cycle=exact, state=state(actual))
            with self.subTest(actual=actual, exact=exact), self.assertRaises(ValueError):
                RUNNER.validate_worker(value, request(), 0)

    def test_identity_limits_exit_status_and_route_cannot_be_forged(self):
        for field, bad in (("preparation_sha256", "0" * 64), ("contract_sha256", "0" * 64),
                           ("library_sha256", "0" * 64), ("route", "interpreter"),
                           ("schema_version", True), ("library_loaded", False),
                           ("runtime_binding_enforced", False)):
            value = worker_report()
            value[field] = bad
            with self.subTest(field=field), self.assertRaises(ValueError):
                RUNNER.validate_worker(value, request(), 0)
        value = worker_report()
        value["limits"]["max_seconds"] = True
        with self.assertRaises(ValueError):
            RUNNER.validate_worker(value, request(), 0)
        with self.assertRaises(ValueError):
            RUNNER.validate_worker(worker_report(), request(), 2)

    def test_load_and_execution_claims_require_explicit_attempt_flags(self):
        # CodexAstraUlt: Completed operations imply attempts; omitted flags and
        # integer aliases cannot silently become older-schema compatibility.
        for name in ("library_load_attempted", "guest_execution_attempted"):
            for mutation in (None, False, 1):
                value = worker_report()
                if mutation is None:
                    del value[name]
                else:
                    value[name] = mutation
                with self.subTest(name=name, mutation=mutation), self.assertRaises(ValueError):
                    RUNNER.validate_worker(value, request(), 0)

    def test_execution_claim_follows_instructions_instead_of_dispatch_attempts(self):
        # CodexAstraUlt: A dispatch can fail before executing any instruction.
        # Its positive outer step count must not fabricate guest execution.
        value = worker_report()
        value["observed"].update(interpreted_instructions=0, recompiled_instructions=0)
        self.assertGreater(value["observed"]["steps"], 0)
        with self.assertRaisesRegex(ValueError, "worker_execution_admission_mismatch"):
            RUNNER.validate_worker(value, request(), 0)
        value["guest_execution_performed"] = False
        self.assertEqual(RUNNER.validate_worker(value, request(), 0), value)
        value["observed"]["interpreted_instructions"] = 1
        with self.assertRaisesRegex(ValueError, "worker_execution_admission_mismatch"):
            RUNNER.validate_worker(value, request(), 0)

    def test_partial_worker_failure_retains_only_valid_bounded_checkpoints(self):
        # CodexAstraUlt: A panic may retain earlier bounded evidence while its
        # absent final observations prevent any comparison or completion claim.
        value = worker_report()
        value.update(status="internal_error", reason="native_worker_panicked", observed={})
        self.assertEqual(RUNNER.validate_worker(value, request(), 1), value)
        for mutation in ("empty_state", "fake_exact", "repeat", "five", "observed"):
            bad = copy.deepcopy(value)
            if mutation == "empty_state":
                bad["checkpoints"][0]["state"] = {}
            elif mutation == "fake_exact":
                bad["checkpoints"][0]["state"]["cycles"] += 1
            elif mutation == "repeat":
                bad["checkpoints"] *= 2
            elif mutation == "five":
                bad["checkpoints"] *= 5
            else:
                bad["observed"] = worker_report()["observed"]
            with self.subTest(mutation=mutation), self.assertRaises(ValueError):
                RUNNER.validate_worker(bad, request(), 1)

    def test_different_state_at_matched_cycle_is_reported(self):
        left, right = worker_report(request("interpreter")), worker_report()
        right["checkpoints"][0]["state"]["registers"][0] = 7
        result = RUNNER.comparison(left, right)
        self.assertEqual(result["status"], "different")
        self.assertEqual(result["mismatches"], [{"cycle": 100000, "different_fields": ["registers"]}])

    def test_unequal_outer_steps_do_not_change_equal_cycle_comparison(self):
        left, right = worker_report(request("interpreter")), worker_report()
        self.assertNotEqual(left["observed"]["steps"], right["observed"]["steps"])
        result = RUNNER.comparison(left, right)
        self.assertEqual(result["status"], "matched")
        self.assertEqual(result["matched_cycles"], [100000])

    def test_entirely_interpreted_callbacks_cannot_qualify_native_execution(self):
        # CodexAstraUlt: A positive bridge total may consist entirely of
        # interpreter callbacks; neither checkpoint nor exit equality proves
        # that generated instructions actually executed in that case.
        for exited in (False, True):
            status = "guest_exited" if exited else "budget_exhausted"
            left, right = worker_report(request("interpreter"), status), worker_report(status=status)
            if exited:
                left["checkpoints"] = right["checkpoints"] = []
            right["observed"]["native_callback_fallback_instructions"] = 990
            result = RUNNER.comparison(left, right)
            with self.subTest(exited=exited):
                self.assertEqual(result["status"], "inconclusive")
                self.assertEqual(result["native_instructions_observed"], 0)
                self.assertEqual(result["compiled_dispatch_instructions"], 990)
                self.assertEqual(result["callback_interpreted_instructions"], 990)

    def test_partial_fallback_reports_only_actual_generated_instruction_delta(self):
        # CodexAstraUlt: Preserve both raw accounting components while reporting
        # actual generated work as the difference, never the bridge total.
        left, right = worker_report(request("interpreter")), worker_report()
        right["observed"]["native_callback_fallback_instructions"] = 989
        result = RUNNER.comparison(left, right)
        self.assertEqual(result["status"], "matched")
        self.assertEqual(result["native_instructions_observed"], 1)
        self.assertEqual(result["compiled_dispatch_instructions"], 990)
        self.assertEqual(result["callback_interpreted_instructions"], 989)

    def test_comparison_itself_rejects_callbacks_exceeding_dispatch_total(self):
        # CodexAstraUlt: Direct comparison callers must not bypass the envelope
        # validator and produce a negative generated-instruction count.
        for route in ("interpreter", "native"):
            left, right = worker_report(request("interpreter")), worker_report()
            observed = (left if route == "interpreter" else right)["observed"]
            observed["native_callback_fallback_instructions"] = observed["recompiled_instructions"] + 1
            with self.subTest(route=route), self.assertRaisesRegex(ValueError, "worker_fallback_accounting_mismatch"):
                RUNNER.comparison(left, right)

    def test_comparison_itself_rejects_empty_states_or_fake_exact_cycles(self):
        for mutation in ("empty", "fake_cycle", "missing_native", "boolean_native"):
            left, right = worker_report(request("interpreter")), worker_report()
            if mutation == "empty":
                left["checkpoints"][0]["state"] = right["checkpoints"][0]["state"] = {}
            elif mutation == "fake_cycle":
                left["checkpoints"][0]["state"]["cycles"] += 1
                right["checkpoints"][0]["state"]["cycles"] += 1
            elif mutation == "missing_native":
                del right["observed"]["recompiled_instructions"]
            else:
                right["observed"]["recompiled_instructions"] = True
            with self.subTest(mutation=mutation), self.assertRaises(ValueError):
                RUNNER.comparison(left, right)

    def test_unmatched_checkpoints_do_not_claim_equivalence(self):
        left, right = worker_report(request("interpreter")), worker_report()
        right["checkpoints"][0].update(exact_cycle=False, state=state(100001))
        result = RUNNER.comparison(left, right)
        self.assertEqual(result["status"], "inconclusive")
        self.assertEqual(result["unmatched_cycles"], [100000])

    def test_guest_exit_requires_real_cycles_and_positive_native_work(self):
        left = worker_report(request("interpreter"), "guest_exited")
        right = worker_report(status="guest_exited")
        left["checkpoints"] = right["checkpoints"] = []
        self.assertEqual(RUNNER.comparison(left, right)["status"], "matched")
        right["observed"]["recompiled_instructions"] = 0
        self.assertEqual(RUNNER.comparison(left, right)["status"], "inconclusive")
        right["observed"]["recompiled_instructions"] = 1
        right["observed"]["state"]["cycles"] += 1
        self.assertEqual(RUNNER.comparison(left, right)["status"], "inconclusive")
        for bad in ({}, {**state(exited=True), "cycles": None}):
            left["observed"]["state"] = right["observed"]["state"] = bad
            with self.subTest(state=bad), self.assertRaises(ValueError):
                RUNNER.comparison(left, right)


# CodexAstraUlt: Original fixed bytes 0..15 are the fixture's base text. Its
# pointer graph and FNV origin hash are valid, but no function is executed here.
ORIGINAL_C = b'''/* CodexAstraUlt: Authored one-entry runtime ABI fixture. */
#include <stdint.h>
#define E __attribute__((visibility("default")))
typedef struct { uint32_t address; void (*code)(void *); } Entry;
typedef struct { uint32_t start,end; uint64_t hash; } Piece;
typedef struct { uint32_t first,count,start; } Origin;
typedef struct { uint32_t first,end; } Run;
typedef struct { uint32_t count,pieces_count; const Piece *pieces; const Origin *functions;
 const Run *runs; const uint32_t *owners; uint8_t *stale; uint32_t *starts; } Origins;
static void original(void *context) { (void)context; }
E const uint32_t recomp_abi=4, recomp_generation=3, recomp_entry_count=1, recomp_module_count=0;
E const Entry recomp_entries[]={{0x100000, original}};
E const unsigned char recomp_modules[0]={};
static const Piece pieces[]={{0x100000,0x100010,0x7c84dc9477851775ULL}};
static const Origin functions[]={{0,1,0x100000}};
static const Run runs[]={{0,1}};
static const uint32_t owners[]={0};
static uint8_t stale[1]; static uint32_t starts[]={0x100000};
E const Origins recomp_origins[]={{1,1,pieces,functions,runs,owners,stale,starts}};
'''


class CoordinatorTests(unittest.TestCase):
    """CodexAstraUlt: Full retained-build admission precedes mocked worker results."""

    @classmethod
    def setUpClass(cls):
        FIXTURES.CompileCoordinatorTests.setUpClass()

    def setUp(self):
        self.fixture = FIXTURES.CompileCoordinatorTests(
            "test_compiles_real_objects_and_library_without_loading_or_mutating_preparation")
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)
        self.fixture.fixture.blobs["generated/program.c"] = ORIGINAL_C
        self.fixture.fixture.descriptor["artifacts"] = [
            {"path": name, "bytes": len(data)} for name, data in self.fixture.fixture.blobs.items()
            if name.startswith("generated/")]
        self.fixture.fixture.write_preparation()
        with mock.patch.object(FIXTURES.RUNNER, "coordinator_identity",
                               return_value=RUNNER.COMPILE.coordinator_identity()):
            code, report = self.fixture.execute()
        self.assertEqual(code, 0, report)
        self.root, self.preparation, self.compilation = self.fixture.root, self.fixture.preparation, self.fixture.output
        self.worker = self.root / "worker boundary placeholder"
        self.worker.write_text("#!/usr/bin/env python3\nraise RuntimeError('must not execute placeholder')\n")
        self.worker.chmod(0o700)
        self.output = self.root / "fresh paired run"
        self.process_calls = []
        self.original_prepared = FIXTURES.tree_bytes(self.preparation)
        self.original_compiled = FIXTURES.tree_bytes(self.compilation)

    def args(self, *extra):
        return RUNNER.parse_args(["--preparation", str(self.preparation), "--compilation", str(self.compilation),
                                  "--output", str(self.output), "--worker", str(self.worker), *extra])

    def process_result(self, command, cwd, timeout, cpu_seconds, memory_mib, pass_fds=()):
        """CodexAstraUlt: Inspect actual inherited seals and inject only worker output."""
        self.assertEqual(len(pass_fds), 3)
        req = json.loads(os.pread(pass_fds[0], RUNNER.MAX_REQUEST, 0))
        self.assertEqual(req["library"]["descriptor"], pass_fds[1])
        self.assertEqual(req["identity_bundle"]["descriptor"], pass_fds[2])
        for descriptor in pass_fds:
            self.assertEqual(fcntl.fcntl(descriptor, RUNNER.GET_SEALS) & RUNNER.SEALS, RUNNER.SEALS)
        for record in (req["library"], req["identity_bundle"]):
            payload = os.pread(record["descriptor"], record["bytes"] + 1, 0)
            self.assertEqual(identity(payload), {key: record[key] for key in ("bytes", "sha256")})
        self.process_calls.append({"request": req, "fds": pass_fds,
                                   "inodes": [os.fstat(fd).st_ino for fd in pass_fds]})
        (Path(cwd) / "worker-report.json").write_text(json.dumps(worker_report(req)))
        return {"outcome": "completed", "exit_code": 0, "elapsed_seconds": 0.01,
                "log_tail": "authored boundary outcome\n", "log_bytes_seen": 26, "limits": {}}

    def execute(self, boundary=None):
        with mock.patch.object(RUNNER.PROCESS, "run_worker", side_effect=boundary or self.process_result):
            return RUNNER.run(self.args())

    def test_both_routes_use_same_sealed_library_and_bundle_and_preserve_originals(self):
        code, report = self.execute()
        self.assertEqual(code, 0, report)
        self.assertEqual(report["comparison"]["status"], "matched")
        self.assertTrue(report["preserved_inputs_verified"])
        self.assertEqual([call["request"]["route"] for call in self.process_calls], ["interpreter", "native"])
        self.assertEqual(self.process_calls[0]["fds"][1:], self.process_calls[1]["fds"][1:])
        self.assertEqual(self.process_calls[0]["inodes"][1:], self.process_calls[1]["inodes"][1:])
        self.assertEqual(FIXTURES.tree_bytes(self.preparation), self.original_prepared)
        self.assertEqual(FIXTURES.tree_bytes(self.compilation), self.original_compiled)
        for call in self.process_calls:
            for fd in call["fds"]:
                with self.assertRaises(OSError):
                    os.fstat(fd)

    def test_audited_library_hash_mismatch_stops_before_worker_loading(self):
        audit = RUNNER.ELF.audit_runtime_library
        def wrong_actual_hash(*args):
            result = audit(*args)
            self.assertTrue(result["runtime_tables_validated"])
            self.assertFalse(result["library_loaded"])
            return {**result, "library_sha256": "0" * 64}
        with mock.patch.object(RUNNER.ELF, "audit_runtime_library", side_effect=wrong_actual_hash):
            code, report = self.execute()
        self.assertEqual(code, 1)
        self.assertEqual(report["reason"], "audited_library_identity_mismatch")
        self.assertEqual(self.process_calls, [])

    def test_failed_interpreter_never_runs_native_or_asserts_signal_cause(self):
        def signal_boundary(*args, **kwargs):
            result = self.process_result(*args, **kwargs)
            result.update(exit_code=-signal.SIGSEGV)
            return result
        code, report = self.execute(signal_boundary)
        self.assertEqual(code, 1)
        self.assertEqual(report["reason"], "worker_signal_11")
        self.assertEqual(list(report["routes"]), ["interpreter"])
        self.assertIsNone(report["comparison"])
        self.assertEqual(len(self.process_calls), 1)

    def test_timeout_interpreter_never_runs_native(self):
        def timeout_boundary(*args, **kwargs):
            result = self.process_result(*args, **kwargs)
            result.update(outcome="timeout", exit_code=-signal.SIGTERM)
            return result
        code, report = self.execute(timeout_boundary)
        self.assertEqual(code, 1)
        self.assertEqual(list(report["routes"]), ["interpreter"])
        self.assertIsNone(report["comparison"])

    def test_runtime_blocker_prevents_native_and_remains_a_blocker(self):
        def blocked_boundary(*args, **kwargs):
            result = self.process_result(*args, **kwargs)
            path = Path(args[1]) / "worker-report.json"
            value = json.loads(path.read_text())
            value.update(status="blocked", reason="runtime_blocker",
                         blocker={"kind": "unsupported_svc", "number": 255})
            path.write_text(json.dumps(value))
            return result
        code, report = self.execute(blocked_boundary)
        self.assertEqual(code, 1)
        self.assertEqual(report["status"], "blocked")
        self.assertEqual(report["reason"], "interpreter_blocked")
        self.assertEqual(list(report["routes"]), ["interpreter"])
        self.assertIsNone(report["comparison"])

    def test_load_error_preserves_failure_and_never_runs_native(self):
        def rejected_boundary(*args, **kwargs):
            result = self.process_result(*args, **kwargs)
            path = Path(args[1]) / "worker-report.json"
            value = json.loads(path.read_text())
            value.update(status="load_error", reason="fixture_loader_rejection", observed={},
                         checkpoints=[], runtime_binding_enforced=False,
                         guest_execution_performed=False, guest_execution_attempted=False)
            path.write_text(json.dumps(value))
            result["exit_code"] = 1
            return result
        code, report = self.execute(rejected_boundary)
        self.assertEqual(code, 1)
        self.assertEqual(report["reason"], "interpreter_load_error")
        self.assertEqual(list(report["routes"]), ["interpreter"])
        self.assertIsNone(report["comparison"])

    def test_partial_internal_error_keeps_checkpoint_and_never_runs_native(self):
        # CodexAstraUlt: Earlier measurements survive worker failure, but a
        # missing final state cannot fall through into native route comparison.
        def partial_boundary(*args, **kwargs):
            result = self.process_result(*args, **kwargs)
            path = Path(args[1]) / "worker-report.json"
            value = json.loads(path.read_text())
            value.update(status="internal_error", reason="native_worker_panicked", observed={})
            path.write_text(json.dumps(value))
            result["exit_code"] = 1
            return result
        code, report = self.execute(partial_boundary)
        self.assertEqual(code, 1)
        self.assertEqual(report["reason"], "interpreter_internal_error")
        self.assertEqual(list(report["routes"]), ["interpreter"])
        self.assertIsNone(report["comparison"])
        self.assertEqual(len(report["routes"]["interpreter"]["worker_report"]["checkpoints"]), 1)

    def test_malformed_success_report_cannot_launch_native(self):
        def malformed_boundary(*args, **kwargs):
            result = self.process_result(*args, **kwargs)
            path = Path(args[1]) / "worker-report.json"
            value = json.loads(path.read_text())
            value["observed"]["state"] = {}
            path.write_text(json.dumps(value))
            return result
        code, report = self.execute(malformed_boundary)
        self.assertEqual(code, 1)
        self.assertEqual(report["status"], "rejected")
        self.assertEqual(list(report["routes"]), ["interpreter"])
        self.assertIsNone(report["comparison"])

    def test_forged_partial_manifest_is_rejected_before_process(self):
        next((self.compilation / "receipts").glob("*.json")).unlink()
        code, report = self.execute()
        self.assertEqual(code, 1)
        self.assertEqual(report["reason"], "runtime_compile_missing_objects")
        self.assertEqual(self.process_calls, [])

    def test_library_manifest_path_escape_is_rejected_before_process(self):
        path = self.compilation / "compiled-manifest.json"
        value = RUNNER.PREP.read_json(path)
        value["library"]["path"] = "../outside-library.so"
        path.write_bytes(RUNNER.PREP.canonical(value))
        code, report = self.execute()
        self.assertEqual(code, 1)
        self.assertEqual(report["status"], "rejected")
        self.assertEqual(self.process_calls, [])

    def test_changed_generated_source_hash_rejects_before_process(self):
        self.fixture.mutate(self.compilation / "source/program.c")
        code, report = self.execute()
        self.assertEqual(code, 1)
        self.assertEqual(report["status"], "rejected")
        self.assertEqual(self.process_calls, [])

    def test_reusing_existing_output_cannot_overwrite_prior_report(self):
        self.output.mkdir()
        previous = self.output / "report.json"
        previous.write_bytes(b"preserved prior report")
        code, report = self.execute()
        self.assertEqual(code, 1)
        self.assertEqual(report["reason"], "output_must_be_new_with_existing_parent")
        self.assertEqual(previous.read_bytes(), b"preserved prior report")
        self.assertEqual(self.process_calls, [])

    def test_duplicate_options_limits_and_parent_timeout_are_rejected(self):
        for extra in (("--model", "old", "--model=new"), ("--max-steps", "0"),
                      ("--max-cycles", "26811185601"), ("--max-frames", "6001"),
                      ("--max-seconds", "301"), ("--timeout", "311"),
                      ("--cpu-seconds", "312"), ("--memory-mib", "255"),
                      ("--memory-mib", "16385"), ("--timeout", "60")):
            with self.subTest(extra=extra), contextlib.redirect_stderr(io.StringIO()):
                with self.assertRaises(SystemExit):
                    self.args(*extra)


if __name__ == "__main__":
    unittest.main()
