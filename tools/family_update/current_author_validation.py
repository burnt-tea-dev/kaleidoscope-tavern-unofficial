"""Exact current-author source proof and fresh stopped-save binding.

Only hashes and reviewed contract metadata are public. Original private CI
artifacts bind the implementation, while native/client acceptance stays distinct.
Altered hosts are not clean author archives. This LIVE candidate adopts new
author UUIDs; the private owner version does not invalidate an already cached
clean Cookery162/Orchard101 client pack. Existing precise clean-install/cache
acceptance remains necessary before claiming public rendered usability.
"""
from functools import lru_cache
from pathlib import Path
import copy,hashlib,io,json,re,subprocess,zipfile
from family_update import common as c
from family_update.cookery_cache_validation import tree
from family_update.repository_identity import current_name,verify_record,verify_remote
from stable_host_profiles import CATALOG,PROFILES,match_stable_profile,public_profiles,receipt as profile_receipt,validate_stable_source

VERSION=[1,0,55]
REPOSITORY='casama233/senluo-family-integration-private'
REPOSITORY_ID=1406868911
LOGICAL='local/senluo-amw-cuisine'
PROFILE='senluo-stable-author-20261018-p55'
CATALOG_KEY='current_author_p55'
CHECKS={'current-source-api','native-freezer-performance.json','saturation-scheduling-functional.json','hud-coexistence-functional.json','ribbits-startup-functional.json','ribbits-fp-decode-functional.json'}

def selected():
    return c.CONFIG.get('extension_stable_profile') in ('current-author-p55','current-author-p56','current-author-p57','current-author-p58','current-author-retained')

def settings():
    selected_profile=c.CONFIG.get('extension_stable_profile')
    if selected_profile in ('current-author-p58','current-author-retained'):
        return [1,0,58], 'senluo-stable-author-20261019-p58', 'current_author_p58'
    if selected_profile in ('current-author-p56','current-author-p57'):
        release={'current-author-p56':56,'current-author-p57':57}[selected_profile]
        return [1,0,release], 'senluo-stable-author-20261018-p'+str(release), 'current_author_p'+str(release)
    assert selected_profile in (None,'current-author-p55'),'Unsupported current author profile'
    return VERSION, PROFILE, CATALOG_KEY

def retained_selected():
    return c.CONFIG.get('extension_stable_profile')=='current-author-retained'

def owner_version():
    return committed('baseline.json')['version'] if retained_selected() else settings()[0]

