"""One exact world/global alias view for native QA and later revalidation.

The original global inventory remains immutable provenance. This projection is
only an engine-input comparison: it never authorizes installation or recovery.
"""
import hashlib
import json
import os
from pathlib import Path
import stat

from family_update import common as c
from family_update.managed_drift_recovery import files_sha256 as fingerprint


def regular_hashes(root):
    root = Path(root)
    assert root.is_dir() and not root.is_symlink() and root.resolve() == root, 'Engine alias must be a real directory'
    for directory, dirs, files in os.walk(root, followlinks=False):
        for name in dirs + files:
            info = (Path(directory) / name).lstat()
            assert stat.S_ISREG(info.st_mode) or stat.S_ISDIR(info.st_mode), 'Engine alias contains a nonregular entry'
    return c.hashes(root)


def document(path):
    path = Path(path)
    assert path.is_file() and not path.is_symlink() and path.resolve() == path, 'Engine projection requires regular evidence'
    raw = path.read_bytes()
    return json.loads(raw), {'path': str(path), 'sha256': hashlib.sha256(raw).hexdigest()}


def parked_alias(original, candidate, candidate_ref):
    """Accept only this run's complete installed relocation, including resume.

    Keep observed-global-displaced for the current usable rollback. Its bytes
    remain necessary even after a successful deployment and completed lease.
    """
    assert c.CONFIG.get('managed_drift_recovery'), 'Missing engine alias has no reviewed relocation'
    source = Path(original['path'])
    displaced = c.R / 'observed-global-displaced' / (original['side'] + '_packs') / source.name
    assert regular_hashes(displaced) == original['files'], 'Parked engine alias bytes differ'
    reviewed, reviewed_ref = document(c.R / 'reviewed-family-receipt.json')
    assert reviewed['assembled_receipt'] == candidate_ref, 'Parked alias belongs to a different candidate'
    review, review_ref = document(Path(c.CONFIG['managed_drift_recovery']))
    assert review_ref in reviewed['evidence']['reports'], 'Parked alias review is not in the admitted receipt'
    retained = review['preserved_existing_inputs']
    assert retained['installation_location'] == 'world' and original['uuid'] in review['observed']['added_uuids']
    pin = retained['packs'][original['uuid']]
    assert pin['global_path'] == str(source) and pin['side'] == original['side'] and pin['version'] == original['version']
    assert pin['manifest_sha256'] == original['files']['manifest.json'] and pin['files_sha256'] == fingerprint(original['files']), 'Parked alias review bytes differ'
    admission, _ = document(c.R / 'admission-policy.json')
    policy, _ = document(c.Q / 'senluo-policy.json')
    assert admission['approved_receipt'] == policy['approved_receipt'] == reviewed_ref['path'], 'Parked alias policy differs'
    inherited = dict(policy)
    for key in ['installed', 'hold_reason']:
        if key in admission:
            inherited[key] = admission[key]
        else:
            inherited.pop(key, None)
    assert inherited == admission, 'Parked alias admission changed'
    installed_policy = policy['installed']
    assert installed_policy['receipt'] == reviewed_ref['path'] and installed_policy['receipt_sha256'] == reviewed_ref['sha256']
    installed_rows = [row for row in installed_policy['packs'] if row['uuid'] == candidate['uuid']]
    assert len(installed_rows) == 1 and all(installed_rows[0][key] == candidate[key] for key in ['side', 'version', 'files']), 'Parked alias installed policy differs'
    installed = c.W / (candidate['side'] + '_packs') / candidate['uuid']
    assert regular_hashes(installed) == candidate['files'], 'Installed engine alias bytes differ'
    rollback, _ = document(c.R / 'rollback-map.json')
    assert rollback.get('incomplete_rollback') is not True
    assert rollback['original_inventory'] == str(c.R / 'production-before/inventory.json')
    assert rollback['backup'] == str(c.R / 'production-snapshot')
    assert rollback['retired'].count([str(displaced), str(source)]) == 1 and str(installed) in rollback['installed'], 'Parked alias retirement differs'
    result, _ = document(c.R / 'deployment-result.json')
    assert result['state'] in ['installed_stopped', 'deployed_running'] and result['guard_admission_passed'] is True
    assert result['receipt_sha256'] == reviewed_ref['sha256'] and result['assembled_receipt_sha256'] == candidate_ref['sha256']
    lease, _ = document(c.LEASE)
    assert lease['owner'] == c.OWNER and lease['candidate'] == str(c.R) and lease['candidate_receipt_sha256'] == candidate_ref['sha256'], 'Parked alias maintenance owner differs'
    assert lease['state'] in ['active', 'completed'], 'Parked alias has no valid maintenance state'
    if result['state'] == 'deployed_running' or lease['state'] == 'completed':
        assert result['state'] == 'deployed_running'
        assert result['poststart_report'] == str(c.R / 'poststart-verification.json')
        post, _ = document(c.R / 'poststart-verification.json')
        assert post['ok'] is True and post['summary']['status'] == 'RUNNING' and post['summary']['name'] == c.SERVER
        assert post['receipt_sha256'] == reviewed_ref['sha256'] and post['exact_pack_files_and_order'] is True
        if lease['state'] == 'completed':
            assert lease['receipt'] == reviewed_ref['path'] and lease['status'] == 'running_for_user_acceptance' and lease['completed_at']


