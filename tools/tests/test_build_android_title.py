#!/usr/bin/env python3
"""CodexAstraUlt: Original package metadata rejects identity/signing/inventory drift."""

import copy
import hashlib
import json
from pathlib import Path
import struct
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch
import xml.etree.ElementTree as ET
import zipfile

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import build_android_title as BUILD


# CodexAstraUlt: Independently authored SDK observations are parser controls,
# not evidence that these fixtures are real signed Android applications.
PROGRAM = "000400000ff3ff00"
PACKAGE = "org.droidds.title.t" + PROGRAM
BADGING = f"""package: name='{PACKAGE}' versionCode='7' versionName='0.0.7-preview.1'
sdkVersion:'29'
targetSdkVersion:'35'
launchable-activity: name='org.droidds.probe.TitleActivity' label='DroiDDS' icon=''
native-code: 'arm64-v8a'
"""
XMLTREE = """E: manifest (line=2)
  E: application (line=4)
    A: android:allowBackup(0x01010280)=(type 0x12)0x0
    A: android:testOnly(0x01010272)=(type 0x12)0x0
    A: android:extractNativeLibs(0x010104ea)=(type 0x12)0xffffffff
    A: android:debuggable(0x0101000f)=(type 0x12)0xffffffff
    E: activity (line=8)
"""


class ManifestTests(unittest.TestCase):
    """CodexAstraUlt: Installation identity and policy derive from packaged XML."""

    def test_staging_preserves_template_and_sets_exact_identity(self):
        source = BUILD.ROOT / "android/title/AndroidManifest.xml"
        original = source.read_bytes()
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary) / "manifest.xml"
            for diagnostic in (False, True):
                BUILD.stage_manifest(source, output, PROGRAM, 7, diagnostic)
                root = ET.parse(output).getroot()
                self.assertEqual(root.get("package"), PACKAGE)
                self.assertEqual(root.get(BUILD.ANDROID + "versionCode"), "7")
                self.assertEqual(root.get(BUILD.ANDROID + "versionName"), BUILD.VERSION)
                app = root.find("application")
                self.assertEqual(app.get(BUILD.ANDROID + "debuggable"), str(diagnostic).lower())
                self.assertEqual(app.get(BUILD.ANDROID + "testOnly"), "false")
        self.assertEqual(source.read_bytes(), original)

    def test_invalid_program_and_version_reject(self):
        for program in (None, "../../bad", PROGRAM.upper(), "0" * 15, "0" * 17):
            with self.subTest(program=program), self.assertRaises(ValueError):
                BUILD.package_name(program)
        with tempfile.TemporaryDirectory() as temporary:
            for code in (True, 0, -1, 2_100_000_001):
                with self.subTest(code=code), self.assertRaises(ValueError):
                    BUILD.stage_manifest(BUILD.ROOT / "android/title/AndroidManifest.xml",
                                         Path(temporary) / "manifest.xml", PROGRAM, code, False)

    def test_probe_template_cannot_be_repurposed(self):
        with tempfile.TemporaryDirectory() as temporary, self.assertRaises(ValueError):
            BUILD.stage_manifest(BUILD.ROOT / "android/probe/AndroidManifest.xml",
                                 Path(temporary) / "manifest.xml", PROGRAM, 7, True)

    def test_binary_observations_accept_exact_package(self):
        actual = BUILD.audit_manifest(BADGING, XMLTREE, PACKAGE, 7, True)
        self.assertEqual(actual["package"], PACKAGE)
        self.assertFalse(actual["test_only"])
        self.assertTrue(actual["debuggable"])

    def test_sdk35_expanded_names_and_literal_booleans(self):
        # CodexAstraUlt: Actual pinned aapt2 emits full namespace URLs and
        # literal booleans instead of the older hexadecimal dump spelling.
        text = XMLTREE.replace("A: android:", "A: http://schemas.android.com/apk/res/android:")
        text = text.replace("(type 0x12)0xffffffff", "true").replace("(type 0x12)0x0", "false")
        self.assertTrue(BUILD.audit_manifest(BADGING, text, PACKAGE, 7, True)["debuggable"])

    def test_wrong_identity_abi_api_launcher_or_permission_rejects(self):
        mutations = (BADGING.replace(PACKAGE, "org.droidds.probe"),
                     BADGING.replace("versionCode='7'", "versionCode='8'"),
                     BADGING.replace("0.0.7-preview.1", "0.0.6"),
                     BADGING.replace("sdkVersion:'29'", "sdkVersion:'28'"),
                     BADGING.replace("targetSdkVersion:'35'", "targetSdkVersion:'34'"),
                     BADGING.replace("'arm64-v8a'", "'x86_64'"),
                     BADGING.replace("TitleActivity", "ProbeActivity"),
                     BADGING + "uses-permission: name='android.permission.INTERNET'\n")
        for bad in mutations:
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                BUILD.audit_manifest(bad, XMLTREE, PACKAGE, 7, True)

    def test_missing_wrong_or_nested_application_policy_rejects(self):
        for bad in (XMLTREE.replace("0xffffffff", "0x0"), XMLTREE.replace("allowBackup", "somethingElse"),
                    XMLTREE + "  E: application (line=10)\n", XMLTREE.replace("E: application", "E: activity"),
                    XMLTREE.replace("    A: android:debuggable", "    E: activity\n      A: android:debuggable")):
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                BUILD.audit_manifest(BADGING, bad, PACKAGE, 7, True)


