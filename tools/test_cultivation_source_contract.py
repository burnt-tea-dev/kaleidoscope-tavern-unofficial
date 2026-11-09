"""Negative controls call the actual current resource validator."""
import json
import shutil
import tempfile
import unittest
from pathlib import Path
from cultivation_source_contract import (ROOT, BLOCKS, LOOT, PLANTS, PLANT_CONTROLS,
    PLANT_FIXTURES, plant_resource_paths, check_resources, check_plant_resources)
from wild_vine_surfaces import GEOMETRY, FIXTURES


class CurrentCultivationResources(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        for name in [*(f'runtime/BP/blocks/{name}.json' for name in BLOCKS),
                     *(f'runtime/RP/textures/kaleidoscope_tavern/block/plant/{name}.png' for name in BLOCKS),
                     'runtime/BP/' + LOOT, GEOMETRY, *plant_resource_paths()]:
            target = self.root / name
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(ROOT / name, target)

        shutil.copytree(ROOT / FIXTURES, self.root / FIXTURES)
        shutil.copytree(ROOT / PLANT_FIXTURES, self.root / PLANT_FIXTURES)

    def edit(self, name, mutate):
        path = self.root / name
        data = json.loads(path.read_text())
        mutate(data)
        path.write_text(json.dumps(data))

    def test_current_resources(self):
        check_resources(self.root)

    def test_block_item_and_tool_predicates_are_rejected(self):
        for change in (lambda pool: pool['entries'][0].update(name='kaleidoscope_tavern:wild_grapevine'),
                       lambda pool: pool.update(conditions=[{'condition': 'match_tool'}])):
            with self.subTest(change=change):
                path = self.root / 'runtime/BP' / LOOT
                shutil.copyfile(ROOT / 'runtime/BP' / LOOT, path)
                self.edit('runtime/BP/' + LOOT, lambda data: change(data['pools'][0]))
                with self.assertRaises(AssertionError):
                    check_resources(self.root)

    def test_disconnected_or_duplicate_loot_is_rejected(self):
        name = 'runtime/BP/blocks/wild_grapevine.json'
        for change in (lambda comp: comp.pop('minecraft:loot'),
                       lambda comp: comp.update({'kaleidoscope_tavern:natural_break': {}})):
            with self.subTest(change=change):
                shutil.copyfile(ROOT / name, self.root / name)
                self.edit(name, lambda data: change(data['minecraft:block']['components']))
                with self.assertRaises(AssertionError):
                    check_resources(self.root)


    def test_source_rescale_and_directed_uv_regressions(self):
        mutations = {
            'old narrow slab': lambda c: c[0]['size'].__setitem__(0, 16),
            'missing Java rescale': lambda c: c[0]['size'].__setitem__(0, 14.4),
            'moved center plane': lambda c: c[0]['origin'].__setitem__(2, .02),
            'wrong rotation': lambda c: c[0]['rotation'].__setitem__(1, 45),
            'wrong pivot': lambda c: c[0]['pivot'].__setitem__(0, 1),
            'mirrored UV': lambda c: c[0]['uv']['north']['uv_size'].__setitem__(0, -16),
            'box UV offset': lambda c: c[0]['uv']['south']['uv'].__setitem__(0, 16),
            'unknown alias': lambda c: c[0]['uv']['north'].update(material_instance='unshaded'),
            'unwanted cap': lambda c: c[0]['uv'].update(up={'uv': [0, 0], 'uv_size': [16, 16]}),
            'missing directed face': lambda c: c[0]['uv'].pop('south'),
            'box UV': lambda c: c[0].update(uv=[0, 0]),
            'undisclosed thickness': lambda c: c[0]['size'].__setitem__(2, .1),
        }
        for label, change in mutations.items():
            with self.subTest(label=label):
                shutil.copyfile(ROOT / GEOMETRY, self.root / GEOMETRY)
                self.edit(GEOMETRY, lambda d: change(d['minecraft:geometry'][0]['bones'][0]['cubes']))
                with self.assertRaises(AssertionError):
                    check_resources(self.root)

    def test_shared_world_item_material_and_permutation_routes(self):
        mutations = {
            'inactive a3': {'minecraft:geometry': {'identifier': 'geometry.kt_assets_a3.wild_grapevine_plant'}},
            'hidden root': {'minecraft:geometry': {'identifier': 'geometry.kt_assets_a2.wild_grapevine', 'bone_visibility': {'root': False}}},
            'changed pose': {'minecraft:transformation': {'scale': [.5, 1, 1]}},
            'partial item override': {'minecraft:item_visual': {'geometry': {'identifier': 'geometry.kt_assets_a2.wild_grapevine'}}},
            'partial material replacement': {'minecraft:material_instances': {'*': {'texture': 'kt_assets_a2_wild_grapevine', 'render_method': 'alpha_test_single_sided'}}},
        }
        for name in BLOCKS:
            path = 'runtime/BP/blocks/' + name + '.json'
            for label, change in mutations.items():
                for permutation in (False, True):
                    with self.subTest(name=name, label=label, permutation=permutation):
                        shutil.copyfile(ROOT / path, self.root / path)
                        def mutate(d):
                            block = d['minecraft:block']
                            if permutation:
                                block['permutations'] = [{'condition': 'true', 'components': change}]
                            else:
                                block['components'].update(change)
                        self.edit(path, mutate)
                        with self.assertRaises(AssertionError):
                            check_resources(self.root)
            shutil.copyfile(ROOT / path, self.root / path)


    def test_source_culling_shading_and_ao_on_every_visual_route(self):
        for name in BLOCKS:
            path = 'runtime/BP/blocks/' + name + '.json'
            for item in (False, True):
                for field, value in (('render_method', 'alpha_test'),
                                     ('render_method', 'blend'),
                                     ('face_dimming', True),
                                     ('ambient_occlusion', 1)):
                    with self.subTest(name=name, item=item, field=field, value=value):
                        shutil.copyfile(ROOT / path, self.root / path)
                        def mutate(d):
                            components = d['minecraft:block']['components']
                            material = (components['minecraft:item_visual']['material_instances']
                                        if item else components['minecraft:material_instances'])
                            material['*'][field] = value
                        self.edit(path, mutate)
                        with self.assertRaises(AssertionError):
                            check_resources(self.root)
            shutil.copyfile(ROOT / path, self.root / path)

    def test_disconnected_terrain_and_changed_source_texture(self):
        path = 'runtime/RP/textures/terrain_texture.json'
        self.edit(path, lambda d: d['texture_data']['kt_assets_a2_wild_grapevine'].update(textures='textures/other'))
        with self.assertRaises(AssertionError):
            check_resources(self.root)
        shutil.copyfile(ROOT / path, self.root / path)
        texture = self.root / 'runtime/RP/textures/kaleidoscope_tavern/block/plant/wild_grapevine.png'
        texture.write_bytes(texture.read_bytes() + b'changed')
        with self.assertRaises(AssertionError):
            check_resources(self.root)


    def test_crop_and_filled_vine_complete_source_routes(self):
        self.assertEqual(check_plant_resources(self.root), {
            'models': 48, 'directed_faces': 660, 'state_combinations': 1026,
            'visual_declarations': 108, 'engine_execution': False})

    def test_every_crop_and_vine_material_declaration_rejects_double_siding(self):
        rejected = 0
        for name in PLANTS + PLANT_CONTROLS:
            relative = 'runtime/BP/blocks/' + name + '.json'
            path = self.root / relative
            original = path.read_bytes()
            block = json.loads(original)['minecraft:block']
            routes = [('base', block['components'])]
            routes += [(str(i), p['components']) for i, p in enumerate(block['permutations'])]
            for location, components in routes:
                contexts = [('world', components['minecraft:material_instances'])]
                if location == 'base':
                    contexts.append(('item', components['minecraft:item_visual']['material_instances']))
                for context, materials in contexts:
                    for tag in materials:
                        with self.subTest(name=name, location=location, context=context, tag=tag):
                            data = json.loads(original)
                            b = data['minecraft:block']
                            c = b['components'] if location == 'base' else b['permutations'][int(location)]['components']
                            m = c['minecraft:material_instances'] if context == 'world' else c['minecraft:item_visual']['material_instances']
                            m[tag]['render_method'] = 'alpha_test'
                            path.write_text(json.dumps(data))
                            with self.assertRaisesRegex(AssertionError, 'cutout material|item fallback'):
                                check_plant_resources(self.root)
                            rejected += 1
            path.write_bytes(original)
        self.assertEqual(rejected, 204)

    def test_plant_geometry_item_shading_and_effective_route_mutations(self):
        mutations = {
            'world geometry': lambda b: b['permutations'][0]['components']['minecraft:geometry'].update(identifier='geometry.unrelated'),
            'hidden world bone': lambda b: b['components']['minecraft:geometry'].update(bone_visibility={'root': False}),
            'partial material override': lambda b: b['permutations'][0]['components']['minecraft:material_instances']['*'].pop('ambient_occlusion'),
            'AO': lambda b: b['components']['minecraft:material_instances']['*'].update(ambient_occlusion=1),
            'dimming': lambda b: b['components']['minecraft:material_instances']['*'].update(face_dimming=False),
            'item geometry': lambda b: b['components']['minecraft:item_visual']['geometry'].update(identifier='geometry.unrelated'),
            'item pose': lambda b: b['components']['minecraft:item_visual'].update(transformation={'scale': [.5, 1, 1]}),
            'world pose': lambda b: b['permutations'][0]['components'].update({'minecraft:transformation': {'scale': [.5, 1, 1]}}),
            'item permutation override': lambda b: b['permutations'][0]['components'].update({'minecraft:item_visual': b['components']['minecraft:item_visual']}),
            'duplicate permutation': lambda b: b['permutations'].append(b['permutations'][0]),
            'missing permutation': lambda b: b['permutations'].pop(),
            'wrong age route': lambda b: b['permutations'][0].update(condition=b['permutations'][1]['condition']),
            'state loss': lambda b: b['description']['states']['kaleidoscope_tavern:age'].pop(),
            'wrong texture binding': lambda b: b['components']['minecraft:material_instances']['*'].update(texture='kt_assets_a2_wild_grapevine'),
        }
        for name in PLANTS + PLANT_CONTROLS:
            relative = 'runtime/BP/blocks/' + name + '.json'
            original = (self.root / relative).read_bytes()
            for label, mutate in mutations.items():
                with self.subTest(name=name, mutation=label):
                    (self.root / relative).write_bytes(original)
                    self.edit(relative, lambda d: mutate(d['minecraft:block']))
                    with self.assertRaises(AssertionError):
                        check_plant_resources(self.root)
            (self.root / relative).write_bytes(original)

    def test_plant_source_faces_and_terrain_are_not_bypassed(self):
        relative = 'runtime/RP/models/entity/grapevine_stage0.geo.json'
        original = (self.root / relative).read_bytes()
        changes = {
            'lost opposite face': lambda c: c[1]['uv'].pop('south'),
            'unrequested cap': lambda c: c[1]['uv'].update(up=c[1]['uv']['north']),
            'lost unshaded owner': lambda c: c[1]['uv']['north'].pop('material_instance'),
            'unknown material': lambda c: c[1]['uv']['north'].update(material_instance='unmapped'),
        }
        for label, change in changes.items():
            with self.subTest(mutation=label):
                (self.root / relative).write_bytes(original)
                self.edit(relative, lambda d: change(d['minecraft:geometry'][0]['bones'][0]['cubes']))
                with self.assertRaises(AssertionError):
                    check_plant_resources(self.root)
        (self.root / relative).write_bytes(original)
        terrain = 'runtime/RP/textures/terrain_texture.json'
        self.edit(terrain, lambda d: d['texture_data']['kt_assets_a2_grape_crop_stage0'].update(textures='textures/other'))
        with self.assertRaisesRegex(AssertionError, 'terrain binding'):
            check_plant_resources(self.root)
        shutil.copyfile(ROOT / terrain, self.root / terrain)
        texture = self.root / 'runtime/RP/textures/kaleidoscope_tavern/block/plant/grape_crop.png'
        texture.write_bytes(texture.read_bytes() + b'changed')
        with self.assertRaisesRegex(AssertionError, 'source texture'):
            check_plant_resources(self.root)


if __name__ == '__main__':
    unittest.main()
