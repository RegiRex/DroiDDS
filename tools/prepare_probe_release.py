#!/usr/bin/env python3
"""CodexAstraUlt: Stage only verified public Android probe release assets."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys
import zipfile

from run_android_probe import apk_manifest, cases_for_version
from validate_runtime_shaders import VARIANTS

APK_SOURCE = "droidds-android-probe-prerelease.apk"
NOTICE_FILE = "THIRD_PARTY_NOTICES.txt"
NOTICE_ENTRY = "assets/THIRD_PARTY_NOTICES.txt"
BUILD_TOOLS_VERSION = "35.0.0"
TAG_PATTERN = r"v(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)-probe\.([1-9][0-9]*)"
def libraries_for_version(version: str) -> set[str]:
    """CodexAstraUlt: Bind every release's packaged code to its exact fixture set."""
    libraries = {"libdroidds_android_probe.so", "libdroidds_probe_jni.so"} | {
        "libdds_fixture_" + name + ".so" for name in cases_for_version(version)}
    # CodexAstraUlt: Only the original runtime guest's generated library joins
    # version 0.0.5; historical releases retain their exact inventories.
    if version == "0.0.5":
        libraries.add("libdroidds_fixture_runtime.so")
    return libraries


# CodexAstraUlt: Preserve the historical fixture used by the 0.0.2 release tests;
# actual APK validation always selects its inventory from the requested version.
LIBRARIES = libraries_for_version("0.0.2")


def digest(data: bytes) -> str:
    """CodexAstraUlt: Release evidence binds the exact signed artifact bytes."""
    return hashlib.sha256(data).hexdigest()


def identity(tag: str, commit: str) -> tuple[str, str]:
    """CodexAstraUlt: Tag input never becomes an unchecked path or shell expression."""
    match = re.fullmatch(TAG_PATTERN, tag)
    if not match or not re.fullmatch(r"[0-9a-f]{40}", commit):
        raise ValueError("Expected canonical vX.Y.Z-probe.N tag and full lowercase commit SHA")
    version = ".".join(match.groups()[:3])
    return version, f"DroidDS-{version}-android-arm64.apk"


def require_values(report: dict, expected: dict) -> None:
    """CodexAstraUlt: Do not promote incomplete builds or claim device execution."""
    for name, value in expected.items():
        if type(report.get(name)) is not type(value) or report[name] != value:
            raise ValueError(f"Release build contract mismatch: {name}")


def bounded_file(path: Path, limit: int) -> bytes:
    """CodexAstraUlt: Only ordinary local files inside the explicit bundle are read."""
    if path.is_symlink() or not path.is_file() or path.stat().st_size > limit:
        raise ValueError(f"Missing, linked or oversized release file: {path.name}")
    return path.read_bytes()


def exact_fields(value: object, fields: set[str], label: str) -> dict:
    """CodexAstraUlt: Unknown nested evidence cannot carry private data into a release."""
    if type(value) is not dict or set(value) != fields:
        raise ValueError(f"Runtime release evidence has missing or unreviewed fields: {label}")
    return value


def checked_sha256(value: object, label: str) -> str:
    """CodexAstraUlt: Accept only canonical measured SHA-256 values, never free text."""
    if type(value) is not str or not re.fullmatch(r"[0-9a-f]{64}", value):
        raise ValueError(f"Invalid runtime release SHA-256: {label}")
    return value


