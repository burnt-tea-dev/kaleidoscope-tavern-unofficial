"""Exact committed drift repair; the drifted stack never becomes a rollback.

The review authorizes replacing one observed inventory with one normally gated
candidate. It does not approve the observed bytes, prove who installed them, or
permit rolling a world database back. Once identity adoption starts, the normal
deployment fail-stop rule still takes precedence.
"""
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import stat
import subprocess

from family_update import common as c

PROFILE = 'reviewed-managed-drift-repair-v1'
SIDES = ('behavior', 'resource')
FIELDS = ('uuid', 'side', 'version', 'files')
_INITIAL_STATE = None


def projection(inventory):
    """Portable full inventory; local directory names confer no authority."""
    rows = [{key: row[key] for key in FIELDS} for row in inventory['packs']]
    by_id = {row['uuid']: row for row in rows}
    assert len(by_id) == len(rows), 'Duplicate inventory identity'
    assert set(inventory['refs']) == set(SIDES), 'Both reference lists are required'
    seen = []
    for side in SIDES:
        for ref in inventory['refs'][side]:
            assert set(ref) == {'pack_id', 'version'}, 'Unexpected reference fields'
            row = by_id[ref['pack_id']]
            assert row['side'] == side and row['version'] == ref['version'], 'Reference identity differs'
            seen.append(row['uuid'])
    assert len(seen) == len(set(seen)) == len(rows) and set(seen) == set(by_id), 'Incomplete reference lists'
    return {'packs': sorted(rows, key=lambda row: row['uuid']), 'refs': inventory['refs']}


def inventory_sha256(inventory):
    raw = json.dumps(projection(inventory), sort_keys=True, separators=(',', ':'), ensure_ascii=False).encode()
    return hashlib.sha256(raw).hexdigest()


def files_sha256(files):
    return hashlib.sha256(json.dumps(files, sort_keys=True, separators=(',', ':'), ensure_ascii=False).encode()).hexdigest()


def receipt_inventory(receipt):
    by_id = {row['uuid']: row for row in receipt['packs']}
    assert len(by_id) == len(receipt['packs']), 'Duplicate receipt identity'
    return projection({'packs': receipt['packs'], 'refs': {
        side: [{'pack_id': uid, 'version': by_id[uid]['version']} for uid in receipt['order'][side]]
        for side in SIDES}})


def matches_receipt(inventory, receipt):
    return projection(inventory) == receipt_inventory(receipt)


def _committed(path):
    source = c.EXTENSION
    assert source, 'A canonical private source is required for drift repair'
    source = source.resolve()
    path = Path(path)
    assert path.is_absolute() and not path.is_symlink(), 'Review inputs must be explicit regular paths'
    relative = path.relative_to(source)
    assert relative.parts[0] == 'maintenance' and path.resolve() == source / relative, 'Review must belong to private maintenance source'
    raw = subprocess.check_output(['git', '-C', str(source), 'show', 'HEAD:' + relative.as_posix()])
    assert path.read_bytes() == raw, 'Drift review input is not committed unchanged'
    return {'path': str(path), 'sha256': hashlib.sha256(raw).hexdigest()}


