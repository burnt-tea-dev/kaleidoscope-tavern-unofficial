"""Synthetic complete host chains, preserving the historical native gate."""
import copy,hashlib,json,subprocess,tempfile,unittest
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
 def test_public_receipt_accepts_reviewed_owner_transfer_and_preserves_other_bindings(self):
  extension=next(row for pack in self.receipt['packs'] for row in pack['source'].get('reviewed_extensions',[]) if row['id']==self.public['id'])
  extension['repository']='burnt-tea-dev/kaleidoscope-grilling-unofficial'
  self.verify()
  for key,value in [('repository','burnt-tea-dev/kaleidoscope-world-liquor-unofficial'),('repository','unreviewed/kaleidoscope-grilling-unofficial'),('commit','foreign-commit'),('spec_sha256','foreign-declaration'),('working_candidate',True)]:
   old=extension[key];extension[key]=value
   with self.subTest(key=key,value=value),self.assertRaises(AssertionError):self.verify()
   extension[key]=old
 def test_retained_candidate_checks_current_owner_and_component_receipt_separately(self):
  component_files=copy.deepcopy(self.proof['owned_runtime']['files'])
  self.baseline.update(version=[1,0,59],retained_runtime={'source_commit':'component58','source_tree':'component-tree'})
  self.proof.update(component_version=[1,0,58]);self.proof['owned_runtime']['previous_files']=component_files
  anchor={'schema':1,'source_commit':'component58','source_tree':'component-tree','source_version':[1,0,58]}
  for filename,spec in self.specs.items():
   profile=self.profiles[filename.removesuffix('.json')+'-p55'];profile.update(owner_version=[1,0,58],admission='current-author-p58')
   if 'owner_version' in spec:spec.update(owner_version=[1,0,58],local_pack_version=[1,0,10658]);profile['version']=[1,0,10658]
   profile['spec_sha256']=stable.declaration_sha(spec);self.spec_records[filename]['declaration_sha256']=profile['spec_sha256']
  for row in self.receipt['packs']:
   if row['uuid'].startswith('private-'):row['version']=[1,0,59]
   elif row['uuid'].startswith('ChineseFood-'):row['version']=[1,0,10658]
   for extension in row['source'].get('reviewed_extensions',[]):
    if extension['repository']!=m.LOGICAL:continue
    extension.update(source_package_version=[1,0,59],component_version=[1,0,58],retained_runtime_profile=copy.deepcopy(anchor))
    if 'owner_version' in extension:extension.update(owner_version=[1,0,58],local_pack_version=[1,0,10658])
  original_git=m.c.git
  def git(root,*args):
   if args==('show','component58:baseline.json'):return json.dumps({'source_trees':{side:m.tree(files)for side,files in component_files.items()}})
   return original_git(root,*args)
  with patch.object(m.c,'CONFIG',{'extension_stable_profile':'current-author-retained'}),patch.object(m,'validate_retained_runtime'),patch.object(m.c,'git',side_effect=git):
   self.verify()
   extension=next(row for row in self.receipt['packs']if row['uuid']=='Orchard-BP')['source']['reviewed_extensions'][0]
   for key,value in [('source_package_version',[1,0,58]),('component_version',[1,0,59]),('retained_runtime_profile',{**anchor,'source_commit':'wrong-anchor'})]:
    old=extension[key];extension[key]=value
    with self.subTest(key=key),self.assertRaises(AssertionError):self.verify()
    extension[key]=old

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

 def test_pair_schema_revision_does_not_replace_owner_and_installed_version_checks(self):
  filename='chinesefood-doll-renderer.json';spec=self.specs[filename]
  spec['version']=[1,0,1]
  profile=self.profiles['chinesefood-doll-renderer-p55']
  profile['spec_sha256']=stable.declaration_sha(spec)
  self.spec_records[filename]['declaration_sha256']=profile['spec_sha256']
  receipts=[extension for row in self.receipt['packs'] for extension in row['source'].get('reviewed_extensions',[]) if extension['id']==spec['id']]
  self.assertEqual(len(receipts),2)
  for receipt in receipts:receipt['version']=[1,0,1]
  self.verify()
  for field,value in [('owner_version',[1,0,54]),('local_pack_version',[1,0,1])]:
   before=[copy.deepcopy(receipt[field]) for receipt in receipts]
   for receipt in receipts:receipt[field]=value
   with self.subTest(field=field),self.assertRaisesRegex(AssertionError,'owner or installed version'):self.verify()
   for receipt,original in zip(receipts,before):receipt[field]=original

 def test_pair_requires_the_same_receipt_on_both_author_sides(self):
  row=next(row for row in self.receipt['packs'] if row['uuid']=='ChineseFood-RP')
  row['source']['reviewed_extensions'][0]['authorization']='Unrelated resource-side provenance'
  with self.assertRaisesRegex(AssertionError,'different reviewed receipts'):self.verify()

class MergedSourceBinding(unittest.TestCase):
 def setUp(self):
  temporary=tempfile.TemporaryDirectory();self.addCleanup(temporary.cleanup);self.root=Path(temporary.name)
  self.git('init','--quiet','--initial-branch=main')
  self.git('config','maintenance.auto','false');self.git('config','gc.auto','0')
  (self.root/'runtime.txt').write_text('Original runtime\n');self.commit('Original source')
  self.base=self.git('rev-parse','HEAD')
  self.git('switch','--quiet','-c','candidate')
  (self.root/'runtime.txt').write_text('Reviewed runtime\n');self.commit('Reviewed candidate')
  self.head=self.git('rev-parse','HEAD');self.head_tree=self.git('rev-parse','HEAD^{tree}')
  self.git('switch','--quiet','main')
  (self.root/'styles.css').write_text('Concurrent source-only CSS\n');self.commit('Concurrent base change')
  self.git('merge','--squash','candidate');self.commit('Squash reviewed candidate onto current base')
  self.merged=self.git('rev-parse','HEAD');self.tree=self.git('rev-parse','HEAD^{tree}')
  record={'full_name':m.current_name(m.REPOSITORY),'id':m.REPOSITORY_ID}
  self.pr={'merged':True,'merge_commit_sha':self.merged,'head':{'sha':self.head,'repo':record},'base':{'ref':'main','repo':record}}
  self.binding={'actual_current_source_commit':self.merged}
  patcher=patch.object(m.c,'EXTENSION',self.root);patcher.start();self.addCleanup(patcher.stop)
 def git(self,*args):
  return subprocess.check_output(['git','-C',str(self.root),'-c','user.name=Fixture','-c','user.email=fixture@example.invalid','-c','commit.gpgsign=false',*args],text=True,stderr=subprocess.PIPE).strip()
 def commit(self,message):
  self.git('add','.');self.git('commit','--quiet','-m',message)
 def test_concurrent_base_squash_accepts_the_exact_merged_tree(self):
  self.assertNotEqual(self.head_tree,self.tree)
  with self.assertRaises(subprocess.CalledProcessError):self.git('merge-base','--is-ancestor',self.head,self.merged)
  m.validate_merged_source(self.pr,self.binding,self.tree)
 def test_head_only_proof_tree_is_rejected(self):
  with self.assertRaisesRegex(AssertionError,'merged PR whole tree differs'):
   m.validate_merged_source(self.pr,self.binding,self.head_tree)
 def test_same_tree_nonancestor_merge_commit_is_rejected(self):
  sibling=self.git('commit-tree',self.tree,'-p',self.base,'-m','Unrelated same-tree sibling')
  self.assertEqual(self.git('rev-parse',sibling+'^{tree}'),self.tree)
  with self.assertRaises(subprocess.CalledProcessError):
   m.validate_merged_source({**self.pr,'merge_commit_sha':sibling},self.binding,self.tree)

class Dispatch(unittest.TestCase):
 def test_new_explicit_profile_dispatches_without_changing_historical_default(self):
  with patch.object(legacy.c,'CONFIG',{'extension_stable_profile':'current-author-p55'}),patch.object(m,'verify_static',return_value=['current']) as verify:
   self.assertEqual(legacy.verify_static({},{}),['current']);verify.assert_called_once()
 def test_fresh_world_requires_static_binding_even_with_unchanged_private_files(self):
  from family_update import extension_validation as extension
  pack={'uuid':'private','source':{'owner':'owned','repository':'local/senluo-amw-cuisine'},'files':{},'version':[1,0,70]}
  with patch.object(extension,'CONFIG',{'fresh_world':True,'extension_stable_validation':'proof'}),patch.object(legacy,'verify_static',return_value=['current']) as verify:
   self.assertEqual(extension.verify_extension({'packs':[pack]},{'private':pack}),['current']);verify.assert_called_once()
  with patch.object(extension,'CONFIG',{'extension_stable_validation':'proof'}),patch.object(legacy,'verify_static') as verify:
   self.assertEqual(extension.verify_extension({'packs':[pack]},{'private':pack}),[]);verify.assert_not_called()

