"""CodexAstraUlt: Mutated release inputs must never become public APK assets."""

import importlib.util
import copy
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest import mock
import zipfile

sys.path.insert(0, str(Path(__file__).parents[1]))
import prepare_probe_release as RELEASE

SPEC = importlib.util.spec_from_file_location(
    "probe_manifest_fixture", Path(__file__).with_name("test_run_android_probe.py"))
FIXTURE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(FIXTURE)
TAG = "v0.0.2-probe.1"
COMMIT = "a" * 40
CERTIFICATE = "b" * 64


class ReleaseTests(unittest.TestCase):
    """CodexAstraUlt: Synthetic archives are test inputs, not build/device evidence."""

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.build = self.base / "build"
        self.build.mkdir()
        self.out = self.base / "release"
        self.apk = self.build / RELEASE.APK_SOURCE
        self.notices = b"Original unit-test notice fixture\n"
        (self.build / RELEASE.NOTICE_FILE).write_bytes(self.notices)
        self.contents = {"AndroidManifest.xml": FIXTURE.binary_manifest(test_only=False),
                         "classes.dex": b"unit-test-dex",
                         "resources.arsc": b"unit-test-resource-table",
                         RELEASE.NOTICE_ENTRY: self.notices}
        self.elf = {}
        for name in RELEASE.LIBRARIES:
            data = ("unit-test-library:" + name).encode()
            self.contents["lib/arm64-v8a/" + name] = data
            self.elf[name] = {"machine": "AArch64", "text_relocations": False,
                              "sha256": RELEASE.digest(data)}
        (self.build / "AndroidManifest.xml").write_bytes(b"unit-test-staged-XML")
        self.report = {"schema": 1, "kind": "droidds-android-probe-build", "status": "built",
                       "runtime_status": "not_run", "target": "aarch64-linux-android",
                       "minimum_api": 29, "compile_target_api": 35, "distribution": "prerelease",
                       "test_only": False, "debuggable": True, "apk": RELEASE.APK_SOURCE,
                       "elf": self.elf, "signing_certificate_sha256": CERTIFICATE,
                       "staged_manifest_sha256": RELEASE.digest(b"unit-test-staged-XML"),
                       "manifest": {"package": "org.droidds.probe", "version_code": 2,
                                    "version_name": "0.0.2", "debuggable": True, "test_only": False},
                       "third_party_notices": {"file": RELEASE.NOTICE_FILE,
                           "apk_entry": RELEASE.NOTICE_ENTRY, "sha256": RELEASE.digest(self.notices)},
                       "commands": [{"argv": ["sign", "/private/keystore"]}],
                       "secret_test_field": "must not publish"}
        self.save()
        self.verify = mock.patch.object(RELEASE, "signature", return_value=CERTIFICATE).start()
        self.addCleanup(mock.patch.stopall)

    def save(self):
        """CodexAstraUlt: Mutations update outer hashes to exercise deeper checks."""
        with zipfile.ZipFile(self.apk, "w") as archive:
            for name, data in self.contents.items():
                archive.writestr(name, data)
        self.report["apk_sha256"] = RELEASE.digest(self.apk.read_bytes())
        self.report["apk_bytes"] = self.apk.stat().st_size
        (self.build / "build-report.json").write_text(json.dumps(self.report))

    def prepare(self, tag=TAG):
        RELEASE.prepare(self.build, self.out, self.base / "sdk", tag, COMMIT)

    def test_valid_bundle_has_only_four_assets_and_no_command_or_secret_fields(self):
        self.prepare()
        self.assertEqual({path.name for path in self.out.iterdir()}, {
            "DroidDS-0.0.2-android-arm64.apk", "BUILD_REPORT.json", "SHA256SUMS",
            "THIRD_PARTY_NOTICES.txt"})
        public = json.loads((self.out / "BUILD_REPORT.json").read_text())
        self.assertNotIn("commands", public)
        self.assertNotIn("secret_test_field", public)
        self.assertNotIn("private", json.dumps(public))
        self.assertEqual(public["runtime_status"], "not_run")
        self.verify.assert_called_once_with(self.apk, self.base / "sdk")
        RELEASE.verify_bundle(self.out, TAG, COMMIT)

    # CodexAstraUlt: New CPU cases change the APK's executable inventory. Verify
    # the actual archive against its version rather than widening old allowlists.
    def current_build(self):
        self.contents["AndroidManifest.xml"] = FIXTURE.binary_manifest(
            test_only=False, version_name="0.0.4", version_code=4)
        self.report["manifest"].update(version_name="0.0.4", version_code=4)
        for name in RELEASE.libraries_for_version("0.0.4") - set(self.elf):
            data = ("original-current-test-library:" + name).encode()
            self.contents["lib/arm64-v8a/" + name] = data
            self.elf[name] = {"machine": "AArch64", "text_relocations": False,
                              "sha256": RELEASE.digest(data)}
        self.save()

    def test_current_release_contains_exact_expanded_fixture_set(self):
        self.current_build()
        self.prepare(tag="v0.0.4-probe.1")
        RELEASE.verify_bundle(self.out, "v0.0.4-probe.1", COMMIT)
        public = json.loads((self.out / "BUILD_REPORT.json").read_text())
        self.assertEqual(len(public["elf"]), 10)
        self.assertEqual(public["apk_manifest"]["version_code"], 4)

    def test_current_release_rejects_missing_new_case(self):
        self.current_build()
        name = "libdds_fixture_arm_vfp_finite.so"
        del self.elf[name]
        del self.contents["lib/arm64-v8a/" + name]
        self.save()
        with self.assertRaisesRegex(ValueError, "known ARM64 libraries"):
            self.prepare(tag="v0.0.4-probe.1")

    # CodexAstraUlt: Full runtime execution adds one original native fixture;
    # stale ten-library APKs cannot become 0.0.5 prereleases.
    def runtime_build(self):
        self.current_build()
        self.contents["AndroidManifest.xml"] = FIXTURE.binary_manifest(
            test_only=False, version_name="0.0.5", version_code=5)
        self.report["manifest"].update(version_name="0.0.5", version_code=5)
        name = "libdroidds_fixture_runtime.so"
        data = b"original-runtime-test-library"
        self.contents["lib/arm64-v8a/" + name] = data
        self.elf[name] = {"machine": "AArch64", "text_relocations": False,
                          "sha256": RELEASE.digest(data)}
        # CodexAstraUlt: Fixture metadata is synthetic, while shader evidence
        # uses the checked-in public source/binary pairs the release will bind.
        self.report["runtime_fixture"] = {
            "manifest": {"schema": 1, "kind": "droidds-runtime-fixture-sources",
                "fixture": "droidds-original-pica-ipc-v1", "library": name,
                "abi": 4, "generation": 3, "native_text_bytes": 492,
                "fallback_entry": 0x100800, "sources": ["code000.c", "entries.c"]},
            "inputs_sha256": {item: "c" * 64 for item in (
                "code000.c", "entries.c", "functions.h", "recomp.h", "runtime-fixture.cxi")},
            "library_sha256": self.elf[name]["sha256"],
        }
        runtime = "libdroidds_android_probe.so"
        self.report["runtime_symbols"] = {
            "unstripped_sha256": "c" * 64, "unstripped_bytes": 1024,
            "method": "llvm-strip --strip-debug", "shipped_sha256": self.elf[runtime]["sha256"],
            "shipped_bytes": len(self.contents["lib/arm64-v8a/" + runtime]),
        }
        root = Path(RELEASE.__file__).resolve().parents[1]
        base = "vendor/zakuro/crates/zakuro-gpu/shaders/"
        self.report["runtime_shaders"] = {}
        for item, (source, definitions) in RELEASE.VARIANTS.items():
            binary = (root / (base + item + ".spv")).read_bytes()
            self.report["runtime_shaders"][item] = {
                "source": base + source, "defines": list(definitions),
                "source_sha256": RELEASE.digest((root / (base + source)).read_bytes()),
                "shipped_sha256": RELEASE.digest(binary), "shipped_bytes": len(binary),
                "rebuilt_sha256": "d" * 64, "byte_identical_rebuild": False,
                "validation_environment": "vulkan1.3", "compiler_target": "vulkan1.0/spv1.0",
            }
        self.save()

    def test_runtime_release_requires_exact_eleven_libraries(self):
        self.runtime_build()
        self.prepare(tag="v0.0.5-probe.1")
        RELEASE.verify_bundle(self.out, "v0.0.5-probe.1", COMMIT)
        public = json.loads((self.out / "BUILD_REPORT.json").read_text())
        self.assertEqual(len(public["elf"]), 11)
        self.assertEqual(public["apk_manifest"]["version_code"], 5)
        for field in ("runtime_fixture", "runtime_shaders", "runtime_symbols"):
            self.assertEqual(public[field], self.report[field])

    def runtime_metadata_mutations(self):
        """CodexAstraUlt: Exercise meaningful metadata corruption at both publication stages."""
        for section in ("runtime_fixture", "runtime_shaders", "runtime_symbols"):
            yield (section,), None
        for location in (("runtime_fixture",), ("runtime_fixture", "manifest"),
                         ("runtime_fixture", "inputs_sha256"), ("runtime_symbols",),
                         ("runtime_shaders",), ("runtime_shaders", "depth.comp")):
            yield location + ("private_path",), "/private/must-not-publish"
        yield ("runtime_fixture", "library_sha256"), "0" * 64
        yield ("runtime_symbols", "shipped_sha256"), "0" * 64
        yield ("runtime_fixture", "manifest", "schema"), True
        yield ("runtime_fixture", "manifest", "sources"), ["../private.c", "entries.c"]
        yield ("runtime_fixture", "inputs_sha256", "recomp.h"), "A" * 64
        yield ("runtime_symbols", "unstripped_bytes"), True
        yield ("runtime_symbols", "shipped_bytes"), 1
        yield ("runtime_symbols", "unstripped_sha256"), "/private/symbols"
        yield ("runtime_symbols", "method"), "unreviewed-strip"
        yield ("runtime_shaders", "depth.comp"), None
        yield ("runtime_shaders", "depth.comp", "defines"), ["UNREVIEWED"]
        yield ("runtime_shaders", "depth.comp", "source"), "/private/shader.comp"
        yield ("runtime_shaders", "depth.comp", "source_sha256"), "0" * 64
        yield ("runtime_shaders", "depth.comp", "shipped_sha256"), "0" * 64
        yield ("runtime_shaders", "depth.comp", "rebuilt_sha256"), "not-a-hash"
        yield ("runtime_shaders", "depth.comp", "byte_identical_rebuild"), True
        yield ("runtime_shaders", "depth.comp", "byte_identical_rebuild"), 0
        yield ("runtime_shaders", "depth.comp", "shipped_bytes"), True

    def mutate_runtime_metadata(self, report, path, value):
        """CodexAstraUlt: Mutations remove fields or change one nested contract fact."""
        node = report
        for key in path[:-1]:
            node = node[key]
        if value is None:
            del node[path[-1]]
        else:
            node[path[-1]] = value

    def test_runtime_preparation_rejects_missing_forged_and_private_metadata(self):
        self.runtime_build()
        original = copy.deepcopy(self.report)
        for path, value in self.runtime_metadata_mutations():
            self.report = copy.deepcopy(original)
            self.mutate_runtime_metadata(self.report, path, value)
            self.save()
            with self.subTest(path=path, value=value), self.assertRaises(ValueError):
                self.prepare(tag="v0.0.5-probe.1")
            self.assertFalse(self.out.exists())

    def test_downloaded_runtime_bundle_independently_checks_nested_evidence(self):
        self.runtime_build()
        tag = "v0.0.5-probe.1"
        self.prepare(tag=tag)
        path = self.out / "BUILD_REPORT.json"
        original = json.loads(path.read_text())
        for location, value in self.runtime_metadata_mutations():
            changed = copy.deepcopy(original)
            self.mutate_runtime_metadata(changed, location, value)
            path.write_text(json.dumps(changed))
            # CodexAstraUlt: Recompute the outer checksums so the publishing job
            # must detect the invalid evidence rather than a superficial mismatch.
            names = sorted(item.name for item in self.out.iterdir() if item.name != "SHA256SUMS")
            (self.out / "SHA256SUMS").write_text("".join(
                RELEASE.digest((self.out / name).read_bytes()) + "  " + name + "\n" for name in names))
            with self.subTest(path=location, value=value), self.assertRaises(ValueError):
                RELEASE.verify_bundle(self.out, tag, COMMIT)

    def test_runtime_release_rejects_missing_or_unreviewed_libraries(self):
        self.runtime_build()
        name = "libdroidds_fixture_runtime.so"
        del self.elf[name]
        del self.contents["lib/arm64-v8a/" + name]
        self.save()
        with self.assertRaisesRegex(ValueError, "known ARM64 libraries"):
            self.prepare(tag="v0.0.5-probe.1")
        name = "libunreviewed.so"
        data = b"not-the-runtime-fixture"
        self.elf[name] = {"machine": "AArch64", "text_relocations": False,
                          "sha256": RELEASE.digest(data)}
        self.contents["lib/arm64-v8a/" + name] = data
        self.save()
        with self.assertRaisesRegex(ValueError, "known ARM64 libraries"):
            self.prepare(tag="v0.0.5-probe.1")

    def test_historical_version_cannot_contain_new_fixture_libraries(self):
        self.current_build()
        self.contents["AndroidManifest.xml"] = FIXTURE.binary_manifest(test_only=False)
        self.report["manifest"].update(version_name="0.0.2", version_code=2)
        self.save()
        with self.assertRaisesRegex(ValueError, "known ARM64 libraries"):
            self.prepare()

    def test_tags_and_commit_are_canonical_and_safe(self):
        for tag in ("v0.0.2", "v0.0.2-probe.0", "v00.0.2-probe.1", "../v0.0.2-probe.1",
                    "v0.0.2-probe.1\n", "v0.0.2-probe.1;true"):
            with self.subTest(tag=tag), self.assertRaisesRegex(ValueError, "canonical"):
                RELEASE.identity(tag, COMMIT)
        for commit in ("HEAD", "a" * 39, "A" * 40):
            with self.subTest(commit=commit), self.assertRaisesRegex(ValueError, "canonical"):
                RELEASE.identity(TAG, commit)

    def test_tag_version_must_match_actual_binary_manifest(self):
        with self.assertRaisesRegex(ValueError, "version_name"):
            self.prepare(tag="v0.0.3-probe.1")

    def test_failed_or_unmeasured_runtime_claim_is_not_publishable(self):
        for field, value in (("status", "failed"), ("status", "building"),
                             ("runtime_status", "passed"), ("test_only", 0),
                             ("distribution", "debug"), ("schema", True)):
            with self.subTest(field=field, value=value):
                old = self.report[field]
                self.report[field] = value
                self.save()
                with self.assertRaisesRegex(ValueError, "contract mismatch"):
                    self.prepare()
                self.report[field] = old

    def test_builder_cannot_choose_an_arbitrary_apk_path(self):
        for name in ("../private.apk", "/tmp/private.apk", "unexpected.apk"):
            self.report["apk"] = name
            self.save()
            with self.assertRaisesRegex(ValueError, "apk"):
                self.prepare()

    def test_apk_hash_and_size_must_match_signed_bytes(self):
        self.apk.write_bytes(self.apk.read_bytes() + b"tampered")
        with self.assertRaisesRegex(ValueError, "hash or size"):
            self.prepare()

    def test_signature_is_verified_again_and_certificate_must_match(self):
        self.report["signing_certificate_sha256"] = "d" * 64
        self.save()
        with self.assertRaisesRegex(ValueError, "signing certificate"):
            self.prepare()
        self.verify.side_effect = ValueError("signature rejected")
        with self.assertRaisesRegex(ValueError, "signature rejected"):
            self.prepare()

    def test_embedded_notice_bytes_must_equal_published_file(self):
        self.contents[RELEASE.NOTICE_ENTRY] = b"different notice\n"
        self.save()
        with self.assertRaisesRegex(ValueError, "Embedded notices"):
            self.prepare()

    def test_notice_file_hash_and_fixed_path_are_required(self):
        for key, value in (("sha256", "0" * 64), ("file", "../private"),
                           ("apk_entry", "private/title.bin")):
            old = self.report["third_party_notices"][key]
            self.report["third_party_notices"][key] = value
            self.save()
            with self.subTest(key=key), self.assertRaisesRegex(ValueError, "contract mismatch"):
                self.prepare()
            self.report["third_party_notices"][key] = old

    def test_real_manifest_must_allow_normal_install_and_debug_report_retrieval(self):
        for kwargs in ({"test_only": True}, {"test_only": False, "debuggable": False},
                       {"test_only": False, "package": "other.package"}):
            self.contents["AndroidManifest.xml"] = FIXTURE.binary_manifest(**kwargs)
            self.save()
            with self.subTest(kwargs=kwargs), self.assertRaises(ValueError):
                self.prepare()

    def test_private_extra_apk_entries_and_library_changes_are_rejected(self):
        for name in ("private/title.bin", "assets/signing.keystore", "../escape"):
            self.contents[name] = b"must not publish"
            self.save()
            with self.subTest(name=name), self.assertRaisesRegex(ValueError, "unsafe|Unexpected"):
                self.prepare()
            del self.contents[name]
        library = "lib/arm64-v8a/libdroidds_android_probe.so"
        self.contents[library] += b"changed"
        self.save()
        with self.assertRaisesRegex(ValueError, "audited binary"):
            self.prepare()

    def test_linked_files_are_not_release_inputs(self):
        data = self.apk.read_bytes()
        self.apk.unlink()
        hidden = self.base / "hidden.apk"
        hidden.write_bytes(data)
        self.apk.symlink_to(hidden)
        with self.assertRaisesRegex(ValueError, "linked"):
            self.prepare()

    def test_staged_source_and_builder_manifest_evidence_are_bound(self):
        self.report["manifest"]["version_code"] = 3
        self.save()
        with self.assertRaisesRegex(ValueError, "Builder manifest evidence"):
            self.prepare()
        self.report["manifest"]["version_code"] = 2
        self.save()
        (self.build / "AndroidManifest.xml").write_text("changed source")
        with self.assertRaisesRegex(ValueError, "Staged manifest source"):
            self.prepare()

    def test_existing_output_is_not_overwritten(self):
        self.out.mkdir()
        sentinel = self.out / "user-file"
        sentinel.write_text("preserve")
        with self.assertRaises(FileExistsError):
            self.prepare()
        self.assertEqual(sentinel.read_text(), "preserve")

    def test_downloaded_bundle_rejects_tampering_extra_files_and_wrong_commit(self):
        self.prepare()
        with self.assertRaisesRegex(ValueError, "source_commit"):
            RELEASE.verify_bundle(self.out, TAG, "d" * 40)
        extra = self.out / "private.log"
        extra.write_text("exclude")
        with self.assertRaisesRegex(ValueError, "four allowlisted"):
            RELEASE.verify_bundle(self.out, TAG, COMMIT)
        extra.unlink()
        (self.out / RELEASE.NOTICE_FILE).write_bytes(b"changed")
        with self.assertRaisesRegex(ValueError, "checksum"):
            RELEASE.verify_bundle(self.out, TAG, COMMIT)

    def test_apksigner_requires_one_verified_signer(self):
        mock.patch.stopall()
        for text in ("Number of signers: 1\nSigner #1 certificate SHA-256 digest: " + CERTIFICATE + "\n",
                     "Number of signers: 2\nSigner #1 certificate SHA-256 digest: " + CERTIFICATE + "\n"):
            with mock.patch.object(RELEASE.subprocess, "run") as run:
                run.return_value.stdout = text
                if "signers: 1" in text:
                    self.assertEqual(RELEASE.signature(self.apk, self.base), CERTIFICATE)
                    self.assertTrue(run.call_args.kwargs["check"])
                else:
                    with self.assertRaisesRegex(ValueError, "one verified"):
                        RELEASE.signature(self.apk, self.base)


if __name__ == "__main__":
    unittest.main()
