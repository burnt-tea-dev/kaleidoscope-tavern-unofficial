"""Current module ownership and preserved-input receipt boundaries.

Synthetic tiny sources contain no author/private implementation. The private
source CI separately executes the real pinned host-module differentials.
"""
import contextlib
import copy
import hashlib
import io
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

import cookery_station_extension as station
import family_bundle


class CurrentStationOwnership(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(); self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name); self.host = self.root / 'host'; self.owned = self.root / 'owned'
        self.host.mkdir(); self.owned.mkdir()
        self.author = b'const synthetic = 1;\n'; self.output = b'const synthetic = 2;\n'
        self.helper = b'export const syntheticHelper = true;\n'
        self.author_sha = station.digest(self.author); self.output_sha = station.digest(self.output)
        self.patch_author = patch.object(station, 'AUTHOR', self.author_sha); self.patch_author.start(); self.addCleanup(self.patch_author.stop)
        self.modules = {f'scripts/api/module_{i}.js': station.digest(('module-' + str(i)).encode()) for i in range(13)}
        self.copies = {name: {'source': name.replace('/api/', '/host_api/'), 'sha256': value} for name, value in self.modules.items()}
        self.api = {'id': 'fixture:public-api', 'version': [0, 2, 13],
                    'original_files': {station.TARGET: self.author_sha, 'scripts/other.js': 'old-other'},
                    'patched_files': {station.TARGET: 'b' * 64, 'scripts/other.js': 'new-other'},
                    'imports': {station.TARGET: 'station-import', 'scripts/other.js': 'other-import'},
                    'insertions': [{'path': station.TARGET, 'anchor': 'a'}, {'path': 'scripts/other.js', 'anchor': 'b'}],
                    'copies': {record['source']: name for name, record in self.copies.items()}}
        retained = {'id': self.api['id'], 'version': self.api['version'], 'target': station.TARGET,
                    'author_sha256': self.author_sha, 'prior_output_sha256': 'b' * 64, 'retained_modules': self.modules}
        self.spec = {'id': station.IDENTITY, 'version': [1, 0, 1],
                     'original_files': {station.TARGET: self.author_sha}, 'patched_files': {station.TARGET: self.output_sha},
                     'imports': {station.TARGET: ''}, 'insertions': [],
                     'text_replacements': [{'path': station.TARGET, 'before': 'synthetic = 1', 'after': 'synthetic = 2'}],
                     'helper_sha256': station.digest(self.helper), 'owner_handoff': retained,
                     'expires': '2026-11-24', 'authorization': 'fixture', 'feedback': 'fixture', 'removal_condition': 'fixture'}
        self.profile = {key: self.spec[key] for key in ('id', 'version', 'original_files', 'patched_files')} | {
            'copies': {station.INSTALLED_HELPER: {'source': station.HELPER, 'sha256': station.digest(self.helper)}}}
        self.binding = {'owner_id': station.IDENTITY, 'owner_repository': station.LOGICAL_PRIVATE,
                        'owner_commit': 'a' * 40, 'owner_version': [1, 0, 63], 'spec_sha256': 'c' * 64,
                        'input_sha256': self.author_sha, 'output_sha256': self.output_sha,
                        'helper_target': station.INSTALLED_HELPER, 'helper_sha256': station.digest(self.helper), 'retained_api': retained}
        self.expected_api = station.public_api_receipt(self.api, self.copies)
        active = station.active_api_declaration(self.api)
        self.api_receipt = station.public_api_receipt(active, self.copies) | {'delegated_files': {station.TARGET: self.binding}}
        self.owner_receipt = copy.deepcopy(self.profile) | {'owner_handoff': self.binding, 'repository': station.LOGICAL_PRIVATE,
                            'commit': 'a' * 40, 'spec_sha256': 'c' * 64, 'working_candidate': False, 'owner_version': [1, 0, 63]}
        self.files = self.modules | {station.TARGET: self.output_sha, station.INSTALLED_HELPER: station.digest(self.helper)}

    def test_only_the_current_target_is_delegated_and_original_declaration_is_immutable(self):
        original = copy.deepcopy(self.api)
        plan = {'api': self.api, 'delegated': False}
        active = station.delegated_api_spec(self.api, plan)
        self.assertNotIn(station.TARGET, active['original_files']); self.assertNotIn(station.TARGET, active['patched_files'])
        self.assertNotIn(station.TARGET, active['imports']); self.assertEqual(active['copies'], self.api['copies'])
        self.assertEqual(active['insertions'], [self.api['insertions'][1]])
        self.assertEqual(self.api, original)
        with self.assertRaisesRegex(ValueError, 'twice'): station.delegated_api_spec(self.api, plan)

    def test_unaffected_api_files_and_all_helpers_are_required(self):
        station.validate_public_delegation(self.api_receipt, self.expected_api, self.binding)
        for field in ('original_files', 'patched_files', 'copies'):
            changed = copy.deepcopy(self.api_receipt); changed[field].pop(next(iter(changed[field])))
            with self.subTest(field=field), self.assertRaises(ValueError): station.validate_public_delegation(changed, self.expected_api, self.binding)
        changed = copy.deepcopy(self.api_receipt); changed['delegated_files'][station.TARGET]['retained_api']['retained_modules'].pop(next(iter(self.modules)))
        with self.assertRaisesRegex(ValueError, 'modules differ'): station.validate_public_delegation(changed, self.expected_api)

    def test_forged_or_extra_target_delegation_is_rejected(self):
        for mutate in (lambda x: x['delegated_files'].update({'scripts/other.js': self.binding}),
                       lambda x: x['delegated_files'][station.TARGET].update(owner_commit='not-a-commit'),
                       lambda x: x['delegated_files'][station.TARGET].update(owner_repository='foreign'),
                       lambda x: x['patched_files'].update({station.TARGET: 'b' * 64})):
            changed = copy.deepcopy(self.api_receipt); mutate(changed)
            with self.assertRaises(ValueError): station.validate_public_delegation(changed, self.expected_api)

    def pair(self, api=None, owner=None, files=None):
        return station.validate_station_receipt_pair(self.spec, self.profile, self.api, api or self.api_receipt,
                owner or self.owner_receipt, files or self.files, owner_commit='a' * 40, owner_version=[1, 0, 63], spec_sha256='c' * 64)

    def test_pending_claim_is_not_a_completed_owner_pair(self):
        self.pair()
        for field, value in [('commit', 'd' * 40), ('spec_sha256', 'e' * 64), ('working_candidate', True),
                             ('owner_handoff', {}), ('copies', {}), ('owner_version', [1, 0, 62])]:
            with self.subTest(field=field), self.assertRaises(ValueError): self.pair(owner={**self.owner_receipt, field: value})
        for name in (station.TARGET, station.INSTALLED_HELPER, *self.modules):
            with self.subTest(file=name), self.assertRaises(ValueError): self.pair(files={**self.files, name: 'f' * 64})

    def plan(self):
        return {'spec': self.spec, 'api': self.api, 'profile': self.profile, 'binding': self.binding, 'delegated': True, 'completed': False}

    def prepare_files(self):
        target = self.host / station.TARGET; target.parent.mkdir(parents=True); target.write_bytes(self.author)
        helper = self.owned / station.HELPER; helper.parent.mkdir(parents=True); helper.write_bytes(self.helper)
        for i, name in enumerate(self.modules):
            p = self.host / name; p.parent.mkdir(parents=True, exist_ok=True); p.write_bytes(('module-' + str(i)).encode())
        return target

    def test_one_clean_input_produces_current_output_once(self):
        target = self.prepare_files(); plan = self.plan()
        source = {'owner': 'upstream_extended', 'archive_sha256': station.ARCHIVE, 'reviewed_extensions': [self.api_receipt]}
        proof = station.apply_station_extension(self.spec, self.owned, self.host, source, plan)
        self.assertEqual(target.read_bytes(), self.output)
        self.assertEqual((self.host / station.INSTALLED_HELPER).read_bytes(), self.helper)
        self.assertEqual(proof['owner_handoff'], self.binding)
        with self.assertRaisesRegex(ValueError, 'repeated'): station.apply_station_extension(self.spec, self.owned, self.host, source, plan)

    def test_changed_api_helper_fails_before_the_station_file_is_written(self):
        target = self.prepare_files(); (self.host / next(iter(self.modules))).write_bytes(b'changed')
        source = {'owner': 'upstream_extended', 'archive_sha256': station.ARCHIVE, 'reviewed_extensions': [self.api_receipt]}
        with self.assertRaisesRegex(ValueError, 'helper changed'): station.apply_station_extension(self.spec, self.owned, self.host, source, self.plan())
        self.assertEqual(target.read_bytes(), self.author); self.assertFalse((self.host / station.INSTALLED_HELPER).exists())

    def test_the_old_public_output_cannot_be_used_as_a_second_patch_layer(self):
        target = self.prepare_files(); target.write_bytes(b'old public patched output')
        source = {'owner': 'upstream_extended', 'archive_sha256': station.ARCHIVE, 'reviewed_extensions': [self.api_receipt]}
        with self.assertRaisesRegex(ValueError, 'clean author'): station.apply_station_extension(self.spec, self.owned, self.host, source, self.plan())
        self.assertEqual(target.read_bytes(), b'old public patched output'); self.assertFalse((self.host / station.INSTALLED_HELPER).exists())

    def current_profile_fixture(self):
        self.prepare_files()
        api = copy.deepcopy(self.api); api.update(host_uuid=station.HOST, archive_sha256=station.ARCHIVE)
        api['insertions'] = [{'path': station.TARGET, 'anchor': 'fixture', 'position': 'after', 'text': 'public-hook'}]
        api_raw = json.dumps(api).encode()
        api_root = self.root / 'grilling'; bp = api_root / 'projects/grilling/gameplay_core/behavior_pack'
        for i, (source, _) in enumerate(api['copies'].items()):
            p = bp / source; p.parent.mkdir(parents=True, exist_ok=True); p.write_bytes(('module-' + str(i)).encode())
        (api_root / station.API_SPEC).parent.mkdir(parents=True, exist_ok=True)
        (api_root / station.API_SPEC).write_bytes(api_raw)
        rp = api_root / 'projects/grilling/gameplay_core/resource_pack'; rp.mkdir(parents=True)
        for root, kind in ((bp, 'data'), (rp, 'resources')):
            (root / 'manifest.json').write_text(json.dumps({'header': {'version': [2, 8, 155]},
                                                          'modules': [{'type': kind, 'version': [2, 8, 155]}]}))
        (rp / 'model.json').write_text('{"synthetic_model":true}')
        (api_root / 'baseline.json').write_text(json.dumps({'version': [2, 8, 155], 'runtime': {
            'BP': bp.relative_to(api_root).as_posix(), 'RP': rp.relative_to(api_root).as_posix()}}))
        (api_root / 'release-history.json').write_text('{"2.8.155":{"fixture":"release identity"}}')
        self.git(api_root, 'init', '--quiet')
        self.git(api_root, 'config', 'user.email', 'fixture@example.invalid')
        self.git(api_root, 'config', 'user.name', 'Synthetic fixture')
        anchor = self.commit(api_root, 'Initial synthetic API handoff')
        operations = [{'path': station.TARGET, 'before': 'fixture-old', 'after': 'fixture-new'}]
        spec = copy.deepcopy(self.spec)
        spec.update(schema=1, kind=station.KIND, host_uuid=station.HOST, archive_sha256=station.ARCHIVE,
                    imports={station.TARGET: station.HELPER_IMPORT + api['imports'][station.TARGET]},
                    insertions=[*api['insertions'], station.INIT], text_replacements=operations,
                    json_updates=[], copies={station.HELPER: station.INSTALLED_HELPER}, expires='2099-01-01')
        spec['owner_handoff'].update(from_repository='burnt-tea-dev/kaleidoscope-grilling-unofficial', from_commit=anchor,
                spec_path=station.API_SPEC, spec_sha256=station.digest(api_raw),
                retained_imports_sha256=station.digest(api['imports'][station.TARGET].encode()),
                retained_insertions_sha256=station.declaration_digest(api['insertions']))
        return spec, api, api_raw, api_root, operations

    @staticmethod
    def git(root, *args):
        return subprocess.check_output(['git', *args], cwd=root, text=True, stderr=subprocess.PIPE).strip()

    def commit(self, root, message):
        self.git(root, 'add', '--all'); self.git(root, 'commit', '--quiet', '-m', message)
        return self.git(root, 'rev-parse', 'HEAD')

    def test_current_profile_binds_the_real_api_hooks_modules_and_owned_helper(self):
        spec, api, api_raw, api_root, operations = self.current_profile_fixture()
        def validate(value):
            return station.current_station_profile(value, self.owned, api, api_raw, api_root)
        with patch.object(station, 'WIRE_OPS', station.declaration_digest(operations)):
            self.assertEqual(validate(spec)['copies'], self.profile['copies'])
            changes = [lambda x: x['owner_handoff'].update(from_commit='b' * 40),
                       lambda x: x['owner_handoff']['retained_modules'].pop(next(iter(self.modules))),
                       lambda x: x['insertions'][0].update(text='changed-hook'),
                       lambda x: x['imports'].update({station.TARGET: 'changed-import'}),
                       lambda x: x['text_replacements'][0].update(after='changed-algorithm-in-wiring'),
                       lambda x: x['original_files'].update({station.TARGET: 'b' * 64}),
                       lambda x: x['copies'].update({'other': 'scripts/other.js'})]
            for mutate in changes:
                changed = copy.deepcopy(spec); mutate(changed)
                with self.assertRaises(ValueError): validate(changed)
            (self.owned / station.HELPER).write_bytes(b'changed-helper')
            with self.assertRaisesRegex(ValueError, 'helper differs'): validate(spec)

    def test_new_author_requires_the_exact_registered_current_owner(self):
        import stable_host_profiles as stable
        spec, api, api_raw, api_root, operations = self.current_profile_fixture()
        host, archive, author = 'new-reviewed-host', '6' * 64, '7' * 64
        api.update(host_uuid=host, archive_sha256=archive); api['original_files'][station.TARGET] = author
        api_raw = json.dumps(api).encode(); (api_root / station.API_SPEC).write_bytes(api_raw)
        anchor = self.commit(api_root, 'New exact author API')
        spec.update(host_uuid=host, archive_sha256=archive, original_files={station.TARGET: author})
        spec['owner_handoff'].update(from_commit=anchor, spec_sha256=station.digest(api_raw), author_sha256=author)
        profile = {'id': station.IDENTITY, 'admission': stable.CURATED, 'spec_sha256': station.declaration_digest(spec),
                   'host_uuid': host, 'archive_sha256': archive, 'original_files': {station.TARGET: author},
                   'version': spec['version'], 'wire_ops_sha256': station.declaration_digest(operations)}
        value = {'schema': 1, 'kind': stable.CURATED, 'profile': 'synthetic-current', 'version': [1, 0, 66],
                 'sources': ['Cookery'], 'functional_checks': {'cookery-station-performance': {'source': 'Cookery', 'cases': 10}},
                 'domains': {'station': ['runtime/BP/host-extensions/cookery-station-performance.json']},
                 'checks': ['current-source-api', 'current-runtime-functional.json'],
                 'check_commands': {'current-source-api': ['node', 'real-source-test.mjs'], 'current-runtime-functional.json': ['python', 'real-producer.py']},
                 'functional_contract': {'path': 'companion-sources/current-author-curated/runtime-contract.json', 'sha256': 'a' * 64},
                 'authors': {}, 'pack_versions': {}, 'station_profile': 'reviewed-current-station'}
        catalog = {'profile': value['profile'], 'version': value['version'], 'authors': {},
                   'selection': {'path': stable.CURATED_INPUT, 'sha256': 'b' * 64, 'value': value}}
        with patch.object(stable, 'CATALOG', {}), self.assertRaisesRegex(ValueError, 'no reviewed catalog'):
            station.current_station_profile(spec, self.owned, api, api_raw, api_root)
        with patch.object(stable, 'CATALOG', {stable.CURATED_KEY: catalog}), patch.object(stable, 'PROFILES', {'reviewed-current-station': profile}):
            self.assertEqual(station.current_station_profile(spec, self.owned, api, api_raw, api_root)['host_uuid'], host)
            changed = copy.deepcopy(spec); changed['text_replacements'][0]['after'] = 'unreviewed-wiring'
            with self.assertRaisesRegex(ValueError, 'curated station declaration differs'):
                station.current_station_profile(changed, self.owned, api, api_raw, api_root)

    def test_delegation_uses_the_exact_public_author_instead_of_the_legacy_constant(self):
        with patch.object(station, 'AUTHOR', 'f' * 64):
            self.assertEqual(station.validate_public_delegation(self.api_receipt, self.expected_api), self.binding)

    def test_original_handoff_survives_a_real_docs_only_descendant_without_changing_receipts(self):
        spec, api, api_raw, api_root, operations = self.current_profile_fixture()
        original = copy.deepcopy(spec)
        with patch.object(station, 'WIRE_OPS', station.declaration_digest(operations)):
            before = station.current_station_profile(spec, self.owned, api, api_raw, api_root)
            docs = api_root / 'docs/RELEASING.md'; docs.parent.mkdir(); docs.write_text('Synthetic maintenance guidance.\n')
            current = self.commit(api_root, 'Document maintenance process')
            self.assertNotEqual(current, spec['owner_handoff']['from_commit'])
            after = station.current_station_profile(spec, self.owned, api, api_raw, api_root)
        self.assertEqual(after, before); self.assertEqual(spec, original)

    def test_exported_runtime_or_manifest_change_cannot_reuse_the_original_handoff(self):
        spec, _, api_raw, api_root, _ = self.current_profile_fixture()
        anchor = spec['owner_handoff']['from_commit']
        paths = ['projects/grilling/gameplay_core/behavior_pack/scripts/other.js',
                 'projects/grilling/gameplay_core/resource_pack/model.json',
                 'projects/grilling/gameplay_core/behavior_pack/manifest.json']
        for path in paths:
            with self.subTest(path=path):
                self.git(api_root, 'reset', '--hard', anchor)
                target = api_root / path; target.parent.mkdir(parents=True, exist_ok=True); target.write_text('changed export')
                self.commit(api_root, 'Change exported release input')
                with self.assertRaisesRegex(ValueError, 'exported runtime changed'):
                    station.validate_api_handoff_anchor(spec['owner_handoff'], api_root, api_raw)

    def test_baseline_and_release_history_changes_cannot_reuse_the_original_handoff(self):
        spec, _, api_raw, api_root, _ = self.current_profile_fixture()
        anchor = spec['owner_handoff']['from_commit']
        for path in ('baseline.json', 'release-history.json'):
            with self.subTest(path=path):
                self.git(api_root, 'reset', '--hard', anchor)
                (api_root / path).write_text('{"changed":"release input"}')
                self.commit(api_root, 'Change release identity')
                with self.assertRaisesRegex(ValueError, 'release input changed'):
                    station.validate_api_handoff_anchor(spec['owner_handoff'], api_root, api_raw)

    def test_changed_api_or_retained_module_cannot_reuse_the_original_handoff(self):
        spec, api, api_raw, api_root, _ = self.current_profile_fixture()
        anchor = spec['owner_handoff']['from_commit']
        for path in (station.API_SPEC, 'projects/grilling/gameplay_core/behavior_pack/' + next(iter(api['copies']))):
            with self.subTest(path=path):
                self.git(api_root, 'reset', '--hard', anchor)
                (api_root / path).write_text('changed public API input')
                self.commit(api_root, 'Change public API')
                with self.assertRaisesRegex(ValueError, 'exported runtime changed'):
                    station.validate_api_handoff_anchor(spec['owner_handoff'], api_root, api_raw)

    def test_unrelated_or_abbreviated_commit_cannot_be_a_retained_api_anchor(self):
        spec, _, api_raw, api_root, _ = self.current_profile_fixture()
        tree = self.git(api_root, 'rev-parse', 'HEAD^{tree}')
        unrelated = self.git(api_root, 'commit-tree', tree, '-m', 'Unrelated identical source')
        with self.assertRaisesRegex(ValueError, 'not an ancestor'):
            station.validate_api_handoff_anchor({**spec['owner_handoff'], 'from_commit': unrelated}, api_root, api_raw)
        self.git(api_root, 'tag', '--annotate', 'synthetic-anchor', '-m', 'Synthetic annotated tag')
        tag = self.git(api_root, 'rev-parse', 'synthetic-anchor')
        for anchor in ('HEAD', 'a' * 7, '--all', 'f' * 40, tag):
            with self.subTest(anchor=anchor), self.assertRaises(ValueError):
                station.validate_api_handoff_anchor({**spec['owner_handoff'], 'from_commit': anchor}, api_root, api_raw)

    def test_uncommitted_api_bytes_cannot_replace_the_committed_declaration(self):
        spec, _, api_raw, api_root, _ = self.current_profile_fixture()
        (api_root / station.API_SPEC).write_bytes(api_raw + b'\n')
        with self.assertRaisesRegex(ValueError, 'declaration differs from committed'):
            station.validate_api_handoff_anchor(spec['owner_handoff'], api_root, api_raw + b'\n')


