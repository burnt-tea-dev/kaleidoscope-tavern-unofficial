"""Install one directly reviewed local family on the authorized staging world.

This transaction deliberately has no CI, native rehearsal or data-repair stages.
It never produces LIVE admission and never restores world data automatically.
"""
import fcntl
import os
from pathlib import Path
import shutil
import sys
import uuid

import family_bundle
import family_guard
import world_backup
from family_update import common as c
from family_update.storage import require_space
from family_update.source_batch import generated_pack, project_staging, source_provenance, staging_advisories


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
    assert live['server_name'] != c.SERVER and not world_backup.overlaps(live_root, c.B) and not world_backup.overlaps(live_world, c.W), 'Staging command cannot select LIVE'
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
    assert all(not world_backup.overlaps(candidate, path) for path in protected), 'Candidate overlaps deployment, server or source data'
    assert all(not world_backup.overlaps(c.R, path) for path in [live_root, live_world, absolute(live['quality_dir']), *source_roots, batch, review, c.AUTHORIZATION, live_path, backup_state]), 'Output overlaps a protected input or LIVE'
    assert Path(sys.executable).absolute() == c.PY, 'Use the configured Python interpreter'
    return options, candidate, batch, review, live_path, backup_state


def candidate_input(candidate, batch, sources, batch_path):
    receipt = c.read(candidate / 'family-receipt.json')
    assert receipt['schema'] == 1 and set(receipt['order']) == set(SIDES), 'Complete family receipt required'
    owned_sources = {source['repository']: source['commit'] for source in sources.values() if 'repository' in source}
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
    for side in SIDES:
        order = receipt['order'][side]
        assert len(order) == len(set(order)) and set(order) == {uid for uid, p in by_uuid.items() if p['side'] == side}, 'Incomplete candidate order'
        directory = candidate / (side + '_packs')
        assert not directory.is_symlink() and {p.name for p in directory.iterdir()} == set(order), 'Unexpected candidate pack directories'
        assert c.read(candidate / ('world_' + side + '_packs.json')) == [{'pack_id': uid, 'version': by_uuid[uid]['version']} for uid in order], 'Candidate selection differs from its full receipt'
    update_uuids = receipt.get('staging_updates')
    if update_uuids is None:
        # Older assemble_batch receipts kept inherited rows in the same batch.
        # Their source descriptors identify which inputs this run introduced.
        update_uuids = [uid for uid in batch['packs'] if uid in by_uuid and
                        by_uuid[uid]['source'].get('source_batch') == str(batch_path)]
        if not update_uuids:
            assert not batch.get('parent_source_batch'), 'Inherited batch lacks an explicit update selection'
            update_uuids = list(batch['packs'])
    assert len(set(update_uuids)) == len(update_uuids) and set(update_uuids) <= batch['packs'].keys() & by_uuid.keys(), 'Candidate omits a specified batch input'
    updates = {}
    for uid in update_uuids:
        row = batch['packs'][uid]
        actual_uid, actual, files = generated_pack(row['name'], row['side'], row['path'])
        assert actual_uid == uid and all(row[key] == value for key, value in actual.items()), 'Normally generated input changed: ' + uid
        pack = by_uuid[uid]
        assert pack['side'] == {'BP': 'behavior', 'RP': 'resource'}[row['side']], 'Generated input side changed'
        assert pack['files'] == files and pack['version'] == row['version'], 'Candidate is not the exact generated input: ' + uid
        updates[uid] = pack
    return receipt, updates


def review_binding(candidate, batch_path, live_path):
    """Return the validated batch, receipt and their direct-review binding."""
    batch, receipt, review, _ = deployment_inputs(candidate, batch_path, live_path)
    return batch, receipt, review