class FreshNativeBinding(unittest.TestCase):
 def setUp(self):
  temporary=tempfile.TemporaryDirectory();self.addCleanup(temporary.cleanup);self.root=Path(temporary.name);candidate=self.root/'release-candidate';candidate.mkdir()
  (candidate/'family-receipt.json').write_text('{"packs":[]}\n');self.receipt={'packs':[]};self.digest=m.c.sha(candidate/'family-receipt.json')
  static={'profile':m.PROFILE,'version':m.VERSION,'candidate_receipt_sha256':self.digest,'affected_packs':{}};(self.root/'current-author-static-validation.json').write_text(json.dumps(static));(self.root/'saved-world-report.json').write_text('{}')
  phase=lambda name:{'phase':name,'ok':True,'errors':[],'real_player_connections':0,'player_records_unchanged':True,'custom_container_inventories_retained':True,'native_freezer_inputs_retained':True}
  self.evidence={'candidate_receipt_sha256':self.digest,'fresh_stopped_backup':True,'existing_world_loaded':True,'exact_files_checked':True,'bds':True,'saved_world_migration':True,'client':False,'simulated_players':False,'test_only_overlays':[],'runs':[phase('first'),phase('restart')]}
  for p in [patch.object(m.c,'R',self.root),patch.object(m.c,'C',candidate),patch.object(m.c,'atomic',side_effect=lambda path,value:path.write_text(json.dumps(value)))]:p.start();self.addCleanup(p.stop)
 def test_retained_component58_requires_fresh_owner59_native_binding(self):
  path=self.root/'current-author-static-validation.json';static=json.loads(path.read_text());static.update(profile='senluo-stable-author-20261019-p58',version=[1,0,59],component_version=[1,0,58]);path.write_text(json.dumps(static))
  with patch.object(m.c,'CONFIG',{'extension_stable_profile':'current-author-retained'}),patch.object(m,'owner_version',return_value=[1,0,59]):
   m.bind_native(self.receipt,self.evidence);native=json.loads((self.root/'current-author-native-validation.json').read_text())
   self.assertEqual(native['version'],[1,0,59]);self.assertEqual(native['component_version'],[1,0,58])
   static['version']=[1,0,58];path.write_text(json.dumps(static))
   with self.assertRaises(AssertionError):m.bind_native(self.receipt,self.evidence)

 def test_only_this_exact_candidate_and_both_fresh_loads_can_bind_native(self):
  for change in [{'candidate_receipt_sha256':'old-candidate'},{'fresh_stopped_backup':False},{'runs':self.evidence['runs'][:1]},{'client':True},{'test_only_overlays':['probe']}]:
   with self.subTest(change=change),self.assertRaises(AssertionError):m.bind_native(self.receipt,{**self.evidence,**change})
  self.assertFalse((self.root/'current-author-native-validation.json').exists())
  m.bind_native(self.receipt,self.evidence);result=json.loads((self.root/'current-author-native-validation.json').read_text())
  self.assertTrue(result['native_loading']);self.assertTrue(result['saved_world_migration']);self.assertFalse(result['client']);self.assertFalse(result['production_ready'])



class PublicApiSourceAdmission(unittest.TestCase):
 def setUp(self):
  temporary=tempfile.TemporaryDirectory();self.addCleanup(temporary.cleanup);self.root=Path(temporary.name)
  self.owned=self.root/'BP';self.path=self.owned/'host-extensions/board-api.json';self.path.parent.mkdir(parents=True)
  self.helper=self.owned/'scripts/helper.js';self.helper.parent.mkdir();self.helper.write_bytes(b'export const tested=1;')
  self.spec={'id':'fixture:public','version':[0,2,13],'host_uuid':'fixture-host','archive_sha256':'fixture-author','original_files':{},'patched_files':{},'copies':{'scripts/helper.js':'scripts/api/helper.js'}}
  self.path.write_text(json.dumps(self.spec))
  self.profile={**{k:self.spec[k] for k in ['id','version','host_uuid','archive_sha256','original_files','patched_files']},'spec_sha256':stable.declaration_sha(self.spec),'copies':{'scripts/api/helper.js':{'source':'scripts/helper.js','sha256':m.digest(self.helper.read_bytes())}},'source_owner':'upstream','required_extensions':[]}
  self.git('init','--quiet');self.commit('Reviewed public source')
  self.api={**{k:self.spec[k] for k in ['id','version','host_uuid','archive_sha256','original_files','patched_files']},'spec_sha256':m.digest(self.path.read_bytes()),'copies_hashes':self.profile['copies'],'repository':m.current_name('casama233/kaleidoscope-grilling-unofficial'),'source_commit':self.git('rev-parse','HEAD'),'git_tree':self.git('rev-parse','HEAD^{tree}')}
  for context in [patch.object(stable,'CATALOG',{'public_api_profile':self.profile}),patch.object(stable,'PROFILES',{})]:context.start();self.addCleanup(context.stop)
 def git(self,*args):
  return subprocess.check_output(['git','-C',str(self.root),'-c','user.name=Fixture','-c','user.email=fixture@example.invalid','-c','commit.gpgsign=false',*args],text=True,stderr=subprocess.PIPE).strip()
 def commit(self,label):self.git('add','.');self.git('commit','-qm',label)
 def validate(self,api=None,catalog=None,curated=True):
  return m.validate_public_api_source(self.api if api is None else api,{} if catalog is None else catalog,self.root,self.spec,self.path,curated=curated)
 def test_actual_reviewed_source_needs_no_duplicate_current_selector(self):
  self.assertEqual(self.validate(),self.profile)
  self.assertEqual(self.validate(catalog={'public_api_profile':'stale','public_api_spec_sha256':'0'*64}),self.profile)
 def test_unreviewed_declaration_and_committed_helper_changes_remain_rejected(self):
  self.helper.write_bytes(b'unreviewed implementation');self.commit('Changed helper')
  self.api.update(source_commit=self.git('rev-parse','HEAD'),git_tree=self.git('rev-parse','HEAD^{tree}'))
  with self.assertRaisesRegex(ValueError,'helper differs'):self.validate()
  self.helper.write_bytes(b'export const tested=1;');self.spec['version']=[0,2,14];self.path.write_text(json.dumps(self.spec))
  with self.assertRaisesRegex(ValueError,'exact reviewed'):self.validate()
 def test_wrong_completed_proof_and_historical_selector_remain_rejected(self):
  with self.assertRaisesRegex(AssertionError,'differs from completed CI'):self.validate(api={**self.api,'spec_sha256':'0'*64})
  valid={'public_api_profile':'public-api','public_api_spec_sha256':self.api['spec_sha256']}
  historical={**self.api,'repository':'casama233/kaleidoscope-grilling-unofficial'}
  self.assertEqual(self.validate(api=historical,catalog=valid,curated=False),self.profile)
  with self.assertRaises(AssertionError):self.validate(api=historical,catalog={**valid,'public_api_spec_sha256':'0'*64},curated=False)


