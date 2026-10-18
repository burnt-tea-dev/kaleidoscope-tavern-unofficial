"""Exact P55 source proof and fresh stopped-save binding; historical gates remain.

Only hashes and reviewed contract metadata are public. Original private CI
artifacts bind the implementation, while native/client acceptance stays distinct.
Altered hosts are not clean author archives. This LIVE candidate adopts new
author UUIDs; the private owner version does not invalidate an already cached
clean Cookery162/Orchard101 client pack. Existing precise clean-install/cache
acceptance remains necessary before claiming public rendered usability.
"""
from functools import lru_cache
from pathlib import Path
import hashlib,io,json,subprocess,zipfile
from family_update import common as c
from family_update.cookery_cache_validation import tree
from stable_host_profiles import CATALOG,PROFILES,match_stable_profile,public_profiles,receipt as profile_receipt,validate_stable_source

VERSION=[1,0,55]
REPOSITORY='casama233/senluo-family-integration-private'
REPOSITORY_ID=1406868911
LOGICAL='local/senluo-amw-cuisine'
PROFILE='senluo-stable-author-20261018-p55'
CATALOG_KEY='current_author_p55'
CHECKS={'current-source-api','native-freezer-performance.json','saturation-scheduling-functional.json','hud-coexistence-functional.json','ribbits-startup-functional.json','ribbits-fp-decode-functional.json'}

def selected():
    return c.CONFIG.get('extension_stable_profile')=='current-author-p55'

def digest(raw):return hashlib.sha256(raw).hexdigest()

def local(path,expected=None):
    path=Path(path);assert path.is_file() and not path.is_symlink(),'Current author evidence missing or linked'
    raw=path.read_bytes()
    if expected is not None:assert digest(raw)==expected,'Current author evidence changed'
    return raw

def sibling(path,ref):
    name=ref['name'];assert isinstance(name,str) and Path(name).name==name and name not in ('','.','..'),'Unsafe current source evidence member'
    target=Path(path).parent/name;local(target,ref['sha256']);return target

def committed(relative,expected=None):
    path=c.EXTENSION/relative;raw=local(path,expected)
    assert path.resolve().is_relative_to(c.EXTENSION.resolve()),'Current source escaped owned checkout'
    assert raw==subprocess.check_output(['git','show','HEAD:'+relative],cwd=c.EXTENSION),'Uncommitted current author source'
    return json.loads(raw)

@lru_cache(maxsize=2)
def artifact_members(run_id,artifact_id,source,full_tree):
    from family_update.workflow import gh_json
    from family_update.cookery_cache_validation import private_ci_records
    from family_update.github_reads import api_bytes
    repo=gh_json('repos/'+REPOSITORY)
    assert repo['id']==REPOSITORY_ID and repo['full_name']==REPOSITORY and repo['private'] is True
    run=gh_json(f'repos/{REPOSITORY}/actions/runs/{run_id}')
    assert run['repository']['id']==REPOSITORY_ID and run['status']=='completed' and run['conclusion']=='success'
    assert run['head_sha']==source and run['head_branch']=='main' and run['event'] in ('push','workflow_dispatch')
    assert run['path']=='.github/workflows/canonical.yml'
    assert gh_json(f'repos/{REPOSITORY}/git/commits/{source}')['tree']['sha']==full_tree
    checks,statuses,unavailable=private_ci_records(REPOSITORY,source)
    artifact=gh_json(f'repos/{REPOSITORY}/actions/artifacts/{artifact_id}')
    assert artifact['name']=='current-author-functional' and artifact['expired'] is False
    assert artifact['workflow_run']['id']==run_id and artifact['workflow_run']['head_sha']==source
    raw=api_bytes(f'repos/{REPOSITORY}/actions/artifacts/{artifact_id}/zip')
    assert len(raw)<=32*1024**2 and artifact['digest']=='sha256:'+digest(raw),'Current author original CI artifact changed'
    with zipfile.ZipFile(io.BytesIO(raw)) as archive:
        names=archive.namelist();assert len(names)<=32 and len(names)==len(set(names)) and all(Path(n).name==n for n in names)
        assert sum(i.file_size for i in archive.infolist())<=32*1024**2,'Current author artifact exceeds bounded evidence scope'
        members={name:archive.read(name) for name in names}
    return members,{'run_id':run_id,'artifact_id':artifact_id,'artifact_digest':artifact['digest'],'checks':checks,'statuses':statuses,'unavailable_optional_services':unavailable}

