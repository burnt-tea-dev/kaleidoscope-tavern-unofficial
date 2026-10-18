"""Fixed organization transfer applies to current reads, never old evidence."""
import copy
import io
import sys
from pathlib import Path
import unittest
from unittest.mock import patch
import zipfile

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from family_update import current_author_validation as current,stable_author_validation as historical
from family_update import preserved_client_assets_inputs as client,workflow,cookery_cache_validation,github_reads


class TransferArtifacts(unittest.TestCase):
    def artifact(self,module,change=None):
        remote=module.current_name(module.REPOSITORY)
        names=['stable-author-functional.json','stable-author-functional.log','cookery-cache-functional.json','cookery-cache-functional.tap',
               'cookery-guide-functional.json','cookery-guide-functional.tap','saturation-scheduling-functional.json','saturation-scheduling-functional.log'] if module is historical else ['source.json','source.log']
        out=io.BytesIO()
        with zipfile.ZipFile(out,'w') as archive:
            for name in names:archive.writestr(name,b'Synthetic unchanged artifact bytes')
        raw=out.getvalue();prefix='repos/'+remote
        record={'id':module.REPOSITORY_ID,'full_name':remote}
        metadata={**record,'private':True,'owner':{'login':'burnt-tea-dev','id':344456559,'type':'Organization'}}
        artifact_name={current:'current-author-functional',historical:'stable-author-functional',client:'client-assets-functional'}[module]
        responses={prefix:metadata,prefix+'/actions/runs/7':{'repository':record,'status':'completed','conclusion':'success','head_sha':'source','head_branch':'main','event':'push','path':'.github/workflows/canonical.yml'},
            prefix+'/git/commits/source':{'tree':{'sha':'full-tree'}},prefix+'/actions/artifacts/8':{'name':artifact_name,'expired':False,'workflow_run':{'id':7,'head_sha':'source'},'digest':'sha256:'+module.digest(raw)}}
        if change:change(responses,prefix)
        module.artifact_members.cache_clear()
        try:
            with patch.object(workflow,'gh_json',side_effect=lambda endpoint:responses[endpoint]),patch.object(cookery_cache_validation,'private_ci_records',return_value=(['canonical'],[],[])),patch.object(github_reads,'api_bytes',return_value=raw):
                return module.artifact_members(7,8,'source','full-tree')
        finally:module.artifact_members.cache_clear()

    def test_all_three_read_exact_same_id_current_private_organization(self):
        for module in [current,historical,client]:
            with self.subTest(module=module.__name__):
                members,ci=self.artifact(module);self.assertTrue(members);self.assertEqual(ci['artifact_id'],8)
                self.assertEqual(module.REPOSITORY,'casama233/senluo-family-integration-private')

    def test_wrong_id_owner_visibility_and_run_record_are_rejected(self):
        mutations=[lambda rows,p:rows[p].update(id=1),lambda rows,p:rows[p].update(private=False),
            lambda rows,p:rows[p]['owner'].update(id=1),lambda rows,p:rows[p]['owner'].update(type='User'),
            lambda rows,p:rows[p].update(full_name='foreign/senluo-family-integration-private'),
            lambda rows,p:rows[p+'/actions/runs/7']['repository'].update(id=1),
            lambda rows,p:rows[p+'/actions/runs/7']['repository'].update(full_name='foreign/senluo-family-integration-private')]
        for module in [current,historical,client]:
            for index,mutate in enumerate(mutations):
                with self.subTest(module=module.__name__,case=index),self.assertRaises(AssertionError):self.artifact(module,mutate)


if __name__=='__main__':unittest.main()
