"""CodexAstraUlt: Original fixtures for the isolated public-tool bootstrap."""

from __future__ import annotations

from contextlib import redirect_stdout
import copy
import importlib.util
import io
import json
import os
from pathlib import Path
import stat
import subprocess
import sys
import tarfile
import tempfile
from types import SimpleNamespace
import unittest
from unittest import mock
import zipfile


# CodexAstraUlt: Import the reviewed installer without running its CLI.
SCRIPT = Path(__file__).resolve().parents[1] / "setup_android_title_tools.py"
SPEC = importlib.util.spec_from_file_location("droidds_setup_tools_under_test", SCRIPT)
setup = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(setup)


class FixtureCase(unittest.TestCase):
    """CodexAstraUlt: Keep all artificial inputs and effects in one temporary tree."""

    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="droidds-tool-tests-")
        self.addCleanup(self.temporary.cleanup)
        self.folder = Path(self.temporary.name)

    def archive(self, entries, name="tools.zip"):
        path = self.folder / name
        with zipfile.ZipFile(path, "w") as output:
            for member, content, mode in entries:
                item = zipfile.ZipInfo(member)
                item.create_system = 3
                item.external_attr = mode << 16
                output.writestr(item, content)
        return path

    def regular_archive(self):
        return self.archive([("fixture/bin/tool", b"authored-tool", stat.S_IFREG | 0o755)])

    def package(self, path):
        return {"url": "https://dl.google.com/android/repository/" + path.name,
                "root": "fixture", "sha256": setup.digest(path), "maximum_bytes": path.stat().st_size}

    def root(self):
        root = self.folder / "owned"
        root.mkdir()
        for name in ("archives", "receipts", "logs", "cargo"):
            (root / name).mkdir()
        return root


class OwnershipTests(FixtureCase):
    """CodexAstraUlt: Refuse adopting existing user folders or following aliases."""

    def test_new_root_is_owned_and_same_manifest_can_resume(self):
        path = self.folder / "new-tools"
        with setup.owned_root(path, "a" * 64) as root:
            self.assertEqual(root, path)
            marker = json.loads((root / "setup-state.json").read_text())
            self.assertEqual(marker["kind"], setup.KIND)
        with setup.owned_root(path, "a" * 64):
            self.assertTrue((path / "cargo").is_dir())

    def test_unknown_existing_folder_is_preserved(self):
        path = self.folder / "existing"
        path.mkdir()
        data = path / "mine.txt"
        data.write_bytes(b"preserve")
        with self.assertRaisesRegex(ValueError, "recognized"):
            with setup.owned_root(path, "a" * 64):
                self.fail("adopted user folder")
        self.assertEqual(data.read_bytes(), b"preserve")
        self.assertEqual(list(path.iterdir()), [data])

    def test_mismatched_manifest_is_rejected(self):
        path = self.folder / "new-tools"
        with setup.owned_root(path, "a" * 64):
            pass
        before = (path / "setup-state.json").read_bytes()
        with self.assertRaisesRegex(ValueError, "manifest"):
            with setup.owned_root(path, "b" * 64):
                self.fail("accepted other manifest")
        self.assertEqual((path / "setup-state.json").read_bytes(), before)

    def test_symlink_ancestor_rejected(self):
        alias = self.folder / "alias"
        alias.symlink_to(self.folder, target_is_directory=True)
        with self.assertRaisesRegex(ValueError, "symlink"):
            setup.plain_path(alias / "tools")

    def test_git_directory_and_worktree_file_rejected(self):
        for name, worktree in (("normal", False), ("worktree", True)):
            checkout = self.folder / name
            checkout.mkdir()
            if worktree:
                (checkout / ".git").write_text("gitdir: /elsewhere\n")
            else:
                (checkout / ".git").mkdir()
                (checkout / ".git/HEAD").write_text("ref: refs/heads/main\n")
            with self.subTest(name=name), self.assertRaisesRegex(ValueError, "Git"):
                setup.outside_git(checkout / "nested" / "tools")

    def test_empty_sandbox_git_mount_is_not_a_checkout(self):
        (self.folder / ".git").mkdir()
        setup.outside_git(self.folder / "tools")

    def test_owned_subdirectory_symlink_rejected(self):
        path = self.folder / "tools"
        with setup.owned_root(path, "a" * 64):
            pass
        (path / "cargo").rmdir()
        (path / "cargo").symlink_to(self.folder)
        with self.assertRaisesRegex(ValueError, "symlink"):
            with setup.owned_root(path, "a" * 64):
                self.fail("accepted redirected cache")

    def test_parallel_setup_is_rejected(self):
        path = self.folder / "tools"
        with setup.owned_root(path, "a" * 64):
            with self.assertRaisesRegex(ValueError, "Another setup"):
                with setup.owned_root(path, "a" * 64):
                    self.fail("accepted concurrent writer")


