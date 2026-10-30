#!/usr/bin/env python3
"""CodexAstraUlt: Package an admitted ARM64 title with the separate Android player.

Private artifacts stay outside Git. Owner signing uses an explicit local profile;
only byte-verified authored fixtures can use an isolated diagnostic signing key.
The historical probe inventory and compilation helpers are never modified.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import shutil
import signal
import struct
import subprocess
import sys
import tomllib
import xml.etree.ElementTree as ET
import zipfile

from build_android_probe import audit_elf, NDK_VERSION, BUILD_TOOLS_VERSION, TARGET
from build_foundation import ROOT, interrupted, snapshot, terminate_group, validate_graph
from validate_runtime_shaders import validate_runtime_shaders
import collect_android_notices as NOTICES

VERSION = "0.0.7-preview.2"
LIBRARIES = {"libdroidds_title.so", "libdroidds_title_player.so", "libdroidds_title_jni.so"}
SHARED_JAVA = ("ScreenView.java", "ScreenGeometry.java", "PcmResampler.java",
               "FramePacer.java", "AudioStartup.java")
ANDROID = "{http://schemas.android.com/apk/res/android}"
MAX_METADATA = 1024 * 1024


def require(condition, message):
    if not condition:
        raise ValueError(message)


def identity(path):
    """CodexAstraUlt: Stream artifact hashes rather than materializing native libraries."""
    digest, size = hashlib.sha256(), 0
    with Path(path).open("rb") as stream:
        while chunk := stream.read(1024 * 1024):
            digest.update(chunk)
            size += len(chunk)
    return {"bytes": size, "sha256": digest.hexdigest()}


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()


def separate_output(output, protected):
    """CodexAstraUlt: Packaging cannot write into SDKs, retained inputs or signer storage."""
    require(not output.exists() and output.parent.is_dir(), "fresh_package_output_required")
    for source in protected:
        source = Path(source).resolve()
        require(output != source and source not in output.parents and output not in source.parents,
                "package_output_overlaps_protected_input")


def package_name(program_id):
    """CodexAstraUlt: Each title has a stable install identity distinct from the probe."""
    require(isinstance(program_id, str) and re.fullmatch(r"[0-9a-f]{16}", program_id),
            "invalid_title_program_id")
    return "org.droidds.title.t" + program_id


def stage_manifest(source, destination, program_id, version_code, diagnostic):
    """CodexAstraUlt: Stage a separate title template without mutating source XML."""
    require(type(version_code) is int and 0 < version_code <= 2_100_000_000, "invalid_version_code")
    ET.register_namespace("android", ANDROID[1:-1])
    tree = ET.parse(source)
    root = tree.getroot()
    require(root.tag == "manifest" and root.get("package") == "org.droidds.title.template",
            "unexpected_title_manifest_template")
    apps = root.findall("application")
    require(len(apps) == 1 and len(root.findall("uses-sdk")) == 1, "invalid_title_manifest_structure")
    require(not root.findall("uses-permission"), "unexpected_title_permission")
    application, sdk = apps[0], root.find("uses-sdk")
    require(sdk.get(ANDROID + "minSdkVersion") == "29" and sdk.get(ANDROID + "targetSdkVersion") == "35",
            "unexpected_title_sdk")
    activities = application.findall("activity")
    require(len(activities) == 1 and activities[0].get(ANDROID + "name") == "org.droidds.probe.TitleActivity",
            "unexpected_title_activity")
    root.set("package", package_name(program_id))
    root.set(ANDROID + "versionCode", str(version_code))
    root.set(ANDROID + "versionName", VERSION)
    for name, value in {"allowBackup": "false", "testOnly": "false", "extractNativeLibs": "true",
                        "debuggable": "true" if diagnostic else "false"}.items():
        application.set(ANDROID + name, value)
    tree.write(destination, encoding="utf-8", xml_declaration=True)


def signing_profile(path, environment):
    """CodexAstraUlt: Password values are never arguments, log fields or report data."""
    with Path(path).open("rb") as stream:
        raw = stream.read(16385)
    require(len(raw) <= 16384, "signing_profile_too_large")
    def unique(pairs):
        result = {}
        for key, value in pairs:
            require(key not in result, "duplicate_signing_profile_key")
            result[key] = value
        return result
    value = json.loads(raw, object_pairs_hook=unique)
    fields = {"schema_version", "kind", "keystore", "alias", "store_password_env",
              "key_password_env", "certificate_sha256"}
    require(isinstance(value, dict) and set(value) == fields and type(value["schema_version"]) is int
            and value["schema_version"] == 1 and value["kind"] == "droidds_android_signing_profile",
            "invalid_signing_profile")
    require(isinstance(value["alias"], str) and re.fullmatch(r"[A-Za-z0-9_.-]{1,128}", value["alias"]),
            "invalid_signing_alias")
    require(isinstance(value["certificate_sha256"], str)
            and re.fullmatch(r"[0-9a-f]{64}", value["certificate_sha256"]), "invalid_signing_certificate")
    require(isinstance(value["keystore"], str), "invalid_keystore_path")
    key = Path(value["keystore"])
    require(key.is_absolute() and key.is_file() and not key.is_symlink(), "owner_keystore_missing_or_symlink")
    for name in ("store_password_env", "key_password_env"):
        variable = value[name]
        require(isinstance(variable, str) and re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]{0,127}", variable),
                "invalid_password_environment_name")
        require(bool(environment.get(variable)), "signing_password_environment_missing")
    return value


def sign_arguments(profile, apk, aligned):
    """CodexAstraUlt: apksigner obtains secrets from explicitly named environment entries."""
    return ["sign", "--ks", profile["keystore"], "--ks-key-alias", profile["alias"],
            "--ks-pass", "env:" + profile["store_password_env"], "--key-pass",
            "env:" + profile["key_password_env"], "--out", str(apk), str(aligned)]


def certificate_fingerprint(text, expected=None):
    """CodexAstraUlt: An APK must have exactly one verified intended public certificate."""
    matches = re.findall(r"Signer #\d+ certificate SHA-256 digest: ([a-fA-F0-9]{64})", text)
    require(len(matches) == 1, "expected_one_signing_certificate")
    digest = matches[0].lower()
    require(expected is None or digest == expected, "signing_certificate_mismatch")
    return digest


def validate_dependencies(tree):
    """CodexAstraUlt: The title's normal Android graph excludes probe and host tooling."""
    records = {}
    for line in tree.splitlines():
        match = re.fullmatch(r"([\w-]+) v(\S+)(.*)", line)
        if match:
            records.setdefault(match[1], set()).add((match[2], match[3].removesuffix(" (*)")))
    required = {"droidds-title-player", "droidds-title-runtime", "recomp-abi", "zakuro-common",
                "zakuro-cpu", "zakuro-core", "zakuro-fs", "zakuro-gpu", "ash", "naga"}
    forbidden = {name for name in records if name in {"recomp3ds", "zakuro", "glow", "winit",
        "eframe", "egui", "sdl2", "sdl3", "droidds-android-probe", "droidds-runtime-probe",
        "droidds-title-builder", "droidds-native-title-tools"} or name.startswith("cranelift-")}
    require(required <= records.keys() and not forbidden,
            "title_dependency_graph_mismatch:" + repr((sorted(required - records.keys()), sorted(forbidden))))
    for name in ("zakuro-core", "zakuro-fs", "zakuro-gpu"):
        require(records[name] == {("0.2.27", f" ({ROOT / 'vendor/zakuro/crates' / name})")},
                "unreviewed_title_runtime_source")
    return {"packages": sorted(records), "host_compiler": False, "probe_runtime": False, "pica_cpu_jit": False}


