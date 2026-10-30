"""Historical views may normalize only bound, explicitly reviewed identities."""
import base64,gzip,hashlib,json,tempfile,unittest
from unittest import mock
from pathlib import Path
import baseline_reference as reference
from baseline_reference import previous_bytes,rows,release_projections,functional_rows,functional_layers,asset_layers
class IdentityTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.r=Path(self.tmp.name);(self.r/'data').mkdir()
  for name,value in [('package.json',{'version':'1.2.3'}),('release.json',{'version':'1.2.3'}),('baseline.json',{'version':[1,2,3]})]:(self.r/name).write_text(json.dumps(value))
 def fixture(self,name,current,reviewed,spec):
  self.p=self.r/name;self.p.parent.mkdir(parents=True,exist_ok=True);self.p.write_bytes(current)
  row={'before':None,'after':hashlib.sha256(reviewed).hexdigest()}
  (self.r/'data/baseline-reconciliation.json').write_text(json.dumps({'files':{name:row},'releaseVersionProjections':{name:spec}}));rows.cache_clear();release_projections.cache_clear();functional_rows.cache_clear();functional_layers.cache_clear();asset_layers.cache_clear()
 def functional_fixture(self,with_baseline=True,name='runtime/BP/scripts/bedrock/drink-effects.js'):
  self.p=self.r/name;self.p.parent.mkdir(parents=True,exist_ok=True)
  self.current=b'applyReviewedSourceFix();\n';self.predecessor=b'previousReviewedSource();\n';self.original=b'immutableHistoricalSource();\n'
  self.p.write_bytes(self.current)
  row={'before':hashlib.sha256(self.predecessor).hexdigest(),'after':hashlib.sha256(self.current).hexdigest(),'reason':'Reviewed source behavior and completion regression','reverseOps':[[0,1,self.predecessor.decode()]]}
  historical={'before':hashlib.sha256(self.original).hexdigest(),'after':row['before'],'beforeContent':self.original.decode()}
  self.ledger={'schema':1,'testOnly':True,'files':{name:historical} if with_baseline else {},'reviewedFunctionalDeltas':{name:row}}
  self.write_functional_ledger()
 def write_functional_ledger(self):
  (self.r/'data/baseline-reconciliation.json').write_text(json.dumps(self.ledger));rows.cache_clear();release_projections.cache_clear();functional_rows.cache_clear();functional_layers.cache_clear();asset_layers.cache_clear()
 def test_bound_script_version_preserves_all_remaining_bytes(self):
  old=b"export const BUILD_VERSION='1.2.2-baseline.1';\n";new=old.replace(b'1.2.2',b'1.2.3')
  self.fixture('runtime/build.js',new,old,{'kind':'build_identity','reviewedVersion':'1.2.2'})
  self.assertEqual(previous_bytes(self.r,self.p),old)
  self.p.write_bytes(new+b'runUnreviewed();\n')
  with self.assertRaises(AssertionError):previous_bytes(self.r,self.p)
 def test_manifest_version_updates_do_not_allow_dependency_or_field_drift(self):
  value={'header':{'uuid':'bp','version':[1,2,3]},'modules':[{'version':[1,2,3]}],'dependencies':[{'uuid':'rp','version':[1,2,3]},{'module_name':'@minecraft/server','version':'2.7.0'}]}
  old=json.loads(json.dumps(value));old['header']['version']=[1,2,2];old['modules'][0]['version']=[1,2,2];old['dependencies'][0]['version']=[1,2,2]
  encode=lambda v:(json.dumps(v,ensure_ascii=False,indent=2)+'\n').encode()
  self.fixture('runtime/manifest.json',encode(value),encode(old),{'kind':'owned_manifest','reviewedVersion':[1,2,2],'ownedUuids':['bp','rp']})
  self.assertEqual(previous_bytes(self.r,self.p),encode(old))
  value['dependencies'][1]['version']='2.9.0';self.p.write_bytes(encode(value))
  with self.assertRaises(AssertionError):previous_bytes(self.r,self.p)
 def test_exact_rp_empty_dependencies_layer_keeps_version_and_historical_guards(self):
  name='runtime/RP/manifest.json';encode=lambda value:(json.dumps(value,ensure_ascii=False,indent=2)+'\n').encode()
  old={'header':{'uuid':'rp','version':[1,2,2]},'modules':[{'uuid':'rp-module','version':[1,2,2]}],'capabilities':['pbr']}
  normalized={**old,'dependencies':[]}
  current=json.loads(json.dumps(normalized));current['header']['version']=[1,2,3];current['modules'][0]['version']=[1,2,3]
  self.fixture(name,encode(current),encode(old),{'kind':'owned_manifest','reviewedVersion':[1,2,2],'ownedUuids':['bp','rp']})
  self.ledger=json.loads((self.r/'data/baseline-reconciliation.json').read_text());self.ledger.update(schema=1,testOnly=True)
  original=encode({**old,'capabilities':[]});historical=self.ledger['files'][name]
  historical.update(before=hashlib.sha256(original).hexdigest(),beforeContent=original.decode())
  unchanged=json.loads(json.dumps(historical))
  self.ledger['reviewedAssetDeltaLayers']=[{'release':'1.2.3','files':{name:{
   'before':hashlib.sha256(encode(old)).hexdigest(),'after':hashlib.sha256(encode(normalized)).hexdigest(),
   'reason':'Exact reviewed explicit empty RP dependency field after bound identity normalization',
   'beforeGzipBase64':base64.b64encode(gzip.compress(encode(old),mtime=0)).decode()}}}]
  self.write_functional_ledger();self.assertEqual(previous_bytes(self.r,self.p),original)
  self.assertEqual(self.ledger['files'][name],unchanged)
  for field,value in [('dependencies',[{'uuid':'foreign','version':[1,0,0]}]),('capabilities',['pbr','unreviewed']),('unreviewed',True)]:
   changed={**current,field:value};self.p.write_bytes(encode(changed))
   with self.assertRaisesRegex(AssertionError,'Reviewed asset source mutated'):previous_bytes(self.r,self.p)
  self.p.write_bytes(encode({k:v for k,v in current.items() if k!='dependencies'}))
  with self.assertRaisesRegex(AssertionError,'Reviewed asset source mutated'):previous_bytes(self.r,self.p)
  bad=json.loads(json.dumps(current));bad['modules'][0]['version']=[1,2,4];self.p.write_bytes(encode(bad))
  with self.assertRaises(AssertionError):previous_bytes(self.r,self.p)
  # A later fully bound pure identity bump still resolves this exact body delta.
  current['header']['version']=[1,2,4];current['modules'][0]['version']=[1,2,4];self.p.write_bytes(encode(current))
  for filename,value in [('package.json',{'version':'1.2.4'}),('release.json',{'version':'1.2.4'}),('baseline.json',{'version':[1,2,4]})]:(self.r/filename).write_text(json.dumps(value))
  self.assertEqual(previous_bytes(self.r,self.p),original)
  self.ledger['files'][name]['beforeContent']='changed historical preimage';self.write_functional_ledger()
  with self.assertRaisesRegex(AssertionError,'Baseline preimage corrupt'):previous_bytes(self.r,self.p)
 def test_inconsistent_current_release_or_unknown_projection_is_rejected(self):
  old=b"BUILD_VERSION='1.2.2-baseline.1'";self.fixture('runtime/build.js',old.replace(b'1.2.2',b'1.2.3'),old,{'kind':'build_identity','reviewedVersion':'1.2.2'})
  (self.r/'baseline.json').write_text(json.dumps({'version':[1,2,4]}))
  with self.assertRaises(AssertionError):previous_bytes(self.r,self.p)
 def test_functional_delta_restores_exact_predecessor_then_original_preimage(self):
  self.functional_fixture()
  self.assertEqual(previous_bytes(self.r,self.p),self.original)
  # A file without an older reconciliation row still returns the exact prior
  # reviewed source to its unchanged downstream historical guards.
  self.ledger['files']={};self.write_functional_ledger()
  self.assertEqual(previous_bytes(self.r,self.p),self.predecessor)
 def test_functional_review_rejects_unreviewed_postimage_bytes(self):
  self.functional_fixture()
  for content in [self.current+b'runUnreviewed();\n',self.current.replace(b'SourceFix',b'Unreviewed')]:
   self.p.write_bytes(content)
   with self.assertRaisesRegex(AssertionError,'Reviewed functional source mutated'):previous_bytes(self.r,self.p)
 def test_exact_shaker_review_restores_baseline_and_rejects_extra_changes(self):
  self.functional_fixture(name='runtime/RP/animations/runtime_shaker.animation.json')
  earlier=json.loads(json.dumps(self.ledger))
  latest=b'calibratedPositionOnly();\n'
  name=self.p.relative_to(self.r).as_posix()
  self.ledger['reviewedFunctionalDeltaLayers']=[{'release':'0.6.127','files':{name:{
   'before':hashlib.sha256(self.current).hexdigest(),'after':hashlib.sha256(latest).hexdigest(),
   'reason':'Exact reviewed main-hand shaker position constants',
   'reverseOps':[[0,1,self.current.decode()]]}}}]
  self.p.write_bytes(latest);self.write_functional_ledger()
  self.assertEqual(previous_bytes(self.r,self.p),self.original)
  self.assertEqual(self.ledger['files'],earlier['files'])
  self.assertEqual(self.ledger['reviewedFunctionalDeltas'],earlier['reviewedFunctionalDeltas'])
  self.p.write_bytes(latest+b'unreviewedRotation();\n')
  with self.assertRaisesRegex(AssertionError,'Reviewed functional source mutated'):previous_bytes(self.r,self.p)
  self.p.write_bytes(latest)
  self.ledger['reviewedFunctionalDeltaLayers'][0]['files'][name]['reverseOps'][0][2]='wrong predecessor\n'
  self.write_functional_ledger()
  with self.assertRaisesRegex(AssertionError,'Functional predecessor mismatch'):previous_bytes(self.r,self.p)
 def test_other_rp_animation_paths_are_not_authorized_for_projection(self):
  self.functional_fixture(name='runtime/RP/animations/unrelated.animation.json')
  with self.assertRaises(AssertionError):previous_bytes(self.r,self.p)
 def asset_fixture(self,name):
  self.functional_fixture(name=name)
  row=self.ledger.pop('reviewedFunctionalDeltas')[name];row.pop('reverseOps')
  row['beforeGzipBase64']=base64.b64encode(gzip.compress(self.predecessor,mtime=0)).decode()
  self.ledger['reviewedAssetDeltaLayers']=[{'release':'0.6.129','files':{name:row}}]
  self.write_functional_ledger()
 def test_exact_cocktail_assets_preserve_historical_witness_and_reject_drift(self):
  for name in ['runtime/BP/blocks/cup_white_lady.json','runtime/RP/ui/hud_screen.json',
               'runtime/RP/texts/languages.json']:
   self.asset_fixture(name)
   self.assertEqual(previous_bytes(self.r,self.p),self.original)
   self.p.write_bytes(self.current+b'unreviewed bytes')
   with self.assertRaisesRegex(AssertionError,'Reviewed asset source mutated'):previous_bytes(self.r,self.p)
   self.p.write_bytes(self.current)
   self.ledger['reviewedAssetDeltaLayers'][0]['files'][name]['beforeGzipBase64']=base64.b64encode(gzip.compress(b'wrong predecessor',mtime=0)).decode()
   self.write_functional_ledger()
   with self.assertRaisesRegex(AssertionError,'Asset predecessor mismatch'):previous_bytes(self.r,self.p)
 def test_asset_review_does_not_admit_other_blocks_ui_or_locales(self):
  for name in ['runtime/BP/blocks/barrel.json','runtime/RP/ui/unrelated.json','runtime/RP/texts/fr_FR.lang',
               'runtime/RP/texts/en_US.lang','runtime/RP/texts/zh_CN.lang','runtime/RP/texts/zh_TW.lang',
               'runtime/RP/texts/ja_JP.lang','runtime/RP/texts/ru_RU.lang']:
   self.asset_fixture(name)
   with self.assertRaisesRegex(AssertionError,'Unsupported reviewed asset path'):previous_bytes(self.r,self.p)
 def test_versioned_body_delta_keeps_release_binding_and_future_identity_only_bumps(self):
  name='runtime/BP/scripts/data/cookery-guide-payload.js'
  old=b'const payload={"version": "1.2.2","body":"old"};\n'
  reviewed=old.replace(b'"old"',b'"fixed"');current=reviewed.replace(b'1.2.2',b'1.2.3')
  self.fixture(name,current,old,{'kind':'payload_version','reviewedVersion':'1.2.2'})
  self.ledger=json.loads((self.r/'data/baseline-reconciliation.json').read_text());self.ledger.update(schema=1,testOnly=True)
  self.ledger['reviewedFunctionalDeltaLayers']=[{'release':'1.2.3','files':{name:{'before':hashlib.sha256(old).hexdigest(),'after':hashlib.sha256(reviewed).hexdigest(),'reason':'Reviewed body only after bound version normalization','reverseOps':[[0,1,old.decode()]]}}}]
  self.write_functional_ledger();self.assertEqual(previous_bytes(self.r,self.p),old)
  self.p.write_bytes(current.replace(b'1.2.3',b'1.2.4'))
  with self.assertRaises(AssertionError):previous_bytes(self.r,self.p)
  for filename,value in [('package.json',{'version':'1.2.4'}),('release.json',{'version':'1.2.4'}),('baseline.json',{'version':[1,2,4]})]:(self.r/filename).write_text(json.dumps(value))
  self.assertEqual(previous_bytes(self.r,self.p),old)
  self.p.write_bytes(self.p.read_bytes().replace(b'"fixed"',b'"unreviewed"'))
  with self.assertRaisesRegex(AssertionError,'Reviewed functional source mutated'):previous_bytes(self.r,self.p)
 def test_functional_review_rejects_corrupt_reverse_delta(self):
  self.functional_fixture()
  row=next(iter(self.ledger['reviewedFunctionalDeltas'].values()))
  row['reverseOps'][0][2]='unreviewedPredecessor();\n';self.write_functional_ledger()
  with self.assertRaisesRegex(AssertionError,'Functional predecessor mismatch'):previous_bytes(self.r,self.p)
 def test_functional_review_keeps_immutable_preimage_guard(self):
  self.functional_fixture()
  row=next(iter(self.ledger['files'].values()))
  row['beforeContent']='tamperedHistoricalSource();\n';self.write_functional_ledger()
  with self.assertRaisesRegex(AssertionError,'Baseline preimage corrupt'):previous_bytes(self.r,self.p)
 def test_functional_review_is_explicitly_test_only(self):
  self.functional_fixture()
  self.ledger['testOnly']=False;self.write_functional_ledger()
  with self.assertRaisesRegex(AssertionError,'Unsupported functional review ledger'):previous_bytes(self.r,self.p)
 def test_appended_functional_layer_preserves_earlier_review_and_preimage(self):
  self.functional_fixture()
  old_review=json.loads(json.dumps(self.ledger['reviewedFunctionalDeltas']))
  latest=b'applyLaterSourceFix();\n'
  name=self.p.relative_to(self.r).as_posix()
  self.ledger['reviewedFunctionalDeltaLayers']=[{'release':'1.2.3','files':{name:{
   'before':hashlib.sha256(self.current).hexdigest(),'after':hashlib.sha256(latest).hexdigest(),
   'reason':'Later effect-first lifecycle review','reverseOps':[[0,1,self.current.decode()]]}}}]
  self.p.write_bytes(latest);self.write_functional_ledger()
  self.assertEqual(previous_bytes(self.r,self.p),self.original)
  self.assertEqual(self.ledger['reviewedFunctionalDeltas'],old_review)
  self.p.write_bytes(latest+b'unreviewed();\n')
  with self.assertRaisesRegex(AssertionError,'Reviewed functional source mutated'):previous_bytes(self.r,self.p)
  self.p.write_bytes(latest)
  self.ledger['reviewedFunctionalDeltaLayers'][0]['files'][name]['reverseOps'][0][2]='wrong predecessor\n';self.write_functional_ledger()
  with self.assertRaisesRegex(AssertionError,'Functional predecessor mismatch'):previous_bytes(self.r,self.p)
