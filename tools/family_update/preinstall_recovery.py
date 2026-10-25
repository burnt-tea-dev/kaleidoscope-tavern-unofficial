"""Close one untouched, stopped transaction after native memory admission failed.

This does not resume a candidate, approve observed drift, restore a database or
start a server. A later candidate must pass the normal deployment gates anew.
"""
import argparse
from contextlib import contextmanager
import fcntl
import hashlib
import json
import os
from pathlib import Path
import subprocess

from family_update import common as c

KIND = 'preinstall_aborted_unchanged'
PROOF = 'preinstall-abort.json'
ALLOWED_ADVANCEMENT = frozenset({
    'tools/family_update.py',
    'family/UPDATE-WORKFLOW.md',
    *('tools/family_update/' + name for name in (
        'common.py', 'managed_drift_recovery.py', 'memory_budget.py',
        'preinstall_recovery.py', 'test_preinstall_recovery.py', 'test_lifecycle_action.py',
        'test_memory_budget.py', 'test_managed_drift_recovery.py')),
})
ALLOWED_OUTPUT = frozenset({
    'build-evidence.json', 'ci-evidence.json', 'compatibility-report.json',
    'current-author-static-validation.json', 'deployment-initial-state.json',
    'deployment-recovery.json', 'handoff-authorization.json',
    'live-authorization-AGENTS.md', 'memory-admissions.json',
    'previous-maintenance.json', 'production-before', 'release-candidate',
    'static-evidence.json', 'stop-result.json', 'stop-response.json',
    'stop-task-response.json', 'stop-readback.json', 'trusted-pack-rollback',
    'trusted-pack-rollback.json', 'preinstall-recovery-memory-admissions.json', PROOF,
})
REFERENCE_FILES = (
    'build-evidence.json', 'static-evidence.json', 'ci-evidence.json',
    'compatibility-report.json', 'deployment-recovery.json', 'stop-result.json',
    'memory-admissions.json', 'deployment-initial-state.json',
    'production-before/capture.json', 'production-before/inventory.json',
    'production-before/senluo-policy.json', 'production-before/index.json',
    'production-before/server.properties', 'release-candidate/family-receipt.json',
)
OPTIONAL_STOP_REFERENCES = ('stop-response.json', 'stop-task-response.json', 'stop-readback.json')


def _references(output):
    return (*REFERENCE_FILES, *(name for name in OPTIONAL_STOP_REFERENCES if (output / name).exists() or (output / name).is_symlink()))


def _bytes(value):
    # Keep this identical to family_guard.atomic, including the final newline.
    return (json.dumps(value, ensure_ascii=False, indent=2) + '\n').encode()


def _regular(path):
    path = Path(path)
    assert path.is_absolute() and path.resolve() == path and path.is_file(), 'Recovery input must be an explicit regular file: ' + str(path)
    assert not any(parent.is_symlink() for parent in [path, *path.parents]), 'Recovery input contains a symlink'
    return path


def _ref(path):
    return c.report_ref(_regular(path))


def _check_ref(reference):
    assert set(reference) == {'path', 'sha256'} and _ref(reference['path']) == reference, 'Recovery evidence changed'


@contextmanager
def _output_context(output):
    old = c.R, c.C
    c.R, c.C = output, output / 'release-candidate'
    try:
        yield
    finally:
        c.R, c.C = old


def _untouched(output):
    assert output.is_dir() and output.resolve() == output, 'Recovery output differs'
    assert set(path.name for path in output.iterdir()) <= ALLOWED_OUTPUT, 'Post-stop, native, installation or retirement state exists'
    before = output / 'production-before'
    assert not (before / 'backup-receipt.json').exists(), 'A stopped snapshot already exists'
    assert not any(path.is_symlink() for path in output.iterdir()), 'Recovery output contains a symlink'


def _stopped(summary):
    assert summary.get('name') == c.SERVER and summary.get('status') == 'STOPPED' and summary.get('player_count') == 0, 'Recovery requires this stopped, empty server'