class PreservedSourceReceipts(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(); self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name); self.pack = self.root / 'preserved'; self.pack.mkdir()
        self.uid = '11111111-2222-4333-8444-555555555555'
        self.manifest = {'format_version': 2, 'header': {'name': 'synthetic input', 'uuid': self.uid, 'version': [1, 0, 1]},
                         'modules': [{'type': 'data', 'uuid': 'aaaaaaaa-bbbb-4ccc-8ddd-eeeeeeeeeeee', 'version': [1, 0, 1]}]}
        (self.pack / 'manifest.json').write_text(json.dumps(self.manifest))
        self.lock = {'schema': 1, 'owned': [], 'upstream': [], 'order': {'behavior': [], 'resource': []}, 'deployment_holds': []}

    def build(self, mapping):
        output = self.root / 'candidate'
        with contextlib.redirect_stdout(io.StringIO()):
            return family_bundle.assemble(copy.deepcopy(self.lock), {}, [], output, working=True, preserved=[self.pack], preserved_sources=mapping)

    def test_verified_preserved_descriptor_is_recorded_before_receipt_and_input_is_immutable(self):
        mapping = {self.uid: {'owner': 'preserved', 'role': 'synthetic_local_repair', 'provenance': {'state': 'unknown'}}}
        original = copy.deepcopy(mapping); receipt = self.build(mapping)
        self.assertEqual(receipt['packs'][0]['source'], mapping[self.uid]); self.assertEqual(mapping, original)
        self.assertEqual(json.loads((self.root / 'candidate/family-receipt.json').read_text()), receipt)

    def test_unmapped_input_keeps_its_original_preserved_role(self):
        receipt = self.build(None)
        self.assertEqual(receipt['packs'][0]['source'], {'owner': 'preserved', 'role': 'unchanged_external_dependency'})

    def test_foreign_owner_or_unmatched_uuid_cannot_create_a_receipt(self):
        for mapping in ({self.uid: {'owner': 'owned'}}, {self.uid: {'owner': 'upstream'}},
                        {self.uid: {'owner': 'preserved', 'official_author_release': True}},
                        {'missing': {'owner': 'preserved'}}):
            output = self.root / 'candidate'
            with self.subTest(mapping=mapping), self.assertRaises(SystemExit): self.build(mapping)
            self.assertFalse((output / 'family-receipt.json').exists())
            if output.exists():
                import shutil
                shutil.rmtree(output)


if __name__ == '__main__':
    unittest.main()
