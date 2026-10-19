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

APK_SOURCE = "droidds-android-probe-prerelease.apk"
NOTICE_FILE = "THIRD_PARTY_NOTICES.txt"
NOTICE_ENTRY = "assets/THIRD_PARTY_NOTICES.txt"
BUILD_TOOLS_VERSION = "35.0.0"
TAG_PATTERN = r"v(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)-probe\.([1-9][0-9]*)"
def libraries_for_version(version: str) -> set[str]:
    """CodexAstraUlt: Bind every release's packaged code to its exact fixture set."""
    return {"libdroidds_android_probe.so", "libdroidds_probe_jni.so"} | {
        "libdds_fixture_" + name + ".so" for name in cases_for_version(version)}


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


def inspect_apk(apk: Path, report: dict, version: str, notices: bytes) -> dict:
    """CodexAstraUlt: Read actual APK identity and contents, not only builder labels."""
    manifest = apk_manifest(apk, allow_prerelease=True)
    require_values(manifest, {"package": "org.droidds.probe", "version_name": version,
                              "debuggable": True, "test_only": False})
    libraries = libraries_for_version(version)
    elf = report.get("elf")
    if not isinstance(elf, dict) or set(elf) != libraries:
        raise ValueError("Release report must audit exactly the version's known ARM64 libraries")
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
            if (audit.get("machine") != "AArch64" or audit.get("text_relocations") is not False
                    or digest(archive.read("lib/arm64-v8a/" + name)) != audit.get("sha256")):
                raise ValueError(f"APK library differs from audited binary: {name}")
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
                  scope="Original synthetic CPU/Vulkan diagnostic probe; no retail game support")
    # CodexAstraUlt: Preserve offline shader provenance when the build includes
    # Vulkan. Android execution remains untested even after host readback passes.
    if "vulkan_shaders" in report:
        public["vulkan_shaders"] = report["vulkan_shaders"]
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
