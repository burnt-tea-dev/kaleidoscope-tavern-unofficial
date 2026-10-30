import contextlib,io,json,tempfile,unittest
from pathlib import Path
from family_bundle import assemble,files_hash,read_definition

class SourceGateEnvironmentTests(unittest.TestCase):
 def test_default_preserves_inherited_identity_semantics(self):
  from family_bundle import source_gate_environment
  self.assertIsNone(source_gate_environment({'key':'peer'},None))
 def test_explicit_peer_identity_is_isolated_and_other_environment_preserved(self):
  import os
  from unittest.mock import patch
  from family_bundle import source_gate_environment
  own={'key':'peer','repository':'owner/peer'}
  with patch.dict(os.environ,{'GITHUB_REPOSITORY':'owner/parent','GITHUB_REPOSITORY_ID':'10','KEEP':'yes'},clear=True):
   env=source_gate_environment(own,{'peer':{'repository':'owner/peer','repository_id':20}})
   self.assertEqual(env,{'GITHUB_REPOSITORY':'owner/peer','GITHUB_REPOSITORY_ID':'20','KEEP':'yes'})
   self.assertEqual(os.environ['GITHUB_REPOSITORY'],'owner/parent')
   self.assertEqual(os.environ['GITHUB_REPOSITORY_ID'],'10')
 def test_reviewed_current_target_preserves_parent_event_and_rejects_forged_metadata(self):
  import os
  from unittest.mock import patch
  from family_bundle import source_gate_environment
  from family_update.repository_identity import target
  own={'key':'tavern','repository':'casama233/kaleidoscope-tavern-unofficial'}
  expected={'tavern':{'repository':own['repository'],'repository_id':1377171148}}
  with tempfile.TemporaryDirectory() as tmp,patch.dict(os.environ,{'GITHUB_EVENT_PATH':'original-event'},clear=True):
   root=Path(tmp);metadata={**target(own['repository']),'logical_runtime_repository':own['repository']}
   (root/'.repo-target.json').write_text(json.dumps(metadata))
   env=source_gate_environment(own,expected,root)
   self.assertEqual(env['GITHUB_REPOSITORY'],'burnt-tea-dev/kaleidoscope-tavern-unofficial')
   self.assertEqual(env['GITHUB_EVENT_PATH'],'original-event');self.assertEqual(env['SENLUO_SOURCE_GATE'],'1')
   metadata['repository_id']=1;(root/'.repo-target.json').write_text(json.dumps(metadata))
   with self.assertRaisesRegex(SystemExit,'reviewed current source target'):source_gate_environment(own,expected,root)

 def test_missing_wrong_or_empty_expected_identity_cannot_disable_child_gate(self):
  from family_bundle import source_gate_environment
  own={'key':'peer','repository':'owner/peer'}
  cases=[{},[],{'peer':{}},{'peer':{'repository':'owner/wrong','repository_id':20}}]
  cases += [{'peer':{'repository':'owner/peer','repository_id':value}} for value in [None,'',0,-1,True,'20']]
  for identities in cases:
   with self.subTest(identities=identities),self.assertRaisesRegex(SystemExit,'invalid expected gate repository identity'):
    source_gate_environment(own,identities)

 def test_explicit_identities_require_exact_source_set_and_strict_mode(self):
  lock={'owned':[{'key':'peer','repository':'owner/peer'}],'upstream':[],'order':{'behavior':[],'resource':[]}}
  with tempfile.TemporaryDirectory() as tmp:
   for identities,working in [({},False),({'extra':{}},False),({'peer':{'repository':'owner/peer','repository_id':20}},True)]:
    out=Path(tmp)/'out'
    with self.subTest(identities=identities,working=working),self.assertRaisesRegex(SystemExit,'expected gate repository identities'):
     assemble(lock,{},[],out,working=working,source_identities=identities)
    self.assertFalse(out.exists())

class PreservedDependencyTests(unittest.TestCase):
 def test_reviewed_interleaving_controls_world_refs_receipt_and_effective_priority(self):
  import zipfile,hashlib
  with tempfile.TemporaryDirectory() as tmp:
   root=Path(tmp);preserved=[];official=[];archive=root/'author.mcaddon'
   with zipfile.ZipFile(archive,'w') as z:
    for uid,side in [('host-b','data'),('host-r','resources')]:
     manifest={'header':{'uuid':uid,'version':[1,0,0]},'modules':[{'type':side}]}
     official.append({'uuid':uid,'version':[1,0,0]})
     z.writestr(uid+'/manifest.json',json.dumps(manifest))
     kind='minecraft:entity' if side=='data' else 'minecraft:client_entity'
     z.writestr(uid+'/overlap.json',json.dumps({kind:{'description':{'identifier':'external:overlap'}}}))
   for uid,side in [('late-b','data'),('first-r','resources'),('first-b','data'),('late-r','resources')]:
    path=root/uid;path.mkdir();preserved.append(path)
    (path/'manifest.json').write_text(json.dumps({'header':{'uuid':uid,'version':[1,0,0]},'modules':[{'type':side}]}))
    kind='minecraft:entity' if side=='data' else 'minecraft:client_entity'
    (path/'overlap.json').write_text(json.dumps({kind:{'description':{'identifier':'external:overlap'}}}))
   order={'behavior':['first-b','host-b','late-b'],'resource':['first-r','host-r','late-r']}
   lock={'owned':[],'upstream':[{'name':'host','sha256':hashlib.sha256(archive.read_bytes()).hexdigest(),'project_id':1,'file_id':2,'packs':official}],'order':{'behavior':['host-b'],'resource':['host-r']}}
   original=json.loads(json.dumps(lock));reviewed=json.loads(json.dumps(order))
   with contextlib.redirect_stdout(io.StringIO()):receipt=assemble(lock,{},[archive],root/'out',preserved=preserved,reviewed_order=order)
   self.assertEqual(lock,original);self.assertEqual(order,reviewed);self.assertEqual(receipt['order'],reviewed)
   for side in order:
    refs=json.loads((root/'out'/('world_'+side+'_packs.json')).read_text())
    self.assertEqual([ref['pack_id'] for ref in refs],order[side])
   overlaps=receipt['definition_overlaps'];self.assertEqual(len(overlaps),4)
   self.assertEqual({row['effective_uuid'] for row in overlaps},{'first-b','first-r'})
   self.assertFalse(receipt['production_ready'])
 def test_reviewed_order_rejects_unknown_missing_duplicate_and_wrong_side(self):
  with tempfile.TemporaryDirectory() as tmp:
   root=Path(tmp);pack=root/'pack';pack.mkdir()
   (pack/'manifest.json').write_text(json.dumps({'header':{'uuid':'a','version':[1,0,0]},'modules':[{'type':'data'}]}))
   lock={'owned':[],'upstream':[],'order':{'behavior':[],'resource':[]}}
   cases=[{'behavior':['unknown'],'resource':[]},{'behavior':[],'resource':[]},{'behavior':['a','a'],'resource':[]},{'behavior':[],'resource':['a']},{'behavior':['a']}]
   for index,order in enumerate(cases):
    with self.subTest(order=order),self.assertRaises(SystemExit):
     assemble(lock,{},[],root/('out'+str(index)),preserved=[pack],reviewed_order=order)
 def test_competing_behavior_players_fail_and_single_definition_is_receipted(self):
  with tempfile.TemporaryDirectory() as tmp:
   root=Path(tmp);packs=[]
   for uid in ['a','b']:
    p=root/uid;p.mkdir();packs.append(p)
    (p/'manifest.json').write_text(json.dumps({'header':{'uuid':uid,'version':[1,0,0]},'modules':[{'type':'data'}]}))
    (p/'player.json').write_text(json.dumps({'minecraft:entity':{'description':{'identifier':'minecraft:player'}}}))
   lock={'owned':[],'upstream':[],'order':{'behavior':[],'resource':[]}}
   with self.assertRaisesRegex(SystemExit,'competing behavior minecraft:player'):
    assemble(lock,{},[],root/'conflict',preserved=packs)
   with contextlib.redirect_stdout(io.StringIO()):r=assemble(lock,{},[],root/'single',preserved=packs[:1])
   self.assertEqual(r['behavior_player_definition']['uuid'],'a')
   self.assertEqual(r['behavior_player_definition']['sha256'],files_hash(packs[0])['player.json'])
 def test_preserved_jsonc_bytes_and_complete_dependency_closure(self):
  with tempfile.TemporaryDirectory() as tmp:
   root=Path(tmp);a=root/'a';b=root/'b';a.mkdir();b.mkdir()
   am={'header':{'uuid':'a','version':[1,0,0]},'modules':[{'type':'data'}],'dependencies':[{'uuid':'b','version':[1,0,0]}]}
   bm={'header':{'uuid':'b','version':[1,0,0]},'modules':[{'type':'resources'}]}
   (a/'manifest.json').write_text(json.dumps(am));(b/'manifest.json').write_text(json.dumps(bm))
   (a/'entity.json').write_text('// preserved author bytes\n{"minecraft:entity":{"description":{"identifier":"external:test","text":"literal ,} // text",},},}')
   lock={'owned':[],'upstream':[],'order':{'behavior':[],'resource':[]}}
   with contextlib.redirect_stdout(io.StringIO()):r=assemble(lock,{},[],root/'candidate',preserved=[a,b])
   self.assertEqual(files_hash(a),files_hash(root/'candidate/behavior_packs/a'));self.assertEqual(len(r['packs']),2)
   self.assertFalse(r['production_ready'])
   with self.assertRaises(SystemExit):assemble(lock,{},[],root/'missing-dependency',preserved=[a])
 def test_jsonc_does_not_rewrite_text_tokens(self):
  with tempfile.TemporaryDirectory() as tmp:
   p=Path(tmp)/'x.json';p.write_text('{"text":"/* quoted */ ,} // quoted", /* comment */ "list":[1,2,],}')
   self.assertEqual(read_definition(p,True),{'text':'/* quoted */ ,} // quoted','list':[1,2]})
   with self.assertRaises(json.JSONDecodeError):read_definition(p,False)

