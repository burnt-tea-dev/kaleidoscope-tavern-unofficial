"""Install one directly reviewed local family on the authorized staging world.

This transaction deliberately has no CI, native rehearsal or data-repair stages.
It never produces LIVE admission and never restores world data automatically.
"""
import fcntl
import hashlib
import json
import os
from pathlib import Path
import shutil
import sys
import uuid

from family_update import common as c
from family_update.storage import require_space
from world_backup import capture, adopt, overlaps


SIDES = ('behavior', 'resource')
LOCAL = {'local': True, 'remote_delivery': False, 'ci': False, 'client': False,
         'java_parity': False, 'tests_executed': False, 'production_ready': False}
# An allowlist keeps new LIVE options from silently becoming staging options.
CONFIG_KEYS = {'schema', 'server_name', 'bds_root', 'world_dir', 'quality_dir',
               'output_dir', 'sources', 'extension', 'api_module',
               'api_path_mappings', 'authorization_file', 'lease_file',
               'lock_file', 'python', 'startup_markers', 'memory_budget',
               'native_port', 'saved_port', 'staging_repair'}


def absolute(value):
    path = Path(value)
    if not path.is_absolute():
        raise ValueError('Staging paths must be absolute: ' + str(path))
    return path.resolve()


def configuration():
    assert set(c.CONFIG) <= CONFIG_KEYS, 'Staging repair rejects other deployment/recovery options: ' + str(sorted(set(c.CONFIG) - CONFIG_KEYS))
    assert isinstance(c.CONFIG.get('memory_budget'), dict), 'Use the existing bounded maintenance memory configuration'
    options = c.CONFIG.get('staging_repair')
    assert isinstance(options, dict) and set(options) == {'candidate_dir', 'source_batch', 'review_file', 'retire_uuids'}, 'Explicit staging_repair candidate, batch, review and retirement selection required'
    candidate, batch, review = (absolute(options[key]) for key in ('candidate_dir', 'source_batch', 'review_file'))
    retired = options['retire_uuids']
    assert isinstance(retired, list) and all(isinstance(uid, str) and str(uuid.UUID(uid)) == uid for uid in retired) and len(set(retired)) == len(retired), 'Retirement requires distinct literal UUIDs'
    auth = c.read(c.AUTHORIZATION)
    assert set(auth) == {'schema', 'scope', 'server_name', 'bds_root', 'world_dir', 'live_config', 'world_backup_state', 'retire_uuids'}, 'Explicit staging target authorization required'
    assert auth['schema'] == 1 and auth['scope'] == 'staging-local-repair', 'Authorization is not for staging local repair'
    assert c.SERVER.endswith('-staging') and auth['server_name'] == c.SERVER, 'Only an explicitly named -staging server is supported'
    assert absolute(auth['bds_root']) == c.B and absolute(auth['world_dir']) == c.W, 'Authorization names another staging target'
    assert auth['retire_uuids'] == retired, 'Retirement differs from the authorized target configuration'
    live_path = absolute(auth['live_config'])
    live = c.read(live_path)
    assert live['schema'] == 1 and 'staging_repair' not in live and not live['server_name'].endswith('-staging'), 'LIVE reference must be an existing normal deployment configuration'
    live_root, live_world = absolute(live['bds_root']), absolute(live['world_dir'])
    assert live['server_name'] != c.SERVER and not overlaps(live_root, c.B) and not overlaps(live_world, c.W), 'Staging command cannot select LIVE'
    assert absolute(live['lock_file']) == c.LOCK and absolute(live['lease_file']) == c.LEASE, 'Staging and LIVE must share the maintenance lock and lease'
    backup_state = absolute(auth['world_backup_state'])
    state = c.read(backup_state)
    assert any(absolute(p) == c.W or absolute(p) in c.W.parents for p in state['protected_worlds']), 'Shared backup index does not protect staging'
    assert any(absolute(p) == live_world or absolute(p) in live_world.parents for p in state['protected_worlds']), 'Shared backup index does not protect LIVE'
    assert any(absolute(p) in (c.R / 'world-backup').parents for p in state['backup_roots']), 'Output must be within the shared world backup roots'
    for policy_root in {c.Q, absolute(live['quality_dir'])}:
        declared = c.read(policy_root / 'senluo-policy.json').get('world_backup_state')
        assert declared is None or absolute(declared) == backup_state, 'Use the shared backup index, not a parallel one'
    source_roots = [absolute(row['path']) for row in c.read(batch)['source_commits'].values()]
    protected = [c.R, c.B, c.W, c.Q, live_root, absolute(live['quality_dir']), *source_roots]
    if c.EXTENSION:
        protected.append(c.EXTENSION)
    assert all(not overlaps(candidate, path) for path in protected), 'Candidate overlaps deployment, server or source data'
    assert all(not overlaps(c.R, path) for path in [live_root, live_world, absolute(live['quality_dir']), *source_roots, batch, review, c.AUTHORIZATION, live_path, backup_state]), 'Output overlaps a protected input or LIVE'
    assert Path(sys.executable).absolute() == c.PY, 'Use the configured Python interpreter'
    return options, candidate, batch, review, live_path, backup_state


