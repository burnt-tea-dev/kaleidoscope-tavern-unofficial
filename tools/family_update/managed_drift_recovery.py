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

from bridge_project import unique_object
from family_bundle import read_definition
from family_update import common as c
from family_update.repository_identity import target as repository_target

PROFILE = 'reviewed-managed-drift-repair-v1'
LOCAL_INPUT_PROFILE = 'reviewed-same-uuid-local-input-repair-v1'
LOCAL_INPUT_UUIDS = {
    'behavior': '5e121bf2-1d2d-4da4-be15-cffc5f216d94',
    'resource': 'e1168f1a-83d6-4abc-8f4b-ecb86e0a91dd',
}
LOCAL_RUNTIME = 'companion-sources/fishing-current-local/runtimeowner'
LOCAL_RECIPE = 'companion-sources/fishing-current-local/recipe.json'
LOCAL_ADDITION_UUIDS = {'behavior': 'd8a147c2-5b9e-4c11-9a32-7e418f20b101', 'resource': 'd8a147c2-5b9e-4c11-9a32-7e418f20b201'}
LOCAL_ADDITION_FOREIGN = {
    'items/novelty.json': 'nvy:novelty',
    'items/novelty_ui_placeholder.json': 'nvy:novelty_ui_placeholder',
    'entities/novelty_database.json': 'nvy:novelty_database',
    'entities/novelty_inventory.json': 'nvy:novelty_inventory',
    'entities/ui_queue_checker.json': 'uq:ui_queue_checker',
}
LOCAL_ADDITION_REPLACED = {'379931a2-7419-40fb-90fb-34288ab4e971', 'ea8da0de-83d7-4ae2-aa43-bbcd4192e0c7', '2d4fb75b-c854-460b-a2f5-b4639e11eaa6'}
LOCAL_ADDITION_RUNTIME = 'companion-sources/witchway-current-local/runtimeowner'
LOCAL_ADDITION_RECIPE = 'companion-sources/witchway-current-local/recipe.json'
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


def _identifiers(root):
    return [identifier for values in _definition_identifiers(root).values() for identifier in values]


