"""Exercise real archive assembly and exact manifest-only release admission."""
import copy
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest
import zipfile

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from family_bundle import assemble, packs
from family_update.upstream_manifest_compatibility import compile_pair, reviewed_pair


class UpstreamManifestCompatibility(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory(); self.addCleanup(temp.cleanup)
        self.root = Path(temp.name); self.archive = self.root / 'author.mcaddon'
        with zipfile.ZipFile(self.archive, 'w') as z:
            for side, kind, other in [('BP', 'data', 'RP'), ('RP', 'resources', 'BP')]:
                manifest = {'header': {'uuid': side, 'version': [1, 0, 0], 'min_engine_version': [1, 21, 60]},
                            'modules': [{'type': kind, 'uuid': side + '-module', 'version': [1, 0, 0]}],
                            'dependencies': [{'uuid': other, 'version': [1, 0, 0]}]}
                if side == 'RP': manifest['capabilities'] = ['pbr']
                z.writestr(side + '/manifest.json', json.dumps(manifest))
                z.writestr(side + '/unchanged-content.bin', b'author asset and gameplay fixture')
        with zipfile.ZipFile(self.archive) as z: self.author = list(packs(z))
        _, evidence = compile_pair(self.author, [1, 0, 10001], [1, 21, 120])
        self.upstream = {'name': 'Fixture', 'project_id': 1, 'file_id': 2,
                         'sha256': hashlib.sha256(self.archive.read_bytes()).hexdigest(),
                         'packs': [{'uuid': side, 'version': [1, 0, 0]} for side in ['BP', 'RP']],
                         'manifest_compatibility_release': 'fixture-1.0.10001'}
        self.release = {key: self.upstream[key] for key in ['project_id', 'file_id', 'sha256']}
        self.release.update(version=[1, 0, 10001], resource_min_engine=[1, 21, 120], **evidence)
        self.releases = {'fixture-1.0.10001': self.release}

    def test_real_assembly_versions_pair_and_preserves_author_content(self):
        original = self.archive.read_bytes()
        lock = {'owned': [], 'upstream': [self.upstream], 'upstream_manifest_releases': self.releases,
                'order': {'behavior': ['BP'], 'resource': ['RP']}}
        receipt = assemble(lock, {}, [self.archive], self.root / 'out')
        for row in receipt['packs']:
            root = self.root / 'out' / (row['side'] + '_packs') / row['uuid']
            self.assertEqual((root / 'unchanged-content.bin').read_bytes(), b'author asset and gameplay fixture')
            manifest = json.loads((root / 'manifest.json').read_text())
            self.assertEqual(manifest['header']['version'], [1, 0, 10001])
            self.assertTrue(all(m['version'] == [1, 0, 10001] for m in manifest['modules']))
            self.assertEqual(manifest['dependencies'][0]['version'], [1, 0, 10001])
            self.assertFalse(row['source']['official_author_release'])
            self.assertEqual(row['source']['manifest_compatibility']['release'], 'fixture-1.0.10001')
            if row['side'] == 'resource': self.assertEqual(manifest['header']['min_engine_version'], [1, 21, 120])
        self.assertEqual(self.archive.read_bytes(), original)

    def test_unreviewed_payload_or_archive_rejects_before_output(self):
        for field in ['sha256', 'source_trees', 'output_trees', 'patched_manifests']:
            release = copy.deepcopy(self.release); release[field] = 'unreviewed'
            with self.subTest(field=field), self.assertRaises(ValueError):
                reviewed_pair(self.upstream, self.author, {'fixture-1.0.10001': release})

    def test_reused_identity_and_invented_pbr_support_reject(self):
        with self.assertRaises(ValueError): compile_pair(self.author, [1, 0, 0], [1, 21, 120])
        changed = copy.deepcopy(self.author)
        del changed[1][0]['capabilities']
        with self.assertRaises(ValueError): compile_pair(changed, [1, 0, 10001], [1, 21, 120])


if __name__ == '__main__': unittest.main()
