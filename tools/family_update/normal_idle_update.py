"""An exact normal-idle owner may hand a stopped server to a new update.

This is independent of drift repair and preinstall recovery. Mutable idle
timestamps are checked at handoff, never treated as immutable build inputs.
"""
import datetime
import hashlib
import json
import os
from pathlib import Path
import stat
from urllib.parse import quote

from family_update import common as c

PROFILE = 'canonical-normal-idle-v1'
IDLE_CONFIG = Path('/root/senluo-maintenance/bedrock-idle/config.json')
CURRENT_CONFIG = Path('/root/senluo-maintenance/config/current.json')
SOURCE = 'maintenance/bedrock-idle/idle_stop.py'
SOURCE_SHA256 = '5bcdba9d1b86d6c4b448ce7652540c60220f207f118f0b01aa4401f2f8ca9b55'
ROOT_UID = 0
_INITIAL = None


def enabled():
    value = c.CONFIG.get('normal_idle_update')
    if value is None:
        return False
    assert isinstance(value, str) and Path(value).is_absolute(), 'Normal idle update requires an explicit review path'
    assert not c.CONFIG.get('managed_drift_recovery') and not c.CONFIG.get('preinstall_recovery_output'), 'Normal idle update cannot borrow recovery exceptions'
    return True


def _raw(path):
    path = Path(path)
    assert path.is_absolute() and '..' not in path.parts
    assert not any(p.is_symlink() for p in [path, *path.parents]), 'Idle input cannot be a symlink'
    with path.open('rb') as stream:
        before = os.fstat(stream.fileno())
        assert stat.S_ISREG(before.st_mode) and before.st_uid == ROOT_UID and not before.st_mode & 0o022, 'Idle input requires a protected regular file'
        raw = stream.read(8 * 1024 * 1024 + 1)
        after = os.fstat(stream.fileno())
    assert len(raw) <= 8 * 1024 * 1024, 'Idle input exceeds its read budget'
    assert (before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns, before.st_ctime_ns) == (after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns, after.st_ctime_ns), 'Idle input changed during read'
    assert path.stat().st_ino == after.st_ino and path.stat().st_dev == after.st_dev, 'Idle input was replaced during read'
    return raw


def _document(path):
    raw = _raw(path)
    return json.loads(raw), {'path': str(path), 'sha256': hashlib.sha256(raw).hexdigest()}


def normalized_sleep(state):
    return {key: state[key] for key in ['server_status', 'log', 'fresh_player_count', 'empty_seconds', 'stop_task', 'last_sleep']}


def _timestamp(value):
    parsed = datetime.datetime.fromisoformat(value.replace('Z', '+00:00'))
    assert parsed.tzinfo is not None, 'Idle times must include their timezone'
    return parsed


