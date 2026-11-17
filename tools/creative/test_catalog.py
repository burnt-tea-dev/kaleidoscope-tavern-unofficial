import ast
"""Native catalog data tests, not a Minecraft inventory renderer simulation."""
import copy
import importlib.util
import json
import os
from pathlib import Path
import tempfile
import unittest
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))

SPEC = importlib.util.spec_from_file_location('creative_catalog', Path(__file__).with_name('catalog.py'))
c = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(c)
TAVERN = Path(__file__).resolve().parents[2]
LIQUOR = Path(os.environ.get('LIQUOR_SOURCE', TAVERN.parent / 'world-liquor-src'))
KEY = 'kaleidoscope_tavern:itemGroup.name.tavern_'
COLORS = 'white light_gray gray black brown red orange yellow lime green cyan light_blue blue purple magenta pink'.split()


def put(root, path, value):
    path = root / path
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(c.encoded(value))


class FixtureTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.id = 'kaleidoscope_tavern:white_bar_stool'
        self.item = 'runtime/BP/items/white_bar_stool.json'
        self.block = 'runtime/BP/blocks/white_bar_stool.json'
        put(self.root, 'data/creative-decoration-groups.json', {})
        put(self.root, c.PLAN, {'schema': 1, 'namespace': 'kaleidoscope_tavern', 'tabs': [{
            'id': 'kaleidoscope_tavern:tavern_deco', 'category': 'items',
            'group': KEY+'deco', 'icon': self.id,
            'labels': {locale: 'Tavern Deco' for locale in c.LOCALES},
            'entries': [{'java': self.id, 'bedrock': self.id, 'state': 'default', 'position': 1}]}]})
        put(self.root, c.CATALOG, {'format_version': '1.21.90', 'minecraft:crafting_items_catalog': {'categories': [
            {'category_name': 'equipment', 'groups': [{'group_identifier': {'name': KEY+'decor', 'icon': self.id}, 'items': [self.id]}]}]}})
        put(self.root, self.item, {'format_version': '1.26.50', 'minecraft:item': {
            'description': {'identifier': self.id, 'menu_category': {'category': 'equipment', 'group': KEY+'decor'}},
            'components': {'minecraft:max_stack_size': 64, 'minecraft:block_placer': {'block': self.id}}}})
        put(self.root, self.block, {'format_version': '1.26.50', 'minecraft:block': {
            'description': {'identifier': self.id, 'menu_category': {'category': 'none'}}, 'components': {'test:untouched': {}}}})
        for locale in c.LOCALES:
            path = self.root / 'runtime/RP/texts' / (locale+'.lang')
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text('pack.name=Original\n## Shared Tavern effect bar names\neffect.test=Original Effect\n')

    def test_visible_menu_matches_new_group(self):
        c.apply(self.root, True)
        self.assertEqual(c.load(self.root/self.item)['minecraft:item']['description']['menu_category']['group'], KEY+'deco')

    def test_hidden_implementation_block_is_byte_preserved(self):
        old = (self.root/self.block).read_bytes()
        c.apply(self.root, True)
        self.assertEqual(old, (self.root/self.block).read_bytes())

    def test_gameplay_components_unchanged(self):
        old = c.load(self.root/self.item)
        c.apply(self.root, True)
        new = c.load(self.root/self.item)
        old['minecraft:item']['description'].pop('menu_category')
        new['minecraft:item']['description'].pop('menu_category')
        self.assertEqual(old, new)

    def test_check_fails_on_stale_data_without_writing(self):
        old = (self.root/c.CATALOG).read_bytes()
        with self.assertRaisesRegex(ValueError, 'Stale creative'):
            c.apply(self.root)
        self.assertEqual(old, (self.root/c.CATALOG).read_bytes())

    def test_idempotent_generation(self):
        c.apply(self.root, True)
        self.assertEqual(c.apply(self.root, True)['changed_files'], 0)

    def test_historical_root_does_not_use_the_current_metadata_owner(self):
        from baseline_reference import previous_bytes
        path = self.root / self.item
        self.assertEqual(previous_bytes(self.root, path), path.read_bytes())
        with self.assertRaisesRegex(ValueError, 'Stale creative'):
            previous_bytes(self.root, path, current_metadata=True)

    def test_catalog_membership_unchanged(self):
        old = set(c.entries(c.load(self.root/c.CATALOG)))
        c.apply(self.root, True)
        self.assertEqual(old, set(c.entries(c.load(self.root/c.CATALOG))))

    def test_unknown_new_decoration_requires_review(self):
        data = c.load(self.root/c.CATALOG)
        data['minecraft:crafting_items_catalog']['categories'][0]['groups'][0]['items'].append('kaleidoscope_tavern:new_decoration')
        put(self.root, c.CATALOG, data)
        with self.assertRaisesRegex(ValueError, 'missing from the reviewed plan'):
            c.planned(self.root)

    def test_does_not_promote_an_undefined_item(self):
        plan = c.load(self.root/c.PLAN)
        plan['tabs'][0]['entries'].append({'java': 'kaleidoscope_tavern:hidden_item', 'bedrock': 'kaleidoscope_tavern:hidden_item'})
        put(self.root, c.PLAN, plan)
        with self.assertRaisesRegex(ValueError, 'No visible definition'):
            c.planned(self.root)

    def test_existing_visible_definition_can_fill_a_missing_catalog_entry(self):
        item = c.load(self.root/self.item)
        lamp = 'kaleidoscope_tavern:green_pendant_lamp'
        item['minecraft:item']['description']['identifier'] = lamp
        put(self.root, 'runtime/BP/items/green_pendant_lamp.json', item)
        plan = c.load(self.root/c.PLAN)
        plan['tabs'][0]['entries'].append({'java': lamp, 'bedrock': lamp})
        put(self.root, c.PLAN, plan)
        c.apply(self.root, True)
        self.assertEqual(c.entries(c.load(self.root/c.CATALOG))[lamp],
                         ('items', KEY+'deco'))

    def test_invalid_native_category_rejected(self):
        plan = c.load(self.root/c.PLAN)
        plan['tabs'][0]['category'] = 'not_real'
        put(self.root, c.PLAN, plan)
        with self.assertRaisesRegex(ValueError, 'Invalid creative category'):
            c.planned(self.root)

    def test_duplicate_plan_rejected(self):
        plan = c.load(self.root/c.PLAN)
        plan['tabs'][0]['entries'].append(copy.deepcopy(plan['tabs'][0]['entries'][0]))
        put(self.root, c.PLAN, plan)
        with self.assertRaisesRegex(ValueError, 'Duplicate plan'):
            c.planned(self.root)

    def test_duplicate_catalog_rejected(self):
        data = c.load(self.root/c.CATALOG)
        data['minecraft:crafting_items_catalog']['categories'][0]['groups'][0]['items'].append(self.id)
        put(self.root, c.CATALOG, data)
        with self.assertRaisesRegex(ValueError, 'Duplicate/invalid catalog'):
            c.planned(self.root)

    def test_hidden_only_id_rejected(self):
        value = c.load(self.root/self.item)
        value['minecraft:item']['description']['menu_category'] = {'category': 'none'}
        put(self.root, self.item, value)
        with self.assertRaisesRegex(ValueError, 'No visible definition'):
            c.planned(self.root)

    def test_other_generated_language_tail_is_preserved(self):
        c.apply(self.root, True)
        for locale in c.LOCALES:
            data = (self.root/'runtime/RP/texts'/(locale+'.lang')).read_text()
            self.assertTrue(data.endswith('## Shared Tavern effect bar names\neffect.test=Original Effect\n'))
            self.assertIn('pack.name=Original\n', data)

    def test_duplicate_localization_rejected(self):
        with self.assertRaisesRegex(ValueError, 'Duplicate'):
            c.localize(KEY+'stools=Other\n', {KEY+'stools': 'Stools'})

    def test_current_catalog_rejects_reinstated_historical_owner(self):
        c.apply(self.root, True)
        baseline = 'data/baseline-reconciliation.json'
        launch = 'data/launch-repair-reference.json'
        put(self.root, baseline, {})
        put(self.root, launch, {})
        self.assertEqual(c.check_current(self.root)['changed_files'], 0)
        # Reintroduce the exact two ownership routes retired by this change.
        for path, section, error in [(baseline, 'files', 'historical postimage'),
                                     (launch, 'reviewedChanges', 'launch hash aggregate')]:
            put(self.root, path, {section: {c.CATALOG.as_posix(): {'after': 'old-catalog-hash'}}})
            with self.subTest(path=path), self.assertRaisesRegex(ValueError, error):
                c.check_current(self.root)
            put(self.root, path, {})

    def test_java_order_rejects_reordered_or_missing_wines(self):
        plan = c.load(self.root/c.PLAN)
        plan['tabs'][0]['entries'] = [
            {'java': 'kaleidoscope_tavern:'+name, 'bedrock': 'kaleidoscope_tavern:'+name+'_q6',
             'state': 'maximum bottle level'} for name in ('wine', 'brandy')]
        put(self.root, c.PLAN, plan)
        catalog = c.load(self.root/c.CATALOG)
        group = catalog['minecraft:crafting_items_catalog']['categories'][0]['groups'][0]
        group['items'] = [entry['bedrock'] for entry in plan['tabs'][0]['entries']]
        put(self.root, c.CATALOG, catalog)
        source = self.root/'ModCreativeTabs.java'
        wine = 'output.accept(BottleBlockItem.getMaxLevelDrink(ModItems.WINE));\n'
        brandy = 'output.accept(BottleBlockItem.getMaxLevelDrink(ModItems.BRANDY));\n'
        unrelated = 'output.accept(ModItems.GRAPE.get());\n'
        source.write_text('// '+wine+'/* '+wine+' */\n'+wine+unrelated+brandy)
        self.assertEqual(c.check_java_wine_order(self.root, source)['items'], 2)
        group['items'].reverse()
        put(self.root, c.CATALOG, catalog)
        with self.assertRaisesRegex(ValueError, 'Visible wine catalog differs'):
            c.check_java_wine_order(self.root, source)
        group['items'].reverse()
        put(self.root, c.CATALOG, catalog)
        for changed in (brandy+wine, wine, wine+brandy+brandy):
            source.write_text(changed)
            with self.subTest(source=changed), self.assertRaisesRegex(ValueError, 'differs from Java'):
                c.check_java_wine_order(self.root, source)

    def test_missing_addition_is_rejected(self):
        plan = c.load(self.root/c.PLAN)
        plan['bedrock_additions'] = [{'bedrock': 'kaleidoscope_tavern:guidebook', 'category': 'items'}]
        put(self.root, c.PLAN, plan)
        with self.assertRaisesRegex(ValueError, 'No visible definition'):
            c.planned(self.root)

    def test_duplicate_addition_is_rejected(self):
        plan = c.load(self.root/c.PLAN)
        plan['bedrock_additions'] = [{'bedrock': self.id, 'category': 'items'}]
        put(self.root, c.PLAN, plan)
        with self.assertRaisesRegex(ValueError, 'Duplicate plan'):
            c.planned(self.root)

    def test_explicit_unavailable_row_is_not_promoted(self):
        plan = c.load(self.root/c.PLAN)
        plan['tabs'][0]['entries'].append({'java': 'kaleidoscope_tavern:missing',
                                          'unavailable': 'No equivalent native stack'})
        put(self.root, c.PLAN, plan)
        c.apply(self.root, True)
        self.assertEqual(set(c.entries(c.load(self.root/c.CATALOG))), {self.id})

    def test_legacy_definition_keeps_catalog_group_without_invalid_menu_group(self):
        value = c.load(self.root/self.item)
        value['format_version'] = '1.21.50'
        put(self.root, self.item, value)
        c.apply(self.root, True)
        self.assertEqual(c.load(self.root/self.item)['minecraft:item']['description']['menu_category'],
                         {'category': 'items'})
        self.assertEqual(c.entries(c.load(self.root/c.CATALOG))[self.id], ('items', KEY+'deco'))


