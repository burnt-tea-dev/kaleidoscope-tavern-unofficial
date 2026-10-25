"""Native proof reuse boundaries; temporary Git repositories, no BDS or network."""
import copy
import io
import json
import pathlib
import subprocess
import tempfile
import unittest
from unittest import mock
import zipfile

import reuse_ci_evidence as reuse


def write(root, name, value):
    target = root / name
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(value)


def command(root, *args):
    return subprocess.check_output(['git', '-C', str(root), *args], stderr=subprocess.DEVNULL).decode().strip()


def commit(root, name):
    command(root, 'add', '.')
    command(root, 'commit', '-qm', name)
    return command(root, 'rev-parse', 'HEAD')


def repository(root, remote):
    root.mkdir()
    command(root, 'init', '-q', '-b', 'main')
    # Git can detach automatic maintenance after a synchronous commit; fixture
    # cleanup must not race another writer in its temporary object directory.
    command(root, 'config', 'maintenance.auto', 'false')
    command(root, 'config', 'gc.auto', '0')
    command(root, 'config', 'user.email', 'native-reuse-test@example.invalid')
    command(root, 'config', 'user.name', 'Native proof test')
    command(root, 'remote', 'add', 'origin', 'https://github.com/' + remote + '.git')


def archive(files):
    output = io.BytesIO()
    with zipfile.ZipFile(output, 'w') as target:
        for name, raw in files.items():
            target.writestr(name, raw)
    return output.getvalue()


class FakeAPI:
    def __init__(self, rows):
        self.rows, self.requests = rows, []

    def json(self, route):
        self.requests.append(route)
        value = self.rows[route]
        if isinstance(value, Exception):
            raise value
        return copy.deepcopy(value)

    def read(self, route, limit):
        self.requests.append(route)
        value = self.rows[route]
        if isinstance(value, Exception):
            raise value
        return value


class ReuseTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base = pathlib.Path(self.temp.name)
        self.root, self.peer = self.base / 'tavern', self.base / 'liquor'
        repository(self.peer, reuse.PEER_REPOSITORY)
        for name in ('runtime/BP/manifest.json', 'runtime/RP/manifest.json', 'baseline.json'):
            write(self.peer, name, '{}\n')
        self.peer_sha = commit(self.peer, 'peer runtime')
        repository(self.root, reuse.REPOSITORY)
        for name in ('runtime/BP/manifest.json', 'runtime/RP/manifest.json', 'baseline.json') + reuse.CLOSURE:
            write(self.root, name, '{}\n')
        self.workflow = ('name: Test\non:\n  pull_request:\njobs:\n  native-persistence:\n'
                         '    runs-on: ubuntu-latest\n    steps:\n      - uses: actions/checkout@v4\n'
                         '        with:\n          repository: ' + reuse.PEER_REPOSITORY + '\n'
                         '          ref: ' + self.peer_sha + '\n'
                         '          path: .source-check/world-liquor-native\n'
                         '          persist-credentials: false\n'
                         '      - name: Native\n        run: python native.py --port 27200\n')
        write(self.root, reuse.WORKFLOW, self.workflow)
        self.old = commit(self.root, 'original native inputs')
        write(self.root, 'README.md', 'metadata only\n')
        self.current = commit(self.root, 'metadata change')
        self.env = {'GITHUB_REPOSITORY': reuse.REPOSITORY, 'GITHUB_RUN_ID': '20', 'GITHUB_SHA': self.current}
        self.run = dict(id=10, status='completed', conclusion='failure', event='pull_request',
                        head_sha=self.old, head_branch='topic', workflow_id=2, run_attempt=1,
                        repository={'id': 1}, head_repository={'id': 1})
        self.current_run = dict(id=20, event='pull_request', head_sha=self.current, head_branch='topic',
                                workflow_id=2, repository={'id': 1, 'full_name': reuse.REPOSITORY},
                                head_repository={'id': 1}, path=reuse.WORKFLOW)
        self.job = dict(id=30, run_id=10, status='completed', name='native-persistence', conclusion='success',
                        steps=[dict(name=name, conclusion='success') for name in reuse.EXECUTION_STEPS +
                               ('Reject incomplete or relabeled native evidence', 'Run actions/upload-artifact@v4')])
        self.report = {'sources': {'tavern': {'commit': self.old}, 'liquor': {'commit': self.peer_sha}}, 'engine': {}}
        self.files = {name: b'original evidence\n' for name in reuse.FILES}
        self.files['t133-paired-native/native-living-report.json'] = json.dumps(self.report).encode()
        self.zip = archive(self.files)
        self.metadata = dict(id=40, name=reuse.ARTIFACT, size_in_bytes=len(self.zip), digest='sha256:' + reuse.sha(self.zip),
                             expired=False, workflow_run={'id': 10, 'head_sha': self.old, 'repository_id': 1, 'head_repository_id': 1})
        log = (f'time [command]/usr/bin/git log -1 --format=%H\ntime {self.old}\n'
               f'time [command]/usr/bin/git log -1 --format=%H\ntime {self.peer_sha}\n'
               f'time SHA256 digest of uploaded artifact zip is {reuse.sha(self.zip)}\n'
               f'time Artifact {reuse.ARTIFACT}.zip successfully finalized. Artifact ID 40\n')
        self.api_base = '/repos/' + reuse.REPOSITORY
        self.routes = {
            '/actions/runs/20': self.current_run,
            '/actions/workflows/validation.yml/runs?per_page=10&branch=topic&event=pull_request': {'workflow_runs': [self.run]},
            '/actions/runs/10/attempts/1/jobs?per_page=100': {'jobs': [self.job]},
            '/actions/runs/10/artifacts?name=' + reuse.ARTIFACT + '&per_page=100': {'artifacts': [self.metadata]},
            '/actions/artifacts/40/zip': self.zip,
            '/actions/jobs/30/logs': log.encode(),
            '/git/commits/' + self.old: {'sha': self.old, 'parents': []},
        }

    def api(self):
        return FakeAPI({self.api_base + route: value for route, value in self.routes.items()})

    def select(self, api=None):
        with mock.patch.object(reuse, 'validate_original', return_value=self.report):
            return reuse.select_and_reuse(api or self.api(), self.root, self.peer, self.base / 'output', self.env)

    def test_exact_inputs_reuse_original_bytes_even_if_other_jobs_failed(self):
        self.assertTrue(self.select())
        output = self.base / 'output'
        self.assertEqual((output / 'original-artifact.zip').read_bytes(), self.zip)
        for name, raw in self.files.items():
            self.assertEqual((output / 'originals' / name).read_bytes(), raw)
        proof = json.loads((output / 'reuse-provenance.json').read_text())
        self.assertFalse(proof['nativeExecutedThisRun'])
        self.assertEqual(proof['original']['executedCommit'], self.old)
        self.assertEqual(proof['current']['commit'], self.current)

    def test_changed_native_input_requires_fresh_run(self):
        for name in ('runtime/BP/manifest.json', 'baseline.json', *reuse.CLOSURE):
            with self.subTest(path=name):
                original = (self.root / name).read_text()
                write(self.root, name, 'changed\n')
                self.env['GITHUB_SHA'] = commit(self.root, 'changed execution input')
                self.current_run['head_sha'] = self.env['GITHUB_SHA']
                self.assertFalse(self.select())
                write(self.root, name, original)
                self.env['GITHUB_SHA'] = commit(self.root, 'restore execution input')
                self.current_run['head_sha'] = self.env['GITHUB_SHA']
        self.assertFalse((self.base / 'output').exists())

    def test_added_selector_is_not_part_of_native_execution_inputs(self):
        write(self.root, 'tools/native/reuse_ci_evidence.py', '# new tooling\n')
        self.env['GITHUB_SHA'] = commit(self.root, 'add selector')
        self.current_run['head_sha'] = self.env['GITHUB_SHA']
        self.assertTrue(self.select())

    def test_revision_before_a_new_probe_is_an_input_mismatch(self):
        # Build an actual historical commit without one of today's probe files.
        command(self.root, 'checkout', '-qb', 'old-runtime', self.old)
        command(self.root, 'rm', '-q', reuse.CLOSURE[7])
        earlier = commit(self.root, 'release before potion observer')
        command(self.root, 'checkout', '-q', 'main')
        self.run['head_sha'] = earlier
        api = self.api()
        self.assertFalse(self.select(api))
        self.assertFalse(any('/artifacts' in route for route in api.requests))

    def test_unreadable_git_object_is_not_an_absent_historical_path(self):
        old_tree = command(self.root, 'rev-parse', self.old + '^{tree}')
        self.assertNotEqual(old_tree, command(self.root, 'rev-parse', 'HEAD^{tree}'))
        (self.root / '.git/objects' / old_tree[:2] / old_tree[2:]).unlink()
        # The commit still exists and today's tree remains readable, but an
        # unreadable old input tree must stop selection instead of returning false.
        command(self.root, 'cat-file', '-e', self.old + '^{commit}')
        with self.assertRaises(subprocess.CalledProcessError):
            self.select()
        self.assertFalse((self.base / 'output').exists())

    def test_unreadable_ancestry_is_not_an_unrelated_revision(self):
        middle = self.current
        write(self.root, 'README.md', 'another metadata change\n')
        self.env['GITHUB_SHA'] = commit(self.root, 'new current head')
        self.current_run['head_sha'] = self.env['GITHUB_SHA']
        (self.root / '.git/objects' / middle[:2] / middle[2:]).unlink()
        with self.assertRaises(subprocess.CalledProcessError):
            self.select()
        self.assertFalse((self.base / 'output').exists())

    def test_fork_or_skipped_original_execution_cannot_supply_proof(self):
        self.run['head_repository']['id'] = 9
        self.assertFalse(self.select())
        self.run['head_repository']['id'] = 1
        self.job['steps'][0]['conclusion'] = 'skipped'
        self.assertFalse(self.select())

    def test_matching_corrupt_or_missing_artifact_fails_closed(self):
        route = '/actions/runs/10/artifacts?name=' + reuse.ARTIFACT + '&per_page=100'
        for artifacts in ([], [dict(self.metadata, expired=True)], [dict(self.metadata, digest='sha256:' + '0' * 64)]):
            self.routes[route] = {'artifacts': artifacts}
            with self.assertRaises(ValueError):
                self.select()
            self.assertFalse((self.base / 'output').exists())
        self.routes[route] = ValueError('network unavailable')
        with self.assertRaises(ValueError):
            self.select()

    def test_current_checkout_and_original_upload_must_be_bound(self):
        self.env['GITHUB_SHA'] = self.old
        with self.assertRaises(ValueError):
            self.select()
        self.env['GITHUB_SHA'] = self.current
        self.routes['/actions/jobs/30/logs'] = self.routes['/actions/jobs/30/logs'].replace(reuse.sha(self.zip).encode(), b'0' * 64)
        with self.assertRaises(ValueError):
            self.select()

    def test_validator_failure_never_becomes_fresh(self):
        with mock.patch.object(reuse, 'validate_original', side_effect=AssertionError('incomplete restart')):
            with self.assertRaises(AssertionError):
                reuse.select_and_reuse(self.api(), self.root, self.peer, self.base / 'output', self.env)
        self.assertFalse((self.base / 'output').exists())

    def test_archive_rejects_extra_missing_duplicate_and_link_paths(self):
        for files in (dict(self.files, **{'../escape': b'bad'}), dict(list(self.files.items())[1:])):
            raw = archive(files)
            with self.assertRaises(ValueError):
                reuse.unpack_artifact(raw, dict(self.metadata, size_in_bytes=len(raw), digest='sha256:' + reuse.sha(raw)))
        output = io.BytesIO()
        with zipfile.ZipFile(output, 'w') as target:
            for index, (name, raw) in enumerate(self.files.items()):
                info = zipfile.ZipInfo(name)
                info.external_attr = ((0o120777 if index == 0 else 0o100644) << 16)
                target.writestr(info, raw)
        raw = output.getvalue()
        with self.assertRaises(ValueError):
            reuse.unpack_artifact(raw, dict(self.metadata, size_in_bytes=len(raw), digest='sha256:' + reuse.sha(raw)))

    def test_workflow_keeps_commands_environment_and_global_defaults_in_contract(self):
        original, peer = reuse.workflow_contract(self.workflow)
        self.assertEqual(peer, self.peer_sha)
        for changed in (self.workflow.replace('--port 27200', '--port 27210'),
                        self.workflow.replace('    steps:', '    env:\n      UNSAFE: true\n    steps:'),
                        'defaults:\n  run:\n    shell: sh\n' + self.workflow):
            self.assertNotEqual(reuse.workflow_contract(changed)[0], original)
        changed_peer = self.workflow.replace(self.peer_sha, '1' * 40)
        self.assertEqual(reuse.workflow_contract(changed_peer), (original, '1' * 40))

    def test_exact_source_relationship_survives_squash_merge(self):
        # Original CI occurs on a feature commit, then metadata-only repairs are
        # squashed into main. The original commit is deliberately not an ancestor.
        command(self.root, 'checkout', '-qb', 'feature')
        write(self.root, 'feature.txt', 'native runtime change\n')
        original = commit(self.root, 'feature runtime')
        write(self.root, 'README.md', 'later CI repair\n')
        final_head = commit(self.root, 'metadata repair')
        command(self.root, 'checkout', '-q', 'main')
        command(self.root, 'merge', '--squash', 'feature')
        merged = commit(self.root, 'squash feature')
        self.assertFalse(reuse.ancestor(self.root, original, 'HEAD'))
        run = dict(self.run, head_sha=original, pull_requests=[{'number': 7}])
        pull = dict(number=7, merged=True, merge_commit_sha=merged,
                    base={'ref': 'main', 'repo': {'id': 1}}, head={'sha': final_head, 'repo': {'id': 1}})
        api = FakeAPI({self.api_base + '/pulls/7': pull})
        relation = reuse.related_run(api, self.root, run, 1)
        self.assertEqual(relation['kind'], 'merged-pull-request')
        self.assertEqual(relation['mergeCommit'], merged)
        pull['head']['repo']['id'] = 9
        self.assertIsNone(reuse.related_run(api, self.root, run, 1))
        pull['head']['repo']['id'] = 1
        pull['head']['sha'] = original  # Final tree no longer equals merged tree.
        self.assertIsNone(reuse.related_run(api, self.root, run, 1))


if __name__ == '__main__':
    unittest.main()
