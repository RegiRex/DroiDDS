#!/usr/bin/env python3
"""CodexAstraUlt: Check the real generic-title C ABI with an original guest."""

import argparse
import ctypes as c
import hashlib
import json
from pathlib import Path
import threading


class Metrics(c.Structure):
    # CodexAstraUlt: Independently declare the caller's ABI, including the flags
    # that distinguish a cooperative yield from a new frame or guest exit.
    _fields_ = [(name, c.c_uint64) for name in (
        "frames", "cycles", "pcm_frames", "exited", "ready_mask")]


def check(condition, message):
    if not condition:
        raise ValueError(message)


def digest(path):
    # CodexAstraUlt: Preserve the caller's original input without a large copy
    # and report only its identity, never game contents or private paths.
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def run(library, manifest, input_path, native_directory, scratch, native=False):
    check(not scratch.exists() and scratch.parent.is_dir(), "fresh scratch directory required")
    check(c.sizeof(Metrics) == 40 and c.alignment(Metrics) == 8, "public metrics ABI differs")
    source_hash, manifest_hash = digest(input_path), digest(manifest)
    raw = manifest.read_bytes()
    check(0 < len(raw) <= 1024 * 1024, "manifest exceeds its bound")
    api = c.CDLL(str(library.resolve()))
    api.droidds_title_open.argtypes = [c.c_void_p, c.c_size_t, c.c_char_p,
        c.c_char_p, c.c_char_p, c.c_uint32, c.c_uint32, c.POINTER(c.c_uint64)]
    api.droidds_title_open.restype = c.c_void_p
    api.droidds_title_report.argtypes, api.droidds_title_report.restype = [c.c_uint64], c.c_void_p
    api.droidds_title_free.argtypes, api.droidds_title_free.restype = [c.c_void_p], None
    for name in ("pause", "resume", "close"):
        function = getattr(api, "droidds_title_" + name)
        function.argtypes, function.restype = [c.c_uint64], c.c_int32
    api.droidds_title_slice.argtypes = [c.c_uint64, c.c_uint32,
        c.c_float, c.c_float, c.c_float, c.c_float, c.c_int32, c.c_int32, c.c_uint32,
        c.POINTER(c.c_uint8), c.c_size_t, c.POINTER(c.c_uint8), c.c_size_t,
        c.POINTER(c.c_int16), c.c_size_t, c.POINTER(Metrics)]
    api.droidds_title_slice.restype = c.c_int32
    scratch.mkdir()
    runtime = scratch / "runtime"
    runtime.mkdir()
    sentinel = runtime / "original-save-sentinel"
    sentinel.write_bytes(b"CodexAstraUlt original FFI preservation fixture\n")
    saved = digest(sentinel)
    paths = [str(path.resolve()).encode() for path in (input_path, native_directory, runtime)]
    controls = []

    def owned(pointer):
        check(bool(pointer), "FFI returned a null report allocation")
        try:
            encoded = c.string_at(pointer)
            check(0 < len(encoded) <= 256 * 1024, "FFI report exceeds its bound")
            return json.loads(encoded)
        finally:
            api.droidds_title_free(pointer)

    def report(token):
        return owned(api.droidds_title_report(token))

    def attempt_open():
        opened = c.c_uint64(42)
        value = owned(api.droidds_title_open(raw, len(raw), *paths, int(native), 0, c.byref(opened)))
        return opened.value, value

    def open_session():
        token, value = attempt_open()
        check(value.get("status") == "opened", "title open failed: " + str(value))
        check(type(value.get("token")) is int and 0 < token < 2**63
              and value["token"] == token, "open token ownership differs")
        check(value.get("sample_rate") == 32728.498046875, "guest sample rate differs")
        return token

    def state(token):
        value = report(token)
        return {key: value.get(key) for key in ("cycles", "frames", "dispatches",
            "interpreted_instructions", "compiled_dispatch_instructions", "pcm_frames")}

    class Buffers:
        # CodexAstraUlt: A separate caller-owned buffer set per worker prevents
        # the negative thread test itself from creating a concurrent write race.
        def __init__(self):
            self.top = (c.c_uint8 * (400 * 240 * 4))()
            self.bottom = (c.c_uint8 * (320 * 240 * 4))()
            self.pcm = (c.c_int16 * 8192)()
            self.metrics = Metrics()

        def slice(self, token, top_bytes=None, bottom=None, axis=0.0):
            return api.droidds_title_slice(token, 0, axis, 0.0, 0.0, 0.0, 0, 0, 0,
                self.top, len(self.top) if top_bytes is None else top_bytes,
                self.bottom if bottom is None else bottom, len(self.bottom),
                self.pcm, len(self.pcm), c.byref(self.metrics))

        def snapshot(self):
            return bytes(self.top), bytes(self.bottom), bytes(self.pcm), bytes(self.metrics)

    buffers = Buffers()
    token = open_session()
    try:
        # CodexAstraUlt: At least one actual completed frame is necessary here;
        # accepting empty yields would leave the frame-copy C layout untested.
        for _ in range(256):
            check(buffers.slice(token) == 0, "title slice failed: " + str(report(token)))
            measured = buffers.metrics
            check(measured.exited in (0, 1) and measured.pcm_frames <= 4096
                  and measured.ready_mask in (0, 1, 2, 3), "invalid slice metrics")
            if measured.ready_mask != 0 or measured.exited:
                break
        check(buffers.metrics.ready_mask == 3 and buffers.metrics.frames > 0
              and buffers.metrics.cycles > 0 and buffers.metrics.exited == 0,
              "original interactive guest did not deliver a complete frame within 256 slices")
        progress = report(token)
        check(progress.get("native") is native and progress.get("renderer") == "software",
              "runtime route differs from the requested host route")
        check(progress.get("native_instructions", 0) > 0 if native else
              progress.get("interpreted_instructions", 0) > 0, "selected route did no execution")
        controls.append("actual_native_frame" if native else "actual_interpreter_frame")

        before = state(token)
        duplicate, value = attempt_open()
        check(duplicate == 0 and value.get("status") == "failed", "duplicate open acquired ownership")
        check(owned(api.droidds_title_open(raw, len(raw), *paths, int(native), 0, None))
              .get("status") == "failed", "missing ownership output was accepted")
        check(api.droidds_title_close(token + 1) == -1
              and api.droidds_title_pause(token + 1) == -1, "unknown token was accepted")
        check(state(token) == before, "unknown token or competing open changed guest state")
        controls.append("failed_open_and_wrong_token_preserve_owner")

        outcome = []
        def wrong_worker():
            try:
                check(report(token).get("status") == "failed", "wrong worker read session")
                check(api.droidds_title_pause(token) == -1 and api.droidds_title_close(token) == -1,
                      "wrong worker changed ownership")
                check(Buffers().slice(token) == -1, "wrong worker executed guest")
                other, value = attempt_open()
                check(other == 0 and value.get("status") == "failed", "second worker opened a session")
                outcome.append("passed")
            except Exception as error:
                outcome.append(str(error))
        worker = threading.Thread(target=wrong_worker, daemon=True)
        worker.start()
        worker.join(timeout=5)
        check(not worker.is_alive() and outcome == ["passed"], "wrong worker isolation failed: " + str(outcome))
        check(state(token) == before, "wrong worker changed owner state")
        controls.append("wrong_worker_and_competing_native_admission_rejected")

        pixels = buffers.snapshot()
        for result in (buffers.slice(token, top_bytes=len(buffers.top) - 1),
                       buffers.slice(token, bottom=buffers.top),
                       buffers.slice(token, axis=float("nan"))):
            check(result == -1, "invalid capacity, alias or axis was accepted")
        check(buffers.snapshot() == pixels and state(token) == before
              and report(token)["status"] == "running", "invalid input advanced or poisoned the session")
        controls.append("invalid_capacity_alias_and_axis_preserve_state_and_output")

        check(api.droidds_title_pause(token) == 0, "pause failed")
        check(buffers.slice(token) == -2 and buffers.snapshot() == pixels
              and state(token) == before and report(token)["status"] == "paused",
              "pause rejection advanced, wrote output or poisoned the session")
        check(api.droidds_title_resume(token) == 0 and buffers.slice(token) == 0,
              "retained session did not resume")
        check(state(token)["cycles"] > before["cycles"], "resumed session made no progress")
        controls.append("pause_cancellation_preserves_resumability")
        measured_progress = report(token)
    finally:
        check(api.droidds_title_close(token) == 0, "owned session failed to close")

    check(report(token).get("status") == "failed", "closed token remains live")
    replacement = open_session()
    try:
        check(replacement > token, "replacement generation did not advance")
        before = state(replacement)
        check(api.droidds_title_close(token) == -1 and buffers.slice(token) == -1
              and state(replacement) == before, "stale token changed replacement")
        check(buffers.slice(replacement) == 0, "replacement cannot execute")
    finally:
        check(api.droidds_title_close(replacement) == 0, "replacement close failed")
    api.droidds_title_free(None)
    check(digest(input_path) == source_hash and digest(manifest) == manifest_hash
          and digest(sentinel) == saved, "input, manifest or existing save changed")
    controls.append("teardown_generation_and_original_save_preservation")
    return {"schema_version": 1, "kind": "droidds-title-ffi-proof", "status": "passed",
            "native": native, "controls": controls, "input_sha256": source_hash,
            "frames": measured_progress["frames"], "cycles": measured_progress["cycles"],
            "native_instructions": measured_progress["native_instructions"],
            "interpreted_instructions": measured_progress["interpreted_instructions"]}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--library", required=True, type=Path)
    parser.add_argument("--manifest", required=True, type=Path)
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--native-dir", required=True, type=Path)
    parser.add_argument("--scratch-dir", required=True, type=Path)
    parser.add_argument("--native", action="store_true")
    arguments = parser.parse_args()
    print(json.dumps(run(arguments.library, arguments.manifest, arguments.input,
                         arguments.native_dir, arguments.scratch_dir, arguments.native), indent=2))
