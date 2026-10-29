"""Build exact full family only from clean canonical main and pinned archives."""
import argparse
from family_update.common import *
from family_bundle import assemble

def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--execute', action='store_true', help='Build task-local release candidate')
    args = parser.parse_args(argv)
    if not args.execute:
        print(json.dumps({'execute': False, 'sources': {k: str(v) for k,v in SOURCES.items()}, 'extension': str(EXTENSION) if EXTENSION else None, 'preserved_inventory': str(R / 'production-before/preserved-packs.json'), 'output': str(C), 'existing_candidate': C.exists()}, indent=2)); return
    lease_available()
    for path in [C, R / 'build-evidence.json', R / 'compatibility-report.json', R / 'curated-input-selection.json']:
        assert not path.exists(), 'Never overwrite existing candidate/report: ' + str(path)
    from family_update.storage import require_space
    require_space(R, "Family candidate assembly")
    original = verify_predeploy()
    sources = source_state(verify_remote=True)
    archives = archive_paths()
    preserved = read(R / 'production-before/preserved-packs.json')
    if CONFIG.get('fresh_world'):
        assert preserved == [], 'Fresh worlds cannot inherit captured retained packs'
    from family_update.current_author_validation import (curated_inputs_enabled,select_curated_inputs,verify_curated_inputs,
        select_replacement_inputs,verify_replacement_inputs)
    local_sources,local_selection,curated_selection={},None,None
    prospective=None
    if curated_inputs_enabled():
        preserved_roots,local_sources,curated_selection=select_curated_inputs(original)
        atomic(R/'curated-input-selection.json',curated_selection)
    else:
        from family_update.prospective_preserved_inputs import select as select_prospective,verify_candidate as verify_prospective
        preserved_roots,prospective=select_prospective(preserved,original)
        if CONFIG.get('managed_drift_recovery'):
            from family_update.managed_drift_recovery import select_local_inputs
            preserved_roots,local_sources,local_selection=select_local_inputs(preserved_roots,original)
    replacement_roots,replacement_sources,replacement_selection=select_replacement_inputs(original)
    if replacement_selection is not None:
        replaced=set(replacement_selection['packs'])
        preserved_roots=[root for root in preserved_roots
                         if read(Path(root)/'manifest.json')['header']['uuid'] not in replaced]+replacement_roots
        local_sources={**local_sources,**replacement_sources}
        atomic(R/'author-replacement-selection.json',replacement_selection)
    from family_update.identity_migration import assembly_order, candidate_plan
    requested=CONFIG.get('held_sources',[])
    assembly_lock, assembly_sources, retention = read(T / 'family/upstream.lock.json'), SOURCES.copy(), None
    if CONFIG.get('approved_runtime_retention'):
        assembly_lock, assembly_sources, retention = select_approved_runtime_retention(original, sources)
    local_arguments={'preserved_sources':local_sources} if local_sources else {}
    receipt = assemble(assembly_lock, assembly_sources, archives, C, extensions=[EXTENSION] if EXTENSION else [], preserved=preserved_roots, reviewed_order=assembly_order(original),held_sources=requested,**local_arguments)
    if CONFIG.get('managed_drift_recovery'):
        from family_update.managed_drift_recovery import verify_owner_accepted_inputs
        verify_owner_accepted_inputs(receipt, original)
    if prospective is not None:verify_prospective(receipt,prospective)
    if curated_selection is not None:verify_curated_inputs(receipt,curated_selection)
    if replacement_selection is not None and curated_selection is None:
        verify_replacement_inputs(receipt,replacement_selection)
    if local_selection is not None:
        from family_update.managed_drift_recovery import verify_local_target
        verify_local_target(receipt,original)
    from family_update.source_holds import verify_retained,verify_retained_extension
    verify_retained(receipt,original,read(T/'family/upstream.lock.json'),requested)
    verify_retained_extension(receipt,original,read(T/'family/upstream.lock.json'),CONFIG.get('extension_hold',False))
    candidate_plan(receipt, original)
    from family_update.approved_runtime_retention import verify_candidate
    verify_candidate(receipt, original, retention)
    audit_candidate(C, receipt)
    compatibility = quality(C, receipt)
    atomic(R / 'compatibility-report.json', compatibility)
    tools = ['family_bundle.py', 'family_guard.py', 'family_saved_world.py', 'author_state_migration.py', 'bedrock_nbt.py', 'baseline_gate.py', 'host_extensions.py', 'container_recovery.py', 'native_actor_recovery.py', 'native_actor_recovery_validation.py', 'cookery_station_extension.py']
    tools = [name for name in tools if (T / 'tools' / name).exists()]
    evidence = {'recorded_at': now(), 'config_sha256': sha(CONFIG_PATH), 'orchestration_sha256': orchestration_hashes(), 'sources': sources, 'candidate_receipt_sha256': sha(C / 'family-receipt.json'), 'upstream_lock_sha256': sha(T / 'family/upstream.lock.json'), 'tool_sha256': {name: sha(T / 'tools' / name) for name in tools}, 'packs': len(receipt['packs']), 'versions': versions(receipt), 'static_family_assembly': True, 'functional_tests_recorded_separately': True, 'client': False, 'production_ready': False}
    if retention is not None:evidence['approved_runtime_retention'] = retention
    if prospective is not None:
        evidence['prospective_preserved_inputs']=prospective
        atomic(R/'prospective-preserved-inputs-check.json',prospective)
    if local_selection is not None:
        evidence['managed_local_input_selection']=local_selection
        atomic(R/'managed-local-input-selection.json',local_selection)
    if curated_selection is not None:
        evidence['curated_input_selection']=report_ref(R/'curated-input-selection.json')
    if replacement_selection is not None:
        evidence['author_replacement_selection']=report_ref(R/'author-replacement-selection.json')
    atomic(R / 'build-evidence.json', evidence)
    evidence['external_input_sha256']=external_input_hashes();atomic(R/'build-evidence.json',evidence)
    verify_predeploy()
    if retention is not None:assert source_state(verify_remote=True) == sources, 'Canonical states changed during retained assembly'
    print(json.dumps({'packs': len(receipt['packs']), 'versions': versions(receipt), 'candidate_receipt_sha256': evidence['candidate_receipt_sha256']}, ensure_ascii=False))
if __name__ == '__main__': main()
