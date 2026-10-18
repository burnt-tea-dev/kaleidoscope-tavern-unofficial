"""Exact drift admission and pack-only failure recovery on synthetic worlds."""
import copy
import hashlib
import json
from pathlib import Path
import runpy
import shutil
import sys
import tempfile
import unittest
from unittest.mock import patch
import zipfile

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from family_update import common as c
from family_update import deploy_live as deploy
from family_update import identity_migration as migration
from family_update import managed_drift_recovery as m
LOAD_REVIEW = m.load_review


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, sort_keys=True) + '\n')


def hashes(root):
    return {p.relative_to(root).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in sorted(root.rglob('*')) if p.is_file()}


class DriftTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.base = Path(temporary.name)
        self.world, self.engine, self.output, self.quality, self.private = [self.base / name for name in ['world', 'engine', 'output', 'quality', 'private']]
        self.sources = {name: self.base / name for name in ['tavern', 'grilling', 'world-liquor']}
        self.trusted = self.base / 'previous/release-candidate'
        for root in [self.world, self.engine, self.trusted]:
            for side in m.SIDES:
                (root / (side + '_packs')).mkdir(parents=True)
        self.output.mkdir(); self.quality.mkdir()
        write(self.world / 'db/sentinel.json', {'newest_player_progress': 17})
        write(self.world / 'level.dat', {'newest_level_metadata': 23})
        self.before_database = hashes(self.world / 'db')
        self.before_level = (self.world / 'level.dat').read_bytes()
        self.approved = {'packs': [], 'order': {s: [] for s in m.SIDES}}
        for side in m.SIDES:
            for name in ['host', 'owned']:
                row = self.pack(self.trusted, name + '-' + side, side, [1, 0, 1])
                row['source'] = {'owner': 'upstream_extended' if name == 'host' else 'owned', 'project_id': 7, 'file_id': 11, 'archive_sha256': 'a' * 64}
                self.approved['packs'].append(row)
                self.approved['order'][side].append(row['uuid'])
        self.assembled = self.trusted / 'family-receipt.json'
        write(self.assembled, self.approved)
        self.approved['assembled_receipt'] = {'path': str(self.assembled), 'sha256': c.sha(self.assembled)}
        self.reviewed = self.trusted.parent / 'reviewed-family-receipt.json'
        write(self.reviewed, self.approved)
        for side, refs in m.receipt_inventory(self.approved)['refs'].items():
            write(self.trusted / ('world_' + side + '_packs.json'), refs)
        self.policy = {'approved_receipt': str(self.reviewed), 'managed_uuids': [p['uuid'] for p in self.approved['packs']],
                       'installed': {'receipt': str(self.reviewed), 'receipt_sha256': c.sha(self.reviewed)}}
        write(self.quality / 'senluo-policy.json', self.policy)
        write(self.output / 'production-before/senluo-policy.json', self.policy)
        self.original = {'packs': [], 'refs': {s: [] for s in m.SIDES}}
        self.archives = {}
        for side in m.SIDES:
            self.original['packs'].append(self.pack(self.world, 'host-' + side, side, [1, 0, 2]))
            foreign = self.pack(self.engine, 'foreign-' + side, side, [1, 2, 0])
            self.original['packs'].append(foreign)
            archive = self.base / ('foreign-' + side + '.mcpack')
            with zipfile.ZipFile(archive, 'w') as zipped:
                root = Path(foreign['path'])
                for name in foreign['files']:
                    zipped.write(root / name, 'original/' + name)
            self.archives[foreign['uuid']] = {'reason': 'Exact independent original pack', 'artifact': {'path': str(archive), 'sha256': c.sha(archive)}}
            self.original['refs'][side] = [{'pack_id': p['uuid'], 'version': p['version']} for p in self.original['packs'] if p['side'] == side]
            write(self.world / ('world_' + side + '_packs.json'), self.original['refs'][side])
        self.addition_path = self.private / 'maintenance/additions.json'
        write(self.addition_path, {'schema': 1, 'source_provenance': 'original archives', 'review_reason': 'Preserve existing unrelated packs',
                                   'observed_inventory': self.original, 'packs': self.archives})
        self.target = {'packs': [], 'order': {s: [] for s in m.SIDES}}
        self.swaps = []
        self.additions = []
        for side in m.SIDES:
            for name in ['new-host', 'foreign', 'owned', 'new-addon']:
                uid = name + '-' + side
                self.target['packs'].append({'uuid': uid, 'side': side, 'version': [2, 0, 1]})
                self.target['order'][side].append(uid)
                if name in ['owned', 'new-addon']:
                    self.additions.append(uid)
            self.swaps.append({'old_uuid': 'host-' + side, 'new_uuid': 'new-host-' + side, 'side': side})
        trees = {}
        for name, path in {**self.sources, 'extension': self.private}.items():
            trees[name] = {'BP': name + '-bp', 'RP': name + '-rp'}
            write(path / 'baseline.json', {'source_trees': trees[name]})
        write(self.sources['tavern'] / 'family/upstream.lock.json', {'reviewed': 'author identity fixture'})
        self.review = {'schema': 1, 'kind': 'managed_drift_recovery', 'profile': m.PROFILE,
            'approved': {'policy_sha256': c.sha(self.quality / 'senluo-policy.json'), 'receipt_sha256': c.sha(self.reviewed),
                         'assembled_receipt_sha256': c.sha(self.assembled), 'pack_count': len(self.approved['packs'])},
            'observed': {'inventory_sha256': m.inventory_sha256(self.original), 'pack_count': len(self.original['packs']),
                         'missing_uuids': ['owned-' + s for s in m.SIDES], 'changed_uuids': ['host-' + s for s in m.SIDES],
                         'added_uuids': ['foreign-' + s for s in m.SIDES]},
            'preserved_additions': {'path': 'maintenance/additions.json', 'sha256': c.sha(self.addition_path)},
            'proofs': [{'path': 'maintenance/proof-' + str(i) + '.json', 'sha256': 'f' * 64} for i in range(3)],
            'target': {**self.target, 'additions': self.additions, 'swaps': self.swaps,
                       'upstream_lock_sha256': c.sha(self.sources['tavern'] / 'family/upstream.lock.json'), 'owned_source_trees': trees},
            'rollback': {'receipt_sha256': c.sha(self.reviewed), 'assembled_receipt_sha256': c.sha(self.assembled)},
            'safety': {'installer_authorization_proven': False, 'unknown_leaf_count': 0, 'repair_only': True,
                       'keep_newest_database': True, 'after_identity_adoption': 'retain_stopped_and_active_lease', 'preserve_displaced_bytes': True}}
        self.binding = {'path': str(self.private / 'maintenance/review.json'), 'sha256': 'b' * 64}
        self.stack = self.enterContext(__import__('contextlib').ExitStack())
        guard = runpy.run_path(str(Path(__file__).resolve().parents[1] / 'family_guard.py'))
        self.lease = self.base / 'maintenance.json'
        write(self.lease, {'state': 'completed', 'owner': 'previous-owner', 'candidate': 'previous-candidate'})
        self.stack.enter_context(patch.multiple(c, W=self.world, B=self.engine, R=self.output, Q=self.quality, T=self.sources['tavern'], LEASE=self.lease, SERVER='test-server',
            EXTENSION=self.private, SOURCES=self.sources,
            CONFIG={'managed_drift_recovery': self.binding['path'], 'managed_drift_rollback_root': str(self.trusted), 'preserved_additions': str(self.addition_path)},
            G={'hashes': hashes, 'atomic': write, 'family_pack': guard['family_pack'], 'audit': lambda w, p: {'ok': True}}))
        self.stack.enter_context(patch.object(m, 'load_review', return_value=(self.review, self.binding)))
        self.stack.enter_context(patch.object(m, '_INITIAL_STATE', None))
        self.stack.enter_context(patch.object(c, 'assert_lease'))
        self.stack.enter_context(patch.object(c, 'summary', return_value={'name': 'test-server', 'status': 'STOPPED', 'player_count': 0}))
        self.global_before = {s: hashes(self.engine / (s + '_packs')) for s in m.SIDES}

    def pack(self, root, uid, side, version):
        path = root / (side + '_packs') / uid
        write(path / 'manifest.json', {'header': {'uuid': uid, 'version': version}, 'modules': [{'uuid': 'module-' + uid, 'type': 'resources' if side == 'resource' else 'data', 'version': version}]})
        write(path / 'content.json', {'owned_by': uid, 'release': version})
        return {'uuid': uid, 'side': side, 'version': version, 'files': hashes(path), 'path': str(path)}

    def unchanged_database(self):
        self.assertEqual(hashes(self.world / 'db'), self.before_database)
        self.assertEqual((self.world / 'level.dat').read_bytes(), self.before_level)
        for side in m.SIDES:
            self.assertEqual(hashes(self.engine / (side + '_packs')), self.global_before[side])

    def existing_mode(self):
        self.review.pop('preserved_additions')
        c.CONFIG.pop('preserved_additions')
        pins = {}
        for row in self.original['packs']:
            if row['uuid'].startswith('foreign-'):
                path = Path(row['path'])
                write(path / ('items' if row['side'] == 'behavior' else 'entity') / 'fishing.json', {'description': {'identifier': 'kaleidoscope_fishing:existing_item'}})
                row['files'] = hashes(path)
                pins[row['uuid']] = {'side': row['side'], 'version': row['version'], 'global_path': row['path'],
                    'manifest_sha256': row['files']['manifest.json'], 'files_sha256': m.files_sha256(row['files']),
                    'modules': c.read(Path(row['path']) / 'manifest.json')['modules']}
                target = next(p for p in self.target['packs'] if p['uuid'] == row['uuid'])
                target.update(version=row['version'], files=row['files'], source={'owner': 'preserved'})
        self.review['preserved_existing_inputs'] = {'schema': 1, 'kind': 'existing_unattributed_paired_input',
            'origin_status': 'unverified_existing_input', 'original_archive_verified': False,
            'latest_stable_verified': False, 'action': 'retain_exact_bytes', 'installation_location': 'world', 'definition_namespace': 'kaleidoscope_fishing', 'packs': pins}
        self.review['observed']['inventory_sha256'] = m.inventory_sha256(self.original)

    def test_existing_unknown_pair_stays_explicit_and_candidate_cannot_change_it(self):
        self.existing_mode()
        admitted = m.provenance_original(self.original, self.approved)
        foreign = next(p for p in admitted['packs'] if p['uuid'] == 'foreign-behavior')
        self.assertFalse(foreign['source']['original_archive_verified'])
        self.assertFalse(foreign['source']['latest_stable_verified'])
        self.assertEqual(foreign['source']['origin_status'], 'unverified_existing_input')
        with patch.object(migration, 'plan_swaps', return_value=self.swaps):
            self.assertEqual(m.validate_target(self.target, self.original, {'fixture': True}), set(self.additions))
            altered = copy.deepcopy(self.target)
            next(p for p in altered['packs'] if p['uuid'] == foreign['uuid'])['files']['extra.json'] = 'f' * 64
            with self.assertRaisesRegex(AssertionError, 'Retain-only input was changed'):
                m.validate_target(altered, self.original, {'fixture': True})
        self.review['preserved_existing_inputs']['original_archive_verified'] = True
        with self.assertRaises(AssertionError):
            m.check_observed(self.original)

    def test_existing_unknown_pair_rejects_another_global_path_or_module(self):
        self.existing_mode()
        pin = self.review['preserved_existing_inputs']['packs']['foreign-behavior']
        pin['global_path'] += '-other'
        with self.assertRaisesRegex(AssertionError, 'path differs'):
            m.check_observed(self.original)
        pin['global_path'] = next(p['path'] for p in self.original['packs'] if p['uuid'] == 'foreign-behavior')
        pin['modules'][0]['uuid'] = 'different-module'
        with self.assertRaisesRegex(AssertionError, 'modules differ'):
            m.check_observed(self.original)

    def test_exact_fishing_namespace_does_not_exempt_managed_definitions_or_dependencies(self):
        self.existing_mode()
        row = next(p for p in self.original['packs'] if p['uuid'] == 'foreign-behavior')
        pin = self.review['preserved_existing_inputs']['packs'][row['uuid']]
        self.assertTrue(c.G['family_pack'](row, {'managed_uuids': self.policy['managed_uuids']}))
        self.assertEqual(m.check_observed(self.original)[0], self.review)
        definition = Path(row['path']) / 'items/fishing.json'
        write(definition, {'description': {'identifier': 'kaleidoscope_tavern:foreign_overlay'}})
        row['files'] = hashes(Path(row['path'])); pin['files_sha256'] = m.files_sha256(row['files'])
        self.review['observed']['inventory_sha256'] = m.inventory_sha256(self.original)
        with self.assertRaisesRegex(AssertionError, 'masks a managed'):
            m.check_observed(self.original)
        write(definition, {'description': {'identifier': 'kaleidoscope_fishing:existing_item'}})
        manifest = c.read(Path(row['path']) / 'manifest.json'); manifest['dependencies'] = [{'uuid': 'host-behavior', 'version': [1, 0, 1]}]
        write(Path(row['path']) / 'manifest.json', manifest)
        row['files'] = hashes(Path(row['path'])); pin['files_sha256'] = m.files_sha256(row['files']); pin['manifest_sha256'] = row['files']['manifest.json']
        self.review['observed']['inventory_sha256'] = m.inventory_sha256(self.original)
        with self.assertRaisesRegex(AssertionError, 'Managed ownership or dependencies'):
            m.check_observed(self.original)

    def test_relocation_selection_installs_both_preserved_inputs_for_world_patrol(self):
        self.existing_mode()
        receipt = copy.deepcopy(self.target)
        for row in receipt['packs']:
            row.setdefault('source', {'owner': 'owned'})
        with patch.object(deploy, 'CONFIG', {'managed_drift_recovery': 'committed-review'}):
            family, unchanged = deploy.installation_selection(receipt, self.original)
        self.assertTrue(set(self.review['observed']['added_uuids']) <= {p['uuid'] for p in family})
        self.assertFalse(unchanged)
        self.review['preserved_existing_inputs']['installation_location'] = 'global'
        with self.assertRaisesRegex(AssertionError, 'installation location'):
            m.global_relocations(self.original)

    def relocate_global_pair(self, only_first=False):
        relocations = m.global_relocations(self.original)
        retired = []; installed = []
        for row in self.original['packs']:
            if row['uuid'] not in relocations:
                continue
            source = Path(row['path'])
            target = m.retirement_target(row, self.output / 'production-rollback', relocations)
            target.parent.mkdir(parents=True, exist_ok=True)
            m.os.replace(source, target); retired.append((target, source))
            if only_first:
                break
            dest = self.world / (row['side'] + '_packs') / row['uuid']
            shutil.copytree(target, dest); installed.append(dest)
        return retired, installed

    def admitted_stage(self):
        assembled = self.output / 'release-candidate/family-receipt.json'
        reviewed = self.output / 'reviewed-family-receipt.json'
        write(assembled, self.target)
        write(reviewed, {'assembled_receipt': {'path': str(assembled), 'sha256': c.sha(assembled)}})
        admission = {'approved_receipt': str(reviewed)}
        write(self.output / 'admission-policy.json', admission)
        write(self.quality / 'senluo-policy.json', admission)
        write(self.lease, {'state': 'active', 'owner': c.OWNER, 'candidate': str(self.output), 'candidate_receipt_sha256': c.sha(assembled)})
        (self.output / 'production-staged').mkdir()

    def test_post_relocation_identity_provenance_reads_exact_displaced_original(self):
        self.existing_mode(); m.prepare_rollback(self.original)
        self.relocate_global_pair(); self.admitted_stage()
        admitted = m.provenance_original(self.original, self.approved)
        self.assertEqual(m.projection(admitted), m.projection(self.original))
        for row in admitted['packs']:
            if row['uuid'] in self.review['observed']['added_uuids']:
                self.assertEqual(row['path'], self.review['preserved_existing_inputs']['packs'][row['uuid']]['global_path'])
                self.assertFalse(row['source']['original_archive_verified'])
        path = self.sources['tavern'] / 'family/identity-migrations/fixture.json'
        write(path, {'fixture': True})
        def validate(spec, receipt, original):
            self.assertIn('observed_reviewed_drift', original)
            return m.validate_target(receipt, original, spec)
        with patch.multiple(migration, CONFIG={**c.CONFIG, 'identity_migration': str(path)}, T=self.sources['tavern'], R=self.output), patch.object(migration, 'plan_swaps', return_value=self.swaps), patch.object(migration, 'validate_plan', side_effect=validate):
            self.assertEqual(migration.candidate_plan(self.target, self.original), set(self.additions))

    def test_corrupt_displaced_original_cannot_pass_identity_revalidation(self):
        self.existing_mode(); m.prepare_rollback(self.original)
        retired, _ = self.relocate_global_pair(); self.admitted_stage()
        (retired[0][0] / 'content.json').write_text('changed-after-displacement')
        with self.assertRaisesRegex(AssertionError, 'Displaced original input bytes changed'):
            m.provenance_original(self.original, self.approved)
        self.assertFalse((self.output / 'production-identity-migration.json').exists())
        self.assertEqual(hashes(self.world / 'db'), self.before_database)

    def test_missing_global_source_has_no_fallback_outside_admitted_stage(self):
        self.existing_mode(); m.prepare_rollback(self.original)
        self.relocate_global_pair()
        with self.assertRaisesRegex(AssertionError, 'No reviewed installation stage'):
            m.provenance_original(self.original, self.approved)

    def test_global_to_world_keeps_one_resolution_and_preserves_both_sides_on_rollback(self):
        self.existing_mode(); m.prepare_rollback(self.original)
        retired, installed = self.relocate_global_pair()
        live = c.live_inventory()
        for row in live['packs']:
            if row['uuid'] in self.review['observed']['added_uuids']:
                self.assertEqual(Path(row['path']).parent.parent, self.world)
        m.restore(self.original, retired, installed)
        self.assertEqual(m.projection(c.live_inventory()), m.receipt_inventory(self.approved))
        for target, source in retired:
            original = next(p for p in self.original['packs'] if p['path'] == str(source))
            self.assertEqual(hashes(target), original['files'])
            self.assertFalse(source.exists())
            self.assertEqual(hashes(self.output / 'managed-drift-displaced' / source.parent.name / original['uuid']), original['files'])
        self.assertEqual(hashes(self.world / 'db'), self.before_database)
        self.assertEqual((self.world / 'level.dat').read_bytes(), self.before_level)

    def test_partial_global_relocation_rolls_back_without_losing_either_original(self):
        self.existing_mode(); m.prepare_rollback(self.original)
        retired, installed = self.relocate_global_pair(only_first=True)
        m.restore(self.original, retired, installed)
        for row in self.original['packs']:
            if row['uuid'] not in self.review['observed']['added_uuids']:
                continue
            path = Path(row['path'])
            displaced = self.output / 'observed-global-displaced' / path.parent.name / path.name
            self.assertEqual(hashes(displaced if displaced.exists() else path), row['files'])
        self.assertEqual(m.projection(c.live_inventory()), m.receipt_inventory(self.approved))
        self.assertEqual(hashes(self.world / 'db'), self.before_database)

    def test_stopped_initial_state_requires_exact_closed_owner_and_never_permits_old_restart(self):
        self.review.update(allow_initially_stopped=True, stopped_server_review={'server_name': 'test-server', 'reason': 'normal_idle_stop', 'lease_sha256': c.sha(self.lease)})
        state = m.validate_initial_status(c.summary())
        self.assertFalse(state['restart_original_after_failure'])
        write(self.output / 'previous-maintenance.json', c.read(self.lease))
        m.record_initial_status()
        self.assertFalse(m.restart_original_allowed())
        saved = c.read(self.output / 'deployment-initial-state.json'); saved['restart_original_after_failure'] = True
        write(self.output / 'deployment-initial-state.json', saved)
        with self.assertRaisesRegex(AssertionError, 'Initial owner state changed'):
            m.restart_original_allowed()
        with patch.object(c, 'summary', return_value={'name': 'test-server', 'status': 'STOPPED', 'player_count': 1}), self.assertRaises(AssertionError):
            m.validate_initial_status(c.summary())

    def test_review_must_be_clean_remote_main_and_committed_unchanged(self):
        for row in self.review['proofs']:
            path = self.private / row['path']; write(path, {'proof': row['path']}); row['sha256'] = c.sha(path)
        review_path = Path(self.binding['path']); write(review_path, self.review)
        write(self.private / '.repo-target.json', {'private': True, 'repository': 'casama233/senluo-family-integration-private', 'repository_id': 1406868911})
        snapshots = {p.relative_to(self.private).as_posix(): p.read_bytes() for p in (self.private / 'maintenance').rglob('*.json')}
        def git(path, *args):
            if args[0] == 'remote': return 'https://github.com/casama233/senluo-family-integration-private.git'
            if args[0] == 'branch': return 'main'
            if args[0] == 'status': return ''
            if args[0] == 'ls-remote': return 'a' * 40 + ' refs/heads/main'
            return 'a' * 40
        def committed(args):
            return snapshots[args[-1].removeprefix('HEAD:')]
        with patch.object(c, 'git', side_effect=git), patch.object(m.subprocess, 'check_output', side_effect=committed):
            self.assertEqual(LOAD_REVIEW()[0], self.review)
            review_path.write_text(review_path.read_text() + ' ')
            with self.assertRaisesRegex(AssertionError, 'not committed unchanged'):
                LOAD_REVIEW()

    def test_identity_hooks_keep_actual_inventory_and_use_reviewed_complete_order(self):
        path = self.sources['tavern'] / 'family/identity-migrations/fixture.json'
        write(path, {'fixture': True})
        config = {**c.CONFIG, 'identity_migration': str(path)}
        with patch.multiple(migration, CONFIG=config, T=self.sources['tavern'], R=self.output), patch.object(migration, 'plan_swaps', return_value=self.swaps):
            admitted = migration.admitted_original(self.original)
            self.assertEqual(m.projection(admitted), m.projection(self.original))
            self.assertIn('observed_reviewed_drift', admitted)
            self.assertEqual(migration.assembly_order(self.original), self.target['order'])

    def test_projection_binds_all_bytes_versions_and_order_but_not_local_paths(self):
        changed = copy.deepcopy(self.original)
        changed['packs'][0]['path'] = '/another/local/location'
        self.assertEqual(m.inventory_sha256(changed), m.inventory_sha256(self.original))
        changed['packs'][0]['files']['new.json'] = 'd' * 64
        self.assertNotEqual(m.inventory_sha256(changed), m.inventory_sha256(self.original))
        with self.assertRaisesRegex(AssertionError, 'bytes or order'):
            m.check_observed(changed)
        changed = copy.deepcopy(self.original); changed['refs']['behavior'].reverse()
        with self.assertRaisesRegex(AssertionError, 'bytes or order'):
            m.check_observed(changed)

    def test_original_archive_admission_is_required_for_global_additions(self):
        self.assertEqual(m.check_observed(self.original)[0], self.review)
        foreign = next(p for p in self.original['packs'] if p['uuid'] == 'foreign-behavior')
        with zipfile.ZipFile(self.archives[foreign['uuid']]['artifact']['path'], 'a') as archive:
            archive.writestr('original/unknown.json', '{}')
        with self.assertRaisesRegex(AssertionError, 'archive changed'):
            m.check_observed(self.original)

    def test_observed_provenance_keeps_changed_bytes_and_versions(self):
        admitted = m.provenance_original(self.original, self.approved)
        host = next(p for p in admitted['packs'] if p['uuid'] == 'host-behavior')
        actual = next(p for p in self.original['packs'] if p['uuid'] == host['uuid'])
        self.assertEqual(host['version'], [1, 0, 2]); self.assertEqual(host['files'], actual['files'])
        self.assertEqual(host['source']['archive_sha256'], 'a' * 64)
        self.assertFalse(host['source']['observed_reviewed_drift']['original_drift_approved'])
        foreign = next(p for p in admitted['packs'] if p['uuid'] == 'foreign-behavior')
        self.assertEqual(foreign['source']['owner'], 'preserved')
        self.assertEqual(len(admitted['packs']), len(self.original['packs']))

    def test_target_and_order_require_exact_additions_swaps_lock_and_source(self):
        with patch.object(migration, 'plan_swaps', return_value=self.swaps):
            self.assertEqual(m.validate_target(self.target, self.original, {'fixture': True}), set(self.additions))
            self.assertEqual(m.reviewed_order(self.original, {'fixture': True}), self.target['order'])
            broken = copy.deepcopy(self.target); broken['order']['behavior'].reverse()
            with self.assertRaisesRegex(AssertionError, 'order'):
                m.validate_target(broken, self.original, {'fixture': True})
            self.review['target']['additions'].append('unreviewed')
            with self.assertRaisesRegex(AssertionError, 'closure'):
                m.validate_target(self.target, self.original, {'fixture': True})

    def test_default_installation_still_rejects_new_identity(self):
        family = [p for p in self.target['packs'] if not p['uuid'].startswith('foreign-')]
        with patch.object(migration, 'plan_swaps', return_value=self.swaps):
            with self.assertRaisesRegex(AssertionError, 'source is missing'):
                deploy.installation_sources(family, self.original, {'fixture': True})
            sources = deploy.installation_sources(family, self.original, {'fixture': True}, self.additions)
            self.assertEqual({p['uuid'] for p in sources}, {'host-behavior', 'host-resource'})

    def test_prepare_and_restore_trusted_stack_preserve_drift_global_and_newest_db(self):
        m.prepare_rollback(self.original)
        self.assertFalse((self.output / 'trusted-pack-rollback/db').exists())
        installed = []
        for side in m.SIDES:
            installed.append(Path(self.pack(self.world, 'candidate-' + side, side, [3, 0, 1])['path']))
        original_before = copy.deepcopy(self.original)
        m.restore(self.original, [], installed)
        self.assertEqual(m.projection(c.live_inventory()), m.receipt_inventory(self.approved))
        for p in self.original['packs']:
            if Path(p['path']).parent.parent == self.world:
                displaced = self.output / 'managed-drift-displaced' / (p['side'] + '_packs') / Path(p['path']).name
                self.assertEqual(hashes(displaced), p['files'])
        self.assertEqual(self.original, original_before)
        self.unchanged_database()
        m.restore(self.original, [], installed)  # Verify, do not consume or overwrite again.
        self.assertEqual(c.sha(self.quality / 'senluo-policy.json'), self.review['approved']['policy_sha256'])

    def test_prepared_corruption_fails_before_moving_live(self):
        m.prepare_rollback(self.original)
        (self.output / 'trusted-pack-rollback/behavior_packs/host-behavior/content.json').write_text('changed')
        before = hashes(self.world)
        with self.assertRaisesRegex(AssertionError, 'modified'):
            m.restore(self.original, [], [])
        self.assertEqual(hashes(self.world), before)
        self.unchanged_database()

    def test_self_consistent_forged_rollback_metadata_cannot_replace_approved_bytes(self):
        m.prepare_rollback(self.original)
        path = self.output / 'trusted-pack-rollback.json'
        record = c.read(path)
        record['packs'][0]['files']['content.json'] = 'e' * 64
        record['trusted_inventory_sha256'] = m.inventory_sha256(record)
        write(path, record)
        before = hashes(self.world)
        with self.assertRaisesRegex(AssertionError, 'immutable approved payload'):
            m.restore(self.original, [], [])
        self.assertEqual(hashes(self.world), before)

    def test_unreviewed_destination_and_global_collision_fail_closed(self):
        m.prepare_rollback(self.original)
        extra = self.pack(self.world, 'owned-behavior', 'behavior', [9, 9, 9])
        before = hashes(self.world)
        with self.assertRaisesRegex(AssertionError, 'destination exists'):
            m.restore(self.original, [], [])
        self.assertEqual(hashes(self.world), before)
        self.assertEqual(hashes(Path(extra['path'])), extra['files'])

    def test_partial_move_failure_keeps_failure_and_does_not_touch_database(self):
        m.prepare_rollback(self.original)
        real_replace = m.os.replace
        count = 0
        def fail_second(source, dest):
            nonlocal count
            count += 1
            if count == 2:
                raise OSError('injected rename failure')
            return real_replace(source, dest)
        with patch.object(m.os, 'replace', side_effect=fail_second), self.assertRaises(OSError):
            m.restore(self.original, [], [])
        self.assertEqual(c.read(self.output / 'managed-drift-pack-recovery.json')['state'], 'recovery_started')
        with self.assertRaisesRegex(AssertionError, 'operator recovery'):
            m.restore(self.original, [], [])
        self.unchanged_database()

    def test_identity_adoption_prevents_any_automatic_pack_restore(self):
        m.prepare_rollback(self.original)
        write(self.output / 'production-identity-migration.json', {'state': 'adoption_started'})
        before = hashes(self.world)
        with self.assertRaisesRegex(AssertionError, 'adoption'):
            m.restore(self.original, [], [])
        self.assertEqual(hashes(self.world), before)
        self.unchanged_database()

    def test_global_inventory_resolves_full_refs_and_rejects_collision(self):
        self.assertEqual(c.live_inventory(), self.original)
        self.pack(self.world, 'foreign-behavior', 'behavior', [1, 2, 0])
        with self.assertRaisesRegex(AssertionError, 'ambiguous'):
            c.live_inventory()


