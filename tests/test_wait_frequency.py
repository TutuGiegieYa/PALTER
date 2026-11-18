"""Rolling per-role wait limits, atomic retry accounting and native continuations."""
from copy import deepcopy
import json
import unittest

from palter import ensemble_world as w, role_schedule as scheduling, wait_lifecycle
from palter.ensemble import EnsembleApplication
from palter.model_contracts import ContractError

# Preserve coverage of the published all-wait policy. V119 has separate tests.
CURRENT_PREFIX = 'ai-tasks-v118.json'
from palter.storage import canonical
from tests.test_ensemble_review import ReviewFixTests


class WaitFrequencyTests(unittest.TestCase):
    def setUp(self):
        ReviewFixTests.setUp(self)
        self.app.gateway.current_version=CURRENT_PREFIX
        self.app.configure_rules(self.state,self.caller())
        self.state['agenda']=[]

    def caller(self,transform=None,version=CURRENT_PREFIX):
        return ReviewFixTests.caller(self,version,transform)

    def decision(self,mode='continue',speech='我先核对已有记录。',choice='wait'):
        def change(task,out,data):
            if task=='ensemble_role':
                out.update(action={'kind':choice,'args':[]},speech=speech,gesture=None,
                    next_decision={'mode':mode,'events':['next_observation'] if mode=='wait' else []})
        return change

    def test_rolling_window_and_cancellation_loop(self):
        s=self.state
        self.app.turn(s,'A',self.caller(self.decision('wait','')),0)
        self.assertEqual(scheduling.frequency(s,'A')['non_wait_replies_required'],2)
        wait_lifecycle.resolve(s,'A','cancelled','等待条件不再成立。')
        before=canonical(s['role_wait_history'])
        for _ in range(3):
            with self.assertRaises(ContractError) as caught:
                self.app.turn(s,'A',self.caller(self.decision('wait','')),0)
            self.assertEqual(caught.exception.feedback['field'],'next_decision')
            self.assertEqual(canonical(s['role_wait_history']),before)
        for remaining in (1,0):
            self.app.turn(s,'A',self.caller(self.decision()),0)
            self.assertEqual(scheduling.frequency(s,'A')['non_wait_replies_required'],remaining)
        self.app.turn(s,'A',self.caller(self.decision('wait','')),0)
        self.assertTrue(scheduling.waiting(s,'A'))
        self.assertEqual(s['role_wait_history']['A'],[False,True])
        self.assertEqual(len(s['decisions']),4)

    def test_empty_continue_counts_but_stationary_speech_and_gesture_do_not(self):
        data=scheduling.context(self.state,'A',limit_waits=True)
        for mode,choice,speech,gesture,waited in (
                ('wait','search','有事要查。',None,True),
                ('continue','wait','',None,True),
                ('continue','wait','我同意。',None,False),
                ('continue','wait','', '点头',False),
                ('continue','search','',None,False)):
            with self.subTest(mode=mode,choice=choice,speech=speech):
                s=deepcopy(self.state);plan={'mode':mode,'events':[]}
                scheduling.record_reply(s,'A',plan,data,choice,speech,gesture)
                self.assertEqual(s['role_wait_history']['A'],[waited])
        self.state['role_wait_history']={'A':[True]}
        data=scheduling.context(self.state,'A',limit_waits=True)
        for mode in ('wait','continue'):
            with self.assertRaises(ContractError):
                scheduling.validate({'mode':mode,'events':[]},data,'wait',speech='',gesture=None)
        scheduling.validate({'mode':'continue','events':[]},data,'wait',speech='我同意。')
        scheduling.validate({'mode':'continue','events':[]},data,'wait',gesture='点头')

    def test_other_actors_timer_pause_and_restart_do_not_reset(self):
        s=self.state
        self.app.turn(s,'A',self.caller(self.decision('wait','')),0)
        s['watch']['clock']=s['role_waits']['A']['deadline'];scheduling.reconcile(s)
        self.assertEqual(s['wait_results']['A']['status'],'timed_out')
        for _ in range(3):self.app.turn(s,'B',self.caller(self.decision()),0)
        self.assertTrue(scheduling.frequency(s,'B')['wait_allowed'])
        s['phase']='paused';s=json.loads(canonical(s));s['phase']='active'
        w.speak(s,'C','我刚收到新的线索。','A')
        self.assertEqual(scheduling.frequency(s,'A')['non_wait_replies_required'],2)
        self.assertNotIn('role_wait_history',canonical(scheduling.context(s,'B',limit_waits=True)))

    def test_all_wait_targets_share_one_allowance(self):
        s=self.state;s['role_wait_history']={'A':[True]}
        w.apply_choice(s,'A','search');data=scheduling.context(s,'A',limit_waits=True)
        for keys in ([],['next_observation'],['own_activity'],['phase:conclusion']):
            with self.subTest(keys=keys),self.assertRaises(ContractError):
                scheduling.validate({'mode':'wait','events':keys},data,'search',speech='我正在核查。')

    def test_fixed_activity_completion_still_wakes_once(self):
        s=self.state
        def search(task,out,data):
            if task=='ensemble_role':out.update(action={'kind':'search','args':[]},speech='',next_decision={'mode':'wait','events':['own_activity']})
        self.app.turn(s,'A',self.caller(search),0)
        self.assertTrue(scheduling.waiting(s,'A'))
        w.advance(s);scheduling.reconcile(s);scheduling.reconcile(s)
        self.assertFalse(scheduling.waiting(s,'A'))
        self.assertEqual(sum(q['actor']=='A' for q in s['agenda']),1)
        self.assertEqual(scheduling.frequency(s,'A')['non_wait_replies_required'],2)

    def test_native_tool_continuation_keeps_quota_and_counts_one_reply(self):
        s=self.state;s['role_wait_history']={'A':[True]};seen=[]
        def tool_then_reply(task,out,data):
            if task!='ensemble_role':return
            seen.append(deepcopy(data['scheduling']['wait_frequency']))
            if '_tool_messages' not in data:
                out.clear();out['_tool_message']={'role':'assistant','content':None,'tool_calls':[
                    {'id':'listener_fixture','type':'function','function':{'name':'create_event_listener',
                    'arguments':canonical({'description':'留意新消息','event_ids':['next_observation'],
                        'completion_condition':'','early_end_condition':''})}}]}
            else:self.decision()(task,out,data)
        self.app.turn(s,'A',self.caller(tool_then_reply),0)
        self.assertEqual(len(seen),2);self.assertEqual(seen[0],seen[1])
        self.assertFalse(seen[1]['wait_allowed'])
        self.assertEqual(s['role_wait_history']['A'],[True,False])
        self.assertEqual(len(s['decisions']),1)
        self.assertFalse(scheduling.waiting(s,'A'))

    def test_legacy_pinned_calls_keep_old_context_and_do_not_consume_quota(self):
        s=self.state;s['role_wait_history']={'A':[True]}
        for _ in range(2):self.app.turn(s,'A',self.caller(self.decision('wait',''),version='ai-tasks-v111.json'),0)
        self.assertEqual(s['role_wait_history']['A'],[True])
        for task,data in self.inputs:
            if task=='ensemble_role':self.assertNotIn('wait_frequency',data['scheduling'])

    def test_retry_and_store_restart_count_only_committed_reply(self):
        owner=self.app.store.session()['id'];s=deepcopy(self.state);s['role_wait_history']={'A':[True]}
        s=self.app.store.create_game(owner,{'command_id':'frequency_create','expected_game_id':None},lambda gid:dict(s,id=gid))
        original=self.provider;sent=[]
        def first_invalid(payload):
            response=original(payload)
            if 'PALTER_TASK: ensemble_role\n' in payload['messages'][0]['content']:
                sent.append(payload)
                if len(sent)==1:
                    out=json.loads(response['choices'][0]['message']['content'])
                    out['next_decision']={'mode':'wait','events':['next_observation']}
                    response['choices'][0]['message']['content']=canonical(out)
            return response
        self.app.gateway.client.transport=first_invalid
        command={'command_id':'frequency_retry','expected_revision':s['revision'],'kind':'background'}
        builder=lambda state,call:self.app.turn(state,'A',call,0)
        saved,_=self.app.operate(owner,s['id'],command,builder)
        self.assertEqual(len(sent),2)
        self.assertIn('Waiting is unavailable',canonical(sent[1]))
        self.assertEqual(saved['role_wait_history']['A'],[True,False])
        self.app=EnsembleApplication(self.app.store.path,self.app.gateway.client)
        self.app.gateway.current_version=CURRENT_PREFIX
        duplicate,_=self.app.operate(owner,s['id'],command,builder)
        self.assertEqual(len(sent),2)
        self.assertEqual(duplicate['role_wait_history']['A'],[True,False])
        saved,_=self.app.operate(owner,s['id'],{**command,'command_id':'frequency_next','expected_revision':saved['revision']},builder)
        self.assertEqual(saved['role_wait_history']['A'],[False,False])
        self.assertTrue(scheduling.frequency(saved,'A')['wait_allowed'])


if __name__=='__main__':unittest.main()
