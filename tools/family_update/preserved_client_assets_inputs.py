"""Admit the fixed reviewed integration AMW/Fishing client repair from original private source CI.

This is a source gate before the single fresh stopped-save first/restart gate.
It cannot reconcile installed drift or admit unrelated preserved-pack edits.
Only reviewed contract metadata and hashes belong in this public module.
"""
import copy
from functools import lru_cache
import hashlib
import io
import json
from pathlib import Path, PurePosixPath
import re
import zipfile

from family_update import common as c
from family_update.repository_identity import current_name, verify_record, verify_remote

PROFILE = 'senluo-client-assets-20261019-p58'
RECIPE = 'companion-sources/client-assets-20261019/recipe.json'
VERSION = [1, 0, 58]
PRIVATE = 'local/senluo-amw-cuisine'
REPOSITORY = 'casama233/senluo-family-integration-private'
REPOSITORY_ID = 1406868911
APPROVED = '3dd505f20b80486620637c307e54a25ef89c06fd034d088af7a7469b0a188a1f'
PACKS = {
    'AMW_BP': ('cd107d2a-333f-4347-ab54-6917142be0d7', 'behavior', [2, 6, 29], [2, 6, 10058]),
    'AMW_RP': ('994f73a2-05ec-41ce-876c-d388a526d9f5', 'resource', [2, 6, 29], [2, 6, 10058]),
    'Fishing_BP': ('5e121bf2-1d2d-4da4-be15-cffc5f216d94', 'behavior', [1, 2, 0], [1, 2, 10058]),
    'Fishing_RP': ('e1168f1a-83d6-4abc-8f4b-ecb86e0a91dd', 'resource', [1, 2, 0], [1, 2, 10058]),
}
CALLERS = {'scripts/blocks/fishTrap.js', 'scripts/blocks/iceHole.js',
           'scripts/creatures/cormorant.js', 'scripts/fishing/rod.js',
           'scripts/world/schools.js'}
HELPER = 'scripts/host_api/fishing-water-particles.js'
LANGS = {'texts/en_US.lang', 'texts/zh_CN.lang', 'texts/zh_TW.lang'}
FACTS = {'original_input_legacy_conflicts_reproduced', 'all_31_legacy_entries_sound_only',
         'core_retired_definitions_unchanged', 'material_methods_uniform',
         'partial_alpha_preserved', 'water_callers_preserved',
         'fallback_no_undefined_direction', 'normal_sets_surface_normals_available',
         'lang_line_joins_only', 'all_other_files_preserved',
         'paired_manifest_identity_api_equal', 'pure_magic_no_fauna_restoration',
         'source_origin_boundary_recorded'}
REPORT = 'client-assets-functional.json'
NATIVE = 'client-assets-native-validation.json'


def is_profile(value):
    return value.get('profile') == PROFILE


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def checked(ref):
    assert set(ref) == {'path', 'sha256'} and Path(ref['path']).is_absolute()
    path = Path(ref['path'])
    assert path.is_file() and not path.is_symlink() and path.stat().st_size <= 16 * 1024**2
    raw = path.read_bytes()
    assert digest(raw) == ref['sha256'], 'Client asset evidence changed'
    return json.loads(raw)


def log_path(report_path, report):
    ref = report['test_log']
    name = ref['name']
    assert isinstance(name, str) and Path(name).name == name and name not in ('', '.', '..')
    path = Path(report_path).parent / name
    assert path.resolve().parent == Path(report_path).parent.resolve() and not path.is_symlink()
    assert path.is_file() and path.stat().st_size <= 16 * 1024**2 and c.sha(path) == ref['sha256']
    return path


def input_refs(review, path, recipe):
    proof = checked(review['source_validation'])
    report = checked(proof['differential'])
    log = log_path(proof['differential']['path'], report)
    return {'prospective_preserved_inputs': c.sha(path), 'prospective_recipe': c.sha(recipe),
            'prospective_source_validation': review['source_validation']['sha256'],
            'prospective_client_assets_differential': proof['differential']['sha256'],
            'prospective_client_assets_log': c.sha(log)}