class CuratedProfileAdmission(unittest.TestCase):
 """One real committed selection drives all current boundaries, including retirement."""
 def setUp(self):
  temporary=tempfile.TemporaryDirectory();self.addCleanup(temporary.cleanup);self.root=Path(temporary.name)
  self.git('init','--quiet','--initial-branch=main');self.git('config','maintenance.auto','false');self.git('config','gc.auto','0')
  self.write('runtime/BP/manifest.json','old BP');self.write('runtime/RP/manifest.json','old RP')
  self.recipe='runtime/BP/recipes/retired.json';self.hud='runtime/RP/ui/hud_screen.json'
  self.write(self.recipe,'FD recipe');self.write(self.hud,'old HUD')
  self.before=self.files();self.previous={'repository':m.LOGICAL,'version':[1,0,65],'source_trees':{side:m.tree(files) for side,files in self.before.items()}}
  self.write('baseline.json',self.previous);self.commit('Prior source');previous=self.git('rev-parse','HEAD')
  (self.root/self.recipe).unlink();self.write(self.hud,'current HUD');self.write('runtime/BP/manifest.json','current BP');self.write('runtime/RP/manifest.json','current RP')
  self.after=self.files();self.domains={'recipe-retirement':{self.recipe:{'before':self.before['BP']['recipes/retired.json'],'after':None}},'family-hud':{self.hud:{'before':self.before['RP']['ui/hud_screen.json'],'after':self.after['RP']['ui/hud_screen.json']}}}
  contract={'schema':1,'kind':'current-functional-runtime','domains':self.domains};self.contract='companion-sources/current-author-curated/runtime-contract.json';self.write(self.contract,contract)
  self.value={'schema':1,'kind':stable.CURATED,'profile':'reviewed-curated-test','version':[1,0,66],
   'sources':['Cookery'],'domains':{name:list(paths) for name,paths in self.domains.items()},
   'checks':['current-source-api','current-runtime-functional.json'],
   'check_commands':{'current-source-api':['node','--experimental-vm-modules','tools/current-author-functional.test.mjs'],'current-runtime-functional.json':['python','tools/build_current_functional_evidence.py']},
   'functional_checks':{'cookery-station-performance':{'source':'Cookery','cases':10}},
   'functional_contract':{'path':self.contract,'sha256':m.digest((self.root/self.contract).read_bytes())},'authors':{},'pack_versions':{},'station_profile':'curated-station'}
  self.write(stable.CURATED_INPUT,self.value)
  self.baseline={'repository':m.LOGICAL,'version':[1,0,66],'runtime':{'BP':'runtime/BP','RP':'runtime/RP'},'current_author_profile':stable.CURATED_INPUT,'source_trees':{side:m.tree(files) for side,files in self.after.items()}}
  self.write('baseline.json',self.baseline)
  self.catalog={'profile':self.value['profile'],'version':self.value['version'],'authors':{},'previous_commit':previous,
   'exact_changed_paths':['runtime/BP/manifest.json','runtime/RP/manifest.json',self.hud],'added_paths':[],'retired_paths':[self.recipe],
   'selection':{'path':stable.CURATED_INPUT,'sha256':m.digest((self.root/stable.CURATED_INPUT).read_bytes()),'value':self.value}}
  self.owned={'schema':1,'kind':'current_functional_runtime','core_only':True,'source_commit':previous,'previous_commit':previous,
   'source_version':self.previous['version'],'version':self.baseline['version'],'current_owner_version':self.baseline['version'],
   'source_trees':self.baseline['source_trees'],'retained_source_trees':self.previous['source_trees'],
   'previous_files':self.before,'files':self.after,'functional_domains':copy.deepcopy(self.domains),
   'exact_changed_paths':self.catalog['exact_changed_paths'],'added_paths':[],'retired_paths':[self.recipe],'conserved_files':0}
  self.commit('Current curated source')
  public={stable.CURATED_KEY:self.catalog}
  profiles={'curated-station':{'id':'senluo:cookery-station-performance','admission':stable.CURATED}}
  for p in [patch.object(stable,'CATALOG',public),patch.object(m,'CATALOG',public),patch.object(stable,'PROFILES',profiles),patch.object(m.c,'EXTENSION',self.root),patch.object(m.c,'CONFIG',{'extension_stable_profile':stable.CURATED,'extension_stable_validation':'fixture'})]:p.start();self.addCleanup(p.stop)
 def git(self,*args):
  return subprocess.check_output(['git','-C',str(self.root),'-c','user.name=Fixture','-c','user.email=fixture@example.invalid','-c','commit.gpgsign=false',*args],text=True,stderr=subprocess.PIPE).strip()
 def commit(self,message):self.git('add','.');self.git('commit','--quiet','-m',message)
 def write(self,name,value):
  p=self.root/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(value) if isinstance(value,dict) else value)
 def files(self):
  return {side:{p.relative_to(self.root/'runtime'/side).as_posix():m.digest(p.read_bytes()) for p in (self.root/'runtime'/side).rglob('*') if p.is_file()} for side in ['BP','RP']}
 def test_committed_selection_is_shared_and_missing_catalog_or_input_never_falls_back(self):
  self.assertEqual(m.settings(),([1,0,66],'reviewed-curated-test',stable.CURATED_KEY));self.assertEqual(m.current_selection(),self.value)
  with patch.object(stable,'CATALOG',{}),self.assertRaisesRegex(ValueError,'no reviewed catalog'):m.settings()
  (self.root/stable.CURATED_INPUT).unlink()
  with self.assertRaisesRegex(AssertionError,'evidence missing'):m.settings()
 def test_baseline_selector_and_raw_input_must_match_the_catalog(self):
  self.write('baseline.json',{**self.baseline,'current_author_profile':'wrong.json'});self.commit('Wrong selector')
  with self.assertRaisesRegex(AssertionError,'baseline must select'):m.settings()
  self.write('baseline.json',self.baseline);self.write(stable.CURATED_INPUT,{**self.value,'sources':['WitchWay']});self.commit('Wrong selection')
  with self.assertRaisesRegex(AssertionError,'evidence changed'):m.settings()
 def test_retirement_is_exact_and_cannot_be_called_conservation_or_left_on_disk(self):
  m.validate_curated_runtime(self.owned,self.baseline,self.catalog)
  bad=copy.deepcopy(self.owned);bad['conserved_files']=1
  with self.assertRaises(AssertionError):m.validate_curated_runtime(bad,self.baseline,self.catalog)
  bad=copy.deepcopy(self.owned);bad['functional_domains']['recipe-retirement'][self.recipe]['before']='0'*64
  with self.assertRaises(AssertionError):m.validate_curated_runtime(bad,self.baseline,self.catalog)
  self.write(self.recipe,'FD recipe')
  with self.assertRaises(AssertionError):m.validate_curated_runtime(self.owned,self.baseline,self.catalog)
 def test_before_only_contract_uses_frozen_outputs_and_rejects_committed_payload_drift(self):
  self.domains['family-hud'][self.hud].pop('after')
  self.write(self.contract,{'schema':1,'kind':'current-functional-runtime','domains':self.domains})
  self.value['functional_contract']['sha256']=m.digest((self.root/self.contract).read_bytes())
  self.write(stable.CURATED_INPUT,self.value)
  self.catalog['selection']['sha256']=m.digest((self.root/stable.CURATED_INPUT).read_bytes())
  self.owned['functional_domains']=copy.deepcopy(self.domains)
  self.commit('One frozen output identity')
  m.validate_curated_runtime(self.owned,self.baseline,self.catalog)
  self.write(self.hud,'unreviewed committed HUD')
  self.commit('Payload changed without a new baseline')
  with self.assertRaisesRegex(AssertionError,'frozen source proof'):
   m.validate_curated_runtime(self.owned,self.baseline,self.catalog)
 def test_omitted_domain_or_report_requirement_is_not_optional(self):
  bad=copy.deepcopy(self.owned);del bad['functional_domains']['family-hud']
  with self.assertRaises(AssertionError):m.validate_curated_runtime(bad,self.baseline,self.catalog)
  self.value['functional_checks']={}
  with self.assertRaisesRegex(ValueError,'do not cover'):stable.curated_profile()
 def test_all_existing_dispatchers_reach_the_same_curated_entry(self):
  for name,args in [('verify_static',({},{})),('evidence_paths',(False,)),('bind_native',({},{})),('verify_installation',({},))]:
   with self.subTest(name=name),patch.object(m,name,return_value='curated') as call:
    self.assertEqual(getattr(legacy,name)(*args),'curated');call.assert_called_once_with(*args)
 def test_selected_functional_sources_and_checks_are_exact_even_before_nested_reports(self):
  fields={'version':self.baseline['version'],'repository':m.LOGICAL,'source_commit':'a'*40,'git_tree':'b'*40,'source_trees':self.baseline['source_trees']}
  current={'schema':1,'kind':'current_runtime_functional',**fields,'test_exit_code':0,'test_command':['python','tools/build_current_functional_evidence.py'],**{key:False for key in ['native_loading','client','simulated_players','production_ready','saved_world_migration','native_full_nbt_verified']},'sources':{'Cookery':{},'WitchWay':{}},'completed_checks':[]}
  def verify():
   raw=json.dumps(current).encode();proof={**fields,'current_functional_sources':current['sources'],'completed_checks':[{'name':'current-runtime-functional.json','report_sha256':m.digest(raw)}]}
   m.validate_functional_artifacts(self.root/'proof.json',proof,self.baseline,{'current-runtime-functional.json':raw})
  with self.assertRaises(AssertionError):verify()
  current['sources']={'Cookery':{}}
  with self.assertRaises(AssertionError):verify()
  current['completed_checks']=[{'name':'cookery-station-performance','exit_code':0,'command':['node','real-test.mjs'],'log':{'name':'missing-log','sha256':'a'*64}}]
  with self.assertRaises(KeyError):verify()
 def test_selected_original_check_reports_cannot_be_missing_or_replaced(self):
  raw=b'{"actual":"original check output"}'
  checks=[{'name':'current-source-api'},{'name':'curated-chinesefood-functional.json','report_sha256':m.digest(raw)}]
  self.assertEqual(m.selected_report_members(checks,{'curated-chinesefood-functional.json':raw}),{'curated-chinesefood-functional.json'})
  with self.assertRaises(KeyError):m.selected_report_members(checks,{})
  with self.assertRaisesRegex(AssertionError,'original check report differs'):
   m.selected_report_members(checks,{'curated-chinesefood-functional.json':raw+b' '})
 def test_selected_cookery_report_passes_without_retired_witch_evidence(self):
  target='scripts/custom_components/blocks/directStation.js';helper='runtime/BP/scripts/host_api/cookery-station-performance.js';spec_path='runtime/BP/host-extensions/cookery-station-performance.json';test_path='tools/cookery-station-performance.test.mjs'
  self.write(helper,'owned fixture helper');self.write(test_path,'fixture test source')
  station={'patched_files':{target:'c'*64},'helper_sha256':m.digest((self.root/helper).read_bytes())};self.write(spec_path,station);self.commit('Functional report fixture inputs')
  closure={'repair_spec_sha256':m.digest((self.root/spec_path).read_bytes()),'station_output_sha256':station['patched_files'][target],'owned_helper_sha256':station['helper_sha256']}
  report={'ok':True,'completeSuite':True,'caseCount':10,'results':[{'ok':True}for _ in range(10)],'input_closure':closure,'native':False,'client':False,'source_test_sha256':m.digest((self.root/test_path).read_bytes())}
  report_raw=json.dumps(report).encode();log=b'actual original CI log fixture';ref={'name':'station-report.json','sha256':m.digest(report_raw)}
  source={'input_closure':closure,'report':ref,'test_source_sha256':report['source_test_sha256']}
  fields={'version':self.baseline['version'],'repository':m.LOGICAL,'source_commit':'a'*40,'git_tree':'b'*40,'source_trees':self.baseline['source_trees']}
  current={'schema':1,'kind':'current_runtime_functional',**fields,'test_exit_code':0,'test_command':['python','tools/build_current_functional_evidence.py'],**{key:False for key in ['native_loading','client','simulated_players','production_ready','saved_world_migration','native_full_nbt_verified']},'sources':{'Cookery':source},'completed_checks':[{'name':'cookery-station-performance','exit_code':0,'command':['node','actual-test.mjs'],'log':{'name':'station.log','sha256':m.digest(log)},'report':ref}], 'test_log':{'name':'station.log','sha256':m.digest(log)},'artifact_members':['station.log','station-report.json','current-runtime-functional.json']}
  raw=json.dumps(current).encode();proof={**fields,'current_functional_sources':current['sources'],'completed_checks':[{'name':'current-runtime-functional.json','report_sha256':m.digest(raw)}]}
  members={'current-runtime-functional.json':raw,'station.log':log,'station-report.json':report_raw}
  self.assertEqual(m.validate_functional_artifacts(self.root/'proof.json',proof,self.baseline,members),set(members))
  members.pop('station-report.json')
  with self.assertRaises(KeyError):m.validate_functional_artifacts(self.root/'proof.json',proof,self.baseline,members)
 def test_real_curated_native_binder_preserves_fresh_world_truth_and_requires_binding(self):
  import family_guard
  out=self.root/'evidence';out.mkdir();candidate=self.root/'candidate';candidate.mkdir()
  self.write('candidate/family-receipt.json',{'packs':[]});self.write('evidence/saved-world-report.json',{'fixture':'already validated native report'})
  proof=self.root/'evidence/proof.json';proof.write_text('{}')
  static={'profile':self.value['profile'],'version':self.value['version'],'source':m.c.report_ref(proof),'candidate_receipt_sha256':m.digest((candidate/'family-receipt.json').read_bytes()),'affected_packs':{}}
  self.write('evidence/current-author-static-validation.json',static)
  evidence={'candidate_receipt_sha256':static['candidate_receipt_sha256'],'native_acceptance_source':'fresh_world','exact_files_checked':True,'bds':True,'fresh_world_initialization':True,'world_persistence':True,'saved_world_migration':False,'existing_world_loaded':False,'test_only_overlays':[],'client':False,'simulated_players':False,'runs':[{'phase':phase,'ok':True,'errors':[],'real_player_connections':0,'generated_database':True,'commands_sent':False}for phase in ['first','restart']]}
  config={**m.c.CONFIG,'extension_stable_validation':str(proof),'fresh_world':{'level_name':'fresh-fixture'}}
  path=out/'current-author-native-validation.json'
  with patch.object(m.c,'R',out),patch.object(m.c,'C',candidate),patch.object(m.c,'CONFIG',config),patch.object(m.c,'G',{'atomic':family_guard.atomic}):
   with patch.object(stable,'CATALOG',{}),self.assertRaisesRegex(ValueError,'no reviewed catalog'):m.bind_native({'packs':[]},evidence)
   self.assertFalse(path.exists())
   m.bind_native({'packs':[]},evidence)
   native=json.loads(path.read_text());self.assertIs(native['saved_world_migration'],False);self.assertIs(native['fresh_world_initialization'],True);self.assertIs(native['world_persistence'],True)
   m.verify_installation({'packs':[]})
   bad=copy.deepcopy(evidence);bad['saved_world_migration']=True
   with self.assertRaises(AssertionError):m.bind_native({'packs':[]},bad)

 def producer_output(self):
  """Only the private CLI is external here; public validation and Git stay real."""
  original=subprocess.check_output
  def output(args,**kwargs):
   return json.dumps(self.owned).encode() if args[0]=='python3' else original(args,**kwargs)
  return patch.object(subprocess,'check_output',side_effect=output)

 def test_independent_bundle_validates_current_pair_without_global_config_or_p58_context(self):
  import family_bundle
  with self.producer_output(),patch.object(m.c,'CONFIG',{}),patch.object(m.c,'EXTENSION',Path('/unconfigured-global-source')):
   component,anchor=family_bundle.retained_component_config(self.root,self.baseline,{'private':self.root})
   self.assertEqual(component,self.baseline);self.assertIsNone(anchor)
   self.write('runtime/BP/unreviewed.js','unexpected payload')
   with self.assertRaisesRegex(SystemExit,'current source payload differs'):
    family_bundle.retained_component_config(self.root,self.baseline,{'private':self.root})

 def test_independent_bundle_requires_curated_binding_before_running_private_producer(self):
  import family_bundle
  with patch.object(stable,'CATALOG',{}),patch.object(subprocess,'check_output') as producer,self.assertRaisesRegex(ValueError,'no reviewed catalog'):
   family_bundle.retained_component_config(self.root,self.baseline,{})
  producer.assert_not_called()

 def test_curated_salt_uses_current_owner_and_exact_selected_fishing_without_expanding_removals(self):
  import host_extensions
  temporary=tempfile.TemporaryDirectory();self.addCleanup(temporary.cleanup);host=Path(temporary.name)
  path=host/'recipes/vanilla_cooking/salt_smelting.json';path.parent.mkdir(parents=True);path.write_bytes(b'clean salt preimage fixture')
  removed={path.relative_to(host).as_posix():m.digest(path.read_bytes())}
  spec={'schema':1,'kind':'chinesefood-reviewed-repairs','id':'senluo:chinesefood-reviewed-repairs','version':[1,0,8],
   'owner_version':self.value['version'],'host_uuid':'reviewed-CF-BP','archive_sha256':'dea708dd6443ea30d23e5791860a50181e8eeb560dcd7ec5a8e80fe22743e659',
   'expires':'2099-01-01','authorization':'fixture','feedback':'fixture','removal_condition':'fixture',
   'original_files':{},'patched_files':{},'imports':{},'copies':{},'insertions':[],'removed_files':removed}
  profile={key:spec[key] for key in ['id','host_uuid','archive_sha256','version','owner_version','original_files','patched_files']}
  profile.update(admission=stable.CURATED,spec_sha256=stable.declaration_sha(spec),copies={},source_owner='upstream',required_extensions=[])
  stable.PROFILES['curated-CF']=profile;stable.PROFILES['curated-station']['host_uuid']='unused-station-host'
  stable.CATALOG['public_api_profile']={'id':'unused-public','host_uuid':'unused-host'}
  self.catalog['host_specs']={'chinesefood-reviewed-repairs.json':{'declaration_sha256':profile['spec_sha256']}}
  dependency={'uuid':'5e121bf2-1d2d-4da4-be15-cffc5f216d94','version':[1,3,10005]}
  self.value['dependencies']={'BP':[dependency],'RP':[]};self.write(stable.CURATED_INPUT,self.value)
  self.catalog['selection']['sha256']=m.digest((self.root/stable.CURATED_INPUT).read_bytes())
  manifest={'header':{'version':self.value['version']},'dependencies':[dependency]}
  self.write('runtime/BP/manifest.json',manifest)
  self.owned['files']['BP']['manifest.json']=m.digest((self.root/'runtime/BP/manifest.json').read_bytes())
  self.baseline['source_trees']={side:m.tree(rows)for side,rows in self.owned['files'].items()};self.owned['source_trees']=self.baseline['source_trees']
  self.baseline['runtime']={'BP':'runtime/BP','RP':'runtime/RP'};self.write('baseline.json',self.baseline);self.commit('Current owner and selected Fishing')
  owned=self.root/'runtime/BP';source={'owner':'upstream','archive_sha256':spec['archive_sha256']}
  context={'source_root':str(self.root),'source_commit':self.git('rev-parse','HEAD'),'sources':{'private':str(self.root)}}
  with patch.object(host_extensions,'REVIEWED_SALT_REMOVAL',removed),patch.object(m.c,'CONFIG',{}),patch.object(m.c,'EXTENSION',Path('/unconfigured-global-source')):
   self.assertEqual(host_extensions.validate_recipe_removals(spec,owned,host,profile),removed)
   with patch.dict(profile,owner_version=[1,0,58]),self.assertRaisesRegex(ValueError,'selected curated declaration'):
    host_extensions.validate_recipe_removals(spec,owned,host,profile)
   wrong={**spec,'removed_files':{**removed,'recipes/unreviewed.json':'f'*64}}
   with self.assertRaisesRegex(ValueError,'exact reviewed coexistence'):host_extensions.validate_recipe_removals(wrong,owned,host,profile)
   manifest['dependencies']=[{**dependency,'version':[1,2,10058]}];self.write('runtime/BP/manifest.json',manifest)
   with self.assertRaisesRegex(ValueError,'exact Fishing'):host_extensions.validate_recipe_removals(spec,owned,host,profile)
   self.assertTrue(path.exists());manifest['dependencies']=[dependency];self.write('runtime/BP/manifest.json',manifest)
   with self.producer_output():proof=host_extensions.apply_host_extension(spec,owned,host,source,retained_owner=context)
   self.assertFalse(path.exists());self.assertEqual(proof['removed_files'],removed)