def _definition_identifiers(root):
    definitions = {}
    for directory in ['blocks', 'items', 'entities', 'entity']:
        for definition in sorted((root / directory).rglob('*.json')):
            relative = definition.relative_to(root).as_posix()
            try:
                value = read_definition(definition, jsonc=True, object_pairs_hook=unique_object)
            except ValueError as error:
                raise AssertionError('Malformed pack definition ' + relative + ': ' + str(error)) from error
            assert isinstance(value, dict), 'Pack definition must be an object: ' + relative
            owners = [name for name in ['minecraft:block', 'minecraft:item', 'minecraft:entity', 'minecraft:client_entity'] if name in value]
            if not owners:
                continue
            assert len(owners) == 1, 'Ambiguous registered definition owners: ' + relative
            body = value[owners[0]]
            assert isinstance(body, dict) and isinstance(body.get('description'), dict), 'Malformed registered definition description: ' + relative
            identifier = body['description'].get('identifier')
            assert isinstance(identifier, str) and re.fullmatch(r'[a-z0-9_.-]+:[a-z0-9_./-]+', identifier), 'Malformed registered definition identifier: ' + relative
            definitions[relative] = [identifier]
    return definitions


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
    expected = repository_target('casama233/senluo-family-integration-private')
    assert all(target.get(key) == expected[key] for key in ['repository', 'repository_id', 'private', 'owner']), 'Drift review repository identity differs'
    assert target['private'] is True and type(target['repository_id']) is int, 'Drift review repository type differs'
    assert c.git(source, 'remote', 'get-url', 'origin').removesuffix('.git') == 'https://github.com/' + target['repository'], 'Drift review remote differs'
    assert c.git(source, 'branch', '--show-current') == 'main' and not c.git(source, 'status', '--porcelain'), 'Drift review requires clean canonical main'
    head = c.git(source, 'rev-parse', 'HEAD')
    assert c.git(source, 'ls-remote', 'origin', 'refs/heads/main').split()[0] == head, 'Drift review is not canonical remote main'
    binding = _committed(path)
    review = c.read(path)
    assert review['schema'] == 1 and review['kind'] == 'managed_drift_recovery' and review['profile'] in (PROFILE, LOCAL_INPUT_PROFILE)
    safety = {
        'installer_authorization_proven': False,
        'repair_only': True, 'keep_newest_database': True,
        'after_identity_adoption': 'retain_stopped_and_active_lease',
        'preserve_displaced_bytes': True}
    if review['profile'] == LOCAL_INPUT_PROFILE:
        safety.update(historical_origin_status='unknown', all_current_input_bytes_identified=True, full_gameplay_parity_verified=False)
        safety['after_candidate_start'] = 'retain_stopped_with_candidate_and_newest_database'
        assert review['safety']['all_current_input_bytes_identified'] is True and review['safety']['full_gameplay_parity_verified'] is False
        assert 'local_existing_input' in review and 'preserved_existing_inputs' not in review, 'Same-UUID local input needs its own exact review'
    else:
        safety['unknown_leaf_count'] = 0
        assert 'local_existing_input' not in review and 'retained_local_additions' not in review, 'Local-origin uncertainty cannot use the author-provenance profile'
    assert review['safety'] == safety, 'Drift repair safety boundary differs'
    assert len(review['proofs']) == 3 and len({row['path'] for row in review['proofs']}) == 3, 'Three distinct provenance proofs are required'
    for proof in review['proofs']:
        relative = Path(proof['path'])
        assert not relative.is_absolute() and '..' not in relative.parts
        assert _committed(source / relative)['sha256'] == proof['sha256'], 'Committed provenance proof differs'
    if review['observed'].get('added_uuids') and 'preserved_existing_inputs' not in review and 'retained_local_additions' not in review:
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
    if review['profile'] == LOCAL_INPUT_PROFILE:
        _local_existing_input(inventory, approved, review)
    if added:
        _review_additions(inventory, approved, review, policy)
    return review, binding


