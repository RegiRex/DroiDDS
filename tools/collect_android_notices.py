#!/usr/bin/env python3
"""CodexAstraUlt: Assemble the probe's supplied notices from its locked build inputs."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys
import tomllib

ROOT = Path(__file__).resolve().parents[1]
NDK_VERSION = "27.3.13750724"
RECOMP_REV = "c3f21f94ba50d688025febc8974ff348d471b587"
ZAKURO_REV = "412900a5a020301da15c1cc382585e05a489a535"

# CodexAstraUlt: Vulkan's core API includes these seven video declaration
# headers even though the probe performs no video work. Require each pinned
# header so a missing input cannot silently disappear from the notice bundle.
VULKAN_HEADERS = (
    "vulkan/vulkan.h", "vulkan/vulkan_core.h", "vulkan/vk_platform.h",
    "vk_video/vulkan_video_codecs_common.h",
    "vk_video/vulkan_video_codec_h264std.h",
    "vk_video/vulkan_video_codec_h264std_decode.h",
    "vk_video/vulkan_video_codec_h264std_encode.h",
    "vk_video/vulkan_video_codec_h265std.h",
    "vk_video/vulkan_video_codec_h265std_decode.h",
    "vk_video/vulkan_video_codec_h265std_encode.h",
)
NDK_INCLUDE = Path("toolchains/llvm/prebuilt/linux-x86_64/sysroot/usr/include")

# CodexAstraUlt: The runtime graph contains multiple versions of several crates.
# Replace the CPU-only name set with reviewed identities, archive checksums and
# supplied notice hashes; no newly resolved package is silently accepted.
INVENTORY = json.loads((ROOT / "tools/android_registry_notices.json").read_text())
REGISTRY_SOURCE = "registry+https://github.com/rust-lang/crates.io-index"
if INVENTORY["schema"] != 1 or INVENTORY["registry"] != REGISTRY_SOURCE:
    raise ValueError("Unrecognized registry notice inventory")
REGISTRY_NOTICES = {(entry["name"], entry["version"]): entry
                    for entry in INVENTORY["packages"]}
if len(REGISTRY_NOTICES) != len(INVENTORY["packages"]):
    raise ValueError("Duplicate registry notice identity")
VENDORED_PACKAGES = {"zakuro-core", "zakuro-fs", "zakuro-gpu"}
# CodexAstraUlt: The measured backward-loop discovery fix requires a maintained
# host compiler, while the loaded ABI remains the exact original Git package.
LOCAL_UPSTREAM_PACKAGES = VENDORED_PACKAGES | {"recomp3ds"}
GIT_PACKAGES = {"recomp-abi", "zakuro-cpu", "zakuro-common"}

# CodexAstraUlt: 3dsrecomp explicitly declares SPDX MIT but supplies no license
# file or copyright notice. Reproduce the standard permission/warranty terms,
# without borrowing Zakuro's copyright line or inventing an upstream notice.
MIT_TERMS = '''MIT License

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
'''


def command(argv: list[str]) -> str:
    """CodexAstraUlt: Read selected toolchain metadata without shell evaluation."""
    return subprocess.run(argv, cwd=ROOT, check=True, text=True,
                          stdout=subprocess.PIPE, timeout=300).stdout.strip()


def supplied_file(path: Path, label: str, expected_sha256: str | None = None) -> str:
    """CodexAstraUlt: Preserve every supplied character and identify its bytes."""
    data = path.read_bytes()
    if not data.strip():
        raise ValueError(f"Empty notice: {label}")
    if expected_sha256 is not None and hashlib.sha256(data).hexdigest() != expected_sha256:
        raise ValueError(f"Changed reviewed notice: {label}")
    return (f"\n----- BEGIN {label} -----\n"
            f"Original file SHA-256: {hashlib.sha256(data).hexdigest()}\n\n"
            + data.decode("utf-8") + f"\n----- END {label} -----\n")


def header_notice(path: Path, label: str) -> str:
    """CodexAstraUlt: Preserve actual attribution without copying API declarations."""
    data = path.read_bytes()
    block = next((part for part in re.findall(rb"/\*.*?\*/", data, re.S)
                  if re.search(rb"copyright", part, re.I)), None)
    if block is None:
        raise ValueError(f"Missing copyright comment: {label}")
    declarations = [value.strip() for value in
                    re.findall(rb"SPDX-License-Identifier:\s*([^\r\n*]+)", block)]
    if declarations != [b"Apache-2.0"]:
        raise ValueError(f"Changed Vulkan header license: {label}")
    return (f"\n----- BEGIN {label} copyright comment -----\n"
            f"Original full header SHA-256: {hashlib.sha256(data).hexdigest()}\n\n"
            + block.decode("utf-8")
            + f"\n----- END {label} copyright comment -----\n")


def vulkan_notices(ndk: Path) -> str:
    """CodexAstraUlt: Retain the actual API-header notices omitted by older NDK summaries."""
    includes = ndk / NDK_INCLUDE
    # CodexAstraUlt: Require the reviewed core/video set, while conservatively
    # retaining any additional supplied video header's attribution as well.
    headers = set(VULKAN_HEADERS) | {
        str(path.relative_to(includes)) for path in (includes / "vk_video").glob("*.h")
    }
    return ("\nVulkan API headers from the pinned Android NDK follow. These are the\n"
            "verbatim first copyright comments; full header hashes identify the\n"
            "inputs without reproducing API declarations. Full Apache-2.0 terms\n"
            "are retained above in the supplied LICENSE-APACHE files. Video API\n"
            "declarations are transitive core-header inputs, not probe features.\n"
            + "".join(header_notice(includes / relative, f"Android NDK/{relative}")
                      for relative in sorted(headers)))


def registry_section(package: dict) -> str:
    """CodexAstraUlt: Retain compound licenses, original files and attribution."""
    key = package["name"], package["version"]
    if key not in REGISTRY_NOTICES:
        raise ValueError(f"Unreviewed registry dependency: {key}")
    entry = REGISTRY_NOTICES[key]
    if package["source"] != REGISTRY_SOURCE or package["license"] != entry["license"]:
        raise ValueError(f"Changed license or source declaration: {key}")
    base = Path(package["manifest_path"]).parent
    identity = " ".join(key)
    result = (f"\nPackage: {identity}\nDeclared license: {entry['license']}\n"
              f"Source: {package['source']}\n"
              f"Source archive: https://static.crates.io/crates/{key[0]}/{key[0]}-{key[1]}.crate\n"
              f"Source archive SHA-256: {entry['checksum']}\n")
    if entry["license"] == "MPL-2.0":
        # CodexAstraUlt: Tell executable recipients exactly how to obtain the
        # unmodified covered sources under MPL, not just where the project lives.
        result += ("This component is distributed under Mozilla Public License 2.0.\n"
                   "Its complete, unmodified Source Code Form is available without charge\n"
                   "at the source archive URL above, with its license and attribution intact.\n"
                   "DroidDS makes no changes to this registry component.\n")
    for filename, digest in entry["files"].items():
        result += supplied_file(base / filename, f"{identity}/{filename}", digest)
    for filename, digest in entry["source_comments"].items():
        result += source_comments(base / filename, f"{identity}/{filename}", digest)
    if entry.get("declaration_only") == "MIT":
        result += supplied_file(base / "Cargo.toml", f"{identity}/Cargo.toml")
        result += ("\nThis registry archive declares MIT but supplies no standalone license\n"
                   "or copyright notice. These standard MIT terms reproduce that declaration;\n"
                   "they are not an upstream-supplied notice. No copyright holder is inferred.\n"
                   + MIT_TERMS)
    for extra in entry.get("supplemental_files", []):
        result += f"\nSupplemental notice source: {extra['source']}\n{extra['reason']}\n"
        result += supplied_file(ROOT / extra["file"], extra["file"], extra["sha256"])
    return result


def source_comments(path: Path, label: str, expected_sha256: str) -> str:
    """CodexAstraUlt: Retain inline notices, including libm's BSD/Sun/Arm terms."""
    data = path.read_bytes()
    if hashlib.sha256(data).hexdigest() != expected_sha256:
        raise ValueError(f"Changed attribution source: {label}")
    comments = re.findall(rb"/\*.*?\*/|(?m:^[ \t]*//[^\n]*(?:\n[ \t]*//[^\n]*)*)", data, re.S)
    notices = [block for block in comments if re.search(
        rb"copyright|permission is hereby|redistribution and use", block, re.I)]
    if not notices:
        raise ValueError(f"Missing reviewed source attribution: {label}")
    return (f"\n----- BEGIN {label} supplied attribution comments -----\n"
            f"Original full source SHA-256: {expected_sha256}\n\n"
            + "\n\n".join(block.decode("utf-8") for block in notices)
            + f"\n----- END {label} supplied attribution comments -----\n")


