"""Stopped idle ownership is explicit; no API lifecycle calls in these tests."""
import contextlib
import copy
import hashlib
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from family_update import common as c, deploy_live as deploy, normal_idle_update as m


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, sort_keys=True) + '\n')


class NormalIdleTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory(); self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name)
        self.output = self.root / 'new-update'; self.output.mkdir()
        self.previous = self.root / 'previous-update'; self.previous.mkdir()
        self.bds = self.root / 'bds'; self.bds.mkdir()
        self.world = self.bds / 'world'; self.world.mkdir()
        self.quality = self.root / 'quality'; self.quality.mkdir()
        self.source = self.root / 'source'; self.source.mkdir()
        self.idle = self.root / 'idle'; self.idle.mkdir()
        self.config_path = self.idle / 'config.json'
        self.current = self.root / 'current.json'
        self.lease = self.root / 'lease.json'; self.lock = self.root / 'maintenance.lock'; self.lock.touch()
        self.old_config = self.root / 'previous-config.json'
        self.review_path = self.root / 'idle-review.json'
        self.authorization = self.root / 'AGENTS.md'; self.authorization.write_text('fixture authorization')
        self.clock = '2026-01-01T00:11:00Z'
        self.summary = {'name': 'fixture', 'status': 'STOPPED', 'player_count': 0, 'version': '1.2.3'}
        self.task = {'status': 'success', 'result': {'status': 'success', 'server_name': 'fixture'}}
        self.code = b'"""Tiny owned idle source fixture."""\n'
        for path in [self.idle / 'idle_stop.py', self.source / m.SOURCE]:
            path.parent.mkdir(parents=True, exist_ok=True); path.write_bytes(self.code)
        self.idle_config = {'schema': 1, 'enabled': True, 'server_name': 'fixture', 'wake': 'lobby', 'idle_seconds': 600, 'max_check_gap_seconds': 100, 'family_config': str(self.current), 'state_file': str(self.idle / 'state.json')}
        write(self.config_path, self.idle_config)
        write(self.old_config, {'output_dir': str(self.previous), 'server_name': 'fixture', 'bds_root': str(self.bds), 'world_dir': str(self.world), 'quality_dir': str(self.quality), 'lease_file': str(self.lease), 'lock_file': str(self.lock)})
        self.current.symlink_to(self.old_config)
        self.assembled = self.previous / 'release-candidate/family-receipt.json'; write(self.assembled, {'fixture': 'full reviewed candidate'})
        self.receipt = self.previous / 'reviewed-family-receipt.json'
        write(self.receipt, {'assembled_receipt': {'path': str(self.assembled), 'sha256': c.sha(self.assembled)}})
        post = self.previous / 'poststart-verification.json'
        write(post, {'ok': True, 'errors': [], 'summary': {**self.summary, 'status': 'RUNNING'}, 'receipt_sha256': c.sha(self.receipt)})
        write(self.previous / 'deployment-result.json', {'state': 'deployed_running', 'receipt_sha256': c.sha(self.receipt), 'assembled_receipt_sha256': c.sha(self.assembled), 'poststart_report': str(post), 'completed_at': '2026-01-01T00:00:00Z'})
        self.old_lease = {'state': 'completed', 'owner': 'Canonical family update ' + hashlib.sha256(str(self.previous).encode()).hexdigest()[:12], 'candidate': str(self.previous), 'receipt': str(self.receipt), 'candidate_receipt_sha256': c.sha(self.assembled)}
        write(self.lease, self.old_lease)
        write(self.quality / 'senluo-policy.json', {'approved_receipt': str(self.receipt), 'installed': {'receipt': str(self.receipt), 'receipt_sha256': c.sha(self.receipt)}})
        (self.bds / 'server_output.txt').write_text('Server stop requested.\nStopping server...\nQuit correctly\n')
        self.state = {'status': 'sleeping', 'server_status': 'STOPPED', 'checked_at_utc': self.clock, 'log': {'valid': True, 'connections': [], 'process': '123:456', 'file': [1, 2], 'offset': 100}, 'fresh_player_count': 0, 'empty_seconds': 604, 'stop_task': 'owned-stop-task', 'last_sleep': {'at_utc': '2026-01-01T00:10:00Z', 'process': '123:456', 'task': 'owned-stop-task', 'empty_seconds': 604}}
        write(self.idle / 'state.json', self.state)
        self.review = {'schema': 1, 'kind': 'normal_idle_update', 'profile': m.PROFILE, 'server_name': 'fixture', 'idle_config': {'path': str(self.config_path), 'sha256': c.sha(self.config_path)}, 'previous_config': {'path': str(self.old_config), 'sha256': c.sha(self.old_config)}, 'previous_output': str(self.previous), 'previous_lease_sha256': c.sha(self.lease), 'policy_sha256': c.sha(self.quality / 'senluo-policy.json'), 'receipt_sha256': c.sha(self.receipt), 'server_log_sha256': c.sha(self.bds / 'server_output.txt'), 'sleep': m.normalized_sleep(self.state)}
        write(self.review_path, self.review)
        self.config = {'normal_idle_update': str(self.review_path)}
        self.stack = contextlib.ExitStack(); self.addCleanup(self.stack.close)
        for name, value in {'CONFIG': self.config, 'R': self.output, 'B': self.bds, 'W': self.world, 'Q': self.quality, 'EXTENSION': self.source, 'LEASE': self.lease, 'LOCK': self.lock, 'SERVER': 'fixture', 'OWNER': 'fixture-new-owner', 'atomic': write, 'now': lambda: self.clock, 'summary': lambda: copy.deepcopy(self.summary)}.items():
            self.stack.enter_context(patch.object(c, name, value))
        self.stack.enter_context(patch.object(m, 'IDLE_CONFIG', self.config_path))
        self.stack.enter_context(patch.object(m, 'CURRENT_CONFIG', self.current))
        self.stack.enter_context(patch.object(m, 'SOURCE_SHA256', hashlib.sha256(self.code).hexdigest()))
        self.stack.enter_context(patch.object(m, 'ROOT_UID', os.getuid()))
        self.blob = self.stack.enter_context(patch.object(c.subprocess, 'check_output', return_value=self.code))
        self.api = self.stack.enter_context(patch.object(c, 'api', side_effect=lambda *a: copy.deepcopy(self.task)))
        self.processes = self.stack.enter_context(patch.object(m, '_processes', return_value=[]))
        self.stack.enter_context(patch.object(m, '_INITIAL', None))

    def lease_handoff(self, receipt=None):
        write(self.output / 'previous-maintenance.json', self.old_lease)
        write(self.lease, {'state': 'active', 'owner': c.OWNER, 'candidate': str(self.output)})

    def test_completed_fresh_deployment_hands_off_its_selected_world(self):
        config=c.read(self.old_config);config['fresh_world']={'level_name':'new-world'}
        write(self.old_config,config);self.review['previous_config']['sha256']=c.sha(self.old_config);write(self.review_path,self.review)
        target=self.bds/'worlds/new-world'
        binding={'server':'fixture','bds_root':str(self.bds),'world_dir':str(target),'level_name':'new-world'}
        for name in ['deployment-result.json','poststart-verification.json']:
            path=self.previous/name;document=c.read(path);document['active_world_binding']=binding
            if name=='deployment-result.json':document['fresh_world']=str(target)
            write(path,document)
        with patch.object(c,'W',target):
            m.load_review()
            path=self.previous/'poststart-verification.json';document=c.read(path)
            document['active_world_binding']['world_dir']=str(self.world);write(path,document)
            with self.assertRaises(AssertionError):m.load_review()
        with self.assertRaises(AssertionError):m.load_review()

    def test_terminal_http_stop_is_bound_to_the_original_operation_without_a_task(self):
        self.state.pop('stop_task')
        self.state['last_sleep'].pop('task')
        self.state['last_sleep']['operation_id']='a'*32
        self.state['stop_operation']={'id':'a'*32,'source':'bsm_http_terminal','method':'POST','action':'stop','server_name':'fixture','process':'123:456','status':'success','outcome':'stopped','started_at_utc':'2026-01-01T00:09:55Z','completed_at_utc':'2026-01-01T00:09:59Z'}
        self.review['sleep']=m.normalized_sleep(self.state)
        write(self.review_path,self.review);write(self.idle/'state.json',self.state)
        m.validate_initial_status(self.summary)
        self.api.assert_not_called()
        for field,value in [('outcome','already_stopped'),('status','unknown'),('process','another-process'),('completed_at_utc','2026-01-01T00:10:01Z')]:
            with self.subTest(field=field):
                changed=copy.deepcopy(self.review);changed['sleep']['stop_operation'][field]=value;write(self.review_path,changed)
                with self.assertRaises(AssertionError):m.load_review()

    def test_exact_idle_handoff_survives_timer_timestamp_and_our_maintenance_lock(self):
        initial = m.validate_initial_status(self.summary)
        self.assertFalse(initial['restart_original_after_failure'])
        self.lease_handoff()
        self.state['status'] = 'maintenance_lock_busy'; self.state['checked_at_utc'] = '2026-01-01T00:10:59Z'
        write(self.idle / 'state.json', self.state)
        m.record_initial_status()
        self.assertEqual(c.read(self.output / 'deployment-initial-state.json'), initial)
        self.assertEqual(self.api.call_args.args, ('/api/tasks/status/owned-stop-task',))

    def test_lost_sleep_label_after_lock_contention_preserves_exact_handoff(self):
        self.state['status'] = 'maintenance_lock_busy'
        write(self.idle / 'state.json', self.state)
        initial = m.validate_initial_status(self.summary)
        self.lease_handoff()
        self.state['status'] = 'server_not_running'
        self.state['checked_at_utc'] = '2026-01-01T00:10:59Z'
        write(self.idle / 'state.json', self.state)
        m.record_initial_status()
        self.assertEqual(c.read(self.output / 'deployment-initial-state.json'), initial)
        self.assertEqual(self.api.call_args.args, ('/api/tasks/status/owned-stop-task',))

    def test_lost_sleep_label_cannot_replace_reviewed_stop_provenance(self):
        original = {**copy.deepcopy(self.state), 'status': 'server_not_running'}
        for field in ['stop_task', 'last_sleep', 'log']:
            changed = copy.deepcopy(original)
            if field == 'stop_task': changed[field] = 'another-stop'
            elif field == 'last_sleep': changed[field]['task'] = 'another-stop'
            else: changed[field]['offset'] += 1
            write(self.idle / 'state.json', changed)
            with self.subTest(field=field), self.assertRaisesRegex(AssertionError, 'identity changed'):
                m.verify_handoff(self.summary)
        write(self.idle / 'state.json', original)
        for path in [self.bds / 'server_output.txt', self.idle / 'idle_stop.py', self.source / m.SOURCE]:
            raw = path.read_bytes()
            try:
                path.write_bytes(raw + b' ')
                with self.subTest(path=path), self.assertRaises(AssertionError):
                    m.verify_handoff(self.summary)
            finally:
                path.write_bytes(raw)

    def test_unknown_inhibited_and_stale_stops_reject(self):
        for status in ['inhibited', 'occupied_or_connecting', 'unknown']:
            write(self.idle / 'state.json', {**self.state, 'status': status})
            with self.subTest(status=status), self.assertRaisesRegex(AssertionError, 'normal idle owner'):
                m.verify_handoff(self.summary)
        for status in ['sleeping', 'server_not_running']:
            write(self.idle / 'state.json', {**self.state, 'status': status, 'checked_at_utc': '2026-01-01T00:08:00Z'})
            with self.subTest(status=status), self.assertRaisesRegex(AssertionError, 'stale'):
                m.verify_handoff(self.summary)

    def test_unconfirmed_task_running_server_or_real_process_rejects(self):
        self.task['status'] = 'error'
        with self.assertRaisesRegex(AssertionError, 'task'): m.verify_handoff(self.summary)
        self.task['status'] = 'success'; self.task['result']['server_name'] = 'foreign'
        with self.assertRaisesRegex(AssertionError, 'task'): m.verify_handoff(self.summary)
        self.task['result']['server_name'] = 'fixture'; self.processes.return_value = ['123']
        with self.assertRaisesRegex(AssertionError, 'BDS process'): m.verify_handoff(self.summary)
        with self.assertRaisesRegex(AssertionError, 'stopped empty'): m.verify_handoff({**self.summary, 'status': 'RUNNING'})

    def test_changed_sleep_identity_and_post_acquisition_owner_reject(self):
        m.validate_initial_status(self.summary); self.lease_handoff()
        self.state['last_sleep']['task'] = 'another-stop'
        write(self.idle / 'state.json', self.state)
        with self.assertRaisesRegex(AssertionError, 'identity changed'): m.record_initial_status()
        self.assertFalse((self.output / 'deployment-initial-state.json').exists())

    def test_changed_log_policy_previous_lease_and_selector_reject(self):
        for path in [self.bds / 'server_output.txt', self.quality / 'senluo-policy.json', self.lease]:
            raw = path.read_bytes(); path.write_bytes(raw + b' ')
            with self.subTest(path=path), self.assertRaises(AssertionError): m.verify_handoff(self.summary)
            path.write_bytes(raw)
        self.current.unlink(); self.current.symlink_to(self.review_path)
        with self.assertRaisesRegex(AssertionError, 'selector'): m.verify_handoff(self.summary)

    def test_foreign_config_source_symlink_or_uncommitted_idle_source_reject(self):
        self.idle_config['server_name'] = 'foreign'; write(self.config_path, self.idle_config)
        self.review['idle_config']['sha256'] = c.sha(self.config_path); write(self.review_path, self.review)
        with self.assertRaises(AssertionError): m.load_review()
        self.idle_config['server_name'] = 'fixture'; write(self.config_path, self.idle_config)
        self.review['idle_config']['sha256'] = c.sha(self.config_path); write(self.review_path, self.review)
        self.blob.return_value = b'foreign committed source'
        with self.assertRaisesRegex(AssertionError, 'committed'): m.load_review()
        self.blob.return_value = self.code
        source = self.idle / 'idle_stop.py'; source.unlink(); source.symlink_to(self.source / m.SOURCE)
        with self.assertRaisesRegex(AssertionError, 'symlink'): m.load_review()

    def test_missing_or_failed_prior_deployment_and_borrowed_recovery_reject(self):
        result = c.read(self.previous / 'deployment-result.json'); result['state'] = 'needs_operator_recovery'
        write(self.previous / 'deployment-result.json', result)
        with self.assertRaises(AssertionError): m.load_review()
        for key in ['managed_drift_recovery', 'preinstall_recovery_output']:
            with patch.dict(c.CONFIG, {key: '/not-an-idle-exception'}), self.assertRaisesRegex(AssertionError, 'cannot borrow'):
                m.enabled()

    def test_build_refs_remain_stable_after_candidate_policy_state_and_lease_change(self):
        before = m.input_refs()
        self.lease_handoff(); write(self.quality / 'senluo-policy.json', {'new': 'candidate'})
        write(self.idle / 'state.json', {'status': 'maintenance_or_unresolved_lease'})
        (self.bds / 'server_output.txt').write_text('New candidate started')
        self.summary['status'] = 'RUNNING'
        self.api.reset_mock()
        self.assertEqual(m.input_refs(), before); self.api.assert_not_called()
        result = c.read(self.previous / 'poststart-verification.json'); result['ok'] = False
        write(self.previous / 'poststart-verification.json', result)
        with self.assertRaises(AssertionError): m.input_refs()

    def test_real_deploy_flow_does_not_stop_already_stopped_runtime_and_failure_cannot_start_it(self):
        m.validate_initial_status(self.summary)
        with contextlib.ExitStack() as stack:
            for name in ['R', 'B', 'W', 'Q', 'EXTENSION', 'LEASE', 'LOCK', 'SERVER', 'OWNER', 'CONFIG', 'summary', 'atomic']:
                stack.enter_context(patch.object(deploy, name, getattr(c, name)))
            stack.enter_context(patch.object(deploy, 'AUTHORIZATION', self.authorization))
            stack.enter_context(patch.object(deploy, 'preflight', return_value=({}, {})))
            stack.enter_context(patch.object(deploy, 'acquire_lease', side_effect=self.lease_handoff))
            stack.enter_context(patch.object(deploy, 'verify_predeploy', return_value={}))
            stack.enter_context(patch('family_update.workflow.same_runtime', return_value=False))
            stack.enter_context(patch('family_update.memory_budget.require', side_effect=RuntimeError('injected native admission refusal')))
            action = stack.enter_context(patch.object(deploy, 'action'))
            restore = stack.enter_context(patch.object(deploy, 'restore_packs'))
            with self.assertRaisesRegex(RuntimeError, 'native admission'): deploy.main(['--execute'])
            action.assert_not_called(); restore.assert_not_called()
            self.assertEqual(c.read(self.lease)['state'], 'active')
            self.assertFalse((self.output / 'production-snapshot').exists())
            self.assertEqual(c.read(self.output / 'deployment-recovery.json')['state'], 'needs_operator_recovery')


class NormalIdleFailureTests(unittest.TestCase):
    def test_partial_install_keeps_exact_move_record_and_running_candidate_only_stops(self):
        from family_update.test_recovery import RecoveryTests
        case = RecoveryTests(); case.setUp()
        try:
            with patch.object(deploy, 'CONFIG', {'normal_idle_update': '/reviewed/idle.json'}):
                retired = [(Path('/rollback/old'), Path('/world/old'))]; installed = [Path('/world/new')]
                with self.assertRaises(deploy.RecoveryRequired): deploy.retain_failed_installation(case.original, retired, installed, OSError('injected partial move'))
                saved = [value for path, value in case.reports if path.endswith('/rollback-map.json')][-1]
                self.assertEqual(saved['retired'], [['/rollback/old', '/world/old']]); self.assertEqual(saved['installed'], ['/world/new'])
                case.status = 'RUNNING'
                self.assertFalse(deploy.recover_after_failure(case.original, True, retired, installed))
                self.assertEqual(case.actions, ['stop']); case.restore.assert_not_called()
                self.assertEqual(case.lease['state'], 'active')
        finally:
            case.doCleanups()


if __name__ == '__main__':
    unittest.main(verbosity=2)
