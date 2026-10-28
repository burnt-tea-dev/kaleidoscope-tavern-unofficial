"""Synthetic boundary cases; no private implementation or author assets."""
import copy
import json
from pathlib import Path
import tempfile
import unittest

from native_freezer_extension import COPIES, LOWERS, NAMESPACE, validate_upper_copies
from doll_renderer_extension import patch_manifests


class NativeUpperBoundary(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.spec = {'id': 'senluo:chinesefood-native-freezer-storage', 'copies': dict(COPIES)}
        self.profile = {'admission': 'current-author-curated'}
        self.changed = {}
        for lower in LOWERS:
            definition = {'format_version': '1.26.30', 'minecraft:block': {
                'description': {'identifier': NAMESPACE + lower,
                                'states': {NAMESPACE + 'top': [False, True]}},
                'components': {'minecraft:geometry': 'geometry.synthetic_' + lower,
                               'minecraft:block_entity': {'container': {'slot_count': 54}, 'dynamic_properties': True},
                               'minecraft:loot': 'loot_tables/senluo_native/freezer_empty.json'},
                'permutations': [{'condition': 'synthetic', 'components': {'fixture:component': {}}}]}}
            self.changed['blocks/kitchen/' + lower + '.json'] = json.dumps(definition).encode()
            upper = copy.deepcopy(definition)
            block = upper['minecraft:block']
            block['description']['identifier'] += '_upper'
            block['description']['states'][NAMESPACE + 'top'] = [True, False]
            block['components']['minecraft:block_entity'] = {'container': {'slot_count': 36}}
            path = self.root / ('host-assets/chinesefood/' + lower + '_upper.json')
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(json.dumps(upper))

    def validate(self):
        return validate_upper_copies(self.spec, self.root, self.changed, self.profile)

    def test_six_derived_definitions_preserve_every_unrelated_field(self):
        before = dict(self.changed)
        self.assertEqual(self.validate(), set(COPIES.values()))
        self.assertEqual(self.changed, before)

    def test_titled_containers_keep_distinct_halves_and_original_capacities(self):
        for lower in LOWERS:
            name = 'blocks/kitchen/' + lower + '.json'
            definition = json.loads(self.changed[name])
            definition['minecraft:block']['components']['minecraft:block_entity']['container']['title'] = 'senluo.freezer.lower'
            self.changed[name] = json.dumps(definition).encode()
            path = self.root / ('host-assets/chinesefood/' + lower + '_upper.json')
            upper = json.loads(path.read_text())
            upper['minecraft:block']['components']['minecraft:block_entity']['container']['title'] = 'senluo.freezer.upper'
            path.write_text(json.dumps(upper))
        self.assertEqual(self.validate(), set(COPIES.values()))
        path = self.root / next(iter(COPIES))
        upper = json.loads(path.read_text())
        upper['minecraft:block']['components']['minecraft:block_entity']['container']['title'] = 'senluo.freezer.lower'
        path.write_text(json.dumps(upper))
        with self.assertRaisesRegex(ValueError, 'author definition'):
            self.validate()

    def test_unreviewed_lower_title_is_rejected(self):
        name = 'blocks/kitchen/freezer.json'
        definition = json.loads(self.changed[name])
        definition['minecraft:block']['components']['minecraft:block_entity']['container']['title'] = 'unrelated.container'
        self.changed[name] = json.dumps(definition).encode()
        with self.assertRaisesRegex(ValueError, 'lower container title'):
            self.validate()

    def test_partial_or_unrelated_copy_inventory_and_unreviewed_profile_fail(self):
        self.profile = None
        with self.assertRaisesRegex(ValueError, 'exact six'): self.validate()
        self.profile = {'admission': 'current-author-curated'}
        self.spec['copies'].pop(next(iter(COPIES)))
        with self.assertRaisesRegex(ValueError, 'exact six'): self.validate()
        self.spec['copies'] = dict(COPIES)
        self.spec['copies']['elsewhere.json'] = 'blocks/unrelated.json'
        with self.assertRaisesRegex(ValueError, 'exact six'): self.validate()

    def test_changed_geometry_capacity_default_or_creative_menu_fail(self):
        path = self.root / next(iter(COPIES))
        original = json.loads(path.read_text())
        for field in ['geometry', 'capacity', 'default', 'creative']:
            changed = copy.deepcopy(original)
            block = changed['minecraft:block']
            if field == 'geometry': block['components']['minecraft:geometry'] = 'geometry.other'
            elif field == 'capacity': block['components']['minecraft:block_entity']['container']['slot_count'] = 54
            elif field == 'default': block['description']['states'][NAMESPACE + 'top'] = [False, True]
            else: block['description']['menu_category'] = {'category': 'items'}
            path.write_text(json.dumps(changed))
            with self.subTest(field=field), self.assertRaisesRegex(ValueError, 'author definition'):
                self.validate()
        path.write_text(json.dumps(original))
        self.changed.pop('blocks/kitchen/freezer.json')
        with self.assertRaisesRegex(ValueError, 'reviewed lower'): self.validate()


class NativeLifecycleApiBoundary(unittest.TestCase):
    def pair(self):
        return [{'header': {'uuid': uid, 'version': [1, 0, 6], 'name': 'Synthetic'},
                 'modules': [{'uuid': uid + '-module', 'version': [1, 0, 6]}],
                 'dependencies': [{'uuid': other, 'version': [1, 0, 6]}] +
                    ([{'module_name': '@minecraft/server', 'version': '2.7.0'},
                      {'module_name': '@minecraft/server-ui', 'version': '2.0.0'}] if uid == 'bp' else [])}
                for uid, other in [('bp', 'rp'), ('rp', 'bp')]]

    def profile(self):
        return {'admission': 'current-author-curated', 'author_version': [1, 0, 6],
                'behavior_uuid': 'bp', 'host_uuid': 'rp', 'owner_version': [1, 0, 73],
                'version': [1, 0, 10673], 'manifest_names': {'BP': 'Synthetic BP', 'RP': 'Synthetic RP'},
                'script_dependencies': {'@minecraft/server': '2.8.0'}}

    def test_only_the_reviewed_behavior_api_advances(self):
        originals = self.pair()
        result = patch_manifests(*originals, [1, 0, 10673], [1, 0, 73], self.profile())
        self.assertEqual(result[0]['dependencies'][1]['version'], '2.8.0')
        self.assertEqual(result[0]['dependencies'][2], originals[0]['dependencies'][2])
        self.assertEqual(originals, self.pair())
        self.assertEqual(len(result[1]['dependencies']), 1)

    def test_unreviewed_api_and_wrong_author_preimage_fail(self):
        profile = self.profile()
        profile['script_dependencies'] = {'@minecraft/server': '9.0.0-beta'}
        with self.assertRaisesRegex(ValueError, 'Unreviewed'):
            patch_manifests(*self.pair(), [1, 0, 10673], [1, 0, 73], profile)
        pair = self.pair()
        pair[0]['dependencies'][1]['version'] = '2.9.0'
        with self.assertRaisesRegex(ValueError, 'original script API'):
            patch_manifests(*pair, [1, 0, 10673], [1, 0, 73], self.profile())


if __name__ == '__main__':
    unittest.main()
