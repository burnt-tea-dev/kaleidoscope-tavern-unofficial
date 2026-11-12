"""A real pre-repair card is red; source-relative north U is green."""
import copy
import json
import unittest
from PIL import Image
from check_machine_ingredient_broadfaces import ROOT, audit, check, source_frames


class MachineBroadFaces(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.frames = source_frames(ROOT)

    def test_all_68_source_frames_and_both_actual_card_routes(self):
        result = check(ROOT)
        self.assertEqual(result['source_frames'], 68)
        self.assertFalse(result['alpha_edge_extrusion'])
        self.assertFalse(result['world_frame_verified'])

    def test_known_before_rejects_and_only_north_u_repairs_relative_sampling(self):
        for name in ('runtime_pressing_card', 'runtime_barrel_ingredients_card'):
            doc = json.loads((ROOT/f'runtime/RP/models/entity/{name}.geo.json').read_text())
            cube = copy.deepcopy(next(b['cubes'][0] for b in doc['minecraft:geometry'][0]['bones'] if b.get('cubes')))
            cube['uv']['north'] = {'uv': [0, 0], 'uv_size': [16, 16]}
            before = audit(cube, self.frames)
            self.assertEqual(before['texel_mismatches'], 68*256)
            self.assertGreater(before['alpha_mismatches'], 0)
            self.assertGreater(before['visible_rgba_mismatches'], 0)
            cube['uv']['north'] = {'uv': [16, 0], 'uv_size': [-16, 16]}
            after = audit(cube, self.frames)
            self.assertEqual(after['texel_mismatches'], 0)
            self.assertEqual(before['normals'], after['normals'])
            self.assertEqual(after['visible_rgba_mismatches'], 0)

    def test_vertical_flip_or_south_reorientation_cannot_hide_the_regression(self):
        cube = {'origin': [-4, -4, -.25], 'size': [8, 8, .5],
                'uv': {'north': {'uv': [16, 0], 'uv_size': [-16, 16]},
                       'south': {'uv': [0, 0], 'uv_size': [16, 16]}}}
        cube['uv']['north'] = {'uv': [16, 16], 'uv_size': [-16, -16]}
        self.assertGreater(audit(cube, self.frames)['texel_mismatches'], 0)
        cube['uv']['south'] = {'uv': [16, 0], 'uv_size': [-16, 16]}
        with self.assertRaisesRegex(AssertionError, 'south'):
            audit(cube, self.frames)

    def test_only_proven_vanilla_pixel_differences_use_private_ingredient_aliases(self):
        source = ROOT/'data/machine-ingredient-source'
        manifest = json.loads((source/'source.json').read_text())
        for row in manifest['items']:
            if row['id'] not in manifest['private_texture_replacements']:
                continue
            original = Image.open(source/row['original_native_texture']).convert('RGBA')
            java = Image.open(source/row['texture']).convert('RGBA')
            path = ROOT/'runtime/RP'/(manifest['private_texture_replacements'][row['id']]+'.png')
            actual = Image.open(path).convert('RGBA')
            self.assertEqual(actual.tobytes(), java.tobytes())
            pixels = [(original.getpixel((x, y)), java.getpixel((x, y))) for y in range(16) for x in range(16)]
            alpha = sum(a[3] != b[3] for a, b in pixels)
            visible = sum(a != b and bool(a[3] or b[3]) for a, b in pixels)
            self.assertEqual((alpha, visible), (8, 8) if row['id'].endswith('honeycomb') else (0, 36))
            self.assertFalse((ROOT/'runtime/RP'/('textures/items/honeycomb.png')).exists())

    def test_pink_petals_version_difference_does_not_justify_an_unrequested_pixel_replacement(self):
        source = ROOT/'data/machine-ingredient-source'
        a = Image.open(source/'textures/minecraft/pink_petals.png').convert('RGBA')
        b = Image.open(source/'cross-version/pink_petals-1.21.1.png').convert('RGBA')
        self.assertNotEqual(a.tobytes(), b.tobytes())
        self.assertEqual([bool(a.getpixel((x, y))[3]) for y in range(16) for x in range(16)],
                         [bool(b.getpixel((x, y))[3]) for y in range(16) for x in range(16)])
        catalog = json.loads((ROOT/'data/barrel-materials.json').read_text())['materials']
        self.assertEqual(next(r for r in catalog if r['id'] == 'minecraft:pink_petals')['texture'], 'textures/items/pink_petals')


if __name__ == '__main__':
    unittest.main()