def source_proof():
    from family_update.extension_validation import source_binding
    from family_update.workflow import gh_json
    assert selected() and c.CONFIG.get('extension_stable_validation')
    assert not any(c.CONFIG.get(key) for key in ['extension_validation','extension_cache_validation','extension_hud_validation','extension_performance_validation'])
    path=Path(c.CONFIG['extension_stable_validation']);raw=local(path);proof=json.loads(raw)
    baseline=c.read(c.EXTENSION/'baseline.json');metadata=committed('.repo-target.json')
    assert baseline['repository']==LOGICAL and baseline['version']==VERSION
    assert metadata['repository']==REPOSITORY and metadata['repository_id']==REPOSITORY_ID and metadata['private'] is True
    assert proof['schema']==1 and proof['kind']=='current_author_functional' and proof['profile']==PROFILE
    assert proof['canonical_repository']==REPOSITORY and proof['canonical_repository_id']==REPOSITORY_ID
    assert proof['test_command']==['python','tools/build_current_author_evidence.py'] and proof['test_exit_code']==0
    assert all(proof[key] is False for key in ['client','native_loading','simulated_players','production_ready'])
    binding=source_binding(proof,baseline);assert proof['git_tree']==binding['current_source_tree_oid']
    catalog=CATALOG[CATALOG_KEY];assert catalog['version']==VERSION and catalog['profile']==PROFILE
    assert proof['owned_runtime']['previous_commit']==catalog['previous_commit']
    c.git(c.EXTENSION,'merge-base','--is-ancestor',catalog['previous_commit'],binding['actual_current_source_commit'])
    authors=committed(catalog['authors_path'],catalog['authors_sha256'])
    assert authors['profile']==PROFILE and authors['source_package_version']==VERSION and authors['authors']==catalog['authors']
    pr=gh_json(f'repos/{REPOSITORY}/pulls/{c.CONFIG["extension_stable_pull_request"]}')
    assert pr['merged'] is True and pr['base']['ref']=='main' and pr['head']['repo']['id']==pr['base']['repo']['id']==REPOSITORY_ID
    c.git(c.EXTENSION,'merge-base','--is-ancestor',pr['merge_commit_sha'],binding['actual_current_source_commit'])
    assert c.git(c.EXTENSION,'rev-parse',pr['head']['sha']+'^{tree}')==proof['git_tree'],'Current author PR whole tree differs'
    members,ci=artifact_members(int(c.CONFIG['extension_stable_run_id']),int(c.CONFIG['extension_stable_artifact_id']),proof['source_commit'],proof['git_tree'])
    assert members.get(path.name)==raw,'Current author proof differs from original CI artifact'
    checks=proof['completed_checks'];assert isinstance(checks,list) and {row['name'] for row in checks}==CHECKS and len(checks)==len(CHECKS)
    refs=[proof['test_log'],*[row['log'] for row in checks]]
    expected={path.name,*[ref['name'] for ref in refs]}
    assert set(proof['artifact_members'])==expected==set(members),'Current author artifact inventory differs'
    for ref in refs:
        member=sibling(path,ref);assert member.read_bytes()==members[ref['name']],'Current author CI log bytes differ'
    assert all(row['exit_code']==0 and isinstance(row['command'],list) and row['command'] for row in checks)
    source_api=next(row for row in checks if row['name']=='current-source-api')
    assert source_api['command']==['node','--test','tools/current-author-functional.test.mjs']
    return path,proof,baseline,binding,catalog,ci

def affected_packs(receipt,catalog=None):
    catalog=catalog or CATALOG[CATALOG_KEY]
    uuids={pin[key] for pin in catalog['authors'].values() for key in ['behavior_uuid','resource_uuid']}
    return {p['uuid']:{'side':p['side'],'version':p['version'],'files':tree(p['files'])} for p in receipt['packs'] if p['uuid'] in uuids or p['source'].get('repository')==LOGICAL}