class HistoryAliasTests(unittest.TestCase):
 def test_alias_rejects_a_different_runtime_tree_before_reading_source(self):
  from unittest.mock import patch
  reference.historical_runtime_source.cache_clear()
  with patch.object(reference.subprocess,'check_output',return_value='unreviewed-tree\n') as git:
   with self.assertRaisesRegex(AssertionError,'alias tree differs'):
    reference.historical_runtime_source('/synthetic-only',reference.T169_BEFORE,reference.T169_PATH)
   self.assertEqual(git.call_count,1)
 def test_alias_cannot_resolve_arbitrary_commit_or_nonruntime_path(self):
  for commit,name in [('HEAD',reference.T169_PATH),(reference.T169_BEFORE,'AGENTS.md')]:
   with self.subTest(commit=commit,name=name),self.assertRaisesRegex(AssertionError,'immutable runtime history'):
    reference.historical_runtime_source('/synthetic-only',commit,name)

class T176ImmutableTests(unittest.TestCase):
 def test_complete_immutable_endpoints_and_mutation_rejection(self):
  root=Path(__file__).resolve().parents[1]
  for name in reference.T176_PATHS:
   before=reference.t176_source(str(root),reference.T176_BEFORE,name)
   after=reference.t176_source(str(root),reference.T176_AFTER,name)
   with self.subTest(name=name):
    self.assertNotEqual(before,after)
    self.assertEqual(reference.t176_preimage(root,name,after),before)
    self.assertEqual(reference.t176_preimage(root,name,before),before)
    for changed in [before+b'runUnreviewed();\n',after+b'runUnreviewed();\n']:
     with self.assertRaisesRegex(AssertionError,'Unreviewed T176 source postimage'):reference.t176_preimage(root,name,changed)
 def test_scope_cannot_read_an_unrelated_path_or_commit(self):
  root=Path(__file__).resolve().parents[1]
  for commit,name in [(reference.T176_AFTER,'runtime/BP/scripts/bedrock/mixology.js'),('HEAD',next(iter(reference.T176_PATHS)))]:
   with self.subTest(commit=commit,name=name),self.assertRaisesRegex(AssertionError,'Outside the T176'):reference.t176_source(str(root),commit,name)