def audit_manifest(badging, xmltree, package, version_code, diagnostic):
    """CodexAstraUlt: Audit the compiled APK's binary manifest via SDK observations."""
    match = re.search(r"^package: name='([^']+)' versionCode='([0-9]+)' versionName='([^']+)'", badging, re.M)
    require(match is not None and match.groups() == (package, str(version_code), VERSION), "apk_identity_mismatch")
    require(re.search(r"^(?:minSdkVersion|sdkVersion):'29'$", badging, re.M)
            and "targetSdkVersion:'35'" in badging and re.search(r"^native-code: 'arm64-v8a'$", badging, re.M),
            "apk_target_mismatch")
    require("launchable-activity: name='org.droidds.probe.TitleActivity'" in badging, "apk_launcher_mismatch")
    require(not re.search(r"^uses-permission", badging, re.M), "apk_unexpected_permission")
    # CodexAstraUlt: Inspect attributes only inside the single application node;
    # same-named metadata or activity attributes cannot satisfy package policy.
    active, application_count, attributes = False, 0, {}
    for line in xmltree.splitlines():
        stripped = line.strip()
        if stripped.startswith("E: "):
            active = stripped.startswith("E: application ") or stripped == "E: application"
            application_count += int(active)
        elif active:
            item = re.fullmatch(r"A: (?:android:|http://schemas\.android\.com/apk/res/android:)"
                                r"(\w+)\(0x[0-9a-f]+\)=(true|false|\(type 0x12\)0x[0-9a-f]+)", stripped)
            if item:
                require(item[1] not in attributes, "duplicate_apk_application_attribute")
                attributes[item[1]] = (item[2] == "true" if item[2] in ("true", "false")
                                       else int(item[2].removeprefix("(type 0x12)"), 16) != 0)
    require(application_count == 1 and all(attributes.get(key) is value for key, value in {
        "allowBackup": False, "testOnly": False, "extractNativeLibs": True,
        "debuggable": diagnostic}.items()), "apk_application_policy_mismatch")
    return {"package": package, "version_code": version_code, "version_name": VERSION,
            "debuggable": diagnostic, "test_only": False, "minimum_api": 29, "target_api": 35}


