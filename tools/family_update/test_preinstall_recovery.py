import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock, patch

from family_update import common as c
from family_update import preinstall_recovery as p


class PreinstallRecoveryTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.output = self.root / 'failed'
        self.output.mkdir()
        self.world = self.root / 'world'
        (self.world / 'db').mkdir(parents=True)
        (self.world / 'db/CURRENT').write_bytes(b'db-current')
        (self.world / 'level.dat').write_bytes(b'stopped-metadata')
        self.bds = self.root / 'server'
        self.bds.mkdir()
        self.quality = self.root / 'plugins/addon_quality'
        self.quality.mkdir(parents=True)
        (self.quality.parent / 'addon_localizations').mkdir()
        self.source = self.root / 'tavern'
        (self.source / 'family').mkdir(parents=True)
        (self.source / 'family/upstream.lock.json').write_bytes(b'locked')
        self.write(self.source / 'baseline.json', {'runtime': {'BP': 'runtime/BP', 'RP': 'runtime/RP'}})
        self.lease_path = self.root / 'lease.json'
        self.owner = 'Canonical family update ' + hashlib.sha256(str(self.output).encode()).hexdigest()[:12]
        self.original_path, self.config_path = self.root / 'original.json', self.root / 'recovery.json'
        self.original = {'schema': 1, 'server_name': 'test-server', 'output_dir': str(self.output),
                         'bds_root': str(self.bds), 'world_dir': str(self.world), 'quality_dir': str(self.quality),
                         'sources': {'tavern': str(self.source)}, 'extension': '/private-fixture',
                         'lease_file': str(self.lease_path), 'lock_file': str(self.root / 'maintenance.lock'),
                         'authorization_file': '/owner-fixture', 'api_module': '/api-fixture',
                         'api_path_mappings': [], 'managed_drift_recovery': '/review-fixture',
                         'managed_drift_failure_policy': 'retain_stopped',
                         'memory_budget': {'unit': 'original.service', 'limit_bytes': 5 * 1024 ** 3 // 2,
                                           'swap_limit_bytes': 0, 'reserve_bytes': 2 * 1024 ** 3,
                                           'phase_limits': {'light': 512 * 1024 ** 2, 'native': 5 * 1024 ** 3 // 2}}}
        self.write(self.original_path, self.original)
        self.config = {**self.original, 'recovery_original_config': str(self.original_path),
                       'memory_budget': {**self.original['memory_budget'], 'unit': 'recovery.service'}}
        self.write(self.config_path, self.config)
        for name in p.REFERENCE_FILES:
            self.write(self.output / name, {})
        self.inventory = {'packs': [{'uuid': 'observed-only', 'files': {'manifest.json': 'manifest-hash'}}], 'refs': {}}
        self.write(self.output / 'production-before/inventory.json', self.inventory)
        for name in ['senluo-policy.json', 'family_guard.py', 'policy.py', 'vibrant_audit.py']:
            (self.quality / name).write_text('original-' + name)
            (self.output / 'production-before' / name).write_text('original-' + name)
        (self.quality.parent / 'addon_localizations/index.json').write_text('original-index')
        (self.output / 'production-before/index.json').write_text('original-index')
        (self.bds / 'server.properties').write_text('original-properties')
        (self.output / 'production-before/server.properties').write_text('original-properties')
        (self.bds / 'bedrock_server').write_bytes(b'engine')
        self.write(self.output / 'production-before/capture.json', {'engine_sha256': c.sha(self.bds / 'bedrock_server')})
        self.sources = {name: {'path': str(self.source if name == 'tavern' else self.root / name),
                               'commit': 'old-' + name, 'tree': 'tree-' + name,
                               'version': [1, 0, 1], 'baseline_sha256': 'baseline-' + name,
                               'source_trees': {'BP': 'unchanged', 'RP': 'unchanged'},
                               'repository': 'fixture/' + name} for name in ('tavern', 'grilling', 'world-liquor', 'extension')}
        self.build = {'config_sha256': c.sha(self.original_path), 'sources': self.sources,
                      'candidate_receipt_sha256': c.sha(self.output / 'release-candidate/family-receipt.json'),
                      'upstream_lock_sha256': c.sha(self.source / 'family/upstream.lock.json'),
                      'external_input_sha256': {'review': 'reviewed'},
                      'orchestration_sha256': {'family_update.py': hashlib.sha256(b'old-runner').hexdigest()},
                      'tool_sha256': {'family_bundle.py': hashlib.sha256(b'old-tool').hexdigest()}}
        self.write(self.output / 'build-evidence.json', self.build)
        static = {'ok': True, 'pr_checks_verified': True, 'sources': self.sources,
                  'candidate_receipt_sha256': self.build['candidate_receipt_sha256'],
                  'reports': [c.report_ref(self.output / name) for name in ['build-evidence.json', 'ci-evidence.json']],
                  'checks': [{'exit_code': 0, 'log': str(self.output / 'ci-evidence.json'), 'sha256': c.sha(self.output / 'ci-evidence.json')}]}
        self.write(self.output / 'static-evidence.json', static)
        self.write(self.output / 'compatibility-report.json', {'ok': True})
        self.failure = {'state': 'needs_operator_recovery', 'phase': 'retain_stopped_without_package_or_database_restore',
                        'server_status': 'STOPPED', 'restart_attempted': False, 'save_database_restored': False}
        self.write(self.output / 'deployment-recovery.json', self.failure)
        self.write(self.output / 'stop-result.json', {'status': 'success', 'result': {'status': 'success', 'server_name': 'test-server'}})
        budget = self.original['memory_budget']
        self.memory = {'observations': [{'ok': False, 'phase': 'saved-world', 'phase_category': 'native',
                    'unit': budget['unit'], 'limit_bytes': budget['limit_bytes'], 'reserve_bytes': budget['reserve_bytes'],
                    'previous_limit_bytes': budget['phase_limits']['light'], 'swap_limit_bytes': 0,
                    'available_bytes': 4 * 1024 ** 3, 'required_available_bytes': budget['limit_bytes'] + budget['reserve_bytes'],
                    'memory_events': {'oom': '0', 'oom_kill': '0', 'max': '10'}}]}
        self.write(self.output / 'memory-admissions.json', self.memory)
        self.lease = {'state': 'active', 'owner': self.owner, 'candidate': str(self.output),
                      'status': 'needs_operator_recovery', 'recovery_report': str(self.output / 'deployment-recovery.json'),
                      'candidate_receipt_sha256': self.build['candidate_receipt_sha256']}
        self.write(self.lease_path, self.lease)
        values = {'R': self.output, 'C': self.output / 'release-candidate', 'W': self.world, 'B': self.bds,
                  'Q': self.quality, 'T': self.source, 'LEASE': self.lease_path, 'LOCK': self.root / 'maintenance.lock',
                  'OWNER': self.owner, 'SERVER': 'test-server', 'CONFIG': self.config, 'CONFIG_PATH': self.config_path}
        for name, value in values.items():
            patcher = patch.object(c, name, value)
            patcher.start(); self.addCleanup(patcher.stop)
        for name, options in {
            'atomic': {'side_effect': self.write}, 'hashes': {'side_effect': self.hashes},
            'summary': {'return_value': {'name': 'test-server', 'status': 'STOPPED', 'player_count': 0}},
            'live_inventory': {'side_effect': lambda: self.inventory},
            'source_state': {'side_effect': lambda: self.sources},
            'audit_candidate': {}, 'external_input_hashes': {'return_value': {'review': 'reviewed'}},
            'orchestration_hashes': {'return_value': {'family_update.py': hashlib.sha256(b'old-runner').hexdigest(),
                                                     'family_update/preinstall_recovery.py': hashlib.sha256(b'old-tool').hexdigest()}},
            'now': {'return_value': '2026-10-18T15:00:00+00:00'},
            'git': {'side_effect': lambda path, *args: '' if args[0] == 'diff' else ('tree-tavern' if args[-1].endswith('^{tree}') else 'same-runtime-object')},
        }.items():
            patcher = patch.object(c, name, **options)
            patcher.start(); self.addCleanup(patcher.stop)
        patcher = patch.object(p.subprocess, 'run', return_value=Mock(returncode=0))
        patcher.start(); self.addCleanup(patcher.stop)
        patcher = patch.object(p, '_blob', side_effect=lambda path, revision, relative: b'old-runner' if relative.endswith('family_update.py') else b'old-tool')
        patcher.start(); self.addCleanup(patcher.stop)

    def write(self, path, value):
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(p._bytes(value))

    def hashes(self, root):
        root = Path(root)
        return {path.relative_to(root).as_posix(): c.sha(path) for path in sorted(root.rglob('*')) if path.is_file()}

    def close(self):
        return p.main(['--execute'])

    def next_context(self):
        c.R = self.root / 'next'
        c.CONFIG = {**self.original, 'output_dir': str(c.R), 'preinstall_recovery_output': str(self.output)}

    def test_close_only_lease_and_append_proof_preserving_original_failure_and_world(self):
        before = {str(path): path.read_bytes() for path in self.output.rglob('*') if path.is_file()}
        database = p._database()
        result = self.close()
        self.assertEqual(result['state'], p.KIND)
        self.assertEqual(p._database(), database)
        for path, raw in before.items():
            self.assertEqual(Path(path).read_bytes(), raw)
        closed = c.read(self.lease_path)
        self.assertEqual(closed['state'], 'failed')
        self.assertEqual(closed['preinstall_abort'], str(self.output / p.PROOF))
        self.assertEqual(c.sha(self.lease_path), c.read(self.output / p.PROOF)['closed_lease']['sha256'])
        self.next_context()
        self.assertTrue(p.verify_completed(self.output, c.summary())['database_unchanged_since_abort'])

    def test_any_post_stop_or_unknown_artifact_rejects_without_writing_proof(self):
        for name in ['production-snapshot', 'saved-world-engine', 'saved-world-report.json',
                     'production-staged', 'production-rollback', 'observed-global-displaced',
                     'admission-policy.json', 'reviewed-family-receipt.json', 'rollback-map.json',
                     'production-identity-migration.json', 'production-container-recovery.json',
                     'original-db', 'start-result.json', 'retired-copies.json']:
            with self.subTest(name=name):
                path = self.output / name
                path.mkdir()
                with self.assertRaises(AssertionError): self.close()
                path.rmdir()
                self.assertEqual(c.read(self.lease_path), self.lease)
                self.assertFalse((self.output / p.PROOF).exists())
        self.write(self.output / 'production-before/backup-receipt.json', {})
        with self.assertRaises(AssertionError): self.close()

    def test_only_actual_native_admission_failure_without_oom_is_eligible(self):
        for changes in [{'ok': True}, {'phase': 'saved_world_first'}, {'phase_category': 'light'},
                        {'available_bytes': 9 * 1024 ** 3}, {'memory_events': {'oom': '1'}},
                        {'limit_bytes': 512 * 1024 ** 2}]:
            with self.subTest(changes=changes):
                changed = {'observations': [{**self.memory['observations'][0], **changes}]}
                self.write(self.output / 'memory-admissions.json', changed)
                with self.assertRaises(AssertionError): self.close()
                self.assertFalse((self.output / p.PROOF).exists())

    def test_original_config_and_recovery_boundary_cannot_change(self):
        c.CONFIG = {**self.config, 'server_name': 'different'}
        with self.assertRaises(AssertionError): self.close()
        c.CONFIG = self.config
        self.original_path.write_text('{}')
        with self.assertRaises((AssertionError, KeyError)): self.close()

    def test_foreign_or_stolen_active_lease_remains_active(self):
        self.write(self.lease_path, {**self.lease, 'owner': 'foreign'})
        with self.assertRaises(AssertionError): self.close()
        self.assertFalse((self.output / p.PROOF).exists())

    def test_changed_inventory_and_policy_fail_actual_predeploy_gate(self):
        self.inventory = {'packs': [], 'refs': {}}
        with self.assertRaisesRegex(AssertionError, 'Concurrent live'): self.close()
        self.inventory = c.read(self.output / 'production-before/inventory.json')
        (self.quality / 'senluo-policy.json').write_text('changed-policy')
        with self.assertRaisesRegex(AssertionError, 'Concurrent policy'): self.close()
        self.assertEqual(c.read(self.lease_path), self.lease)

    def test_changed_static_or_candidate_bytes_cannot_close_owner(self):
        (self.output / 'release-candidate/family-receipt.json').write_text('{"different":true}')
        with self.assertRaisesRegex(AssertionError, 'candidate receipt'): self.close()

    def test_database_change_during_inspection_keeps_active_lease(self):
        def audit(*args):
            (self.world / 'db/CURRENT').write_text('concurrent-write')
        c.audit_candidate.side_effect = audit
        with self.assertRaisesRegex(AssertionError, 'database changed'): self.close()
        self.assertEqual(c.read(self.lease_path), self.lease)
        self.assertFalse((self.output / p.PROOF).exists())

    def test_post_snapshot_marker_appearing_during_candidate_audit_does_not_close_owner(self):
        c.audit_candidate.side_effect = lambda *args: (self.output / 'production-snapshot').mkdir()
        with self.assertRaisesRegex(AssertionError, 'Post-stop'): self.close()
        self.assertEqual(c.read(self.lease_path), self.lease)
        self.assertFalse((self.output / p.PROOF).exists())

    def test_changed_producer_runner_is_rejected_as_a_git_blob_mismatch(self):
        self.close()
        self.next_context()
        proof = c.read(self.output / p.PROOF)
        proof['producer']['orchestration_sha256']['family_update/preinstall_recovery.py'] = 'fabricated'
        self.write(self.output / p.PROOF, proof)
        with self.assertRaisesRegex(AssertionError, 'producer runner changed'):
            p.verify_completed(self.output, c.summary())

    def test_runtime_drift_and_unreviewed_tavern_advancement_are_rejected(self):
        self.sources['tavern'] = {**self.sources['tavern'], 'version': [1, 0, 2]}
        with self.assertRaisesRegex(AssertionError, 'runtime or baseline'): self.close()
        self.sources = dict(c.read(self.output / 'build-evidence.json')['sources'])
        c.git.side_effect = lambda path, *args: 'runtime/BP/changed.js' if args[0] == 'diff' else 'same-runtime-object'
        with self.assertRaisesRegex(AssertionError, 'tooling paths'): self.close()

    def test_non_tavern_commit_and_original_runner_hashes_remain_exact(self):
        self.sources['extension'] = {**self.sources['extension'], 'commit': 'foreign-private'}
        with self.assertRaisesRegex(AssertionError, 'Non-Tavern'): self.close()
        self.sources = dict(c.read(self.output / 'build-evidence.json')['sources'])
        p._blob.side_effect = lambda *args: b'not-the-original-runner'
        with self.assertRaisesRegex(AssertionError, 'Original runner'): self.close()

    def test_closed_record_database_and_proof_tampering_deny_next_owner(self):
        self.close()
        self.next_context()
        closed = c.read(self.lease_path)
        self.write(self.lease_path, {**closed, 'owner': 'stolen'})
        with self.assertRaisesRegex(AssertionError, 'closure changed'): p.verify_completed(self.output, c.summary())
        self.write(self.lease_path, closed)
        (self.world / 'db/CURRENT').write_text('changed-after-abort')
        with self.assertRaisesRegex(AssertionError, 'database changed since'): p.verify_completed(self.output, c.summary())
        (self.world / 'db/CURRENT').write_bytes(b'db-current')
        proof = c.read(self.output / p.PROOF)
        self.write(self.output / p.PROOF, {**proof, 'world_mutated': True})
        with self.assertRaises(AssertionError): p.verify_completed(self.output, c.summary())

    def test_immutable_input_refs_survive_next_lease_and_database_adoption(self):
        self.close()
        self.next_context()
        before = p.input_refs()
        self.write(self.lease_path, {'state': 'active', 'owner': 'next-owner'})
        (self.world / 'db/CURRENT').write_text('newest-adopted-db')
        self.assertEqual(p.input_refs(), before)
        self.assertIn('preinstall_recovery_abort', before)

    def test_partial_lease_write_preserves_proof_and_retry_never_overwrites_it(self):
        self.write(self.output / 'preinstall-recovery-memory-admissions.json', {'observations': []})
        c.atomic.side_effect = OSError('fixture write failure')
        with self.assertRaises(OSError): self.close()
        raw = (self.output / p.PROOF).read_bytes()
        self.assertEqual(c.read(self.lease_path), self.lease)
        c.atomic.side_effect = self.write
        self.close()
        self.assertEqual((self.output / p.PROOF).read_bytes(), raw)


if __name__ == '__main__':
    unittest.main()