class CurrentExtensionSourceTests(unittest.TestCase):
 def setUp(self):
  import shutil
  from current_extension_source_contract import runtime_sources
  self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.root=Path(self.tmp.name)
  original=Path(__file__).resolve().parents[1]
  for name in runtime_sources()|{'runtime/BP/scripts/main.js','runtime/BP/scripts/data/guide-catalog.js',
   'runtime/BP/scripts/bedrock/writing-boards.js',
   'runtime/BP/scripts/core/bottles.js','runtime/BP/scripts/bedrock/bottles.js',
   'data/baseline-reconciliation.json','data/launch-repair-reference.json',
   'data/efficiency-repair-reference.json','data/pickup-pick-baseline.json',
   'data/pick-block-prefixes.json'}:
   target=self.root/name;target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(original/name,target)
 def test_current_owners_use_actual_source_after_the_validated_handoff(self):
  from current_extension_source_contract import check,runtime_sources,LOCALE_SOURCES
  self.assertEqual(LOCALE_SOURCES,{f'runtime/RP/texts/{locale}.lang' for locale in ('en_US','zh_CN','zh_TW','ja_JP','ru_RU')})
  self.assertEqual(check(self.root,syntax=False,localization=False)['ownershipAndWiring'],'passed')
  original=Path(__file__).resolve().parents[1]
  for name in runtime_sources():
   with self.subTest(name=name):self.assertEqual(previous_bytes(original,original/name),(original/name).read_bytes())
 def test_parallel_transport_or_missing_host_connection_is_rejected(self):
  from current_extension_source_contract import check
  path=self.root/'runtime/BP/scripts/bedrock/extension-host.js';original=path.read_text()
  path.write_text(original.replace("'../core/transport.js'","'../core/parallel-transport.js'"))
  with self.assertRaisesRegex(AssertionError,'owner import differs'):check(self.root,syntax=False,localization=False)
  path.write_text(original);entry=self.root/'runtime/BP/scripts/main.js'
  entry.write_text(entry.read_text().replace('installExtensionHost(registry)',''))
  with self.assertRaisesRegex(AssertionError,'host is disconnected'):check(self.root,syntax=False,localization=False)
 def test_historical_body_guards_cannot_reclaim_current_owners(self):
  baseline=self.root/'data/baseline-reconciliation.json';original=json.loads(baseline.read_text())
  launch=self.root/'data/launch-repair-reference.json';launch_original=json.loads(launch.read_text())
  efficiency=self.root/'data/efficiency-repair-reference.json';efficiency_original=json.loads(efficiency.read_text())
  for name in (
   'runtime/BP/scripts/core/registry.js',
   'runtime/BP/scripts/core/transport.js',
   'runtime/BP/scripts/core/util.js',
   'runtime/BP/scripts/core/quality-tooltip.js',
   'runtime/BP/scripts/bedrock/extension-host.js',
   'runtime/BP/scripts/bedrock/quality-tooltip.js',
   'runtime/BP/scripts/core/cookery-guide-publisher.js',
   'runtime/BP/scripts/bedrock/board-text.js',
   'runtime/BP/scripts/core/board-layout.js',
   'runtime/BP/scripts/data/board-font.js',
   'runtime/BP/scripts/bedrock/mixology.js',
  ):
   with self.subTest(owner=name):
    baseline.write_text(json.dumps(original));launch.write_text(json.dumps(launch_original))
    with mock.patch.object(reference,'__file__',str(self.root/'tools/baseline_reference.py')):
     self.assertEqual(previous_bytes(self.root,self.root/name),(self.root/name).read_bytes())
     for section in ('files','reviewedFunctionalDeltas'):
      ledger=json.loads(json.dumps(original));ledger.setdefault(section,{})[name]={};baseline.write_text(json.dumps(ledger))
      with self.assertRaisesRegex(AssertionError,'historical postimage'):previous_bytes(self.root,self.root/name)
     for section in ('reviewedFunctionalDeltaLayers','reviewedAssetDeltaLayers'):
      ledger=json.loads(json.dumps(original));ledger[section].append({'release':'fixture','files':{name:{}}});baseline.write_text(json.dumps(ledger))
      with self.assertRaisesRegex(AssertionError,'reverse delta'):previous_bytes(self.root,self.root/name)
     baseline.write_text(json.dumps(original))
     for section in ('reviewedChanges','newRuntimeFiles'):
      ledger=json.loads(json.dumps(launch_original));ledger[section][name]={};launch.write_text(json.dumps(ledger))
      with self.assertRaisesRegex(AssertionError,'launch hash aggregate'):previous_bytes(self.root,self.root/name)
     launch.write_text(json.dumps(launch_original))
     for section in ('reviewedChanges','newRuntimeFiles'):
      ledger=json.loads(json.dumps(efficiency_original));ledger[section][name]={};efficiency.write_text(json.dumps(ledger))
      with self.assertRaisesRegex(AssertionError,'efficiency hash aggregate'):previous_bytes(self.root,self.root/name)
     efficiency.write_text(json.dumps(efficiency_original))
 def test_missing_or_empty_actual_quality_feedback_translation_is_rejected(self):
  from current_extension_source_contract import check,COMPLETE_LOCALE_SOURCES,QUALITY_UP_KEY
  for name in COMPLETE_LOCALE_SOURCES:
   path=self.root/name;original=path.read_text()
   row=next(line for line in original.splitlines(keepends=True) if line.startswith(QUALITY_UP_KEY+'='))
   for replacement in ('',QUALITY_UP_KEY+'=\n'):
    path.write_text(original.replace(row,replacement))
    with self.subTest(name=name,replacement=replacement),self.assertRaises(AssertionError):check(self.root,syntax=False,localization=False)
   path.write_text(original)
 def test_partial_locales_keep_fallback_and_validate_optional_quality_feedback(self):
  from current_extension_source_contract import check,PARTIAL_LOCALE_SOURCES,QUALITY_UP_KEY
  for name in PARTIAL_LOCALE_SOURCES:
   path=self.root/name;original=path.read_text()
   fallback=''.join(line for line in original.splitlines(keepends=True) if not line.startswith(QUALITY_UP_KEY+'='))
   path.write_text(fallback)
   self.assertEqual(check(self.root,syntax=False,localization=False)['ownershipAndWiring'],'passed')
   path.write_text(fallback+'\n'+QUALITY_UP_KEY+'=Quality increased.\n')
   self.assertEqual(check(self.root,syntax=False,localization=False)['ownershipAndWiring'],'passed')
   path.write_text(fallback+'\n'+QUALITY_UP_KEY+'=Quality increased: %s\n')
   with self.subTest(name=name),self.assertRaisesRegex(AssertionError,'Quality feedback placeholders differ'):
    check(self.root,syntax=False,localization=False)
   path.write_text(original)
 def test_historical_asset_guards_cannot_reclaim_partial_locales(self):
  from current_extension_source_contract import check,PARTIAL_LOCALE_SOURCES
  path=self.root/'data/baseline-reconciliation.json';original=json.loads(path.read_text())
  for name in PARTIAL_LOCALE_SOURCES:
   ledger=json.loads(json.dumps(original));ledger['reviewedAssetDeltaLayers'].append({'release':'fixture','files':{name:{}}})
   path.write_text(json.dumps(ledger))
   with self.subTest(name=name),self.assertRaisesRegex(AssertionError,'reverse delta'):
    check(self.root,syntax=False,localization=False)

