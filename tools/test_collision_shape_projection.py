#!/usr/bin/env python3
import copy
import json
from pathlib import Path
import unittest
from collision_shape_projection import collision_preimage, immutable_before, TAVERN_PREVIOUS

ROOT = Path(__file__).resolve().parents[1]
NAME = 'runtime/BP/blocks/barrel_part.json'


class CollisionProjectionTest(unittest.TestCase):
    def test_reviewed_barrel_delta_restores_exact_public_predecessor(self):
        self.assertEqual(collision_preimage(ROOT, NAME, (ROOT / NAME).read_bytes()),
                         immutable_before(str(ROOT), TAVERN_PREVIOUS, NAME))

    def test_other_components_or_state_semantics_cannot_hide_inside_shape_delta(self):
        source = json.loads((ROOT / NAME).read_text())
        for field in ('minecraft:loot', 'minecraft:movable'):
            changed = copy.deepcopy(source)
            changed['minecraft:block']['components'][field] = False
            with self.assertRaises(AssertionError):
                collision_preimage(ROOT, NAME, json.dumps(changed).encode())

    def test_shape_direction_or_selection_cannot_be_coordinately_forged(self):
        source = json.loads((ROOT / NAME).read_text())
        for field in ('condition', 'components'):
            changed = copy.deepcopy(source)
            changed['minecraft:block']['permutations'][0][field] = changed['minecraft:block']['permutations'][1][field]
            with self.assertRaises(AssertionError):
                collision_preimage(ROOT, NAME, json.dumps(changed).encode())


if __name__ == '__main__':
    unittest.main()
