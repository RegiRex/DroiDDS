#!/usr/bin/env python3
"""CodexAstraUlt: Exercise live exported native-session ownership on the host."""

import argparse
import ctypes as c
import json
from pathlib import Path
import threading


class Metrics(c.Structure):
    # CodexAstraUlt: This is the public C ABI, independently declared by its
    # caller; actual frame writes must agree with these four uint64 fields.
    _fields_ = [(name, c.c_uint64) for name in ("frame_index", "guest_serial", "pcm_frames", "exited")]


def check(condition, message):
    if not condition:
        raise ValueError(message)


def run(library: Path, native: Path, scratch: Path) -> dict:
    # CodexAstraUlt: Only the freshly built project CDylib and original guest
    # directory are accepted by the parent gate; there is no plugin discovery.
    api = c.CDLL(str(library.resolve()))
    for name in ("droidds_homebrew_probe", "droidds_runtime_run"):
        function = getattr(api, name)
        function.argtypes, function.restype = [c.c_char_p, c.c_char_p], c.c_void_p
    api.droidds_homebrew_open.argtypes = [c.c_char_p, c.c_char_p, c.POINTER(c.c_uint64)]
    api.droidds_homebrew_open.restype = c.c_void_p
    api.droidds_probe_run.argtypes, api.droidds_probe_run.restype = [c.c_char_p], c.c_void_p
    api.droidds_probe_free.argtypes, api.droidds_probe_free.restype = [c.c_void_p], None
    api.droidds_homebrew_report.argtypes, api.droidds_homebrew_report.restype = [c.c_uint64], c.c_void_p
    api.droidds_homebrew_close.argtypes, api.droidds_homebrew_close.restype = [c.c_uint64], None
    api.droidds_homebrew_pause.argtypes, api.droidds_homebrew_pause.restype = [c.c_uint64, c.c_uint32], c.c_int32
    api.droidds_homebrew_frame.argtypes = [c.c_uint64, c.c_uint32, c.c_int32, c.c_int32, c.c_uint32,
        c.POINTER(c.c_uint8), c.c_size_t, c.POINTER(c.c_uint8), c.c_size_t,
        c.POINTER(c.c_int16), c.c_size_t, c.POINTER(Metrics)]
    api.droidds_homebrew_frame.restype = c.c_int32
    native_bytes, scratch_bytes = str(native.resolve()).encode(), str(scratch.resolve()).encode()
    top, bottom, pcm = (c.c_uint8 * (400 * 240 * 4))(), (c.c_uint8 * (320 * 240 * 4))(), (c.c_int16 * 8192)()
    metrics = Metrics()
    controls = []

    def owned(pointer):
        check(bool(pointer), "FFI returned a null report allocation")
        try:
            data = c.string_at(pointer)
            check(0 < len(data) <= 256 * 1024, "FFI report exceeds its bound")
            return json.loads(data)
        finally:
            api.droidds_probe_free(pointer)

    def report(token):
        return owned(api.droidds_homebrew_report(token))

    def open_session():
        opened = c.c_uint64(0)
        result = owned(api.droidds_homebrew_open(native_bytes, scratch_bytes, c.byref(opened)))
        check(result.get("status") == "opened", "Actual native session did not open: " + str(result))
        check(type(result.get("token")) is int and 0 < result["token"] < 2**63, "Invalid session token")
        check(opened.value == result["token"], "Open ownership token differs from the delivered report")
        check(result.get("sample_rate") == 32728.498046875, "Guest sample rate differs")
        return result["token"]

    def frame(token, top_length=None):
        return api.droidds_homebrew_frame(token, 0, 0, 0, 0, top,
            len(top) if top_length is None else top_length, bottom, len(bottom), pcm, len(pcm), c.byref(metrics))

    def state(token):
        value = report(token)
        return {key: value.get(key) for key in ("frames", "steps", "guest", "cycles")}

    token = open_session()
    try:
        check(c.sizeof(Metrics) == 32 and c.alignment(Metrics) == 8, "Public metrics ABI differs")
        check(frame(token) == 0 and metrics.frame_index > 0 and metrics.guest_serial > 0,
              "Actual native frame did not return valid metrics")
        check(0 < metrics.pcm_frames <= 4096 and metrics.exited == 0, "PCM/frame state differs")
        controls.append("actual_native_frame_and_metrics")
        before = state(token)
        opened = c.c_uint64(123456)
        duplicate = owned(api.droidds_homebrew_open(native_bytes, scratch_bytes, c.byref(opened)))
        check(duplicate.get("status") == "failed", "Duplicate worker session was accepted")
        check(opened.value == 0, "Failed open returned ownership of an unrelated session")
        check(owned(api.droidds_homebrew_open(native_bytes, scratch_bytes, None)).get("status") == "failed",
              "Open without cleanup ownership output was accepted")
        for pointer in (api.droidds_probe_run(native_bytes), api.droidds_runtime_run(native_bytes, scratch_bytes),
                        api.droidds_homebrew_probe(native_bytes, scratch_bytes)):
            busy = owned(pointer)
            check(busy.get("status") == "failed" and "active" in busy.get("error", ""),
                  "A reentrant native probe was not rejected as busy")
        check(state(token) == before, "Competing probe changed the live guest")
        controls.append("live_session_reentrant_probes_rejected")

        # CodexAstraUlt: A real second OS thread must not reach or close the
        # owner's System. The parent build tool supplies a process deadline too.
        outcome = []
        def wrong_worker():
            try:
                check(report(token).get("status") == "failed", "Wrong worker read the live session")
                check(api.droidds_homebrew_pause(token, 1) < 0, "Wrong worker paused the live session")
                check(frame(token) < 0, "Wrong worker advanced the live session")
                api.droidds_homebrew_close(token)
                outcome.append("passed")
            except Exception as error:
                outcome.append(str(error))
        worker = threading.Thread(target=wrong_worker, daemon=True)
        worker.start()
        worker.join(timeout=5)
        check(not worker.is_alive() and outcome == ["passed"], "Wrong-worker isolation failed: " + str(outcome))
        check(state(token) == before, "Wrong worker changed owner state")
        controls.append("wrong_worker_preserves_live_session")

        check(api.droidds_homebrew_pause(token, 1) == 0, "Pause rejected")
        paused = state(token)
        check(frame(token) == -2, "Paused frame was not a recoverable rejection")
        check(state(token) == paused and report(token)["status"] == "paused", "Pause advanced or poisoned the guest")
        check(api.droidds_homebrew_pause(token, 0) == 0 and frame(token) == 0,
              "Retained session did not resume after a rejected paused frame")
        check(state(token)["frames"] > paused["frames"], "Resume did not make progress")
        controls.append("pause_rejection_preserves_resumability")
    finally:
        api.droidds_homebrew_close(token)
    check(report(token).get("status") == "failed", "Closed token remains live")
    check(not (scratch / "homebrew-fixture.cxi").exists(), "Closed session retained its scratch fixture")

    replacement = open_session()
    try:
        check(replacement > token, "Session generation did not advance")
        before = state(replacement)
        api.droidds_homebrew_close(token)
        check(frame(token) < 0 and state(replacement) == before, "Stale token changed replacement session")
        check(frame(replacement) == 0, "Replacement session was destroyed by stale close")
        controls.append("stale_token_preserves_replacement")
        # CodexAstraUlt: Invalid capacity fails before touching caller output and
        # fails the affected session rather than permitting partial guest output.
        top[0], bottom[0], pcm[0] = 17, 23, 29
        metrics.frame_index = 123456
        check(frame(replacement, len(top) - 1) < 0, "Short framebuffer was accepted")
        check((top[0], bottom[0], pcm[0], metrics.frame_index) == (17, 23, 29, 123456),
              "Invalid buffer call wrote output")
        check(report(replacement).get("status") == "failed" and frame(replacement) < 0,
              "Failed buffer contract did not fail closed")
        controls.append("invalid_capacity_preserves_output_and_fails_closed")
    finally:
        api.droidds_homebrew_close(replacement)
    recovery = open_session()
    try:
        check(frame(recovery) == 0, "New session could not recover after failed teardown")
    finally:
        api.droidds_homebrew_close(recovery)
    check(not (scratch / "homebrew-fixture.cxi").exists(), "Final teardown retained guest scratch")
    controls.append("normal_and_failed_teardown_release_ownership")
    return {"schema": 1, "kind": "droidds-homebrew-ffi-proof", "status": "passed", "controls": controls}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--library", required=True, type=Path)
    parser.add_argument("--native-dir", required=True, type=Path)
    parser.add_argument("--scratch-dir", required=True, type=Path)
    arguments = parser.parse_args()
    print(json.dumps(run(arguments.library, arguments.native_dir, arguments.scratch_dir), indent=2))
