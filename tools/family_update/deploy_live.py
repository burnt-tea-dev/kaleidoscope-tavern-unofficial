"""Reviewable full-family deployment. Default is read-only; --execute is required."""
import argparse, fcntl, shutil, traceback
from family_update.common import *
import hashlib

CONSOLIDATED_AUTHORIZATION_LINE_SHA256 = '470615d4dd6da2d869a9e0d4d4606d265230fb36e060ed4acab15fdccd00017b'
CURRENT_AUTHORIZATION_LINE_SHA256S = {
    CONSOLIDATED_AUTHORIZATION_LINE_SHA256,
    # Current managed policy after the owner's 2026-10-27 native/experimental clarification.
    '135356da8e3ab5ea3a18baa9a35458ccd5643f6a8862df32163d1eb96608fff7',
}

class RecoveryRequired(RuntimeError):
    """A failed rollback must retain the stopped server and active lease."""

def retain_stopped_on_failure():
    """Explicit recovery and normal-idle handoffs never restart an old stack."""
    policy = CONFIG.get('managed_drift_failure_policy')
    assert policy in [None, 'retain_stopped'], 'Unknown managed drift failure policy'
    if policy is not None:
        assert CONFIG.get('managed_drift_recovery'), 'Stopped drift recovery requires a reviewed managed repair'
    idle = CONFIG.get('normal_idle_update')
    if idle is not None:
        assert isinstance(idle, str) and Path(idle).is_absolute(), 'Normal idle update needs its reviewed input'
        assert not CONFIG.get('managed_drift_recovery') and not CONFIG.get('preinstall_recovery_output'), 'Normal idle update cannot borrow recovery exceptions'
        return True
    return policy == 'retain_stopped' or bool(CONFIG.get('native_actor_recovery_plan') or CONFIG.get('fresh_world'))

def deployment_authorized(agents):
    """Recognize only the reviewed standing instructions, without broadening scope."""
    if all((text in agents for text in ['使用者已持續授權', '供使用者直接測試開發效果', '`deferred_client_acceptance`'])):
        return True
    lines = set(agents.splitlines())
    return {'# Senluo maintenance', "Scope: Senluo family work on this host. These are the owner's standing requirements (2026-09-30 through 2026-10-11), consolidated on 2026-10-16. Later explicit user instructions take precedence."}.issubset(lines) and any((hashlib.sha256(line.encode('utf-8', 'surrogatepass')).hexdigest() in CURRENT_AUTHORIZATION_LINE_SHA256S for line in lines))

def preflight():
    retain_stopped_on_failure()
    if CONFIG.get('native_actor_recovery_plan'):
        assert not CONFIG.get('container_recovery_plan') and not CONFIG.get('identity_migration'), 'Combined actor and block/identity recovery needs a separately reviewed transaction'
    initial = summary()
    initial_status = initial['status']
    original = verify_predeploy()
    receipt = verify_candidate_sources()
    from family_update.workflow import no_update_needed
    if not CONFIG.get('fresh_world') and no_update_needed(receipt, original):
        return original, receipt
    if CONFIG.get('fresh_world'):
        target = B / 'worlds' / CONFIG['fresh_world']['level_name']
        assert not target.exists(), 'Never replace an existing fresh-world target'
    if CONFIG.get('fresh_world') or CONFIG.get('normal_idle_update'):
        from family_update.normal_idle_update import validate_initial_status
        validate_initial_status(initial)
    elif CONFIG.get('managed_drift_recovery'):
        from family_update.managed_drift_recovery import validate_initial_status
        validate_initial_status(initial)
    else:
        assert initial_status == 'RUNNING', 'Live must initially be RUNNING; never start an intentionally stopped server during recovery'
    assert sha(Q / 'family_guard.py') == sha(T / 'tools/family_guard.py'), 'BSM guard differs from canonical; investigate, never silently replace'
    # Every entry point uses the same evidence validator; share the already
    # verified immutable candidate within this preflight instead of rescanning.
    from family_update.workflow import record_static
    record_static(verified_candidate=receipt)
    quality(C, receipt)
    from family_update.identity_migration import candidate_plan
    candidate_plan(receipt, original)
    source_state(verify_remote=True)
    agents = Path(str(AUTHORIZATION)).read_text()
    assert deployment_authorized(agents), 'Re-read current deployment authorization'
    from family_update.storage import deployment_allocation, require_space
    allocation = deployment_allocation(W, C,
        identity_migration=bool(CONFIG.get('identity_migration')),
        container_recovery=bool(CONFIG.get('container_recovery_plan')),
        native_actor_recovery=bool(CONFIG.get('native_actor_recovery_plan')))
    if CONFIG.get('managed_drift_recovery'):
        from family_update.managed_drift_recovery import check_observed, rollback_metadata
        from family_update.storage import allocated
        review, _ = check_observed(original)
        trusted, _ = rollback_metadata(review)
        allocation += allocated(trusted)
    require_space(R, "Stopped backup and saved-world rehearsal", allocation)
    return original,receipt

def acquire_lease(receipt):
    old = lease_available()
    atomic(R / 'previous-maintenance.json', old)
    atomic(LEASE, {'state':'active','owner':OWNER,'candidate':str(R),'created_at':now(),'authorization_source':str(AUTHORIZATION),'authorization_sha256':sha(str(AUTHORIZATION)),'versions':versions(receipt),'candidate_receipt_sha256':sha(C/'family-receipt.json')})
    assert_lease()

