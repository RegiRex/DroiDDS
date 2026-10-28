#!/usr/bin/env python3
"""CodexAstraUlt: Original subprocess fixtures qualify bounded compilation tools."""

import copy
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import signal
import sys
import tempfile
import unittest
from unittest import mock


# CodexAstraUlt: Import only the assigned helper; tests need no game, compiler
# installation, executable library load, network access or shared build output.
SPEC = importlib.util.spec_from_file_location(
    "private_compile_process", Path(__file__).resolve().parents[1] / "private_compile_process.py")
PROCESS = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(PROCESS)


class ProcessTests(unittest.TestCase):
    """CodexAstraUlt: Execute actual original children under the Linux limits."""

    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="droidds-compile-process-")
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)

    def run_python(self, source, **overrides):
        arguments = {"command": [sys.executable, "-c", source], "cwd": self.root,
                     "timeout": 3, "cpu_seconds": 2, "memory_mib": 256,
                     "file_bytes": 1024**2}
        arguments.update(overrides)
        return PROCESS.run_command(**arguments)

    def test_real_child_observes_limits_closed_stdin_and_clean_environment(self):
        env = dict(os.environ, CPATH="untrusted-include", CFLAGS="-ffast-math",
                   HTTP_PROXY="http://retained.invalid", LANG="untrusted")
        result = self.run_python(
            "import json, os, resource, sys\n"
            "print(json.dumps({'stdin':sys.stdin.read(), 'cpu':resource.getrlimit(resource.RLIMIT_CPU), "
            "'as':resource.getrlimit(resource.RLIMIT_AS), 'file':resource.getrlimit(resource.RLIMIT_FSIZE), "
            "'core':resource.getrlimit(resource.RLIMIT_CORE), 'cpath':os.environ.get('CPATH'), "
            "'cflags':os.environ.get('CFLAGS'), 'proxy':os.environ.get('HTTP_PROXY'), "
            "'locale':os.environ.get('LC_ALL')}))", env=env)
        self.assertEqual(result["outcome"], "completed")
        self.assertEqual(result["exit_code"], 0)
        actual = json.loads(result["log_tail"])
        self.assertEqual(actual, {"stdin": "", "cpu": [2, 2], "as": [256 * 1024**2] * 2,
                                  "file": [1024**2] * 2, "core": [0, 0], "cpath": None,
                                  "cflags": None, "proxy": "http://retained.invalid", "locale": "C"})
        self.assertEqual(result["limits"]["cpu_scope"], "per_process_all_threads")
        self.assertEqual(list(self.root.iterdir()), [])

    def test_real_child_log_is_drained_but_only_tail_is_retained(self):
        result = self.run_python("import os\nos.write(1,b'X'*200000+b'LAST-BYTES')")
        self.assertEqual(result["exit_code"], 0)
        self.assertEqual(result["log_bytes_seen"], 200010)
        self.assertEqual(len(result["log_tail"]), PROCESS.LOG_BYTES)
        self.assertTrue(result["log_tail"].endswith("LAST-BYTES"))
        self.assertEqual(result["limits"]["log_retained_bytes"], PROCESS.LOG_BYTES)

    def test_continuous_log_writer_cannot_starve_wall_timeout(self):
        result = self.run_python("import os\nwhile True: os.write(1,b'X'*8192)", timeout=0.15)
        self.assertEqual(result["outcome"], "timeout")
        self.assertNotEqual(result["exit_code"], 0)
        self.assertLess(result["elapsed_seconds"], 5)
        self.assertLessEqual(len(result["log_tail"]), PROCESS.LOG_BYTES)

    def test_real_sleeping_process_is_stopped_at_wall_deadline(self):
        result = self.run_python("import time\ntime.sleep(30)", timeout=0.1)
        self.assertEqual(result["outcome"], "timeout")
        self.assertNotEqual(result["exit_code"], 0)
        self.assertLess(result["elapsed_seconds"], 5)

    def test_grandchild_is_terminated_even_when_leader_exits_successfully(self):
        result = self.run_python(
            "import os, signal, time\n"
            "pid=os.fork()\n"
            "if pid==0:\n"
            " signal.signal(signal.SIGTERM,signal.SIG_IGN)\n"
            " print(os.getpid(),flush=True)\n"
            " time.sleep(30)\n"
            "else:\n"
            " time.sleep(0.1)\n"
            " os._exit(0)\n")
        self.assertEqual(result["outcome"], "completed")
        self.assertEqual(result["exit_code"], 0)
        pid = int(result["log_tail"].strip())
        # CodexAstraUlt: The helper cannot waitpid an orphaned grandchild; Linux
        # may retain its zombie until the adopter reaps it, but it must not run.
        path = Path(f"/proc/{pid}/stat")
        if path.exists():
            state = path.read_text().rsplit(") ", 1)[1].split()[0]
            self.assertEqual(state, "Z")

    def test_keyboard_interrupt_stops_child_and_returns_incomplete_outcome(self):
        result = self.run_python(
            "import os,signal,time\ntime.sleep(0.05)\n"
            "os.kill(os.getppid(),signal.SIGINT)\ntime.sleep(30)")
        self.assertEqual(result["outcome"], "interrupted")
        self.assertNotEqual(result["exit_code"], 0)
        self.assertLess(result["elapsed_seconds"], 5)

    def test_cpu_limit_terminates_actual_busy_child(self):
        result = self.run_python("while True: pass", timeout=4, cpu_seconds=1)
        self.assertEqual(result["outcome"], "completed")
        self.assertEqual(result["exit_code"], -signal.SIGKILL)
        self.assertLess(result["elapsed_seconds"], 5)

    def test_address_space_limit_rejects_actual_large_allocation(self):
        result = self.run_python("data=bytearray(512*1024*1024)")
        self.assertEqual(result["outcome"], "completed")
        self.assertNotEqual(result["exit_code"], 0)
        self.assertIn("MemoryError", result["log_tail"])

    def test_file_limit_bounds_partial_child_output(self):
        result = self.run_python("from pathlib import Path\nPath('partial.o').write_bytes(b'X'*4096)", file_bytes=1024)
        self.assertEqual(result["outcome"], "completed")
        self.assertNotEqual(result["exit_code"], 0)
        self.assertLessEqual((self.root / "partial.o").stat().st_size, 1024)

    def test_invalid_requests_fail_before_spawn(self):
        invalid = [dict(timeout=0), dict(timeout=float("nan")), dict(timeout=float("inf")),
                   dict(timeout=True), dict(timeout=3601), dict(cpu_seconds=0), dict(cpu_seconds=True),
                   dict(cpu_seconds=3601), dict(memory_mib=255), dict(memory_mib=16385),
                   dict(file_bytes=0), dict(file_bytes=PROCESS.MAX_FILE_BYTES + 1),
                   dict(command=[]), dict(command="cc"), dict(command=["cc", "bad\0option"]),
                   dict(env={"BAD": 42}), dict(cwd=self.root / "missing")]
        with mock.patch.object(PROCESS.subprocess, "Popen") as spawn:
            for request in invalid:
                with self.subTest(request=request), self.assertRaises(ValueError):
                    self.run_python("pass", **request)
            spawn.assert_not_called()


