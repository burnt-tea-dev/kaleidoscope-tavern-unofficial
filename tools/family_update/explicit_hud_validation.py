"""Admit only the P35 UI host, conserving the installed P34 gameplay/assets."""
import copy
import hashlib
import json
from pathlib import Path
from family_update import common as c

PRIVATE = 'local/senluo-amw-cuisine'
REPOSITORY = 'casama233/senluo-family-integration-private'
PREVIOUS = 'be7cf5287be8d6982052e409de6f9efc28d5cc0c'
VERSION = [1, 0, 35]
PROVIDERS = {'c2990d50-2cf7-59f7-886a-0f2d0240d156', 'bbbd2d60-52e5-53a6-8b9a-c09b0f516389',
             'a610b357-ba70-5a2f-bca5-5a7a8a0fb2a8', '994f73a2-05ec-41ce-876c-d388a526d9f5',
             '9071b6bc-915d-4d26-8486-05bb8db48762'}


def conserved_scope(old, new, old_manifest, new_manifest, side, own_uuids):
    before, after = dict(old), dict(new)
    additions = {'ui/hud_screen.json', 'ui/_global_variables.json'} if side == 'RP' else set()
    assert set(after) - set(before) == additions and not set(before) - set(after), 'Unexpected private runtime addition/removal'
    for name in additions:
        after.pop(name)
    assert all(before[name] == after[name] for name in before if name != 'manifest.json'), 'Private gameplay/storage/assets changed'
    projected = copy.deepcopy(new_manifest)
    assert projected['header']['version'] == VERSION
    projected['header']['version'] = [1, 0, 34]
    projected['header']['name'] = projected['header']['name'].replace('1.0.35', '1.0.34')
    for module in projected['modules']:
        assert module['version'] == VERSION
        module['version'] = [1, 0, 34]
    if side == 'RP':
        companions = [row for row in projected['dependencies'] if row.get('uuid') in PROVIDERS]
        assert len(companions) == len(PROVIDERS) and {row['uuid'] for row in companions} == PROVIDERS
        projected['dependencies'] = [row for row in projected['dependencies'] if row.get('uuid') not in PROVIDERS]
    for dependency in projected['dependencies']:
        if dependency.get('uuid') in own_uuids:
            assert dependency['version'] == VERSION
            dependency['version'] = [1, 0, 34]
    assert projected == old_manifest, 'Private manifest changes beyond identity/HUD dependencies'


def verify_static(receipt, prior):
    from family_update.extension_validation import source_binding
    from family_update.cookery_cache_validation import private_ci_records
    from family_update.workflow import gh_json
    path = Path(c.CONFIG['extension_hud_validation'])
    proof = c.read(path)
    baseline = c.read(c.EXTENSION / 'baseline.json')
    assert baseline['repository'] == PRIVATE and baseline['version'] == VERSION
    assert proof['kind'] == 'explicit_family_hud' and proof['canonical_repository'] == REPOSITORY and proof['canonical_repository_id'] == 1406868911
    binding = source_binding(proof, baseline)
    assert proof['git_tree'] == binding['current_source_tree_oid']
    assert proof['test_exit_code'] == 0 and proof['test_command'] == ['python', 'tools/test_family_hud_host.py']
    assert proof['native_controls'] == 29 and proof['literal_owned_roots'] == 2
    assert proof['native_and_amw_conserved'] and proof['dependency_bound']
    assert all(proof[key] is False for key in ['native_loading', 'client', 'simulated_players', 'production_ready'])
    log = path.parent / proof['test_log']['name']
    assert log.parent.resolve() == path.parent.resolve() and c.sha(log) == proof['test_log']['sha256']
    pr = gh_json(f'repos/{REPOSITORY}/pulls/{c.CONFIG["extension_hud_pull_request"]}')
    assert pr['merged_at'] and pr['state'] == 'closed' and pr['base']['ref'] == 'main'
    assert c.git(c.EXTENSION, 'rev-parse', pr['head']['sha'] + '^{tree}') == binding['current_source_tree_oid']
    checks, statuses, unavailable = private_ci_records(gh_json, pr['head']['sha'])
    assert proof['previous_commit'] == PREVIOUS
    old_baseline = json.loads(c.git(c.EXTENSION, 'show', PREVIOUS + ':baseline.json'))
    assert old_baseline['version'] == [1, 0, 34]
    owned = [row for row in receipt['packs'] if row['source'].get('repository') == PRIVATE]
    assert len(owned) == 2 and receipt['order']['resource'][0] == baseline['packs']['RP']['uuid'], 'Explicit HUD must be the selected first resource host'
    own_uuids = {row['uuid'] for row in owned}
    for row in owned:
        side = 'BP' if row['side'] == 'behavior' else 'RP'
        old = prior[row['uuid']]
        assert old['version'] == [1, 0, 34] and row['version'] == VERSION
        hashes = proof['previous_files'][side]
        assert {'sha256': hashlib.sha256(json.dumps(hashes, sort_keys=True, separators=(',', ':')).encode()).hexdigest(), 'files': len(hashes)} == old_baseline['source_trees'][side], 'P34 preimage is not the frozen canonical source'
        assert old['files'] == {name: digest for name, digest in proof['previous_files'][side].items()}, 'Installed private source differs from reviewed P34'
        assert row['files'] == proof['files'][side]
        relative = baseline['runtime'][side] + '/manifest.json'
        old_manifest = json.loads(c.git(c.EXTENSION, 'show', PREVIOUS + ':' + relative))
        new_manifest = c.read(c.EXTENSION / relative)
        conserved_scope(old['files'], row['files'], old_manifest, new_manifest, side, own_uuids)
        if side == 'RP':
            for dependency in new_manifest['dependencies']:
                if dependency.get('uuid') in PROVIDERS:
                    provider = next(p for p in receipt['packs'] if p['uuid'] == dependency['uuid'])
                    assert provider['side'] == 'resource' and provider['version'] == dependency['version']
    target = c.R / 'explicit-hud-static-validation.json'
    c.atomic(target, {'schema': 1, **binding, 'candidate_receipt_sha256': c.sha(c.C / 'family-receipt.json'),
                      'version': VERSION, 'source': c.report_ref(path), 'checks': checks, 'statuses': statuses,
                      'unavailable_paid_service': unavailable, 'exact_private_scope': True, 'client': False, 'production_ready': False})
    return [c.report_ref(path), c.report_ref(log), c.report_ref(target)]


def bind_native(receipt, evidence):
    if not c.CONFIG.get('extension_hud_validation'):
        return
    static = c.read(c.R / 'explicit-hud-static-validation.json')
    assert static['candidate_receipt_sha256'] == evidence['candidate_receipt_sha256'] == c.sha(c.C / 'family-receipt.json')
    assert evidence['fresh_stopped_backup'] and evidence['exact_files_checked'] and evidence['bds'] and evidence['saved_world_migration']
    assert not evidence['client'] and not evidence['simulated_players']
    assert [row['phase'] for row in evidence['runs']] == ['first', 'restart']
    assert all(row['ok'] and not row['errors'] for row in evidence['runs'])
    c.atomic(c.R / 'explicit-hud-native-validation.json', {'schema': 1, 'static': c.report_ref(c.R / 'explicit-hud-static-validation.json'),
             'fresh_native': c.report_ref(c.R / 'saved-world-report.json'), 'candidate_receipt_sha256': evidence['candidate_receipt_sha256'],
             'native_loading': True, 'saved_world_migration': True, 'client': False, 'production_ready': False})
