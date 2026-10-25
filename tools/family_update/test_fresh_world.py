"""Actual fresh-world orchestration with temporary files and external API/BDS doubles.

No engine process, formal world, service or network is used by these tests.
"""
from copy import deepcopy
from pathlib import Path
import shutil
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import family_guard as guard
from family_update import common as c, native_common as native, rehearse_saved_world as rehearsal
from family_update import deploy_live as deploy, workflow, identity_migration, capture_predeploy
from family_update import normal_idle_update as handoff


class FreshWorldTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(); self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name); self.b = self.root / 'servers/test'
        self.r = self.root / 'run'; self.w = self.b / 'worlds/Old'
        self.q = self.root / 'plugins/addon_quality'; self.candidate = self.r / 'release-candidate'
        for path in [self.r, self.w, self.q, self.candidate]: path.mkdir(parents=True)
        for name in ['definitions', 'behavior_packs', 'resource_packs', 'config', 'minecraftpe', 'treatments']:
            (self.b / name).mkdir()
        (self.b / 'bedrock_server').write_bytes(b'NONEXECUTABLE ENGINE FIXTURE')
        (self.b / 'server.properties').write_text('level-name=Old\nlevel-seed=OLD\ngamemode=creative\nserver-port=19132\nserver-portv6=19133\n')
        (self.w / 'db').mkdir(); (self.w / 'db/old').write_bytes(b'old player and actor data')
        (self.w / 'level.dat').write_bytes(b'old spawn/creative metadata')
        self.receipt = {'packs': [], 'order': {'behavior': [], 'resource': []}}
        for side in ['behavior', 'resource']:
            uid = 'new-' + side; path = self.candidate / (side + '_packs') / uid; path.mkdir(parents=True)
            guard.atomic(path / 'manifest.json', {'header': {'uuid': uid, 'version': [1, 0, 1]}})
            (path / 'content').write_bytes(b'canonical curated source')
            self.receipt['packs'].append({'uuid': uid, 'side': side, 'version': [1, 0, 1], 'files': guard.hashes(path),
                                         'source': {'owner': 'owned', 'repository': 'fixture/owned', 'commit': 'committed'}})
            self.receipt['order'][side] = [uid]
            guard.atomic(self.candidate / ('world_' + side + '_packs.json'), [{'pack_id': uid, 'version': [1, 0, 1]}])
            (self.w / (side + '_packs')).mkdir()
            guard.atomic(self.w / ('world_' + side + '_packs.json'), [])
        old = self.b / 'behavior_packs/old-global'; old.mkdir()
        guard.atomic(old / 'manifest.json', {'header': {'uuid': 'old-global', 'version': [1, 0, 0]}})
        (old / 'content').write_bytes(b'unverified old addon')
        guard.atomic(self.w / 'world_behavior_packs.json', [{'pack_id': 'old-global', 'version': [1, 0, 0]}])
        guard.atomic(self.candidate / 'family-receipt.json', self.receipt)
        self.config = {'fresh_world': {'level_name': 'New', 'seed': '12345',
                       'properties': {'gamemode': 'survival', 'difficulty': 'normal', 'level-type': 'DEFAULT'}}}
        self.lease = self.root / 'lease.json'; self.authorization = self.root / 'AGENTS.md'
        self.authorization.write_text('explicit fixture instruction')
        guard.atomic(self.q / 'senluo-policy.json', {'managed_uuids': ['old-global'], 'owned_uuids': [],
                                                   'approved_receipt': '/unverified-old-receipt-not-a-new-input'})
        (self.q / 'family_guard.py').write_text('fixture guard provenance')
        (self.q / 'vibrant_audit.py').write_text('fixture external quality tool')
        (self.q / 'policy.py').write_text("from pathlib import Path\nfrom family_guard import validate_incoming as gate\n"
            "def validate_incoming(packs, enabled, activate):\n gate(packs,Path(__file__).with_name('senluo-policy.json'))\n"
            "def validate_world(world):\n return {'ok':True}\n")
        (self.q.parent / 'addon_localizations').mkdir(); guard.atomic(self.q.parent / 'addon_localizations/index.json', {})
        self.t = self.root / 'source'; (self.t / 'family').mkdir(parents=True)
        guard.atomic(self.t / 'family/upstream.lock.json', {'fixture': True})
        guard.atomic(self.lease, {'state': 'active', 'owner': 'fixture', 'candidate': str(self.r)})
        values = dict(R=self.r, B=self.b, W=self.w, Q=self.q, C=self.candidate, T=self.t,
                      CONFIG=self.config, LEASE=self.lease, OWNER='fixture', SERVER='test', SOURCES={},
                      AUTHORIZATION=self.authorization, EXTENSION=None,
                      G={'hashes': guard.hashes, 'atomic': guard.atomic, 'audit': guard.audit, 'validate_incoming': guard.validate_incoming})
        for module in [c, native, rehearsal, deploy, workflow, identity_migration, capture_predeploy]:
            self.enterContext(patch.multiple(module, **{k: v for k, v in values.items() if hasattr(module, k)}))
        self.posts = []; self.status = 'STOPPED'
        previous_config = self.root / 'previous-config.json'; guard.atomic(previous_config, {'output_dir': '/previous'})
        selector = self.root / 'current.json'; selector.symlink_to(previous_config)
        self.enterContext(patch.object(handoff, 'CURRENT_CONFIG', selector))
        self.enterContext(patch.object(c, '_api_request', self.api))
        self.original = c.live_inventory(); self.old_files = guard.hashes(self.w)
        self.enterContext(patch('family_update.memory_budget.require'))

    def api(self, path, payload=None, method='GET'):
        properties = dict(line.split('=', 1) for line in (self.b / 'server.properties').read_text().splitlines())
        if path == '/api/settings/get': return {'settings': {'paths': {'servers': str(self.b.parent)}}}
        if path.endswith('/summary'): return {'name': 'test', 'status': self.status, 'player_count': 0}
        if path.endswith('/properties/set'):
            self.posts.append((path, deepcopy(payload)))
            self.assertEqual(set(payload), {'properties'}); self.assertEqual(self.status, 'STOPPED')
            properties.update(payload['properties'])
            (self.b / 'server.properties').write_text(''.join(f'{k}={v}\n' for k, v in properties.items()))
            return {'status': 'success', 'message': 'Server properties updated successfully.', 'server_name': 'test'}
        if path.endswith('/properties/get'):
            return {'properties': properties, 'raw_content': (self.b / 'server.properties').read_text()}
        self.fail('Unexpected external operation: ' + path)

    def capture(self):
        # Capture really reads old inventory/policy, but never opens its DB.
        import hashlib
        guard.atomic(self.lease, {'state': 'completed', 'owner': 'Canonical family update ' + hashlib.sha256(b'/previous').hexdigest()[:12], 'candidate': '/previous'})
        capture_predeploy.main(['--execute'])
        guard.atomic(self.lease, {'state': 'active', 'owner': 'fixture', 'candidate': str(self.r)})
        shutil.copytree(self.w, self.r / 'production-snapshot')
        backup = {'consistent_stopped_snapshot': str(self.r / 'production-snapshot'), 'status': 'consistent_stopped_backup',
                  'lease_owner': 'fixture', 'files': guard.hashes(self.r / 'production-snapshot'), 'recorded_at': '2026-10-26T00:00:00Z'}
        guard.atomic(self.r / 'production-before/backup-receipt.json', backup)
        return backup

    def generate(self, fail_restart=False):
        self.capture(); phases = []
        def engine_boundary(engine, phase, **kwargs):
            phases.append(phase); self.assertNotIn('commands', kwargs); self.assertNotIn('delayed_commands', kwargs)
            world = engine / 'worlds/New'
            if phase == 'first':
                self.assertFalse((world / 'level.dat').exists()); self.assertFalse((world / 'db').exists())
                self.assertFalse((engine / 'behavior_packs/old-global').exists())
                self.assertIn('gamemode=survival\n', (engine / 'server.properties').read_text())
                self.assertIn('level-seed=12345\n', (engine / 'server.properties').read_text())
                (world / 'db').mkdir(); (world / 'db/fresh').write_bytes(b'first normal save')
                (world / 'level.dat').write_bytes(b'new native metadata')
            else:
                self.assertEqual((world / 'db/fresh').read_bytes(), b'first normal save')
                (world / 'db/fresh').write_bytes(b'same DB normal restart save')
            log = engine / (phase + '.log'); log.write_text('External engine fixture only\n')
            return {'phase': phase, 'ok': not (fail_restart and phase == 'restart'), 'started': True,
                    'family_initialized': True, 'exit_code': 0, 'errors': [], 'real_player_connections': 0,
                    'commands_sent': False, 'log_sha256': c.sha(log)}
        with patch.object(rehearsal, 'verify_candidate_sources', return_value=self.receipt), \
             patch.object(rehearsal, 'native_run', side_effect=engine_boundary):
            result = rehearsal.main(['--execute'])
        self.assertEqual(phases, ['first', 'restart'])
        self.assertEqual(guard.hashes(self.w), self.old_files)
        return result

    def finalize(self):
        for name in ['build-evidence.json', 'static-evidence.json', 'compatibility-report.json', 'handoff-authorization.json']:
            guard.atomic(self.r / name, {'sources': {}, 'instruction': 'fixture fresh-world instruction'})
        guard.atomic(self.r / 'deployment-initial-state.json', {'fixture': 'normal stopped handoff'})
        return deploy.finalize_receipt()

    def test_empty_generation_same_db_restart_truthful_receipt_and_guard(self):
        self.assertEqual(self.generate(), 0)
        self.assertEqual(c.read(self.r / 'production-before/preserved-packs.json'), [])
        self.assertIsNone(identity_migration.assembly_order(self.original))
        self.assertIsNone(identity_migration.candidate_plan(self.receipt, self.original))
        receipt = self.finalize(); gates = receipt['acceptance']
        self.assertFalse(gates['saved_world_migration']); self.assertTrue(gates['fresh_world_initialization'])
        self.assertTrue(gates['world_persistence']); self.assertFalse(gates['client']); self.assertFalse(receipt['production_ready'])
        deploy.prepare_admission(receipt, self.original)  # Actual family_guard accepts exact fresh evidence.
        self.assertFalse(self.posts)

    def test_admission_then_exact_clean_world_promotion_and_no_restart_property_switch(self):
        self.generate(); receipt = self.finalize()
        source = self.r / 'saved-world-engine/worlds/New'; prepared = guard.hashes(source)
        with patch('family_update.storage.assert_idle'), patch('family_update.storage.require_space'):
            deploy.install_fresh_world(receipt, self.original)
        target = self.b / 'worlds/New'
        self.assertFalse(source.exists()); self.assertEqual(guard.hashes(target), prepared)
        self.assertEqual(guard.hashes(self.w), self.old_files)
        self.assertEqual(len(self.posts), 1); self.assertEqual(c.active_world(), target)
        self.assertEqual(c.verify_server_binding()['level_name'], 'New')
        self.assertEqual({p['uuid'] for p in c.live_inventory()['packs']}, {'new-behavior', 'new-resource'})
        self.assertTrue((self.r / 'production-rollback/behavior_packs/old-global/manifest.json').exists())
        self.assertEqual(self.status, 'STOPPED'); self.assertTrue(deploy.retain_stopped_on_failure())

    def test_failed_restart_or_changed_generated_bytes_cannot_be_promoted(self):
        self.assertEqual(self.generate(fail_restart=True), 1)
        with self.assertRaises(AssertionError): self.finalize()
        self.assertFalse((self.r / 'reviewed-family-receipt.json').exists()); self.assertFalse(self.posts)

    def test_post_validation_world_edit_is_rejected_before_policy_or_switch(self):
        self.generate(); receipt = self.finalize()
        (self.r / 'saved-world-engine/worlds/New/db/fresh').write_bytes(b'QA pollution after validation')
        with patch('family_update.storage.assert_idle'), self.assertRaisesRegex(AssertionError, 'Prepared world changed'):
            deploy.install_fresh_world(receipt, self.original)
        self.assertFalse((self.b / 'worlds/New').exists()); self.assertFalse(self.posts)

    def test_rejected_properties_response_is_preserved_once_and_keeps_stopped_recovery(self):
        self.generate(); receipt = self.finalize()
        def rejected(path, payload=None, method='GET'):
            if path.endswith('/properties/set'):
                self.posts.append((path, deepcopy(payload)))
                return {'status': 'error', 'server_name': 'test', 'message': 'fixture rejection'}
            return self.api(path, payload, method)
        with patch.object(c, '_api_request', rejected), patch('family_update.storage.assert_idle'), \
             patch('family_update.storage.require_space'), self.assertRaises(deploy.RecoveryRequired):
            deploy.install_fresh_world(receipt, self.original)
        self.assertEqual(len(self.posts), 1); self.assertEqual(self.status, 'STOPPED')
        self.assertEqual(c.read(self.r / 'fresh-world-properties-response.json')['status'], 'error')
        self.assertEqual(c.read(self.r / 'deployment-result.json')['state'], 'needs_operator_recovery')
        self.assertEqual(guard.hashes(self.w), self.old_files)

    def test_uncaptured_global_collision_cannot_enter_the_fresh_engine(self):
        self.capture()
        alias = self.b / 'behavior_packs/uncaptured'; alias.mkdir()
        guard.atomic(alias / 'manifest.json', {'header': {'uuid': 'new-behavior', 'version': [0, 0, 1]}})
        with patch.object(rehearsal, 'verify_candidate_sources', return_value=self.receipt), \
             patch.object(rehearsal, 'native_run') as launch, self.assertRaisesRegex(AssertionError, 'Uncaptured global'):
            rehearsal.main(['--execute'])
        launch.assert_not_called(); self.assertFalse((self.r / 'saved-world-engine').exists())

    def test_generation_properties_change_invalidates_native_receipt(self):
        self.generate()
        (self.r / 'saved-world-engine/server.properties').write_text('level-name=Other\n')
        with self.assertRaises(AssertionError): self.finalize()
        self.assertFalse((self.r / 'reviewed-family-receipt.json').exists())

    def stopped_handoff(self):
        self.capture()
        previous = c.read(self.r / 'production-before/capture.json')['previous_lease']
        guard.atomic(self.lease, previous)
        self.enterContext(patch.object(handoff, '_INITIAL', None))
        processes = self.enterContext(patch.object(handoff, '_processes', return_value=[]))
        return previous, processes

    def test_fresh_stopped_preflight_and_post_lease_handoff_use_the_same_normal_owner(self):
        previous, _ = self.stopped_handoff()
        (self.t / 'tools').mkdir(); shutil.copy2(self.q / 'family_guard.py', self.t / 'tools/family_guard.py')
        with patch.object(deploy, 'verify_candidate_sources', return_value=self.receipt), \
             patch.object(workflow, 'record_static'), patch.object(deploy, 'quality'), \
             patch.object(deploy, 'source_state'), patch.object(deploy, 'deployment_authorized', return_value=True), \
             patch('family_update.storage.require_space'):
            self.assertEqual(deploy.preflight(), (self.original, self.receipt))
        deploy.acquire_lease(self.receipt)
        handoff.record_initial_status()
        initial = c.read(self.r / 'deployment-initial-state.json')
        self.assertEqual(initial['server']['status'], 'STOPPED'); self.assertEqual(initial['previous_lease'], previous)
        self.assertFalse(self.posts)

    def test_stopped_handoff_rejects_actual_bds_process_error_or_changed_owner(self):
        previous, processes = self.stopped_handoff()
        processes.return_value = ['123']
        with self.assertRaisesRegex(AssertionError, 'BDS process'): handoff.validate_initial_status(c.summary())
        processes.return_value = []
        self.status = 'ERROR'
        with self.assertRaisesRegex(AssertionError, 'known running or stopped'): handoff.validate_initial_status(c.summary())
        self.status = 'STOPPED'
        guard.atomic(self.lease, {**previous, 'owner': 'foreign'})
        with self.assertRaisesRegex(AssertionError, 'owner changed'): handoff.validate_initial_status(c.summary())
        guard.atomic(self.lease, previous); handoff.validate_initial_status(c.summary())
        deploy.acquire_lease(self.receipt)
        guard.atomic(self.r / 'previous-maintenance.json', {**previous, 'state': 'failed'})
        with self.assertRaisesRegex(AssertionError, 'owner changed'): handoff.record_initial_status()
        self.assertFalse((self.r / 'deployment-initial-state.json').exists()); self.assertFalse(self.posts)

    def test_fresh_handoff_rejects_running_players_and_unknown_counts(self):
        self.stopped_handoff(); self.status = 'RUNNING'
        for count in [1, None, False]:
            with self.subTest(player_count=count), self.assertRaisesRegex(AssertionError, 'confirmed zero players'):
                handoff.validate_initial_status({**c.summary(), 'player_count': count})
        self.assertEqual(handoff.validate_initial_status(c.summary())['server']['status'], 'RUNNING')
        self.assertFalse(self.posts)


if __name__ == '__main__': unittest.main()