class ReviewedHostExtensionTests(unittest.TestCase):
 def test_current_guide_uses_its_reviewed_helper_and_rejects_changed_bytes(self):
  import hashlib
  from unittest.mock import patch
  from host_extensions import apply_host_extension,GUIDE_HELPER_SOURCE,GUIDE_HELPER_TARGET
  from stable_host_profiles import PROFILES,declaration_sha
  digest=lambda raw:hashlib.sha256(raw).hexdigest()
  before=b'export const ready=1;\n';after=b'export const ready=0+1;\n'
  helper=b'export const currentGuideQueue=true;\n';name='scripts/api/guide.js'
  spec={'schema':1,'kind':'cookery-guide-startup-repair','id':'senluo:cookery-guide-startup-repair','version':[1,0,6],
        'host_uuid':'fixture:current-cookery','archive_sha256':'reviewed-current-archive',
        'expires':'2099-01-01','feedback':'pending author review','authorization':'reviewed current source',
        'removal_condition':'author adopts queue','original_files':{name:digest(before)},
        'patched_files':{name:digest(after)},'imports':{},'json_updates':[],
        'insertions':[{'path':name,'anchor':'1;','position':'before','text':'0+'}],
        'copies':{GUIDE_HELPER_SOURCE:GUIDE_HELPER_TARGET},'helper_sha256':digest(helper)}
  profile={key:spec[key] for key in ['id','version','host_uuid','archive_sha256','original_files','patched_files']}
  profile.update(spec_sha256=declaration_sha(spec),source_owner='upstream',required_extensions=[],
                 copies={GUIDE_HELPER_TARGET:{'source':GUIDE_HELPER_SOURCE,'sha256':digest(helper)}})
  source={'owner':'upstream','archive_sha256':spec['archive_sha256']}
  with tempfile.TemporaryDirectory() as tmp,patch.dict(PROFILES,{'fixture-current-guide':profile}):
   owned,host=Path(tmp)/'owned',Path(tmp)/'host'
   (owned/GUIDE_HELPER_SOURCE).parent.mkdir(parents=True)
   (host/name).parent.mkdir(parents=True)
   (host/name).write_bytes(before);(owned/GUIDE_HELPER_SOURCE).write_bytes(helper)
   apply_host_extension(spec,owned,host,source)
   self.assertEqual((host/name).read_bytes(),after)
   self.assertEqual((host/GUIDE_HELPER_TARGET).read_bytes(),helper)
   (host/GUIDE_HELPER_TARGET).unlink();(host/name).write_bytes(before)
   (owned/GUIDE_HELPER_SOURCE).write_bytes(helper+b'changed')
   with self.assertRaisesRegex(ValueError,'helper differs from the exact reviewed source'):
    apply_host_extension(spec,owned,host,source)
   self.assertEqual((host/name).read_bytes(),before)
   self.assertFalse((host/GUIDE_HELPER_TARGET).exists())
 def test_recipe_cache_profile_is_one_exact_registry_after_the_public_api(self):
  from host_extensions import apply_host_extension,validate_recipe_cache_profile
  name='scripts/api/extensionRegistry.js';before='db08671267c46ed151836a4bb80dccc10dee5ef486489009f49d8e83ac112ca1';after='5cc512e108df7c3ab3583bb9f48422bf9f013c333bcd04bd2a3098022d70eee7'
  pin='da12fe6d39d7514aff1de3c963d69899324d771be5ca0fc3da1ccb759c7ad458'
  # Declaration-only fixture: no synthetic author module or checksum bypass.
  # Actual source and completed hashes remain required by apply_host_extension.
  spec={'schema':1,'kind':'cookery-recipe-cache-repair','id':'senluo:cookery-recipe-cache-repair','version':[1,0,1],'host_uuid':'5df753c9-3436-4fba-87f1-a2da3651cfcf','expires':'2099-01-01','feedback':'author reproduction','authorization':'reviewed private source','removal_condition':'author fixes','archive_sha256':pin,'original_files':{name:before},'patched_files':{name:after},'imports':{},'copies':{},'json_updates':[],'insertions':[{'path':name,'anchor':'anchor'+str(i),'position':'before','text':''} for i in range(7)]}
  source={'owner':'upstream_extended','archive_sha256':pin,'reviewed_extensions':[{'id':'kaleidoscope_grilling:family-api-0.2.10','version':[0,2,10],'patched_files':{name:before}}]}
  validate_recipe_cache_profile(spec,source)
  for field,bad in [('host_uuid','wrong'),('archive_sha256','wrong'),('original_files',{'scripts/other.js':before}),('patched_files',{name:'wrong'}),('imports',{name:'import unsafe;'}),('copies',{'scripts/unsafe.js':'scripts/unsafe.js'}),('json_updates',[{'path':'manifest.json'}]),('insertions',spec['insertions'][:-1])]:
   with self.assertRaises(ValueError):validate_recipe_cache_profile({**spec,field:bad},source)
  for bad in [{'owner':'upstream','archive_sha256':pin},{**source,'reviewed_extensions':[]},{**source,'archive_sha256':'wrong'}]:
   with self.assertRaises(ValueError):validate_recipe_cache_profile(spec,bad)
  with tempfile.TemporaryDirectory() as tmp:
   root=Path(tmp);(root/'scripts/api').mkdir(parents=True);path=root/name;path.write_text('Unreviewed source must remain untouched.\n')
   with self.assertRaisesRegex(ValueError,'original host file hash differs'):apply_host_extension(spec,root,root,source)
   self.assertEqual(path.read_text(),'Unreviewed source must remain untouched.\n')
 def test_guide_profile_rejects_arbitrary_insertions_imports_and_helper_copies(self):
  from host_extensions import validate_guide_startup_profile,GUIDE_HOST_FILE,GUIDE_PREIMAGE,GUIDE_POSTIMAGE,GUIDE_HELPER_SOURCE,GUIDE_HELPER_TARGET,GUIDE_HELPER_SHA
  pin='da12fe6d39d7514aff1de3c963d69899324d771be5ca0fc3da1ccb759c7ad458'
  # A declaration-shaped fixture is insufficient: exact private insertion bytes
  # remain cryptographically pinned, and no author/private module is copied here.
  spec={'id':'senluo:cookery-guide-startup-repair','version':[1,0,1],'host_uuid':'5df753c9-3436-4fba-87f1-a2da3651cfcf','archive_sha256':pin,
        'original_files':{GUIDE_HOST_FILE:GUIDE_PREIMAGE},'patched_files':{GUIDE_HOST_FILE:GUIDE_POSTIMAGE},
        'imports':{GUIDE_HOST_FILE:'import {createCookeryGuideWorkQueue} from "./senluo_guide_startup.js";\n'},
        'copies':{GUIDE_HELPER_SOURCE:GUIDE_HELPER_TARGET},'helper_sha256':GUIDE_HELPER_SHA,'slice_units':24,'json_updates':[],
        'insertions':[{'path':GUIDE_HOST_FILE,'anchor':'unreviewed'+str(i),'position':'after','text':''} for i in range(16)]}
  source={'owner':'upstream_extended','archive_sha256':pin,'reviewed_extensions':[]}
  with self.assertRaisesRegex(ValueError,'exact sixteen'):validate_guide_startup_profile(spec,source)
  for key,value in [('imports',{}),('copies',{'scripts/other.js':GUIDE_HELPER_TARGET}),('helper_sha256','wrong'),('slice_units',25),('patched_files',{GUIDE_HOST_FILE:'changed'})]:
   with self.subTest(key=key),self.assertRaisesRegex(ValueError,'pinned normalization'):validate_guide_startup_profile({**spec,key:value},source)
 def test_exact_insertions_copies_and_immutable_author_identity(self):
  import hashlib
  from host_extensions import apply_host_extension
  with tempfile.TemporaryDirectory() as tmp:
   root=Path(tmp);own=root/'own';host=root/'host';(own/'scripts').mkdir(parents=True);(host/'scripts').mkdir(parents=True)
   p=host/'scripts/entry.js';p.write_text('function run(){return 1;}\n');(own/'scripts/api.js').write_text('export const api=1;\n')
   h=lambda x:hashlib.sha256(x.encode()).hexdigest()
   spec={'schema':1,'id':'own:api','version':[0,1,0],'expires':'2099-01-01','feedback':'docs/proposal.md','authorization':'explicit request','removal_condition':'author adopts API','original_files':{'scripts/entry.js':h(p.read_text())},'patched_files':{'scripts/entry.js':h('function run(){api();return 1;}\n')},'imports':{},'insertions':[{'path':'scripts/entry.js','anchor':'function run(){','position':'after','text':'api();'}],'copies':{'scripts/api.js':'scripts/api.js'},'archive_sha256':'pinned'}
   source={'owner':'upstream','archive_sha256':'pinned'}
   for key,bad in [('expires','2000-01-01'),('archive_sha256','wrong')]:
    broken={**spec,key:bad}
    with self.assertRaises(ValueError):apply_host_extension(broken,own,host,source)
   broken={**spec,'copies':{'../secrets.js':'scripts/api.js'}}
   with self.assertRaises(ValueError):apply_host_extension(broken,own,host,source)
   # Failed path validation must happen before mutations (use a fresh host below).
   p.write_text('function run(){return 1;}\n')
   proof=apply_host_extension(spec,own,host,source)
   self.assertEqual(proof['version'],[0,1,0]);self.assertEqual(p.read_text(),'function run(){api();return 1;}\n');self.assertEqual((host/'scripts/api.js').read_bytes(),(own/'scripts/api.js').read_bytes())
   with self.assertRaises(ValueError):apply_host_extension(spec,own,host,source)

 def test_reviewed_script_replacement_checks_the_real_apply_boundary(self):
  import copy,hashlib
  from unittest.mock import patch
  import stable_host_profiles as profiles
  from host_extensions import apply_host_extension
  with tempfile.TemporaryDirectory() as tmp:
   root=Path(tmp);own=root/'own';own.mkdir();host=root/'host';(host/'scripts').mkdir(parents=True)
   path=host/'scripts/entry.js';before='export function run(){return 1;}\n';after='export function run(){return 2;}\n'
   sha=lambda value:hashlib.sha256(value.encode()).hexdigest()
   spec={'schema':1,'id':'own:startup','version':[1,0,0],'host_uuid':'fixture-host','archive_sha256':'fixture-archive',
         'expires':'2099-01-01','authorization':'fixture','feedback':'fixture','removal_condition':'author adopts fix',
         'original_files':{'scripts/entry.js':sha(before)},'patched_files':{'scripts/entry.js':sha(after)},
         'copies':{},'imports':{},'insertions':[],
         'text_replacements':[{'path':'scripts/entry.js','before':before,'after':after}]}
   def reviewed(value):
    return {'id':value['id'],'host_uuid':value['host_uuid'],'archive_sha256':value['archive_sha256'],
            'admission':profiles.CURATED,'spec_sha256':profiles.declaration_sha(value),
            'source_owner':'upstream','required_extensions':[],'copies':{}}
   source={'owner':'upstream','archive_sha256':spec['archive_sha256']};path.write_text(before)
   with patch.dict(profiles.PROFILES,{'fixture-startup':reviewed(spec)}):
    apply_host_extension(spec,own,host,source)
   self.assertEqual(path.read_text(),after)
   path.write_text(before)
   bad=copy.deepcopy(spec);bad['text_replacements'][0]['before']='return'
   with patch.dict(profiles.PROFILES,{'fixture-startup':reviewed(bad)}):
    with self.assertRaisesRegex(ValueError,'patched host hash differs'):apply_host_extension(bad,own,host,source)
   self.assertEqual(path.read_text(),before)
   bad['text_replacements'][0]['before']='missing anchor'
   with patch.dict(profiles.PROFILES,{'fixture-startup':reviewed(bad)}):
    with self.assertRaisesRegex(ValueError,'non-unique reviewed replacement'):apply_host_extension(bad,own,host,source)
   self.assertEqual(path.read_text(),before)