def source_identity(batch):
    """Read offline identities, including directly reviewed unfinished work."""
    selected = batch['source_commits']
    for name, path in c.SOURCES.items():
        assert absolute(selected[name]['path']) == path, 'Batch source path differs: ' + name
    if c.EXTENSION:
        assert any(absolute(row['path']) == c.EXTENSION for row in selected.values()), 'Batch omits the configured private integration'
    states = {}
    for name, row in selected.items():
        path = absolute(row['path'])
        assert c.git(path, 'rev-parse', 'HEAD') == row['commit'], 'Batch source commit changed: ' + name
        untracked = c.git(path, 'ls-files', '--others', '--exclude-standard').splitlines()
        states[name] = {'path': str(path), 'commit': row['commit'],
                        'tree': c.git(path, 'rev-parse', row['commit'] + '^{tree}'),
                        'worktree_status': c.git(path, 'status', '--porcelain', '--untracked-files=all'),
                        'worktree_diff_sha256': hashlib.sha256(c.git(path, 'diff', '--binary', 'HEAD').encode()).hexdigest(),
                        'untracked_files': {relative: c.sha(path / relative) for relative in untracked}}
    return states


def candidate_input(candidate, batch):
    receipt = c.read(candidate / 'family-receipt.json')
    assert receipt['schema'] == 1 and set(receipt['order']) == set(SIDES), 'Complete family receipt required'
    owned_sources = {}
    for source in batch['source_commits'].values():
        path = absolute(source['path'])
        if (path / 'baseline.json').is_file():
            baseline = json.loads(c.git(path, 'show', source['commit'] + ':baseline.json'))
            owned_sources[baseline['repository']] = source['commit']
    by_uuid = {p['uuid']: p for p in receipt['packs']}
    assert len(by_uuid) == len(receipt['packs']) and by_uuid, 'Candidate pack identities must be unique'
    for uid, pack in by_uuid.items():
        assert str(uuid.UUID(uid)) == uid and pack['side'] in SIDES, 'Invalid pack identity or side'
        assert isinstance(pack['source'], dict) and pack['source'].get('owner'), 'Candidate must retain its source descriptors'
        if pack['source']['owner'] == 'owned':
            assert pack['source'].get('repository') in owned_sources and pack['source'].get('commit') == owned_sources[pack['source']['repository']], 'Owned receipt differs from the selected source identity'
        assert pack['files'] and 'manifest.json' in pack['files'], 'Candidate pack is incomplete'
        # hashes rejects symlinks, which family_bundle.audit alone does not.
        root = candidate / (pack['side'] + '_packs') / uid
        assert c.hashes(root) == pack['files'], 'Candidate pack bytes differ: ' + uid
        manifest = c.read(root / 'manifest.json')
        assert manifest['header']['uuid'] == uid and manifest['header']['version'] == pack['version'], 'Candidate manifest identity differs'
        assert manifest.get('dependencies', []) == pack['dependencies'], 'Candidate dependency receipt differs'
        for dep in pack['dependencies']:
            if 'uuid' in dep:
                assert dep['uuid'] in by_uuid and dep['version'] == by_uuid[dep['uuid']]['version'], 'Candidate dependency is missing or has another version'
    for side in SIDES:
        order = receipt['order'][side]
        assert len(order) == len(set(order)) and set(order) == {uid for uid, p in by_uuid.items() if p['side'] == side}, 'Incomplete candidate order'
        directory = candidate / (side + '_packs')
        assert not directory.is_symlink() and {p.name for p in directory.iterdir()} == set(order), 'Unexpected candidate pack directories'
        assert c.read(candidate / ('world_' + side + '_packs.json')) == [{'pack_id': uid, 'version': by_uuid[uid]['version']} for uid in order], 'Candidate selection differs from its full receipt'
    assert set(batch['packs']) <= set(by_uuid), 'Candidate omits a generated batch input'
    pairs = {}
    for uid, row in batch['packs'].items():
        root = absolute(row['path'])
        files = c.hashes(root)
        tree = {'sha256': hashlib.sha256(json.dumps(files, sort_keys=True, separators=(',', ':')).encode()).hexdigest(), 'files': len(files)}
        assert tree == row['tree'], 'Normally generated input changed: ' + uid
        pack = by_uuid[uid]
        assert row['side'] in {'BP', 'RP'} and pack['side'] == {'BP': 'behavior', 'RP': 'resource'}[row['side']], 'Generated input side changed'
        assert pack['files'] == files and pack['version'] == row['version'], 'Candidate is not the exact generated input: ' + uid
        manifest = c.read(root / 'manifest.json')
        assert manifest['modules'] == row['modules'] and manifest.get('dependencies', []) == row['dependencies'], 'Generated input metadata changed'
        pairs.setdefault(row['name'], {})[row['side']] = row['version']
    for name, sides in pairs.items():
        if set(sides) == {'BP', 'RP'}:
            assert sides['BP'] == sides['RP'], 'Generated BP/RP versions differ: ' + name
    return receipt


