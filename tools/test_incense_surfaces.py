"""Bounded mutation tests for current incense geometry, alpha, and consumers."""
import copy
import json
from pathlib import Path
import shutil
import tempfile
import unittest
from unittest.mock import patch

from PIL import Image
import check_incense_surfaces as contract


class IncenseSurfaces(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        paths = set(contract.runtime_sources()) | {
            'data/baseline-reconciliation.json', 'data/launch-repair-reference.json',
            'runtime/RP/textures/terrain_texture.json',
            'data/incense-surfaces/source.json', 'data/incense-surfaces/java-closed.json',
            'data/incense-surfaces/java-open.json',
        } | {f'runtime/RP/textures/kaleidoscope_tavern/block/deco/incense/{kind}_incense.png'
             for kind in contract.KINDS}
        for name in paths:
            target = self.root / name
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(contract.ROOT / name, target)

    def change(self, name, edit):
        path = self.root / name
        value = json.loads(path.read_text())
        edit(value)
        path.write_text(json.dumps(value, indent=2) + '\n')

    def models(self, state):
        source = json.loads((self.root / f'data/incense-surfaces/java-{state}.json').read_text())
        geo = json.loads((self.root / f'runtime/RP/models/entity/incense_{state}.geo.json').read_text())['minecraft:geometry'][0]
        image = Image.open(self.root / 'runtime/RP/textures/kaleidoscope_tavern/block/deco/incense/catnip_incense.png').convert('RGBA')
        return source, geo, image

    def test_current_all_types_states_and_rays(self):
        result = contract.check(self.root)
        self.assertEqual(result['firstVisibleUndersideRays'], 256)
        self.assertFalse(result['clientRenderingTested'])

    def test_missing_face_is_visible_regression_in_both_models(self):
        for state in ('closed', 'open'):
            with self.subTest(state=state):
                source, geo, image = self.models(state)
                del geo['bones'][0]['cubes'][3]['uv']['down']
                self.assertEqual(contract.first_opaque_down(geo, image, -.5, -.5, java=False)[:2], (4, 1))
                with self.assertRaisesRegex(AssertionError, 'First-visible incense underside differs'):
                    contract.check_underside(source, geo, image)

    def test_wrong_uv_is_visible_regression(self):
        source, geo, image = self.models('closed')
        geo['bones'][0]['cubes'][3]['uv']['down'] = copy.deepcopy(geo['bones'][0]['cubes'][1]['uv']['down'])
        with self.assertRaisesRegex(AssertionError, 'First-visible incense underside differs'):
            contract.check_underside(source, geo, image)

    def test_source_fill_geometry_and_top_are_preserved(self):
        for field in ('origin', 'size', 'uv'):
            with self.subTest(field=field):
                name = 'runtime/RP/models/entity/incense_open.geo.json'
                original = (self.root / name).read_text()
                def alter(value):
                    cube = value['minecraft:geometry'][0]['bones'][0]['cubes'][3]
                    if field == 'uv':
                        cube['uv']['up']['uv'][0] += 1
                    else:
                        cube[field][1] += .1
                self.change(name, alter)
                with self.assertRaisesRegex(AssertionError, 'Source solid'):
                    contract.check(self.root)
                (self.root / name).write_text(original)

    def test_opaque_base_cannot_silently_hide_missing_fill(self):
        path = self.root / 'runtime/RP/textures/kaleidoscope_tavern/block/deco/incense/catnip_incense.png'
        image = Image.open(path).convert('RGBA')
        image.putpixel((9, 10), (255, 0, 0, 255)); image.save(path)
        with self.assertRaisesRegex(AssertionError, 'Opaque base blocks'):
            contract.check(self.root)

    def test_transparent_fill_is_rejected(self):
        path = self.root / 'runtime/RP/textures/kaleidoscope_tavern/block/deco/incense/catnip_incense.png'
        image = Image.open(path).convert('RGBA')
        image.putpixel((16, 12), (0, 0, 0, 0)); image.save(path)
        with self.assertRaisesRegex(AssertionError, 'Transparent source fill bottom'):
            contract.check(self.root)

    def test_material_sidedness_still_required(self):
        self.change('runtime/BP/blocks/catnip_incense.json', lambda d: d['minecraft:block']['components']['minecraft:material_instances']['foliage'].update(render_method='alpha_test'))
        with self.assertRaisesRegex(AssertionError, 'Mixed render methods'):
            contract.check(self.root)

    def test_lifecycle_wiring_remains_guarded(self):
        self.change('runtime/BP/blocks/catnip_incense.json', lambda d: d['minecraft:block']['components']['minecraft:tick'].update(looping=False))
        with self.assertRaises(AssertionError):
            contract.check(self.root)

    def test_effective_open_lifecycle_rejects_overrides(self):
        mutations = {
            'kaleidoscope_tavern:incense': {'disabled': True},
            'kaleidoscope_tavern:natural_break': {'drop': 'minecraft:dirt'},
            'minecraft:loot': 'loot_tables/blocks/dirt.json',
            'minecraft:tick': {'interval_range': [20, 20], 'looping': False},
            'minecraft:redstone_consumer': {'min_power': 1, 'propagates_power': False},
            'minecraft:movable': {'movement_type': 'push_pull'},
            'minecraft:collision_box': False,
            'minecraft:selection_box': False,
            'minecraft:destructible_by_mining': {'seconds_to_destroy': 1},
            'minecraft:destructible_by_explosion': {'explosion_resistance': 1},
            'minecraft:light_dampening': 15,
            'minecraft:connection_rule': {'accepts_connections_from': 'all'},
        }
        name = 'runtime/BP/blocks/catnip_incense.json'
        original = (self.root / name).read_text()
        for component, value in mutations.items():
            with self.subTest(component=component):
                self.change(name, lambda d: d['minecraft:block']['permutations'][0]['components'].update({component: value}))
                with self.assertRaisesRegex(AssertionError, 'Effective incense lifecycle differs.*open.*' + component):
                    contract.check(self.root)
                (self.root / name).write_text(original)

    def test_effective_components_replace_rather_than_deep_merge(self):
        self.change('runtime/BP/blocks/catnip_incense.json', lambda d: d['minecraft:block']['permutations'][0]['components'].update({'minecraft:tick': {'looping': True}}))
        with self.assertRaisesRegex(AssertionError, 'Effective incense lifecycle differs.*open.*minecraft:tick'):
            contract.check(self.root)

    def test_identical_explicit_open_overrides_are_valid(self):
        def repeat_inherited(d):
            block = d['minecraft:block']
            inherited = {k: copy.deepcopy(v) for k, v in block['components'].items()
                         if k not in ('minecraft:geometry', 'minecraft:material_instances')}
            block['permutations'][0]['components'].update(inherited)
        self.change('runtime/BP/blocks/catnip_incense.json', repeat_inherited)
        self.assertEqual(contract.check(self.root)['firstVisibleUndersideRays'], 256)

    def visibility_routes(self, block):
        return {
            'closed': block['components']['minecraft:geometry'],
            'open': block['permutations'][0]['components']['minecraft:geometry'],
            'item': block['components']['minecraft:item_visual']['geometry'],
        }

    def test_geometry_visibility_is_guarded_on_all_routes(self):
        name = 'runtime/BP/blocks/catnip_incense.json'
        original = (self.root / name).read_text()
        routes = ('closed', 'open', 'item', 'open_item')
        for route, visible in [(r, v) for r in routes for v in (False, "q.block_state('kaleidoscope_tavern:open') == 1")]:
            with self.subTest(route=route, visibility=visible):
                def hide(d):
                    block = d['minecraft:block']
                    if route == 'open_item':
                        item = copy.deepcopy(block['components']['minecraft:item_visual'])
                        item['geometry']['bone_visibility'] = {'root': visible}
                        block['permutations'][0]['components']['minecraft:item_visual'] = item
                    else:
                        self.visibility_routes(block)[route]['bone_visibility'] = {'root': visible}
                self.change(name, hide)
                with self.assertRaisesRegex(AssertionError, 'Incense geometry route/visibility differs'):
                    contract.check(self.root)
                (self.root / name).write_text(original)

    def test_launch_entry_rejects_each_guard_gap_with_and_without_source(self):
        import check_launch
        # A bounded author-input tree exercises the real --java-source route.
        # Its model elements and PNG bytes come from the already pinned fixtures.
        java = self.root / 'author-input'
        assets = java / 'src/main/resources/assets/kaleidoscope_tavern'
        for kind in contract.KINDS:
            texture = assets / f'textures/block/deco/incense/{kind}_incense.png'
            texture.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(self.root / f'runtime/RP/textures/kaleidoscope_tavern/block/deco/incense/{kind}_incense.png', texture)
            for state, folder in (('closed', 'incense'), ('open', 'incense_open')):
                model = assets / f'models/block/deco/{folder}/{kind}_incense.json'
                model.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(self.root / f'data/incense-surfaces/java-{state}.json', model)
        self.assertEqual(contract.check(self.root, java)['firstVisibleUndersideRays'], 256)
        mutations = {
            'tick': lambda b: b['permutations'][0]['components'].update({'minecraft:tick': {'interval_range': [20, 20], 'looping': False}}),
            'collision': lambda b: b['permutations'][0]['components'].update({'minecraft:collision_box': False}),
            'drop': lambda b: b['permutations'][0]['components'].update({'kaleidoscope_tavern:natural_break': {'drop': 'minecraft:dirt'}}),
            **{route: lambda b, route=route: self.visibility_routes(b)[route].update(bone_visibility={'root': False})
               for route in ('closed', 'open', 'item')},
        }
        name = 'runtime/BP/blocks/catnip_incense.json'
        original = (self.root / name).read_text()
        for label, edits in [*[(k, [v]) for k, v in mutations.items()], ('combined', list(mutations.values()))]:
            for with_source in (False, True):
                with self.subTest(mutation=label, java_source=with_source):
                    self.change(name, lambda d: [edit(d['minecraft:block']) for edit in edits])
                    argv = ['check_launch.py'] + (['--java-source', str(java)] if with_source else [])
                    # Only relocate the entry point's inputs. Neither the
                    # checker nor its runtime/source validation is mocked.
                    with patch.object(check_launch, 'ROOT', self.root), patch('sys.argv', argv):
                        with self.assertRaisesRegex(AssertionError, 'Effective incense lifecycle differs|Incense geometry route/visibility differs'):
                            check_launch.main()
                    (self.root / name).write_text(original)

    def test_cutouts_cannot_be_thickened(self):
        self.change('runtime/RP/models/entity/incense_closed.geo.json', lambda d: d['minecraft:geometry'][0]['bones'][0]['cubes'][4]['size'].__setitem__(0, .1))
        with self.assertRaisesRegex(AssertionError, 'No thickened duplicate cutout layers'):
            contract.check(self.root)

    def test_item_must_use_shared_closed_owner(self):
        self.change('runtime/BP/blocks/catnip_incense.json', lambda d: d['minecraft:block']['components']['minecraft:item_visual']['geometry'].update(identifier='geometry.unrelated'))
        with self.assertRaises(AssertionError):
            contract.check(self.root)

    def test_open_state_must_use_shared_open_owner(self):
        self.change('runtime/BP/blocks/catnip_incense.json', lambda d: d['minecraft:block']['permutations'][0]['components']['minecraft:geometry'].update(identifier='geometry.unrelated'))
        with self.assertRaises(AssertionError):
            contract.check(self.root)

    def test_retired_projection_cannot_return(self):
        name = 'runtime/RP/models/entity/incense_closed.geo.json'
        self.change('data/baseline-reconciliation.json', lambda d: d['reviewedAssetDeltaLayers'].append({'release': 'obsolete', 'files': {name: {}}}))
        with self.assertRaisesRegex(AssertionError, 'Incense returned to a reverse delta'):
            contract.check(self.root)

    def test_current_owner_is_not_reconstructed(self):
        from baseline_reference import previous_bytes
        for name in contract.runtime_sources():
            self.assertEqual(previous_bytes(contract.ROOT, contract.ROOT/name), (contract.ROOT/name).read_bytes())


if __name__ == '__main__':
    unittest.main()