class AdditiveHostItemCapabilityTests(unittest.TestCase):
 def test_reviewed_titled_freezer_runs_the_real_apply_path_without_widening_storage(self):
  import copy,hashlib
  from unittest.mock import patch
  import stable_host_profiles as profiles
  from host_extensions import apply_host_extension
  with tempfile.TemporaryDirectory() as tmp:
   root=Path(tmp);own=root/'own';host=root/'host';own.mkdir();(host/'blocks/kitchen').mkdir(parents=True)
   name='blocks/kitchen/freezer.json';path=host/name
   original={'minecraft:block':{'description':{'identifier':'kaleidoscope_chinesefood:freezer'},'components':{'minecraft:geometry':'geometry.synthetic_freezer'}}}
   encoded=lambda value:json.dumps(value,ensure_ascii=False,indent=2)+'\n'
   sha=lambda text:hashlib.sha256(text.encode()).hexdigest()
   before=encoded(original);path.write_text(before)
   native={'container':{'slot_count':54,'title':'senluo.freezer.lower'},'dynamic_properties':True}
   def declaration(value):
    changed=copy.deepcopy(original);changed['minecraft:block']['components']['minecraft:block_entity']=value
    return {'schema':1,'id':'senluo:chinesefood-native-freezer-storage','version':[2,0,1],'host_uuid':'synthetic-freezer-host','expires':'2099-01-01','feedback':'synthetic boundary','authorization':'reviewed fixture','removal_condition':'author provides storage','archive_sha256':'synthetic-freezer-archive','original_files':{name:sha(before)},'patched_files':{name:sha(encoded(changed))},'insertions':[],'imports':{},'copies':{},'json_updates':[{'path':name,'pointer':['minecraft:block','components','minecraft:block_entity'],'value':value}]},changed
   def reviewed(spec):
    return {'id':spec['id'],'host_uuid':spec['host_uuid'],'archive_sha256':spec['archive_sha256'],'spec_sha256':profiles.declaration_sha(spec),'admission':profiles.CURATED,'source_owner':'upstream','required_extensions':[],'copies':{}}
   source={'owner':'upstream','archive_sha256':'synthetic-freezer-archive'}
   spec,changed=declaration(native)
   # The normal declaration matcher and its exact digest gate remain active.
   with patch.dict(profiles.PROFILES,{'synthetic-native-freezer':reviewed(spec)}):
    apply_host_extension(spec,own,host,source)
   self.assertEqual(json.loads(path.read_text()),changed)
   path.write_text(before)
   for value in [{'container':{'slot_count':54,'title':'unreviewed.title'},'dynamic_properties':True},
                 {'container':{'slot_count':36,'title':'senluo.freezer.lower'},'dynamic_properties':True},
                 {**native,'unreviewed':True}]:
    bad,_=declaration(value)
    with self.subTest(value=value),patch.dict(profiles.PROFILES,{'synthetic-native-freezer':reviewed(bad)}):
     with self.assertRaisesRegex(ValueError,'reviewed additive freezer'):
      apply_host_extension(bad,own,host,source)
    self.assertEqual(path.read_text(),before)
   with patch.dict(profiles.PROFILES,{'synthetic-native-freezer':reviewed(spec)}):
    drift=copy.deepcopy(spec);drift['patched_files'][name]='0'*64
    with self.assertRaisesRegex(ValueError,'exact reviewed profile'):
     apply_host_extension(drift,own,host,source)
   self.assertEqual(path.read_text(),before)

 def test_freezer_storage_is_additive_and_other_blocks_or_capabilities_fail(self):
  import hashlib,copy
  from host_extensions import apply_host_extension
  with tempfile.TemporaryDirectory() as tmp:
   root=Path(tmp);own=root/'own';host=root/'host';own.mkdir();(host/'blocks/kitchen').mkdir(parents=True)
   name='blocks/kitchen/freezer.json';p=host/name
   original={'minecraft:block':{'description':{'identifier':'kaleidoscope_chinesefood:freezer'},'components':{}}}
   before=json.dumps(original,indent=2)+'\n';p.write_text(before)
   native={'container':{'slot_count':54},'dynamic_properties':True};changed=copy.deepcopy(original);changed['minecraft:block']['components']['minecraft:block_entity']=native
   h=lambda x:hashlib.sha256(x.encode()).hexdigest();op={'path':name,'pointer':['minecraft:block','components','minecraft:block_entity'],'value':native}
   spec={'schema':1,'id':'own:freezer','version':[1,0,0],'expires':'2099-01-01','feedback':'report','authorization':'repair','removal_condition':'author restores storage','archive_sha256':'pinned','original_files':{name:h(before)},'patched_files':{name:h(json.dumps(changed,ensure_ascii=False,indent=2)+'\n')},'insertions':[],'imports':{},'copies':{},'json_updates':[op]}
   for value in [{'container':{'slot_count':999}},True]:
    with self.assertRaises(ValueError):apply_host_extension({**spec,'json_updates':[{**op,'value':value}]},own,host,{'owner':'upstream','archive_sha256':'pinned'})
    self.assertEqual(p.read_text(),before)
   apply_host_extension(spec,own,host,{'owner':'upstream','archive_sha256':'pinned'})
   self.assertEqual(json.loads(p.read_text()),changed)
 def test_only_pinned_additive_offhand_capability_is_accepted(self):
  import hashlib,copy
  from host_extensions import apply_host_extension
  with tempfile.TemporaryDirectory() as tmp:
   root=Path(tmp);own=root/'own';host=root/'host';own.mkdir();(host/'items').mkdir(parents=True)
   p=host/'items/pot.json';original={'minecraft:item':{'description':{'identifier':'author:pot'},'components':{'minecraft:max_stack_size':1}}};before=json.dumps(original,indent=2)+'\n';p.write_text(before)
   changed=copy.deepcopy(original);changed['minecraft:item']['components']['minecraft:allow_off_hand']=True
   h=lambda text:hashlib.sha256(text.encode()).hexdigest();name='items/pot.json'
   op={'path':name,'pointer':['minecraft:item','components','minecraft:allow_off_hand'],'value':True}
   spec={'schema':1,'id':'own:api','version':[0,2,0],'expires':'2099-01-01','feedback':'docs/proposal.md','authorization':'explicit request','removal_condition':'author adds capability','archive_sha256':'pinned','original_files':{name:h(before)},'patched_files':{name:h(json.dumps(changed,ensure_ascii=False,indent=2)+'\n')},'imports':{},'insertions':[],'copies':{},'json_updates':[op]}
   source={'owner':'upstream','archive_sha256':'pinned'}
   for pointer,value in [(['minecraft:item','components','minecraft:max_stack_size'],64),(op['pointer'],False)]:
    bad={**spec,'json_updates':[{**op,'pointer':pointer,'value':value}]}
    with self.assertRaises(ValueError):apply_host_extension(bad,own,host,source)
    self.assertEqual(p.read_text(),before)
   proof=apply_host_extension(spec,own,host,source);self.assertEqual(proof['version'],[0,2,0]);self.assertEqual(json.loads(p.read_text()),changed)