def _local_existing_input(inventory, approved, review):
    """Review the known current pair without inventing its historical author.

    Every leaf has an exact input identity. Historical attribution remains
    unknown even when those current bytes are reviewed for a forward repair.
    This mode cannot admit an added UUID, foreign namespace or another pair.
    """
    proof = review['local_existing_input']
    assert proof['schema'] == 1 and proof['kind'] == 'same_uuid_unattributed_paired_input'
    assert proof['historical_origin_status'] == 'unknown' and proof['original_archive_verified'] is False and proof['latest_stable_verified'] is False
    assert proof['input_review_scope'] == 'exact_local_bytes_and_listed_repairs_only' and proof['full_gameplay_parity_verified'] is False
    assert isinstance(proof['audited_input_paths'], list) and proof['audited_input_paths'] == sorted(set(proof['audited_input_paths']))
    assert {'scripts/blocks/tanks.js', 'scripts/blocks/keep.js'} <= set(proof['audited_input_paths']), 'Specific tank safety review is required'
    assert proof['action'] in ('retain_exact_bytes', 'repair_forward') and proof['installation_location'] == 'world'
    assert proof['definition_namespace'] == 'kaleidoscope_fishing'
    ids = set(LOCAL_INPUT_UUIDS.values())
    assert set(proof['packs']) == ids and ids <= set(review['observed']['changed_uuids']), 'Local input must be the exact changed Fishing pair'
    assert set(proof['audited_input_paths']) <= set(proof['packs'][LOCAL_INPUT_UUIDS['behavior']]['files']), 'Audited tank input paths are absent'
    assert not ids & set(review['observed'].get('added_uuids', [])), 'Same-UUID input is not an addition'
    old = {row['uuid']: row for row in approved['packs']}
    actual = {row['uuid']: row for row in inventory['packs']}
    assert ids <= set(old) & set(actual), 'Same-UUID input must already belong to the approved stack'
    assert set(proof['target_packs']) == ids, 'Complete local target pair is required'
    module_ids = set()
    for side, uid in LOCAL_INPUT_UUIDS.items():
        row, pin = actual[uid], proof['packs'][uid]
        assert row['side'] == pin['side'] == old[uid]['side'] == side
        assert pin['approved_version'] == old[uid]['version'] and pin['version'] == row['version'], 'Local input version differs'
        assert row['files'] == pin['files'] and files_sha256(row['files']) == pin['files_sha256'], 'Local input full byte map differs'
        path = Path(row['path'])
        assert path.is_absolute() and path.resolve() == path and str(path) == pin['original_path'], 'Local input original path differs'
        assert path.parent in {c.B / (side + '_packs'), c.W / (side + '_packs')}, 'Local input is outside reviewed pack catalogs'
        if not path.exists():
            assert path.parent == c.B / (side + '_packs'), 'Missing world input is not a global displacement'
            path = _displaced_existing_source(row, path)
        assert _files(path) == set(row['files']), 'Local input contains unsafe or unreviewed leaves'
        assert c.sha(path / 'manifest.json') == row['files']['manifest.json'], 'Local input manifest changed'
        manifest = c.read(path / 'manifest.json')
        assert manifest['header']['uuid'] == uid and manifest['header']['version'] == row['version']
        assert manifest['modules'] == pin['modules'] and manifest.get('dependencies', []) == pin['dependencies'], 'Local input modules or dependencies differ'
        assert manifest['modules'] and all(module['version'] == row['version'] for module in manifest['modules'])
        for module in manifest['modules']:
            assert module['uuid'] not in module_ids, 'Local pair duplicates a module identity'
            module_ids.add(module['uuid'])
        module_side = 'resource' if all(module['type'] == 'resources' for module in manifest['modules']) else 'behavior'
        assert module_side == side, 'Local input module side differs'
        identifiers = _identifiers(path)
        assert all(identifier.startswith(proof['definition_namespace'] + ':') for identifier in identifiers), 'Local input masks a managed or foreign definition'
        assert identifiers or side == 'resource', 'Local behavior input has no reviewed definitions'
    _local_pair_target_contract(proof, actual, LOCAL_INPUT_UUIDS)
    _local_runtime_contract(proof, LOCAL_RUNTIME, LOCAL_RECIPE)
    return proof


def _local_runtime_contract(proof, runtime_path, recipe_path):
    runtime = proof.get('canonical_runtime')
    if proof['action'] == 'repair_forward':
        assert isinstance(runtime, dict) and set(runtime) == {'path', 'tree', 'recipe_path', 'recipe_sha256'}
        root = Path(runtime['path'])
        assert root.as_posix() == runtime_path, 'Local runtime owner path differs'
        assert c.git(c.EXTENSION, 'rev-parse', 'HEAD:' + root.as_posix()) == runtime['tree'], 'Local repair runtime owner changed'
        recipe = Path(runtime['recipe_path'])
        assert recipe.as_posix() == recipe_path, 'Local repair recipe path differs'
        raw = subprocess.check_output(['git', '-C', str(c.EXTENSION), 'show', 'HEAD:' + recipe.as_posix()])
        assert (c.EXTENSION / recipe).read_bytes() == raw and hashlib.sha256(raw).hexdigest() == runtime['recipe_sha256'], 'Local repair recipe differs from canonical source'
    else:
        assert runtime is None, 'Retained input cannot claim a new runtime producer'


def _local_components(review):
    yield 'fishing', review['local_existing_input'], LOCAL_INPUT_UUIDS, LOCAL_RUNTIME, LOCAL_RECIPE, 'canonical_local_fishing_repair'
    if 'retained_local_additions' in review:
        yield 'witchway', review['retained_local_additions'], LOCAL_ADDITION_UUIDS, LOCAL_ADDITION_RUNTIME, LOCAL_ADDITION_RECIPE, 'canonical_local_witchway_repair'