class RecoveryHookTests(unittest.TestCase):
    def test_failure_before_install_still_restores_trusted_packs(self):
        from family_update.test_recovery import RecoveryTests
        case = RecoveryTests('test_verified_normal_rollback_can_start'); case.setUp()
        try:
            with patch.object(deploy, 'CONFIG', {'managed_drift_recovery': 'canonical-review'}), patch.object(deploy, 'verify_original_before_restart'), patch.object(m, 'restart_original_allowed', return_value=True):
                self.assertTrue(deploy.recover_after_failure(case.original, False, [], []))
            case.restore.assert_called_once_with(case.original, [], [])
            self.assertEqual(case.actions, ['start'])
            self.assertEqual(case.result()['state'], 'trusted_approved_stack_running_after_failure')
            self.assertFalse(case.result()['original_inventory_verified'])
            self.assertTrue(case.result()['trusted_approved_inventory_verified'])
        finally:
            case.doCleanups()

    def test_initially_stopped_failure_restores_packs_but_keeps_active_lease(self):
        from family_update.test_recovery import RecoveryTests
        case = RecoveryTests('test_verified_normal_rollback_can_start'); case.setUp()
        try:
            with patch.object(deploy, 'CONFIG', {'managed_drift_recovery': 'canonical-review'}), patch.object(deploy, 'verify_original_before_restart'), patch.object(m, 'restart_original_allowed', return_value=False):
                self.assertFalse(deploy.recover_after_failure(case.original, False, [], []))
            case.restore.assert_called_once_with(case.original, [], [])
            self.assertEqual(case.actions, [])
            self.assertEqual(case.status, 'STOPPED')
            self.assertEqual(case.lease['state'], 'active')
        finally:
            case.doCleanups()


if __name__ == '__main__':
    unittest.main(verbosity=2)
