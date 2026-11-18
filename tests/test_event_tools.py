"""Native tool receipts, prefix isolation and bounded role feedback."""
from copy import deepcopy
import json
import unittest

from palter import event_tools, role_schedule as scheduling, role_events, ensemble_world as w
from palter.storage import canonical
from tests import test_ensemble_review as fixture
from tests import test_spectator as watch_fixture


def tool(arguments,identity='native_call_1'):
    return {'id':identity,'type':'function','function':{'name':'create_event_listener','arguments':canonical(arguments)}}

def proposal():
    return {'description':'等有人公开说明时间差','event_ids':[],'completion_condition':'我听到有人公开说明时间差','early_end_condition':'我决定不再等'}

class EventToolTests(unittest.TestCase):
    def setUp(self):
        fixture.ReviewFixTests.setUp(self);self.app.configure_rules(self.state,lambda:None);self.state['agenda']=[]

    def test_native_tools_and_shared_protocol_are_stable_when_instances_change(self):
        gateway=self.app.gateway;baseline=w.baseline(self.state,'C')
        first,h1=gateway.payload('ensemble_role',baseline,{'events':[]})
        second,h2=gateway.payload('ensemble_role',baseline,{'events':[{'id':'instance-canary','status':'active'}]})
        self.assertEqual(h1,h2);self.assertEqual(first['tools'],second['tools'])
        self.assertEqual(first['messages'][:-1],second['messages'][:-1]);self.assertNotEqual(first['messages'][-1],second['messages'][-1])
        self.assertNotIn('instance-canary',canonical(first['tools']));self.assertNotIn('instance-canary',canonical(second['messages'][:-1]))
        dm,_=gateway.payload('ensemble_dm',None,{'tracked_events':[]})
        self.assertEqual(first['messages'][0]['content'].split('PALTER_TASK:')[0],dm['messages'][0]['content'].split('PALTER_TASK:')[0])
        self.assertEqual(first['tools'][0]['function']['name'],'create_event_listener')
        self.assertEqual(first['response_format'],{'type':'text'})
        self.assertEqual(dm['response_format'],{'type':'json_object'})

    def test_each_role_has_same_tool_permission_without_other_listener_visibility(self):
        s=self.state
        for actor in w.ACTORS:
            result=event_tools.execute(s,actor,tool(proposal(),actor),'provider_'+actor)
            self.assertEqual(result['status'],'pending_dm')
            own=scheduling.options(s,actor);self.assertIn(result['wait_event'],{x['id'] for x in own})
            for other in w.ACTORS:
                if other!=actor:self.assertNotIn(result['wait_event'],{x['id'] for x in scheduling.options(s,other)})
        self.assertEqual(len(s['tracked_events']),4)

    def test_fixed_listener_needs_no_dm_and_native_receipt_is_idempotent(self):
        s=self.state;w.apply_choice(s,'A','invite:B');w.apply_choice(s,'B','accept:i1');scheduling.reconcile(s)
        t=tool({'description':'等他们谈完','event_ids':['conversation:private-1'],'completion_condition':'','early_end_condition':''})
        result=event_tools.execute(s,'C',t,'paid-1');same=event_tools.execute(s,'C',t,'paid-1')
        self.assertEqual(result,same);self.assertEqual(result['status'],'registered');self.assertFalse(s.get('tracked_events'))
        self.assertEqual(len(s['event_tool_receipts']),1);self.assertFalse(self.provider.calls)
        s['agenda']=[q for q in s['agenda'] if q['actor']!='C']
        scheduling.commit(s,'C',{'mode':'wait','events':[result['wait_event']]},scheduling.context(s,'C'))
        self.assertEqual(s['role_waits']['C']['events'],['conversation:private-1'])
        w.close_chat(s,w.chat_for(s,'A'));scheduling.reconcile(s);self.assertFalse(scheduling.waiting(s,'C'))

    def test_tool_cannot_choose_foreign_actor_or_hidden_event_or_unknown_function(self):
        s=self.state;w.apply_choice(s,'A','search');hidden='activity:'+s['activities'][-1]['id']
        variants=[{**proposal(),'actor':'A'},dict(description='x',event_ids=[hidden],completion_condition='',early_end_condition='')]
        for args in variants:
            with self.assertRaises(ValueError):event_tools.validate_call(s,'C',tool(args))
        forbidden=tool(proposal());forbidden['function']['name']='reveal_hidden_truth'
        with self.assertRaises(ValueError):event_tools.validate_call(s,'C',forbidden)

    def test_old_pinned_prefixes_have_no_tools_or_new_protocol(self):
        payload,_=self.app.gateway.payload('ensemble_role',w.baseline(self.state,'C'),{},'ai-tasks-v55.json')
        self.assertNotIn('tools',payload);self.assertNotIn('SHARED EVENT PROTOCOL',payload['messages'][0]['content'])
        self.assertEqual(payload['response_format'],{'type':'json_object'})