class GuideCurrentSourceTests(unittest.TestCase):
 def test_current_guide_owners_reach_launch_without_a_historical_source_view(self):
  root=Path(__file__).resolve().parents[1]
  for name in ('runtime/BP/scripts/bedrock/standalone-guide.js','runtime/BP/scripts/core/standalone-guide-model.js'):
   with self.subTest(name=name):
    self.assertEqual(previous_bytes(root,root/name),(root/name).read_bytes())

class FoundationCurrentSourceTests(unittest.TestCase):
 def setUp(self):
  import shutil
  from foundation.source_contract import BRIDGE,FURNITURE,SDK
  self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.root=Path(self.tmp.name)
  original=Path(__file__).resolve().parents[1]
  for name in [BRIDGE,FURNITURE,SDK,'runtime/BP/scripts/main.js','data/baseline-reconciliation.json']:
   target=self.root/name;target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(original/name,target)
 def test_current_owner_checks_actual_wiring_instead_of_a_frozen_postimage(self):
  from foundation.source_contract import check
  result=check(self.root,syntax=False)
  self.assertEqual(result['ownershipAndWiring'],'passed')
  self.assertFalse(result['nativeInventoryRecovery'])
 def test_wrong_native_owner_and_missing_entrypoint_connection_are_rejected(self):
  from foundation.source_contract import check,FURNITURE
  path=self.root/FURNITURE;original=path.read_text()
  path.write_text(original.replace("from './native-item-storage.js'","from './parallel-item-storage.js'"))
  with self.assertRaisesRegex(AssertionError,'owner import differs'):check(self.root,syntax=False)
  path.write_text(original);entry=self.root/'runtime/BP/scripts/main.js'
  entry.write_text(entry.read_text().replace('installFoundationBridge(registry,extensionFurniture)',''))
  with self.assertRaises(AssertionError):check(self.root,syntax=False)
 def test_sdk_consumer_must_equal_the_current_owner_and_keep_its_connection(self):
  from foundation.source_contract import check,CONSUMER,SDK
  consumer=self.root/'consumer';path=consumer/CONSUMER;path.parent.mkdir(parents=True);path.write_bytes((self.root/SDK).read_bytes())
  owner=consumer/'runtime/BP/scripts/foundation.js';owner.write_text("import {createFoundationClient} from './sdk/tavern-foundation-client.js';\nbridge=createFoundationClient();\n")
  (consumer/'data').mkdir();(consumer/'data/baseline-reconciliation.json').write_text('{"files":{}}')
  self.assertEqual(check(self.root,consumer,syntax=False)['consumer'],CONSUMER)
  path.write_bytes(path.read_bytes()+b'// stale independent SDK copy\n')
  with self.assertRaisesRegex(AssertionError,'consumer differs'):check(self.root,consumer,syntax=False)
