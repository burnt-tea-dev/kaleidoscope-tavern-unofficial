import unittest
from family_upstream_watch import watch,latest
class UpstreamWatchTests(unittest.TestCase):
 def setUp(self):
  self.lock={'upstream':[{'name':'Cookery','project_id':1,'file_id':10}]};self.project={'id':1,'authors':[{'name':'Loyallay'}]};self.files=[{'id':10,'fileDate':'2026-09-26','releaseType':1,'isAvailable':True}]
 def get(self,path):return self.files if '/files?' in path else self.project
 def test_current_lock(self):
  result=watch(self.lock,self.get);self.assertTrue(result['all_pins_latest']);self.assertFalse(result['automatic_deployment'])
 def test_new_author_file_requires_review_without_mutating_lock(self):
  self.files.append({'id':11,'fileDate':'2026-09-30','releaseType':1});r=watch(self.lock,self.get);self.assertEqual(r['projects'][0]['status'],'review_required');self.assertEqual(self.lock['upstream'][0]['file_id'],10)
 def test_beta_is_reported_separately(self):
  self.files.append({'id':12,'fileDate':'2026-10-01','releaseType':2});r=watch(self.lock,self.get)['projects'][0];self.assertEqual(r['newest_author_file']['id'],12);self.assertEqual(r['newest_stable_file']['id'],10)
 def test_unavailable_file_ignored(self):
  self.files.append({'id':13,'fileDate':'2026-10-02','releaseType':1,'isAvailable':False});self.assertEqual(latest(self.files)['id'],10)
 def test_author_change_not_accepted(self):
  self.project['authors']=[{'name':'Other'}];self.assertEqual(watch(self.lock,self.get)['projects'][0]['status'],'check_failed')
 def test_api_failure_not_current(self):
  def fail(path):raise ValueError('API unavailable')
  self.assertFalse(watch(self.lock,fail)['all_pins_latest'])
 def test_pinned_author_id_accepts_a_rename_but_rejects_a_different_owner(self):
  self.lock['upstream'][0]['author_id']=42;self.project['authors']=[{'id':42,'name':'Renamed'}]
  self.assertTrue(watch(self.lock,self.get)['all_pins_latest'])
  self.project['authors']=[{'id':43,'name':'Loyallay'}]
  self.assertEqual(watch(self.lock,self.get)['projects'][0]['status'],'check_failed')
 def test_owned_port_reference_updates_are_monitored_without_installing_them(self):
  self.lock['monitored_sources']=[{**self.lock['upstream'][0],'name':'Owned port reference','file_id':9,'role':'owned_port_reference'}]
  report=watch(self.lock,self.get)
  self.assertFalse(report['all_pins_latest']);self.assertEqual(len(report['projects']),2)
  self.assertEqual(report['projects'][1]['role'],'owned_port_reference')
  self.assertEqual(report['projects'][1]['status'],'review_required')
if __name__=='__main__':unittest.main()
