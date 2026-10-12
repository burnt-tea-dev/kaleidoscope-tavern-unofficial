"""Admit one conserved Ribbits pair from exact source CI, then fresh saved load.

This profile cannot approve installed drift, another addon, storage changes or
an arbitrary script replacement. The complete family gates remain mandatory.
Full third-party scripts and structure fixtures remain in the private source.
"""
import copy
from pathlib import Path
from family_update import common as c

PROFILE = 'senluo-ribbits-startup-20261013'
RECIPE = 'companion-sources/ribbits-startup-20261013/recipe.json'
PRIVATE = 'local/senluo-amw-cuisine'
REPOSITORY = 'casama233/senluo-family-integration-private'
REPOSITORY_ID = 1406868911
VERSION = [1, 0, 10036]
PACKS = {
    'RIBBITS_BP': ('1e47fa97-55db-492e-b732-350e338b4fe5', 'behavior'),
    'RIBBITS_RP': ('a26e36f3-6fa2-4866-97bf-f9c2b9be8bdd', 'resource'),
}
PATCH_PATHS = {'RIBBITS_BP': {'manifest.json', 'scripts/main.js'},
               'RIBBITS_RP': {'manifest.json'}}
FACTS = ['actual_fixed_assets_equal', 'exact_connection_sequence_equal',
         'duplicate_rows_and_order_equal', 'bounds_and_noninteger_equal',
         'registered_native_state_equal', 'missing_native_permutation_equal',
         'unknown_or_malformed_fallback_equal', 'fixed_id_size_table_guarded',
         'all_other_files_preserved', 'original_archive_hotpath_reproduced',
         'extra_unregistered_malformed_jigsaw_warning_boundary_recorded',
         'paired_manifest_identity_api_equal', 'private_runtime_34_unchanged']


def is_profile(value):
    return value.get('profile') == PROFILE


def checked(ref):
    assert set(ref) == {'path', 'sha256'} and Path(ref['path']).is_absolute()
    assert c.sha(ref['path']) == ref['sha256'], 'Ribbits evidence changed'
    return c.read(Path(ref['path']))


def source_evidence(review, recipe):
    from family_update.extension_validation import source_binding
    from family_update.cookery_cache_validation import private_ci_records
    from family_update.workflow import gh_json
    proof = checked(review['source_validation'])
    baseline = c.read(c.EXTENSION / 'baseline.json')
    assert baseline['repository'] == PRIVATE and baseline['version'] == [1, 0, 34]
    assert proof['kind'] == 'ribbits_startup'
    binding = source_binding(proof, baseline)
    assert binding['actual_current_source_commit'] == review['source_commit']
    target = c.read(c.EXTENSION / '.repo-target.json')
    assert target['repository'] == REPOSITORY and target['repository_id'] == REPOSITORY_ID and target['private'] is True
    remote = gh_json('repos/' + REPOSITORY)
    assert remote['full_name'] == REPOSITORY and remote['id'] == REPOSITORY_ID and remote['private'] is True
    pr = gh_json(f'repos/{REPOSITORY}/pulls/{proof["private_pull_request"]}')
    assert pr['merged'] and pr['base']['ref'] == 'main'
    assert pr['head']['repo']['id'] == pr['base']['repo']['id'] == REPOSITORY_ID
    assert c.git(c.EXTENSION, 'merge-base', pr['merge_commit_sha'], review['source_commit']) == pr['merge_commit_sha']
    assert gh_json(f'repos/{REPOSITORY}/git/commits/{pr["head"]["sha"]}')['tree']['sha'] == binding['current_source_tree_oid']
    checks, statuses, unavailable = private_ci_records(REPOSITORY, review['source_commit'])
    report = checked(proof['differential'])
    assert report['schema'] == 1 and report['kind'] == 'ribbits_startup'
    assert report['repository'] == PRIVATE and report['canonical_repository'] == REPOSITORY and report['canonical_repository_id'] == REPOSITORY_ID
    assert report['version'] == baseline['version'] and report['source_trees'] == baseline['source_trees']
    assert report['git_tree'] == binding['current_source_tree_oid']
    assert gh_json(f'repos/{REPOSITORY}/git/commits/{report["source_commit"]}')['tree']['sha'] == report['git_tree']
    assert report['recipe_sha256'] == review['recipe']['sha256']
    for key in ['approved_input_receipt_sha256', 'approved_inputs_sha256', 'patch_source_sha256',
                'structure_coverage_sha256', 'uuids', 'input_hashes', 'output_hashes',
                'changed', 'before_versions', 'versions']:
        assert report[key] == recipe[key], 'Ribbits source recipe differs: ' + key
    assert report['structure_count'] == 54 and report['original_native_reads'] == 29635
    assert report['repaired_native_reads'] == report['connection_count'] == 158
    assert all(report['facts'].get(key) is True for key in FACTS), 'Ribbits differential coverage missing'
    clean = report['clean_stored_archive_reproduction']
    assert clean['path'] == 'companion-sources/ribbits-startup-20261013/clean-stored-archive-reproduction.json'
    assert c.sha(c.EXTENSION / clean['path']) == clean['sha256'] == recipe['clean_stored_archive_reproduction_sha256']
    assert clean['archive_sha256'] == report['original_archive_sha256'] == recipe['original_archive_sha256']
    assert clean['official_latest_verified'] is False and clean['original_editor_known'] is False
    assert report['test_command'] == ['node', 'companion-sources/ribbits-startup-20261013/ribbits-startup.test.mjs'] and report['test_exit_code'] == 0
    assert all(report[key] is False for key in ['client', 'simulated_players', 'native_loading', 'production_ready'])
    log = Path(proof['differential']['path']).parent / report['test_log']['name']
    assert log.parent.resolve() == Path(proof['differential']['path']).parent.resolve() and c.sha(log) == report['test_log']['sha256']
    return proof['differential'], binding, {'private_pull_request': proof['private_pull_request'],
        'private_checks': checks, 'private_statuses': statuses, 'unavailable_optional_services': unavailable}