def project(trees, world_receipt):
    """Remove only captured exact aliases; return stable compact evidence."""
    candidates = {row['uuid']: row for row in world_receipt['packs']}
    assert len(candidates) == len(world_receipt['packs']), 'World receipt duplicates an identity'
    inventory_path = c.R / 'production-before/inventory.json'
    if inventory_path.exists():
        original, inventory_ref = document(inventory_path)
    else:
        original, inventory_ref = {'packs': []}, None
    if c.CONFIG.get('fresh_world'):
        # Old active globals are rollback inputs, not part of the curated world.
        # The same roots are parked by deployment before its normal start.
        aliases = []
        for row in original['packs']:
            path = Path(row['path'])
            if path.parent != c.B / (row['side'] + '_packs'):
                continue
            parked = c.R / 'production-rollback' / (row['side'] + '_packs') / path.name
            assert regular_hashes(path if path.exists() else parked) == row['files'], 'Old global rollback input changed'
            root = row['side'] + '_packs'
            for relative in [p for p in trees[root] if p.startswith(path.name + '/')]:
                del trees[root][relative]
            aliases.append({'uuid': row['uuid'], 'side': row['side'], 'global_path': str(path),
                            'files_sha256': fingerprint(row['files'])})
        excluded = {row['global_path'] for row in aliases}
        for side in ['behavior', 'resource']:
            for manifest in (c.B / (side + '_packs')).glob('*/manifest.json'):
                uid = c.read(manifest)['header']['uuid']
                if uid in candidates:
                    assert str(manifest.parent) in excluded, 'Uncaptured global candidate alias'
        return {'schema': 1, 'captured_inventory': inventory_ref,
                'fresh_world': True, 'aliases': aliases}
    aliases = {}
    for row in original['packs']:
        if row['uuid'] not in candidates or not row.get('path'):
            continue
        path = Path(row['path'])
        if row['side'] not in ['behavior', 'resource'] or path.parent != c.B / (row['side'] + '_packs'):
            continue
        assert path.is_absolute() and path.resolve() == path, 'Captured global alias path is not canonical'
        assert row['uuid'] not in aliases, 'Captured global aliases duplicate an identity'
        aliases[row['uuid']] = row
    for side in ['behavior', 'resource']:
        for manifest in (c.B / (side + '_packs')).glob('*/manifest.json'):
            try:
                uid = c.read(manifest)['header']['uuid']
            except (ValueError, KeyError, TypeError):
                continue  # Unknown inputs remain visible and fully pinned.
            if uid in candidates:
                assert candidates[uid]['side'] == side, 'Global candidate alias has the wrong side'
                assert uid in aliases and manifest.parent == Path(aliases[uid]['path']), 'Uncaptured or ambiguous global candidate alias'
    if not aliases:
        return None
    capture, _ = document(c.R / 'production-before/capture.json')
    assert capture['inventory'] == inventory_ref, 'Captured global inventory changed'
    recorded, candidate_ref = document(c.C / 'family-receipt.json')
    assert recorded == world_receipt, 'Explicit world receipt differs from candidate'
    descriptors = []
    for uid, original in sorted(aliases.items()):
        candidate = candidates[uid]
        assert all(candidate[key] == original[key] for key in ['side', 'version', 'files']), 'Global candidate alias differs from captured bytes or identity'
        name = candidate.get('directory', uid)
        assert isinstance(name, str) and Path(name).name == name and name not in ['', '.', '..'], 'Unsafe candidate alias directory'
        candidate_path = c.C / (candidate['side'] + '_packs') / name
        assert regular_hashes(candidate_path) == candidate['files'], 'Current candidate alias bytes differ'
        source = Path(original['path'])
        if source.exists() or source.is_symlink():
            assert regular_hashes(source) == original['files'], 'Current global alias bytes differ'
        else:
            parked_alias(original, candidate, candidate_ref)
        root = original['side'] + '_packs'
        prefix = source.name + '/'
        for relative in [p for p in trees[root] if p.startswith(prefix)]:
            del trees[root][relative]
        descriptors.append({'uuid': uid, 'side': candidate['side'], 'version': candidate['version'],
                            'global_path': str(source), 'candidate_directory': name,
                            'files_sha256': fingerprint(candidate['files'])})
    return {'schema': 1, 'captured_inventory': inventory_ref,
            'candidate_receipt': candidate_ref, 'aliases': descriptors}
