"""CodexAstraUlt: Reject misleading Android proof and unsafe device-run contracts."""

import copy
import importlib.util
import json
import os
from pathlib import Path
import shlex
import signal
import struct
import sys
import tempfile
import time
import unittest
from unittest import mock
import uuid
import zipfile

SPEC = importlib.util.spec_from_file_location(
    "run_android_probe", Path(__file__).parents[1] / "run_android_probe.py")
RUNNER = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(RUNNER)
REQUEST = "038443d8-40e4-4e83-a991-501702b37836"
MANIFEST = {"package": "org.droidds.probe", "version_code": 2, "version_name": "0.0.2",
            "debuggable": True, "test_only": True}


def report():
    """CodexAstraUlt: Protocol examples are unit-test inputs, never device evidence."""
    values = [("arm_integer_memory", 11, 0, 0, 11),
              ("thumb_integer_memory", 7, 0, 0, 7),
              ("arm_missing_entry_fallback", 2, 3, 0, 5),
              ("arm_to_thumb_native", 5, 0, 1, 5)]
    return {
        "schema": 1, "kind": "droidds-android-cpu-probe", "status": "passed",
        "version": "0.0.2", "host_arch": "aarch64", "host_os": "android", "pointer_bits": 64,
        "host_page_size": 4096, "abi": 4, "generation": 3,
        "android_shell": {"schema_version": 1, "request_id": REQUEST,
                          "run_id": "f8d9dc64-03a2-422d-a017-2f7849eeeb20", "process_id": 123,
                          "started_at_epoch_ms": 100, "finished_at_epoch_ms": 110,
                          "app_version_name": "0.0.2", "app_version_code": 2},
        "cases": [{"name": name, "library": f"libdds_fixture_{name}.so", "status": "passed",
                   "checkpoint_svc": 42, "native_calls": 1, "native_lookup_hits": lookup,
                   "native_budget_charged": work, "fallback_steps": fallback,
                   "instruction_callbacks": 0, "interpreter_steps": interpreted,
                   "memory_bytes_compared": 65536, "strict_expected_match": True,
                   "strict_interpreter_match": True, "route_counts_match": True}
                  for name, work, fallback, lookup, interpreted in values],
        "negative_controls": [{"name": name, "status": "passed", "rejection": "actual mismatch"}
                              for name in ("nan_shaped_integer_register_mismatch",
                                           "nan_shaped_integer_memory_mismatch")],
    }


class ReportTests(unittest.TestCase):
    """CodexAstraUlt: Mutate proof independently so permissive acceptance is visible."""

    def reject(self, changed, message):
        with self.assertRaisesRegex(ValueError, message):
            RUNNER.validate_report(changed, REQUEST, MANIFEST)

    def test_complete_protocol_examples_qualify_only_their_observed_page_size(self):
        for size in (4096, 16384):
            value = report()
            value["host_page_size"] = size
            RUNNER.validate_report(value, REQUEST, MANIFEST)

    def test_host_reports_cannot_be_android_execution(self):
        for key, value in (("host_os", "linux"), ("host_arch", "x86_64"),
                           ("pointer_bits", 32), ("kind", "mock"), ("status", "running")):
            with self.subTest(key=key):
                changed = report()
                changed[key] = value
                self.reject(changed, "identity/status")

    def test_stale_or_missing_request_is_rejected(self):
        for value in (None, str(uuid.uuid4()), ""):
            changed = report()
            changed["android_shell"]["request_id"] = value
            self.reject(changed, "request_id")

    def test_abi_schema_and_generation_must_be_exact_integers(self):
        for key, value in (("schema", True), ("abi", 5), ("generation", "3")):
            changed = report()
            changed[key] = value
            self.reject(changed, "identity/status")

    def test_report_version_must_match_installed_apk(self):
        changed = report()
        changed["android_shell"]["app_version_code"] = 1
        self.reject(changed, "version")
        changed = report()
        changed["version"] = "0.0.1"
        self.reject(changed, "version")

    def test_unobserved_or_invalid_page_size_is_rejected(self):
        for page in (None, True, 0, 4097, 131072):
            changed = report()
            changed["host_page_size"] = page
            self.reject(changed, "page size")

    def test_partial_duplicate_and_unknown_cases_are_rejected(self):
        changed = report()
        changed["cases"].pop()
        self.reject(changed, "CPU cases")
        changed = report()
        changed["cases"][3] = copy.deepcopy(changed["cases"][0])
        self.reject(changed, "CPU cases")
        changed = report()
        changed["cases"][0]["name"] = "unvalidated_new_fixture"
        self.reject(changed, "CPU cases")

    def test_every_counter_is_required_and_native_fallback_routes_are_exact(self):
        for key in ("checkpoint_svc", "native_calls", "native_lookup_hits", "native_budget_charged",
                    "fallback_steps", "instruction_callbacks", "interpreter_steps", "memory_bytes_compared"):
            with self.subTest(counter=key):
                changed = report()
                del changed["cases"][0][key]
                self.reject(changed, "proof counter")
        for index, key, value in ((0, "native_calls", True), (0, "fallback_steps", 1),
                                  (2, "fallback_steps", 0), (3, "native_lookup_hits", 0),
                                  (1, "native_budget_charged", 0)):
            changed = report()
            changed["cases"][index][key] = value
            self.reject(changed, "proof counter")

    def test_strict_comparisons_cannot_be_missing_false_or_truthy_integers(self):
        for key in ("strict_expected_match", "strict_interpreter_match", "route_counts_match"):
            for value in (None, False, 1):
                changed = report()
                changed["cases"][0][key] = value
                self.reject(changed, "strict CPU proof")

    def test_negative_controls_must_exist_and_prove_rejection(self):
        changed = report()
        changed["negative_controls"].pop()
        self.reject(changed, "negative controls")
        changed = report()
        changed["negative_controls"][0]["rejection"] = ""
        self.reject(changed, "prove rejection")