def validate_recipe(recipe, admitted, current):
    assert recipe['schema'] == 1 and recipe['profile'] == PROFILE and recipe['source_package_version'] == [1, 0, 34]
    assert recipe['client'] is False and recipe['production_ready'] is False
    assert set(recipe['uuids']) == set(recipe['input_hashes']) == set(recipe['output_hashes']) == set(recipe['changed']) == set(recipe['before_versions']) == set(recipe['versions']) == set(PACKS)
    for name, (uid, side) in PACKS.items():
        assert recipe['uuids'][name] == uid and recipe['before_versions'][name] == [1, 0, 10] and recipe['versions'][name] == VERSION
        assert admitted[uid]['source']['owner'] == 'preserved' and admitted[uid]['side'] == side and admitted[uid]['version'] == [1, 0, 10]
        assert all(current[uid][key] == admitted[uid][key] for key in ['side', 'version', 'files']), 'Ribbits cannot approve installed drift'
        before, after = recipe['input_hashes'][name], recipe['output_hashes'][name]
        assert before == admitted[uid]['files'] and set(before) == set(after), 'Ribbits file inventory changed'
        changed = {p for p in before if before[p] != after[p]}
        assert changed == set(recipe['changed'][name]) == PATCH_PATHS[name], 'Ribbits delta exceeds its exact initialization/identity paths'
        assert all(recipe['changed'][name][p] == {'before': before[p], 'after': after[p]} for p in changed)


def validate_manifest(name, manifest, prior):
    uid, _ = PACKS[name]
    assert prior['header']['uuid'] == manifest['header']['uuid'] == uid
    assert prior['header']['version'] == [1, 0, 10] and manifest['header']['version'] == VERSION
    label = prior['header']['name'] + ' [Senluo startup 1.0.10036]'
    assert manifest['header']['name'] == label
    normalized = copy.deepcopy(manifest)
    normalized['header'] = copy.deepcopy(prior['header'])
    assert len(normalized['modules']) == len(prior['modules'])
    for module, old in zip(normalized['modules'], prior['modules'], strict=True):
        assert module['version'] == VERSION
        module['version'] = old['version']
    assert len(normalized.get('dependencies', [])) == len(prior.get('dependencies', []))
    peers = {row[0] for row in PACKS.values()}
    for dependency, old in zip(normalized.get('dependencies', []), prior.get('dependencies', []), strict=True):
        expected = copy.deepcopy(old)
        if old.get('uuid') in peers:
            expected['version'] = VERSION
        assert dependency == expected, 'Ribbits dependency changed beyond the exact pair'
        if 'version' in old:
            dependency['version'] = old['version']
    # Header fields other than name/version must also stay exact.
    header = copy.deepcopy(manifest['header'])
    header['name'], header['version'] = prior['header']['name'], prior['header']['version']
    assert header == prior['header'] and normalized == prior, 'Ribbits identity/API changed beyond paired version'


