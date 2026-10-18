"""Exact filesystem alias projection; no BDS, network, formal save or LIVE."""
from copy import deepcopy
import json
from pathlib import Path
import shutil
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from family_guard import hashes
from family_update import common as c, native_common as native
from family_update.engine_pack_projection import fingerprint


class EnginePackProjection(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.b = self.root / 'bds'
        self.r = self.root / 'run'
        self.candidate = self.r / 'release-candidate'
        self.w = self.b / 'world'
        self.q = self.root / 'quality'
        self.lease = self.root / 'lease.json'
        self.review = self.root / 'review.json'
        for root in [self.b, self.candidate, self.w, self.q, self.r / 'production-before']:
            root.mkdir(parents=True, exist_ok=True)
        for name in ['definitions', 'behavior_packs', 'resource_packs', 'config', 'minecraftpe', 'treatments']:
            (self.b / name).mkdir()
        (self.b / 'bedrock_server').write_bytes(b'non-executable engine fixture')
        (self.b / 'server.properties').write_text('server-port=19132\nserver-portv6=19133\n')
        self.receipt = {'packs': [], 'order': {'behavior': [], 'resource': []}}
        self.inventory = {'packs': [], 'refs': {'behavior': [], 'resource': []}}
        self.sources = {}
        for side, uid in [('behavior', '11111111-1111-1111-1111-111111111111'),
                          ('resource', '22222222-2222-2222-2222-222222222222')]:
            source = self.b / (side + '_packs') / 'original-addon'
            source.mkdir()
            self.write(source / 'manifest.json', {'header': {'uuid': uid, 'version': [1, 2, 0]}})
            (source / 'content.dat').write_bytes((side + ' original bytes').encode())
            destination = self.candidate / (side + '_packs') / uid
            shutil.copytree(source, destination)
            pack = {'uuid': uid, 'side': side, 'version': [1, 2, 0], 'files': hashes(source),
                    'source': {'owner': 'preserved'}, 'directory': uid}
            self.receipt['packs'].append(pack)
            self.receipt['order'][side].append(uid)
            self.inventory['packs'].append({**deepcopy(pack), 'path': str(source)})
            self.inventory['refs'][side].append({'pack_id': uid, 'version': [1, 2, 0]})
            self.sources[side] = source
            vanilla = self.b / (side + '_packs') / 'vanilla'
            vanilla.mkdir()
            self.write(vanilla / 'manifest.json', {'header': {'uuid': 'vanilla-' + side, 'version': [1, 0, 0]}})
            (vanilla / 'foundation.dat').write_bytes(b'vanilla fixture')
            (self.b / (side + '_packs') / 'loose.dat').write_bytes(b'unknown loose input')
            unknown = self.b / (side + '_packs') / 'unknown/nested'
            unknown.mkdir(parents=True)
            (unknown / 'keep.dat').write_bytes(b'unknown nested input')
        self.write(self.candidate / 'family-receipt.json', self.receipt)
        self.write(self.r / 'production-before/inventory.json', self.inventory)
        self.write(self.r / 'production-before/capture.json', {
            'inventory': self.ref(self.r / 'production-before/inventory.json')})
        values = dict(B=self.b, R=self.r, C=self.candidate, W=self.w, Q=self.q,
                      LEASE=self.lease, OWNER='fixture-owner', SERVER='fixture-server',
                      CONFIG={'managed_drift_recovery': str(self.review)}, G={'hashes': hashes})
        self.enterContext(patch.multiple(c, **values))
        self.enterContext(patch.object(native, 'B', self.b))

    @staticmethod
    def write(path, value):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(value, indent=2) + '\n')

    @staticmethod
    def ref(path):
        return {'path': str(path), 'sha256': c.sha(path)}

    def view(self):
        return c.engine_inputs(world_receipt=self.receipt)

    def setup(self, inputs=None, suffix='qa'):
        engine = self.root / suffix
        native.setup_engine(engine, 'Fixture QA', 29124,
                            expected_inputs=self.view() if inputs is None else inputs,
                            world_receipt=self.receipt)
        return engine

    def park(self, *, completed=False):
        candidate_ref = self.ref(self.candidate / 'family-receipt.json')
        self.write(self.review, {
            'observed': {'added_uuids': [p['uuid'] for p in self.receipt['packs']]},
            'preserved_existing_inputs': {'installation_location': 'world', 'packs': {
                p['uuid']: {'global_path': p['path'], 'side': p['side'], 'version': p['version'],
                            'manifest_sha256': p['files']['manifest.json'], 'files_sha256': fingerprint(p['files'])}
                for p in self.inventory['packs']}}})
        reviewed = self.r / 'reviewed-family-receipt.json'
        self.write(reviewed, {**self.receipt, 'assembled_receipt': candidate_ref,
                              'evidence': {'reports': [self.ref(self.review)]}})
        reviewed_ref = self.ref(reviewed)
        admission = {'approved_receipt': str(reviewed), 'installed': {'old': True}, 'hold_reason': 'old', 'unchanged': True}
        self.write(self.r / 'admission-policy.json', admission)
        policy = {**admission, 'hold_reason': 'pending acceptance', 'installed': {
            'receipt': str(reviewed), 'receipt_sha256': reviewed_ref['sha256'], 'packs': self.receipt['packs']}}
        self.write(self.q / 'senluo-policy.json', policy)
        retired, installed = [], []
        for row in self.inventory['packs']:
            source = Path(row['path'])
            displaced = self.r / 'observed-global-displaced' / (row['side'] + '_packs') / source.name
            displaced.parent.mkdir(parents=True, exist_ok=True)
            source.rename(displaced)
            destination = self.w / (row['side'] + '_packs') / row['uuid']
            shutil.copytree(self.candidate / (row['side'] + '_packs') / row['uuid'], destination)
            retired.append([str(displaced), str(source)])
            installed.append(str(destination))
        self.write(self.r / 'rollback-map.json', {'retired': retired, 'installed': installed,
            'original_inventory': str(self.r / 'production-before/inventory.json'),
            'backup': str(self.r / 'production-snapshot')})
        result = {'state': 'deployed_running' if completed else 'installed_stopped',
                  'guard_admission_passed': True, 'receipt_sha256': reviewed_ref['sha256'],
                  'assembled_receipt_sha256': candidate_ref['sha256']}
        lease = {'owner': c.OWNER, 'candidate': str(self.r),
                 'candidate_receipt_sha256': candidate_ref['sha256'], 'state': 'completed' if completed else 'active'}
        if completed:
            result['poststart_report'] = str(self.r / 'poststart-verification.json')
            lease.update(receipt=str(reviewed), status='running_for_user_acceptance', completed_at='fixture-time')
            self.write(self.r / 'poststart-verification.json', {'ok': True,
                'summary': {'status': 'RUNNING', 'name': c.SERVER}, 'receipt_sha256': reviewed_ref['sha256'],
                'exact_pack_files_and_order': True})
        self.write(self.r / 'deployment-result.json', result)
        self.write(self.lease, lease)

    def test_exact_alias_is_visible_once_and_other_global_inputs_stay_visible(self):
        before = {side: hashes(self.b / (side + '_packs')) for side in self.sources}
        view = self.view()
        engine = self.setup(view)
        self.assertEqual(len(view['global_pack_projection']['aliases']), 2)
        for row in self.receipt['packs']:
            side, uid = row['side'], row['uuid']
            root = engine / (side + '_packs')
            self.assertFalse(root.is_symlink())
            self.assertFalse((root / 'original-addon').exists())
            self.assertTrue((root / 'vanilla').is_symlink())
            self.assertEqual((root / 'unknown/nested/keep.dat').read_bytes(), b'unknown nested input')
            self.assertEqual((root / 'loose.dat').read_bytes(), b'unknown loose input')
            world_pack = engine / 'worlds/Fixture QA' / (side + '_packs') / uid
            shutil.copytree(self.candidate / (side + '_packs') / uid, world_pack)
            visible = [p for p in [root / 'original-addon', world_pack] if (p / 'manifest.json').exists()]
            self.assertEqual(len(visible), 1)
            self.assertEqual(hashes(self.b / (side + '_packs')), before[side])
            self.assertIn('loose.dat', view['trees'][side + '_packs'])
            self.assertIn('unknown/nested/keep.dat', view['trees'][side + '_packs'])

    def test_legacy_setup_without_receipt_keeps_original_full_global_view(self):
        engine = self.root / 'legacy'
        native.setup_engine(engine, 'Fixture QA', 29124, expected_inputs=c.engine_inputs())
        self.assertTrue((engine / 'behavior_packs').is_symlink())
        self.assertTrue((engine / 'behavior_packs/original-addon/manifest.json').is_file())

    def test_changed_global_bytes_version_extra_file_or_wrong_side_rejected(self):
        for kind in ['bytes', 'version', 'extra', 'wrong_side', 'duplicate']:
            source = self.sources['behavior']
            original = {p: p.read_bytes() for p in source.iterdir()}
            extra = None
            try:
                if kind == 'bytes': (source / 'content.dat').write_bytes(b'changed')
                elif kind == 'version':
                    manifest = json.loads((source / 'manifest.json').read_text()); manifest['header']['version'] = [1, 2, 1]
                    self.write(source / 'manifest.json', manifest)
                elif kind == 'extra': extra = source / 'unexpected.dat'; extra.write_bytes(b'new')
                else:
                    side = 'resource' if kind == 'wrong_side' else 'behavior'
                    extra = self.b / (side + '_packs') / 'second-alias'; shutil.copytree(source, extra)
                with self.subTest(kind=kind), self.assertRaises(AssertionError): self.view()
            finally:
                if extra is not None:
                    shutil.rmtree(extra) if extra.is_dir() else extra.unlink()
                for path, raw in original.items(): path.write_bytes(raw)

    def test_candidate_payload_receipt_or_captured_inventory_change_is_rejected(self):
        paths = [self.candidate / 'behavior_packs' / self.receipt['packs'][0]['uuid'] / 'content.dat',
                 self.candidate / 'family-receipt.json', self.r / 'production-before/inventory.json']
        for path in paths:
            before = self.view()
            raw = path.read_bytes()
            try:
                if path.name == 'content.dat': path.write_bytes(b'changed candidate')
                else: path.write_bytes(raw + b'\n')
                # Receipt whitespace changes are deliberately part of the raw
                # binding captured by the first engine identity, below.
                if path.name != 'family-receipt.json':
                    with self.subTest(path=path.name), self.assertRaises(AssertionError): self.view()
                else:
                    self.assertNotEqual(self.view(), before)
                    with self.assertRaisesRegex(AssertionError, 'Projected engine inputs differ'): self.setup(before)
                    changed = deepcopy(self.receipt); changed['packs'][0]['version'] = [9, 9, 9]
                    with self.assertRaisesRegex(AssertionError, 'Explicit world receipt'): c.engine_inputs(world_receipt=changed)
            finally: path.write_bytes(raw)

    def test_alias_root_and_leaf_links_and_nonregular_entries_are_rejected(self):
        source = self.sources['behavior']
        leaf = source / 'content.dat'; raw = leaf.read_bytes()
        leaf.unlink(); leaf.symlink_to(self.sources['resource'] / 'content.dat')
        with self.assertRaises(ValueError): self.view()
        leaf.unlink(); leaf.write_bytes(raw)
        moved = source.with_name('moved'); source.rename(moved); source.symlink_to(moved, target_is_directory=True)
        with self.assertRaises((AssertionError, ValueError)): self.view()
        source.unlink(); moved.rename(source)
        import os
        fifo = source / 'unsafe'; os.mkfifo(fifo)
        with self.assertRaisesRegex(AssertionError, 'nonregular'): self.view()

    def test_no_alias_explicit_view_preserves_unknown_inputs_and_legacy_identity(self):
        empty = {'packs': [], 'order': {'behavior': [], 'resource': []}}
        self.assertEqual(c.engine_inputs(world_receipt=empty), c.engine_inputs())

    def test_parked_alias_identity_is_stable_for_active_and_completed_leases(self):
        before = self.view()
        self.park()
        self.assertEqual(self.view(), before)
        result = c.read(self.r / 'deployment-result.json'); result.update(state='deployed_running', poststart_report=str(self.r / 'poststart-verification.json'))
        self.write(self.r / 'deployment-result.json', result)
        self.write(self.r / 'poststart-verification.json', {'ok': True, 'summary': {'status': 'RUNNING', 'name': c.SERVER},
            'receipt_sha256': result['receipt_sha256'], 'exact_pack_files_and_order': True})
        lease = c.read(self.lease); lease.update(state='completed', receipt=str(self.r / 'reviewed-family-receipt.json'), status='running_for_user_acceptance', completed_at='fixture-time')
        self.write(self.lease, lease)
        self.assertEqual(self.view(), before)

    def test_unexplained_absence_and_changed_parked_or_installed_bytes_rejected(self):
        self.sources['behavior'].rename(self.root / 'hidden')
        with self.assertRaises(AssertionError): self.view()
        (self.root / 'hidden').rename(self.sources['behavior'])
        self.park(completed=True)
        paths = [self.r / 'observed-global-displaced/behavior_packs/original-addon/content.dat',
                 self.w / 'behavior_packs' / self.receipt['packs'][0]['uuid'] / 'content.dat',
                 self.candidate / 'behavior_packs' / self.receipt['packs'][0]['uuid'] / 'content.dat']
        for path in paths:
            raw = path.read_bytes(); path.write_bytes(b'changed')
            with self.subTest(path=str(path)), self.assertRaises(AssertionError): self.view()
            path.write_bytes(raw)

    def test_parked_alias_requires_the_exact_installed_policy_owner_and_readback_chain(self):
        self.park(completed=True)
        cases = [
            (self.r / 'rollback-map.json', lambda value: value.update(retired=[])),
            (self.r / 'deployment-result.json', lambda value: value.update(state='needs_operator_recovery')),
            (self.r / 'poststart-verification.json', lambda value: value.update(receipt_sha256='wrong')),
            (self.lease, lambda value: value.update(candidate='another-run')),
            (self.q / 'senluo-policy.json', lambda value: value.update(unreviewed=True)),
            (self.review, lambda value: value['preserved_existing_inputs'].update(installation_location='global')),
        ]
        for path, mutate in cases:
            raw = path.read_bytes(); value = json.loads(raw); mutate(value); self.write(path, value)
            with self.subTest(path=path.name), self.assertRaises(AssertionError): self.view()
            path.write_bytes(raw)

    def test_unknown_inputs_remain_pinned_after_parking(self):
        self.park(completed=True); before = self.view()
        (self.b / 'resource_packs/loose.dat').write_bytes(b'changed unknown')
        self.assertNotEqual(before, self.view())

    def test_setup_rejects_changed_candidate_before_creating_engine(self):
        before = self.view()
        (self.candidate / 'behavior_packs' / self.receipt['packs'][0]['uuid'] / 'content.dat').write_bytes(b'changed')
        with self.assertRaises(AssertionError): self.setup(before)
        self.assertFalse((self.root / 'qa').exists())


if __name__ == '__main__':
    unittest.main()