def binary_manifest(package="org.droidds.probe", debuggable=True, test_only=True, utf8=True):
    """CodexAstraUlt: Minimal original binary XML exercises actual package decoding."""
    strings = ["manifest", "application", "package", package,
               "http://schemas.android.com/apk/res/android", "versionCode", "versionName",
               "0.0.2", "debuggable", "testOnly"]
    data = bytearray()
    offsets = []
    for text in strings:
        offsets.append(len(data))
        encoded = text.encode("utf-8" if utf8 else "utf-16le")
        if utf8:
            data.extend(bytes([len(text), len(encoded)]) + encoded + b"\x00")
        else:
            data.extend(struct.pack("<H", len(text)) + encoded + b"\x00\x00")
    data.extend(b"\x00" * (-len(data) % 4))
    start = 28 + 4 * len(strings)
    pool = struct.pack("<HHIIIIII", 1, 28, start + len(data), len(strings), 0,
                       0x100 if utf8 else 0, start, 0)
    pool += struct.pack("<" + "I" * len(offsets), *offsets) + data

    def element(name, attrs):
        result = struct.pack("<HHIII", 0x102, 16, 36 + len(attrs) * 20, 1, 0xffffffff)
        result += struct.pack("<IIHHHHHH", 0xffffffff, name, 20, 20, len(attrs), 0, 0, 0)
        for namespace, name, value_type, value in attrs:
            result += struct.pack("<IIIHBBI", namespace, name, 0xffffffff, 8, 0, value_type, value)
        return result

    contents = pool + element(0, [(0xffffffff, 2, 3, 3), (4, 5, 0x10, 2), (4, 6, 3, 7)])
    contents += element(1, [(4, 8, 0x12, int(debuggable)), (4, 9, 0x12, int(test_only))])
    return struct.pack("<HHI", 3, 8, 8 + len(contents)) + contents