def deployment_inputs(candidate, batch_path, live_path):
    assert c.read(c.CONFIG_PATH) == c.CONFIG, 'Loaded staging configuration changed'
    batch = c.read(batch_path)
    sources = source_provenance(batch, c.SOURCES, c.EXTENSION)
    receipt, updates = candidate_input(candidate, batch, sources, batch_path)
    tools = Path(__file__).resolve().parents[1]
    runner_paths = {tools / name for name in (
        'family_update.py',
        'family_update/__init__.py', 'family_update/common.py',
        'family_update/staging_repair.py', 'family_update/source_batch.py',
        'family_update/storage.py', 'family_update/memory_budget.py')}
    runner_paths.update({Path(family_bundle.__file__).resolve(), Path(family_guard.__file__).resolve(),
                         Path(world_backup.__file__).resolve(),
                         c.T / 'tools/family_guard.py'})
    review = {'schema': 2, 'scope': 'direct-source-review-staging',
            'config_sha256': c.sha(c.CONFIG_PATH),
            'authorization_sha256': c.sha(c.AUTHORIZATION),
            'live_config_sha256': c.sha(live_path),
            'api_module_sha256': c.sha(c.CONFIG['api_module']),
            'candidate_receipt_sha256': c.sha(candidate / 'family-receipt.json'),
            'source_batch_sha256': c.sha(batch_path),
            'sources': sources,
            'runner_sha256': {str(path): c.sha(path) for path in sorted(runner_paths)}}
    return batch, receipt, review, updates


def selection(original, updates, batch, retired):
    projected, changed = project_staging(original, updates, retired)
    prior = {row['uuid']: row for row in original['packs']}
    for uid in changed:
        identities = lambda modules: {(row['uuid'], row['type']) for row in modules}
        assert identities(batch['packs'][uid]['modules']) == identities(prior[uid]['modules']), 'Module identity migration is not supported: ' + uid
    return projected, changed


def idle_binding():
    binding = c.verify_server_binding()
    for side in SIDES:
        assert not (c.W / ('world_' + side + '_packs.json')).is_symlink(), 'Selected pack list is a symlink'
        assert not (c.W / (side + '_packs')).is_symlink() and not (c.B / (side + '_packs')).is_symlink(), 'Pack directory is a symlink'
    observed = c.summary()
    assert observed['name'] == c.SERVER and observed['status'] in {'STOPPED', 'RUNNING'}, 'Wait for the current lifecycle transition'
    assert type(observed['player_count']) is int and observed['player_count'] == 0, 'Staging requires a known zero-player state'
    return binding, observed


def installed_inventory():
    return c.pack_inventory(c.W, c.B, include_manifest=True, hash_files=c.hashes)


def pack_readback(applied, receipt, binding, engine):
    current_binding = c.verify_server_binding()
    assert current_binding == binding and c.sha(c.B / 'bedrock_server') == engine, 'Server binding, properties or engine changed'
    inventory = installed_inventory()
    expected = {p['uuid']: p for p in applied['packs']}
    assert {p['uuid'] for p in inventory['packs']} == set(expected), 'Installed selected UUIDs differ'
    for row in inventory['packs']:
        pack = expected[row['uuid']]
        assert all(row[key] == pack[key] for key in ('uuid', 'side', 'version', 'files', 'path')), 'Installed pack differs from the applied selection'
    assert inventory['refs'] == applied['refs'], 'Installed selection/order differs'
    candidate = {p['uuid']: p for p in receipt['packs']}
    exact = (candidate.keys() == expected.keys() and
             all(expected[uid]['files'] == pack['files'] for uid, pack in candidate.items()) and
             all(refs == [{'pack_id': uid, 'version': candidate[uid]['version']} for uid in receipt['order'][side]]
                 for side, refs in applied['refs'].items()))
    return {'binding': current_binding, 'summary': c.summary(),
            'exact_applied_files_and_refs': True, 'exact_candidate_files_and_refs': exact}


def copy_bytes(root):
    # Logical size includes expansion of sparse files and hardlinked inputs.
    return sum(path.stat().st_size for path in root.rglob('*') if path.is_file())


