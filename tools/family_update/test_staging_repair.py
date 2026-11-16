"""Review fixed packs through the real loader, without a server or API calls."""
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

TOOLS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(TOOLS))
from family_update.source_batch import generated_pack


REVIEW = """
import json, sys
from pathlib import Path
sys.path.insert(0, sys.argv[1])
from family_update import common as c
c.configure(Path(sys.argv[2]))
from family_update import staging_repair
options = c.CONFIG['staging_repair']
_, _, binding = staging_repair.review_binding(
    Path(options['candidate_dir']), Path(options['source_batch']), Path(sys.argv[3]))
print(json.dumps(binding))
"""


class StagingReviewTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.sources = {}
        source_commits = {}
        for name in ('tavern', 'grilling', 'world-liquor'):
            source = self.root / name
            source.mkdir()
            self.write(source / 'baseline.json', {'repository': 'example/' + name})
            (source / 'README.md').write_text('Source documentation\n')
            if name == 'tavern':
                (source / 'tools').mkdir()
                for tool in ('family_guard.py', 'world_backup.py'):
                    shutil.copy2(TOOLS / tool, source / 'tools' / tool)
            self.git(source, 'init', '-q')
            self.git(source, 'add', '.')
            self.git(source, 'commit', '-qm', 'Generation source')
            self.sources[name] = source
            source_commits[name] = {'path': str(source), 'commit': self.git(source, 'rev-parse', 'HEAD')}

        self.candidate = self.root / 'candidate'
        self.inputs = self.root / 'inputs'
        ids = {'BP': '11111111-1111-4111-8111-111111111111',
               'RP': '22222222-2222-4222-8222-222222222222'}
        receipt = {'schema': 1, 'order': {}, 'packs': []}
        batch = {'source_commits': source_commits, 'packs': {}}
        for side, uid in ids.items():
            other = ids['RP' if side == 'BP' else 'BP']
            root = self.inputs / side
            root.mkdir(parents=True)
            manifest = {'header': {'uuid': uid, 'version': [1, 0, 1]},
                        'modules': [{'uuid': '33333333-3333-4333-8333-33333333333' + str(len(receipt['packs'])),
                                     'type': 'data' if side == 'BP' else 'resources', 'version': [1, 0, 1]}],
                        'dependencies': [{'uuid': other, 'version': [1, 0, 1]}]}
            self.write(root / 'manifest.json', manifest)
            (root / 'payload.txt').write_text('Reviewed payload\n')
            _, row, files = generated_pack('Tavern', side, root)
            batch['packs'][uid] = row
            family_side = 'behavior' if side == 'BP' else 'resource'
            receipt['order'][family_side] = [uid]
            receipt['packs'].append({
                'uuid': uid, 'side': family_side, 'version': row['version'],
                'files': files, 'dependencies': row['dependencies'],
                'source': {'owner': 'owned', 'repository': 'example/tavern',
                           'commit': source_commits['tavern']['commit']}})
            shutil.copytree(root, self.candidate / (family_side + '_packs') / uid)
            self.write(self.candidate / ('world_' + family_side + '_packs.json'),
                       [{'pack_id': uid, 'version': row['version']}])
        self.write(self.candidate / 'family-receipt.json', receipt)
        self.batch = self.root / 'source-batch.json'
        self.write(self.batch, batch)
        self.live = self.root / 'live.json'
        self.write(self.live, {})
        authorization = self.root / 'authorization.json'
        self.write(authorization, {})
        adapter = self.root / 'api.py'
        adapter.write_text('raise RuntimeError("Review must not load the API adapter")\n')
        self.config = self.root / 'config.json'
        self.write(self.config, {
            'schema': 1, 'server_name': 'example-staging',
            'bds_root': str(self.root / 'server'), 'world_dir': str(self.root / 'server/worlds/existing'),
            'quality_dir': str(self.root / 'quality'), 'output_dir': str(self.root / 'deployment'),
            'sources': {name: str(path) for name, path in self.sources.items()},
            'api_module': str(adapter), 'authorization_file': str(authorization),
            'lease_file': str(self.root / 'maintenance.json'), 'lock_file': str(self.root / 'maintenance.lock'),
            'python': sys.executable,
            'startup_markers': ['Server started.', 'Registered kaleidoscope_world_liquor',
                                '[Cookery board API 0.1.0] registered kaleidoscope_grilling:chopping_board/chicken_skin'],
            'staging_repair': {'candidate_dir': str(self.candidate), 'source_batch': str(self.batch),
                               'review_file': str(self.root / 'review.json'), 'retire_uuids': []}})

    @staticmethod
    def write(path, value):
        path.write_text(json.dumps(value))

    @staticmethod
    def git(path, *args):
        return subprocess.check_output([
            'git', '-c', 'user.name=Review boundary test', '-c', 'user.email=review@example.invalid',
            '-c', 'commit.gpgsign=false', '-c', 'core.hooksPath=/dev/null', '-C', str(path), *args], text=True).strip()

    def review(self):
        return subprocess.run([sys.executable, '-B', '-c', REVIEW, str(TOOLS), str(self.config), str(self.live)],
                              capture_output=True, text=True)

    def binding(self):
        result = self.review()
        self.assertEqual(result.returncode, 0, result.stderr)
        return json.loads(result.stdout)

    def test_unrelated_tracked_untracked_and_new_commit_keep_review_valid(self):
        before = self.binding()
        source = self.sources['tavern']
        (source / 'README.md').write_text('Unrelated documentation edit\n')
        (source / 'draft.txt').write_text('Untracked notes\n')
        self.assertEqual(self.binding(), before)
        self.git(source, 'add', 'README.md')
        self.git(source, 'commit', '-qm', 'Unrelated documentation update')
        self.assertEqual(self.binding(), before)

    def test_generated_pack_byte_change_rejects_review(self):
        self.binding()
        (self.inputs / 'BP/payload.txt').write_text('Changed after review\n')
        result = self.review()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('Normally generated input changed', result.stderr)

    def test_candidate_byte_change_rejects_review(self):
        self.binding()
        payload = next((self.candidate / 'resource_packs').glob('*/payload.txt'))
        payload.write_text('Changed after review\n')
        result = self.review()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('Candidate pack bytes differ', result.stderr)

    def test_separate_selected_tools_bind_the_actual_loaded_files(self):
        before = self.binding()
        selected = self.sources['tavern'] / 'tools'
        for name in ('world_backup.py', 'family_guard.py'):
            with self.subTest(tool=name):
                self.assertIn(str(selected / name), before['runner_sha256'])
                self.assertNotIn(str(TOOLS / name), before['runner_sha256'])
                path = selected / name
                path.write_text(path.read_text() + '\n# Changed deployment implementation.\n')
                after = self.binding()
                self.assertNotEqual(after, before)
                before = after


if __name__ == '__main__':
    unittest.main()
