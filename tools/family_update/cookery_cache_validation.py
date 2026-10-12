"""Narrow private cache repair: source CI first, this update's saved load later.

This accepts no gameplay or storage changes. It reuses no earlier native result
for the new pack. The common saved-world rehearsal remains mandatory.
"""
import copy
import hashlib
import json
import re
from pathlib import Path
from family_update.common import CONFIG, R, C, EXTENSION, read, sha, git, report_ref, atomic

REPOSITORY = 'casama233/senluo-family-integration-private'
REPOSITORY_ID = 1406868911
LOGICAL = 'local/senluo-amw-cuisine'
PREVIOUS = '8d05a3da291861048dc7e759be3ba96fde45ebb8'
OLD_VERSION, NEW_VERSION = [1, 0, 32], [1, 0, 33]
SPEC = 'host-extensions/cookery-recipe-cache-repair.json'
ARCHIVE = 'da12fe6d39d7514aff1de3c963d69899324d771be5ca0fc3da1ccb759c7ad458'


def tree(rows):
    return {'sha256': hashlib.sha256(json.dumps(rows, sort_keys=True, separators=(',', ':')).encode()).hexdigest(), 'files': len(rows)}


def identity_projection(manifest, own_uuids):
    value = copy.deepcopy(manifest)
    assert value['header']['version'] == NEW_VERSION, 'Cache pack identity differs'
    value['header']['version'] = OLD_VERSION
    name = value['header']['name']
    assert name.count('1.0.33') == 1, 'Cache pack name identity differs'
    value['header']['name'] = name.replace('1.0.33', '1.0.32', 1)
    for module in value['modules']:
        assert module['version'] == NEW_VERSION
        module['version'] = OLD_VERSION
    for dependency in value.get('dependencies', []):
        if dependency.get('uuid') in own_uuids:
            assert dependency['version'] == NEW_VERSION
            dependency['version'] = OLD_VERSION
    return value


def conserved_packs(before, after, old_config, config, manifests):
    assert config['version'] == NEW_VERSION and old_config['version'] == OLD_VERSION
    assert config['repository'] == old_config['repository'] == LOGICAL
    assert config.get('retained_renderer_profile') == {'source_commit': PREVIOUS, 'spec_sha256': '292e337a073ea713c22c84c66f85a2c8cb9d2d5c453c308b1569107d2656b703'}, 'Unchanged renderer source retention missing'
    assert set(before) == set(after) == {p['uuid'] for p in config['packs'].values()}, 'Private cache pack set differs'
    uuids = set(after)
    for side in ['BP', 'RP']:
        uid = config['packs'][side]['uuid']
        previous, current = before[uid], after[uid]
        assert previous['version'] == OLD_VERSION and current['version'] == NEW_VERSION
        assert previous['side'] == current['side'] == ('behavior' if side == 'BP' else 'resource')
        assert tree(previous['files']) == old_config['source_trees'][side], 'Prior private source does not match approved P32'
        assert tree(current['files']) == config['source_trees'][side], 'Current private source does not match P33'
        old, new = dict(previous['files']), dict(current['files'])
        if side == 'BP':
            assert SPEC not in old and SPEC in new, 'Cache declaration must be the only new private file'
            new.pop(SPEC)
        assert set(old) == set(new), 'Unexpected cache-only private file addition/removal'
        assert all(old[name] == new[name] for name in old if name != 'manifest.json'), 'Unrelated private gameplay/storage/assets changed'
        old_manifest, new_manifest = manifests[side]
        assert identity_projection(new_manifest, uuids) == old_manifest, 'Private manifest changed beyond paired identity'


