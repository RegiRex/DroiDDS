#!/usr/bin/env python3
"""CodexAstraUlt: Exercise sealed descriptors and actual bounded worker children."""

import fcntl
import importlib.util
import json
import os
from pathlib import Path
import signal
import sys
import tempfile
import unittest
from unittest import mock

from process_assertions import assert_process_stopped

# CodexAstraUlt: These authored subprocesses use no private game, native title
# library, network access or shared build directory.
SPEC = importlib.util.spec_from_file_location(
    "private_runtime_process_test", Path(__file__).resolve().parents[1] / "private_runtime_process.py")
PROCESS = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(PROCESS)


class RuntimeProcessTests(unittest.TestCase):
    """CodexAstraUlt: A missing Linux primitive fails the gate rather than skips."""

    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="droidds-runtime-process-")
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)

    def memfd(self, data=b"original immutable input", seals=None):
        descriptor = os.memfd_create("droidds-original-test", os.MFD_CLOEXEC | os.MFD_ALLOW_SEALING)
        self.addCleanup(os.close, descriptor)
        os.write(descriptor, data)
        os.lseek(descriptor, 0, os.SEEK_SET)
        if seals is None:
            seals = PROCESS.REQUIRED_SEALS
        if seals:
            fcntl.fcntl(descriptor, PROCESS.F_ADD_SEALS, seals)
        return descriptor

    def run_python(self, source, **overrides):
        arguments = {"command": [sys.executable, "-c", source], "cwd": self.root,
                     "timeout": 3, "cpu_seconds": 2, "memory_mib": 256}
        arguments.update(overrides)
        return PROCESS.run_worker(**arguments)

    def test_sealed_inputs_survive_exec_and_remain_owned_immutable_parent_descriptors(self):
        descriptor = self.memfd()
        was_inheritable = os.get_inheritable(descriptor)
        result = self.run_python(
            "import fcntl,json,os\n"
            f"fd={descriptor}\n"
            "errors=[]\n"
            "for action in (lambda:os.write(fd,b'X'),lambda:os.ftruncate(fd,0),"
            "lambda:os.ftruncate(fd,100)):\n"
            " try: action()\n"
            " except OSError as error: errors.append(error.errno)\n"
            "print(json.dumps({'bytes':os.pread(fd,100,0).decode(),"
            f"'seals':fcntl.fcntl(fd,{PROCESS.F_GET_SEALS}),'failures':len(errors)}}))",
            pass_fds=(descriptor,))
        self.assertEqual(result["exit_code"], 0, result)
        self.assertEqual(json.loads(result["log_tail"]), {
            "bytes": "original immutable input", "seals": PROCESS.REQUIRED_SEALS, "failures": 3})
        self.assertEqual(os.pread(descriptor, 100, 0), b"original immutable input")
        self.assertEqual(os.get_inheritable(descriptor), was_inheritable)
        self.assertEqual(result["limits"]["passed_sealed_fds"], 1)

    def test_unlisted_inheritable_descriptor_is_closed_in_worker(self):
        descriptor = self.memfd()
        excluded = os.open(self.root / "unlisted", os.O_CREAT | os.O_RDWR, 0o600)
        self.addCleanup(os.close, excluded)
        os.set_inheritable(excluded, True)
        result = self.run_python(
            "import os\n"
            f"assert os.pread({descriptor},100,0)==b'original immutable input'\n"
            f"try: os.fstat({excluded})\n"
            "except OSError: print('closed')\n"
            "else: raise AssertionError('unlisted descriptor leaked')\n",
            pass_fds=[descriptor])
        self.assertEqual(result["exit_code"], 0, result)
        self.assertEqual(result["log_tail"].strip(), "closed")
        self.assertTrue(os.get_inheritable(excluded))

    def test_mutable_partially_sealed_empty_oversize_and_non_memfd_inputs_reject(self):
        cases = [self.memfd(seals=0), self.memfd(data=b"")]
        for omitted in (PROCESS.F_SEAL_WRITE, PROCESS.F_SEAL_GROW,
                        PROCESS.F_SEAL_SHRINK, PROCESS.F_SEAL_SEAL):
            cases.append(self.memfd(seals=PROCESS.REQUIRED_SEALS & ~omitted))
        big = os.memfd_create("droidds-too-large", os.MFD_CLOEXEC | os.MFD_ALLOW_SEALING)
        self.addCleanup(os.close, big)
        os.ftruncate(big, PROCESS.MAX_INPUT_BYTES + 1)
        fcntl.fcntl(big, PROCESS.F_ADD_SEALS, PROCESS.REQUIRED_SEALS)
        cases.append(big)
        ordinary = os.open(self.root / "ordinary", os.O_CREAT | os.O_RDWR, 0o600)
        self.addCleanup(os.close, ordinary)
        os.write(ordinary, b"ordinary file")
        cases.append(ordinary)
        read_pipe, write_pipe = os.pipe()
        self.addCleanup(os.close, read_pipe)
        self.addCleanup(os.close, write_pipe)
        cases.append(read_pipe)
        with mock.patch.object(PROCESS.subprocess, "Popen") as spawn:
            for descriptor in cases:
                with self.subTest(descriptor=descriptor), self.assertRaises(ValueError):
                    self.run_python("pass", pass_fds=(descriptor,))
            spawn.assert_not_called()

    def test_duplicate_invalid_and_closed_descriptors_reject(self):
        descriptor = self.memfd()
        closed = os.dup(descriptor)
        os.close(closed)
        cases = [(descriptor, descriptor), (True,), (-1,), (0,), (1,), (2,),
                 ("3",), (closed,), tuple(range(3, 3 + PROCESS.MAX_PASSED_FDS + 1)), {descriptor}]
        with mock.patch.object(PROCESS.subprocess, "Popen") as spawn:
            for descriptors in cases:
                with self.subTest(descriptors=descriptors), self.assertRaises(ValueError):
                    self.run_python("pass", pass_fds=descriptors)
            spawn.assert_not_called()

    def test_limits_stdin_and_environment_are_enforced_before_exec(self):
        extras = {"CPATH": "untrusted", "CFLAGS": "-ffast-math", "LD_PRELOAD": "absent.so",
                  "PYTHONPATH": "/untrusted", "PYTHONINSPECT": "1", "GLIBC_TUNABLES": "untrusted",
                  "HTTP_PROXY": "http://retained.invalid", "LC_ALL": "untrusted"}
        with mock.patch.dict(os.environ, extras):
            result = self.run_python(
                "import json,os,resource,sys\n"
                "print(json.dumps({'stdin':sys.stdin.read(),"
                "'cpu':resource.getrlimit(resource.RLIMIT_CPU),"
                "'as':resource.getrlimit(resource.RLIMIT_AS),"
                "'file':resource.getrlimit(resource.RLIMIT_FSIZE),"
                "'core':resource.getrlimit(resource.RLIMIT_CORE),"
                "'overrides':[os.environ.get(k) for k in ('CPATH','CFLAGS','LD_PRELOAD',"
                "'PYTHONPATH','PYTHONINSPECT','GLIBC_TUNABLES')],"
                "'proxy':os.environ.get('HTTP_PROXY'),'locale':os.environ.get('LC_ALL')}))")
        self.assertEqual(result["exit_code"], 0, result)
        self.assertEqual(json.loads(result["log_tail"]), {
            "stdin": "", "cpu": [2, 2], "as": [256 * 1024**2] * 2,
            "file": [PROCESS.FILE_BYTES] * 2, "core": [0, 0],
            "overrides": [None] * 6, "proxy": "http://retained.invalid", "locale": "C"})
        self.assertEqual(result["limits"]["cpu_scope"], "per_process_all_threads")
        self.assertEqual(list(self.root.iterdir()), [])

    def test_large_log_is_drained_and_only_bounded_tail_survives(self):
        result = self.run_python("import os\nos.write(1,b'X'*200000+b'FINAL')")
        self.assertEqual(result["exit_code"], 0, result)
        self.assertEqual(result["log_bytes_seen"], 200005)
        self.assertEqual(len(result["log_tail"]), PROCESS.LOG_BYTES)
        self.assertTrue(result["log_tail"].endswith("FINAL"))

    def test_continuous_output_cannot_starve_deadline(self):
        result = self.run_python("import os\nwhile True: os.write(1,b'X'*8192)", timeout=0.15)
        self.assertEqual(result["outcome"], "timeout", result)
        self.assertNotEqual(result["exit_code"], 0)
        self.assertLess(result["elapsed_seconds"], 5)
        self.assertLessEqual(len(result["log_tail"]), PROCESS.LOG_BYTES)

    def test_sleeping_worker_is_terminated_at_wall_deadline(self):
        result = self.run_python("import time\ntime.sleep(30)", timeout=0.1)
        self.assertEqual(result["outcome"], "timeout", result)
        self.assertNotEqual(result["exit_code"], 0)
        self.assertLess(result["elapsed_seconds"], 5)

    def test_grandchild_is_killed_after_successful_leader_exit(self):
        result = self.run_python(
            "import os,signal,time\n"
            "if os.fork()==0:\n"
            " signal.signal(signal.SIGTERM,signal.SIG_IGN)\n"
            " print(os.getpid(),flush=True)\n"
            " time.sleep(30)\n"
            "else:\n"
            " time.sleep(0.1)\n"
            " os._exit(0)\n")
        self.assertEqual(result["outcome"], "completed", result)
        self.assertEqual(result["exit_code"], 0)
        pid = int(result["log_tail"].strip())
        # CodexAstraUlt: An adopter can reap the orphan while its state is read;
        # accept only disappearance or a zombie, retaining the live-child gate.
        assert_process_stopped(self, pid)

    def test_interrupt_terminates_worker_and_returns_distinct_outcome(self):
        result = self.run_python(
            "import os,signal,time\ntime.sleep(0.05)\n"
            "os.kill(os.getppid(),signal.SIGINT)\ntime.sleep(30)")
        self.assertEqual(result["outcome"], "interrupted", result)
        self.assertNotEqual(result["exit_code"], 0)
        self.assertLess(result["elapsed_seconds"], 5)

    def test_busy_worker_reaches_hard_cpu_limit(self):
        result = self.run_python("while True: pass", timeout=4, cpu_seconds=1)
        self.assertEqual(result["outcome"], "completed", result)
        self.assertEqual(result["exit_code"], -signal.SIGKILL)

    def test_address_space_limit_rejects_actual_large_allocation(self):
        result = self.run_python("data=bytearray(512*1024*1024)")
        self.assertEqual(result["outcome"], "completed", result)
        self.assertNotEqual(result["exit_code"], 0)
        self.assertIn("MemoryError", result["log_tail"])

    def test_file_limit_rejects_oversize_worker_file(self):
        result = self.run_python(
            "import os\nfd=os.open('partial',os.O_CREAT|os.O_WRONLY,0o600)\n"
            f"os.ftruncate(fd,{PROCESS.FILE_BYTES + 1})\n")
        self.assertEqual(result["outcome"], "completed", result)
        self.assertNotEqual(result["exit_code"], 0)
        self.assertLessEqual((self.root / "partial").stat().st_size, PROCESS.FILE_BYTES)

    def test_sigsegv_remains_signal_and_core_file_is_disabled(self):
        result = self.run_python("import os,signal\nos.kill(os.getpid(),signal.SIGSEGV)")
        self.assertEqual(result["outcome"], "completed", result)
        self.assertEqual(result["exit_code"], -signal.SIGSEGV)
        self.assertEqual(list(self.root.iterdir()), [])

    # CodexAstraUlt: An error after spawn must still kill and reap the worker,
    # even before the output selector is ready to supervise it.
    def test_pipe_setup_error_reaps_already_started_worker(self):
        real_spawn = PROCESS.subprocess.Popen
        started = []

        def spawn(*args, **kwargs):
            child = real_spawn(*args, **kwargs)
            started.append(child)
            return child

        with mock.patch.object(PROCESS.subprocess, "Popen", side_effect=spawn), \
                mock.patch.object(PROCESS.selectors, "DefaultSelector", side_effect=OSError("fixture setup failure")):
            with self.assertRaisesRegex(OSError, "fixture setup failure"):
                self.run_python("import time\ntime.sleep(30)")
        self.assertEqual(len(started), 1)
        self.assertIsNotNone(started[0].returncode)
        self.assertNotEqual(started[0].returncode, 0)
        self.assertTrue(started[0].stdout.closed)

    def test_invalid_requests_and_non_linux_fail_before_spawn(self):
        invalid = [dict(timeout=0), dict(timeout=float("nan")), dict(timeout=float("inf")),
                   dict(timeout=True), dict(timeout=311), dict(cpu_seconds=0),
                   dict(cpu_seconds=True), dict(cpu_seconds=312), dict(memory_mib=255),
                   dict(memory_mib=16385), dict(command=[]), dict(command="worker"),
                   dict(command=["worker", "bad\0option"]), dict(cwd=self.root / "missing")]
        with mock.patch.object(PROCESS.subprocess, "Popen") as spawn:
            for request in invalid:
                with self.subTest(request=request), self.assertRaises(ValueError):
                    self.run_python("pass", **request)
            with mock.patch.object(PROCESS.platform, "system", return_value="Darwin"):
                with self.assertRaisesRegex(ValueError, "requires_linux"):
                    self.run_python("pass")
            spawn.assert_not_called()


if __name__ == "__main__":
    unittest.main()
