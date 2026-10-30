#!/usr/bin/env python3
"""CodexAstraUlt: Publish only the reviewed original interactive title candidate."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import tempfile
import zipfile

import build_android_title as BUILD
from prepare_probe_release import bounded_file, exact_fields, require_values, signature


# CodexAstraUlt: This release policy intentionally admits one authored input,
# not arbitrary title packages bearing a diagnostic flag or familiar program ID.
TAG = "v0.0.7-preview.2"
VERSION = "0.0.7-preview.2"
PROGRAM = "000400000d5d0006"
APK_SOURCE = "droidds-title.apk"
APK_NAME = "DroiDDS-0.0.7-preview.2-original-android-arm64.apk"
NOTICE = "THIRD_PARTY_NOTICES.txt"
INPUT = {"bytes": 30720, "sha256": "efbf68988056b7973f14b934d792d87af430a15e7549cdf3a022e261b9aecbfd"}
MIB = 1024 * 1024
MAX_APK = 128 * MIB
PACKAGE = "org.droidds.title.t" + PROGRAM
MANIFEST = {"package": PACKAGE, "version_code": 9, "version_name": VERSION,
            "debuggable": True, "test_only": False, "minimum_api": 29, "target_api": 35}
PREPARED = {
    "container": "ncch", "ncch_format_version": 0, "remaster_version": 0,
    "cia_title_version": None, "bss_size": 0,
    "components": [
        {"kind": "decompressed_code", "path": "identity/code.bin", "bytes": 28672,
         "sha256": "f2898dee9bd6a54aa0465085d967103f4e00b07932c9eaff3ad263deda55e871"},
        {"kind": "exheader", "path": "identity/exheader.bin", "bytes": 1024,
         "sha256": "7bc671622bcb0dabc2d0c9e4e93c7cb9e0b06e2e6d218f50c7576d3d3a29c080"},
        {"kind": "ncch_header", "path": "identity/ncch-header.bin", "bytes": 512,
         "sha256": "0b2606708831e2b9599c894fd7b72671a3cfc51195f6ea9ff6fd42b494d02723"},
    ],
    "segments": [
        {"name": "text", "address": 1048576, "offset": 0, "size": 8192, "mapped_bytes": 8192,
         "hash_scope": "logical_segment_bytes", "sha256": "c9f10a7653727f12d1e669b953e1fd58546bb4077e31f383f233722451c05d2a"},
        {"name": "rodata", "address": 1056768, "offset": 8192, "size": 16384, "mapped_bytes": 16384,
         "hash_scope": "logical_segment_bytes", "sha256": "79b2df2cc230d1b9fcff86bcc7dfdd98e6e3e6f9b06f25375808b3b67c573c30"},
        {"name": "data", "address": 1073152, "offset": 24576, "size": 4096, "mapped_bytes": 4096,
         "hash_scope": "logical_segment_bytes", "sha256": "ad7facb2586fc6e966c004d7d1d16b024f5805ff7cb47c7a85dabd8b48892ca7"},
    ],
}
PUBLIC_FIELDS = {
    "schema_version", "kind", "status", "tag", "version", "source_commit", "source_inventory_sha256",
    "apk", "apk_identity", "manifest", "title_manifest", "original_fixture", "elf",
    "signing_certificate_sha256", "third_party_notices", "device_execution", "retail_boot",
    "distribution", "scope",
}


def require(condition, message):
    """CodexAstraUlt: Rejections use bounded categories rather than input contents."""
    if not condition:
        raise ValueError(message)


def digest(data):
    return hashlib.sha256(data).hexdigest()


def measured(data):
    return {"bytes": len(data), "sha256": digest(data)}


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()


def identity(tag, commit):
    """CodexAstraUlt: A later release needs an explicit reviewed policy update."""
    require(tag == TAG and type(commit) is str and re.fullmatch(r"[0-9a-f]{40}", commit),
            "Expected reviewed preview tag and full lowercase source commit")
    return VERSION, APK_NAME


def source_commit(commit):
    """CodexAstraUlt: Public source labels must identify this exact clean checkout."""
    def git(*arguments):
        return subprocess.run(["git", "-C", str(BUILD.ROOT), *arguments], check=True,
                              text=True, capture_output=True, timeout=30).stdout.strip()
    require(git("rev-parse", "HEAD") == commit, "Release source commit differs from checkout HEAD")
    require(not git("status", "--porcelain=v1", "--untracked-files=all"),
            "Release preparation requires a clean committed checkout")


def json_object(data):
    """CodexAstraUlt: Duplicate fields cannot hide a different publication policy."""
    def unique(pairs):
        result = {}
        for key, value in pairs:
            require(key not in result, "Duplicate release JSON field")
            result[key] = value
        return result
    result = json.loads(data, object_pairs_hook=unique)
    require(type(result) is dict, "Release JSON must be an object")
    return result


def same(actual, expected, label):
    """CodexAstraUlt: Canonical comparison also distinguishes true from integer 1."""
    require(canonical(actual) == canonical(expected), "Release identity mismatch: " + label)


def producer_sources():
    """CodexAstraUlt: Producer provenance is recomputed from this reviewed checkout."""
    result = {}
    for name in ("droidds-runtime-probe", "droidds-title-builder"):
        directory = BUILD.ROOT / "crates" / name
        for path in sorted([directory / "Cargo.toml", *directory.rglob("*.rs")]):
            result[path.relative_to(BUILD.ROOT).as_posix()] = digest(bounded_file(path, 4 * MIB))
    return result


def original_proof(value):
    """CodexAstraUlt: Do not project unchecked nested metadata into a public report."""
    expected = {"fixture": "droidds-original-homebrew-v1", "producer": "droidds-runtime-probe",
                "action": "emit-homebrew", "input": INPUT, "producer_sources": producer_sources()}
    same(value, expected, "original producer proof")
    return expected


def title_manifest(value, native):
    """CodexAstraUlt: Every public component/layout field belongs to the fixed fixture."""
    expected = {"schema_version": 1, "kind": "droidds_android_title", "program_id": PROGRAM,
                "input": INPUT, "native": {"file": "libdroidds_title.so", **native},
                "abi": 4, "generation": 3, "prepared": PREPARED}
    same(value, expected, "original title manifest")
    return expected


def sdk_manifest(apk, sdk):
    """CodexAstraUlt: Read the actual compiled manifest in both release stages."""
    tool = sdk / "build-tools" / BUILD.BUILD_TOOLS_VERSION / "aapt2"
    def run(arguments):
        return subprocess.run([str(tool), *arguments], check=True, text=True, capture_output=True,
                              timeout=30).stdout
    return BUILD.audit_manifest(run(["dump", "badging", str(apk)]),
        run(["dump", "xmltree", str(apk), "--file", "AndroidManifest.xml"]),
        PACKAGE, MANIFEST["version_code"], MANIFEST["debuggable"])


def elf_metadata(data):
    """CodexAstraUlt: Decode shipped ELF headers/dependencies without loading code."""
    with tempfile.TemporaryDirectory(prefix="droidds-public-elf-") as temporary:
        path = Path(temporary) / "library.so"
        path.write_bytes(data)
        result = subprocess.run(["readelf", "-W", "-h", "-l", "-d", str(path)],
                                env=os.environ | {"LC_ALL": "C"}, check=True, text=True,
                                capture_output=True, timeout=30)
    return BUILD.audit_elf(result.stdout, BUILD.LIBRARIES) | measured(data)


def inspect_apk(apk, sdk, notices, report):
    """CodexAstraUlt: Inspect archive bytes before trusting the builder's evidence."""
    same(sdk_manifest(apk, sdk), MANIFEST, "compiled Android manifest")
    same(report["manifest"], MANIFEST, "reported Android manifest")
    with zipfile.ZipFile(apk) as archive:
        infos = archive.infolist()
        names = [info.filename for info in infos]
        required = {"AndroidManifest.xml", "classes.dex", "assets/title-manifest.json",
                    "assets/original-title.cxi", "assets/THIRD_PARTY_NOTICES.txt", "assets/THIRD_PARTY_NOTICES.md"}
        required |= {"lib/arm64-v8a/" + name for name in BUILD.LIBRARIES}
        allowed = required | {"resources.arsc"}
        require(len(names) == len(set(names)) and required <= set(names), "Missing or duplicate APK entry")
        require(all(name in allowed or re.fullmatch(
            r"META-INF/[A-Z0-9_-]+\.(SF|RSA|DSA|EC)|META-INF/MANIFEST\.MF", name) for name in names),
            "Unexpected APK content")
        require(sum(info.file_size for info in infos) <= 192 * MIB and all(
            info.file_size <= (96 * MIB if info.filename.startswith("lib/") else 8 * MIB)
            and not info.flag_bits & 1 for info in infos), "Oversized or encrypted APK entry")
        same(measured(archive.read("assets/original-title.cxi")), INPUT, "original image")
        require(archive.read("assets/THIRD_PARTY_NOTICES.txt") == notices, "Embedded notices differ")
        require(archive.read("assets/THIRD_PARTY_NOTICES.md") ==
                bounded_file(BUILD.ROOT / "THIRD_PARTY_NOTICES.md", 8 * MIB), "Source notices changed")
        elf = {name: elf_metadata(archive.read("lib/arm64-v8a/" + name)) for name in sorted(BUILD.LIBRARIES)}
        same(report["elf"], elf, "audited packaged libraries")
        native = {key: elf["libdroidds_title.so"][key] for key in ("bytes", "sha256")}
        manifest_bytes = archive.read("assets/title-manifest.json")
        require(len(manifest_bytes) <= MIB, "Title manifest exceeds bound")
        manifest = title_manifest(json_object(manifest_bytes), native)
        same(report["title_manifest"], manifest, "reported title manifest")
    # CodexAstraUlt: Reuse the packager's stored/native ZIP alignment checks;
    # its library list is this candidate's separate three-library inventory.
    BUILD.audit_zip(apk, {name: {key: value[key] for key in ("bytes", "sha256")}
                         for name, value in elf.items()}, manifest_bytes, INPUT)
    certificate = signature(apk, sdk)
    same(report["signing_certificate_sha256"], certificate, "verified APK signer")
    return manifest, elf, certificate