def review_binding(candidate, batch_path, live_path):
    batch = c.read(batch_path)
    runner = c.orchestration_hashes()
    for name in ('family_bundle.py', 'family_guard.py', 'world_backup.py'):
        path = c.T / 'tools' / name
        runner[str(path)] = c.sha(path)
    return {'schema': 1, 'scope': 'direct-source-review-staging',
            'config_sha256': c.sha(c.CONFIG_PATH),
            'authorization_sha256': c.sha(c.AUTHORIZATION),
            'live_config_sha256': c.sha(live_path),
            'api_module_sha256': c.sha(c.CONFIG['api_module']),
            'candidate_receipt_sha256': c.sha(candidate / 'family-receipt.json'),
            'source_batch_sha256': c.sha(batch_path),
            'sources': source_identity(batch), 'runner_sha256': runner}


def selection(receipt, original, batch, retired):
    prior = {p['uuid']: p for p in original['packs']}
    target = {p['uuid']: p for p in receipt['packs']}
    assert len(prior) == len(original['packs']), 'Installed identities are ambiguous'
    assert set(prior) - set(target) == set(retired) and not set(target) - set(prior), 'Only explicitly retired UUIDs may disappear; new identities are not supported'
    changed = []
    for uid, pack in target.items():
        old = prior[uid]
        assert pack['side'] == old['side'], 'Pack side migration is not supported'
        old_manifest = c.read(Path(old['path']) / 'manifest.json')
        assert old_manifest['header']['uuid'] == uid and old_manifest['header']['version'] == old['version'], 'Installed manifest differs from selected reference'
        if pack['files'] == old['files'] and pack['version'] == old['version']:
            continue
        assert uid in batch['packs'], 'Changed pack is absent from the reviewed generated batch: ' + uid
        assert pack['version'] > old['version'], 'Changed bytes require a fresh version; downgrades are not supported: ' + uid
        manifest = c.read(absolute(batch['packs'][uid]['path']) / 'manifest.json')
        identities = lambda m: {(x['uuid'], x['type']) for x in m['modules']}
        assert identities(manifest) == identities(old_manifest), 'Module identity migration is not supported: ' + uid
        assert all(module['version'] == pack['version'] for module in manifest['modules']), 'Changed pack module versions must match the header'
        changed.append(uid)
    return changed


def idle_binding():
    binding = c.verify_server_binding()
    for side in SIDES:
        assert not (c.W / ('world_' + side + '_packs.json')).is_symlink(), 'Selected pack list is a symlink'
        assert not (c.W / (side + '_packs')).is_symlink() and not (c.B / (side + '_packs')).is_symlink(), 'Pack directory is a symlink'
    observed = c.summary()
    assert observed['name'] == c.SERVER and observed['status'] in {'STOPPED', 'RUNNING'}, 'Wait for the current lifecycle transition'
    assert type(observed['player_count']) is int and observed['player_count'] == 0, 'Staging requires a known zero-player state'
    return binding, observed