class ArchiveTests(FixtureCase):
    """CodexAstraUlt: Executable modes survive; malformed paths cannot escape staging."""

    def test_zip_regular_file_mode_and_confined_link(self):
        path = self.archive([
            ("fixture/bin/tool", b"authored-tool", stat.S_IFREG | 0o755),
            ("fixture/link", b"bin/tool", stat.S_IFLNK | 0o777),
        ])
        root = setup.unpack(path, self.folder / "unpacked", "fixture")
        self.assertEqual((root / "link").read_bytes(), b"authored-tool")
        self.assertEqual(stat.S_IMODE((root / "bin/tool").stat().st_mode), 0o755)

    def test_zip_traversal_absolute_and_backslash_rejected(self):
        for index, name in enumerate(("fixture/../../outside", "/fixture/file", "fixture\\file")):
            path = self.archive([(name, b"bad", stat.S_IFREG | 0o644)], f"bad-{index}.zip")
            with self.subTest(name=name), self.assertRaises(ValueError):
                setup.unpack(path, self.folder / f"out-{index}", "fixture")
        self.assertFalse((self.folder / "outside").exists())

    def test_zip_wrong_root_rejected(self):
        path = self.archive([("unexpected/file", b"bad", stat.S_IFREG | 0o644)])
        with self.assertRaisesRegex(ValueError, "root"):
            setup.unpack(path, self.folder / "out", "fixture")

    def test_zip_escaping_link_rejected(self):
        path = self.archive([("fixture/link", b"../../outside", stat.S_IFLNK | 0o777)])
        with self.assertRaisesRegex(ValueError, "escapes"):
            setup.unpack(path, self.folder / "out", "fixture")

    def test_zip_link_chain_escaping_root_rejected(self):
        path = self.archive([
            ("fixture/first", b"second", stat.S_IFLNK | 0o777),
            ("fixture/second", b"../../outside", stat.S_IFLNK | 0o777),
        ])
        with self.assertRaisesRegex(ValueError, "escapes"):
            setup.unpack(path, self.folder / "out", "fixture")

    def test_zip_special_file_rejected(self):
        path = self.archive([("fixture/device", b"", stat.S_IFCHR | 0o600)])
        with self.assertRaisesRegex(ValueError, "special"):
            setup.unpack(path, self.folder / "out", "fixture")

    def test_tar_executable_and_relative_link_preserved(self):
        path = self.folder / "tools.tar"
        with tarfile.open(path, "w") as output:
            item = tarfile.TarInfo("fixture/tool")
            item.mode, item.size = 0o755, 4
            output.addfile(item, io.BytesIO(b"tool"))
            item = tarfile.TarInfo("fixture/link")
            item.type, item.linkname = tarfile.SYMTYPE, "tool"
            output.addfile(item)
        root = setup.unpack(path, self.folder / "out", "fixture")
        self.assertEqual((root / "link").read_bytes(), b"tool")
        self.assertEqual(stat.S_IMODE((root / "tool").stat().st_mode), 0o755)

    def test_tar_traversal_rejected_without_external_write(self):
        path = self.folder / "tools.tar"
        with tarfile.open(path, "w") as output:
            item = tarfile.TarInfo("fixture/../../external")
            item.size = 4
            output.addfile(item, io.BytesIO(b"evil"))
        with self.assertRaises(ValueError):
            setup.unpack(path, self.folder / "out", "fixture")
        self.assertFalse((self.folder / "external").exists())

    def test_tar_root_escape_symlink_rejected(self):
        path = self.folder / "tools.tar"
        with tarfile.open(path, "w") as output:
            item = tarfile.TarInfo("fixture/link")
            item.type, item.linkname = tarfile.SYMTYPE, "../sibling"
            output.addfile(item)
        with self.assertRaisesRegex(ValueError, "escapes"):
            setup.unpack(path, self.folder / "out", "fixture")