def retire_replaced_package_rollbacks(result, batch, live_path, backup_state):
    from family_update.cleanup_copies import absolute_paths
    from family_update.retention import _assert_idle, _mount_paths, _walk

    cleanup_path = Path(c.read(c.AUTHORIZATION)['live_config']).with_name('cleanup.json')
    cleanup = c.read(cleanup_path)
    assert Path(cleanup['lock_file']).resolve() == c.LOCK and Path(cleanup['lease_file']).resolve() == c.LEASE, 'Cleanup configuration has another maintenance lock or lease'
    expected_namespace = cleanup['retention_pid_namespace']
    assert os.readlink('/proc/self/ns/pid') == expected_namespace, 'Package retirement must observe the configured host process namespace'
    state = c.read(backup_state)
    current = next(row for row in state['current'] if row['world'] == str(c.W))
    assert Path(current['backup']) == c.R / 'world-backup', 'Current staging recovery point changed'
    lease = c.read(c.LEASE)
    assert lease.get('candidate') == str(c.R) and lease.get('state') == 'completed', 'Maintenance owner changed'
    assert c.read(c.CONFIG_PATH) == c.CONFIG and c.read(c.CONFIG['staging_repair']['source_batch']) == batch, 'Current staging inputs changed'
    live = c.read(live_path)
    references = list(absolute_paths([c.CONFIG, batch, live, state['current'], lease]))
    references += [c.B, c.W, c.Q, c.R, Path(result['candidate'])]
    references += list(map(Path, state['protected_worlds']))
    references += list(absolute_paths(c.read(c.Q / 'senluo-policy.json')))
    references += list(absolute_paths(c.read(Path(live['quality_dir']) / 'senluo-policy.json')))
    removed = []
    for name in result['backup_rotation']['retired']:
        old_backup = Path(name)
        if old_backup.name != 'world-backup' or old_backup.parent == c.R:
            continue
        report_path = old_backup.parent / 'staging-repair-result.json'
        if not report_path.is_file():
            continue
        old = c.read(report_path)
        target = old_backup.parent / 'package-rollback'
        if not target.exists():
            continue
        assert old['state'] == 'staging_deployed_running' and old['world'] == str(c.W), 'Old staging deployment is not completed on this world'
        assert old['completed_at'] < result['completed_at'], 'Old staging deployment is not superseded'
        assert old['readback']['summary']['status'] == 'RUNNING', 'Old staging deployment has no successful readback'
        assert old['world_backup'] == str(old_backup) and old['package_rollback'] == str(target), 'Old staging copy ownership differs'
        if any(world_backup.overlaps(target, protected) for reference in references
               for protected in (reference, reference.resolve())):
            continue
        _walk(target, old_backup.parent, _mount_paths())
        _assert_idle(target, Path('/proc'))
        shutil.rmtree(target)
        removed.append(str(target))
    return removed