class RecoveryCapabilityTests(unittest.TestCase):
 def test_recovery_is_pinned_and_cannot_replace_identity_or_freezers(self):
  import copy,hashlib
  from host_extensions import apply_host_extension
  with tempfile.TemporaryDirectory() as tmp:
   root=Path(tmp);host=root/'host';own=root/'own';own.mkdir();(host/'blocks').mkdir(parents=True)
   name='blocks/jar.json';path=host/name;value={'minecraft:block':{'description':{'identifier':'kaleidoscope_chinesefood:pickle_jar'},'components':{'minecraft:tick':{'interval_range':[20,20]}}}}
   raw=json.dumps(value,ensure_ascii=False,indent=2)+'\n';path.write_text(raw)
   changed=copy.deepcopy(value);changed['minecraft:block']['components']['minecraft:tick']={'interval_range':[8,8]}
   h=lambda text:hashlib.sha256(text.encode()).hexdigest();pin='63bd2eb2ee2819c985d7c484df633c913cbb995abf3162aa68c997c24ef607f2'
   op={'path':name,'pointer':['minecraft:block','components','minecraft:tick'],'value':{'interval_range':[8,8]},'mode':'reviewed_set'}
   spec={'schema':1,'kind':'chinesefood-reviewed-repairs','id':'own:recovery','version':[1,0,0],'host_uuid':'b3c9db76-4ae6-4986-a380-90a4025d95a9','expires':'2099-01-01','feedback':'review','authorization':'user restoration','removal_condition':'author implements equivalent','archive_sha256':pin,'original_files':{name:h(raw)},'patched_files':{name:h(json.dumps(changed,ensure_ascii=False,indent=2)+'\n')},'imports':{},'insertions':[],'copies':{},'json_updates':[op]}
   source={'owner':'upstream_extended','archive_sha256':pin}
   for pointer in [None,[],['minecraft:block','description','identifier'],['minecraft:block','components','minecraft:block_entity']]:
    bad={**spec,'json_updates':[{**op,'pointer':pointer}]}
    with self.assertRaises(ValueError):apply_host_extension(bad,own,host,source)
    self.assertEqual(path.read_text(),raw)
   with self.assertRaises(ValueError):apply_host_extension({**spec,'host_uuid':'wrong'},own,host,source)
   apply_host_extension(spec,own,host,source);self.assertEqual(json.loads(path.read_text()),changed)
 def test_dough_profile_rejects_unrelated_files_and_capabilities(self):
  from host_extensions import apply_host_extension
  pin='9e5b617cc4c7a08ecd429fb9e42ec10e8d40a1ed5fc1f6f6687c3aff8a45a5d5'
  spec={'schema':1,'kind':'cookery-mooncake-dough-repair','id':'own:dough','version':[1,0,0],'host_uuid':'d322809c-a51e-4742-bfc4-16d3c1491c9d','expires':'2099-01-01','feedback':'review','authorization':'restore','removal_condition':'author fixes','archive_sha256':pin,'original_files':{'scripts/unrelated.js':'x'},'patched_files':{},'imports':{},'insertions':[],'copies':{}}
  with tempfile.TemporaryDirectory() as tmp:
   with self.assertRaisesRegex(ValueError,'unexpected file inventory'):apply_host_extension(spec,Path(tmp),Path(tmp),{'owner':'upstream_extended','archive_sha256':pin})