def load_review():
    assert enabled(), 'Normal idle update is not configured'
    review, binding = _document(Path(c.CONFIG['normal_idle_update']))
    assert set(review) == {'schema', 'kind', 'profile', 'server_name', 'idle_config', 'previous_config', 'previous_output', 'previous_lease_sha256', 'policy_sha256', 'receipt_sha256', 'server_log_sha256', 'sleep'}
    assert review['schema'] == 1 and review['kind'] == 'normal_idle_update' and review['profile'] == PROFILE
    assert review['server_name'] == c.SERVER
    assert Path(review['idle_config']['path']) == IDLE_CONFIG
    idle, idle_ref = _document(IDLE_CONFIG)
    assert idle_ref == review['idle_config'], 'Idle owner configuration changed'
    assert idle['schema'] == 1 and idle['enabled'] is True and idle['server_name'] == c.SERVER and idle['wake'] == 'lobby'
    assert type(idle['idle_seconds']) is int and idle['idle_seconds'] == 600
    assert type(idle['max_check_gap_seconds']) is int and 0 < idle['max_check_gap_seconds'] <= 100
    assert Path(idle['family_config']) == CURRENT_CONFIG
    assert Path(idle['state_file']) == IDLE_CONFIG.parent / 'state.json'
    installed = IDLE_CONFIG.parent / 'idle_stop.py'
    assert c.EXTENSION is not None, 'Canonical idle owner source is required'
    source = c.EXTENSION / SOURCE
    assert all(hashlib.sha256(_raw(path)).hexdigest() == SOURCE_SHA256 for path in [installed, source]), 'Idle owner source differs from the reviewed implementation'
    assert c.subprocess.check_output(['git', '-C', str(c.EXTENSION), 'show', 'HEAD:' + SOURCE]) == _raw(source), 'Idle owner differs from committed canonical source'
    previous_config = Path(review['previous_config']['path'])
    old_config, old_ref = _document(previous_config)
    assert old_ref == review['previous_config'], 'Previous immutable configuration changed'
    previous = Path(review['previous_output'])
    assert previous.is_absolute() and previous != c.R
    assert old_config['output_dir'] == str(previous)
    for key, value in [('server_name', c.SERVER), ('bds_root', str(c.B)), ('world_dir', str(c.W)), ('quality_dir', str(c.Q)), ('lease_file', str(c.LEASE)), ('lock_file', str(c.LOCK))]:
        assert old_config[key] == value, 'Previous server/owner binding differs: ' + key
    documents = {}
    refs = {'review': binding, 'idle_config': idle_ref, 'previous_config': old_ref}
    for name in ['reviewed-family-receipt.json', 'deployment-result.json', 'poststart-verification.json']:
        documents[name], refs[name] = _document(previous / name)
    result, post = documents['deployment-result.json'], documents['poststart-verification.json']
    receipt_ref = refs['reviewed-family-receipt.json']
    assert receipt_ref['sha256'] == review['receipt_sha256'] == result['receipt_sha256'] == post['receipt_sha256']
    assert result['state'] == 'deployed_running' and result['poststart_report'] == str(previous / 'poststart-verification.json')
    assert post['ok'] is True and not post['errors'] and post['summary']['name'] == c.SERVER and post['summary']['status'] == 'RUNNING'
    assembled = documents['reviewed-family-receipt.json']['assembled_receipt']
    assert assembled['path'] == str(previous / 'release-candidate/family-receipt.json')
    assert assembled['sha256'] == result['assembled_receipt_sha256'] == c.sha(Path(assembled['path']))
    refs['assembled_receipt'] = assembled
    sleep = review['sleep']
    assert set(sleep) == {'server_status', 'log', 'fresh_player_count', 'empty_seconds', 'stop_task', 'last_sleep'}
    assert sleep['server_status'] == 'STOPPED' and type(sleep['fresh_player_count']) is int and sleep['fresh_player_count'] == 0
    assert type(sleep['empty_seconds']) is int and sleep['empty_seconds'] >= idle['idle_seconds']
    assert sleep['log']['valid'] is True and sleep['log']['connections'] == []
    assert sleep['last_sleep']['process'] == sleep['log']['process']
    assert sleep['last_sleep']['task'] == sleep['stop_task'] and sleep['last_sleep']['empty_seconds'] == sleep['empty_seconds']
    assert _timestamp(result['completed_at']) < _timestamp(sleep['last_sleep']['at_utc']), 'Idle stop predates the installed deployment'
    return review, refs, idle


def input_refs():
    if not enabled():
        return {}
    _, refs, _ = load_review()
    # No mutable global lease, idle state, log or installed policy is a build
    # input: those legitimately change after the exact handoff and installation.
    return {'normal_idle:' + key: value for key, value in refs.items()}


def _processes():
    expected = c.B.stat()
    matches = []
    for path in Path('/proc').iterdir():
        if not path.name.isdecimal():
            continue
        try:
            if (path / 'comm').read_text().strip() != 'bedrock_server':
                continue
            actual = (path / 'cwd').stat()
            if (actual.st_dev, actual.st_ino) == (expected.st_dev, expected.st_ino):
                matches.append(path.name)
        except (FileNotFoundError, ProcessLookupError):
            continue
    return matches


