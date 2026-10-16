"""Actual artifact/source and fresh-native boundaries; no Minecraft players."""
import copy
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import zipfile
from family_update import stable_author_validation as m
from family_update import workflow, cookery_cache_validation


class StableAuthorValidationTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory();self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        m.artifact_members.cache_clear();self.addCleanup(m.artifact_members.cache_clear)

    def artifact(self, mutation=None):
        names = ['stable-author-functional.json', 'stable-author-functional.log',
                 'cookery-cache-functional.json', 'cookery-cache-functional.tap',
                 'cookery-guide-functional.json', 'cookery-guide-functional.tap',
                 'saturation-scheduling-functional.json', 'saturation-scheduling-functional.log']
        raw = io.BytesIO()
        with zipfile.ZipFile(raw, 'w') as archive:
            for name in names:archive.writestr(name, b'exact original source evidence')
        data = raw.getvalue()
        records = {
            'repos/' + m.REPOSITORY: {'id': m.REPOSITORY_ID, 'full_name': m.REPOSITORY, 'private': True},
            f'repos/{m.REPOSITORY}/actions/runs/7': {'repository': {'id': m.REPOSITORY_ID}, 'status': 'completed', 'conclusion': 'success',
                'head_sha': 'source', 'event': 'push', 'head_branch': 'main', 'path': '.github/workflows/canonical.yml'},
            f'repos/{m.REPOSITORY}/git/commits/source': {'tree': {'sha': 'whole-tree'}},
            f'repos/{m.REPOSITORY}/actions/artifacts/8': {'name': 'stable-author-functional', 'expired': False,
                'workflow_run': {'id': 7, 'head_sha': 'source'}, 'digest': 'sha256:' + m.digest(data)},
        }
        if mutation:mutation(records)
        m.artifact_members.cache_clear()
        with patch.object(workflow, 'gh_json', side_effect=lambda endpoint: records[endpoint]), \
                patch.object(cookery_cache_validation, 'private_ci_records', return_value=(['canonical'], [], [])), \
                patch.object(m.subprocess, 'check_output', return_value=data):
            return m.artifact_members(7, 8, 'source', 'whole-tree')

    def test_original_artifact_requires_main_success_source_tree_and_exact_digest(self):
        members, identity = self.artifact()
        self.assertEqual(len(members), 8)
        self.assertEqual(identity['artifact_id'], 8)
        run = f'repos/{m.REPOSITORY}/actions/runs/7'
        artifact = f'repos/{m.REPOSITORY}/actions/artifacts/8'
        commit = f'repos/{m.REPOSITORY}/git/commits/source'
        for endpoint, change in [(run, {'conclusion': 'failure'}), (run, {'event': 'pull_request'}),
                                 (run, {'head_sha': 'another'}), (run, {'head_branch': 'feature'}),
                                 (artifact, {'digest': 'sha256:forged'}), (artifact, {'workflow_run': {'id': 9, 'head_sha': 'source'}}),
                                 (commit, {'tree': {'sha': 'runtime-only-same-full-tree-different'}})]:
            with self.subTest(change=change), self.assertRaises(AssertionError):
                self.artifact(lambda records: records[endpoint].update(change))

    def test_sibling_rejects_paths_and_changed_raw_evidence(self):
        path = self.root / 'source.json';path.write_text('{}')
        log = self.root / 'source.log';log.write_text('actual source log')
        self.assertEqual(m.sibling(path, log.name, m.c.sha(log)), log)
        for name in ['../source.log', '/source.log', '.', '']:
            with self.subTest(name=name), self.assertRaises(AssertionError):m.sibling(path, name, m.c.sha(log))
        with self.assertRaises(AssertionError):m.sibling(path, log.name, 'forged')

    def test_regular_host_receipt_owner_and_extra_renderer_package_are_distinct(self):
        # family_bundle regular branch adds owner_version; its renderer branch
        # separately adds source_package_version to apply_renderer_extension.
        regular = {'owner_version': m.VERSION}
        renderer = {**regular, 'source_package_version': m.VERSION}
        m.private_receipt_version(regular, {'kind': 'cookery-guide-startup-repair'})
        m.private_receipt_version(renderer, {'kind': 'chinesefood-doll-renderer-cleanup'})
        for record, declaration in [
            ({'owner_version': [1, 0, 44]}, {'kind': 'cookery-guide-startup-repair'}),
            (regular, {'kind': 'chinesefood-doll-renderer-cleanup'}),
            ({**renderer, 'source_package_version': [1, 0, 44]}, {'kind': 'chinesefood-doll-renderer-cleanup'}),
            ({**renderer, 'source_package_version': [1, 0, 44]}, {'kind': 'cookery-guide-startup-repair'}),
        ]:
            with self.subTest(record=record, declaration=declaration), self.assertRaises((AssertionError, KeyError)):
                m.private_receipt_version(record, declaration)

    def test_prior_p43_or_p44_artifact_cannot_admit_new_paired_source(self):
        from family_update import workflow
        # Import before rebinding common so this module cannot retain fixture
        # globals if this focused test runs before its own test module.
        from family_update import extension_validation
        baseline = {'repository': m.LOGICAL, 'version': m.VERSION, 'source_trees': {}}
        (self.root / 'baseline.json').write_text(json.dumps(baseline))
        (self.root / '.repo-target.json').write_text(json.dumps({
            'repository': m.REPOSITORY, 'repository_id': m.REPOSITORY_ID, 'private': True}))
        proof = {'schema': 1, 'repository': m.LOGICAL, 'version': m.VERSION, 'source_trees': {},
                 'kind': 'stable_author_adaptation', 'profile': m.PROFILE,
                 'canonical_repository': m.REPOSITORY, 'canonical_repository_id': m.REPOSITORY_ID,
                 'previous_commit': m.PREVIOUS, 'test_command': ['python', 'tools/build_stable_author_evidence.py'],
                 'test_exit_code': 0, 'client': False, 'native_loading': False,
                 'simulated_players': False, 'production_ready': False}
        for change in [{'profile': 'senluo-stable-author-20261016'}, {'version': [1, 0, 43]},
                       {'profile': 'senluo-stable-author-20261016-p44'}, {'version': [1, 0, 44]}]:
            with self.subTest(change=change), \
                    patch.multiple(m.c, CONFIG={'extension_stable_validation': str(self.root / 'proof.json')}, EXTENSION=self.root), \
                    patch.object(m, 'local_report', return_value={**proof, **change}), \
                    patch.object(workflow, 'gh_json') as remote:
                with self.assertRaises(AssertionError):m.source_proof()
                remote.assert_not_called()

    def test_native_binds_only_this_candidates_fresh_first_and_restart(self):
        candidate = self.root / 'release-candidate';candidate.mkdir()
        receipt_file = candidate / 'family-receipt.json';receipt_file.write_text('{}')
        saved = self.root / 'saved-world-report.json';saved.write_text('{}')
        static = {'schema': 1, 'profile': m.PROFILE, 'version': m.VERSION,
                  'candidate_receipt_sha256': m.c.sha(receipt_file), 'affected_packs': {'pack': {'files': 'exact'}}}
        (self.root / 'stable-author-static-validation.json').write_text(json.dumps(static))
        evidence = {'candidate_receipt_sha256': static['candidate_receipt_sha256'], 'fresh_stopped_backup': True,
                    'existing_world_loaded': True, 'exact_files_checked': True, 'bds': True, 'saved_world_migration': True,
                    'client': False, 'simulated_players': False, 'test_only_overlays': [],
                    'runs': [{'phase': phase, 'ok': True, 'errors': [], 'real_player_connections': 0,
                              'player_records_unchanged': True, 'custom_container_inventories_retained': True,
                              'native_freezer_inputs_retained': True} for phase in ['first', 'restart']]}
        with patch.multiple(m.c, CONFIG={'extension_stable_validation': 'source'}, R=self.root, C=candidate), \
                patch.object(m, 'affected_packs', return_value=static['affected_packs']), \
                patch.object(m.c, 'atomic', side_effect=lambda path, data: path.write_text(json.dumps(data))):
            m.bind_native({}, evidence)
            actual = json.loads((self.root / 'stable-author-native-validation.json').read_text())
            self.assertEqual(actual['fresh_native'], m.c.report_ref(saved))
            self.assertFalse(actual['client'])
            for key, value in [('candidate_receipt_sha256', 'old'), ('fresh_stopped_backup', False),
                               ('client', True), ('test_only_overlays', ['old freezer probe']), ('runs', evidence['runs'][:1])]:
                changed = copy.deepcopy(evidence);changed[key] = value
                with self.subTest(key=key), self.assertRaises(AssertionError):m.bind_native({}, changed)
            changed = copy.deepcopy(evidence);changed['runs'][1]['native_freezer_inputs_retained'] = False
            with self.assertRaises(AssertionError):m.bind_native({}, changed)

    def test_changed_private_source_routes_to_new_profile(self):
        from family_update import extension_validation
        receipt = {'packs': [{'uuid': 'private', 'files': {'new': 'bytes'}, 'version': m.VERSION,
                             'source': {'owner': 'owned', 'repository': m.LOGICAL}}]}
        with patch.object(extension_validation, 'CONFIG', {'extension_stable_validation': 'source'}), \
                patch.object(m, 'verify_static', return_value=['actual new source report']) as verify:
            self.assertEqual(extension_validation.verify_extension(receipt, {}), ['actual new source report'])
            verify.assert_called_once_with(receipt, {})

    def test_stable_saturation_candidate_rejects_old_recipe_missing_pair_or_changed_files(self):
        from family_update import prospective_preserved_inputs as prospective
        recipe_path = self.root / m.RECIPE;recipe_path.parent.mkdir(parents=True);recipe_path.write_text('{}')
        proof = self.root / 'stable-author-functional.json';proof.write_text('{}')
        recipe = {'output_hashes': {side: {'manifest.json': side + '-manifest', 'unchanged': 'same'} for side in m.SAT_UUIDS}}
        selected = {'profile': m.SAT_PROFILE, 'version': m.VERSION, 'recipe': m.c.report_ref(recipe_path),
                    'source_validation': m.c.report_ref(proof), 'packs': {}}
        receipt = {'packs': []}
        for side, uid in m.SAT_UUIDS.items():
            data = {'uuid': uid, 'side': 'behavior' if side == 'BP' else 'resource', 'version': m.SAT_VERSION}
            selected['packs'][side] = data
            receipt['packs'].append({**data, 'source': {'owner': 'preserved'}, 'files': recipe['output_hashes'][side]})
        with patch.multiple(m.c, CONFIG={'extension_stable_validation': str(proof)}, EXTENSION=self.root), \
                patch.object(m, 'reviewed_profiles', return_value=({}, recipe)), patch.object(m, 'RECIPE_SHA', m.c.sha(recipe_path)):
            prospective.verify_candidate(receipt, selected)
            for kind in ['files', 'version', 'missing_pair', 'old_source']:
                value = copy.deepcopy(receipt);chosen = copy.deepcopy(selected)
                if kind == 'files':value['packs'][0]['files']['unchanged'] = 'unreviewed'
                elif kind == 'version':value['packs'][0]['version'] = [1, 5, 6]
                elif kind == 'missing_pair':chosen['packs'].pop('RP')
                else:chosen['source_validation']['sha256'] = 'old-P41-native-report'
                with self.subTest(kind=kind), self.assertRaises(AssertionError):prospective.verify_candidate(value, chosen)


if __name__ == '__main__':
    unittest.main()