class CacheAndReceiptTests(FixtureCase):
    """CodexAstraUlt: Reuse requires verified bytes and survives publication interruption."""

    def test_verified_external_cache_is_read_only(self):
        archive = self.regular_archive()
        root = self.root()
        before = archive.stat()
        with mock.patch.object(setup.urllib.request, "urlopen", side_effect=AssertionError("network used")):
            result = setup.acquire(self.package(archive), root, self.folder, True)
        self.assertEqual(result, archive)
        self.assertEqual(archive.stat().st_mtime_ns, before.st_mtime_ns)
        self.assertEqual(list((root / "archives").iterdir()), [])

    def test_corrupt_cached_archive_rejected_without_network_fallback(self):
        archive = self.regular_archive()
        package = self.package(archive)
        archive.write_bytes(b"z" * archive.stat().st_size)
        with mock.patch.object(setup.urllib.request, "urlopen", side_effect=AssertionError("network used")):
            with self.assertRaisesRegex(ValueError, "checksum"):
                setup.acquire(package, self.root(), self.folder, False)

    def test_oversize_cached_archive_rejected_before_hash(self):
        archive = self.regular_archive()
        package = self.package(archive)
        package["maximum_bytes"] -= 1
        with mock.patch.object(setup, "digest", side_effect=AssertionError("oversize archive hashed")):
            with self.assertRaises(ValueError):
                setup.acquire(package, self.root(), self.folder, True)

    def test_offline_cache_miss_never_downloads(self):
        archive = self.regular_archive()
        package = self.package(archive)
        with mock.patch.object(setup.urllib.request, "urlopen", side_effect=AssertionError("network used")):
            with self.assertRaisesRegex(ValueError, "not cached"):
                setup.acquire(package, self.root(), None, True)

    def test_download_requires_exact_hash_and_cleans_failed_partial(self):
        archive = self.regular_archive()
        package = self.package(archive)
        root = self.root()
        incoming = io.BytesIO(b"z" * archive.stat().st_size)
        with mock.patch.object(setup.urllib.request, "urlopen", return_value=incoming):
            with self.assertRaisesRegex(ValueError, "checksum"):
                setup.acquire(package, root, None, False)
        self.assertEqual(list((root / "archives").iterdir()), [])

    def test_verified_download_is_published_after_checksum(self):
        archive = self.regular_archive()
        package = self.package(archive)
        root = self.root()
        incoming = io.BytesIO(archive.read_bytes())
        with mock.patch.object(setup.urllib.request, "urlopen", return_value=incoming):
            with redirect_stdout(io.StringIO()):
                downloaded = setup.acquire(package, root, None, False)
        self.assertEqual(downloaded, root / "archives" / archive.name)
        self.assertEqual(downloaded.read_bytes(), archive.read_bytes())
        self.assertFalse(list((root / "archives").glob("*.partial")))

    def test_install_then_read_only_reuse_and_tamper_rejection(self):
        archive = self.regular_archive()
        root = self.root()
        args = SimpleNamespace(archive_cache=self.folder, offline=True)
        catalog = {"tool": self.package(archive)}
        destination = root / "sdk/tool"
        with redirect_stdout(io.StringIO()):
            setup.component(root, "tool", destination, ["tool"], catalog, args)
        receipt = root / "receipts/tool.json"
        before = receipt.read_bytes(), (destination / "bin/tool").stat().st_mtime_ns
        with mock.patch.object(setup, "acquire", side_effect=AssertionError("reuse reacquired archive")):
            with redirect_stdout(io.StringIO()):
                setup.component(root, "tool", destination, ["tool"], catalog, args)
        self.assertEqual((receipt.read_bytes(), (destination / "bin/tool").stat().st_mtime_ns), before)
        (destination / "bin/tool").write_bytes(b"tampered")
        with self.assertRaisesRegex(ValueError, "changed"):
            setup.component(root, "tool", destination, ["tool"], catalog, args)

    def test_failed_publish_can_resume_from_matching_receipt(self):
        archive = self.regular_archive()
        root = self.root()
        args = SimpleNamespace(archive_cache=self.folder, offline=True)
        catalog = {"tool": self.package(archive)}
        destination = root / "sdk/tool"
        with mock.patch.object(setup.os, "rename", side_effect=OSError("simulated interrupted publish")):
            with self.assertRaisesRegex(OSError, "simulated"):
                setup.component(root, "tool", destination, ["tool"], catalog, args)
        self.assertFalse(destination.exists())
        self.assertFalse(list(root.glob(".stage-*")))
        with redirect_stdout(io.StringIO()):
            setup.component(root, "tool", destination, ["tool"], catalog, args)
        self.assertEqual((destination / "bin/tool").read_bytes(), b"authored-tool")

    def test_existing_unreceipted_component_is_preserved(self):
        archive = self.regular_archive()
        root = self.root()
        destination = root / "sdk"
        destination.mkdir()
        (destination / "user-file").write_bytes(b"preserve")
        args = SimpleNamespace(archive_cache=self.folder, offline=True)
        with self.assertRaisesRegex(ValueError, "receipt"):
            setup.component(root, "tool", destination, ["tool"], {"tool": self.package(archive)}, args)
        self.assertEqual((destination / "user-file").read_bytes(), b"preserve")

    def test_component_destination_symlink_is_rejected(self):
        archive = self.regular_archive()
        root = self.root()
        unrelated = self.folder / "user-data"
        unrelated.mkdir()
        (unrelated / "keep").write_bytes(b"preserve")
        destination = root / "redirected"
        destination.symlink_to(unrelated, target_is_directory=True)
        args = SimpleNamespace(archive_cache=self.folder, offline=True)
        with self.assertRaisesRegex(ValueError, "symlink"):
            setup.component(root, "tool", destination, ["tool"], {"tool": self.package(archive)}, args)
        self.assertEqual((unrelated / "keep").read_bytes(), b"preserve")