class CompilerIdentityTests(unittest.TestCase):
    """CodexAstraUlt: Original tool bytes expose helper mutation without installations."""

    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="droidds-compiler-identity-")
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.paths = {}
        for name in ("driver", "cc1", "as", "collect2", "ld"):
            path = self.root / name
            path.write_bytes(b"\x7fELF original tool " + name.encode())
            path.chmod(0o700)
            self.paths[name] = path
        self.version = "original gcc (Fixture) 1.0\nFree Software Foundation"
        self.target = "x86_64-original-linux-gnu"
        self.probe_commands = []
        self.system = mock.patch.object(PROCESS.platform, "system", return_value="Linux")
        self.machine = mock.patch.object(PROCESS.platform, "machine", return_value="x86_64")
        self.system.start()
        self.machine.start()
        self.addCleanup(self.system.stop)
        self.addCleanup(self.machine.stop)

    def probe(self, command, cwd, timeout, cpu_seconds, memory_mib, file_bytes, env=None):
        self.assertEqual((timeout, cpu_seconds, memory_mib, file_bytes), (10, 10, 512, 1024**2))
        self.assertEqual(env["LC_ALL"], "C")
        self.probe_commands.append(command.copy())
        arguments = command[1:]
        if arguments[0] == "--no-default-config":
            arguments = arguments[1:]
        if arguments[0] == "--version":
            text = self.version
        elif arguments[0] == "-dumpmachine":
            text = self.target
        else:
            name = arguments[0].removeprefix("-print-prog-name=")
            text = str(self.paths[name])
        return {"outcome": "completed", "exit_code": 0, "log_tail": text + "\n",
                "log_bytes_seen": len(text) + 1}

    def inspect(self):
        with mock.patch.object(PROCESS, "run_command", side_effect=self.probe):
            return PROCESS.inspect_compiler(self.paths["driver"])

    def test_gcc_identity_binds_driver_and_actual_helper_bytes(self):
        result = self.inspect()
        self.assertEqual(result["invocation"], str(self.paths["driver"]))
        identity = result["identity"]
        self.assertEqual(identity["family"], "gcc")
        self.assertEqual(identity["target"], self.target)
        self.assertFalse(identity["binary_source_attested"])
        self.assertEqual(set(identity["tools"]), set(self.paths))
        for name, item in identity["tools"].items():
            data = self.paths[name].read_bytes()
            self.assertEqual(item, {"path": str(self.paths[name]), "bytes": len(data),
                                    "sha256": hashlib.sha256(data).hexdigest()})

    def test_changed_helper_changes_identity_when_driver_is_unchanged(self):
        first = self.inspect()
        self.paths["cc1"].write_bytes(b"\x7fELF changed original helper")
        second = self.inspect()
        self.assertNotEqual(first, second)
        self.assertEqual(first["identity"]["tools"]["driver"], second["identity"]["tools"]["driver"])

    def test_helper_changed_during_discovery_is_rejected(self):
        def changed(*args, **kwargs):
            result = self.probe(*args, **kwargs)
            if args[0][1] == "-print-prog-name=ld":
                self.paths["cc1"].write_bytes(b"\x7fELF replacement")
            return result
        with mock.patch.object(PROCESS, "run_command", side_effect=changed):
            with self.assertRaisesRegex(ValueError, "changed_during_inspection"):
                PROCESS.inspect_compiler(self.paths["driver"])

    def test_clang_identity_uses_integrated_driver_and_external_linker(self):
        self.version = "clang version 19.1.0 (original fixture)"
        result = self.inspect()
        self.assertEqual(result["identity"]["family"], "clang")
        self.assertEqual(set(result["identity"]["tools"]), {"driver", "ld"})
        # CodexAstraUlt: Query the effective target/linker under the same
        # explicit no-config policy used by the subsequent compiler recipe.
        self.assertEqual([command[1:] for command in self.probe_commands], [
            ["--version"], ["--no-default-config", "-dumpmachine"],
            ["--no-default-config", "-print-prog-name=ld"],
        ])

    def test_unsupported_family_cross_target_and_wrapper_are_rejected(self):
        self.version = "another original compiler"
        with self.assertRaisesRegex(ValueError, "unsupported_native_compiler_family"):
            self.inspect()
        self.version = "original gcc\nFree Software Foundation"
        self.target = "aarch64-original-linux-gnu"
        with self.assertRaisesRegex(ValueError, "target_is_not_native_linux"):
            self.inspect()
        self.paths["driver"].write_text("#!/bin/sh\nexit 0\n")
        with self.assertRaisesRegex(ValueError, "wrapper_unsupported"):
            self.inspect()

    def test_truncated_failed_or_empty_metadata_cannot_identify_a_compiler(self):
        original = {"outcome": "completed", "exit_code": 0, "log_tail": self.version, "log_bytes_seen": len(self.version)}
        for change in ({"log_bytes_seen": PROCESS.LOG_BYTES + 1}, {"exit_code": 1},
                       {"outcome": "timeout"}, {"log_tail": ""}):
            result = copy.deepcopy(original)
            result.update(change)
            with self.subTest(change=change), mock.patch.object(PROCESS, "run_command", return_value=result):
                with self.assertRaises(ValueError):
                    PROCESS.inspect_compiler(self.paths["driver"])

    def test_environment_cleanup_removes_injection_without_changing_proxy(self):
        dirty = {name: "override" for name in PROCESS._ENVIRONMENT_EXCLUSIONS}
        dirty.update(LD_PRELOAD="override", LD_AUDIT="override", GCC_EXEC_PREFIX="override",
                     CLANG_CONFIG_FILE_SYSTEM_DIR="override", HTTP_PROXY="http://retained.invalid",
                     HTTPS_PROXY="http://retained.invalid", PATH="/original/path", HOME="/original/home")
        cleaned = PROCESS.clean_environment(dirty)
        self.assertEqual(cleaned, {"HTTP_PROXY": "http://retained.invalid", "HTTPS_PROXY": "http://retained.invalid",
                                   "PATH": "/original/path", "HOME": "/original/home", "LC_ALL": "C", "LANG": "C",
                                   "SOURCE_DATE_EPOCH": "0", "PYTHONDONTWRITEBYTECODE": "1"})


if __name__ == "__main__":
    unittest.main()