def load_review():
    path = Path(c.CONFIG['managed_drift_recovery'])
    source = c.EXTENSION
    assert source, 'Drift repair requires its canonical private review'
    target = c.read(source / '.repo-target.json')
    assert target['private'] is True and target['repository'] == 'casama233/senluo-family-integration-private' and target['repository_id'] == 1406868911
    assert c.git(source, 'remote', 'get-url', 'origin').removesuffix('.git') == 'https://github.com/' + target['repository'], 'Drift review remote differs'
    assert c.git(source, 'branch', '--show-current') == 'main' and not c.git(source, 'status', '--porcelain'), 'Drift review requires clean canonical main'
    head = c.git(source, 'rev-parse', 'HEAD')
    assert c.git(source, 'ls-remote', 'origin', 'refs/heads/main').split()[0] == head, 'Drift review is not canonical remote main'
    binding = _committed(path)
    review = c.read(path)
    assert review['schema'] == 1 and review['kind'] == 'managed_drift_recovery' and review['profile'] == PROFILE
    assert review['safety'] == {
        'installer_authorization_proven': False, 'unknown_leaf_count': 0,
        'repair_only': True, 'keep_newest_database': True,
        'after_identity_adoption': 'retain_stopped_and_active_lease',
        'preserve_displaced_bytes': True}, 'Drift repair safety boundary differs'
    assert len(review['proofs']) == 3 and len({row['path'] for row in review['proofs']}) == 3, 'Three distinct provenance proofs are required'
    for proof in review['proofs']:
        relative = Path(proof['path'])
        assert not relative.is_absolute() and '..' not in relative.parts
        assert _committed(source / relative)['sha256'] == proof['sha256'], 'Committed provenance proof differs'
    if review['observed'].get('added_uuids') and 'preserved_existing_inputs' not in review:
        addition = review['preserved_additions']
        relative = Path(addition['path'])
        assert not relative.is_absolute() and '..' not in relative.parts
        assert _committed(source / relative)['sha256'] == addition['sha256'], 'Committed addition review differs'
    if review.get('allow_initially_stopped'):
        stopped = review['stopped_server_review']
        assert stopped['server_name'] == c.SERVER and stopped['reason'] == 'normal_idle_stop', 'Stopped server authorization differs'
        evidence = stopped['evidence']
        relative = Path(evidence['path'])
        assert not relative.is_absolute() and '..' not in relative.parts
        assert _committed(source / relative)['sha256'] == evidence['sha256'], 'Stopped owner evidence differs'
    assert review['rollback'] == {key: review['approved'][key] for key in ['receipt_sha256', 'assembled_receipt_sha256']}, 'Rollback must be the original approved stack'
    return review, binding


def _approved(review, policy=None):
    policy_path = (c.R / 'production-before/senluo-policy.json') if policy is not None else (c.Q / 'senluo-policy.json')
    policy = policy if policy is not None else c.read(policy_path)
    assert c.sha(policy_path) == review['approved']['policy_sha256'], 'Original policy changed'
    path = Path(policy['approved_receipt'])
    assert c.sha(path) == review['approved']['receipt_sha256'], 'Original reviewed receipt changed'
    receipt = c.read(path)
    assert len(receipt['packs']) == review['approved']['pack_count']
    assert receipt['assembled_receipt']['sha256'] == review['approved']['assembled_receipt_sha256']
    return receipt


def check_observed(inventory, policy=None):
    review, binding = load_review()
    approved = _approved(review, policy)
    assert inventory_sha256(inventory) == review['observed']['inventory_sha256'], 'Observed drift bytes or order changed'
    assert len(inventory['packs']) == review['observed']['pack_count']
    actual = {row['uuid']: row for row in inventory['packs']}
    old = {row['uuid']: row for row in approved['packs']}
    added = set(actual) - set(old)
    assert added == set(review['observed'].get('added_uuids', [])), 'Unreviewed identity appeared in observed drift'
    assert set(old) - set(actual) == set(review['observed']['missing_uuids']), 'Missing identities differ'
    changed = {uid for uid in set(actual) & set(old) if any(actual[uid][key] != old[uid][key] for key in FIELDS)}
    assert changed == set(review['observed']['changed_uuids']), 'Changed identities differ'
    assert all(actual[uid]['side'] == old[uid]['side'] for uid in set(actual) & set(old)), 'Observed pack side changed'
    if added:
        _review_additions(inventory, approved, review, policy)
    return review, binding


