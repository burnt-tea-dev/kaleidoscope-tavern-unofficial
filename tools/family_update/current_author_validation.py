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
from stable_host_profiles import CATALOG,PROFILES,CURATED,CURATED_KEY,curated_profile,match_stable_profile,public_profiles,receipt as profile_receipt,validate_stable_source

VERSION=[1,0,55]
REPOSITORY='casama233/senluo-family-integration-private'
REPOSITORY_ID=1406868911
LOGICAL='local/senluo-amw-cuisine'
PROFILE='senluo-stable-author-20261018-p55'
CATALOG_KEY='current_author_p55'
CHECKS={'current-source-api','native-freezer-performance.json','saturation-scheduling-functional.json','hud-coexistence-functional.json','ribbits-startup-functional.json','ribbits-fp-decode-functional.json'}
CURRENT_DOMAINS={
 'cookery-station-performance':{'runtime/BP/host-extensions/cookery-station-performance.json','runtime/BP/scripts/host_api/cookery-station-performance.js'},
 'witchway-family-hud':{'runtime/RP/ui/_global_variables.json','runtime/RP/ui/hud_screen.json'}}
CURRENT_CONTRACT='data/current-runtime-contract.json'

def functional_selected(baseline=None):
    if curated_selected():return True
    baseline=committed('baseline.json') if baseline is None else baseline
    return baseline.get('retained_runtime',{}).get('kind')=='current-functional'

def selected():
    return c.CONFIG.get('extension_stable_profile') in ('current-author-p55','current-author-p56','current-author-p57','current-author-p58','current-author-retained',CURATED)

def curated_selected():
    return c.CONFIG.get('extension_stable_profile')==CURATED

def current_selection(*,source_root=None):
    catalog=curated_profile();selection=catalog['selection']
    assert committed('baseline.json',source_root=source_root).get('current_author_profile')==selection['path'],'Curated baseline must select the reviewed producer input'
    assert committed(selection['path'],selection['sha256'],source_root=source_root)==selection['value'],'Curated producer selection differs from reviewed profile'
    return selection['value']

def functional_contract():
    return current_selection()['functional_contract']['path'] if curated_selected() else CURRENT_CONTRACT

def settings():
    selected_profile=c.CONFIG.get('extension_stable_profile')
    if curated_selected():
        selection=current_selection()
        return selection['version'],selection['profile'],CURATED_KEY
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
    if anchor.get('kind')=='current-functional':
        return validate_current_runtime(owned,baseline,binding,root,selected_sources)
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
    # 370 is a reviewed reviewed integration component fact, not permission for arbitrary profiles.
    assert seen==set(peers) and count==owned['conserved_files']==370,'Retained complete payload/profile differs'
    component=owned['retained_component_conservation'];catalog=CATALOG['current_author_p58']
    assert component['files']==owned['previous_files'] and component['previous_commit']==catalog['previous_commit']
    old_component=json.loads(c.git(root,'show',catalog['previous_commit']+':baseline.json'))
    for side in ['BP','RP']:assert tree(component['previous_files'][side])==old_component['source_trees'][side]
    # settings() deliberately selects the retained reviewed integration catalog; its original
    # reviewed add/change boundaries remain mandatory for the immutable anchor.
    validate_owned_conservation(component,catalog,version=[1,0,58])
    return owned