@lru_cache(maxsize=2)
def artifact_members(run_id, artifact_id, source, full_tree):
    from family_update.workflow import gh_json
    from family_update.cookery_cache_validation import private_ci_records
    from family_update.github_reads import api_bytes
    remote = current_name(REPOSITORY)
    repo = gh_json('repos/' + remote)
    verify_remote(repo, REPOSITORY)
    run = gh_json(f'repos/{remote}/actions/runs/{run_id}')
    verify_record(run['repository'], REPOSITORY)
    assert run['status'] == 'completed' and run['conclusion'] == 'success'
    assert run['head_sha'] == source and run['head_branch'] == 'main' and run['event'] in ('push', 'workflow_dispatch')
    assert run['path'] == '.github/workflows/canonical.yml'
    assert gh_json(f'repos/{remote}/git/commits/{source}')['tree']['sha'] == full_tree
    checks, statuses, unavailable = private_ci_records(remote, source)
    artifact = gh_json(f'repos/{remote}/actions/artifacts/{artifact_id}')
    assert artifact['name'] == 'client-assets-functional' and artifact['expired'] is False
    assert artifact['workflow_run']['id'] == run_id and artifact['workflow_run']['head_sha'] == source
    raw = api_bytes(f'repos/{remote}/actions/artifacts/{artifact_id}/zip')
    assert len(raw) <= 32 * 1024**2 and artifact['digest'] == 'sha256:' + digest(raw)
    with zipfile.ZipFile(io.BytesIO(raw)) as archive:
        names = archive.namelist()
        assert 1 <= len(names) <= 4 and len(names) == len(set(names))
        assert all(Path(name).name == name and name not in ('', '.', '..') for name in names)
        assert sum(row.file_size for row in archive.infolist()) <= 32 * 1024**2
        assert not any((row.external_attr >> 16) & 0o170000 == 0o120000 for row in archive.infolist())
        members = {name: archive.read(name) for name in names}
    return members, {'run_id': run_id, 'artifact_id': artifact_id, 'artifact_digest': artifact['digest'],
                     'checks': checks, 'statuses': statuses, 'unavailable_optional_services': unavailable}


