"""Synthetic complete host chains, preserving the historical native gate."""
import copy,hashlib,json,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
import stable_host_profiles as stable
from family_update import current_author_validation as m
from family_update import stable_author_validation as legacy

class CurrentAuthorCandidate(unittest.TestCase):
 def setUp(self):
  temporary=tempfile.TemporaryDirectory();self.addCleanup(temporary.cleanup);self.root=Path(temporary.name)
  self.pins={key:{'project_id':index,'file_id':100+index,'sha256':'archive-'+key,'behavior_uuid':key+'-BP','resource_uuid':key+'-RP','author_version':[1,0,6] if key=='ChineseFood' else [1,0,1]} for index,key in enumerate(['Cookery','ChineseFood','Nether','End','Orchard','PresenceFootsteps','Deco'],1)}
  self.original={key:{side:{'manifest.json':key+'-'+side+'-original'} for side in ['BP','RP']} for key in self.pins}
  self.profiles={};self.specs={};self.spec_records={};self.host_proofs={}
  names=[('chinesefood-freezer-storage.json','ChineseFood','BP'),('chinesefood-reviewed-repairs.json','ChineseFood','BP'),('chinesefood-doll-renderer.json','ChineseFood','RP'),('cookery-mooncake-dough-repair.json','Cookery','BP'),('cookery-guide-startup-repair.json','Cookery','BP'),('cookery-enamel-basin-lid-repair.json','Cookery','BP'),('cookery-held-geometry-canonicalization.json','Cookery','RP'),('orchard-tavern-bridge-adapter.json','Orchard','BP')]
  public={'id':'fixture:public-0.2.13','version':[0,2,13],'host_uuid':'Cookery-BP','archive_sha256':'archive-Cookery','original_files':{'scripts/public.js':'public-before'},'patched_files':{'scripts/public.js':'public-after'},'copies':{}}
  self.original['Cookery']['BP'].update(public['original_files']);self.public_spec=public
  self.public={**public,'spec_sha256':stable.declaration_sha(public),'source_owner':'upstream','required_extensions':[]}
  self.public_sha='public-spec-sha';self.public_meta={key:self.public[key] for key in ['id','version','host_uuid','archive_sha256','original_files','patched_files']}
  self.public_meta.update(repository='casama233/kaleidoscope-grilling-unofficial',source_commit='g-proof',git_tree='g-tree',spec_sha256=self.public_sha,copies_hashes={})
  for filename,key,side in names:
   stem=filename.removesuffix('.json');paired=stem=='chinesefood-doll-renderer';path='scripts/'+stem+'.js'
   spec={'schema':1,'kind':'chinesefood-doll-renderer-cleanup' if paired else stem,'id':'fixture:'+stem,'host_uuid':key+'-'+side,'archive_sha256':'archive-'+key,'original_files':{},'patched_files':{},'copies':{}}
   if paired:
    spec.update(owner_version=[1,0,55],local_pack_version=[1,0,10655],behavior_uuid=key+'-BP')
    for pair_side in ['BP','RP']:spec['original_files'][pair_side+'/manifest.json']=self.original[key][pair_side]['manifest.json'];spec['patched_files'][pair_side+'/manifest.json']=key+'-'+pair_side+'-local55'
   else:
    spec['version']=[1,0,1];spec['original_files'][path]=stem+'-before';spec['patched_files'][path]=stem+'-after';self.original[key][side].update(spec['original_files'])
   if key=='Orchard':
    helper='scripts/compat/owned.js';target='scripts/integrations/owned.js';raw=b'export const owned=true;\n';p=self.root/'runtime/BP'/helper;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(raw);spec['copies']={helper:target}
   required=[];owner='upstream'
   if stem=='chinesefood-reviewed-repairs':required=['chinesefood-freezer-storage-p55'];owner='upstream_extended'
   elif paired:required=['chinesefood-freezer-storage-p55','chinesefood-reviewed-repairs-p55'];owner='upstream_extended'
   elif key=='Cookery' and side=='BP':required=['public-api'];owner='upstream_extended'
   copies={target:{'source':src,'sha256':hashlib.sha256((self.root/'runtime/BP'/src).read_bytes()).hexdigest()} for src,target in spec['copies'].items()}
   profile={key:spec[key] for key in ['id','host_uuid','archive_sha256','original_files','patched_files']};profile.update(version=spec.get('version',spec.get('local_pack_version')),owner_version=[1,0,55],spec_sha256=stable.declaration_sha(spec),copies=copies,source_owner=owner,required_extensions=required,admission='current-author-p55')
   self.specs[filename]=spec;self.profiles[stem+'-p55']=profile;self.spec_records[filename]={'profile':stem+'-p55','sha256':'raw-'+stem,'declaration_sha256':profile['spec_sha256']}
   self.host_proofs[filename]={'sha256':'raw-'+stem,**{field:spec[field] for field in ['id','host_uuid','archive_sha256','original_files','patched_files']},'copies_hashes':copies}
  self.catalog={'authors':self.pins,'host_specs':self.spec_records,'public_api_profile':'public-api-0.2.13','public_api_spec_sha256':self.public_sha,'previous_commit':'previous'}
  stable_catalog={'profiles':self.profiles,'public_api_profile':{'id':'historic','host_uuid':'historic'},'public_api_profiles':{'public-api-0.2.13':self.public},'public_api_predecessors':{name:['public-api-0.2.13'] for name,profile in self.profiles.items() if 'public-api' in profile['required_extensions']}}
  for p in [patch.object(stable,'CATALOG',stable_catalog),patch.object(stable,'PROFILES',self.profiles),patch.object(m,'PROFILES',self.profiles),patch.object(m.c,'EXTENSION',self.root),patch.object(m.c,'SOURCES',{'grilling':self.root/'grilling'}),patch.object(m.c,'sha',return_value=self.public_sha),patch.object(m.c,'read',return_value=self.public_spec),patch.object(m,'committed',side_effect=lambda relative,expected=None:self.specs[Path(relative).name])]:p.start();self.addCleanup(p.stop)
  current=copy.deepcopy(self.original);extensions={key:{side:[] for side in ['BP','RP']} for key in self.pins}
  def apply(spec,profile,key,side,spec_sha,repository,commit):
   paired=spec.get('kind')=='chinesefood-doll-renderer-cleanup';sides=['BP','RP'] if paired else [side]
   row={key:copy.deepcopy(spec[key]) for key in ['id','original_files','patched_files']};row.update(copies=profile['copies'],spec_sha256=spec_sha,repository=repository,commit=commit,working_candidate=False)
   if 'version' in spec:row['version']=spec['version']
   else:row.update(owner_version=[1,0,55],local_pack_version=[1,0,10655])
   for target_side in sides:
    extensions[key][target_side].append(copy.deepcopy(row))
    for path,value in spec['patched_files'].items():
     if paired:
      if not path.startswith(target_side+'/'):continue
      path=path[3:]
     current[key][target_side][path]=value
    for path,record in profile['copies'].items():current[key][target_side][path]=record['sha256']
  apply(public,self.public,'Cookery','BP',self.public_sha,self.public_meta['repository'],'g-current')
  for filename,key,side in names:apply(self.specs[filename],self.profiles[filename.removesuffix('.json')+'-p55'],key,side,self.spec_records[filename]['sha256'],m.LOGICAL,'p-current')
  self.receipt={'packs':[]}
  for key,pin in self.pins.items():
   for side,label in [('BP','behavior'),('RP','resource')]:self.receipt['packs'].append({'uuid':key+'-'+side,'side':label,'version':[1,0,10655] if key=='ChineseFood' else pin['author_version'],'files':copy.deepcopy(current[key][side]),'source':{'owner':'upstream_extended' if extensions[key][side] else 'upstream','archive_sha256':pin['sha256'],'project_id':pin['project_id'],'file_id':pin['file_id'],'reviewed_extensions':extensions[key][side]}})
  files={'BP':{'manifest.json':'owned55','scripts/compat/owned.js':hashlib.sha256((self.root/'runtime/BP/scripts/compat/owned.js').read_bytes()).hexdigest(),'scripts/conserved.js':'same-owned-bytes'},'RP':{'manifest.json':'owned55-rp'}};previous={'BP':{'manifest.json':'owned54','scripts/conserved.js':'same-owned-bytes','host-extensions/retired.json':'reviewed54'},'RP':{'manifest.json':'owned54-rp'}}
  self.baseline={'packs':{side:{'uuid':'private-'+side} for side in ['BP','RP']},'runtime':{'BP':'runtime/BP','RP':'runtime/RP'},'source_trees':{side:m.tree(value) for side,value in files.items()}}
  for side,label in [('BP','behavior'),('RP','resource')]:self.receipt['packs'].append({'uuid':'private-'+side,'side':label,'version':m.VERSION,'files':files[side],'source':{'owner':'owned','repository':m.LOGICAL,'commit':'p-current','working_candidate':False}})
  self.proof={'owned_runtime':{'files':files,'previous_files':previous,'exact_changed_paths':['runtime/BP/manifest.json','runtime/RP/manifest.json'],'added_paths':['runtime/BP/scripts/compat/owned.js'],'retired_paths':['runtime/BP/host-extensions/retired.json']},'authors':{key:{**pin,'original_files':copy.deepcopy(self.original[key]),'resolved_files':copy.deepcopy(current[key])} for key,pin in self.pins.items()},'resolved_host_files':current,'host_specs':self.host_proofs,'public_api':self.public_meta}
  old={'source_trees':{side:m.tree(value) for side,value in previous.items()}}
  def git(path,*args):
   if args[0]=='show':return json.dumps(old)
   if args[0]=='merge-base':return ''
   return 'g-tree' if args[-1].endswith('^{tree}') else 'g-current'
  p=patch.object(m.c,'git',side_effect=git);p.start();self.addCleanup(p.stop)
 def verify(self):m.validate_candidate(self.receipt,self.proof,self.baseline,{'actual_current_source_commit':'p-current'},self.catalog)
 def test_full_seven_author_pairs_and_same_owned_source_are_accepted(self):self.verify()
 def test_successor_profile_cannot_relabel_the_previous_owned_pair(self):
  with patch.object(m.c,'CONFIG',{'extension_stable_profile':'current-author-p56'}),self.assertRaises(AssertionError):self.verify()
 def test_added_runtime_paths_cannot_be_omitted_or_misreported(self):
  owned=self.proof['owned_runtime']
  for paths in [[],['runtime/BP/scripts/compat/owned.js','runtime/BP/scripts/conserved.js']]:
   with self.subTest(paths=paths):
    owned['added_paths']=paths
    with self.assertRaisesRegex(AssertionError,'conservation added paths'):self.verify()
  del owned['added_paths']
  with self.assertRaises(KeyError):self.verify()
 def test_retired_runtime_paths_cannot_be_omitted_or_misreported(self):
  owned=self.proof['owned_runtime']
  for paths in [[],['runtime/BP/host-extensions/retired.json','runtime/BP/scripts/conserved.js']]:
   with self.subTest(paths=paths):
    owned['retired_paths']=paths
    with self.assertRaisesRegex(AssertionError,'conservation retired paths'):self.verify()
  del owned['retired_paths']
  with self.assertRaises(KeyError):self.verify()
 def test_changed_runtime_paths_must_be_the_exact_changed_intersection(self):
  owned=self.proof['owned_runtime'];expected=list(owned['exact_changed_paths'])
  for paths in [expected[:1],sorted(expected+owned['added_paths']+owned['retired_paths']),sorted(expected+['runtime/BP/scripts/conserved.js'])]:
   with self.subTest(paths=paths):
    owned['exact_changed_paths']=paths
    with self.assertRaisesRegex(AssertionError,'conservation changed paths'):self.verify()
 def test_missing_new_pair_or_changed_untouched_pack_is_rejected(self):
  original=copy.deepcopy(self.receipt)
  self.receipt['packs']=[row for row in self.receipt['packs'] if row['uuid']!='Deco-RP']
  with self.assertRaises((AssertionError,KeyError)):self.verify()
  self.receipt=original;next(row for row in self.receipt['packs'] if row['uuid']=='PresenceFootsteps-RP')['files']['unexpected']='modified'
  with self.assertRaises((AssertionError,ValueError)):self.verify()
 def test_old_public_receipt_and_private_helper_mix_are_rejected(self):
  row=next(row for row in self.receipt['packs'] if row['uuid']=='Cookery-BP');row['source']['reviewed_extensions'][0]['id']='historic'
  with self.assertRaises(AssertionError):self.verify()
 def test_private_helper_and_ordered_preimage_changes_are_rejected(self):
  row=next(row for row in self.receipt['packs'] if row['uuid']=='Orchard-BP');row['source']['reviewed_extensions'][0]['copies']={}
  with self.assertRaises(AssertionError):self.verify()
 def test_extra_owned_or_author_identity_cannot_hide_behind_the_expected_pair(self):
  extra=copy.deepcopy(next(row for row in self.receipt['packs'] if row['uuid']=='private-BP'));extra['uuid']='extra-private';self.receipt['packs'].append(extra)
  with self.assertRaises(AssertionError):self.verify()
 def test_pair_renderer_cannot_borrow_an_unrelated_bp_history(self):
  row=next(row for row in self.receipt['packs'] if row['uuid']=='ChineseFood-BP');row['source']['reviewed_extensions'].pop(0)
  with self.assertRaises((AssertionError,ValueError)):self.verify()