def finalize_receipt():
    raw=read(C/'family-receipt.json'); digest=sha(C/'family-receipt.json')
    from family_update.workflow import verify_native
    saved=verify_native(verified_candidate=raw)
    reports=['build-evidence.json','static-evidence.json','compatibility-report.json','saved-world-report.json','production-before/backup-receipt.json','handoff-authorization.json']
    if not CONFIG.get('fresh_world'):
        reports.append('saved-world-container-inventories.json')
    if saved.get('test_only_overlays'):
        # verify_native authenticated this one fixed observer, its original
        # logs, both native phase reports and exact closed-world restoration.
        reports.extend(overlay['evidence']['path'] for overlay in saved['test_only_overlays'])
        reports.extend(['fishing-native-observer-first.json','fishing-native-observer-restart.json',saved['test_only_overlay_removal']['path']])
    if CONFIG.get('native_storage_reanchor_plan'):
        from family_update.native_storage_reanchor import verify as verify_native_storage
        storage=read(R/'saved-world-native-storage.json')
        assert storage['ok'] and storage['only_qa_world_loaded'] and storage['client'] is False
        assert storage['plan']==report_ref(Path(CONFIG['native_storage_reanchor_plan']))
        assert storage['uuid']==read(SOURCES['tavern']/'baseline.json')['packs']['BP']['uuid']
        assert [row['phase'] for row in storage['runs']]==['first','restart']
        for row,run in zip(storage['runs'],saved['runs']):
            assert row['original_identity_and_full_item_nbt_retained'] and run['native_storage_reanchor_verified']
            verify_native_storage(storage['before'],row['rows'])
        reports.append('saved-world-native-storage.json')
    if CONFIG.get('extension_validation'):reports.append(str(Path(CONFIG['extension_validation']).resolve()))
    if CONFIG.get('extension_stable_validation'):
        from family_update.stable_author_validation import evidence_paths
        reports.extend(ref['path'] for ref in evidence_paths())
    if CONFIG.get('extension_performance_validation'):
        from family_update.freezer_performance_validation import evidence_paths
        reports.extend(map(str,evidence_paths()))
    if CONFIG.get('extension_hud_validation') and not CONFIG.get('extension_performance_validation'):
        from family_update.explicit_hud_validation import evidence_paths
        reports.extend(map(str,evidence_paths()))
    if CONFIG.get('extension_cache_validation'):
        reports.extend([str(Path(CONFIG['extension_cache_validation']).resolve()), 'cookery-cache-static-validation.json', 'cookery-cache-native-validation.json'])
        cache_static=read(R/'cookery-cache-static-validation.json')
        reports.append(cache_static['differential']['path'])
        if cache_static.get('guide_differential'):reports.append(cache_static['guide_differential']['path'])
    if CONFIG.get('container_recovery_plan'):reports.append('saved-world-container-recovery.json')
    if CONFIG.get('native_actor_recovery_plan'):
        from native_actor_recovery_validation import verify as verify_actor_preservation
        plan=read(Path(CONFIG['native_actor_recovery_plan']))
        recovery=read(R/'saved-world-native-actor-recovery.json')
        preservation=read(R/'saved-world-native-actor-preservation.json')
        assert preservation['plan']==report_ref(Path(CONFIG['native_actor_recovery_plan']))
        assert preservation['ok'] and preservation['client'] is False
        assert [row['phase'] for row in preservation['runs']]==['first','restart']
        previous=None
        for row,run in zip(preservation['runs'],saved['runs']):
            observed_run=row['observation']['native_run']
            assert observed_run and all(run.get(key)==value for key,value in observed_run.items()), 'Actor observations refer to a different native run'
            result=verify_actor_preservation(plan,recovery,row['observation'],previous=previous)
            assert result==row['verification'] and result['ok'] and run['native_actor_recovery_verified']
            previous=row['observation']
        reports.extend(['saved-world-native-actor-recovery.json','saved-world-native-actor-preservation.json'])
    if CONFIG.get('identity_migration'):reports.append('saved-world-identity-migration.json')
    if (R/'saved-world-author-states.json').is_file():reports.append('saved-world-author-states.json')
    if CONFIG.get('startup_reconciliation'):reports.append('startup-reconciliation-check.json')
    if CONFIG.get('translation_reconciliation'):reports.append('translation-reconciliation-check.json')
    if CONFIG.get('preserved_reconciliation'):reports.append('preserved-reconciliation-check.json')
    if CONFIG.get('preserved_additions'):reports.append('preserved-additions-check.json')
    if CONFIG.get('managed_drift_recovery'):
        from family_update.managed_drift_recovery import load_review
        review, binding = load_review()
        reports.extend([binding['path'], 'trusted-pack-rollback.json', 'deployment-initial-state.json'])
        reports.extend(str(EXTENSION / row['path']) for row in review['proofs'])
        if review.get('allow_initially_stopped'):
            reports.append(str(EXTENSION / review['stopped_server_review']['evidence']['path']))
    if CONFIG.get('normal_idle_update'):
        reports.extend([CONFIG['normal_idle_update'], 'deployment-initial-state.json'])
    elif CONFIG.get('fresh_world'):
        reports.append('deployment-initial-state.json')
    if CONFIG.get('prospective_preserved_inputs'):
        reports.append('prospective-preserved-inputs-check.json')
        prospective=read(R/'prospective-preserved-inputs-check.json')
        from family_update.preserved_hud_inputs import is_profile
        if is_profile(prospective):
            reports.extend(['hud-coexistence-native-validation.json', prospective['review']['path'], prospective['recipe']['path'], prospective['source_validation']['path'], prospective['hud_differential']['path']])
        from family_update.preserved_ribbits_inputs import is_profile as is_ribbits
        if is_ribbits(prospective):
            reports.extend(['ribbits-startup-native-validation.json', prospective['review']['path'], prospective['recipe']['path'], prospective['source_validation']['path'], prospective['differential']['path']])
        from family_update.preserved_client_assets_inputs import is_profile as is_client_assets, NATIVE as client_assets_native
        if is_client_assets(prospective):
            reports.extend([client_assets_native, prospective['review']['path'], prospective['recipe']['path'], prospective['source_validation']['path'], prospective['differential']['path'], prospective['source_log']['path']])
        from family_update.preserved_saturation_inputs import is_profile as is_saturation
        if is_saturation(prospective):
            reports.extend(['saturation-scheduling-native-validation.json', prospective['review']['path'], prospective['recipe']['path'], prospective['source_validation']['path'], prospective['source_log']['path'], prospective['source_diagnosis']['path'], prospective['author_file_boundary']['path']])
    raw['acceptance']={'static':True,'bds':True,'client':False,'saved_world_migration':not bool(CONFIG.get('fresh_world'))}
    if CONFIG.get('fresh_world'):
        raw['acceptance'].update(fresh_world_initialization=True, world_persistence=True)
        raw['world_initialization']={'kind':'fresh_world', 'level_name':CONFIG['fresh_world']['level_name'],
                                     'properties':fresh_world_properties(), 'native_report':report_ref(R/'saved-world-report.json')}
    raw['production_ready']=False
    raw['assembled_receipt']={'path':str(C/'family-receipt.json'),'sha256':digest}
    raw['evidence']={'reports':[report_ref(p) for p in dict.fromkeys((R/p).resolve() for p in reports)],'client_acceptance':f'Deferred for this exact candidate under the continuing user instruction in {AUTHORIZATION}; no human client pass claimed.'}
    reviewed=R/'reviewed-family-receipt.json'
    assert not reviewed.exists(), 'Do not overwrite a previous reviewed candidate'
    atomic(reviewed,raw); audit_candidate(C,raw)
    return raw