class NativeToolRecoveryTests(unittest.TestCase):
    def setUp(self):
        watch_fixture.SpectatorTests.setUp(self);self.requests=[];self.fail_final=False;self.repeat_tools=False;self.skip_listener=False
        base=self.provider
        def transport(payload):
            self.requests.append(deepcopy(payload))
            is_role='PALTER_TASK: ensemble_role\n' in payload['messages'][0]['content']
            feedback=[m for m in payload['messages'] if m['role']=='tool']
            if is_role and (not feedback or self.repeat_tools):
                return {'choices':[{'finish_reason':'tool_calls','message':{'role':'assistant','content':None,'tool_calls':[tool(proposal())]}}],
                        'usage':{'prompt_tokens':100,'completion_tokens':30,'prompt_cache_hit_tokens':40,'prompt_cache_miss_tokens':60}}
            if is_role and self.fail_final:raise TimeoutError()
            response=base(payload)
            if is_role:
                out=json.loads(response['choices'][0]['message']['content']);receipt=json.loads(feedback[0]['content'])
                out['next_decision']={'mode':'wait','events':[receipt['wait_event']]}
                if self.skip_listener:out['next_decision']['events']=['next_observation']
                response['choices'][0]['message']['content']=canonical(out)
            return response
        self.app.gateway.client.transport=transport
    def create(self):return watch_fixture.SpectatorTests.create(self)
    def state(self):return watch_fixture.SpectatorTests.state(self)
    def cmd(self,*args,**kwargs):return watch_fixture.SpectatorTests.cmd(self,*args,**kwargs)

    def test_native_call_result_and_final_decision_are_persisted_and_scoped(self):
        self.create();self.cmd('watch_step');self.app.pump(self.gid,True);s=self.state()
        self.assertIsNone(s['background_error']);self.assertTrue(scheduling.waiting(s,'A'))
        self.assertEqual(len(s['tracked_events']),1);self.assertEqual(s['tracked_events'][0]['status'],'active')
        follow=next(p for p in self.requests if any(m['role']=='tool' for m in p['messages']))
        message=next(m for m in follow['messages'] if m['role']=='assistant')
        result=next(m for m in follow['messages'] if m['role']=='tool')
        self.assertEqual(result['tool_call_id'],message['tool_calls'][0]['id'])
        self.assertNotIn('event_tool_receipts',canonical(w.context(s,'B')))
        with self.app.store.transaction(False) as con:
            rows=con.execute("SELECT stage,result,response FROM ai_calls WHERE task='ensemble_role' ORDER BY started").fetchall()
        self.assertEqual([r['stage'] for r in rows],['role_A','role_A_continuation_1'])
        self.assertIn('_tool_message',json.loads(rows[0]['result']));self.assertIn('tool_calls',json.loads(rows[0]['response'])['choices'][0]['message'])

    def test_resume_reuses_native_call_without_duplicate_listener_or_creation(self):
        self.create();self.cmd('watch_add_budget')  # Reserve four unknown-usage retries plus recovery.
        self.fail_final=True;self.cmd('watch_resume');self.app.pump(self.gid,True)
        self.assertEqual(self.state()['watch']['pause_reason'],'error');self.assertFalse(self.state().get('event_listeners'))
        self.fail_final=False;self.cmd('watch_step');self.app.pump(self.gid,True);s=self.state()
        self.assertIsNone(s['background_error']);self.assertEqual(len(s['event_listeners']),1);self.assertEqual(len(s['tracked_events']),1)
        native=[p for p in self.requests if 'PALTER_TASK: ensemble_role\n' in p['messages'][0]['content'] and not any(m['role']=='tool' for m in p['messages'])]
        self.assertEqual(len(native),1)

    def test_second_tool_batch_stops_without_saving_partial_effects(self):
        self.create();self.repeat_tools=True;self.cmd('watch_step');self.app.pump(self.gid,True);s=self.state()
        self.assertEqual(s['watch']['pause_reason'],'error');self.assertFalse(s.get('event_listeners'))
        self.assertEqual(len([p for p in self.requests if 'PALTER_TASK: ensemble_role\n' in p['messages'][0]['content']]),5)

    def test_custom_wait_cannot_skip_its_new_listener(self):
        self.create();self.skip_listener=True;self.cmd('watch_step');self.app.pump(self.gid,True);s=self.state()
        self.assertEqual(s['watch']['pause_reason'],'error');self.assertFalse(s.get('tracked_events'))
        self.skip_listener=False;self.cmd('watch_step');self.app.pump(self.gid,True);s=self.state()
        self.assertIsNone(s['background_error']);self.assertEqual(len(s['tracked_events']),1)


if __name__=='__main__':unittest.main()