def pack_readback(receipt, original, binding, engine):
    current_binding = c.verify_server_binding()
    assert current_binding == binding and c.sha(c.B / 'bedrock_server') == engine, 'Server binding, properties or engine changed'
    inventory = c.live_inventory()
    want = {p['uuid']: p for p in receipt['packs']}
    assert {p['uuid'] for p in inventory['packs']} == set(want), 'Installed selected UUIDs differ'
    prior_paths = {p['uuid']: p['path'] for p in original['packs']}
    for row in inventory['packs']:
        pack = want[row['uuid']]
        assert row['path'] == prior_paths[row['uuid']], 'Installed pack path changed unexpectedly'
        assert all(row[key] == pack[key] for key in ('uuid', 'side', 'version', 'files')), 'Installed pack differs from the complete candidate receipt'
    for side in SIDES:
        assert inventory['refs'][side] == [{'pack_id': uid, 'version': want[uid]['version']} for uid in receipt['order'][side]], 'Installed selection/order differs'
    return {'binding': current_binding, 'summary': c.summary(), 'exact_candidate_files_and_refs': True}


def copy_bytes(root):
    # Logical size includes expansion of sparse files and hardlinked inputs.
    return sum(path.stat().st_size for path in root.rglob('*') if path.is_file())


def run(*, execute=False):
    options, candidate, batch_path, review_path, live_path, backup_state = configuration()
    batch = c.read(batch_path)
    receipt = candidate_input(candidate, batch)
    review = review_binding(candidate, batch_path, live_path)
    if not execute:
        return {'command': 'staging-repair', 'execute': False, 'candidate': str(candidate),
                'output': str(c.R), 'server': c.SERVER, 'world': str(c.W),
                'retire_uuids': options['retire_uuids'], 'review_input': review, **LOCAL}
    assert review_path.is_file() and c.read(review_path) == review, 'Root direct source review is missing or its exact inputs changed'
    assert not c.R.exists(), 'Preserve existing deployment output; choose a new output_dir'
    # Same maintenance mutex and visible lease as normal family deployment.
    with c.LOCK.open('a+') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        previous = c.lease_available()
        binding, initial = idle_binding()
        original = c.live_inventory()
        changed = selection(receipt, original, batch, options['retire_uuids'])
        assert c.R.parent.is_dir(), 'Create the evidence parent before deployment'
        assert c.R.parent.stat().st_dev == c.W.stat().st_dev == c.B.stat().st_dev, 'Package staging and rollback require the server filesystem'
        target = {p['uuid']: p for p in receipt['packs']}
        pack_bytes = sum(copy_bytes(candidate / (target[uid]['side'] + '_packs') / uid) for uid in changed)
        space = require_space(c.R.parent, 'Staging stopped backup and package copies', copy_bytes(c.W) + pack_bytes)
        c.R.mkdir()
        from family_update.memory_budget import require
        require('deploy')  # Existing light deployment cap; no native stage.
        c.atomic(c.R / 'source-review.json', review)
        c.atomic(c.R / 'previous-maintenance.json', previous)
        c.atomic(c.R / 'original-inventory.json', original)
        shutil.copy2(candidate / 'family-receipt.json', c.R / 'local-family-receipt.json')
        shutil.copy2(c.AUTHORIZATION, c.R / 'staging-authorization.json')
        result_path = c.R / 'staging-repair-result.json'
        result = {'state': 'prepared', 'created_at': c.now(), 'server': c.SERVER,
                  'world': str(c.W), 'candidate': str(candidate), 'before': initial,
                  'space': space, 'changed_uuids': changed, 'retire_uuids': options['retire_uuids'],
                  'world_backup': str(c.R / 'world-backup'),
                  'world_backup_receipt': str(c.R / 'world-backup-receipt.json'),
                  'package_rollback': str(c.R / 'package-rollback'),
                  'start_requested': False, 'save_database_restored': False, **LOCAL}
        c.atomic(result_path, result)
        lease = {'state': 'active', 'owner': c.OWNER, 'candidate': str(c.R),
                 'created_at': c.now(), 'server': c.SERVER, 'world': str(c.W),
                 'scope': 'staging-local-repair', 'receipt': str(result_path),
                 'authorization_source': str(c.AUTHORIZATION),
                 'authorization_sha256': c.sha(c.AUTHORIZATION)}
        c.atomic(c.LEASE, lease)
        try:
            c.assert_lease()
            binding_now, _ = idle_binding()
            assert binding_now == binding and c.live_inventory() == original, 'Concurrent staging configuration or package change'
            if initial['status'] != 'STOPPED':
                c.action('stop')
            binding_now, stopped = idle_binding()
            assert stopped['status'] == 'STOPPED' and binding_now == binding, 'Staging did not stop on the captured world'
            assert c.live_inventory() == original, 'Staging package inventory changed before backup'
            engine = c.sha(c.B / 'bedrock_server')
            # Normal shutdown can grow the DB; remeasure the stopped copy.
            result['stopped_space'] = require_space(c.R, 'Stopped staging backup and package copies', copy_bytes(c.W) + pack_bytes)
            capture(c.W, c.R / 'world-backup', c.R / 'world-backup-receipt.json')
            result['backup_rotation'] = adopt(backup_state, c.R / 'world-backup', c.R / 'world-backup-receipt.json')
            result['state'] = 'backed_up_stopped'
            c.atomic(result_path, result)
            # The full candidate is already immutable; copy only changed packs.
            prior = {p['uuid']: p for p in original['packs']}
            moves = []
            for uid in [*changed, *options['retire_uuids']]:
                old = prior[uid]
                source = Path(old['path'])
                assert source.parent in {c.W / (old['side'] + '_packs'), c.B / (old['side'] + '_packs')}, 'Pack path escaped the staging server'
                backup = c.R / 'package-rollback' / (old['side'] + '_packs') / uid
                backup.parent.mkdir(parents=True, exist_ok=True)
                staged = c.R / 'package-staged' / (old['side'] + '_packs') / uid
                if uid in target:
                    staged.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copytree(candidate / (old['side'] + '_packs') / uid, staged)
                    assert c.hashes(staged) == target[uid]['files'], 'Staged package copy differs'
                moves.append({'uuid': uid, 'original': str(source), 'rollback': str(backup),
                              'staged': str(staged) if uid in target else None})
            c.atomic(c.R / 'package-moves.json', {'moves': moves, 'automatic_restore': False})
            assert review_binding(candidate, batch_path, live_path) == review and c.read(review_path) == review, 'Reviewed source/candidate/config changed before installation'
            c.assert_lease()
            assert idle_binding()[1]['status'] == 'STOPPED' and c.live_inventory() == original, 'Staging changed while preparing packages'
            for move in moves:
                os.replace(move['original'], move['rollback'])
                if move['staged']:
                    os.replace(move['staged'], move['original'])
            for side in SIDES:
                filename = 'world_' + side + '_packs.json'
                assert not (c.W / filename).is_symlink(), 'Selected pack list is a symlink'
                shutil.copy2(candidate / filename, c.W / filename)
            # No DB/metadata write is allowed before normal BDS startup.
            before = c.read(c.R / 'world-backup-receipt.json')['files']
            data_files = lambda rows: {key: digest for key, digest in rows.items() if not key.startswith(('behavior_packs/', 'resource_packs/')) and key not in {'world_behavior_packs.json', 'world_resource_packs.json'}}
            data = {}
            for path in c.W.iterdir():
                if path.name in {'behavior_packs', 'resource_packs', 'world_behavior_packs.json', 'world_resource_packs.json'}:
                    continue
                assert not path.is_symlink(), 'World data is a symlink'
                if path.is_dir():
                    data.update({path.name + '/' + key: digest for key, digest in c.hashes(path).items()})
                elif path.is_file():
                    data[path.name] = c.sha(path)
            assert data == data_files(before), 'World/player/item data changed before normal start'
            result['installed_readback'] = pack_readback(receipt, original, binding, engine)
            result['state'] = 'installed_stopped'
            c.atomic(result_path, result)
            result['start_requested'] = True
            c.atomic(result_path, result)  # Persist ambiguity before sending POST.
            c.action('start')
            result['readback'] = pack_readback(receipt, original, binding, engine)
            assert result['readback']['summary']['status'] == 'RUNNING', 'Staging is not running after installation'
            result.update(state='staging_deployed_running', completed_at=c.now())
            c.atomic(result_path, result)
            lease.update(state='completed', completed_at=c.now(), status='running')
            c.atomic(c.LEASE, lease)
            return result
        except BaseException as error:
            result.update(state='failed', error=str(error), failed_at=c.now(),
                          recovery_required=True,
                          world_may_have_new_data=result['start_requested'],
                          automatic_restore=False)
            try:
                result['observed_summary'] = c.summary()
            except Exception as observation_error:
                result['summary_error'] = str(observation_error)
            c.atomic(result_path, result)
            # Retain the active lease and all actual files. An uncertain start
            # may have saved new data even if its API response was rejected.
            lease.update(recovery_required=True, failed_at=c.now(), status='inspect_actual_state')
            c.atomic(c.LEASE, lease)
            raise