def validate_candidate(receipt,proof,baseline,binding,catalog):
    """Validate every output and the exact ordered chain, not just changed paths."""
    rows={row['uuid']:row for row in receipt['packs']};assert len(rows)==len(receipt['packs'])
    assert {row['uuid'] for row in rows.values() if row['source'].get('repository')==LOGICAL}=={p['uuid'] for p in baseline['packs'].values()},'Current private pair inventory differs'
    owned=proof['owned_runtime'];assert set(owned['files'])=={'BP','RP'}
    previous=json.loads(c.git(c.EXTENSION,'show',catalog['previous_commit']+':baseline.json'))
    for side,definition in baseline['packs'].items():
        pack=rows[definition['uuid']]
        assert pack['source']['owner']=='owned' and pack['source']['repository']==LOGICAL and pack['version']==VERSION
        assert pack['source']['commit']==binding['actual_current_source_commit'] and pack['source']['working_candidate'] is False
        assert pack['files']==owned['files'][side] and tree(pack['files'])==baseline['source_trees'][side]
        assert tree(owned['previous_files'][side])==previous['source_trees'][side]
    changed=sorted('runtime/'+side+'/'+name for side in ['BP','RP'] for name in owned['files'][side].keys()&owned['previous_files'][side].keys() if owned['files'][side][name]!=owned['previous_files'][side][name])
    added=sorted('runtime/'+side+'/'+name for side in ['BP','RP'] for name in owned['files'][side].keys()-owned['previous_files'][side].keys())
    retired=sorted('runtime/'+side+'/'+name for side in ['BP','RP'] for name in owned['previous_files'][side].keys()-owned['files'][side].keys())
    assert changed==owned['exact_changed_paths'],'Current author conservation changed paths differ'
    assert added==owned['added_paths'],'Current author conservation added paths differ'
    assert retired==owned['retired_paths'],'Current author conservation retired paths differ'
    assert set(proof['authors'])==set(proof['resolved_host_files'])==set(catalog['authors'])
    specs={}
    assert set(proof['host_specs'])==set(catalog['host_specs'])
    for name,record in catalog['host_specs'].items():
        spec=committed('runtime/BP/host-extensions/'+name,record['sha256']);profile=match_stable_profile(spec,c.EXTENSION/baseline['runtime']['BP'])
        assert profile==PROFILES[record['profile']] and profile['spec_sha256']==record['declaration_sha256']
        expected={'sha256':record['sha256'],'id':spec['id'],'host_uuid':spec['host_uuid'],'archive_sha256':spec['archive_sha256'],'original_files':spec['original_files'],'patched_files':spec['patched_files'],'copies_hashes':profile['copies']}
        if spec.get('removed_files'):expected['removed_files']=spec['removed_files']
        assert proof['host_specs'][name]==expected,'Current author host proof differs from committed profile'
        specs[spec['id']]=(spec,profile,record['sha256'])
    public=public_profiles()[catalog['public_api_profile']];api=proof['public_api'];g=c.SOURCES['grilling']
    public_path=g/'projects/grilling/gameplay_core/behavior_pack/host-extensions/board-api.json'
    public_spec=c.read(public_path)
    assert c.sha(public_path)==api['spec_sha256']==catalog['public_api_spec_sha256']
    assert match_stable_profile(public_spec)==public
    assert api['repository']=='casama233/kaleidoscope-grilling-unofficial'
    assert api['git_tree']==c.git(g,'rev-parse','HEAD^{tree}')==c.git(g,'rev-parse',api['source_commit']+'^{tree}')
    c.git(g,'merge-base','--is-ancestor',api['source_commit'],c.git(g,'rev-parse','HEAD'))
    for key in ['id','version','host_uuid','archive_sha256','original_files','patched_files']:assert api[key]==public[key]
    assert api['copies_hashes']==public['copies']
    seen=set()
    for key,pin in catalog['authors'].items():
        assert {row['uuid'] for row in rows.values() if row['source'].get('archive_sha256')==pin['sha256']}=={pin['behavior_uuid'],pin['resource_uuid']},'Current author pair inventory differs'
        authored=proof['authors'][key];assert {name:authored[name] for name in pin}==pin
        assert authored['resolved_files']==proof['resolved_host_files'][key]
        for side,label,uid_key in [('BP','behavior','behavior_uuid'),('RP','resource','resource_uuid')]:
            pack=rows[pin[uid_key]];source=pack['source'];extensions=source.get('reviewed_extensions',[])
            assert pack['side']==label and pack['files']==authored['resolved_files'][side]
            assert source['owner']==('upstream_extended' if extensions else 'upstream') and source['archive_sha256']==pin['sha256']
            assert source['project_id']==pin['project_id'] and source['file_id']==pin['file_id']
            expected_version=[1,0,10655] if key=='ChineseFood' else pin['author_version']
            assert pack['version']==expected_version
            current=dict(authored['original_files'][side])
            for index,extension in enumerate(extensions):
                prefix={**source,'owner':'upstream' if index==0 else 'upstream_extended','reviewed_extensions':extensions[:index]}
                if extension['id']==public['id']:
                    declared=public_spec;profile=public;spec_sha=catalog['public_api_spec_sha256'];repository=api['repository'];commit=c.git(g,'rev-parse','HEAD')
                else:
                    assert extension['id'] in specs,'Unexpected current author host extension'
                    declared,profile,spec_sha=specs[extension['id']];repository=LOGICAL;commit=binding['actual_current_source_commit'];seen.add(extension['id'])
                paired=declared.get('kind')=='chinesefood-doll-renderer-cleanup'
                if paired and side=='RP':
                    bp_extensions=rows[pin['behavior_uuid']]['source']['reviewed_extensions']
                    matching=[i for i,row in enumerate(bp_extensions) if row['id']==extension['id']];assert len(matching)==1
                    prefix={**source,'owner':'upstream' if matching[0]==0 else 'upstream_extended','reviewed_extensions':bp_extensions[:matching[0]]}
                validate_stable_source(profile,prefix)
                assert extension['spec_sha256']==spec_sha and extension['repository']==repository and extension['commit']==commit and extension['working_candidate'] is False
                assert extension['original_files']==declared['original_files'] and extension['patched_files']==declared['patched_files']
                assert extension.get('removed_files',{})==declared.get('removed_files',{}),'Current author removal receipt differs'
                if 'version' in declared:assert extension['version']==declared['version']
                else:assert extension['owner_version']==VERSION and extension['local_pack_version']==[1,0,10655]
                copies=profile['copies'];assert extension.get('copies',{})==copies
                for name,value in declared['original_files'].items():
                    if paired:
                        if not name.startswith(side+'/'):continue
                        name=name[3:]
                    assert current.get(name)==value,'Current author ordered hook preimage differs'
                for name,value in declared['patched_files'].items():
                    if paired:
                        if not name.startswith(side+'/'):continue
                        name=name[3:]
                    current[name]=value
                for name,value in declared.get('removed_files',{}).items():
                    assert current.get(name)==value,'Current author removal preimage differs'
                    del current[name]
                for name,record in copies.items():assert name not in current,'Current author helper overwrote existing data';current[name]=record['sha256']
            assert current==pack['files'],'Current author complete output differs from exact hook replay'
            if key in ['Nether','End','PresenceFootsteps','Deco']:assert not extensions and authored['original_files'][side]==pack['files']
    assert seen==set(specs),'Current author host profile omitted'

