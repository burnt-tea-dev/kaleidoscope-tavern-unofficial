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
        vine = 'BP/scripts/custom_components/netherGrapevine.js'
        self.before[vine] = b'export const tick={onTick({block}){if(!attached(block,c))detach(block);}};\n'
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
        self.after[vine] = b'export const tick={onTick({block}){if(!block.isValid)return;if(!attached(block,c))detach(block);}};\n'
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
                     'id': 'senluo:dimensions-wine-snow-repair', 'version': [1, 0, 2],
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
        self.spec['text_replacements'].append({'path': vine, 'before': 'onTick({block}){if(!attached(block,c))',
                                                'after': 'onTick({block}){if(!block.isValid)return;if(!attached(block,c))'})
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
        self.assertEqual(receipt['version'], [1, 0, 2])
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

    def test_last_output_or_rp_preimage_failure_leaves_all_reviewed_files_unchanged(self):
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
        for field, value in [('version', [1, 0, 3]), ('owner_version', [1, 0, 69]),
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
            self.assertEqual(proof['version'], [1, 0, 2])
        self.assertIs(receipt['production_ready'], False)


class OwnedDataSources(unittest.TestCase):
    def setUp(self):
        PairedDataRepair.setUp(self)
        self.spec['kind'] = 'addon-owned-data'
        self.spec['id'] = 'fixture:owned-data'
        self.spec['manifest_names'] = self.names
        self.spec['source_files'] = {name: 'authored/' + name for name in self.after}
        for key in ('imports', 'insertions', 'json_updates', 'text_replacements'):
            self.spec.pop(key)
        self.owned = self.root / 'addon-sources'
        for name, raw in self.after.items():
            path = self.owned / self.spec['source_files'][name]
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(raw)
        self.register(self.spec)

    register = PairedDataRepair.register
    snapshot = PairedDataRepair.snapshot

    def apply(self, spec=None):
        return extension.apply_owned_data_extension(
            self.spec if spec is None else spec, self.owned, self.root / 'BP',
            self.root / 'RP', self.source, self.source, self.owner)

    def canonical_owned_spec(self):
        self.spec['archive_sha256'] = None
        self.source = {'owner': 'owned', 'repository': 'fixture/canonical',
                       'commit': 'a' * 40, 'working_candidate': False}
        self.spec['canonical_host'] = {'key': 'peer', 'repository': self.source['repository'],
                                      'commit': self.source['commit']}
        for field in ('original_files', 'patched_files', 'source_files'):
            self.spec[field] = {name: value for name, value in self.spec[field].items()
                                if name.endswith('/manifest.json')}
        self.spec['dependency_rewrites'] = [{'uuid': 'host-bp', 'before': [2, 0, 0], 'after': [2, 0, 1]}]
        name = 'BP/manifest.json'
        before, after = json.loads(self.before[name]), json.loads(self.after[name])
        before['dependencies'].append({'uuid': 'host-bp', 'version': [2, 0, 0]})
        after['dependencies'].append({'uuid': 'host-bp', 'version': [2, 0, 1]})
        (self.root / name).write_bytes(encoded(before))
        (self.owned / self.spec['source_files'][name]).write_bytes(encoded(after))
        self.spec['original_files'][name] = sha(encoded(before))
        self.spec['patched_files'][name] = sha(encoded(after))
        self.register(self.spec)
        self.registry['fixture']['source_owner'] = 'owned'

    def test_canonical_owned_pair_changes_only_metadata_and_keeps_source_identity(self):
        self.canonical_owned_spec()
        before = {name: (self.root / name).read_bytes() for name in self.before
                  if not name.endswith('/manifest.json')}
        proof = self.apply()
        manifest = json.loads((self.root / 'BP/manifest.json').read_bytes())
        self.assertEqual(manifest['header']['version'], self.local)
        self.assertEqual(manifest['dependencies'][-1], {'uuid': 'host-bp', 'version': [2, 0, 1]})
        self.assertEqual(proof['canonical_host'], self.spec['canonical_host'])
        for name, raw in before.items(): self.assertEqual((self.root / name).read_bytes(), raw)
        self.assertEqual(self.source['owner'], 'owned')

    def test_owned_pair_rejects_other_source_or_gameplay_data_without_writes(self):
        self.canonical_owned_spec()
        self.source['commit'] = 'b' * 40
        before = self.snapshot()
        with self.assertRaisesRegex(ValueError, 'declared manifest release'): self.apply()
        self.assertEqual(self.snapshot(), before)
        self.source['commit'] = 'a' * 40
        name = 'BP/scripts/data/tavern-extension.js'
        self.spec['source_files'][name] = 'authored/' + name
        self.spec['original_files'][name] = sha(self.before[name])
        self.spec['patched_files'][name] = sha(self.after[name])
        self.register(self.spec); self.registry['fixture']['source_owner'] = 'owned'
        before = self.snapshot()
        with self.assertRaisesRegex(ValueError, 'declared manifest release'): self.apply()
        self.assertEqual(self.snapshot(), before)

    def test_owned_output_validation_rejects_non_manifest_drift(self):
        import shutil
        from family_bundle import files_hash
        from family_update.current_author_validation import validate_owned_pair_metadata, tree
        from family_update import common
        from family_guard import hashes
        self.enterContext(patch.object(common, 'G', {'hashes': hashes}))
        self.canonical_owned_spec()
        canonical = self.root / 'canonical'; canonical.mkdir()
        for side in ('BP', 'RP'): shutil.copytree(self.root / side, canonical / side)
        baseline = {'repository': self.source['repository'], 'version': [1, 0, 0],
                    'runtime': {'BP': 'BP', 'RP': 'RP'},
                    'packs': {side: {'uuid': uid} for side, uid in self.ids.items()},
                    'source_trees': {side: tree(files_hash(canonical / side)) for side in ('BP', 'RP')}}
        (canonical / 'baseline.json').write_text(json.dumps(baseline))
        subprocess.run(['git', 'init', '--quiet', str(canonical)], check=True)
        subprocess.run(['git', '-C', str(canonical), 'add', '.'], check=True)
        subprocess.run(['git', '-C', str(canonical), '-c', 'user.name=Fixture',
                        '-c', 'user.email=fixture@example.invalid', '-c', 'commit.gpgsign=false',
                        'commit', '--quiet', '-m', 'Canonical input'], check=True)
        commit = subprocess.check_output(['git', '-C', str(canonical), 'rev-parse', 'HEAD'], text=True).strip()
        self.source['commit'] = self.spec['canonical_host']['commit'] = commit
        self.register(self.spec); self.registry['fixture']['source_owner'] = 'owned'
        proof = self.apply(); spec_sha = sha(encoded(self.spec))
        owner = {'repository': 'fixture/integration', 'commit': 'b' * 40, 'version': self.owner}
        proof.update(repository=owner['repository'], commit=owner['commit'], spec_sha256=spec_sha, working_candidate=False)
        records = {uid: {'uuid': uid, 'side': 'behavior' if side == 'BP' else 'resource',
                          'version': self.local, 'files': files_hash(self.root / side),
                          'source': {**self.source, 'reviewed_extensions': [proof]}}
                   for side, uid in self.ids.items()}
        validate_owned_pair_metadata(self.spec, records, {'peer': canonical}, owner, spec_sha)
        target = self.root / 'BP/scripts/data/tavern-extension.js'
        target.write_bytes(b'undeclared gameplay change')
        records[self.ids['BP']]['files'] = files_hash(self.root / 'BP')
        with self.assertRaisesRegex(AssertionError, 'non-manifest bytes'):
            validate_owned_pair_metadata(self.spec, records, {'peer': canonical}, owner, spec_sha)

    def test_data_is_owned_by_pair_with_one_shared_receipt(self):
        receipt = self.apply()
        for name, raw in self.after.items():
            self.assertEqual((self.root / name).read_bytes(), raw)
        self.assertEqual((self.root / 'RP/untouched.bin').read_bytes(), b'untouched invented body')
        extension.validate_pair_receipt(self.spec, receipt, self.owner, self.local,
                                        self.ids['BP'], self.ids['RP'])

    def test_complete_owner_replacement_keeps_its_own_data_and_provenance(self):
        self.spec['archive_sha256'] = None
        self.register(self.spec)
        self.registry['fixture']['source_owner'] = 'preserved'
        self.source = {'owner': 'preserved', 'role': 'owner_accepted_author_replacement',
                       'official_author_release': False}
        self.apply()
        self.assertEqual((self.root / 'RP/untouched.bin').read_bytes(), b'untouched invented body')
        self.source['role'] = 'unchanged_external_dependency'
        with self.assertRaisesRegex(ValueError, 'complete accepted replacement'):
            self.apply()

    def test_new_data_is_added_only_to_an_unoccupied_target(self):
        name='BP/entities/restored.json';raw=b'{"fixture":"restored owner data"}\n'
        source='authored/'+name
        self.spec['source_files'][name]=source
        self.spec['original_files'][name]=None
        self.spec['patched_files'][name]=sha(raw)
        target=self.owned/source;target.parent.mkdir(parents=True);target.write_bytes(raw)
        self.register(self.spec)
        target=self.root/name;target.parent.mkdir(parents=True);target.write_bytes(b'newer host data')
        before=self.snapshot()
        with self.assertRaisesRegex(ValueError,'addition is occupied'):
            self.apply()
        self.assertEqual(self.snapshot(),before)
        target.unlink()
        self.apply()
        self.assertEqual(target.read_bytes(),raw)

    def test_retiring_duplicate_checks_all_preimages_before_writing(self):
        name = 'RP/models/legacy.json'
        target = self.root / name
        target.parent.mkdir(parents=True)
        target.write_bytes(b'newer host model')
        self.spec['removed_files'] = {name: sha(b'old duplicate')}
        self.register(self.spec)
        before = self.snapshot()
        with self.assertRaisesRegex(ValueError, 'removal preimage differs'):
            self.apply()
        self.assertEqual(self.snapshot(), before)
        target.write_bytes(b'old duplicate')
        receipt = self.apply()
        self.assertFalse(target.exists())
        self.assertEqual(receipt['removed_files'], self.spec['removed_files'])
        self.assertEqual((self.root / 'RP/untouched.bin').read_bytes(), b'untouched invented body')

    def test_newer_host_data_or_damaged_source_cannot_partially_write(self):
        path = self.root / 'RP/manifest.json'
        path.write_bytes(path.read_bytes() + b'\n')
        before = self.snapshot()
        with self.assertRaisesRegex(ValueError, 'preimage differs'):
            self.apply()
        self.assertEqual(self.snapshot(), before)
        path.write_bytes(self.before['RP/manifest.json'])
        path = self.owned / self.spec['source_files']['RP/manifest.json']
        path.write_bytes(path.read_bytes() + b'\n')
        before = self.snapshot()
        with self.assertRaisesRegex(ValueError, 'source differs'):
            self.apply()
        self.assertEqual(self.snapshot(), before)

    def test_sources_cannot_escape_and_manifests_keep_pack_and_module_ids(self):
        for mutation in ('escape', 'module'):
            spec = copy.deepcopy(self.spec)
            if mutation == 'escape':
                spec['source_files']['BP/manifest.json'] = '../BP/manifest.json'
            else:
                name = 'BP/manifest.json'
                value = json.loads(self.after[name]);value['modules'][0]['uuid'] = 'foreign'
                raw = encoded(value)
                (self.owned / spec['source_files'][name]).write_bytes(raw)
                spec['patched_files'][name] = sha(raw)
            self.register(spec)
            before = self.snapshot()
            with self.subTest(mutation=mutation), self.assertRaises(ValueError):
                self.apply(spec)
            self.assertEqual(self.snapshot(), before)


if __name__ == '__main__':
    unittest.main()