def local_input_sources(original):
    """Descriptors for assembly, before its immutable receipt is written."""
    review, binding = check_observed(original, c.read(c.R / 'production-before/senluo-policy.json'))
    if review['profile'] != LOCAL_INPUT_PROFILE:
        return {}
    result = {}
    for _, proof, identities, *_ in _local_components(review):
        for uid in identities.values():
            source = {'owner': 'preserved', 'role': 'existing_unattributed_input' if proof['action'] == 'retain_exact_bytes' else 'canonical_local_repair',
                      'origin_status': 'unverified_existing_input', 'original_archive_verified': False,
                      'latest_stable_verified': False, 'action': proof['action'], 'local_input_review': binding,
                      'historical_origin_status': 'unknown', 'full_gameplay_parity_verified': False,
                      'input_files_sha256': proof['packs'][uid]['files_sha256']}
            if proof['action'] == 'repair_forward':
                source['canonical_runtime'] = {**proof['canonical_runtime'], 'repository': repository_target('casama233/senluo-family-integration-private')['repository'],
                                               'repository_id': 1406868911, 'commit': c.git(c.EXTENSION, 'rev-parse', 'HEAD')}
            result[uid] = source
    return result


def _local_target_pins(review):
    result = dict(review['local_existing_input']['target_packs'])
    if 'retained_local_additions' in review:
        result.update(review['retained_local_additions']['target_packs'])
    return result


def verify_local_target(receipt, original):
    """Exact output gate shared by assembly and relocation selection."""
    review, _ = check_observed(original, c.read(c.R / 'production-before/senluo-policy.json'))
    if review['profile'] != LOCAL_INPUT_PROFILE:
        return set()
    proof = review['local_existing_input']
    sources = local_input_sources(original)
    rows = {row['uuid']: row for row in receipt['packs']}
    targets = _local_target_pins(review)
    for uid, target in targets.items():
        assert uid in rows and all(rows[uid][key] == target[key] for key in ['side', 'version', 'files']), 'Local target bytes or identity differ'
        assert rows[uid]['source'] == sources[uid], 'Local input origin or canonical repair proof differs'
    return set(targets)


def _canonical_local_payload(side, proof, component='fishing'):
    """Read a complete committed pack once; working bytes must match its blobs."""
    assert component in ('fishing', 'witchway'), 'Unreviewed local runtime component'
    runtime, identities = (LOCAL_RUNTIME, LOCAL_INPUT_UUIDS) if component == 'fishing' else (LOCAL_ADDITION_RUNTIME, LOCAL_ADDITION_UUIDS)
    relative = Path(runtime) / ('BP' if side == 'behavior' else 'RP')
    path = c.EXTENSION / relative
    assert path.is_dir() and not path.is_symlink() and path.resolve() == path, 'Local runtime pack path is not canonical'
    uid = identities[side]
    expected = proof['target_packs'][uid]
    raw = subprocess.check_output(['git', '-C', str(c.EXTENSION), 'ls-tree', '-rz', 'HEAD:' + relative.as_posix()])
    blobs = {}
    for entry in raw.split(b'\0'):
        if not entry:
            continue
        header, name = entry.split(b'\t', 1)
        mode, kind, oid = header.decode('ascii').split()
        name = name.decode('utf-8')
        assert mode in ('100644', '100755') and kind == 'blob' and name not in blobs, 'Local runtime contains a linked, duplicate or nonregular object'
        blobs[name] = oid
    assert set(blobs) == _files(path) == set(expected['files']), 'Complete canonical local runtime inventory differs'
    for name, oid in blobs.items():
        source = path / name
        descriptor = os.open(source, os.O_RDONLY | os.O_NOFOLLOW)
        with os.fdopen(descriptor, 'rb') as stream:
            before = os.fstat(stream.fileno()); content = stream.read(); after = os.fstat(stream.fileno())
        final = source.lstat()
        assert stat.S_ISREG(before.st_mode) and stat.S_ISREG(final.st_mode) and (final.st_dev, final.st_ino) == (before.st_dev, before.st_ino), 'Local runtime source was replaced or linked'
        assert (before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns, before.st_ctime_ns) == (after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns, after.st_ctime_ns), 'Local runtime changed during read'
        assert hashlib.sha256(content).hexdigest() == expected['files'][name], 'Local runtime differs from exact reviewed output'
        assert hashlib.sha1(b'blob ' + str(len(content)).encode() + b'\0' + content).hexdigest() == oid, 'Local runtime is not committed unchanged'
    manifest = c.read(path / 'manifest.json')
    assert manifest['header']['uuid'] == uid and manifest['header']['version'] == expected['version'], 'Local target manifest identity differs'
    assert manifest['modules'] and all(module['version'] == expected['version'] for module in manifest['modules']), 'Local target module versions differ'
    assert all(module['type'] == 'resources' for module in manifest['modules']) if side == 'resource' else any(module['type'] in ('data', 'script') for module in manifest['modules']), 'Local target module side differs'
    for dependency in manifest.get('dependencies', []):
        if dependency.get('uuid') in identities.values():
            assert dependency['version'] == expected['version'], 'Local target paired dependency differs'
    if component == 'fishing':
        assert all(identifier.startswith('kaleidoscope_fishing:') for identifier in _identifiers(path)), 'Local target masks a managed or foreign definition'
    else:
        _witch_definition_scope(path, side, proof['packs'][uid]['foreign_definitions'])
    return path, manifest


