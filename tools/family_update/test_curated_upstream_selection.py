"""Committed synthetic sources exercise author selection; no BDS or client claims."""
import contextlib
import copy
import hashlib
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
import zipfile

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import family_bundle as bundle
import stable_host_profiles as stable
from family_update import current_author_validation as current
from family_update.repository_identity import target
from family_update import test_current_author_validation as current_tests


class CuratedUpstreamSelection(unittest.TestCase):
    def setUp(self):
        # Reuse the existing genuine Git preimage/current-source fixture and its
        # real conservation validator, adding small valid manifest archives.
        self.fixture = current_tests.CuratedProfileAdmission()
        self.addCleanup(self.fixture.doCleanups)
        self.fixture.setUp()
        self.root = self.fixture.root
        self.baseline = self.fixture.baseline
        self.value = self.fixture.value
        self.catalog = self.fixture.catalog
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.output = Path(self.temporary.name)
        self.archive = self.output / 'author.mcaddon'
        self.manifests = [self.manifest('author-b', 'data'), self.manifest('author-r', 'resources')]
        self.write_archive(self.manifests)
        self.pin = {'project_id': 11, 'file_id': 22, 'sha256': self.sha(self.archive.read_bytes()),
                    'behavior_uuid': 'author-b', 'resource_uuid': 'author-r', 'author_version': [1, 0, 0]}
        self.author = {'name': 'Cookery', **{key: self.pin[key] for key in ('project_id', 'file_id', 'sha256')},
                       'packs': [{'uuid': row['header']['uuid'], 'version': [1, 0, 0]} for row in self.manifests]}
        full = json.loads((Path(bundle.ROOT) / 'family/upstream.lock.json').read_text())
        self.deferred = copy.deepcopy(next(row for row in full['upstream'] if row['name'] == 'BetterBiomes'))
        self.baseline.update(runtime={'BP': 'runtime/BP', 'RP': 'runtime/RP'},
                             packs={'BP': {'uuid': 'private-b'}, 'RP': {'uuid': 'private-r'}})
        for side, uid, kind in [('BP', 'private-b', 'data'), ('RP', 'private-r', 'resources')]:
            self.fixture.write('runtime/' + side + '/manifest.json', self.manifest(uid, kind, [1, 0, 66]))
        self.fixture.write(self.fixture.hud, {'namespace': 'synthetic_current'})
        self.fixture.after = self.fixture.files()
        self.baseline['source_trees'] = {side: current.tree(files) for side, files in self.fixture.after.items()}
        owned = self.fixture.owned
        owned.update(files=copy.deepcopy(self.fixture.after), source_trees=copy.deepcopy(self.baseline['source_trees']))
        owned['functional_domains']['family-hud'][self.fixture.hud]['after'] = self.fixture.after['RP']['ui/hud_screen.json']
        contract = {'schema': 1, 'kind': 'current-functional-runtime', 'domains': owned['functional_domains']}
        self.fixture.write(self.fixture.contract, contract)
        self.value['functional_contract']['sha256'] = self.sha((self.root / self.fixture.contract).read_bytes())
        self.value.update(authors={'Cookery': self.pin}, pack_versions={'Cookery': {'BP': [1, 0, 0], 'RP': [1, 0, 0]}})
        self.catalog.update(authors=self.value['authors'], upstream_selection={'schema': 1, 'kind': 'exact-curated-author-set',
            'deferred': {'BetterBiomes': {'upstream': copy.deepcopy(self.deferred), 'reason': 'Synthetic fixture retains its reviewed family scope.'}}})
        self.fixture.write('.repo-target.json', {'schema': 1, **target('burnt-tea-dev/senluo-family-integration-private'),
                                               'logical_runtime_repository': current.LOGICAL})
        self.fixture.write('fixture-conservation.json', owned)
        self.fixture.write('tools/current_release.py', "from pathlib import Path\nprint((Path(__file__).resolve().parents[1]/'fixture-conservation.json').read_text())\n")
        self.sync_selection()
        self.lock = {'owned': [{'key': 'private', 'repository': current.LOGICAL, 'version': self.baseline['version'],
                                'source_trees': self.baseline['source_trees']}],
                     'upstream': [self.author, self.deferred],
                     'order': {'behavior': ['private-b', 'author-b', self.deferred['packs'][0]['uuid']],
                               'resource': ['private-r', 'author-r', self.deferred['packs'][1]['uuid']]}}
        self.count = 0

    @staticmethod
    def sha(raw):
        return hashlib.sha256(raw).hexdigest()

    @staticmethod
    def manifest(uid, kind, version=None):
        return {'format_version': 2, 'header': {'uuid': uid, 'version': version or [1, 0, 0]},
                'modules': [{'type': kind}]}

    def write_archive(self, manifests):
        with zipfile.ZipFile(self.archive, 'w') as archive:
            for index, manifest in enumerate(manifests):
                archive.writestr(str(index) + '/manifest.json', json.dumps(manifest))

    def sync_selection(self):
        self.fixture.write('baseline.json', self.baseline)
        self.fixture.write(stable.CURATED_INPUT, self.value)
        self.catalog['selection'] = {'path': stable.CURATED_INPUT,
                                     'sha256': self.sha((self.root / stable.CURATED_INPUT).read_bytes()),
                                     'value': self.value}
        self.fixture.commit('Committed synthetic curated selection')

    def selection(self, lock=None):
        return stable.curated_upstream_selection(lock or self.lock, self.baseline, self.root)

    def assemble(self, **kwargs):
        self.count += 1
        with contextlib.redirect_stdout(io.StringIO()):
            return bundle.assemble(self.lock, {'private': self.root}, kwargs.pop('archives', [self.archive]),
                                   self.output / ('out-' + str(self.count)), working=True, **kwargs)

    def test_default_without_curated_owner_still_requires_deferred_catalog_archive(self):
        lock = copy.deepcopy(self.lock)
        lock['owned'] = []
        with self.assertRaisesRegex(SystemExit, 'missing hash-pinned upstream archive: BetterBiomes'):
            bundle.assemble(lock, {}, [self.archive], self.output / 'default')

    def test_actual_conservation_precedes_exact_selection_without_mutating_catalog_or_lock(self):
        before_lock, before_catalog = copy.deepcopy(self.lock), copy.deepcopy(stable.CATALOG)
        receipt = self.assemble()
        self.assertEqual(self.lock, before_lock)
        self.assertEqual(stable.CATALOG, before_catalog)
        self.assertEqual({row['uuid'] for row in receipt['packs']}, {'private-b', 'private-r', 'author-b', 'author-r'})
        proof = self.selection()
        self.assertEqual(receipt['upstream_selection'], proof)
        effective = copy.deepcopy(self.lock)
        effective['upstream'] = [self.author]
        effective['order'] = {'behavior': ['private-b', 'author-b'], 'resource': ['private-r', 'author-r']}
        self.assertEqual(receipt['lock_sha256'], self.sha(json.dumps(effective, sort_keys=True).encode()))
        self.assertEqual(proof['full_lock_sha256'], self.sha(json.dumps(self.lock, sort_keys=True).encode()))
        self.assertNotEqual(receipt['lock_sha256'], proof['full_lock_sha256'])
        self.assertEqual(receipt['acceptance'], {'static': True, 'bds': False, 'client': False, 'saved_world_migration': False})

    def test_committed_profile_baseline_and_private_target_are_required_even_when_working(self):
        for relative in (stable.CURATED_INPUT, 'baseline.json', '.repo-target.json'):
            path = self.root / relative
            raw = path.read_bytes()
            path.write_bytes(raw + b'\n')
            with self.subTest(relative=relative), self.assertRaises(SystemExit):
                self.assemble()
            path.write_bytes(raw)
        target_path = self.root / '.repo-target.json'
        value = json.loads(target_path.read_text())
        value['repository_id'] += 1
        self.fixture.write('.repo-target.json', value)
        self.fixture.commit('Wrong synthetic repository target')
        with self.assertRaisesRegex(SystemExit, 'private repository target differs'):
            self.assemble()

    def test_failed_current_runtime_proof_cannot_activate_selection(self):
        path = self.root / 'fixture-conservation.json'
        value = json.loads(path.read_text())
        value['conserved_files'] += 1
        path.write_text(json.dumps(value))
        with self.assertRaisesRegex(SystemExit, 'retained runtime rejected'):
            self.assemble()

    def test_selected_pin_must_match_name_archive_project_file_pair_and_author_version(self):
        mutations = [lambda row: row.update(name='Unknown'), lambda row: row.update(project_id=33),
                     lambda row: row.update(file_id=44), lambda row: row.update(sha256='a' * 64),
                     lambda row: row['packs'][0].update(uuid='changed'),
                     lambda row: row['packs'][0].update(version=[1, 0, 9]), lambda row: row['packs'].pop()]
        for mutate in mutations:
            lock = copy.deepcopy(self.lock)
            mutate(lock['upstream'][0])
            with self.subTest(mutate=mutate), self.assertRaises(ValueError):
                self.selection(lock)

    def test_full_catalog_partition_rejects_unknown_missing_duplicate_and_overlapping_authors(self):
        cases = []
        unknown = copy.deepcopy(self.author)
        unknown.update(name='Unreviewed', project_id=77, file_id=88, sha256='b' * 64,
                       packs=[{'uuid': 'new-b', 'version': [1, 0, 0]}, {'uuid': 'new-r', 'version': [1, 0, 0]}])
        cases.append([*self.lock['upstream'], unknown])
        cases.extend([[self.author], [*self.lock['upstream'], copy.deepcopy(self.author)]])
        for key in ('project_id', 'file_id', 'sha256'):
            rows = copy.deepcopy(self.lock['upstream'])
            rows[1][key] = rows[0][key]
            cases.append(rows)
        rows = copy.deepcopy(self.lock['upstream'])
        rows[1]['packs'][0]['uuid'] = rows[0]['packs'][0]['uuid']
        cases.append(rows)
        for rows in cases:
            with self.subTest(rows=rows), self.assertRaises(ValueError):
                self.selection({**self.lock, 'upstream': rows})
        self.catalog['upstream_selection']['deferred']['Cookery'] = {'upstream': self.author, 'reason': 'Not permitted.'}
        with self.assertRaisesRegex(ValueError, 'overlap'):
            self.selection()

    def test_deferred_complete_row_including_manifest_release_and_reason_is_exact(self):
        for mutate in [lambda row: row.update(manifest_compatibility_release='unreviewed'),
                       lambda row: row.pop('manifest_compatibility_release'),
                       lambda row: row.update(file_id=123), lambda row: row.update(sha256='c' * 64)]:
            lock = copy.deepcopy(self.lock)
            mutate(lock['upstream'][1])
            with self.subTest(mutate=mutate), self.assertRaisesRegex(ValueError, 'deferred author differs'):
                self.selection(lock)
        self.catalog['upstream_selection']['deferred']['BetterBiomes']['reason'] = '   '
        with self.assertRaisesRegex(ValueError, 'reason'):
            self.selection()

    def test_missing_or_malformed_selected_archive_is_still_rejected(self):
        with self.assertRaisesRegex(SystemExit, 'missing hash-pinned upstream archive: Cookery'):
            self.assemble(archives=[])
        for change in ('half', 'uuid', 'version', 'side'):
            manifests = copy.deepcopy(self.manifests)
            if change == 'half':
                manifests.pop()
            elif change == 'side':
                manifests[0]['modules'][0]['type'] = 'resources'
            else:
                manifests[0]['header'][change] = 'wrong' if change == 'uuid' else [9, 9, 9]
            self.write_archive(manifests)
            self.pin['sha256'] = self.author['sha256'] = self.sha(self.archive.read_bytes())
            self.sync_selection()
            with self.subTest(change=change), self.assertRaises(SystemExit):
                self.assemble()

    def test_reviewed_order_is_preserved_and_never_silently_filters_deferred_or_unknown_ids(self):
        order = {'behavior': ['author-b', 'private-b'], 'resource': ['private-r', 'author-r']}
        self.assertEqual(self.assemble(reviewed_order=order)['order'], order)
        for uid in (self.deferred['packs'][0]['uuid'], 'unknown'):
            changed = copy.deepcopy(order)
            changed['behavior'].append(uid)
            with self.subTest(uid=uid), self.assertRaisesRegex(SystemExit, 'reviewed order contains unknown'):
                self.assemble(reviewed_order=changed)

    def test_receipt_cannot_omit_active_pairs_inject_authors_or_disguise_deferred_as_preserved(self):
        receipt, expected = self.assemble(), self.selection()
        def remove(value, identifiers):
            value['packs'] = [row for row in value['packs'] if row['uuid'] not in identifiers]
            value['order'] = {side: [uid for uid in order if uid not in identifiers] for side, order in value['order'].items()}
        mutations = [lambda value: remove(value, {'author-b'}), lambda value: remove(value, {'author-b', 'author-r'}),
                     lambda value: value['packs'].append(copy.deepcopy(value['packs'][0]))]
        for uid, owner, archive in [(self.deferred['packs'][0]['uuid'], 'preserved', self.deferred['sha256']),
                                    ('renamed-deferred', 'preserved', self.deferred['sha256']),
                                    ('unselected-author', 'upstream', 'd' * 64)]:
            def add(value, uid=uid, owner=owner, archive=archive):
                value['packs'].append({'uuid': uid, 'side': 'behavior', 'version': [1, 0, 0],
                                       'source': {'owner': owner, 'archive_sha256': archive}})
                value['order']['behavior'].append(uid)
            mutations.append(add)
        for mutate in mutations:
            changed = copy.deepcopy(receipt)
            mutate(changed)
            with self.subTest(mutate=mutate), self.assertRaises(ValueError):
                stable.validate_curated_upstream_receipt(changed, expected)

    def test_receipt_binds_profile_policy_full_lock_owner_and_output_identities(self):
        receipt, expected = self.assemble(), self.selection()
        mutations = [lambda value: value.pop('upstream_selection'),
                     lambda value: value['upstream_selection'].update(full_lock_sha256='0' * 64),
                     lambda value: value['upstream_selection'].update(policy_sha256='0' * 64),
                     lambda value: value['upstream_selection']['profile'].update(sha256='0' * 64),
                     lambda value: value['upstream_selection']['owner'].update(commit='0' * 40),
                     lambda value: value['upstream_selection']['deferred'][0].update(reason='Changed'),
                     lambda value: value['packs'][0]['source'].update(commit='0' * 40)]
        for field, wrong in [('project_id', 111), ('file_id', 222), ('archive_sha256', '0' * 64)]:
            mutations.append(lambda value, field=field, wrong=wrong: next(row for row in value['packs'] if row['uuid'] == 'author-b')['source'].update({field: wrong}))
        mutations.append(lambda value: next(row for row in value['packs'] if row['uuid'] == 'author-b').update(version=[1, 0, 9]))
        for mutate in mutations:
            changed = copy.deepcopy(receipt)
            mutate(changed)
            with self.subTest(mutate=mutate), self.assertRaises(ValueError):
                stable.validate_curated_upstream_receipt(changed, expected)

    def test_formal_candidate_boundary_recomputes_selection_before_accepting_receipt(self):
        receipt = self.assemble()
        tavern = self.output / 'tavern'
        (tavern / 'family').mkdir(parents=True)
        (tavern / 'family/upstream.lock.json').write_text(json.dumps(self.lock))
        with patch.object(current.c, 'T', tavern):
            for change in ('proof', 'missing-pair'):
                altered = copy.deepcopy(receipt)
                if change == 'proof':
                    altered['upstream_selection']['owner']['commit'] = '0' * 40
                else:
                    altered['packs'] = [row for row in altered['packs'] if row['uuid'] != 'author-r']
                    altered['order']['resource'].remove('author-r')
                with self.subTest(change=change), self.assertRaisesRegex(ValueError, 'Curated upstream receipt'):
                    current.validate_candidate(altered, {}, self.baseline, {}, self.catalog)


if __name__ == '__main__':
    unittest.main()