def installation_selection(receipt,original):
    """Reviewed future preserved inputs join the same install/rollback transaction."""
    if CONFIG.get('extension_stable_validation'):
        from family_update.stable_author_validation import verify_installation
        verify_installation(receipt)
    if CONFIG.get('extension_performance_validation'):
        from family_update.freezer_performance_validation import verify_installation
        verify_installation(receipt)
    if CONFIG.get('extension_hud_validation') and not CONFIG.get('extension_performance_validation'):
        from family_update.explicit_hud_validation import verify_installation
        verify_installation(receipt)
    prospective={}
    if CONFIG.get('prospective_preserved_inputs'):
        from family_update.prospective_preserved_inputs import verify_candidate
        proof=read(R/'prospective-preserved-inputs-check.json')
        assert proof['review']==report_ref(Path(CONFIG['prospective_preserved_inputs'])), 'Prospective review changed before installation'
        verify_candidate(receipt,proof)
        prospective={p['uuid']:p for p in proof['packs'].values()}
        from family_update.preserved_hud_inputs import is_profile, PACKS
        from family_update import preserved_ribbits_inputs as ribbits
        from family_update import preserved_client_assets_inputs as client_assets
        from family_update import preserved_saturation_inputs as saturation
        from family_update import stable_author_validation as stable
        if is_profile(proof):
            assert len(prospective)==5 and set(prospective)=={row[0] for row in PACKS.values()}, 'Complete five HUD outputs required'
            native=read(R/'hud-coexistence-native-validation.json')
            assert native['candidate_receipt_sha256']==sha(C/'family-receipt.json') and native['version']==[1,0,34] and native['source']==proof['hud_differential'], 'HUD native binding differs from this candidate'
            assert native['source_commit']==proof['source_commit'] and native['source_tree_oid']==proof['current_source_tree_oid'], 'HUD native source changed'
            assert native['fresh_native']==report_ref(R/'saved-world-report.json'), 'HUD native evidence changed'
            recipe=read(Path(proof['recipe']['path']))
            expected={name:{'uuid':row[0],'side':row[1],'version':row[3],'files':recipe['output_hashes'][name]} for name,row in PACKS.items()}
            assert native['packs']==expected, 'HUD native outputs differ from all five current variants'
            assert native['native_loading'] is True and native['saved_world_migration'] is True and native['client'] is False and native['production_ready'] is False
        elif ribbits.is_profile(proof):
            ribbits.verify_installation(receipt,proof)
        elif client_assets.is_profile(proof):
            assert len(prospective)==4 and set(prospective)=={row[0] for row in client_assets.PACKS.values()}
            client_assets.verify_installation(receipt,proof)
        elif saturation.is_profile(proof):
            assert len(prospective)==2 and set(prospective)=={row[0] for row in saturation.PACKS.values()}
            saturation.verify_installation(receipt,proof)
        elif stable.is_preserved_profile(proof):
            assert len(prospective)==2 and set(prospective)==set(stable.SAT_UUIDS.values())
            stable.verify_installation(receipt)
        else:
            assert len(prospective)==4, 'Complete prospective pairs required'
    prior={p['uuid']:p for p in original['packs']}
    assert len(prior)==len(original['packs']), 'Original inventory duplicates an identity'
    relocations={}
    local_targets=set()
    if CONFIG.get('managed_drift_recovery'):
        from family_update.managed_drift_recovery import global_relocations,verify_local_target
        relocations=global_relocations(original)
        local_targets=verify_local_target(receipt,original)
        assert not local_targets & set(prospective), 'A local repair cannot also use another prospective producer'
    family=[];unchanged=[]
    for p in receipt['packs']:
        if p['source']['owner']!='preserved':family.append(p);continue
        old=prior.get(p['uuid']);assert old and old['side']==p['side'], 'Preserved identity or side changed'
        assert hashes(old['path'])==old['files'], 'Installed preserved pack drifted from its captured original'
        if p['uuid'] in prospective or p['uuid'] in relocations or p['uuid'] in local_targets:
            if p['uuid'] in relocations and p['uuid'] not in local_targets:
                assert p['files']==old['files'] and p['version']==old['version'], 'Relocation cannot alter existing global input'
            family.append(p)
        else:
            assert p['files']==old['files'] and p['version']==old['version'], 'Unreviewed preserved pack changed'
            unchanged.append(p)
    assert set(prospective)<={p['uuid'] for p in family}, 'Prospective pair omitted from installation'
    assert set(relocations)<={p['uuid'] for p in family}, 'Reviewed global pair omitted from installation'
    assert local_targets<={p['uuid'] for p in family}, 'Reviewed local pair omitted from installation'
    return family,unchanged

