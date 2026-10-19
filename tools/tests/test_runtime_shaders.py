"""CodexAstraUlt: Imported binary/source drift must block runtime distribution."""

import hashlib
import json
from pathlib import Path
import struct
import sys
import tempfile
import unittest
from unittest import mock

sys.path.insert(0, str(Path(__file__).parents[1]))
import validate_runtime_shaders as SHADERS


class RuntimeShaderGateTests(unittest.TestCase):
    """CodexAstraUlt: Mutation checks exercise provenance and actual tool failure handling."""

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.addCleanup(mock.patch.stopall)
        mock.patch.object(SHADERS, "ROOT", self.root).start()
        self.ndk = self.root / "ndk"
        self.ndk.mkdir()
        (self.ndk / "source.properties").write_text("Pkg.Revision = " + SHADERS.NDK_VERSION)
        self.base = self.root / "vendor/zakuro"
        self.sources = self.base / "crates/zakuro-gpu/shaders"
        self.sources.mkdir(parents=True)
        self.binary = struct.pack("<5I", 0x07230203, 0x10000, 0, 1, 0)
        for name, (source, _) in SHADERS.VARIANTS.items():
            (self.sources / source).write_text("// original test shader\n")
            (self.sources / (name + ".spv")).write_bytes(self.binary)
        (self.base / "UPSTREAM.json").write_text(json.dumps({"files": {
            str(p.relative_to(self.base)): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in self.sources.iterdir()}}))
        self.calls = []

    def tool(self, name, args):
        self.calls.append((name, args))
        if Path(args[0]).name == "glslc":
            args[-1].write_bytes(self.binary)

    def run_gate(self):
        return SHADERS.validate_runtime_shaders(self.ndk, self.root / "out", self.tool)

    def test_exact_assets_are_validated_and_every_source_variant_rebuilt(self):
        evidence = self.run_gate()
        self.assertEqual(len(evidence), 13)
        self.assertEqual(len(self.calls), 39)
        self.assertTrue(all(value["byte_identical_rebuild"] for value in evidence.values()))
        self.assertEqual(evidence["raster_depth.frag"]["defines"], ["WRITES_DEPTH"])

    def test_changed_binary_or_source_is_not_admitted(self):
        for filename in ("depth.comp", "depth.comp.spv"):
            path = self.sources / filename
            before = path.read_bytes()
            path.write_bytes(before + b"changed")
            with self.subTest(filename=filename), self.assertRaisesRegex(ValueError, "reviewed source"):
                self.run_gate()
            path.write_bytes(before)
            (self.root / "out").rmdir()

    def test_unreviewed_variant_is_rejected(self):
        (self.sources / "unreviewed.comp.spv").write_bytes(self.binary)
        with self.assertRaisesRegex(ValueError, "inventory"):
            self.run_gate()

    def test_validator_failure_cannot_become_a_pass(self):
        with mock.patch.object(self, "tool", side_effect=RuntimeError("SPIR-V rejected")):
            with self.assertRaisesRegex(RuntimeError, "SPIR-V rejected"):
                self.run_gate()

    def test_compiler_differences_are_recorded_without_replacing_shipped_bytes(self):
        def compile_differently(name, args):
            self.tool(name, args)
            if Path(args[0]).name == "glslc":
                args[-1].write_bytes(self.binary + b"more")
        evidence = SHADERS.validate_runtime_shaders(self.ndk, self.root / "out", compile_differently)
        self.assertTrue(all(not value["byte_identical_rebuild"] for value in evidence.values()))
        self.assertEqual((self.sources / "depth.comp.spv").read_bytes(), self.binary)

    def test_wrong_toolchain_is_rejected(self):
        (self.ndk / "source.properties").write_text("Pkg.Revision = 0.0")
        with self.assertRaisesRegex(ValueError, "pinned NDK"):
            self.run_gate()


if __name__ == "__main__":
    unittest.main()
