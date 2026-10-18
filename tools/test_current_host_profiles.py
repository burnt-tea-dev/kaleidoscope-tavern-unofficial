"""Synthetic exact-profile tests contain no author/private implementation."""
import copy,hashlib,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
import stable_host_profiles as stable
import host_extensions
from held_geometry_extension import validate_held_geometry_owner

class CurrentHostProfiles(unittest.TestCase):
 def setUp(self):
  temporary=tempfile.TemporaryDirectory();self.addCleanup(temporary.cleanup);self.root=Path(temporary.name)
  helper=self.root/'scripts/helper.js';helper.parent.mkdir();helper.write_bytes(b'export const synthetic=1;\n')
  self.spec={'id':'fixture:extension','version':[1,0,2],'owner_version':[1,0,55],'host_uuid':'current-host','archive_sha256':'new-archive','original_files':{'scripts/host.js':'before'},'patched_files':{'scripts/host.js':'after'},'copies':{'scripts/helper.js':'scripts/installed.js'}}
  self.public={'id':'fixture:public-0.2.13','version':[0,2,13],'host_uuid':'current-host','archive_sha256':'new-archive','original_files':{'api.js':'native'},'patched_files':{'api.js':'extended'},'copies':{'api-helper.js':{'source':'scripts/api-helper.js','sha256':'exact-public-helper'}}}
  self.profile={**{key:self.spec[key] for key in ['id','version','owner_version','host_uuid','archive_sha256','original_files','patched_files']},'spec_sha256':stable.declaration_sha(self.spec),'copies':{'scripts/installed.js':{'source':'scripts/helper.js','sha256':hashlib.sha256(helper.read_bytes()).hexdigest()}},'source_owner':'upstream_extended','required_extensions':['public-api'],'admission':'current-author-p55'}
  self.catalog={'profiles':{'fresh':self.profile},'public_api':{'id':'old-public','version':[0,2,12],'original_files':{},'patched_files':{},'copies':{}},'public_api_profile':{'id':'old-public','host_uuid':'old-host'},'public_api_profiles':{'public-api-0.2.13':self.public},'public_api_predecessors':{'fresh':['public-api-0.2.13']}}
  for p in [patch.object(stable,'PROFILES',self.catalog['profiles']),patch.object(stable,'CATALOG',self.catalog)]:p.start();self.addCleanup(p.stop)
  self.source={'owner':'upstream_extended','archive_sha256':'new-archive','reviewed_extensions':[stable.receipt(self.public)]}
 def test_exact_declaration_helper_and_one_current_public_receipt_are_required(self):
  self.assertEqual(stable.current_author_profile(self.spec,self.root,self.source),self.profile)
  for key,value in [('owner_version',[1,0,56]),('archive_sha256','old-archive'),('version',[1,0,1]),('patched_files',{'scripts/host.js':'changed'})]:
   with self.subTest(key=key),self.assertRaises(ValueError):stable.current_author_profile({**self.spec,key:value},self.root,self.source)
  for receipts in [[],[self.catalog['public_api']],[stable.receipt(self.public)]*2,[{**stable.receipt(self.public),'copies':{}}]]:
   with self.subTest(receipts=receipts),self.assertRaises(ValueError):stable.current_author_profile(self.spec,self.root,{**self.source,'reviewed_extensions':receipts})
 def test_same_uuid_and_owner_cannot_mix_declared_helpers_or_change_the_source_owner(self):
  for change in [{'owner':'upstream'},{'archive_sha256':'old-archive'}]:
   with self.subTest(change=change),self.assertRaises(ValueError):stable.current_author_profile(self.spec,self.root,{**self.source,**change})
  (self.root/'scripts/helper.js').write_bytes(b'changed implementation')
  with self.assertRaisesRegex(ValueError,'helper differs'):stable.current_author_profile(self.spec,self.root,self.source)
 def test_native_owner_admission_uses_the_reviewed_declaration_not_a_version_whitelist(self):
  config={'repository':'local/senluo-amw-cuisine','version':[1,0,55]}
  validate_held_geometry_owner(config,self.spec)
  for changed in [{**config,'version':[1,0,56]},{**config,'repository':'foreign'}]:
   with self.assertRaises(ValueError):validate_held_geometry_owner(changed,self.spec)
  changed=copy.deepcopy(self.spec);changed['copies']['extra']='scripts/elsewhere.js'
  with self.assertRaisesRegex(ValueError,'exact reviewed profile'):validate_held_geometry_owner(config,changed)

 def test_component58_owner_uses_exact_catalog_for_held_and_enamel(self):
  from enamel_basin_extension import validate_enamel_basin_owner
  self.spec['owner_version']=[1,0,58];self.profile.update(owner_version=[1,0,58],admission='current-author-p58',spec_sha256=stable.declaration_sha(self.spec))
  for validate in [validate_held_geometry_owner,validate_enamel_basin_owner]:
   with self.subTest(adapter=validate.__name__):
    validate({'repository':'local/senluo-amw-cuisine','version':[1,0,58]},self.spec)
    with self.assertRaises(ValueError):validate({'repository':'local/senluo-amw-cuisine','version':[1,0,59]},self.spec)
    changed=copy.deepcopy(self.spec);changed['version']=[1,0,99]
    with self.assertRaisesRegex(ValueError,'exact reviewed profile'):validate({'repository':'local/senluo-amw-cuisine','version':[1,0,58]},changed)

