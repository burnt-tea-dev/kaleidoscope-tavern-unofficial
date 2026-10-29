"""Public-ID contract fixture; no author scripts or private family payloads.

Reviewed official files: Tavern 9317036, Sculk 9317015, DimensionsWine 9317013.
Archive SHA256: 71fd6f635b9cdf7d91b3d0e511ed9601401b1bea62ca88d8dcf84c8b041cfe47,
15b64840f20c0ab7da26c6af4f5108512345a5947f381f202594a7f04137c4dd,
63f455fb6413daecedbd95452031610f3dd51aa1e03c80355b257be5ff38d692.
Only the external host dependency contract is reproduced, not addon assets.
"""
import copy
import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
NAME = 'controller.render.kt_runtime.machine_liquid'
CONTRACT = {'geometry': 'Geometry.default', 'materials': [{'*': 'Material.default'}],
            'textures': ['Texture.default'], 'color': {'r': 1, 'g': 1, 'b': 1, 'a': .85}}
FLUIDS = {'kaleidoscope_sculk': ('sculk_juice',), 'kaleidoscope_dim_wine': (
    'dragon_blood', 'enchanted_berry_juice', 'frostheart_fruit_juice',
    'warped_grape_juice', 'crimson_grape_juice', 'torchberries_juice', 'dreamfruit_juice')}
# These are public identifiers and host aliases, not copied client-entity bodies.
REFERENCES = [{'id': f'{namespace}:liquid_{machine}_{fluid}_visual',
               'geometry': f'geometry.kt_assets_a17.liquid_{machine}',
               'animation': f'animation.kt_assets_a17.liquid_{machine}'}
              for namespace, fluids in FLUIDS.items() for fluid in fluids
              for machine in ('barrel', 'pressing_tub')]


def validate(root=ROOT, controllers=None):
    rp = root / 'runtime/RP'
    if controllers is None:
        controllers = {}
        for path in (rp / 'render_controllers').glob('*.json'):
            for key, value in json.loads(path.read_text()).get('render_controllers', {}).items():
                assert key not in controllers, f'duplicate controller: {key}'
                controllers[key] = value
    assert controllers.get(NAME) == CONTRACT, 'missing or changed external liquid contract'
    geometries = {geo['description']['identifier']
                  for path in (rp / 'models').rglob('*.json')
                  for geo in json.loads(path.read_text()).get('minecraft:geometry', [])}
    animations = {key for path in (rp / 'animations').rglob('*.json')
                  for key in json.loads(path.read_text()).get('animations', {})}
    assert len(REFERENCES) == 16 and len({r['id'] for r in REFERENCES}) == 16
    for row in REFERENCES:
        assert row['geometry'] in geometries, row
        assert row['animation'] in animations, row
    return len(REFERENCES)


class ExternalLiquidContract(unittest.TestCase):
    def test_all_sixteen_external_dependencies(self):
        self.assertEqual(validate(), 16)

    def test_missing_controller_is_not_ignored(self):
        with self.assertRaisesRegex(AssertionError, 'missing or changed'):
            validate(controllers={})

    def test_opaque_static_alias_is_not_equivalent(self):
        opaque = copy.deepcopy(CONTRACT)
        opaque['color']['a'] = 1
        with self.assertRaisesRegex(AssertionError, 'missing or changed'):
            validate(controllers={NAME: opaque})

    def test_wrong_friendly_name_is_rejected(self):
        wrong = copy.deepcopy(CONTRACT)
        wrong['textures'] = ['Texture.water']
        with self.assertRaisesRegex(AssertionError, 'missing or changed'):
            validate(controllers={NAME: wrong})


if __name__ == '__main__':
    unittest.main()
