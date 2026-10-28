#!/usr/bin/env python3
"""CodexAstraUlt: Compile original C fixtures and reject false resume evidence.

Default checks use authored synthetic preparation records and the real installed
C compiler. --worker additionally requires actual original NCCH preparation.
No test loads the resulting library or executes guest functions.
"""

import contextlib
import copy
import importlib.util
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest import mock


# CodexAstraUlt: Explicit module paths keep discovery independent of import order.
TOOLS = Path(__file__).resolve().parents[1]


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


RUNNER = load("compile_private_title_test", TOOLS / "compile_private_title.py")
INPUT_FIXTURES = load("compile_private_input_fixtures", TOOLS / "tests/test_private_compile_inputs.py")
PREP_FIXTURES = load("compile_private_ncch_fixtures", TOOLS / "tests/test_prepare_private_title.py")
REAL_WORKER = None
REAL_CC = None

# CodexAstraUlt: These zero-filled arrays deliberately test static ABI metadata,
# not valid runtime pointer tables. They must never be executed or dlopened.
ORIGINAL_C = b'''/* CodexAstraUlt: Authored static-library fixture, not guest output. */
#include <stdint.h>
#include "recomp.h"
#define EXPORT __attribute__((visibility("default")))
EXPORT const uint32_t recomp_abi = 4;
EXPORT const uint32_t recomp_generation = 3;
EXPORT const uint32_t recomp_entry_count = 1;
EXPORT const uint32_t recomp_module_count = 0;
EXPORT const unsigned char recomp_entries[16] = {0};
EXPORT const unsigned char recomp_modules[0] = {};
EXPORT const unsigned char recomp_origins[56] = {0};
int original(void) { return ORIGINAL_VALUE; }
'''


def tree_bytes(root):
    """CodexAstraUlt: Preservation checks cover every preparation file's bytes."""
    return {path.relative_to(root).as_posix(): path.read_bytes()
            for path in root.rglob('*') if path.is_file()}


