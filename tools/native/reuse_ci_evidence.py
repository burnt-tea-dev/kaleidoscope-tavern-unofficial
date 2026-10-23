#!/usr/bin/env python3
"""Reuse original native CI proof only for identical execution inputs.

This does not run BDS or rewrite a receipt. GitHub's original successful job,
immutable artifact digest, complete logs and current validators are all required.
No matching inputs permits a fresh run; an unavailable or corrupt matching proof
is an error, never an excuse to silently rerun an unchanged native world.
"""
import argparse
import ast
import hashlib
import io
import json
import os
import pathlib
import re
import stat
import subprocess
import sys
import urllib.error
import urllib.parse
import urllib.request
import zipfile

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'tools/native'))
sys.path.insert(0, str(ROOT / 'tools/pickup'))
import record_shaker_migration as recorder
import run_native_smoke as pickup

REPOSITORY = 'burnt-tea-dev/kaleidoscope-tavern-unofficial'
PEER_REPOSITORY = 'burnt-tea-dev/kaleidoscope-world-liquor-unofficial'
WORKFLOW = '.github/workflows/validation.yml'
ARTIFACT = 'pickup-native-persistence-evidence'
CLOSURE = (
    'tools/pickup/run_native_smoke.py', 'tools/pickup/native-storage-smoke.js',
    'tools/native/run_living_effects.py', 'tools/native/record_shaker_migration.py',
    'tools/native/shaker-migration-probe.js', 'tools/native/machine-ingredients-probe.js',
    'tools/native/status-aura-probe.js', 'tools/native/potion-bottle-probe.js',
    'tools/native/living-probe-entity.json', 'tools/native/health-helper-entity.json',
    'tools/baseline_gate.py', 'data/java-parity/potion-colors.json',
)
FILES = frozenset(
    ['pickup-native/native-storage-evidence.json']
    + [f'pickup-native/stage-{n}{suffix}' for n in (1, 2)
       for suffix in ('.log', '-runner-validation.json')]
    + ['t133-paired-native/' + name for name in (
        'first.log', 'restart.log', 'native-living-report.json',
        recorder.EVIDENCE_NAME, recorder.LOG_NAME)]
)
EXECUTION_STEPS = (
    'Native isolated inventory save/restart, no player sessions',
    'Complete Tavern and World Liquor load, migration, effects and restart, zero players',
    'Bind complete native observations to exact source and overlay bytes',
)
OVERLAY_FILES = {
    'scripts/living-effects-probe.js': 'tools/native/shaker-migration-probe.js',
    'entities/living-probe.json': 'tools/native/living-probe-entity.json',
    'entities/health-helper-probe.json': 'tools/native/health-helper-entity.json',
    'scripts/machine-ingredients-probe.js': 'tools/native/machine-ingredients-probe.js',
    'scripts/potion-bottle-probe.js': 'tools/native/potion-bottle-probe.js',
    'scripts/status-aura-probe.js': 'tools/native/status-aura-probe.js',
}


class ReuseError(ValueError):
    """A deliberately credential-free diagnostic safe to show in CI."""


def require(condition, message):
    if not condition:
        raise ReuseError(message)


def sha(data):
    return hashlib.sha256(data).hexdigest()


def git(root, *args):
    return subprocess.check_output(['git', '-C', str(root), *args], stderr=subprocess.PIPE).decode().strip()


def ensure_commit(root, commit):
    require(re.fullmatch(r'[0-9a-f]{40}', commit), 'invalid source commit')
    if subprocess.run(['git', '-C', str(root), 'cat-file', '-e', commit + '^{commit}'],
                      stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL).returncode:
        # Both origins were checked against fixed public canonical repositories.
        subprocess.run(['git', '-C', str(root), 'fetch', '--no-tags', 'origin', commit],
                       check=True, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)