def validate_retained_runtime(owned,baseline,binding,*,source_root=None,sources=None):
    """Check public hashes/metadata only; never import or copy private runtime."""
    root=Path(source_root) if source_root is not None else c.EXTENSION
    selected_sources=sources if sources is not None else c.SOURCES
    anchor=baseline['retained_runtime']
    assert set(anchor)=={'schema','kind','source_commit','source_tree','source_version','dependency_versions'}
    assert anchor['schema']==1 and anchor['kind']=='dependency-only' and anchor['source_version']==[1,0,58]
    commit=anchor['source_commit'];assert isinstance(commit,str) and re.fullmatch('[0-9a-f]{40}',commit)
    assert c.git(root,'rev-parse',commit+'^{tree}')==anchor['source_tree']==owned['source_tree']
    c.git(root,'merge-base','--is-ancestor',commit,binding['actual_current_source_commit'])
    previous=json.loads(c.git(root,'show',commit+':baseline.json'))
    assert previous['repository']==baseline['repository']==LOGICAL
    assert previous['version']==anchor['source_version']==owned['source_version']
    assert baseline['version']!=previous['version'] and baseline['version'][:2]==[1,0] and baseline['version'][-1]>58
    assert owned['schema']==1 and owned['kind']=='dependency_only_runtime'
    assert owned['source_commit']==owned['previous_commit']==commit and owned['version']==baseline['version']
    assert owned['source_trees']==baseline['source_trees'] and owned['retained_source_trees']==previous['source_trees']
    assert owned['core_only'] is True and owned['added_paths']==owned['retired_paths']==[]
    assert owned['exact_changed_paths']==['runtime/BP/manifest.json','runtime/RP/manifest.json']
    assert baseline['runtime']==previous['runtime']=={'BP':'runtime/BP','RP':'runtime/RP'}
    assert set(owned['files'])==set(owned['previous_files'])=={'BP','RP'}
    anchor_manifests={side:subprocess.check_output(['git','show',commit+':runtime/'+side+'/manifest.json'],cwd=root) for side in ['BP','RP']}
    selected_peers={}
    for key in ['tavern','grilling','world-liquor']:
        peer=c.read(selected_sources[key]/'baseline.json')
        uid=peer['packs']['RP']['uuid'];assert uid not in selected_peers
        selected_peers[uid]=peer['version']
    peers={}
    for raw in anchor_manifests.values():
        for dependency in json.loads(raw).get('dependencies',[]):
            uid=dependency.get('uuid')
            if uid in selected_peers and dependency['version']!=selected_peers[uid]:peers[uid]=selected_peers[uid]
    assert anchor['dependency_versions']==owned['dependency_versions']==peers,'Retained peer versions differ from selected source pair'
    uuids={row['uuid'] for row in previous['packs'].values()}
    assert uuids=={row['uuid'] for row in baseline['packs'].values()}
    count=0;seen=set()
    for side in ['BP','RP']:
        before,after=owned['previous_files'][side],owned['files'][side]
        assert tree(before)==previous['source_trees'][side] and tree(after)==baseline['source_trees'][side]
        assert set(before)==set(after) and 'manifest.json' in before,'Retained runtime inventory changed'
        for name,value in {**before,**after}.items():
            path=Path(name)
            assert isinstance(name,str) and not path.is_absolute() and '..' not in path.parts and path.as_posix()==name and '\\' not in name
            assert isinstance(value,str) and re.fullmatch('[0-9a-f]{64}',value)
            if name!='manifest.json':assert before[name]==after[name],'Retained non-manifest payload changed'
        count+=len(before)-1
        relative=previous['runtime'][side]+'/manifest.json'
        raw=anchor_manifests[side]
        old=json.loads(raw);current_raw=local(root/relative)
        assert current_raw==subprocess.check_output(['git','show','HEAD:'+relative],cwd=root),'Uncommitted retained manifest'
        assert digest(raw)==before['manifest.json'] and digest(current_raw)==after['manifest.json']
        expected=copy.deepcopy(old);expected['header']['version']=baseline['version']
        assert old['header']['uuid']==baseline['packs'][side]['uuid'] and old['header']['version']==previous['version']
        for module in expected['modules']:
            assert module['version']==previous['version'];module['version']=baseline['version']
        for dependency in expected.get('dependencies',[]):
            uid=dependency.get('uuid')
            if uid in uuids:dependency['version']=baseline['version']
            elif uid in peers:dependency['version']=peers[uid];seen.add(uid)
        assert json.loads(current_raw)==expected,'Retained manifest changed outside reviewed versions'
        assert baseline['packs'][side]['dependencies']==expected.get('dependencies',[])
    # 370 is a reviewed P58 component fact, not permission for arbitrary profiles.
    assert seen==set(peers) and count==owned['conserved_files']==370,'Retained complete payload/profile differs'
    component=owned['retained_component_conservation'];catalog=CATALOG['current_author_p58']
    assert component['files']==owned['previous_files'] and component['previous_commit']==catalog['previous_commit']
    old_component=json.loads(c.git(root,'show',catalog['previous_commit']+':baseline.json'))
    for side in ['BP','RP']:assert tree(component['previous_files'][side])==old_component['source_trees'][side]
    # settings() deliberately selects the retained P58 catalog; its original
    # reviewed add/change boundaries remain mandatory for the immutable anchor.
    validate_owned_conservation(component,catalog,version=[1,0,58])
    return owned

def source_repository():
    # Historical source artifacts retain their recorded identity. Only the
    # fresh P58 producer runs after the reviewed organization transfer.
    version,_,_=settings()
    return current_name(REPOSITORY) if version==[1,0,58] else REPOSITORY

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
    remote=current_name(REPOSITORY)
    repo=gh_json('repos/'+remote)
    verify_remote(repo,REPOSITORY)
    run=gh_json(f'repos/{remote}/actions/runs/{run_id}')
    verify_record(run['repository'],REPOSITORY)
    assert run['status']=='completed' and run['conclusion']=='success'
    assert run['head_sha']==source and run['head_branch']=='main' and run['event'] in ('push','workflow_dispatch')
    assert run['path']=='.github/workflows/canonical.yml'
    assert gh_json(f'repos/{remote}/git/commits/{source}')['tree']['sha']==full_tree
    checks,statuses,unavailable=private_ci_records(remote,source)
    artifact=gh_json(f'repos/{remote}/actions/artifacts/{artifact_id}')
    assert artifact['name']=='current-author-functional' and artifact['expired'] is False
    assert artifact['workflow_run']['id']==run_id and artifact['workflow_run']['head_sha']==source
    raw=api_bytes(f'repos/{remote}/actions/artifacts/{artifact_id}/zip')
    assert len(raw)<=32*1024**2 and artifact['digest']=='sha256:'+digest(raw),'Current author original CI artifact changed'
    with zipfile.ZipFile(io.BytesIO(raw)) as archive:
        names=archive.namelist();assert len(names)<=32 and len(names)==len(set(names)) and all(Path(n).name==n for n in names)
        assert sum(i.file_size for i in archive.infolist())<=32*1024**2,'Current author artifact exceeds bounded evidence scope'
        members={name:archive.read(name) for name in names}
    return members,{'run_id':run_id,'artifact_id':artifact_id,'artifact_digest':artifact['digest'],'checks':checks,'statuses':statuses,'unavailable_optional_services':unavailable}