class CompileCoordinatorTests(unittest.TestCase):
    """CodexAstraUlt: Real compiler outputs exercise receipts, linking and failures."""

    @classmethod
    def setUpClass(cls):
        # CodexAstraUlt: An absent compiler is a failed gate, never a skipped pass.
        cls.compiler = RUNNER.PROCESS.inspect_compiler(REAL_CC)

    def setUp(self):
        self.fixture = INPUT_FIXTURES.CompileInputTests('test_valid_preparation_copies_only_readonly_generated_sources')
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)
        self.root, self.preparation = self.fixture.root, self.fixture.run
        self.output = self.root / "build with spaces and an owner's apostrophe"
        self.fixture.blobs['generated/program.c'] = ORIGINAL_C
        self.fixture.blobs['generated/recomp.h'] = b'/* CodexAstraUlt: Original header. */\n#define ORIGINAL_VALUE 17\n'
        self.fixture.blobs['generated/extra.c'] = b'/* CodexAstraUlt: Original second unit. */\nint another(void) { return 23; }\n'
        self.fixture.descriptor['artifacts'] = [
            {'path': name, 'bytes': len(data)} for name, data in self.fixture.blobs.items()
            if name.startswith('generated/')]
        self.fixture.descriptor['sources'] = ['generated/extra.c', 'generated/program.c']
        self.fixture.write_preparation()
        self.before = tree_bytes(self.preparation)
        # CodexAstraUlt: Separate tool-discovery tests cover inspection itself;
        # coordinator controls use one observed identity while parallel code edits
        # cannot masquerade as input mutation in an unrelated failure injection.
        self.compiler_patch = mock.patch.object(RUNNER.PROCESS, 'inspect_compiler', return_value=copy.deepcopy(self.compiler))
        self.source_patch = mock.patch.object(RUNNER, 'coordinator_identity', return_value={'original_fixture': '1' * 64})
        self.compiler_patch.start()
        self.source_patch.start()
        self.addCleanup(self.compiler_patch.stop)
        self.addCleanup(self.source_patch.stop)

    def args(self, *extra):
        return RUNNER.parse_args(['--preparation', str(self.preparation), '--output', str(self.output),
                                  '--batch-seconds', '30', '--command-seconds', '10',
                                  '--cpu-seconds', '10', '--memory-mib', '512', '--output-mib', '64', *extra])

    def execute(self, *extra):
        with contextlib.redirect_stdout(io.StringIO()):
            code, report = RUNNER.run(self.args(*extra))
        if report.get('report_path'):
            saved = json.loads(Path(report['report_path']).read_text())
            self.assertEqual(saved['status'], report['status'])
            self.assertEqual(saved['objects_ready'], report['objects_ready'])
        return code, report

    def pause_after_one_object(self):
        """CodexAstraUlt: Deterministic batch stop preserves one genuinely compiled object."""
        original = RUNNER.command_result
        calls = []
        def pause(command, *args):
            calls.append(command)
            return original(command, *args) if len(calls) == 1 else None
        with mock.patch.object(RUNNER, 'command_result', side_effect=pause):
            code, report = self.execute()
        self.assertEqual(code, 2, report)
        self.assertEqual(report['status'], 'incomplete', report)
        self.assertEqual(report['reason'], 'batch_budget')
        self.assertEqual(report['objects_ready'], 1)
        self.assertFalse((self.output / 'compiled-manifest.json').exists())
        return report

    def mutate(self, path):
        """CodexAstraUlt: Deliberate local fixture corruption preserves readonly policy."""
        path.chmod(0o600)
        data = path.read_bytes()
        path.write_bytes(bytes([data[0] ^ 1]) + data[1:])
        path.chmod(0o400)

    def test_compiles_real_objects_and_library_without_loading_or_mutating_preparation(self):
        code, report = self.execute()
        self.assertEqual(code, 0, report)
        self.assertEqual(report['status'], 'compiled')
        self.assertEqual(report['objects_compiled'], 3)
        self.assertEqual(report['objects_ready'], 3)
        self.assertEqual(report['generated_sources'], 2)
        manifest = RUNNER.read_canonical(self.output / 'compiled-manifest.json')
        self.assertEqual(manifest['stage'], 'compiled')
        self.assertEqual(manifest['elf']['abi'], 4)
        self.assertEqual(manifest['elf']['generation'], 3)
        self.assertEqual(manifest['elf']['module_count'], 0)
        for name in ('library_loaded', 'guest_execution_performed', 'runtime_binding_enforced'):
            self.assertIs(manifest[name], False)
        self.assertIs(manifest['elf']['runtime_tables_validated'], False)
        self.assertTrue((self.output / manifest['library']['path']).is_file())
        self.assertEqual(len(list((self.output / 'receipts').glob('*.json'))), 3)
        self.assertEqual(tree_bytes(self.preparation), self.before)

    def test_bounded_resume_reuses_only_verified_objects(self):
        first = self.pause_after_one_object()
        first_report = Path(first['report_path']).read_bytes()
        receipts_before = tree_bytes(self.output / 'receipts')
        code, report = self.execute('--resume')
        self.assertEqual(code, 0, report)
        self.assertEqual(report['objects_reused'], 1)
        self.assertEqual(report['objects_compiled'], 2)
        self.assertEqual(Path(first['report_path']).read_bytes(), first_report)
        for name, data in receipts_before.items():
            self.assertEqual((self.output / 'receipts' / name).read_bytes(), data)
        self.assertEqual(tree_bytes(self.preparation), self.before)

    def test_completed_resume_validates_existing_library_without_recompiling(self):
        code, report = self.execute()
        self.assertEqual(code, 0, report)
        previous = (self.output / 'compiled-manifest.json').read_bytes()
        with mock.patch.object(RUNNER, 'command_result', side_effect=AssertionError('completed build must not relink')):
            code, report = self.execute('--resume')
        self.assertEqual(code, 0, report)
        self.assertEqual(report['objects_compiled'], 0)
        self.assertEqual((self.output / 'compiled-manifest.json').read_bytes(), previous)

    def test_changed_generated_source_refuses_resume(self):
        self.pause_after_one_object()
        self.mutate(self.output / 'source/extra.c')
        code, report = self.execute('--resume')
        self.assertNotEqual(code, 0, report)
        self.assertEqual(report['status'], 'rejected')
        self.assertEqual(report['commands'], [])
        self.assertFalse((self.output / 'compiled-manifest.json').exists())

    def test_changed_header_refuses_resume(self):
        self.pause_after_one_object()
        self.mutate(self.output / 'source/recomp.h')
        code, report = self.execute('--resume')
        self.assertNotEqual(code, 0, report)
        self.assertEqual(report['commands'], [])
        self.assertFalse((self.output / 'compiled-manifest.json').exists())

    def test_changed_object_refuses_resume(self):
        self.pause_after_one_object()
        path = next((self.output / 'receipts').glob('*.json'))
        receipt = RUNNER.read_canonical(path)
        self.mutate(self.output / receipt['object']['path'])
        code, report = self.execute('--resume')
        self.assertNotEqual(code, 0, report)
        self.assertEqual(report['reason'], 'compiled_object_changed')
        self.assertEqual(report['commands'], [])

    def test_receipt_scalar_aliases_cannot_qualify_reuse(self):
        """CodexAstraUlt: Numeric equality cannot replace exact receipt JSON types."""
        self.pause_after_one_object()
        path = next((self.output / 'receipts').glob('*.json'))
        original = RUNNER.read_canonical(path)
        for field, value in (('job', True), ('object', float(original['object']['bytes'])), ('elf', 0)):
            with self.subTest(field=field):
                receipt = copy.deepcopy(original)
                if field == 'job':
                    self.assertEqual(receipt['job']['index'], 1)
                    receipt['job']['index'] = value
                elif field == 'object':
                    receipt['object']['bytes'] = value
                else:
                    receipt['elf']['library_loaded'] = value
                path.write_bytes(RUNNER.PREP.canonical(receipt))
                code, report = self.execute('--resume')
                self.assertNotEqual(code, 0, report)
                self.assertEqual(report['commands'], [])
                self.assertFalse((self.output / 'compiled-manifest.json').exists())
        path.write_bytes(RUNNER.PREP.canonical(original))

    def test_metadata_admission_reserves_report_at_exact_boundary(self):
        """CodexAstraUlt: A one-byte shortage stops before metadata or temporary publication."""
        value = {'kind': 'original_metadata_boundary', 'status': 'compiled'}
        encoded = RUNNER.PREP.canonical(value)
        for shortage in (0, 1):
            with self.subTest(shortage=shortage):
                directory = self.root / f'metadata-boundary-{shortage}'
                directory.mkdir()
                retained = directory / 'retained.bin'
                retained.write_bytes(b'keep')
                output = directory / 'compiled-manifest.json'
                with mock.patch.object(RUNNER, 'REPORT_RESERVE', 8):
                    ceiling = 4 + len(encoded) + 8 - shortage
                    if shortage:
                        with self.assertRaisesRegex(ValueError, 'compile_metadata_exceeds_output_allowance'):
                            RUNNER.publish(output, value, directory, ceiling)
                        self.assertEqual({path.name for path in directory.iterdir()}, {'retained.bin'})
                    else:
                        RUNNER.publish(output, value, directory, ceiling)
                        self.assertEqual(output.read_bytes(), encoded)
                self.assertEqual(retained.read_bytes(), b'keep')

    def test_final_manifest_requires_remaining_output_allowance(self):
        """CodexAstraUlt: A linked/audited library cannot bypass final metadata admission."""
        original = RUNNER.publish
        observed = []
        def shortage(path, value, root=None, ceiling=None):
            if path.name != 'compiled-manifest.json':
                return original(path, value, root, ceiling)
            observed.append(value)
            used = ceiling - RUNNER.REPORT_RESERVE - len(RUNNER.PREP.canonical(value)) + 1
            with mock.patch.object(RUNNER, 'output_size', return_value=used):
                return original(path, value, root, ceiling)
        with mock.patch.object(RUNNER, 'publish', side_effect=shortage):
            code, report = self.execute()
        self.assertNotEqual(code, 0, report)
        self.assertEqual(report['reason'], 'compile_metadata_exceeds_output_allowance')
        self.assertEqual(report['stage'], 'audit')
        self.assertEqual(report['objects_ready'], 3)
        self.assertEqual(len(observed), 1)
        self.assertTrue((self.output / observed[0]['library']['path']).is_file())
        self.assertEqual(len(list((self.output / 'receipts').glob('*.json'))), 3)
        self.assertFalse((self.output / 'compiled-manifest.json').exists())
        self.assertEqual(tree_bytes(self.preparation), self.before)

    def test_changed_compiler_or_plan_refuses_resume(self):
        self.pause_after_one_object()
        compiler = copy.deepcopy(self.compiler)
        compiler['identity']['version'] += '\nOriginal control mutation'
        with mock.patch.object(RUNNER.PROCESS, 'inspect_compiler', return_value=compiler):
            code, report = self.execute('--resume')
        self.assertNotEqual(code, 0, report)
        self.assertEqual(report['reason'], 'compile_plan_changed_use_a_new_output')
        plan = RUNNER.read_canonical(self.output / 'compile-plan.json')
        plan['contract']['compile_flags'].append('-ffast-math')
        (self.output / 'compile-plan.json').write_bytes(RUNNER.PREP.canonical(plan))
        code, report = self.execute('--resume')
        self.assertNotEqual(code, 0, report)
        self.assertEqual(report['commands'], [])

    def test_changed_preparation_refuses_resume_without_overwriting_prior_evidence(self):
        first = self.pause_after_one_object()
        previous = Path(first['report_path']).read_bytes()
        self.mutate(self.preparation / 'prepared/generated/program.c')
        code, report = self.execute('--resume')
        self.assertNotEqual(code, 0, report)
        self.assertEqual(report['commands'], [])
        self.assertEqual(Path(first['report_path']).read_bytes(), previous)

    def test_link_failure_cannot_publish_compiled_manifest(self):
        original = RUNNER.PROCESS.run_command
        def failing_link(command, *args, **kwargs):
            if '-shared' not in command:
                return original(command, *args, **kwargs)
            return {'outcome': 'completed', 'exit_code': 1, 'elapsed_seconds': 0.0,
                    'log_tail': 'original fixture link rejection', 'log_bytes_seen': 31, 'limits': {}}
        with mock.patch.object(RUNNER.PROCESS, 'run_command', side_effect=failing_link):
            code, report = self.execute()
        self.assertEqual(code, 2, report)
        self.assertEqual(report['reason'], 'compiler_exit_1')
        self.assertEqual(report['objects_ready'], 3)
        self.assertFalse((self.output / 'compiled-manifest.json').exists())
        self.assertEqual(tree_bytes(self.preparation), self.before)

    def test_static_audit_rejection_cannot_publish_compiled_manifest(self):
        with mock.patch.object(RUNNER.ELF, 'audit_library', side_effect=ValueError('original fixture audit rejection')):
            code, report = self.execute()
        self.assertNotEqual(code, 0, report)
        self.assertEqual(report['stage'], 'audit')
        self.assertEqual(report['reason'], 'original fixture audit rejection')
        self.assertFalse((self.output / 'compiled-manifest.json').exists())
        self.assertEqual(tree_bytes(self.preparation), self.before)

    def test_timeout_and_interruption_create_no_object_receipt(self):
        for index, outcome in enumerate(('timeout', 'interrupted')):
            with self.subTest(outcome=outcome):
                self.output = self.root / f'failed-command-{index}'
                process = {'outcome': outcome, 'exit_code': -15, 'elapsed_seconds': 0.0,
                           'log_tail': 'original fixture cancellation', 'log_bytes_seen': 29, 'limits': {}}
                with mock.patch.object(RUNNER.PROCESS, 'run_command', return_value=process):
                    code, report = self.execute()
                self.assertEqual(code, 130 if outcome == 'interrupted' else 2)
                self.assertEqual(report['objects_ready'], 0)
                self.assertEqual(list((self.output / 'receipts').iterdir()), [])
                self.assertFalse((self.output / 'compiled-manifest.json').exists())

    def test_existing_output_and_invalid_flags_preserve_owner_files(self):
        self.output.mkdir()
        marker = self.output / 'owner.txt'
        marker.write_text('preserve')
        code, report = self.execute()
        self.assertNotEqual(code, 0, report)
        self.assertEqual(marker.read_text(), 'preserve')
        self.assertEqual({path.name for path in self.output.iterdir()}, {'owner.txt'})
        for flags in (('--batch-seconds', 'nan'), ('--memory-mib', '255'), ('--output-mib', '8193'),
                      ('--cpu-seconds', '0'), ('--resume', '--resume')):
            with self.subTest(flags=flags), contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
                RUNNER.parse_args(['--preparation', str(self.preparation), '--output', str(self.output), *flags])