def snapshot(root, commit, host=False, allow_missing=False):
    paths = ('runtime', 'baseline.json') + (CLOSURE if host else ())
    rows = git(root, 'ls-tree', '--full-tree', '-z', commit, '--', *paths)
    objects = {}
    for row in rows.split('\0'):
        if not row:
            continue
        entry, name = row.split('\t', 1)
        mode, kind, object_id = entry.split()
        require(kind == ('tree' if name == 'runtime' else 'blob'), 'unexpected execution input object type')
        require(mode == '040000' if name == 'runtime' else mode in ('100644', '100755'),
                'execution input is a link or unsupported Git mode')
        objects[name] = object_id
    if set(objects) != set(paths):
        if allow_missing and set(objects) < set(paths):
            return None
        raise ReuseError('execution input paths are missing or ambiguous')
    return objects


def working_source(root, repository, host=False):
    require(git(root, 'remote', 'get-url', 'origin').removesuffix('.git') == 'https://github.com/' + repository,
            'source origin is not the canonical public repository')
    paths = ('runtime', 'baseline.json') + (CLOSURE if host else ())
    require(not git(root, 'status', '--porcelain', '--untracked-files=all', '--', *paths),
            'native execution inputs contain uncommitted files')
    commit = git(root, 'rev-parse', 'HEAD')
    return commit, snapshot(root, commit, host)


def workflow_contract(text):
    """Compare exact workflow text, allowing only the declared reuse wiring.

    Everything outside this job is irrelevant except the complete global prefix.
    No general YAML rewriting can accidentally discard environment or run options.
    A changed command, setup step, action, runner or global setting fails equality.
    """
    prefix, jobs = text.split('\njobs:\n', 1)
    match = re.search(r'^  native-persistence:\n(.*?)(?=^  [\w-]+:|\Z)', jobs, re.M | re.S)
    require(match is not None, 'native job absent from workflow')
    job = match.group(0)
    peer = re.search(r'          repository: ' + re.escape(PEER_REPOSITORY)
                     + r'\n          ref: ([0-9a-f]{40})\n          path: \.source-check/world-liquor-native\n', job)
    require(peer is not None, 'native peer checkout is not an exact canonical revision')
    peer_commit = peer.group(1)
    job = job[:peer.start(1)] + '<peer-commit>' + job[peer.end(1):]
    wiring = (
        '    permissions:\n      contents: read\n      actions: read\n',
        '          fetch-depth: 0\n',
        "        if: steps.retained.outputs.reused == 'false'\n",
        '            ${{ runner.temp }}/native-reuse/\n',
    )
    for item in wiring:
        job = job.replace(item, '')
    job = job.replace('        run: |\n          python tools/native/test_record_shaker_migration.py\n'
                      '          python tools/native/test_reuse_ci_evidence.py\n',
                      '        run: python tools/native/test_record_shaker_migration.py\n')
    selection = ('      - id: retained\n'
                 '        name: Verify previous native success for identical execution inputs\n'
                 '        env:\n          GH_TOKEN: ${{ github.token }}\n'
                 '        run: python tools/native/reuse_ci_evidence.py --liquor .source-check/world-liquor-native --output "$RUNNER_TEMP/native-reuse"\n')
    job = job.replace(selection, '')
    guard = ('      - name: Require an explicit native evidence decision\n'
             '        env:\n          NATIVE_EVIDENCE_REUSED: ${{ steps.retained.outputs.reused }}\n'
             '        run: |\n          case "$NATIVE_EVIDENCE_REUSED" in\n'
             '            true|false) ;;\n'
             '            *) echo "Missing or invalid native evidence decision" >&2; exit 1 ;;\n'
             '          esac\n')
    job = job.replace(guard, '')
    return prefix + '\njobs:\n' + job, peer_commit


class SafeRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, request, fp, code, msg, headers, newurl):
        require(urllib.parse.urlparse(newurl).scheme == 'https', 'insecure GitHub download redirect')
        redirected = super().redirect_request(request, fp, code, msg, headers, newurl)
        # Signed artifact/log storage URLs do not need the GitHub credential.
        if redirected is not None:
            redirected.remove_header('Authorization')
        return redirected


