"""New request terms must not alter scheduling, retries or historical requests."""
from copy import deepcopy
import json
import unittest

from palter import ensemble_world as w, role_schedule, scheduling_terms
from palter.ensemble import EnsembleApplication
from palter.storage import canonical
from tests import test_ensemble_review as fixture

VERSION='ai-tasks-v125.json'


class SchedulingTermsTests(unittest.TestCase):
    def setUp(self):
        self.f=fixture.ReviewFixTests();self.f.setUp();self.addCleanup(self.f.doCleanups)
        self.app,self.s=self.f.app,self.f.state
        self.app.gateway.current_version=VERSION;self.app.gateway.retry_delays=(0,0,0)
        self.app.configure_rules(self.s,self.f.caller(VERSION));self.s['agenda']=[]

    def context(self):
        return role_schedule.context(self.s,'A',limit_waits=2,explicit_options=True,
            own_action_completion=True,message_wait_guard=True)

    def park_others(self):
        for actor in 'BCD':
            role_schedule.commit(self.s,actor,{'mode':'wait','events':['next_observation']},
                role_schedule.context(self.s,actor))

    def payload(self,data,version=VERSION):
        return self.app.gateway.payload('ensemble_role',w.baseline(self.s,'A'),data,version)[0]

    def unpack(self,body):
        return json.loads(next(m['content'] for m in body['messages'] if m['role']=='user'))

    def good(self,out):
        out.update(action={'kind':'wait','args':[]},speech='我先核对已有材料。',gesture=None,
            question_to=None,memory_update=None,progress={'kind':'none','sources':[]},relationships=[],
            next_decision={'mode':'continue','events':[]})
        for key in ('belief_update','strategy_update'):
            if key in out:out[key]=None

    def test_independent_checks_keep_all_four_permission_combinations(self):
        original=deepcopy(self.s)
        for last_available in (False,True):
            for previous_observation_wait in (False,True):
                with self.subTest(last_available=last_available,previous=previous_observation_wait):
                    self.s=deepcopy(original)
                    if last_available:self.park_others()
                    self.s['role_next_observation_wait']={'A':previous_observation_wait}
                    data={'scheduling':self.context()};before=deepcopy(data)
                    old=self.unpack(self.payload(data,'ai-tasks-v124.json'))['scheduling']
                    new=self.unpack(self.payload(data))['scheduling']
                    self.assertEqual(data,before)
                    self.assertEqual(new['event_candidates'],old['waitable_events'])
                    self.assertEqual(new['wait_frequency']['passes_consecutive_wait_check'],not previous_observation_wait)
                    self.assertEqual(new['message_wait_guard']['message_only_subscription_allowed'],not last_available)
                    self.assertEqual(new['decision_options']['frequency_blocked_event_ids'],old['decision_options']['disallowed_wait_events'])
                    self.assertNotIn('next_observation_allowed',canonical(new))
                    for events,valid in ((['next_observation'],not last_available and not previous_observation_wait),
                            (['next_observation','phase:conclusion'],not previous_observation_wait),
                            (['phase:conclusion'],True),([],not last_available),(['own_activity'],True)):
                        plan={'mode':'wait','events':events}
                        if valid:role_schedule.validate(plan,data['scheduling'],'move:r2')
                        else:
                            with self.assertRaises(ValueError):role_schedule.validate(plan,data['scheduling'],'move:r2')

    def test_error_terms_match_menu_and_keep_other_feedback_exact(self):
        self.park_others();context=self.context()
        with self.assertRaises(ValueError) as caught:
            role_schedule.validate({'mode':'wait','events':['next_observation']},context,'wait')
        error=caught.exception.feedback
        source={'field':'belief_update.testimony_ids','actual':'next_observation_allowed','instruction':'Keep my exact source.'}
        error.update(role_recovery_version=1,unresolved_issues=[deepcopy(error),source])
        data={'scheduling':context,'validation_feedback':error};before=deepcopy(data)
        sent=self.unpack(self.payload(data))['validation_feedback']
        self.assertEqual(data,before)
        self.assertFalse(sent['message_only_subscription_allowed'])
        self.assertFalse(sent['unresolved_issues'][0]['message_only_subscription_allowed'])
        self.assertEqual(sent['unresolved_issues'][1],source)
        self.assertEqual(sent['actual_events'],['next_observation'])

    def test_frequency_error_uses_frequency_specific_field(self):
        self.s['role_next_observation_wait']={'A':True};context=self.context()
        with self.assertRaises(ValueError) as caught:
            role_schedule.validate({'mode':'wait','events':['next_observation']},context,'wait')
        sent=self.unpack(self.payload({'scheduling':context,'validation_feedback':caught.exception.feedback}))
        feedback=sent['validation_feedback']
        self.assertEqual(feedback['frequency_blocked_event_ids'],['next_observation'])
        self.assertIn('frequency_blocked_event_ids',feedback['instruction'])
        self.assertNotIn('disallowed_wait_events',canonical(feedback))

    def test_native_listener_continuation_gets_updated_candidates_and_conditions(self):
        self.park_others();sent=[]
        def transform(task,out,data):
            if task!='ensemble_role':return
            sent.append(self.payload(data))
            if '_tool_messages' not in data:
                out.clear();out['_tool_message']={'role':'assistant','content':None,'tool_calls':[
                    {'id':'listener','type':'function','function':{'name':'create_event_listener',
                        'arguments':canonical({'description':'留意新信息','event_ids':['next_observation'],
                            'completion_condition':'','early_end_condition':''})}}]}
            else:
                self.good(out)
                self.assertEqual(sent[-1]['messages'][-len(data['_tool_messages']):],data['_tool_messages'])
        self.app.turn(self.s,'A',self.f.caller(VERSION,transform),0)
        self.assertEqual(len(sent),2)
        for body in sent:
            schedule=self.unpack(body)['scheduling']
            self.assertFalse(schedule['message_wait_guard']['message_only_subscription_allowed'])
        schedule=self.unpack(sent[-1])['scheduling']
        self.assertIn('listener:listener-1',[e['id'] for e in schedule['event_candidates']])
        self.assertEqual(schedule['message_wait_guard']['message_only_events'],['next_observation','listener:listener-1'])

    def test_retry_and_restart_reuse_paid_new_format_without_duplicate_action(self):
        self.park_others();owner=self.app.store.session()['id']
        game=self.app.store.create_game(owner,{'command_id':'terms_create','expected_game_id':None},lambda gid:dict(self.s,id=gid))
        original=self.f.provider;sent=[]
        def transport(body):
            response=original(body)
            if 'PALTER_TASK: ensemble_role\n' in body['messages'][0]['content']:
                sent.append(deepcopy(body));out=json.loads(response['choices'][0]['message']['content']);self.good(out)
                if len(sent)==1:out['next_decision']={'mode':'wait','events':['next_observation']}
                response['choices'][0]['message']['content']=canonical(out)
            return response
        self.app.gateway.client.transport=transport
        command={'command_id':'terms_retry','expected_revision':game['revision'],'kind':'background'}
        builder=lambda state,call:self.app.turn(state,'A',call,0)
        saved,_=self.app.operate(owner,game['id'],command,builder)
        self.assertEqual(len(sent),2);self.assertEqual(len(saved['decisions']),1)
        self.assertFalse(self.unpack(sent[1])['validation_feedback']['message_only_subscription_allowed'])
        self.app=EnsembleApplication(self.app.store.path,self.app.gateway.client)
        duplicate,_=self.app.operate(owner,game['id'],command,builder)
        self.assertEqual(len(sent),2);self.assertEqual(len(duplicate['decisions']),1)

    def test_historical_payload_keeps_old_names(self):
        data={'scheduling':self.context()};before=deepcopy(data)
        first=canonical(self.payload(data,'ai-tasks-v124.json'))
        self.payload(data)
        self.assertEqual(first,canonical(self.payload(data,'ai-tasks-v124.json')))
        self.assertEqual(data,before)
        self.assertIn('next_observation_allowed',first);self.assertNotIn('passes_consecutive_wait_check',first)

    def test_both_perspectives_and_listener_schema_explain_scopes(self):
        spec=self.app.gateway.versions[VERSION]['ensemble_role']
        for item in (spec,spec['perspectives']['concealment']):
            text=item['instruction']
            self.assertIn('passes_consecutive_wait_check只表示',text)
            self.assertIn('true不等于本轮获准等待',text)
            self.assertIn('message_only_subscription_allowed=false',text)
            self.assertNotIn('next_observation_allowed',text)
            self.assertNotIn('disallowed_wait_events',text)
        tool=next(t for t in spec['tools'] if t['function']['name']=='create_event_listener')
        self.assertIn('scheduling.event_candidates',tool['function']['parameters']['properties']['event_ids']['description'])

    def test_new_prefix_preserves_all_other_tasks_model_settings_and_output_schema(self):
        old=deepcopy(self.app.gateway.versions['ai-tasks-v124.json']);new=deepcopy(self.app.gateway.versions[VERSION])
        self.assertEqual(new['ensemble_role'].pop('scheduling_terms_version'),1)
        for task in (old,new):
            role=task['ensemble_role'];role.pop('instruction');role['perspectives']['concealment'].pop('instruction')
            tool=next(t for t in role['tools'] if t['function']['name']=='create_event_listener')
            tool['function']['parameters']['properties']['event_ids'].pop('description')
        self.assertEqual(old,new)


if __name__=='__main__':unittest.main()
