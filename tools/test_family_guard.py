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
 def test_curated_selection_does_not_weaken_complete_47_pack_or_file_gates(self):
  data=guard.read(self.receipt);incoming=[self.row]
  for index in range(46):
   uid='synthetic-retained-'+str(index);path=self.root/uid;path.mkdir();(path/'manifest.json').write_text('{}')
   data['packs'].append({'uuid':uid,'version':[1,0,0],'files':guard.hashes(path),'source':{'owner':'preserved'}})
   incoming.append({'uuid':uid,'version':[1,0,0],'path':str(path)})
  data['upstream_selection']={'synthetic_fixture_only':True,'kind':'current-author-curated-upstream'}
  self.receipt.write_text(json.dumps(data));self.defer_client()
  guard.validate_incoming(incoming,self.policy)
  for changed in (incoming[:-1],incoming+[{'uuid':'unreviewed-extra'}]):
   with self.assertRaisesRegex(ValueError,'完整'):guard.validate_incoming(changed,self.policy)
  (self.pack/'manifest.json').write_text('{"changed":true}')
  with self.assertRaisesRegex(ValueError,'雜湊'):guard.validate_incoming(incoming,self.policy)
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
if __name__=='__main__':unittest.main()