class GitHub:
    def __init__(self, token):
        require(bool(token), 'GitHub read token missing')
        self.token = token
        self.opener = urllib.request.build_opener(SafeRedirect())

    def read(self, route, limit=4 * 1024 * 1024):
        require(route.startswith('/repos/'), 'unexpected GitHub API route')
        request = urllib.request.Request('https://api.github.com' + route, headers={
            'Authorization': 'Bearer ' + self.token, 'Accept': 'application/vnd.github+json',
            'X-GitHub-Api-Version': '2022-11-28', 'User-Agent': 'senluo-native-evidence-reuse'})
        try:
            with self.opener.open(request, timeout=45) as response:
                raw = response.read(limit + 1)
        except urllib.error.HTTPError as error:
            raise ReuseError('GitHub evidence request failed: HTTP ' + str(error.code)) from None
        except urllib.error.URLError:
            raise ReuseError('GitHub evidence request failed') from None
        require(len(raw) <= limit, 'GitHub response exceeds evidence size bound')
        return raw

    def json(self, route):
        return json.loads(self.read(route))


def original_job(job):
    if job.get('name') != 'native-persistence' or job.get('conclusion') != 'success':
        return False
    steps = job.get('steps', [])
    for name in EXECUTION_STEPS + ('Reject incomplete or relabeled native evidence', 'Run actions/upload-artifact@v4'):
        matches = [row for row in steps if row.get('name') == name]
        if len(matches) != 1 or matches[0].get('conclusion') != 'success':
            return False
    # An original run may have searched for reuse and then genuinely run BDS.
    # Reuse-chain jobs have skipped execution steps and are excluded above.
    return True


def unpack_artifact(raw, metadata):
    require(metadata.get('expired') is False, 'matching original artifact expired')
    require(metadata.get('size_in_bytes') == len(raw), 'original artifact size mismatch')
    require(metadata.get('digest') == 'sha256:' + sha(raw), 'original artifact digest mismatch')
    result = {}
    with zipfile.ZipFile(io.BytesIO(raw)) as archive:
        rows = archive.infolist()
        require(len(rows) == len(FILES) and {row.filename for row in rows} == FILES,
                'original artifact has missing, duplicate or unexpected paths')
        require(sum(row.file_size for row in rows) <= 8 * 1024 * 1024, 'expanded artifact too large')
        for row in rows:
            require(not row.is_dir() and not stat.S_ISLNK(row.external_attr >> 16), 'artifact contains a link/directory')
            result[row.filename] = archive.read(row)
    return result


def checkout_commits(log):
    lines = log.splitlines()
    commits = []
    for index, line in enumerate(lines[:-1]):
        if '[command]' in line and 'git log -1 --format=%H' in line:
            match = re.fullmatch(r'\S+ ([0-9a-f]{40})', lines[index + 1])
            require(match is not None, 'original checkout log lacks exact commit')
            commits.append(match.group(1))
    require(len(commits) == 2, 'original native job must have exactly two recorded checkouts')
    return commits


def pickup_sources(root):
    """Read the runner's literal copy contract instead of duplicating its list."""
    tree = ast.parse((root / 'tools/pickup/run_native_smoke.py').read_text())
    main = next(node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == 'main')
    assignments = {node.targets[0].id: node.value for node in main.body
                   if isinstance(node, ast.Assign) and isinstance(node.targets[0], ast.Name)}
    scripts = ast.literal_eval(assignments['scripts'])
    copies = ast.literal_eval(assignments['copies'].left)
    paths = [row[0] for row in copies] + ['runtime/BP/scripts/' + name for name in scripts]
    return {name: sha((root / name).read_bytes()) for name in paths}


