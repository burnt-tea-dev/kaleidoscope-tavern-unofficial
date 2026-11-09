"""Mutation tests call the actual shared resource validator, not a postimage."""
import copy
import json
import shutil
import tempfile
import unittest
from unittest.mock import patch
from pathlib import Path
from machine_ingredient_geometry import (ROOT, SOURCE, CARD, CUBE, BARREL, ANIMATION,
                                        CONTROLLER, FOODS, HELPERS, check, resource_paths)


class PressingCardContract(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        cls.root = Path(cls.temp.name)
        for name in resource_paths():
            p = cls.root / name
            p.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(ROOT / name, p)
        shutil.copytree(ROOT / SOURCE, cls.root / SOURCE)

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def rejects(self, name, mutate):
        p = self.root / name
        before = p.read_bytes()
        try:
            doc = json.loads(before)
            mutate(doc)
            p.write_text(json.dumps(doc))
            with self.assertRaises(AssertionError):
                check(self.root)
        finally:
            p.write_bytes(before)

    def test_source_dimensions_and_routes(self):
        result = check(self.root)
        self.assertEqual([8, 8, .5], result['card_dimensions'])
        self.assertEqual((8, 64, 22, 5), tuple(result[k] for k in ('helpers', 'slots', 'card_ids', 'cube_kinds')))
        self.assertIs(False, result['native_frame_culling_verified'])

    def test_every_cube_dimensions_centers_and_uvs(self):
        for i in range(8):
            for field in ('origin', 'size'):
                for axis in range(3):
                    with self.subTest(cube=i, field=field, axis=axis):
                        self.rejects(CARD, lambda d, i=i, field=field, axis=axis:
                            d['minecraft:geometry'][0]['bones'][5+i*3]['cubes'][0][field].__setitem__(axis, 1))
            for face in ('north', 'south'):
                with self.subTest(cube=i, face=face):
                    self.rejects(CARD, lambda d, i=i, face=face:
                        d['minecraft:geometry'][0]['bones'][5+i*3]['cubes'][0]['uv'][face]['uv_size'].__setitem__(0, -16))

    def test_no_slot_or_pose_scaling_and_hierarchy_drift(self):
        for i in range(27):
            with self.subTest(bone=i):
                self.rejects(CARD, lambda d, i=i: d['minecraft:geometry'][0]['bones'][i]['pivot'].__setitem__(1, 1))
                self.rejects(CARD, lambda d, i=i: d['minecraft:geometry'][0]['bones'][i].update(parent='wrong'))
        self.rejects(CARD, lambda d: d['minecraft:geometry'][0]['description'].update(visible_bounds_width=4))
        self.rejects(CARD, lambda d: d['minecraft:geometry'][0]['bones'][0].update(scale=[2, 2, 2]))
        self.rejects(CARD, lambda d: d['minecraft:geometry'][0]['bones'][0]['pivot'].__setitem__(0, False))
        for name in ('tilt', 'offset', 'ingredient_7', 'item_y_7', 'item_z_7'):
            self.rejects(ANIMATION, lambda d, name=name:
                d['animations']['animation.kt_runtime.pressing.layout']['bones'][name].update(scale=[2, 2, 2]))
        self.rejects(ANIMATION, lambda d:
            d['animations']['animation.kt_runtime.pressing.layout']['bones']['tilt']['rotation'].__setitem__(0, 45))

    def test_all_eight_consumers_keep_routes_and_no_compensating_scale(self):
        for helper in HELPERS:
            name = 'runtime/RP/entity/runtime_' + helper + '.entity.json'
            for key, value in [('geometry', {'card': 'geometry.wrong'}), ('materials', {'default': 'entity_alphablend'}),
                               ('scripts', {'animate': ['layout'], 'scale': '2'}), ('textures', {})]:
                with self.subTest(helper=helper, field=key):
                    self.rejects(name, lambda d, key=key, value=value:
                        d['minecraft:client_entity']['description'].__setitem__(key, value))
            name = 'runtime/BP/entities/' + helper + '_visual.json'
            self.rejects(name, lambda d: d['minecraft:entity']['components'].update({'minecraft:scale': {'value': 2}}))
            self.rejects(name, lambda d: d['minecraft:entity']['description']['properties']['kaleidoscope_tavern:fill_stage']['range'].__setitem__(1, 7))
        path = self.root / 'runtime/RP/attachables/unexpected.json'
        path.parent.mkdir(parents=True, exist_ok=True)
        try:
            path.write_text('{"geometry":"geometry.kt_runtime.pressing_card"}')
            with self.assertRaisesRegex(AssertionError, 'census'):
                check(self.root)
        finally:
            path.unlink()

    def test_controller_food_kind_visibility_and_clock_controls(self):
        def rc(d):
            return d['render_controllers']['controller.render.kt_runtime.pressing_ingredients']
        for key, value in [('geometry', 'Geometry.card'), ('textures', ['Texture.kind_1']),
                           ('materials', [{'*': 'Material.other'}]), ('part_visibility', [])]:
            self.rejects(CONTROLLER, lambda d, key=key, value=value: rc(d).__setitem__(key, value))
        for i in range(8):
            self.rejects(CONTROLLER, lambda d, i=i: rc(d)['part_visibility'][i].update({f'ingredient_{i}': '1'}))
        p = self.root / FOODS
        before = p.read_bytes()
        try:
            p.write_bytes(before.replace(b'"minecraft:ice": 22', b'"minecraft:ice": 1'))
            with self.assertRaisesRegex(AssertionError, 'Food'):
                check(self.root)
        finally:
            p.write_bytes(before)

    def test_barrel_and_cube_controls_are_not_enlarged(self):
        for i in range(8):
            self.rejects(CUBE, lambda d, i=i: d['minecraft:geometry'][0]['bones'][5+i*3]['cubes'][0].update(size=[8, 8, 8]))
        for i in range(9):
            self.rejects(BARREL, lambda d, i=i: d['minecraft:geometry'][0]['bones'][i]['cubes'][0].update(size=[4, 4, .25]))

    def test_current_owner_cannot_return_to_historical_projection(self):
        for section in ('files', 'reviewedFunctionalDeltas'):
            self.rejects('data/baseline-reconciliation.json', lambda d, section=section:
                d.setdefault(section, {}).__setitem__(CARD, {}))
        for section in ('reviewedFunctionalDeltaLayers', 'reviewedAssetDeltaLayers'):
            self.rejects('data/baseline-reconciliation.json', lambda d, section=section:
                d.setdefault(section, []).append({'release': 'fixture', 'files': {CARD: {}}}))
        for section in ('reviewedChanges', 'newRuntimeFiles'):
            self.rejects('data/launch-repair-reference.json', lambda d, section=section:
                d.setdefault(section, {}).__setitem__(CARD, {}))

    def test_launch_reaches_and_rejects_malformed_pressing_after_valid_incense(self):
        import check_launch
        import check_incense_surfaces as incense
        # The launch entry checks incense first. Provide its real bounded inputs,
        # not a mocked check, then require the pressing owner's actual failure.
        paths = set(incense.runtime_sources()) | {
            'runtime/RP/textures/terrain_texture.json',
            'data/incense-surfaces/source.json', 'data/incense-surfaces/java-closed.json',
            'data/incense-surfaces/java-open.json',
        } | {f'runtime/RP/textures/kaleidoscope_tavern/block/deco/incense/{kind}_incense.png'
             for kind in incense.KINDS}
        for name in paths:
            p = self.root / name
            p.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(ROOT / name, p)
        self.assertEqual(incense.check(self.root)['firstVisibleUndersideRays'], 256)
        cases = [(CARD, lambda d: d['minecraft:geometry'][0]['bones'][26]['cubes'][0]['size'].__setitem__(0, 4),
                  'Centered dimensions'),
                 ('runtime/RP/entity/runtime_pressing_tub_ingredients_7.entity.json',
                  lambda d: d['minecraft:client_entity']['description']['materials'].update(default='entity_alphablend'),
                  'Helper resource route')]
        for name, mutate, reason in cases:
            with self.subTest(resource=name):
                path = self.root / name
                raw = path.read_bytes()
                try:
                    value = json.loads(raw); mutate(value); path.write_text(json.dumps(value))
                    # Relocate only inputs/argv. Neither validator is patched.
                    with patch.object(check_launch, 'ROOT', self.root), patch('sys.argv', ['check_launch.py']):
                        with self.assertRaisesRegex(AssertionError, reason):
                            check_launch.main()
                finally:
                    path.write_bytes(raw)

    def test_source_cannot_assert_false_scale_by_changing_metadata(self):
        self.rejects(SOURCE + '/1.20.1-generated.json', lambda d: d['display']['fixed'].update(scale=[.5, .5, .5]))


if __name__ == '__main__':
    unittest.main()
