"""reviewed integration reuses reviewed integration authors without reopening retired AMW gameplay."""
import copy
import hashlib
import json
import tempfile
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from family_update import current_author_validation as m, stable_author_validation as dispatch


class P58Admission(unittest.TestCase):
    def test_fixed58_settings_and_all_stable_dispatches(self):
        config={'extension_stable_profile':'current-author-p58','extension_stable_validation':'fixture'}
        with patch.object(m.c,'CONFIG',config):
            self.assertTrue(m.selected())
            self.assertEqual(m.settings(),([1,0,58],'senluo-stable-author-20261019-p58','current_author_p58'))
        for name,args in [('verify_static',({},{})),('evidence_paths',(False,)),('bind_native',({},{})),('verify_installation',({},))]:
            with self.subTest(name=name),patch.object(m.c,'CONFIG',config),patch.object(m,name,return_value='exact58') as call:
                self.assertEqual(getattr(dispatch,name)(*args),'exact58');call.assert_called_once_with(*args)
        with patch.object(m.c,'CONFIG',{'extension_stable_profile':'current-author-p59'}):
            self.assertFalse(m.selected())
            with self.assertRaises(AssertionError):m.settings()

    def test_retained_profile_reaches_existing_stable_dispatchers(self):
        config={'extension_stable_profile':'current-author-retained','extension_stable_validation':'fixture'}
        for name,args in [('verify_static',({},{})),('evidence_paths',(False,)),('bind_native',({},{})),('verify_installation',({},))]:
            with self.subTest(name=name),patch.object(m.c,'CONFIG',config),patch.object(m,name,return_value='retained') as call:
                self.assertEqual(getattr(dispatch,name)(*args),'retained');call.assert_called_once_with(*args)

    def test_only58_source_records_use_new_owner_historical_names_stay_exact(self):
        self.assertEqual(m.REPOSITORY,'casama233/senluo-family-integration-private')
        for version in [55,56,57,58]:
            with self.subTest(version=version),patch.object(m.c,'CONFIG',{'extension_stable_profile':'current-author-p'+str(version)}):
                self.assertEqual(m.source_repository(),m.current_name(m.REPOSITORY) if version==58 else m.REPOSITORY)

    def test_actual_renderer_retains10658_and_rejects_relabelled59_owner(self):
        import doll_renderer_extension as renderer
        from stable_host_profiles import PROFILES
        profile=PROFILES['chinesefood-doll-renderer-p58']
        manifests=[{'header':{'uuid':uid,'name':'author','version':profile['author_version']},'modules':[{'version':profile['author_version']}],
                    'dependencies':[{'uuid':other,'version':profile['author_version']}]}for uid,other in [(profile['behavior_uuid'],profile['host_uuid']),(profile['host_uuid'],profile['behavior_uuid'])]]
        result=renderer.patch_manifests(*manifests,[1,0,10658],[1,0,58],profile)
        self.assertTrue(all(row['header']['version']==[1,0,10658]for row in result))
        with self.assertRaisesRegex(ValueError,'exact owner release'):renderer.patch_manifests(*manifests,[1,0,10659],[1,0,59],profile)

    def fixture(self):
        before={'BP':{'manifest.json':'before','host-extensions/reviewed.json':'before-spec','scripts/kept.js':'same'},'RP':{'manifest.json':'before-rp','entity/inscription.json':'same'}}
        after=copy.deepcopy(before);after['BP'].update({'manifest.json':'after','host-extensions/reviewed.json':'after-spec',
            'scripts/host_api/fishing-water-particles.js':'helper','client-repairs/repair-plan.json':'plan'})
        after['RP']['manifest.json']='after-rp'
        for n in range(156):after['RP'][f'textures/integration/fishing-normal/kfv_item_{n:03}_normal.png']='normal'
        changed=['runtime/BP/host-extensions/reviewed.json','runtime/BP/manifest.json','runtime/RP/manifest.json']
        added=sorted(['runtime/BP/scripts/host_api/fishing-water-particles.js','runtime/BP/client-repairs/repair-plan.json',
            *[f'runtime/RP/textures/integration/fishing-normal/kfv_item_{n:03}_normal.png' for n in range(156)]])
        owned={'previous_files':before,'files':after,'exact_changed_paths':changed,'added_paths':added,'retired_paths':[]}
        catalog={key:copy.deepcopy(owned[key]) for key in ['exact_changed_paths','added_paths','retired_paths']};catalog['host_specs']={'reviewed.json':{}}
        return owned,catalog

    def validate(self,owned,catalog):
        with patch.object(m.c,'CONFIG',{'extension_stable_profile':'current-author-p58'}):m.validate_owned_conservation(owned,catalog)

    def test_only_identity_declarations_helper_plan_and156_normals_can_change(self):
        owned,catalog=self.fixture();self.validate(owned,catalog)
        for case in ['runtime','fauna','retire','normal-count','claim']:
            changed=copy.deepcopy(owned);policy=copy.deepcopy(catalog)
            if case=='runtime':
                changed['files']['BP']['scripts/kept.js']='changed';changed['exact_changed_paths'].append('runtime/BP/scripts/kept.js');changed['exact_changed_paths'].sort();policy['exact_changed_paths']=changed['exact_changed_paths']
            elif case=='fauna':
                changed['files']['BP']['scripts/fauna.js']='restored';changed['added_paths'].append('runtime/BP/scripts/fauna.js');changed['added_paths'].sort();policy['added_paths']=changed['added_paths']
            elif case=='retire':
                del changed['files']['RP']['entity/inscription.json'];changed['retired_paths']=['runtime/RP/entity/inscription.json'];policy['retired_paths']=changed['retired_paths']
            elif case=='normal-count':
                key='textures/integration/fishing-normal/kfv_item_000_normal.png';del changed['files']['RP'][key];changed['added_paths'].remove('runtime/RP/'+key);policy['added_paths']=changed['added_paths']
            else:changed['added_paths']=[]
            with self.subTest(case=case),self.assertRaises(AssertionError):self.validate(changed,policy)