class T169ImmutableTests(unittest.TestCase):
 def setUp(self):
  self.root=Path(__file__).resolve().parents[1]
  ledger=json.loads((self.root/'data/baseline-reconciliation.json').read_text())
  layer=next(row for row in ledger['reviewedAssetDeltaLayers'] if row['release']=='0.6.169')
  self.assertEqual(set(layer['files']),{reference.T169_PATH})
  self.row=layer['files'][reference.T169_PATH]
  self.before=reference.t169_source(str(self.root),reference.T169_BEFORE)
  self.after=reference.t169_source(str(self.root),reference.T169_AFTER)
 def test_frozen_ui_reverses_to_t168_and_keeps_all_earlier_guards(self):
  self.assertEqual(reference.reverse_t169_delta(self.root,reference.T169_PATH,self.after,self.row),self.before)
  historical=reference.rows(str(self.root))[reference.T169_PATH]
  self.assertEqual(hashlib.sha256(previous_bytes(self.root,self.root/reference.T169_PATH)).hexdigest(),historical['before'] or historical['after'])
 def test_extra_ui_field_cannot_be_admitted_by_synchronizing_ledger_hash(self):
  changed=json.loads(self.after);changed['kt_mixology_packet']['unreviewed']=True
  changed=(json.dumps(changed,separators=(',',':'))+'\n').encode()
  row={**self.row,'after':hashlib.sha256(changed).hexdigest()}
  with self.assertRaisesRegex(AssertionError,'immutable postimage'):reference.reverse_t169_delta(self.root,reference.T169_PATH,changed,row)
 def test_forged_predecessor_and_other_ui_paths_cannot_expand_review(self):
  for kind in ['before','gzip','path']:
   row={**self.row};name=reference.T169_PATH
   if kind=='before':row['before']=hashlib.sha256(b'forged UI').hexdigest()
   elif kind=='gzip':row['beforeGzipBase64']=base64.b64encode(gzip.compress(b'forged UI',mtime=0)).decode()
   else:name='runtime/RP/ui/hud_screen.json'
   with self.subTest(kind=kind),self.assertRaises(AssertionError):reference.reverse_t169_delta(self.root,name,self.after,row)
if __name__=='__main__':unittest.main()