def verify_static(receipt,prior):
    path,proof,baseline,binding,catalog,ci=source_proof()
    validate_candidate(receipt,proof,baseline,binding,catalog)
    target=c.R/'current-author-static-validation.json'
    c.atomic(target,{'schema':1,'profile':PROFILE,'version':VERSION,**binding,'source':c.report_ref(path),'ci':ci,'candidate_receipt_sha256':c.sha(c.C/'family-receipt.json'),'affected_packs':affected_packs(receipt,catalog),'client':False,'native_loading':False,'production_ready':False})
    return [*evidence_paths(include_native=False),c.report_ref(target)]

def evidence_paths(include_native=True):
    path=Path(c.CONFIG['extension_stable_validation']);proof=c.read(path)
    paths=[path,*[sibling(path,ref) for ref in [proof['test_log'],*[row['log'] for row in proof['completed_checks']]]]]
    if include_native:paths.extend([c.R/'current-author-static-validation.json',c.R/'current-author-native-validation.json'])
    return [c.report_ref(path) for path in dict.fromkeys(paths)]

def bind_native(receipt,evidence):
    static=c.read(c.R/'current-author-static-validation.json')
    assert static['profile']==PROFILE and static['version']==VERSION
    assert static['candidate_receipt_sha256']==evidence['candidate_receipt_sha256']==c.sha(c.C/'family-receipt.json')
    assert static['affected_packs']==affected_packs(receipt)
    assert all(evidence[key] for key in ['fresh_stopped_backup','existing_world_loaded','exact_files_checked','bds','saved_world_migration'])
    assert evidence['client'] is False and evidence['simulated_players'] is False and evidence['test_only_overlays']==[]
    assert [row['phase'] for row in evidence['runs']]==['first','restart']
    assert all(row['ok'] and not row['errors'] and row['real_player_connections']==0 and all(row[key] for key in ['player_records_unchanged','custom_container_inventories_retained','native_freezer_inputs_retained']) for row in evidence['runs'])
    c.atomic(c.R/'current-author-native-validation.json',{'schema':1,'profile':PROFILE,'version':VERSION,'static':c.report_ref(c.R/'current-author-static-validation.json'),'fresh_native':c.report_ref(c.R/'saved-world-report.json'),'candidate_receipt_sha256':evidence['candidate_receipt_sha256'],'affected_packs':static['affected_packs'],'native_loading':True,'saved_world_migration':True,'client':False,'production_ready':False})

def verify_installation(receipt):
    static=c.read(c.R/'current-author-static-validation.json');native=c.read(c.R/'current-author-native-validation.json')
    assert static['source']==c.report_ref(Path(c.CONFIG['extension_stable_validation']))
    assert static['profile']==native['profile']==PROFILE and static['version']==native['version']==VERSION
    assert static['candidate_receipt_sha256']==native['candidate_receipt_sha256']==c.sha(c.C/'family-receipt.json')
    assert static['affected_packs']==native['affected_packs']==affected_packs(receipt)
    assert native['static']==c.report_ref(c.R/'current-author-static-validation.json') and native['fresh_native']==c.report_ref(c.R/'saved-world-report.json')
    assert native['native_loading'] is True and native['saved_world_migration'] is True and native['client'] is False and native['production_ready'] is False