class ManifestTests(unittest.TestCase):
    """CodexAstraUlt: Package restrictions apply before any device mutation."""

    def decode(self, content, allow_prerelease=False):
        with tempfile.TemporaryDirectory() as temp:
            apk = Path(temp) / "fixture.apk"
            with zipfile.ZipFile(apk, "w") as archive:
                archive.writestr("AndroidManifest.xml", content)
            return RUNNER.apk_manifest(apk, allow_prerelease=allow_prerelease)

    def test_utf8_and_utf16_android_string_pools(self):
        for utf8 in (True, False):
            self.assertEqual(self.decode(binary_manifest(utf8=utf8)), MANIFEST)

    def test_another_package_cannot_be_installed(self):
        with self.assertRaisesRegex(ValueError, "Only the org.droidds.probe"):
            self.decode(binary_manifest(package="org.example.private"))

    def test_non_debug_and_non_test_apks_are_rejected(self):
        for options in ({"debuggable": False}, {"test_only": False}):
            with self.assertRaisesRegex(ValueError, "debuggable|testOnly"):
                self.decode(binary_manifest(**options))

    def test_published_probe_requires_explicit_prerelease_scope(self):
        decoded = self.decode(binary_manifest(test_only=False), allow_prerelease=True)
        self.assertFalse(decoded["test_only"])
        self.assertEqual(decoded["package"], "org.droidds.probe")
        self.assertTrue(decoded["debuggable"])
        for options in ({"package": "another.app"}, {"debuggable": False}):
            with self.assertRaises(ValueError):
                self.decode(binary_manifest(test_only=False, **options), allow_prerelease=True)

    def test_truncated_and_malformed_manifests_are_rejected(self):
        good = binary_manifest()
        malformed = bytearray(good)
        struct.pack_into("<I", malformed, 12, 0xffffffff)
        for content in (good[:-1], b"<manifest package='org.droidds.probe'/>", malformed):
            with self.subTest(length=len(content)), self.assertRaises(ValueError):
                self.decode(content)


class FakeAdb:
    """CodexAstraUlt: Record a simulated command boundary without touching a device."""

    def __init__(self, output, result=None, installed_sha="a" * 64, install_failure=False):
        self.output = output
        self.commands = []
        self.result = result or report()
        self.installed_sha = installed_sha
        self.install_failure = install_failure

    def run(self, name, args, **kwargs):
        self.commands.append((name, args))
        if name == "device-state":
            return "device\n"
        if name == "install":
            if self.install_failure:
                raise RuntimeError("INSTALL_FAILED_UPDATE_INCOMPATIBLE")
            return "Success\n"
        raise AssertionError(name)

    def remote(self, name, words, **kwargs):
        self.commands.append((name, words))
        if name.startswith("property-"):
            return "arm64-v8a\n" if words[-1] == "ro.product.cpu.abi" else "test-protocol\n"
        if name == "installed-apk-path":
            return "package:/data/app/synthetic/base.apk\n"
        if name == "installed-apk-sha256":
            return self.installed_sha + "  /data/app/synthetic/base.apk\n"
        if name in ("stop-before-run", "remove-stale-report", "launch", "stop-after-run"):
            return ""
        if name == "read-report":
            return json.dumps(self.result)
        raise AssertionError(name)