def audit_zip(apk, libraries, manifest_bytes, original=None):
    """CodexAstraUlt: Verify signed ZIP entries, exact identities and 16 KiB storage."""
    require(set(libraries) == LIBRARIES, "title_library_inventory_mismatch")
    with zipfile.ZipFile(apk) as archive, Path(apk).open("rb") as stream:
        names = [item.filename for item in archive.infolist()]
        require(len(names) == len(set(names)), "duplicate_apk_entry")
        required = {"AndroidManifest.xml", "resources.arsc", "classes.dex", "assets/title-manifest.json",
                    "assets/THIRD_PARTY_NOTICES.md", "assets/THIRD_PARTY_NOTICES.txt"}
        required |= {"lib/arm64-v8a/" + name for name in LIBRARIES}
        if original is not None:
            required.add("assets/original-title.cxi")
        require(required <= set(names), "missing_title_apk_entry")
        require(all(name in required or re.fullmatch(r"META-INF/(?:MANIFEST\.MF|[A-Za-z0-9_-]+\.(?:SF|RSA|DSA|EC))", name)
                    for name in names),
                "unexpected_title_apk_entry")
        require(archive.read("assets/title-manifest.json") == manifest_bytes, "packaged_title_manifest_changed")
        entries = {}
        for name, expected in libraries.items():
            info = archive.getinfo("lib/arm64-v8a/" + name)
            require(info.compress_type == zipfile.ZIP_STORED, "compressed_title_native_library")
            stream.seek(info.header_offset)
            header = stream.read(30)
            require(header[:4] == b"PK\x03\x04" and len(header) == 30, "invalid_apk_local_header")
            name_bytes, extra_bytes = struct.unpack_from("<HH", header, 26)
            offset = info.header_offset + 30 + name_bytes + extra_bytes
            require(offset % 16384 == 0, "unaligned_title_native_zip_entry")
            digest, size = hashlib.sha256(), 0
            with archive.open(info) as member:
                while chunk := member.read(1024 * 1024):
                    size += len(chunk)
                    digest.update(chunk)
            require({"bytes": size, "sha256": digest.hexdigest()} == expected, "packaged_native_identity_mismatch")
            entries[name] = {**expected, "zip_offset": offset, "stored": True}
        if original is not None:
            info = archive.getinfo("assets/original-title.cxi")
            require(info.file_size == original["bytes"] and
                    hashlib.sha256(archive.read(info)).hexdigest() == original["sha256"], "packaged_original_fixture_changed")
    return entries


