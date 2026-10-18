"""Bounded capacity waiting changes no game, lease, cap or admission receipt."""
import contextlib
import copy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from family_update import common as c, memory_budget as budget, native_capacity_wait as m


class NativeCapacityWaitTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory(); self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name)
        self.output = self.root / 'output'; self.output.mkdir()
        self.group = self.root / 'cgroup'; self.group.mkdir()
        self.light, self.native = 512 * budget.MIB, 5 * budget.GIB // 2
        self.config = {'native_capacity_wait_seconds': 120, 'memory_budget': {
            'unit': 'wait-test.service', 'limit_bytes': self.native, 'swap_limit_bytes': 0,
            'reserve_bytes': 2 * budget.GIB, 'phase_limits': {'light': self.light, 'native': self.native}}}
        self.config_path = self.root / 'config.json'; self.config_path.write_text(json.dumps(self.config))
        self.lease = self.root / 'lease.json'
        self.lease_bytes = b'{"state":"completed","owner":"previous","candidate":"/previous"}\n'
        self.lease.write_bytes(self.lease_bytes)
        self.admissions = self.output / 'memory-admissions.json'
        self.admission_bytes = b'{"schema":1,"observations":[{"phase":"update","ok":true}]}\n'
        self.admissions.write_bytes(self.admission_bytes)
        self.clock = 0
        self.available = 3 * budget.GIB
        self.source = {'tavern': {'commit': 'reviewed-fixed-source'}}
        self.after_sleep = lambda: None
        self.write_controls()
        original_read = Path.read_text
        def read(path, *args, **kwargs):
            if str(path) == '/proc/meminfo':
                return f'MemAvailable: {self.available // 1024} kB\n'
            return original_read(path, *args, **kwargs)
        self.stack = contextlib.ExitStack(); self.addCleanup(self.stack.close)
        for name, value in {'CONFIG': self.config, 'CONFIG_PATH': self.config_path, 'R': self.output,
                            'C': self.output / 'release-candidate', 'LEASE': self.lease,
                            'now': lambda: 'fixture-clock', 'source_state': lambda: copy.deepcopy(self.source),
                            'orchestration_hashes': lambda: {'runner': 'reviewed-bytes'},
                            'atomic': lambda p, value: p.write_text(json.dumps(value))}.items():
            self.stack.enter_context(patch.object(c, name, value))
        self.stack.enter_context(patch.object(Path, 'read_text', read))
        self.stack.enter_context(patch.object(m.time, 'monotonic', side_effect=lambda: self.clock))
        self.stack.enter_context(patch.object(m.time, 'sleep', side_effect=self.sleep))
        self.stack.enter_context(patch.object(budget, '_group', return_value=('/system.slice/wait-test.service', self.group)))
        self.runner = self.stack.enter_context(patch.object(c, 'verify_canonical_runner'))
        self.api = self.stack.enter_context(patch.object(c, 'api', side_effect=AssertionError('No API during capacity waiting')))
        self.cap = self.stack.enter_context(patch.object(budget, '_set_limit', side_effect=AssertionError('Never change a cap')))
        self.require = self.stack.enter_context(patch.object(budget, 'require', side_effect=AssertionError('No repeated admission receipts')))

    def sleep(self, seconds):
        self.assertLessEqual(seconds, 60)
        self.clock += seconds
        self.after_sleep()

    def write_controls(self):
        for name, value in {'memory.max': self.light, 'memory.swap.max': 0,
                            'memory.current': 10 * budget.MIB,
                            'memory.events': 'oom 0\noom_kill 0\noom_group_kill 0\n'}.items():
            (self.group / name).write_text(str(value))

    def assert_no_operations(self):
        self.api.assert_not_called(); self.cap.assert_not_called(); self.require.assert_not_called()
        self.assertEqual(self.lease.read_bytes(), self.lease_bytes)
        self.assertEqual(self.admissions.read_bytes(), self.admission_bytes)
        self.assertFalse((self.output / 'production-before').exists())
        self.assertFalse((self.output / 'release-candidate').exists())

    def test_wait_then_fit_uses_no_resident_credit_and_leaves_all_actual_gates(self):
        needed = self.native + 2 * budget.GIB + budget.RESIDENT_ACCOUNTING_PAD
        self.after_sleep = lambda: setattr(self, 'available', needed)
        state = m.wait_if_configured()
        self.assertEqual(self.clock, 60)
        self.assertEqual(state['state'], 'projection_available')
        self.assertEqual(state['required_available_bytes'], needed)
        self.assertEqual(state['self_resident_credit_bytes'], 0)
        self.assertEqual(state['observations'], 2)
        self.assertFalse(state['native_admission']); self.assertFalse(state['receipt'])
        self.runner.assert_called_once_with()
        self.assert_no_operations()

    def test_timeout_is_terminal_without_live_operations_or_automatic_retry(self):
        with self.assertRaisesRegex(RuntimeError, 'timed out'):
            m.wait_if_configured()
        state = json.loads((self.output / m.STATE).read_text())
        self.assertEqual(state['state'], 'timed_out'); self.assertEqual(self.clock, 120)
        with self.assertRaisesRegex(RuntimeError, 'already ran'):
            m.wait_if_configured()
        self.assertEqual(self.clock, 120); self.runner.assert_not_called()
        self.assert_no_operations()

    def test_actual_control_and_oom_drift_reject_before_any_native_action(self):
        for filename, value in [('memory.max', self.native), ('memory.swap.max', 1),
                                ('memory.events', 'oom 0\noom_kill 1\noom_group_kill 0\n')]:
            with self.subTest(filename=filename):
                (self.output / m.STATE).unlink(missing_ok=True); self.clock = 0; self.write_controls()
                self.after_sleep = lambda: (self.group / filename).write_text(str(value))
                with self.assertRaisesRegex(RuntimeError, 'control changed|ceiling|OOM'):
                    m.wait_if_configured()
                self.assertEqual(json.loads((self.output / m.STATE).read_text())['state'], 'rejected')
        self.runner.assert_not_called(); self.assert_no_operations()

    def test_source_configuration_or_lease_drift_fails_closed(self):
        original = self.config_path.read_bytes()
        for changed in ['source', 'config', 'lease']:
            with self.subTest(changed=changed):
                (self.output / m.STATE).unlink(missing_ok=True); self.clock = 0
                self.source = {'tavern': {'commit': 'reviewed-fixed-source'}}
                self.config_path.write_bytes(original); self.lease.write_bytes(self.lease_bytes)
                def drift():
                    if changed == 'source': self.source['tavern']['commit'] = 'different'
                    elif changed == 'config': self.config_path.write_bytes(original + b'\n')
                    else: self.lease.write_bytes(b'{"state":"active"}\n')
                self.after_sleep = drift
                with self.assertRaisesRegex(RuntimeError, 'identity changed'):
                    m.wait_if_configured()
        self.lease.write_bytes(self.lease_bytes)
        (self.output / m.STATE).unlink(missing_ok=True)
        changed_config = copy.deepcopy(self.config); changed_config['native_capacity_wait_seconds'] = 121
        self.config_path.write_text(json.dumps(changed_config))
        with self.assertRaisesRegex(RuntimeError, 'Loaded configuration differs'):
            m.wait_if_configured()
        self.runner.assert_not_called(); self.assert_no_operations()

    def test_invalid_seconds_and_existing_transactions_cannot_create_a_wait(self):
        for value in [None, False, 0, -1, 7201, 1.5, '60']:
            with self.subTest(seconds=value):
                self.config['native_capacity_wait_seconds'] = value
                with self.assertRaisesRegex(ValueError, '1..7200'):
                    m.wait_if_configured()
        self.config['native_capacity_wait_seconds'] = 120
        (self.output / 'release-candidate').mkdir()
        self.assertIsNone(m.wait_if_configured())
        self.assertFalse((self.output / m.STATE).exists())
        (self.output / 'release-candidate').rmdir()
        self.lease.write_bytes(b'{"state":"active","owner":"other","candidate":"/other"}\n')
        with self.assertRaisesRegex(RuntimeError, 'lease is active'):
            m.wait_if_configured()
        self.assertFalse((self.output / m.STATE).exists())
        self.lease.write_bytes(self.lease_bytes)
        self.assert_no_operations()


if __name__ == '__main__':
    unittest.main()