class SigningTests(unittest.TestCase):
    """CodexAstraUlt: Only selected environment variable names enter command records."""

    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.key = self.root / "owner.keystore"
        self.key.write_bytes(b"original fake key file; not a real signer")
        self.profile = {"schema_version": 1, "kind": "droidds_android_signing_profile",
                        "keystore": str(self.key), "alias": "owner-title",
                        "store_password_env": "DROIDDS_OWNER_STORE", "key_password_env": "DROIDDS_OWNER_KEY",
                        "certificate_sha256": "1" * 64}
        self.environment = {"DROIDDS_OWNER_STORE": "secret-store-value", "DROIDDS_OWNER_KEY": "secret-key-value"}

    def write(self, profile=None):
        path = self.root / "profile.json"
        path.write_text(json.dumps(self.profile if profile is None else profile))
        return path

    def test_explicit_profile_and_secret_free_command_preserve_key(self):
        before = self.key.read_bytes(), self.key.stat().st_mtime_ns
        profile = BUILD.signing_profile(self.write(), self.environment)
        args = BUILD.sign_arguments(profile, self.root / "out.apk", self.root / "aligned.apk")
        self.assertIn("env:DROIDDS_OWNER_STORE", args)
        self.assertIn("env:DROIDDS_OWNER_KEY", args)
        for secret in self.environment.values():
            self.assertNotIn(secret, json.dumps(args))
        self.assertEqual(before, (self.key.read_bytes(), self.key.stat().st_mtime_ns))

    def test_missing_secret_rejects_without_key_mutation(self):
        with self.assertRaisesRegex(ValueError, "environment_missing"):
            BUILD.signing_profile(self.write(), {})
        self.assertTrue(self.key.exists())

    def test_signer_validation_precedes_any_build_output(self):
        # CodexAstraUlt: A missing owner secret rejects before even a report
        # directory is created; the external signing key stays unchanged.
        output = self.root / "new-package"
        args = SimpleNamespace(output=output, signing_profile=self.write(),
                               preparation=self.root / "preparation", compilation=self.root / "compilation",
                               sdk=self.root / "sdk", java_home=self.root / "jdk")
        before = self.key.read_bytes(), self.key.stat().st_mtime_ns
        with patch.dict("os.environ", {}, clear=True), self.assertRaisesRegex(ValueError, "environment_missing"):
            BUILD.build(args)
        self.assertFalse(output.exists())
        self.assertEqual(before, (self.key.read_bytes(), self.key.stat().st_mtime_ns))

    def test_wrong_or_extra_profile_fields_reject(self):
        for name, value in (("schema_version", True), ("alias", "x;echo secret"),
                            ("store_password_env", "literal:secret"), ("certificate_sha256", "1234"),
                            ("keystore", "relative-key"), ("unexpected", "value")):
            profile = copy.deepcopy(self.profile)
            profile[name] = value
            with self.subTest(name=name), self.assertRaises(ValueError):
                BUILD.signing_profile(self.write(profile), self.environment)

    def test_symlink_key_rejects(self):
        alias = self.root / "alias"
        alias.symlink_to(self.key)
        profile = {**self.profile, "keystore": str(alias)}
        with self.assertRaisesRegex(ValueError, "symlink"):
            BUILD.signing_profile(self.write(profile), self.environment)

    def test_duplicate_or_oversized_profile_rejects(self):
        path = self.write()
        path.write_text(path.read_text().replace('{', '{"alias":"duplicate",', 1))
        with self.assertRaisesRegex(ValueError, "duplicate"):
            BUILD.signing_profile(path, self.environment)
        path.write_bytes(b" " * 16385)
        with self.assertRaisesRegex(ValueError, "too_large"):
            BUILD.signing_profile(path, self.environment)

    def test_certificate_exact_single_identity(self):
        text = "Signer #1 certificate SHA-256 digest: " + "A" * 64
        self.assertEqual(BUILD.certificate_fingerprint(text, "a" * 64), "a" * 64)
        for bad, expected in ((text, "b" * 64), (text + "\n" + text, None), ("", None)):
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                BUILD.certificate_fingerprint(bad, expected)