def validate_current_runtime(owned,baseline,binding,root,sources):
    """Current domains have current owners; every unrelated component byte stays exact."""
    anchor=baseline['retained_runtime']
    assert set(anchor)=={'schema','kind','source_commit','source_tree','source_version','dependency_versions','functional_contract','retired_dependencies'}
    assert anchor['schema']==1 and anchor['source_version']==[1,0,58] and anchor['functional_contract']==CURRENT_CONTRACT
    assert anchor['retired_dependencies']==['994f73a2-05ec-41ce-876c-d388a526d9f5']
    commit=anchor['source_commit'];assert re.fullmatch('[0-9a-f]{40}',commit)
    assert c.git(root,'rev-parse',commit+'^{tree}')==anchor['source_tree']==owned['source_tree']
    c.git(root,'merge-base','--is-ancestor',commit,binding['actual_current_source_commit'])
    previous=json.loads(c.git(root,'show',commit+':baseline.json'))
    assert previous['repository']==baseline['repository']==LOGICAL and previous['version']==owned['source_version']==[1,0,58]
    assert tuple(baseline['version'])>tuple(previous['version']) and baseline['runtime']==previous['runtime']=={'BP':'runtime/BP','RP':'runtime/RP'}
    assert owned['schema']==1 and owned['kind']=='current_functional_runtime' and owned['core_only'] is True
    assert owned['source_commit']==owned['previous_commit']==commit and owned['version']==owned['current_owner_version']==baseline['version']
    assert owned['source_trees']==baseline['source_trees'] and owned['retained_source_trees']==previous['source_trees']
    raw=local(root/CURRENT_CONTRACT)
    assert raw==subprocess.check_output(['git','show','HEAD:'+CURRENT_CONTRACT],cwd=root)
    contract=json.loads(raw)
    assert set(contract)=={'schema','kind','domains'} and contract['schema']==1 and contract['kind']=='current-functional-runtime'
    assert contract['domains']==owned['functional_domains'] and set(contract['domains'])==set(CURRENT_DOMAINS)
    active=set()
    for domain,paths in CURRENT_DOMAINS.items():
        assert set(contract['domains'][domain])==paths
        for name,hashes in contract['domains'][domain].items():
            assert set(hashes)=={'before','after'} and hashes['before']!=hashes['after']
            side,relative=name.removeprefix('runtime/').split('/',1)
            assert owned['previous_files'][side].get(relative)==hashes['before'] and owned['files'][side][relative]==hashes['after']
            assert digest(local(root/name))==hashes['after'],'Current domain differs from committed source proof'
        active|=paths
    selected_peers={}
    for key in ['tavern','grilling','world-liquor']:
        peer=c.read(sources[key]/'baseline.json');selected_peers[peer['packs']['RP']['uuid']]=peer['version']
    for name,side in [('fishing','BP'),('witchway','RP')]:
        manifest=c.read(root/f'companion-sources/{name}-current-local/runtimeowner/{side}/manifest.json')
        selected_peers[manifest['header']['uuid']]=manifest['header']['version']
    anchor_manifests={side:subprocess.check_output(['git','show',commit+':runtime/'+side+'/manifest.json'],cwd=root) for side in ['BP','RP']}
    peers={d['uuid']:selected_peers[d['uuid']] for raw in anchor_manifests.values() for d in json.loads(raw).get('dependencies',[])
           if d.get('uuid') in selected_peers and d['version']!=selected_peers[d['uuid']]}
    peers['d8a147c2-5b9e-4c11-9a32-7e418f20b201']=selected_peers['d8a147c2-5b9e-4c11-9a32-7e418f20b201']
    assert anchor['dependency_versions']==owned['dependency_versions']==peers
    assert owned['retired_dependencies']==anchor['retired_dependencies']
    own={p['uuid'] for p in previous['packs'].values()};assert own=={p['uuid'] for p in baseline['packs'].values()}
    changed=[];added=[];count=0;seen=set();retired_seen=set()
    for side in ['BP','RP']:
        before,after=owned['previous_files'][side],owned['files'][side]
        assert tree(before)==previous['source_trees'][side] and tree(after)==baseline['source_trees'][side]
        domain={name.removeprefix('runtime/'+side+'/') for name in active if name.startswith('runtime/'+side+'/')}
        assert set(after)==set(before)|domain
        for name,value in after.items():
            path=Path(name);assert not path.is_absolute() and '..' not in path.parts and path.as_posix()==name and '\\' not in name
            assert isinstance(value,str) and re.fullmatch('[0-9a-f]{64}',value)
            full='runtime/'+side+'/'+name
            if name not in before:added.append(full)
            elif before[name]!=value:changed.append(full)
            if name!='manifest.json' and name not in domain:
                assert before[name]==value,'Current release changed a retained component byte';count+=1
        old_raw=anchor_manifests[side]
        actual_raw=local(root/'runtime'/side/'manifest.json')
        assert digest(old_raw)==before['manifest.json'] and digest(actual_raw)==after['manifest.json']
        expected=json.loads(old_raw);expected['header']['version']=baseline['version']
        for module in expected['modules']:assert module['version']==[1,0,58];module['version']=baseline['version']
        dependencies=[];original={d.get('uuid') for d in expected.get('dependencies',[])}
        for dependency in expected.get('dependencies',[]):
            uid=dependency.get('uuid')
            if uid in anchor['retired_dependencies']:retired_seen.add(uid);continue
            if uid in own:dependency['version']=baseline['version']
            elif uid in peers:dependency['version']=peers[uid];seen.add(uid)
            dependencies.append(dependency)
        if side=='RP':
            uid='d8a147c2-5b9e-4c11-9a32-7e418f20b201';assert uid not in original
            dependencies.append({'uuid':uid,'version':peers[uid]});seen.add(uid)
        expected['dependencies']=dependencies
        assert json.loads(actual_raw)==expected and baseline['packs'][side]['dependencies']==dependencies
    assert seen==set(peers) and retired_seen==set(anchor['retired_dependencies'])
    assert sorted(changed)==owned['exact_changed_paths'] and sorted(added)==owned['added_paths'] and owned['retired_paths']==[]
    assert count==owned['conserved_files']==368
    component=owned['retained_component_conservation'];catalog=CATALOG['current_author_p58']
    assert component['files']==owned['previous_files'] and component['previous_commit']==catalog['previous_commit']
    old_component=json.loads(c.git(root,'show',catalog['previous_commit']+':baseline.json'))
    for side in ['BP','RP']:assert tree(component['previous_files'][side])==old_component['source_trees'][side]
    validate_owned_conservation(component,catalog,version=[1,0,58])
    return owned

def source_repository():
    # Historical source artifacts retain their recorded identity. Only the
    # fresh reviewed integration producer runs after the reviewed organization transfer.
    version,_,_=settings()
    return current_name(REPOSITORY) if curated_selected() or version==[1,0,58] else REPOSITORY

def digest(raw):return hashlib.sha256(raw).hexdigest()

def local(path,expected=None):
    path=Path(path);assert path.is_file() and not path.is_symlink(),'Current author evidence missing or linked'
    raw=path.read_bytes()
    if expected is not None:assert digest(raw)==expected,'Current author evidence changed'
    return raw

def sibling(path,ref):
    name=ref['name'];assert isinstance(name,str) and Path(name).name==name and name not in ('','.','..'),'Unsafe current source evidence member'
    target=Path(path).parent/name;local(target,ref['sha256']);return target

def committed(relative,expected=None,*,source_root=None):
    root=c.EXTENSION if source_root is None else Path(source_root)
    path=root/relative;raw=local(path,expected)
    assert path.resolve().is_relative_to(root.resolve()),'Current source escaped owned checkout'
    assert raw==subprocess.check_output(['git','show','HEAD:'+relative],cwd=root),'Uncommitted current author source'
    return json.loads(raw)