def verify_static(receipt, prior):
    from family_update.extension_validation import source_binding
    from family_update.workflow import gh_json, actual_ci_records
    path = Path(CONFIG['extension_cache_validation'])
    proof, config = read(path), read(EXTENSION / 'baseline.json')
    assert proof.get('kind') == 'cookery_recipe_cache', 'Unsupported private functional scope'
    original_binding = source_binding(proof, config)
    binding = {'actual_current_source_commit': original_binding['actual_current_source_commit'],
               'validated_source_commit': original_binding['native_source_commit'],
               'current_source_tree_oid': original_binding['current_source_tree_oid'],
               'validated_source_tree_oid': original_binding['native_source_tree_oid'],
               'identical_full_tree_reuse': original_binding['identical_full_tree_reuse']}
    assert git(EXTENSION, 'merge-base', PREVIOUS, binding['actual_current_source_commit']) == PREVIOUS
    old_config = json.loads(git(EXTENSION, 'show', PREVIOUS + ':baseline.json'))
    after = {p['uuid']: p for p in receipt['packs'] if p['source'].get('repository') == LOGICAL}
    before = {uid: prior[uid] for uid in after if uid in prior}
    manifests = {side: (json.loads(git(EXTENSION, 'show', PREVIOUS + ':' + relative + '/manifest.json')),
                        read(EXTENSION / relative / 'manifest.json')) for side, relative in config['runtime'].items()}
    conserved_packs(before, after, old_config, config, manifests)
    assert proof['packs'] == {uid: row['files'] for uid, row in after.items()}, 'Private functional pack bytes differ'
    spec_path = EXTENSION / config['runtime']['BP'] / SPEC
    spec = read(spec_path)
    assert spec['kind'] == 'cookery-recipe-cache-repair' and spec['archive_sha256'] == ARCHIVE
    target = 'scripts/api/extensionRegistry.js'
    assert set(spec['original_files']) == set(spec['patched_files']) == {target}
    assert not spec['imports'] and not spec['copies'] and not spec['json_updates']
    host = next(p for p in receipt['packs'] if p['uuid'] == spec['host_uuid'])
    assert host['side'] == 'behavior' and host['version'] == [1, 6, 0]
    assert host['files'][target] == spec['patched_files'][target], 'Candidate recipe cache postimage differs'
    assert any(row.get('id') == spec['id'] for row in host['source']['reviewed_extensions']), 'Cache repair provenance missing'
    metadata = read(EXTENSION / '.repo-target.json')
    assert metadata['repository'] == REPOSITORY and metadata['repository_id'] == REPOSITORY_ID and metadata['private'] is True
    repo = gh_json('repos/' + REPOSITORY)
    assert repo['id'] == REPOSITORY_ID and repo['full_name'] == REPOSITORY and repo['private'] is True
    pr = gh_json(f'repos/{REPOSITORY}/pulls/{proof["private_pull_request"]}')
    assert pr['merged'] is True and pr['base']['ref'] == 'main'
    assert pr['head']['repo']['id'] == pr['base']['repo']['id'] == REPOSITORY_ID
    assert git(EXTENSION, 'merge-base', pr['merge_commit_sha'], binding['actual_current_source_commit']) == pr['merge_commit_sha']
    current_tree = binding['current_source_tree_oid']
    checked = pr['head']['sha']
    assert gh_json(f'repos/{REPOSITORY}/git/commits/{checked}')['tree']['sha'] == current_tree, 'Private reviewed full Git tree differs'
    checks, statuses = actual_ci_records(REPOSITORY, checked)
    assert any(c['name'] == 'baseline' and c['app_slug'] == 'github-actions' and c['conclusion'] == 'success' for c in checks), 'Private canonical functional CI missing'
    ref = proof['differential']
    assert sha(ref['path']) == ref['sha256'], 'Private recipe differential evidence changed'
    report = read(Path(ref['path']))
    assert report['schema'] == 1 and report['kind'] == 'cookery_recipe_cache'
    assert report['git_tree'] == current_tree and report['version'] == NEW_VERSION and report['source_trees'] == config['source_trees']
    assert isinstance(report['source_commit'],str) and re.fullmatch(r'[a-f0-9]{40}',report['source_commit'])
    assert gh_json(f'repos/{REPOSITORY}/git/commits/{report["source_commit"]}')['tree']['sha'] == current_tree, 'Actual differential checkout differs'
    assert report['cache_spec_sha256'] == sha(spec_path) and report['fixture_provenance']['official_archive_sha256'] == ARCHIVE
    assert report['original_registry_sha256'] == spec['original_files'][target] == report['fixture_provenance']['modules'][target]
    assert report['repaired_registry_sha256'] == spec['patched_files'][target]
    assert report['client'] is False and report['simulated_players'] is False and report['native_loading'] is False
    assert report['registration_kind_count'] == 11 and report['ready_batches'] == 6
    assert report['original_rebuilds'] == 75 and report['repaired_rebuilds'] == 7
    assert all(report.get(key) is True for key in ['ordered_views_equal', 'registration_acks_equal', 'dynamic_overwrite_equal', 'all_five_getters_fresh', 'all_author_v1_kinds', 'invalid_registrations_equal', 'unrelated_station_does_not_rebuild_pots'])
    log = Path(ref['path']).parent / report['test_log']['name']
    assert log.parent.resolve() == Path(ref['path']).parent.resolve() and sha(log) == report['test_log']['sha256'] and report['test_exit_code'] == 0
    result = {'schema': 1, 'scope': 'Pure original recipe registry differential and unchanged private gameplay; fresh current-candidate BDS/save is separately mandatory',
              'source': report_ref(path), 'differential': ref, **binding, 'private_pull_request': proof['private_pull_request'],
              'private_checks': checks, 'private_statuses': statuses, 'candidate_receipt_sha256': sha(C / 'family-receipt.json'),
              'packs': proof['packs'], 'spec_sha256': sha(spec_path), 'static_functional': True,
              'native_loading': False, 'saved_world_migration': False, 'client': False, 'production_ready': False}
    atomic(R / 'cookery-cache-static-validation.json', result)
    return [report_ref(path), ref, report_ref(R / 'cookery-cache-static-validation.json')]


def bind_native(receipt, evidence):
    """Called only after the normal fresh-native report has been validated."""
    if not CONFIG.get('extension_cache_validation'):
        return
    static = read(R / 'cookery-cache-static-validation.json')
    assert static['candidate_receipt_sha256'] == sha(C / 'family-receipt.json') == evidence['candidate_receipt_sha256']
    assert static['packs'] == {p['uuid']: p['files'] for p in receipt['packs'] if p['source'].get('repository') == LOGICAL}
    assert evidence['fresh_stopped_backup'] and evidence['exact_files_checked'] and evidence['bds'] and evidence['saved_world_migration']
    assert evidence['client'] is False and evidence['simulated_players'] is False
    assert [r['phase'] for r in evidence['runs']] == ['first', 'restart'] and all(r['ok'] and not r['errors'] for r in evidence['runs'])
    atomic(R / 'cookery-cache-native-validation.json', {'schema': 1, 'static': report_ref(R / 'cookery-cache-static-validation.json'),
           'fresh_native': report_ref(R / 'saved-world-report.json'), 'candidate_receipt_sha256': evidence['candidate_receipt_sha256'],
           'scope': 'Current exact P33 candidate loaded and restarted on this stopped save; cache semantics are source-CI evidence, not an engine performance benchmark',
           'native_loading': True, 'saved_world_migration': True, 'client': False, 'production_ready': False})