def source_proof():
    VERSION,PROFILE,CATALOG_KEY=settings()
    from family_update.extension_validation import source_binding
    from family_update.workflow import gh_json
    assert selected() and c.CONFIG.get('extension_stable_validation')
    assert not any(c.CONFIG.get(key) for key in ['extension_validation','extension_cache_validation','extension_hud_validation','extension_performance_validation'])
    path=Path(c.CONFIG['extension_stable_validation']);raw=local(path);proof=json.loads(raw)
    baseline=c.read(c.EXTENSION/'baseline.json');metadata=committed('.repo-target.json')
    assert baseline['repository']==LOGICAL and baseline['version']==(owner_version() if retained_selected() else VERSION)
    recorded_repository=source_repository()
    assert metadata['repository']==recorded_repository and metadata['repository_id']==REPOSITORY_ID and metadata['private'] is True
    assert proof['schema']==1 and proof['kind']=='current_author_functional' and proof['profile']==PROFILE
    assert proof['canonical_repository']==recorded_repository and proof['canonical_repository_id']==REPOSITORY_ID
    assert proof['test_command']==['python','tools/build_current_author_evidence.py'] and proof['test_exit_code']==0
    assert all(proof[key] is False for key in ['client','native_loading','simulated_players','production_ready'])
    binding=source_binding(proof,baseline);assert proof['git_tree']==binding['current_source_tree_oid']
    catalog=CATALOG[CATALOG_KEY];assert catalog['version']==VERSION and catalog['profile']==PROFILE
    if retained_selected():
        assert proof['component_version']==VERSION
        validate_retained_runtime(proof['owned_runtime'],baseline,binding)
        owned_component=proof['owned_runtime']['retained_component_conservation']
    else:owned_component=proof['owned_runtime']
    assert owned_component['previous_commit']==catalog['previous_commit']
    c.git(c.EXTENSION,'merge-base','--is-ancestor',catalog['previous_commit'],binding['actual_current_source_commit'])
    authors=committed(catalog['authors_path'],catalog['authors_sha256'])
    assert authors['profile']==PROFILE and authors['source_package_version']==VERSION and authors['authors']==catalog['authors']
    pr=gh_json(f'repos/{current_name(REPOSITORY)}/pulls/{c.CONFIG["extension_stable_pull_request"]}')
    verify_record(pr['head']['repo'],REPOSITORY);verify_record(pr['base']['repo'],REPOSITORY)
    assert pr['merged'] is True and pr['base']['ref']=='main'
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
    assert source_api['command']==['node','--experimental-vm-modules','tools/current-author-functional.test.mjs']
    return path,proof,baseline,binding,catalog,ci

def affected_packs(receipt,catalog=None):
    VERSION,PROFILE,CATALOG_KEY=settings()
    catalog=catalog or CATALOG[CATALOG_KEY]
    uuids={pin[key] for pin in catalog['authors'].values() for key in ['behavior_uuid','resource_uuid']}
    return {p['uuid']:{'side':p['side'],'version':p['version'],'files':tree(p['files'])} for p in receipt['packs'] if p['uuid'] in uuids or p['source'].get('repository')==LOGICAL}