class CuratedRetainedInputs(unittest.TestCase):
 """Real pack directories and committed recipes drive the fresh selector."""
 git=CuratedProfileAdmission.git
 commit=CuratedProfileAdmission.commit
 write=CuratedProfileAdmission.write
 files=CuratedProfileAdmission.files

 def setUp(self):
  CuratedProfileAdmission.setUp(self)
  import family_guard as guard
  self.guard=guard
  self.enterContext(patch.object(m.c,'G',{'hashes':guard.hashes,'atomic':guard.atomic}))
  self.run=self.root/'run';(self.run/'production-before').mkdir(parents=True)
  self.enterContext(patch.object(m.c,'R',self.run))
  m.c.CONFIG['fresh_world']=True
  self.original={'packs':[]};self.rows=[]
  def pack(path,uid,side,version,content):
   path.mkdir(parents=True)
   guard.atomic(path/'manifest.json',{'header':{'uuid':uid,'version':version},'modules':[{'type':'data' if side=='behavior' else 'resources','version':version}]})
   (path/'content.bin').write_bytes(content)
   return {'uuid':uid,'side':side,'version':version,'files':guard.hashes(path),'path':str(path)}
  self.pack=pack
  def row(actual,kind,provenance,output=None):
   output=actual if output is None else output
   return {'group':kind,'kind':kind,'uuid':actual['uuid'],'side':actual['side'],
    'input_version':actual['version'],'output_version':output['version'],
    'input_tree':m.tree(actual['files']),'output_tree':m.tree(output['files']),'provenance':provenance}
  literal=pack(self.root/'captured/literal','literal-bp','behavior',[1,0,0],b'exact current exception')
  self.original['packs'].append(literal)
  self.rows.append(row(literal,'literal',{'original_archive_verified':False,'latest_stable_verified':False,'official_author_release':False}))
  self.excluded=pack(self.root/'captured/excluded','excluded-bp','behavior',[1,0,0],b'not selected')
  self.original['packs'].append(self.excluded)
  saturation_path='companion-sources/stable-author-20261017-p48/saturation-recipe.json'
  sat={side:pack(self.root/'captured'/('sat-'+side),'sat-'+side,label,[1,6,10048],b'existing canonical Saturation output') for side,label in [('BP','behavior'),('RP','resource')]}
  self.write(saturation_path,{'file_id':9071891,'archive_sha256':'a'*64,
   'uuids':{side:p['uuid'] for side,p in sat.items()},'versions':{side:p['version'] for side,p in sat.items()},'output_hashes':{side:p['files'] for side,p in sat.items()}})
  for actual in sat.values():
   self.original['packs'].append(actual)
   item=row(actual,'saturation',{'official_author_release':False,'latest_stable_input_verified':True,'file_id':9071891,'clean_archive_sha256':'a'*64})
   item.update(recipe_path=saturation_path,recipe_sha256=m.digest((self.root/saturation_path).read_bytes()));self.rows.append(item)
  fish={};outputs={}
  for side,label,uid in [('BP','behavior','5e121bf2-1d2d-4da4-be15-cffc5f216d94'),('RP','resource','e1168f1a-83d6-4abc-8f4b-ecb86e0a91dd')]:
   fish[side]=pack(self.root/'captured'/('fish-'+side),uid,label,[1,3,0],b'current raw local Fishing')
   outputs[side]=pack(self.root/'companion-sources/fishing-current-local/runtimeowner'/side,uid,label,[1,3,10005],b'whole canonical Fishing output')
   extra=Path(outputs[side]['path'])/'owned-fix.js';extra.write_bytes(b'export const fixed=true;\n');outputs[side]['files']=guard.hashes(Path(outputs[side]['path']))
  input_path='companion-sources/fishing-current-local/input-recipe.json'
  self.write(input_path,{'packs':{side:{key:p[key] for key in ['uuid','version','files']} for side,p in fish.items()}})
  self.fish_ref={'path':input_path,'sha256':m.digest((self.root/input_path).read_bytes())}
  recipe_path='companion-sources/fishing-current-local/recipe.json'
  self.write(recipe_path,{'kind':'canonical_local_fishing_repair','historical_origin_status':'unknown','original_archive_verified':False,'latest_stable_verified':False,
   'version':[1,3,10005],'input_recipe':self.fish_ref,'input_hashes':{side:p['files'] for side,p in fish.items()},
   'owned_runtime':{side:p['files'] for side,p in outputs.items()},'output_hashes':{side:p['files'] for side,p in outputs.items()}})
  for side,actual in fish.items():
   self.original['packs'].append(actual)
   item=row(actual,'canonical-fishing',{'official_author_release':False,'input_recipe':self.fish_ref},outputs[side])
   item.update(canonical_source='companion-sources/fishing-current-local/runtimeowner/'+side,
               recipe_path=recipe_path,recipe_sha256=m.digest((self.root/recipe_path).read_bytes()));self.rows.append(item)
  self.value['retained_inputs']=self.rows;self.write(stable.CURATED_INPUT,self.value)
  self.catalog['selection']['sha256']=m.digest((self.root/stable.CURATED_INPUT).read_bytes())
  self.commit('Explicit retained source inputs')
  guard.atomic(self.run/'production-before/inventory.json',self.original)

 def selected(self):
  roots,sources,report=m.select_curated_inputs(self.original)
  receipt={'packs':[{'uuid':uid,'side':row['side'],'version':row['version'],
                    'files':self.guard.hashes(Path(row['path'])),'source':sources[uid]}
                   for uid,row in report['packs'].items()]}
  return roots,sources,report,receipt

 def owner_pair(self,replacement=False):
  folder=tempfile.TemporaryDirectory();self.addCleanup(folder.cleanup);root=Path(folder.name)
  inputs={}
  for side in ('behavior','resource'):
   uid='reviewed-'+side;path=root/uid;path.mkdir()
   self.guard.atomic(path/'manifest.json',{'header':{'uuid':uid,'version':[1,0,2]},'modules':[{'type':'data' if side=='behavior' else 'resources','version':[1,0,2]}]})
   (path/'payload.js').write_text('export const reviewed=true;')
   inputs[uid]={'uuid':uid,'side':side,'version':[1,0,2],'path':str(path),'files':self.guard.hashes(path)}
  if replacement:
   self.value['authors']['ReviewedLocal']={'behavior_uuid':'reviewed-behavior','resource_uuid':'reviewed-resource'}
   self.catalog['authors']=copy.deepcopy(self.value['authors']);self.value['pack_versions']['ReviewedLocal']={'BP':[1,0,2],'RP':[1,0,2]}
   self.value['replacement_packs']={'ReviewedLocal':{('BP' if row['side']=='behavior' else 'RP'):{'uuid':uid,'version':row['version'],'tree':m.tree(row['files'])}for uid,row in inputs.items()}}
  else:
   for uid,row in inputs.items():
    self.rows.append({'uuid':uid,'side':row['side'],'group':'ReviewedLocal','kind':'literal','input_version':row['version'],'output_version':row['version'],'input_tree':m.tree(row['files']),'output_tree':m.tree(row['files']),'provenance':{'official_author_release':False,'original_archive_verified':False,'latest_stable_verified':False}})
   self.value['retained_inputs']=self.rows
  self.write(stable.CURATED_INPUT,self.value);self.catalog['selection']['sha256']=m.digest((self.root/stable.CURATED_INPUT).read_bytes());self.commit('Reviewed complete local owner pair')
  m.c.CONFIG.pop('fresh_world',None);m.c.CONFIG['delivery_profile']='senluo-stable-lock-v1';m.c.CONFIG['curated_owner_inputs']={uid:row['path']for uid,row in inputs.items()}
  return inputs

 def test_owner_pair_addition_uses_exact_new_inputs_without_rewriting_live_capture(self):
  inputs=self.owner_pair();before=copy.deepcopy(self.original)
  roots,sources,selection=m.select_curated_inputs(self.original)
  self.assertTrue(set(inputs)<=set(selection['packs']));self.assertEqual(self.original,before)
  from family_update import identity_migration as migration
  original={**self.original,'refs':{side:[{'pack_id':row['uuid']}for row in self.original['packs']if row['side']==side]for side in ('behavior','resource')}}
  with patch.object(migration,'CONFIG',m.c.CONFIG):
   order=migration.assembly_order(original)
   for uid,row in inputs.items():self.assertEqual(order[row['side']][0],uid)
   candidate={'packs':[*self.original['packs'],*inputs.values()]};self.assertIsNone(migration.candidate_plan(candidate,original))
   changed=copy.deepcopy(candidate);changed['packs'][-1]['side']='behavior' if changed['packs'][-1]['side']=='resource' else 'resource'
   with self.assertRaisesRegex(AssertionError,'candidate identity differs'):migration.candidate_plan(changed,original)
   candidate['packs'].pop(0)
   with self.assertRaisesRegex(AssertionError,'UUID change'):migration.candidate_plan(candidate,original)

 def test_first_owner_pair_install_does_not_require_or_retire_missing_directories(self):
  from family_update import deploy_live as deploy
  from family_update import identity_migration as migration
  inputs=self.owner_pair()
  _,_,selection,receipt=self.selected()
  original={'packs':[row for row in self.original['packs'] if row['uuid'] in selection['packs']]}
  self.guard.atomic(self.run/'curated-input-selection.json',selection)
  self.guard.atomic(self.run/'reviewed-family-receipt.json',receipt)
  self.guard.atomic(self.run/'handoff-authorization.json',{})
  self.guard.atomic(self.run/'build-evidence.json',{'sources':{}})
  candidate=self.run/'candidate';candidate.mkdir()
  self.guard.atomic(candidate/'family-receipt.json',receipt)
  quality=self.run/'quality';quality.mkdir()
  self.guard.atomic(quality/'senluo-policy.json',{'managed_uuids':[]})
  repository=Path(__file__).resolve().parents[2]
  with patch.object(deploy,'CONFIG',m.c.CONFIG),patch.object(migration,'CONFIG',m.c.CONFIG),\
       patch.object(deploy,'R',self.run),patch.object(deploy,'C',candidate),\
       patch.object(deploy,'Q',quality),patch.object(deploy,'T',repository),\
       patch.object(deploy,'G',{'validate_incoming':lambda *args:None}),\
       patch.object(legacy,'verify_installation'):
   policy,_,family,sources=deploy.prepare_admission(receipt,original)
  self.assertTrue(set(inputs)<={row['uuid'] for row in family})
  self.assertTrue(set(inputs)<=set(policy['managed_uuids']))
  self.assertFalse(set(inputs)&{row['uuid'] for row in sources})
  self.assertEqual({row['uuid'] for row in sources},{row['uuid'] for row in family}-set(inputs))
  changed=copy.deepcopy(receipt);changed['packs'][-1]['files']['payload.js']='unknown'
  with self.assertRaisesRegex(AssertionError,'Curated candidate output differs'):
   m.installation_targets(changed)

 def test_whole_owner_replacement_selects_new_pair_without_claiming_it_was_installed(self):
  inputs=self.owner_pair(replacement=True)
  captured={'packs':[dict(row,version=[1,0,1],files={'manifest.json':'old'})for row in inputs.values()]};before=copy.deepcopy(captured)
  roots,sources,selection=m.select_replacement_inputs(captured)
  self.assertEqual(set(selection['packs']),set(inputs));self.assertEqual(captured,before)
  self.assertTrue(all(row['source']['role']=='owner_accepted_author_replacement'for row in selection['packs'].values()))

 def test_owner_inputs_reject_partial_pair_unknown_identity_and_changed_bytes(self):
  inputs=self.owner_pair();configured=dict(m.c.CONFIG['curated_owner_inputs'])
  m.c.CONFIG['curated_owner_inputs']={next(iter(configured)):next(iter(configured.values()))}
  with self.assertRaisesRegex(AssertionError,'complete declared'):m.curated_owner_inputs()
  m.c.CONFIG['curated_owner_inputs']={'unknown':next(iter(configured.values()))}
  with self.assertRaisesRegex(AssertionError,'Unreviewed'):m.curated_owner_inputs()
  m.c.CONFIG['curated_owner_inputs']=configured
  (Path(next(iter(configured.values())))/'payload.js').write_text('changed')
  with self.assertRaisesRegex(AssertionError,'committed profile'):m.curated_owner_inputs()

 def test_installed_selected_literal_update_preserves_observation_and_old_receipt(self):
  inputs=self.owner_pair();inventory={'packs':list(inputs.values())}
  expected={uid:{**row,'version':[1,0,1],'files':{'manifest.json':'old'}}for uid,row in inputs.items()}
  before=copy.deepcopy((inventory,expected))
  self.assertTrue(m.curated_live_inputs_match(inventory,expected))
  self.assertEqual((inventory,expected),before)
  self.assertFalse(m.curated_live_inputs_match(inventory,inputs))
  order={side:[uid for uid,row in inputs.items()if row['side']==side]for side in ('behavior','resource')}
  inventory['refs']={side:[{'pack_id':uid,'version':inputs[uid]['version']}for uid in uids]for side,uids in order.items()}
  quality=self.root/'quality';quality.mkdir();receipt=self.root/'previous-family.json'
  self.guard.atomic(receipt,{'packs':list(expected.values()),'order':order})
  policy={'approved_receipt':str(receipt),'managed_uuids':list(expected)}
  policy_path=quality/'senluo-policy.json';self.guard.atomic(policy_path,policy);old=policy_path.read_bytes()
  with patch.object(m.c,'Q',quality):
   self.assertEqual(m.c.check_live_against_policy(inventory),policy)
  self.assertEqual(policy_path.read_bytes(),old)

 def test_installed_update_rejects_unknown_bytes_versions_sides_and_identities(self):
  inputs=self.owner_pair();inventory={'packs':list(inputs.values())}
  expected={uid:{**row,'version':[1,0,1],'files':{'manifest.json':'old'}}for uid,row in inputs.items()}
  for field,value in [('files',{'manifest.json':'changed'}),('version',[1,0,3]),
                      ('side','resource'),('uuid','unknown')]:
   with self.subTest(field=field):
    changed=copy.deepcopy(inventory);changed['packs'][0][field]=value
    self.assertFalse(m.curated_live_inputs_match(changed,expected))

 def test_reviewed_installed_preimage_can_be_replaced_by_different_selected_output(self):
  inputs=self.owner_pair();inventory={'packs':copy.deepcopy(list(inputs.values()))}
  expected={uid:{**row,'version':[1,0,1],'files':{'manifest.json':'old'}}for uid,row in inputs.items()}
  observed=inventory['packs'][0];observed['files']['content.bin']='owner-installed-content'
  selection=copy.deepcopy(m.current_selection())
  selection['owner_installed_inputs']={observed['uuid']:{'side':observed['side'],'version':observed['version'],
   'tree':m.tree(observed['files']),'reason':'Owner-installed temporary fix; replace with canonical output'}}
  before=copy.deepcopy((inventory,expected,selection))
  with patch.object(m,'current_selection',return_value=selection):
   self.assertTrue(m.curated_live_inputs_match(inventory,expected))
   for field,value in [('files',{'content.bin':'unreviewed'}),('version',[1,0,3]),('side','resource')]:
    changed=copy.deepcopy(inventory);changed['packs'][0][field]=value
    self.assertFalse(m.curated_live_inputs_match(changed,expected))
  self.assertEqual((inventory,expected,selection),before)

 def test_installed_updates_do_not_admit_undeclared_changes_in_other_packs(self):
  inputs=self.owner_pair();other=self.original['packs'][0]
  inventory={'packs':[*inputs.values(),copy.deepcopy(other)]}
  expected={uid:{**row,'version':[1,0,1],'files':{'manifest.json':'old'}}for uid,row in inputs.items()}
  expected[other['uuid']]=copy.deepcopy(other)
  inventory['packs'][-1]['files']['unexpected.js']='unknown'
  self.assertFalse(m.curated_live_inputs_match(inventory,expected))

 def owner_companion(self,modules=None,dependency_version=None):
  inputs=self.owner_pair();uid='reviewed-data-companion';root=Path(inputs['reviewed-behavior']['path']).parent/uid;root.mkdir()
  version=[1,0,3]
  self.guard.atomic(root/'manifest.json',{'header':{'uuid':uid,'version':version},
   'modules':modules or [{'type':'data','version':version}],
   'dependencies':[{'uuid':'reviewed-behavior','version':dependency_version or [1,0,2]}]})
  (root/'recipes.json').write_text('{"ingredient":"retained-item"}')
  self.rows.append({'uuid':uid,'side':'behavior','group':'Reviewed data companion','kind':'literal',
   'companion_of':'reviewed-behavior','input_version':version,'output_version':version,
   'input_tree':m.tree(self.guard.hashes(root)),'output_tree':m.tree(self.guard.hashes(root)),
   'provenance':{'official_author_release':False}})
  self.value['retained_inputs']=self.rows;self.write(stable.CURATED_INPUT,self.value)
  self.catalog['selection']['sha256']=m.digest((self.root/stable.CURATED_INPUT).read_bytes());self.commit('Exact declared data companion')
  m.c.CONFIG['curated_owner_inputs'][uid]=str(root)
  return uid

 def test_declared_data_companion_requires_exact_complete_parent_pair(self):
  uid=self.owner_companion();before=copy.deepcopy(self.original)
  selected=m.curated_owner_inputs();self.assertIn(uid,selected);self.assertEqual(self.original,before)
  del m.c.CONFIG['curated_owner_inputs']['reviewed-behavior']
  with self.assertRaisesRegex(AssertionError,'declared parent pair|complete declared'):m.curated_owner_inputs()

 def test_data_companion_cannot_introduce_script_or_wrong_parent_dependency(self):
  self.owner_companion(modules=[{'type':'script','version':[1,0,3]}])
  with self.assertRaisesRegex(AssertionError,'companion modules'):m.curated_owner_inputs()

 def test_data_companion_rejects_stale_parent_version(self):
  self.owner_companion(dependency_version=[1,0,1])
  with self.assertRaisesRegex(AssertionError,'companion modules'):m.curated_owner_inputs()

 def owner_standalone(self,modules=None):
  uid=self.owner_companion(modules=modules);root=Path(m.c.CONFIG['curated_owner_inputs'][uid])
  row=next(row for row in self.rows if row['uuid']==uid);row.pop('companion_of')
  manifest=self.guard.read(root/'manifest.json')
  manifest['dependencies'].append({'uuid':'reviewed-resource','version':[1,0,2]})
  self.guard.atomic(root/'manifest.json',manifest)
  row['input_tree']=row['output_tree']=m.tree(self.guard.hashes(root))
  self.write(stable.CURATED_INPUT,self.value)
  self.catalog['selection']['sha256']=m.digest((self.root/stable.CURATED_INPUT).read_bytes())
  self.commit('Explicit standalone data input')
  return uid

 def test_standalone_data_input_can_preserve_multiple_dependencies(self):
  uid=self.owner_standalone();before=copy.deepcopy(self.original)
  selected=m.curated_owner_inputs();self.assertIn(uid,selected)
  self.assertEqual(self.original,before)

 def test_standalone_owner_input_cannot_add_script_execution(self):
  self.owner_standalone(modules=[{'type':'script','version':[1,0,3]}])
  with self.assertRaisesRegex(AssertionError,'only data modules'):m.curated_owner_inputs()

 def test_only_selected_roots_and_complete_canonical_fishing_are_used(self):
  roots,sources,report,receipt=self.selected()
  self.assertEqual(len(roots),5);self.assertNotIn(Path(self.excluded['path']),roots)
  for uid,row in report['packs'].items():
   self.assertEqual(sources[uid]['owner'],'preserved');self.assertIs(sources[uid]['official_author_release'],False)
   if sources[uid]['kind']=='canonical-fishing':
    self.assertTrue(Path(row['path']).is_relative_to(self.root/'companion-sources/fishing-current-local/runtimeowner'))
    self.assertIn('owned-fix.js',next(p for p in receipt['packs'] if p['uuid']==uid)['files'])
  m.verify_curated_inputs(receipt,report)
  self.guard.atomic(self.run/'curated-input-selection.json',report)
  refs=m.input_refs();self.assertIn('curated_retained_capture',refs)
  self.guard.atomic(self.run/'curated-input-selection.json',{**report,'client':True})
  self.assertNotEqual(m.input_refs(),refs)

 def test_stable_saved_world_reuses_exact_retained_inputs_without_a_fresh_world_claim(self):
  m.c.CONFIG.pop('fresh_world')
  m.c.CONFIG['delivery_profile']='senluo-stable-lock-v1'
  roots,sources,report,receipt=self.selected()
  self.assertEqual(len(roots),5)
  self.assertNotIn(Path(self.excluded['path']),roots)
  m.verify_curated_inputs(receipt,report)
  self.assertFalse(report['native_loading'])
  changed=copy.deepcopy(self.original);changed['packs'][0]['files']['content.bin']='0'*64
  with self.assertRaisesRegex(AssertionError,'captured input bytes changed'):
   m.select_curated_inputs(changed)

 def test_missing_capture_or_changed_captured_bytes_are_rejected(self):
  missing=copy.deepcopy(self.original);missing['packs']=missing['packs'][1:]
  with self.assertRaisesRegex(AssertionError,'Missing or ambiguous'):m.select_curated_inputs(missing)
  changed=copy.deepcopy(self.original);changed['packs'][0]['files']['content.bin']='f'*64
  with self.assertRaisesRegex(AssertionError,'captured input bytes changed'):m.select_curated_inputs(changed)

 def test_installation_targets_require_the_exact_selected_retained_outputs(self):
  _,_,report,receipt=self.selected()
  m.c.atomic(self.run/'curated-input-selection.json',report)
  self.assertEqual(m.installation_targets(receipt),set(report['packs']))
  changed=copy.deepcopy(receipt);changed['packs'][0]['files']['content.bin']='0'*64
  with self.assertRaisesRegex(AssertionError,'Curated candidate output differs'):
   m.installation_targets(changed)

 def test_curated_candidate_also_checks_the_declared_whole_author_replacement(self):
  _,_,report,receipt=self.selected()
  replacements={};selected={}
  for side in ('behavior','resource'):
   uid='replacement-'+side
   actual=self.pack(self.root/'replacement'/side,uid,side,[1,8,10071],b'exact owner replacement')
   replacements[uid]={'side':side,'version':actual['version'],'tree':m.tree(actual['files'])}
   selected[uid]={**replacements[uid],'path':actual['path']}
   receipt['packs'].append({**actual,'source':{'owner':'preserved','role':'owner_accepted_author_replacement','official_author_release':False}})
  selection={'kind':'author_replacement_selection','packs':selected}
  with patch.object(m,'replacement_rows',return_value=replacements):
   with self.assertRaises(AssertionError):m.verify_curated_inputs(receipt,report)
   m.verify_curated_inputs(receipt,report,selection)
   altered=copy.deepcopy(receipt);altered['packs'][-1]['files']['content.bin']='0'*64
   with self.assertRaisesRegex(AssertionError,'Replacement candidate output differs'):
    m.verify_curated_inputs(altered,report,selection)

 def test_retained_pair_data_changes_replay_from_actual_selected_paths(self):
  _,_,report,receipt=self.selected();rows={};selected={};outputs={}
  for side,label in [('BP','behavior'),('RP','resource')]:
   uid='data-owner-'+side
   before=self.pack(self.root/'replacement'/side,uid,label,[1,0,0],b'retain this extra file')
   after=self.pack(self.root/'output'/side,uid,label,[1,0,10001],b'retain this extra file')
   rows[uid]={'uuid':uid,'author':'DataOwner','side':label,'version':before['version'],'tree':m.tree(before['files'])}
   selected[uid]={**rows[uid],'path':before['path']};outputs[side]=after
  block='blocks/owned.json';payload=b'{"owned":true}'
  outputs['BP']['files'][block]=hashlib.sha256(payload).hexdigest()
  spec={'kind':'addon-owned-data','id':'data-owner','host_uuid':'data-owner-BP',
        'behavior_uuid':'data-owner-BP','resource_uuid':'data-owner-RP',
        'owner_version':self.baseline['version'],'local_pack_version':[1,0,10001],
        'official_author_release':False,
        'original_files':{side+'/manifest.json':self.guard.hashes(Path(selected['data-owner-'+side]['path']))['manifest.json'] for side in outputs},
        'patched_files':{side+'/'+name:value for side,out in outputs.items() for name,value in out['files'].items() if name=='manifest.json' or name==block}}
  path=self.root/'runtime/BP/host-extensions/data-owner.json';path.parent.mkdir();self.guard.atomic(path,spec)
  self.commit('Declared owner data move')
  extension={**spec,'spec_sha256':m.c.sha(path),'repository':self.baseline['repository'],
             'commit':self.git('rev-parse','HEAD'),'working_candidate':False}
  for out in outputs.values():
   receipt['packs'].append({**out,'source':{'owner':'preserved','role':'owner_accepted_author_replacement',
                                          'official_author_release':False,'reviewed_extensions':[extension]}})
  selection={'kind':'author_replacement_selection','packs':selected}
  with patch.object(m,'replacement_rows',return_value=rows):
   m.verify_curated_inputs(receipt,report,selection)
   altered=copy.deepcopy(receipt);altered['packs'][-1]['files']['unreviewed.bin']='0'*64
   with self.assertRaisesRegex(AssertionError,'undeclared files'):m.verify_curated_inputs(altered,report,selection)
   (Path(selected['data-owner-BP']['path'])/'content.bin').write_bytes(b'changed captured input')
   with self.assertRaisesRegex(AssertionError,'input changed after selection'):m.verify_curated_inputs(receipt,report,selection)

 def test_new_owner_fishing_pair_is_retained_without_the_legacy_adapter(self):
  for row in self.rows:
   if row['kind']!='canonical-fishing':continue
   row.update(group='Fishing',kind='literal',output_version=row['input_version'],output_tree=row['input_tree'],
              provenance={'official_author_release':False,'original_archive_verified':False,'latest_stable_verified':False})
   for key in ('canonical_source','recipe_path','recipe_sha256'):row.pop(key)
  self.write(stable.CURATED_INPUT,self.value)
  self.catalog['selection']['sha256']=m.digest((self.root/stable.CURATED_INPUT).read_bytes())
  self.commit('Select the complete owner Fishing pair')
  _,sources,report,receipt=self.selected()
  m.verify_curated_inputs(receipt,report)
  for row in self.rows:
   if row['group']=='Fishing':
    self.assertEqual(sources[row['uuid']]['kind'],'literal')
    self.assertEqual(report['packs'][row['uuid']]['path'],next(p['path'] for p in self.original['packs'] if p['uuid']==row['uuid']))
  row=next(row for row in self.rows if row['group']=='Fishing')
  row['kind']='canonical-fishing'
  self.write(stable.CURATED_INPUT,self.value)
  self.catalog['selection']['sha256']=m.digest((self.root/stable.CURATED_INPUT).read_bytes())
  self.commit('Reject mixing two Fishing producers')
  with self.assertRaisesRegex(AssertionError,'incomplete or mixed'):self.selected()

 def test_new_world_can_reuse_the_complete_installed_fishing_output(self):
  for actual in self.original['packs']:
   row=next((row for row in self.rows if row['uuid']==actual['uuid'] and row['kind']=='canonical-fishing'),None)
   if row is None:continue
   root=self.root/row['canonical_source']
   actual.update(version=row['output_version'],files=self.guard.hashes(root))
  _,_,report,receipt=self.selected()
  m.verify_curated_inputs(receipt,report)
  for actual in self.original['packs']:
   if actual['version']==[1,3,10005]:
    self.assertEqual(report['packs'][actual['uuid']]['captured_version'],[1,3,10005])
    actual['files']['content.bin']='f'*64
    with self.assertRaisesRegex(AssertionError,'captured input bytes changed'):self.selected()
    break

 def test_whole_fishing_recipe_and_candidate_selection_cannot_be_substituted(self):
  roots,sources,report,receipt=self.selected()
  fishing=self.root/'companion-sources/fishing-current-local/runtimeowner/BP/content.bin'
  before=fishing.read_bytes();fishing.write_bytes(b'packaging substitution')
  with self.assertRaisesRegex(AssertionError,'canonical runtime bytes differ'):m.select_curated_inputs(self.original)
  fishing.write_bytes(before)
  altered=copy.deepcopy(receipt);altered['packs'][0]['files']['content.bin']='f'*64
  with self.assertRaisesRegex(AssertionError,'candidate output differs'):m.verify_curated_inputs(altered,report)
  altered=copy.deepcopy(receipt);altered['packs'].append({**self.excluded,'source':{'owner':'preserved'}})
  with self.assertRaisesRegex(AssertionError,'unselected retained input'):m.verify_curated_inputs(altered,report)
  recipe=self.root/'companion-sources/fishing-current-local/recipe.json';recipe.write_bytes(recipe.read_bytes()+b'\n')
  with self.assertRaisesRegex(AssertionError,'evidence changed'):m.select_curated_inputs(self.original)