class StableAuthorSourceChainTests(unittest.TestCase):
 def test_stable_source_requires_complete_exact_preceding_api_and_private_receipts(self):
  import copy
  from stable_host_profiles import CATALOG,PROFILES,public_profiles,receipt,validate_stable_source
  for name,profile in {**PROFILES,'public-api':CATALOG['public_api_profile'],**CATALOG.get('public_api_profiles',{})}.items():
   public=CATALOG.get('public_api_predecessors',{}).get(name,['public-api'])[0]
   prior=[copy.deepcopy(receipt(public_profiles()[public]) if key=='public-api' else receipt(PROFILES[key])) for key in profile['required_extensions']]
   source={'owner':profile['source_owner'],'archive_sha256':profile['archive_sha256'],'reviewed_extensions':prior}
   validate_stable_source(profile,source)
   for field,value in [('owner','preserved'),('archive_sha256','unreviewed')]:
    with self.subTest(profile=name,field=field),self.assertRaisesRegex(ValueError,'exact preceding author'):validate_stable_source(profile,{**source,field:value})
   if not prior:continue
   for index in range(len(prior)):
    missing=copy.deepcopy(source);missing['reviewed_extensions'].pop(index)
    with self.subTest(profile=name,missing=index),self.assertRaisesRegex(ValueError,'exact preceding receipt'):validate_stable_source(profile,missing)
    for field in ['version','original_files','patched_files','copies']:
     bad=copy.deepcopy(source);bad['reviewed_extensions'][index][field]=[] if field=='version' else ({'foreign':'unreviewed'} if not prior[index][field] else {})
     with self.subTest(profile=name,changed=field),self.assertRaisesRegex(ValueError,'exact preceding receipt'):validate_stable_source(profile,bad)
 def test_new_author_identity_cannot_admit_an_unknown_or_coordinated_forged_declaration(self):
  from stable_host_profiles import PROFILES,match_stable_profile
  profile=PROFILES['cookery-recipe-cache-repair']
  with self.assertRaisesRegex(ValueError,'unregistered'):match_stable_profile({'id':'foreign:hook','host_uuid':profile['host_uuid'],'archive_sha256':profile['archive_sha256']})
  # Supplying plausible IDs and matched before/after claims cannot substitute
  # for the reviewed full declaration, including its exact operation bodies.
  forged={key:profile[key] for key in ['id','host_uuid','archive_sha256','version','original_files','patched_files']}
  forged.update(imports={},insertions=[],copies={},json_updates=[])
  with self.assertRaisesRegex(ValueError,'exact reviewed profile'):match_stable_profile(forged)
 def test_old_author_profiles_still_use_their_original_validators(self):
  from stable_host_profiles import match_stable_profile
  self.assertIsNone(match_stable_profile({'host_uuid':'5df753c9-3436-4fba-87f1-a2da3651cfcf','archive_sha256':'da12fe6d39d7514aff1de3c963d69899324d771be5ca0fc3da1ccb759c7ad458'}))

