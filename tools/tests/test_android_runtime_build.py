"""CodexAstraUlt: Keep Android's integrated runtime graph and emitted payload bounded."""

import copy
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import build_android_probe as build


class AndroidRuntimeGraphTests(unittest.TestCase):
    # CodexAstraUlt: Model Cargo's target-specific tree, including repeated
    # dependencies, then inject regressions that must not enter an APK.
    def setUp(self):
        self.tree = "\n".join(f"{name} v1.0.0" for name in (
            "droidds-android-probe", "droidds-foundation", "droidds-runtime-probe",
            "recomp-abi", "zakuro-common", "zakuro-cpu", "ash", "naga"))
        for name in ("zakuro-core", "zakuro-fs", "zakuro-gpu"):
            row = f"{name} v0.2.27 ({build.ROOT / 'vendor/zakuro/crates' / name})"
            self.tree += "\n" + row + "\n" + row + " (*)"

    def test_reviewed_runtime_is_required_and_allowed(self):
        report = build.validate_target_dependencies(self.tree)
        self.assertIn("zakuro-gpu", report["packages"])
        self.assertFalse(report["host_compiler"])
        self.assertFalse(report["pica_cpu_jit"])

    def test_host_compiler_desktop_and_pica_jit_are_rejected(self):
        for name in ("recomp3ds", "zakuro", "cranelift-codegen", "cranelift-jit", "egui", "glow"):
            with self.subTest(name=name), self.assertRaisesRegex(ValueError, "forbidden"):
                build.validate_target_dependencies(self.tree + f"\n{name} v1.0.0")

    def test_cpu_only_or_non_vulkan_graph_cannot_pass(self):
        for name in ("droidds-runtime-probe", "zakuro-core", "zakuro-gpu", "ash", "naga"):
            tree = "\n".join(row for row in self.tree.splitlines() if not row.startswith(name + " "))
            with self.subTest(name=name), self.assertRaisesRegex(ValueError, "missing"):
                build.validate_target_dependencies(tree)

    def test_vendor_path_and_version_are_pinned(self):
        for before, after in (("v0.2.27", "v0.3.0"), ("vendor/zakuro", "unreviewed/zakuro")):
            with self.subTest(after=after), self.assertRaisesRegex(ValueError, "unreviewed vendored"):
                build.validate_target_dependencies(self.tree.replace(before, after))

    def test_second_vendor_identity_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "unreviewed vendored"):
            build.validate_target_dependencies(self.tree + "\nzakuro-gpu v0.2.27 (/other/copy)")


class AndroidRuntimePayloadTests(unittest.TestCase):
    # CodexAstraUlt: Original placeholder bytes test source selection and hashes;
    # real NDK compilation and ELF inspection are separate build evidence.
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.directory = Path(temporary.name)
        (self.directory / "guest.c").write_text("void fixture(void) {}\n")
        (self.directory / "guest.h").write_text("void fixture(void);\n")
        (self.directory / "runtime-fixture.cxi").write_bytes(b"original placeholder")
        self.manifest = {"schema": 1, "kind": "droidds-runtime-fixture-sources",
                         "fixture": "droidds-original-pica-ipc-v1",
                         "library": "libdroidds_fixture_runtime.so", "abi": 4, "generation": 3,
                         "sources": ["guest.c"]}

    def test_runtime_source_and_header_provenance(self):
        paths, report = build.runtime_fixture_sources(self.manifest, self.directory)
        self.assertEqual(paths, [self.directory / "guest.c"])
        self.assertEqual(set(report["inputs_sha256"]), {"guest.c", "guest.h", "runtime-fixture.cxi"})
        self.assertEqual(report["inputs_sha256"]["guest.h"], build.sha256(self.directory / "guest.h"))

    def test_missing_header_is_rejected(self):
        (self.directory / "guest.h").unlink()
        with self.assertRaisesRegex(ValueError, "support header"):
            build.runtime_fixture_sources(self.manifest, self.directory)

    def test_unlisted_c_source_is_rejected(self):
        (self.directory / "extra.c").write_text("void extra(void) {}\n")
        with self.assertRaisesRegex(ValueError, "every generated C source"):
            build.runtime_fixture_sources(self.manifest, self.directory)

    def test_source_path_escape_is_rejected(self):
        manifest = copy.deepcopy(self.manifest)
        manifest["sources"] = ["../guest.c"]
        with self.assertRaisesRegex(ValueError, "nonlocal"):
            build.runtime_fixture_sources(manifest, self.directory)

    def test_unexpected_binary_or_symlink_is_rejected(self):
        extra = self.directory / "unreviewed.so"
        extra.write_bytes(b"foreign ELF")
        with self.assertRaisesRegex(ValueError, "unexpected artifact"):
            build.runtime_fixture_sources(self.manifest, self.directory)
        extra.unlink()
        (self.directory / "alias.h").symlink_to(self.directory / "guest.h")
        with self.assertRaisesRegex(ValueError, "unexpected artifact"):
            build.runtime_fixture_sources(self.manifest, self.directory)

    # CodexAstraUlt: Both independent original guests are mandatory in .6;
    # neither omission nor an extra unreviewed native payload may publish.
    def test_exact_twelve_library_inventory(self):
        self.assertEqual(len(build.PACKAGED_LIBRARIES), 12)
        build.validate_packaged_libraries(build.PACKAGED_LIBRARIES)
        for inventory in (build.PACKAGED_LIBRARIES - {build.RUNTIME_LIBRARY},
                          build.PACKAGED_LIBRARIES - {build.HOMEBREW_LIBRARY},
                          build.PACKAGED_LIBRARIES | {"libforeign.so"}):
            with self.assertRaisesRegex(ValueError, "exactly"):
                build.validate_packaged_libraries(inventory)

    def test_homebrew_cannot_reuse_the_earlier_runtime_identity(self):
        with self.assertRaisesRegex(ValueError, "identity mismatch"):
            build.runtime_fixture_sources(self.manifest, self.directory, homebrew=True)
        manifest = {**self.manifest, "kind": "droidds-homebrew-fixture-sources",
                    "fixture": "droidds-original-homebrew-v1", "library": build.HOMEBREW_LIBRARY}
        with self.assertRaisesRegex(ValueError, "NCCH fixture"):
            build.runtime_fixture_sources(manifest, self.directory, homebrew=True)
        (self.directory / "runtime-fixture.cxi").rename(self.directory / "homebrew-fixture.cxi")
        paths, report = build.runtime_fixture_sources(manifest, self.directory, homebrew=True)
        self.assertEqual(paths, [self.directory / "guest.c"])
        self.assertIn("homebrew-fixture.cxi", report["inputs_sha256"])


if __name__ == "__main__":
    unittest.main()
