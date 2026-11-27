"""Use independently reviewed sources for a same-UUID saved-world update."""
from pathlib import Path

from family_update import common as c
from family_update.current_author_validation import committed
from family_update.source_batch import generated_pack, pack_tree

KEY = 'live_selected_repair'


def review():
    from family_update.repository_identity import target
    private = c.EXTENSION
    assert private is not None, 'Selected repair requires the canonical private review'
    identity = target('casama233/senluo-family-integration-private')
    checkout = c.read(private / '.repo-target.json')
    assert all(checkout[key] == value for key, value in identity.items()), 'Selected repair review repository differs'
    assert c.git(private, 'remote', 'get-url', 'origin').removesuffix('.git') == 'https://github.com/' + identity['repository']
    path = Path(c.CONFIG[KEY])
    assert path.is_absolute() and path.resolve() == path
    relative = path.relative_to(private)
    assert relative.parts[0] == 'maintenance', 'Selected repair review must be committed private maintenance data'
    document = committed(relative.as_posix())
    assert document['schema'] == 1 and document['kind'] == KEY
    assert document['site'] == {'server': c.SERVER, 'bds_root': str(c.B), 'world_dir': str(c.W)}, 'Selected repair site differs'
    for key in ('fresh_world', 'managed_drift_recovery', 'preinstall_recovery_output',
                'identity_migration', 'preserved_additions', 'approved_runtime_retention',
                'container_recovery_plan', 'native_actor_recovery_plan', 'native_storage_reanchor_plan',
                'curated_owner_inputs', 'extension_hud_validation', 'extension_stable_validation'):
        assert not c.CONFIG.get(key), 'Selected repair cannot be combined with ' + key
    return document, c.report_ref(path)


def source(uid, row, side):
    evidence = row['evidence']
    relative = Path(evidence['path'])
    assert not relative.is_absolute() and '..' not in relative.parts and relative.parts[0] == 'maintenance'
    proof = committed(relative.as_posix(), evidence['sha256'])
    assert proof['schema'] == 1 and proof['kind'] == 'selected_pack_source'
    assert proof['origin'] in ('author_archive', 'owned_release')
    assert isinstance(proof['source'], str) and proof['source'].strip(), 'Selected pack requires original source evidence'
    original = Path(proof['original']['path'])
    protected = [c.B, c.W, c.Q, c.R, *c.SOURCES.values(), c.EXTENSION]
    assert original.is_absolute() and original.resolve() == original
    assert not any(original.is_relative_to(path) for path in (c.B, c.W, c.Q, c.R)), 'Original source cannot be an active or candidate file'
    assert c.report_ref(original) == proof['original'], 'Original source evidence changed'
    assert proof['packs'][uid] == {'side': side, 'version': row['version'], 'tree': row['tree']}, 'Source evidence does not identify the reviewed payload'
    root = Path(row['artifact'])
    assert root.is_absolute() and root.resolve() == root
    assert not any(root.is_relative_to(path) or path.is_relative_to(root) for path in protected), 'Source artifact overlaps active data'
    label = 'BP' if side == 'behavior' else 'RP'
    actual_uid, manifest, files = generated_pack(proof['source'], label, root)
    assert actual_uid == uid and manifest['version'] == row['version'] and pack_tree(files) == row['tree'], 'Source artifact differs: ' + uid
    types = {module['type'] for module in manifest['modules']}
    assert types and (types == {'resources'} if side == 'resource' else 'resources' not in types), 'Source pack side differs: ' + uid
    return root, files, {'owner': 'preserved', 'role': 'reviewed_live_selected_input', 'source_evidence': evidence}


def inputs(original, policy):
    document, binding = review()
    path = Path(policy['approved_receipt'])
    assert c.sha(path) == document['approved_receipt_sha256'], 'Historical receipt differs from the review'
    approved_rows = c.read(path)['packs']
    approved = {row['uuid']: row for row in approved_rows}
    assert len(approved) == len(approved_rows), 'Historical receipt contains duplicate identities'
    current = {row['uuid']: row for row in original['packs']}
    assert len(current) == len(original['packs']), 'Selected identities are ambiguous'
    assert original['refs'] == document['refs'], 'Selected references or order changed'
    refs = [(ref['pack_id'], side, ref['version'])
            for side, entries in original['refs'].items() for ref in entries]
    assert len(refs) == len(current) and len({uid for uid, _, _ in refs}) == len(refs)
    assert all(uid in current and (side, version) == (current[uid]['side'], current[uid]['version'])
               for uid, side, version in refs), 'Selected inventory and references differ'
    assert set(approved) - set(current) == set(document['removed']), 'Selected removals differ from review'
    differences = {uid for uid, row in current.items()
                   if uid not in approved or any(row[key] != approved[uid][key] for key in ('side', 'version', 'files'))}
    assert differences == set(document['observed_sources']), 'Selected source changes differ from review'
    updates = document['replacements']
    assert updates and set(updates) <= set(current), 'Replacement must keep existing UUIDs'
    for item in updates.values():
        pair = [uid for uid, replacement in updates.items() if replacement['evidence'] == item['evidence']
                and replacement['version'] == item['version']]
        assert len(pair) == 2 and {current[uid]['side'] for uid in pair} == {'behavior', 'resource'}, 'Replacement release must be a reviewed pair'
    roots, descriptors, expected = [], {}, {}
    for uid, row in current.items():
        side = row['side']
        assert uid not in approved or approved[uid]['side'] == side, 'Selected pack side changed: ' + uid
        installed = Path(row['path'])
        assert installed.parent == c.W / (side + '_packs'), 'Selected repair needs a world-local pack: ' + uid
        manifest = c.read(installed / 'manifest.json')
        assert manifest['header']['uuid'] == uid and manifest['header']['version'] == row['version'], 'Selected manifest differs from the world reference: ' + uid
        descriptor = {'owner': 'preserved', 'role': 'unchanged_reviewed_live_input', 'approved_source': approved.get(uid, {}).get('source')}
        if uid in differences:
            _, files, descriptor = source(uid, document['observed_sources'][uid], side)
            assert files == row['files'], 'Reproduced source differs from installed pack: ' + uid
        if uid in updates:
            replacement = updates[uid]
            root, files, descriptor = source(uid, replacement, side)
            assert replacement['version'] > row['version'] and files != row['files'], 'Selected repair needs a fresh release: ' + uid
            row = {**row, 'version': replacement['version'], 'files': files}
        else:
            root = installed
        roots.append(root)
        descriptors[uid] = descriptor
        expected[uid] = {key: row[key] for key in ('side', 'version', 'files')}
    return roots, descriptors, expected, binding


def verify_candidate(receipt, original, policy):
    _, descriptors, expected, _ = inputs(original, policy)
    actual = {row['uuid']: {key: row[key] for key in ('side', 'version', 'files')} for row in receipt['packs']}
    assert len(actual) == len(receipt['packs']) and actual == expected, 'Candidate differs from exact selected repair'
    assert {row['uuid']: row['source'] for row in receipt['packs']} == descriptors, 'Candidate source evidence differs'
    assert receipt['order'] == {side: [ref['pack_id'] for ref in refs] for side, refs in original['refs'].items()}, 'Candidate changed selection order'
