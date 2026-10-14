import copy
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from family_update import explicit_hud_validation as module
from family_update.explicit_hud_validation import conserved_scope, PROVIDERS


class ConservedHudScope(unittest.TestCase):
    def stable_fixture(self, side='RP'):
        old = {'manifest.json': 'old', 'scripts/owned.js': 'kept', 'textures/owned.png': 'kept'}
        if side == 'RP':
            old.update({'ui/hud_screen.json': 'old-host', 'ui/_global_variables.json': 'kept'})
        new = {**old, 'manifest.json': 'new'}
        manifest = {'header': {'version': [1, 0, 36], 'name': 'Owned 1.0.36'},
                    'modules': [{'version': [1, 0, 36]}],
                    'dependencies': [{'uuid': 'paired', 'version': [1, 0, 36]}]}
        if side == 'RP':
            manifest['dependencies'] += [
                {'uuid': uid, 'version': copy.deepcopy(module.STABLE_PROVIDER_VERSIONS[uid][0])
                 if uid in module.STABLE_PROVIDER_VERSIONS else [1, 0, 1]} for uid in sorted(PROVIDERS)]
            new['ui/hud_screen.json'] = 'new-host'
        changed = copy.deepcopy(manifest)
        changed['header'].update(version=[1, 0, 37], name='Owned 1.0.37')
        changed['modules'][0]['version'] = [1, 0, 37]
        changed['dependencies'][0]['version'] = [1, 0, 37]
        for dependency in changed['dependencies']:
            if dependency['uuid'] in module.STABLE_PROVIDER_VERSIONS:
                dependency['version'] = copy.deepcopy(module.STABLE_PROVIDER_VERSIONS[dependency['uuid']][1])
        hud = {'namespace': 'hud', 'root_panel': {'type': 'panel', 'controls': []},
               'kt_family_empty': copy.deepcopy(module.EMPTY_CONTROL)}
        for leaf in module.ACTIONBAR_LEAVES:
            hud[leaf] = {'$kt_family_actionbar_text': '$actionbar_text', 'visible': 'prior-filter'}
        repaired = copy.deepcopy(hud)
        for leaf in module.ACTIONBAR_LEAVES:
            repaired[leaf]['visible'] = module.STABLE_ACTIONBAR_FILTER
        return old, new, manifest, changed, side, {'paired'}, [1, 0, 37], hud, repaired

    def test_p37_admits_only_both_native_filters_and_exact_provider_versions(self):
        conserved_scope(*self.stable_fixture())
        conserved_scope(*self.stable_fixture('BP'))
        self.assertEqual(module.PROFILES[(1, 0, 37)],
                         ('aaeaacf28883d1aeb4a21cdde0dd0aa9e4ab5f56', [1, 0, 36]))

    def test_p37_rejects_other_ui_gameplay_assets_and_manifest_changes(self):
        for label in ['filter', 'other-leaf', 'empty', 'root', 'global', 'gameplay', 'texture', 'addition', 'removal', 'manifest']:
            with self.subTest(change=label):
                args = self.stable_fixture()
                if label == 'filter':
                    args[-1][module.ACTIONBAR_LEAVES[1]]['visible'] = 'wrong-filter'
                elif label == 'other-leaf':
                    args[-1][module.ACTIONBAR_LEAVES[0]]['$kt_family_actionbar_text'] = '$foreign_text'
                elif label == 'empty':
                    args[-1]['kt_family_empty']['size'] = [1, 1]
                elif label == 'root':
                    args[-1]['root_panel']['controls'].append({'foreign': {'type': 'panel'}})
                elif label in ['global', 'gameplay', 'texture']:
                    key = {'global': 'ui/_global_variables.json', 'gameplay': 'scripts/owned.js', 'texture': 'textures/owned.png'}[label]
                    args[1][key] = 'changed'
                elif label == 'addition':
                    args[1]['ui/foreign.json'] = 'new'
                elif label == 'removal':
                    args[1].pop('textures/owned.png')
                else:
                    args[3]['header']['description'] = 'changed'
                with self.assertRaises(AssertionError):
                    conserved_scope(*args)

    def test_p37_rejects_wrong_missing_extra_or_foreign_provider_updates(self):
        for label in ['wrong-owned', 'unchanged-owned', 'changed-foreign', 'missing', 'extra', 'paired']:
            with self.subTest(change=label):
                args = self.stable_fixture()
                dependencies = args[3]['dependencies']
                owned = next(row for row in dependencies if row['uuid'] in module.STABLE_PROVIDER_VERSIONS)
                if label == 'wrong-owned':
                    owned['version'] = [9, 0, 0]
                elif label == 'unchanged-owned':
                    owned['version'] = module.STABLE_PROVIDER_VERSIONS[owned['uuid']][0]
                elif label == 'changed-foreign':
                    next(row for row in dependencies if row['uuid'] in PROVIDERS - module.STABLE_PROVIDER_VERSIONS.keys())['version'] = [9, 0, 0]
                elif label == 'missing':
                    dependencies.remove(owned)
                elif label == 'extra':
                    dependencies.append({'uuid': 'foreign', 'version': [1, 0, 1]})
                else:
                    dependencies[0]['version'] = [1, 0, 36]
                with self.assertRaises(AssertionError):
                    conserved_scope(*args)

    def fallback_fixture(self):
        old = {'manifest.json': 'old', 'scripts/owned.js': 'kept',
               'ui/hud_screen.json': 'old-host', 'ui/_global_variables.json': 'kept'}
        new = {**old, 'manifest.json': 'new', 'ui/hud_screen.json': 'new-host'}
        manifest = {'header': {'version': [1, 0, 35], 'name': 'Owned 1.0.35'},
                    'modules': [{'version': [1, 0, 35]}],
                    'dependencies': [{'uuid': 'paired', 'version': [1, 0, 35]}] +
                                    [{'uuid': uid, 'version': [1, 0, 1]} for uid in PROVIDERS]}
        changed = copy.deepcopy(manifest)
        changed['header'].update(version=[1, 0, 36], name='Owned 1.0.36')
        changed['modules'][0]['version'] = [1, 0, 36]
        changed['dependencies'][0]['version'] = [1, 0, 36]
        hud = {'namespace': 'hud', 'root_panel': {'type': 'panel', 'controls': []}}
        repaired = copy.deepcopy(hud)
        repaired['kt_family_empty'] = module.EMPTY_CONTROL
        return old, new, manifest, changed, 'RP', {'paired'}, [1, 0, 36], hud, repaired

    def test_p36_admits_only_the_fallback_and_paired_identity(self):
        conserved_scope(*self.fallback_fixture())

    def test_p36_rejects_other_ui_gameplay_or_dependency_changes(self):
        args = self.fallback_fixture()
        args[-1]['root_panel']['type'] = 'image'
        with self.assertRaises(AssertionError):
            conserved_scope(*args)
        args = self.fallback_fixture()
        args[1]['scripts/owned.js'] = 'changed'
        with self.assertRaises(AssertionError):
            conserved_scope(*args)
        args = self.fallback_fixture()
        args[3]['dependencies'][-1]['version'] = [9, 0, 0]
        with self.assertRaises(AssertionError):
            conserved_scope(*args)

    def fixture(self, side='RP'):
        old = {'manifest.json': 'old', 'scripts/owned.js': 'kept'}
        new = {**old, 'manifest.json': 'new'}
        if side == 'RP':
            new.update({'ui/hud_screen.json': 'host', 'ui/_global_variables.json': 'providers'})
        manifest = {'header': {'version': [1, 0, 34], 'name': 'Owned 1.0.34'},
                    'modules': [{'version': [1, 0, 34]}], 'dependencies': [{'uuid': 'paired', 'version': [1, 0, 34]}]}
        changed = copy.deepcopy(manifest)
        changed['header'].update(version=[1, 0, 35], name='Owned 1.0.35')
        changed['modules'][0]['version'] = [1, 0, 35]
        changed['dependencies'][0]['version'] = [1, 0, 35]
        if side == 'RP':
            changed['dependencies'] += [{'uuid': uid, 'version': [1, 0, 1]} for uid in PROVIDERS]
        return old, new, manifest, changed, side, {'paired'}

    def test_accepts_only_exact_identity_and_dependency_bound_ui_scope(self):
        conserved_scope(*self.fixture())
        conserved_scope(*self.fixture('BP'))

    def test_rejects_gameplay_change_and_missing_hud_provider(self):
        args = self.fixture()
        args[1]['scripts/owned.js'] = 'changed'
        with self.assertRaises(AssertionError):
            conserved_scope(*args)

    def test_static_source_validation_calls_the_real_ci_adapter_signature(self):
        # Synthetic source context stops at the CI boundary; this catches an
        # integration error that the manifest-only tests cannot exercise.
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'baseline.json').write_text(json.dumps({'repository': module.PRIVATE, 'version': module.VERSION}))
            log = root / 'synthetic.log'
            log.write_text('synthetic source fixture only')
            proof = {'kind': 'explicit_family_hud', 'canonical_repository': module.REPOSITORY,
                     'canonical_repository_id': 1406868911, 'git_tree': 'synthetic-tree',
                     'test_exit_code': 0, 'test_command': ['python', 'tools/test_family_hud_host.py'],
                     'native_controls': 29, 'literal_owned_roots': 2,
                     'native_and_amw_conserved': True, 'dependency_bound': True,
                     'native_loading': False, 'client': False, 'simulated_players': False, 'production_ready': False,
                     'test_log': {'name': log.name, 'sha256': module.c.sha(log)}}
            path = root / 'synthetic.json'
            path.write_text(json.dumps(proof))
            pull = {'merged_at': 'synthetic-time', 'state': 'closed', 'base': {'ref': 'main'}, 'head': {'sha': 'synthetic-head'}}
            for version in [module.VERSION, [1, 0, 36], [1, 0, 37]]:
                with self.subTest(version=version):
                    (root / 'baseline.json').write_text(json.dumps({'repository': module.PRIVATE, 'version': version}))
                    proof.update(typed_empty_fallback=True, fallback_base='hud.kt_family_empty')
                    path.write_text(json.dumps(proof))
                    with patch.multiple(module.c, CONFIG={'extension_hud_validation': str(path), 'extension_hud_pull_request': 22}, EXTENSION=root), \
                         patch.object(module.c, 'git', return_value='synthetic-tree'), \
                         patch('family_update.extension_validation.source_binding', return_value={'current_source_tree_oid': 'synthetic-tree'}), \
                         patch('family_update.workflow.gh_json', return_value=pull), \
                         patch('family_update.cookery_cache_validation.private_ci_records', autospec=True, side_effect=RuntimeError('CI boundary reached')) as ci:
                        with self.assertRaisesRegex(RuntimeError, 'CI boundary reached'):
                            module.verify_static({}, {})
                        ci.assert_called_once_with(module.REPOSITORY, 'synthetic-head')
                        if version != module.VERSION:
                            proof['typed_empty_fallback'] = False
                            path.write_text(json.dumps(proof))
                            ci.reset_mock()
                            with self.assertRaises(AssertionError):
                                module.verify_static({}, {})
                            ci.assert_not_called()
        args = self.fixture()
        args[3]['dependencies'].pop()
        with self.assertRaises(AssertionError):
            conserved_scope(*args)


if __name__ == '__main__':
    unittest.main()