def validate_owned_conservation(owned,catalog,version=None):
    """Retain historical deltas; P57 additionally admits only its exact removal."""
    VERSION=version if version is not None else settings()[0]
    changed=sorted('runtime/'+side+'/'+name for side in ['BP','RP'] for name in owned['files'][side].keys()&owned['previous_files'][side].keys() if owned['files'][side][name]!=owned['previous_files'][side][name])
    added=sorted('runtime/'+side+'/'+name for side in ['BP','RP'] for name in owned['files'][side].keys()-owned['previous_files'][side].keys())
    retired=sorted('runtime/'+side+'/'+name for side in ['BP','RP'] for name in owned['previous_files'][side].keys()-owned['files'][side].keys())
    assert changed==owned['exact_changed_paths'],'Current author conservation changed paths differ'
    assert added==owned['added_paths'],'Current author conservation added paths differ'
    assert retired==owned['retired_paths'],'Current author conservation retired paths differ'
    if VERSION==[1,0,57]:
        def reviewed_paths(key):
            paths=catalog[key]
            assert isinstance(paths,list) and all(isinstance(path,str) for path in paths),'P57 conservation catalog paths must be a list'
            assert paths==sorted(set(paths)),'P57 conservation catalog paths must be sorted and unique'
            for value in paths:
                path=Path(value)
                assert len(path.parts)>=3 and path.parts[:2] in [('runtime','BP'),('runtime','RP')] and '..' not in path.parts and path.as_posix()==value,'Unsafe P57 conservation catalog path'
            return paths
        assert catalog['added_paths']==added==[],'P57 cannot add unreviewed runtime content'
        assert retired==reviewed_paths('retired_paths') and retired,'P57 retired content differs from the exact reviewed scope'
        assert changed==reviewed_paths('exact_changed_paths'),'P57 changed content differs from the exact reviewed scope'
    if VERSION==[1,0,58]:
        for key,actual in [('exact_changed_paths',changed),('added_paths',added),('retired_paths',retired)]:
            expected=catalog[key]
            assert isinstance(expected,list) and all(isinstance(path,str) for path in expected) and expected==sorted(set(expected))
            assert actual==expected,'P58 conservation differs from the exact reviewed '+key
            for value in expected:
                path=Path(value)
                assert len(path.parts)>=3 and path.parts[:2] in [('runtime','BP'),('runtime','RP')] and '..' not in path.parts and path.as_posix()==value
        assert retired==[],'P58 cannot retire additional content'
        from family_update.preserved_client_assets_inputs import HELPER
        allowed_added={'runtime/BP/'+HELPER,'runtime/BP/client-repairs/repair-plan.json'}
        normals=[name for name in added if name.startswith('runtime/RP/textures/integration/fishing-normal/') and name.endswith('_normal.png')]
        assert len(normals)==156 and set(added)==allowed_added|set(normals),'P58 additions exceed client helper/plan/normals'
        assert set(changed)=={'runtime/BP/manifest.json','runtime/RP/manifest.json',*['runtime/BP/host-extensions/'+name for name in catalog['host_specs']]},'P58 runtime changes exceed paired identity/host declarations'

def validate_candidate(receipt,proof,baseline,binding,catalog):
    """Validate every output and the exact ordered chain, not just changed paths."""
    VERSION,PROFILE,CATALOG_KEY=settings()
    component_version=VERSION
    if retained_selected():
        assert proof['component_version']==component_version
        validate_retained_runtime(proof['owned_runtime'],baseline,binding)
        VERSION=baseline['version']
    variant={55:[1,0,10655],56:[1,0,10656],57:[1,0,10657],58:[1,0,10658]}[component_version[-1]]
    rows={row['uuid']:row for row in receipt['packs']};assert len(rows)==len(receipt['packs'])
    assert {row['uuid'] for row in rows.values() if row['source'].get('repository')==LOGICAL}=={p['uuid'] for p in baseline['packs'].values()},'Current private pair inventory differs'
    owned=proof['owned_runtime'];assert set(owned['files'])=={'BP','RP'}
    previous_commit=baseline['retained_runtime']['source_commit'] if retained_selected() else catalog['previous_commit']
    previous=json.loads(c.git(c.EXTENSION,'show',previous_commit+':baseline.json'))
    for side,definition in baseline['packs'].items():
        pack=rows[definition['uuid']]
        assert pack['source']['owner']=='owned' and pack['source']['repository']==LOGICAL and pack['version']==VERSION
        assert pack['source']['commit']==binding['actual_current_source_commit'] and pack['source']['working_candidate'] is False
        assert pack['files']==owned['files'][side] and tree(pack['files'])==baseline['source_trees'][side]
        assert tree(owned['previous_files'][side])==previous['source_trees'][side]
    if not retained_selected():validate_owned_conservation(owned,catalog)
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
            expected_version=variant if key=='ChineseFood' else pin['author_version']
            assert pack['version']==expected_version
            current=dict(authored['original_files'][side])
            for index,extension in enumerate(extensions):
                prefix={**source,'owner':'upstream' if index==0 else 'upstream_extended','reviewed_extensions':extensions[:index]}
                if extension['id']==public['id']:
                    declared=public_spec;profile=public;spec_sha=catalog['public_api_spec_sha256'];repository=api['repository'];commit=c.git(g,'rev-parse','HEAD')
                else:
                    assert extension['id'] in specs,'Unexpected current author host extension'
                    declared,profile,spec_sha=specs[extension['id']];repository=LOGICAL;commit=binding['actual_current_source_commit'];seen.add(extension['id'])
                if retained_selected() and repository==LOGICAL:
                    anchor=baseline['retained_runtime']
                    assert extension['source_package_version']==VERSION and extension['component_version']==component_version
                    assert extension['retained_runtime_profile']=={'schema':1,'source_commit':anchor['source_commit'],'source_tree':anchor['source_tree'],'source_version':component_version}
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
                else:assert extension['owner_version']==component_version and extension['local_pack_version']==variant
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
    VERSION,PROFILE,CATALOG_KEY=settings()
    path,proof,baseline,binding,catalog,ci=source_proof()
    validate_candidate(receipt,proof,baseline,binding,catalog)
    target=c.R/'current-author-static-validation.json'
    c.atomic(target,{'schema':1,'profile':PROFILE,'version':baseline['version'],**({'component_version':VERSION} if retained_selected() else {}),**binding,'source':c.report_ref(path),'ci':ci,'candidate_receipt_sha256':c.sha(c.C/'family-receipt.json'),'affected_packs':affected_packs(receipt,catalog),'client':False,'native_loading':False,'production_ready':False})
    return [*evidence_paths(include_native=False),c.report_ref(target)]

