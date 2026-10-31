"""Validate the owner's exact review of the currently installed inventory."""
import hashlib
import io
import json
import re
import subprocess
import tarfile
from pathlib import Path

from family_update import common as c
from family_update.managed_drift_recovery import files_sha256, inventory_sha256, matches_receipt


SIDES = {'behavior': 'BP', 'resource': 'RP'}
_SOURCE_STATE = None
_SOURCE_STATE_KEY = None


def _git(root, *args):
    return subprocess.check_output(['git', '-C', str(root), *args], text=True).strip()


def _committed_json(path, root, *, maintenance_review=False):
    path = Path(path)
    assert path.is_absolute() and path.is_file() and not path.is_symlink(), 'Review input must be a regular absolute path'
    root = Path(root).resolve()
    assert path == path.resolve(), 'Review input cannot pass through a symlink'
    relative = path.resolve().relative_to(root).as_posix()
    if maintenance_review:
        assert relative.startswith('maintenance/reviews/'), 'Current inventory review must be under maintenance/reviews'
    raw = path.read_bytes()
    assert raw == subprocess.check_output(['git', '-C', str(root), 'show', 'HEAD:' + relative]), 'Review input is not committed unchanged'
    return json.loads(raw), hashlib.sha256(raw).hexdigest()


def _profile():
    from stable_host_profiles import curated_profile
    catalog = curated_profile()
    selection = catalog['selection']
    value, digest = _committed_json(c.EXTENSION / selection['path'], c.EXTENSION)
    assert digest == selection['sha256'] and value == selection['value'], 'Curated profile changed from its committed binding'
    return value, digest


def _source_files(root, commit, runtime_path):
    archive = subprocess.check_output(['git', '-C', str(root), 'archive', '--format=tar', commit, runtime_path])
    prefix = runtime_path.rstrip('/') + '/'
    result, contents = {}, {}
    with tarfile.open(fileobj=io.BytesIO(archive), mode='r:') as bundle:
        for member in bundle.getmembers():
            if not member.isfile():
                continue
            assert member.name.startswith(prefix), 'Canonical runtime archive escaped its root'
            relative = member.name[len(prefix):]
            assert relative and '..' not in Path(relative).parts and Path(relative).as_posix() == relative
            stream = bundle.extractfile(member)
            assert stream is not None
            raw = stream.read()
            contents[relative] = raw
            result[relative] = hashlib.sha256(raw).hexdigest()
    assert result, 'Canonical runtime tree is missing'
    return result, contents


def _canonical_state():
    global _SOURCE_STATE, _SOURCE_STATE_KEY
    roots = {**c.SOURCES, **({'extension': c.EXTENSION} if c.EXTENSION else {})}
    key = (str(c.CONFIG_PATH), tuple(sorted((name, str(root.resolve())) for name, root in roots.items())))
    if _SOURCE_STATE is None or _SOURCE_STATE_KEY != key:
        _SOURCE_STATE = c.source_state(verify_remote=True)
        _SOURCE_STATE_KEY = key
    return _SOURCE_STATE


def _owned_identities():
    identities = {}
    state = _canonical_state()
    roots = {**c.SOURCES, **({'extension': c.EXTENSION} if c.EXTENSION else {})}
    assert set(roots) == {'tavern', 'grilling', 'world-liquor', 'extension'}, 'Complete canonical source family is required'
    for key, root in roots.items():
        row = state[key]
        assert Path(row['path']).resolve() == Path(root).resolve(), 'Canonical source state path differs'
        baseline = c.read(Path(root) / 'baseline.json')
        assert baseline['repository'] == row['repository'], 'Canonical baseline repository identity differs'
        for side, pack in baseline['packs'].items():
            uid = pack['uuid']
            assert uid not in identities, 'Canonical family pack UUID is duplicated'
            identities[uid] = {'repository_key': key, 'side': side, 'version': baseline['version'],
                               'runtime_path': baseline['runtime'][side], 'repository': baseline['repository']}
    return identities


