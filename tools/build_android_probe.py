#!/usr/bin/env python3
"""CodexAstraUlt: Build a local Android CPU probe and audit its packaged binaries."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import signal
import subprocess
import sys
import tomllib
import xml.etree.ElementTree as ET
import zipfile

from build_foundation import ROOT, interrupted, snapshot, terminate_group, validate_graph
from build_vulkan_probe import generate_shaders
from run_android_probe import apk_manifest, cases_for_version

NDK_VERSION = "27.3.13750724"
BUILD_TOOLS_VERSION = "35.0.0"
TARGET = "aarch64-linux-android"
PACKAGE = "org.droidds.probe"
# CodexAstraUlt: Build exactly the current report contract's fixture inventory;
# historical report validation retains its separate four-case requirements.
CASES = set(cases_for_version("0.0.4"))


def stage_manifest(source: Path, destination: Path, prerelease: bool) -> None:
    """CodexAstraUlt: Enable browser installation only for the requested public probe."""
    if not prerelease:
        shutil.copyfile(source, destination)
        return
    android = "http://schemas.android.com/apk/res/android"
    ET.register_namespace("android", android)
    tree = ET.parse(source)
    root = tree.getroot()
    application = root.find("application")
    if root.get("package") != PACKAGE or application is None:
        raise ValueError("Only the synthetic DroidDS probe may be staged for publication")
    if application.get("{" + android + "}debuggable") != "true":
        raise ValueError("Probe report retrieval requires the diagnostic debuggable flag")
    application.set("{" + android + "}testOnly", "false")
    tree.write(destination, encoding="utf-8", xml_declaration=True)


def sha256(path: Path) -> str:
    """CodexAstraUlt: Bind the evidence to actual inputs and final signed bytes."""
    return hashlib.sha256(path.read_bytes()).hexdigest()


def inputs() -> dict:
    """CodexAstraUlt: Android sources join the existing locked CPU source record."""
    result = snapshot()
    result["THIRD_PARTY_NOTICES.md"] = sha256(ROOT / "THIRD_PARTY_NOTICES.md")
    for path in sorted((ROOT / "android/probe").rglob("*")):
        if path.is_file():
            result[str(path.relative_to(ROOT))] = sha256(path)
    return result


def audit_elf(text: str, packaged: set[str]) -> dict:
    """CodexAstraUlt: Reject host ELF, text relocations and insufficient load alignment."""
    if not re.search(r"Class:\s+ELF64", text) or not re.search(r"Machine:\s+AArch64", text):
        raise ValueError("Expected a 64-bit AArch64 ELF library")
    if not re.search(r"Type:\s+DYN", text):
        raise ValueError("Expected a shared ELF library")
    loads = [line.split() for line in text.splitlines() if line.strip().startswith("LOAD ")]
    if not loads:
        raise ValueError("ELF has no load segments")
    for row in loads:
        alignment = int(row[-1], 16)
        if alignment < 16384 or alignment & (alignment - 1):
            raise ValueError("ELF load segment does not support 16 KiB alignment")
        if int(row[1], 16) % alignment != int(row[2], 16) % alignment:
            raise ValueError("ELF load address/offset alignment differs")
        if "W" in "".join(row[6:-1]) and "E" in "".join(row[6:-1]):
            raise ValueError("Writable executable ELF segment")
    if "TEXTREL" in text:
        raise ValueError("ELF contains text relocations")
    needed = re.findall(r"\(NEEDED\).*?\[([^]]+)\]", text)
    # CodexAstraUlt: The Vulkan probe uses Android's platform loader, without
    # bundling a desktop loader or requiring a vendor-specific graphics service.
    allowed = packaged | {"libc.so", "libm.so", "libdl.so", "liblog.so", "libvulkan.so"}
    unexpected = set(needed) - allowed
    if unexpected:
        raise ValueError(f"Unpackaged/non-Android dependencies: {sorted(unexpected)}")
    return {"machine": "AArch64", "load_alignments": [int(row[-1], 16) for row in loads],
            "needed": needed, "text_relocations": False}


def main() -> int:
    # CodexAstraUlt: SDK paths are explicit or conventional environment inputs;
    # this tool never mutates a sibling project or consumes its signing identity.
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sdk", type=Path, default=os.environ.get("ANDROID_HOME"))
    parser.add_argument("--java-home", type=Path, default=os.environ.get("JAVA_HOME"))
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--jobs", type=int, default=2)
    parser.add_argument("--prerelease", action="store_true",
                        help="make the diagnostic probe installable from a downloaded APK")
    parser.add_argument("--debug-keystore", type=Path,
                        default=ROOT / "build/android-probe-debug.keystore")
    args = parser.parse_args()
    if not args.sdk or not args.java_home or args.jobs < 1:
        parser.error("--sdk/ANDROID_HOME and --java-home/JAVA_HOME are required; jobs must be positive")
    out = args.output.resolve()
    out.mkdir(parents=True, exist_ok=False)
    sdk, java = args.sdk.resolve(), args.java_home.resolve()
    ndk = sdk / "ndk" / NDK_VERSION
    llvm = ndk / "toolchains/llvm/prebuilt/linux-x86_64/bin"
    cc = llvm / "aarch64-linux-android29-clang"
    build_tools = sdk / "build-tools" / BUILD_TOOLS_VERSION
    android_jar = sdk / "platforms/android-35/android.jar"
    env = dict(os.environ)
    env["JAVA_HOME"] = str(java)
    env["PATH"] = str(java / "bin") + os.pathsep + env.get("PATH", "")
    # CodexAstraUlt: Keep artifact paths and target flags reproducible even when
    # a caller's interactive shell has unrelated Cargo overrides configured.
    env["CARGO_TARGET_DIR"] = str(ROOT / "target")
    env.pop("RUSTFLAGS", None)
    env.pop("CARGO_ENCODED_RUSTFLAGS", None)
    commands = []
    report = {"schema": 1, "kind": "droidds-android-probe-build", "status": "building",
              "runtime_status": "not_run", "target": TARGET, "minimum_api": 29,
              "compile_target_api": 35, "ndk": NDK_VERSION, "build_tools": BUILD_TOOLS_VERSION,
              "distribution": "prerelease" if args.prerelease else "local-debug",
              "commands": commands}

    def run(name: str, argv: list, timeout: int = 600, extra_env: dict | None = None,
            json_stdout: bool = False) -> str:
        """CodexAstraUlt: Preserve command logs/status and terminate owned descendants."""
        argv = [str(x) for x in argv]
        print(f"[{name}]", flush=True)
        log = out / f"{name}.log"
        entry = {"step": name, "argv": argv, "log": log.name}
        commands.append(entry)
        # CodexAstraUlt: Cold Cargo downloads write progress to stderr. Preserve
        # that evidence separately so it cannot corrupt machine-readable JSON.
        error_log = out / f"{name}-stderr.log"
        with log.open("wb") as stream, error_log.open("wb") as errors:
            process = subprocess.Popen(argv, cwd=ROOT, env=env | (extra_env or {}),
                                       stdout=stream, stderr=errors if json_stdout else subprocess.STDOUT,
                                       start_new_session=True)
            try:
                entry["exit_code"] = process.wait(timeout=timeout)
            except (subprocess.TimeoutExpired, KeyboardInterrupt):
                terminate_group(process)
                entry["status"] = "inconclusive"
                raise RuntimeError(f"{name}: timed out or interrupted") from None
        text = log.read_text(encoding="utf-8", errors="replace")
        if entry["exit_code"]:
            diagnostic = text + error_log.read_text(encoding="utf-8", errors="replace")
            raise RuntimeError(f"{name} failed: {diagnostic[-5000:]}")
        return text

    try:
        for path in (cc, llvm / "llvm-readelf", android_jar, java / "bin/javac",
                     java / "bin/keytool", build_tools / "aapt2", build_tools / "d8",
                     build_tools / "zipalign", build_tools / "apksigner"):
            if not path.is_file():
                raise RuntimeError(f"Missing prerequisite: {path}")
        properties = (ndk / "source.properties").read_text()
        if not re.search(rf"Pkg.Revision\s*=\s*{re.escape(NDK_VERSION)}\s*$", properties, re.M):
            raise RuntimeError("NDK directory does not contain the pinned revision")
        report["inputs_sha256"] = inputs()
        report["rustc"] = run("rust-version", ["rustc", "--version"], json_stdout=True).strip()
        if not report["rustc"].startswith("rustc 1.95.0 "):
            raise RuntimeError(f"Pinned Rust 1.95.0 is required; observed {report['rustc']!r}")
        report["clang"] = run("clang-version", [cc, "--version"]).splitlines()[0]
        report["java"] = run("java-version", [java / "bin/java", "-version"]).strip()
        metadata = json.loads(run("metadata", ["cargo", "metadata", "--locked", "--format-version", "1"],
                                  json_stdout=True))
        pins = tomllib.loads((ROOT / "upstream.lock.toml").read_text())
        report["sources"] = validate_graph(metadata, pins)
        # CodexAstraUlt: Ship supplied dependency notices and explicit SPDX-based
        # terms in the APK itself, as well as beside a downloadable prerelease.
        notices = out / "THIRD_PARTY_NOTICES.txt"
        run("dependency-notices", [sys.executable, ROOT / "tools/collect_android_notices.py",
                                   "--ndk", ndk, "--output", notices])
        report["third_party_notices"] = {"file": notices.name, "sha256": sha256(notices),
                                         "apk_entry": "assets/THIRD_PARTY_NOTICES.txt"}
        tree = run("android-dependencies", ["cargo", "tree", "--locked", "-p",
                   "droidds-android-probe", "--target", TARGET, "-e", "normal,build", "--prefix", "none"])
        if any(re.search(rf"^{name}\s", tree, re.M) for name in
               ("recomp3ds", "zakuro", "zakuro-core", "zakuro-gpu")):
            raise RuntimeError("Android probe unexpectedly includes host compiler/full runtime")
        run("generator-build", ["cargo", "build", "--locked", "--release", "-p",
                                "droidds-foundation", "--bin", "droidds-foundation", "-j", args.jobs])
        run("emit-fixtures", [ROOT / "target/release/droidds-foundation", "--emit-sources", out / "generated"])
        manifest = json.loads((out / "generated/manifest.json").read_text())
        cases = manifest["cases"]
        if {case["name"] for case in cases} != CASES or len(cases) != len(CASES):
            raise ValueError("Generator did not emit exactly the current fixture libraries")
        libs = out / "libraries"
        libs.mkdir()
        # CodexAstraUlt: Match upstream semantic options while selecting NDK's
        # Bionic target explicitly. Never use fast-math or host GCC for the APK.
        c_flags = ["-O2", "-ffp-contract=off", "-fno-math-errno", "-fPIC", "-fvisibility=hidden"]
        link_flags = ["-shared", "-Wl,-z,max-page-size=16384", "-Wl,-z,common-page-size=16384",
                      "-Wl,-z,relro", "-Wl,-z,now", "-Wl,--no-undefined"]
        for case in cases:
            folder = out / "generated" / case["name"]
            expected_name = "libdds_fixture_" + case["name"] + ".so"
            if case["library"] != expected_name or not case["sources"]:
                raise ValueError("Unexpected generated library name/sources")
            sources = []
            for source in case["sources"]:
                if Path(source).name != source or not source.endswith(".c"):
                    raise ValueError("Generator returned a non-local C source")
                sources.append(folder / source)
            run("compile-" + case["name"], [cc, *c_flags, *link_flags,
                "-Wl,-soname," + expected_name, "-I", folder, *sources,
                "-o", libs / expected_name, "-lm"])
        cross_env = {"CARGO_TARGET_AARCH64_LINUX_ANDROID_LINKER": str(cc),
                     "CARGO_TARGET_AARCH64_LINUX_ANDROID_RUSTFLAGS":
                     "-C link-arg=-Wl,-z,max-page-size=16384 -C link-arg=-Wl,-z,common-page-size=16384"}
        run("rust-android", ["cargo", "build", "--locked", "--release", "--target", TARGET,
                             "-p", "droidds-android-probe", "-j", args.jobs], extra_env=cross_env)
        shutil.copy2(ROOT / "target" / TARGET / "release/libdroidds_android_probe.so", libs)
        # CodexAstraUlt: Compile and validate original shaders offline. The APK
        # creates real Vulkan pipelines but carries no runtime shader compiler.
        report["vulkan_shaders"] = generate_shaders(ndk, out / "shaders", run)
        run("jni-bridge", [cc, *c_flags, *link_flags, "-std=c11", "-Wall", "-Wextra", "-Werror",
            "-Wl,-soname,libdroidds_probe_jni.so", ROOT / "android/probe/jni/probe_jni.c",
            ROOT / "android/probe/jni/vulkan_probe.c", ROOT / "android/probe/jni/vulkan_renderer.c",
            "-I", out / "shaders",
            "-L", libs, "-ldroidds_android_probe", "-lvulkan", "-o", libs / "libdroidds_probe_jni.so"])
        packaged = {path.name for path in libs.glob("*.so")}
        report["elf"] = {}
        for path in sorted(libs.glob("*.so")):
            details = run("elf-" + path.stem, [llvm / "llvm-readelf", "-W", "-h", "-l", "-d", path])
            report["elf"][path.name] = audit_elf(details, packaged) | {"sha256": sha256(path)}
        classes, dex = out / "classes", out / "dex"
        classes.mkdir(); dex.mkdir()
        sources = sorted((ROOT / "android/probe/java").rglob("*.java"))
        if not sources:
            raise ValueError("Android Java shell sources are missing")
        # CodexAstraUlt: javac needs the Java 8 lambda bootstrap signatures;
        # d8 then desugars the bytecode for API29. Android stubs alone omit them.
        run("javac", [java / "bin/javac", "--release", "8", "-Xlint:all", "-Werror",
                      "-encoding", "UTF-8", "-classpath", android_jar, "-d", classes, *sources])
        run("dex", [build_tools / "d8", "--min-api", "29", "--lib", android_jar,
                    "--output", dex, *sorted(classes.rglob("*.class"))])
        raw_apk = out / "probe-unaligned.apk"
        staged_manifest = out / "AndroidManifest.xml"
        stage_manifest(ROOT / "android/probe/AndroidManifest.xml", staged_manifest, args.prerelease)
        report["staged_manifest_sha256"] = sha256(staged_manifest)
        run("manifest", [build_tools / "aapt2", "link", "-I", android_jar, "--manifest",
                         staged_manifest, "-o", raw_apk])
        with zipfile.ZipFile(raw_apk, "a") as archive:
            archive.write(dex / "classes.dex", "classes.dex", compress_type=zipfile.ZIP_DEFLATED)
            for path in sorted(libs.glob("*.so")):
                archive.write(path, "lib/arm64-v8a/" + path.name, compress_type=zipfile.ZIP_STORED)
            archive.write(ROOT / "THIRD_PARTY_NOTICES.md", "assets/THIRD_PARTY_NOTICES.md",
                          compress_type=zipfile.ZIP_DEFLATED)
            archive.write(notices, "assets/THIRD_PARTY_NOTICES.txt", compress_type=zipfile.ZIP_DEFLATED)
        aligned = out / "probe-aligned.apk"
        run("zipalign", [build_tools / "zipalign", "-P", "16", "-f", "4", raw_apk, aligned])
        # CodexAstraUlt: This isolated diagnostic key is not a product signing key
        # and is never copied from Uberhar. Its conventional password is public.
        key = args.debug_keystore.resolve()
        if not key.exists():
            key.parent.mkdir(parents=True, exist_ok=True)
            run("debug-key", [java / "bin/keytool", "-genkeypair", "-keystore", key,
                "-storepass", "android", "-keypass", "android", "-alias", "droidds-probe-debug",
                "-dname", "CN=DroidDS development,O=Android,C=US", "-keyalg", "RSA",
                "-keysize", "2048", "-validity", "10000", "-storetype", "JKS", "-noprompt"])
            key.chmod(0o600)
        apk = out / ("droidds-android-probe-prerelease.apk" if args.prerelease
                     else "droidds-android-probe-debug.apk")
        run("sign", [build_tools / "apksigner", "sign", "--ks", key, "--ks-key-alias",
            "droidds-probe-debug", "--ks-pass", "pass:android", "--key-pass", "pass:android",
            "--out", apk, aligned])
        report["signature_verification"] = run("verify-signature", [build_tools / "apksigner",
                                               "verify", "--verbose", "--print-certs", apk])
        # CodexAstraUlt: Publish a certificate fingerprint, never the signing key.
        # The first disposable probe has no previously established public signer.
        certificates = re.findall(r"Signer #\d+ certificate SHA-256 digest: ([a-fA-F0-9]{64})",
                                  report["signature_verification"])
        if len(certificates) != 1:
            raise ValueError("Expected exactly one verified APK signing certificate")
        report["signing_certificate_sha256"] = certificates[0].lower()
        run("verify-apk-alignment", [build_tools / "zipalign", "-c", "-P", "16", "-v", "4", apk])
        badging = run("verify-package", [build_tools / "aapt2", "dump", "badging", apk])
        if f"package: name='{PACKAGE}'" not in badging or "native-code: 'arm64-v8a'" not in badging:
            raise ValueError("APK package/ABI differs from the Android probe")
        if not re.search(r"^(?:minSdkVersion|sdkVersion):'29'$", badging, re.M) or "targetSdkVersion:'35'" not in badging:
            raise ValueError("APK API levels differ from the probe contract")
        actual_manifest = apk_manifest(apk, allow_prerelease=args.prerelease)
        if actual_manifest["test_only"] != (not args.prerelease):
            raise ValueError("Packaged APK install mode differs from the requested mode")
        report.update(manifest=actual_manifest, test_only=actual_manifest["test_only"],
                      debuggable=actual_manifest["debuggable"])
        if inputs() != report["inputs_sha256"]:
            raise ValueError("Build inputs changed during execution; rerun from stable sources")
        report.update(status="built", apk=apk.name, apk_sha256=sha256(apk),
                      apk_bytes=apk.stat().st_size,
                      completed_utc=datetime.now(timezone.utc).isoformat())
        print(f"Android probe built: {apk}\nDevice execution: NOT RUN", flush=True)
        return 0
    except (OSError, ValueError, KeyError, RuntimeError, KeyboardInterrupt) as error:
        report.update(status="failed", error=str(error))
        print(f"Android probe build failed: {error}", file=sys.stderr)
        return 1
    finally:
        (out / "build-report.json").write_text(json.dumps(report, indent=2) + "\n")


if __name__ == "__main__":
    signal.signal(signal.SIGTERM, interrupted)
    raise SystemExit(main())
