"""Normal BSM lifecycle requests are single-shot across both response contracts."""
import copy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from family_update import common as c


class LifecycleActionTests(unittest.TestCase):
    def setUp(self):
        temporary=tempfile.TemporaryDirectory();self.addCleanup(temporary.cleanup)
        self.output=Path(temporary.name);self.server='fixture server'
        self.answer={'status':'success','server_name':self.server,'outcome':'started','message':'Started'}
        self.readback={'name':self.server,'status':'RUNNING','version':'native-fixture','player_count':0}
        self.tasks=[];self.calls=[];self.events=[];self.post_error=None;self.read_error=None
        for context in [patch.multiple(c,R=self.output,SERVER=self.server),
                        patch.object(c,'assert_lease'),patch.object(c,'verify_server_binding'),
                        patch.object(c,'atomic',side_effect=self.write),patch.object(c,'api',side_effect=self.api),
                        patch.object(c.time,'sleep')]:
            active=context.start();self.addCleanup(context.stop)
            if getattr(context,'attribute',None)=='verify_server_binding':self.binding=active

    def write(self,path,value):
        self.events.append(('persist',Path(path).name))
        Path(path).write_text(json.dumps(value))

    def api(self,path,body=None,method='GET'):
        self.calls.append((path,body,method));self.events.append(('request',method,path))
        if method=='POST':
            if self.post_error:raise self.post_error
            return copy.deepcopy(self.answer)
        if path.endswith('/summary'):
            if self.read_error:raise self.read_error
            # Readback happens only after the exact terminal result is durable.
            self.assertTrue(any(self.output.glob('*-result.json')))
            return copy.deepcopy(self.readback)
        self.assertEqual(path,'/api/tasks/status/owned-task')
        return copy.deepcopy(self.tasks.pop(0))

    def read(self,name):return json.loads((self.output/name).read_text())

    def posts(self):return [call for call in self.calls if call[2]=='POST']

    def test_actual_terminal_start_persists_before_independent_readback(self):
        c.action('start')
        self.assertEqual(self.posts(),[('/api/server/fixture%20server/start',{},'POST')])
        self.assertEqual(self.read('start-response.json'),self.answer)
        self.assertEqual(self.read('start-result.json'),self.answer)
        self.assertEqual(self.read('start-readback.json'),self.readback)
        self.assertEqual(len(self.calls),2);self.assertEqual(self.binding.call_count,2)
        self.assertLess(self.events.index(('persist','start-result.json')),self.events.index(('request','GET','/api/server/fixture%20server/summary')))

    def test_actual_terminal_already_running_is_confirmed_without_another_post(self):
        self.answer['outcome']='already_running';c.action('start')
        self.assertEqual(len(self.posts()),1)

    def test_actual_terminal_stop_and_already_stopped_require_stopped_empty_summary(self):
        self.readback['status']='STOPPED'
        for outcome in ['stopped','already_stopped']:
            self.calls.clear();self.answer['outcome']=outcome;c.action('stop')
            self.assertEqual(len(self.posts()),1)
            self.assertEqual(self.read('stop-result.json'),self.answer)

    def test_wrong_server_outcome_or_error_is_preserved_and_never_retried(self):
        for changed in [{'server_name':'foreign'},{'outcome':'stopped'},{'status':'error'},{'outcome':None}]:
            self.calls.clear();answer={**self.answer,**changed};self.answer=answer
            with self.subTest(changed=changed),self.assertRaises(AssertionError):c.action('start')
            self.assertEqual(len(self.calls),1);self.assertEqual(len(self.posts()),1)
            self.assertEqual(self.read('start-result.json'),answer)
            self.answer={'status':'success','server_name':self.server,'outcome':'started'}

    def test_unknown_and_ambiguous_post_shapes_do_not_create_or_poll_a_task(self):
        cases=[None,[],{}, {'status':'success','task_id':'owned-task'},
               {'status':'pending','task_id':'owned-task','server_name':self.server},
               {'status':'pending','task_id':'../foreign'},
               {'status':'success','result':{'status':'success','server_name':self.server}}]
        for answer in cases:
            self.calls.clear();self.answer=answer
            with self.subTest(answer=answer),self.assertRaises(AssertionError):c.action('start')
            self.assertEqual(len(self.calls),1);self.assertEqual(self.read('start-response.json'),answer)

    def test_post_transport_error_is_not_retried_or_reclassified_as_a_task(self):
        self.post_error=OSError('ambiguous transport result')
        with self.assertRaisesRegex(OSError,'ambiguous transport'):c.action('start')
        self.assertEqual(len(self.calls),1);self.assertFalse((self.output/'start-result.json').exists())

    def test_failed_summary_read_preserves_success_response_without_another_post(self):
        self.read_error=OSError('status read failed')
        with self.assertRaisesRegex(OSError,'status read failed'):c.action('start')
        self.assertEqual(len(self.posts()),1);self.assertEqual(len(self.calls),2)
        self.assertEqual(self.read('start-result.json'),self.answer)

    def test_stale_or_foreign_readback_is_preserved_and_refused_without_retry(self):
        for changed in [{'status':'STOPPED'},{'status':'STARTING'},{'name':'foreign'}]:
            self.calls.clear();self.readback={**self.readback,**changed}
            with self.subTest(changed=changed),self.assertRaises(AssertionError):c.action('start')
            self.assertEqual(len(self.posts()),1);self.assertEqual(self.read('start-readback.json'),self.readback)
            self.readback={'name':self.server,'status':'RUNNING','version':'native-fixture','player_count':0}

    def test_stop_readback_with_unknown_player_count_is_refused(self):
        self.answer['outcome']='stopped';self.readback.update(status='STOPPED',player_count=None)
        with self.assertRaisesRegex(AssertionError,'unknown or nonzero players'):c.action('stop')
        self.assertEqual(len(self.posts()),1)

    def test_known_pending_task_completes_then_gets_independent_readback(self):
        self.answer={'status':'pending','task_id':'owned-task','message':'Queued'}
        completed={'status':'success','task_id':'owned-task','result':{'status':'success','server_name':self.server}}
        self.tasks=[{'status':'running','task_id':'owned-task'},completed]
        c.action('start')
        self.assertEqual(len(self.posts()),1);self.assertEqual(len(self.calls),4)
        self.assertEqual(self.read('start-response.json'),self.answer)
        self.assertEqual(self.read('start-result.json'),completed)

    def test_failed_or_foreign_legacy_task_result_is_preserved_without_resubmission(self):
        self.answer={'status':'pending','task_id':'owned-task'}
        for row in [{'status':'error','result':None},
                    {'status':'success','result':{'status':'success','server_name':'foreign'}},
                    {'status':'success','result':{'status':'error','server_name':self.server}},
                    {'status':'success','result':{'status':'success','server_name':self.server,'outcome':'stopped'}}]:
            self.calls.clear();self.tasks=[row]
            with self.subTest(row=row),self.assertRaises(AssertionError):c.action('start')
            self.assertEqual(len(self.posts()),1);self.assertEqual(len(self.calls),2)
            self.assertEqual(self.read('start-result.json'),row)

    def test_foreign_task_identity_or_unknown_state_never_gets_accepted(self):
        self.answer={'status':'pending','task_id':'owned-task'}
        for row in [{'status':'success','id':'foreign','result':{}},{'status':'completed','result':{}}]:
            self.calls.clear();self.tasks=[row]
            with self.subTest(row=row),self.assertRaises(AssertionError):c.action('start')
            self.assertEqual(len(self.posts()),1);self.assertEqual(self.read('start-task-response.json'),row)

    def test_legacy_task_timeout_does_not_repeat_the_original_post(self):
        self.answer={'status':'pending','task_id':'owned-task'};self.tasks=[{'status':'running'}]
        with patch.object(c.time,'monotonic',side_effect=[0,1,61]):
            with self.assertRaisesRegex(RuntimeError,'timed out'):c.action('start')
        self.assertEqual(len(self.posts()),1);self.assertEqual(len(self.calls),2)


if __name__=='__main__':unittest.main()