class RetainedPayloadAdmission(unittest.TestCase):
    """Fresh owning pair cannot masquerade as republished component58."""
    def setUp(self):
        temporary=tempfile.TemporaryDirectory();self.addCleanup(temporary.cleanup)
        self.root=Path(temporary.name);self.commit='a'*40;self.previous='c'*40;self.git_tree='b'*40
        self.peers={'T-RP':[0,6,177],'W-RP':[0,1,154]}
        for key,uid,version in [('tavern','T-RP',[0,6,177]),('world-liquor','W-RP',[0,1,154]),('grilling','G-RP',[2,8,155])]:
            target=self.root/key;target.mkdir();(target/'baseline.json').write_text(json.dumps({'packs':{'RP':{'uuid':uid}},'version':version}))
        self.raw={};self.manifests={}
        component,self.catalog=P58Admission().fixture();self.catalog['previous_commit']=self.previous
        # Historical fixture has161 payloads after reviewed integration additions; pad conserved
        # opaque hashes to the real370 profile size without private contents.
        for n in range(209):
            for files in [component['previous_files'],component['files']]:files['BP'][f'scripts/kept-{n:03}.js']='unchanged-'+str(n)
        for files in [component['previous_files'],component['files']]:
            for side in ['BP','RP']:
                for name,value in files[side].items():files[side][name]=m.digest(value.encode())
        for side,other in [('BP','RP'),('RP','BP')]:
            old={'header':{'uuid':'private-'+side,'version':[1,0,58],'name':'retained58','min_engine_version':[1,26,50]},
                 'modules':[{'uuid':'module-'+side,'type':'script' if side=='BP' else 'resources','version':[1,0,58]}],
                 'dependencies':[{'uuid':'private-'+other,'version':[1,0,58]}]}
            if side=='BP':old['dependencies'] += [{'uuid':'G-RP','version':[2,8,155]}]+ [{'uuid':uid,'version':[0,0,1]}for uid in self.peers]+[{'uuid':'5e121bf2-1d2d-4da4-be15-cffc5f216d94','version':[1,2,10058]},{'module_name':'@minecraft/server','version':'2.7.0'}]
            relative='runtime/'+side+'/manifest.json';self.raw[self.commit+':'+relative]=json.dumps(old).encode()+b'\n'
            component['files'][side]['manifest.json']=m.digest(self.raw[self.commit+':'+relative])
            current=copy.deepcopy(old);current['header']['version']=[1,0,59]
            for row in current['modules']:row['version']=[1,0,59]
            for row in current['dependencies']:
                if row.get('uuid','').startswith('private-'):row['version']=[1,0,59]
                elif row.get('uuid') in self.peers:row['version']=self.peers[row['uuid']]
            self.manifests[side]=current
            (self.root/relative).parent.mkdir(parents=True,exist_ok=True)
        component['previous_commit']=self.previous
        self.old={'repository':m.LOGICAL,'version':[1,0,58],'runtime':{'BP':'runtime/BP','RP':'runtime/RP'},
                  'packs':{side:{'uuid':'private-'+side}for side in ['BP','RP']},'source_trees':{side:m.tree(files)for side,files in component['files'].items()}}
        self.pre_old={'source_trees':{side:m.tree(files)for side,files in component['previous_files'].items()}}
        self.baseline={**copy.deepcopy(self.old),'version':[1,0,59],'retained_runtime':{'schema':1,'kind':'dependency-only','source_commit':self.commit,'source_tree':self.git_tree,'source_version':[1,0,58],'dependency_versions':copy.deepcopy(self.peers)}}
        self.owned={'schema':1,'kind':'dependency_only_runtime','source_commit':self.commit,'previous_commit':self.commit,'source_tree':self.git_tree,'source_version':[1,0,58],'version':[1,0,59],
                    'retained_source_trees':self.old['source_trees'],'previous_files':component['files'],'files':copy.deepcopy(component['files']),
                    'exact_changed_paths':['runtime/BP/manifest.json','runtime/RP/manifest.json'],'added_paths':[],'retired_paths':[],'conserved_files':370,'core_only':True,
                    'dependency_versions':copy.deepcopy(self.peers),'retained_component_conservation':component}
        self.refresh()
        for target in [patch.object(m.c,'EXTENSION',self.root),patch.object(m.c,'SOURCES',{key:self.root/key for key in ['tavern','grilling','world-liquor']}),
                       patch.object(m,'CATALOG',{'current_author_p58':self.catalog}),patch.object(m.c,'git',side_effect=self.git),
                       patch.object(m.subprocess,'check_output',side_effect=lambda args,cwd:self.raw[args[-1]])]:
            target.start();self.addCleanup(target.stop)

    def refresh(self):
        for side,current in self.manifests.items():
            relative='runtime/'+side+'/manifest.json';raw=json.dumps(current).encode()+b'\n'
            (self.root/relative).write_bytes(raw);self.raw['HEAD:'+relative]=raw
            self.owned['files'][side]['manifest.json']=m.digest(raw)
            self.baseline['packs'][side]['dependencies']=current['dependencies']
        self.baseline['source_trees']={side:m.tree(files)for side,files in self.owned['files'].items()}
        self.owned['source_trees']=self.baseline['source_trees']

    def git(self,root,*args):
        if args==('rev-parse',self.commit+'^{tree}'):return self.git_tree
        if args[:2]==('merge-base','--is-ancestor'):return ''
        if args==('show',self.commit+':baseline.json'):return json.dumps(self.old)
        if args==('show',self.previous+':baseline.json'):return json.dumps(self.pre_old)
        raise AssertionError('Unexpected synthetic Git metadata read '+repr(args))

    def validate(self):
        return m.validate_retained_runtime(self.owned,self.baseline,{'actual_current_source_commit':'d'*40})

    def test_dependency_only_owner59_keeps_component58_and370_exact_payloads(self):
        self.assertIs(self.validate(),self.owned)
        with patch.object(m.c,'CONFIG',{}),patch.object(m.c,'EXTENSION',None),patch.object(m.c,'SOURCES',{}):
            self.assertIs(m.validate_retained_runtime(self.owned,self.baseline,{'actual_current_source_commit':'d'*40},source_root=self.root,sources={key:self.root/key for key in ['tavern','grilling','world-liquor']}),self.owned)
        with patch.object(m.c,'CONFIG',{'extension_stable_profile':'current-author-retained'}):
            self.assertTrue(m.selected());self.assertEqual(m.settings()[0],[1,0,58])

    def test_rehashed_helper_or_inventory_drift_still_fails(self):
        for mutation in ['helper','normal','add','remove']:
            before=copy.deepcopy(self.owned);baseline=copy.deepcopy(self.baseline)
            files=self.owned['files']['RP']
            if mutation=='helper':self.owned['files']['BP']['scripts/kept-000.js']='0'*64
            elif mutation=='normal':files['textures/integration/fishing-normal/kfv_item_000_normal.png']='0'*64
            elif mutation=='add':files['textures/new.png']='0'*64
            else:del files['entity/inscription.json']
            self.refresh()
            with self.subTest(mutation=mutation),self.assertRaises(AssertionError):self.validate()
            self.owned=before;self.baseline=baseline

    def test_complete_manifest_api_uuid_and_unreviewed_dependency_edits_fail(self):
        for mutation in ['uuid','api','name','order','added','owner58']:
            old=copy.deepcopy(self.manifests);current=self.manifests['BP']
            if mutation=='uuid':current['modules'][0]['uuid']='foreign'
            elif mutation=='api':current['dependencies'][-1]['version']='99.0.0'
            elif mutation=='name':current['header']['name']='republished'
            elif mutation=='order':current['dependencies'].reverse()
            elif mutation=='added':current['dependencies'].append({'uuid':'foreign','version':[1,0,0]})
            else:current['header']['version']=[1,0,58]
            self.refresh()
            with self.subTest(mutation=mutation),self.assertRaises(AssertionError):self.validate()
            self.manifests=old;self.refresh()

    def test_peer_delta_is_derived_from_all_selected_sources_without_version_allowlist(self):
        path=self.root/'grilling/baseline.json';peer=json.loads(path.read_text());peer['version']=[2,8,156];path.write_text(json.dumps(peer))
        with self.assertRaisesRegex(AssertionError,'Retained peer versions'):self.validate()
        self.baseline['retained_runtime']['dependency_versions']['G-RP']=[2,8,156]
        self.owned['dependency_versions']['G-RP']=[2,8,156]
        for row in self.manifests['BP']['dependencies']:
            if row.get('uuid')=='G-RP':row['version']=[2,8,156]
        self.refresh();self.validate()
        self.owned['dependency_versions']['foreign']=[1,0,1]
        self.baseline['retained_runtime']['dependency_versions']['foreign']=[1,0,1]
        with self.assertRaisesRegex(AssertionError,'Retained peer versions'):self.validate()

    def test_wrong_anchor_peer_component_and_owner_claims_fail(self):
        for mutation in ['tree','peer','component','owner','count','historical-oracle']:
            before=copy.deepcopy(self.owned);baseline=copy.deepcopy(self.baseline)
            if mutation=='tree':self.baseline['retained_runtime']['source_tree']='0'*40
            elif mutation=='peer':self.owned['dependency_versions']['T-RP']=[0,6,178];self.baseline['retained_runtime']['dependency_versions']['T-RP']=[0,6,178]
            elif mutation=='component':self.owned['source_version']=[1,0,59]
            elif mutation=='owner':self.baseline['version']=[1,0,58];self.owned['version']=[1,0,58]
            elif mutation=='count':self.owned['conserved_files']=369
            else:self.owned['retained_component_conservation']['added_paths']=[]
            with self.subTest(mutation=mutation),self.assertRaises(AssertionError):self.validate()
            self.owned=before;self.baseline=baseline

    def host_fixture(self):
        """Materialize the existing370 opaque fixture, never private scripts."""
        import host_extensions
        candidates=['before','before-rp','before-spec','after','after-rp','after-spec','same','helper','plan','normal',*[f'unchanged-{n}'for n in range(209)]]
        raw_by_hash={m.digest(raw.encode()):raw.encode() for raw in candidates}
        for side,files in self.owned['files'].items():
            for name,digest in files.items():
                if name=='manifest.json':continue
                target=self.root/'runtime'/side/name;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(raw_by_hash[digest])
        (self.root/'baseline.json').write_text(json.dumps(self.baseline))
        host=self.root/'host';recipe=host/'recipes/vanilla_cooking/salt_smelting.json';recipe.parent.mkdir(parents=True);recipe.write_bytes(b'synthetic salt recipe')
        removed={'recipes/vanilla_cooking/salt_smelting.json':m.digest(recipe.read_bytes())}
        spec={'schema':1,'id':'fixture:salt','version':[1,0,4],'kind':'chinesefood-reviewed-repairs',
              'host_uuid':'fixture:author','archive_sha256':'dea708dd6443ea30d23e5791860a50181e8eeb560dcd7ec5a8e80fe22743e659',
              'expires':'2099-12-31','removal_condition':'fixture','feedback':'fixture','authorization':'fixture',
              'original_files':{},'patched_files':{},'imports':{},'copies':{},'insertions':[],'removed_files':removed}
        def output(args,cwd=None,**kwargs):
            if args[0]=='python3':return json.dumps(self.owned).encode()
            if args==['git','rev-parse','HEAD']:value='d'*40
            elif args==['git','status','--porcelain']:value=''
            elif args==['git','show','HEAD:baseline.json']:return (self.root/'baseline.json').read_bytes()
            elif args==['git','show',self.commit+':baseline.json']:return json.dumps(self.old).encode()
            else:return self.raw[args[-1]]
            return value if kwargs.get('text') else value.encode()
        for target in [patch.object(host_extensions,'REVIEWED_SALT_REMOVAL',removed),
                       patch.object(host_extensions,'match_stable_profile',return_value={'admission':'current-author-p58'}),
                       patch.object(m.subprocess,'check_output',side_effect=output)]:
            target.start();self.addCleanup(target.stop)
        context={'source_root':str(self.root),'source_commit':'d'*40,'sources':{key:str(self.root/key) for key in ['tavern','grilling','world-liquor']}}
        return host_extensions,spec,host,recipe,context

    def test_formal_host_guard_accepts_verified59_owner_with58_companion_contract(self):
        guard,spec,host,recipe,context=self.host_fixture()
        # The original implementation rejects this valid owning manifest59.
        with self.assertRaisesRegex(ValueError,'companion'):
            guard.apply_host_extension(spec,self.root/'runtime/BP',host,{})
        proof=guard.apply_host_extension(spec,self.root/'runtime/BP',host,{},retained_owner=context)
        self.assertFalse(recipe.exists());self.assertEqual(proof['removed_files'],spec['removed_files'])
        self.assertEqual(json.loads((self.root/'runtime/BP/manifest.json').read_text())['header']['version'],[1,0,59])

    def test_formal_host_guard_rejects_forged_context_and_nonconserved_runtime_before_removal(self):
        guard,spec,host,recipe,context=self.host_fixture()
        for forged in [{**context,'source_commit':'e'*40},{**context,'owner_version':[1,0,59]},
                       {**context,'source_root':str(self.root/'elsewhere')},
                       {**context,'sources':{**context['sources'],'tavern':'relative-peer'}}]:
            with self.subTest(forged=forged),self.assertRaisesRegex(ValueError,'retained salt owner'):
                guard.apply_host_extension(spec,self.root/'runtime/BP',host,{},retained_owner=forged)
            self.assertTrue(recipe.exists())
        helper=self.root/'runtime/BP/scripts/kept-000.js';helper.write_bytes(b'unreviewed payload')
        with self.assertRaisesRegex(ValueError,'current source payload differs'):
            guard.apply_host_extension(spec,self.root/'runtime/BP',host,{},retained_owner=context)
        self.assertTrue(recipe.exists())

    def test_formal_host_guard_keeps_wrong_fishing_and_corrupt_inner_conservation_closed(self):
        guard,spec,host,recipe,context=self.host_fixture()
        for row in self.manifests['BP']['dependencies']:
            if row.get('uuid')=='5e121bf2-1d2d-4da4-be15-cffc5f216d94':row['version']=[1,2,0]
        self.refresh();(self.root/'baseline.json').write_text(json.dumps(self.baseline))
        with self.assertRaisesRegex(ValueError,'retained salt owner'):
            guard.apply_host_extension(spec,self.root/'runtime/BP',host,{},retained_owner=context)
        self.assertTrue(recipe.exists())
        for row in self.manifests['BP']['dependencies']:
            if row.get('uuid')=='5e121bf2-1d2d-4da4-be15-cffc5f216d94':row['version']=[1,2,10058]
        self.refresh();(self.root/'baseline.json').write_text(json.dumps(self.baseline))
        self.owned['retained_component_conservation']['added_paths']=[]
        with self.assertRaisesRegex(ValueError,'retained salt owner'):
            guard.apply_host_extension(spec,self.root/'runtime/BP',host,{},retained_owner=context)
        self.assertTrue(recipe.exists())


if __name__=='__main__':unittest.main()