def source_evidence(review, recipe):
    from family_update.extension_validation import source_binding
    from family_update.workflow import gh_json
    from family_update.prospective_preserved_inputs import committed
    proof = checked(review['source_validation'])
    baseline = c.read(c.EXTENSION / 'baseline.json')
    assert baseline['repository'] == PRIVATE and baseline['version'] == VERSION
    target = c.EXTENSION / '.repo-target.json'
    committed(target, '.repo-target.json')
    metadata = c.read(target)
    remote = current_name(REPOSITORY)
    assert metadata['repository'] == remote and metadata['repository_id'] == REPOSITORY_ID and metadata['private'] is True
    assert proof['schema'] == 1 and proof['kind'] == 'client_assets_source' and proof['profile'] == PROFILE
    binding = source_binding(proof, baseline)
    assert binding['actual_current_source_commit'] == review['source_commit']
    assert proof['git_tree'] == binding['current_source_tree_oid']
    assert type(proof['private_pull_request']) is int and proof['private_pull_request'] > 0
    pr = gh_json(f'repos/{remote}/pulls/{proof["private_pull_request"]}')
    assert pr['merged'] is True and pr['base']['ref'] == 'main'
    verify_record(pr['head']['repo'], REPOSITORY)
    verify_record(pr['base']['repo'], REPOSITORY)
    c.git(c.EXTENSION, 'merge-base', '--is-ancestor', pr['merge_commit_sha'], review['source_commit'])
    pr_tree = gh_json(f'repos/{remote}/git/commits/{pr["head"]["sha"]}')['tree']['sha']
    if pr_tree != proof['git_tree']:
        assert pr['merge_commit_sha'] == review['source_commit'], 'Client asset PR whole tree differs'
        assert gh_json(f'repos/{remote}/git/commits/{pr["merge_commit_sha"]}')['tree']['sha'] == proof['git_tree']
    report_ref = proof['differential']
    report = checked(report_ref)
    assert Path(report_ref['path']).name == REPORT
    assert report['schema'] == 1 and report['kind'] == 'client_assets_functional' and report['profile'] == PROFILE
    assert report['repository'] == PRIVATE and report['canonical_repository'] == remote and report['canonical_repository_id'] == REPOSITORY_ID
    assert report['version'] == baseline['version'] and report['source_trees'] == baseline['source_trees']
    assert report['source_commit'] == proof['source_commit'] and report['git_tree'] == proof['git_tree']
    assert report['recipe_sha256'] == review['recipe']['sha256']
    for key in ['approved_input_receipt_sha256', 'patch_source_sha256', 'uuids', 'input_hashes',
                'output_hashes', 'changed', 'before_versions', 'versions', 'source_facts']:
        assert report[key] == recipe[key], 'Client asset source recipe differs: ' + key
    assert all(report['facts'].get(key) is True for key in FACTS), 'Client asset differential coverage missing'
    assert report['test_command'] == ['python', 'tools/build_client_assets_evidence.py'] and report['test_exit_code'] == 0
    assert all(report[key] is False for key in ['client', 'simulated_players', 'native_loading', 'production_ready'])
    log = log_path(report_ref['path'], report)
    ci = proof['ci']
    assert set(ci) == {'run_id', 'artifact_id'} and all(type(ci[k]) is int and ci[k] > 0 for k in ci)
    members, ci_evidence = artifact_members(ci['run_id'], ci['artifact_id'], proof['source_commit'], proof['git_tree'])
    assert set(members) == {REPORT, log.name}, 'Client asset original CI artifact inventory differs'
    assert members[REPORT] == Path(report_ref['path']).read_bytes() and members[log.name] == log.read_bytes(), 'Client asset proof differs from original CI artifact'
    sources = recipe['patch_source_sha256']
    assert isinstance(sources, dict) and sources, 'Client asset patch sources must be pinned'
    for name, expected in sources.items():
        safe_relative(name)
        filename = c.EXTENSION / name
        assert filename.is_file() and not filename.is_symlink() and c.sha(filename) == expected
        committed(filename, name)
    return report_ref, binding, {'private_pull_request': proof['private_pull_request'], 'source_ci': ci_evidence}


def safe_relative(value):
    assert isinstance(value, str)
    path = PurePosixPath(value)
    assert path.parts and not path.is_absolute() and '..' not in path.parts and '\\' not in value and path.as_posix() == value


def patch_paths(recipe):
    facts = recipe['source_facts']
    identifiers = facts['legacy_identifiers']
    assert isinstance(identifiers, list) and len(identifiers) == 31 and identifiers == sorted(set(identifiers))
    assert all(isinstance(name, str) and re.fullmatch(r'(?:amw|amw_c|kaleidoscope_amw):[a-z0-9_]+', name) for name in identifiers)
    sets, normals = facts['item_heightmap_sets'], facts['normal_files']
    assert isinstance(sets, list) and len(sets) == 156 and sets == sorted(set(sets))
    assert all(isinstance(name, str) and re.fullmatch(r'textures/items/kfv_[a-z0-9_]+\.texture_set\.json', name) for name in sets)
    expected_normals = sorted('textures/items/' + Path(name).name.removesuffix('.texture_set.json') + '_normal.png' for name in sets)
    assert normals == expected_normals, 'Client asset normal paths exceed their exact item set'
    return {'AMW_BP': {'manifest.json'}, 'AMW_RP': {'manifest.json', 'blocks.json'},
            'Fishing_BP': {'manifest.json', 'blocks/fish_tank.json', HELPER, *CALLERS},
            'Fishing_RP': {'manifest.json', *LANGS, *sets, *normals}}


