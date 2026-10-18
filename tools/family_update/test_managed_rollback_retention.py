"""Synthetic filesystem rollback closure; no native process, world or live API."""
import copy
import hashlib
import json
from pathlib import Path
import shutil
import tempfile
import unittest
from unittest.mock import patch

from family_update import retention as m
from family_update.managed_drift_recovery import inventory_sha256, files_sha256
from family_update import test_retention as fixtures


class ManagedRollbackRetentionTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        fixture = fixtures.RetentionTests()
        fixture.root = self.root
        self.put = fixture.write
        self.old = fixture.deployment('old', 1)
        self.r = fixture.deployment('managed', 3, saved_only=True)
        self.lease = self.root / 'lease.json'
        self.put(self.lease, {'state': 'completed'})
        self.proc = self.root / 'proc'
        self.proc.mkdir()
        idle = patch.object(m, 'assert_idle')
        idle.start()
        self.addCleanup(idle.stop)
        original = self.get('production-before/inventory.json')
        approved_packs = []
        for row in original['packs']:
            row['version'] = [1, 0, 1]
            approved_packs.append({k: row[k] for k in ('uuid', 'side', 'version', 'files')})
        order = {side: [x['uuid'] for x in approved_packs if x['side'] == side] for side in ('behavior', 'resource')}
        original['refs'] = {side: [{'pack_id': uid, 'version': [1, 0, 1]} for uid in ids] for side, ids in order.items()}
        approved_root = self.root / 'approved'
        assembled_path = approved_root / 'release-candidate/family-receipt.json'
        assembled = {'packs': approved_packs, 'order': order}
        self.put(assembled_path, assembled)
        approved = {**assembled, 'assembled_receipt': self.ref(assembled_path)}
        self.approved_path = approved_root / 'reviewed-family-receipt.json'
        self.put(self.approved_path, approved)
        policy = {'approved_receipt': str(self.approved_path)}
        self.put(self.r / 'production-before/senluo-policy.json', policy)
        self.pins = {}
        rollback = self.get('rollback-map.json')
        candidate = self.get('reviewed-family-receipt.json')
        for side, uid in [('behavior', '5e121bf2-1d2d-4da4-be15-cffc5f216d94'), ('resource', 'e1168f1a-83d6-4abc-8f4b-ecb86e0a91dd')]:
            name = 'Fishing_' + side
            source = self.root / 'bds' / (side + '_packs') / name
            target = self.r / 'observed-global-displaced' / (side + '_packs') / name
            modules = [{'type': 'data' if side == 'behavior' else 'resources', 'version': [1, 2, 0]}]
            self.put(target / 'manifest.json', {'header': {'uuid': uid, 'version': [1, 2, 0]}, 'modules': modules})
            files = {'manifest.json': self.sha(target / 'manifest.json')}
            row = {'uuid': uid, 'side': side, 'version': [1, 2, 0], 'path': str(source), 'files': files}
            original['packs'].append(row)
            original['refs'][side].append({'pack_id': uid, 'version': row['version']})
            rollback['retired'].append([str(target), str(source)])
            candidate['packs'].append({k: row[k] for k in ('uuid', 'side', 'version', 'files')})
            self.pins[uid] = {'side': side, 'version': row['version'], 'global_path': str(source),
                              'manifest_sha256': files['manifest.json'], 'files_sha256': files_sha256(files), 'modules': modules}
        self.put(self.r / 'production-before/inventory.json', original)
        self.put(self.r / 'rollback-map.json', rollback)
        self.original = original
        self.review_path = self.root / 'private/maintenance/managed-review.json'
        review = {'schema': 1, 'kind': 'managed_drift_recovery', 'profile': 'reviewed-managed-drift-repair-v1',
                  'approved': {'policy_sha256': self.sha(self.r / 'production-before/senluo-policy.json'),
                               'receipt_sha256': self.sha(self.approved_path), 'assembled_receipt_sha256': self.sha(assembled_path), 'pack_count': 2},
                  'observed': {'inventory_sha256': inventory_sha256(original), 'added_uuids': sorted(self.pins)},
                  'preserved_existing_inputs': {'schema': 1, 'kind': 'existing_unattributed_paired_input',
                      'origin_status': 'unverified_existing_input', 'original_archive_verified': False, 'latest_stable_verified': False,
                      'action': 'retain_exact_bytes', 'definition_namespace': 'kaleidoscope_fishing', 'installation_location': 'world', 'packs': self.pins}}
        review['rollback'] = {k: review['approved'][k] for k in ('receipt_sha256', 'assembled_receipt_sha256')}
        self.put(self.review_path, review)
        for row in approved_packs:
            path = self.r / 'trusted-pack-rollback' / (row['side'] + '_packs') / row['uuid'] / 'manifest.json'
            path.parent.mkdir(parents=True)
            path.write_text('old pack')
        self.put(self.r / 'trusted-pack-rollback/senluo-policy.json', policy)
        for side, refs in {side: [{'pack_id': uid, 'version': [1, 0, 1]} for uid in ids] for side, ids in order.items()}.items():
            self.put(self.r / 'trusted-pack-rollback' / ('world_' + side + '_packs.json'), refs)
        record = {'schema': 1, 'state': 'prepared', 'review': self.ref(self.review_path),
                  'observed_inventory_sha256': inventory_sha256(original), 'receipt_sha256': review['rollback']['receipt_sha256'],
                  'policy_sha256': review['approved']['policy_sha256'], 'packs': approved_packs,
                  'refs': {side: [{'pack_id': uid, 'version': [1, 0, 1]} for uid in ids] for side, ids in order.items()}, 'database_copied': False}
        record['trusted_inventory_sha256'] = inventory_sha256(record)
        self.put(self.r / 'trusted-pack-rollback.json', record)
        (self.r / 'production-original-db/never').unlink()
        shutil.copy2(self.r / 'production-snapshot/db/data', self.r / 'production-original-db/data')
        migrated = {'candidate_receipt_sha256': self.get('deployment-result.json')['assembled_receipt_sha256'],
                    'database_files': {'data': hashlib.sha256(b'migrated').hexdigest()}}
        self.put(self.r / 'saved-world-identity-migration.json', migrated)
        self.put(self.r / 'production-identity-migration.json', {'state': 'adopted_stopped',
            'proof': self.ref(self.r / 'saved-world-identity-migration.json'), 'database_files': migrated['database_files'],
            'original_database': str(self.r / 'production-original-db')})
        candidate['evidence']['reports'].extend([self.ref(self.review_path), self.ref(self.r / 'trusted-pack-rollback.json'),
                                                 self.ref(self.r / 'saved-world-identity-migration.json')])
        self.put(self.r / 'reviewed-family-receipt.json', candidate)
        self.change('deployment-result.json', lambda d: d.update(reviewed_identity_migration=True))
        self.change('poststart-verification.json', lambda d: d.update(pack_count=4))
        self.change('admission-report.json', lambda d: d.update(complete_packs=4))

    @staticmethod
    def sha(path):
        return hashlib.sha256(path.read_bytes()).hexdigest()

    def ref(self, path):
        return {'path': str(path), 'sha256': self.sha(path)}

    def get(self, relative):
        return json.loads((self.r / relative).read_text())

    def change(self, relative, fn):
        value = self.get(relative)
        fn(value)
        self.put(self.r / relative, value)

    def plan(self):
        return m.plan(self.root, lease=self.lease, proc_root=self.proc)

    def proof(self):
        return m._proof(self.r, self.root, set())

    def rebind_record(self):
        self.change('reviewed-family-receipt.json', lambda d: d['evidence']['reports'].__setitem__(-2, self.ref(self.r / 'trusted-pack-rollback.json')))

    def test_complete_global_move_and_current_database_are_a_usable_retained_closure(self):
        planned = self.plan()
        self.assertTrue(planned['rollback_retention_ready'], planned['rollback_checks'])
        cache = m._retained_integrity(planned, self.root, set())
        for relative in ('trusted-pack-rollback', 'observed-global-displaced', 'production-original-db'):
            self.assertTrue(any(Path(name).is_relative_to(self.r / relative) for name in cache['files']))
        self.assertEqual(cache['hash_boundary_passes'], 1)
        m._recheck_retained(planned, cache, self.root, set())
        self.assertEqual(m.BACKUPS, ('production-snapshot', 'production-rollback', 'production-staged'))
        self.assertTrue(all(not any(x in target['relative'] for x in ('trusted', 'global', 'original-db'))
                            for row in planned['outputs'] for target in row['delete']))

    def test_unreviewed_alternate_missing_or_duplicate_global_mapping_rejected(self):
        original = self.get('rollback-map.json')
        for change in ('outside', 'missing', 'duplicate', 'wrong_destination'):
            with self.subTest(change=change):
                value = copy.deepcopy(original)
                if change == 'outside': value['retired'][-1][0] = str(self.r / 'other-displaced/resource_packs/Fishing_resource')
                elif change == 'missing': value['retired'].pop()
                elif change == 'duplicate': value['retired'].append(value['retired'][-1])
                else: value['retired'][-1][1] = str(self.root / 'other-global/resource_packs/Fishing_resource')
                self.put(self.r / 'rollback-map.json', value)
                self.assertFalse(m._backup_complete(self.proof(), self.r, self.root, set())[0])
        self.put(self.r / 'rollback-map.json', original)

    def test_every_retained_root_rejects_extra_missing_or_linked_leaves(self):
        roots = ['production-snapshot', 'production-rollback', 'trusted-pack-rollback', 'observed-global-displaced', 'production-original-db']
        for relative in roots:
            with self.subTest(relative=relative):
                path = self.r / relative / 'unknown'
                path.write_text('unreviewed')
                self.assertFalse(m._backup_complete(self.proof(), self.r, self.root, set())[0])
                path.unlink()
                leaf = next(p for p in (self.r / relative).rglob('*') if p.is_file())
                raw = leaf.read_bytes()
                leaf.unlink()
                # Missing trusted reference metadata fails before the topology check.
                try: self.assertFalse(m._backup_complete(self.proof(), self.r, self.root, set())[0])
                except (OSError, ValueError): pass
                leaf.write_bytes(raw)
                leaf.unlink(); leaf.symlink_to(self.root / 'outside')
                try: self.assertFalse(m._backup_complete(self.proof(), self.r, self.root, set())[0])
                except (OSError, ValueError): pass
                leaf.unlink(); leaf.write_bytes(raw)

    def test_content_boundary_hashes_displaced_trusted_and_current_original_db(self):
        for relative in ['production-rollback', 'trusted-pack-rollback/behavior_packs', 'observed-global-displaced', 'production-original-db']:
            with self.subTest(relative=relative):
                leaf = next(p for p in (self.r / relative).rglob('*') if p.is_file())
                raw = leaf.read_bytes(); leaf.write_bytes(b'wrong bytes')
                planned = self.plan()
                self.assertTrue(planned['rollback_retention_ready'])
                with self.assertRaisesRegex(ValueError, 'content differs'):
                    m._retained_integrity(planned, self.root, set())
                leaf.write_bytes(raw)

    def test_relabelled_self_consistent_trusted_record_cannot_replace_approved_bytes(self):
        self.change('trusted-pack-rollback.json', lambda d: d['packs'][0]['files'].update({'manifest.json': 'e' * 64}))
        self.change('trusted-pack-rollback.json', lambda d: d.update(trusted_inventory_sha256=inventory_sha256(d)))
        self.rebind_record()
        with self.assertRaisesRegex(ValueError, 'original approved payload'):
            self.proof()

    def test_wrong_review_archive_policy_or_observed_binding_fails_closed(self):
        paths = [self.review_path, self.approved_path, self.r / 'production-before/senluo-policy.json', self.r / 'trusted-pack-rollback.json']
        for path in paths:
            with self.subTest(path=path.name):
                raw = path.read_bytes(); path.write_bytes(raw + b' ')
                with self.assertRaisesRegex(ValueError, 'report bytes differ'):
                    self.proof()
                path.write_bytes(raw)
        original = self.get('production-before/inventory.json')
        self.change('production-before/inventory.json', lambda d: d['packs'][0]['files'].update({'unexpected': 'e' * 64}))
        with self.assertRaisesRegex(ValueError, 'inventory binding'):
            self.proof()
        self.put(self.r / 'production-before/inventory.json', original)

    def test_adoption_and_original_db_markers_are_required_and_bound(self):
        marker = self.get('production-identity-migration.json')
        for field, value in [('state', 'adoption_started'), ('original_database', str(self.root / 'foreign-db')), ('database_files', {'new': 'e' * 64})]:
            with self.subTest(field=field):
                self.put(self.r / 'production-identity-migration.json', {**marker, field: value})
                with self.assertRaisesRegex(ValueError, 'identity adoption proof'):
                    self.proof()
        self.put(self.r / 'production-identity-migration.json', marker)
        self.change('deployment-result.json', lambda d: d.update(reviewed_identity_migration=False))
        with self.assertRaisesRegex(ValueError, 'original database/adoption'):
            self.proof()

    def test_bound_report_cannot_change_between_read_and_stat_capture(self):
        target = self.r / 'production-before/senluo-policy.json'
        original_read = Path.read_bytes
        def changing(path):
            raw = original_read(path)
            if path == target:
                path.write_bytes(raw + b' ')
            return raw
        with patch.object(Path, 'read_bytes', changing):
            with self.assertRaisesRegex(ValueError, 'changed while reading'):
                self.proof()

    def test_corruption_after_hash_boundary_is_detected_without_rehashing(self):
        planned = self.plan(); cache = m._retained_integrity(planned, self.root, set())
        (self.r / 'production-original-db/data').write_text('changed after successful boundary')
        with self.assertRaisesRegex(ValueError, 'changed after content verification'):
            m._recheck_retained(planned, cache, self.root, set())


if __name__ == '__main__':
    unittest.main()
