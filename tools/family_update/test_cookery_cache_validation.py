"""Reject unrelated private changes and reused/falsely accepted native records."""
import copy
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from family_update import cookery_cache_validation as m
from family_bundle import renderer_source_version


class CacheBoundary(unittest.TestCase):
    def setUp(self):
        self.old = {'repository': m.LOGICAL, 'version': m.OLD_VERSION, 'source_trees': {}}
        self.new = {'repository': m.LOGICAL, 'version': m.NEW_VERSION, 'source_trees': {}, 'packs': {},
                    'retained_renderer_profile': {'source_commit': m.PREVIOUS, 'spec_sha256': '292e337a073ea713c22c84c66f85a2c8cb9d2d5c453c308b1569107d2656b703'}}
        self.before, self.after, self.manifests = {}, {}, {}
        for side, label in [('BP', 'behavior'), ('RP', 'resource')]:
            uid, other = side.lower(), ('rp' if side == 'BP' else 'bp')
            old = {'header': {'uuid': uid, 'name': 'family 1.0.32 ' + side, 'version': m.OLD_VERSION},
                   'modules': [{'uuid': uid + '-module', 'version': m.OLD_VERSION}],
                   'dependencies': [{'uuid': other, 'version': m.OLD_VERSION}, {'module_name': 'server', 'version': '2.7.0'}]}
            new = copy.deepcopy(old)
            new['header'].update(name='family 1.0.33 ' + side, version=m.NEW_VERSION)
            new['modules'][0]['version'] = new['dependencies'][0]['version'] = m.NEW_VERSION
            rows = {'manifest.json': 'old-manifest', 'retained-gameplay': 'unchanged-source'}
            current = {**rows, 'manifest.json': 'new-manifest'}
            if side == 'BP': current[m.SPEC] = 'reviewed-cache-spec'
            self.before[uid] = {'version': m.OLD_VERSION, 'side': label, 'files': rows}
            self.after[uid] = {'version': m.NEW_VERSION, 'side': label, 'files': current}
            self.old['source_trees'][side], self.new['source_trees'][side] = m.tree(rows), m.tree(current)
            self.new['packs'][side] = {'uuid': uid}
            self.manifests[side] = (old, new)

    def verify(self):
        m.conserved_packs(self.before, self.after, self.old, self.new, self.manifests)

    def test_identity_and_one_cache_declaration_keep_every_old_feature(self):
        self.verify()

    def test_even_a_new_frozen_tree_cannot_hide_gameplay_or_an_extra_file(self):
        for mode in ['mutate', 'add', 'remove']:
            with self.subTest(mode=mode):
                original = copy.deepcopy(self.after['bp']['files'])
                if mode == 'mutate': self.after['bp']['files']['retained-gameplay'] = 'different'
                elif mode == 'add': self.after['bp']['files']['other-patch.js'] = 'new'
                else: self.after['bp']['files'].pop('retained-gameplay')
                self.new['source_trees']['BP'] = m.tree(self.after['bp']['files'])
                with self.assertRaises(AssertionError): self.verify()
                self.after['bp']['files'] = original
                self.new['source_trees']['BP'] = m.tree(original)

    def test_dependency_uuid_and_retained_renderer_profile_cannot_change(self):
        self.manifests['BP'][1]['dependencies'][1]['version'] = 'different-api'
        with self.assertRaisesRegex(AssertionError, 'manifest'): self.verify()
        self.manifests['BP'][1]['dependencies'][1]['version'] = '2.7.0'
        self.new['retained_renderer_profile']['source_commit'] = 'another-source'
        with self.assertRaisesRegex(AssertionError, 'renderer'): self.verify()

    def test_generic_owner_or_renderer_retention_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / 'spec.json'; p.write_text('{}')
            with self.assertRaises(SystemExit): renderer_source_version(self.new, {'owner_version': m.OLD_VERSION}, p)
            self.new['version'] = [1, 0, 34]
            with self.assertRaises(SystemExit): renderer_source_version(self.new, {'owner_version': m.OLD_VERSION}, p)

    def test_native_binding_requires_current_candidate_and_two_fresh_phases(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); candidate = root / 'candidate'; candidate.mkdir()
            receipt = {'packs': [{'uuid': 'private', 'files': {'same': 'bytes'}, 'source': {'repository': m.LOGICAL}}]}
            (candidate / 'family-receipt.json').write_text(json.dumps(receipt))
            digest = hashlib.sha256((candidate / 'family-receipt.json').read_bytes()).hexdigest()
            static = {'candidate_receipt_sha256': digest, 'packs': {'private': {'same': 'bytes'}}}
            (root / 'cookery-cache-static-validation.json').write_text(json.dumps(static))
            valid = {'candidate_receipt_sha256': digest, 'fresh_stopped_backup': True, 'exact_files_checked': True,
                     'bds': True, 'saved_world_migration': True, 'client': False, 'simulated_players': False,
                     'runs': [{'phase': 'first', 'ok': True, 'errors': []}, {'phase': 'restart', 'ok': True, 'errors': []}]}
            (root / 'saved-world-report.json').write_text(json.dumps(valid))
            with patch.multiple(m, CONFIG={'extension_cache_validation': 'explicit'}, R=root, C=candidate,
                                atomic=lambda p, value: p.write_text(json.dumps(value))):
                for key, value in [('candidate_receipt_sha256', 'prior-candidate'), ('fresh_stopped_backup', False), ('bds', False), ('client', True), ('simulated_players', True), ('runs', valid['runs'][:1])]:
                    with self.subTest(key=key), self.assertRaises(AssertionError): m.bind_native(receipt, {**valid, key: value})
                m.bind_native(receipt, valid)
                result = json.loads((root / 'cookery-cache-native-validation.json').read_text())
                self.assertFalse(result['client']); self.assertEqual(result['candidate_receipt_sha256'], digest)


if __name__ == '__main__': unittest.main()