def curated_inputs_enabled():
    return bool(c.CONFIG.get('fresh_world')) and curated_selected()

def _curated_retained_rows():
    assert curated_inputs_enabled(), 'Retained curated inputs require a fresh current-author selection'
    assert not c.CONFIG.get('managed_drift_recovery') and not c.CONFIG.get('prospective_preserved_inputs'), 'Curated inputs cannot combine retained selectors'
    rows=current_selection()['retained_inputs']
    assert isinstance(rows,list) and rows, 'Curated retained inputs must be explicit'
    assert len({row['uuid'] for row in rows})==len(rows), 'Curated retained input UUID is repeated'
    for row in rows:
        assert row['kind'] in ('literal','saturation','canonical-fishing') and row['side'] in ('behavior','resource'), 'Unknown curated retained input kind or side'
        for key in ('input_version','output_version'):
            value=row[key]
            assert isinstance(value,list) and len(value)==3 and all(type(n) is int and n>=0 for n in value), 'Invalid curated retained input version'
        assert row['provenance']['official_author_release'] is False, 'Retained compatibility bytes are not official author releases'
    for kind in ('saturation','canonical-fishing'):
        selected=[row for row in rows if row['kind']==kind]
        assert len(selected)==2 and {row['side'] for row in selected}=={'behavior','resource'}, 'Curated retained pair is incomplete: '+kind
    return rows

def _curated_retained_recipes(rows):
    references={}
    for row in rows:
        refs=[]
        if row['kind']!='literal':refs.append({'path':row['recipe_path'],'sha256':row['recipe_sha256']})
        if row['kind']=='canonical-fishing':refs.append(row['provenance']['input_recipe'])
        for ref in refs:
            name=ref['path'];path=Path(name)
            assert not path.is_absolute() and '..' not in path.parts and path.as_posix()==name and '\\' not in name, 'Curated recipe must be relative canonical source'
            assert references.get(name,ref['sha256'])==ref['sha256'], 'Conflicting curated recipe references'
            references[name]=ref['sha256']
    return {name:committed(name,expected) for name,expected in references.items()},references

def _curated_retained_descriptor(row):
    source={'owner':'preserved','role':'curated_retained_input','group':row['group'],
            'kind':row['kind'],'official_author_release':False,'provenance':copy.deepcopy(row['provenance'])}
    if row['kind']!='literal':source['recipe']={'path':row['recipe_path'],'sha256':row['recipe_sha256']}
    if row['kind']=='canonical-fishing':source['canonical_source']=row['canonical_source']
    return source

def select_curated_inputs(original):
    """Select only declared captured inputs or a complete canonical Fishing pair.

    The captured maps already identify the literal roots. Assembly rechecks
    their bytes at its copy boundary; this selector does not rescan those roots.
    """
    rows=_curated_retained_rows();recipes,_=_curated_retained_recipes(rows)
    captured={}
    for row in original['packs']:captured.setdefault(row['uuid'],[]).append(row)
    roots=[];descriptors={};selected={}
    for row in rows:
        uid=row['uuid'];matches=captured.get(uid,[])
        assert len(matches)==1, 'Missing or ambiguous curated captured input: '+uid
        actual=matches[0];side='BP' if row['side']=='behavior' else 'RP'
        assert actual['side']==row['side'] and actual['version']==row['input_version'], 'Curated captured input identity changed: '+uid
        assert tree(actual['files'])==row['input_tree'], 'Curated captured input bytes changed: '+uid
        root=Path(actual['path'])
        if row['kind']=='literal':
            assert row['input_version']==row['output_version'] and row['input_tree']==row['output_tree'], 'Literal retained inputs cannot be transformed'
            assert row['provenance']['original_archive_verified'] is False and row['provenance']['latest_stable_verified'] is False, 'Literal source provenance differs'
        elif row['kind']=='saturation':
            recipe=recipes[row['recipe_path']];provenance=row['provenance']
            assert recipe['file_id']==provenance['file_id'] and recipe['archive_sha256']==provenance['clean_archive_sha256'], 'Saturation author provenance differs'
            assert provenance['latest_stable_input_verified'] is True, 'Saturation requires its reviewed current author input'
            assert recipe['uuids'][side]==uid and recipe['versions'][side]==row['output_version'], 'Saturation canonical pair differs'
            assert actual['files']==recipe['output_hashes'][side] and row['input_version']==row['output_version'], 'Saturation is not the existing canonical compatibility output'
            assert tree(recipe['output_hashes'][side])==row['output_tree'], 'Saturation output fingerprint differs'
        else:
            relative='companion-sources/fishing-current-local/runtimeowner/'+side
            assert row['canonical_source']==relative and row['recipe_path']=='companion-sources/fishing-current-local/recipe.json', 'Fishing must select its complete fixed canonical runtime'
            recipe=recipes[row['recipe_path']];ref=row['provenance']['input_recipe'];input_recipe=recipes[ref['path']]
            assert recipe['kind']=='canonical_local_fishing_repair' and recipe['input_recipe']==ref, 'Fishing canonical source recipe differs'
            assert recipe['historical_origin_status']=='unknown' and recipe['original_archive_verified'] is False and recipe['latest_stable_verified'] is False, 'Fishing origin uncertainty must remain explicit'
            assert input_recipe['packs'][side]['uuid']==uid and input_recipe['packs'][side]['version']==row['input_version'], 'Fishing original identity differs'
            assert actual['files']==input_recipe['packs'][side]['files']==recipe['input_hashes'][side], 'Fishing original bytes differ from its canonical input recipe'
            assert recipe['owned_runtime']==recipe['output_hashes'] and recipe['version']==row['output_version'], 'Fishing must use the whole canonical owner output'
            root=c.EXTENSION/relative
            assert c.hashes(root)==recipe['output_hashes'][side], 'Fishing canonical runtime bytes differ'
            assert tree(recipe['output_hashes'][side])==row['output_tree'], 'Fishing output fingerprint differs'
            manifest=c.read(root/'manifest.json')
            assert manifest['header']['uuid']==uid and manifest['header']['version']==row['output_version'], 'Fishing canonical manifest identity differs'
            assert all(module['version']==row['output_version'] for module in manifest['modules']), 'Fishing canonical module version differs'
        roots.append(root);descriptors[uid]=_curated_retained_descriptor(row)
        selected[uid]={'path':str(root),'side':row['side'],'input_version':row['input_version'],
                       'version':row['output_version'],'input_tree':row['input_tree'],
                       'output_tree':row['output_tree'],'source':descriptors[uid]}
    binding=CATALOG[CURATED_KEY]['selection']
    report={'schema':1,'kind':'curated_input_selection','profile':{'path':binding['path'],'sha256':binding['sha256']},
            'packs':selected,'native_loading':False,'client':False,'production_ready':False}
    return roots,descriptors,report