def select_local_inputs(roots, original):
    """Select only the exact retained input or complete canonical repaired pair.

    Paths are fixed inside verified private main. Configuration cannot supply
    an arbitrary output directory or a per-file gameplay substitution.
    """
    roots = [Path(root) for root in roots]
    if not c.CONFIG.get('managed_drift_recovery'):
        return roots, {}, None
    review, binding = check_observed(original, c.read(c.R / 'production-before/senluo-policy.json'))
    if review['profile'] != LOCAL_INPUT_PROFILE:
        return roots, {}, None
    proof = review['local_existing_input']
    identities = [c.read(root / 'manifest.json')['header']['uuid'] for root in roots]
    expected_sources = local_input_sources(original)
    assert len(identities) == len(set(identities)) and set(expected_sources) <= set(identities), 'Local pair selection is missing or ambiguous'
    actual = {row['uuid']: row for row in original['packs']}
    for root, uid in zip(roots, identities):
        if uid in expected_sources:
            assert root == Path(actual[uid]['path']), 'Another selector already replaced the local input'
    replacements = {}
    manifests = []
    for component, selected_proof, component_ids, _, recipe_path, recipe_kind in _local_components(review):
        if selected_proof['action'] == 'repair_forward':
            recipe = c.read(c.EXTENSION / recipe_path)
            assert recipe['schema'] == 1 and recipe['kind'] == recipe_kind
            assert recipe['historical_origin_status'] == 'unknown' and recipe['original_archive_verified'] is False and recipe['latest_stable_verified'] is False
            assert recipe['native_loading'] is False and recipe['saved_world_migration'] is False and recipe['client'] is False and recipe['production_ready'] is False, 'Source recipe cannot certify native/client admission'
            for side, uid in component_ids.items():
                label = 'BP' if side == 'behavior' else 'RP'
                assert recipe['input_hashes'][label] == selected_proof['packs'][uid]['files'], 'Local recipe input identity differs'
                assert recipe['output_hashes'][label] == selected_proof['target_packs'][uid]['files'], 'Local recipe output identity differs'
                assert recipe['version'] == selected_proof['target_packs'][uid]['version'], 'Local recipe release identity differs'
                replacements[uid], manifest = _canonical_local_payload(side, selected_proof, component)
                manifests.append(manifest)
    module_ids = [module['uuid'] for manifest in manifests for module in manifest['modules']]
    assert len(module_ids) == len(set(module_ids)), 'Local target duplicates module identities'
    selected = [replacements.get(uid, root) for root, uid in zip(roots, identities)]
    evidence = {'schema': 1, 'kind': 'exact_local_input_selection', 'review': binding,
                'historical_origin_status': 'unknown', 'full_gameplay_parity_verified': False,
                'action': proof['action'], 'input_files_sha256': {uid: row['files_sha256'] for uid, row in proof['packs'].items()},
                'output_files_sha256': {uid: files_sha256(row['files']) for uid, row in proof['target_packs'].items()},
                'canonical_runtime': proof.get('canonical_runtime'),
                'selected': {uid: str(replacements.get(uid, Path(actual[uid]['path']))) for uid in expected_sources},
                'native_loading': False, 'saved_world_migration': False, 'client': False, 'production_ready': False}
    if 'retained_local_additions' in review:
        added = review['retained_local_additions']
        evidence['retained_local_additions'] = {uid: {'files_sha256': pin['files_sha256'], 'target_files_sha256': files_sha256(added['target_packs'][uid]['files']),
                                                    'action': added['action'], 'canonical_runtime': added.get('canonical_runtime'), 'historical_origin_status': 'unknown', 'full_gameplay_parity_verified': False}
                                                for uid, pin in review['retained_local_additions']['packs'].items()}
    return selected, expected_sources, evidence