def source_identity():
    """CodexAstraUlt: Bind shared Java, new player sources and reviewed build tools."""
    result = snapshot()
    paths = [ROOT / "THIRD_PARTY_NOTICES.md"]
    paths += sorted(path for path in (ROOT / "android/title").rglob("*") if path.is_file())
    paths += [ROOT / "android/probe/java/org/droidds/probe" / name for name in SHARED_JAVA]
    for path in paths:
        result[path.relative_to(ROOT).as_posix()] = identity(path)["sha256"]
    return result


def parse_args(argv=None):
    """CodexAstraUlt: Title compilation, versioning and signer selection are explicit."""
    parser = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    for option in ("preparation", "compilation", "output", "sdk", "java-home"):
        parser.add_argument("--" + option, type=Path, required=True)
    parser.add_argument("--version-code", type=int, required=True)
    parser.add_argument("--jobs", type=int, default=2)
    signer = parser.add_mutually_exclusive_group(required=True)
    signer.add_argument("--signing-profile", type=Path)
    signer.add_argument("--diagnostic-signing", action="store_true")
    parser.add_argument("--diagnostic-fixture", choices=("runtime", "homebrew"))
    args = parser.parse_args(argv)
    if not 1 <= args.jobs <= 8 or not 1 <= args.version_code <= 2_100_000_000:
        parser.error("jobs or version code is outside its bound")
    if bool(args.diagnostic_fixture) != args.diagnostic_signing:
        parser.error("diagnostic signing requires an explicit original fixture; owner signing cannot select one")
    return args