def verify_curated_inputs(receipt,selection):
    rows=_curated_retained_rows();binding=CATALOG[CURATED_KEY]['selection']
    assert selection['schema']==1 and selection['kind']=='curated_input_selection' and selection['profile']=={'path':binding['path'],'sha256':binding['sha256']}, 'Curated input selection profile changed'
    assert all(selection[key] is False for key in ('native_loading','client','production_ready')), 'Source selection cannot certify native or client acceptance'
    assert set(selection['packs'])=={row['uuid'] for row in rows}, 'Curated input selection set changed'
    actual={row['uuid']:row for row in receipt['packs']}
    assert len(actual)==len(receipt['packs']), 'Candidate contains duplicate pack identities'
    assert {uid for uid,row in actual.items() if row['source']['owner']=='preserved'}==set(selection['packs']), 'Candidate contains an unselected retained input'
    for row in rows:
        uid=row['uuid'];pack=actual[uid];selected=selection['packs'][uid]
        expected={'side':row['side'],'input_version':row['input_version'],'version':row['output_version'],
                  'input_tree':row['input_tree'],'output_tree':row['output_tree'],'source':_curated_retained_descriptor(row)}
        assert {key:selected[key] for key in expected}==expected, 'Curated selection metadata changed: '+uid
        assert pack['side']==row['side'] and pack['version']==row['output_version'] and tree(pack['files'])==row['output_tree'], 'Curated candidate output differs: '+uid
        assert pack['source']==expected['source'], 'Curated candidate provenance differs: '+uid

def input_refs():
    if not curated_inputs_enabled():return {}
    rows=_curated_retained_rows();_,references=_curated_retained_recipes(rows)
    binding=CATALOG[CURATED_KEY]['selection']
    result={'curated_retained_profile':binding['sha256'],
            'curated_retained_capture':c.sha(c.R/'production-before/inventory.json'),
            'curated_retained_selection':c.sha(c.R/'curated-input-selection.json')}
    result.update({'curated_retained_recipe:'+name:value for name,value in references.items()})
    return result

def committed_digest(relative,*,source_root=None):
    root=c.EXTENSION if source_root is None else Path(source_root)
    raw=local(root/relative)
    assert raw==subprocess.check_output(['git','show','HEAD:'+relative],cwd=root),'Uncommitted current functional source'
    return digest(raw)

def validate_curated_runtime(owned,baseline,catalog,*,source_root=None):
    """Current source conserves every byte outside the one reviewed domain map."""
    root=c.EXTENSION if source_root is None else Path(source_root)
    selection=current_selection(source_root=root);reference=selection['functional_contract']
    contract=committed(reference['path'],reference['sha256'],source_root=root)
    assert contract['schema']==1 and contract['kind']=='current-functional-runtime'
    assert contract['domains']==owned['functional_domains'] and set(contract['domains'])==set(selection['domains'])
    assert owned['schema']==1 and owned['kind']=='current_functional_runtime' and owned['core_only'] is True
    assert owned['source_commit']==owned['previous_commit']==catalog['previous_commit']
    assert owned['version']==owned['current_owner_version']==baseline['version']==selection['version']
    previous=json.loads(c.git(root,'show',catalog['previous_commit']+':baseline.json'))
    assert previous['repository']==baseline['repository']==LOGICAL and previous['version']==owned['source_version']
    assert owned['source_trees']==baseline['source_trees'] and owned['retained_source_trees']==previous['source_trees']
    assert set(owned['files'])==set(owned['previous_files'])=={'BP','RP'}
    active=set()
    for domain,paths in selection['domains'].items():
        assert len(paths)==len(set(paths)) and set(contract['domains'][domain])==set(paths)
        for name,hashes in contract['domains'][domain].items():
            assert name not in active,'Curated domain path has two owners'
            active.add(name)
            assert set(hashes)=={'before','after'} and hashes['before']!=hashes['after']
            path=Path(name);assert len(path.parts)>=3 and path.parts[:2] in [('runtime','BP'),('runtime','RP')]
            side=path.parts[1];relative='/'.join(path.parts[2:])
            assert owned['previous_files'][side].get(relative)==hashes['before'] and owned['files'][side].get(relative)==hashes['after']
            if hashes['after'] is not None:assert committed_digest(name,source_root=root)==hashes['after']
            else:assert not (root/name).exists()
    validate_owned_conservation(owned,catalog,version=baseline['version'])
    reviewed=set(owned['exact_changed_paths']+owned['added_paths']+owned['retired_paths'])
    assert active==reviewed-{'runtime/BP/manifest.json','runtime/RP/manifest.json'},'Curated domains do not cover the exact reviewed runtime changes'
    conserved=0
    for side in ['BP','RP']:
        before,after=owned['previous_files'][side],owned['files'][side]
        assert tree(before)==previous['source_trees'][side] and tree(after)==baseline['source_trees'][side]
        for name,value in {**before,**after}.items():
            path=Path(name)
            assert not path.is_absolute() and '..' not in path.parts and path.as_posix()==name and '\\' not in name
            assert isinstance(value,str) and re.fullmatch('[0-9a-f]{64}',value)
        conserved+=sum(before[name]==after[name] for name in before.keys()&after.keys())
    assert owned['conserved_files']==conserved