class PublicApiPredecessorTests(unittest.TestCase):
 def test_previous_public_and_private_profiles_are_retained_exactly(self):
  from stable_host_profiles import CATALOG,declaration_sha
  historical=('chinesefood-doll-renderer','chinesefood-freezer-storage','chinesefood-reviewed-repairs',
   'cookery-guide-startup-repair','cookery-mooncake-dough-repair','cookery-recipe-cache-repair',
   'chinesefood-doll-renderer-p44','chinesefood-doll-renderer-p45','chinesefood-doll-renderer-p46',
   'chinesefood-doll-renderer-p47','nether-placeable-drinks-schema-repair-p48',
   'chinesefood-doll-renderer-p48','cookery-enamel-basin-lid-repair-p49')
  self.assertEqual(declaration_sha({name:CATALOG['profiles'][name] for name in historical}),'fb34f46ab2d3e107fb104c27b6987b2567d0e422ff4d1382d28ae2ae254c01e7')
  self.assertEqual(declaration_sha(CATALOG['public_api']),'5041cab6e01b97dec00794cb9d9fb69842fd930d86f21d1a5a6ae6c5e371207c')
  self.assertEqual(declaration_sha(CATALOG['public_api_profile']),'a0c4a77c65b4faca822ae01f71020bb5553ee57bc5029eb5027b880cb80c3939')
  self.assertEqual(declaration_sha(CATALOG['profiles']['cookery-millstone-extension-admission-p50']),'5e29bfc8058016d58d3751ed579743104bbfe0d67c685d028a186a4a723d51d6')
  self.assertEqual(declaration_sha(CATALOG['profiles']['cookery-held-geometry-canonicalization-p50']),'acbb312e00c509e1c5a8b8eefecd98081830cf8563e777c76155dc174ef7ec56')
 def test_millstone_predecessor_has_disjoint_host_writes(self):
  from stable_host_profiles import CATALOG
  mill=CATALOG['profiles']['cookery-millstone-extension-admission-p50']
  api=CATALOG['public_api_profiles']['public-api-0.2.12']
  self.assertFalse(set(mill['original_files']) & (set(api['original_files']) | set(api['patched_files']) | set(api['copies'])))
 def sources(self):
  import copy
  from stable_host_profiles import CATALOG,PROFILES,public_profiles,receipt
  for name,accepted in CATALOG['public_api_predecessors'].items():
   profile=PROFILES[name]
   for public_name in accepted:
    public=receipt(public_profiles()[public_name])
    prior=[copy.deepcopy(public if key=='public-api' else receipt(PROFILES[key])) for key in profile['required_extensions']]
    yield name,profile,{'owner':profile['source_owner'],'archive_sha256':profile['archive_sha256'],'reviewed_extensions':prior}
 def test_each_named_private_profile_accepts_its_declared_complete_public_sources(self):
  from stable_host_profiles import validate_stable_source
  for name,profile,source in self.sources():
   with self.subTest(profile=name,public=source['reviewed_extensions'][0]['id']):validate_stable_source(profile,source)
 def test_unlisted_public_versions_cannot_cross_old_or_current_profile_boundaries(self):
  import copy
  from stable_host_profiles import CATALOG,PROFILES,public_profiles,receipt,validate_stable_source
  for name,accepted in CATALOG['public_api_predecessors'].items():
   profile=PROFILES[name]
   for public_name,public in public_profiles().items():
    if public_name in accepted:continue
    prior=[copy.deepcopy(receipt(public) if key=='public-api' else receipt(PROFILES[key])) for key in profile['required_extensions']]
    source={'owner':profile['source_owner'],'archive_sha256':profile['archive_sha256'],'reviewed_extensions':prior}
    with self.subTest(profile=name,public=public_name),self.assertRaisesRegex(ValueError,'exact preceding receipt'):validate_stable_source(profile,source)
 def test_new_public_source_keeps_every_private_prerequisite(self):
  import copy
  from stable_host_profiles import validate_stable_source
  for name,profile,source in self.sources():
   for index in range(len(source['reviewed_extensions'])):
    missing=copy.deepcopy(source);missing['reviewed_extensions'].pop(index)
    with self.subTest(profile=name,missing=index),self.assertRaisesRegex(ValueError,'exact preceding receipt'):
     validate_stable_source(profile,missing)
 def test_public_identity_cannot_mix_old_helpers_or_drifted_host_bytes(self):
  import copy
  from stable_host_profiles import CATALOG,PROFILES,receipt,validate_stable_source
  profile=PROFILES['cookery-recipe-cache-repair'];public=receipt(CATALOG['public_api_profiles']['public-api-0.2.12'])
  for field in ['id','version','original_files','patched_files','copies']:
   changed=copy.deepcopy(public)
   changed[field]=copy.deepcopy(CATALOG['public_api'][field]) if field in ['id','version','copies'] else {'unreviewed':'bytes'}
   source={'owner':'upstream_extended','archive_sha256':profile['archive_sha256'],'reviewed_extensions':[changed]}
   with self.subTest(field=field),self.assertRaisesRegex(ValueError,'exact preceding receipt'):validate_stable_source(profile,source)
 def test_two_public_installations_cannot_substitute_for_one_predecessor(self):
  import copy
  from stable_host_profiles import CATALOG,PROFILES,receipt,validate_stable_source
  profile=PROFILES['cookery-recipe-cache-repair']
  old=copy.deepcopy(CATALOG['public_api']);new=receipt(CATALOG['public_api_profiles']['public-api-0.2.12'])
  for prior in [[old,new],[new,old],[new,new]]:
   with self.subTest(ids=[p['id'] for p in prior]),self.assertRaisesRegex(ValueError,'exact preceding receipt'):
    validate_stable_source(profile,{'owner':'upstream_extended','archive_sha256':profile['archive_sha256'],'reviewed_extensions':prior})
 def test_any_reviewed_public_receipt_is_an_acceptable_predecessor(self):
  import copy
  from stable_host_profiles import CATALOG,PROFILES,receipt,validate_stable_source
  profile=copy.deepcopy(PROFILES['cookery-recipe-cache-repair'])
  reviewed=receipt(CATALOG['public_api_profiles']['public-api-0.2.12'])
  source={'owner':'upstream_extended','archive_sha256':profile['archive_sha256'],
          'reviewed_extensions':[reviewed]}
  validate_stable_source(profile,source)
  unreviewed=copy.deepcopy(reviewed);unreviewed['id']='unreviewed:public'
  with self.assertRaisesRegex(ValueError,'exact preceding receipt'):
   validate_stable_source(profile,{'owner':'upstream_extended','archive_sha256':profile['archive_sha256'],
                                   'reviewed_extensions':[unreviewed]})
 def test_public_declarations_require_full_digest_and_owned_helper_bytes(self):
  import copy,hashlib
  from unittest.mock import patch
  import stable_host_profiles as m
  raw=b'owned reviewed helper'
  def declared(version):
   return {'id':'owned:public-'+str(version),'version':[version],'host_uuid':'author-host','archive_sha256':'author-archive',
           'original_files':{},'patched_files':{},'copies':{'source.js':'api.js'},'insertions':[{'before':'exact-hook'}]}
  old,new=declared(11),declared(12)
  def profile(spec):
   return {**spec,'spec_sha256':m.declaration_sha(spec),'source_owner':'upstream','required_extensions':[],
           'copies':{'api.js':{'source':'source.js','sha256':hashlib.sha256(raw).hexdigest()}}}
  pold,pnew=profile(old),profile(new)
  catalog={'public_api_profile':pold,'public_api':m.receipt(pold),'public_api_profiles':{'public-api-0.2.12':pnew}}
  with tempfile.TemporaryDirectory() as tmp,patch.object(m,'CATALOG',catalog),patch.object(m,'PROFILES',{}):
   root=Path(tmp);(root/'source.js').write_bytes(raw)
   source={'owner':'upstream','archive_sha256':'author-archive'}
   self.assertIs(m.match_stable_profile(old,root,source),pold)
   self.assertIs(m.match_stable_profile(new,root,source),pnew)
   changed=copy.deepcopy(new);changed['insertions'][0]['before']='different-hook'
   with self.assertRaisesRegex(ValueError,'exact reviewed profile'):m.match_stable_profile(changed,root,source)
   (root/'source.js').write_bytes(b'old or changed helper')
   with self.assertRaisesRegex(ValueError,'exact reviewed source'):m.match_stable_profile(new,root,source)
 def test_actual_grilling151_declaration_and_twelve_owned_copies(self):
  import copy,os
  from stable_host_profiles import CATALOG,match_stable_profile
  configured=os.environ.get('GRILLING151_BP')
  if not configured:self.skipTest('set GRILLING151_BP for the actual public source check')
  root=Path(configured);spec=json.loads((root/'host-extensions/board-api.json').read_text())
  source={'owner':'upstream','archive_sha256':'5b01865d4dd9a455cd80dae4ddc94dc45964e074025f7d24c6f0c5e35f0fbe52'}
  self.assertIs(match_stable_profile(spec,root,source),CATALOG['public_api_profiles']['public-api-0.2.12'])
  self.assertEqual(len(spec['copies']),12)
  for field,value in [('version',[0,2,13]),('archive_sha256','unreviewed'),('insertions',[])]:
   changed=copy.deepcopy(spec);changed[field]=value
   with self.subTest(field=field),self.assertRaisesRegex(ValueError,'exact reviewed profile'):
    match_stable_profile(changed,root,source)