def installation_sources(family,original,migration,additions=None):
    """Resolve every retired header before policy, staging or package moves."""
    from family_update.identity_migration import plan_swaps
    swaps=plan_swaps(migration) if migration else []
    reverse={row['new_uuid']:row['old_uuid'] for row in swaps}
    assert len(reverse)==len(swaps), 'Migration duplicates a replacement identity'
    prior={p['uuid']:p for p in original['packs']}
    assert len(prior)==len(original['packs']), 'Original inventory duplicates an identity'
    additions=set(additions or [])
    targets=set();sources=set();paths=set();resolved=[];seen_additions=set()
    for pack in family:
        uid=pack['uuid'];old_uuid=reverse.get(uid,uid)
        assert uid not in targets, 'Installation duplicates a target identity'
        targets.add(uid)
        if uid in additions:
            assert old_uuid==uid and uid not in prior, 'Addition overlaps a retired source'
            seen_additions.add(uid)
            continue
        assert old_uuid in prior, 'Installation source is missing from original inventory: '+old_uuid
        old=prior[old_uuid];path=str(Path(old['path']).resolve())
        assert old['side']==pack['side'], 'Installation source side differs from target'
        assert old_uuid not in sources and path not in paths, 'Installation reuses an original source'
        sources.add(old_uuid);paths.add(path);resolved.append(old)
    assert seen_additions==additions, 'Reviewed addition is absent from installation'
    return resolved

def prepare_admission(receipt,original):
    policy=read(Q/'senluo-policy.json')
    approved=R/'reviewed-family-receipt.json'
    if CONFIG.get('fresh_world') and CONFIG.get('extension_stable_validation'):
        from family_update.stable_author_validation import verify_installation
        verify_installation(receipt)
    family = receipt['packs'] if CONFIG.get('fresh_world') else installation_selection(receipt,original)[0]
    from family_update.identity_migration import candidate_plan
    migration=candidate_plan(receipt,original)
    additions=None
    if CONFIG.get('managed_drift_recovery'):
        from family_update.managed_drift_recovery import validate_target
        additions=validate_target(receipt,original,migration)
    sources=[] if CONFIG.get('fresh_world') else installation_sources(family,original,migration,additions)
    policy['approved_receipt']=str(approved)
    policy['deferred_client_acceptance']={'source':'explicit_user_instruction','instruction':read(R/'handoff-authorization.json')['instruction'],'recorded_at':now(),'receipt_sha256':sha(approved),'authorization_source':str(AUTHORIZATION),'authorization_sha256':sha(str(AUTHORIZATION))}
    policy['managed_uuids']=sorted(set(policy['managed_uuids'])|{p['uuid'] for p in family})
    policy['upstream_lock_sha256']=sha(T/'family/upstream.lock.json')
    policy['reviewed_targets']=[{'name':name,'canonical_path':str(SOURCES[name]),'commit':row['commit'],'tree':row['tree']} for name,row in read(R/'build-evidence.json')['sources'].items() if name in SOURCES]
    note = 'Canonical merged sources; static, clean fresh-world initialization and same-world save/restart; old world retained for rollback, no migration claimed.' if CONFIG.get('fresh_world') else 'Canonical merged sources; complete static, native BDS and fresh stopped-world rehearsal; human client remains pending.'
    policy['latest_observed_deployment']={'path':str(approved),'status':'reviewed_full_family_for_live_development','recorded_at':now(),'note':note}
    atomic(R/'admission-policy.json',policy)
    incoming=[{'uuid':p['uuid'],'version':p['version'],'path':str(C/(p['side']+'_packs')/p['uuid'])} for p in receipt['packs']]
    G['validate_incoming'](incoming,R/'admission-policy.json')
    atomic(R/'admission-report.json',{'ok':True,'candidate_receipt_sha256':sha(C/'family-receipt.json'),'reviewed_receipt_sha256':sha(approved),'complete_packs':len(incoming),'client':False,'production_ready':False,'authorization':report_ref(R/'handoff-authorization.json')})
    return policy,incoming,family,sources

def restore_packs(original,retired,installed):
    if CONFIG.get('managed_drift_recovery'):
        from family_update.managed_drift_recovery import restore
        return restore(original,retired,installed)
    for dest in installed:
        if dest.exists(): shutil.rmtree(dest)
    for src,dest in reversed(retired):
        if src.exists(): os.replace(src,dest)
    for side,refs in original['refs'].items(): atomic(W/('world_'+side+'_packs.json'),refs)
    shutil.copy2(R/'production-before/senluo-policy.json',Q/'senluo-policy.json')
    check_live_against_policy(original)

def verify_original_before_restart(original):
    if CONFIG.get('managed_drift_recovery'):
        from family_update.managed_drift_recovery import verify_restored
        return verify_restored(original)
    assert live_inventory()==original, 'Original complete pack inventory/order not restored; do not start'
    assert sha(Q/'senluo-policy.json')==sha(R/'production-before/senluo-policy.json'), 'Original policy not restored; do not start'

