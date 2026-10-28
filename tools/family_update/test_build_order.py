"""Candidate build carries the captured reviewed order into family assembly."""
from pathlib import Path
import sys,tempfile,unittest
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from family_update import build_candidate as m, identity_migration, managed_drift_recovery

class BuildOrderTests(unittest.TestCase):
 def test_captured_order_is_not_discarded_by_the_candidate_caller(self):
  with tempfile.TemporaryDirectory() as tmp:
   root=Path(tmp);original={'refs':{'behavior':[{'pack_id':uid} for uid in ['extra-first','host','extra-last']],'resource':[]}}
   def read(path):return [{'path':str(root/'extra')}] if Path(path).name=='preserved-packs.json' else {'lock':'test'}
   class AssemblyReached(Exception):pass
   with patch.multiple(m,R=root,C=root/'candidate',T=root,SOURCES={},EXTENSION=None),patch.object(m,'lease_available'),patch.object(m,'verify_predeploy',return_value=original),patch.object(m,'source_state',return_value={}),patch.object(m,'archive_paths',return_value=[]),patch.object(m,'read',side_effect=read),patch.object(identity_migration,'CONFIG',{}),patch.object(m,'assemble',side_effect=AssemblyReached) as assemble:
    with self.assertRaises(AssemblyReached):m.main(['--execute'])
   self.assertEqual(assemble.call_args.kwargs['reviewed_order'],{'behavior':['extra-first','host','extra-last'],'resource':[]})
   self.assertEqual(assemble.call_args.kwargs['preserved'],[root/'extra'])

 def test_reviewed_local_source_descriptor_reaches_assembly_before_receipt_creation(self):
  with tempfile.TemporaryDirectory() as tmp:
   root=Path(tmp);original={'refs':{'behavior':[{'pack_id':'local'}],'resource':[]}}
   sources={'local':{'owner':'preserved','role':'canonical_local_repair','origin_status':'unverified_existing_input'}}
   def read(path):return [{'path':str(root/'original')}] if Path(path).name=='preserved-packs.json' else {}
   class AssemblyReached(Exception):pass
   with patch.multiple(m,R=root,C=root/'candidate',T=root,SOURCES={},EXTENSION=None,CONFIG={'managed_drift_recovery':'review.json'}),patch.object(m,'lease_available'),patch.object(m,'verify_predeploy',return_value=original),patch.object(m,'source_state',return_value={}),patch.object(m,'archive_paths',return_value=[]),patch.object(m,'read',side_effect=read),patch.object(identity_migration,'CONFIG',{}),patch.object(managed_drift_recovery,'select_local_inputs',return_value=([root/'canonical-output'],sources,{'review':'bound'})) as select,patch.object(m,'assemble',side_effect=AssemblyReached) as assemble:
    with self.assertRaises(AssemblyReached):m.main(['--execute'])
   select.assert_called_once_with([root/'original'],original)
   self.assertEqual(assemble.call_args.kwargs['preserved'],[root/'canonical-output'])
   self.assertEqual(assemble.call_args.kwargs['preserved_sources'],sources)


class ReplacementBuildOrderTests(unittest.TestCase):
 def test_replacement_mapping_keys_deduplicate_existing_roots_before_assembly(self):
  from family_update import current_author_validation as v, prospective_preserved_inputs as prospective
  with tempfile.TemporaryDirectory() as tmp:
   root=Path(tmp);original={'refs':{'behavior':[{'pack_id':'bp'},{'pack_id':'extra'}],'resource':[{'pack_id':'rp'}]}}
   old=[root/'old-bp',root/'keep',root/'old-rp'];new=[root/'accepted-bp',root/'accepted-rp']
   sources={uid:{'owner':'preserved','role':'owner_accepted_author_replacement','official_author_release':False} for uid in ['bp','rp']}
   selection={'packs':{'bp':{'path':str(new[0]),'side':'behavior'},'rp':{'path':str(new[1]),'side':'resource'}}}
   def read(path):
    path=Path(path)
    if path.name=='manifest.json':return {'header':{'uuid':{'old-bp':'bp','old-rp':'rp','keep':'extra'}[path.parent.name]}}
    return [] if path.name=='preserved-packs.json' else {}
   class AssemblyReached(Exception):pass
   with patch.multiple(m,R=root,C=root/'candidate',T=root,SOURCES={},EXTENSION=None,CONFIG={}),patch.object(m,'lease_available'),patch.object(m,'verify_predeploy',return_value=original),patch.object(m,'source_state',return_value={}),patch.object(m,'archive_paths',return_value=[]),patch.object(m,'read',side_effect=read),patch.object(m,'atomic'),patch.object(v,'curated_inputs_enabled',return_value=False),patch.object(prospective,'select',return_value=(old,None)),patch.object(v,'select_replacement_inputs',return_value=(new,sources,selection),create=True),patch.object(v,'verify_replacement_inputs',create=True),patch.object(identity_migration,'CONFIG',{}),patch.object(m,'assemble',side_effect=AssemblyReached) as assemble:
    with self.assertRaises(AssemblyReached):m.main(['--execute'])
   self.assertEqual(assemble.call_args.kwargs['preserved'],[root/'keep',*new])
   self.assertEqual(assemble.call_args.kwargs['preserved_sources'],sources)

if __name__=='__main__':unittest.main()
