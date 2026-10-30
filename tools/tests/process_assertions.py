"""CodexAstraUlt: Observe descendant cleanup without racing the kernel reaper."""

from pathlib import Path


def assert_process_stopped(testcase, pid):
    """CodexAstraUlt: A vanished process or zombie is dead; every live state fails.

    Read once instead of checking existence first: an orphan's adopter can reap
    it between any two observations. Only disappearance is accepted; unrelated
    filesystem errors must still fail the test.
    """
    try:
        observed = Path(f"/proc/{pid}/stat").read_text()
    except FileNotFoundError:
        return
    state = observed.rsplit(") ", 1)[1].split()[0]
    testcase.assertEqual(state, "Z", "worker descendant is still live")
