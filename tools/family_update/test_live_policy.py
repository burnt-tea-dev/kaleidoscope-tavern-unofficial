"""Ordinary readback admits exact reviewed files and rejects unexplained drift."""
from copy import deepcopy
from pathlib import Path
import sys
import unittest
from unittest.mock import Mock, patch
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from family_update import common as c

class LivePolicyTests(unittest.TestCase):
    def setUp(self):
        self.policy = {'approved_receipt': '/approved.json', 'managed_uuids': ['bp', 'rp']}
        self.receipt = {'packs': [
            {'uuid': 'bp', 'side': 'behavior', 'version': [1, 2, 3], 'files': {'main.js': 'canonical'}},
            {'uuid': 'rp', 'side': 'resource', 'version': [1, 2, 3], 'files': {'ui.json': 'canonical'}},
        ], 'order': {'behavior': ['bp'], 'resource': ['rp']}}
        self.inventory = {'packs': deepcopy(self.receipt['packs']), 'refs': {
            side: [{'pack_id': uid, 'version': [1, 2, 3]} for uid in uids]
            for side, uids in self.receipt['order'].items()}}

    def check(self, inventory, audit_ok=True):
        audit = Mock(return_value={'ok': audit_ok})
        with patch.multiple(c, CONFIG={}, W=Path('/world'),
                            Q=Path('/quality'), G={'audit': audit}), \
             patch.object(c, 'read', side_effect=[self.policy, self.receipt]), \
             patch.object(c, 'atomic') as write:
            result = c.check_live_against_policy(inventory)
            write.assert_not_called()
            audit.assert_called_once()
            return result

    def test_exact_approved_readback_does_not_write_policy(self):
        self.assertEqual(self.check(self.inventory), self.policy)

    def test_approved_files_still_require_guard(self):
        with self.assertRaisesRegex(AssertionError, 'family audit'):
            self.check(self.inventory, audit_ok=False)

    def test_postdeploy_drift_cannot_use_approved_readback(self):
        for kind in ['file', 'version', 'side', 'missing', 'extra', 'duplicate', 'reference', 'order']:
            with self.subTest(kind=kind):
                v = deepcopy(self.inventory)
                if kind == 'file': v['packs'][0]['files']['main.js'] = 'drift'
                elif kind == 'version': v['packs'][0]['version'] = [1, 2, 2]
                elif kind == 'side': v['packs'][0]['side'] = 'resource'
                elif kind == 'missing': v['packs'].pop()
                elif kind == 'extra': v['packs'].append({**v['packs'][0], 'uuid': 'foreign'})
                elif kind == 'duplicate': v['packs'].append(deepcopy(v['packs'][0]))
                elif kind == 'reference': v['refs']['behavior'][0]['version'] = [1, 2, 2]
                elif kind == 'order': v['refs']['behavior'].append(v['refs']['resource'][0])
                with self.assertRaises(AssertionError):
                    self.check(v)

if __name__ == '__main__': unittest.main()
