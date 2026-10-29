import importlib.util,json,tempfile,unittest
from pathlib import Path
spec=importlib.util.spec_from_file_location('guard',Path(__file__).with_name('family_guard.py'));guard=importlib.util.module_from_spec(spec);spec.loader.exec_module(guard)
class FamilyAdmissionTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name);self.pack=self.root/'pack';self.pack.mkdir();(self.pack/'manifest.json').write_text('{}');self.policy=self.root/'policy.json';self.receipt=self.root/'receipt.json'
  self.row={'uuid':'own','version':[1,0,0],'path':str(self.pack)}
  self.receipt.write_text(json.dumps({'packs':[{'uuid':'own','version':[1,0,0],'files':guard.hashes(self.pack),'source':{'owner':'owned','commit':'abc','working_candidate':False}}],'production_ready':True,'acceptance':dict.fromkeys(['static','bds','client','saved_world_migration'],True)}));self.write_policy(str(self.receipt))
 def write_policy(self,approved):self.policy.write_text(json.dumps({'managed_uuids':['own','old-upstream'],'approved_receipt':approved}))
 def tearDown(self):self.tmp.cleanup()
 def test_exact_accepted(self):guard.validate_incoming([self.row],self.policy)
 def test_unrelated_accepted(self):guard.validate_incoming([{'uuid':'other'}],self.policy)
 def test_renamed_family_uuid_rejected(self):
  self.write_policy(None);directory=self.pack/'blocks';directory.mkdir()
  (directory/'alias.json').write_text(json.dumps({'minecraft:block':{'description':{'identifier':'kaleidoscope_tavern:bar_cabinet'}}}))
  with self.assertRaises(ValueError):guard.validate_incoming([{'uuid':'disguised-family','path':str(self.pack)}],self.policy)
 def test_unregistered_family_dependency_rejected(self):
  self.write_policy(None);(self.pack/'manifest.json').write_text(json.dumps({'dependencies':[{'uuid':'own'}]}))
  with self.assertRaises(ValueError):guard.validate_incoming([{'uuid':'new-overlay','path':str(self.pack)}],self.policy)
 def test_unrelated_jsonc_and_comments_accepted(self):
  self.write_policy(None);directory=self.pack/'blocks';directory.mkdir()
  (directory/'other.json').write_text('// "identifier":"kaleidoscope_tavern:example"\n{"minecraft:block":{"description":{"identifier":"unrelated:thing",},},}')
  guard.validate_incoming([{'uuid':'unrelated','path':str(self.pack)}],self.policy)
 def test_audit_detects_new_family_uuid(self):
  world=self.root/'world';pack=world/'behavior_packs/disguised';(pack/'blocks').mkdir(parents=True);(world/'resource_packs').mkdir()
  (pack/'manifest.json').write_text(json.dumps({'header':{'uuid':'disguised'}}))
  (pack/'blocks/alias.json').write_text('{"minecraft:block":{"description":{"identifier":"kaleidoscope_tavern:bar_cabinet"}}}')
  (world/'world_behavior_packs.json').write_text('[{"pack_id":"disguised","version":[1,0,0]}]');(world/'world_resource_packs.json').write_text('[]')
  policy={'managed_uuids':['own'],'installed':{'packs':[],'refs':{'behavior':[],'resource':[]},'status':'quarantined'}}
  result=guard.audit(world,policy);self.assertFalse(result['ok']);self.assertIn('unregistered family',result['errors'][0]['error'])
 def test_hold_blocks_owned_and_old_upstream(self):
  self.write_policy(None)
  for uid in ['own','old-upstream']:
   with self.assertRaises(ValueError):guard.validate_incoming([{'uuid':uid}],self.policy)
 def test_missing_client_acceptance(self):
  data=guard.read(self.receipt);data['acceptance']['client']=False;self.receipt.write_text(json.dumps(data))
  with self.assertRaises(ValueError):guard.validate_incoming([self.row],self.policy)
 def defer_client(self):
  import hashlib
  data=guard.read(self.receipt);data['acceptance']['client']=False;data['production_ready']=False;self.receipt.write_text(json.dumps(data))
  policy=guard.read(self.policy);policy['deferred_client_acceptance']={'source':'explicit_user_instruction','instruction':'Deploy now; I will test the client later.','recorded_at':'2026-10-02T00:00:00Z','receipt_sha256':hashlib.sha256(self.receipt.read_bytes()).hexdigest()};self.policy.write_text(json.dumps(policy))
 def test_explicit_exact_client_deferral(self):
  self.defer_client();guard.validate_incoming([self.row],self.policy)
 def test_deferral_cannot_skip_migration(self):
  self.defer_client();data=guard.read(self.receipt);data['acceptance']['saved_world_migration']=False;self.receipt.write_text(json.dumps(data))
  import hashlib
  policy=guard.read(self.policy);policy['deferred_client_acceptance']['receipt_sha256']=hashlib.sha256(self.receipt.read_bytes()).hexdigest();self.policy.write_text(json.dumps(policy))
  with self.assertRaises(ValueError):guard.validate_incoming([self.row],self.policy)
 def test_fresh_initialization_and_persistence_replace_only_the_fresh_world_gate(self):
  import hashlib
  self.defer_client();data=guard.read(self.receipt)
  data['world_initialization']={'kind':'fresh_world','level_name':'New'}
  data['acceptance'].update(saved_world_migration=False,fresh_world_initialization=True,world_persistence=True)
  def save(value):
   self.receipt.write_text(json.dumps(value));policy=guard.read(self.policy)
   policy['deferred_client_acceptance']['receipt_sha256']=hashlib.sha256(self.receipt.read_bytes()).hexdigest()
   self.policy.write_text(json.dumps(policy))
  save(data);guard.validate_incoming([self.row],self.policy)
  for key in ['fresh_world_initialization','world_persistence']:
   data['acceptance'][key]=False;save(data)
   with self.assertRaises(ValueError):guard.validate_incoming([self.row],self.policy)
   data['acceptance'][key]=True
  data['acceptance']['saved_world_migration']=True;save(data)
  with self.assertRaises(ValueError):guard.validate_incoming([self.row],self.policy)
 def test_deferral_rejects_another_receipt(self):
  self.defer_client();data=guard.read(self.receipt);data['new_candidate']=True;self.receipt.write_text(json.dumps(data))
  with self.assertRaises(ValueError):guard.validate_incoming([self.row],self.policy)
 def test_deferral_still_rejects_patch(self):
  self.defer_client();(self.pack/'hidden-patch.js').write_text('changed')
  with self.assertRaises(ValueError):guard.validate_incoming([self.row],self.policy)
 def test_deferral_does_not_claim_client_passed(self):
  self.defer_client();guard.validate_incoming([self.row],self.policy)
  self.assertFalse(guard.read(self.receipt)['acceptance']['client']);self.assertFalse(guard.read(self.receipt)['production_ready'])
 def test_install_patch_rejected(self):
  (self.pack/'install-only.js').write_text('hidden fix')
  with self.assertRaises(ValueError):guard.validate_incoming([self.row],self.policy)
 def test_incomplete_family_rejected(self):
  data=guard.read(self.receipt);data['packs'].append({'uuid':'second'});self.receipt.write_text(json.dumps(data))
  with self.assertRaises(ValueError):guard.validate_incoming([self.row],self.policy)
 def test_dirty_source_rejected(self):
  data=guard.read(self.receipt);data['packs'][0]['source']['working_candidate']=True;self.receipt.write_text(json.dumps(data))
  with self.assertRaises(ValueError):guard.validate_incoming([self.row],self.policy)