def vendor_section(package: dict, emitted: set[str]) -> str:
    """CodexAstraUlt: Local dependency paths must not hide copied upstream code."""
    name = package["name"]
    vendor = ROOT / "vendor/zakuro"
    manifest = vendor / "crates" / name / "Cargo.toml"
    if (name not in VENDORED_PACKAGES or package["source"] is not None
            or package["license"] != "MIT" or package["version"] != "0.2.27"
            or Path(package["manifest_path"]).resolve() != manifest.resolve()):
        raise ValueError(f"Changed vendored package identity: {name}")
    origin = json.loads((vendor / "UPSTREAM.json").read_text())
    if (origin.get("schema") != 1 or origin.get("revision") != ZAKURO_REV
            or origin.get("repository") != "https://github.com/fearkov/zakuro"):
        raise ValueError("Changed vendored Zakuro origin")
    license_digest = hashlib.sha256((vendor / "LICENSE").read_bytes()).hexdigest()
    if license_digest != origin["files"]["LICENSE"]:
        raise ValueError("Changed vendored Zakuro license")
    result = (f"\nPackage: {name} {package['version']}\nDeclared license: MIT\n"
              f"Source: https://github.com/fearkov/zakuro/tree/{ZAKURO_REV}\n"
              f"DroidDS maintained copy: vendor/zakuro/crates/{name}\n"
              "Integration changes are marked CodexAstraUlt; original attribution is retained.\n"
              "The DroidDS release source contains the maintained copy and UPSTREAM.json.\n")
    if "zakuro" not in emitted:
        result += supplied_file(vendor / "LICENSE", "Zakuro/LICENSE", license_digest)
        emitted.add("zakuro")
    return result