def recover_after_failure(original,changed,retired,installed,rollback_failed=False):
    """Only restart a verified original stack; persist failed recovery honestly."""
    phase='inspect_failure'
    try:
        assert_lease()
        from family_update.world_experiments import adoption_recorded
        if adoption_recorded():
            phase='retain_stopped_after_world_experiment_adoption'
            if summary()['status']!='STOPPED':action('stop')
            assert summary()['status']=='STOPPED', 'World feature migration must remain stopped after a failed deployment'
            raise RecoveryRequired('Rehearsed world experiment adoption began; retain the compatible candidate and newest save stopped. The original complete backup remains available for reviewed recovery.')
        if retain_stopped_on_failure():
            phase='retain_stopped_without_package_or_database_restore'
            if summary()['status']!='STOPPED': action('stop')
            assert summary()['status']=='STOPPED', 'Failed stopped-state update must remain stopped'
            raise RecoveryRequired('The reviewed failure policy retains current packages, displaced inputs and the newest database for operator recovery; no rollback runtime may start')
        if any((R/name).exists() for name in ['production-container-recovery.json','production-identity-migration.json','production-native-actor-recovery.json']):
            if summary()['status']!='STOPPED':action('stop')
            assert summary()['status']=='STOPPED', 'Recovered containers must remain stopped after a failed deployment'
            raise RecoveryRequired('Migrated owners or recovered inventories require the compatible runtime; retain stopped state instead of restarting an incompatible rollback')
        if rollback_failed:
            raise RecoveryRequired('The installation rollback failed; operator recovery is required before any restart')
        if changed or CONFIG.get('managed_drift_recovery'):
            phase='stop_candidate'
            if summary()['status']!='STOPPED': action('stop')
            assert summary()['status']=='STOPPED', 'Candidate must stop before rollback'
            phase='restore_original_packs'
            restore_packs(original,retired,installed)
        phase='verify_complete_original_stack'
        verify_original_before_restart(original)
        if CONFIG.get('managed_drift_recovery'):
            from family_update.managed_drift_recovery import restart_original_allowed
            if not restart_original_allowed():
                raise RecoveryRequired('The server was initially stopped or its owner evidence is incomplete; retain stopped state and active lease after trusted pack-only recovery')
        phase='restart_verified_original_stack'
        if summary()['status']=='STOPPED': action('start')
        assert summary()['status']=='RUNNING', 'Original stack restart is not confirmed'
        state='trusted_approved_stack_running_after_failure' if CONFIG.get('managed_drift_recovery') else 'original_stack_running_after_failure'
        atomic(R/'deployment-recovery.json',{'state':state,'recorded_at':now(),'original_inventory_verified':not bool(CONFIG.get('managed_drift_recovery')),'trusted_approved_inventory_verified':bool(CONFIG.get('managed_drift_recovery')),'original_policy_verified':True,'save_database_restored':False,'original_drift_approved':False,'client':False,'production_ready':False})
        lease=read(LEASE); lease.update(state='failed',failed_at=now(),status=state); atomic(LEASE,lease)
        return True
    except BaseException as error:
        try: current_status=summary()['status']
        except BaseException: current_status='UNKNOWN'
        atomic(R/'deployment-recovery.json',{'state':'needs_operator_recovery','recorded_at':now(),'phase':phase,'error':str(error),'server_status':current_status,'restart_attempted':phase=='restart_verified_original_stack','save_database_restored':False,'client':False,'production_ready':False})
        # Do not overwrite another maintenance owner if the lease was stolen.
        assert_lease()
        lease=read(LEASE); lease.update(state='active',failure_at=now(),status='needs_operator_recovery',recovery_report=str(R/'deployment-recovery.json')); atomic(LEASE,lease)
        return False

def retain_failed_installation(original,retired,installed,install_error):
    """Persist partial renames before refusing automatic package rollback."""
    if not retain_stopped_on_failure():
        return
    assert_lease()
    assert summary()['status']=='STOPPED', 'Installation recovery must remain stopped'
    atomic(R/'rollback-map.json',{'retired':[[str(a),str(b)] for a,b in retired],'installed':[str(p) for p in installed],'original_inventory':str(R/'production-before/inventory.json'),'backup':str(R/'production-snapshot'),'incomplete_installation':True,'automatic_package_restore':False})
    atomic(R/'deployment-result.json',{'state':'needs_operator_recovery','stage':'installation_retained_stopped','install_error':str(install_error),'automatic_package_restore':False,'save_database_restored':False,'client':False,'production_ready':False})
    raise RecoveryRequired('Installation failed; preserve partial package moves and the newest database without installing or starting a rollback runtime') from install_error

def adopt_native_actor_recovery():
    """Reapply the rehearsed pointer transaction to the latest stopped save."""
    assert_lease();assert summary()['status']=='STOPPED'
    assert not CONFIG.get('container_recovery_plan') and not CONFIG.get('identity_migration')
    from native_actor_recovery import recover_world as recover_actors,verify_world as verify_actors
    fresh=R/'production-snapshot'
    assert hashes(W/'db')==hashes(fresh/'db'), 'Actor recovery must use the latest stopped database'
    stage_root=R/'native-actor-recovery-stage';stage_root.mkdir()
    stage=stage_root/'world';stage.mkdir();shutil.copytree(W/'db',stage/'db')
    shutil.copy2(W/'world_behavior_packs.json',stage/'world_behavior_packs.json')
    plan=read(Path(CONFIG['native_actor_recovery_plan']))
    restored=recover_actors(stage,plan,stage_root=R,source_world=W)
    assert restored==read(R/'saved-world-native-actor-recovery.json'), 'Actor restoration differs from the rehearsed exact transaction'
    verify_actors(stage,plan,restored,stage_root=R,source_world=W)
    # Publish the failure fence before either rename. A partial move must keep
    # the server stopped with all original/staged database files retained.
    assert not (R/'production-native-actor-recovery.json').exists()
    atomic(R/'production-native-actor-recovery.json',restored)
    os.replace(W/'db',R/'production-original-db');os.replace(stage/'db',W/'db')

