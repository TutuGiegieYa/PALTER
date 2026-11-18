"""Only consecutive subscriptions to the next received observation are limited."""
from copy import deepcopy
import json
import unittest

from palter import event_tools, ensemble_world as w, role_schedule as scheduling, wait_lifecycle
from palter.ensemble import EnsembleApplication
from palter.model_contracts import ContractError, CURRENT_PREFIX
from palter.storage import canonical
from tests import test_ensemble_review as fixture


class ObservationWaitTests(unittest.TestCase):
    def setUp(self):
        fixture.ReviewFixTests.setUp(self)
        self.app.gateway.current_version=CURRENT_PREFIX
        self.app.gateway.retry_delays=(0,0,0)
        self.app.configure_rules(self.state,self.caller())
        self.state['agenda']=[]

    def caller(self,transform=None,version=CURRENT_PREFIX):
        return fixture.ReviewFixTests.caller(self,version,transform)

    def decision(self,events=None,mode='wait',speech=''):
        def change(task,out,data):
            if task=='ensemble_role':
                out.update(action={'kind':'wait','args':[]},speech=speech,gesture=None,
                    next_decision={'mode':mode,'events':list(events or [])})
        return change

    def data(self,actor='A'):
        return scheduling.context(self.state,actor,limit_waits=2,explicit_options=True)

    def listener(self,events,actor='A',identity='test_listener'):
        tool={'id':identity,'type':'function','function':{'name':'create_event_listener',
            'arguments':canonical({'description':'留意实际结果','event_ids':events,
                'completion_condition':'','early_end_condition':''})}}
        return event_tools.execute(self.state,actor,tool,'test_call')['wait_event']

    def test_one_different_reply_restores_next_observation(self):
        s=self.state
        self.app.turn(s,'A',self.caller(self.decision(['next_observation'])),0)
        self.assertEqual(s['role_next_observation_wait'],{'A':True})
        wait_lifecycle.resolve(s,'A','cancelled','等待条件已变化。')
        for _ in range(2):
            with self.assertRaises(ContractError) as caught:
                self.app.turn(s,'A',self.caller(self.decision(['next_observation'])),0)
            self.assertEqual(caught.exception.feedback['field'],'next_decision.events')
            self.assertEqual(s['role_next_observation_wait'],{'A':True})
        for _ in range(2):self.app.turn(s,'A',self.caller(self.decision(['phase:conclusion'])),0)
        self.assertFalse(s['role_next_observation_wait']['A'])
        self.app.turn(s,'A',self.caller(self.decision(['next_observation'])),0)
        self.assertEqual(len(s['decisions']),4)
        self.assertTrue(s['role_next_observation_wait']['A'])

    def test_other_targets_can_repeat_and_have_no_silent_continue_limit(self):
        s=self.state;s['role_next_observation_wait']={'A':True}
        s['tracked_events']=[{'id':'custom','creator':'A','status':'active','description':'已有具体事件'}]
        w.apply_choice(s,'A','invite:B');w.apply_choice(s,'B','accept:i1')
        w.apply_choice(s,'C','invite:D')
        data=self.data()
        events=[o['id'] for o in data['waitable_events'] if o['id']!='next_observation']
        self.assertTrue(any(e.startswith('conversation:') for e in events))
        self.assertIn('tracked:custom',events)
        for target in events+['own_activity','own_invitation','proposed_event']:
            for _ in range(2):
                with self.subTest(target=target):
                    choice={'own_activity':'search','own_invitation':'invite:B'}.get(target,'wait')
                    scheduling.validate({'mode':'wait','events':[target]},data,choice,
                        target=='proposed_event',speech='',gesture=None)
        scheduling.validate({'mode':'continue','events':[]},data,'wait',speech='',gesture=None)
        scheduling.validate({'mode':'wait','events':[]},data,'wait',speech='',gesture=None)
        # An event still has to be visible/eligible, even though it has no frequency cap.
        with self.assertRaises(ValueError):
            scheduling.validate({'mode':'wait','events':['tracked:FOREIGN']},data,'wait')

    def test_listener_aliases_and_mixed_targets_share_the_restriction(self):
        alias=self.listener(['next_observation','phase:conclusion'])
        phase=self.listener(['phase:conclusion'],identity='phase_listener')
        self.listener(['next_observation'],actor='B',identity='foreign_listener')
        data=self.data()
        self.assertEqual(data['wait_frequency']['matching_events'],['next_observation',alias])
        plan={'mode':'wait','events':[alias]}
        scheduling.validate(plan,data,'wait')
        scheduling.record_reply(self.state,'A',plan,data,'wait','',None)
        data=self.data()
        self.assertEqual(data['decision_options']['allowed_modes'],['continue','wait'])
        self.assertEqual(data['decision_options']['disallowed_wait_events'],['next_observation',alias])
        for targets in ([alias],['next_observation'],['phase:conclusion','next_observation']):
            with self.subTest(targets=targets),self.assertRaises(ContractError):
                scheduling.validate({'mode':'wait','events':targets},data,'wait',speech='我等结果。')
        scheduling.validate({'mode':'wait','events':[phase]},data,'wait')

    def test_other_actors_timeout_and_restart_preserve_only_own_last_reply(self):
        s=self.state
        self.app.turn(s,'A',self.caller(self.decision(['next_observation'])),0)
        s['watch']['clock']=s['role_waits']['A']['deadline'];scheduling.reconcile(s)
        self.assertEqual(s['wait_results']['A']['status'],'timed_out')
        self.app.turn(s,'B',self.caller(self.decision(['next_observation'])),0)
        s['phase']='paused';self.state=json.loads(canonical(s));self.state['phase']='active'
        self.assertFalse(self.data()['wait_frequency']['next_observation_allowed'])
        self.assertTrue(self.data('C')['wait_frequency']['next_observation_allowed'])
        self.app.turn(self.state,'A',self.caller(self.decision(mode='continue')),0)
        self.assertTrue(self.data()['wait_frequency']['next_observation_allowed'])

    def test_native_tools_preserve_version_and_include_new_aliases(self):
        self.state['role_next_observation_wait']={'A':True};seen=[]
        def tool_then_reply(task,out,data):
            if task!='ensemble_role':return
            seen.append(deepcopy(data['scheduling']))
            if '_tool_messages' not in data:
                out.clear();out['_tool_message']={'role':'assistant','content':None,'tool_calls':[
                    {'id':'native_listener','type':'function','function':{'name':'create_event_listener',
                        'arguments':canonical({'description':'留意新信息','event_ids':['next_observation'],
                            'completion_condition':'','early_end_condition':''})}}]}
            else:self.decision(['phase:conclusion'])(task,out,data)
        self.app.turn(self.state,'A',self.caller(tool_then_reply),0)
        self.assertEqual(len(seen),2)
        for item in seen:
            self.assertEqual(item['wait_frequency']['version'],2)
            self.assertFalse(item['wait_frequency']['next_observation_allowed'])
        self.assertEqual(seen[1]['decision_options']['disallowed_wait_events'],
            ['next_observation','listener:listener-1'])
        self.assertEqual(self.state['role_next_observation_wait'],{'A':False})
        self.assertEqual(len(self.state['decisions']),1)

    def test_listener_registration_alone_does_not_advance_accounting(self):
        self.state['role_next_observation_wait']={'A':True}
        self.listener(['next_observation'])
        self.assertFalse(self.data()['wait_frequency']['next_observation_allowed'])
        self.assertEqual(self.state['role_next_observation_wait'],{'A':True})

    def test_legacy_context_and_accounting_remain_separate(self):
        s=self.state;s['role_wait_history']={'A':[True]}
        self.assertTrue(self.data()['wait_frequency']['next_observation_allowed'])
        old=scheduling.context(s,'A',limit_waits=True,explicit_options=True)
        self.assertEqual(old['wait_frequency'],{'reply_window':3,'maximum_waits':1,
            'wait_allowed':False,'non_wait_replies_required':2})
        with self.assertRaises(ContractError):
            self.app.turn(s,'A',self.caller(self.decision(['phase:conclusion']),'ai-tasks-v118.json'),0)
        self.app.turn(s,'A',self.caller(self.decision(['next_observation'])),0)
        self.assertEqual(s['role_wait_history'],{'A':[True]})
        self.app.turn(s,'A',self.caller(self.decision(mode='continue',speech='我先核对。'),'ai-tasks-v118.json'),0)
        self.assertEqual(s['role_wait_history'],{'A':[True,False]})
        self.assertEqual(s['role_next_observation_wait'],{'A':True})

    def test_retry_commits_once_and_paid_request_is_reused_after_restart(self):
        s=deepcopy(self.state);s['role_next_observation_wait']={'A':True}
        owner=self.app.store.session()['id']
        s=self.app.store.create_game(owner,{'command_id':'observation_create','expected_game_id':None},lambda gid:dict(s,id=gid))
        original=self.provider;sent=[]
        def transport(body):
            response=original(body)
            if 'PALTER_TASK: ensemble_role\n' in body['messages'][0]['content']:
                sent.append(deepcopy(body));out=json.loads(response['choices'][0]['message']['content'])
                out['next_decision']={'mode':'wait','events':['next_observation' if len(sent)==1 else 'phase:conclusion']}
                response['choices'][0]['message']['content']=canonical(out)
            return response
        self.app.gateway.client.transport=transport
        command={'command_id':'observation_retry','expected_revision':s['revision'],'kind':'background'}
        builder=lambda state,call:self.app.turn(state,'A',call,0)
        saved,_=self.app.operate(owner,s['id'],command,builder)
        self.assertEqual(len(sent),2)
        self.assertIn('next_decision.events',canonical(sent[1]))
        self.assertFalse(saved['role_next_observation_wait']['A'])
        self.assertEqual(len(saved['decisions']),1)
        self.app=EnsembleApplication(self.app.store.path,self.app.gateway.client)
        duplicate,_=self.app.operate(owner,s['id'],command,builder)
        self.assertEqual(len(sent),2)
        self.assertEqual(duplicate['role_next_observation_wait'],{'A':False})

    def test_prefix_only_changes_wait_policy_for_both_perspectives(self):
        old=deepcopy(self.app.gateway.versions['ai-tasks-v118.json'])
        new=deepcopy(self.app.gateway.versions['ai-tasks-v119.json'])
        self.assertEqual(new['ensemble_role'].pop('wait_frequency_version'),2)
        self.assertEqual(old['ensemble_role'].pop('wait_frequency_version'),1)
        for role in (None,'concealment'):
            a=old['ensemble_role'] if role is None else old['ensemble_role']['perspectives'][role]
            b=new['ensemble_role'] if role is None else new['ensemble_role']['perspectives'][role]
            old_lines=a.pop('instruction').splitlines();new_lines=b.pop('instruction').splitlines()
            self.assertEqual(len(old_lines),len(new_lines))
            changes=[(x,y) for x,y in zip(old_lines,new_lines) if x!=y]
            self.assertEqual(len(changes),2)
            self.assertTrue(changes[0][1].startswith('等待频率：仅next_observation'))
            self.assertTrue(changes[1][1].startswith('本轮调度：'))
        self.assertEqual(old,new)


if __name__=='__main__':unittest.main()