def _verify_owned(uid, row, source, by_id):
    key = source['repository_key']
    root = c.EXTENSION if key == 'extension' else c.SOURCES[key]
    commit = source['commit']
    assert isinstance(commit, str) and re.fullmatch('[0-9a-f]{40}', commit), 'Reviewed source commit must be a full Git identity'
    state = _canonical_state()
    assert Path(state[key]['path']).resolve() == Path(root).resolve(), 'Reviewed source is not the configured canonical repository'
    head = state[key]['commit']
    subprocess.check_call(['git', '-C', str(root), 'merge-base', '--is-ancestor', commit, head])
    baseline = json.loads(subprocess.check_output(['git', '-C', str(root), 'show', commit + ':baseline.json']))
    current_baseline = c.read(root / 'baseline.json')
    assert baseline.get('repository') == current_baseline.get('repository') == state[key]['repository'], 'Owned source baseline identity changed'
    side = SIDES[row['side']]
    owned = baseline.get('packs', {}).get(side)
    runtime_path = baseline.get('runtime', {}).get(side)
    assert isinstance(owned, dict) and owned.get('uuid') == uid and baseline.get('version') == row['version'], 'Owned source baseline pack identity differs'
    assert source['runtime_path'] == runtime_path, 'Reviewed runtime path differs from canonical baseline'
    expected, contents = _source_files(root, commit, runtime_path)
    actual = row['files']
    repins = source['dependency_repins']
    assert isinstance(repins, list) and len(repins) == len(set(repins)), 'Invalid dependency repin list'
    assert set(expected) == set(actual), 'Owned source runtime has added or missing files'
    for name in expected:
        if name != 'manifest.json':
            assert actual[name] == expected[name], 'Owned runtime differs from canonical committed source: ' + name
    original = json.loads(contents['manifest.json'])
    actual_manifest_path = Path(row['path']) / 'manifest.json'
    actual_manifest = c.read(actual_manifest_path)
    approved = json.loads(json.dumps(original))
    dep_by_uid = {d.get('uuid'): d for d in approved.get('dependencies', [])}
    assert len(dep_by_uid) == len(approved.get('dependencies', [])), 'Canonical manifest has duplicate dependencies'
    assert set(repins) <= set(dep_by_uid), 'Repin names a dependency absent from canonical manifest'
    for peer_uid in repins:
        assert peer_uid in by_id, 'Repinned dependency is not present in observed inventory'
        dep_by_uid[peer_uid]['version'] = by_id[peer_uid]['version']
    assert actual_manifest == approved, 'Owned manifest changed outside reviewed dependency repins'
    actual_hash = hashlib.sha256(actual_manifest_path.read_bytes()).hexdigest()
    assert actual['manifest.json'] == actual_hash, 'Inventory manifest digest is stale'


def verify(inventory, policy=None):
    """Verify an unapproved observed inventory and return UUIDs to snapshot as preserved inputs."""
    if policy is None:
        policy = c.read(c.Q / 'senluo-policy.json')
    receipt_path = Path(policy['approved_receipt'])
    receipt = c.read(receipt_path)
    if matches_receipt(inventory, receipt):
        return set()
    review_path = Path(c.CONFIG['current_inventory_review'])
    review, _ = _committed_json(review_path, c.EXTENSION, maintenance_review=True)
    assert set(review) == {'schema', 'kind', 'authorization', 'prior_receipt_sha256', 'observed_inventory_sha256', 'curated_profile_sha256', 'packs', 'owned_sources'}
    assert review['schema'] == 1 and review['kind'] == 'owner_current_inventory'
    authorization = review['authorization']
    assert isinstance(authorization, dict)
    assert set(authorization) == {'source', 'request', 'at'}
    assert authorization.get('source') == 'user' and authorization.get('at') and authorization.get('request'), 'Owner authorization record is incomplete'
    assert review['prior_receipt_sha256'] == c.sha(receipt_path), 'Prior approved receipt changed'
    assert review['observed_inventory_sha256'] == inventory_sha256(inventory), 'Observed inventory differs from owner review'
    profile, profile_sha = _profile()
    assert review['curated_profile_sha256'] == profile_sha, 'Curated profile differs from owner review'
    packs = {row['uuid']: row for row in inventory['packs']}
    assert len(packs) == len(inventory['packs']) and set(packs) == set(review['packs']), 'Observed pack set differs from exact reviewed inventory'
    old = {row['uuid']: row for row in receipt['packs']}
    assert len(old) == len(receipt['packs']), 'Prior approved receipt has duplicate UUIDs'
    owned = review['owned_sources']
    canonical_owned = _owned_identities()
    assert set(owned) == set(canonical_owned) and set(owned) <= set(packs), 'Owned source review differs from current canonical family identities'
    for uid, row in packs.items():
        reviewed = review['packs'][uid]
        assert set(reviewed) == {'side', 'version', 'tree'}
        assert reviewed['side'] == row['side'] and reviewed['version'] == row['version']
        assert reviewed['tree'] == {'sha256': files_sha256(row['files']), 'files': len(row['files'])}, 'Pack tree differs from owner review'
        if uid in owned:
            assert set(owned[uid]) == {'repository_key', 'commit', 'runtime_path', 'dependency_repins'}, 'Owned source record has unknown fields'
            source_identity = canonical_owned[uid]
            assert owned[uid]['repository_key'] == source_identity['repository_key']
            assert owned[uid]['runtime_path'] == source_identity['runtime_path']
            _verify_owned(uid, row, owned[uid], packs)
            continue
        previous = old.get(uid)
        unchanged = previous is not None and previous['side'] == row['side'] and previous['version'] == row['version'] and previous['files'] == row['files']
        if unchanged:
            continue
        curated = [entry for entry in profile.get('retained_inputs', []) if entry.get('uuid') == uid and entry.get('side') == row['side']]
        replacements = [entry for family in profile.get('replacement_packs', {}).values()
                        for side, entry in family.items()
                        if entry.get('uuid') == uid and SIDES.get(row['side']) == side]
        accepted = curated + replacements
        assert len(accepted) == 1, 'Changed or new non-owned pack is not exactly curated'
        entry = accepted[0]
        tree = entry.get('output_tree') or entry.get('tree')
        assert entry.get('version', entry.get('output_version')) == row['version']
        assert tree == {'sha256': files_sha256(row['files']), 'files': len(row['files'])}, 'Curated retained input tree differs'
    return (set(packs) - set(old)) - set(owned)