class Dispatch(unittest.TestCase):
 def test_new_explicit_profile_dispatches_without_changing_historical_default(self):
  with patch.object(legacy.c,'CONFIG',{'extension_stable_profile':'current-author-p55'}),patch.object(m,'verify_static',return_value=['current']) as verify:
   self.assertEqual(legacy.verify_static({},{}),['current']);verify.assert_called_once()

class FreshNativeBinding(unittest.TestCase):
 def setUp(self):
  temporary=tempfile.TemporaryDirectory();self.addCleanup(temporary.cleanup);self.root=Path(temporary.name);candidate=self.root/'release-candidate';candidate.mkdir()
  (candidate/'family-receipt.json').write_text('{"packs":[]}\n');self.receipt={'packs':[]};self.digest=m.c.sha(candidate/'family-receipt.json')
  static={'profile':m.PROFILE,'version':m.VERSION,'candidate_receipt_sha256':self.digest,'affected_packs':{}};(self.root/'current-author-static-validation.json').write_text(json.dumps(static));(self.root/'saved-world-report.json').write_text('{}')
  phase=lambda name:{'phase':name,'ok':True,'errors':[],'real_player_connections':0,'player_records_unchanged':True,'custom_container_inventories_retained':True,'native_freezer_inputs_retained':True}
  self.evidence={'candidate_receipt_sha256':self.digest,'fresh_stopped_backup':True,'existing_world_loaded':True,'exact_files_checked':True,'bds':True,'saved_world_migration':True,'client':False,'simulated_players':False,'test_only_overlays':[],'runs':[phase('first'),phase('restart')]}
  for p in [patch.object(m.c,'R',self.root),patch.object(m.c,'C',candidate),patch.object(m.c,'atomic',side_effect=lambda path,value:path.write_text(json.dumps(value)))]:p.start();self.addCleanup(p.stop)
 def test_only_this_exact_candidate_and_both_fresh_loads_can_bind_native(self):
  for change in [{'candidate_receipt_sha256':'old-candidate'},{'fresh_stopped_backup':False},{'runs':self.evidence['runs'][:1]},{'client':True},{'test_only_overlays':['probe']}]:
   with self.subTest(change=change),self.assertRaises(AssertionError):m.bind_native(self.receipt,{**self.evidence,**change})
  self.assertFalse((self.root/'current-author-native-validation.json').exists())
  m.bind_native(self.receipt,self.evidence);result=json.loads((self.root/'current-author-native-validation.json').read_text())
  self.assertTrue(result['native_loading']);self.assertTrue(result['saved_world_migration']);self.assertFalse(result['client']);self.assertFalse(result['production_ready'])

if __name__=='__main__':unittest.main()