class LockedArchiveReplacementTests(unittest.TestCase):
 def test_current_whole_pair_can_replace_a_locked_archive_without_a_host_adapter(self):
  with tempfile.TemporaryDirectory() as directory:
   root=Path(directory);(root/'family').mkdir()
   pair={side:{'uuid':'archive-'+side,'version':[1,0,10001],
               'tree':m.tree({'manifest.json':'1'*64})} for side in ('BP','RP')}
   upstream={'upstream':[{'name':'BetterBiomes','packs':[{'uuid':row['uuid']} for row in pair.values()]}]}
   (root/'family/upstream.lock.json').write_text(json.dumps(upstream))
   selection={'authors':{},'replacement_packs':{'BetterBiomes':pair}}
   captured={'packs':[{'uuid':row['uuid'],'side':side,'version':row['version'],
                       'files':{'manifest.json':'1'*64},'path':str(root/side)}
                      for side,row in (('behavior',pair['BP']),('resource',pair['RP']))]}
   with patch.object(m,'curated_selected',return_value=True),patch.object(m,'current_selection',return_value=selection),patch.object(m.c,'T',root):
    roots,sources,report=m.select_replacement_inputs(captured)
    self.assertEqual(len(roots),2)
    self.assertTrue(all(row['role']=='owner_accepted_author_replacement' and row['official_author_release'] is False for row in sources.values()))
    self.assertEqual(set(report['packs']),{row['uuid'] for row in pair.values()})
    changed=copy.deepcopy(captured);changed['packs'][0]['files']['clover.json']='2'*64
    with self.assertRaisesRegex(AssertionError,'replacement bytes changed'):m.select_replacement_inputs(changed)
    pair['RP']['uuid']='unrelated-resource'
    with self.assertRaisesRegex(AssertionError,'complete archive pair'):m.replacement_rows()
    selection['replacement_packs']={'Unknown':pair}
    with self.assertRaisesRegex(AssertionError,'reviewed upstream lock'):m.replacement_rows()