def _review_additions(inventory, approved, review, policy=None):
    """Reuse the original-archive gate; only reviewed missing rows are omitted."""
    from family_update.preserved_additions import review as review_additions
    if 'retained_local_additions' in review:
        assert review['profile'] == LOCAL_INPUT_PROFILE and 'preserved_existing_inputs' not in review and 'preserved_additions' not in review, 'Use one exact local addition admission mode'
        return _retained_local_additions(inventory, approved, review)
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


def _retained_local_additions(inventory, approved, review):
    """Review the exact current Witch pair and its five embedded provider IDs.

    This is no author/runtime approval. It cannot admit another UUID pair,
    another foreign definition, or re-enable the displaced old providers.
    """
    proof = review['retained_local_additions']
    assert proof['schema'] == 1 and proof['kind'] == 'exact_unattributed_existing_pair'
    assert proof['historical_origin_status'] == 'unknown' and proof['original_archive_verified'] is False and proof['latest_stable_verified'] is False
    assert proof['action'] in ('retain_exact_bytes', 'repair_forward') and proof['installation_location'] == 'world' and proof['definition_namespace'] == 'aww'
    assert proof['full_gameplay_parity_verified'] is False
    assert proof['input_review_scope'] == 'exact_local_bytes_and_listed_repairs_only'
    if proof['action'] == 'repair_forward':
        assert 'scripts/coven_and_reactions.js' in proof['audited_input_paths'], 'Specific native drop consumer review is required'
    ids = set(LOCAL_ADDITION_UUIDS.values())
    assert set(proof['packs']) == ids == set(review['observed'].get('added_uuids', [])), 'Local addition must be the exact current Witch pair'
    if proof['action'] == 'repair_forward':
        assert set(proof['audited_input_paths']) <= set(proof['packs'][LOCAL_ADDITION_UUIDS['behavior']]['files']), 'Audited local addition input paths are absent'
    assert LOCAL_ADDITION_REPLACED <= set(review['observed']['missing_uuids']), 'Embedded providers must replace their exact retired standalone identities'
    actual = {row['uuid']: row for row in inventory['packs']}
    assert not LOCAL_ADDITION_REPLACED & set(actual), 'Embedded and standalone providers cannot coexist'
    adjusted = {row['uuid']: row for row in approved['packs'] if row['uuid'] not in review['observed']['missing_uuids']}
    modules = set()
    for side, uid in LOCAL_ADDITION_UUIDS.items():
        row, pin = actual[uid], proof['packs'][uid]
        assert row['side'] == pin['side'] == side and row['version'] == pin['version']
        assert row['files'] == pin['files'] and files_sha256(row['files']) == pin['files_sha256'], 'Retained local addition byte map differs'
        path = Path(row['path'])
        assert path.is_absolute() and path.resolve() == path and str(path) == pin['original_path'] and path.parent == c.B / (side + '_packs'), 'Retained local addition original global path differs'
        if not path.exists():
            path = _displaced_existing_source(row, path)
        assert _files(path) == set(row['files']) and c.sha(path / 'manifest.json') == row['files']['manifest.json'], 'Retained local addition inventory or manifest differs'
        manifest = c.read(path / 'manifest.json')
        assert manifest['header']['uuid'] == uid and manifest['header']['version'] == row['version']
        assert manifest['modules'] == pin['modules'] and manifest.get('dependencies', []) == pin['dependencies'], 'Retained local addition modules or dependencies differ'
        assert manifest['modules'] and all(module['version'] == row['version'] for module in manifest['modules'])
        inferred = 'resource' if all(module['type'] == 'resources' for module in manifest['modules']) else 'behavior'
        assert inferred == side
        for module in manifest['modules']:
            assert module['uuid'] not in modules, 'Retained local addition duplicates a module identity'
            modules.add(module['uuid'])
        _witch_definition_scope(path, side, pin['foreign_definitions'])
        adjusted[uid] = {**row, 'source': {'owner': 'preserved', 'role': 'existing_unattributed_input',
            'origin_status': 'unverified_existing_input', 'historical_origin_status': 'unknown',
            'original_archive_verified': False, 'latest_stable_verified': False, 'action': 'retain_exact_bytes',
            'full_gameplay_parity_verified': False}}
    assert len({tuple(row['version']) for row in proof['packs'].values()}) == 1, 'Retained local addition must be a complete paired version'
    _local_pair_target_contract(proof, actual, LOCAL_ADDITION_UUIDS)
    _local_runtime_contract(proof, LOCAL_ADDITION_RUNTIME, LOCAL_ADDITION_RECIPE)
    return adjusted