def runtime_metadata(report: dict, version: str) -> dict:
    """CodexAstraUlt: Bind the .5 runtime evidence to reviewed sources and audited ELF hashes."""
    if version != "0.0.5":
        return {}
    fixture = exact_fields(report.get("runtime_fixture"),
                           {"manifest", "inputs_sha256", "library_sha256"}, "runtime_fixture")
    expected_manifest = {
        "schema": 1, "kind": "droidds-runtime-fixture-sources",
        "fixture": "droidds-original-pica-ipc-v1", "library": "libdroidds_fixture_runtime.so",
        "abi": 4, "generation": 3, "native_text_bytes": 492, "fallback_entry": 0x100800,
        "sources": ["code000.c", "entries.c"],
    }
    manifest = exact_fields(fixture["manifest"], set(expected_manifest), "runtime fixture manifest")
    require_values(manifest, expected_manifest)
    hashes = exact_fields(fixture["inputs_sha256"],
                         {"code000.c", "entries.c", "functions.h", "recomp.h", "runtime-fixture.cxi"},
                         "runtime fixture inputs")
    hashes = {name: checked_sha256(value, name) for name, value in hashes.items()}
    fixture_hash = checked_sha256(fixture["library_sha256"], "runtime fixture library")
    elf = report["elf"]
    if fixture_hash != elf[manifest["library"]].get("sha256"):
        raise ValueError("Runtime fixture hash differs from audited ELF")

    # CodexAstraUlt: Full symbol files stay local. Only their hashes, measured
    # sizes and the exact stripping operation are admitted to public evidence.
    symbols = exact_fields(report.get("runtime_symbols"), {
        "unstripped_sha256", "unstripped_bytes", "method", "shipped_sha256", "shipped_bytes",
    }, "runtime_symbols")
    require_values(symbols, {"method": "llvm-strip --strip-debug"})
    for name in ("unstripped_sha256", "shipped_sha256"):
        checked_sha256(symbols[name], name)
    if (any(type(symbols[name]) is not int for name in ("unstripped_bytes", "shipped_bytes"))
            or not 0 < symbols["shipped_bytes"] <= symbols["unstripped_bytes"] <= 128 * 1024 * 1024):
        raise ValueError("Invalid runtime symbol byte counts")
    if symbols["shipped_sha256"] != elf["libdroidds_android_probe.so"].get("sha256"):
        raise ValueError("Runtime symbol hash differs from audited ELF")

    # CodexAstraUlt: Recheck the exact shader inventory in the publishing job as
    # well as preparation. The commit's reviewed source/binary bytes bind these
    # claims; a rebuild difference remains explicit and never replaces a binary.
    shaders = exact_fields(report.get("runtime_shaders"), set(VARIANTS), "runtime_shaders")
    source_root = Path(__file__).resolve().parents[1]
    shader_base = "vendor/zakuro/crates/zakuro-gpu/shaders/"
    shader_fields = {"source", "defines", "source_sha256", "shipped_sha256", "shipped_bytes",
                     "rebuilt_sha256", "byte_identical_rebuild", "validation_environment", "compiler_target"}
    checked_shaders = {}
    for name, (source_name, definitions) in sorted(VARIANTS.items()):
        shader = exact_fields(shaders[name], shader_fields, "runtime shader " + name)
        require_values(shader, {"source": shader_base + source_name, "defines": list(definitions),
                                "validation_environment": "vulkan1.3", "compiler_target": "vulkan1.0/spv1.0"})
        for field in ("source_sha256", "shipped_sha256", "rebuilt_sha256"):
            checked_sha256(shader[field], name + "/" + field)
        source = bounded_file(source_root / shader["source"], 1024 * 1024)
        binary = bounded_file(source_root / (shader_base + name + ".spv"), 1024 * 1024)
        if (shader["source_sha256"] != digest(source) or shader["shipped_sha256"] != digest(binary)
                or type(shader["shipped_bytes"]) is not int or shader["shipped_bytes"] != len(binary)):
            raise ValueError("Runtime shader provenance differs from reviewed source/binary: " + name)
        identical = shader["shipped_sha256"] == shader["rebuilt_sha256"]
        if type(shader["byte_identical_rebuild"]) is not bool or shader["byte_identical_rebuild"] != identical:
            raise ValueError("Runtime shader rebuild identity is inconsistent: " + name)
        checked_shaders[name] = {field: shader[field] for field in sorted(shader_fields)}
    return {
        "runtime_fixture": {"manifest": dict(expected_manifest), "inputs_sha256": hashes,
                            "library_sha256": fixture_hash},
        "runtime_symbols": {field: symbols[field] for field in sorted(symbols)},
        "runtime_shaders": checked_shaders,
    }