def validate_original(files, root, liquor):
    """Revalidate retained bytes; no field in an original report is relabeled."""
    report = json.loads(files['t133-paired-native/native-living-report.json'])
    evidence = json.loads(files['t133-paired-native/' + recorder.EVIDENCE_NAME])
    pickup_raw = files['pickup-native/native-storage-evidence.json']
    receipt = json.loads(pickup_raw)
    for key, expected in {'native_script_behavior': True, 'client': False, 'full_family': False,
                          'live': False, 'test_only_host_overlay': True,
                          'copied_runtime_matches_frozen_source': True}.items():
        recorder.same(report[key], expected)
    sources = {}
    for label, source in (('tavern', root), ('liquor', liquor)):
        baseline = json.loads((source / 'baseline.json').read_bytes())
        trees = {kind: recorder.fingerprint(source / 'runtime' / kind)[0] for kind in ('BP', 'RP')}
        sources[label] = {'baseline': baseline, 'source_trees': trees, 'commit': report['sources'][label]['commit']}
    headers = {kind: json.loads((liquor / 'runtime' / kind / 'manifest.json').read_bytes())['header'] for kind in ('BP', 'RP')}
    generated = recorder.render_world_liquor_probe_inputs(sources['liquor']['baseline'], headers).encode()
    overlays = {name: sha((root / path).read_bytes()) for name, path in OVERLAY_FILES.items()}
    overlays['scripts/native-probe-inputs.js'] = sha(generated)
    overlays['scripts/main.js'] = recorder.MAIN_OVERLAY_NOTE
    recorder.validate_recorded_inputs(report, sources, overlays)
    inputs = {path: overlays[name] for name, path in OVERLAY_FILES.items()}
    inputs['generated/scripts/native-probe-inputs.js'] = sha(generated)
    recorder.same(evidence['observerInputsSHA256'], inputs)
    recorder.same(evidence['sourceTrees'], {name: source['source_trees'] for name, source in sources.items()})
    versions = {name: '.'.join(map(str, source['baseline']['version'])) for name, source in sources.items()}
    recorder.same(evidence['versions'], versions)
    for key, value in {'schema': 1, 'bdsVersion': '1.26.52.3', 'scriptAPI': '2.7.0',
                       'sourcePacksEqualNativeInputsExceptExplicitObserver': True,
                       'nativeServerSaveRestart': True, 'nativeCrossIdReadableMetadata': True,
                       'nativePutRecoveryAndRearm': True, 'playerSessions': 0, 'client': False,
                       'live': False, 'fpsMeasured': False, 'idleCallbacksMeasured': False,
                       'crossPackPrivateDataPreservation': False}.items():
        recorder.same(evidence[key], value)
    recorder.same([row['phase'] for row in report['reports']], ['first', 'restart'])
    summaries, registrations, filtered_logs = [], [], []
    for row in report['reports']:
        raw = files['t133-paired-native/' + row['phase'] + '.log']
        registrations.append(recorder.validate_phase(row, raw, versions['liquor']))
        summaries.append({**row, 'completeLogSHA256': sha(raw), 'completeLogBytes': len(raw),
                          'returnCode': 0, 'completeLogAdditionalChecks': True})
        filtered_logs.append('\n'.join(line for line in raw.decode().splitlines() if any(marker in line for marker in
                             ('Version:', 'Build ID:', 'Commit ID:', 'Pack Stack', '[LIVING_EFFECT_QA]',
                              'stop requested', 'Stopping server', 'Quit correctly'))))
    recorder.same(registrations[0], registrations[1])
    recorder.validate_potion_pair(report['reports'])
    recorder.same(evidence['reports'], summaries)
    require(files['t133-paired-native/' + recorder.LOG_NAME] == ('\n\n'.join(filtered_logs) + '\n').encode(),
            'filtered recorder log differs from complete original logs')
    recorder.same(receipt['sourceSHA256'], pickup_sources(root))
    recorder.same(receipt['bdsDownload'], pickup.URL)
    recorder.same(receipt['nativeServerSaveRestart'], True)
    recorder.same(receipt['playerSessions'], 0)
    recorder.same(sorted(receipt['stages']), ['1', '2'])
    for phase in (1, 2):
        validation = json.loads(files[f'pickup-native/stage-{phase}-runner-validation.json'])
        recorder.same(validation, {'accepted': True, 'returncode': 0, 'stopRequested': True,
                                   'completeOutputCaptured': True, 'violations': []})
        raw = files[f'pickup-native/stage-{phase}.log'].decode()
        marker = f'KT_PICKUP_SMOKE_STAGE{phase}_OK '
        observed = [json.loads(line.split(marker, 1)[1]) for line in raw.splitlines() if marker in line]
        recorder.same(observed, [receipt['stages'][str(phase)]])
        recorder.same(pickup.stage_violations(raw.splitlines(True), observed[0], 0, True, True), [])
    engine = report['engine']
    recorder.fields(engine, 'executable_sha256 download archive_sha256 reused_successful_save_restart_receipt_sha256')
    recorder.same(engine['download'], pickup.URL)
    recorder.same(engine['archive_sha256'], receipt['bdsSHA256'])
    recorder.same(engine['reused_successful_save_restart_receipt_sha256'], sha(pickup_raw))
    for value in (engine['archive_sha256'], engine['executable_sha256']):
        require(re.fullmatch(r'[0-9a-f]{64}', value), 'invalid retained engine digest')
    return report