def install_fresh_world(receipt, original):
    from family_update.native_common import world_data_hashes
    from family_update.storage import allocated, assert_idle, require_space
    source = R / 'saved-world-engine/worlds' / CONFIG['fresh_world']['level_name']
    target = B / 'worlds' / CONFIG['fresh_world']['level_name']
    native = read(R / 'saved-world-report.json')
    assert not target.exists(), 'Never overwrite a world during fresh delivery'
    assert_idle(source.parent.parent)
    assert world_data_hashes(source) == native['world_files'], 'Prepared world changed after native validation'
    audit_candidate(source, receipt)
    policy, incoming, family, _ = prepare_admission(receipt, original)
    rollback = R / 'production-rollback'; rollback.mkdir()
    retired = []; installed = []
    try:
        atomic(Q / 'senluo-policy.json', policy)
        runpy.run_path(str(Q / 'policy.py'))['validate_incoming'](incoming, {p['uuid'] for p in original['packs']}, True)
        for old in original['packs']:
            path = Path(old['path'])
            if path.parent != B / (old['side'] + '_packs'):
                continue
            parked = rollback / (old['side'] + '_packs') / path.name
            parked.parent.mkdir(parents=True, exist_ok=True)
            assert hashes(path) == old['files'] and not parked.exists(), 'Old global rollback input changed'
            os.replace(path, parked); retired.append((parked, path))
        # A cross-filesystem move temporarily needs one actual new-world copy.
        require_space(target.parent, 'Fresh world delivery', allocated(source))
        shutil.move(str(source), str(target)); installed.append(target)
        assert world_data_hashes(target) == native['world_files'], 'Fresh world delivery bytes differ'
        audit_candidate(target, receipt)
        properties = fresh_world_properties()
        response = api('/api/server/' + quote(SERVER, safe='') + '/properties/set',
                       {'properties': properties}, 'POST')
        atomic(R / 'fresh-world-properties-response.json', response)
        assert response.get('status') == 'success' and response.get('server_name') == SERVER, 'World properties update was not confirmed'
        binding = verify_server_binding()
        observed = api('/api/server/' + quote(SERVER, safe='') + '/properties/get')['properties']
        assert all(str(observed.get(key)) == value for key, value in properties.items()), 'New world properties were not applied'
        assert summary()['status'] == 'STOPPED', 'World selection must not start the server'
        policy['installed']={'status':'pending_client_acceptance','receipt':str(R/'reviewed-family-receipt.json'),
                             'receipt_sha256':sha(R/'reviewed-family-receipt.json'),'installed_at':now(),
                             'packs':[{**p,'directory':p['uuid']} for p in family],
                             'refs':{side:read(target/('world_'+side+'_packs.json')) for side in ['behavior','resource']}}
        policy['hold_reason']='Fresh initialization and same-world persistence passed; no old-world migration or human client acceptance claimed.'
        atomic(Q/'senluo-policy.json',policy)
        drift=G['audit'](target,policy); assert drift['ok']; atomic(R/'production-drift.json',drift)
        valid=runpy.run_path(str(Q/'policy.py'))['validate_world'](target); assert valid['ok']; atomic(R/'production-quality.json',valid)
        atomic(R/'rollback-map.json',{'retired':[[str(a),str(b)] for a,b in retired],'installed':[str(p) for p in installed],
                                     'original_inventory':str(R/'production-before/inventory.json'),'backup':str(R/'production-snapshot'),
                                     'original_world':str(W),'new_world':str(target),'original_properties':str(R/'production-before/server.properties')})
        atomic(R/'deployment-result.json',{'schema':1,'state':'installed_stopped','versions':versions(receipt),
                'family_packs':len(family),'preserved_packs':0,'receipt_sha256':sha(R/'reviewed-family-receipt.json'),
                'assembled_receipt_sha256':sha(C/'family-receipt.json'),'guard_admission_passed':True,
                'fresh_world':str(target),'active_world_binding':binding,'original_database_untouched_during_install':True,
                'original_level_dat_untouched_during_install':True,'rollback':str(rollback),
                'client':False,'production_ready':False})
        return retired, installed
    except BaseException as error:
        retain_failed_installation(original, retired, installed, error)