def validate_functional_artifacts(path,proof,baseline,members):
    name='current-runtime-functional.json';raw=members[name];current=json.loads(raw)
    completed=next(row for row in proof['completed_checks'] if row['name']==name)
    assert completed['report_sha256']==digest(raw)
    assert current['schema']==1 and current['kind']=='current_runtime_functional'
    for key in ['version','repository','source_commit','git_tree','source_trees']:assert current[key]==proof[key]
    assert current['version']==baseline['version'] and current['test_exit_code']==0
    assert current['test_command']==['python','tools/build_current_functional_evidence.py']
    assert all(current[key] is False for key in ['native_loading','client','simulated_players','production_ready','saved_world_migration','native_full_nbt_verified'])
    policy=current_selection() if curated_selected() else {'sources':['Cookery','Fishing','WitchWay'],'functional_checks':{
        'cookery-station-performance':{'source':'Cookery','cases':10},'fishing-current':{'source':'Fishing','cases':22},'witchway-native-drop-items':{'source':'WitchWay','cases':28}}}
    assert current['sources']==proof['current_functional_sources'] and set(current['sources'])==set(policy['sources'])
    checks=current['completed_checks'];assert len(checks)==len(policy['functional_checks']) and {row['name'] for row in checks}==set(policy['functional_checks'])
    for row in checks:
        assert row['exit_code']==0 and isinstance(row['command'],list)
        for ref in [row['log'],*([row['report']] if row.get('report') else [])]:assert digest(members[ref['name']])==ref['sha256']
    if 'Cookery' in policy['sources']:
        cookery=current['sources']['Cookery'];station=committed('runtime/BP/host-extensions/cookery-station-performance.json')
        closure=cookery['input_closure'];target='scripts/custom_components/blocks/directStation.js'
        assert closure['repair_spec_sha256']==committed_digest('runtime/BP/host-extensions/cookery-station-performance.json')
        assert closure['station_output_sha256']==station['patched_files'][target]
        assert closure['owned_helper_sha256']==station['helper_sha256']==committed_digest('runtime/BP/scripts/host_api/cookery-station-performance.js')
        report=json.loads(members[cookery['report']['name']]);assert digest(members[cookery['report']['name']])==cookery['report']['sha256']
        assert report['ok'] is True and report['completeSuite'] is True and report['caseCount']==len(report['results'])==policy['functional_checks']['cookery-station-performance']['cases']
        assert report['input_closure']==closure and report['native'] is False and report['client'] is False
        assert report['source_test_sha256']==cookery['test_source_sha256']==committed_digest('tools/cookery-station-performance.test.mjs')
    if 'Fishing' in policy['sources']:
        fish=current['sources']['Fishing'];assert fish['kind']=='current_local_fishing_functional' and fish['historical_origin_status']=='unknown'
        assert fish['original_archive_verified'] is False and fish['latest_stable_verified'] is False
        recipe=committed('companion-sources/fishing-current-local/recipe.json',fish['export_recipe']['sha256'])
        assert recipe['kind']=='canonical_local_fishing_repair' and recipe['version']==fish['version']
        assert recipe['owned_runtime']==recipe['output_hashes']==fish['runtime_files']
        assert fish['input_recipe']['sha256']==recipe['input_recipe']['sha256']==committed_digest('companion-sources/fishing-current-local/input-recipe.json')
        assert fish['test_source_sha256']==committed_digest('tools/fishing-tank-safety.test.mjs')
    if 'WitchWay' in policy['sources']:
        witch=current['sources']['WitchWay'];report=json.loads(members[witch['report']['name']])
        assert digest(members[witch['report']['name']])==witch['report']['sha256']
        assert report['status']=='PASS' and report['test_returncode']==0 and report['sources']==witch['source_integrity']
        assert all(report[key] is False for key in ['bds_verified','rendered_client_verified','production_ready','live_modified'])
        assert report['sources']['origin_status']=='unknown_current_local' and report['sources']['paired_runtime_identity_frozen'] is True
        assert report['test_source_sha256']==witch['test_source_sha256']==committed_digest('tools/witchway-native-drop-items.test.mjs')
        assert report['tool_sha256']==committed_digest('tools/witchway-native-drop-items.py')
        assert report['sources']['helper_sha256']==committed_digest('companion-sources/witchway-current-local/runtimeowner/BP/scripts/senluo/native-drop-items.js')
    for name,check in policy['functional_checks'].items():
        if name=='cookery-station-performance':continue
        count=check['cases']
        row=next(row for row in checks if row['name']==name);text=members[row['log']['name']].decode()
        cases=re.findall(r'^ok \d+ - (.+)$',text,re.M)
        totals={key:int(value) for key,value in re.findall(r'^# (tests|pass|fail|cancelled|skipped|todo) (\d+)$',text,re.M)}
        assert len(cases)==len(set(cases))==count and cases==row['test_cases']
        assert totals==row['test_totals']=={'tests':count,'pass':count,'fail':0,'cancelled':0,'skipped':0,'todo':0}
    assert digest(members[current['test_log']['name']])==current['test_log']['sha256']
    return set(current['artifact_members'])