def _review_additions(inventory, approved, review, policy=None):
    """Reuse the original-archive gate; only reviewed missing rows are omitted."""
    from family_update.preserved_additions import review as review_additions
    if 'preserved_existing_inputs' in review:
        assert 'preserved_additions' not in review, 'Use one explicit addition admission mode'
        return _existing_inputs(inventory, approved, review, policy)
    missing = set(review['observed']['missing_uuids'])
    expected = {row['uuid']: row for row in approved['packs'] if row['uuid'] not in missing}
    order = {side: [uid for uid in approved['order'][side] if uid not in missing] for side in SIDES}
    policy = policy if policy is not None else c.read(c.Q / 'senluo-policy.json')
    observed = {'packs': [{key: row[key] for key in [*FIELDS, 'path']} for row in inventory['packs']], 'refs': inventory['refs']}
    adjusted, _ = review_additions(observed, expected, order, policy['managed_uuids'], reviewed_path=c.EXTENSION / review['preserved_additions']['path'])
    assert set(adjusted) - set(expected) == set(review['observed']['added_uuids']), 'Addition archive review exceeds committed drift scope'
    return adjusted


def _existing_inputs(inventory, approved, review, policy=None):
    """Retain exact existing global bytes without claiming an author release."""
    proof = review['preserved_existing_inputs']
    assert proof['schema'] == 1 and proof['kind'] == 'existing_unattributed_paired_input'
    assert proof['origin_status'] == 'unverified_existing_input' and proof['action'] == 'retain_exact_bytes'
    assert proof['installation_location'] == 'world', 'Retained input installation location differs'
    assert proof['original_archive_verified'] is False and proof['latest_stable_verified'] is False
    # This is an admission for the one reviewed existing add-on, not a general
    # exemption from the family namespace/ownership boundary.
    assert proof['definition_namespace'] == 'kaleidoscope_fishing', 'Unreviewed retained definition namespace'
    actual = {row['uuid']: row for row in inventory['packs']}
    ids = set(review['observed']['added_uuids'])
    assert len(ids) == len(proof['packs']) == 2 and set(proof['packs']) == ids, 'Existing input must be one exact complete pair'
    policy = policy if policy is not None else c.read(c.Q / 'senluo-policy.json')
    adjusted = {row['uuid']: row for row in approved['packs'] if row['uuid'] not in review['observed']['missing_uuids']}
    sides = set(); module_ids = set()
    for uid in sorted(ids):
        row, pin = actual[uid], proof['packs'][uid]
        path = Path(row['path'])
        assert path.is_absolute() and str(path) == pin['global_path'] and path.resolve() == path, 'Existing global input path differs'
        assert path.parent == c.B / (row['side'] + '_packs'), 'Existing input is not in the exact global pack root'
        assert row['side'] == pin['side'] and row['version'] == pin['version']
        assert row['files']['manifest.json'] == pin['manifest_sha256'] and files_sha256(row['files']) == pin['files_sha256'], 'Existing input bytes differ'
        if not path.exists():
            path = _displaced_existing_source(row, path)
        assert _files(path) == set(row['files']), 'Existing input has unsafe or unreviewed leaves'
        assert c.sha(path / 'manifest.json') == pin['manifest_sha256'], 'Existing input manifest changed'
        manifest = c.read(path / 'manifest.json')
        assert manifest['header']['uuid'] == uid and manifest['header']['version'] == row['version']
        assert manifest['modules'] == pin['modules'] and manifest['modules'], 'Existing input modules differ'
        assert all(module['version'] == row['version'] for module in manifest['modules'])
        side = 'resource' if all(module['type'] == 'resources' for module in manifest['modules']) else 'behavior'
        assert side == row['side'] and side not in sides, 'Existing input pair side differs'
        for module in manifest['modules']:
            assert module['uuid'] not in module_ids, 'Existing input duplicates a module identity'
            module_ids.add(module['uuid'])
        assert uid not in policy['managed_uuids'] and not any(dep.get('uuid') in policy['managed_uuids'] for dep in manifest.get('dependencies', [])), 'Managed ownership or dependencies cannot use retain-only admission'
        identifiers = []
        for directory in ['blocks', 'items', 'entities', 'entity']:
            for definition in (path / directory).rglob('*.json'):
                text = definition.read_text(encoding='utf-8-sig')
                text = re.sub(r'"(?:\\.|[^"\\])*"|//[^\n]*|/\*.*?\*/', lambda match: match[0] if match[0].startswith('"') else '', text, flags=re.S)
                identifiers.extend(re.findall(r'"identifier"\s*:\s*"([^"\s]+)"', text))
        assert all(identifier.startswith(proof['definition_namespace'] + ':') for identifier in identifiers), 'Retained input masks a managed or foreign definition'
        assert identifiers or side == 'resource', 'Retained behavior input has no reviewed definitions'
        sides.add(side)
        adjusted[uid] = {**row, 'source': {'owner': 'preserved', 'role': 'existing_unattributed_input',
            'origin_status': proof['origin_status'], 'original_archive_verified': False,
            'latest_stable_verified': False, 'action': 'retain_exact_bytes'}}
    assert sides == set(SIDES)
    return adjusted


