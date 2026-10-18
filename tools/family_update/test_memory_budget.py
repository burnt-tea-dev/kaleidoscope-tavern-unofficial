import unittest
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


if __name__ == '__main__':
    unittest.main()