class RealPackTests(unittest.TestCase):
    def test_catalog_is_owned_by_the_current_generator(self):
        self.assertEqual(c.check_current(TAVERN)['changed_files'], 0)
        from baseline_reference import previous_bytes
        self.assertEqual(previous_bytes(TAVERN,TAVERN/c.CATALOG), (TAVERN/c.CATALOG).read_bytes())

    def test_both_current_catalogs_are_reproducible(self):
        self.assertEqual(c.apply(TAVERN)['changed_files'], 0)
        self.assertEqual(c.apply(LIQUOR)['changed_files'], 0)

    def test_shared_merge_membership_independent_of_pack_order(self):
        expected = {}
        for root in (TAVERN, LIQUOR):
            for tab in c.load(root/c.PLAN)['tabs']:
                expected.setdefault(tab['group'], set()).update(
                    entry['bedrock'] for entry in tab['entries'] if not entry.get('unavailable'))
        for roots in ((TAVERN, LIQUOR), (LIQUOR, TAVERN)):
            actual = {}
            for root in roots:
                for category in c.load(root/c.CATALOG)['minecraft:crafting_items_catalog']['categories']:
                    for group in category['groups']:
                        if 'group_identifier' in group:
                            actual.setdefault(group['group_identifier']['name'], set()).update(group['items'])
            self.assertEqual(actual, expected)

    def test_visible_items_follow_selected_java_tabs(self):
        for root in (TAVERN, LIQUOR):
            plan = c.load(root/c.PLAN)
            expected = []
            for tab in plan['tabs']:
                category = next((row for row in expected if row['category_name'] == tab['category']), None)
                if category is None:
                    category = {'category_name': tab['category'], 'groups': []}
                    expected.append(category)
                category['groups'].append({
                    'group_identifier': {'name': tab['group'], 'icon': tab['icon']},
                    'items': [entry['bedrock'] for entry in tab['entries'] if not entry.get('unavailable')]})
            for addition in plan.get('bedrock_additions', []):
                category = next(row for row in expected if row['category_name'] == addition['category'])
                if 'group_identifier' in category['groups'][-1]:
                    category['groups'].append({'items': []})
                category['groups'][-1]['items'].append(addition['bedrock'])
            self.assertEqual(c.load(root/c.CATALOG)['minecraft:crafting_items_catalog']['categories'], expected)

    def test_all_members_resolve_and_hidden_variants_stay_absent(self):
        for root in (TAVERN, LIQUOR):
            catalog, defs = c.entries(c.load(root/c.CATALOG)), c.definitions(root)
            self.assertTrue(set(catalog).issubset(defs))
            self.assertFalse(any(item.endswith(tuple('_q'+str(i) for i in range(1,6))) for item in catalog))
            for item, (category, group) in catalog.items():
                visible = [(value, kind) for _, value, kind in defs[item]
                           if value[kind]['description'].get('menu_category', {}).get('category')
                           in ('construction', 'equipment', 'items', 'nature')]
                self.assertTrue(visible, item)
                for value, kind in visible:
                    expected = {'category': category}
                    if group and tuple(map(int, value['format_version'].split('.'))) >= (1, 21, 60):
                        expected['group'] = group
                    self.assertEqual(value[kind]['description']['menu_category'], expected, item)

    def test_standalone_guide_is_visible_without_promoting_legacy_alias(self):
        catalog = c.entries(c.load(TAVERN/c.CATALOG))
        self.assertEqual(catalog['kaleidoscope_tavern:guidebook'], ('items', None))
        self.assertNotIn('kaleidoscope_tavern:recipe_book', catalog)

    def test_author_pendant_lamps_have_visible_definition_and_catalog_membership(self):
        catalog, defs = c.entries(c.load(LIQUOR/c.CATALOG)), c.definitions(LIQUOR)
        for color in ('green', 'pink'):
            item = 'kaleidoscope_world_liquor:'+color+'_pendant_lamp'
            self.assertEqual(catalog[item], ('items', 'kaleidoscope_world_liquor:itemGroup.main'))
            for _, value, kind in defs[item]:
                self.assertEqual(value[kind]['description']['menu_category'],
                                 {'category': 'items', 'group': 'kaleidoscope_world_liquor:itemGroup.main'})

    def test_group_icons_follow_java_representatives_and_declare_gaps(self):
        java_icons = {
            'kaleidoscope_tavern:tavern_main': 'kaleidoscope_tavern:wine',
            'kaleidoscope_tavern:tavern_deco': 'kaleidoscope_tavern:stepladder',
            'kaleidoscope_world_liquor:kaleidoscope_world_liquor_tab':
                'kaleidoscope_world_liquor:bombay_sapphire_gin'}
        expected = {}
        for root in (TAVERN, LIQUOR):
            for tab in c.load(root/c.PLAN)['tabs']:
                if tab.get('kind') == 'java_tab_extension':
                    continue
                java_icon = java_icons[tab['id']]
                representative = next(entry['bedrock'] for entry in tab['entries'] if entry['java'] == java_icon)
                self.assertEqual(tab['icon'], representative)
                if representative != java_icon:
                    self.assertTrue(tab['icon_gap'])
                expected[tab['group']] = representative
        seen = {}
        for root in (TAVERN, LIQUOR):
            for category in c.load(root/c.CATALOG)['minecraft:crafting_items_catalog']['categories']:
                for group in category['groups']:
                    if 'group_identifier' not in group:
                        continue
                    ident = group['group_identifier']
                    self.assertEqual(ident['icon'], expected[ident['name']])
                    value = (category['category_name'], ident['icon'])
                    if ident['name'] in seen:
                        self.assertEqual(value, seen[ident['name']])
                    seen[ident['name']] = value
        self.assertEqual(set(seen), set(expected))

    def test_color_order_matches_java_and_between_packs(self):
        t = c.load(TAVERN/c.PLAN)['tabs'][1]['entries']
        w = c.load(LIQUOR/c.PLAN)['tabs'][0]['entries']
        def short(rows):
            return [row['bedrock'].split(':', 1)[1] for row in rows]
        self.assertEqual([name for name in short(t) if name.endswith('_sofa')], [x+'_sofa' for x in COLORS])
        self.assertEqual([name for name in short(t) if name.endswith('_bar_stool')], [x+'_bar_stool' for x in COLORS])
        self.assertEqual([name for name in short(w) if name.startswith('bar_stool_')], ['bar_stool_'+x for x in COLORS])
        self.assertEqual([name for name in short(t) if name.startswith('string_lights_')],
                         ['string_lights_'+x for x in ['colorless', *COLORS]])

    def test_wild_vine_addition_and_java_freezer_position(self):
        t, w = c.entries(c.load(TAVERN/c.CATALOG)), c.entries(c.load(LIQUOR/c.CATALOG))
        self.assertEqual(t['kaleidoscope_tavern:wild_grapevine'], ('items', None))
        self.assertEqual(w['kaleidoscope_world_liquor:freezer'], ('items', 'kaleidoscope_world_liquor:itemGroup.main'))
        items = list(w)
        prefix = 'kaleidoscope_world_liquor:'
        self.assertEqual(items[items.index(prefix+'freezer')-1:items.index(prefix+'freezer')+2],
                         [prefix+'gin_tonic', prefix+'freezer', prefix+'custom_record'])

    def test_owner_titles_and_shared_extension_match_in_all_languages(self):
        for locale in c.LOCALES:
            shared = {}
            for root in (TAVERN, LIQUOR):
                lines = [line for line in (root/'runtime/RP/texts'/(locale+'.lang')).read_text().splitlines()
                         if line and not line.startswith('##')]
                keys = [line.split('=', 1)[0] for line in lines]
                self.assertEqual(len(keys), len(set(keys)))
                labels = dict(line.split('=', 1) for line in lines)
                for tab in c.load(root/c.PLAN)['tabs']:
                    self.assertEqual(labels[tab['group']], tab['labels'][locale])
                    if tab['group'] in shared:
                        self.assertEqual(labels[tab['group']], shared[tab['group']])
                    shared[tab['group']] = labels[tab['group']]

    def test_retired_use_groups_are_absent(self):
        for root in (TAVERN, LIQUOR):
            groups = {group for _, group in c.entries(c.load(root/c.CATALOG)).values() if group}
            self.assertEqual(groups, {tab['group'] for tab in c.load(root/c.PLAN)['tabs']})

    def test_build_and_validation_hooks_exist(self):
        self.assertIn('creative/catalog.py', (TAVERN/'tools/check_release.py').read_text())
        self.assertIn('creative/catalog.py', (LIQUOR/'tools/check_release.py').read_text())
        builder=(LIQUOR/'tools/build_port.py').read_text()
        if 'creative/catalog.py' not in builder:
            # The reviewed wall-record normalizer wraps the byte-preserved
            # converter. Verify an executable delegation, not a comment match.
            tree=ast.parse(builder)
            calls=[node for node in ast.walk(tree) if isinstance(node,ast.Call)]
            self.assertTrue(any(
                ast.unparse(call.func)=='runpy.run_path'
                and call.args and ast.unparse(call.args[0])=="str(tools / '_build_port_source.py')"
                and any(k.arg=='run_name' and isinstance(k.value,ast.Constant) and k.value.value=='__main__' for k in call.keywords)
                for call in calls), 'Converter wrapper must execute its pinned source')
            builder=(LIQUOR/'tools/_build_port_source.py').read_text()
        self.assertIn('creative/catalog.py',builder)

class HistoricalProjectionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        spec = importlib.util.spec_from_file_location('creative_history', Path(__file__).with_name('historical.py'))
        cls.module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(cls.module)

    def test_current_generation_changes_only_menu_metadata(self):
        for root in (TAVERN, LIQUOR):
            for path, content in c.planned(root).items():
                relative = path.relative_to(root).as_posix()
                if not relative.startswith(('runtime/BP/items/', 'runtime/BP/blocks/')):
                    continue
                current, generated = c.load(path), json.loads(content)
                kind = 'minecraft:item' if '/items/' in relative else 'minecraft:block'
                current[kind]['description'].pop('menu_category')
                generated[kind]['description'].pop('menu_category')
                self.assertEqual(current, generated, relative)

    def legacy_fixture(self, root):
        path = 'runtime/BP/items/white_bar_stool.json'
        value = c.load(TAVERN/path)
        reference = c.load(TAVERN/'data/creative-legacy-menus.json')
        before = next(row['menu_category'] for row in reference['groups'] if path in row['paths'])
        taxonomy = c.load(TAVERN/'tools/creative/groups.json')
        group = taxonomy['groups']['stools']
        value['minecraft:item']['description']['menu_category'] = {
            **before, 'category': group['category'], 'group': group['name']}
        put(root, 'data/creative-legacy-menus.json', {'schema': 1, 'groups': [
            {'menu_category': before, 'paths': [path]}]})
        put(root, 'data/creative-decoration-groups.json', {'namespace': 'kaleidoscope_tavern',
                                                       'groups': {'stools': ['white_bar_stool']}})
        put(root, path, value)
        return path, value, before

    def test_historical_projection_preserves_body_and_restores_reviewed_menu(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            path, value, before = self.legacy_fixture(root)
            expected = copy.deepcopy(value)
            expected['minecraft:item']['description']['menu_category'] = before
            self.assertEqual(json.loads(self.module.LegacyMenuProjection(root).read_bytes(root/path)), expected)

    def test_unreviewed_menu_change_is_not_masked(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            path, value, _ = self.legacy_fixture(root)
            value['minecraft:item']['description']['menu_category']['is_hidden_in_commands'] = True
            put(root, path, value)
            with self.assertRaisesRegex(ValueError, 'Unreviewed menu'):
                self.module.LegacyMenuProjection(root).read_bytes(root/path)

    def test_gameplay_changes_still_change_historical_bytes(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            path, value, _ = self.legacy_fixture(root)
            before = self.module.LegacyMenuProjection(root).read_bytes(root/path)
            value['minecraft:item']['components']['test:accidental_gameplay_change'] = True
            put(root, path, value)
            after = self.module.LegacyMenuProjection(root).read_bytes(root/path)
            self.assertNotEqual(after, before)
            self.assertTrue(json.loads(after)['minecraft:item']['components']['test:accidental_gameplay_change'])

    def test_native_pick_projection_preserves_body_and_rejects_unreviewed_change(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            path = 'runtime/BP/items/grass_sandwich_board.json'
            value = c.load(TAVERN/path)
            before = next(row['menu_category'] for row in c.load(TAVERN/'data/creative-legacy-menus.json')['groups']
                          if path in row['paths'])
            plan = c.load(TAVERN/'data/creative-decoration-groups.json')
            alias = next(alias for alias, items in plan['groups'].items() if 'grass_sandwich_board' in items)
            taxonomy = c.load(TAVERN/'tools/creative/groups.json')
            group = {**taxonomy['existing_groups'], **taxonomy['groups']}[alias]
            pick = c.load(TAVERN/'data/creative-pick-native-history.json')['items'][path]
            value['minecraft:item']['description']['menu_category'] = {
                **before, 'category': group['category'], 'group': group['name']}
            value['minecraft:item']['components']['minecraft:block_placer'] = copy.deepcopy(pick['after'])
            put(root, path, value)
            put(root, 'data/creative-legacy-menus.json', {'schema': 1, 'groups': [
                {'menu_category': before, 'paths': [path]}]})
            put(root, 'data/creative-decoration-groups.json', {'namespace': plan['namespace'],
                                                           'groups': {alias: ['grass_sandwich_board']}})
            put(root, 'data/creative-pick-native-history.json', {'items': {path: pick}})
            expected = copy.deepcopy(value)
            expected['minecraft:item']['description']['menu_category'] = before
            if pick['before'] is None:
                expected['minecraft:item']['components'].pop('minecraft:block_placer')
            else:
                expected['minecraft:item']['components']['minecraft:block_placer'] = pick['before']
            self.assertEqual(json.loads(self.module.LegacyMenuProjection(root).read_bytes(root/path)), expected)
            value['minecraft:item']['components']['minecraft:block_placer']['replace_block_item'] = False
            put(root, path, value)
            with self.assertRaisesRegex(ValueError, 'Unreviewed pick component change'):
                self.module.LegacyMenuProjection(root).read_bytes(root/path)

    def test_unaffected_asset_keeps_exact_bytes(self):
        projection = self.module.LegacyMenuProjection(TAVERN)
        # The T131 shaker item now has a reviewed offhand delta. Its original
        # PNG remains an unaffected binary asset and must never be rewritten by
        # the menu/native-pick or functional-history projections.
        path = TAVERN/'runtime/RP/textures/kaleidoscope_tavern_jar/item/shaker.png'
        self.assertEqual(projection.read_bytes(path), path.read_bytes())

if __name__ == '__main__':
    unittest.main(verbosity=2)
