"""Exercise private original-CI artifact binding; no real API, source or packs."""
import copy
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
from contextlib import ExitStack
from unittest.mock import patch
import zipfile

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from family_update import common as c, extension_validation, workflow, github_reads
from family_update import preserved_client_assets_inputs as m
from family_update import prospective_preserved_inputs as dispatch


class ClientSourceBoundaries(unittest.TestCase):
    def setUp(self):
        temp=tempfile.TemporaryDirectory();self.addCleanup(temp.cleanup)
        self.root=Path(temp.name);self.ext=self.root/'source';self.ext.mkdir()
        self.head,self.tree,self.old_tree='a'*40,'b'*40,'c'*40
        self.baseline={'repository':m.PRIVATE,'version':m.VERSION,'source_trees':{'BP':{'sha256':'d'*64,'files':3},'RP':{'sha256':'e'*64,'files':2}}}
        self.write(self.ext/'baseline.json',self.baseline)
        self.write(self.ext/'.repo-target.json',{'repository':m.REPOSITORY,'repository_id':m.REPOSITORY_ID,'private':True})
        source=self.ext/'tools/client_assets.py';self.write(source,'Synthetic owned recipe producer')
        self.recipe={key:{} for key in ['uuids','input_hashes','output_hashes','changed','before_versions','versions','source_facts']}
        self.recipe.update(approved_input_receipt_sha256=m.APPROVED,patch_source_sha256={'tools/client_assets.py':c.sha(source)})
        self.recipe_path=self.ext/m.RECIPE;self.write(self.recipe_path,self.recipe)
        self.report_path=self.root/'ci'/m.REPORT;self.log=self.report_path.parent/'client-assets.log';self.write(self.log,'Synthetic successful source checks, never native/client.')
        self.report={'schema':1,'kind':'client_assets_functional','profile':m.PROFILE,'repository':m.PRIVATE,
            'canonical_repository':m.REPOSITORY,'canonical_repository_id':m.REPOSITORY_ID,
            'version':m.VERSION,'source_trees':self.baseline['source_trees'],'source_commit':self.head,'git_tree':self.tree,
            'recipe_sha256':c.sha(self.recipe_path),**copy.deepcopy(self.recipe),'facts':{key:True for key in m.FACTS},
            'test_command':['python','tools/build_client_assets_evidence.py'],'test_exit_code':0,
            'test_log':{'name':self.log.name,'sha256':c.sha(self.log)},
            'client':False,'simulated_players':False,'native_loading':False,'production_ready':False}
        self.proof={'schema':1,'kind':'client_assets_source','profile':m.PROFILE,'repository':m.PRIVATE,
            'version':m.VERSION,'source_trees':self.baseline['source_trees'],'source_commit':self.head,
            'git_tree':self.tree,'private_pull_request':58,'ci':{'run_id':100,'artifact_id':200}}
        self.proof_path=self.root/'proof.json';self.review={'source_commit':self.head,'recipe':{'path':m.RECIPE,'sha256':c.sha(self.recipe_path)}}
        self.checks=[{'id':1,'name':'baseline','status':'completed','conclusion':'success','head_sha':self.head,'html_url':'https://example.invalid/source','completed_at':'2026-10-19T00:00:00Z','app':{'id':1,'slug':'github-actions'}}]
        self.run={'repository':{'id':m.REPOSITORY_ID},'status':'completed','conclusion':'success','head_sha':self.head,'head_branch':'main','event':'push','path':'.github/workflows/canonical.yml'}
        self.pr={'merged':True,'merge_commit_sha':self.head,'base':{'ref':'main','repo':{'id':m.REPOSITORY_ID}},'head':{'sha':'f'*40,'repo':{'id':m.REPOSITORY_ID}}}
        self.remote_trees={self.head:self.tree,'f'*40:self.tree}
        self.artifact={'name':'client-assets-functional','expired':False,'workflow_run':{'id':100,'head_sha':self.head}}
        self.save()

    def write(self,path,value):
        path.parent.mkdir(parents=True,exist_ok=True);path.write_text(json.dumps(value)+'\n' if isinstance(value,dict) else value)

    def save(self,artifact=True):
        self.write(self.report_path,self.report);self.proof['differential']=c.report_ref(self.report_path)
        self.write(self.proof_path,self.proof);self.review['source_validation']=c.report_ref(self.proof_path)
        if artifact:
            out=io.BytesIO()
            with zipfile.ZipFile(out,'w') as archive:
                archive.writestr(m.REPORT,self.report_path.read_bytes());archive.writestr(self.log.name,self.log.read_bytes())
            self.archive=out.getvalue();self.artifact['digest']='sha256:'+m.digest(self.archive)
        m.artifact_members.cache_clear()

    def git(self,root,*args):
        if args==('rev-parse','HEAD'):return self.head
        if args[0]=='rev-parse' and args[1].endswith('^{tree}'):return self.tree if args[1] in ['HEAD^{tree}',self.head+'^{tree}'] else self.old_tree
        if args[:2]==('merge-base','--is-ancestor'):return ''
        raise AssertionError('Unexpected synthetic git '+repr(args))

    def github(self,endpoint):
        prefix='repos/'+m.REPOSITORY
        if endpoint==prefix:return {'full_name':m.REPOSITORY,'id':m.REPOSITORY_ID,'private':True}
        if endpoint==prefix+'/pulls/58':return self.pr
        if endpoint.startswith(prefix+'/git/commits/'):return {'tree':{'sha':self.remote_trees[endpoint.rsplit('/',1)[1]]}}
        if endpoint==prefix+'/actions/runs/100':return self.run
        if endpoint==prefix+'/actions/artifacts/200':return self.artifact
        if endpoint==prefix+'/commits/'+self.head+'/check-runs?per_page=100':return {'total_count':len(self.checks),'check_runs':self.checks}
        if endpoint==prefix+'/commits/'+self.head+'/status':return {'statuses':[]}
        raise AssertionError('Unexpected synthetic API '+endpoint)

    def admit(self):
        with ExitStack() as stack:
            stack.enter_context(patch.object(c,'EXTENSION',self.ext))
            stack.enter_context(patch.object(c,'git',side_effect=self.git))
            stack.enter_context(patch.object(extension_validation,'EXTENSION',self.ext))
            stack.enter_context(patch.object(extension_validation,'git',side_effect=self.git))
            stack.enter_context(patch.object(dispatch,'committed',side_effect=lambda path,name:self.assertTrue(path.is_file())))
            stack.enter_context(patch.object(workflow,'gh_json',side_effect=self.github))
            stack.enter_context(patch.object(github_reads,'api_bytes',side_effect=lambda endpoint:self.archive))
            return m.source_evidence(self.review,self.recipe)

    def test_real_binding_ci_classifier_and_original_main_artifact_succeed(self):
        before=self.report_path.read_bytes();ref,binding,ci=self.admit()
        self.assertEqual(ref,c.report_ref(self.report_path));self.assertEqual(binding['current_source_tree_oid'],self.tree)
        self.assertEqual(ci['source_ci']['run_id'],100);self.assertEqual(ci['source_ci']['checks'][0]['head_sha'],self.head)
        self.assertEqual(before,self.report_path.read_bytes())

    def test_main_success_exact_digest_and_completed_checks_required(self):
        checks=copy.deepcopy(self.checks)
        for field,value in [('head_branch','feature'),('conclusion','failure'),('head_sha','0'*40),('path','other.yml')]:
            old=self.run[field];self.run[field]=value;m.artifact_members.cache_clear()
            with self.subTest(field=field),self.assertRaises(AssertionError):self.admit()
            self.run[field]=old
        self.checks=[];m.artifact_members.cache_clear()
        with self.assertRaisesRegex(AssertionError,'Private CI'):self.admit()
        self.checks=checks
        self.artifact['digest']='sha256:'+'0'*64;m.artifact_members.cache_clear()
        with self.assertRaises(AssertionError):self.admit()

    def test_rebound_local_report_cannot_replace_original_artifact(self):
        self.report['facts']['partial_alpha_preserved']=True;self.report['extra']='locally rewritten'
        self.save(artifact=False)
        with self.assertRaisesRegex(AssertionError,'original CI artifact'):self.admit()

    def test_missing_fact_recipe_mismatch_or_client_promotion_rejected(self):
        original=copy.deepcopy(self.report)
        for mutate in [lambda d:d['facts'].pop('core_retired_definitions_unchanged'),lambda d:d.update(recipe_sha256='0'*64),
                       lambda d:d.update(client=True),lambda d:d['output_hashes'].update({'foreign':{}})]:
            self.report=copy.deepcopy(original);mutate(self.report);self.save()
            with self.assertRaises(AssertionError):self.admit()

    def test_full_tree_and_private_pr_scope_cannot_be_relaxed(self):
        self.proof['source_commit']='1'*40;self.save()
        with self.assertRaisesRegex(AssertionError,'full Git tree'):self.admit()
        self.proof['source_commit']=self.head;self.save()
        self.pr['base']['repo']['id']=1
        with self.assertRaises(AssertionError):self.admit()
        self.pr['base']['repo']['id']=m.REPOSITORY_ID
        self.remote_trees['f'*40]=self.old_tree;self.remote_trees[self.head]=self.old_tree
        with self.assertRaises(AssertionError):self.admit()

    def test_changed_log_source_or_artifact_identity_fails(self):
        self.write(self.log,'changed');self.save(artifact=False)
        with self.assertRaises(AssertionError):self.admit()
        self.report['test_log']['sha256']=c.sha(self.log);self.save()
        self.write(self.ext/'tools/client_assets.py','changed producer')
        with self.assertRaises(AssertionError):self.admit()


if __name__=='__main__':unittest.main()
