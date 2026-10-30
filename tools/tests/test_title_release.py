"""CodexAstraUlt: Public title publication rejects private or relabeled artifacts."""

import copy
import json
from pathlib import Path
import struct
import sys
import tempfile
import unittest
from unittest import mock
import zipfile

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import prepare_title_release as RELEASE

COMMIT = "a" * 40
CERTIFICATE = "b" * 64


class TitleReleaseTests(unittest.TestCase):
    """CodexAstraUlt: Original synthetic archives exercise policy, not Android execution."""

    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.base = Path(temporary.name)
        self.build = self.base / "build"
        self.build.mkdir()
        self.output = self.base / "release"
        self.sdk = self.base / "sdk"
        self.apk = self.build / RELEASE.APK_SOURCE
        self.original = b"Original unit-test image, not the public interactive program"
        self.input_identity = RELEASE.measured(self.original)
        self.source = {"tools/build_android_title.py": "c" * 64}
        # CodexAstraUlt: Only this unit fixture substitutes its byte identity.
        # The production policy pins the real 30,720-byte reviewed image.
        mock.patch.object(RELEASE, "INPUT", self.input_identity).start()
        mock.patch.object(RELEASE.BUILD, "source_identity", return_value=self.source).start()
        mock.patch.object(RELEASE, "source_commit").start()
        self.manifest_reader = mock.patch.object(RELEASE, "sdk_manifest", return_value=RELEASE.MANIFEST).start()
        self.signature = mock.patch.object(RELEASE, "signature", return_value=CERTIFICATE).start()
        mock.patch.object(RELEASE, "elf_metadata", side_effect=self.audit).start()
        self.addCleanup(mock.patch.stopall)
        self.notices = b"Authored unit-test notice\n"
        (self.build / RELEASE.NOTICE).write_bytes(self.notices)
        self.contents = {
            "AndroidManifest.xml": b"Synthetic binary XML; SDK decoding is tested by packager gates",
            "classes.dex": b"original-test-dex", "resources.arsc": b"original-test-resources",
            "assets/original-title.cxi": self.original,
            "assets/THIRD_PARTY_NOTICES.txt": self.notices,
            "assets/THIRD_PARTY_NOTICES.md": (RELEASE.BUILD.ROOT / "THIRD_PARTY_NOTICES.md").read_bytes(),
        }
        self.elf = {}
        for name in sorted(RELEASE.BUILD.LIBRARIES):
            binary = ("original-test-ELF:" + name).encode()
            self.contents["lib/arm64-v8a/" + name] = binary
            self.elf[name] = self.audit(binary)
        self.title = {"schema_version": 1, "kind": "droidds_android_title", "program_id": RELEASE.PROGRAM,
            "input": self.input_identity, "native": {"file": "libdroidds_title.so", **{
                key: self.elf["libdroidds_title.so"][key] for key in ("bytes", "sha256")}},
            "abi": 4, "generation": 3, "prepared": copy.deepcopy(RELEASE.PREPARED)}
        self.contents["assets/title-manifest.json"] = RELEASE.canonical(self.title)
        self.report = {"schema_version": 1, "kind": "droidds_android_title_build", "status": "built",
            "version": RELEASE.VERSION, "device_execution": "not_run", "apk": RELEASE.APK_SOURCE,
            "diagnostic_signing": True, "preserved_inputs_verified": True, "source": self.source,
            "original_fixture": {"fixture": "droidds-original-homebrew-v1", "producer": "droidds-runtime-probe",
                "action": "emit-homebrew", "input": self.input_identity, "producer_sources": RELEASE.producer_sources()},
            "manifest": copy.deepcopy(RELEASE.MANIFEST), "title_manifest": self.title, "elf": self.elf,
            "signing_certificate_sha256": CERTIFICATE,
            "commands": [{"argv": ["sign", "/private/signing-profile"]}],
            "owner_profile": {"password": "must-never-publish"}}
        self.save()

    @staticmethod
    def audit(data):
        """CodexAstraUlt: SDK/ELF mocks describe only these independently authored bytes."""
        return {"machine": "AArch64", "load_alignments": [16384], "needed": ["libc.so"],
                "text_relocations": False, **RELEASE.measured(data)}

    def save(self, compressed=False):
        """CodexAstraUlt: Preserve real ZIP alignment and update outer hash after mutations."""
        with zipfile.ZipFile(self.apk, "w") as archive:
            for name, data in self.contents.items():
                info = zipfile.ZipInfo(name)
                if name.startswith("lib/"):
                    padding = (-(archive.fp.tell() + 30 + len(name.encode()))) % 16384
                    if padding:
                        padding += 16384 if padding < 4 else 0
                        info.extra = struct.pack("<HH", 0xCAFE, padding - 4) + bytes(padding - 4)
                    info.compress_type = zipfile.ZIP_DEFLATED if compressed else zipfile.ZIP_STORED
                archive.writestr(info, data)
        self.report["apk_identity"] = RELEASE.measured(self.apk.read_bytes())
        (self.build / "build-report.json").write_text(json.dumps(self.report))

    def prepare(self):
        RELEASE.prepare(self.build, self.output, self.sdk, RELEASE.TAG, COMMIT)

    def rewrite_public(self, mutate):
        """CodexAstraUlt: Rehash mutations so verification reaches the inner policy."""
        path = self.output / "BUILD_REPORT.json"
        report = json.loads(path.read_text())
        mutate(report)
        path.write_text(json.dumps(report))
        names = sorted((RELEASE.APK_NAME, RELEASE.NOTICE, "BUILD_REPORT.json"))
        (self.output / "SHA256SUMS").write_text("".join(RELEASE.digest((self.output / name).read_bytes())
                                                     + "  " + name + "\n" for name in names))

    def test_valid_four_assets_are_sanitized_and_independently_verified(self):
        self.prepare()
        self.assertEqual({path.name for path in self.output.iterdir()},
                         {RELEASE.APK_NAME, RELEASE.NOTICE, "BUILD_REPORT.json", "SHA256SUMS"})
        public = (self.output / "BUILD_REPORT.json").read_text()
        for secret in ("owner_profile", "commands", "/private/", "must-never-publish"):
            self.assertNotIn(secret, public)
        self.assertEqual(json.loads(public)["device_execution"], "not_run")
        RELEASE.verify_bundle(self.output, self.sdk, RELEASE.TAG, COMMIT)
        self.assertEqual(self.signature.call_count, 3)
        self.assertEqual(self.manifest_reader.call_count, 3)

    def test_owner_signing_and_missing_original_proof_reject(self):
        for field, value in (("diagnostic_signing", False), ("diagnostic_signing", 1),
                             ("original_fixture", None), ("preserved_inputs_verified", False)):
            original = self.report[field]
            self.report[field] = value
            self.save()
            with self.subTest(field=field, value=value), self.assertRaises(ValueError):
                self.prepare()
            self.assertFalse(self.output.exists())
            self.report[field] = original

    def test_changed_or_noninteractive_producer_and_private_fields_reject(self):
        saved = copy.deepcopy(self.report["original_fixture"])
        for field, value in (("fixture", "droidds-original-runtime-v1"), ("action", "emit"),
                             ("producer_sources", {}), ("owner_path", "/private/game")):
            self.report["original_fixture"] = {**saved, field: value}
            self.save()
            with self.subTest(field=field), self.assertRaises(ValueError):
                self.prepare()

    def test_arbitrary_title_cannot_pass_by_relabeling_program_id_and_hashes(self):
        self.contents["assets/original-title.cxi"] = b"private or otherwise unreviewed bytes"
        forged = RELEASE.measured(self.contents["assets/original-title.cxi"])
        self.report["original_fixture"]["input"] = forged
        self.title["input"] = forged
        self.contents["assets/title-manifest.json"] = RELEASE.canonical(self.title)
        self.save()
        with self.assertRaisesRegex(ValueError, "original producer proof"):
            self.prepare()

    def test_changed_embedded_image_rejects_even_with_matching_outer_apk_hash(self):
        self.contents["assets/original-title.cxi"] = b"changed original"
        self.save()
        with self.assertRaisesRegex(ValueError, "original image"):
            self.prepare()

    def test_missing_or_extra_asset_or_library_rejects(self):
        saved = dict(self.contents)
        for name in ("assets/original-title.cxi", "lib/arm64-v8a/libdroidds_title.so"):
            self.contents = {key: value for key, value in saved.items() if key != name}
            self.save()
            with self.subTest(missing=name), self.assertRaises(ValueError):
                self.prepare()
        for name in ("assets/owner-title.cci", "diagnostic-title.keystore", "../private", "lib/x86_64/host.so"):
            self.contents = saved | {name: b"unreviewed"}
            self.save()
            with self.subTest(extra=name), self.assertRaisesRegex(ValueError, "Unexpected APK content"):
                self.prepare()

    def test_changed_library_and_compressed_library_reject(self):
        self.contents["lib/arm64-v8a/libdroidds_title.so"] += b"mutated"
        self.save()
        with self.assertRaisesRegex(ValueError, "audited packaged libraries"):
            self.prepare()
        self.contents["lib/arm64-v8a/libdroidds_title.so"] = self.contents["lib/arm64-v8a/libdroidds_title.so"][:-7]
        self.save(compressed=True)
        with self.assertRaisesRegex(ValueError, "compressed_title_native_library"):
            self.prepare()

    def test_private_or_wrong_component_metadata_rejects(self):
        self.title["prepared"]["components"][0]["path"] = "/private/game/code.bin"
        self.contents["assets/title-manifest.json"] = RELEASE.canonical(self.title)
        self.save()
        with self.assertRaisesRegex(ValueError, "original title manifest"):
            self.prepare()

    def test_duplicate_manifest_keys_reject(self):
        self.contents["assets/title-manifest.json"] = self.contents["assets/title-manifest.json"].replace(
            b'{', b'{"abi":4,', 1)
        self.save()
        with self.assertRaisesRegex(ValueError, "Duplicate"):
            self.prepare()

    def test_wrong_android_identity_or_certificate_rejects(self):
        self.manifest_reader.return_value = {**RELEASE.MANIFEST, "package": "org.private.title"}
        with self.assertRaisesRegex(ValueError, "compiled Android manifest"):
            self.prepare()
        self.manifest_reader.return_value = RELEASE.MANIFEST
        self.signature.return_value = "d" * 64
        with self.assertRaisesRegex(ValueError, "verified APK signer"):
            self.prepare()

    def test_notice_or_source_changes_reject(self):
        self.contents["assets/THIRD_PARTY_NOTICES.txt"] = b"wrong notice"
        self.save()
        with self.assertRaisesRegex(ValueError, "Embedded notices differ"):
            self.prepare()
        self.contents["assets/THIRD_PARTY_NOTICES.txt"] = self.notices
        self.report["source"] = {}
        self.save()
        with self.assertRaisesRegex(ValueError, "builder source inventory"):
            self.prepare()

    def test_verified_bundle_rejects_injected_fields_and_false_device_claims(self):
        self.prepare()
        original = (self.output / "BUILD_REPORT.json").read_bytes()
        for mutate in (lambda r: r.update(owner_profile="/private/profile"),
                       lambda r: r.update(device_execution="passed"),
                       lambda r: r["elf"]["libdroidds_title.so"].update(command="secret"),
                       lambda r: r["original_fixture"].update(private_path="/private")):
            (self.output / "BUILD_REPORT.json").write_bytes(original)
            self.rewrite_public(mutate)
            with self.assertRaises(ValueError):
                RELEASE.verify_bundle(self.output, self.sdk, RELEASE.TAG, COMMIT)

    def test_exact_bundle_inventory_and_checksums_reject(self):
        self.prepare()
        (self.output / "private.log").write_bytes(b"unreviewed")
        with self.assertRaisesRegex(ValueError, "four public assets"):
            RELEASE.verify_bundle(self.output, self.sdk, RELEASE.TAG, COMMIT)
        (self.output / "private.log").unlink()
        (self.output / "SHA256SUMS").write_text("forged\n")
        with self.assertRaisesRegex(ValueError, "bundle checksums"):
            RELEASE.verify_bundle(self.output, self.sdk, RELEASE.TAG, COMMIT)

    def test_input_symlink_rejects_without_output(self):
        real = self.build / "actual.apk"
        self.apk.rename(real)
        self.apk.symlink_to(real)
        with self.assertRaisesRegex(ValueError, "linked"):
            self.prepare()
        self.assertFalse(self.output.exists())


