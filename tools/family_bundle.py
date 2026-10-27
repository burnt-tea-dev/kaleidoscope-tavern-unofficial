#!/usr/bin/env python3
"""Assemble exact owned runtimes plus hash-pinned upstream archives and declared canonical host extensions."""
from pathlib import Path,PurePosixPath
import argparse,hashlib,io,json,os,re,shutil,subprocess,zipfile
from host_extensions import apply_host_extension
from retained_host_profiles import retained_host_source
from paired_host_extension import DATA_REPAIRS,PAIRED_KINDS,pair_uuids
ROOT=Path(__file__).resolve().parents[1]
def fail(message):raise SystemExit('FAMILY: '+message)
def read(path):return json.loads(path.read_text(encoding='utf-8-sig'))
def validate_client_scripts(obj,path):
 if not isinstance(obj,dict) or obj.get('format_version')!='1.8.0':return
 scripts=obj.get('minecraft:client_entity',{}).get('description',{}).get('scripts',{})
 if 'initialize' in scripts:fail('client_entity format 1.8.0 does not support scripts.initialize: '+str(path))
def read_definition(path,jsonc=False,*,object_pairs_hook=None):
 raw=path.read_text(encoding='utf-8-sig')
 try:return json.loads(raw,object_pairs_hook=object_pairs_hook)
 except json.JSONDecodeError:
  if not jsonc:raise
 # Bedrock JSONC is allowed in preserved third-party definitions. Only the
 # scanner parses it; copied bytes and their per-file receipts stay untouched.
 raw=re.sub(r'"(?:\\.|[^"\\])*"|//[^\n]*|/\*.*?\*/',lambda m:m[0] if m[0].startswith('"') else '',raw,flags=re.S)
 raw=re.sub(r'"(?:\\.|[^"\\])*"|,\s*([}\]])',lambda m:m[0] if m[0].startswith('"') else m[1],raw)
 return json.loads(raw,object_pairs_hook=object_pairs_hook)
def files_hash(root):return {p.relative_to(root).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(root.rglob('*')) if p.is_file()}
def packs(z):
 names=z.namelist()
 if len(names)!=len(set(names)):fail('duplicate ZIP entries')
 for n in names:
  parts=PurePosixPath(n)
  if parts.is_absolute() or '..' in parts.parts or '\\' in n:fail('unsafe archive path')
  if (z.getinfo(n).external_attr>>16)&0o170000==0o120000:fail('symlink in archive')
  if n.endswith('.mcpack'):
   with zipfile.ZipFile(io.BytesIO(z.read(n))) as sub:yield from packs(sub)
 for n in names:
  if n.split('/')[-1]!='manifest.json':continue
  m=json.loads(z.read(n).decode('utf-8-sig'))
  if 'header' not in m:continue
  pre=n[:-len('manifest.json')]
  data={x[len(pre):]:z.read(x) for x in names if x.startswith(pre) and not x.endswith('/') and not x.endswith('.mcpack')}
  yield m,data

def source_gate_environment(own,identities,repo=None):
 # A multi-repository CI caller may supply independently verified identities.
 # Never derive the expected identity from the source config being checked.
 # Default callers retain their original inherited-environment gate semantics.
 if identities is None:return None
 expected=identities.get(own['key']) if isinstance(identities,dict) else None
 if not isinstance(expected,dict) or expected.get('repository')!=own['repository'] or type(expected.get('repository_id')) is not int or expected['repository_id']<=0:
  fail('invalid expected gate repository identity: '+own['key'])
 environment={**os.environ,'GITHUB_REPOSITORY':expected['repository'],'GITHUB_REPOSITORY_ID':str(expected['repository_id'])}
 if repo is not None and (repo/'.repo-target.json').exists():
  from family_update.repository_identity import target
  current=target(expected['repository']);metadata=read(repo/'.repo-target.json')
  if current['repository_id']!=expected['repository_id'] or metadata.get('logical_runtime_repository')!=own['repository'] or any(metadata.get(k)!=v for k,v in current.items()):fail('invalid reviewed current source target')
  environment.update(GITHUB_REPOSITORY=current['repository'],SENLUO_SOURCE_GATE='1')
 return environment