class ManifestAndEnvironmentTests(FixtureCase):
    """CodexAstraUlt: Pins and shell exports retain their exact reviewed meanings."""

    def test_checked_in_manifest_validates(self):
        setup.validate_catalog(json.loads(setup.MANIFEST.read_text()))

    def test_invalid_package_pins_and_urls_rejected(self):
        original = json.loads(setup.MANIFEST.read_text())
        for key, value in (("sha256", "not-a-hash"), ("url", "http://dl.google.com/tool.zip"),
                           ("url", "https://example.invalid/tool.zip"), ("root", "../escape"),
                           ("maximum_bytes", -1), ("maximum_bytes", True), ("sha256", None),
                           ("root", None),
                           ("url", "https://dl.google.com/android/repository/../../unexpected.zip"),
                           ("url", "https://dl.google.com/android/repository/%2e%2e/unexpected.zip"),
                           ("url", "https://dl.google.com/android/repository/tool.zip?replacement=1")):
            catalog = copy.deepcopy(original)
            catalog["packages"]["ndk"][key] = value
            with self.subTest(key=key, value=value), self.assertRaises(ValueError):
                setup.validate_catalog(catalog)

    def test_missing_package_rejected(self):
        catalog = json.loads(setup.MANIFEST.read_text())
        del catalog["packages"]["rust_std_android"]
        with self.assertRaises(ValueError):
            setup.validate_catalog(catalog)

    def test_environment_preserves_home_and_uses_owned_cache(self):
        root = self.folder / "tools"
        with mock.patch.dict(os.environ, {"HOME": "/authored/home", "RUSTFLAGS": "bad", "RUSTUP_TOOLCHAIN": "bad"}):
            value = setup.environment(root, root / "sdk", root / "jdk")
            self.assertEqual(os.environ["RUSTFLAGS"], "bad")
        self.assertEqual(value["HOME"], "/authored/home")
        self.assertEqual(value["CARGO_HOME"], str(root / "cargo"))
        self.assertEqual(value["RUSTC"], str(root / "rust/bin/rustc"))
        self.assertNotIn("RUSTFLAGS", value)
        self.assertNotIn("RUSTUP_TOOLCHAIN", value)

    def test_shell_environment_quotes_special_characters(self):
        root = self.folder / "tools ' dollar$ semicolon;"
        root.mkdir()
        setup.write_environment(root, root / "sdk", root / "jdk")
        code = '. "$1"; printf "%s\\n" "$CARGO_HOME" "$RUSTC" "$JAVA_HOME"'
        result = subprocess.run(["sh", "-c", code, "fixture", str(root / "env.sh")],
                                check=True, text=True, capture_output=True)
        self.assertEqual(result.stdout.splitlines(), [str(root / "cargo"), str(root / "rust/bin/rustc"), str(root / "jdk")])

    def test_environment_output_cannot_redirect_to_user_file(self):
        root = self.root()
        user_file = self.folder / "profile"
        user_file.write_bytes(b"preserve profile")
        (root / "env.sh").symlink_to(user_file)
        with self.assertRaisesRegex(ValueError, "symlink"):
            setup.write_environment(root, root / "sdk", root / "jdk")
        self.assertEqual(user_file.read_bytes(), b"preserve profile")

    def test_environment_failed_publish_preserves_previous_content(self):
        root = self.root()
        setup.write_environment(root, root / "sdk", root / "jdk")
        previous = (root / "env.sh").read_bytes()
        with mock.patch.object(setup.os, "replace", side_effect=OSError("simulated interrupted publish")):
            with self.assertRaisesRegex(OSError, "simulated"):
                setup.write_environment(root, root / "other-sdk", root / "other-jdk")
        self.assertEqual((root / "env.sh").read_bytes(), previous)
        self.assertFalse(list(root.glob("env.sh.*.tmp")))

    def test_process_failure_retains_local_log(self):
        root = self.root()
        with self.assertRaisesRegex(ValueError, "fixture failed"):
            setup.run(root, "fixture", ["sh", "-c", "printf 'original diagnostic'; exit 2"], dict(os.environ))
        logs = list((root / "logs").glob("fixture-*.log"))
        self.assertEqual(len(logs), 1)
        self.assertEqual(logs[0].read_text(), "original diagnostic")

    def test_real_process_output_limit_stops_writer_before_log_overflows(self):
        root = self.root()
        processes = []
        original_popen = subprocess.Popen

        def track_process(*args, **kwargs):
            process = original_popen(*args, **kwargs)
            processes.append(process)
            return process

        # CodexAstraUlt: Reduce the fixture cap, then use a real pipe and child
        # so blocking output and process cleanup are exercised together.
        with mock.patch.object(setup, "MIB", 1024), mock.patch.object(setup.subprocess, "Popen", side_effect=track_process):
            with self.assertRaisesRegex(RuntimeError, "output exceeds bound"):
                setup.run(root, "overflow", [sys.executable, "-c",
                    "import sys,time; sys.stdout.buffer.write(b'x'*65536); sys.stdout.flush(); time.sleep(30)"],
                    dict(os.environ), timeout=5)
        self.assertEqual(len(processes), 1)
        self.assertIsNotNone(processes[0].poll())
        logs = list((root / "logs").glob("overflow-*.log"))
        self.assertEqual(len(logs), 1)
        self.assertLessEqual(logs[0].stat().st_size, 32 * 1024)

    def test_real_process_deadline_stops_silent_child(self):
        root = self.root()
        processes = []
        original_popen = subprocess.Popen

        def track_process(*args, **kwargs):
            process = original_popen(*args, **kwargs)
            processes.append(process)
            return process

        with mock.patch.object(setup.subprocess, "Popen", side_effect=track_process):
            with self.assertRaisesRegex(RuntimeError, "time bound"):
                setup.run(root, "timeout", [sys.executable, "-c", "import time; time.sleep(30)"],
                          dict(os.environ), timeout=0.15)
        self.assertEqual(len(processes), 1)
        self.assertIsNotNone(processes[0].poll())
        self.assertEqual(len(list((root / "logs").glob("timeout-*.log"))), 1)


if __name__ == "__main__":
    unittest.main()
