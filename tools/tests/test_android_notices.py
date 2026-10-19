"""CodexAstraUlt: Exercise release notice failures and verbatim attribution retention."""

import importlib.util
import copy
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

SPEC = importlib.util.spec_from_file_location(
    "android_notices", Path(__file__).resolve().parents[1] / "collect_android_notices.py")
notices = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(notices)


class NoticeTests(unittest.TestCase):
    # CodexAstraUlt: Tiny synthetic packages test the actual collector without
    # downloading dependencies or copying another project's real attribution.
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        # CodexAstraUlt: Small reviewed synthetic inventory exercises identities
        # and file hashes without copying the real dependencies into test inputs.
        selected = {"libloading", "unicode-ident", "windows-link", "bitflags",
                    "symphonia-core", "block", "libm"}
        inventory = {key: copy.deepcopy(entry) for key, entry in notices.REGISTRY_NOTICES.items()
                     if key[0] in selected}
        for entry in inventory.values():
            entry["source_comments"] = {}
            entry.pop("supplemental_files", None)
            for file in entry["files"]:
                data = f"Supplied {entry['name']}/{file}\n".encode()
                entry["files"][file] = hashlib.sha256(data).hexdigest()
        self.inventory = inventory
        self.inventory_patch = patch.object(notices, "REGISTRY_NOTICES", inventory)
        self.inventory_patch.start()
        self.addCleanup(self.inventory_patch.stop)

    def package(self, name="libloading", license="ISC", source=notices.REGISTRY_SOURCE,
                version=None):
        base = self.root / name
        base.mkdir(exist_ok=True)
        (base / "Cargo.toml").write_text(f'[package]\nname="{name}"\nlicense="{license}"\n')
        if version is None:
            version = next((key[1] for key in self.inventory if key[0] == name), "0.1.0")
        return {"name": name, "version": version, "source": source,
                "license": license, "manifest_path": str(base / "Cargo.toml")}

    def test_verbatim_notice_and_byte_hash_retained(self):
        package = self.package()
        data = b"Copyright (c) Synthetic Test Holder\r\nExact text.\n"
        (self.root / "libloading/LICENSE").write_bytes(data)
        self.inventory[("libloading", package["version"])]["files"]["LICENSE"] = hashlib.sha256(data).hexdigest()
        result = notices.registry_section(package)
        self.assertIn(data.decode(), result)
        self.assertIn(notices.hashlib.sha256(data).hexdigest(), result)

    def test_missing_supplied_notice_fails(self):
        with self.assertRaises(FileNotFoundError):
            notices.registry_section(self.package())

    def test_empty_notice_fails(self):
        package = self.package()
        (self.root / "libloading/LICENSE").write_text(" \n")
        with self.assertRaisesRegex(ValueError, "Empty notice"):
            notices.registry_section(package)

    def test_unreviewed_registry_package_fails(self):
        with self.assertRaisesRegex(ValueError, "Unreviewed registry"):
            notices.registry_section(self.package(name="new-dependency"))

    def test_changed_license_fails(self):
        with self.assertRaisesRegex(ValueError, "Changed license"):
            notices.registry_section(self.package(license="GPL-3.0-only"))

    def test_unicode_conjunction_preserves_all_supplied_notices(self):
        entry = self.inventory[("unicode-ident", "1.0.27")]
        license, files = entry["license"], entry["files"]
        package = self.package("unicode-ident", license)
        for name in files:
            data = "Supplied " + name
            (self.root / "unicode-ident" / name).write_text(data)
            files[name] = hashlib.sha256(data.encode()).hexdigest()
        result = notices.registry_section(package)
        for name in files:
            self.assertIn("Supplied " + name, result)
        self.assertIn("AND Unicode-3.0", result)

    def test_missing_unicode_notice_fails(self):
        entry = self.inventory[("unicode-ident", "1.0.27")]
        license, files = entry["license"], entry["files"]
        package = self.package("unicode-ident", license)
        for name in list(files)[:-1]:
            data = "Supplied " + name
            (self.root / "unicode-ident" / name).write_text(data)
            files[name] = hashlib.sha256(data.encode()).hexdigest()
        with self.assertRaises(FileNotFoundError):
            notices.registry_section(package)

    def test_mit_declaration_kept_without_invented_copyright(self):
        source = ("git+https://github.com/fearkov/3dsrecomp?rev="
                  + notices.RECOMP_REV + "#" + notices.RECOMP_REV)
        package = self.package("recomp-abi", "MIT", source)
        result = notices.git_section(package, set())
        self.assertIn('license="MIT"', result)
        self.assertIn(notices.MIT_TERMS, result)
        self.assertIn("not an upstream-supplied notice file", result)
        self.assertNotIn("Copyright (c)", result)

    def test_changed_git_revision_fails(self):
        package = self.package("recomp-abi", "MIT", "git+https://github.com/fearkov/3dsrecomp#other")
        with self.assertRaisesRegex(ValueError, "Changed Git source"):
            notices.git_section(package, set())

    def test_original_git_compiler_cannot_replace_the_reviewed_local_fix(self):
        source = ("git+https://github.com/fearkov/3dsrecomp?rev="
                  + notices.RECOMP_REV + "#" + notices.RECOMP_REV)
        with self.assertRaisesRegex(ValueError, "Unreviewed Git"):
            notices.git_section(self.package("recomp3ds", "MIT", source), set())

    def test_zakuro_copyright_retained_once(self):
        source = ("git+https://github.com/fearkov/zakuro?rev="
                  + notices.ZAKURO_REV + "#" + notices.ZAKURO_REV)
        first = self.package("zakuro-cpu", "MIT", source)
        second = self.package("zakuro-common", "MIT", source)
        supplied = "Copyright (c) Synthetic Test Holder\nPermission terms\n"
        (self.root / "LICENSE").write_text(supplied)
        seen = set()
        with patch.object(notices, "command", return_value=str(self.root)):
            result = notices.git_section(first, seen) + notices.git_section(second, seen)
        self.assertEqual(result.count(supplied), 1)

    # CodexAstraUlt: Runtime integration adds path crates, multiple registry
    # versions and MPL sources; exercise failures that would omit their terms.
    def test_changed_registry_version_fails(self):
        with self.assertRaisesRegex(ValueError, "Unreviewed registry"):
            notices.registry_section(self.package(version="99.0.0"))

    def test_changed_registry_source_fails(self):
        with self.assertRaisesRegex(ValueError, "source declaration"):
            notices.registry_section(self.package(source="registry+unreviewed"))

    def test_changed_notice_bytes_fail(self):
        package = self.package()
        (self.root / "libloading/LICENSE").write_text("Changed permission terms")
        with self.assertRaisesRegex(ValueError, "Changed reviewed notice"):
            notices.registry_section(package)

    def test_mpl_sources_are_identified_without_relicensing(self):
        package = self.package("symphonia-core", "MPL-2.0")
        (self.root / "symphonia-core/LICENSE").write_text("Supplied symphonia-core/LICENSE\n")
        result = notices.registry_section(package)
        self.assertIn("complete, unmodified Source Code Form", result)
        self.assertIn("https://static.crates.io/crates/symphonia-core/symphonia-core-0.6.1.crate", result)
        self.assertIn(self.inventory[("symphonia-core", "0.6.1")]["checksum"], result)
        self.assertIn("Supplied symphonia-core/LICENSE", result)

    def test_registry_declaration_exception_does_not_invent_copyright(self):
        result = notices.registry_section(self.package("block", "MIT"))
        self.assertIn(notices.MIT_TERMS, result)
        self.assertIn("not an upstream-supplied notice", result)
        self.assertNotIn("Copyright (c)", result)

    def test_inline_notice_retains_exact_comment_without_function_body(self):
        path = self.root / "math.rs"
        comment = b"// Copyright Synthetic Holder\r\n// Redistribution and use permitted.\r\n"
        data = comment + b"fn implementation() {}\n"
        path.write_bytes(data)
        result = notices.source_comments(path, "test/math.rs", hashlib.sha256(data).hexdigest())
        self.assertIn(comment.rstrip(b"\n").decode(), result)
        self.assertNotIn("fn implementation", result)
        with self.assertRaisesRegex(ValueError, "Changed attribution source"):
            notices.source_comments(path, "test/math.rs", "0" * 64)

    def test_empty_source_attribution_fails(self):
        path = self.root / "math.rs"
        data = b"// Nothing about attribution.\nfn implementation() {}\n"
        path.write_bytes(data)
        with self.assertRaisesRegex(ValueError, "Missing reviewed source attribution"):
            notices.source_comments(path, "test/math.rs", hashlib.sha256(data).hexdigest())

    def test_supplemental_notice_source_and_bytes_are_preserved(self):
        package = self.package()
        (self.root / "libloading/LICENSE").write_text("Supplied libloading/LICENSE\n")
        data = "Copyright Synthetic Supplement Holder\nPermission terms\n"
        (self.root / "extra-notice").write_text(data)
        self.inventory[("libloading", "0.8.9")]["supplemental_files"] = [{
            "file": "extra-notice", "sha256": hashlib.sha256(data.encode()).hexdigest(),
            "source": "https://example.invalid/exact-commit/LICENSE", "reason": "Synthetic fixture."}]
        with patch.object(notices, "ROOT", self.root):
            result = notices.registry_section(package)
            self.assertIn(data, result)
            self.assertIn("https://example.invalid/exact-commit/LICENSE", result)
            (self.root / "extra-notice").unlink()
            with self.assertRaises(FileNotFoundError):
                notices.registry_section(package)

    def test_wrong_rust_fails(self):
        with self.assertRaisesRegex(ValueError, "pinned Rust"):
            notices.assemble({}, self.root, self.root, "rustc 1.90.0 example")

    def test_wrong_ndk_fails(self):
        (self.root / "source.properties").write_text("Pkg.Revision = 99.0.0\n")
        with self.assertRaisesRegex(ValueError, "pinned NDK"):
            notices.assemble({}, self.root, self.root, "rustc 1.95.0 example")

    def test_incomplete_inventory_fails(self):
        (self.root / "source.properties").write_text(f"Pkg.Revision = {notices.NDK_VERSION}\n")
        with self.assertRaisesRegex(ValueError, "inventory changed"):
            notices.assemble({"packages": []}, self.root, self.root, "rustc 1.95.0 example")

    def full_inputs(self):
        """CodexAstraUlt: Model the reviewed graph to exercise runtime notice gates."""
        packages = []
        for (name, version), entry in self.inventory.items():
            packages.append(self.package(name, entry["license"], version=version))
            for file in entry["files"]:
                (self.root / name / file).write_text(f"Supplied {name}/{file}\n")
        # CodexAstraUlt: The collector binds the exact archive checksums against
        # Cargo.lock, including two simultaneous versions of bitflags.
        lines = []
        for (name, version), entry in self.inventory.items():
            lines += ["[[package]]", f'name = "{name}"', f'version = "{version}"',
                      f'source = "{notices.REGISTRY_SOURCE}"',
                      f'checksum = "{entry["checksum"]}"', ""]
        (self.root / "Cargo.lock").write_text("\n".join(lines))
        self.root_patch = patch.object(notices, "ROOT", self.root)
        self.root_patch.start()
        self.addCleanup(self.root_patch.stop)
        vendor = self.root / "vendor/zakuro"
        vendor.mkdir(parents=True)
        license_data = "Supplied Zakuro attribution\n"
        (vendor / "LICENSE").write_text(license_data)
        (vendor / "UPSTREAM.json").write_text(json.dumps({
            "schema": 1, "repository": "https://github.com/fearkov/zakuro",
            "revision": notices.ZAKURO_REV,
            "files": {"LICENSE": hashlib.sha256(license_data.encode()).hexdigest()}}))
        for name in sorted(notices.VENDORED_PACKAGES):
            manifest = vendor / "crates" / name / "Cargo.toml"
            manifest.parent.mkdir(parents=True)
            manifest.write_text('[package]\nlicense = "MIT"\n')
            packages.append({"name": name, "version": "0.2.27", "source": None,
                             "license": "MIT", "manifest_path": str(manifest)})
        # CodexAstraUlt: The maintained host compiler preserves its exact original
        # MIT declaration separately from the locally adapted Cargo manifest.
        compiler = self.root / "vendor/3dsrecomp"
        compiler.mkdir()
        original = '[package]\nname = "recomp3ds"\nlicense = "MIT"\n'
        (compiler / "UPSTREAM-Cargo.toml").write_text(original)
        (compiler / "Cargo.toml").write_text(original)
        (compiler / "UPSTREAM.json").write_text(json.dumps({
            "repository": "https://github.com/fearkov/3dsrecomp", "revision": notices.RECOMP_REV,
            "license": "MIT", "manifest_provenance": {
                "file": "UPSTREAM-Cargo.toml", "upstream_path": "Cargo.toml",
                "sha256": hashlib.sha256(original.encode()).hexdigest()}}))
        packages.append({"name": "recomp3ds", "version": "0.1.0", "source": None,
                         "license": "MIT", "manifest_path": str(compiler / "Cargo.toml")})
        for project, rev, names in (
                ("3dsrecomp", notices.RECOMP_REV, ("recomp-abi",)),
                ("zakuro", notices.ZAKURO_REV, ("zakuro-common", "zakuro-cpu"))):
            for name in names:
                packages.append(self.package(name, "MIT",
                    f"git+https://github.com/fearkov/{project}?rev={rev}#{rev}"))
        (self.root / "LICENSE").write_text("Supplied Zakuro attribution\n")
        (self.root / "source.properties").write_text(f"Pkg.Revision = {notices.NDK_VERSION}\n")
        for file in ("NOTICE", "NOTICE.toolchain", "toolchains/llvm/prebuilt/linux-x86_64/NOTICE",
                     "share/doc/rust/COPYRIGHT-library.html"):
            path = self.root / file
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(f"Supplied runtime {file}\n")
        # CodexAstraUlt: Model real NDK header comment shape without copying
        # upstream attribution into synthetic fixture ownership statements.
        for file in notices.VULKAN_HEADERS:
            path = self.root / notices.NDK_INCLUDE / file
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("#ifndef TEST_API\n/*\n** Copyright Synthetic Test Holder\n"
                            "** SPDX-License-Identifier: Apache-2.0\n*/\n"
                            "typedef int TestApiDeclaration;\n")
        return {"packages": packages}

    def test_full_bundle_keeps_runtime_and_build_records(self):
        metadata = self.full_inputs()
        with patch.object(notices, "command", return_value=str(self.root)):
            result = notices.assemble(metadata, self.root, self.root, "rustc 1.95.0 example")
        self.assertIn("Supplied runtime share/doc/rust/COPYRIGHT-library.html", result)
        self.assertIn("Supplied runtime NOTICE.toolchain", result)
        self.assertIn("Supplied windows-link/license-mit", result)
        self.assertIn("Inclusion does not assert", result)
        self.assertIn("vulkan/vulkan_core.h copyright comment", result)
        self.assertIn("vk_video/vulkan_video_codecs_common.h copyright comment", result)
        self.assertNotIn("typedef int TestApiDeclaration", result)
        self.assertIn("Package: bitflags 1.3.2", result)
        self.assertIn("Package: bitflags 2.13.2", result)
        self.assertIn("Package: zakuro-core 0.2.27", result)
        self.assertEqual(result.count("Supplied Zakuro attribution"), 1)

    def test_missing_vendor_crate_fails(self):
        metadata = self.full_inputs()
        metadata["packages"] = [p for p in metadata["packages"] if p["name"] != "zakuro-gpu"]
        with self.assertRaisesRegex(ValueError, "inventory changed"):
            notices.assemble(metadata, self.root, self.root, "rustc 1.95.0 example")

    def test_changed_archive_checksum_fails(self):
        metadata = self.full_inputs()
        lock = self.root / "Cargo.lock"
        original = next(iter(self.inventory.values()))["checksum"]
        lock.write_text(lock.read_text().replace(original, "0" * 64))
        with self.assertRaisesRegex(ValueError, "archive inventory changed"):
            notices.assemble(metadata, self.root, self.root, "rustc 1.95.0 example")

    def test_disabled_optional_lock_entry_is_not_treated_as_linked(self):
        metadata = self.full_inputs()
        lock = self.root / "Cargo.lock"
        lock.write_text(lock.read_text() + '\n[[package]]\nname = "optional-unused"\n'
                        'version = "1.0.0"\n'
                        f'source = "{notices.REGISTRY_SOURCE}"\nchecksum = "unused"\n')
        with patch.object(notices, "command", return_value=str(self.root)):
            result = notices.assemble(metadata, self.root, self.root, "rustc 1.95.0 example")
        self.assertNotIn("Package: optional-unused", result)
        metadata["packages"].append(self.package("optional-unused", "MIT", version="1.0.0"))
        with self.assertRaisesRegex(ValueError, "inventory changed"):
            notices.assemble(metadata, self.root, self.root, "rustc 1.95.0 example")

    def test_duplicate_registry_identity_is_rejected(self):
        metadata = self.full_inputs()
        metadata["packages"].append(copy.deepcopy(metadata["packages"][0]))
        with self.assertRaisesRegex(ValueError, "inventory changed"):
            notices.assemble(metadata, self.root, self.root, "rustc 1.95.0 example")

    def test_wrong_vendor_origin_and_license_fail(self):
        metadata = self.full_inputs()
        package = next(p for p in metadata["packages"] if p["name"] == "zakuro-core")
        path = self.root / "vendor/zakuro/UPSTREAM.json"
        original = path.read_text()
        path.write_text(original.replace(notices.ZAKURO_REV, "0" * 40))
        with self.assertRaisesRegex(ValueError, "Changed vendored Zakuro origin"):
            notices.vendor_section(package, set())
        path.write_text(original)
        (path.parent / "LICENSE").write_text("Changed terms")
        with self.assertRaisesRegex(ValueError, "Changed vendored Zakuro license"):
            notices.vendor_section(package, set())

    def test_vendor_path_cannot_substitute_an_unreviewed_copy(self):
        metadata = self.full_inputs()
        package = next(p for p in metadata["packages"] if p["name"] == "zakuro-core")
        package["manifest_path"] = str(self.root / "other/Cargo.toml")
        with self.assertRaisesRegex(ValueError, "Changed vendored package identity"):
            notices.vendor_section(package, set())

    def test_maintained_compiler_keeps_original_manifest_and_rejects_changes(self):
        metadata = self.full_inputs()
        package = next(p for p in metadata["packages"] if p["name"] == "recomp3ds")
        result = notices.compiler_section(package, set())
        self.assertIn("3dsrecomp/original-Cargo.toml", result)
        self.assertIn(notices.MIT_TERMS, result)
        self.assertIn("host compiler is not packaged", result)
        self.assertNotIn("Copyright (c)", result)
        original = self.root / "vendor/3dsrecomp/UPSTREAM-Cargo.toml"
        original.write_text(original.read_text() + "# changed\n")
        with self.assertRaisesRegex(ValueError, "Changed reviewed notice"):
            notices.compiler_section(package, set())

    def test_maintained_compiler_wrong_origin_fails(self):
        metadata = self.full_inputs()
        package = next(p for p in metadata["packages"] if p["name"] == "recomp3ds")
        origin = self.root / "vendor/3dsrecomp/UPSTREAM.json"
        origin.write_text(origin.read_text().replace(notices.RECOMP_REV, "0" * 40))
        with self.assertRaisesRegex(ValueError, "compiler origin"):
            notices.compiler_section(package, set())

    def test_missing_rust_runtime_notice_fails(self):
        metadata = self.full_inputs()
        (self.root / "share/doc/rust/COPYRIGHT-library.html").unlink()
        with patch.object(notices, "command", return_value=str(self.root)):
            with self.assertRaises(FileNotFoundError):
                notices.assemble(metadata, self.root, self.root, "rustc 1.95.0 example")

    def test_missing_ndk_support_notice_fails(self):
        metadata = self.full_inputs()
        (self.root / "NOTICE.toolchain").unlink()
        with patch.object(notices, "command", return_value=str(self.root)):
            with self.assertRaises(FileNotFoundError):
                notices.assemble(metadata, self.root, self.root, "rustc 1.95.0 example")

    def test_header_notice_preserves_comment_and_full_header_hash(self):
        self.full_inputs()
        path = self.root / notices.NDK_INCLUDE / "vulkan/vulkan_core.h"
        data = (b"#ifndef TEST\r\n/*\r\n** Copyright Synthetic Test Holder\r\n"
                b"** SPDX-License-Identifier: Apache-2.0\r\n*/\r\n"
                b"typedef int TestApiDeclaration;\r\n")
        path.write_bytes(data)
        result = notices.header_notice(path, "test header")
        self.assertIn(data[data.index(b"/*"):data.index(b"*/") + 2].decode(), result)
        self.assertIn(notices.hashlib.sha256(data).hexdigest(), result)
        self.assertNotIn("TestApiDeclaration", result)

    def test_missing_required_vulkan_header_fails(self):
        self.full_inputs()
        (self.root / notices.NDK_INCLUDE / "vulkan/vulkan_core.h").unlink()
        with self.assertRaises(FileNotFoundError):
            notices.vulkan_notices(self.root)

    def test_missing_transitive_video_header_fails(self):
        self.full_inputs()
        (self.root / notices.NDK_INCLUDE / "vk_video/vulkan_video_codecs_common.h").unlink()
        with self.assertRaises(FileNotFoundError):
            notices.vulkan_notices(self.root)

    def test_changed_vulkan_header_license_fails(self):
        self.full_inputs()
        path = self.root / notices.NDK_INCLUDE / "vulkan/vulkan_core.h"
        for replacement in ("MIT", "Apache-2.0 OR MIT", ""):
            with self.subTest(replacement=replacement):
                path.write_text("/* Copyright Synthetic Test Holder\n"
                                f"SPDX-License-Identifier: {replacement}\n*/")
                with self.assertRaisesRegex(ValueError, "Changed Vulkan header license"):
                    notices.vulkan_notices(self.root)

    def test_missing_vulkan_copyright_comment_fails(self):
        self.full_inputs()
        path = self.root / notices.NDK_INCLUDE / "vulkan/vulkan_core.h"
        path.write_text("/* SPDX-License-Identifier: Apache-2.0 */\n")
        with self.assertRaisesRegex(ValueError, "Missing copyright comment"):
            notices.vulkan_notices(self.root)

    def test_extra_video_header_notice_is_preserved(self):
        self.full_inputs()
        path = self.root / notices.NDK_INCLUDE / "vk_video/additional_codec.h"
        path.write_text("/* Copyright Additional Synthetic Holder\n"
                        "SPDX-License-Identifier: Apache-2.0\n*/\n")
        self.assertIn("Copyright Additional Synthetic Holder", notices.vulkan_notices(self.root))


if __name__ == "__main__":
    unittest.main()
