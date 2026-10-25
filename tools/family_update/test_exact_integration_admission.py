"""Owned synthetic Git histories exercise the real CLI producer/consumer.

No private payload is a fixture. Only the immutable policy/catalog input hashes
are replaced with hashes of our generated test data in the consumer child.
No validation function, Git read, source inventory or producer result is mocked.
"""
import copy,hashlib,json,os,subprocess,sys,tempfile,unittest
from pathlib import Path

TOOLS=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(TOOLS))
from family_update.integration_runtime_validation import FISH,AMW,AWW,CHANGED

def encoded(value):return (json.dumps(value,sort_keys=True,indent=2)+'\n').encode()
def sha(raw):return hashlib.sha256(raw).hexdigest()
def tree(rows):return {'sha256':sha(json.dumps(rows,sort_keys=True,separators=(',',':')).encode()),'files':len(rows)}

CONSUMER=r'''
import json,sys
from pathlib import Path
from unittest.mock import patch
from family_update import integration_runtime_validation as integration
from family_update import current_author_validation as validation
import family_bundle,host_extensions
request=json.loads(Path(sys.argv[1]).read_text());root=Path(request['root'])
config=json.loads((root/'baseline.json').read_bytes())
context={'source_root':str(root),'source_commit':host_extensions.subprocess.check_output(['git','rev-parse','HEAD'],cwd=root,text=True).strip(),'sources':request['sources']}
with patch.dict(integration.PROFILES,{(1,0,64):request['policy']},clear=True),patch.object(validation,'CATALOG',{'current_author_p58':request['catalog']}),patch.object(host_extensions,'REVIEWED_SALT_REMOVAL',request['spec']['removed_files']):
 component,anchor=family_bundle.retained_component_config(root,config,{k:Path(v) for k,v in request['sources'].items()})
 result=host_extensions.validate_recipe_removals(request['spec'],root/'runtime/BP',Path(request['host']),{'admission':'current-author-p58'},retained_owner=context if anchor else None)
 assert result==request['spec']['removed_files']
 print(json.dumps({'owner':config['version'],'component':component['version'],'historical_anchor':anchor,'salt_removal':result,'native':False,'client':False}))
'''

