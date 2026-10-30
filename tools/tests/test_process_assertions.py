"""CodexAstraUlt: Reaping races cannot weaken the descendant-cleanup oracle."""

from pathlib import Path
import select
import subprocess
import sys
import unittest
from unittest import mock

from process_assertions import assert_process_stopped


class ProcessAssertionTests(unittest.TestCase):
    """CodexAstraUlt: Check disappearance deterministically and reject a real live child."""

    def test_reaped_during_read_is_accepted_without_existence_check(self):
        # CodexAstraUlt: A prior observation could have reported present; the
        # authoritative read now sees the kernel's completed reap instead.
        with mock.patch.object(Path, "exists", return_value=True) as exists, \
                mock.patch.object(Path, "read_text", side_effect=FileNotFoundError) as read:
            assert_process_stopped(self, 123)
        exists.assert_not_called()
        read.assert_called_once_with()

    def test_zombie_is_accepted_with_spaces_and_parentheses_in_process_name(self):
        with mock.patch.object(Path, "read_text", return_value="123 (original (child)) Z 1 2 3"):
            assert_process_stopped(self, 123)

    def test_reaped_after_open_during_file_read_is_accepted(self):
        # CodexAstraUlt: Linux can open a proc entry before its task disappears,
        # then return ESRCH from the read itself, as observed on the CI runner.
        with mock.patch.object(Path, "open") as opened:
            stream = opened.return_value.__enter__.return_value
            stream.read.side_effect = ProcessLookupError(3, "No such process")
            assert_process_stopped(self, 123)
        opened.assert_called_once()
        stream.read.assert_called_once_with()

    def test_other_read_errors_are_not_mistaken_for_successful_cleanup(self):
        for error in (PermissionError, OSError):
            with self.subTest(error=error), mock.patch.object(Path, "read_text", side_effect=error):
                with self.assertRaises(error):
                    assert_process_stopped(self, 123)

    def test_actual_running_child_is_rejected(self):
        # CodexAstraUlt: Explicit readiness establishes that this original child
        # is live. Its cleanup is owned by this test even if the oracle fails.
        process = subprocess.Popen([sys.executable, "-c",
            "import time; print('ready', flush=True); time.sleep(30)"],
            stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        try:
            readable, _, _ = select.select([process.stdout], [], [], 5)
            self.assertTrue(readable, "original child did not signal readiness")
            self.assertEqual(process.stdout.readline(), b"ready\n")
            self.assertIsNone(process.poll())
            with self.assertRaisesRegex(AssertionError, "still live"):
                assert_process_stopped(self, process.pid)
        finally:
            process.kill()
            process.communicate(timeout=3)


if __name__ == "__main__":
    unittest.main()