def _displaced_existing_source(row, original_path):
    """Read the same original bytes after this stopped transaction moved them.

    Identity adoption revalidates original provenance after pack placement. Only
    this run's reviewed global displacement is a valid missing-source location.
    The captured inventory continues to describe its original global path.
    """
    c.assert_lease()
    assert c.summary()['status'] == 'STOPPED', 'Displaced provenance requires the stopped maintenance window'
    assert (c.R / 'production-staged').is_dir(), 'No reviewed installation stage for displaced provenance'
    admission = c.R / 'admission-policy.json'
    reviewed = c.R / 'reviewed-family-receipt.json'
    assembled = c.R / 'release-candidate/family-receipt.json'
    assert c.read(admission)['approved_receipt'] == str(reviewed), 'Displaced provenance admission differs'
    assert c.sha(c.Q / 'senluo-policy.json') == c.sha(admission), 'Displaced provenance policy is not the admitted candidate'
    digest = c.sha(assembled)
    assert c.read(reviewed)['assembled_receipt'] == {'path': str(assembled), 'sha256': digest}, 'Displaced provenance candidate differs'
    lease = c.read(c.LEASE)
    assert lease['candidate'] == str(c.R) and lease['candidate_receipt_sha256'] == digest, 'Displaced provenance belongs to another candidate'
    path = c.R / 'observed-global-displaced' / (row['side'] + '_packs') / original_path.name
    assert _files(path) == set(row['files']) and c.hashes(path) == row['files'], 'Displaced original input bytes changed'
    return path


def captured_addition_ids():
    review, _ = load_review()
    return set(review['observed'].get('added_uuids', []))


def global_relocations(original):
    review, _ = check_observed(original, c.read(c.R / 'production-before/senluo-policy.json'))
    if 'preserved_existing_inputs' not in review:
        return {}
    proof = review['preserved_existing_inputs']
    assert proof['installation_location'] == 'world'
    return {uid: Path(row['global_path']) for uid, row in proof['packs'].items()}


def retirement_target(original_pack, rollback, relocations):
    """Only exact reviewed global directories may leave the engine catalog."""
    source = Path(original_pack['path'])
    side = original_pack['side'] + '_packs'
    if original_pack['uuid'] in relocations:
        assert source == relocations[original_pack['uuid']] and source.parent == c.B / side, 'Global relocation source differs'
        return c.R / 'observed-global-displaced' / side / source.name
    assert source.parent == c.W / side, 'Unreviewed global relocation is forbidden'
    return rollback / side / source.name


def input_refs():
    if not c.CONFIG.get('managed_drift_recovery'):
        return {}
    review, binding = load_review()
    result = {'managed_drift_recovery': binding['sha256']}
    result.update({'managed_drift_proof:' + row['path']: row['sha256'] for row in review['proofs']})
    if review['observed'].get('added_uuids') and 'preserved_existing_inputs' not in review:
        result['managed_drift_additions_review'] = review['preserved_additions']['sha256']
        additions = c.read(c.EXTENSION / review['preserved_additions']['path'])
        for uid, row in additions['packs'].items():
            assert c.sha(row['artifact']['path']) == row['artifact']['sha256']
            result['managed_drift_addition_archive:' + uid] = row['artifact']['sha256']
    if review.get('allow_initially_stopped'):
        result['managed_drift_stopped_evidence'] = review['stopped_server_review']['evidence']['sha256']
    root, receipt = rollback_metadata(review)
    result['managed_drift_rollback_reviewed'] = c.sha(root.parent / 'reviewed-family-receipt.json')
    result['managed_drift_rollback_assembled'] = c.sha(root / 'family-receipt.json')
    return result


