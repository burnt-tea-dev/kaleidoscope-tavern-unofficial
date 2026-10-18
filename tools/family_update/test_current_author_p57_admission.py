"""P57 removes only reviewed AMW content; earlier source contracts stay exact."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from family_update import current_author_validation as current
from family_update import stable_author_validation as dispatch
import stable_host_profiles as stable
import doll_renderer_extension as renderer
import enamel_basin_extension as enamel
import held_geometry_extension as held
import host_extensions


class P57Admission(unittest.TestCase):
    def test_migration_targets_match_actual_current_renderer_output(self):
        root = Path(__file__).resolve().parents[2]
        migration = json.loads((root / 'family/identity-migrations/stable-author-20261018.json').read_text())
        project = next(row for row in migration['projects'] if row['project_id'] == 1683300)
        profile = stable.PROFILES['chinesefood-doll-renderer-p57']
        originals = [{'header': {'uuid': uid, 'name': 'original', 'version': profile['author_version']},
                      'modules': [{'version': profile['author_version']}],
                      'dependencies': [{'uuid': other, 'version': profile['author_version']}]}
                     for uid, other in [(profile['behavior_uuid'], profile['host_uuid']),
                                        (profile['host_uuid'], profile['behavior_uuid'])]]
        manifests = renderer.patch_manifests(*originals, profile['version'], profile['owner_version'], profile)
        for side, manifest in zip(['behavior', 'resource'], manifests):
            planned = next(row for row in project['packs'] if row['side'] == side)
            self.assertEqual(planned['new_uuid'], manifest['header']['uuid'])
            self.assertEqual(planned['new_version'], manifest['header']['version'])

    def test_migration_binds_the_reviewed_enamel_repair_output(self):
        root = Path(__file__).resolve().parents[2]
        migration = json.loads((root / 'family/identity-migrations/stable-author-20261018.json').read_text())
        rule = next(row for row in migration['block_states']['blocks']
                    if row['identifier'] == 'kaleidoscope_cookery:enamel_basin')
        profile = stable.PROFILES['cookery-enamel-basin-lid-repair-p57']
        relative = rule['path'][3:]
        self.assertEqual(rule['before_sha256'], profile['original_files'][relative])
        self.assertEqual(rule['after_sha256'], profile['patched_files'][relative])
        self.assertEqual(rule['conversion'], 'identity')
        self.assertEqual(rule['before_states'], rule['after_states'])

    def fixture(self):
        owned = {
            'previous_files': {
                'BP': {'manifest.json': 'before', 'scripts/compat/host.js': 'kept', 'items/fauna.json': 'removed'},
                'RP': {'manifest.json': 'before-rp', 'entity/inscription.json': 'cf-text', 'textures/fauna.png': 'removed'},
            },
            'files': {
                'BP': {'manifest.json': 'after', 'scripts/compat/host.js': 'kept'},
                'RP': {'manifest.json': 'after-rp', 'entity/inscription.json': 'cf-text'},
            },
            'exact_changed_paths': ['runtime/BP/manifest.json', 'runtime/RP/manifest.json'],
            'added_paths': [],
            'retired_paths': ['runtime/BP/items/fauna.json', 'runtime/RP/textures/fauna.png'],
        }
        catalog = {key: deepcopy(owned[key]) for key in ['exact_changed_paths', 'added_paths', 'retired_paths']}
        return owned, catalog

    def validate(self, owned, catalog, version=57):
        with patch.object(current.c, 'CONFIG', {'extension_stable_profile': 'current-author-p' + str(version)}):
            current.validate_owned_conservation(owned, catalog)

    def test_explicit_settings_keep55_and56_and_admit57_but_never58(self):
        for version in [55, 56, 57]:
            with self.subTest(version=version), patch.object(current.c, 'CONFIG', {'extension_stable_profile': 'current-author-p' + str(version)}):
                self.assertTrue(current.selected())
                self.assertEqual(current.settings(), ([1, 0, version], 'senluo-stable-author-20261018-p' + str(version), 'current_author_p' + str(version)))
        with patch.object(current.c, 'CONFIG', {'extension_stable_profile': 'current-author-p58'}):
            self.assertFalse(current.selected())
            with self.assertRaisesRegex(AssertionError, 'Unsupported'):
                current.settings()

    def test_exact_catalog_removal_keeps_cf_helper_and_inscription_bytes(self):
        owned, catalog = self.fixture()
        self.validate(owned, catalog)
        changed = deepcopy(owned)
        changed['files']['BP']['scripts/compat/host.js'] = 'unreviewed-helper'
        changed['exact_changed_paths'].insert(1, 'runtime/BP/scripts/compat/host.js')
        with self.assertRaisesRegex(AssertionError, 'changed content differs'):
            self.validate(changed, catalog)
        changed = deepcopy(owned)
        del changed['files']['RP']['entity/inscription.json']
        changed['retired_paths'].insert(1, 'runtime/RP/entity/inscription.json')
        with self.assertRaisesRegex(AssertionError, 'retired content differs'):
            self.validate(changed, catalog)

    def test_added_reenabled_content_and_inaccurate_producer_claims_fail(self):
        owned, catalog = self.fixture()
        changed = deepcopy(owned)
        changed['files']['BP']['items/new_fauna.json'] = 'unreviewed'
        changed['added_paths'] = ['runtime/BP/items/new_fauna.json']
        with self.assertRaisesRegex(AssertionError, 'cannot add'):
            self.validate(changed, catalog)
        changed = deepcopy(owned)
        changed['retired_paths'] = []
        with self.assertRaisesRegex(AssertionError, 'retired paths differ'):
            self.validate(changed, catalog)

    def test_empty_duplicate_unsorted_or_unsafe_retirement_catalog_fails(self):
        owned, catalog = self.fixture()
        for paths in [[], catalog['retired_paths'] * 2, list(reversed(catalog['retired_paths'])), ['runtime/BP/../items/fauna.json']]:
            changed = deepcopy(catalog)
            changed['retired_paths'] = paths
            with self.subTest(paths=paths), self.assertRaises(AssertionError):
                self.validate(owned, changed)

    def test_historical55_and56_retain_their_own_add_remove_contract(self):
        owned, _ = self.fixture()
        owned['files']['BP']['scripts/new-host.js'] = 'new-host'
        owned['added_paths'] = ['runtime/BP/scripts/new-host.js']
        for version in [55, 56]:
            with self.subTest(version=version):
                self.validate(owned, {}, version)
                wrong = deepcopy(owned)
                wrong['retired_paths'] = []
                with self.assertRaisesRegex(AssertionError, 'retired paths differ'):
                    self.validate(wrong, {}, version)

    def test_all_current57_dispatches_reach_current_validator(self):
        config = {'extension_stable_profile': 'current-author-p57', 'extension_stable_validation': 'fixture'}
        for name, args in [('verify_static', ({}, {})), ('evidence_paths', (False,)), ('bind_native', ({}, {})), ('verify_installation', ({},))]:
            with self.subTest(name=name), patch.object(current.c, 'CONFIG', config), patch.object(current, name, return_value='current57') as target:
                self.assertEqual(getattr(dispatch, name)(*args), 'current57')
                target.assert_called_once_with(*args)

    def test_current_profile_requires_exact57_catalog_not_future_admission(self):
        with patch.object(stable, 'match_stable_profile', return_value={'admission': 'current-author-p57'}):
            self.assertIsNotNone(stable.current_author_profile({}))
        with patch.object(stable, 'match_stable_profile', return_value={'admission': 'current-author-p58'}):
            self.assertIsNone(stable.current_author_profile({}))

    def test_geometry_and_enamel_owners_match_exact57_profile(self):
        owner = {'repository': 'local/senluo-amw-cuisine', 'version': [1, 0, 57]}
        spec = {'owner_version': [1, 0, 57]}
        for module, name in [(held, 'validate_held_geometry_owner'), (enamel, 'validate_enamel_basin_owner')]:
            with self.subTest(module=module.__name__), patch.object(module, 'current_author_profile', return_value={'owner_version': [1, 0, 57]}):
                getattr(module, name)(owner, spec)
                with self.assertRaises(ValueError):
                    getattr(module, name)({**owner, 'version': [1, 0, 58]}, {'owner_version': [1, 0, 58]})

    def test_renderer57_keeps_reviewed_repair_label_and_rejects_owner_relabel(self):
        profile = {'admission': 'current-author-p57', 'owner_version': [1, 0, 57], 'version': [1, 0, 10657],
                   'author_version': [1, 0, 6], 'behavior_uuid': 'fixture-bp', 'host_uuid': 'fixture-rp',
                   'manifest_names': {'BP': 'BP repair1.0.55', 'RP': 'RP repair1.0.55'}}
        originals = [{'header': {'uuid': uid, 'name': 'original', 'version': [1, 0, 6]},
                      'modules': [{'version': [1, 0, 6]}],
                      'dependencies': [{'uuid': other, 'version': [1, 0, 6]}]}
                     for uid, other in [('fixture-bp', 'fixture-rp'), ('fixture-rp', 'fixture-bp')]]
        before = deepcopy(originals)
        result = renderer.patch_manifests(*originals, [1, 0, 10657], [1, 0, 57], profile)
        self.assertEqual(originals, before)
        for side, manifest in zip(['BP', 'RP'], result):
            self.assertEqual(manifest['header']['name'], profile['manifest_names'][side])
            self.assertEqual(manifest['header']['version'], [1, 0, 10657])
        with self.assertRaisesRegex(ValueError, 'exact owner release'):
            renderer.patch_manifests(*originals, [1, 0, 10657], [1, 0, 56], profile)

    def test_salt_removal57_still_requires_exact_companion_and_owner(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            owned, host = root / 'owned', root / 'host'
            owned.mkdir()
            recipe = host / 'recipes/vanilla_cooking/salt_smelting.json'
            recipe.parent.mkdir(parents=True)
            recipe.write_bytes(b'synthetic recipe')
            removal = {'recipes/vanilla_cooking/salt_smelting.json': hashlib.sha256(recipe.read_bytes()).hexdigest()}
            manifest = {'header': {'version': [1, 0, 57]}, 'dependencies': [{'uuid': '5e121bf2-1d2d-4da4-be15-cffc5f216d94', 'version': [1, 2, 0]}]}
            (owned / 'manifest.json').write_text(json.dumps(manifest))
            spec = {'kind': 'chinesefood-reviewed-repairs', 'archive_sha256': 'dea708dd6443ea30d23e5791860a50181e8eeb560dcd7ec5a8e80fe22743e659', 'removed_files': removal}
            with patch.object(host_extensions, 'REVIEWED_SALT_REMOVAL', removal):
                self.assertEqual(host_extensions.validate_recipe_removals(spec, owned, host, {'admission': 'current-author-p57'}), removal)
                with self.assertRaisesRegex(ValueError, 'exact reviewed'):
                    host_extensions.validate_recipe_removals(spec, owned, host, {'admission': 'current-author-p58'})
                manifest['header']['version'] = [1, 0, 56]
                (owned / 'manifest.json').write_text(json.dumps(manifest))
                with self.assertRaisesRegex(ValueError, 'companion'):
                    host_extensions.validate_recipe_removals(spec, owned, host, {'admission': 'current-author-p57'})
            self.assertEqual(recipe.read_bytes(), b'synthetic recipe')


if __name__ == '__main__':
    unittest.main()
