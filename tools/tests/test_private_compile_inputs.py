#!/usr/bin/env python3
"""CodexAstraUlt: Original source records exercise private compilation admission."""

import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import stat
import tempfile
import unittest
from unittest import mock


# CodexAstraUlt: Reuse original descriptor fixtures without running their tests
# or modifying shared Python module/import state.
TOOLS = Path(__file__).resolve().parents[1]
def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

INPUTS = load("compile_inputs_test", TOOLS / "private_compile_inputs.py")
FIXTURES = load("compile_input_originals", TOOLS / "tests/test_prepare_private_title.py")
PREP = INPUTS.PREP


class CompileInputTests(unittest.TestCase):
    """CodexAstraUlt: A manifest is accepted only with matching local source evidence."""

    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="droidds-compile-inputs-")
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.run = self.root / "prepared-run"
        self.run.mkdir(mode=0o700)
        self.output = self.root / "compile-sources"
        self.descriptor, self.blobs = FIXTURES.fixture()
        self.snapshot = b"original synthetic preparation input\n"
        self.worker = {"sha256": hashlib.sha256(b"original worker").hexdigest(), "bytes": 15,
                       "source": {"checkout_commit": "1" * 40, "checkout_dirty": False,
                                  "binary_source_attested": False,
                                  "files_sha256": {"Cargo.lock": "2" * 64}}}
        self.write_preparation()

    def write_preparation(self):
        """CodexAstraUlt: Populate only synthetic identity/source bytes, never a retail image."""
        prepared = self.run / "prepared"
        prepared.mkdir(exist_ok=True)
        for name, data in self.blobs.items():
            path = prepared / name
            path.parent.mkdir(exist_ok=True)
            path.write_bytes(data)
        (prepared / "prepare-report.json").write_text(json.dumps(self.descriptor))
        resolved = PREP.validate_preparation(prepared, self.descriptor)
        source = {"sha256": hashlib.sha256(self.snapshot).hexdigest(), "bytes": len(self.snapshot)}
        self.manifest = {"schema_version": 1, "kind": "droidds_private_title_preparation_manifest",
                         "stage": "prepared", "input": source, "worker": copy.deepcopy(self.worker),
                         "prepared": resolved, "runtime_binding_enforced": False,
                         "guest_execution_performed": False}
        self.report = {"schema_version": 1, "kind": "droidds_private_title_preparation_run",
                       "status": "prepared", "reason": "validated_native_sources",
                       "worker": copy.deepcopy(self.worker), "process": {"outcome": "completed", "exit_code": 0},
                       "input": {**source, "snapshot": "input.cxi", "snapshot_read_only": True,
                                 "stable_before_run": True, "stable_after_run": True},
                       "output_limits": {"prepared_bytes": 1024 * 1024**2,
                                         "failure_diagnostic_bytes": 64 * 1024},
                       "requested": {"prepared_mib": 1024}}
        snapshot = self.run / "input.cxi"
        if snapshot.exists():
            snapshot.chmod(0o600)
        snapshot.write_bytes(self.snapshot)
        snapshot.chmod(0o400)
        self.write_records()

    def write_records(self):
        """CodexAstraUlt: Deliberate fixture mutations remain internally hash-bound when requested."""
        data = PREP.canonical(self.manifest)
        (self.run / "manifest.json").write_bytes(data)
        self.report["manifest_sha256"] = hashlib.sha256(data).hexdigest()
        (self.run / "report.json").write_text(json.dumps(self.report))

    def test_valid_preparation_copies_only_readonly_generated_sources(self):
        before = {p.relative_to(self.run): p.read_bytes() for p in self.run.rglob('*') if p.is_file()}
        loaded = INPUTS.load_preparation(self.run)
        self.assertEqual(loaded["generated_bytes"], sum(len(data) for path, data in self.blobs.items() if path.startswith("generated/")))
        self.assertEqual(loaded["sources"], ["generated/program.c"])
        self.assertEqual(loaded["module_count"], 0)
        copied = INPUTS.snapshot_generated(self.run, loaded, self.output)
        self.assertEqual({p.name for p in self.output.iterdir()}, {"program.c", "recomp.h"})
        self.assertEqual(stat.S_IMODE(self.output.stat().st_mode), 0o700)
        for item in copied:
            self.assertEqual(stat.S_IMODE((self.output / item['path']).stat().st_mode), 0o400)
        self.assertEqual(INPUTS.verify_snapshot(self.output, copied), {"files": 2, "bytes": loaded['generated_bytes']})
        self.assertEqual(before, {p.relative_to(self.run): p.read_bytes() for p in self.run.rglob('*') if p.is_file()})

    def test_manifest_must_be_canonical_and_not_duplicate_key_json(self):
        for contents in (json.dumps(self.manifest).encode(), b'{"schema_version":1,"schema_version":1}'):
            with self.subTest(contents=contents[:40]):
                (self.run / 'manifest.json').write_bytes(contents)
                with self.assertRaises(ValueError):
                    INPUTS.load_preparation(self.run)
        self.assertFalse(self.output.exists())

    def test_manifest_contract_false_claims_and_boolean_aliases_rejected(self):
        original = copy.deepcopy(self.manifest)
        changes = ({"guest_execution_performed": True}, {"runtime_binding_enforced": 0},
                   {"schema_version": True}, {"stage": "compiled"}, {"extra": False},
                   {"input": {"sha256": "0" * 64, "bytes": True}})
        for mutation in changes:
            with self.subTest(mutation=mutation):
                self.manifest = {**copy.deepcopy(original), **mutation}
                self.write_records()
                with self.assertRaises(ValueError):
                    INPUTS.load_preparation(self.run)
        self.manifest = copy.deepcopy(original)
        self.manifest['prepared']['runtime_binding_enforced'] = 0
        self.write_records()
        with self.assertRaisesRegex(ValueError, 'manifest_artifacts_mismatch'):
            INPUTS.load_preparation(self.run)

    def test_worker_and_success_report_identity_must_match_exactly(self):
        original = copy.deepcopy(self.report)
        for mutation in ({"status": "worker_failed"}, {"reason": "worker_exit_2"},
                         {"process": {"outcome": "completed", "exit_code": False}},
                         {"process": {"outcome": "timed_out", "exit_code": 0}}):
            with self.subTest(mutation=mutation):
                self.report = {**copy.deepcopy(original), **mutation}
                self.write_records()
                with self.assertRaises(ValueError):
                    INPUTS.load_preparation(self.run)
        self.report = copy.deepcopy(original)
        self.report['worker']['source']['checkout_dirty'] = 0
        self.write_records()
        with self.assertRaisesRegex(ValueError, 'success_record_mismatch'):
            INPUTS.load_preparation(self.run)
        self.report = copy.deepcopy(original)
        self.write_records()
        self.report['manifest_sha256'] = '0' * 64
        (self.run / 'report.json').write_text(json.dumps(self.report))
        with self.assertRaisesRegex(ValueError, 'success_record_mismatch'):
            INPUTS.load_preparation(self.run)

    def test_artifact_header_and_module_identity_changes_are_rejected(self):
        for path in ('generated/program.c', 'generated/recomp.h', 'identity/code.bin'):
            with self.subTest(path=path):
                file = self.run / 'prepared' / path
                original = file.read_bytes()
                file.write_bytes(bytes([original[0] ^ 1]) + original[1:])
                with self.assertRaises(ValueError):
                    INPUTS.load_preparation(self.run)
                file.write_bytes(original)
        self.descriptor['components'] += [
            {'path': 'identity/module-0000.bin', 'kind': 'cro', 'bytes': 4,
             'source_path': '/original.cro', 'module_name': 'Original'},
            {'path': 'identity/module-0001.bin', 'kind': 'static_crs', 'bytes': 4,
             'source_path': '/static.crs', 'module_name': 'OriginalStatic'}]
        self.blobs.update({'identity/module-0000.bin': b'CRO0', 'identity/module-0001.bin': b'CRS0'})
        self.write_preparation()
        self.assertEqual(INPUTS.load_preparation(self.run)['module_count'], 1)
        (self.run / 'prepared/identity/module-0000.bin').write_bytes(b'CRO1')
        with self.assertRaises(ValueError):
            INPUTS.load_preparation(self.run)

    def test_changed_writable_or_escaping_input_snapshot_is_rejected(self):
        original = copy.deepcopy(self.report['input'])
        for path in ('../input.cxi', '/input.cxi', 'input.cxi/other', 'owner.cxi'):
            with self.subTest(path=path):
                self.report['input'] = {**original, 'snapshot': path}
                self.write_records()
                with self.assertRaisesRegex(ValueError, 'snapshot_path'):
                    INPUTS.load_preparation(self.run)
        self.report['input'] = original
        self.write_records()
        snapshot = self.run / 'input.cxi'
        snapshot.chmod(0o600)
        with self.assertRaisesRegex(ValueError, 'snapshot_is_writable'):
            INPUTS.load_preparation(self.run)
        snapshot.write_bytes(b'changed' + self.snapshot[7:])
        snapshot.chmod(0o400)
        with self.assertRaisesRegex(ValueError, 'snapshot_hash_mismatch'):
            INPUTS.load_preparation(self.run)

    def test_output_allowance_must_match_success_record(self):
        original = copy.deepcopy(self.report)
        for mutation in ({'output_limits': {'prepared_bytes': 2**40, 'failure_diagnostic_bytes': 65536}},
                         {'requested': {'prepared_mib': True}}, {'requested': None},
                         {'output_limits': {'prepared_bytes': 512 * 1024**2, 'failure_diagnostic_bytes': 65536}}):
            with self.subTest(mutation=mutation):
                self.report = {**copy.deepcopy(original), **mutation}
                self.write_records()
                with self.assertRaises(ValueError):
                    INPUTS.load_preparation(self.run)
        self.report = copy.deepcopy(original)
        del self.report['output_limits']
        del self.report['requested']['prepared_mib']
        self.write_records()
        self.assertEqual(INPUTS.load_preparation(self.run)['output_limit_bytes'], 512 * 1024**2)

    def test_missing_extra_and_symlink_artifacts_are_rejected(self):
        source = self.run / 'prepared/generated/program.c'
        original = source.read_bytes()
        source.unlink()
        with self.assertRaises(ValueError):
            INPUTS.load_preparation(self.run)
        source.symlink_to(self.run / 'prepared/generated/recomp.h')
        with self.assertRaises(ValueError):
            INPUTS.load_preparation(self.run)
        source.unlink()
        source.write_bytes(original)
        (self.run / 'prepared/generated/unreported.c').write_text('int other;')
        with self.assertRaises(ValueError):
            INPUTS.load_preparation(self.run)

    def test_source_change_after_load_cannot_become_a_compilation_snapshot(self):
        loaded = INPUTS.load_preparation(self.run)
        source = self.run / 'prepared/generated/program.c'
        source.write_bytes(b'x' * source.stat().st_size)
        with self.assertRaisesRegex(ValueError, 'generated_source_changed'):
            INPUTS.snapshot_generated(self.run, loaded, self.output)
        self.assertFalse((self.output / 'manifest.json').exists())

    def test_changed_manifest_or_loaded_identity_refuses_snapshot_creation(self):
        loaded = INPUTS.load_preparation(self.run)
        loaded['manifest']['guest_execution_performed'] = True
        with self.assertRaisesRegex(ValueError, 'changed_before_source_snapshot'):
            INPUTS.snapshot_generated(self.run, loaded, self.output)
        self.assertFalse(self.output.exists())
        loaded = INPUTS.load_preparation(self.run)
        (self.run / 'manifest.json').write_bytes(b'changed')
        with self.assertRaisesRegex(ValueError, 'changed_before_source_snapshot'):
            INPUTS.snapshot_generated(self.run, loaded, self.output)
        self.assertFalse(self.output.exists())

    def test_existing_symlink_and_git_snapshot_destinations_are_preserved(self):
        loaded = INPUTS.load_preparation(self.run)
        self.output.mkdir()
        marker = self.output / 'owner.txt'
        marker.write_text('preserve')
        with self.assertRaises(ValueError):
            INPUTS.snapshot_generated(self.run, loaded, self.output)
        self.assertEqual(marker.read_text(), 'preserve')
        linked = self.root / 'linked'
        linked.symlink_to(self.output, target_is_directory=True)
        with self.assertRaises(ValueError):
            INPUTS.snapshot_generated(self.run, loaded, linked / 'child')
        repo = self.root / 'repo'
        repo.mkdir()
        (repo / '.git').write_text('gitdir: somewhere')
        with self.assertRaisesRegex(ValueError, 'outside_git'):
            INPUTS.snapshot_generated(self.run, loaded, repo / 'sources')

    def test_retained_snapshot_checks_hash_permissions_and_exact_inventory(self):
        loaded = INPUTS.load_preparation(self.run)
        records = INPUTS.snapshot_generated(self.run, loaded, self.output)
        source = self.output / 'program.c'
        source.chmod(0o600)
        with self.assertRaisesRegex(ValueError, 'snapshot_is_writable'):
            INPUTS.verify_snapshot(self.output, records)
        original = source.read_bytes()
        source.write_bytes(b'x' * len(original))
        source.chmod(0o400)
        with self.assertRaisesRegex(ValueError, 'snapshot_hash_mismatch'):
            INPUTS.verify_snapshot(self.output, records)
        source.chmod(0o600)
        source.write_bytes(original)
        source.chmod(0o400)
        (self.output / 'extra').write_bytes(b'unclaimed')
        with self.assertRaisesRegex(ValueError, 'inventory_mismatch'):
            INPUTS.verify_snapshot(self.output, records)

    def test_metadata_change_during_snapshot_hashing_is_rejected(self):
        original = INPUTS._file_identity
        def changing(path, ceiling):
            result = original(path, ceiling)
            if Path(path).name == 'input.cxi':
                with (self.run / 'report.json').open('a') as target:
                    target.write(' ')
            return result
        with mock.patch.object(INPUTS, '_file_identity', side_effect=changing):
            with self.assertRaisesRegex(ValueError, 'input_changed'):
                INPUTS.load_preparation(self.run)


if __name__ == '__main__':
    unittest.main()