def validate_target(receipt, original, migration):
    review, _ = check_observed(original, c.read(c.R / 'production-before/senluo-policy.json'))
    target = review['target']
    identities = lambda rows: sorted([{key: row[key] for key in ['uuid', 'side', 'version']} for row in rows], key=lambda row: row['uuid'])
    assert identities(receipt['packs']) == identities(target['packs']) and receipt['order'] == target['order'], 'Candidate identities or order differ from drift repair review'
    assert c.sha(c.T / 'family/upstream.lock.json') == target['upstream_lock_sha256'], 'Candidate author lock differs'
    paths = {**c.SOURCES, 'extension': c.EXTENSION}
    assert set(target['owned_source_trees']) == set(paths)
    for name, path in paths.items():
        assert c.read(path / 'baseline.json')['source_trees'] == target['owned_source_trees'][name], 'Reviewed candidate runtime source differs: ' + name
    from family_update.identity_migration import plan_swaps
    swaps = plan_swaps(migration) if migration else []
    selected = lambda rows: sorted([{key: row[key] for key in ['old_uuid', 'new_uuid', 'side']} for row in rows], key=lambda row: row['old_uuid'])
    assert selected(swaps) == selected(target['swaps']), 'Reviewed identity swaps differ'
    before = {row['uuid'] for row in original['packs']}
    after = {row['uuid'] for row in receipt['packs']}
    old_swaps = {row['old_uuid'] for row in swaps}
    new_swaps = {row['new_uuid'] for row in swaps}
    additions = set(target['additions'])
    assert len(additions) == len(target['additions']) and not additions & (before | new_swaps), 'Additions overlap existing or swapped identities'
    assert old_swaps <= before and before - old_swaps | new_swaps | additions == after, 'Candidate repair identity closure differs'
    assert len(after) == len(receipt['packs']), 'Duplicate candidate identity'
    if 'preserved_existing_inputs' in review:
        actual = {row['uuid']: row for row in original['packs']}
        candidate = {row['uuid']: row for row in receipt['packs']}
        for uid in review['observed']['added_uuids']:
            assert all(candidate[uid][key] == actual[uid][key] for key in FIELDS), 'Retain-only input was changed by candidate'
            assert candidate[uid]['source']['owner'] == 'preserved', 'Retain-only input cannot masquerade as a current author release'
    return additions


def provenance_original(original, approved):
    """Keep observed bytes, adding approved archive origin and explicit drift."""
    review, binding = check_observed(original, c.read(c.R / 'production-before/senluo-policy.json'))
    assert receipt_inventory(approved) == receipt_inventory(_approved(review, c.read(c.R / 'production-before/senluo-policy.json')))
    prior = {row['uuid']: row for row in approved['packs']}
    if review['observed'].get('added_uuids'):
        prior = _review_additions(original, approved, review, c.read(c.R / 'production-before/senluo-policy.json'))
    packs = []
    for row in original['packs']:
        source = dict(prior[row['uuid']]['source'])
        if row['uuid'] in review['observed']['changed_uuids']:
            source['observed_reviewed_drift'] = {
                'review': binding, 'approved_receipt_sha256': review['approved']['receipt_sha256'],
                'approved_version': prior[row['uuid']]['version'],
                'observed_version': row['version'], 'original_drift_approved': False}
        packs.append({**row, 'source': source})
    return {**original, 'packs': packs, 'observed_reviewed_drift': binding}