class RealPreparedCompilationTests(unittest.TestCase):
    """CodexAstraUlt: Actual original NCCH emission reaches a statically bound host library."""

    def prepared_original(self, root):
        source = root / 'original.cxi'
        source.write_bytes(PREP_FIXTURES.original_ncch())
        output = root / 'preparation'
        args = RUNNER.PREP.parse_args(['--input', str(source), '--output', str(output), '--worker', str(REAL_WORKER)])
        code, report = RUNNER.PREP.run(args)
        self.assertEqual(code, 0, report)
        return source, output

    def test_real_preparation_compiles_without_execution(self):
        with tempfile.TemporaryDirectory(prefix='droidds-real-native-compile-') as temporary:
            root = Path(temporary)
            source, preparation = self.prepared_original(root)
            before = tree_bytes(preparation)
            output = root / 'native'
            values = ['--preparation', str(preparation), '--output', str(output), '--output-mib', '64']
            if REAL_CC:
                values += ['--cc', str(REAL_CC)]
            with contextlib.redirect_stdout(io.StringIO()):
                code, report = RUNNER.run(RUNNER.parse_args(values))
            self.assertEqual(code, 0, report)
            manifest = RUNNER.read_canonical(output / 'compiled-manifest.json')
            self.assertGreaterEqual(manifest['elf']['entry_count'], 1)
            self.assertFalse(manifest['library_loaded'])
            self.assertFalse(manifest['guest_execution_performed'])
            self.assertFalse(manifest['runtime_binding_enforced'])
            self.assertEqual(tree_bytes(preparation), before)
            self.assertEqual(source.read_bytes(), PREP_FIXTURES.original_ncch())

    def test_real_preparation_source_tampering_is_rejected_before_compiler(self):
        with tempfile.TemporaryDirectory(prefix='droidds-real-native-reject-') as temporary:
            root = Path(temporary)
            _, preparation = self.prepared_original(root)
            generated = next((preparation / 'prepared/generated').glob('*.c'))
            generated.write_bytes(generated.read_bytes() + b'/* altered original control */\n')
            args = RUNNER.parse_args(['--preparation', str(preparation), '--output', str(root / 'native'), '--output-mib', '64'])
            with mock.patch.object(RUNNER.PROCESS, 'inspect_compiler', side_effect=AssertionError('bad preparation must not reach compiler')):
                code, report = RUNNER.run(args)
            self.assertNotEqual(code, 0, report)
            self.assertFalse((root / 'native/compiled-manifest.json').exists())


def load_tests(loader, tests, pattern):
    """CodexAstraUlt: Real preparation integration requires an explicitly built worker."""
    suite = loader.loadTestsFromTestCase(CompileCoordinatorTests)
    if REAL_WORKER is not None:
        suite.addTests(loader.loadTestsFromTestCase(RealPreparedCompilationTests))
    return suite


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument('--worker', type=Path)
    parser.add_argument('--cc', type=Path)
    args, remaining = parser.parse_known_args()
    if args.worker:
        REAL_WORKER = args.worker.resolve(strict=True)
    if args.cc:
        REAL_CC = args.cc.resolve(strict=True)
    unittest.main(argv=[__file__, *remaining])
