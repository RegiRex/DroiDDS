#!/usr/bin/env python3
"""CodexAstraUlt: Bound a Linux diagnostic worker using immutable input FDs.

The supervisor owns process-group cleanup and resource ceilings, not a native
plugin sandbox. Its caller owns input/library admission, paths and final reports.
Keeping this separate preserves the existing compilation contract identities.
"""

import fcntl
import importlib.util
import math
import os
from pathlib import Path
import platform
import resource
import selectors
import signal
import stat
import subprocess
import time


# CodexAstraUlt: Reuse the established loader/compiler environment policy while
# leaving that compilation-identity-bound source unchanged.
_SPEC = importlib.util.spec_from_file_location(
    "native_runtime_compile_environment", Path(__file__).with_name("private_compile_process.py"))
_ENVIRONMENT = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_ENVIRONMENT)
LOG_BYTES = 64 * 1024
FILE_BYTES = 64 * 1024**2
MAX_INPUT_BYTES = 512 * 1024**2
MAX_PASSED_FDS = 8
MAX_WALL_SECONDS = 310
MAX_CPU_SECONDS = 311
MAX_MEMORY_MIB = 16384
# CodexAstraUlt: Some Linux Python builds omit these names. The stable Linux
# fcntl UAPI numbers permit the same kernel checks without another dependency.
F_ADD_SEALS = getattr(fcntl, "F_ADD_SEALS", 1033)
F_GET_SEALS = getattr(fcntl, "F_GET_SEALS", 1034)
F_SEAL_SEAL = getattr(fcntl, "F_SEAL_SEAL", 1)
F_SEAL_SHRINK = getattr(fcntl, "F_SEAL_SHRINK", 2)
F_SEAL_GROW = getattr(fcntl, "F_SEAL_GROW", 4)
F_SEAL_WRITE = getattr(fcntl, "F_SEAL_WRITE", 8)
REQUIRED_SEALS = F_SEAL_WRITE | F_SEAL_GROW | F_SEAL_SHRINK | F_SEAL_SEAL


def _integer(value, low, high, name):
    """CodexAstraUlt: Booleans are not valid descriptors or resource bounds."""
    if type(value) is not int or not low <= value <= high:
        raise ValueError("invalid_native_worker_" + name)


def validate_descriptors(pass_fds):
    """CodexAstraUlt: Only immutable, bounded memfds may cross the exec boundary.

    The caller retains ownership and must keep descriptors open until return.
    Seals bind their bytes; this check does not interpret or authenticate them.
    """
    if not isinstance(pass_fds, (tuple, list)) or len(pass_fds) > MAX_PASSED_FDS:
        raise ValueError("invalid_native_worker_pass_fds")
    result = []
    for descriptor in pass_fds:
        _integer(descriptor, 3, 2**31 - 1, "descriptor")
        if descriptor in result:
            raise ValueError("duplicate_native_worker_descriptor")
        try:
            info = os.fstat(descriptor)
            label = os.readlink(f"/proc/self/fd/{descriptor}")
            seals = fcntl.fcntl(descriptor, F_GET_SEALS)
        except OSError as error:
            raise ValueError("native_worker_input_is_not_sealed_memfd") from error
        if (not stat.S_ISREG(info.st_mode) or info.st_nlink != 0
                or not 0 < info.st_size <= MAX_INPUT_BYTES
                or not label.startswith("/memfd:") or not label.endswith(" (deleted)")
                or seals & REQUIRED_SEALS != REQUIRED_SEALS):
            raise ValueError("native_worker_input_is_not_sealed_memfd")
        result.append(descriptor)
    return tuple(result)


def _stop_group(process):
    """CodexAstraUlt: Kill descendants even after their direct parent exits.

    Only the direct child can be reaped here. Orphaned grandchildren are left to
    their system adopter; changing session/process groups is outside this guard.
    """
    for signum, pause in ((signal.SIGTERM, 0.1), (signal.SIGKILL, 0)):
        try:
            os.killpg(process.pid, signum)
        except ProcessLookupError:
            break
        if pause:
            time.sleep(pause)
    try:
        process.wait(timeout=3)
    except subprocess.TimeoutExpired as error:
        raise RuntimeError("native_worker_could_not_be_reaped") from error