def compiler_section(package: dict, emitted: set[str]) -> str:
    """CodexAstraUlt: Preserve compiler/generated-support terms after the local fix."""
    directory = ROOT / "vendor/3dsrecomp"
    if (package["name"] != "recomp3ds" or package["source"] is not None
            or package["version"] != "0.1.0" or package["license"] != "MIT"
            or Path(package["manifest_path"]).resolve() != (directory / "Cargo.toml").resolve()):
        raise ValueError("Changed maintained compiler identity")
    origin = json.loads((directory / "UPSTREAM.json").read_text())
    manifest = origin.get("manifest_provenance", {})
    if (origin.get("repository") != "https://github.com/fearkov/3dsrecomp"
            or origin.get("revision") != RECOMP_REV or origin.get("license") != "MIT"
            or manifest.get("file") != "UPSTREAM-Cargo.toml" or manifest.get("upstream_path") != "Cargo.toml"
            or not re.fullmatch(r"[a-f0-9]{64}", manifest.get("sha256", ""))):
        raise ValueError("Changed maintained compiler origin or manifest provenance")
    original = directory / "UPSTREAM-Cargo.toml"
    if tomllib.loads(original.read_text())["package"]["license"] != "MIT":
        raise ValueError("Original compiler manifest no longer declares MIT")
    result = ("\nPackage: recomp3ds 0.1.0\nDeclared license: MIT\n"
              f"Source: https://github.com/fearkov/3dsrecomp/tree/{RECOMP_REV}\n"
              "DroidDS maintained copy: vendor/3dsrecomp\n"
              "The host compiler is not packaged; its generated support code is included.\n"
              "Local discovery fixes are marked CodexAstraUlt; original provenance is retained.\n"
              + supplied_file(original, "3dsrecomp/original-Cargo.toml", manifest["sha256"]))
    if "3dsrecomp" not in emitted:
        result += ("\nThe original manifest explicitly declares SPDX MIT; this revision supplies\n"
                   "no standalone license or copyright notice. These standard terms reproduce\n"
                   "that declaration and are not an upstream-supplied notice file.\n"
                   "No copyright holder or year is inferred.\n" + MIT_TERMS)
        emitted.add("3dsrecomp")
    return result