def renderer_source_version(config,spec,path):
 # The fixed cache/guide and later HUD/dependency updates retain unchanged ChineseFood graphics.
 # This single, immutable retained component is independently checked again
 # by the version-specific private source conservation gate before live admission.
 profile=config.get('retained_renderer_profile')
 if profile is None:return config['version']
 expected={'source_commit':'8d05a3da291861048dc7e759be3ba96fde45ebb8',
           'spec_sha256':'292e337a073ea713c22c84c66f85a2c8cb9d2d5c453c308b1569107d2656b703'}
 if config['repository']!='local/senluo-amw-cuisine' or config['version'] not in [[1,0,33],[1,0,34],[1,0,35],[1,0,36],[1,0,37],[1,0,38],[1,0,39],[1,0,40]] or profile!=expected:
  fail('unsupported retained renderer source profile')
 if spec.get('owner_version')!=[1,0,32] or hashlib.sha256(path.read_bytes()).hexdigest()!=expected['spec_sha256']:
  fail('retained renderer component differs from reviewed reviewed integration')
 return [1,0,32]

def retained_component_config(repo,config,sources):
 # The private producer emits only the existing conservation metadata. Public
 # validation independently checks its complete hashes and exact manifests.
 curated=config.get('current_author_profile') is not None
 if not curated and config.get('retained_runtime') is None:return config,None
 from family_update.current_author_validation import validate_retained_runtime,validate_curated_runtime
 if curated:
  from stable_host_profiles import curated_profile
  catalog=curated_profile()
 current=subprocess.check_output(['git','rev-parse','HEAD'],cwd=repo,text=True).strip()
 raw=subprocess.check_output(['python3',str(repo/'tools/current_release.py')],cwd=repo)
 proof=json.loads(raw)
 if curated:validate_curated_runtime(proof,config,catalog,source_root=repo)
 else:validate_retained_runtime(proof,config,{'actual_current_source_commit':current},source_root=repo,sources=sources)
 for side,relative in config['runtime'].items():
  if files_hash(repo/relative)!=proof['files'][side]:fail('retained current source payload differs from proof')
 if curated:return config,None
 anchor=config['retained_runtime']
 component=json.loads(subprocess.check_output(['git','show',anchor['source_commit']+':baseline.json'],cwd=repo))
 return component,{'schema':1,'source_commit':anchor['source_commit'],'source_tree':anchor['source_tree'],'source_version':anchor['source_version']}