def inspect_apk(apk: Path, report: dict, version: str, notices: bytes) -> dict:
    """CodexAstraUlt: Read actual APK identity and contents, not only builder labels."""
    manifest = apk_manifest(apk, allow_prerelease=True)
    require_values(manifest, {"package": "org.droidds.probe", "version_name": version,
                              "debuggable": True, "test_only": False})
    libraries = libraries_for_version(version)
    elf = report.get("elf")
    if not isinstance(elf, dict) or set(elf) != libraries:
        raise ValueError("Release report must audit exactly the version's known ARM64 libraries")
    runtime = runtime_metadata(report, version)
    with zipfile.ZipFile(apk) as archive:
        names = archive.namelist()
        if len(names) != len(set(names)) or any(
                name.startswith("/") or "\\" in name or ".." in name.split("/")
                for name in names):
            raise ValueError("Duplicate or unsafe APK entry")
        allowed = {"AndroidManifest.xml", "resources.arsc", "classes.dex", NOTICE_ENTRY,
                   "assets/THIRD_PARTY_NOTICES.md"} | {"lib/arm64-v8a/" + name for name in libraries}
        # CodexAstraUlt: aapt2 emits a resources.arsc table even for this plain
        # manifest-only application; only that fixed resource-table name joins
        # the allowlist. APK v1 signature entries are optional; no unrelated asset,
        # private title or signing keystore is allowed through the public bundle.
        if any(name not in allowed and not re.fullmatch(
                r"META-INF/[A-Z0-9_-]+\.(SF|RSA|DSA|EC)|META-INF/MANIFEST\.MF", name)
               for name in names):
            raise ValueError("Unexpected APK content")
        if archive.read(NOTICE_ENTRY) != notices:
            raise ValueError("Embedded notices differ from the published notice file")
        for name, audit in elf.items():
            binary = archive.read("lib/arm64-v8a/" + name)
            if (audit.get("machine") != "AArch64" or audit.get("text_relocations") is not False
                    or digest(binary) != audit.get("sha256")):
                raise ValueError(f"APK library differs from audited binary: {name}")
            # CodexAstraUlt: The stripped size is checked against the actual APK,
            # not just another field in the same build report.
            if (runtime and name == "libdroidds_android_probe.so"
                    and len(binary) != runtime["runtime_symbols"]["shipped_bytes"]):
                raise ValueError("Runtime symbol byte count differs from packaged ELF")
    return manifest


def signature(apk: Path, sdk: Path) -> str:
    """CodexAstraUlt: A report's fingerprint cannot substitute for signature verification."""
    tool = sdk / "build-tools" / BUILD_TOOLS_VERSION / "apksigner"
    result = subprocess.run([str(tool), "verify", "--verbose", "--print-certs", str(apk)],
                            check=True, text=True, capture_output=True, timeout=60)
    fingerprints = re.findall(r"^Signer #[0-9]+ certificate SHA-256 digest: ([0-9a-fA-F]{64})$",
                              result.stdout, re.M)
    if len(fingerprints) != 1 or not re.search(r"^Number of signers: 1$", result.stdout, re.M):
        raise ValueError("Expected one verified APK signing certificate")
    return fingerprints[0].lower()


def prepare(build: Path, output: Path, sdk: Path, tag: str, commit: str) -> None:
    """CodexAstraUlt: Export an allowlisted report; exclude commands, logs and key paths."""
    version, apk_name = identity(tag, commit)
    report = json.loads(bounded_file(build / "build-report.json", 8 * 1024 * 1024))
    if not isinstance(report, dict):
        raise ValueError("Build report must be an object")
    require_values(report, {"schema": 1, "kind": "droidds-android-probe-build", "status": "built",
                            "runtime_status": "not_run", "target": "aarch64-linux-android",
                            "minimum_api": 29, "compile_target_api": 35,
                            "distribution": "prerelease", "test_only": False,
                            "debuggable": True, "apk": APK_SOURCE})
    apk = build / APK_SOURCE
    apk_bytes = bounded_file(apk, 128 * 1024 * 1024)
    if report.get("apk_sha256") != digest(apk_bytes) or report.get("apk_bytes") != len(apk_bytes):
        raise ValueError("Signed APK hash or size differs from build evidence")
    notices = bounded_file(build / NOTICE_FILE, 8 * 1024 * 1024)
    if not notices.strip():
        raise ValueError("Third-party notices must not be empty")
    require_values(report.get("third_party_notices", {}), {
        "file": NOTICE_FILE, "sha256": digest(notices), "apk_entry": NOTICE_ENTRY})
    manifest = inspect_apk(apk, report, version, notices)
    if report.get("manifest") != manifest:
        raise ValueError("Builder manifest evidence differs from actual APK")
    certificate = signature(apk, sdk)
    if report.get("signing_certificate_sha256") != certificate:
        raise ValueError("Verified signing certificate differs from build evidence")
    staged_manifest = bounded_file(build / "AndroidManifest.xml", 1024 * 1024)
    if digest(staged_manifest) != report.get("staged_manifest_sha256"):
        raise ValueError("Staged manifest source differs from build evidence")
    # CodexAstraUlt: Public evidence includes measured build facts only; device
    # performance, graphics and real games have not been exercised by this job.
    public = {name: report[name] for name in (
        "schema", "kind", "status", "runtime_status", "target", "minimum_api",
        "compile_target_api", "distribution", "test_only", "debuggable", "apk_sha256",
        "apk_bytes", "signing_certificate_sha256", "staged_manifest_sha256", "elf",
        "third_party_notices")}
    public.update(tag=tag, source_commit=commit, version=version, apk=apk_name,
                  apk_manifest=manifest, device_execution="not_run", graphics_execution="not_run",
                  scope=("Original CPU, Vulkan and 3DS runtime diagnostic; no retail game support"
                         if version == "0.0.5" else
                         "Original synthetic CPU/Vulkan diagnostic probe; no retail game support"))
    # CodexAstraUlt: Preserve offline shader provenance when the build includes
    # Vulkan. Android execution remains untested even after host readback passes.
    if "vulkan_shaders" in report:
        public["vulkan_shaders"] = report["vulkan_shaders"]
    # CodexAstraUlt: Replace unchecked optional nested copying with mandatory .5
    # validation/projection, so missing evidence and private extra fields fail.
    public.update(runtime_metadata(report, version))
    output.mkdir(parents=True, exist_ok=False)
    (output / apk_name).write_bytes(apk_bytes)
    (output / NOTICE_FILE).write_bytes(notices)
    (output / "BUILD_REPORT.json").write_text(json.dumps(public, indent=2, sort_keys=True) + "\n")
    files = [apk_name, "BUILD_REPORT.json", NOTICE_FILE]
    (output / "SHA256SUMS").write_text("".join(
        digest((output / name).read_bytes()) + "  " + name + "\n" for name in sorted(files)))
    verify_bundle(output, tag, commit)