def install(receipt,original):
    assert_lease(); assert summary()['status']=='STOPPED'; verify_predeploy()
    verify_server_binding()
    verify_candidate_sources()
    if CONFIG.get('fresh_world'):
        return install_fresh_world(receipt, original)
    policy,incoming,family,sources=prepare_admission(receipt,original)
    prior={p['uuid']:p for p in original['packs']}
    foreign={p['uuid']:p for p in receipt['packs'] if p['source']['owner']=='preserved' and p['uuid'] not in {row['uuid'] for row in family}}
    index=read(Q.parent/'addon_localizations/index.json')
    assert not any(p.get('uuid') in policy['owned_uuids'] for p in index.get(SERVER,[])), 'Unexpected owned localization replacement'
    staged,rollback=R/'production-staged',R/'production-rollback'; staged.mkdir(); rollback.mkdir()
    for p in family: shutil.copytree(C/(p['side']+'_packs')/p['uuid'],staged/(p['side']+'_packs')/p['uuid'])
    db_before=hashes(W/'db'); level_before=sha(W/'level.dat'); retired=[]; installed=[]
    try:
        atomic(Q/'senluo-policy.json',policy)
        runpy.run_path(str(Q/'policy.py'))['validate_incoming'](incoming,set(prior),True)
        relocations={}
        if CONFIG.get('managed_drift_recovery'):
            from family_update.managed_drift_recovery import global_relocations
            relocations=global_relocations(original)
        for old in sources:
            source=Path(old['path']); target=rollback/(old['side']+'_packs')/source.name
            if CONFIG.get('managed_drift_recovery'):
                from family_update.managed_drift_recovery import retirement_target
                target=retirement_target(old,rollback,relocations)
            target.parent.mkdir(parents=True,exist_ok=True)
            assert not target.exists(), 'Preserve previously displaced pack bytes'
            os.replace(source,target); retired.append((target,source))
        for p in family:
            source=staged/(p['side']+'_packs')/p['uuid']; target=W/(p['side']+'_packs')/p['uuid']; assert not target.exists(); os.replace(source,target); installed.append(target)
        for side in ['behavior','resource']: shutil.copy2(C/('world_'+side+'_packs.json'),W/('world_'+side+'_packs.json'))
        assert hashes(W/'db')==db_before and sha(W/'level.dat')==level_before, 'Pack installation must not mutate live save'
        if CONFIG.get('container_recovery_plan'):
            from container_recovery import recover_world
            fresh=R/'production-snapshot'
            assert hashes(W/'db')==hashes(fresh/'db'), 'Recovery must use the latest stopped database'
            stage=R/'container-recovery-stage';stage.mkdir();shutil.copytree(W/'db',stage/'db')
            restored=recover_world(stage,read(Path(CONFIG['container_recovery_plan'])))
            assert restored==read(R/'saved-world-container-recovery.json'), 'Live restoration differs from rehearsed records'
            atomic(R/'production-container-recovery.json',restored)
            os.replace(W/'db',R/'production-original-db');os.replace(stage/'db',W/'db')
        if CONFIG.get('native_actor_recovery_plan'):
            adopt_native_actor_recovery()
        from family_update.identity_migration import adopt_world
        adopt_world(receipt,original)
        from family_update.world_experiments import adopt as adopt_experiments, required as required_experiments
        experiment_transition=adopt_experiments(read(R/'saved-world-report.json')) if required_experiments() else None
        policy['installed']={'status':'pending_client_acceptance','receipt':str(R/'reviewed-family-receipt.json'),'receipt_sha256':sha(R/'reviewed-family-receipt.json'),'installed_at':now(),'packs':[{**p,'directory':p['uuid']} for p in family],'refs':{side:[p for p in read(W/('world_'+side+'_packs.json')) if p['pack_id'] in policy['managed_uuids']] for side in ['behavior','resource']}}
        policy['hold_reason']='依使用者持續授權更新 live 供開發效果真人測試；完整家族 static、BDS、停服一致存檔驗證已通過。client=false，production_ready=false，仍需真人聲畫與玩法驗收。'
        atomic(Q/'senluo-policy.json',policy)
        drift=G['audit'](W,policy); assert drift['ok']; atomic(R/'production-drift.json',drift)
        valid=runpy.run_path(str(Q/'policy.py'))['validate_world'](W); assert valid['ok']; atomic(R/'production-quality.json',valid)
        atomic(R/'rollback-map.json',{'retired':[[str(a),str(b)] for a,b in retired],'installed':[str(p) for p in installed],'original_inventory':str(R/'production-before/inventory.json'),'backup':str(R/'production-snapshot')})
        atomic(R/'deployment-result.json',{'schema':1,'state':'installed_stopped','versions':versions(receipt),'family_packs':len(family),'preserved_packs':len(foreign),'receipt_sha256':sha(R/'reviewed-family-receipt.json'),'assembled_receipt_sha256':sha(C/'family-receipt.json'),'guard_admission_passed':True,'original_database_untouched_during_install':not bool(CONFIG.get('container_recovery_plan') or CONFIG.get('identity_migration') or CONFIG.get('native_actor_recovery_plan')),'reviewed_identity_migration':bool(CONFIG.get('identity_migration')),'reviewed_container_recovery':bool(CONFIG.get('container_recovery_plan')),'reviewed_native_actor_recovery':bool(CONFIG.get('native_actor_recovery_plan')),'world_experiments':experiment_transition,'original_level_dat_untouched_during_install':not bool(experiment_transition and experiment_transition['changed_flags']),'rollback':str(rollback),'client':False,'production_ready':False})
        return retired,installed
    except BaseException as install_error:
        from family_update.world_experiments import adoption_recorded
        if adoption_recorded():
            raise RecoveryRequired('World feature adoption began; keep the compatible candidate and newest metadata stopped for recovery') from install_error
        retain_failed_installation(original,retired,installed,install_error)
        if any((R/name).exists() for name in ['production-container-recovery.json','production-identity-migration.json','production-native-actor-recovery.json']):
            raise RecoveryRequired('Container recovery has begun; keep the compatible candidate stopped for recovery') from install_error
        try:
            restore_packs(original,retired,installed)
        except BaseException as rollback_error:
            try:
                atomic(R/'rollback-map.json',{'retired':[[str(a),str(b)] for a,b in retired],'installed':[str(p) for p in installed],'original_inventory':str(R/'production-before/inventory.json'),'backup':str(R/'production-snapshot'),'incomplete_rollback':True})
                atomic(R/'deployment-result.json',{'state':'needs_operator_recovery','stage':'installation_rollback','install_error':str(install_error),'rollback_error':str(rollback_error),'client':False,'production_ready':False})
            finally:
                # Even a full disk while recording the rollback failure cannot
                # erase the signal which prohibits an automatic restart.
                raise RecoveryRequired('Installation rollback failed: '+str(rollback_error)) from rollback_error
        atomic(R/'deployment-result.json',{'state':'trusted_packs_restored_before_restart' if CONFIG.get('managed_drift_recovery') else 'rolled_back_before_restart','save_database_restored':False,'client':False,'production_ready':False})
        raise