def evidence_paths(include_native=True):
    path=Path(c.CONFIG['extension_stable_validation']);proof=c.read(path)
    paths=[path,*[sibling(path,ref) for ref in [proof['test_log'],*[row['log'] for row in proof['completed_checks']]]]]
    if include_native:paths.extend([c.R/'current-author-static-validation.json',c.R/'current-author-native-validation.json'])
    return [c.report_ref(path) for path in dict.fromkeys(paths)]

def bind_native(receipt,evidence):
    VERSION,PROFILE,CATALOG_KEY=settings()
    VERSION=owner_version()
    static=c.read(c.R/'current-author-static-validation.json')
    assert static['profile']==PROFILE and static['version']==VERSION
    if retained_selected():assert static['component_version']==settings()[0]
    assert static['candidate_receipt_sha256']==evidence['candidate_receipt_sha256']==c.sha(c.C/'family-receipt.json')
    assert static['affected_packs']==affected_packs(receipt)
    assert all(evidence[key] for key in ['fresh_stopped_backup','existing_world_loaded','exact_files_checked','bds','saved_world_migration'])
    assert evidence['client'] is False and evidence['simulated_players'] is False and evidence['test_only_overlays']==[]
    assert [row['phase'] for row in evidence['runs']]==['first','restart']
    assert all(row['ok'] and not row['errors'] and row['real_player_connections']==0 and all(row[key] for key in ['player_records_unchanged','custom_container_inventories_retained','native_freezer_inputs_retained']) for row in evidence['runs'])
    c.atomic(c.R/'current-author-native-validation.json',{'schema':1,'profile':PROFILE,'version':VERSION,**({'component_version':settings()[0]} if retained_selected() else {}),'static':c.report_ref(c.R/'current-author-static-validation.json'),'fresh_native':c.report_ref(c.R/'saved-world-report.json'),'candidate_receipt_sha256':evidence['candidate_receipt_sha256'],'affected_packs':static['affected_packs'],'native_loading':True,'saved_world_migration':True,'client':False,'production_ready':False})

def verify_installation(receipt):
    VERSION,PROFILE,CATALOG_KEY=settings()
    VERSION=owner_version()
    static=c.read(c.R/'current-author-static-validation.json');native=c.read(c.R/'current-author-native-validation.json')
    assert static['source']==c.report_ref(Path(c.CONFIG['extension_stable_validation']))
    assert static['profile']==native['profile']==PROFILE and static['version']==native['version']==VERSION
    if retained_selected():assert static['component_version']==native['component_version']==settings()[0]
    assert static['candidate_receipt_sha256']==native['candidate_receipt_sha256']==c.sha(c.C/'family-receipt.json')
    assert static['affected_packs']==native['affected_packs']==affected_packs(receipt)
    assert native['static']==c.report_ref(c.R/'current-author-static-validation.json') and native['fresh_native']==c.report_ref(c.R/'saved-world-report.json')
    assert native['native_loading'] is True and native['saved_world_migration'] is True and native['client'] is False and native['production_ready'] is False