def _database():
    root = c.W / 'db'
    assert root.is_dir() and not root.is_symlink(), 'Stopped database is missing'
    files = c.hashes(root)
    assert files, 'Stopped database is empty'
    levels = {name: c.sha(_regular(c.W / name)) for name in ('level.dat', 'level.dat_old') if (c.W / name).exists()}
    assert 'level.dat' in levels, 'Stopped level metadata is missing'
    return {'database_files': files, 'level_files': levels}


def _original_config(path, output):
    path = _regular(path)
    config = c.read(path)
    assert Path(config['output_dir']) == output, 'Original transaction output differs'
    assert config.get('managed_drift_recovery') and config.get('managed_drift_failure_policy') == 'retain_stopped', 'Original transaction lacks fail-stop review'
    assert c.sha(path) == c.read(output / 'build-evidence.json')['config_sha256'], 'Original configuration differs from the built transaction'
    return config


def _configuration_for_recovery(original):
    current = dict(c.CONFIG)
    path = current.pop('recovery_original_config')
    current['memory_budget'] = dict(current['memory_budget'])
    original_budget = original['memory_budget']
    assert current['memory_budget'].pop('unit') != original_budget['unit'], 'Recovery requires its own maintenance unit'
    expected = dict(original)
    expected['memory_budget'] = {key: value for key, value in original_budget.items() if key != 'unit'}
    assert current == expected, 'Only the recovery memory unit may differ from the original configuration'
    return Path(path)


def _failure(output, original):
    report = c.read(output / 'deployment-recovery.json')
    assert report['state'] == 'needs_operator_recovery' and report['phase'] == 'retain_stopped_without_package_or_database_restore', 'Failure is not an untouched fail-stop transaction'
    assert report['server_status'] == 'STOPPED' and report['restart_attempted'] is False and report['save_database_restored'] is False
    stop = c.read(output / 'stop-result.json')
    c.validate_lifecycle_result('stop', stop)
    rows = c.read(output / 'memory-admissions.json')['observations']
    assert rows and all(row['ok'] is True for row in rows[:-1]), 'An earlier admission also failed'
    last, budget = rows[-1], original['memory_budget']
    assert last['phase'] == 'saved-world' and last['phase_category'] == 'native' and last['ok'] is False, 'Failure was not before the native snapshot boundary'
    assert last['unit'] == budget['unit'] and last['limit_bytes'] == budget['limit_bytes'] == budget['phase_limits']['native']
    assert last['previous_limit_bytes'] == budget['phase_limits']['light'] and last['swap_limit_bytes'] == budget['swap_limit_bytes'] == 0
    assert last['reserve_bytes'] == budget['reserve_bytes'] >= 2 * 1024 ** 3
    assert last['available_bytes'] < last['required_available_bytes'] and last['required_available_bytes'] >= last['reserve_bytes'] + last['limit_bytes'], 'Recorded memory failure lacks the complete native headroom'
    assert all(not int(row['memory_events'].get(key, 0)) for row in rows for key in ('oom', 'oom_kill', 'oom_group_kill')), 'An OOM cannot use untouched admission recovery'


def _blob(path, revision, relative):
    return subprocess.check_output(['git', '-C', str(path), 'show', revision + ':' + relative])