def ancestor(root, before, after):
    command = ['git', '-C', str(root), 'merge-base', '--is-ancestor', before, after]
    result = subprocess.run(command, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
    # Some Git versions return 1 even when graph traversal prints a missing
    # parent error. A clean negative relationship has no diagnostic output.
    if result.returncode not in (0, 1) or result.stderr:
        raise subprocess.CalledProcessError(result.returncode, command, stderr=result.stderr)
    return result.returncode == 0


def related_run(api, root, run, repository_id):
    """Retain provenance through a reviewed squash merge without a version ledger."""
    if ancestor(root, run['head_sha'], 'HEAD'):
        return {'kind': 'ancestor', 'headCommit': run['head_sha']}
    if run['event'] != 'pull_request':
        return None
    pulls = run.get('pull_requests', [])
    if not pulls:
        pulls = api.json('/repos/' + REPOSITORY + '/commits/' + run['head_sha'] + '/pulls?per_page=10')
        require(len(pulls) < 10, 'source PR listing may be truncated')
    require(len(pulls) <= 10, 'source PR relationship exceeds bound')
    for link in pulls:
        pull = api.json('/repos/' + REPOSITORY + '/pulls/' + str(int(link['number'])))
        if not pull.get('merged') or pull.get('base', {}).get('ref') != 'main':
            continue
        if any(pull.get(side, {}).get('repo', {}).get('id') != repository_id for side in ('base', 'head')):
            continue
        final_head, merged = pull['head']['sha'], pull['merge_commit_sha']
        ensure_commit(root, final_head)
        ensure_commit(root, merged)
        if not ancestor(root, run['head_sha'], final_head) or not ancestor(root, merged, 'HEAD'):
            continue
        if git(root, 'rev-parse', final_head + '^{tree}') != git(root, 'rev-parse', merged + '^{tree}'):
            continue
        return {'kind': 'merged-pull-request', 'number': pull['number'], 'originalHeadCommit': run['head_sha'],
                'finalHeadCommit': final_head, 'mergeCommit': merged}
    return None


def matching_run(api, current, root, liquor, current_inputs, peer_inputs, contract, current_id):
    base = '/repos/' + REPOSITORY
    query = {'per_page': '10'}
    if current['event'] == 'pull_request':
        query.update(branch=current['head_branch'], event='pull_request')
    runs = api.json(base + '/actions/workflows/validation.yml/runs?' + urllib.parse.urlencode(query))['workflow_runs']
    require(len(runs) <= 10, 'candidate search exceeded bound')
    for run in runs:
        if run['id'] >= current_id or run.get('status') != 'completed' or run.get('event') not in ('push', 'pull_request'):
            continue
        if run['workflow_id'] != current['workflow_id']:
            continue
        if any(run.get(key, {}).get('id') != current['repository']['id'] for key in ('repository', 'head_repository')):
            continue
        head = run['head_sha']
        ensure_commit(root, head)
        # Older releases can legitimately predate a current probe. Missing source
        # paths are an input mismatch before selecting proof, not corrupt proof.
        previous_inputs = snapshot(root, head, True, allow_missing=True)
        if previous_inputs != current_inputs:
            continue
        relation = related_run(api, root, run, current['repository']['id'])
        if relation is None:
            continue
        old_contract, peer = workflow_contract(git(root, 'show', head + ':' + WORKFLOW) + '\n')
        if old_contract != contract:
            continue
        ensure_commit(liquor, peer)
        if snapshot(liquor, peer) != peer_inputs:
            continue
        jobs = api.json(base + f"/actions/runs/{run['id']}/attempts/{run['run_attempt']}/jobs?per_page=100")['jobs']
        require(len(jobs) < 100, 'native job listing may be truncated')
        candidates = [job for job in jobs if original_job(job)]
        require(len(candidates) <= 1, 'ambiguous successful native jobs')
        if candidates:
            job = candidates[0]
            require(job['run_id'] == run['id'] and job['status'] == 'completed', 'native job belongs to a different/incomplete run')
            return run, job, peer, relation
    return None


def select_and_reuse(api, root, liquor, output, env):
    require(env.get('GITHUB_REPOSITORY') == REPOSITORY, 'reuse only runs in the canonical repository')
    current_id = int(env['GITHUB_RUN_ID'])
    require(current_id > 0, 'invalid current run ID')
    require(not output.exists(), 'preserve prior reuse output; choose a new directory')
    current_commit, current_inputs = working_source(root, REPOSITORY, True)
    require(env.get('GITHUB_SHA') == current_commit, 'current checkout differs from the current workflow commit')
    peer_commit, peer_inputs = working_source(liquor, PEER_REPOSITORY)
    current_contract, pinned_peer = workflow_contract((root / WORKFLOW).read_text())
    require(pinned_peer == peer_commit, 'current peer checkout differs from workflow pin')
    base = '/repos/' + REPOSITORY
    current = api.json(base + f'/actions/runs/{current_id}')
    require(current['repository']['full_name'] == REPOSITORY and
            current['head_repository']['id'] == current['repository']['id'], 'current run has an untrusted source repository')
    require(current['event'] in ('push', 'pull_request', 'workflow_dispatch'), 'unsupported current event')
    require(current['path'] == WORKFLOW, 'current run is not the canonical validation workflow')
    if current['head_sha'] != current_commit:
        parents = git(root, 'show', '-s', '--format=%P', current_commit).split()
        require(current['event'] == 'pull_request' and len(parents) == 2 and parents[1] == current['head_sha'],
                'current checkout is not the current run head or its exact PR merge')
    match = matching_run(api, current, root, liquor, current_inputs, peer_inputs, current_contract, current_id)
    if match is None:
        return False
    run, job, old_peer, relation = match
    # A matching original execution now exists. Every error below is fatal.
    artifacts = api.json(base + f"/actions/runs/{run['id']}/artifacts?name={ARTIFACT}&per_page=100")['artifacts']
    require(len(artifacts) == 1 and artifacts[0]['name'] == ARTIFACT, 'matching original artifact missing or ambiguous')
    artifact = artifacts[0]
    binding = artifact['workflow_run']
    require(binding['id'] == run['id'] and binding['head_sha'] == run['head_sha'] and
            binding['repository_id'] == current['repository']['id'] and
            binding['head_repository_id'] == current['repository']['id'], 'artifact source run/repository mismatch')
    require(artifact.get('expired') is False, 'matching original artifact expired')
    archive = api.read(base + f"/actions/artifacts/{artifact['id']}/zip", 16 * 1024 * 1024)
    files = unpack_artifact(archive, artifact)
    job_log = api.read(base + f"/actions/jobs/{job['id']}/logs", 16 * 1024 * 1024)
    log_text = job_log.decode()
    require('SHA256 digest of uploaded artifact zip is ' + sha(archive) in log_text and
            f"Artifact {ARTIFACT}.zip successfully finalized. Artifact ID {artifact['id']}" in log_text,
            'original job upload does not bind the selected artifact')
    source_commit, logged_peer = checkout_commits(log_text)
    require(logged_peer == old_peer, 'original peer checkout differs from original workflow')
    original = api.json(base + '/git/commits/' + source_commit)
    require(original['sha'] == source_commit, 'original checkout commit response mismatch')
    parents = [row['sha'] for row in original['parents']]
    require(source_commit == run['head_sha'] or (run['event'] == 'pull_request' and len(parents) == 2 and parents[1] == run['head_sha']),
            'original merge checkout is unrelated to the source run')
    ensure_commit(root, source_commit)
    require(snapshot(root, source_commit, True) == current_inputs, 'original executed merge inputs differ from current inputs')
    executed_contract, executed_peer = workflow_contract(git(root, 'show', source_commit + ':' + WORKFLOW) + '\n')
    require(executed_contract == current_contract and executed_peer == old_peer, 'original executed workflow differs from source run')
    report = validate_original(files, root, liquor)
    require(report['sources']['tavern']['commit'] == source_commit and report['sources']['liquor']['commit'] == old_peer,
            'original report source does not match original checkout logs')
    proof = {
        'schema': 1, 'reused': True, 'nativeExecutedThisRun': False,
        'original': {'repository': REPOSITORY, 'runId': run['id'], 'runAttempt': run['run_attempt'],
                     'jobId': job['id'], 'headCommit': run['head_sha'], 'executedCommit': source_commit,
                     'peerCommit': old_peer, 'artifactId': artifact['id'], 'artifactSHA256': sha(archive),
                     'jobLogSHA256': sha(job_log)},
        'current': {'runId': current_id, 'commit': current_commit, 'peerCommit': peer_commit},
        'sourceRelationship': relation,
        'identicalGitInputs': {'tavern': current_inputs, 'liquor': peer_inputs},
        'nativeWorkflowContractSHA256': sha(current_contract.encode()),
        'reuseValidatorSHA256': sha(pathlib.Path(__file__).read_bytes()),
        'originalFileSHA256': {name: sha(raw) for name, raw in sorted(files.items())},
        'engine': report['engine'], 'client': False, 'live': False, 'fullFamily': False,
        'limits': 'Retains original zero-player native scope. The engine archive and extracted support files are not in this artifact; their original-run verification is reused, not repeated. No client or private saved-world acceptance.',
    }
    output.mkdir(parents=True)
    (output / 'original-artifact.zip').write_bytes(archive)
    (output / 'original-job.log').write_bytes(job_log)
    for name, raw in files.items():
        target = output / 'originals' / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(raw)
    (output / 'reuse-provenance.json').write_text(json.dumps(proof, indent=2) + '\n')
    return True


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--liquor', type=pathlib.Path, required=True)
    parser.add_argument('--output', type=pathlib.Path, required=True)
    args = parser.parse_args()
    try:
        reused = select_and_reuse(GitHub(os.environ.get('GH_TOKEN') or os.environ.get('GITHUB_TOKEN')),
                                  ROOT, args.liquor.resolve(), args.output.resolve(), os.environ)
    except (ValueError, AssertionError, KeyError, TypeError, OSError, subprocess.SubprocessError, zipfile.BadZipFile) as error:
        # Do not print credential-bearing requests, signed URLs or complete observations.
        detail = str(error) if isinstance(error, ReuseError) else type(error).__name__
        print('Native evidence reuse failed closed: ' + detail, file=sys.stderr)
        return 1
    if os.environ.get('GITHUB_OUTPUT'):
        with open(os.environ['GITHUB_OUTPUT'], 'a') as output:
            output.write('reused=' + str(reused).lower() + '\n')
    print('Reused verified original native evidence.' if reused else 'No identical original native execution found; fresh execution required.')
    return 0


if __name__ == '__main__':
    sys.exit(main())
