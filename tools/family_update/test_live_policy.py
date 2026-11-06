"""Ordinary readback admits exact reviewed files and rejects unexplained drift."""
from copy import deepcopy
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import Mock, patch
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import family_guard as guard
from family_update import common as c
from family_update import deploy_live as deploy

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
                elif kind == 'version':
                    v['packs'][0]['version'] = [1, 2, 2]
                    v['refs']['behavior'][0]['version'] = [1, 2, 2]
                elif kind == 'side': v['packs'][0]['side'] = 'resource'
                elif kind == 'missing': v['packs'].pop()
                elif kind == 'extra': v['packs'].append({**v['packs'][0], 'uuid': 'foreign'})
                elif kind == 'duplicate': v['packs'].append(deepcopy(v['packs'][0]))
                elif kind == 'reference': v['refs']['behavior'][0]['version'] = [1, 2, 2]
                elif kind == 'order': v['refs']['behavior'].append(v['refs']['resource'][0])
                with self.assertRaises(AssertionError):
                    self.check(v)

class ReviewedAdmissionTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(); self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.policy_path = self.root / 'policy.json'
        self.approved = self.root / 'current-receipt.json'
        self.incoming = []; packs = []
        for uid in ['bp', 'rp']:
            path = self.root / uid; path.mkdir()
            guard.atomic(path / 'manifest.json', {'header': {'uuid': uid, 'version': [1, 0, 2]}})
            self.incoming.append({'uuid': uid, 'version': [1, 0, 2], 'path': str(path)})
            packs.append({'uuid': uid, 'version': [1, 0, 2], 'files': guard.hashes(path),
                          'source': {'owner': 'owned', 'commit': 'committed'}})
        self.receipt = {'packs': packs, 'acceptance': dict.fromkeys(['static', 'bds', 'saved_world_migration'], True)}
        guard.atomic(self.approved, self.receipt)
        self.previous = {'managed_uuids': ['bp', 'rp'], 'family_lock_enforcement': 'required',
                         'approved_receipt': str(self.root / 'old-receipt.json'),
                         'delivery_profile': 'senluo-stable-lock-v1',
                         **{key: {'path': str(self.root / (key + '.retired.json')), 'sha256': '0' * 64}
                            for key in ['stable_lock', 'stable_gate_b', 'stable_rollback_exercise']}}

    def project(self, mode):
        previous = {**self.previous, 'family_lock_enforcement': mode}
        policy = deploy.reviewed_family_policy(previous, self.approved)
        guard.atomic(self.policy_path, policy)
        return previous, policy

    def test_current_receipt_accepts_exact_family_without_old_lock_files(self):
        previous, policy = self.project('advisory')
        self.assertTrue(guard.validate_incoming(self.incoming, self.policy_path)['matched'])
        self.assertEqual(previous['approved_receipt'], self.previous['approved_receipt'])
        self.assertEqual(policy['family_lock_enforcement'], 'advisory')

    def test_advisory_still_reports_real_current_content_difference(self):
        self.project('advisory')
        (self.root / 'bp' / 'extra.js').write_text('unreviewed change')
        with self.assertWarns(RuntimeWarning):
            result = guard.validate_incoming(self.incoming, self.policy_path)
        self.assertFalse(result['matched'])

    def test_required_still_rejects_current_identity_source_and_acceptance_changes(self):
        self.project('required')
        manifest = self.root / 'bp' / 'manifest.json'; original = manifest.read_bytes()
        for change in ['static', 'bds', 'saved_world_migration', 'commit', 'working_candidate',
                       'version', 'incomplete', 'dependency']:
            with self.subTest(change=change):
                receipt = deepcopy(self.receipt); incoming = deepcopy(self.incoming)
                try:
                    if change in receipt['acceptance']: receipt['acceptance'][change] = False
                    elif change == 'commit': receipt['packs'][0]['source']['commit'] = None
                    elif change == 'working_candidate': receipt['packs'][0]['source']['working_candidate'] = True
                    elif change == 'version': incoming[0]['version'] = [1, 0, 1]
                    elif change == 'incomplete': incoming.pop()
                    else: guard.atomic(manifest, {'dependencies': [{'uuid': 'unreviewed', 'version': [1, 0, 1]}]})
                    guard.atomic(self.approved, receipt)
                    with self.assertRaises(ValueError): guard.validate_incoming(incoming, self.policy_path)
                finally:
                    manifest.write_bytes(original)
                    guard.atomic(self.approved, self.receipt)

if __name__ == '__main__': unittest.main()