def _sources(build):
    current = c.source_state()
    assert set(current) == set(build['sources']), 'Recovery source set changed'
    for name, old in build['sources'].items():
        row = current[name]
        if name != 'tavern':
            assert all(old.get(key) == value for key, value in row.items()), 'Non-Tavern recovery source changed: ' + name
            continue
        assert {key: value for key, value in row.items() if key not in {'commit', 'tree', 'remote_main'}} == {key: value for key, value in old.items() if key not in {'commit', 'tree', 'remote_main'}}, 'Tavern runtime or baseline changed'
        ancestor = subprocess.run(['git', '-C', str(c.T), 'merge-base', '--is-ancestor', old['commit'], row['commit']], capture_output=True)
        assert ancestor.returncode == 0, 'Original Tavern is not an ancestor of the canonical recovery runner'
        changed = set(c.git(c.T, 'diff', '--name-only', old['commit'], row['commit']).splitlines())
        assert changed <= ALLOWED_ADVANCEMENT, 'Recovery runner advanced beyond the reviewed tooling paths'
        baseline = c.read(c.T / 'baseline.json')
        for relative in ['baseline.json', 'family/upstream.lock.json', *baseline['runtime'].values()]:
            assert c.git(c.T, 'rev-parse', old['commit'] + ':' + relative) == c.git(c.T, 'rev-parse', row['commit'] + ':' + relative), 'Recovery changed a runtime, baseline or family lock'
        for key, root in [('orchestration_sha256', 'tools/'), ('tool_sha256', 'tools/')]:
            for relative, digest in build[key].items():
                assert hashlib.sha256(_blob(c.T, old['commit'], root + relative)).hexdigest() == digest, 'Original runner evidence is not its recorded canonical commit'
    assert c.sha(c.T / 'family/upstream.lock.json') == build['upstream_lock_sha256'], 'Family lock changed'
    return current


def _compiled(output, original):
    build = c.read(output / 'build-evidence.json')
    assert c.sha(Path(original['_config_path'])) == build['config_sha256']
    sources = _sources(build)
    receipt_path = output / 'release-candidate/family-receipt.json'
    assert c.sha(receipt_path) == build['candidate_receipt_sha256'], 'Compiled candidate receipt changed'
    receipt = c.read(receipt_path)
    c.audit_candidate(receipt_path.parent, receipt)
    static = c.read(output / 'static-evidence.json')
    assert static['ok'] is True and static['pr_checks_verified'] is True and static['sources'] == build['sources'] and static['candidate_receipt_sha256'] == build['candidate_receipt_sha256'], 'Static evidence differs from the compiled candidate'
    for reference in static['reports']:
        _check_ref(reference)
    for check in static['checks']:
        assert check['exit_code'] == 0 and c.sha(_regular(check['log'])) == check['sha256'], 'Static CI evidence changed'
    assert c.read(output / 'compatibility-report.json')['ok'] is True
    current_config = c.CONFIG
    try:
        c.CONFIG = {key: value for key, value in original.items() if key != '_config_path'}
        assert c.external_input_hashes() == build['external_input_sha256'], 'Reviewed external inputs changed'
    finally:
        c.CONFIG = current_config
    return sources


def _closed_lease(previous, proof_path, recorded_at):
    return {**previous, 'state': 'failed', 'failed_at': recorded_at,
            'status': KIND, 'preinstall_abort': str(proof_path)}


def _producer(proof, build):
    producer = proof['producer']
    assert set(producer['sources']) == set(build['sources']), 'Abort producer source set changed'
    for name, row in producer['sources'].items():
        old = build['sources'][name]
        ignored = {'commit', 'tree', 'remote_main'} if name == 'tavern' else {'remote_main'}
        assert all(old.get(key) == value for key, value in row.items() if key not in ignored), 'Abort producer runtime changed'
    revision = producer['canonical_commit']
    assert revision == producer['sources']['tavern']['commit']
    assert c.git(c.T, 'rev-parse', revision + '^{tree}') == producer['sources']['tavern']['tree'], 'Abort producer tree changed'
    for before, after in [(build['sources']['tavern']['commit'], revision), (revision, c.git(c.T, 'rev-parse', 'HEAD'))]:
        result = subprocess.run(['git', '-C', str(c.T), 'merge-base', '--is-ancestor', before, after], capture_output=True)
        assert result.returncode == 0, 'Abort producer is outside the canonical recovery lineage'
    runner = producer['orchestration_sha256']
    assert {'family_update.py', 'family_update/preinstall_recovery.py'} <= set(runner), 'Abort producer runner closure is incomplete'
    for relative, digest in runner.items():
        assert relative == 'family_update.py' or (Path(relative).parent == Path('family_update') and Path(relative).suffix == '.py' and not Path(relative).name.startswith('test_')), 'Unexpected abort runner path'
        assert hashlib.sha256(_blob(c.T, revision, 'tools/' + relative)).hexdigest() == digest, 'Abort producer runner changed'