def prepare(build, output, sdk, tag, commit):
    """CodexAstraUlt: Export measured allowlisted facts; keep local build logs private."""
    identity(tag, commit)
    source_commit(commit)
    report = json_object(bounded_file(build / "build-report.json", 8 * MIB))
    require_values(report, {"schema_version": 1, "kind": "droidds_android_title_build", "status": "built",
        "version": VERSION, "device_execution": "not_run", "apk": APK_SOURCE,
        "diagnostic_signing": True, "preserved_inputs_verified": True})
    proof = original_proof(report.get("original_fixture"))
    same(report.get("source"), BUILD.source_identity(), "builder source inventory")
    apk = build / APK_SOURCE
    apk_bytes = bounded_file(apk, MAX_APK)
    same(report.get("apk_identity"), measured(apk_bytes), "built APK")
    notices = bounded_file(build / NOTICE, 8 * MIB)
    require(bool(notices.strip()), "Empty notices")
    manifest, elf, certificate = inspect_apk(apk, sdk, notices, report)
    public = {
        "schema_version": 1, "kind": "droidds_original_title_prerelease", "status": "built",
        "tag": tag, "version": VERSION, "source_commit": commit,
        "source_inventory_sha256": digest(canonical(report["source"])), "apk": APK_NAME,
        "apk_identity": measured(apk_bytes), "manifest": MANIFEST, "title_manifest": manifest,
        "original_fixture": proof, "elf": elf, "signing_certificate_sha256": certificate,
        "third_party_notices": {"file": NOTICE, **measured(notices)},
        "device_execution": "not_run", "retail_boot": "not_qualified", "distribution": "diagnostic-original",
        "scope": "Original interactive guest through generic Android title path; device and retail qualification pending",
    }
    output.mkdir(parents=True, exist_ok=False)
    (output / APK_NAME).write_bytes(apk_bytes)
    (output / NOTICE).write_bytes(notices)
    (output / "BUILD_REPORT.json").write_bytes(json.dumps(public, indent=2, sort_keys=True).encode() + b"\n")
    files = sorted((APK_NAME, NOTICE, "BUILD_REPORT.json"))
    (output / "SHA256SUMS").write_text("".join(digest((output / name).read_bytes()) + "  " + name + "\n"
                                               for name in files))
    verify_bundle(output, sdk, tag, commit)