def selected_report_members(checks,members):
    """Bind the selected original check reports, in addition to their real logs."""
    names=set()
    for row in checks:
        if row['name'].endswith('.json'):
            assert digest(members[row['name']])==row['report_sha256'],'Selected original check report differs'
            names.add(row['name'])
    return names

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

def validate_merged_source(pr,binding,full_tree):
    """Bind canonical evidence to the merged result, including current base changes."""
    verify_record(pr['head']['repo'],REPOSITORY);verify_record(pr['base']['repo'],REPOSITORY)
    assert pr['merged'] is True and pr['base']['ref']=='main'
    merged=pr['merge_commit_sha']
    c.git(c.EXTENSION,'merge-base','--is-ancestor',merged,binding['actual_current_source_commit'])
    assert c.git(c.EXTENSION,'rev-parse',merged+'^{tree}')==full_tree,'Current author merged PR whole tree differs'

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
    if curated_selected():
        assert proof['selected_profile']=={key:catalog['selection'][key] for key in ['path','sha256']}
        validate_curated_runtime(proof['owned_runtime'],baseline,catalog)
    if retained_selected():
        assert proof['component_version']==VERSION
        validate_retained_runtime(proof['owned_runtime'],baseline,binding)
        owned_component=proof['owned_runtime']['retained_component_conservation']
    else:owned_component=proof['owned_runtime']
    assert owned_component['previous_commit']==catalog['previous_commit']
    c.git(c.EXTENSION,'merge-base','--is-ancestor',catalog['previous_commit'],binding['actual_current_source_commit'])
    if curated_selected():authors=current_selection()
    else:
        authors=committed(catalog['authors_path'],catalog['authors_sha256'])
        assert authors['source_package_version']==VERSION
    assert authors['profile']==PROFILE and authors['authors']==catalog['authors']
    pr=gh_json(f'repos/{current_name(REPOSITORY)}/pulls/{c.CONFIG["extension_stable_pull_request"]}')
    validate_merged_source(pr,binding,proof['git_tree'])
    members,ci=artifact_members(int(c.CONFIG['extension_stable_run_id']),int(c.CONFIG['extension_stable_artifact_id']),proof['source_commit'],proof['git_tree'])
    assert members.get(path.name)==raw,'Current author proof differs from original CI artifact'
    active=functional_selected(baseline)
    expected_checks=set(current_selection()['checks']) if curated_selected() else CHECKS|({'current-runtime-functional.json'} if active else set())
    checks=proof['completed_checks'];assert isinstance(checks,list) and {row['name'] for row in checks}==expected_checks and len(checks)==len(expected_checks)
    if curated_selected():
        commands=current_selection()['check_commands']
        for row in checks:assert row['command']==commands[row['name']],'Curated check command differs from reviewed implementation'
    refs=[proof['test_log'],*[row['log'] for row in checks]]
    expected={path.name,*[ref['name'] for ref in refs]}
    if curated_selected():expected|=selected_report_members(checks,members)
    if active:expected|=validate_functional_artifacts(path,proof,baseline,members)
    assert set(proof['artifact_members'])==expected==set(members),'Current author artifact inventory differs'
    for ref in refs:
        member=sibling(path,ref);assert member.read_bytes()==members[ref['name']],'Current author CI log bytes differ'
    for name in expected:assert local(path.parent/name)==members[name],'Current functional artifact bytes differ from original CI'
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
    """Retain historical deltas; reviewed integration additionally admits only its exact removal."""
    VERSION=version if version is not None else settings()[0]
    changed=sorted('runtime/'+side+'/'+name for side in ['BP','RP'] for name in owned['files'][side].keys()&owned['previous_files'][side].keys() if owned['files'][side][name]!=owned['previous_files'][side][name])
    added=sorted('runtime/'+side+'/'+name for side in ['BP','RP'] for name in owned['files'][side].keys()-owned['previous_files'][side].keys())
    retired=sorted('runtime/'+side+'/'+name for side in ['BP','RP'] for name in owned['previous_files'][side].keys()-owned['files'][side].keys())
    assert changed==owned['exact_changed_paths'],'Current author conservation changed paths differ'
    assert added==owned['added_paths'],'Current author conservation added paths differ'
    assert retired==owned['retired_paths'],'Current author conservation retired paths differ'
    if catalog.get('selection',{}).get('value',{}).get('kind')==CURATED:
        for key,actual in [('exact_changed_paths',changed),('added_paths',added),('retired_paths',retired)]:
            expected=catalog[key]
            assert isinstance(expected,list) and expected==sorted(set(expected)) and actual==expected,'Curated conservation differs from reviewed '+key
            for value in expected:
                path=Path(value)
                assert len(path.parts)>=3 and path.parts[:2] in [('runtime','BP'),('runtime','RP')] and '..' not in path.parts and path.as_posix()==value and '\\' not in value
        return
    if VERSION==[1,0,57]:
        def reviewed_paths(key):
            paths=catalog[key]
            assert isinstance(paths,list) and all(isinstance(path,str) for path in paths),'reviewed integration conservation catalog paths must be a list'
            assert paths==sorted(set(paths)),'reviewed integration conservation catalog paths must be sorted and unique'
            for value in paths:
                path=Path(value)
                assert len(path.parts)>=3 and path.parts[:2] in [('runtime','BP'),('runtime','RP')] and '..' not in path.parts and path.as_posix()==value,'Unsafe reviewed integration conservation catalog path'
            return paths
        assert catalog['added_paths']==added==[],'reviewed integration cannot add unreviewed runtime content'
        assert retired==reviewed_paths('retired_paths') and retired,'reviewed integration retired content differs from the exact reviewed scope'
        assert changed==reviewed_paths('exact_changed_paths'),'reviewed integration changed content differs from the exact reviewed scope'
    if VERSION==[1,0,58]:
        for key,actual in [('exact_changed_paths',changed),('added_paths',added),('retired_paths',retired)]:
            expected=catalog[key]
            assert isinstance(expected,list) and all(isinstance(path,str) for path in expected) and expected==sorted(set(expected))
            assert actual==expected,'reviewed integration conservation differs from the exact reviewed '+key
            for value in expected:
                path=Path(value)
                assert len(path.parts)>=3 and path.parts[:2] in [('runtime','BP'),('runtime','RP')] and '..' not in path.parts and path.as_posix()==value
        assert retired==[],'reviewed integration cannot retire additional content'
        from family_update.preserved_client_assets_inputs import HELPER
        allowed_added={'runtime/BP/'+HELPER,'runtime/BP/client-repairs/repair-plan.json'}
        normals=[name for name in added if name.startswith('runtime/RP/textures/integration/fishing-normal/') and name.endswith('_normal.png')]
        assert len(normals)==156 and set(added)==allowed_added|set(normals),'reviewed integration additions exceed client helper/plan/normals'
        assert set(changed)=={'runtime/BP/manifest.json','runtime/RP/manifest.json',*['runtime/BP/host-extensions/'+name for name in catalog['host_specs']]},'reviewed integration runtime changes exceed paired identity/host declarations'