def _proof_binding(proof, output):
    assert proof['schema'] == 1 and proof['kind'] == KIND and proof['output'] == str(output)
    assert proof['server']['name'] == c.SERVER
    _stopped(proof['server'])
    for reference in proof['references'].values():
        _check_ref(reference)
    old = proof['lease_before']
    assert old['state'] == 'active' and old['candidate'] == str(output) and old['status'] == 'needs_operator_recovery'
    owner = 'Canonical family update ' + hashlib.sha256(str(output).encode()).hexdigest()[:12]
    assert old['owner'] == owner and old['recovery_report'] == str(output / 'deployment-recovery.json'), 'Abort belongs to another transaction'
    build = c.read(output / 'build-evidence.json')
    assert old['candidate_receipt_sha256'] == build['candidate_receipt_sha256'], 'Abort owner candidate changed'
    assert set(proof['references']) == {*_references(output), 'original_config', 'recovery_config'}, 'Abort evidence closure is incomplete'
    _producer(proof, build)
    closed = _closed_lease(old, output / PROOF, proof['recorded_at'])
    assert proof['old_lease_sha256'] == hashlib.sha256(_bytes(old)).hexdigest(), 'Original owner byte binding differs'
    expected = {'path': str(c.LEASE), 'sha256': hashlib.sha256(_bytes(closed)).hexdigest()}
    assert proof['closed_lease'] == expected, 'Closed owner binding was changed'
    assert proof['database_before'] == proof['database_after'], 'Recovery changed the stopped database'
    assert proof['world_mutated'] is False and proof['server_started'] is False and proof['original_drift_approved'] is False
    return closed


def _validate(output, original):
    _untouched(output)
    _failure(output, original)
    with _output_context(output):
        c.verify_predeploy()
    return _compiled(output, {**original, '_config_path': str(original['_config_path'])})