def verify_handoff(summary, *, lease_bound=False):
    review, refs, idle = load_review()
    assert summary['name'] == c.SERVER and summary['status'] == 'STOPPED' and type(summary['player_count']) is int and summary['player_count'] == 0, 'Normal idle handoff requires the exact stopped empty server'
    assert CURRENT_CONFIG.is_symlink() and CURRENT_CONFIG.resolve(strict=True) == Path(review['previous_config']['path']), 'Current deployment selector changed'
    assert c.sha(CURRENT_CONFIG) == review['previous_config']['sha256']
    state, _ = _document(Path(idle['state_file']))
    # Lock contention can replace sleeping with maintenance_lock_busy; the next
    # stopped poll then labels it server_not_running. These diagnostic labels
    # still require the exact reviewed sleep and every ownership check below.
    assert state['status'] in ['sleeping', 'maintenance_lock_busy', 'server_not_running'], 'Stopped state was not confirmed by the normal idle owner'
    assert not state.get('error') and normalized_sleep(state) == review['sleep'], 'Normal idle stop identity changed'
    age = (_timestamp(c.now()) - _timestamp(state['checked_at_utc'])).total_seconds()
    assert 0 <= age <= idle['max_check_gap_seconds'], 'Idle owner observation is stale'
    task = c.api('/api/tasks/status/' + quote(state['stop_task'], safe=''))
    assert task['status'] == 'success' and task['result']['status'] == 'success' and task['result']['server_name'] == c.SERVER, 'Normal idle stop task is not confirmed successful'
    assert not _processes(), 'Stopped server still has a BDS process'
    assert c.sha(c.B / 'server_output.txt') == review['server_log_sha256'], 'Stopped server log changed after the reviewed idle stop'
    assert c.sha(c.Q / 'senluo-policy.json') == review['policy_sha256'], 'Installed policy changed after the idle review'
    policy = c.read(c.Q / 'senluo-policy.json')
    receipt = str(Path(review['previous_output']) / 'reviewed-family-receipt.json')
    assert policy['approved_receipt'] == receipt == policy['installed']['receipt']
    assert policy['installed']['receipt_sha256'] == review['receipt_sha256']
    lease_path = c.R / 'previous-maintenance.json' if lease_bound else c.LEASE
    lease, lease_ref = _document(lease_path)
    assert lease_ref['sha256'] == review['previous_lease_sha256'], 'Previous completed owner changed'
    assert lease['state'] == 'completed' and lease['candidate'] == review['previous_output'] and lease['receipt'] == receipt
    assert lease['owner'] == 'Canonical family update ' + hashlib.sha256(review['previous_output'].encode()).hexdigest()[:12]
    assert lease['candidate_receipt_sha256'] == refs['assembled_receipt']['sha256']
    if lease_bound:
        c.assert_lease()
    else:
        assert c.lease_available() == lease
    assert c.summary() == summary, 'Server status changed during idle handoff verification'
    return {'schema': 1, 'profile': PROFILE, 'server': summary, 'review': refs['review'], 'previous_lease_sha256': lease_ref['sha256'], 'sleep': review['sleep'], 'restart_original_after_failure': False}


def validate_initial_status(summary):
    global _INITIAL
    _INITIAL = verify_fresh_handoff(summary) if c.CONFIG.get('fresh_world') else verify_handoff(summary)
    return _INITIAL


def verify_fresh_handoff(summary, *, lease_bound=False):
    """Explicit new-world delivery can follow an owner's normal stopped handoff."""
    assert c.CONFIG.get('fresh_world'), 'Stopped fresh handoff requires fresh_world'
    assert summary['name'] == c.SERVER and summary['status'] in ['RUNNING', 'STOPPED'], 'Fresh handoff requires a known running or stopped server'
    assert type(summary['player_count']) is int and summary['player_count'] == 0, 'Fresh handoff requires confirmed zero players'
    binding = c.verify_server_binding()
    assert binding['world_dir'] == str(c.W), 'Fresh handoff must still own the original active world'
    previous = c.read(c.R / 'previous-maintenance.json') if lease_bound else c.lease_available()
    capture = c.read(c.R / 'production-before/capture.json')
    assert previous == capture['previous_lease'], 'Previous maintenance owner changed after capture'
    selector = capture['current_selector']
    assert selector['path'] == str(CURRENT_CONFIG) and CURRENT_CONFIG.is_symlink() and os.readlink(CURRENT_CONFIG) == selector['target'], 'Current deployment selector changed'
    assert c.sha(CURRENT_CONFIG) == selector['sha256'] == c.sha(selector['backup']['path']), 'Previous configuration changed after capture'
    if previous:
        assert previous['state'] == 'completed', 'Fresh handoff cannot replace an active or failed owner'
        expected = 'Canonical family update ' + hashlib.sha256(previous['candidate'].encode()).hexdigest()[:12]
        assert previous['owner'] == expected, 'Previous completed maintenance owner differs'
    if summary['status'] == 'STOPPED':
        assert not _processes(), 'Stopped server still has a BDS process'
    if lease_bound:
        c.assert_lease()
    assert c.summary() == summary, 'Server state changed during fresh handoff'
    return {'schema': 1, 'profile': 'fresh_world', 'server': summary, 'binding': binding,
            'previous_lease': previous, 'restart_original_after_failure': False}


def record_initial_status():
    c.assert_lease()
    assert _INITIAL is not None, 'Normal idle preflight did not verify the original owner'
    observed = verify_fresh_handoff(c.summary(), lease_bound=True) if c.CONFIG.get('fresh_world') else verify_handoff(c.summary(), lease_bound=True)
    assert observed == _INITIAL, 'Normal handoff changed after lease acquisition'
    path = c.R / 'deployment-initial-state.json'
    assert not path.exists(), 'Preserve the previous initial-state report'
    c.atomic(path, _INITIAL)
