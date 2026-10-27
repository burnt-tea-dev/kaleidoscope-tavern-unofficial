"""Optional fresh-world inputs never change the reviewed producer profile."""
import copy
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from family_update import current_author_validation as m


class FreshWorldExclusions(unittest.TestCase):
    def setUp(self):
        self.profile = copy.deepcopy(m.CATALOG[m.CURATED_KEY]['selection']['value'])
        self.original = copy.deepcopy(self.profile)
        self.config = {'fresh_world': {'level_name': 'New'}, 'extension_stable_profile': m.CURATED}
        self.enterContext(patch.object(m.c, 'CONFIG', self.config))
        self.enterContext(patch.object(m, 'current_selection', return_value=self.profile))
        self.groups = ['Magical Furniture Add-On', 'Structures Add-On / Structures & Stuff']

    def test_default_preserves_all_reviewed_inputs(self):
        self.assertEqual(m._curated_retained_rows(), self.profile['retained_inputs'])

    def test_two_optional_pairs_are_removed_without_changing_other_rows(self):
        self.config['fresh_world_excluded_groups'] = self.groups
        rows = m._curated_retained_rows()
        self.assertEqual(len(rows), len(self.profile['retained_inputs']) - 4)
        self.assertTrue(all(row['group'] not in self.groups for row in rows))
        self.assertTrue(all(row in self.profile['retained_inputs'] for row in rows))
        self.assertEqual(self.profile, self.original)

    def test_unknown_duplicate_single_side_and_adapted_groups_reject(self):
        for groups in [['unknown'], [self.groups[0]] * 2, ['Fishing'], ['Java Saturation'], ['Wuthering Manor']]:
            with self.subTest(groups=groups), self.assertRaises(AssertionError):
                self.config['fresh_world_excluded_groups'] = groups
                m._curated_retained_rows()

    def test_receipt_cannot_reintroduce_an_excluded_pair(self):
        self.config['fresh_world_excluded_groups'] = self.groups
        rows = m._curated_retained_rows()
        binding = m.CATALOG[m.CURATED_KEY]['selection']
        selection = {'schema': 1, 'kind': 'curated_input_selection',
                     'profile': {key: binding[key] for key in ['path', 'sha256']},
                     'excluded_groups': self.groups, 'packs': {row['uuid']: {} for row in rows},
                     'native_loading': False, 'client': False, 'production_ready': False}
        receipt = {'packs': [{'uuid': row['uuid'], 'source': {'owner': 'preserved'}}
                             for row in self.profile['retained_inputs']]}
        with self.assertRaisesRegex(AssertionError, 'unselected retained input'):
            m.verify_curated_inputs(receipt, selection)


if __name__ == '__main__':
    unittest.main()
