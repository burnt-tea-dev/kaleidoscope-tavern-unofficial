"""The inventory exception is bound to committed review and canonical Git trees."""
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from family_update import common as c
from family_update import current_inventory_review as m
from family_update.managed_drift_recovery import files_sha256, inventory_sha256


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, sort_keys=True) + '\n')


def commit(root, message):
    subprocess.run(['git', 'add', '.'], cwd=root, check=True)
    subprocess.run(['git', '-c', 'user.name=Review Test', '-c', 'user.email=review@example.invalid',
                    'commit', '-q', '-m', message], cwd=root, check=True)
    return subprocess.check_output(['git', '-C', str(root), 'rev-parse', 'HEAD'], text=True).strip()


class CurrentInventoryReviewTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(); self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.owned = {}
        self.rows = []
        self.commits = {}
        self.extension = self.root / 'extension'
        self.sources = {key: self.root / key for key in ['tavern', 'grilling', 'world-liquor']}
        self.roots = {**self.sources, 'extension': self.extension}
        for key, root in self.roots.items():
            root.mkdir()
            subprocess.run(['git', 'init', '-q', '-b', 'main', str(root)], check=True)
            packs = {'BP': {}, 'RP': {}}
            for side in ['BP', 'RP']:
                uid = self.uid(key, side)
                version = [1, 0, len(packs[side]) + 1]
                base = ('runtime/' + side) if key in ('tavern', 'extension', 'world-liquor') else ('projects/grilling/gameplay_core/' + ('behavior_pack' if side == 'BP' else 'resource_pack'))
                runtime = root / base
                manifest = {'header': {'uuid': uid, 'version': version}, 'modules': [], 'dependencies': []}
                write(runtime / 'manifest.json', manifest)
                (runtime / 'scripts').mkdir(parents=True, exist_ok=True)
                (runtime / 'scripts/main.js').write_text(key + side)
                packs[side] = {'uuid': uid, 'version': version}
                self.owned[uid] = {'repository_key': key, 'runtime_path': base,
                                   'dependency_repins': []}
            runtime = {'BP': 'runtime/BP', 'RP': 'runtime/RP'} if key != 'grilling' else {
                'BP': 'projects/grilling/gameplay_core/behavior_pack',
                'RP': 'projects/grilling/gameplay_core/resource_pack'}
            write(root / 'baseline.json', {'repository': 'test/' + key, 'version': [1, 0, 1],
                                           'runtime': runtime, 'packs': packs})
            self.commits[key] = commit(root, 'Canonical source')
        self.live = self.root / 'live'; self.live.mkdir()
        pack_rows = []
        refs = {'behavior': [], 'resource': []}
        # Eight owned identities use the four committed source trees above.
        for key, root in self.roots.items():
            for side, packside in [('behavior', 'BP'), ('resource', 'RP')]:
                uid = self.uid(key, packside)
                version = [1, 0, 1]
                source_path = self.owned[uid]['runtime_path']
                source_files = self._files(root, self.commits[key], source_path)
                live_path = self.live / uid
                for name in source_files:
                    raw = subprocess.check_output(['git', '-C', str(root), 'show', self.commits[key] + ':' + source_path + '/' + name])
                    (live_path / name).parent.mkdir(parents=True, exist_ok=True)
                    (live_path / name).write_bytes(raw)
                files = {name: hashlib.sha256((live_path / name).read_bytes()).hexdigest() for name in source_files}
                row = {'uuid': uid, 'side': side, 'version': version, 'path': str(live_path), 'files': files}
                self.rows.append(row); pack_rows.append({k: row[k] for k in ('uuid', 'side', 'version', 'files')})
                refs[side].append({'pack_id': uid, 'version': version})
        # Several other packs are unchanged receipt rows.
        for index in range(3):
            side = 'behavior' if index < 22 else 'resource'
            uid = f'00000000-0000-4000-8000-{index+1:012d}'
            version = [1, 0, index]
            files = {'manifest.json': hashlib.sha256(uid.encode()).hexdigest()}
            live_path = self.live / uid; live_path.mkdir()
            (live_path / 'manifest.json').write_text(uid)
            row = {'uuid': uid, 'side': side, 'version': version, 'path': str(live_path), 'files': files}
            self.rows.append(row); pack_rows.append({k: row[k] for k in ('uuid', 'side', 'version', 'files')})
            refs[side].append({'pack_id': uid, 'version': version})
        refs = {side: [ref for ref in refs[side]] for side in ['behavior', 'resource']}
        self.inventory = {'packs': self.rows, 'refs': refs}
        self.receipt = {'packs': pack_rows[:-1],
                        'order': {side: [r['pack_id'] for r in refs[side] if r['pack_id'] != pack_rows[-1]['uuid']] for side in refs}}
        self.receipt_path = self.root / 'approved.json'; write(self.receipt_path, self.receipt)
        self.policy_path = self.root / 'senluo-policy.json'
        write(self.policy_path, {'approved_receipt': str(self.receipt_path)})
        self.policy_bytes = self.policy_path.read_bytes()
        self.review_path = self.extension / 'maintenance/reviews/current.json'
        added = self.rows[-1]
        profile = {'retained_inputs': [{'uuid': added['uuid'], 'side': added['side'],
                                        'version': added['version'],
                                        'output_tree': {'sha256': files_sha256(added['files']), 'files': len(added['files'])}}],
                   'replacement_packs': {}}
        self.profile_sha = 'a' * 64
        self.enterContext(patch.object(m, '_profile', return_value=(profile, self.profile_sha)))
        self.enterContext(patch.object(m, '_SOURCE_STATE', None))
        self.enterContext(patch.object(m, '_SOURCE_STATE_KEY', None))
        self.enterContext(patch.object(c, 'source_state', side_effect=lambda verify_remote=False: {
            key: {'path': str(root), 'commit': subprocess.check_output(['git', '-C', str(root), 'rev-parse', 'HEAD'], text=True).strip(),
                  'repository': 'test/' + key}
            for key, root in self.roots.items()}))
        self.enterContext(patch.multiple(c, EXTENSION=self.extension, SOURCES=self.sources,
                         CONFIG={'current_inventory_review': str(self.review_path)}))
        self._write_review()

    @staticmethod
    def uid(key, side):
        number = {'tavern': 1, 'grilling': 2, 'world-liquor': 3, 'extension': 4}[key] * 10 + (1 if side == 'BP' else 2)
        return f'10000000-0000-4000-8000-{number:012d}'

    @staticmethod
    def _files(root, commit_id, runtime):
        names = subprocess.check_output(['git', '-C', str(root), 'ls-tree', '-r', '--name-only', commit_id, '--', runtime], text=True).splitlines()
        prefix = runtime + '/'
        return {name[len(prefix):]: hashlib.sha256(subprocess.check_output(['git', '-C', str(root), 'show', commit_id + ':' + name])).hexdigest() for name in names}

    def _write_review(self):
        review_packs = {}
        for row in self.rows:
            review_packs[row['uuid']] = {'side': row['side'], 'version': row['version'],
                                         'tree': {'sha256': files_sha256(row['files']), 'files': len(row['files'])}}
        self.review = {'schema': 1, 'kind': 'owner_current_inventory',
                       'authorization': {'source': 'user', 'request': 'test authorization', 'at': '2026-10-31T00:00:00Z'},
                       'prior_receipt_sha256': c.sha(self.receipt_path),
                       'observed_inventory_sha256': inventory_sha256(self.inventory),
                       'curated_profile_sha256': self.profile_sha, 'packs': review_packs,
                       'owned_sources': {uid: {**source, 'commit': self.commits[source['repository_key']]}
                                         for uid, source in self.owned.items()}}
        write(self.review_path, self.review)
        commit(self.extension, 'Commit reviewed inventory')

    def _commit_review(self):
        write(self.review_path, self.review)
        commit(self.extension, 'Commit adjusted test review')
        m._SOURCE_STATE = None
        m._SOURCE_STATE_KEY = None

    def test_reviewed_inventory_returns_only_new_non_owned_preserved_uuids(self):
        preserved = m.verify(self.inventory, {'approved_receipt': str(self.receipt_path)})
        self.assertEqual(len(preserved), 1)
        self.assertFalse(preserved & set(self.owned))
        self.assertEqual(self.policy_path.read_bytes(), self.policy_bytes)

    def test_unreviewed_owned_script_change_is_rejected(self):
        row = next(row for row in self.rows if row['uuid'] in self.owned)
        path = Path(row['path']) / 'scripts/main.js'
        path.write_text('tampered')
        row['files']['scripts/main.js'] = hashlib.sha256(b'tampered').hexdigest()
        self.review['observed_inventory_sha256'] = inventory_sha256(self.inventory)
        self.review['packs'][row['uuid']]['tree'] = {'sha256': files_sha256(row['files']), 'files': len(row['files'])}
        write(self.review_path, self.review)
        commit(self.extension, 'Commit forged script inventory claim')
        with self.assertRaisesRegex(AssertionError, 'Owned runtime differs from canonical committed source'):
            m.verify(self.inventory, {'approved_receipt': str(self.receipt_path)})

    def test_approved_receipt_does_not_require_old_review_file(self):
        self.review_path.unlink()
        exact = {'packs': [{k: row[k] for k in ('uuid', 'side', 'version', 'files')} for row in self.inventory['packs']],
                 'order': {side: [ref['pack_id'] for ref in self.inventory['refs'][side]] for side in self.inventory['refs']}}
        exact_path = self.root / 'approved-exact.json'; write(exact_path, exact)
        self.assertEqual(m.verify(self.inventory, {'approved_receipt': str(exact_path)}), set())

    def test_prior_receipt_digest_change_is_rejected(self):
        self.review['prior_receipt_sha256'] = '0' * 64
        self._commit_review()
        with self.assertRaisesRegex(AssertionError, 'Prior approved receipt changed'):
            m.verify(self.inventory, {'approved_receipt': str(self.receipt_path)})

    def test_curated_profile_digest_change_is_rejected(self):
        self.review['curated_profile_sha256'] = '0' * 64
        self._commit_review()
        with self.assertRaisesRegex(AssertionError, 'Curated profile differs'):
            m.verify(self.inventory, {'approved_receipt': str(self.receipt_path)})

    def test_captured_inventory_byte_change_is_rejected(self):
        row = self.rows[-2]
        row['files']['manifest.json'] = '0' * 64
        with self.assertRaisesRegex(AssertionError, 'Observed inventory differs'):
            m.verify(self.inventory, {'approved_receipt': str(self.receipt_path)})

    def test_unregistered_new_pack_is_rejected(self):
        source = self.rows[-1]
        uid = '20000000-0000-4000-8000-000000000001'
        row = {**source, 'uuid': uid, 'version': [1, 0, 7], 'files': dict(source['files'])}
        self.rows.append(row)
        self.inventory['refs'][row['side']].append({'pack_id': uid, 'version': row['version']})
        self.review['observed_inventory_sha256'] = inventory_sha256(self.inventory)
        self._commit_review()
        with self.assertRaisesRegex(AssertionError, 'Observed pack set differs'):
            m.verify(self.inventory, {'approved_receipt': str(self.receipt_path)})

    def test_owned_manifest_non_dependency_change_is_rejected(self):
        row = next(row for row in self.rows if row['uuid'] in self.owned)
        path = Path(row['path']) / 'manifest.json'
        manifest = json.loads(path.read_text())
        manifest['header']['name'] = 'tampered'
        write(path, manifest)
        row['files']['manifest.json'] = hashlib.sha256(path.read_bytes()).hexdigest()
        self.review['observed_inventory_sha256'] = inventory_sha256(self.inventory)
        self.review['packs'][row['uuid']]['tree'] = {'sha256': files_sha256(row['files']), 'files': len(row['files'])}
        self._commit_review()
        with self.assertRaisesRegex(AssertionError, 'Owned manifest changed outside'):
            m.verify(self.inventory, {'approved_receipt': str(self.receipt_path)})


if __name__ == '__main__':
    unittest.main()