class DependencyTests(unittest.TestCase):
    """CodexAstraUlt: Title packaging cannot accidentally include the probe/compiler."""

    def tree(self):
        names = ("droidds-title-player", "droidds-title-runtime", "recomp-abi", "zakuro-common", "zakuro-cpu", "ash", "naga")
        lines = [name + " v0.1.0" for name in names]
        lines += [f"{name} v0.2.27 ({BUILD.ROOT / 'vendor/zakuro/crates' / name})"
                  for name in ("zakuro-core", "zakuro-fs", "zakuro-gpu")]
        return "\n".join(lines)

    def test_expected_title_graph_passes(self):
        self.assertFalse(BUILD.validate_dependencies(self.tree())["host_compiler"])

    def test_missing_forbidden_or_replaced_runtime_rejects(self):
        for bad in (self.tree().replace("ash v0.1.0", ""), self.tree() + "\nrecomp3ds v0.1.0",
                    self.tree() + "\ndroidds-android-probe v0.0.6", self.tree() + "\ncranelift-codegen v1.0.0",
                    self.tree().replace("vendor/zakuro", "foreign/zakuro")):
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                BUILD.validate_dependencies(bad)


class OutputPreservationTests(unittest.TestCase):
    """CodexAstraUlt: A new package directory cannot live inside preserved inputs."""

    def test_separate_fresh_output_passes_without_creating_it(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            preserved = root / "existing"
            preserved.mkdir()
            output = root / "new-package"
            BUILD.separate_output(output, [preserved])
            self.assertFalse(output.exists())

    def test_existing_nested_or_parent_output_rejects(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            preserved = root / "sdk"
            preserved.mkdir()
            for output in (preserved, preserved / "new-output", root):
                with self.subTest(output=output), self.assertRaises(ValueError):
                    BUILD.separate_output(output, [preserved])


class PackageInventoryTests(unittest.TestCase):
    """CodexAstraUlt: Original ZIP bytes exercise offset/hash/duplicate controls."""

    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.manifest = BUILD.canonical({"original": True})
        self.blobs = {name: ("original ELF control " + name).encode() for name in BUILD.LIBRARIES}
        self.identities = {name: {"bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()}
                           for name, data in self.blobs.items()}

    def archive(self, *, aligned=True, compressed=False, extra=False, original=None):
        path = self.root / "original.apk"
        with zipfile.ZipFile(path, "w") as archive:
            for name in ("AndroidManifest.xml", "resources.arsc", "classes.dex", "assets/THIRD_PARTY_NOTICES.md", "assets/THIRD_PARTY_NOTICES.txt"):
                archive.writestr(name, b"original test placeholder")
            archive.writestr("assets/title-manifest.json", self.manifest)
            if original is not None:
                archive.writestr("assets/original-title.cxi", original)
            for name, data in sorted(self.blobs.items()):
                info = zipfile.ZipInfo("lib/arm64-v8a/" + name)
                if aligned:
                    padding = (-(archive.fp.tell() + 30 + len(info.filename))) % 16384
                    if 0 < padding < 4:
                        padding += 16384
                    if padding:
                        info.extra = struct.pack("<HH", 0xD935, padding - 4) + bytes(padding - 4)
                archive.writestr(info, data, compress_type=zipfile.ZIP_DEFLATED if compressed else zipfile.ZIP_STORED)
            if extra:
                archive.writestr("lib/arm64-v8a/libforeign.so", b"unexpected")
        return path

    def test_exact_stored_aligned_inventory_passes(self):
        result = BUILD.audit_zip(self.archive(), self.identities, self.manifest)
        self.assertEqual(set(result), BUILD.LIBRARIES)
        self.assertTrue(all(value["zip_offset"] % 16384 == 0 for value in result.values()))

    def test_compiled_resource_table_is_required(self):
        # CodexAstraUlt: Pinned aapt2 emits a resource table even without app
        # resources; require that known entry instead of allowing arbitrary extras.
        missing = self.root / "missing-resource-table.apk"
        with zipfile.ZipFile(self.archive()) as source, zipfile.ZipFile(missing, "w") as destination:
            for info in source.infolist():
                if info.filename != "resources.arsc":
                    destination.writestr(info, source.read(info))
        with self.assertRaisesRegex(ValueError, "missing_title_apk_entry"):
            BUILD.audit_zip(missing, self.identities, self.manifest)

    def test_unaligned_compressed_and_extra_libraries_reject(self):
        for options in ({"aligned": False}, {"compressed": True}, {"extra": True}):
            with self.subTest(options=options), self.assertRaises(ValueError):
                BUILD.audit_zip(self.archive(**options), self.identities, self.manifest)

    def test_library_or_manifest_tampering_rejects(self):
        path = self.archive()
        identities = copy.deepcopy(self.identities)
        identities[next(iter(identities))]["sha256"] = "0" * 64
        with self.assertRaisesRegex(ValueError, "native_identity"):
            BUILD.audit_zip(path, identities, self.manifest)
        with self.assertRaisesRegex(ValueError, "manifest_changed"):
            BUILD.audit_zip(path, self.identities, b"different manifest")

    def test_original_asset_requires_explicit_exact_identity(self):
        data = b"original authored fixture"
        path = self.archive(original=data)
        with self.assertRaisesRegex(ValueError, "unexpected"):
            BUILD.audit_zip(path, self.identities, self.manifest)
        expected = {"bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()}
        BUILD.audit_zip(path, self.identities, self.manifest, expected)
        with self.assertRaisesRegex(ValueError, "original_fixture_changed"):
            BUILD.audit_zip(path, self.identities, self.manifest, {**expected, "sha256": "0" * 64})

    def test_duplicate_manifest_entry_rejects(self):
        import warnings
        path = self.archive()
        with warnings.catch_warnings(), zipfile.ZipFile(path, "a") as archive:
            warnings.simplefilter("ignore", UserWarning)
            archive.writestr("assets/title-manifest.json", self.manifest)
        with self.assertRaisesRegex(ValueError, "duplicate"):
            BUILD.audit_zip(path, self.identities, self.manifest)

    def test_only_signing_metadata_can_extend_exact_inventory(self):
        # CodexAstraUlt: META-INF is not a general-purpose payload exception.
        path = self.archive()
        with zipfile.ZipFile(path, "a") as archive:
            for name in ("MANIFEST.MF", "TITLE.SF", "TITLE.RSA"):
                archive.writestr("META-INF/" + name, b"original signature parser fixture")
        BUILD.audit_zip(path, self.identities, self.manifest)
        with zipfile.ZipFile(path, "a") as archive:
            archive.writestr("META-INF/private.cxi", b"unexpected payload")
        with self.assertRaisesRegex(ValueError, "unexpected"):
            BUILD.audit_zip(path, self.identities, self.manifest)


if __name__ == "__main__":
    unittest.main()