def git_section(package: dict, emitted: set[str]) -> str:
    """CodexAstraUlt: Bind exceptional upstream notice handling to exact sources."""
    name, source = package["name"], package["source"]
    manifest = Path(package["manifest_path"])
    if name == "recomp-abi":
        expected = f"git+https://github.com/fearkov/3dsrecomp?rev={RECOMP_REV}#{RECOMP_REV}"
    elif name in {"zakuro-cpu", "zakuro-common"}:
        expected = f"git+https://github.com/fearkov/zakuro?rev={ZAKURO_REV}#{ZAKURO_REV}"
    else:
        raise ValueError(f"Unreviewed Git dependency: {name}")
    if source != expected or package["license"] != "MIT":
        raise ValueError(f"Changed Git source or license declaration: {name}")
    result = (f"\nPackage: {name} {package['version']}\nDeclared license: MIT\n"
              f"Source: {source}\n")
    if name == "recomp-abi":
        result += supplied_file(manifest, f"3dsrecomp/{name}/Cargo.toml")
        if "3dsrecomp" not in emitted:
            result += ("\nThe upstream manifests explicitly declare SPDX MIT. No upstream\n"
                       "LICENSE/NOTICE/COPYING file or copyright notice was supplied at\n"
                       "this revision. The following standard MIT terms reproduce that\n"
                       "declaration; they are not an upstream-supplied notice file. No\n"
                       "copyright holder or copyright year has been inferred.\n\n"
                       + MIT_TERMS)
            emitted.add("3dsrecomp")
    elif "zakuro" not in emitted:
        base = Path(command(["git", "-C", str(manifest.parent), "rev-parse", "--show-toplevel"]))
        result += supplied_file(base / "LICENSE", "Zakuro/LICENSE")
        emitted.add("zakuro")
    return result


