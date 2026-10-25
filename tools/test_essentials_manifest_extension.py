"""Actual official manifests keep scripts/assets outside the compatibility delta."""
import copy
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import essentials_manifest_extension as extension
import stable_host_profiles as profiles


class EssentialsManifestCompatibility(unittest.TestCase):
    def setUp(self):
        fixture = json.loads((Path(__file__).parent / 'fixtures/essentials-183-manifests.json').read_bytes())
        self.raw = {side: text.encode('utf-8') for side, text in fixture['manifests'].items()}
        self.spec, self.changed = extension.compile_spec(self.raw, [1, 0, 66], [1, 8, 10066])
        profile = {'id': self.spec['id'], 'host_uuid': self.spec['host_uuid'],
                   'archive_sha256': extension.ARCHIVE, 'owner_version': [1, 0, 66],
                   'admission': profiles.CURATED, 'spec_sha256': profiles.declaration_sha(self.spec),
                   'source_owner': 'upstream', 'required_extensions': [], 'copies': {}}
        self.enterContext(patch.dict(profiles.PROFILES, {'essentials-current-fixture': profile}))
        self.source = {'owner': 'upstream', 'project_id': 1285412, 'file_id': 8837761,
                       'archive_sha256': extension.ARCHIVE, 'reviewed_extensions': []}
        temporary = tempfile.TemporaryDirectory(); self.addCleanup(temporary.cleanup)
        self.roots = {side: Path(temporary.name) / side for side in self.raw}
        for side, root in self.roots.items():
            root.mkdir(); (root / 'manifest.json').write_bytes(self.raw[side])
            (root / 'body.bin').write_bytes(b'unchanged pack body')

    def apply(self, spec=None, source=None):
        return extension.apply_manifest_extension(
            self.spec if spec is None else spec, self.roots['BP'], self.roots['RP'],
            self.source if source is None else source, self.source, [1, 0, 66])

    def test_actual_manifests_keep_every_field_except_allocated_versions_and_rp_compatibility(self):
        for side in ['BP', 'RP']:
            before = json.loads(self.raw[side]); after = json.loads(self.changed[side + '/manifest.json'])
            self.assertEqual(after['header']['version'], [1, 8, 10066])
            for module in after['modules']:self.assertEqual(module['version'], [1, 8, 10066])
            restored = copy.deepcopy(after); restored['header']['version'] = before['header']['version']
            for new, old in zip(restored['modules'], before['modules'], strict=True):new['version'] = old['version']
            for new, old in zip(restored['dependencies'], before['dependencies'], strict=True):
                if new.get('uuid') in extension.UUIDS.values():
                    self.assertEqual(new['version'], [1, 8, 10066]);new['version'] = old['version']
            if side == 'RP':
                self.assertEqual(after['capabilities'], ['pbr'])
                self.assertEqual(after['header']['min_engine_version'], [1, 21, 120])
                del restored['capabilities']
                restored['header']['min_engine_version'] = before['header']['min_engine_version']
            self.assertEqual(restored, before)

    def test_extra_api_or_metadata_delta_and_wrong_source_are_rejected_without_writes(self):
        for side in ['BP', 'RP']:
            raw = copy.deepcopy(self.raw); manifest = json.loads(raw[side])
            if side == 'BP':
                api = next(row for row in manifest['dependencies'] if row.get('module_name') == '@minecraft/server')
                api['version'] = '999.0.0'
            else:manifest['metadata'] = {'extra': True}
            raw[side] = json.dumps(manifest).encode()
            with self.subTest(side=side), self.assertRaisesRegex(ValueError, 'clean author manifest'):
                extension.compile_spec(raw, [1, 0, 66], [1, 8, 10066])
        forged = copy.deepcopy(self.spec);forged['patched_files']['RP/manifest.json'] = 'f' * 64
        with self.assertRaisesRegex(ValueError, 'reviewed manifests'):self.apply(forged)
        with self.assertRaisesRegex(ValueError, 'clean official source'):
            self.apply(source={**self.source, 'owner': 'upstream_extended'})
        self.assertEqual({side: (root / 'manifest.json').read_bytes() for side, root in self.roots.items()}, self.raw)

    def test_pair_is_fully_validated_before_write_and_receipt_binds_real_output(self):
        path = self.roots['RP'] / 'manifest.json';path.write_bytes(self.raw['RP'] + b'\n')
        with self.assertRaisesRegex(ValueError, 'clean author manifest'):self.apply()
        self.assertEqual((self.roots['BP'] / 'manifest.json').read_bytes(), self.raw['BP'])
        path.write_bytes(self.raw['RP']);receipt = self.apply()
        for side, root in self.roots.items():
            self.assertEqual((root / 'manifest.json').read_bytes(), self.changed[side + '/manifest.json'])
            self.assertEqual((root / 'body.bin').read_bytes(), b'unchanged pack body')
            self.assertEqual(receipt['patched_files'][side + '/manifest.json'],
                             hashlib.sha256((root / 'manifest.json').read_bytes()).hexdigest())
        self.assertEqual(receipt['local_pack_version'], [1, 8, 10066])
        self.assertIs(receipt['official_author_release'], False)


if __name__ == '__main__':
    unittest.main()