def validate_candidate(receipt,proof,baseline,binding,catalog):
    """Validate every output and the exact ordered chain, not just changed paths."""
    VERSION,PROFILE,CATALOG_KEY=settings()
    component_version=VERSION
    active=functional_selected(baseline)
    if retained_selected():
        assert proof['component_version']==component_version
        validate_retained_runtime(proof['owned_runtime'],baseline,binding)
        VERSION=baseline['version']
    selection=current_selection() if curated_selected() else None
    variant=None if selection else {55:[1,0,10655],56:[1,0,10656],57:[1,0,10657],58:[1,0,10658]}[component_version[-1]]
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
    from cookery_station_extension import (KIND as STATION_KIND, IDENTITY as STATION_ID,
        current_station_profile, active_api_declaration, validate_station_receipt_pair)
    public_path=c.SOURCES['grilling']/'projects/grilling/gameplay_core/behavior_pack/host-extensions/board-api.json'
    public_spec=c.read(public_path)
    specs={}
    records=dict(catalog['host_specs'])
    if active and not curated_selected():
        name='cookery-station-performance.json'
        contract=committed(CURRENT_CONTRACT)
        raw_sha=contract['domains']['cookery-station-performance']['runtime/BP/host-extensions/'+name]['after']
        spec=committed('runtime/BP/host-extensions/'+name,raw_sha)
        profile=current_station_profile(spec,c.EXTENSION/baseline['runtime']['BP'],public_spec,public_path.read_bytes(),c.SOURCES['grilling'])
        records[name]={'profile':profile['admission'],'sha256':raw_sha,'declaration_sha256':profile['spec_sha256']}
    assert set(proof['host_specs'])==set(records)
    for name,record in records.items():
        spec=committed('runtime/BP/host-extensions/'+name,record['sha256'])
        if spec.get('kind')==STATION_KIND:
            profile=current_station_profile(spec,c.EXTENSION/baseline['runtime']['BP'],public_spec,public_path.read_bytes(),c.SOURCES['grilling'])
            assert record['profile']==profile['admission'] and profile['spec_sha256']==record['declaration_sha256']
        else:
            profile=match_stable_profile(spec,c.EXTENSION/baseline['runtime']['BP'])
            assert profile==PROFILES[record['profile']] and profile['spec_sha256']==record['declaration_sha256']
        expected={'sha256':record['sha256'],'id':spec['id'],'host_uuid':spec['host_uuid'],'archive_sha256':spec['archive_sha256'],'original_files':spec['original_files'],'patched_files':spec['patched_files'],'copies_hashes':profile['copies']}
        if spec.get('kind')==STATION_KIND:expected['owner_handoff']=spec['owner_handoff']
        if spec.get('removed_files'):expected['removed_files']=spec['removed_files']
        assert proof['host_specs'][name]==expected,'Current author host proof differs from committed profile'
        specs[spec['id']]=(spec,profile,record['sha256'])
    public=public_profiles()[catalog['public_api_profile']];api=proof['public_api'];g=c.SOURCES['grilling']
    assert c.sha(public_path)==api['spec_sha256']==catalog['public_api_spec_sha256']
    assert match_stable_profile(public_spec)==public
    assert api['repository']==(current_name('casama233/kaleidoscope-grilling-unofficial') if curated_selected() else 'casama233/kaleidoscope-grilling-unofficial')
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
            expected_version=selection['pack_versions'][key][side] if selection else variant if key=='ChineseFood' else pin['author_version']
            assert pack['version']==expected_version
            current=dict(authored['original_files'][side])
            for index,extension in enumerate(extensions):
                prefix={**source,'owner':'upstream' if index==0 else 'upstream_extended','reviewed_extensions':extensions[:index]}
                if extension['id']==public['id']:
                    declared=public_spec;profile=public;spec_sha=catalog['public_api_spec_sha256'];repository=api['repository'];commit=c.git(g,'rev-parse','HEAD')
                    if extension.get('delegated_files'):
                        assert STATION_ID in specs,'Public station delegation has no current private source owner'
                        station_spec,station_profile,station_sha=specs[STATION_ID]
                        paired_owners=[row for row in extensions if row.get('id')==STATION_ID]
                        assert len(paired_owners)==1,'Public station delegation requires one completed private owner'
                        validate_station_receipt_pair(station_spec,station_profile,public_spec,extension,paired_owners[0],pack['files'],
                            owner_commit=binding['actual_current_source_commit'],owner_version=VERSION,spec_sha256=station_sha)
                        declared=active_api_declaration(public_spec)
                else:
                    assert extension['id'] in specs,'Unexpected current author host extension'
                    declared,profile,spec_sha=specs[extension['id']];repository=LOGICAL;commit=binding['actual_current_source_commit'];seen.add(extension['id'])
                if retained_selected() and repository==LOGICAL and declared.get('kind')!=STATION_KIND:
                    anchor=baseline['retained_runtime']
                    assert extension['source_package_version']==VERSION and extension['component_version']==component_version
                    assert extension['retained_runtime_profile']=={'schema':1,'source_commit':anchor['source_commit'],'source_tree':anchor['source_tree'],'source_version':component_version}
                if declared.get('kind')==STATION_KIND:
                    assert active and extension['owner_version']==VERSION
                    assert 'retained_runtime_profile' not in extension and 'component_version' not in extension
                paired=declared.get('kind') in {'chinesefood-doll-renderer-cleanup','essentials-manifest-compatibility'}
                if paired and side=='RP':
                    bp_extensions=rows[pin['behavior_uuid']]['source']['reviewed_extensions']
                    matching=[i for i,row in enumerate(bp_extensions) if row['id']==extension['id']];assert len(matching)==1
                    prefix={**source,'owner':'upstream' if matching[0]==0 else 'upstream_extended','reviewed_extensions':bp_extensions[:matching[0]]}
                validate_stable_source(profile,prefix)
                receipt_repository=extension['repository']
                if repository!=LOGICAL:
                    # Receipts keep their historical logical owner; CI records
                    # the reviewed current remote after the organization move.
                    receipt_repository=current_name(receipt_repository)
                    repository=current_name(repository)
                assert extension['spec_sha256']==spec_sha and receipt_repository==repository and extension['commit']==commit and extension['working_candidate'] is False,'Current author extension source binding differs: '+extension['id']
                assert extension['original_files']==declared['original_files'] and extension['patched_files']==declared['patched_files']
                assert extension.get('removed_files',{})==declared.get('removed_files',{}),'Current author removal receipt differs'
                if 'version' in declared:assert extension['version']==declared['version']
                else:assert extension['owner_version']==component_version and extension['local_pack_version']==(selection['pack_versions'][key][side] if selection else variant)
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
    if proof.get('owned_runtime',{}).get('kind')=='current_functional_runtime':
        for name in proof['artifact_members']:
            assert Path(name).name==name
            member=path.parent/name;local(member);paths.append(member)
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
    fresh=curated_selected() and bool(c.CONFIG.get('fresh_world'))
    assert evidence['client'] is False and evidence['simulated_players'] is False
    assert [row['phase'] for row in evidence['runs']]==['first','restart']
    if fresh:
        assert evidence['native_acceptance_source']=='fresh_world' and evidence['exact_files_checked'] is True and evidence['bds'] is True
        assert evidence['fresh_world_initialization'] is True and evidence['world_persistence'] is True
        assert evidence['saved_world_migration'] is False and evidence['existing_world_loaded'] is False and evidence['test_only_overlays']==[]
        assert all(row['ok'] and not row['errors'] and row['real_player_connections']==0 and row['generated_database'] is True and row['commands_sent'] is False for row in evidence['runs'])
    else:
        assert all(evidence[key] for key in ['fresh_stopped_backup','existing_world_loaded','exact_files_checked','bds','saved_world_migration'])
        from family_update.fishing_native_observer import validate_native_evidence as verify_fishing_observer
        verify_fishing_observer(evidence)
        assert all(row['ok'] and not row['errors'] and row['real_player_connections']==0 and all(row[key] for key in ['player_records_unchanged','custom_container_inventories_retained','native_freezer_inputs_retained']) for row in evidence['runs'])
    c.atomic(c.R/'current-author-native-validation.json',{'schema':1,'profile':PROFILE,'version':VERSION,**({'component_version':settings()[0]} if retained_selected() else {}),'static':c.report_ref(c.R/'current-author-static-validation.json'),'fresh_native':c.report_ref(c.R/'saved-world-report.json'),'candidate_receipt_sha256':evidence['candidate_receipt_sha256'],'affected_packs':static['affected_packs'],'native_loading':True,'saved_world_migration':not fresh,**({'native_acceptance_source':'fresh_world','fresh_world_initialization':True,'world_persistence':True} if fresh else {}),'client':False,'production_ready':False})

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
    assert native['native_loading'] is True and native['client'] is False and native['production_ready'] is False
    if curated_selected() and c.CONFIG.get('fresh_world'):
        assert native['native_acceptance_source']=='fresh_world' and native['saved_world_migration'] is False
        assert native['fresh_world_initialization'] is True and native['world_persistence'] is True
    else:assert native['saved_world_migration'] is True