class RecipeRemovalBoundary(unittest.TestCase):
 def setUp(self):
  temporary=tempfile.TemporaryDirectory();self.addCleanup(temporary.cleanup);self.root=Path(temporary.name)
  self.host=self.root/'host';self.host.mkdir();self.owned=self.root/'owned';self.owned.mkdir()
  self.path=self.host/'recipes/vanilla_cooking/salt_smelting.json';self.path.parent.mkdir(parents=True);self.path.write_bytes(b'synthetic recipe')
  self.allowed={'recipes/vanilla_cooking/salt_smelting.json':hashlib.sha256(self.path.read_bytes()).hexdigest()}
  p=patch.object(host_extensions,'REVIEWED_SALT_REMOVAL',self.allowed);p.start();self.addCleanup(p.stop)
  self.manifest={'header':{'version':[1,0,55]},'dependencies':[{'uuid':'5e121bf2-1d2d-4da4-be15-cffc5f216d94','version':[1,2,0]}]}
  self.write_manifest()
  self.spec={'kind':'chinesefood-reviewed-repairs','archive_sha256':'dea708dd6443ea30d23e5791860a50181e8eeb560dcd7ec5a8e80fe22743e659','removed_files':dict(self.allowed)}
  self.profile={'admission':'current-author-p55'}
 def write_manifest(self):
  import json
  (self.owned/'manifest.json').write_text(json.dumps(self.manifest))
 def validate(self):return host_extensions.validate_recipe_removals(self.spec,self.owned,self.host,self.profile)
 def test_missing_or_wrong_companion_fails_before_host_mutation(self):
  self.assertEqual(self.validate(),self.allowed)
  for dependencies in [[],[{'uuid':'5e121bf2-1d2d-4da4-be15-cffc5f216d94','version':[1,1,0]}]]:
   self.manifest['dependencies']=dependencies;self.write_manifest()
   with self.assertRaisesRegex(ValueError,'companion'):self.validate()
   self.assertEqual(self.path.read_bytes(),b'synthetic recipe')
 def test_unreviewed_removals_and_changed_preimage_are_rejected(self):
  self.spec['removed_files']['scripts/main.js']='f'*64
  with self.assertRaisesRegex(ValueError,'exact reviewed'):self.validate()
  self.spec['removed_files']=dict(self.allowed);self.path.write_bytes(b'new author recipe')
  with self.assertRaisesRegex(ValueError,'preimage'):self.validate()
  self.assertEqual(self.path.read_bytes(),b'new author recipe')
 def test_symlink_and_historical_profile_cannot_authorize_removal(self):
  self.profile={'admission':'previous-author'}
  with self.assertRaisesRegex(ValueError,'exact reviewed'):self.validate()
  self.profile={'admission':'current-author-p55'};outside=self.root/'outside';outside.write_bytes(b'synthetic recipe');self.path.unlink();self.path.symlink_to(outside)
  with self.assertRaisesRegex(ValueError,'preimage'):self.validate()
  self.assertEqual(outside.read_bytes(),b'synthetic recipe')

if __name__=='__main__':unittest.main()
