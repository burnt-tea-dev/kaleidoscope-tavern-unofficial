import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import Mock, patch
from family_update import memory_budget as m
from family_update.memory_budget import assess, GIB


class MemoryBudgetTests(unittest.TestCase):
    def setUp(self):
        self.config = {'unit': 'family-test.service', 'limit_bytes': 2 * GIB,
                       'swap_limit_bytes': 0, 'reserve_bytes': 2 * GIB}

    def check(self, available, current=0, maximum=str(2 * GIB), swap='0', membership='/system.slice/family-test.service'):
        return assess(self.config, 'MemAvailable: ' + str(available // 1024) + ' kB\n', membership, current, maximum, swap)

    def test_real_headroom_must_cover_whole_remaining_budget_and_margin(self):
        self.assertFalse(self.check(3 * GIB)['ok'])
        self.assertTrue(self.check(4 * GIB)['ok'])
        self.assertTrue(self.check(3 * GIB, current=GIB)['ok'])

    def test_unbounded_or_different_actual_limits_cannot_borrow_approval(self):
        for maximum, swap in [('max', '0'), (str(2 * GIB), 'max'), (str(GIB), '0')]:
            with self.assertRaises(ValueError):
                self.check(8 * GIB, maximum=maximum, swap=swap)

    def test_running_in_parent_manager_or_unrelated_unit_is_rejected(self):
        for membership in ['/system.slice/manager.service', '/family-test.service/child.service']:
            with self.assertRaises(ValueError):
                self.check(8 * GIB, membership=membership)

    def test_missing_observation_budget_or_margin_fails_closed(self):
        with self.assertRaises(ValueError):
            assess(self.config, 'MemFree: 99999999 kB', '/family-test.service', 0, str(2 * GIB), '0')
        for config in [None, {**self.config, 'reserve_bytes': GIB}]:
            with self.assertRaises(ValueError):
                assess(config, 'MemAvailable: 99999999 kB', '/family-test.service', 0, str(2 * GIB), '0')


class PhasedMemoryBudgetTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.group = self.root / 'cgroup'
        self.group.mkdir()
        self.light, self.native = 512 * m.MIB, 5 * GIB // 2
        self.config = {'unit': 'phase-test.service', 'limit_bytes': self.native, 'swap_limit_bytes': 0,
                       'reserve_bytes': 2 * GIB, 'phase_limits': {'light': self.light, 'native': self.native}}
        self.member = '/system.slice/phase-test.service'
        self.available = 6 * GIB
        self.write('memory.max', self.light)
        self.write('memory.swap.max', 0)
        self.usage(10 * m.MIB, 10 * m.MIB)
        self.write('memory.events', 'oom 0\noom_kill 0\noom_group_kill 0\n')
        original_read = Path.read_text
        def read(path, *args, **kwargs):
            return 'MemAvailable: ' + str(self.available // 1024) + ' kB\n' if str(path) == '/proc/meminfo' else original_read(path, *args, **kwargs)
        for patcher in [patch.object(Path, 'read_text', read), patch.object(m, '_group', return_value=(self.member, self.group)),
                        patch.object(m.c, 'CONFIG', {'memory_budget': self.config}), patch.object(m.c, 'R', self.root / 'evidence'),
                        patch.object(m.c, 'SERVER', 'synthetic'), patch.object(m.c, 'now', return_value='fixture-clock'),
                        patch.object(m.c, 'atomic', side_effect=lambda path, value: Path(path).write_text(json.dumps(value)))]:
            patcher.start(); self.addCleanup(patcher.stop)
        self.lease = patch.object(m.c, 'assert_lease').start()
        self.addCleanup(patch.stopall)
        self.server = patch.object(m.c, 'summary', return_value={'name': 'synthetic', 'status': 'STOPPED', 'player_count': 0}).start()
        self.set_cap = patch.object(m, '_set_limit', side_effect=lambda config, value: self.write('memory.max', value)).start()

    def write(self, name, value):
        (self.group / name).write_text(str(value))

    def usage(self, current, anon, file=0):
        self.write('memory.current', current)
        self.write('memory.stat', f'anon {anon}\nkernel {m.MIB}\nfile {file}\nshmem 0\nunevictable 0\nslab_reclaimable 0\n')

    def test_known_phase_table_and_single_budget_backward_compatibility(self):
        for phase in m.LIGHT_PHASES:
            self.assertEqual(m.phase_budget(self.config, phase)[0]['limit_bytes'], self.light)
        for phase in m.NATIVE_PHASES:
            self.assertEqual(m.phase_budget(self.config, phase)[0]['limit_bytes'], self.native)
        with self.assertRaisesRegex(ValueError, 'Unknown'):
            m.phase_budget(self.config, 'caller-chosen-phase')
        legacy = {k: v for k, v in self.config.items() if k != 'phase_limits'}
        self.assertEqual(m.phase_budget(legacy, 'historical-unrestricted-label'), (legacy, None))
        with self.assertRaises(ValueError):
            m.phase_budget({**self.config, 'phase_limits': {'light': self.light}}, 'update')
        with self.assertRaises(ValueError):
            m.phase_budget({**self.config, 'swap_limit_bytes': m.MIB}, 'update')

    def test_filecache_current_cannot_credit_host_margin(self):
        record = m.assess_phase(self.config, 'update', f'MemAvailable: {(2 * GIB + self.light - 1024) // 1024} kB',
                                self.member, GIB, str(self.native), '0')
        self.assertFalse(record['ok'])
        self.assertEqual(record['required_available_bytes'], 2 * GIB + self.light)
        self.assertEqual(record['current_headroom_credit_bytes'], 0)
        for maximum, swap, member in [('max', '0', self.member), (str(GIB), '0', self.member),
                                      (str(self.light), 'max', self.member), (str(self.light), '0', '/other.service')]:
            with self.assertRaises(ValueError):
                m.assess_phase(self.config, 'update', 'MemAvailable: 99999999 kB', member, 0, maximum, swap)

    def test_light_phase_already_bounded_does_not_touch_systemd_or_server(self):
        record = m.require('update')
        self.assertTrue(record['ok'])
        self.set_cap.assert_not_called(); self.lease.assert_not_called(); self.server.assert_not_called()

    def test_native_raise_requires_owned_stopped_server_and_exact_readback(self):
        record = m.require('saved-world')
        self.assertTrue(record['limit_transition_verified'])
        self.assertEqual(record['limit_transition'], {'from_bytes': self.light, 'to_bytes': self.native})
        self.assertEqual(int((self.group / 'memory.max').read_text()), self.native)
        self.assertEqual(self.lease.call_count, 2)
        self.assertEqual(record['required_available_bytes'], 2 * GIB + self.native)

    def test_running_populated_foreign_server_or_lost_lease_cannot_raise(self):
        for value in [{'name': 'synthetic', 'status': 'RUNNING', 'player_count': 0},
                      {'name': 'synthetic', 'status': 'STOPPED', 'player_count': 1},
                      {'name': 'foreign', 'status': 'STOPPED', 'player_count': 0}]:
            self.server.return_value = value
            with self.assertRaisesRegex(ValueError, 'owned, stopped and empty'):
                m.require('saved-world')
        self.lease.side_effect = AssertionError('lost owner')
        with self.assertRaisesRegex(AssertionError, 'lost owner'):
            m.require('saved-world')
        self.set_cap.assert_not_called()

    def test_insufficient_host_memory_is_recorded_before_any_cap_change(self):
        self.available = 2 * GIB + self.light - 1024
        with self.assertRaisesRegex(RuntimeError, 'insufficient memory'):
            m.require('update')
        history = json.loads((m.c.R / 'memory-admissions.json').read_text())
        self.assertFalse(history['observations'][-1]['ok'])
        self.set_cap.assert_not_called()

    def test_realized_filecache_reclaim_precedes_low_cap(self):
        self.write('memory.max', self.native)
        self.usage(700 * m.MIB, 100 * m.MIB, 600 * m.MIB)
        def reclaim(group, amount, timeout):
            self.assertEqual(int((group / 'memory.max').read_text()), self.native)
            self.assertLessEqual(amount, 256 * m.MIB)
            self.assertLessEqual(timeout, 0.35)
            self.usage(int((group / 'memory.current').read_text()) - amount, 100 * m.MIB, 300 * m.MIB)
        with patch.object(m, '_reclaim', side_effect=reclaim) as called:
            result = m.require('verify-live')
        self.assertTrue(result['ok']); called.assert_called()
        self.assertLessEqual(result['shrink']['current_bytes'], self.light - m.SHRINK_HEADROOM)
        self.set_cap.assert_called_once_with(self.config, self.light)

    def test_unreclaimable_usage_or_stuck_cache_never_lower_limit(self):
        self.write('memory.max', self.native)
        self.usage(700 * m.MIB, 700 * m.MIB)
        with patch.object(m, '_reclaim') as reclaim:
            with self.assertRaisesRegex(RuntimeError, 'cannot safely fit'):
                m.require('verify-live')
            reclaim.assert_not_called()
        self.usage(700 * m.MIB, 100 * m.MIB, 600 * m.MIB)
        with patch.object(m, '_reclaim') as reclaim:
            with self.assertRaisesRegex(RuntimeError, 'cannot safely fit'):
                m.require('verify-live')
            self.assertEqual(reclaim.call_count, m.RECLAIM_ATTEMPTS)
        self.set_cap.assert_not_called()

    def test_reclaim_partial_result_and_timeout_cannot_authorize_unrealized_shrink(self):
        with patch.object(m, '_bounded_command', return_value=75):
            m._reclaim(self.group, m.MIB, 0.1)  # EAGAIN means reobserve, never pretend a byte count.
        self.write('memory.max', self.native)
        self.usage(700 * m.MIB, 100 * m.MIB, 600 * m.MIB)
        with patch.object(m, '_reclaim', side_effect=RuntimeError('helper timed out')):
            with self.assertRaisesRegex(RuntimeError, 'timed out'):
                m.require('verify-live')
        self.set_cap.assert_not_called()
        child = Mock(); child.wait.side_effect = subprocess.TimeoutExpired('worker', 0.1)
        with patch.object(m.subprocess, 'Popen', return_value=child):
            with self.assertRaisesRegex(RuntimeError, 'timed out'):
                m._bounded_command(['synthetic'], 0.1)
        child.kill.assert_called_once()

    def test_memory_regrowth_after_reclaim_cannot_trigger_dangerous_lowering(self):
        self.write('memory.max', self.native)
        def regrown(group, target):
            self.usage(700 * m.MIB, 100 * m.MIB, 600 * m.MIB)
            return {'current_bytes': target - m.SHRINK_HEADROOM}
        with patch.object(m, '_fit_before_shrink', side_effect=regrown):
            with self.assertRaisesRegex(RuntimeError, 'regrew'):
                m.require('verify-live')
        self.set_cap.assert_not_called()

    def test_wrong_readback_membership_and_prior_oom_are_rejected(self):
        self.set_cap.side_effect = None
        with self.assertRaisesRegex(ValueError, 'readback differs'):
            m.require('saved-world')
        self.set_cap.side_effect = lambda config, value: self.write('memory.max', value)
        with patch.object(m, '_group', side_effect=[(self.member, self.group), ('/foreign.service', self.group)]):
            with self.assertRaisesRegex(ValueError, 'cgroup changed'):
                m.require('saved-world')
        self.write('memory.events', 'oom 1\noom_kill 1\noom_group_kill 0\n')
        self.set_cap.reset_mock()
        with self.assertRaisesRegex(RuntimeError, 'already recorded an OOM'):
            m.require('update')
        self.set_cap.assert_not_called()

    def test_falling_host_headroom_rechecks_before_changing_cap(self):
        original_assess = m._assess_current
        calls = []
        def assess(*args):
            result = original_assess(*args)
            calls.append(result)
            if len(calls) == 2:
                result['ok'] = False
            return result
        with patch.object(m, '_assess_current', side_effect=assess):
            with self.assertRaisesRegex(RuntimeError, 'insufficient memory'):
                m.require('saved-world')
        self.set_cap.assert_not_called()


if __name__ == '__main__':
    unittest.main()
