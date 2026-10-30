"""Direct deletion counterexamples; temp fixtures only, no native/live operations."""
import copy
from collections import Counter
import gc
import hashlib
import json
import os
from pathlib import Path
import shutil
import sys
import tempfile
import unittest
import weakref
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from family_update import retention as m

class RetentionTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.lease = self.root / 'lease.json'
        self.write(self.lease, {'state': 'completed'})
        self.a, self.b, self.c = [self.deployment(name, day, saved_only=day == 3)
                                for name, day in [('old', 1), ('previous', 2), ('new', 3)]]
        self.idle = patch.object(m, 'assert_idle')
        self.idle.start()
        self.addCleanup(self.idle.stop)
    def write(self, path, data):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(data))
    def modify(self, output, name, fn):
        p = output / name
        d = json.loads(p.read_text())
        fn(d)
        self.write(p, d)
    def deployment(self, name, day, saved_only=False):
        r = self.root / name
        stamp = f'2026-10-{day:02}T01:00:00+00:00'
        assembled, reviewed, engine = name + '-assembled', name + '-reviewed', 'original-engine'
        refs = [{'path': str(r / relative), 'sha256': relative + '-existing-digest'} for relative in [
            'saved-world-report.json', 'exact-engine/native-report.json', 'production-before/backup-receipt.json',
            'build-evidence.json', 'static-evidence.json']]
        packs = [{'side': side, 'uuid': side + '-uuid', 'files': {'manifest.json': hashlib.sha256(b'copy').hexdigest()}} for side in ['behavior', 'resource']]
        inventory = {'packs': [{**p, 'files': {'manifest.json': hashlib.sha256(b'old pack').hexdigest()}, 'path': str(self.root / 'live' / (p['side'] + '_packs') / p['uuid'])} for p in packs]}
        rollback = {'backup': str(r / 'production-snapshot'), 'original_inventory': str(r / 'production-before/inventory.json'),
                    'retired': [[str(r / 'production-rollback' / (p['side'] + '_packs') / p['uuid']), p['path']] for p in inventory['packs']]}
        backup_files = {path: hashlib.sha256(b'backup').hexdigest() for path in ['level.dat', 'db/data', 'behavior_packs/behavior-uuid/manifest.json', 'resource_packs/resource-uuid/manifest.json']}
        dep = {'state': 'deployed_running', 'completed_at': stamp, 'guard_admission_passed': True,
               'receipt_sha256': reviewed, 'assembled_receipt_sha256': assembled, 'poststart_report': str(r / 'poststart-verification.json'),
               'rollback': str(r / 'production-rollback'), 'versions': {'family': [day]}}
        post = {'ok': True, 'summary': {'status': 'RUNNING'}, 'receipt_sha256': reviewed, 'pack_count': 2,
                'exact_pack_files_and_order': True, 'whole_stack_quality': True, 'native_started': True,
                'family_initialized': True, 'errors': [], 'drift': {'ok': True}, 'versions': dep['versions']}
        native = {'candidate_receipt_sha256': assembled, 'bds': True, 'exact_files_checked': True,
                  'test_only_overlays': [], 'simulated_players': False, 'real_players': 0, 'engine_sha256': engine,
                  'engine_inputs': {'original': 'bound'}, 'versions': dep['versions'],
                  'runs': [{'phase': phase, 'started': True, 'family_initialized': True, 'exit_code': 0,
                            'errors': [], 'real_player_connections': 0, 'ok': True} for phase in ['first', 'restart']]}
        saved = {**native, 'fresh_stopped_backup': True, 'existing_world_loaded': True, 'saved_world_migration': True,
                 'players': 0, 'player_records_before': {'player': 'existing'}, 'player_records_after': {'player': 'existing'},
                 'snapshot_source': str(r / 'production-snapshot'), 'snapshot_cutoff': stamp,
                 'backup_receipt': next(p for p in refs if p['path'].endswith('backup-receipt.json')),
                 'runs': [{**run, 'player_records_unchanged': True, 'custom_container_inventories_retained': True} for run in native['runs']]}
        docs = {'deployment-result.json': dep, 'poststart-verification.json': post, 'saved-world-report.json': saved,
                'exact-engine/native-report.json': native, 'admission-report.json': {'ok': True, 'candidate_receipt_sha256': assembled, 'reviewed_receipt_sha256': reviewed, 'complete_packs': 2},
                'production-before/backup-receipt.json': {'status': 'consistent_stopped_backup', 'live_status': 'STOPPED', 'consistent_stopped_snapshot': str(r / 'production-snapshot'), 'recorded_at': stamp, 'level_dat_sha256': backup_files['level.dat'], 'files': backup_files},
                'reviewed-family-receipt.json': {'acceptance': {'static': True, 'bds': True, 'saved_world_migration': True}, 'packs': packs,
                                               'assembled_receipt': {'path': str(r / 'release-candidate/family-receipt.json'), 'sha256': assembled}, 'evidence': {'reports': refs}},
                'build-evidence.json': {'candidate_receipt_sha256': assembled, 'versions': dep['versions'], 'sources': {'tavern': {'canonical_path': str(self.root / 'source')}}},
                'static-evidence.json': {'ok': True, 'pr_checks_verified': True, 'candidate_receipt_sha256': assembled},
                'rollback-map.json': rollback, 'production-before/inventory.json': inventory}
        if saved_only:
            saved.update(native_acceptance_source='saved_world')
            del docs['exact-engine/native-report.json']
            refs[:] = [row for row in refs if not row['path'].endswith('exact-engine/native-report.json')]
        for relative, value in docs.items():
            self.write(r / relative, value)
        for relative in m.COPIES:
            p = r / relative
            p.mkdir(parents=True)
            if relative.endswith('packs'):
                side = 'behavior' if relative.endswith('behavior_packs') else 'resource'
                (p / (side + '-uuid')).mkdir()
                (p / (side + '-uuid') / 'manifest.json').write_text('copy')
            else:
                (p / 'data').write_text('qa db')
        for relative in backup_files:
            p = r / 'production-snapshot' / relative
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text('backup')
        for source, _ in rollback['retired']:
            p = Path(source)
            p.mkdir(parents=True)
            (p / 'manifest.json').write_text('old pack')
        (r / 'production-staged/behavior_packs').mkdir(parents=True)
        (r / 'production-original-db').mkdir()
        (r / 'production-original-db/never').write_text('migration original')
        (r / 'original.mcaddon').write_text('author archive')
        (r / 'production-startup.log').write_text('evidence')
        return r
    def plan(self, **kwargs):
        return m.plan(self.root, lease=self.lease, **kwargs)
    def row(self, plan, output):
        return next(row for row in plan['outputs'] if row['output'] == str(output))
    def execute(self, planned, **kwargs):
        return m.execute(planned, lease=self.lease, **kwargs)
    def m1_deployment(self, name='m1-live'):
        r = self.root / name
        server, world = '/var/lib/docker/volumes/bsm_data/_data/servers/luosen', 'Senluo'
        previous = {'schema': 1, 'name': 'previous', 'digest_format': m.M1_TREE_DIGEST_FORMAT,
                    'observed_at': '2026-10-29T00:00:00+00:00',
                    'status': {'ci': False, 'staging_smoke': False, 'staging_human': None, 'live': None},
                    'packs': [{'kind': 'behavior', 'slot': 1, 'uuid': '11111111-1111-4111-8111-111111111111',
                               'version': [1, 0, 0], 'path': 'behavior_packs/old',
                               'sha256': '910d3f050dae67a6633db910d18a481384e29a8d2cd88a2194b32ef30b9a3bcf'}]}
        candidate = {'schema': 1, 'name': 'candidate', 'digest_format': m.M1_TREE_DIGEST_FORMAT,
                     'observed_at': '2026-10-30T00:00:00+00:00',
                     'status': {'ci': True, 'staging_smoke': True, 'staging_human': False, 'live': False},
                     'packs': [{'kind': 'behavior', 'slot': 1, 'uuid': '22222222-2222-4222-8222-222222222222',
                                'version': [2, 0, 0], 'path': f'worlds/{world}/behavior_packs/new',
                                'sha256': '393dfa706fb9e01a81d106ee05fd80af7f69f32101bbddb29aeadce8cd59f37f'}]}
        self.write(r / 'previous-lock.json', previous)
        self.write(r / 'candidate-lock.json', candidate)
        (r / 'backup/world/db').mkdir(parents=True, exist_ok=True)
        (r / 'backup/world/db/data').write_bytes(b'world-leveldb-bytes')
        (r / 'backup/world/level.dat').write_bytes(b'level')
        (r / 'backup/server/behavior_packs/old').mkdir(parents=True)
        (r / 'backup/server/behavior_packs/old/manifest.json').write_bytes(b'previous-pack')
        manifest = {'world_sha256': '84754d022bd88f4ca63bbc369b2b760332f78b75e7a5165c650e2753ff6c6ff1',
                    'global_packs': {'behavior_packs/old': previous['packs'][0]['sha256']},
                    'previous_lock_sha256': hashlib.sha256((r / 'previous-lock.json').read_bytes()).hexdigest(),
                    'candidate_lock_sha256': hashlib.sha256((r / 'candidate-lock.json').read_bytes()).hexdigest()}
        self.write(r / 'backup/manifest.json', manifest)
        controls = {
            'policy': ('policy-original.json', 'senluo-policy.json', b'old policy'),
            'family_guard': ('family-guard-original.py', 'family_guard.py', b'old family guard'),
            'stable_lock_guard': ('stable-lock-guard-original.py', 'stable_lock_guard.py', b'old stable guard'),
            'current_selector': ('current-selector.json', 'current.json', b'old selector'),
        }
        control_rows = {}
        for key, (backup_name, source_name, content) in controls.items():
            (r / 'backup' / backup_name).write_bytes(content)
            control_rows[key] = {'source': '/tmp/quality/' + source_name, 'backup': backup_name,
                                 'present': True, 'sha256': hashlib.sha256(content).hexdigest(),
                                 'size': len(content), 'mode': 0o600, 'uid': 1000, 'gid': 1000}
        self.write(r / 'backup/control-state.json', {'schema': 1, 'files': control_rows})
        receipt = {'schema': 1, 'operation': 'live_family_deployment', 'server': server, 'world': world,
                   'status': 'deployed', 'result': 'deployed', 'live': True, 'client': False,
                   'production_ready': False, 'finished_at': '2026-10-30T02:00:00+00:00',
                   'live_save_binding': {'status': 'verified', 'world': world,
                                         'live_world': server + '/worlds/' + world},
                   'candidate_lock_sha256': hashlib.sha256((r / 'candidate-lock.json').read_bytes()).hexdigest(),
                   'backup_manifest_sha256': hashlib.sha256((r / 'backup/manifest.json').read_bytes()).hexdigest(),
                   'control_state': {'path': str((r / 'backup/control-state.json').resolve()),
                       'sha256': hashlib.sha256((r / 'backup/control-state.json').read_bytes()).hexdigest()},
                   'control_state_sha256': hashlib.sha256((r / 'backup/control-state.json').read_bytes()).hexdigest()}
        self.write(r / 'receipt.json', receipt)
        return r

    def test_m1_rollback_is_newest_complete_and_legacy_copies_can_retire(self):
        m1 = self.m1_deployment()
        planned = self.plan()
        self.assertEqual(planned['newest_retained'], [str(m1)])
        self.assertTrue(planned['rollback_retention_ready'])
        self.assertEqual(self.row(planned, m1)['delete'], [])
        self.assertIn('M1 run is retained whole', self.row(planned, m1)['reason'])
        result = self.execute(planned)
        self.assertEqual(result['state'], 'completed')
        for output in (self.a, self.b, self.c):
            self.assertFalse((output / 'production-snapshot').exists())
        self.assertTrue((m1 / 'backup/world/db/data').exists())
        self.assertTrue((m1 / 'backup/server/behavior_packs/old/manifest.json').exists())

    def test_m1_bad_world_global_manifest_or_lock_reference_never_counts(self):
        cases = ('world', 'global', 'manifest', 'lock', 'control-missing', 'control-corrupt')
        for case in cases:
            with self.subTest(case=case):
                m1 = self.m1_deployment('m1-live-' + case)
                if case == 'world':
                    (m1 / 'backup/world/db/data').write_bytes(b'corrupt')
                elif case == 'global':
                    (m1 / 'backup/server/behavior_packs/old/manifest.json').unlink()
                elif case == 'manifest':
                    self.modify(m1 / 'backup', 'manifest.json', lambda value: value.update(world_sha256='0' * 64))
                elif case == 'control-missing':
                    (m1 / 'backup/policy-original.json').unlink()
                elif case == 'control-corrupt':
                    (m1 / 'backup/policy-original.json').write_bytes(b'corrupt')
                else:
                    self.modify(m1, 'candidate-lock.json', lambda value: value.update(name='changed'))
                planned = self.plan()
                self.assertEqual(planned['newest_retained'], [str(self.c)])
                self.assertTrue(planned['rollback_retention_ready'])
                row = self.row(planned, m1)
                self.assertEqual(row['delete'], [])
                self.assertIn('mismatched M1', row['reason'])
                self.assertTrue((m1 / 'receipt.json').exists())

    def test_m1_explicit_absent_stable_guard_is_a_complete_control_snapshot(self):
        m1 = self.m1_deployment()
        state_path = m1 / 'backup/control-state.json'
        state = json.loads(state_path.read_text())
        state['files']['stable_lock_guard'] = {
            'source': '/tmp/quality/stable_lock_guard.py',
            'backup': 'stable-lock-guard-original.py',
            'present': False, 'sha256': None, 'size': None,
            'mode': None, 'uid': None, 'gid': None}
        (m1 / 'backup/stable-lock-guard-original.py').unlink()
        self.write(state_path, state)
        receipt_path = m1 / 'receipt.json'
        receipt = json.loads(receipt_path.read_text())
        control_sha = hashlib.sha256(state_path.read_bytes()).hexdigest()
        receipt['control_state'] = {'path': str(state_path.resolve()), 'sha256': control_sha}
        receipt['control_state_sha256'] = control_sha
        self.write(receipt_path, receipt)
        planned = self.plan()
        self.assertEqual(planned['newest_retained'], [str(m1)])
        self.assertTrue(planned['rollback_retention_ready'])
    def test_latest_one_original_evidence_retained_with_single_integrity_boundary(self):
        before = {rel: (self.a / rel).read_bytes() for rel in m.REPORTS}
        p = self.plan()
        self.assertEqual(p['retain'], 1)
        self.assertEqual(p['newest_retained'], [str(self.c)])
        self.assertTrue(p['rollback_retention_ready'])
        self.assertEqual(len(self.row(p, self.a)['delete']), 11)
        self.assertTrue((self.a / 'production-snapshot').exists()) # read-only plan
        result = self.execute(p)
        self.assertEqual(result['state'], 'completed')
        for rel in m.COPIES + m.BACKUPS:
            self.assertFalse((self.a / rel).exists())
            self.assertFalse((self.b / rel).exists())
            self.assertTrue((self.c / rel).exists())
        for rel, data in before.items():
            self.assertEqual((self.a / rel).read_bytes(), data)
        self.assertTrue((self.a / 'production-original-db/never').exists())
        self.assertTrue((self.a / 'original.mcaddon').exists())
        marker = json.loads((self.a / m.MARKER).read_text())
        self.assertTrue(marker['cannot_resume_or_redeploy'])
        self.assertEqual(marker['state'], 'pruned')
        self.assertEqual(result['retained_backup_integrity']['hash_boundary_passes'], 1)
        self.assertFalse((self.c / 'exact-engine/native-report.json').exists())
        self.assertIn('disk_after', result)
    def test_completed_sort_uses_metadata_not_output_name(self):
        self.modify(self.a, 'deployment-result.json', lambda d: d.update(completed_at='2026-10-04T01:00:00+00:00'))
        self.assertEqual(self.plan()['newest_retained'], [str(self.a)])

    def fresh_deployment(self):
        target = str(self.root / 'live/worlds/New')
        self.modify(self.c, 'deployment-result.json', lambda d: d.update(fresh_world=target))
        self.modify(self.c, 'poststart-verification.json', lambda d: d.update(active_world_binding={'world_dir': target}))
        self.modify(self.c, 'rollback-map.json', lambda d: d.update(original_world=str(self.root / 'old-world')))
        def saved(d):
            d.update(native_acceptance_source='fresh_world', fresh_world_initialization=True, world_persistence=True,
                     saved_world_migration=False, existing_world_loaded=False, rollback_snapshot=d.pop('snapshot_source'))
            d['runs'][0].update(world_input_files={}, world_output_files={'db/data': 'first'})
            d['runs'][1].update(world_input_files={'db/data': 'first'}, world_output_files={'db/data': 'restart'})
            d['world_files'] = {'db/data': 'restart'}
            for row in d['runs']: row.update(generated_database=True, commands_sent=False)
        self.modify(self.c, 'saved-world-report.json', saved)
        def receipt(d):
            d['acceptance'].update(saved_world_migration=False, fresh_world_initialization=True, world_persistence=True)
            d['world_initialization'] = {'kind': 'fresh_world', 'level_name': 'New'}
        self.modify(self.c, 'reviewed-family-receipt.json', receipt)

    def test_fresh_delivery_retains_one_complete_old_rollback_and_retires_old_generated_copies(self):
        self.fresh_deployment()
        planned = self.plan()
        self.assertEqual(planned['newest_retained'], [str(self.c)]); self.assertTrue(planned['rollback_retention_ready'])
        self.assertEqual(self.execute(planned)['state'], 'completed')
        self.assertTrue((self.c / 'production-snapshot/level.dat').exists())
        self.assertTrue((self.c / 'production-rollback/behavior_packs/behavior-uuid/manifest.json').exists())
        self.assertFalse((self.a / 'production-snapshot').exists()); self.assertFalse((self.b / m.COPIES[0]).exists())

    def test_missing_fresh_persistence_or_global_rollback_preserves_unproven_copies(self):
        self.fresh_deployment()
        self.modify(self.c, 'reviewed-family-receipt.json', lambda d: d['acceptance'].update(world_persistence=False))
        planned = self.plan(); self.assertEqual(self.row(planned, self.c)['delete'], [])
        self.modify(self.c, 'reviewed-family-receipt.json', lambda d: d['acceptance'].update(world_persistence=True))
        self.modify(self.c, 'rollback-map.json', lambda d: d.update(retired=d['retired'][:1]))
        planned = self.plan(); self.assertEqual(self.row(planned, self.c)['delete'], [])
        self.assertFalse(planned['rollback_retention_ready'])
        self.assertTrue(all(not (self.row(planned, output)['delete'] and any(
            row['relative'] in m.BACKUPS for row in self.row(planned, output)['delete'])) for output in [self.a, self.b]))
    def test_many_histories_validate_once_without_retaining_full_proof_documents(self):
        histories = [self.a, self.b, self.c]
        histories += [self.deployment(f'history-{day}', day) for day in range(4, 25)]
        class Documents(dict):
            pass
        original_proof, original_read = m._proof, m._read
        documents, proof_calls, report_reads = [], Counter(), Counter()
        peak = 0
        def observed_proof(output, *args):
            nonlocal peak
            proof_calls[output] += 1
            proof = original_proof(output, *args)
            proof['docs'] = Documents(proof['docs'])
            documents.append(weakref.ref(proof['docs']))
            gc.collect()
            peak = max(peak, sum(reference() is not None for reference in documents))
            return proof
        def observed_read(path, *args, **kwargs):
            report_reads[path] += 1
            return original_read(path, *args, **kwargs)
        with patch.object(m, '_proof', side_effect=observed_proof), patch.object(m, '_read', side_effect=observed_read):
            planned = self.plan(retain=2)
        self.assertEqual(proof_calls, Counter({output: 1 for output in histories}))
        self.assertEqual(planned['newest_retained'], [str(histories[-1]), str(histories[-2])])
        self.assertTrue(planned['rollback_retention_ready'])
        self.assertTrue(all('binding' in self.row(planned, output) for output in histories))
        self.assertEqual(sum(self.row(planned, output)['state'] == 'eligible' for output in histories), len(histories) - 2)
        for output in histories:
            for name in ['reviewed-family-receipt.json', 'production-before/inventory.json', 'production-before/backup-receipt.json']:
                self.assertEqual(report_reads[output / name], 1, str(output / name))
        self.assertLessEqual(peak, 3, 'full proof reachability must stay bounded by retained rollbacks plus one history')
        gc.collect()
        self.assertFalse(any(reference() is not None for reference in documents), 'returned plan must not retain full proof documents')
    def test_report_changed_after_header_discovery_is_still_validated_and_preserved(self):
        original_proof = m._proof
        calls = Counter()
        def changed_report(output, *args):
            calls[output] += 1
            if output == self.c:
                self.modify(self.a, 'poststart-verification.json', lambda d: d.update(receipt_sha256='changed-after-headers'))
            return original_proof(output, *args)
        with patch.object(m, '_proof', side_effect=changed_report):
            planned = self.plan()
        self.assertEqual(calls, Counter({output: 1 for output in [self.a, self.b, self.c]}))
        self.assertEqual(self.row(planned, self.a)['delete'], [])
        self.assertIn('Reviewed receipt binding differs', self.row(planned, self.a)['reason'])
        self.assertTrue((self.a / m.COPIES[0]).exists())
        self.assertTrue(self.row(planned, self.b)['delete'])
        self.assertTrue(planned['rollback_retention_ready'])
    def reviewed_plan(self, targets):
        receipt = json.loads((self.a / 'reviewed-family-receipt.json').read_text())
        self.write(self.a / 'release-candidate/family-receipt.json', {'packs': receipt['packs']})
        manifest = self.root / 'reviewed.json'
        self.write(manifest, {'schema': 1, 'outputs': [
            {'output': str(self.a), 'reason': 'Superseded test fixture; preserve original reports', 'targets': targets}]})
        return self.plan(retire_outputs=manifest)
    def stable_projection(self):
        run = self.a
        source = {'owner': 'owned', 'repository': 'burnt-tea-dev/kaleidoscope-tavern-unofficial',
                  'commit': 'a' * 40, 'working_candidate': False}
        receipt_packs, lock_packs, order, projected = [], [], {'behavior': [], 'resource': []}, []
        for side, uid in [('behavior', '11111111-1111-4111-8111-111111111111'),
                          ('resource', '22222222-2222-4222-8222-222222222222')]:
            files = {'manifest.json': (side + ' manifest').encode(), 'scripts/main.js': (side + ' js').encode(),
                     'assets/reclaim.bin': (side.encode() * (512 * 1024))}
            pack_files = {name: hashlib.sha256(data).hexdigest() for name, data in files.items()}
            world = 'Fixture World'
            relative = f'worlds/{world}/{side}_packs/{uid}'
            pack_root = run / 'lock-source-projection' / relative
            candidate_pack = run / 'release-candidate' / f'{side}_packs' / uid
            pack_root.mkdir(parents=True)
            candidate_pack.mkdir(parents=True)
            for name, data in files.items():
                candidate_file = candidate_pack / name
                candidate_file.parent.mkdir(parents=True, exist_ok=True)
                candidate_file.write_bytes(data)
                projection_file = pack_root / name
                projection_file.parent.mkdir(parents=True, exist_ok=True)
                os.link(candidate_file, projection_file)
            digest = hashlib.sha256(b'senluo-pack-tree-v1\0')
            for name in sorted(files):
                encoded = name.encode()
                digest.update(len(encoded).to_bytes(8, 'big'))
                digest.update(encoded)
                digest.update(len(files[name]).to_bytes(8, 'big'))
                digest.update(files[name])
            receipt_packs.append({'uuid': uid, 'side': side, 'version': [1, 2, 3], 'source': source,
                                  'dependencies': [], 'files': pack_files})
            lock_packs.append({'kind': side, 'uuid': uid, 'version': [1, 2, 3], 'path': relative,
                               'sha256': digest.hexdigest(), 'source': source['repository'] + '@' + source['commit']})
            order[side].append(uid)
            projected.extend(pack_root.rglob('*'))
        for side in ('behavior', 'resource'):
            (run / 'lock-source-projection/worlds' / 'Fixture World' / f'world_{side}_packs.json').write_text(
                json.dumps([{'pack_id': uid, 'version': [1, 2, 3]} for uid in order[side]]))
        lock = {'schema': 1, 'digest_format': 'senluo-pack-tree-v1', 'name': 'stable',
                'packs': lock_packs}
        self.write(run / 'family-lock.json', lock)
        raw = {'schema': 1, 'lock_sha256': hashlib.sha256((run / 'family-lock.json').read_bytes()).hexdigest(),
               'packs': receipt_packs, 'order': order}
        receipt_path = run / 'release-candidate/family-receipt.json'
        self.write(receipt_path, raw)
        build = json.loads((run / 'build-evidence.json').read_text())
        build['candidate_receipt_sha256'] = hashlib.sha256(receipt_path.read_bytes()).hexdigest()
        self.write(run / 'build-evidence.json', build)
        self.write(run / 'candidate-result.json', {
            'schema': 1, 'state': 'candidate_built_ci_verified',
            'candidate_receipt_sha256': hashlib.sha256(receipt_path.read_bytes()).hexdigest(),
            'family_lock_sha256': hashlib.sha256((run / 'family-lock.json').read_bytes()).hexdigest()})
        return run / 'lock-source-projection', run / 'release-candidate/behavior_packs/11111111-1111-4111-8111-111111111111/manifest.json'
    def reviewed_projection_plan(self, *guards, targets=None):
        output = self.a
        manifest = self.root / 'reviewed-projection.json'
        self.write(manifest, {'schema': 1, 'outputs': [{'output': str(output),
            'reason': 'Superseded stable lock projection; source-bound build retained',
            'targets': targets or ['release-candidate/behavior_packs', 'release-candidate/resource_packs',
                                   'lock-source-projection']} ]})
        return m.plan(self.root, lease=self.lease, protected=guards, retire_outputs=manifest)
    def test_stable_projection_retirement_frees_last_hardlink_alias(self):
        projection, candidate_file = self.stable_projection()
        old_marker = self.a / m.EXPLICIT_MARKER
        old_marker.write_text(json.dumps({'schema': 1, 'state': 'pruned',
            'targets': ['release-candidate/behavior_packs', 'release-candidate/resource_packs'],
            'retired_scopes': ['release-candidate/behavior_packs', 'release-candidate/resource_packs'],
            'removed': ['release-candidate/behavior_packs/older-reviewed-leaf']}))
        old_marker_bytes = old_marker.read_bytes()
        unknown = projection / 'review-note.txt'
        unknown.write_text('preserve')
        projection_file = projection / 'worlds/Fixture World/behavior_packs/11111111-1111-4111-8111-111111111111/manifest.json'
        self.assertEqual(candidate_file.stat().st_ino, projection_file.stat().st_ino)
        self.assertEqual(candidate_file.stat().st_nlink, 2)
        free_before = shutil.disk_usage(self.root).free
        result = self.execute(self.reviewed_projection_plan())
        self.assertEqual(result['state'], 'completed', result['errors'])
        self.assertGreater(shutil.disk_usage(self.root).free, free_before)
        self.assertFalse(candidate_file.exists())
        self.assertFalse(projection_file.exists())
        self.assertEqual(unknown.read_text(), 'preserve')
        self.assertTrue((self.a / 'family-lock.json').exists())
        self.assertTrue((self.a / 'build-evidence.json').exists())
        self.assertEqual(old_marker.read_bytes(), old_marker_bytes)
        self.assertTrue((self.a / 'lock-source-projection-retirement.json').is_file())
    def test_projection_only_retirement_keeps_existing_retirement_record(self):
        projection, _ = self.stable_projection()
        old_marker = self.a / m.EXPLICIT_MARKER
        old_marker.write_text(json.dumps({'schema': 1, 'state': 'pruned',
            'targets': ['release-candidate/behavior_packs', 'release-candidate/resource_packs'],
            'retired_scopes': ['release-candidate/behavior_packs', 'release-candidate/resource_packs'],
            'removed': ['release-candidate/behavior_packs/older-reviewed-leaf']}))
        old_marker_bytes = old_marker.read_bytes()
        result = self.execute(self.reviewed_projection_plan(targets=['lock-source-projection']))
        self.assertEqual(result['state'], 'completed', result['errors'])
        self.assertEqual(old_marker.read_bytes(), old_marker_bytes)
        self.assertTrue((self.a / 'lock-source-projection-retirement.json').is_file())
        self.assertTrue((self.a / 'release-candidate/behavior_packs/11111111-1111-4111-8111-111111111111/manifest.json').exists())
        self.assertFalse((projection / 'worlds/Fixture World/behavior_packs/11111111-1111-4111-8111-111111111111/manifest.json').exists())
    def test_stable_projection_refuses_current_reference_active_lease_and_unreviewed_file(self):
        projection, _ = self.stable_projection()
        candidate_file = self.a / 'release-candidate/behavior_packs/11111111-1111-4111-8111-111111111111/manifest.json'
        with self.assertRaisesRegex(ValueError, 'Current source/evidence/configuration reference'):
            self.reviewed_projection_plan(candidate_file)
        self.write(self.lease, {'state': 'active'})
        with self.assertRaisesRegex(ValueError, 'Active maintenance lease'):
            self.reviewed_projection_plan()
        self.write(self.lease, {'state': 'completed'})
        (projection / 'worlds/Fixture World/behavior_packs/11111111-1111-4111-8111-111111111111/unreviewed.txt').write_text('extra')
        with self.assertRaisesRegex(ValueError, 'file set differs'):
            self.reviewed_projection_plan()
    def test_stable_projection_refuses_wrong_file_hash_and_git_entry(self):
        projection, _ = self.stable_projection()
        pack = projection / 'worlds/Fixture World/resource_packs/22222222-2222-4222-8222-222222222222'
        (pack / 'scripts/main.js').write_text('changed')
        with self.assertRaisesRegex(ValueError, 'file hash differs'):
            self.reviewed_projection_plan()
        (pack / 'scripts/main.js').write_text('resource js')
        (projection / '.git').mkdir()
        with self.assertRaisesRegex(ValueError, 'Git entry'):
            self.reviewed_projection_plan()
    def test_stable_projection_refuses_selector_order_drift(self):
        projection, _ = self.stable_projection()
        selector = projection / 'worlds/Fixture World/world_behavior_packs.json'
        selector.write_text('[]')
        with self.assertRaisesRegex(ValueError, 'selector differs'):
            self.reviewed_projection_plan()
    def test_explicit_empty_directory_scope_is_bound_and_resumes_after_partial_cleanup(self):
        empty = self.a / 'production-rollback'
        shutil.rmtree(empty)
        for side in ['behavior_packs', 'resource_packs']:
            (empty / side).mkdir(parents=True)
        planned = self.reviewed_plan(['production-snapshot', 'production-rollback'])
        row = self.row(planned, self.a)
        self.assertEqual([target['relative'] for target in row['delete']], ['production-snapshot', 'production-rollback'])
        self.assertEqual(row['delete'][1]['metadata']['selected_files'], [])
        from family_update import cleanup_engine_inputs
        original_unlink = cleanup_engine_inputs.unlink_selected
        def interrupted(metadata, *args):
            if metadata['path'] == str(empty):
                raise RuntimeError('interrupted before empty scope completion')
            return original_unlink(metadata, *args)
        with patch.object(cleanup_engine_inputs, 'unlink_selected', side_effect=interrupted):
            partial = self.execute(planned)
        self.assertEqual(partial['state'], 'partial')
        marker = json.loads((self.a / m.EXPLICIT_MARKER).read_text())
        self.assertEqual(marker['retired_scopes'], ['production-snapshot'])
        self.assertEqual(marker['state'], 'partial')
        # Both scopes now contain only directories. A fresh plan must still
        # bind them and let the original partial marker close without a delete.
        resumed = self.execute(self.plan(retire_outputs=self.root / 'reviewed.json'))
        self.assertEqual(resumed['state'], 'completed', resumed['errors'])
        self.assertEqual(resumed['deleted'], [])
        marker = json.loads((self.a / m.EXPLICIT_MARKER).read_text())
        self.assertEqual(marker['state'], 'pruned')
        self.assertEqual(marker['retired_scopes'], ['production-snapshot', 'production-rollback'])
        self.assertTrue((empty / 'behavior_packs').is_dir())
        self.assertTrue((self.c / 'production-snapshot/db/data').exists())
        closed_marker = (self.a / m.EXPLICIT_MARKER).read_bytes()
        closed = self.plan(retire_outputs=self.root / 'reviewed.json')
        self.assertEqual(self.row(closed, self.a)['state'], 'no_remaining_copies')
        self.assertEqual(self.row(closed, self.a)['delete'], [])
        with patch.object(m, '_retained_integrity', side_effect=AssertionError('no leaf remains to delete')):
            self.assertEqual(self.execute(closed)['state'], 'completed')
        self.assertEqual((self.a / m.EXPLICIT_MARKER).read_bytes(), closed_marker)
    def test_explicit_unselected_scope_preserves_diagnostics_and_closes_with_no_unlinks(self):
        relative = 'exact-engine/worlds/Family QA/db'
        diagnostic = self.a / relative / 'LOG'
        diagnostic.write_text('original diagnostic')
        planned = self.reviewed_plan([relative])
        self.assertEqual(self.row(planned, self.a)['delete'][0]['metadata']['selected_files'], [])
        result = self.execute(planned)
        self.assertEqual(result['state'], 'completed', result['errors'])
        self.assertEqual(result['deleted'], [])
        self.assertEqual(diagnostic.read_text(), 'original diagnostic')
        self.assertEqual((diagnostic.parent / 'data').read_text(), 'qa db')
        self.assertEqual(json.loads((self.a / m.EXPLICIT_MARKER).read_text())['retired_scopes'], [relative])
    def assert_unselected_scope_leaf_race(self, relative, leaf):
        planned = self.reviewed_plan([relative])
        self.assertEqual(self.row(planned, self.a)['delete'][0]['metadata']['selected_files'], [])
        added = self.a / relative / leaf
        calls = 0
        def context():
            nonlocal calls
            calls += 1
            if calls == 2:
                added.write_text('unplanned selected leaf')
            return {'lease': self.lease}
        result = self.execute(planned, context=context)
        self.assertEqual(result['state'], 'partial')
        self.assertIn('Selected generated files changed', result['errors'][0]['error'])
        self.assertEqual(result['deleted'], [])
        self.assertEqual(added.read_text(), 'unplanned selected leaf')
    def test_empty_scope_gaining_selected_leaf_rejects_at_execution_boundary(self):
        self.assert_unselected_scope_leaf_race('production-staged', 'new-copy.bin')
    def test_unselected_scope_gaining_selected_database_leaf_rejects_at_execution_boundary(self):
        self.assert_unselected_scope_leaf_race('exact-engine/worlds/Family QA/db', '000002.ldb')
    def test_latest_missing_snapshot_keeps_every_older_backup(self):
        (self.c / 'production-snapshot/db/data').unlink()
        p = self.plan()
        self.assertFalse(p['rollback_retention_ready'])
        self.assertTrue(self.row(p, self.a)['delete'])
        self.assertFalse(set(m.BACKUPS) & {x['relative'] for x in self.row(p, self.a)['delete']})
        self.execute(p)
        self.assertTrue((self.a / 'production-snapshot/db/data').exists())
    def test_latest_incomplete_proof_still_blocks_backup_retirement(self):
        (self.c / 'poststart-verification.json').unlink()
        p = self.plan()
        self.assertEqual(p['newest_retained'], [str(self.c)])
        self.assertFalse(p['rollback_retention_ready'])
        self.assertFalse(set(m.BACKUPS) & {x['relative'] for x in self.row(p, self.a)['delete']})
    def test_failed_partial_and_metadata_mismatch_preserved(self):
        for file, edit in [('deployment-result.json', lambda d: d.update(state='rolled_back_before_restart')),
                           ('poststart-verification.json', lambda d: d.update(ok=False)),
                           ('saved-world-report.json', lambda d: d.update(candidate_receipt_sha256='other')),
                           ('admission-report.json', lambda d: d.update(reviewed_receipt_sha256='other')),
                           ('production-before/backup-receipt.json', lambda d: d.update(live_status='RUNNING'))]:
            with self.subTest(file=file):
                p = self.a / file
                original = p.read_text()
                self.modify(self.a, file, edit)
                self.assertEqual(self.row(self.plan(), self.a)['delete'], [])
                p.write_text(original)
        (self.a / 'exact-engine/native-report.json').unlink()
        self.assertEqual(self.row(self.plan(), self.a)['delete'], [])
    def test_current_references_preserve_output_but_do_not_hide_latest_horizon(self):
        p = self.plan(protected=[self.c, self.a / 'reviewed-family-receipt.json'])
        self.assertEqual(p['newest_retained'], [str(self.c)])
        self.assertEqual(self.row(p, self.a)['delete'], [])
    def test_source_sibling_does_not_hide_deployment(self):
        protected = self.root / 'source-sibling'
        protected.mkdir()
        self.assertEqual(self.plan(protected=[protected])['newest_retained'], [str(self.c)])
    def test_active_process_and_active_lease_preserve_all(self):
        with patch.object(m, 'assert_idle', side_effect=RuntimeError('active process')):
            self.assertEqual(self.row(self.plan(), self.a)['delete'], [])
        self.write(self.lease, {'state': 'active', 'candidate': str(self.c)})
        self.assertEqual(self.row(self.plan(), self.a)['delete'], [])
    def test_symlink_special_git_and_source_overlap_preserved(self):
        path = self.a / m.COPIES[0] / 'unsafe'
        for mode in ['symlink', 'fifo', 'git']:
            with self.subTest(mode=mode):
                if mode == 'symlink':
                    path.symlink_to(self.root / 'source')
                elif mode == 'fifo':
                    os.mkfifo(path)
                else:
                    path = path.with_name('.git')
                    path.write_text('source checkout')
                self.assertEqual(self.row(self.plan(), self.a)['delete'], [])
                path.unlink()
                path = path.with_name('unsafe')
        self.modify(self.a, 'build-evidence.json', lambda d: d.update(sources={'tavern': {'canonical_path': str(self.a / m.COPIES[0])}}))
        self.assertEqual(self.row(self.plan(), self.a)['delete'], [])
    def test_child_mount_does_not_block_root_but_target_mount_preserved(self):
        historical = self.root / 'historical-mount'
        historical.mkdir()
        with patch.object(m, '_mount_paths', return_value={historical}):
            self.assertTrue(self.row(self.plan(), self.a)['delete'])
        nested = self.a / m.COPIES[0] / 'mounted'
        nested.mkdir()
        with patch.object(m, '_mount_paths', return_value={nested}):
            self.assertEqual(self.row(self.plan(), self.a)['delete'], [])
    def test_plan_metadata_change_refuses_execution_without_marker(self):
        p = self.plan()
        self.modify(self.a, 'poststart-verification.json', lambda d: d.update(receipt_sha256='new'))
        with self.assertRaisesRegex(ValueError, 'plan changed'):
            self.execute(p)
        self.assertFalse((self.a / m.MARKER).exists())
    def test_lease_or_reference_added_after_plan_blocks_before_deletion(self):
        p = self.plan()
        self.write(self.lease, {'state': 'active', 'candidate': str(self.c)})
        with self.assertRaisesRegex(ValueError, 'lease became active'):
            self.execute(p)
        self.assertTrue((self.a / m.COPIES[0]).exists())
        self.write(self.lease, {'state': 'completed'})
        with self.assertRaisesRegex(ValueError, 'plan changed'):
            self.execute(p, context=lambda: {'protected': [self.a / 'reviewed-family-receipt.json']})
    def test_lease_becomes_active_during_cleanup_then_bound_plan_resumes(self):
        p = self.plan()
        calls = 0
        def context():
            nonlocal calls
            calls += 1
            if calls == 3:
                self.write(self.lease, {'state': 'active', 'candidate': str(self.c)})
            return {'lease': self.lease}
        result = self.execute(p, context=context)
        self.assertEqual(result['state'], 'partial')
        self.assertFalse((self.a / m.COPIES[0]).exists())
        self.assertTrue((self.a / m.COPIES[1]).exists())
        self.write(self.lease, {'state': 'completed'})
        resumed = self.execute(self.plan())
        self.assertEqual(resumed['state'], 'completed')
        self.assertEqual(json.loads((self.a / m.MARKER).read_text())['state'], 'pruned')
    def test_partial_rmtree_resume_and_report_binding_preserved(self):
        p = self.plan()
        real = shutil.rmtree
        calls = 0
        def interrupted(path):
            nonlocal calls
            calls += 1
            if calls == 2:
                next(Path(path).rglob('manifest.json')).unlink()
                raise OSError('interrupted after unlink')
            real(path)
        with patch.object(m.shutil, 'rmtree', side_effect=interrupted):
            result = self.execute(p)
        self.assertEqual(result['state'], 'partial')
        resumed = self.execute(self.plan())
        self.assertEqual(resumed['state'], 'completed')
        self.assertFalse((self.a / m.COPIES[1]).exists())
    def test_unknown_marker_and_nonempty_stage_do_not_delete(self):
        self.write(self.a / m.MARKER, {'state': 'partial', 'metadata_binding': {'foreign': True}})
        self.assertEqual(self.row(self.plan(), self.a)['delete'], [])
        (self.a / m.MARKER).unlink()
        (self.a / 'production-staged/foreign').write_text('unknown staged input')
        self.assertEqual(self.row(self.plan(), self.a)['delete'], [])
    def test_complete_file_names_with_truncated_latest_db_refuse_backup_deletion(self):
        (self.c / 'production-snapshot/db/data').write_bytes(b'')
        p = self.plan()
        self.assertTrue(p['rollback_retention_ready']) # plan proves structure only
        result = self.execute(p)
        self.assertEqual(result['state'], 'partial')
        self.assertIn('content differs', result['errors'][0]['error'])
        for rel in m.BACKUPS:
            self.assertTrue((self.a / rel).exists())
    def test_verified_retained_backup_modified_before_next_group_refuses_and_never_rehashes(self):
        older = self.deployment('older', 4)
        self.modify(older, 'deployment-result.json', lambda d: d.update(completed_at='2026-09-30T01:00:00+00:00'))
        p = self.plan()
        real_check = m._retained_integrity
        checks = 0
        def verified(*args):
            nonlocal checks
            checks += 1
            return real_check(*args)
        def context():
            if (self.a / m.MARKER).exists() and json.loads((self.a / m.MARKER).read_text()).get('state') == 'pruned':
                (self.c / 'production-snapshot/db/data').write_text('modified after verification')
            return {'lease': self.lease}
        with patch.object(m, '_retained_integrity', side_effect=verified):
            result = self.execute(p, context=context)
        self.assertEqual(checks, 1)
        self.assertEqual(result['state'], 'partial')
        self.assertIn('changed after content verification', result['errors'][0]['error'])
        self.assertTrue((older / 'production-snapshot/db/data').exists())
    def test_unrelated_parent_report_written_during_cleanup_does_not_change_horizon(self):
        p = self.plan()
        calls = 0
        def context():
            nonlocal calls
            calls += 1
            if calls == 3:
                self.write(self.root / 'unrelated-native-report.json', {'native_job': 'independent'})
            return {'lease': self.lease}
        result = self.execute(p, context=context)
        self.assertEqual(result['state'], 'completed')
        self.assertTrue((self.root / 'unrelated-native-report.json').exists())
        self.assertFalse((self.a / 'production-snapshot').exists())
        self.assertFalse((self.b / 'production-snapshot/db/data').exists())
        self.assertTrue((self.c / 'production-snapshot/db/data').exists())
    def test_new_protected_deployment_header_refuses_next_backup_group(self):
        older = self.deployment('older', 4)
        self.modify(older, 'deployment-result.json', lambda d: d.update(completed_at='2026-09-30T01:00:00+00:00'))
        p = self.plan(protected=[self.b, self.c])
        newest = self.root / 'new-protected-deployment'
        def context():
            if (self.a / m.MARKER).exists() and json.loads((self.a / m.MARKER).read_text()).get('state') == 'pruned':
                if not (newest / 'deployment-result.json').exists():
                    self.write(newest / 'deployment-result.json', {
                        'state': 'deployed_running', 'completed_at': '2026-10-07T01:00:00+00:00'})
            return {'lease': self.lease, 'protected': [self.b, self.c, newest]}
        result = self.execute(p, context=context)
        self.assertEqual(result['state'], 'partial')
        self.assertIn('header set differs', result['errors'][0]['error'])
        self.assertTrue((older / 'production-snapshot/db/data').exists())
        self.assertTrue((newest / 'deployment-result.json').exists())
        self.assertEqual(result['retained_backup_integrity']['hash_boundary_passes'], 1)
    def test_cmdline_reference_without_cwd_or_fd_preserves_output(self):
        proc = self.root / 'fake-proc'
        job = proc / '123456'
        job.mkdir(parents=True)
        (job / 'cmdline').write_bytes(b'python\0--config=' + str(self.a / 'config.json').encode() + b'\0')
        self.assertEqual(self.row(self.plan(proc_root=proc), self.a)['delete'], [])

    def test_newly_idle_output_is_deferred_without_blocking_original_safe_selection(self):
        older = self.deployment('older-active', 4)
        self.modify(older, 'deployment-result.json', lambda d: d.update(completed_at='2026-09-30T01:00:00+00:00'))
        real_idle = m._assert_idle
        def still_active(output, proc_root):
            if output == older:
                raise RuntimeError('active process')
            return real_idle(output, proc_root)
        with patch.object(m, '_assert_idle', side_effect=still_active):
            planned = self.plan()
        self.assertEqual(self.row(planned, older)['state'], 'preserved')
        result = self.execute(planned)
        self.assertEqual(result['state'], 'completed')
        self.assertEqual(result['newly_eligible_deferred'], [str(older)])
        self.assertFalse((self.a / m.COPIES[0]).exists())
        self.assertTrue((older / m.COPIES[0]).is_dir())
        self.assertFalse((older / m.MARKER).exists())
    def test_no_backup_targets_never_hash_retained_contents(self):
        (self.c / 'production-snapshot/db/data').unlink()
        p = self.plan()
        with patch.object(m, '_retained_integrity', side_effect=AssertionError('unnecessary hash')):
            self.assertEqual(self.execute(p)['state'], 'completed')

    def test_root_must_be_explicit_absolute_and_not_symlink(self):
        with self.assertRaises(ValueError):
            m.plan(Path('relative'))
        alias = self.root / 'alias'
        alias.symlink_to(self.root, target_is_directory=True)
        with self.assertRaises(ValueError):
            m.plan(alias)
        with self.assertRaisesRegex(ValueError, 'at least the newest complete rollback'):
            self.plan(retain=0)

if __name__ == '__main__':
    unittest.main()
