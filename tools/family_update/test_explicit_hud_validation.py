import copy
import unittest
from family_update.explicit_hud_validation import conserved_scope, PROVIDERS


class ConservedHudScope(unittest.TestCase):
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
        args = self.fixture()
        args[3]['dependencies'].pop()
        with self.assertRaises(AssertionError):
            conserved_scope(*args)


if __name__ == '__main__':
    unittest.main()