def assemble(lock,sources,archives,out,working=False,extensions=(),preserved=(),reviewed_order=None,held_sources=(),source_identities=None,preserved_sources=None):
 from family_update.source_holds import selected,effective
 holds=selected(lock,list(held_sources));lock=effective(lock,list(held_sources))
 lock=json.loads(json.dumps(lock))
 if reviewed_order is not None:
  if not isinstance(reviewed_order,dict) or set(reviewed_order)!={'behavior','resource'}:fail('reviewed order requires both pack sides')
  for side,uids in reviewed_order.items():
   if not isinstance(uids,list) or any(not isinstance(uid,str) or not uid for uid in uids) or len(uids)!=len(set(uids)):fail('invalid reviewed pack order')
  lock['order']=json.loads(json.dumps(reviewed_order))
 # Optional local integrations have their own committed runtime and release
 # history. They never rewrite an owned port or an upstream author archive.
 for repo in extensions:
  config=read(repo/'baseline.json');key=config['repository']
  if key in sources:fail('duplicate extension source')
  sources={**sources,key:repo}
  lock['owned'].append({'key':key,'repository':key,'version':config['version'],'source_trees':config['source_trees']})
  for side,label in [('BP','behavior'),('RP','resource')]:
   uid=config['packs'][side]['uuid']
   if reviewed_order is None:
    if uid in lock['order'][label]:fail('extension collides with locked pack')
    lock['order'][label].insert(0,uid)
 if source_identities is not None:
  if working:fail('expected gate repository identities require strict committed sources')
  if not isinstance(source_identities,dict) or set(source_identities)!={own['key'] for own in lock['owned']}:
   fail('expected gate repository identities must cover exactly the selected owned sources')
  for own in lock['owned']:source_gate_environment(own,source_identities)
 if out.exists():fail('output exists; never replace another candidate')
 out.mkdir(parents=True);records=[];by_uuid={};components={}
 # Index every candidate archive once. Read and recheck the selected bytes at
 # use time so a concurrent file replacement cannot exploit the index.
 archive_index={}
 for archive in dict.fromkeys(archives):
  digest=hashlib.sha256(archive.read_bytes()).hexdigest()
  archive_index.setdefault(digest,[]).append(archive)
 def add(source,manifest,data=None,root=None):
  uid=manifest['header']['uuid'];side='resource' if any(x['type']=='resources' for x in manifest['modules']) else 'behavior'
  if uid in by_uuid:fail('duplicate pack UUID '+uid)
  dest=out/(side+'_packs')/uid
  if root:
   before=files_hash(root);shutil.copytree(root,dest)
   copied=files_hash(dest)
   if files_hash(root)!=before or copied!=before:fail('source changed during candidate copy')
  else:
   for name,b in data.items():
    target=dest/name;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(b)
  row={'uuid':uid,'side':side,'version':manifest['header']['version'],'source':source,'dependencies':manifest.get('dependencies',[]),'files':copied if root else files_hash(dest)};records.append(row);by_uuid[uid]=row
 for own in lock['owned']:
  repo=sources[own['key']]
  config=read(repo/'baseline.json')
  if own.get('version')!=config['version'] or own.get('source_trees')!=config['source_trees']:fail('owned source differs from family lock')
  if not working:subprocess.run(['python3',str(repo/'tools/baseline_gate.py'),'check','--release'],check=True,env=source_gate_environment(own,source_identities,repo))
  if config['repository']!=own['repository']:fail('wrong owned repository')
  try:components[own['key']]=retained_component_config(repo,config,sources)
  except (AssertionError,ValueError,KeyError) as error:fail('retained runtime rejected: '+str(error))
  for side,relative in config['runtime'].items():
   root=repo/relative;m=read(root/'manifest.json');source={'owner':'owned','repository':config['repository'],'commit':subprocess.check_output(['git','rev-parse','HEAD'],cwd=repo,text=True).strip(),'working_candidate':working}
   if own['key'] in holds:
    if source['commit']!=holds[own['key']]['commit']:fail('held source revision differs')
    source['held_revision']=holds[own['key']]
   add(source,m,root=root)
 for upstream in lock['upstream']:
  matches=archive_index.get(upstream['sha256'],[])
  if not matches:fail('missing hash-pinned upstream archive: '+upstream['name'])
  archive_bytes=matches[0].read_bytes()
  if hashlib.sha256(archive_bytes).hexdigest()!=upstream['sha256']:fail('upstream archive changed after indexing: '+upstream['name'])
  with zipfile.ZipFile(io.BytesIO(archive_bytes)) as z:
   found=[]
   for manifest,data in packs(z):
    header=manifest['header'];found.append({'uuid':header['uuid'],'version':header['version']});add({'owner':'upstream','project_id':upstream['project_id'],'file_id':upstream['file_id'],'archive_sha256':upstream['sha256']},manifest,data=data)
   if sorted(found,key=lambda p:p['uuid'])!=sorted(upstream['packs'],key=lambda p:p['uuid']):fail('official pack identity differs from lock')
 # Resolve current module ownership from both exact source checkouts before the
 # public API runs. Its delegated file stays clean until the one current owner.
 from cookery_station_extension import collect_station_handoffs,verify_station_handoffs
 try:station_handoffs=collect_station_handoffs(lock['owned'],sources)
 except (ValueError,KeyError) as error:fail('station owner handoff rejected: '+str(error))
 # Only committed owned runtimes may declare a reviewed extension of a pinned host.
 # Spec and module bytes are in that runtime's versioned baseline, never a BSM hook.
 for own in lock['owned']:
  repo=sources[own['key']];config=read(repo/'baseline.json');owned_root=repo/config['runtime']['BP']
  source_component,retained_runtime=components[own['key']]
  for path in sorted((owned_root/'host-extensions').glob('*.json'),key=lambda p:(read(p).get('kind')=='chinesefood-doll-renderer-cleanup',read(p).get('kind')=='cookery-guide-startup-repair',p.name)):
   spec=read(path)
   if spec.get('kind') in PAIRED_KINDS:
    renderer=spec['kind']=='chinesefood-doll-renderer-cleanup'
    if renderer:
     from doll_renderer_extension import apply_renderer_extension as apply_pair
    elif spec['kind']=='essentials-manifest-compatibility':
     from essentials_manifest_extension import apply_manifest_extension as apply_pair
    elif spec['kind'] in DATA_REPAIRS:
     from paired_host_extension import apply_paired_data_extension as apply_pair
    else:
     from nether_placeable_extension import apply_nether_extension as apply_pair
    bp_uuid,rp_uuid=pair_uuids(spec)
    bp=by_uuid.get(bp_uuid);rp=by_uuid.get(rp_uuid)
    if not bp or not rp:fail('paired host extension requires complete author pair')
    try:retained=retained_host_source(source_component,spec,path)
    except ValueError as e:fail('paired host retention rejected: '+str(e))
    extension_version=retained['owner_version'] if retained else (renderer_source_version(source_component,spec,path) if renderer else source_component['version'])
    try:proof=apply_pair(spec,out/'behavior_packs'/bp['uuid'],out/'resource_packs'/rp['uuid'],bp['source'],rp['source'],extension_version)
    except (ValueError,KeyError) as e:fail('paired host extension rejected: '+str(e))
    proof.update({'repository':config['repository'],'commit':subprocess.check_output(['git','rev-parse','HEAD'],cwd=repo,text=True).strip(),'source_package_version':config['version'],'spec_sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'working_candidate':working,'official_author_release':False})
    if retained_runtime:proof.update(component_version=source_component['version'],retained_runtime_profile=retained_runtime)
    if retained:proof['retained_host_profile']=retained
    elif renderer and extension_version!=source_component['version']:proof['retained_renderer_profile']=config['retained_renderer_profile']
    for row in [bp,rp]:
     root=out/(row['side']+'_packs')/row['uuid'];manifest=read(root/'manifest.json')
     row.update(version=manifest['header']['version'],dependencies=manifest.get('dependencies',[]),files=files_hash(root))
     row['source']={**row['source'],'owner':'upstream_extended','reviewed_extensions':[*row['source'].get('reviewed_extensions',[]),proof]}
     if spec.get('official_author_release') is False:row['source']['official_author_release']=False
    continue
   retained=None
   if config.get('version') in ([1,0,51],[1,0,52],[1,0,53],[1,0,54]) and spec.get('kind') in ('cookery-held-geometry-canonicalization','cookery-millstone-extension-admission'):
    try:retained=retained_host_source(source_component,spec,path)
    except ValueError as e:fail('host retention rejected: '+str(e))
   component_config={**source_component,'version':retained['owner_version']} if retained else source_component
   if spec.get('kind')=='cookery-held-geometry-canonicalization':
    from held_geometry_extension import validate_held_geometry_owner
    try:validate_held_geometry_owner(component_config,spec)
    except ValueError as e:fail('host extension owner rejected: '+str(e))
   if spec.get('kind')=='cookery-millstone-extension-admission':
    from millstone_extension import validate_millstone_owner
    try:validate_millstone_owner(component_config,spec)
    except ValueError as e:fail('host extension owner rejected: '+str(e))
   if spec.get('kind')=='cookery-enamel-basin-lid-repair':
    from enamel_basin_extension import validate_enamel_basin_owner
    try:
     retained=retained_host_source(source_component,spec,path) if config.get('version') in ([1,0,50],[1,0,51],[1,0,52],[1,0,53],[1,0,54]) else None
     validate_enamel_basin_owner({**source_component,'version':retained['owner_version']} if retained else source_component,spec)
    except ValueError as e:fail('host extension owner rejected: '+str(e))
   host=by_uuid.get(spec['host_uuid'])
   if host is None:fail('host extension target missing')
   host_root=out/(host['side']+'_packs')/host['uuid']
   context={}
   station=station_handoffs.get(spec.get('host_uuid'))
   if station is not None and ((own['key']==station['api_key'] and spec.get('id')==station['api']['id']) or (own['key']==station['private_key'] and spec.get('kind')=='cookery-station-performance')):
    context['station_handoff']=station
   if retained_runtime and spec.get('removed_files'):
    context['retained_owner']={'source_root':str(repo.resolve()),'source_commit':subprocess.check_output(['git','rev-parse','HEAD'],cwd=repo,text=True).strip(),'sources':{key:str(value.resolve())for key,value in sources.items()}}
   try:proof=apply_host_extension(spec,owned_root,host_root,host['source'],**context)
   except (ValueError,KeyError) as e:fail('host extension rejected: '+str(e))
   current_station=spec.get('kind')=='cookery-station-performance'
   proof.update({'repository':config['repository'],'commit':subprocess.check_output(['git','rev-parse','HEAD'],cwd=repo,text=True).strip(),'owner_version':config['version'] if current_station else source_component['version'],'spec_sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'working_candidate':working})
   if retained_runtime and not current_station:proof.update(source_package_version=config['version'],component_version=source_component['version'],retained_runtime_profile=retained_runtime)
   if retained:
    proof.update(owner_version=retained['owner_version'],source_package_version=config['version'],retained_host_profile=retained)
   host['source']={**host['source'],'owner':'upstream_extended','reviewed_extensions':[*host['source'].get('reviewed_extensions',[]),proof]};host['files']=files_hash(host_root)
 try:verify_station_handoffs(station_handoffs,records,out)
 except (ValueError,KeyError) as error:fail('station owner handoff incomplete: '+str(error))
 if preserved_sources is None:preserved_sources={}
 if (not isinstance(preserved_sources,dict) or any(not isinstance(uid,str) or not uid or not isinstance(source,dict) or source.get('owner')!='preserved' or source.get('official_author_release') is True for uid,source in preserved_sources.items())):fail('preserved source descriptors must retain preserved ownership')
 used_preserved_sources=set()
 for root in preserved:
  manifest=read(root/'manifest.json');uid=manifest['header']['uuid']
  source=preserved_sources.get(uid,{'owner':'preserved','role':'unchanged_external_dependency'})
  if uid in preserved_sources:used_preserved_sources.add(uid)
  add(json.loads(json.dumps(source)),manifest,root=root)
  label=by_uuid[uid]['side']
  if reviewed_order is None:lock['order'][label].append(uid)
 if used_preserved_sources!=set(preserved_sources):fail('preserved source descriptor has no exact input UUID')
 for row in records:
  for dep in row['dependencies']:
   if 'uuid' in dep and (dep['uuid'] not in by_uuid or by_uuid[dep['uuid']]['version']!=dep['version']):fail('unresolved exact dependency '+row['uuid']+' -> '+dep['uuid'])
 for side in ['behavior','resource']:
  if reviewed_order is not None and any(uid not in by_uuid or by_uuid[uid]['side']!=side for uid in lock['order'][side]):fail('reviewed order contains unknown or wrong-side identity')
  order=[uid for uid in lock['order'][side] if uid in by_uuid and by_uuid[uid]['side']==side]
  expected={p['uuid'] for p in records if p['side']==side}
  if len(order)!=len(set(order)) or set(order)!=expected:fail('pack order missing or duplicate identity')
  (out/('world_'+side+'_packs.json')).write_text(json.dumps([{'pack_id':uid,'version':by_uuid[uid]['version']} for uid in order],indent=2)+'\n')
 definitions={};overlaps=[];behavior_player=None
 for side in ['behavior','resource']:
  # First world ref has priority. Report effective owner; do not silently merge definitions.
  order=lock['order'][side]
  for uid in order:
   root=out/(side+'_packs')/uid
   for path in root.rglob('*.json'):
    try:obj=read_definition(path,by_uuid[uid]['source']['owner']=='preserved')
    except Exception as e:fail('invalid JSON '+str(path)+': '+str(e))
    for key in ['minecraft:item','minecraft:block','minecraft:entity','minecraft:client_entity']:
     identifier=obj.get(key,{}).get('description',{}).get('identifier') if isinstance(obj,dict) else None
     if not identifier:continue
     if key=='minecraft:client_entity' and (side,key,identifier) not in definitions:validate_client_scripts(obj,path)
     if side=='behavior' and key=='minecraft:entity' and identifier=='minecraft:player':
      if behavior_player is not None:fail('competing behavior minecraft:player definitions: '+behavior_player['uuid']+' and '+uid)
      behavior_player={'uuid':uid,'path':path.relative_to(root).as_posix(),'sha256':hashlib.sha256(path.read_bytes()).hexdigest()}
     identity=(side,key,identifier)
     if identity in definitions:overlaps.append({'kind':key,'identifier':identifier,'effective_uuid':definitions[identity],'shadowed_uuid':uid})
     else:definitions[identity]=uid
 receipt={'schema':1,'lock_sha256':hashlib.sha256(json.dumps(lock,sort_keys=True).encode()).hexdigest(),'packs':records,'order':lock['order'],'definition_overlaps':overlaps,'behavior_player_definition':behavior_player,'acceptance':{'static':True,'bds':False,'client':False,'saved_world_migration':False},'production_ready':False}
 (out/'family-receipt.json').write_text(json.dumps(receipt,indent=2)+'\n');print(json.dumps({'candidate':str(out),'packs':len(records),'overlaps':len(overlaps),'production_ready':False}))
 return receipt

def audit(world,receipt):
 errors=[];expected={}
 for pack in receipt['packs']:
  root=world/(pack['side']+'_packs')/pack['uuid'];actual=files_hash(root)
  if actual!=pack['files']:errors.append({'uuid':pack['uuid'],'changed':sorted(k for k in actual.keys()&pack['files'].keys() if actual[k]!=pack['files'][k]),'missing':sorted(pack['files'].keys()-actual.keys()),'extra':sorted(actual.keys()-pack['files'].keys())})
  expected[pack['uuid']]=pack
 for side,order in receipt['order'].items():
  refs=read(world/('world_'+side+'_packs.json'));want=[{'pack_id':uid,'version':expected[uid]['version']} for uid in order]
  if refs!=want:errors.append({'side':side,'error':'pack order/version references differ'})
 if errors:fail(json.dumps(errors,ensure_ascii=False))
 print('Family files and world order match the deployment receipt')

def main():
 p=argparse.ArgumentParser(description=__doc__);sub=p.add_subparsers(dest='command',required=True)
 b=sub.add_parser('build');b.add_argument('--tavern',type=Path,default=ROOT);b.add_argument('--grilling',type=Path,required=True);b.add_argument('--world-liquor',type=Path,required=True);b.add_argument('--archives',type=Path,action='append',required=True);b.add_argument('--output',type=Path,required=True);b.add_argument('--extension',type=Path,action='append',default=[],help='Committed local integration with the same canonical baseline gate and release history');b.add_argument('--working-candidate',action='store_true',help='isolated BDS development only; receipt never authorizes production')
 b.add_argument('--preserved-pack',type=Path,action='append',default=[],help='Unchanged external dependency copied with an exact per-file receipt')
 g=sub.add_parser('build-public-grilling',help='Build a local public Grilling/Cookery bundle from one legal clean author archive')
 g.add_argument('--grilling',type=Path,required=True);g.add_argument('--tavern',type=Path);g.add_argument('--archives',type=Path,action='append',required=True);g.add_argument('--output',type=Path,required=True)
 a=sub.add_parser('audit');a.add_argument('--world',type=Path,required=True);a.add_argument('--receipt',type=Path,required=True)
 args=p.parse_args()
 if args.command=='audit':audit(args.world,read(args.receipt));return
 if args.command=='build-public-grilling':
  from public_grilling_profile import build_public_grilling
  sources={'grilling':args.grilling}
  if args.tavern is not None:sources['tavern']=args.tavern
  build_public_grilling(read(ROOT/'family/upstream.lock.json'),sources,args.archives,args.output,assemble_family=assemble,read_author_packs=packs)
  return
 paths=[]
 for root in args.archives:paths.extend(root.rglob('*.mcaddon') if root.is_dir() else [root])
 assemble(read(ROOT/'family/upstream.lock.json'),{'tavern':args.tavern,'grilling':args.grilling,'world-liquor':args.world_liquor},paths,args.output,args.working_candidate,args.extension,args.preserved_pack)
if __name__=='__main__':main()
