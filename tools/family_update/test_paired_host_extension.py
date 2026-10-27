"""Small invented packs exercise the real catalog-bound pair consumer."""
import copy
import contextlib
import hashlib
import io
import json
from pathlib import Path
import sys
import subprocess
import tempfile
import unittest
from unittest.mock import patch
import zipfile

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import paired_host_extension as extension
import stable_host_profiles as stable


def encoded(value):
    return (json.dumps(value, ensure_ascii=False, indent=2) + '\n').encode()


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


class PairedDataRepair(unittest.TestCase):
    def setUp(self):
        self.owner, self.local = [1, 0, 70], [1, 0, 10070]
        self.ids = {'BP': '11111111-1111-4111-8111-111111111111',
                    'RP': '22222222-2222-4222-8222-222222222222'}
        self.names = {side: 'Fixture ' + side + ' [reviewed local compatibility]' for side in self.ids}
        self.author = {'behavior_uuid': self.ids['BP'], 'resource_uuid': self.ids['RP'],
                       'project_id': 71, 'file_id': 72, 'sha256': sha(b'invented archive'),
                       'author_version': [1, 0, 0]}
        manifests = {
            side: {'header': {'uuid': self.ids[side], 'version': [1, 0, 0], 'name': 'Author ' + side,
                              'description': 'Keep this author metadata'},
                   'modules': [{'uuid': side + '-module', 'version': [1, 0, 0],
                                'type': 'data' if side == 'BP' else 'resources'}],
                   'dependencies': [{'uuid': self.ids[peer], 'version': [1, 0, 0]},
                                    {'module_name': '@minecraft/server', 'version': '2.9.0'}]}
            for side, peer in [('BP', 'RP'), ('RP', 'BP')]}
        payload = 'BP/scripts/data/tavern-extension.js'
        guide = 'BP/scripts/data/guidebook.js'
        self.before = {side + '/manifest.json': encoded(value) for side, value in manifests.items()}
        self.before.update({payload: b'export const data=["minecraft:snow_block"];\n',
                            guide: b'export const guide=[["minecraft:blue_ice","minecraft:snow_block"],{"minecraft:snow_block":"Snow Block"}];\n'})
        self.after = {
            side + '/manifest.json': encoded({
                'header': {'uuid': self.ids[side], 'version': self.local, 'name': self.names[side],
                           'description': 'Keep this author metadata'},
                'modules': [{'uuid': side + '-module', 'version': self.local,
                             'type': 'data' if side == 'BP' else 'resources'}],
                'dependencies': [{'uuid': self.ids[peer], 'version': self.local},
                                 {'module_name': '@minecraft/server', 'version': '2.9.0'}]})
            for side, peer in [('BP', 'RP'), ('RP', 'BP')]}
        self.after.update({payload: b'export const data=["minecraft:snow"];\n',
                           guide: b'export const guide=[["minecraft:blue_ice","minecraft:snow"],{"minecraft:snow":"Snow Block"}];\n'})
        updates = []
        # Fixture declarations are literal input, rather than a call to the consumer's planner.
        for side in ('BP', 'RP'):
            updates.extend([
                {'path': side + '/manifest.json', 'pointer': ['header', 'version'], 'mode': 'reviewed_set', 'value': self.local},
                {'path': side + '/manifest.json', 'pointer': ['modules', '0', 'version'], 'mode': 'reviewed_set', 'value': self.local},
                {'path': side + '/manifest.json', 'pointer': ['dependencies', '0', 'version'], 'mode': 'reviewed_set', 'value': self.local},
                {'path': side + '/manifest.json', 'pointer': ['header', 'name'], 'mode': 'reviewed_set', 'value': self.names[side]},
            ])
        self.spec = {'schema': 1, 'kind': 'dimensions-wine-snow-repair',
                     'id': 'senluo:dimensions-wine-snow-repair', 'version': [1, 0, 1],
                     'host_uuid': self.ids['RP'], 'behavior_uuid': self.ids['BP'], 'resource_uuid': self.ids['RP'],
                     'archive_sha256': self.author['sha256'], 'owner_version': self.owner,
                     'local_pack_version': self.local, 'official_author_release': False,
                     'expires': '2099-01-01', 'authorization': 'Synthetic review', 'feedback': 'Fixture only',
                     'removal_condition': 'Fixture only', 'copies': {}, 'imports': {}, 'insertions': [],
                     'original_files': {name: sha(raw) for name, raw in self.before.items()},
                     'patched_files': {name: sha(raw) for name, raw in self.after.items()},
                     'json_updates': updates,
                     'text_replacements': [
                         {'path': payload, 'before': '"minecraft:snow_block"', 'after': '"minecraft:snow"'},
                         {'path': guide, 'before': '"minecraft:blue_ice","minecraft:snow_block"]',
                          'after': '"minecraft:blue_ice","minecraft:snow"]'},
                         {'path': guide, 'before': '"minecraft:snow_block":"Snow Block"',
                          'after': '"minecraft:snow":"Snow Block"'},
                     ]}
        self.registry = {}
        self.enterContext(patch.object(stable, 'PROFILES', self.registry))
        self.enterContext(patch.object(stable, 'CATALOG', {
            'public_api_profile': {'id': 'fixture:unrelated', 'host_uuid': 'unrelated'},
            stable.CURATED_KEY: {'authors': {'DimensionsWine': self.author}}}))
        self.register(self.spec)
        self.source = {'owner': 'upstream', 'project_id': 71, 'file_id': 72,
                       'archive_sha256': self.author['sha256'], 'reviewed_extensions': []}
        temporary = tempfile.TemporaryDirectory(); self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        for name, raw in self.before.items():
            path = self.root / name; path.parent.mkdir(parents=True, exist_ok=True); path.write_bytes(raw)
        (self.root / 'RP/untouched.bin').write_bytes(b'untouched invented body')

    def register(self, spec):
        self.registry['fixture'] = {key: copy.deepcopy(spec[key]) for key in (
            'id', 'kind', 'version', 'host_uuid', 'behavior_uuid', 'resource_uuid', 'owner_version',
            'local_pack_version', 'archive_sha256', 'original_files', 'patched_files', 'official_author_release')}
        self.registry['fixture'].update(admission=stable.CURATED, source_owner='upstream',
                                        required_extensions=[], copies={}, author_version=[1, 0, 0],
                                        manifest_names=self.names, spec_sha256=stable.declaration_sha(spec))

    def apply(self, spec=None, rp_source=None, owner=None):
        return extension.apply_paired_data_extension(
            self.spec if spec is None else spec, self.root / 'BP', self.root / 'RP',
            self.source, self.source if rp_source is None else rp_source,
            self.owner if owner is None else owner)

    def snapshot(self):
        return {path.relative_to(self.root).as_posix(): path.read_bytes()
                for path in self.root.rglob('*') if path.is_file()}

    def test_exact_pair_changes_only_reviewed_data_names_and_own_versions(self):
        receipt = self.apply()
        for name, raw in self.after.items():self.assertEqual((self.root / name).read_bytes(), raw)
        self.assertEqual((self.root / 'RP/untouched.bin').read_bytes(), b'untouched invented body')
        self.assertEqual(receipt['version'], [1, 0, 1])
        self.assertEqual(receipt['local_pack_version'], self.local)
        self.assertEqual(receipt['spec_sha256'], stable.declaration_sha(self.spec))
        extension.validate_pair_receipt(self.spec, receipt, self.owner, self.local, self.ids['BP'], self.ids['RP'])

    def test_unknown_declaration_owner_and_either_source_cannot_write(self):
        original = self.snapshot()
        forged = copy.deepcopy(self.spec); forged['authorization'] += ' unreviewed'
        with self.assertRaisesRegex(ValueError, 'exact reviewed profile'):self.apply(forged)
        with self.assertRaisesRegex(ValueError, 'reviewed author/owner'):self.apply(owner=[1, 0, 71])
        for key, value in [('project_id', 99), ('file_id', 99), ('archive_sha256', 'f' * 64),
                           ('owner', 'upstream_extended'), ('reviewed_extensions', [{'id': 'foreign'}])]:
            with self.subTest(key=key), self.assertRaisesRegex(ValueError, 'both exact clean author'):
                self.apply(rp_source={**self.source, key: value})
        self.assertEqual(self.snapshot(), original)

    def test_catalog_registration_does_not_allow_unknown_kind_path_or_operations(self):
        original = self.snapshot()
        for mutation in ('kind', 'path', 'api', 'name', 'replacement', 'copy'):
            spec = copy.deepcopy(self.spec)
            if mutation == 'kind':spec['kind'] = 'unknown-paired-repair'
            elif mutation == 'path':spec['original_files']['BP/scripts/main.js'] = sha(b'foreign')
            elif mutation == 'api':spec['json_updates'][2]['pointer'] = ['dependencies', '1', 'version']
            elif mutation == 'name':spec['json_updates'][3]['value'] = 'Unreviewed label'
            elif mutation == 'replacement':spec['text_replacements'][0]['after'] = '"minecraft:diamond"'
            else:spec['copies'] = {'private.js': 'BP/scripts/main.js'}
            self.register(spec)
            with self.subTest(mutation=mutation), self.assertRaises(ValueError):self.apply(spec)
            self.assertEqual(self.snapshot(), original)

    def test_last_output_or_rp_preimage_failure_leaves_all_four_files_unchanged(self):
        original = self.snapshot()
        spec = copy.deepcopy(self.spec); spec['patched_files']['BP/scripts/data/guidebook.js'] = 'f' * 64
        self.register(spec)
        with self.assertRaisesRegex(ValueError, 'reviewed output'):self.apply(spec)
        self.assertEqual(self.snapshot(), original)
        self.register(self.spec)
        path = self.root / 'RP/manifest.json';path.write_bytes(path.read_bytes() + b'\n')
        before = self.snapshot()
        with self.assertRaisesRegex(ValueError, 'preimage differs'):self.apply()
        self.assertEqual(self.snapshot(), before)

    def test_duplicate_anchor_and_wrong_pair_ids_are_rejected_before_write(self):
        spec = copy.deepcopy(self.spec); spec['resource_uuid'] = 'another-pack'; self.register(spec)
        with self.assertRaisesRegex(ValueError, 'reviewed author/owner'):self.apply(spec)
        self.register(self.spec)
        name = 'BP/scripts/data/tavern-extension.js';raw = self.before[name] + b'"minecraft:snow_block"\n'
        (self.root / name).write_bytes(raw);spec = copy.deepcopy(self.spec);spec['original_files'][name] = sha(raw);self.register(spec)
        before = self.snapshot()
        with self.assertRaisesRegex(ValueError, 'anchor is not unique'):self.apply(spec)
        self.assertEqual(self.snapshot(), before)

    def test_pair_receipt_checks_schema_revision_separately_from_owner_and_pack(self):
        receipt = self.apply()
        for field, value in [('version', [1, 0, 2]), ('owner_version', [1, 0, 69]),
                             ('owner_version', [True, 0, 70]), ('local_pack_version', [1, 0, 1]),
                             ('resource_uuid', 'other'), ('official_author_release', True),
                             ('official_author_release', 0)]:
            with self.subTest(field=field), self.assertRaises(ValueError):
                extension.validate_pair_receipt(self.spec, {**receipt, field: value}, self.owner,
                                                self.local, self.ids['BP'], self.ids['RP'])

    def test_family_builder_dispatches_real_pair_replay_and_attaches_same_receipt(self):
        import family_bundle as bundle
        from baseline_gate import fingerprint
        archive = self.root / 'invented-author.mcaddon'
        with zipfile.ZipFile(archive, 'w') as z:
            for name, raw in self.before.items():z.writestr(name, raw)
            z.writestr('RP/untouched.bin', b'untouched invented body')
        self.author['sha256'] = sha(archive.read_bytes())
        self.spec['archive_sha256'] = self.source['archive_sha256'] = self.author['sha256']
        self.register(self.spec)
        owned = self.root / 'owned';owned.mkdir()
        ids = {'BP': '33333333-3333-4333-8333-333333333333',
               'RP': '44444444-4444-4444-8444-444444444444'}
        for side in ('BP', 'RP'):
            root = owned / 'runtime' / side;root.mkdir(parents=True)
            (root / 'manifest.json').write_bytes(encoded({
                'header': {'uuid': ids[side], 'version': self.owner},
                'modules': [{'type': 'data' if side == 'BP' else 'resources'}]}))
        declarations = owned / 'runtime/BP/host-extensions';declarations.mkdir()
        (declarations / 'fixture.json').write_bytes(encoded(self.spec))
        trees = {side: fingerprint(owned / 'runtime' / side)[0] for side in ids}
        config = {'repository': 'fixture/owned', 'version': self.owner, 'source_trees': trees,
                  'runtime': {side: 'runtime/' + side for side in ids}}
        (owned / 'baseline.json').write_bytes(encoded(config))
        for args in [('init', '--quiet', '--initial-branch=main'), ('add', '.'),
                     ('-c', 'user.name=Fixture', '-c', 'user.email=fixture@example.invalid',
                      '-c', 'commit.gpgsign=false', 'commit', '--quiet', '-m', 'Invented source')]:
            subprocess.run(['git', '-C', str(owned), *args], check=True, capture_output=True)
        lock = {'owned': [{'key': 'fixture', 'repository': config['repository'],
                           'version': self.owner, 'source_trees': trees}],
                'upstream': [{'name': 'DimensionsWine', 'project_id': 71, 'file_id': 72,
                              'sha256': self.author['sha256'],
                              'packs': [{'uuid': uid, 'version': [1, 0, 0]} for uid in self.ids.values()]}],
                'order': {label: [ids[side], self.ids[side]]
                          for side, label in [('BP', 'behavior'), ('RP', 'resource')]}}
        output = self.root / 'candidate'
        with contextlib.redirect_stdout(io.StringIO()):
            receipt = bundle.assemble(lock, {'fixture': owned}, [archive], output, working=True)
        rows = [row for row in receipt['packs'] if row['uuid'] in self.ids.values()]
        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[0]['source']['reviewed_extensions'], rows[1]['source']['reviewed_extensions'])
        for row in rows:
            self.assertEqual(row['version'], self.local)
            self.assertIs(row['source']['official_author_release'], False)
            proof = row['source']['reviewed_extensions'][0]
            self.assertEqual(proof['source_package_version'], self.owner)
            self.assertTrue(proof['working_candidate'])
            self.assertEqual(proof['version'], [1, 0, 1])
        self.assertIs(receipt['production_ready'], False)


if __name__ == '__main__':
    unittest.main()