class RetainedAssemblyTests(unittest.TestCase):
 def test_real_assembler_passes_verified58_component_to_adapters_but_records59_source(self):
  import copy,hashlib,zipfile
  from unittest.mock import patch
  import family_bundle as bundle
  import held_geometry_extension as held,enamel_basin_extension as enamel,doll_renderer_extension as renderer
  for kind in ['cookery-held-geometry-canonicalization','cookery-enamel-basin-lid-repair','chinesefood-doll-renderer-cleanup','chinesefood-reviewed-repairs']:
   with self.subTest(kind=kind),tempfile.TemporaryDirectory() as tmp:
    root=Path(tmp);repo=root/'owned';repo.mkdir();archive=root/'author.mcaddon'
    spec={'id':'fixture:'+kind,'kind':kind,'owner_version':[1,0,58],'version':[1,0,4],'host_uuid':'host-r' if kind=='chinesefood-doll-renderer-cleanup' else 'host-b','behavior_uuid':'host-b'}
    if kind=='chinesefood-reviewed-repairs':spec['removed_files']={'recipes/vanilla_cooking/salt_smelting.json':'synthetic-preimage'}
    for side,module in [('BP','data'),('RP','resources')]:
     target=repo/'runtime'/side;target.mkdir(parents=True)
     (target/'manifest.json').write_text(json.dumps({'header':{'uuid':'owned-'+side,'version':[1,0,59]},'modules':[{'type':module}]}))
    declarations=repo/'runtime/BP/host-extensions';declarations.mkdir();(declarations/'fixture.json').write_text(json.dumps(spec))
    config={'repository':'local/senluo-amw-cuisine','version':[1,0,59],'runtime':{'BP':'runtime/BP','RP':'runtime/RP'},'source_trees':{side:files_hash(repo/'runtime'/side)for side in ['BP','RP']}}
    (repo/'baseline.json').write_text(json.dumps(config));component={**config,'version':[1,0,58]}
    anchor={'schema':1,'source_commit':'a'*40,'source_tree':'b'*40,'source_version':[1,0,58]}
    with zipfile.ZipFile(archive,'w') as z:
     for uid,module in [('host-b','data'),('host-r','resources')]:z.writestr(uid+'/manifest.json',json.dumps({'header':{'uuid':uid,'version':[1,0,1]},'modules':[{'type':module}]}))
    lock={'owned':[{'key':'private','repository':config['repository'],'version':config['version'],'source_trees':config['source_trees']}],
          'upstream':[{'name':'synthetic','project_id':1,'file_id':2,'sha256':hashlib.sha256(archive.read_bytes()).hexdigest(),'packs':[{'uuid':uid,'version':[1,0,1]}for uid in ['host-b','host-r']]}],
          'order':{'behavior':['owned-BP','host-b'],'resource':['owned-RP','host-r']}}
    calls=[]
    def apply(spec,owned,host,source,**context):
     self.assertEqual(context,{'retained_owner':{'source_root':str(repo),'source_commit':'d'*40,'sources':{'private':str(repo)}}} if kind=='chinesefood-reviewed-repairs' else {})
     calls.append('single');return {'id':spec['id'],'kind':spec['kind'],'version':spec['version'],'owner_version':spec['owner_version']}
    def apply_pair(spec,bp,rp,bps,rps,owner):
     self.assertEqual(owner,[1,0,58]);calls.append('paired')
     return {'id':spec['id'],'kind':spec['kind'],'owner_version':owner,'local_pack_version':[1,0,10658]}
    def git(args,**kwargs):
     self.assertEqual(args,['git','rev-parse','HEAD']);return 'd'*40+'\n'
    with patch.object(bundle,'retained_component_config',return_value=(component,anchor)) as validate,patch.object(bundle,'apply_host_extension',side_effect=apply),patch.object(renderer,'apply_renderer_extension',side_effect=apply_pair),patch.object(held,'current_author_profile',return_value={'owner_version':[1,0,58]}),patch.object(enamel,'current_author_profile',return_value={'owner_version':[1,0,58]}),patch.object(bundle.subprocess,'check_output',side_effect=git),contextlib.redirect_stdout(io.StringIO()):
     receipt=assemble(lock,{'private':repo},[archive],root/'candidate',working=True)
    validate.assert_called_once_with(repo,config,{'private':repo});self.assertEqual(len(calls),1)
    for row in receipt['packs']:
     if row['uuid'].startswith('owned-'):self.assertEqual(row['version'],[1,0,59])
     elif row['source'].get('reviewed_extensions'):
      proof=row['source']['reviewed_extensions'][0];self.assertEqual(proof['owner_version'],[1,0,58]);self.assertEqual(proof['component_version'],[1,0,58]);self.assertEqual(proof['source_package_version'],[1,0,59]);self.assertEqual(proof['retained_runtime_profile'],anchor)

 def test_component_loader_rechecks_actual_payload_after_explicit_contract_validation(self):
  from unittest.mock import patch
  import family_bundle as bundle
  from family_update import current_author_validation as current
  with tempfile.TemporaryDirectory() as tmp:
   root=Path(tmp);config={'runtime':{'BP':'runtime/BP','RP':'runtime/RP'},'retained_runtime':{'source_commit':'a'*40,'source_tree':'b'*40,'source_version':[1,0,58]}}
   for side in ['BP','RP']:
    target=root/'runtime'/side;target.mkdir(parents=True);(target/'manifest.json').write_text('{}')
   proof={'files':{side:files_hash(root/'runtime'/side)for side in ['BP','RP']}}
   (root/'runtime/BP/unreviewed.js').write_text('unreviewed')
   def output(args,**kwargs):return 'd'*40 if args[0]=='git' else json.dumps(proof).encode()
   with patch.object(bundle.subprocess,'check_output',side_effect=output),patch.object(current,'validate_retained_runtime') as validate,self.assertRaisesRegex(SystemExit,'current source payload differs'):
    bundle.retained_component_config(root,config,{'tavern':root})
   self.assertEqual(validate.call_args.kwargs,{'source_root':root,'sources':{'tavern':root}})