def validate_recipe(recipe, admitted, current):
    assert recipe['schema'] == 1 and recipe['profile'] == PROFILE and recipe['source_package_version'] == VERSION
    assert recipe['approved_input_receipt_sha256'] == APPROVED
    assert all(recipe[key] is False for key in ['client', 'native_loading', 'production_ready'])
    assert all(set(recipe[key]) == set(PACKS) for key in ['uuids', 'input_hashes', 'output_hashes', 'changed', 'before_versions', 'versions'])
    expected_paths = patch_paths(recipe)
    for name, (uid, side, before_version, after_version) in PACKS.items():
        assert recipe['uuids'][name] == uid and recipe['before_versions'][name] == before_version and recipe['versions'][name] == after_version
        assert admitted[uid]['source']['owner'] == 'preserved' and admitted[uid]['side'] == side and admitted[uid]['version'] == before_version
        assert all(current[uid][key] == admitted[uid][key] for key in ['side', 'version', 'files']), 'Client assets cannot approve installed drift'
        before, after = recipe['input_hashes'][name], recipe['output_hashes'][name]
        assert before == admitted[uid]['files'] and set(before) <= set(after), 'Client asset file inventory removed or changed inputs'
        for path, value in {**before, **after}.items():
            safe_relative(path)
            assert isinstance(value, str) and re.fullmatch('[0-9a-f]{64}', value)
        changed = {path for path in after if before.get(path) != after[path]}
        assert changed == set(recipe['changed'][name]) == expected_paths[name], 'Client asset delta exceeds fixed repair paths'
        assert all(recipe['changed'][name][p] == {'before': before.get(p), 'after': after[p]} for p in changed)
        additions = {HELPER} if name == 'Fishing_BP' else set(recipe['source_facts']['normal_files']) if name == 'Fishing_RP' else set()
        assert set(after) - set(before) == additions, 'Client asset additions exceed helper/normals'


def validate_manifest(name, manifest, prior):
    uid, side, old_version, version = PACKS[name]
    assert prior['header']['uuid'] == manifest['header']['uuid'] == uid
    assert prior['header']['version'] == old_version and manifest['header']['version'] == version
    assert manifest['header']['name'] == prior['header']['name'] + ' [本機顯示修復 1.0.58]'
    result = copy.deepcopy(manifest)
    result['header']['name'], result['header']['version'] = prior['header']['name'], prior['header']['version']
    assert len(result['modules']) == len(prior['modules']) and result['modules']
    for row, old in zip(result['modules'], prior['modules'], strict=True):
        assert row['version'] == version
        row['version'] = old['version']
    assert ('resource' if all(row['type'] == 'resources' for row in result['modules']) else 'behavior') == side
    assert len(result.get('dependencies', [])) == len(prior.get('dependencies', []))
    for row, old in zip(result.get('dependencies', []), prior.get('dependencies', []), strict=True):
        expected = copy.deepcopy(old)
        if old.get('uuid') in {value[0] for value in PACKS.values()}:
            peer = next(value for value in PACKS.values() if value[0] == old['uuid'])
            expected['version'] = peer[3]
        assert row == expected, 'Client asset dependency/API changed beyond paired versions'
        if 'version' in old:
            row['version'] = old['version']
    assert result == prior, 'Client asset manifest changed beyond names/paired versions'