def assemble(metadata: dict, ndk: Path, sysroot: Path, rust_version: str) -> str:
    """CodexAstraUlt: Include conservative build provenance without asserting linkage."""
    if not rust_version.startswith("rustc 1.95.0 "):
        raise ValueError("Notices must come from pinned Rust 1.95.0")
    properties = (ndk / "source.properties").read_text()
    if not any(line.strip() == f"Pkg.Revision = {NDK_VERSION}" for line in properties.splitlines()):
        raise ValueError("Notices must come from pinned NDK " + NDK_VERSION)
    packages = sorted(metadata["packages"], key=lambda item: (item["name"], item["version"]))
    third_party = [package for package in packages
                   if package["source"] or package["name"] in LOCAL_UPSTREAM_PACKAGES]
    registry = [package for package in third_party
                if (package["source"] or "").startswith("registry+")]
    registry_keys = {(package["name"], package["version"]) for package in registry}
    nonregistry = [package for package in third_party if package not in registry]
    names = {package["name"] for package in nonregistry}
    if (registry_keys != set(REGISTRY_NOTICES) or len(registry_keys) != len(registry)
            or names != GIT_PACKAGES | LOCAL_UPSTREAM_PACKAGES or len(names) != len(nonregistry)):
        raise ValueError("Resolved package inventory changed; review notices before release")
    # CodexAstraUlt: Check archive identity as well as names/licenses. Cargo's
    # locked fetch validates archive integrity; these pins force notice review
    # when a dependency version or checksum changes.
    locked_registry = {(package["name"], package["version"]): package
                       for package in tomllib.loads((ROOT / "Cargo.lock").read_text())["package"]
                       if (package.get("source") or "").startswith("registry+")}
    # CodexAstraUlt: Cargo.lock also records disabled optional graphs (such as
    # Cranelift). They are not metadata/build inputs until enabled; activation
    # still changes registry_keys and fails the exact reviewed graph above.
    if not registry_keys <= set(locked_registry) or any(
            locked_registry[key]["source"] != REGISTRY_SOURCE
            or locked_registry[key]["checksum"] != entry["checksum"]
            for key, entry in REGISTRY_NOTICES.items()):
        raise ValueError("Locked registry archive inventory changed; review notices before release")
    emitted: set[str] = set()
    output = ["DroidDS Android runtime probe - third-party notices\n\n",
              "CodexAstraUlt: Generated from locked fetched sources and the build's toolchain.\n",
              "This preserves all resolved Cargo dependency notices, including host-only,\n",
              "procedural-macro and other-target packages. Inclusion does not assert that\n",
              "every package is linked into the APK. The generated ARM/Thumb fixtures are\n",
              "original DroidDS synthetic code; 3dsrecomp's generated support code is\n",
              "covered by its declared MIT terms. No retail game data is distributed.\n\n",
              "The APK contains Zakuro CPU/common plus maintained core/filesystem/GPU copies,\n",
              "recomp-abi and their enabled dependencies,\n",
              "plus Rust runtime support, NDK-linked support and original DroidDS code.\n",
              "It does not bundle the host 3dsrecomp executable, NDK tools, Rust compiler,\n",
              "Android framework implementations, or Azahar/MMJ/Uberhar/AnyPS5 code.\n",
              "Android's system shared libraries are supplied by the device.\n\n",
              f"Rust: {rust_version}\nNDK: {NDK_VERSION}\n",
              f"Cargo.lock SHA-256: {hashlib.sha256((ROOT / 'Cargo.lock').read_bytes()).hexdigest()}\n"]
    for package in third_party:
        if package["source"] is None:
            output.append(compiler_section(package, emitted) if package["name"] == "recomp3ds"
                          else vendor_section(package, emitted))
        elif package["source"].startswith("registry+"):
            output.append(registry_section(package))
        elif package["source"].startswith("git+"):
            output.append(git_section(package, emitted))
        else:
            raise ValueError(f"Unreviewed package source: {package['name']}")
    # CodexAstraUlt: Rust supplies a runtime-specific, self-contained copyright
    # record. Keep its original HTML intact, including all exceptions/licenses;
    # the much larger compiler-only copyright inventory is not an APK input.
    output.append("\nRust Standard Library supplied notice follows as verbatim HTML.\n")
    output.append(supplied_file(sysroot / "share/doc/rust/COPYRIGHT-library.html",
                               "Rust/COPYRIGHT-library.html"))
    # CodexAstraUlt: These broad supplied NDK notices cover CRT/runtime support
    # and retain exception text without claiming unrelated SDK code is bundled.
    for relative in ("NOTICE", "NOTICE.toolchain", "toolchains/llvm/prebuilt/linux-x86_64/NOTICE"):
        output.append(supplied_file(ndk / relative, f"Android NDK/{relative}"))
    output.append(vulkan_notices(ndk))
    return "".join(output)


def main() -> int:
    """CodexAstraUlt: Fail closed before packaging if a required notice is absent."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ndk", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    try:
        metadata = json.loads(command(["cargo", "metadata", "--locked", "--format-version", "1"]))
        sysroot = Path(command(["rustc", "--print", "sysroot"]))
        text = assemble(metadata, args.ndk.resolve(), sysroot, command(["rustc", "--version"]))
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text, encoding="utf-8")
        count = sum(bool(package["source"]) or package["name"] in LOCAL_UPSTREAM_PACKAGES
                    for package in metadata["packages"])
        print(f"Collected {count} third-party package records: {args.output}")
        return 0
    except (OSError, ValueError, KeyError, subprocess.SubprocessError) as error:
        print(f"Notice collection failed: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