def verify_bundle(bundle: Path, tag: str, commit: str) -> None:
    """CodexAstraUlt: The publish job rechecks the exact same-run artifact allowlist."""
    version, apk_name = identity(tag, commit)
    files = {apk_name, "BUILD_REPORT.json", NOTICE_FILE}
    if {path.name for path in bundle.iterdir()} != files | {"SHA256SUMS"}:
        raise ValueError("Release bundle must contain exactly four allowlisted files")
    checksums = bounded_file(bundle / "SHA256SUMS", 1024 * 1024).decode("ascii")
    expected = "".join(digest(bounded_file(bundle / name, 128 * 1024 * 1024)) + "  " + name + "\n"
                       for name in sorted(files))
    if checksums != expected:
        raise ValueError("Release bundle checksum mismatch")
    report = json.loads(bounded_file(bundle / "BUILD_REPORT.json", 8 * 1024 * 1024))
    require_values(report, {"tag": tag, "source_commit": commit, "version": version,
                            "apk": apk_name, "status": "built", "runtime_status": "not_run",
                            "device_execution": "not_run", "graphics_execution": "not_run",
                            "distribution": "prerelease", "test_only": False, "debuggable": True})
    apk = bounded_file(bundle / apk_name, 128 * 1024 * 1024)
    if digest(apk) != report.get("apk_sha256") or len(apk) != report.get("apk_bytes"):
        raise ValueError("Bundle APK differs from release report")
    notices = bounded_file(bundle / NOTICE_FILE, 8 * 1024 * 1024)
    require_values(report.get("third_party_notices", {}), {
        "file": NOTICE_FILE, "sha256": digest(notices), "apk_entry": NOTICE_ENTRY})
    manifest = inspect_apk(bundle / apk_name, report, version, notices)
    if report.get("apk_manifest") != manifest:
        raise ValueError("Bundled manifest evidence differs from actual APK")


def main() -> int:
    """CodexAstraUlt: Explicit paths and identities support local and tag-triggered CI."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--build", type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--sdk", type=Path)
    parser.add_argument("--verify-bundle", type=Path)
    parser.add_argument("--tag", required=True)
    parser.add_argument("--commit", required=True)
    args = parser.parse_args()
    try:
        if args.verify_bundle:
            verify_bundle(args.verify_bundle, args.tag, args.commit)
        elif args.build and args.output and args.sdk:
            prepare(args.build, args.output, args.sdk, args.tag, args.commit)
        else:
            parser.error("Use --verify-bundle or all of --build, --output and --sdk")
        return 0
    except (ValueError, KeyError, OSError, subprocess.SubprocessError, zipfile.BadZipFile) as error:
        print(f"Probe release preparation failed: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