def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--execute',action='store_true',help='Perform already-authorized live development deployment after review')
    args=parser.parse_args(argv)
    if not args.execute:
        print(json.dumps({'execute':False,'lease':read(LEASE) if LEASE.exists() else {},'live':summary(),'candidate':str(C),'fresh_backup':str(R/'production-snapshot'),'required_reports':[str(R/p) for p in ['production-before/inventory.json','build-evidence.json','static-evidence.json','compatibility-report.json']],'native_rehearsal':'Fresh stopped-world first/start and restart during deployment','authorization_source':str(AUTHORIZATION),'client':False,'production_ready':False},ensure_ascii=False,indent=2)); return
    # A separate advisory lock protects cooperating helpers; the visible lease
    # also protects against other existing deployment scripts and must be free.
    with open(str(LOCK), 'a+') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        lease_available(); original,receipt=preflight()
        from family_update.workflow import no_update_needed
        if not CONFIG.get('fresh_world') and no_update_needed(receipt, original):
            print('NO_RUNTIME_CHANGES: full live bytes and order already match; no restart', flush=True)
            return {'state': 'no_runtime_changes', 'live_mutated': False, 'client': False}
        for path in [R/name for name in ['previous-maintenance.json','handoff-authorization.json','live-authorization-AGENTS.md','reviewed-family-receipt.json','admission-policy.json','admission-report.json','deployment-result.json','deployment-recovery.json','rollback-map.json','production-snapshot','production-staged','production-rollback','saved-world-engine','saved-world-report.json','deployment-initial-state.json']]:
            assert not path.exists(), 'Existing report or deployment state must be preserved: ' + str(path)
        if CONFIG.get('managed_drift_recovery'):
            for name in ['trusted-pack-rollback','trusted-pack-rollback.json','managed-drift-displaced','managed-drift-pack-recovery.json','deployment-initial-state.json','observed-global-displaced']:
                assert not (R/name).exists(), 'Preserve previous drift recovery state: ' + name
        acquire_lease(receipt)
        changed=False; retired=[]; installed=[]
        try:
            if CONFIG.get('fresh_world') or CONFIG.get('normal_idle_update'):
                from family_update.normal_idle_update import record_initial_status
                record_initial_status()
            elif CONFIG.get('managed_drift_recovery'):
                from family_update.managed_drift_recovery import record_initial_status
                record_initial_status()
            verify_predeploy()
            instruction=Path(str(AUTHORIZATION)).read_text()
            shutil.copy2(str(AUTHORIZATION),R/'live-authorization-AGENTS.md')
            atomic(R/'handoff-authorization.json',{'source':'explicit_user_instruction','instruction':instruction,'recorded_at':now(),'source_file':str(AUTHORIZATION),'source_sha256':sha(str(AUTHORIZATION)),'snapshot':report_ref(R/'live-authorization-AGENTS.md'),'scope':'Continuing authorization for per-candidate live development updates after merged PR/static/BDS/saved-world gates; human client acceptance remains pending.'})
            if CONFIG.get('managed_drift_recovery'):
                from family_update.managed_drift_recovery import prepare_rollback
                prepare_rollback(original)
            print(f'Preparing {SERVER} for a fresh stopped backup and saved-world rehearsal',flush=True)
            if not (CONFIG.get('fresh_world') or CONFIG.get('managed_drift_recovery') or CONFIG.get('normal_idle_update')) or summary()['status']!='STOPPED':
                action('stop')
            assert summary()['status']=='STOPPED'; verify_predeploy()
            # Admit the larger native ceiling only after normal production stop.
            from family_update.memory_budget import require as require_memory
            require_memory('saved-world')
            snapshot=R/'production-snapshot'; assert not snapshot.exists(); shutil.copytree(W,snapshot)
            before=hashes(W); copied=hashes(snapshot); assert before==copied, 'Stopped snapshot copy mismatch'
            atomic(R/'production-before/backup-receipt.json',{'recorded_at':now(),'world':str(W),'consistent_stopped_snapshot':str(snapshot),'files':copied,'packs':len(original['packs']),'status':'consistent_stopped_backup','lease_owner':OWNER,'level_dat_sha256':sha(W/'level.dat'),'live_status':'STOPPED'})
            command([PY,ENTRY,'--config',CONFIG_PATH,'saved-world','--execute'],R/'saved-world-summary.log')
            receipt=finalize_receipt(); retired,installed=install(receipt,original); changed=True
            shutil.copy2(B/'server_output.txt',R/'production-before/server-output-before-start.txt')
            # Release the native ceiling and its file cache before production
            # starts competing for memory. The child verifier rechecks this cap.
            require_memory('verify-live')
            action('start')
            command([PY,ENTRY,'--config',CONFIG_PATH,'verify-live','--execute'],R/'poststart-summary.log')
            result=read(R/'deployment-result.json'); result.update(state='deployed_running',poststart_report=str(R/'poststart-verification.json'),completed_at=now()); atomic(R/'deployment-result.json',result)
            lease=read(LEASE); lease.update(state='completed',completed_at=now(),receipt=str(R/'reviewed-family-receipt.json'),status='running_for_user_acceptance'); atomic(LEASE,lease)
            print('LIVE_DEVELOPMENT_DEPLOYED_PENDING_CLIENT',flush=True)
        except BaseException as failure:
            traceback.print_exc()
            try:
                restored=recover_after_failure(original,changed,retired,installed,rollback_failed=isinstance(failure,RecoveryRequired))
                if changed and restored:
                    atomic(R/'deployment-result.json',{'state':'trusted_stack_restored_after_candidate_start' if CONFIG.get('managed_drift_recovery') else 'rolled_back_after_candidate_start','save_database_restored':False,'note':'Verified rollback package inventory and original policy before restart. Newest database retained; stopped backup is available for explicit data recovery.','client':False,'production_ready':False})
            except BaseException:
                traceback.print_exc()
            raise
        finally:
            fcntl.flock(lock,fcntl.LOCK_UN)
    # The live transaction has completed. Cleanup has its own lock and cannot
    # enter this function's recovery path, including on interruption or ENOSPC.
    from family_update.cleanup_copies import after_deployment
    after_deployment()
if __name__=='__main__': main()
