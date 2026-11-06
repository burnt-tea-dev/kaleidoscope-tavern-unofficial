"""Exercise curated and managed-local installation against captured old files."""
import copy,json,sys,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from family_update import deploy_live as m
from family_update import managed_drift_recovery, current_author_validation
import family_guard

class InstallationTests(unittest.TestCase):
 def setUp(self):
  self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup);self.root=Path(self.temp.name)
  guard=patch.dict(m.G,{'hashes':family_guard.hashes});guard.start();self.addCleanup(guard.stop)
  self.review=self.root/'review.json';self.review.write_text('{}\n')
  self.original={'packs':[]};self.receipt={'packs':[]};self.outputs={}
  for n in range(4):
   uid='pair-'+str(n);side='behavior' if n%2==0 else 'resource';p=self.root/uid;p.mkdir();(p/'payload').write_text('old')
   old={'uuid':uid,'side':side,'version':[0,0,1],'files':m.hashes(p),'path':str(p),'source':{'owner':'preserved'}}
   row={**old,'version':[0,0,2],'files':{'payload':'new-reviewed-'+str(n)}}
   self.original['packs'].append(old);self.receipt['packs'].append(row);self.outputs[uid]=row['files']
  p=self.root/'unrelated';p.mkdir();(p/'payload').write_text('unchanged')
  row={'uuid':'unrelated','side':'behavior','version':[0,0,1],'files':m.hashes(p),'path':str(p),'source':{'owner':'preserved'}};self.original['packs'].append(row);self.receipt['packs'].append(copy.deepcopy(row))
  self.receipt['packs'].append({'uuid':'owned','side':'behavior','version':[0,0,2],'files':{'payload':'own-source'},'source':{'owner':'owned'}})
 def selection(self):
  with patch.object(m,'R',self.root),patch.object(m,'CONFIG',{}):return m.installation_selection(self.receipt,self.original)
 def test_verified_curated_changes_join_install_while_exact_unchanged_packs_stay_put(self):
  with patch.object(m,'R',self.root),patch.object(m,'CONFIG',{'extension_stable_validation':'source-proof.json'}),patch('family_update.stable_author_validation.verify_installation'),patch.object(current_author_validation,'installation_targets',return_value=set(self.outputs)) as verify:
   family,unchanged=m.installation_selection(self.receipt,self.original)
   verify.assert_called_once_with(self.receipt)
   self.assertEqual({row['uuid'] for row in family},{'owned',*self.outputs})
   self.assertEqual([row['uuid'] for row in unchanged],['unrelated'])
   self.receipt['packs'][4]['files']={'payload':'unreviewed'}
   with self.assertRaisesRegex(AssertionError,'Unreviewed'):
    m.installation_selection(self.receipt,self.original)

 def test_no_review_cannot_upgrade_preserved_files(self):
  with self.assertRaisesRegex(AssertionError,'Unreviewed'):self.selection()
 def test_actual_old_live_drift_is_rejected_even_when_the_new_candidate_is_reviewed(self):
  (Path(self.original['packs'][0]['path'])/'payload').write_text('unauthorized live change')
  with self.assertRaisesRegex(AssertionError,'drifted'):self.selection()

class ManagedLocalInstallationTests(unittest.TestCase):
 def setUp(self):
  InstallationTests.setUp(self)
  self.local_ids={p['uuid'] for p in self.receipt['packs'][:2]}
  self.receipt['packs'][2:4]=copy.deepcopy(self.original['packs'][2:4])
 def selection_local(self):
  with patch.object(m,'R',self.root),patch.object(m,'CONFIG',{'managed_drift_recovery':str(self.review)}),patch.object(managed_drift_recovery,'global_relocations',return_value={uid:{} for uid in self.local_ids}),patch.object(managed_drift_recovery,'verify_local_target',return_value=self.local_ids) as verify:
   result=m.installation_selection(self.receipt,self.original)
   verify.assert_called_once_with(self.receipt,self.original)
   return result
 def test_exact_local_repaired_pair_can_relocate_changed_bytes_without_approving_other_changes(self):
  family,foreign=self.selection_local()
  self.assertEqual({p['uuid'] for p in family},{'owned',*self.local_ids})
  self.assertEqual({p['uuid'] for p in foreign},{'pair-2','pair-3','unrelated'})
  self.receipt['packs'][4]['files']={'payload':'unreviewed'}
  with self.assertRaisesRegex(AssertionError,'Unreviewed'):self.selection_local()
 def test_local_contract_rejection_precedes_preserved_content_reads(self):
  with patch.object(m,'CONFIG',{'managed_drift_recovery':str(self.review)}),patch.object(managed_drift_recovery,'global_relocations',return_value={}),patch.object(managed_drift_recovery,'verify_local_target',side_effect=AssertionError('Exact local target rejected')),patch.object(m,'hashes') as content:
   with self.assertRaisesRegex(AssertionError,'Exact local target rejected'):m.installation_selection(self.receipt,self.original)
   content.assert_not_called()

if __name__=='__main__':unittest.main()