class LocalEvidenceBundle(unittest.TestCase):
 def setUp(self):
  temporary=tempfile.TemporaryDirectory();self.addCleanup(temporary.cleanup);self.root=Path(temporary.name)
  self.repo=self.root/'source';self.repo.mkdir()
  self.git('init','--quiet');(self.repo/'runtime.txt').write_text('runtime\n');self.git('add','.');self.commit('source')
  self.source=self.git('rev-parse','HEAD');self.tree=self.git('rev-parse','HEAD^{tree}')
  patcher=patch.object(m.c,'EXTENSION',self.repo);patcher.start();self.addCleanup(patcher.stop)
  self.zip=self.root/'bundle.zip'
 def git(self,*args):
  return subprocess.check_output(['git','-C',str(self.repo),'-c','user.name=Fixture','-c','user.email=fixture@example.invalid','-c','commit.gpgsign=false',*args],text=True).strip()
 def commit(self,label):self.git('commit','--quiet','-m',label)
 def write(self,members):
  import zipfile
  with zipfile.ZipFile(self.zip,'w',zipfile.ZIP_DEFLATED) as archive:
   for name,raw in members.items():archive.writestr(name,raw)
 def test_bundle_members_bind_to_the_exact_source_tree(self):
  self.write({'current-author-functional.json':b'{"schema":1}','report.json':b'ok'})
  members,ci=m.local_artifact_members(str(self.zip),self.source,self.tree)
  self.assertEqual(members['current-author-functional.json'],b'{"schema":1}')
  self.assertEqual(ci['mode'],'local_bundle')
  self.assertEqual(ci['artifact_digest'],'sha256:'+hashlib.sha256(self.zip.read_bytes()).hexdigest())
 def test_changed_source_tree_is_rejected(self):
  self.write({'proof.json':b'x'})
  with self.assertRaisesRegex(AssertionError,'source tree differs'):m.local_artifact_members(str(self.zip),self.source,'0'*40)
 def test_unsafe_member_paths_are_rejected(self):
  self.write({'dir/proof.json':b'x'})
  with self.assertRaises(AssertionError):m.local_artifact_members(str(self.zip),self.source,self.tree)
 def test_missing_bundle_is_rejected(self):
  with self.assertRaisesRegex(AssertionError,'missing or unsafe'):m.local_artifact_members(str(self.root/'none.zip'),self.source,self.tree)

if __name__=='__main__':unittest.main()