def select(preserved, original, path, review):
    from family_update.prospective_preserved_inputs import committed, recipe_path, separate
    assert c.EXTENSION and not any(c.CONFIG.get(key) for key in ['approved_runtime_retention', 'extension_hold', 'held_sources', 'preserved_reconciliation', 'preserved_additions'])
    assert set(review) == {'schema', 'profile', 'source_commit', 'recipe', 'source_validation', 'packs'}
    assert type(review['schema']) is int and review['schema'] == 1 and is_profile(review) and set(review['packs']) == set(PACKS)
    assert Path(path).is_absolute() and not c.git(c.EXTENSION, 'status', '--porcelain')
    assert review['source_commit'] == c.git(c.EXTENSION, 'rev-parse', 'HEAD')
    for source in [c.EXTENSION, *c.SOURCES.values()]:
        assert not Path(path).resolve().is_relative_to(Path(source).resolve())
    committed(c.EXTENSION / 'baseline.json', 'baseline.json')
    filename, relative = recipe_path(review)
    assert relative == RECIPE
    committed(filename, relative)
    recipe = checked({'path': str(filename), 'sha256': review['recipe']['sha256']})
    old = {row['uuid']: row for row in original['packs']}
    current = {row['uuid']: row for row in preserved}
    approved_path = Path(c.read(c.R / 'production-before/senluo-policy.json')['approved_receipt'])
    approved = c.read(approved_path)
    admitted = {row['uuid']: row for row in approved['packs']}
    assert len(old) == len(original['packs']) and len(current) == len(preserved) and len(admitted) == len(approved['packs'])
    assert set(old) == set(admitted) and set(current) == {uid for uid, row in admitted.items() if row['source']['owner'] == 'preserved'}
    assert all(all(old[uid][key] == admitted[uid][key] for key in ['side', 'version', 'files']) for uid in old), 'Captured family differs from admission'
    assert all(all(current[uid][key] == admitted[uid][key] for key in ['side', 'version', 'files']) for uid in current), 'Unaffected preserved pack drift'
    assert recipe['approved_input_receipt_sha256'] == c.sha(approved_path)
    validate_recipe(recipe, admitted, current)
    differential, binding, ci = source_evidence(review, recipe)
    roots, outputs, manifests = [], {}, {}
    protected = [c.B, c.W, c.Q, c.R, c.C, c.EXTENSION, *c.SOURCES.values()]
    for name, (uid, side, _, version) in PACKS.items():
        row = review['packs'][name]
        assert set(row) == {'path', 'uuid'} and row['uuid'] == uid
        root = separate(Path(row['path']), protected)
        assert all(root != other and root not in other.parents and other not in root.parents for other in roots)
        roots.append(root)
        assert c.hashes(root) == recipe['output_hashes'][name], 'Prepared client assets differ from source CI'
        prior = Path(current[uid]['path']) / 'manifest.json'
        assert c.sha(prior) == current[uid]['files']['manifest.json']
        manifest = c.read(root / 'manifest.json')
        validate_manifest(name, manifest, c.read(prior))
        manifests[uid] = manifest
        outputs[name] = {'uuid': uid, 'path': str(root), 'side': side, 'version': version}
    for uid, manifest in manifests.items():
        for dependency in manifest.get('dependencies', []):
            if dependency.get('uuid') in manifests:
                assert dependency['version'] == manifests[dependency['uuid']]['header']['version']
    evidence = {'schema': 1, 'profile': PROFILE, 'review': c.report_ref(path), 'source_commit': review['source_commit'],
                **binding, **ci, 'version': VERSION, 'recipe': c.report_ref(filename),
                'source_validation': review['source_validation'], 'differential': differential,
                'source_log': c.report_ref(log_path(differential['path'], checked(differential))),
                'packs': outputs, 'unaffected_preserved': {uid: {key: row[key] for key in ['side', 'version', 'files']}
                    for uid, row in current.items() if uid not in {value[0] for value in PACKS.values()}},
                'current_live_reconciled': False,
                'full_family_acceptance_still_required': True, 'client': False, 'production_ready': False}
    assert c.git(c.EXTENSION, 'rev-parse', 'HEAD') == review['source_commit'] and not c.git(c.EXTENSION, 'status', '--porcelain')
    replacements = {row['uuid']: Path(row['path']) for row in outputs.values()}
    return [replacements.get(row['uuid'], Path(row['path'])) for row in preserved], evidence


