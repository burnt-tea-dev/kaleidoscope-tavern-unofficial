"""Small input/output-boundary regressions; no geometry or GUI testing."""
import importlib.util
import json
import os
import subprocess
import zipfile
from unittest.mock import patch
from pathlib import Path
import sys
import tempfile
import unittest

sys.dont_write_bytecode = True
spec = importlib.util.spec_from_file_location("decor_verifier", Path(__file__).with_name("validate_evidence.py"))
verifier = importlib.util.module_from_spec(spec)
spec.loader.exec_module(verifier)


class BoundaryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="decor-boundaries-")
        self.root = Path(self.temp.name)

    def tearDown(self):
        self.temp.cleanup()

    def inventory_fixture(self):
        root = self.root / "evidence"
        root.mkdir()
        (root / "payload.txt").write_text("unchanged\n")
        (root / "verification.json").write_text("{}\n")
        row = {"file": "payload.txt", "bytes": 10, "sha256": verifier.sha(root / "payload.txt")}
        (root / "artifact-sha256.json").write_text(json.dumps({"files": [row]}))
        return root, row

    def test_relative_path_rejections(self):
        for name in ["/absolute", "../escape", "a/../escape", "a\\escape", "C:/escape", "C:escape", "a:escape", "a//b", "./file"]:
            with self.subTest(name=name), self.assertRaises(ValueError):
                verifier.relative_file(self.root, name)

    def test_resolved_symlink_escape(self):
        root = self.root / "declared"
        root.mkdir()
        (root / "escape").symlink_to(self.root, target_is_directory=True)
        with self.assertRaises(ValueError):
            verifier.relative_file(root, "escape/new.txt")

    def test_complete_inventory(self):
        root, _ = self.inventory_fixture()
        verifier.verify_inventory(root)

    def test_duplicate_inventory(self):
        root, row = self.inventory_fixture()
        (root / "artifact-sha256.json").write_text(json.dumps({"files": [row, row]}))
        with self.assertRaises(ValueError):
            verifier.verify_inventory(root)

    def test_omitted_inventory(self):
        root, _ = self.inventory_fixture()
        (root / "artifact-sha256.json").write_text(json.dumps({"files": []}))
        with self.assertRaises(ValueError):
            verifier.verify_inventory(root)

    def test_inventory_file_symlink_escape(self):
        root = self.root / "evidence"
        root.mkdir()
        outside = self.root / "outside.json"
        outside.write_text("{}")
        (root / "artifact-sha256.json").symlink_to(outside)
        with self.assertRaises(ValueError):
            verifier.verify_inventory(root)

    def test_report_alias_into_evidence(self):
        alias = self.root / "alias"
        alias.symlink_to(verifier.HERE, target_is_directory=True)
        with self.assertRaises(ValueError):
            verifier.output_location(alias / "new-report.json")

    def test_report_inside_checkout(self):
        repo = self.root / "checkout"
        (repo / ".git").mkdir(parents=True)
        (repo / ".git/HEAD").write_text("ref: refs/heads/main\n")
        for supplied_repository in [None, repo]:
            with self.assertRaises(ValueError):
                verifier.output_location(repo / "runtime/new-report.json", supplied_repository)

    def test_report_existing_file_and_safe_new_file(self):
        existing = self.root / "existing.json"
        existing.write_text("do not overwrite")
        with self.assertRaises(FileExistsError):
            verifier.output_location(existing)
        self.assertEqual(existing.read_text(), "do not overwrite")
        target = verifier.output_location(self.root / "new-report.json")
        with target.open("x") as stream:
            stream.write("{}\n")
        self.assertEqual(target.read_text(), "{}\n")
        with self.assertRaises(FileExistsError):
            verifier.output_location(target)

    def test_optimization_rejected_before_output_creation(self):
        output = self.root / 'should-not-exist'
        result = subprocess.run([sys.executable, '-O', str(verifier.HERE / 'validate_evidence.py'), '--work-dir', str(output)], capture_output=True, text=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('without Python optimization', result.stderr)
        self.assertFalse(output.exists())

    def test_symlink_inside_inventory_rejected(self):
        root, _ = self.inventory_fixture()
        (root / 'alias').symlink_to(root / 'payload.txt')
        with self.assertRaises(ValueError):
            verifier.verify_inventory(root)

    def test_duplicate_zip_members_rejected(self):
        root = self.root / 'package'
        (root / 'archives').mkdir(parents=True)
        archives = []
        import warnings
        for i in range(8):
            path = root / 'archives' / f'{i}.zip'
            with zipfile.ZipFile(path, 'w') as archive, warnings.catch_warnings():
                warnings.simplefilter('ignore')
                archive.writestr('review/duplicate.txt', 'payload')
                archive.writestr('review/duplicate.txt', 'payload')
            archives.append({'file':f'archives/{i}.zip','bytes':path.stat().st_size,'sha256':verifier.sha(path),'entries':[{'file':'review/duplicate.txt','bytes':7,'sha256':verifier.digest(b'payload')}]})
        (root / 'archive-entries.json').write_text(json.dumps(archives))
        work = self.root / 'extraction'
        work.mkdir()
        with patch.object(verifier, 'HERE', root), self.assertRaises(ValueError):
            verifier.extract_archives(work)
        self.assertFalse((work / 'review/duplicate.txt').exists())

    def test_undeclared_historical_root_rejected(self):
        sys.path.insert(0, str(verifier.HERE / 'audits'))
        from portable_context import relocate
        with self.assertRaises(ValueError):
            relocate('/workspace/scratch/f31f84fbb9ff/unrelated/private.json', self.root)
        with self.assertRaises(ValueError):
            relocate('/workspace/scratch/f31f84fbb9ff/tavern-next-decor-review-20261108/../escape', self.root)

    def test_exact_typed_json_values(self):
        compare = verifier.same_json_values_and_types
        self.assertTrue(compare({"a": 1, "b": [False, 1.0]}, {"b": [False, 1.0], "a": 1}))
        for left, right in [(True, 1), (1, 1.0), ([1, 2], [2, 1]), (0.0625, 0.0625000001)]:
            self.assertFalse(compare(left, right))


if __name__ == "__main__":
    unittest.main()