def reviewed_order(original, migration):
    review, _ = check_observed(original, c.read(c.R / 'production-before/senluo-policy.json'))
    # Validate every existing swap and all additions even before payloads exist.
    target = review['target']
    synthetic_rows = [{**row} for row in target['packs']]
    if 'preserved_existing_inputs' in review:
        actual = {row['uuid']: row for row in original['packs']}
        for row in synthetic_rows:
            if row['uuid'] in review['observed']['added_uuids']:
                assert all(row[key] == actual[row['uuid']][key] for key in ['side', 'version']), 'Reviewed retained identity changed'
                row.update(files=actual[row['uuid']]['files'], source={'owner': 'preserved'})
    synthetic = {'packs': synthetic_rows, 'order': target['order']}
    validate_target(synthetic, original, migration)
    return {side: list(target['order'][side]) for side in SIDES}


def validate_initial_status(summary):
    global _INITIAL_STATE
    review, binding = load_review()
    assert summary['status'] in ['RUNNING', 'STOPPED'], 'Server is not in a stable deployable state'
    if summary['status'] == 'STOPPED':
        assert review.get('allow_initially_stopped') is True, 'Stopped deployment needs its exact owner review'
        assert summary['name'] == c.SERVER and summary['player_count'] == 0, 'Stopped server must be the reviewed empty server'
        assert c.sha(c.LEASE) == review['stopped_server_review']['lease_sha256'], 'Previous maintenance owner state changed'
        c.lease_available()
    _INITIAL_STATE = {'schema': 1, 'server': dict(summary), 'review': binding,
        'previous_lease': c.lease_available(), 'previous_lease_sha256': c.sha(c.LEASE),
        'restart_original_after_failure': summary['status'] == 'RUNNING'}
    return _INITIAL_STATE


def record_initial_status():
    # Preflight already checked the old lease before acquisition. The captured
    # prior owner record is immutable evidence; the current lease must be ours.
    c.assert_lease()
    assert _INITIAL_STATE is not None, 'Initial deployment owner state was not checked'
    status = c.summary()
    assert status['status'] == _INITIAL_STATE['server']['status'], 'Server state changed before lease acquisition'
    assert c.read(c.R / 'previous-maintenance.json') == _INITIAL_STATE['previous_lease'], 'Previous maintenance owner changed'
    if status['status'] == 'STOPPED':
        assert status['name'] == c.SERVER and status['player_count'] == 0
    c.atomic(c.R / 'deployment-initial-state.json', _INITIAL_STATE)


def restart_original_allowed():
    path = c.R / 'deployment-initial-state.json'
    if not path.is_file():
        return False
    _, binding = load_review()
    record = c.read(path)
    assert record == _INITIAL_STATE and record['review'] == binding, 'Initial owner state changed; do not restart'
    return record['restart_original_after_failure'] is True and record['server']['status'] == 'RUNNING'


def rollback_metadata(review):
    raw = Path(c.CONFIG['managed_drift_rollback_root'])
    assert raw.is_absolute() and not raw.is_symlink(), 'Trusted rollback needs an explicit immutable pack root'
    root = raw.resolve()
    for protected in [c.R, c.W, c.B, c.Q, *c.SOURCES.values(), c.EXTENSION]:
        if protected:
            protected = protected.resolve()
            assert root != protected and root not in protected.parents and protected not in root.parents, 'Trusted rollback overlaps active data'
    reviewed = c.read(root.parent / 'reviewed-family-receipt.json')
    assert c.sha(root.parent / 'reviewed-family-receipt.json') == review['rollback']['receipt_sha256']
    assert c.sha(root / 'family-receipt.json') == review['rollback']['assembled_receipt_sha256']
    assert reviewed['assembled_receipt'] == {'path': str(root / 'family-receipt.json'), 'sha256': review['rollback']['assembled_receipt_sha256']}
    assembled = c.read(root / 'family-receipt.json')
    assert receipt_inventory(reviewed) == receipt_inventory(assembled), 'Trusted assembled and reviewed payload differ'
    assert len(assembled['packs']) == review['approved']['pack_count']
    for side, refs in receipt_inventory(assembled)['refs'].items():
        assert c.read(root / ('world_' + side + '_packs.json')) == refs, 'Trusted rollback references differ'
    return root, assembled