def verify_bundle(bundle, sdk, tag, commit):
    """CodexAstraUlt: Downloaded artifacts must repeat signature/content/source checks."""
    identity(tag, commit)
    source_commit(commit)
    files = {APK_NAME, NOTICE, "BUILD_REPORT.json"}
    require({path.name for path in bundle.iterdir()} == files | {"SHA256SUMS"}, "Expected exactly four public assets")
    expected = "".join(digest(bounded_file(bundle / name, MAX_APK)) + "  " + name + "\n" for name in sorted(files))
    same(bounded_file(bundle / "SHA256SUMS", 4096).decode("ascii"), expected, "bundle checksums")
    report = exact_fields(json_object(bounded_file(bundle / "BUILD_REPORT.json", 8 * MIB)), PUBLIC_FIELDS, "public report")
    require_values(report, {"schema_version": 1, "kind": "droidds_original_title_prerelease", "status": "built",
        "tag": tag, "version": VERSION, "source_commit": commit, "apk": APK_NAME,
        "device_execution": "not_run", "retail_boot": "not_qualified", "distribution": "diagnostic-original",
        "scope": "Original interactive guest through generic Android title path; device and retail qualification pending"})
    same(report["source_inventory_sha256"], digest(canonical(BUILD.source_identity())), "release source inventory")
    original_proof(report["original_fixture"])
    apk = bundle / APK_NAME
    same(report["apk_identity"], measured(bounded_file(apk, MAX_APK)), "bundle APK")
    notices = bounded_file(bundle / NOTICE, 8 * MIB)
    same(report["third_party_notices"], {"file": NOTICE, **measured(notices)}, "bundle notices")
    inspect_apk(apk, sdk, notices, report)


def main():
    """CodexAstraUlt: Build/publish stages share the same explicit verification entry."""
    parser = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--build", type=Path)
    mode.add_argument("--verify-bundle", type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--sdk", type=Path, required=True)
    parser.add_argument("--tag", required=True)
    parser.add_argument("--commit", required=True)
    args = parser.parse_args()
    if args.build is not None:
        if args.output is None:
            parser.error("--build requires --output")
        prepare(args.build, args.output, args.sdk, args.tag, args.commit)
    else:
        if args.output is not None:
            parser.error("--output is only valid with --build")
        verify_bundle(args.verify_bundle, args.sdk, args.tag, args.commit)
    print("Verified four original-title prerelease assets; device qualification remains pending.")


if __name__ == "__main__":
    main()