def input_refs():
    """Pin immutable handoff evidence, including after the next lease/DB changes."""
    configured = c.CONFIG.get('preinstall_recovery_output')
    if not configured:
        return {}
    output = Path(configured)
    assert output.is_absolute() and output.resolve() == output and output != c.R
    path = _regular(output / PROOF)
    proof = c.read(path)
    _proof_binding(proof, output)
    result = {'preinstall_recovery_abort': c.sha(path)}
    result.update({'preinstall_recovery:' + name: row['sha256'] for name, row in proof['references'].items()})
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--execute', action='store_true')
    args = parser.parse_args(argv)
    if not args.execute:
        return {'execute': False, 'output': str(c.R), 'operation': KIND, 'world_mutated': False, 'server_started': False}
    output = c.R
    original_path = Path(c.CONFIG['recovery_original_config'])
    original = _original_config(original_path, output)
    assert _configuration_for_recovery(original) == original_path
    original = {**original, '_config_path': str(original_path)}
    with open(c.LOCK, 'a+') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        c.assert_lease()
        lease = c.read(c.LEASE)
        assert lease['status'] == 'needs_operator_recovery' and lease['recovery_report'] == str(output / 'deployment-recovery.json'), 'Active owner is not this failed transaction'
        first = c.summary()
        _stopped(first)
        before = _database()
        sources = _validate(output, original)
        references = {name: _ref(output / name) for name in _references(output)}
        references.update(original_config=_ref(original_path), recovery_config=_ref(c.CONFIG_PATH))
        after = _database()
        _stopped(c.summary())
        assert before == after, 'Stopped database changed during recovery inspection'
        _untouched(output)
        c.verify_predeploy()
        assert c.read(c.LEASE) == lease, 'Maintenance owner changed during inspection'
        c.assert_lease()
        path = output / PROOF
        if path.exists():
            proof = c.read(_regular(path))
            _proof_binding(proof, output)
            assert proof['lease_before'] == lease and proof['references'] == references and proof['database_after'] == after and proof['producer']['sources'] == sources, 'Preserved abort proof differs; retain active lease'
        else:
            recorded = c.now()
            closed = _closed_lease(lease, path, recorded)
            proof = {'schema': 1, 'kind': KIND, 'recorded_at': recorded, 'output': str(output),
                     'server': first, 'references': references, 'lease_before': lease,
                     'old_lease_sha256': c.sha(c.LEASE),
                     'closed_lease': {'path': str(c.LEASE), 'sha256': hashlib.sha256(_bytes(closed)).hexdigest()},
                     'producer': {'canonical_commit': sources['tavern']['commit'], 'sources': sources,
                                  'orchestration_sha256': c.orchestration_hashes()},
                     'database_before': before, 'database_after': after,
                     'database_claim': 'Only unchanged across this stopped abort inspection; not compared with the earlier running capture.',
                     'world_mutated': False, 'server_started': False, 'original_drift_approved': False,
                     'client': False, 'production_ready': False}
            # Preserve all original failure reports. A partially written proof
            # leaves the original active lease and cannot authorize a new run.
            with path.open('xb') as handle:
                handle.write(_bytes(proof)); handle.flush(); os.fsync(handle.fileno())
        closed = _proof_binding(proof, output)
        assert c.read(c.LEASE) == lease, 'Maintenance owner changed before closure'
        _stopped(c.summary())
        assert _database() == after, 'Stopped database changed before closure'
        _untouched(output)
        c.verify_predeploy()
        c.atomic(c.LEASE, closed)
        assert c.sha(c.LEASE) == proof['closed_lease']['sha256'], 'Closed owner bytes differ; do not start another transaction'
        return {'state': KIND, 'proof': _ref(path), 'closed_lease': proof['closed_lease'], 'world_mutated': False, 'server_started': False, 'client': False}


def verify_completed(output, summary):
    """Verify an exact closed owner before a new candidate adopts STOPPED state."""
    output = Path(output)
    assert output.is_absolute() and output != c.R and output.resolve() == output
    _stopped(summary)
    proof_path = _regular(output / PROOF)
    proof = c.read(proof_path)
    closed = _proof_binding(proof, output)
    assert c.read(c.LEASE) == closed and c.sha(c.LEASE) == proof['closed_lease']['sha256'], 'Stopped owner closure changed or was stolen'
    original_path = Path(proof['references']['original_config']['path'])
    original = _original_config(original_path, output)
    # The new transaction may choose new outputs, reviewed tooling PRs and its
    # own memory unit. All production locations and non-Tavern sources remain.
    for key in ('server_name', 'bds_root', 'world_dir', 'quality_dir', 'sources', 'extension', 'lease_file', 'lock_file', 'authorization_file', 'api_module', 'api_path_mappings'):
        assert c.CONFIG.get(key) == original.get(key), 'New transaction changed the recovered production boundary: ' + key
    sources = _validate(output, {**original, '_config_path': str(original_path)})
    assert proof['database_after'] == _database(), 'Stopped database changed since owner closure'
    _stopped(c.summary())
    assert c.sha(c.LEASE) == proof['closed_lease']['sha256'], 'Stopped owner changed during admission'
    return {'proof': _ref(proof_path), 'closed_lease': dict(proof['closed_lease']),
            'original_config': _ref(original_path), 'producer_commit': proof['producer']['canonical_commit'],
            'current_canonical_commit': sources['tavern']['commit'], 'observed_stack_unchanged': True,
            'database_unchanged_since_abort': True, 'original_drift_approved': False,
            'restart_original_after_failure': False}
