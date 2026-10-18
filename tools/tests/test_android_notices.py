"""CodexAstraUlt: Exercise release notice failures and verbatim attribution retention."""

import importlib.util
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

    def package(self, name="libloading", license="ISC", source="registry+example"):
        base = self.root / name
        base.mkdir(exist_ok=True)
        (base / "Cargo.toml").write_text(f'[package]\nname="{name}"\nlicense="{license}"\n')
        return {"name": name, "version": "0.1.0", "source": source,
                "license": license, "manifest_path": str(base / "Cargo.toml")}

    def test_verbatim_notice_and_byte_hash_retained(self):
        package = self.package()
        data = b"Copyright (c) Synthetic Test Holder\r\nExact text.\n"
        (self.root / "libloading/LICENSE").write_bytes(data)
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
        license, files = notices.REGISTRY_NOTICES["unicode-ident"]
        package = self.package("unicode-ident", license)
        for name in files:
            (self.root / "unicode-ident" / name).write_text("Supplied " + name)
        result = notices.registry_section(package)
        for name in files:
            self.assertIn("Supplied " + name, result)
        self.assertIn("AND Unicode-3.0", result)

    def test_missing_unicode_notice_fails(self):
        license, files = notices.REGISTRY_NOTICES["unicode-ident"]
        package = self.package("unicode-ident", license)
        for name in files[:-1]:
            (self.root / "unicode-ident" / name).write_text("Supplied " + name)
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
        for name, (license, files) in notices.REGISTRY_NOTICES.items():
            packages.append(self.package(name, license))
            for file in files:
                (self.root / name / file).write_text(f"Supplied {name}/{file}\n")
        for project, rev, names in (
                ("3dsrecomp", notices.RECOMP_REV, ("recomp3ds", "recomp-abi")),
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