def build(args):
    """CodexAstraUlt: Package an admitted read-only library under its shared lock."""
    spec = importlib.util.spec_from_file_location("droidds_android_compilation", ROOT / "tools/compile_android_title.py")
    compiler = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(compiler)
    common = compiler.COMMON
    output = common.absolute_plain(args.output)
    common.outside_git(output)
    environment = dict(os.environ)
    # CodexAstraUlt: Validate signer storage before creating output, so an
    # invalid owner profile cannot leave a misleading partial build directory.
    profile = signing_profile(args.signing_profile, environment) if args.signing_profile else None
    protected = [args.preparation, args.compilation, args.sdk, args.java_home]
    if profile is not None:
        protected.extend((args.signing_profile, Path(profile["keystore"])))
    separate_output(output, protected)
    key_before = Path(profile["keystore"]).stat() if profile else None
    output.mkdir(mode=0o700)
    sdk, java = args.sdk.resolve(), args.java_home.resolve()
    ndk = sdk / "ndk" / NDK_VERSION
    llvm = ndk / "toolchains/llvm/prebuilt/linux-x86_64/bin"
    cc = llvm / "aarch64-linux-android29-clang"
    build_tools = sdk / "build-tools" / BUILD_TOOLS_VERSION
    android_jar = sdk / "platforms/android-35/android.jar"
    environment["JAVA_HOME"] = str(java)
    environment["PATH"] = str(java / "bin") + os.pathsep + environment.get("PATH", "")
    environment["CARGO_TARGET_DIR"] = str(ROOT / "target")
    environment.pop("RUSTFLAGS", None)
    environment.pop("CARGO_ENCODED_RUSTFLAGS", None)
    report = {"schema_version": 1, "kind": "droidds_android_title_build", "status": "building",
              "version": VERSION, "commands": [], "device_execution": "not_run", "source": source_identity()}

    def run(name, command, timeout=600, extra=None):
        # CodexAstraUlt: Record only argv with password variable names. Each
        # owned process group has a deadline and is reaped on interruption.
        command = [str(part) for part in command]
        entry = {"step": name, "argv": command, "log": name + ".log"}
        report["commands"].append(entry)
        print("[" + name + "]", flush=True)
        log, errors = output / entry["log"], output / (name + "-stderr.log")
        with log.open("xb") as stdout, errors.open("xb") as stderr:
            process = subprocess.Popen(command, cwd=ROOT, env=environment | (extra or {}),
                stdout=stdout, stderr=stderr, stdin=subprocess.DEVNULL, start_new_session=True)
            try:
                entry["exit_code"] = process.wait(timeout=timeout)
            except (subprocess.TimeoutExpired, KeyboardInterrupt):
                terminate_group(process)
                raise RuntimeError(name + ": timed out or interrupted") from None
        require(entry["exit_code"] == 0, name + "_failed; inspect retained local logs")
        require(log.stat().st_size <= 32 * MAX_METADATA, name + "_stdout_exceeds_bound")
        require(errors.stat().st_size <= 32 * MAX_METADATA, name + "_stderr_exceeds_bound")
        return log.read_text(errors="replace")

    try:
        for path in (cc, llvm / "llvm-readelf", llvm / "llvm-strip", android_jar,
                     java / "bin/javac", java / "bin/keytool", build_tools / "aapt2",
                     build_tools / "d8", build_tools / "zipalign", build_tools / "apksigner"):
            require(path.is_file(), "missing_android_prerequisite:" + str(path))
        require(re.search(rf"^Pkg.Revision\s*=\s*{re.escape(NDK_VERSION)}\s*$",
                          (ndk / "source.properties").read_text(), re.M), "wrong_ndk_revision")
        report["rustc"] = run("rust-version", ["rustc", "--version"]).strip()
        require(report["rustc"].startswith("rustc 1.95.0 "), "pinned_rust_required")
        report["clang"] = run("clang-version", [cc, "--version"]).splitlines()[0]
        # CodexAstraUlt: Import cancellation/publication, save preservation and
        # input mapping run on the host JVM before an APK can be reported built.
        report["java_title_logic"] = json.loads(run("java-title-logic", [sys.executable,
            ROOT / "tools/check_java_title.py", "--java-home", java, "--output", output / "java-title-logic"]))
        require(report["java_title_logic"].get("status") == "passed"
                and report["java_title_logic"].get("kind") == "droidds-java-title-logic"
                and report["java_title_logic"].get("checks") == 55
                and report["java_title_logic"].get("controls") == [
                    "verified_import_reuse_preservation", "rejection_cancel_io_cleanup",
                    "atomic_publication_races", "symlink_and_atomic_report_preservation",
                    "input_edges_axes_release", "pause_resume_retires_delayed_callbacks"],
                "java_title_logic_did_not_pass")
        metadata = json.loads(run("metadata", ["cargo", "metadata", "--offline", "--locked", "--format-version", "1"]))
        report["sources"] = validate_graph(metadata, tomllib.loads((ROOT / "upstream.lock.toml").read_text()))
        report["dependencies"] = validate_dependencies(run("target-dependencies", ["cargo", "tree", "--offline", "--locked",
            "-p", "droidds-title-player", "--target", TARGET, "-e", "normal,build", "--prefix", "none"]))
        # CodexAstraUlt: The player ships the same reviewed Vulkan assets as the
        # probe; each binary and source variant keeps its actual validation gate.
        report["runtime_shaders"] = validate_runtime_shaders(ndk, output / "runtime-shaders", run)
        sysroot = Path(run("rust-sysroot", ["rustc", "--print", "sysroot"]).strip())
        # CodexAstraUlt: The collector retains exact dependency/license gates
        # while its explicit title mode avoids labeling private code as a fixture.
        notices = NOTICES.assemble(metadata, ndk, sysroot, report["rustc"], title_player=True)
        notice_path = output / "THIRD_PARTY_NOTICES.txt"
        notice_path.write_text(notices)
        with compiler.admitted_android_inputs(args.preparation, args.compilation) as admitted:
            contract = admitted["plan"]["contract"]
            require(contract.get("target") == TARGET and contract.get("minimum_api") == 29
                    and contract.get("ndk") == NDK_VERSION and contract.get("machine") == 183,
                    "non_android_title_compilation")
            manifest = compiler.title_manifest(admitted)
            manifest_bytes = canonical(manifest)
            require(len(manifest_bytes) <= MAX_METADATA, "title_manifest_too_large")
            package = package_name(manifest["program_id"])
            original = None
            if args.diagnostic_signing:
                run("original-producer-build", ["cargo", "build", "--offline", "--locked", "--release",
                    "-p", "droidds-runtime-probe", "--features", "producer", "-j", args.jobs], timeout=1800)
                generated = output / "original-proof"
                action = "emit-homebrew" if args.diagnostic_fixture == "homebrew" else "emit"
                run("original-proof", [ROOT / "target/release/droidds-runtime-probe", action, "--output", generated])
                original = generated / ("homebrew-fixture.cxi" if args.diagnostic_fixture == "homebrew" else "runtime-fixture.cxi")
                require(identity(original) == manifest["input"], "diagnostic_signing_requires_exact_original_fixture")
                # CodexAstraUlt: Public provenance describes only the authored
                # producer and exact verified bytes, with no owner-local paths.
                producer_sources = {}
                for crate in ("droidds-runtime-probe", "droidds-title-builder"):
                    directory = ROOT / "crates" / crate
                    for path in [directory / "Cargo.toml", *sorted(directory.rglob("*.rs"))]:
                        producer_sources[path.relative_to(ROOT).as_posix()] = identity(path)["sha256"]
                report["original_fixture"] = {
                    "fixture": "droidds-original-" + args.diagnostic_fixture + "-v1",
                    "producer": "droidds-runtime-probe", "action": action,
                    "input": identity(original), "producer_sources": producer_sources}
                key = output / "diagnostic-title.keystore"
                environment["DROIDDS_TITLE_DIAGNOSTIC_PASSWORD"] = "droidds-title-diagnostic"
                profile = {"keystore": str(key), "alias": "droidds-title-diagnostic",
                    "store_password_env": "DROIDDS_TITLE_DIAGNOSTIC_PASSWORD",
                    "key_password_env": "DROIDDS_TITLE_DIAGNOSTIC_PASSWORD", "certificate_sha256": None}
                run("diagnostic-key", [java / "bin/keytool", "-genkeypair", "-keystore", key,
                    "-storepass:env", "DROIDDS_TITLE_DIAGNOSTIC_PASSWORD", "-keypass:env", "DROIDDS_TITLE_DIAGNOSTIC_PASSWORD",
                    "-alias", profile["alias"], "-dname", "CN=DroiDDS original title diagnostic,O=Android,C=US",
                    "-keyalg", "RSA", "-keysize", "2048", "-validity", "10000", "-storetype", "JKS", "-noprompt"])
                key.chmod(0o600)
            libs = output / "libraries"
            libs.mkdir()
            title_library = libs / "libdroidds_title.so"
            shutil.copyfile(admitted["library_path"], title_library)
            require(identity(title_library) == {key: manifest["native"][key] for key in ("bytes", "sha256")},
                    "copied_title_library_changed")
            cross = {"CARGO_TARGET_AARCH64_LINUX_ANDROID_LINKER": str(cc),
                     "CARGO_TARGET_AARCH64_LINUX_ANDROID_RUSTFLAGS":
                     "-C link-arg=-Wl,-z,max-page-size=16384 -C link-arg=-Wl,-z,common-page-size=16384"}
            run("android-runtime", ["cargo", "build", "--offline", "--locked", "--release", "--target", TARGET,
                "-p", "droidds-title-player", "-j", args.jobs], timeout=1800, extra=cross)
            player = libs / "libdroidds_title_player.so"
            shutil.copyfile(ROOT / "target" / TARGET / "release" / player.name, player)
            symbols = output / "symbols"
            symbols.mkdir()
            shutil.copyfile(player, symbols / player.name)
            run("strip-runtime", [llvm / "llvm-strip", "--strip-debug", player])
            run("jni", [cc, "-O2", "-fPIC", "-fvisibility=hidden", "-shared", "-std=c11", "-Wall", "-Wextra", "-Werror",
                "-Wl,-z,max-page-size=16384", "-Wl,-z,common-page-size=16384", "-Wl,-z,relro", "-Wl,-z,now",
                "-Wl,--no-undefined", "-Wl,-soname,libdroidds_title_jni.so", ROOT / "android/title/jni/title_jni.c",
                "-I", ROOT / "android/title/jni", "-L", libs, "-ldroidds_title_player", "-o", libs / "libdroidds_title_jni.so"])
            require({path.name for path in libs.iterdir()} == LIBRARIES, "title_library_inventory_mismatch")
            report["elf"] = {path.name: audit_elf(run("elf-" + path.stem,
                [llvm / "llvm-readelf", "-W", "-h", "-l", "-d", path]), LIBRARIES) | identity(path)
                for path in sorted(libs.iterdir())}
            classes, dex = output / "classes", output / "dex"
            classes.mkdir(); dex.mkdir()
            sources = sorted((ROOT / "android/title/java").rglob("*.java"))
            require(bool(sources), "title_java_sources_missing")
            sources += [ROOT / "android/probe/java/org/droidds/probe" / name for name in SHARED_JAVA]
            run("javac", [java / "bin/javac", "--release", "8", "-Xlint:all", "-Werror", "-encoding", "UTF-8",
                "-classpath", android_jar, "-d", classes, *sources])
            run("dex", [build_tools / "d8", "--min-api", "29", "--lib", android_jar, "--output", dex,
                *sorted(classes.rglob("*.class"))])
            raw, aligned, apk = (output / name for name in ("title-unaligned.apk", "title-aligned.apk", "droidds-title.apk"))
            staged = output / "AndroidManifest.xml"
            stage_manifest(ROOT / "android/title/AndroidManifest.xml", staged, manifest["program_id"], args.version_code,
                           args.diagnostic_signing)
            run("manifest", [build_tools / "aapt2", "link", "-I", android_jar, "--manifest", staged, "-o", raw])
            with zipfile.ZipFile(raw, "a") as archive:
                archive.write(dex / "classes.dex", "classes.dex", compress_type=zipfile.ZIP_DEFLATED)
                for path in sorted(libs.iterdir()):
                    archive.write(path, "lib/arm64-v8a/" + path.name, compress_type=zipfile.ZIP_STORED)
                archive.writestr("assets/title-manifest.json", manifest_bytes, compress_type=zipfile.ZIP_DEFLATED)
                for path in (ROOT / "THIRD_PARTY_NOTICES.md", notice_path):
                    archive.write(path, "assets/" + path.name, compress_type=zipfile.ZIP_DEFLATED)
                if original is not None:
                    archive.write(original, "assets/original-title.cxi", compress_type=zipfile.ZIP_DEFLATED)
            run("zipalign", [build_tools / "zipalign", "-P", "16", "-f", "4", raw, aligned])
            run("sign", [build_tools / "apksigner", *sign_arguments(profile, apk, aligned)])
            certificate = run("signature", [build_tools / "apksigner", "verify", "--verbose", "--print-certs", apk])
            report["signing_certificate_sha256"] = certificate_fingerprint(certificate, profile["certificate_sha256"])
            run("alignment", [build_tools / "zipalign", "-c", "-P", "16", "4", apk])
            report["manifest"] = audit_manifest(run("badging", [build_tools / "aapt2", "dump", "badging", apk]),
                run("xmltree", [build_tools / "aapt2", "dump", "xmltree", apk, "--file", "AndroidManifest.xml"]),
                package, args.version_code, args.diagnostic_signing)
            report["packaged_libraries"] = audit_zip(apk, {name: identity(libs / name) for name in LIBRARIES},
                                                      manifest_bytes, identity(original) if original else None)
            compiler.verify_unchanged(admitted)
            if key_before is not None:
                after = Path(profile["keystore"]).stat()
                require((key_before.st_ino, key_before.st_size, key_before.st_mtime_ns) ==
                        (after.st_ino, after.st_size, after.st_mtime_ns), "owner_keystore_changed")
            require(source_identity() == report["source"], "title_build_sources_changed")
            report.update(status="built", apk=apk.name, apk_identity=identity(apk), title_manifest=manifest,
                diagnostic_signing=args.diagnostic_signing, preserved_inputs_verified=True,
                completed_utc=datetime.now(timezone.utc).isoformat())
        return 0, report
    except (OSError, ValueError, KeyError, RuntimeError, KeyboardInterrupt) as error:
        report.update(status="failed", reason=str(error))
        return 1, report
    finally:
        (output / "build-report.json").write_text(json.dumps(report, indent=2) + "\n")


def main(argv=None):
    signal.signal(signal.SIGTERM, interrupted)
    try:
        code, report = build(parse_args(argv))
        print(json.dumps({key: report[key] for key in ("status", "reason", "apk", "apk_identity") if key in report}, indent=2))
        return code
    except (OSError, ValueError, RuntimeError) as error:
        print("Android title build rejected: " + str(error), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