def _witch_definition_scope(path, side, expected_foreign):
    definitions = _definition_identifiers(path)
    foreign = {name: values for name, values in definitions.items() if any(not identifier.startswith('aww:') for identifier in values)}
    assert foreign == expected_foreign, 'Retained local foreign definition scope differs'
    assert all(identifier.startswith('aww:') or identifier in LOCAL_ADDITION_FOREIGN.values() for values in definitions.values() for identifier in values), 'Retained local addition masks an unreviewed foreign definition'
    if side == 'behavior':
        assert foreign == {name: [identifier] for name, identifier in LOCAL_ADDITION_FOREIGN.items()}, 'Retained local embedded provider definitions differ'
        assert any(identifier.startswith('aww:') for values in definitions.values() for identifier in values), 'Retained local behavior input has no reviewed namespace'


def _local_pair_target_contract(proof, actual, identities):
    assert set(proof['target_packs']) == set(identities.values()), 'Complete local target pair is required'
    for side, uid in identities.items():
        row, target = actual[uid], proof['target_packs'][uid]
        assert set(target) == {'side', 'version', 'files'} and target['side'] == side
        assert isinstance(target['version'], list) and len(target['version']) == 3 and all(type(v) is int and v >= 0 for v in target['version'])
        assert isinstance(target['files'], dict) and target['files'] and 'manifest.json' in target['files']
        for name, digest in {**row['files'], **target['files']}.items():
            leaf = Path(name)
            assert not leaf.is_absolute() and '..' not in leaf.parts and leaf.as_posix() == name and '\\' not in name
            assert isinstance(digest, str) and re.fullmatch('[0-9a-f]{64}', digest), 'Local input/output hash is malformed'
        if proof['action'] == 'retain_exact_bytes':
            assert all(target[key] == row[key] for key in ['side', 'version', 'files']), 'Retain-only local input changed'
        else:
            assert tuple(target['version']) > tuple(row['version']), 'A forward runtime repair needs a fresh pair'
    assert len({tuple(row['version']) for row in proof['target_packs'].values()}) == 1, 'Local target must have a paired release identity'


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
        identifiers = _identifiers(path)
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
    if review['profile'] == LOCAL_INPUT_PROFILE:
        pins = {**review['local_existing_input']['packs'], **review.get('retained_local_additions', {}).get('packs', {})}
        return {uid: Path(row['original_path']) for uid, row in pins.items()
                if Path(row['original_path']).parent == c.B / (row['side'] + '_packs')}
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
    if review['profile'] == LOCAL_INPUT_PROFILE:
        proof = review['local_existing_input']
        result['managed_drift_local_input'] = hashlib.sha256(json.dumps(proof, sort_keys=True, separators=(',', ':')).encode()).hexdigest()
        if 'retained_local_additions' in review:
            result['managed_drift_retained_local_additions'] = hashlib.sha256(json.dumps(review['retained_local_additions'], sort_keys=True, separators=(',', ':')).encode()).hexdigest()
    if review['observed'].get('added_uuids') and 'preserved_existing_inputs' not in review and 'retained_local_additions' not in review:
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
    assert identities(receipt['packs']) == identities(target['packs']) and receipt['order'] == target.get('order', receipt['order']), 'Candidate identities or order differ from drift repair review'
    # The receipt is the candidate identity. Older reviews may carry the
    # duplicated source/upstream/swap pins; compare them only when present.
    if 'upstream_lock_sha256' in target:
        assert c.sha(c.T / 'family/upstream.lock.json') == target['upstream_lock_sha256'], 'Candidate author lock differs'
    if 'owned_source_trees' in target:
        paths = {**c.SOURCES, 'extension': c.EXTENSION}
        assert set(target['owned_source_trees']) == set(paths)
        for name, path in paths.items():
            assert c.read(path / 'baseline.json')['source_trees'] == target['owned_source_trees'][name], 'Reviewed candidate runtime source differs: ' + name
    from family_update.identity_migration import plan_swaps
    swaps = plan_swaps(migration) if migration else []
    if 'swaps' in target:
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
    if review['profile'] == LOCAL_INPUT_PROFILE:
        verify_local_target(receipt, original)
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
        if review['profile'] == LOCAL_INPUT_PROFILE and row['uuid'] in LOCAL_INPUT_UUIDS.values():
            source = {'owner': 'preserved', 'role': 'existing_unattributed_input',
                      'origin_status': 'unverified_existing_input', 'original_archive_verified': False,
                      'latest_stable_verified': False, 'action': 'observed_input_only',
                      'approved_reference_source': source}
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
    if review['profile'] == LOCAL_INPUT_PROFILE:
        sources = local_input_sources(original)
        pins = _local_target_pins(review)
        for row in synthetic_rows:
            if row['uuid'] in sources:
                row.update(pins[row['uuid']], source=sources[row['uuid']])
    synthetic = {'packs': synthetic_rows, 'order': target['order']}
    validate_target(synthetic, original, migration)
    return {side: list(target['order'][side]) for side in SIDES}


def validate_initial_status(summary):
    global _INITIAL_STATE
    review, binding = load_review()
    preinstall_recovery = None
    assert summary['status'] in ['RUNNING', 'STOPPED'], 'Server is not in a stable deployable state'
    if summary['status'] == 'STOPPED':
        assert review.get('allow_initially_stopped') is True, 'Stopped deployment needs its exact owner review'
        assert summary['name'] == c.SERVER and summary['player_count'] == 0, 'Stopped server must be the reviewed empty server'
        if c.CONFIG.get('preinstall_recovery_output'):
            from family_update.preinstall_recovery import verify_completed
            preinstall_recovery = verify_completed(Path(c.CONFIG['preinstall_recovery_output']), summary)
        else:
            assert c.sha(c.LEASE) == review['stopped_server_review']['lease_sha256'], 'Previous maintenance owner state changed'
        c.lease_available()
    _INITIAL_STATE = {'schema': 1, 'server': dict(summary), 'review': binding,
        'previous_lease': c.lease_available(), 'previous_lease_sha256': c.sha(c.LEASE),
        'restart_original_after_failure': summary['status'] == 'RUNNING'}
    if preinstall_recovery is not None:
        _INITIAL_STATE['preinstall_recovery'] = preinstall_recovery
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