class StableLockAdmissionTests(unittest.TestCase):
 def setUp(self):
  import hashlib
  self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name)
  self.rows=[];self.incoming=[];self.lock_packs=[];self.receipt_packs=[]
  self.order={'behavior':[],'resource':[]}
  for side,prefix in [('behavior','1'),('behavior','2'),('resource','3'),('resource','4')]:
   uid=prefix*8+'-'+prefix*4+'-4'+prefix*3+'-8'+prefix*3+'-'+prefix*12
   root=self.root/uid;root.mkdir()
   manifest={'header':{'uuid':uid,'version':[2,0,1],'name':'Pack '+prefix},
    'modules':[{'type':'data','uuid':str(__import__('uuid').uuid4()),'version':[2,0,1]}],
    'dependencies':[]}
   (root/'manifest.json').write_text(json.dumps(manifest))
   item={'uuid':uid,'version':[2,0,1],'path':str(root)}
   files=guard.hashes(root)
   receipt={'uuid':uid,'side':side,'version':[2,0,1],'files':files,'dependencies':[],
    'source':{'owner':'owned','commit':'a'*40,'working_candidate':False}}
   slot=sum(p['kind']==side for p in self.lock_packs)+1
   source=['observed-installed','example/repo@'+'b'*40,
    'third-party: as-installed 2026-10-29T00:00Z','third-party: as-installed 2026-10-29T00:00+00:00'][len(self.lock_packs)]
   lock={'uuid':uid,'kind':side,'slot':slot,'version':[2,0,1],
    'name':manifest['header']['name'],'path':'worlds/test/'+side+'_packs/'+uid,
    'sha256':hashlib.sha256(uid.encode()).hexdigest(),'modules':manifest['modules'],
    'dependencies':[],'source':source}
   self.incoming.append(item);self.receipt_packs.append(receipt);self.lock_packs.append(lock)
   self.order[side].append(uid)
  # Incoming order is intentionally different from refs/lock order; receipt source
  # order is interleaved, while lock order is behavior slots then resource slots.
  self.incoming.reverse()
  self.receipt_packs=[self.receipt_packs[0],self.receipt_packs[2],self.receipt_packs[1],self.receipt_packs[3]]
  self.family=self.root/'family.json'
  self.family.write_text(json.dumps({'packs':self.receipt_packs,'order':self.order,
   'acceptance':{'client':False,'static':True,'bds':True},'production_ready':False}))
  self.lock=self.root/'lock.json'
  self.lock_value={'schema':1,'name':'candidate','digest_format':'senluo-pack-tree-v1',
   'observed_at':'2026-10-29T00:00:00+00:00','packs':self.lock_packs,
   'status':{'ci':True,'staging_smoke':False,'staging_human':None,'live':None}}
  self.lock.write_text(json.dumps(self.lock_value))
  lock_sha=hashlib.sha256(self.lock.read_bytes()).hexdigest()
  results=[]
  for test in ['family:one','family:two','family:three']:
   for phase in ['first_start','same_world_restart']:
    results.append({'test':test,'phase':phase,'run_id':test+phase,
     'verdict':'pass','checks':{'loaded':True,'saved':True}})
  self.gate={'verdict':'pass','lock_file_sha256':lock_sha,
   'candidate_source':{'packs':[{'path':p['path'],'sha256':p['sha256']} for p in self.lock_packs]},
   'gametest':{'status':'pass','results':results,
    'fixture':{'removed_after_readback':True},'observers':[{'restored':True}],
    'station_census':{'comparison':{'same_station_ids_and_counts':True}}},
   'phases':{'readback':{'drift_zero':True},
    'world_dynamic_properties':{'comparison':{'same_keys_and_types':True}},
    'original_players':{'changed_original_records':{'after_first_stop':[],'after_restart_stop':[]}},
    'perf_gate':{'gate':{'ok':True,'owned_slowdowns':0}},
    'windows':{'first_seconds':120,'restart_seconds':30},
    'prepare':{'mode':'verified_lkg_restore','status':'restored_verified',
     'source_hashes_match':True,'target_hashes_match':True}},
   'native_backend':{'backend':'direct_native','live':False,'admissions':[
    {'ok':True,'reserve_bytes':2*1024**3,'swap_limit_bytes':0}]}}
  self.gate_path=self.root/'gate.json';self.gate_path.write_text(json.dumps(self.gate))
  self.rollback_path=self.root/'rollback.json'
  self.rollback={'status':'rehearsed','rollback_exercise_complete':True,
   'fault':{'injected_module_error_confirmed':True,'script_error_monitor_verified':True},
   'rollback_timing':{'within_15_minutes':True},
   'restore':{'world_and_global_hashes_match_backup':True,'previous_lock_drift_zero':True}}
  self.rollback_path.write_text(json.dumps(self.rollback))
  self.policy=self.root/'policy.json'
  self.policy.write_text(json.dumps({'managed_uuids':[p['uuid'] for p in self.receipt_packs],
   'delivery_profile':'senluo-stable-lock-v1','stable_lock':{'path':str(self.lock),'sha256':lock_sha},
   'stable_gate_b':{'path':str(self.gate_path),'sha256':hashlib.sha256(self.gate_path.read_bytes()).hexdigest()},
   'stable_rollback_exercise':{'path':str(self.rollback_path),'sha256':hashlib.sha256(self.rollback_path.read_bytes()).hexdigest()},
   'approved_receipt':str(self.family),'deferred_client_acceptance':{
    'source':'explicit_user_instruction','instruction':'approved','recorded_at':'2026-10-29T00:00:00Z',
    'receipt_sha256':hashlib.sha256(self.family.read_bytes()).hexdigest()}}))
 def tearDown(self):self.tmp.cleanup()
 def run_guard(self):guard.validate_incoming(self.incoming,self.policy)
 def refresh_gate_hash(self):
  import hashlib
  policy=guard.read(self.policy);policy['stable_gate_b']['sha256']=hashlib.sha256(self.gate_path.read_bytes()).hexdigest()
  self.policy.write_text(json.dumps(policy))
 def refresh_lock_hash(self):
  import hashlib
  policy=guard.read(self.policy);lock_sha=hashlib.sha256(self.lock.read_bytes()).hexdigest()
  policy['stable_lock']['sha256']=lock_sha;self.gate['lock_file_sha256']=lock_sha
  self.gate_path.write_text(json.dumps(self.gate))
  policy['stable_gate_b']['sha256']=hashlib.sha256(self.gate_path.read_bytes()).hexdigest()
  self.policy.write_text(json.dumps(policy))
 def test_valid_profile_accepts_interleaved_receipt_and_reversed_incoming(self):self.run_guard()
 def test_old_policy_remains_compatible(self):
  import hashlib
  policy=guard.read(self.policy);policy.pop('delivery_profile');policy.pop('stable_lock');policy.pop('stable_gate_b')
  data=guard.read(self.family);data['acceptance']['saved_world_migration']=True
  self.family.write_text(json.dumps(data))
  policy['deferred_client_acceptance']['receipt_sha256']=hashlib.sha256(self.family.read_bytes()).hexdigest()
  self.policy.write_text(json.dumps(policy));self.run_guard()
 def test_lock_hash_mismatch_rejected(self):
  policy=guard.read(self.policy);policy['stable_lock']['sha256']='0'*64;self.policy.write_text(json.dumps(policy))
  with self.assertRaises(ValueError):self.run_guard()
 def test_gate_hash_mismatch_rejected(self):
  policy=guard.read(self.policy);policy['stable_gate_b']['sha256']='0'*64;self.policy.write_text(json.dumps(policy))
  with self.assertRaises(ValueError):self.run_guard()
 def test_rollback_hash_mismatch_rejected(self):
  policy=guard.read(self.policy);policy['stable_rollback_exercise']['sha256']='0'*64;self.policy.write_text(json.dumps(policy))
  with self.assertRaises(ValueError):self.run_guard()
 def test_incomplete_rollback_rejected(self):
  self.rollback['fault']['script_error_monitor_verified']=False
  self.rollback_path.write_text(json.dumps(self.rollback))
  policy=guard.read(self.policy);import hashlib
  policy['stable_rollback_exercise']['sha256']=hashlib.sha256(self.rollback_path.read_bytes()).hexdigest()
  self.policy.write_text(json.dumps(policy))
  with self.assertRaises(ValueError):self.run_guard()
 def test_missing_restart_run_rejected(self):
  self.gate['gametest']['results'].pop();self.gate_path.write_text(json.dumps(self.gate));self.refresh_gate_hash()
  with self.assertRaises(ValueError):self.run_guard()
 def test_false_check_rejected(self):
  self.gate['gametest']['results'][0]['checks']['saved']=False;self.gate_path.write_text(json.dumps(self.gate));self.refresh_gate_hash()
  with self.assertRaises(ValueError):self.run_guard()
 def test_unrestored_observer_rejected(self):
  self.gate['gametest']['observers'][0]['restored']=False;self.gate_path.write_text(json.dumps(self.gate));self.refresh_gate_hash()
  with self.assertRaises(ValueError):self.run_guard()
 def test_incoming_drift_rejected(self):
  (Path(self.incoming[0]['path'])/'extra.js').write_text('drift')
  with self.assertRaises(ValueError):self.run_guard()
 def test_helper_loads_from_guard_directory_outside_sys_path(self):
  import runpy,shutil,sys
  checkout=self.root/'isolated-Q';checkout.mkdir()
  tools=Path(__file__).parent
  shutil.copy2(tools/'family_guard.py',checkout/'family_guard.py')
  shutil.copy2(tools/'stable_lock_guard.py',checkout/'stable_lock_guard.py')
  old_path=list(sys.path)
  try:
   sys.path[:]=[p for p in old_path if Path(p or '.').resolve() not in (checkout.resolve(),tools.resolve())]
   loaded=runpy.run_path(str(checkout/'family_guard.py'))
   loaded['validate_incoming'](self.incoming,self.policy)
  finally:sys.path[:]=old_path
 def test_legacy_guard_runpy_works_when_helper_absent(self):
  import runpy,shutil,sys,hashlib
  checkout=self.root/'legacy-Q';checkout.mkdir()
  tools=Path(__file__).parent;shutil.copy2(tools/'family_guard.py',checkout/'family_guard.py')
  policy=guard.read(self.policy);policy.pop('delivery_profile');policy.pop('stable_lock');policy.pop('stable_gate_b');policy.pop('stable_rollback_exercise')
  family=guard.read(self.family);family['acceptance']['saved_world_migration']=True
  self.family.write_text(json.dumps(family));policy['deferred_client_acceptance']['receipt_sha256']=hashlib.sha256(self.family.read_bytes()).hexdigest()
  self.policy.write_text(json.dumps(policy));old_path=list(sys.path)
  try:
   sys.path[:]=[p for p in old_path if Path(p or '.').resolve() not in (checkout.resolve(),tools.resolve())]
   loaded=runpy.run_path(str(checkout/'family_guard.py'));loaded['validate_incoming'](self.incoming,self.policy)
  finally:sys.path[:]=old_path
 def test_lock_rejects_unrecognized_pending_source(self):
  self.lock_value['packs'][0]['source']='working-candidate';self.lock.write_text(json.dumps(self.lock_value));self.refresh_lock_hash()
  with self.assertRaises(ValueError):self.run_guard()
 def test_family_side_order_mismatch_rejected(self):
  import hashlib
  data=guard.read(self.family);data['order']['behavior'].reverse();self.family.write_text(json.dumps(data))
  policy=guard.read(self.policy);policy['deferred_client_acceptance']['receipt_sha256']=hashlib.sha256(self.family.read_bytes()).hexdigest()
  self.policy.write_text(json.dumps(policy))
  with self.assertRaises(ValueError):self.run_guard()
if __name__=='__main__':unittest.main()
