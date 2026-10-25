"""Admit an exact reviewed integration without relabelling historical payloads.

Public policy contains only hashes and common manifest/recipe contracts. Private
runtime is neither imported nor copied. A successful check is source admission,
never native, saved-world, rendering or performance acceptance.
"""
from pathlib import Path
import collections,copy,hashlib,io,json,re,subprocess

PROFILES={(1,0,64):{
    'kind':'aww-exact-four-file',
    'contract':'data/aww-p64-runtime-contract.json',
    'contract_sha256':'4d547d207dd9bf1f9c2f2cbe19123dc5d4e87ac31a253c4e3d126240acae1e3f',
    'fishing_inputs':'data/fishing-1.3-salt-inputs.json',
    'fishing_sha256':'c0927a8c463081cd207daf44403eb37863ecdbafa7e415d61fd457adf2b9b4eb'}}
CHANGED=['runtime/BP/manifest.json','runtime/RP/manifest.json',
         'runtime/RP/ui/_global_variables.json','runtime/RP/ui/hud_screen.json']
FISH='5e121bf2-1d2d-4da4-be15-cffc5f216d94'
AMW='994f73a2-05ec-41ce-876c-d388a526d9f5'
AWW='d8a147c2-5b9e-4c11-9a32-7e418f20b201'

def sha(raw):return hashlib.sha256(raw).hexdigest()
def git(root,*args):return subprocess.check_output(['git',*args],cwd=root)
def blob(root,commit,path):return git(root,'show',commit+':'+path)
def committed(root,path):
    p=root/path
    assert not p.is_symlink() and p.is_file(),'Missing/linked integration input'
    raw=p.read_bytes();assert raw==blob(root,'HEAD',path),'Uncommitted integration input'
    return raw
def inventory(root,config):
    result={}
    for side,relative in config['runtime'].items():
        directory=root/relative;assert directory.is_dir() and not directory.is_symlink()
        rows={}
        for p in sorted(directory.rglob('*')):
            assert not p.is_symlink(),'Linked integration runtime'
            if p.is_file():rows[p.relative_to(directory).as_posix()]=sha(p.read_bytes())
        result[side]=rows
    return result
def git_inventory(root,commit):
    rows=git(root,'ls-tree','-r','-z',commit,'--','runtime').split(b'\0')
    result={'BP':{},'RP':{}}
    blobs=[]
    for row in filter(None,rows):
        meta,path=row.split(b'\t',1);mode,kind,oid=meta.split()
        assert mode==b'100644' or mode==b'100755','Linked/special integration anchor'
        assert kind==b'blob'
        name=path.decode();side,relative=name.removeprefix('runtime/').split('/',1)
        assert side in result and Path(relative).as_posix()==relative
        blobs.append((side,relative,oid.decode()))
    output=subprocess.check_output(['git','cat-file','--batch'],cwd=root,
        input=('\n'.join(row[2] for row in blobs)+'\n').encode())
    stream=io.BytesIO(output)
    for side,relative,oid in blobs:
        actual,kind,size=stream.readline().split();assert actual.decode()==oid and kind==b'blob'
        result[side][relative]=sha(stream.read(int(size)));assert stream.read(1)==b'\n'
    return result

def validate_salt_inputs(root,policy):
    raw=committed(root,policy['fishing_inputs'])
    assert sha(raw)==policy['fishing_sha256'],'Unreviewed Fishing source'
    value=json.loads(raw);manifest=value['manifest']
    assert value['schema']==1 and value['kind']=='captured-local-fishing-salt-inputs'
    assert manifest['header']['uuid']==FISH and manifest['header']['version']==[1,3,0]
    assert re.fullmatch('[0-9a-f]{64}',value['manifest_sha256'])
    assert all(value[k] is False for k in ['original_author_archive_verified','latest_author_release_verified','native','client'])
    recipes=value['recipes']
    ids=['kaleidoscope_fishing:salt_bucket','kaleidoscope_fishing:salt_from_bucket','kaleidoscope_fishing:grilled_fish_plank']
    assert set(recipes)==set(ids)
    for name,record in recipes.items():
        assert record['definition']['description']['identifier']==name
        assert re.fullmatch('[0-9a-f]{64}',record['sha256']) and record['file'].startswith('recipes/')
    furnace=recipes[ids[0]];assert furnace['kind']=='minecraft:recipe_furnace'
    assert furnace['definition']['input']=='minecraft:water_bucket' and furnace['definition']['output']==ids[0]
    assert set(furnace['definition']['tags'])=={'furnace','smoker','campfire'}
    salt=recipes[ids[1]];assert salt['kind']=='minecraft:recipe_shaped'
    assert salt['definition']['pattern']==['S'] and salt['definition']['key']=={'S':{'item':ids[0]}}
    assert salt['definition']['result']==[{'item':'kaleidoscope_fishing:sea_salt','count':3},{'item':'minecraft:bucket','count':1}]
    original=recipes[ids[2]];assert original['kind']=='minecraft:recipe_shapeless'
    expected=copy.deepcopy(original['definition'])
    expected['description']['identifier']='senluo:fishing_grilled_fish_plank_cf_salt'
    for ingredient in expected['ingredients']+expected['unlock']:
        if ingredient.get('item')=='kaleidoscope_fishing:sea_salt':ingredient['item']='kaleidoscope_chinesefood:salt'
    actual=json.loads(committed(root,'runtime/BP/recipes/alternatives/fishing_grilled_fish_plank_cf_salt.json'))['minecraft:recipe_shapeless']
    assert actual==expected,'Fishing salt coexistence recipe differs'
    needs=collections.Counter(row.get('item','#'+row.get('tag','')) for row in actual['ingredients'])
    assert needs==collections.Counter({'kaleidoscope_fishing:grilled_fish':2,'kaleidoscope_chinesefood:salt':1,'#minecraft:wooden_slabs':1})
    assert actual['result']=={'item':ids[2],'count':1}
    return [1,3,0]