def _files(root):
    """List regular files without following links, including otherwise hidden leaves."""
    result = set()
    assert root.is_dir() and not root.is_symlink()
    for directory, dirs, files in os.walk(root, followlinks=False):
        for name in dirs:
            assert not (Path(directory) / name).is_symlink(), 'Rollback contains a linked directory'
        for name in files:
            path = Path(directory) / name
            assert stat.S_ISREG(path.lstat().st_mode), 'Rollback contains a nonregular file'
            result.add(path.relative_to(root).as_posix())
    return result


def prepare_rollback(original):
    """Make and verify the extra pack-only copy before stopping or changing LIVE."""
    review, binding = check_observed(original)
    source, receipt = rollback_metadata(review)
    dest = c.R / 'trusted-pack-rollback'
    assert not dest.exists(), 'Preserve previous trusted rollback state'
    dest.mkdir()
    expected = receipt_inventory(receipt)
    for side in SIDES:
        roots = source / (side + '_packs')
        wanted = {row['uuid'] for row in expected['packs'] if row['side'] == side}
        assert {path.name for path in roots.iterdir()} == wanted, 'Trusted rollback contains unlisted pack roots'
    for row in expected['packs']:
        src = source / (row['side'] + '_packs') / row['uuid']
        assert _files(src) == set(row['files']), 'Trusted rollback file inventory differs'
        target = dest / (row['side'] + '_packs') / row['uuid']
        shutil.copytree(src, target, symlinks=True)
        assert _files(target) == set(row['files']) and c.hashes(target) == row['files'], 'Trusted rollback copy bytes differ'
        header = c.read(target / 'manifest.json')['header']
        assert header['uuid'] == row['uuid'] and header['version'] == row['version'], 'Trusted rollback manifest differs'
    for side, refs in expected['refs'].items():
        c.atomic(dest / ('world_' + side + '_packs.json'), refs)
    shutil.copy2(c.R / 'production-before/senluo-policy.json', dest / 'senluo-policy.json')
    assert c.sha(dest / 'senluo-policy.json') == review['approved']['policy_sha256']
    c.atomic(c.R / 'trusted-pack-rollback.json', {
        'schema': 1, 'state': 'prepared', 'review': binding,
        'observed_inventory_sha256': inventory_sha256(original),
        'trusted_inventory_sha256': inventory_sha256(expected),
        'receipt_sha256': review['rollback']['receipt_sha256'],
        'policy_sha256': review['approved']['policy_sha256'],
        'packs': expected['packs'], 'refs': expected['refs'], 'database_copied': False})


def _prepared(original):
    review, binding = load_review()
    record = c.read(c.R / 'trusted-pack-rollback.json')
    assert record['review'] == binding and record['observed_inventory_sha256'] == inventory_sha256(original)
    assert record['policy_sha256'] == review['approved']['policy_sha256'] and record['receipt_sha256'] == review['rollback']['receipt_sha256']
    assert record['database_copied'] is False and record['trusted_inventory_sha256'] == inventory_sha256(record)
    _, receipt = rollback_metadata(review)
    assert projection(record) == receipt_inventory(receipt), 'Prepared rollback metadata differs from immutable approved payload'
    assert c.sha(c.R / 'trusted-pack-rollback/senluo-policy.json') == review['approved']['policy_sha256'], 'Prepared original policy changed'
    return review, record


def verify_restored(original):
    review, record = _prepared(original)
    assert inventory_sha256(c.live_inventory()) == record['trusted_inventory_sha256'], 'Trusted complete rollback inventory not restored; do not start'
    assert c.sha(c.Q / 'senluo-policy.json') == review['approved']['policy_sha256'], 'Original policy not restored; do not start'
    assert c.G['audit'](c.W, c.read(c.Q / 'senluo-policy.json'))['ok'], 'Trusted rollback failed the original family audit'


