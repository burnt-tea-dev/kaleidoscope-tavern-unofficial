"""Actor repair adoption must preserve the latest save across failed renames."""
import json
from pathlib import Path
import tempfile
import types
import unittest
from unittest.mock import patch

from family_update import deploy_live as m,storage
from family_guard import hashes,atomic


class NativeActorInstallationTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name);self.output=self.root/'candidate';self.output.mkdir()
        self.world=self.root/'live';(self.world/'db').mkdir(parents=True)
        (self.world/'db/data').write_bytes(b'latest native items')
        (self.world/'world_behavior_packs.json').write_text('[]')
        (self.output/'production-snapshot/db').mkdir(parents=True)
        (self.output/'production-snapshot/db/data').write_bytes(b'latest native items')
        self.plan=self.root/'plan.json';self.plan.write_text('{}')
        self.receipt={'only_planned_keys_changed':True,'items_materialized':False}
        (self.output/'saved-world-native-actor-recovery.json').write_text(json.dumps(self.receipt))
        self.config={'native_actor_recovery_plan':str(self.plan)}
        self.calls=[]
        def recover(world,plan,**boundary):
            self.calls.append((world,boundary))
            self.assertNotEqual(world,self.world)
            self.assertEqual((self.world/'db/data').read_bytes(),b'latest native items')
            (world/'db/data').write_bytes(b'repaired original items')
            return dict(self.receipt)
        self.adapter=types.SimpleNamespace(recover_world=recover,verify_world=lambda *a,**kw:None)
        for context in [patch.multiple(m,R=self.output,W=self.world,CONFIG=self.config),
                        patch.object(m,'hashes',hashes),
                        patch.object(m,'atomic',atomic),
                        patch.object(m,'assert_lease'),patch.object(m,'summary',return_value={'status':'STOPPED'}),
                        patch.dict('sys.modules',{'native_actor_recovery':self.adapter})]:
            context.start();self.addCleanup(context.stop)

    def test_only_rehearsed_stage_is_adopted_and_original_database_remains(self):
        m.adopt_native_actor_recovery()
        self.assertEqual((self.world/'db/data').read_bytes(),b'repaired original items')
        self.assertEqual((self.output/'production-original-db/data').read_bytes(),b'latest native items')
        self.assertEqual(self.calls[0][1],{'stage_root':self.output,'source_world':self.world})
        self.assertTrue((self.output/'production-native-actor-recovery.json').is_file())

    def test_changed_latest_save_rejected_before_copy_or_repair(self):
        (self.world/'db/data').write_bytes(b'new player change')
        with self.assertRaisesRegex(AssertionError,'latest stopped database'):m.adopt_native_actor_recovery()
        self.assertEqual(self.calls,[])
        self.assertFalse((self.output/'native-actor-recovery-stage').exists())

    def test_receipt_mismatch_never_swaps_live_database(self):
        (self.output/'saved-world-native-actor-recovery.json').write_text('{}')
        with self.assertRaisesRegex(AssertionError,'rehearsed exact transaction'):m.adopt_native_actor_recovery()
        self.assertEqual((self.world/'db/data').read_bytes(),b'latest native items')
        self.assertFalse((self.output/'production-native-actor-recovery.json').exists())

    def test_second_rename_failure_preserves_fence_and_both_databases(self):
        replace=m.os.replace
        def fail_stage(source,target):
            if Path(source).name=='db' and 'native-actor-recovery-stage' in Path(source).parts:
                raise OSError('injected second rename failure')
            return replace(source,target)
        with patch.object(m.os,'replace',side_effect=fail_stage):
            with self.assertRaisesRegex(OSError,'second rename'):m.adopt_native_actor_recovery()
        self.assertTrue((self.output/'production-native-actor-recovery.json').is_file())
        self.assertEqual((self.output/'production-original-db/data').read_bytes(),b'latest native items')
        self.assertEqual((self.output/'native-actor-recovery-stage/world/db/data').read_bytes(),b'repaired original items')
        self.assertTrue(m.retain_stopped_on_failure())

    def test_new_database_copy_is_included_in_disk_budget(self):
        candidate=self.output/'packs';candidate.mkdir();(candidate/'pack').write_bytes(b'pack')
        base=storage.deployment_allocation(self.world,candidate)
        repaired=storage.deployment_allocation(self.world,candidate,native_actor_recovery=True)
        self.assertEqual(repaired-base,storage.allocated(self.world/'db'))

    def test_final_receipt_rejects_observations_from_another_native_run(self):
        from family_update import workflow
        candidate=self.output/'release-candidate';candidate.mkdir()
        (candidate/'family-receipt.json').write_text('{}')
        (self.output/'saved-world-native-actor-recovery.json').write_text(json.dumps(self.receipt))
        saved={'test_only_overlays':[],'runs':[{'phase':phase,'log_sha256':'actual '+phase,
                       'ticking_areas_created':[{'name':'actual'}],
                       'native_actor_recovery_verified':True} for phase in ['first','restart']]}
        checker=unittest.mock.Mock(return_value={'ok':True})
        for changed in [{'log_sha256':'other log'},{'ticking_areas_created':[{'name':'other'}]}]:
            rows=[{'phase':run['phase'],'observation':{'native_run':{key:value for key,value in run.items() if key!='native_actor_recovery_verified'}},'verification':{'ok':True}} for run in saved['runs']]
            rows[0]['observation']['native_run'].update(changed)
            proof={'plan':m.report_ref(self.plan),'ok':True,'client':False,'runs':rows}
            (self.output/'saved-world-native-actor-preservation.json').write_text(json.dumps(proof))
            with self.subTest(changed=changed),patch.object(m,'C',candidate),patch.object(workflow,'verify_native',return_value=saved),patch.dict('sys.modules',{'native_actor_recovery_validation':types.SimpleNamespace(verify=checker)}):
                with self.assertRaisesRegex(AssertionError,'different native run'):m.finalize_receipt()
        checker.assert_not_called()


if __name__=='__main__':unittest.main()