class WholeAuthorReplacementTests(unittest.TestCase):
 def fixture(self, root):
  import hashlib,zipfile
  archive=root/'author.mcaddon';official=[];preserved=[]
  with zipfile.ZipFile(archive,'w') as z:
   for uid,kind in [('host-b','data'),('host-r','resources')]:
    m={'header':{'uuid':uid,'version':[1,0,0]},'modules':[{'type':kind,'version':[1,0,0]}]}
    official.append({'uuid':uid,'version':[1,0,0]});z.writestr(uid+'/manifest.json',json.dumps(m))
    path=root/uid;path.mkdir();m['header']['version']=[1,0,7];m['modules'][0]['version']=[1,0,7]
    (path/'manifest.json').write_text(json.dumps(m));(path/'accepted.txt').write_text('owner accepted extra body')
    preserved.append(path)
  order={'behavior':['host-b'],'resource':['host-r']}
  upstream={'name':'host','sha256':hashlib.sha256(archive.read_bytes()).hexdigest(),'project_id':1,'file_id':2,'packs':official,'manifest_compatibility_release':'must-not-run'}
  lock={'owned':[],'upstream':[upstream],'order':order,'upstream_manifest_releases':{}}
  descriptors={uid:{'owner':'preserved','role':'owner_accepted_author_replacement','official_author_release':False} for uid in ['host-b','host-r']}
  return archive,preserved,lock,descriptors
 def test_complete_pair_skips_archive_transform_and_preserves_all_bytes(self):
  from unittest.mock import patch
  with tempfile.TemporaryDirectory() as tmp:
   root=Path(tmp);archive,preserved,lock,descriptors=self.fixture(root)
   with patch('family_update.upstream_manifest_compatibility.reviewed_pair',side_effect=AssertionError('Archive producer must not execute')),contextlib.redirect_stdout(io.StringIO()):
    receipt=assemble(lock,{},[archive],root/'out',preserved=preserved,preserved_sources=descriptors)
   self.assertEqual(receipt['order'],lock['order'])
   for row,path in zip(receipt['packs'],preserved):
    self.assertEqual(row['files'],files_hash(path));self.assertEqual(row['version'],[1,0,7])
    self.assertEqual(row['source'],descriptors[row['uuid']])
 def test_split_pair_and_missing_captured_half_are_rejected(self):
  with tempfile.TemporaryDirectory() as tmp:
   root=Path(tmp);archive,preserved,lock,descriptors=self.fixture(root)
   with self.assertRaisesRegex(SystemExit,'complete archive pair'):
    assemble(lock,{},[archive],root/'partial',preserved=preserved[:1],preserved_sources={'host-b':descriptors['host-b']})
   with self.assertRaisesRegex(SystemExit,'no exact input UUID'):
    assemble(lock,{},[archive],root/'missing',preserved=preserved[:1],preserved_sources=descriptors)
 def test_ordinary_preserved_descriptor_cannot_suppress_an_author(self):
  from unittest.mock import patch
  with tempfile.TemporaryDirectory() as tmp:
   root=Path(tmp);archive,preserved,lock,descriptors=self.fixture(root)
   for value in descriptors.values():value['role']='unchanged_external_dependency'
   with patch('family_update.upstream_manifest_compatibility.reviewed_pair',side_effect=ValueError('Author path still selected')) as producer:
    with self.assertRaisesRegex(ValueError,'Author path still selected'):
     assemble(lock,{},[archive],root/'out',preserved=preserved,preserved_sources=descriptors)
   producer.assert_called_once()
 def test_owned_paired_hook_is_not_applied_to_a_preserved_replacement(self):
  from unittest.mock import patch
  with tempfile.TemporaryDirectory() as tmp:
   root=Path(tmp);archive,preserved,lock,descriptors=self.fixture(root);owner=root/'owner';bp=owner/'BP';(bp/'host-extensions').mkdir(parents=True)
   config={'repository':'fixture/owner','version':[1,0,1],'runtime':{'BP':'BP'},'source_trees':{}}
   (owner/'baseline.json').write_text(json.dumps(config));(bp/'manifest.json').write_text(json.dumps({'header':{'uuid':'owner','version':[1,0,1]},'modules':[{'type':'data'}]}))
   spec={'kind':'essentials-manifest-compatibility','host_uuid':'host-r','behavior_uuid':'host-b','resource_uuid':'host-r'}
   (bp/'host-extensions/replacement.json').write_text(json.dumps(spec));lock['owned']=[{'key':'fixture','repository':'fixture/owner','version':[1,0,1],'source_trees':{}}];lock['order']['behavior'].insert(0,'owner')
   with patch('family_bundle.subprocess.check_output',return_value='fixture-commit\n'),patch('essentials_manifest_extension.apply_manifest_extension',side_effect=AssertionError('Preserved pair must remain untouched')) as transform,contextlib.redirect_stdout(io.StringIO()):
    receipt=assemble(lock,{'fixture':owner},[archive],root/'out',working=True,preserved=preserved,preserved_sources=descriptors)
   transform.assert_not_called();self.assertEqual(len(receipt['packs']),3)

if __name__=='__main__':unittest.main()
