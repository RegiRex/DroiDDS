#!/usr/bin/env python3
"""CodexAstraUlt: Bounded Linux compiler processes and observed tool identities.

These helpers neither load a generated library nor execute a guest. Resource
limits apply to individual processes; the wall deadline covers their process
group. Installed compiler tools are trusted, not sandboxed native plugins.
"""

import hashlib
import math
import os
from pathlib import Path
import platform
import resource
import selectors
import shutil
import signal
import stat
import subprocess
import time


# CodexAstraUlt: Bound retained diagnostics independently of total pipe output;
# metadata probes reject truncated results instead of identifying a partial tool.
LOG_BYTES = 64 * 1024
MAX_TOOL_BYTES = 512 * 1024**2
MAX_COMMAND_SECONDS = 3600
MAX_MEMORY_MIB = 16384
MAX_FILE_BYTES = 4 * 1024**3
_ENVIRONMENT_EXCLUSIONS = {
    "CC", "CXX", "CPP", "AR", "AS", "LD", "RANLIB", "CFLAGS", "CXXFLAGS",
    "CPPFLAGS", "LDFLAGS", "CPATH", "C_INCLUDE_PATH", "CPLUS_INCLUDE_PATH",
    "OBJC_INCLUDE_PATH", "LIBRARY_PATH", "COMPILER_PATH", "DEPENDENCIES_OUTPUT",
    "SUNPRO_DEPENDENCIES", "INCLUDE", "LIB", "LIBPATH", "SDKROOT",
    "MACOSX_DEPLOYMENT_TARGET", "SOURCE_DATE_EPOCH",
}


def clean_environment(base=None):
    """CodexAstraUlt: Exclude ambient compiler/loader overrides, retaining proxies."""
    source = os.environ if base is None else base
    if not isinstance(source, (dict, os._Environ)) or any(
            not isinstance(key, str) or not isinstance(value, str) or "\0" in key + value
            for key, value in source.items()):
        raise ValueError("compiler_environment_must_contain_strings")
    result = {key: value for key, value in source.items()
              if key not in _ENVIRONMENT_EXCLUSIONS
              and not key.startswith(("GCC_", "CLANG_", "CCC_", "LD_", "DYLD_"))}
    result.update(LC_ALL="C", LANG="C", SOURCE_DATE_EPOCH="0", PYTHONDONTWRITEBYTECODE="1")
    return result


def _integer(value, low, high, name):
    """CodexAstraUlt: Reject booleans and unbounded resource requests before spawn."""
    if type(value) is not int or not low <= value <= high:
        raise ValueError("invalid_compiler_" + name)