def verify_candidate(receipt, selected):
    assert is_profile(selected) and selected['version'] == VERSION and set(selected['packs']) == set(PACKS)
    recipe = checked(selected['recipe'])
    assert recipe['profile'] == PROFILE and set(recipe['output_hashes']) == set(PACKS)
    rows = {row['uuid']: row for row in receipt['packs']}
    assert len(rows) == len(receipt['packs'])
    expected_uuids = {value[0] for value in PACKS.values()} | set(selected['unaffected_preserved'])
    assert {uid for uid, row in rows.items() if row['source']['owner'] == 'preserved'} == expected_uuids
    for uid, original in selected['unaffected_preserved'].items():
        assert {key: rows[uid][key] for key in ['side', 'version', 'files']} == original, 'Unaffected candidate preserved pack changed'
    for name, (uid, side, _, version) in PACKS.items():
        expected = selected['packs'][name]
        assert expected['uuid'] == uid and expected['side'] == side and expected['version'] == version
        row = rows[uid]
        assert row['source']['owner'] == 'preserved' and row['files'] == recipe['output_hashes'][name] and row['side'] == side and row['version'] == version


def bind_native(receipt, evidence):
    if not c.CONFIG.get('prospective_preserved_inputs'):
        return
    review = c.read(Path(c.CONFIG['prospective_preserved_inputs']))
    if not is_profile(review):
        return
    selected = c.read(c.R / 'prospective-preserved-inputs-check.json')
    assert selected['review'] == c.report_ref(Path(c.CONFIG['prospective_preserved_inputs']))
    verify_candidate(receipt, selected)
    assert c.git(c.EXTENSION, 'rev-parse', 'HEAD') == selected['source_commit'] and c.git(c.EXTENSION, 'rev-parse', 'HEAD^{tree}') == selected['current_source_tree_oid']
    assert checked(selected['source_validation'])['differential'] == selected['differential']
    assert selected['source_log'] == c.report_ref(log_path(selected['differential']['path'], checked(selected['differential'])))
    assert all(evidence[key] is True for key in ['fresh_stopped_backup', 'existing_world_loaded', 'exact_files_checked', 'bds', 'saved_world_migration'])
    assert evidence['candidate_receipt_sha256'] == c.sha(c.C / 'family-receipt.json')
    assert evidence['client'] is False and evidence['simulated_players'] is False and evidence['test_only_overlays'] == []
    assert [row['phase'] for row in evidence['runs']] == ['first', 'restart']
    assert all(row['ok'] and not row['errors'] and row['real_player_connections'] == 0 and all(row[key] for key in ['player_records_unchanged', 'custom_container_inventories_retained', 'native_freezer_inputs_retained']) for row in evidence['runs'])
    c.atomic(c.R / NATIVE, {'schema': 1, 'profile': PROFILE, 'version': VERSION,
        'source': selected['differential'], 'source_log': selected['source_log'],
        'fresh_native': c.report_ref(c.R / 'saved-world-report.json'),
        'candidate_receipt_sha256': evidence['candidate_receipt_sha256'],
        'source_commit': selected['source_commit'], 'source_tree_oid': selected['current_source_tree_oid'],
        'packs': selected['packs'], 'native_loading': True, 'saved_world_migration': True,
        'client': False, 'production_ready': False})


def verify_installation(receipt, selected):
    verify_candidate(receipt, selected)
    native = c.read(c.R / NATIVE)
    assert native['profile'] == PROFILE and native['version'] == VERSION
    assert native['candidate_receipt_sha256'] == c.sha(c.C / 'family-receipt.json') and native['source'] == selected['differential']
    assert native['source_commit'] == selected['source_commit'] and native['source_tree_oid'] == selected['current_source_tree_oid']
    assert native['source_log'] == selected['source_log'] and native['fresh_native'] == c.report_ref(c.R / 'saved-world-report.json')
    assert native['packs'] == selected['packs']
    assert native['native_loading'] is True and native['saved_world_migration'] is True and native['client'] is False and native['production_ready'] is False