def run(*, execute=False):
    options, candidate, batch_path, review_path, live_path, backup_state = configuration()
    batch, receipt, review, updates = deployment_inputs(candidate, batch_path, live_path)
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
        initial_inventory = installed_inventory()
        retired = options['retire_uuids']
        _, proposed = selection(initial_inventory, updates, batch, retired)
        assert c.R.parent.is_dir(), 'Create the evidence parent before deployment'
        assert c.R.parent.stat().st_dev == c.W.stat().st_dev == c.B.stat().st_dev, 'Package staging and rollback require the server filesystem'
        inputs = {uid: candidate / (pack['side'] + '_packs') / uid for uid, pack in updates.items()}
        pack_bytes = sum(copy_bytes(inputs[uid]) for uid in proposed)
        space = require_space(c.R.parent, 'Staging stopped backup and package copies', copy_bytes(c.W) + pack_bytes)
        c.R.mkdir()
        from family_update.memory_budget import require
        require('deploy')  # Existing light deployment cap; no native stage.
        c.atomic(c.R / 'source-review.json', review)
        c.atomic(c.R / 'previous-maintenance.json', previous)
        c.atomic(c.R / 'original-inventory.json', initial_inventory)
        shutil.copy2(candidate / 'family-receipt.json', c.R / 'local-family-receipt.json')
        shutil.copy2(c.AUTHORIZATION, c.R / 'staging-authorization.json')
        result_path = c.R / 'staging-repair-result.json'
        result = {'state': 'prepared', 'created_at': c.now(), 'server': c.SERVER,
                  'world': str(c.W), 'candidate': str(candidate), 'before': initial,
                  'space': space, 'changed_uuids': proposed, 'retire_uuids': retired,
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
            binding_now, observed = idle_binding()
            assert binding_now == binding, 'Concurrent staging server binding change'
            if observed['status'] != 'STOPPED':
                c.action('stop')
            binding_now, stopped = idle_binding()
            assert stopped['status'] == 'STOPPED' and binding_now == binding, 'Staging did not stop on the captured world'
            engine = c.sha(c.B / 'bedrock_server')
            # Normal shutdown can grow the DB; remeasure the stopped copy.
            result['stopped_space'] = require_space(c.R, 'Stopped staging backup and package copies', copy_bytes(c.W) + pack_bytes)
            world_backup.capture(c.W, c.R / 'world-backup', c.R / 'world-backup-receipt.json')
            result['backup_rotation'] = world_backup.adopt(backup_state, c.R / 'world-backup', c.R / 'world-backup-receipt.json')
            result['state'] = 'backed_up_stopped'
            c.atomic(result_path, result)
            assert review_binding(candidate, batch_path, live_path)[2] == review and c.read(review_path) == review, 'Reviewed input/candidate/config changed before installation'
            original = installed_inventory()
            staged_inputs = {}
            while True:
                applied, changed = selection(original, updates, batch, retired)
                pending = [uid for uid in changed if uid not in staged_inputs]
                if not pending:
                    break
                require_space(c.R, 'Selected staging package copies', sum(copy_bytes(inputs[uid]) for uid in pending))
                for uid in pending:
                    staged = c.R / 'package-staged' / (updates[uid]['side'] + '_packs') / uid
                    staged.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copytree(inputs[uid], staged)
                    assert c.hashes(staged) == updates[uid]['files'], 'Staged package copy differs'
                    staged_inputs[uid] = staged
                original = installed_inventory()
            c.assert_lease()
            binding_now, observed = idle_binding()
            assert observed['status'] == 'STOPPED' and binding_now == binding, 'Staging target changed while preparing packages'
            # Capture the exact selection immediately preceding the package writes.
            c.atomic(c.R / 'original-inventory.json', original)
            result['changed_uuids'] = changed
            result['installed_advisories'] = staging_advisories(initial_inventory, original, updates)
            result['dependency_check'] = {'mode': 'advisory', 'differences': family_bundle.exact_dependency_differences(applied['packs'])}
            c.atomic(result_path, result)
            prior = {p['uuid']: p for p in original['packs']}
            moves = []
            for uid in [*changed, *(uid for uid in retired if uid in prior)]:
                old = prior[uid]
                source = Path(old['path'])
                assert source.parent in {c.W / (old['side'] + '_packs'), c.B / (old['side'] + '_packs')}, 'Pack path escaped the staging server'
                backup = c.R / 'package-rollback' / (old['side'] + '_packs') / uid
                backup.parent.mkdir(parents=True, exist_ok=True)
                staged = staged_inputs.get(uid)
                moves.append({'uuid': uid, 'original': str(source), 'rollback': str(backup),
                              'staged': str(staged) if staged else None})
            ref_backups = {}
            for side in SIDES:
                if applied['refs'][side] == original['refs'][side]:
                    continue
                path = c.W / ('world_' + side + '_packs.json')
                backup = c.R / 'package-rollback' / path.name
                backup.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(path, backup)
                ref_backups[side] = backup
            c.atomic(c.R / 'package-moves.json', {'moves': moves, 'automatic_restore': False,
                      'original_refs': {side: str(path) for side, path in ref_backups.items()}})
            for move in moves:
                os.replace(move['original'], move['rollback'])
                if move['staged']:
                    os.replace(move['staged'], move['original'])
            for side in ref_backups:
                c.atomic(c.W / ('world_' + side + '_packs.json'), applied['refs'][side])
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
            result['installed_readback'] = pack_readback(applied, receipt, binding, engine)
            result['state'] = 'installed_stopped'
            c.atomic(result_path, result)
            result['start_requested'] = True
            c.atomic(result_path, result)  # Persist ambiguity before sending POST.
            c.action('start')
            result['readback'] = pack_readback(applied, receipt, binding, engine)
            assert result['readback']['summary']['status'] == 'RUNNING', 'Staging is not running after installation'
            result.update(state='staging_deployed_running', completed_at=c.now())
            c.atomic(result_path, result)
            lease.update(state='completed', completed_at=c.now(), status='running')
            c.atomic(c.LEASE, lease)
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

        try:
            result['retired_package_rollbacks'] = retire_replaced_package_rollbacks(result, batch, live_path, backup_state)
        except Exception as error:
            result['package_retirement_warning'] = str(error)
        c.atomic(result_path, result)
        return result