def _stop_group(process):
    """CodexAstraUlt: Terminate descendants even after their leader has exited.

    Reap the direct child; orphaned grandchildren are reaped by the operating
    system. This is process-group supervision, not a hostile-child sandbox.
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
        raise RuntimeError("compiler_process_could_not_be_reaped") from error


def run_command(command, cwd, timeout, cpu_seconds, memory_mib, file_bytes, env=None):
    """CodexAstraUlt: Run one bounded command, retaining only a 64 KiB log tail.

    No files are written by this helper. The caller owns command output paths,
    report publication and SIGTERM-to-KeyboardInterrupt handling. A compiler's
    forked helpers inherit process limits; their CPU times are not summed.
    """
    if platform.system() != "Linux":
        raise ValueError("compiler_supervision_requires_linux")
    if (not isinstance(command, list) or not command or len(command) > 8192
            or any(not isinstance(word, str) or not word or "\0" in word for word in command)
            or sum(len(word) for word in command) > 1024**2):
        raise ValueError("invalid_compiler_command")
    if type(timeout) not in (int, float) or not math.isfinite(timeout) or not 0 < timeout <= MAX_COMMAND_SECONDS:
        raise ValueError("invalid_compiler_timeout")
    _integer(cpu_seconds, 1, MAX_COMMAND_SECONDS, "cpu_seconds")
    _integer(memory_mib, 256, MAX_MEMORY_MIB, "memory_mib")
    _integer(file_bytes, 1, MAX_FILE_BYTES, "file_bytes")
    directory = Path(cwd).absolute()
    if not directory.is_dir():
        raise ValueError("compiler_cwd_must_exist")
    environment = clean_environment(env)

    # CodexAstraUlt: Establish hard limits before exec, including compiler
    # temporary files. Niceness is optional and cannot turn a valid build into
    # failure when a host forbids changing scheduling priority.
    def ceilings():
        resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
        resource.setrlimit(resource.RLIMIT_AS, (memory_mib * 1024**2,) * 2)
        resource.setrlimit(resource.RLIMIT_FSIZE, (file_bytes,) * 2)
        resource.setrlimit(resource.RLIMIT_CPU, (cpu_seconds,) * 2)
        try:
            os.nice(10)
        except OSError:
            pass

    started = time.monotonic()
    process = subprocess.Popen(command, cwd=directory, env=environment,
                               stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                               stderr=subprocess.STDOUT, start_new_session=True,
                               preexec_fn=ceilings)
    tail, seen = bytearray(), 0
    outcome = "completed"
    pipe_open = True
    os.set_blocking(process.stdout.fileno(), False)
    selector = selectors.DefaultSelector()
    selector.register(process.stdout, selectors.EVENT_READ)

    # CodexAstraUlt: Nonblocking reads avoid a logging thread that could survive
    # interruption. Drain continuously but never retain an unbounded compiler log.
    def drain():
        nonlocal seen, pipe_open
        # CodexAstraUlt: A compiler that writes continuously must still yield
        # to deadline/exit checks instead of keeping this drain loop alive.
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
            # CodexAstraUlt: Drain bytes already in flight after group cleanup,
            # with a separate short bound if an unrelated pipe holder survives.
            deadline = time.monotonic() + 1
            while pipe_open and time.monotonic() < deadline:
                drain()
                if pipe_open:
                    selector.select(0.01)
        finally:
            selector.close()
            process.stdout.close()
    return {"outcome": outcome, "exit_code": process.returncode,
            "elapsed_seconds": time.monotonic() - started,
            "log_tail": tail.decode("utf-8", errors="replace"),
            "log_bytes_seen": seen,
            "limits": {"wall_seconds": timeout, "cpu_seconds": cpu_seconds,
                       "memory_mib": memory_mib, "file_bytes": file_bytes,
                       "cpu_scope": "per_process_all_threads", "log_retained_bytes": len(tail)}}


def _tool(path, environment):
    """CodexAstraUlt: Resolve ordinary installed tool symlinks and hash real bytes."""
    selected = os.fspath(path)
    located = shutil.which(selected, path=environment.get("PATH", os.defpath))
    if located is None:
        raise ValueError("compiler_tool_not_found")
    resolved = Path(located).resolve(strict=True)
    with resolved.open("rb") as stream:
        before = os.fstat(stream.fileno())
        if not stat.S_ISREG(before.st_mode) or not 0 < before.st_size <= MAX_TOOL_BYTES:
            raise ValueError("compiler_tool_not_regular_or_bounded")
        digest, count = hashlib.sha256(), 0
        while block := stream.read(1024**2):
            count += len(block)
            if count > MAX_TOOL_BYTES:
                raise ValueError("compiler_tool_grew_beyond_bound")
            digest.update(block)
        after = os.fstat(stream.fileno())
    def fingerprint(info):
        return (info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns, info.st_ctime_ns)
    if count != before.st_size or fingerprint(before) != fingerprint(after) or fingerprint(after) != fingerprint(resolved.stat()):
        raise ValueError("compiler_tool_changed_while_hashing")
    return {"path": str(resolved), "bytes": count, "sha256": digest.hexdigest()}


def inspect_compiler(path=None):
    """CodexAstraUlt: Identify installed native Linux GCC/Clang and direct helpers.

    This records observed binaries, not full toolchain provenance: system headers,
    runtime libraries and source-to-binary attestation remain separate concerns.
    No generated library is loaded and no tool installation is attempted.
    """
    host = platform.machine()
    if platform.system() != "Linux" or host not in ("x86_64", "aarch64"):
        raise ValueError("unsupported_native_compiler_host")
    environment = clean_environment()
    driver = _tool("cc" if path is None else path, environment)
    # CodexAstraUlt: Restrict this first pipeline to direct installed native
    # drivers; wrappers can hide independent caches, plugins and child identities.
    with Path(driver["path"]).open("rb") as stream:
        if stream.read(4) != b"\x7fELF":
            raise ValueError("compiler_driver_wrapper_unsupported")

    probe_flags = []

    def query(*arguments):
        result = run_command([driver["path"], *probe_flags, *arguments], Path.cwd(), 10, 10, 512, 1024**2, environment)
        if result["outcome"] != "completed" or result["exit_code"] != 0 or result["log_bytes_seen"] > LOG_BYTES:
            raise ValueError("compiler_metadata_probe_failed")
        value = result["log_tail"].strip()
        if not value or "\0" in value:
            raise ValueError("compiler_metadata_probe_empty")
        return value

    version = query("--version")
    if "clang version" in version:
        family = "clang"
        # CodexAstraUlt: Match the compilation/link recipe after identifying
        # Clang, so ambient clang.cfg cannot select a different target/helper.
        probe_flags = ["--no-default-config"]
    elif "Free Software Foundation" in version:
        family = "gcc"
    else:
        raise ValueError("unsupported_native_compiler_family")
    target = query("-dumpmachine")
    if (len(target) > 128 or not target.startswith(host + "-") or "linux" not in target
            or any(not (character.isascii() and (character.isalnum() or character in "_.+-")) for character in target)):
        raise ValueError("compiler_target_is_not_native_linux")
    tools = {"driver": driver}
    for name in (("cc1", "as", "collect2", "ld") if family == "gcc" else ("ld",)):
        selected = query("-print-prog-name=" + name)
        if "\n" in selected or "\r" in selected:
            raise ValueError("compiler_helper_path_invalid")
        tools[name] = _tool(selected, environment)
    # CodexAstraUlt: Detect helper/driver replacement during discovery; callers
    # bind this identity to their build and recheck it before accepting results.
    if any(_tool(item["path"], environment) != item for item in tools.values()):
        raise ValueError("compiler_tool_changed_during_inspection")
    return {"invocation": driver["path"],
            "identity": {"schema_version": 1, "family": family, "version": version,
                         "target": target, "host_arch": host, "tools": tools,
                         "binary_source_attested": False}}