def select(preserved, original, path, review):
    from family_update.prospective_preserved_inputs import committed, recipe_path, separate
    assert c.EXTENSION and not any(c.CONFIG.get(k) for k in ['approved_runtime_retention', 'extension_hold', 'held_sources', 'preserved_reconciliation', 'preserved_additions'])
    assert set(review) == {'schema', 'profile', 'source_commit', 'recipe', 'source_validation', 'packs'}
    assert type(review['schema']) is int and review['schema'] == 1 and is_profile(review) and set(review['packs']) == set(PACKS)
    assert Path(path).is_absolute() and not c.git(c.EXTENSION, 'status', '--porcelain')
    for source in [c.EXTENSION, *c.SOURCES.values()]:
        assert not Path(path).resolve().is_relative_to(Path(source).resolve())
    committed(c.EXTENSION / 'baseline.json', 'baseline.json')
    filename, relative = recipe_path(review)
    assert relative == RECIPE
    committed(filename, relative)
    recipe = checked({'path': str(filename), 'sha256': review['recipe']['sha256']})
    old = {p['uuid']: p for p in original['packs']}
    current = {p['uuid']: p for p in preserved}
    approved_path = Path(c.read(c.R / 'production-before/senluo-policy.json')['approved_receipt'])
    approved = c.read(approved_path)
    admitted = {p['uuid']: p for p in approved['packs']}
    assert len(old) == len(original['packs']) and len(current) == len(preserved) and len(admitted) == len(approved['packs'])
    assert set(old) == set(admitted) and set(current) == {u for u, p in admitted.items() if p['source']['owner'] == 'preserved'}
    assert all(all(old[u][k] == admitted[u][k] for k in ['side', 'version', 'files']) for u in old), 'Captured family differs from admission'
    assert recipe['approved_input_receipt_sha256'] == c.sha(approved_path)
    validate_recipe(recipe, admitted, current)
    differential, binding, ci = source_evidence(review, recipe)
    protected = [c.B, c.W, c.Q, c.R, c.C, c.EXTENSION, *c.SOURCES.values()]
    roots, outputs, manifests = [], {}, {}
    for name, (uid, side) in PACKS.items():
        row = review['packs'][name]
        assert set(row) == {'path', 'uuid'} and row['uuid'] == uid
        root = separate(Path(row['path']), protected)
        assert all(root != p and root not in p.parents and p not in root.parents for p in roots)
        roots.append(root)
        assert c.hashes(root) == recipe['output_hashes'][name], 'Prepared Ribbits output differs from source CI'
        prior_path = Path(current[uid]['path']) / 'manifest.json'
        assert c.sha(prior_path) == current[uid]['files']['manifest.json']
        manifest = c.read(root / 'manifest.json')
        validate_manifest(name, manifest, c.read(prior_path))
        manifests[uid] = manifest
        outputs[name] = {'uuid': uid, 'path': str(root), 'side': side, 'version': VERSION}
    for uid, manifest in manifests.items():
        for dep in manifest.get('dependencies', []):
            if dep.get('uuid') in manifests:
                assert dep['version'] == manifests[dep['uuid']]['header']['version']
    evidence = {'schema': 1, 'profile': PROFILE, 'review': c.report_ref(path), 'source_commit': review['source_commit'],
        **binding, **ci, 'version': [1, 0, 34], 'recipe': c.report_ref(filename), 'source_validation': review['source_validation'],
        'differential': differential, 'packs': outputs, 'current_live_reconciled': False,
        'full_family_acceptance_still_required': True, 'client': False, 'production_ready': False}
    assert c.git(c.EXTENSION, 'rev-parse', 'HEAD') == review['source_commit'] and not c.git(c.EXTENSION, 'status', '--porcelain')
    replacements = {p['uuid']: Path(p['path']) for p in outputs.values()}
    return [replacements.get(p['uuid'], Path(p['path'])) for p in preserved], evidence


def verify_candidate(receipt, selected):
    assert selected['profile'] == PROFILE and selected['version'] == [1, 0, 34] and set(selected['packs']) == set(PACKS)
    recipe = checked(selected['recipe'])
    assert recipe['profile'] == PROFILE and set(recipe['output_hashes']) == set(PACKS)
    rows = {p['uuid']: p for p in receipt['packs']}
    assert len(rows) == len(receipt['packs'])
    for name, (uid, side) in PACKS.items():
        expected = selected['packs'][name]
        assert expected['uuid'] == uid and expected['side'] == side and expected['version'] == VERSION
        row = rows[uid]
        assert row['source']['owner'] == 'preserved' and row['files'] == recipe['output_hashes'][name] and row['side'] == side and row['version'] == VERSION


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
    checked(selected['differential'])
    assert evidence['fresh_stopped_backup'] and evidence['exact_files_checked'] and evidence['bds'] and evidence['saved_world_migration']
    assert evidence['candidate_receipt_sha256'] == c.sha(c.C / 'family-receipt.json')
    assert evidence['client'] is False and evidence['simulated_players'] is False
    assert [p['phase'] for p in evidence['runs']] == ['first', 'restart'] and all(p['ok'] and not p['errors'] for p in evidence['runs'])
    c.atomic(c.R / 'ribbits-startup-native-validation.json', {'schema': 1, 'source': selected['differential'],
        'fresh_native': c.report_ref(c.R / 'saved-world-report.json'), 'candidate_receipt_sha256': evidence['candidate_receipt_sha256'],
        'source_commit': selected['source_commit'], 'source_tree_oid': selected['current_source_tree_oid'],
        'packs': selected['packs'], 'native_loading': True, 'saved_world_migration': True,
        'client': False, 'production_ready': False,
        'scope': 'This exact conserved pair loaded/restarted on the fresh stopped save; diagnostics and client acceptance remain separate.'})


def verify_installation(receipt, selected):
    verify_candidate(receipt, selected)
    native = c.read(c.R / 'ribbits-startup-native-validation.json')
    assert native['candidate_receipt_sha256'] == c.sha(c.C / 'family-receipt.json') and native['source'] == selected['differential']
    assert native['source_commit'] == selected['source_commit'] and native['source_tree_oid'] == selected['current_source_tree_oid']
    assert native['fresh_native'] == c.report_ref(c.R / 'saved-world-report.json')
    assert native['packs'] == selected['packs']
    assert native['native_loading'] is True and native['saved_world_migration'] is True and native['client'] is False and native['production_ready'] is False