class DeviceContractTests(unittest.TestCase):
    """CodexAstraUlt: Prove data-preserving scope and cleanup with a fake boundary."""

    def run_fake(self, directory, **kwargs):
        adb = FakeAdb(Path(directory), **kwargs)
        evidence = {"request_id": REQUEST, "apk_sha256": "a" * 64}
        RUNNER.execute_probe(adb, Path("/tmp/fixture.apk"), MANIFEST, evidence, 5)
        return adb

    def test_only_probe_package_is_launched_once_without_destructive_operations(self):
        with tempfile.TemporaryDirectory() as temp:
            adb = self.run_fake(temp)
        install = next(args for name, args in adb.commands if name == "install")
        self.assertEqual(install, ["install", "-r", "-t", "/tmp/fixture.apk"])
        self.assertEqual([args for name, args in adb.commands if name == "launch"],
                         [["am", "start", "-W", "-n", "org.droidds.probe/.ProbeActivity",
                           "--es", "request_id", REQUEST]])
        self.assertEqual([args for name, args in adb.commands if name == "remove-stale-report"],
                         [["run-as", "org.droidds.probe", "rm", "-f", "files/latest-probe.json"]])
        stops = [args for _, args in adb.commands if "force-stop" in args]
        self.assertEqual(stops, [["am", "force-stop", "org.droidds.probe"]] * 2)
        for _, args in adb.commands:
            self.assertTrue(set(args).isdisjoint({"uninstall", "clear", "root", "reboot", "logcat"}))

    def test_failed_report_still_force_stops_only_owned_probe(self):
        with tempfile.TemporaryDirectory() as temp:
            failed = report()
            failed["status"] = "failed"
            adb = FakeAdb(Path(temp), result=failed)
            with self.assertRaisesRegex(ValueError, "identity/status"):
                RUNNER.execute_probe(adb, Path("/tmp/fixture.apk"), MANIFEST,
                                     {"request_id": REQUEST, "apk_sha256": "a" * 64}, 5)
            self.assertEqual(adb.commands[-1], ("stop-after-run", ["am", "force-stop", RUNNER.PACKAGE]))
            self.assertTrue((Path(temp) / "android-probe.json").is_file())

    def test_apk_hash_mismatch_prevents_launch(self):
        with tempfile.TemporaryDirectory() as temp:
            adb = FakeAdb(Path(temp), installed_sha="b" * 64)
            with self.assertRaisesRegex(RuntimeError, "SHA-256 differs"):
                RUNNER.execute_probe(adb, Path("/tmp/fixture.apk"), MANIFEST,
                                     {"request_id": REQUEST, "apk_sha256": "a" * 64}, 5)
            self.assertNotIn("launch", [name for name, _ in adb.commands])

    def test_running_marker_cannot_pass_and_deadline_stops_owned_probe(self):
        with tempfile.TemporaryDirectory() as temp:
            running = report()
            running["status"] = "running"
            adb = FakeAdb(Path(temp), result=running)
            with mock.patch.object(RUNNER.time, "monotonic", side_effect=[0, 0, 0, 0, 6, 6]), \
                    mock.patch.object(RUNNER.time, "sleep"), \
                    self.assertRaisesRegex(RuntimeError, "timed out without a complete"):
                RUNNER.execute_probe(adb, Path("/tmp/fixture.apk"), MANIFEST,
                                     {"request_id": REQUEST, "apk_sha256": "a" * 64}, 5)
            self.assertEqual(adb.commands[-1], ("stop-after-run", ["am", "force-stop", RUNNER.PACKAGE]))

    def test_signing_failure_never_triggers_uninstall(self):
        with tempfile.TemporaryDirectory() as temp:
            adb = FakeAdb(Path(temp), install_failure=True)
            with self.assertRaisesRegex(RuntimeError, "Do not uninstall or clear data"):
                RUNNER.execute_probe(adb, Path("/tmp/fixture.apk"), MANIFEST,
                                     {"request_id": REQUEST, "apk_sha256": "a" * 64}, 5)
            self.assertEqual(adb.commands[-1][0], "install")

    def test_remote_argv_quotes_shell_metacharacters_as_literal_words(self):
        with tempfile.TemporaryDirectory() as temp:
            adb = RUNNER.Adb("/usr/bin/adb", "literal-serial", Path(temp), [])
            words = ["sha256sum", "/data/app/space ' ; $(false) `false`/base.apk"]
            with mock.patch.object(adb, "run", return_value="") as run:
                adb.remote("hash", words, output=True)
                args = run.call_args.args[1]
                self.assertEqual(args[0], "exec-out")
                self.assertEqual(shlex.split(args[1]), words)

    def test_timeout_stops_actual_local_client_and_its_descendant(self):
        # CodexAstraUlt: This is a real process-tree regression, not an Android
        # execution claim. The fixture sleeps and never contacts ADB or USB.
        with tempfile.TemporaryDirectory() as temp:
            directory = Path(temp)
            script = directory / "fake-adb"
            pid_file = directory / "child.pid"
            script.write_text(f"#!{sys.executable}\nimport subprocess,time\n"
                              "child=subprocess.Popen(['sleep','30'])\n"
                              f"open({str(pid_file)!r},'w').write(str(child.pid))\n"
                              "time.sleep(30)\n")
            script.chmod(0o700)
            adb = RUNNER.Adb(str(script), "synthetic", directory, [])
            with self.assertRaisesRegex(RuntimeError, "timed out"):
                adb.run("timeout", ["get-state"], timeout=0.2)
            pid = int(pid_file.read_text())
            for _ in range(30):
                status = Path(f"/proc/{pid}/stat")
                if not status.exists() or status.read_text().split()[2] == "Z":
                    break
                time.sleep(0.01)
            else:
                os.kill(pid, signal.SIGKILL)
                self.fail("ADB client's descendant survived timeout")


if __name__ == "__main__":
    unittest.main()