def run_worker(command, cwd, timeout, cpu_seconds=120, memory_mib=4096, pass_fds=()):
    """CodexAstraUlt: Execute one worker with hard per-process resource limits.

    Returned signals remain signals: SIGSEGV is not proof of a protected write,
    and SIGKILL is not proof of an out-of-memory failure. The caller distinguishes
    process completion from a valid worker result. No output files are written
    here, and file ceilings are per file rather than an aggregate disk quota.
    """
    if platform.system() != "Linux":
        raise ValueError("native_worker_supervision_requires_linux")
    if (not isinstance(command, list) or not command or len(command) > 8192
            or any(not isinstance(word, str) or not word or "\0" in word for word in command)
            or sum(len(word) for word in command) > 1024**2):
        raise ValueError("invalid_native_worker_command")
    if (type(timeout) not in (int, float) or not math.isfinite(timeout)
            or not 0 < timeout <= MAX_WALL_SECONDS):
        raise ValueError("invalid_native_worker_timeout")
    _integer(cpu_seconds, 1, MAX_CPU_SECONDS, "cpu_seconds")
    _integer(memory_mib, 256, MAX_MEMORY_MIB, "memory_mib")
    directory = Path(cwd).absolute()
    if not directory.is_dir():
        raise ValueError("native_worker_cwd_must_exist")
    descriptors = validate_descriptors(pass_fds)
    environment = _ENVIRONMENT.clean_environment()
    # CodexAstraUlt: Diagnostics may launch original Python fixtures in tests;
    # do not let ambient interpreter hooks or libc tuning change those runs.
    for name in ("PYTHONPATH", "PYTHONHOME", "PYTHONSTARTUP", "PYTHONINSPECT",
                 "GLIBC_TUNABLES", "GCONV_PATH", "LOCPATH"):
        environment.pop(name, None)

    # CodexAstraUlt: Set ceilings before exec. CPU includes each process's
    # threads, while a descendant inherits its own ceiling, not a shared sum.
    def ceilings():
        resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
        resource.setrlimit(resource.RLIMIT_AS, (memory_mib * 1024**2,) * 2)
        resource.setrlimit(resource.RLIMIT_FSIZE, (FILE_BYTES,) * 2)
        resource.setrlimit(resource.RLIMIT_CPU, (cpu_seconds,) * 2)
        try:
            os.nice(10)
        except OSError:
            pass

    started = time.monotonic()
    process = subprocess.Popen(command, cwd=directory, env=environment,
                               stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                               stderr=subprocess.STDOUT, close_fds=True,
                               pass_fds=descriptors, start_new_session=True,
                               preexec_fn=ceilings)
    tail, seen, pipe_open = bytearray(), 0, True
    outcome, selector = "completed", None

    # CodexAstraUlt: A bounded drain yields to timeout checks even if the worker
    # continuously writes. Cleanup also covers failures during pipe setup.
    def drain():
        nonlocal seen, pipe_open
        for _ in range(64):
            if not pipe_open:
                break
            try:
                block = os.read(process.stdout.fileno(), 8192)
            except BlockingIOError:
                break
            if not block:
                pipe_open = False
                selector.unregister(process.stdout)
                break
            seen += len(block)
            tail.extend(block)
            if len(tail) > LOG_BYTES:
                del tail[:-LOG_BYTES]

    try:
        os.set_blocking(process.stdout.fileno(), False)
        selector = selectors.DefaultSelector()
        selector.register(process.stdout, selectors.EVENT_READ)
        while True:
            drain()
            if process.poll() is not None:
                break
            remaining = timeout - (time.monotonic() - started)
            if remaining <= 0:
                outcome = "timeout"
                break
            selector.select(min(0.05, remaining))
    except KeyboardInterrupt:
        outcome = "interrupted"
    finally:
        try:
            _stop_group(process)
            # CodexAstraUlt: Retain in-flight tail bytes after group termination
            # without waiting forever for a pipe holder outside that group.
            if selector is not None and process.stdout in selector.get_map():
                deadline = time.monotonic() + 1
                while pipe_open and time.monotonic() < deadline:
                    drain()
                    if pipe_open:
                        selector.select(0.01)
        finally:
            if selector is not None:
                selector.close()
            process.stdout.close()
    return {"outcome": outcome, "exit_code": process.returncode,
            "elapsed_seconds": time.monotonic() - started,
            "log_tail": tail.decode("utf-8", errors="replace"), "log_bytes_seen": seen,
            "limits": {"wall_seconds": timeout, "cpu_seconds": cpu_seconds,
                       "memory_mib": memory_mib, "file_bytes": FILE_BYTES,
                       "cpu_scope": "per_process_all_threads", "passed_sealed_fds": len(descriptors),
                       "log_retained_bytes": len(tail)}}