def restore(original, retired, installed):
    """Preserve displaced packages; restore trusted packages and refs, never DB."""
    c.assert_lease()
    assert c.summary()['status'] == 'STOPPED', 'Pack recovery requires a stopped server'
    assert not any((c.R / name).exists() for name in ['production-container-recovery.json', 'production-identity-migration.json']), 'Identity adoption prohibits automatic pack rollback'
    review, record = _prepared(original)
    result = c.R / 'managed-drift-pack-recovery.json'
    if result.exists():
        assert c.read(result)['state'] == 'restored_trusted_packs', 'Incomplete trusted rollback requires operator recovery'
        verify_restored(original)
        return
    root = c.R / 'trusted-pack-rollback'
    for row in record['packs']:
        path = root / (row['side'] + '_packs') / row['uuid']
        assert _files(path) == set(row['files']) and c.hashes(path) == row['files'], 'Prepared trusted rollback was modified'
    world_roots = {c.W / (side + '_packs') for side in SIDES}
    global_roots = {c.B / (side + '_packs') for side in SIDES}
    original_paths = {Path(row['path']).absolute() for row in original['packs']}
    assert all(path.parent in world_roots | global_roots for path in original_paths), 'Original pack is outside world/global roots'
    # Unchanged global packs are preserved in place. The approved rollback refs
    # determine which are active; their bytes are never silently deleted.
    controlled = {path for path in original_paths if path.parent in world_roots} | {Path(path).absolute() for path in installed}
    for path in controlled:
        assert path.parent in {c.W / (side + '_packs') for side in SIDES}, 'Recovery source is outside world pack roots'
        assert not path.is_symlink(), 'Recovery source is linked'
    destinations = {c.W / (row['side'] + '_packs') / row['uuid'] for row in record['packs']}
    assert all(not path.exists() or path in controlled for path in destinations), 'Unreviewed rollback destination exists; preserve it and stop'
    # A second unreferenced directory with a restored UUID would make lookup
    # ambiguous. Inspect only manifest identities; unrelated roots stay intact.
    for side in SIDES:
        wanted = {row['uuid'] for row in record['packs'] if row['side'] == side}
        for directory in {c.W / (side + '_packs'), c.B / (side + '_packs')}:
            if not directory.is_dir():
                continue
            for path in directory.iterdir():
                if path not in controlled and (path / 'manifest.json').is_file():
                    assert c.read(path / 'manifest.json')['header']['uuid'] not in wanted, 'Unreviewed duplicate rollback identity exists'
    displaced = c.R / 'managed-drift-displaced'
    assert not displaced.exists(), 'Preserve earlier displaced bytes'
    c.atomic(result, {'schema': 1, 'state': 'recovery_started', 'review': record['review'], 'database_restored': False})
    moves = []
    for path in sorted(controlled):
        if path.exists():
            target = displaced / path.parent.name / path.name
            target.parent.mkdir(parents=True, exist_ok=True)
            assert not target.exists()
            os.replace(path, target)
            moves.append({'from': str(path), 'to': str(target)})
    for row in record['packs']:
        relative = Path(row['side'] + '_packs') / row['uuid']
        assert not (c.W / relative).exists()
        os.replace(root / relative, c.W / relative)
    for side, refs in record['refs'].items():
        c.atomic(c.W / ('world_' + side + '_packs.json'), refs)
    shutil.copy2(root / 'senluo-policy.json', c.Q / 'senluo-policy.json')
    verify_restored(original)
    c.atomic(result, {'schema': 1, 'state': 'restored_trusted_packs', 'review': record['review'],
        'trusted_inventory_sha256': record['trusted_inventory_sha256'], 'displaced': moves,
        'retired_preserved': [[str(a), str(b)] for a, b in retired],
        'database_restored': False, 'original_drift_approved': False,
        'client': False, 'production_ready': False})
