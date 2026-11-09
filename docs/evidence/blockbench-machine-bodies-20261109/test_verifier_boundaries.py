"""Targeted negative tests for path, ZIP, output and exact-comparison boundaries."""
import importlib.util
import json
import math
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
import warnings
import zipfile

sys.dont_write_bytecode = True
spec = importlib.util.spec_from_file_location('machine_body_verifier', Path(__file__).with_name('validate_evidence.py'))
v = importlib.util.module_from_spec(spec)
spec.loader.exec_module(v)


class Boundaries(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='machine-body-boundaries-')
        self.root = Path(self.temp.name)

    def tearDown(self):
        self.temp.cleanup()

    def inventory(self):
        root = self.root / 'evidence'
        root.mkdir()
        raw = b'unchanged\n'
        (root / 'payload').write_bytes(raw)
        row = {'file': 'payload', 'bytes': len(raw), 'sha256': v.digest(raw), 'git_blob_sha1': v.gitblob(raw)}
        (root / 'artifact-sha256.json').write_text(json.dumps({'files': [row]}))
        return root, row

    def test_relative_paths(self):
        for name in ['/absolute', '../escape', 'a/../escape', 'a\\escape', 'C:/escape', 'C:escape', 'a:escape', 'a//b', './file', 'a/', 'a\0b', '']:
            with self.subTest(name=name), self.assertRaises(ValueError):
                v.relative_file(self.root, name)

    def test_symlink_members_even_inside_root(self):
        (self.root / 'target').write_text('bytes')
        (self.root / 'link').symlink_to(self.root / 'target')
        (self.root / 'directory-link').symlink_to(self.root, target_is_directory=True)
        for name in ['link', 'directory-link/target']:
            with self.assertRaises(ValueError):
                v.relative_file(self.root, name)

    def test_complete_inventory(self):
        root, _ = self.inventory()
        v.verify_inventory(root)

    def test_duplicate_inventory(self):
        root, row = self.inventory()
        (root / 'artifact-sha256.json').write_text(json.dumps({'files': [row, row]}))
        with self.assertRaises(ValueError):
            v.verify_inventory(root)

    def test_missing_inventory(self):
        root, _ = self.inventory()
        (root / 'artifact-sha256.json').write_text('{"files": []}')
        with self.assertRaises(ValueError):
            v.verify_inventory(root)

    def test_altered_payload(self):
        root, _ = self.inventory()
        (root / 'payload').write_text('changed\n')
        with self.assertRaises(AssertionError):
            v.verify_inventory(root)

    def test_inventory_symlink(self):
        root, _ = self.inventory()
        (root / 'link').symlink_to(root / 'payload')
        with self.assertRaises(ValueError):
            v.verify_inventory(root)

    def test_duplicate_json_keys(self):
        path = self.root / 'duplicate.json'
        path.write_text('{"x": 1, "x": 2}')
        with self.assertRaises(ValueError):
            v.read(path)

    def test_nonfinite_json(self):
        path = self.root / 'nonfinite.json'
        for token in ['NaN', 'Infinity', '-Infinity', '1e999', '-1e999']:
            with self.subTest(token=token):
                path.write_text('{"x": ' + token + '}')
                with self.assertRaises(ValueError):
                    v.read(path)

    def test_finite_json_preserves_standard_floats(self):
        path = self.root / 'finite.json'
        path.write_text('[0.0, -0.0, 1e2, 1e-3, 1]')
        parsed = v.read(path)
        self.assertEqual(parsed, [0.0, -0.0, 100.0, 0.001, 1])
        self.assertEqual([type(value) for value in parsed], [float, float, float, float, int])
        self.assertEqual(math.copysign(1.0, parsed[1]), -1.0)

    def test_numeric_overflow_rejected_by_cli(self):
        for index, token in enumerate(['1e999', '-1e999']):
            with self.subTest(token=token):
                package = self.root / ('package-' + str(index))
                shutil.copytree(v.HERE, package)
                inventory = package / 'artifact-sha256.json'
                inventory.write_text(inventory.read_text().replace(
                    '{', '{"numeric_overflow_probe": ' + token + ',', 1))
                receipt = self.root / ('receipt-' + str(index) + '.json')
                result = subprocess.run(
                    [sys.executable, '-B', str(package / 'validate_evidence.py'), '--report', str(receipt)],
                    text=True, capture_output=True)
                self.assertNotEqual(result.returncode, 0)
                self.assertIn('Non-finite JSON number: ' + token, result.stderr)
                self.assertFalse(receipt.exists())

    def test_output_in_checkout_or_alias(self):
        repo = self.root / 'checkout'
        (repo / '.git').mkdir(parents=True)
        (repo / '.git/HEAD').write_text('ref: refs/heads/main\n')
        alias = self.root / 'alias'
        alias.symlink_to(repo, target_is_directory=True)
        for path in [repo / 'new', alias / 'new', v.HERE / 'new', repo / 'sub/../new']:
            with self.subTest(path=str(path)), self.assertRaises(ValueError):
                v.output_location(path)

    def test_output_in_worktree(self):
        repo = self.root / 'checkout'
        repo.mkdir()
        (repo / '.git').write_text('gitdir: /some/common/directory\n')
        with self.assertRaises(ValueError):
            v.output_location(repo / 'new')

    def test_existing_outputs_and_safe_new(self):
        path = self.root / 'output.json'
        self.assertEqual(v.output_location(path), path)
        path.write_text('do not overwrite')
        with self.assertRaises(FileExistsError):
            v.output_location(path)
        self.assertEqual(path.read_text(), 'do not overwrite')
        with self.assertRaises(FileExistsError):
            v.output_location(self.root)

    def test_optimized_execution_rejected(self):
        for switch, extra_env in [('-O', {}), ('-OO', {}), ('', {'PYTHONOPTIMIZE': '1'})]:
            path = self.root / ('output' + switch)
            command = [sys.executable] + ([switch] if switch else []) + [str(v.HERE / 'validate_evidence.py'), '--work-dir', str(path)]
            result = subprocess.run(command, env={**os.environ, **extra_env}, text=True, capture_output=True)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn('without Python optimization', result.stderr)
            self.assertFalse(path.exists())

    def zip_fixture(self, alteration):
        root = self.root / 'package'
        (root / 'archives').mkdir(parents=True)
        archives = []
        for i in range(2):
            path = root / 'archives' / f'{i}.zip'
            name = f'review/payload-{i}'
            if alteration == 'cross-duplicate':
                name = 'review/duplicate'
            if i == 0 and alteration == 'traversal':
                name = 'review/../../escape'
            if i == 0 and alteration == 'absolute':
                name = '/absolute'
            if i == 0 and alteration == 'backslash':
                name = 'review\\escape'
            info = zipfile.ZipInfo(name)
            info.external_attr = (0o120777 if i == 0 and alteration == 'symlink' else 0o100644) << 16
            raw = b'payload'
            with zipfile.ZipFile(path, 'w') as z, warnings.catch_warnings():
                warnings.simplefilter('ignore')
                z.writestr(info, raw)
                if i == 0 and alteration == 'duplicate-member':
                    z.writestr(info, raw)
            entry = {'file': name, 'bytes': 7, 'sha256': v.digest(raw), 'git_blob_sha1': v.gitblob(raw)}
            entries = [entry]
            if i == 0 and alteration == 'missing-inventory':
                entries = []
            if i == 0 and alteration == 'duplicate-inventory':
                entries = [entry, entry]
            if i == 0 and alteration == 'missing-member':
                entries = [{**entry, 'file': 'review/not-present'}]
            if i == 0 and alteration == 'wrong-hash':
                entries = [{**entry, 'sha256': '0' * 64}]
            b = path.read_bytes()
            archives.append({'file': 'archives/' + path.name, 'bytes': len(b), 'sha256': v.digest(b), 'git_blob_sha1': v.gitblob(b), 'entries': entries})
        (root / 'archive-entries.json').write_text(json.dumps(archives))
        work = self.root / 'extraction'
        work.mkdir()
        return root, work

    def test_malformed_archives_rejected_before_extraction(self):
        for alteration in ['cross-duplicate', 'traversal', 'absolute', 'backslash', 'symlink', 'duplicate-member', 'missing-inventory', 'duplicate-inventory', 'missing-member', 'wrong-hash']:
            with self.subTest(alteration=alteration):
                # Each case gets a separate fixture and the entire archive is inspected first.
                base = self.root
                self.root = base / alteration
                self.root.mkdir()
                root, work = self.zip_fixture(alteration)
                with patch.object(v, 'HERE', root), self.assertRaises((ValueError, AssertionError)):
                    v.extract_archives(work)
                self.assertEqual(list(work.iterdir()), [])
                self.root = base

    def test_explicit_historical_relocation(self):
        sys.path.insert(0, str(v.HERE / 'audits'))
        from portable_context import relocate, HISTORICAL_ROOT
        self.assertEqual(relocate(HISTORICAL_ROOT + '/scenes/a.bbmodel', self.root), str(self.root / 'scenes/a.bbmodel'))
        for path in ['/workspace/unrelated/private.json', HISTORICAL_ROOT + '/../escape', HISTORICAL_ROOT + '/a//b']:
            with self.assertRaises(ValueError):
                relocate(path, self.root)

    def test_exact_json_values_types_array_order(self):
        self.assertTrue(v.same_json_values_and_types({'a': 1, 'b': [False, 1.0]}, {'b': [False, 1.0], 'a': 1}))
        for left, right in [(True, 1), (1, 1.0), ([1, 2], [2, 1]), (0.0625, 0.0625000001), (-0.0, 0.0)]:
            self.assertFalse(v.same_json_values_and_types(left, right))


if __name__ == '__main__':
    unittest.main()