class PublicPolicyTests(unittest.TestCase):
    """CodexAstraUlt: Public policy constants are not fixture-derived trust inputs."""

    def test_only_exact_reviewed_tag_and_commit_are_accepted(self):
        self.assertEqual(RELEASE.identity(RELEASE.TAG, COMMIT), (RELEASE.VERSION, RELEASE.APK_NAME))
        for tag, commit in (("v0.0.7-preview.2", COMMIT), ("v0.1.0", COMMIT), (RELEASE.TAG, "main"),
                            (RELEASE.TAG, "A" * 40), ("../v0.0.7-preview.1", COMMIT)):
            with self.subTest(tag=tag), self.assertRaises(ValueError):
                RELEASE.identity(tag, commit)

    def test_original_identity_is_fixed_independently_of_builder_report(self):
        self.assertEqual(RELEASE.INPUT, {"bytes": 30720,
            "sha256": "efbf68988056b7973f14b934d792d87af430a15e7549cdf3a022e261b9aecbfd"})
        self.assertEqual(RELEASE.PROGRAM, "000400000d5d0006")
        self.assertEqual(set(RELEASE.PUBLIC_FIELDS), set(RELEASE.PUBLIC_FIELDS) - {"commands", "owner_profile"})

    def test_source_commit_and_clean_tree_are_required(self):
        for head, status in ((COMMIT, ""), ("b" * 40, ""), (COMMIT, " M tracked.py"),
                             (COMMIT, "?? untracked-private.json")):
            result = [mock.Mock(stdout=head + "\n"), mock.Mock(stdout=status + "\n")]
            with self.subTest(head=head, status=status), mock.patch.object(
                    RELEASE.subprocess, "run", side_effect=result):
                if head == COMMIT and not status:
                    RELEASE.source_commit(COMMIT)
                else:
                    with self.assertRaises(ValueError):
                        RELEASE.source_commit(COMMIT)


if __name__ == "__main__":
    unittest.main()