def validate_exact_integration(owned,baseline,binding,root,sources):
    from family_update.current_author_validation import _validate_dependency_only_runtime,tree
    root=Path(root)
    policy=PROFILES.get(tuple(baseline['version']));assert policy,'Unknown integration version'
    assert owned['kind']==policy['kind'],'P64 cannot impersonate a dependency-only release'
    current=git(root,'rev-parse','HEAD').decode().strip()
    assert current==binding['actual_current_source_commit'] and not git(root,'status','--porcelain').strip(),'Dirty or wrong current source'
    assert json.loads(committed(root,'baseline.json'))==baseline
    pin=baseline['integration_runtime']
    assert pin['kind']==policy['kind'] and pin['contract']==policy['contract']
    raw=committed(root,policy['contract'])
    assert sha(raw)==pin['contract_sha256']==policy['contract_sha256'],'Unreviewed integration contract'
    contract=json.loads(raw);base=contract['base_commit']
    assert contract['schema']==1 and contract['kind']==policy['kind'] and contract['version']==baseline['version']
    assert re.fullmatch('[0-9a-f]{40}',base) and pin['base_commit']==base
    assert git(root,'rev-parse',base+'^{tree}').decode().strip()==pin['base_tree'],'Wrong integration anchor tree'
    git(root,'merge-base','--is-ancestor',base,current)
    prior=json.loads(blob(root,base,'baseline.json'))
    assert prior['repository']==baseline['repository']=='local/senluo-amw-cuisine'
    assert prior['version']==[1,0,62] and baseline['version']==[1,0,64]
    assert prior['runtime']==baseline['runtime']=={'BP':'runtime/BP','RP':'runtime/RP'}
    assert baseline['retained_runtime']==prior['retained_runtime'],'Changed historical anchor'
    before=git_inventory(root,base);after=inventory(root,baseline)
    assert before==owned['previous_files'] and after==owned['files'],'Proof differs from actual Git/current runtime'
    assert {s:tree(v) for s,v in before.items()}==prior['source_trees']
    assert {s:tree(v) for s,v in after.items()}==baseline['source_trees']==contract['source_trees']==owned['source_trees']
    assert all(set(before[s])==set(after[s]) for s in before),'Added/retired runtime file'
    changed=sorted('runtime/'+s+'/'+n for s in before for n in before[s] if before[s][n]!=after[s][n])
    assert changed==sorted(CHANGED)==contract['exact_changed_paths']==owned['exact_changed_paths'],'Unexpected integration delta'
    assert owned['previous_commit']==base and owned['version']==baseline['version'] and owned['source_version']==[1,0,58]
    assert sum(len(v) for v in before.values())-len(CHANGED)==contract['conserved_files']==owned['conserved_files']==368
    assert contract['added_paths']==contract['retired_paths']==[] and set(contract['changed_files'])==set(CHANGED)
    for name in CHANGED:
        side,relative=name.removeprefix('runtime/').split('/',1)
        assert contract['changed_files'][name]=={'before':before[side][relative],'after':after[side][relative]},'Wrong reviewed file hash'
    for k in ['client','native','performance','production_ready','live','publication_request']:
        assert owned[k] is False and contract[k] is False
    # Keep the old P62/P58 checks intact, reading P62 manifests from its Git
    # snapshot instead of pretending the current P64 files are conserved P58.
    historical=owned['historical_p62_conservation']
    assert 'retained_component_conservation' not in historical,'Unexpected historical proof shape'
    # The honest producer emits the P62 comparison and P58 component as peers.
    # Compose those two real proofs only for the unchanged legacy validator.
    component=owned['retained_component_conservation']
    assert component['core_only'] is True
    assert component['conserved_files']==sum(1 for side in component['files']
        for name in component['files'][side].keys()&component['previous_files'][side].keys()
        if component['files'][side][name]==component['previous_files'][side][name]),'Incorrect component conservation count'
    legacy={**historical,'retained_component_conservation':component}
    _validate_dependency_only_runtime(legacy,prior,{'actual_current_source_commit':base},root,sources,reference_commit=base)
    fishing=validate_salt_inputs(root,policy)
    uuids={v['uuid'] for v in prior['packs'].values()}
    for side in ['BP','RP']:
        expected=json.loads(blob(root,base,'runtime/'+side+'/manifest.json'))
        expected['header']['version']=baseline['version']
        for module in expected['modules']:module['version']=baseline['version']
        for dep in expected.get('dependencies',[]):
            if dep.get('uuid') in uuids:dep['version']=baseline['version']
            elif side=='BP' and dep.get('uuid')==FISH:dep['version']=fishing
            elif side=='RP' and dep.get('uuid')==AMW:dep.update(uuid=AWW,version=[1,3,0])
        actual=json.loads(committed(root,'runtime/'+side+'/manifest.json'))
        assert actual==expected,'Manifest differs outside exact owning/Fishing/AWW changes'
        assert baseline['packs'][side]=={'uuid':actual['header']['uuid'],'dependencies':actual['dependencies']}
    return owned
