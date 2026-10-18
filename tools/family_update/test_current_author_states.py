"""The current identity migration must never repeat the prior state conversion."""
import copy
import json
from pathlib import Path
import sys
import unittest

import nbtlib

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from author_state_migration import validate_profile, convert_block


class CurrentAuthorStateTests(unittest.TestCase):
    def setUp(self):
        path = Path(__file__).resolve().parents[2] / 'family/identity-migrations/stable-author-20261018.json'
        self.profile = json.loads(path.read_text())['block_states']

    def node(self, rule):
        states = {}
        for key, domain in rule['before_states'].items():
            value = domain[-1]
            tag = nbtlib.Byte if type(value) is bool else nbtlib.Int if type(value) is int else nbtlib.String
            states[key] = tag(value)
        states['minecraft:cardinal_direction'] = nbtlib.String('west')
        return nbtlib.Compound({'name': nbtlib.String(rule['identifier']),
                               'states': nbtlib.Compound(states),
                               'version': nbtlib.Int(18168865)})

    def test_current_palettes_keep_all_values_and_nbt_types(self):
        rules = validate_profile(self.profile)
        for rule in rules.values():
            with self.subTest(block=rule['identifier']):
                node = self.node(rule)
                before = copy.deepcopy(node)
                self.assertEqual(convert_block(node, rules), 0)
                self.assertEqual(node, before)
                self.assertEqual({k: type(v) for k, v in node['states'].items()},
                                 {k: type(v) for k, v in before['states'].items()})

    def test_previous_conversion_cannot_be_relabelled_current(self):
        for mutation in ('conversion', 'domain'):
            profile = copy.deepcopy(self.profile)
            if mutation == 'conversion':
                profile['blocks'][0]['conversion'] = 'chair_carpet'
            else:
                profile['blocks'][0]['after_states']['unreviewed'] = [0, 1]
            with self.subTest(mutation=mutation), self.assertRaises(ValueError):
                validate_profile(profile)

    def test_invalid_persisted_current_state_fails_before_mutation(self):
        rules = validate_profile(self.profile)
        rule = next(iter(rules.values()))
        node = self.node(rule)
        key = next(iter(rule['before_states']))
        node['states'][key] = nbtlib.String('invalid-author-value')
        before = copy.deepcopy(node)
        with self.assertRaises(ValueError):
            convert_block(node, rules)
        self.assertEqual(node, before)


if __name__ == '__main__':
    unittest.main()