class ExactIntegrationCLI(unittest.TestCase):
 def setUp(self):
  temporary=tempfile.TemporaryDirectory();self.addCleanup(temporary.cleanup)
  self.tmp=Path(temporary.name).resolve();self.root=self.tmp/'owned';self.root.mkdir()
  self.env={**os.environ,'PYTHON':sys.executable,'PYTHONPATH':str(TOOLS),'PYTHONDONTWRITEBYTECODE':'1',
            'GIT_CONFIG_COUNT':'1','GIT_CONFIG_KEY_0':'core.autocrlf','GIT_CONFIG_VALUE_0':'false'}
  for key in ['GIT_DIR','GIT_WORK_TREE','GIT_INDEX_FILE']:self.env.pop(key,None)
  self.git('init','-q');self.git('config','user.name','Owned admission fixture');self.git('config','user.email','fixture@example.invalid')
  self.sources={}
  for name,uid,version in [('tavern','T-RP',[0,6,180]),('world-liquor','W-RP',[0,1,158]),('grilling','G-RP',[2,8,155])]:
   p=self.tmp/name;p.mkdir();(p/'baseline.json').write_bytes(encoded({'packs':{'RP':{'uuid':uid}},'version':version}));self.sources[name]=str(p)
  self.manifests={}
  for side,other in [('BP','RP'),('RP','BP')]:
   m={'header':{'uuid':'owned-'+side,'version':[1,0,57],'name':'Owned synthetic fixture'},'modules':[{'uuid':'module-'+side,'type':'data' if side=='BP' else 'resources','version':[1,0,57]}],
      'dependencies':[{'uuid':'owned-'+other,'version':[1,0,57]}]}
   if side=='BP':m['dependencies'] += [{'uuid':FISH,'version':[1,2,10058]}]
   else:m['dependencies'] += [{'uuid':'T-RP','version':[0,6,176]},{'uuid':'W-RP','version':[0,1,153]},{'uuid':'G-RP','version':[2,8,155]},{'uuid':AMW,'version':[2,6,10058]}]
   self.manifests[side]=m
  for n in range(135):self.write(f'runtime/BP/kept/{n}.json',encoded({'owned':n}))
  for n in range(73):self.write(f'runtime/RP/kept/{n}.json',encoded({'owned':n}))
  self.write('runtime/BP/host-extensions/fixture.json',b'{"owner":57}\n')
  self.write('runtime/RP/ui/hud_screen.json',b'{"namespace":"owned_fixture","root":{"type":"panel"}}\n')
  self.write('runtime/RP/ui/_global_variables.json',b'{"$owned":"old"}\n')
  self.alternate={'description':{'identifier':'senluo:fishing_grilled_fish_plank_cf_salt'},'tags':['crafting_table'],
    'ingredients':[{'item':'kaleidoscope_fishing:grilled_fish'},{'item':'kaleidoscope_fishing:grilled_fish'},{'item':'kaleidoscope_chinesefood:salt'},{'tag':'minecraft:wooden_slabs'}],
    'result':{'item':'kaleidoscope_fishing:grilled_fish_plank','count':1},'unlock':[{'item':'kaleidoscope_fishing:grilled_fish'},{'item':'kaleidoscope_chinesefood:salt'}]}
  self.write('runtime/BP/recipes/alternatives/fishing_grilled_fish_plank_cf_salt.json',encoded({'minecraft:recipe_shapeless':self.alternate}))
  self.write('tools/current_release.py',b'import pathlib\nprint(pathlib.Path(__file__).resolve().parents[1].joinpath("proof.json").read_text())\n')
  self.save_baseline([1,0,57]);self.p57files=self.files();self.p57=self.commit('owned P57')
  self.advance([1,0,58]);self.write('runtime/BP/host-extensions/fixture.json',b'{"owner":58}\n')
  self.write('runtime/BP/scripts/host_api/fishing-water-particles.js',b'// owned fixture helper\n')
  self.write('runtime/BP/client-repairs/repair-plan.json',b'{"owned_fixture":true}\n')
  for n in range(156):self.write(f'runtime/RP/textures/integration/fishing-normal/owned_{n}_normal.png',b'owned opaque hash fixture '+str(n).encode())
  self.save_baseline([1,0,58]);self.p58files=self.files();self.p58config=copy.deepcopy(self.config)
  self.component={'previous_commit':self.p57,'previous_files':self.p57files,'files':self.p58files,
    'exact_changed_paths':self.changes(self.p57files,self.p58files),'added_paths':self.added(self.p57files,self.p58files),'retired_paths':[],'core_only':True,'conserved_files':211}
  self.catalog={k:copy.deepcopy(self.component[k]) for k in ['previous_commit','exact_changed_paths','added_paths','retired_paths']};self.catalog['host_specs']={'fixture.json':{}}
  self.write('proof.json',encoded(self.component));self.p58=self.commit('owned P58');self.p58tree=self.git('rev-parse','HEAD^{tree}')
  self.advance([1,0,62]);self.peers={'T-RP':[0,6,180],'W-RP':[0,1,158]}
  for d in self.manifests['RP']['dependencies']:
   if d['uuid'] in self.peers:d['version']=self.peers[d['uuid']]
  self.anchor={'schema':1,'kind':'dependency-only','source_commit':self.p58,'source_tree':self.p58tree,'source_version':[1,0,58],'dependency_versions':self.peers}
  self.save_baseline([1,0,62],self.anchor);self.p62files=self.files();self.p62config=copy.deepcopy(self.config)
  self.historical={'schema':1,'kind':'dependency_only_runtime','source_commit':self.p58,'previous_commit':self.p58,'source_tree':self.p58tree,'source_version':[1,0,58],'version':[1,0,62],
    'source_trees':self.config['source_trees'],'retained_source_trees':self.p58config['source_trees'],'files':self.p62files,'previous_files':self.p58files,
    'exact_changed_paths':['runtime/BP/manifest.json','runtime/RP/manifest.json'],'added_paths':[],'retired_paths':[],'conserved_files':370,'core_only':True,'dependency_versions':self.peers,'retained_component_conservation':self.component}
  self.write('proof.json',encoded(self.historical));self.p62=self.commit('owned P62');self.p62tree=self.git('rev-parse','HEAD^{tree}')
  self.advance([1,0,64])
  self.manifests['BP']['dependencies'][-1]['version']=[1,3,0]
  next(d for d in self.manifests['RP']['dependencies'] if d['uuid']==AMW).update(uuid=AWW,version=[1,3,0])
  self.write('runtime/RP/ui/hud_screen.json',b'{"namespace":"owned_fixture","root":{"type":"panel","controls":[{"owned_aww":{"type":"panel"}}]}}\n')
  self.write('runtime/RP/ui/_global_variables.json',b'{"$owned":"new-aww"}\n')
  self.save_baseline([1,0,64],self.anchor);self.after=self.files()
  self.contract={'schema':1,'kind':'aww-exact-four-file','base_commit':self.p62,'version':[1,0,64],'exact_changed_paths':sorted(CHANGED),
   'changed_files':{name:{'before':self.lookup(self.p62files,name),'after':self.lookup(self.after,name)} for name in CHANGED},'added_paths':[],'retired_paths':[],'conserved_files':368,'source_trees':self.config['source_trees'],
   **{k:False for k in ['client','native','performance','production_ready','live','publication_request']}}
  self.write('data/aww-p64-runtime-contract.json',encoded(self.contract))
  self.config['integration_runtime']={'kind':'aww-exact-four-file','base_commit':self.p62,'base_tree':self.p62tree,'contract':'data/aww-p64-runtime-contract.json','contract_sha256':sha(encoded(self.contract))}
  self.write('baseline.json',encoded(self.config))
  self.proof={'kind':'aww-exact-four-file','version':[1,0,64],'source_version':[1,0,58],'previous_commit':self.p62,'previous_files':self.p62files,'files':self.after,'source_trees':self.config['source_trees'],'exact_changed_paths':sorted(CHANGED),'conserved_files':368,'historical_p62_conservation':self.historical,'retained_component_conservation':self.component,
    **{k:False for k in ['client','native','performance','production_ready','live','publication_request']}}
  self.write('proof.json',encoded(self.proof));self.salt=self.salt_input();self.write('data/fishing-1.3-salt-inputs.json',encoded(self.salt));self.good=self.commit('owned P64')
  host=self.tmp/'host';salt=host/'recipes/vanilla_cooking/salt_smelting.json';salt.parent.mkdir(parents=True);salt.write_bytes(b'owned salt recipe fixture')
  self.policy={'kind':'aww-exact-four-file','contract':'data/aww-p64-runtime-contract.json','contract_sha256':sha(encoded(self.contract)),'fishing_inputs':'data/fishing-1.3-salt-inputs.json','fishing_sha256':sha(encoded(self.salt))}
  self.request={'root':str(self.root),'sources':self.sources,'host':str(host),'policy':self.policy,'catalog':self.catalog,
    'spec':{'kind':'chinesefood-reviewed-repairs','archive_sha256':'dea708dd6443ea30d23e5791860a50181e8eeb560dcd7ec5a8e80fe22743e659','removed_files':{'recipes/vanilla_cooking/salt_smelting.json':sha(salt.read_bytes())}}}
 def git(self,*args):return subprocess.check_output(['git',*args],cwd=self.root,env=self.env,text=True,stderr=subprocess.PIPE).strip()
 def write(self,name,raw):
  p=self.root/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(raw)
 def files(self):return {s:{p.relative_to(self.root/'runtime'/s).as_posix():sha(p.read_bytes()) for p in sorted((self.root/'runtime'/s).rglob('*')) if p.is_file()} for s in ['BP','RP']}
 def changes(self,a,b):return sorted('runtime/'+s+'/'+n for s in a for n in a[s].keys()&b[s].keys() if a[s][n]!=b[s][n])
 def added(self,a,b):return sorted('runtime/'+s+'/'+n for s in a for n in b[s].keys()-a[s].keys())
 def lookup(self,files,name):s,p=name.removeprefix('runtime/').split('/',1);return files[s][p]
 def advance(self,version):
  for m in self.manifests.values():
   m['header']['version']=version
   for module in m['modules']:module['version']=version
   for dep in m['dependencies']:
    if dep['uuid'].startswith('owned-'):dep['version']=version
 def save_baseline(self,version,anchor=None):
  for s,m in self.manifests.items():self.write('runtime/'+s+'/manifest.json',encoded(m))
  self.config={'repository':'local/senluo-amw-cuisine','version':version,'runtime':{'BP':'runtime/BP','RP':'runtime/RP'},'packs':{s:{'uuid':m['header']['uuid'],'dependencies':m['dependencies']} for s,m in self.manifests.items()},'source_trees':{s:tree(rows) for s,rows in self.files().items()}}
  if anchor:self.config['retained_runtime']=copy.deepcopy(anchor)
  self.write('baseline.json',encoded(self.config))
 def commit(self,message):self.git('add','.');self.git('commit','-qm',message);return self.git('rev-parse','HEAD')
 def salt_input(self):
  original=copy.deepcopy(self.alternate);original['description']['identifier']='kaleidoscope_fishing:grilled_fish_plank'
  for x in original['ingredients']+original['unlock']:
   if x.get('item')=='kaleidoscope_chinesefood:salt':x['item']='kaleidoscope_fishing:sea_salt'
  values=[('kaleidoscope_fishing:salt_bucket','minecraft:recipe_furnace',{'description':{'identifier':'kaleidoscope_fishing:salt_bucket'},'tags':['furnace','smoker','campfire'],'input':'minecraft:water_bucket','output':'kaleidoscope_fishing:salt_bucket'}),
   ('kaleidoscope_fishing:salt_from_bucket','minecraft:recipe_shaped',{'description':{'identifier':'kaleidoscope_fishing:salt_from_bucket'},'pattern':['S'],'key':{'S':{'item':'kaleidoscope_fishing:salt_bucket'}},'result':[{'item':'kaleidoscope_fishing:sea_salt','count':3},{'item':'minecraft:bucket','count':1}]}),
   ('kaleidoscope_fishing:grilled_fish_plank','minecraft:recipe_shapeless',original)]
  return {'schema':1,'kind':'captured-local-fishing-salt-inputs','manifest':{'header':{'uuid':FISH,'version':[1,3,0]}},'manifest_sha256':sha(b'owned manifest fixture'),'recipes':{name:{'kind':kind,'file':'recipes/'+name.split(':')[1]+'.json','sha256':sha(encoded(value)),'definition':value} for name,kind,value in values},**{k:False for k in ['original_author_archive_verified','latest_author_release_verified','native','client']}}
 def consume(self):
  request=self.tmp/'request.json';request.write_bytes(encoded(self.request))
  return subprocess.run([sys.executable,'-c',CONSUMER,str(request)],env=self.env,capture_output=True,text=True)
 def restore(self):
  assert self.root.resolve().is_relative_to(self.tmp)
  self.git('reset','--hard',self.good)
  for name in ['runtime/BP/fifth.json','dirty-source.txt']:
   p=self.root/name
   if p.exists():p.unlink()
 def test_real_producer_consumer_p64_and_legacy_p58_p62_positive(self):
  for commit,version in [(self.good,[1,0,64]),(self.p62,[1,0,62]),(self.p58,[1,0,58])]:
   self.git('reset','--hard',commit);result=self.consume()
   self.assertEqual(result.returncode,0,result.stderr);self.assertEqual(json.loads(result.stdout)['owner'],version)
 def test_p64_cannot_impersonate_old_kind_or_change_anchor_tree(self):
  for mutation in ['old-kind','anchor','tree','unknown-version']:
   self.restore();config=copy.deepcopy(self.config);proof=copy.deepcopy(self.proof)
   if mutation=='old-kind':proof['kind']='dependency_only_runtime'
   elif mutation=='anchor':config['integration_runtime']['base_commit']=self.p58
   elif mutation=='tree':config['integration_runtime']['base_tree']='0'*40
   else:config['version']=[1,0,65]
   self.write('baseline.json',encoded(config));self.write('proof.json',encoded(proof));self.commit(mutation)
   result=self.consume();self.assertNotEqual(result.returncode,0,mutation)
 def test_fifth_change_wrong_ui_added_removed_and_rehashed_helper_reject(self):
  for mutation in ['fifth','ui','added','removed','helper']:
   self.restore();config=copy.deepcopy(self.config);proof=copy.deepcopy(self.proof)
   path={'fifth':'runtime/BP/kept/0.json','ui':'runtime/RP/ui/hud_screen.json','added':'runtime/BP/fifth.json','removed':'runtime/BP/kept/0.json','helper':'runtime/BP/scripts/host_api/fishing-water-particles.js'}[mutation]
   if mutation=='removed':(self.root/path).unlink()
   else:self.write(path,b'owned unreviewed mutation\n')
   files=self.files();proof['files']=files;proof['source_trees']=config['source_trees']={s:tree(v) for s,v in files.items()}
   self.write('proof.json',encoded(proof));self.write('baseline.json',encoded(config));self.commit(mutation)
   result=self.consume();self.assertNotEqual(result.returncode,0,mutation)
 def test_wrong_fishing_version_or_source_and_dirty_source_reject(self):
  for mutation in ['fishing-version','fishing-source','dirty']:
   self.restore()
   if mutation=='fishing-version':
    manifest=copy.deepcopy(self.manifests['BP']);manifest['dependencies'][-1]['version']=[1,2,10058];self.write('runtime/BP/manifest.json',encoded(manifest))
   elif mutation=='fishing-source':
    salt=copy.deepcopy(self.salt);salt['manifest_sha256']='0'*64;self.write('data/fishing-1.3-salt-inputs.json',encoded(salt))
   else:self.write('dirty-source.txt',b'uncommitted owned fixture')
   if mutation!='dirty':self.commit(mutation)
   result=self.consume();self.assertNotEqual(result.returncode,0,mutation)

if __name__=='__main__':unittest.main(verbosity=2)
