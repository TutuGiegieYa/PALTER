"""DM-owned free-form conditions cannot grant knowledge or execute effects."""
from copy import deepcopy
import unittest

from palter import ensemble_world as w, role_events, role_schedule as scheduling, spectator
from palter.storage import canonical
from tests import test_ensemble_review as fixture


class RoleEventTests(unittest.TestCase):
    def setUp(self):
        fixture.ReviewFixTests.setUp(self)
        self.app.configure_rules(self.state,self.caller());self.state['agenda']=[]

    def caller(self,transform=None,version=None):return fixture.ReviewFixTests.caller(self,version or self.app.gateway.current_version,transform)

    def propose(self,actor='C',speech=''):
        proposal={'description':'等私聊结束并听到公开的时间说明','completion_condition':'私聊已结束，而且有人向我说明记录中的时间差','early_end_condition':'当事人明确拒绝继续说明'}
        def generate(task,out,data):
            if task=='ensemble_role':out.update(speech=speech,event_request=proposal,next_decision={'mode':'wait','events':['proposed_event']})
        start=len(self.state['events']);self.app.turn(self.state,actor,self.caller(generate),0)
        return self.state['tracked_events'][-1],start

    def judge(self,status='active',sources=(),reason='尚待收到后续信息。',start=None):
        def decisions(task,out,data):
            if task=='ensemble_dm':
                out['event_decisions']=[{'id':e['id'],'status':status,'reason':reason,'progress':'按实际收到的信息跟踪。','source_ids':list(sources)} for e in data['tracked_events']]
        self.app.adjudicate_ensemble(self.state,len(self.state['events']) if start is None else start,self.caller(decisions))

    def test_proposal_approval_uses_dm_without_waking_creator_or_polling_again(self):
        s=self.state;event,start=self.propose();self.assertEqual(event['status'],'pending');self.assertTrue(scheduling.waiting(s,'C'))
        self.judge(start=start);self.assertEqual(event['status'],'active');self.assertTrue(scheduling.waiting(s,'C'))
        self.assertFalse(any(q['actor']=='C' for q in s['agenda']));calls=len(self.provider.calls)
        for _ in range(10):self.app.adjudicate_ensemble(s,len(s['events']),self.caller())
        self.assertEqual(len(self.provider.calls),calls);self.assertEqual(calls,2)
        data=next(d for t,d in self.inputs if t=='ensemble_dm');self.assertEqual(data['utterances'],[])

    def test_judgment_merges_with_existing_speech_dm_call(self):
        event,start=self.propose(speech='我先等他们把时间问题说清楚。');self.judge(start=start)
        self.assertEqual(sum(t=='ensemble_dm' for t,_,_ in self.provider.calls),1)
        data=next(d for t,d in self.inputs if t=='ensemble_dm');self.assertEqual(len(data['utterances']),1)
        self.assertEqual(data['tracked_events'][0]['id'],event['id'])

    def test_completion_requires_received_support_and_delivers_only_to_creator(self):
        s=self.state;event,start=self.propose();self.judge(start=start)
        e=w.speak(s,'D','时间差来自校时，原先的记录快了十七分钟。')
        source=next(o['id'] for o in s['observations']['C'] if o['event_id']==e['id'])
        self.judge('completed',[source],'已收到所等待的公开说明。')
        self.assertEqual(event['status'],'completed');self.assertFalse(scheduling.waiting(s,'C'))
        self.assertEqual(sum(q['actor']=='C' for q in s['agenda']),1)
        record=s['events'][-1];self.assertEqual(record['kind'],'tracking_resolved')
        self.assertTrue(any(o['event_id']==record['id'] for o in s['observations']['C']))
        for a in 'ABD':self.assertFalse(any(o['event_id']==record['id'] for o in s['observations'][a]))

    def test_private_speech_is_not_valid_completion_support_for_an_outside_creator(self):
        s=self.state;event,start=self.propose();self.judge(start=start)
        w.apply_choice(s,'A','invite:B');w.apply_choice(s,'B','accept:i1')
        e=w.speak(s,'A','UNHEARD_CUSTOM_EVENT_CANARY','B')
        source=next(o['id'] for o in s['observations']['A'] if o['event_id']==e['id'])
        records,contexts,allowed=role_events.package(s,'public')
        self.assertNotIn('UNHEARD_CUSTOM_EVENT_CANARY',canonical(contexts));self.assertNotIn(source,allowed['C'])
        for forbidden in (source,e['id']):
            with self.assertRaisesRegex(ValueError,'source'):
                role_events.validate_decisions({'event_decisions':[{'id':event['id'],'status':'completed','reason':'x','progress':'','source_ids':[forbidden]}]},records,allowed)

    def test_rejection_and_early_end_are_distinct_from_success_and_preserve_world(self):
        original=deepcopy(self.state)
        for status in ('rejected','cancelled'):
            self.state=deepcopy(original);s=self.state;event,start=self.propose()
            truth=canonical(s['case']);objects=canonical(s['objects'])
            if status=='cancelled':
                self.judge(start=start);w.speak(s,'D','我明确拒绝继续说明这件事。')
            self.judge(status,reason='该事项不能按提出的条件继续。',start=start if status=='rejected' else None)
            self.assertEqual(event['status'],status);self.assertFalse(scheduling.waiting(s,'C'))
            self.assertNotIn('条件已达成',s['observations']['C'][-1]['text'])
            self.assertEqual(canonical(s['case']),truth);self.assertEqual(canonical(s['objects']),objects)

    def test_owner_can_cancel_active_tracker_but_other_roles_cannot(self):
        s=self.state;event,start=self.propose();self.judge(start=start)
        with self.assertRaises(ValueError):role_events.validate({'cancel_events':[event['id']]},role_events.role_context(s,'D'))
        role_events.validate({'cancel_events':[event['id']]},role_events.role_context(s,'C'))
        role_events.request(s,'C',{'cancel_events':[event['id']]});self.assertIn('public',role_events.scopes_due(s))
        self.judge('cancelled',reason='我已不再等待这件事。');self.assertEqual(event['status'],'cancelled')

    def test_event_state_routes_to_owner_current_private_dm_without_exposing_to_other_roles(self):
        s=self.state;event,start=self.propose();self.judge(start=start)
        w.apply_choice(s,'C','invite:D');w.apply_choice(s,'D','accept:i1')
        e=w.speak(s,'D','PRIVATE_EVENT_CONTEXT_CANARY','C')
        self.inputs=[];self.app.adjudicate_ensemble(s,s['events'].index(e),self.caller())
        data=next(d for t,d in self.inputs if t=='ensemble_dm')
        self.assertIn('PRIVATE_EVENT_CONTEXT_CANARY',canonical(data['event_recipient_contexts']['C']))
        self.assertEqual(role_events.package(s,'public')[0],[])
        self.assertNotIn(event['description'],canonical(w.context(s,'D')))
        self.assertNotIn(event['description'],canonical(role_events.role_context(s,'D')))

    def test_no_changed_receipts_no_dm_call_even_when_all_models_wait(self):
        s=self.state;event,start=self.propose();self.judge(start=start)
        for a in 'ABD':
            s['agenda']=[q for q in s['agenda'] if q['actor']!=a]
            scheduling.commit(s,a,{'mode':'wait','events':[]},scheduling.context(s,a))
        count=len(self.provider.calls);spectator.background(self.app,s,self.caller())
        self.assertEqual(len(self.provider.calls),count);self.assertEqual(s['watch']['pause_reason'],'waiting')
        self.assertEqual(event['status'],'active')

    def test_prior_progress_and_source_are_retained_without_mutating_condition(self):
        s=self.state;event,start=self.propose();condition=event['completion_condition']
        self.judge(start=start);e=w.speak(s,'D','他们已经结束私聊，但还没有说明时间。')
        source=next(o['id'] for o in s['observations']['C'] if o['event_id']==e['id'])
        self.judge('active',[source],'只收到部分进展，仍需要说明。')
        for n in range(30):w.note(s,'C',w.emit(s,'observation'),str(n))
        records,contexts,allowed=role_events.package(s,'public')
        self.assertIn(source,allowed['C']);self.assertEqual(records[0]['source_ids'],[source])
        self.assertEqual(event['completion_condition'],condition);self.assertEqual(event['status'],'active')

    def test_received_event_id_is_a_valid_alias_and_rehydrates_only_own_record(self):
        s=self.state;event,start=self.propose();self.judge(start=start)
        received=w.speak(s,'D','我刚公开核对了时差。')
        self.judge('active',[received['id']],'已收到说明，还需要其他条件。')
        for n in range(30):w.note(s,'C',w.emit(s,'observation'),str(n))
        records,contexts,allowed=role_events.package(s,'public')
        self.assertIn(received['id'],allowed['C'])
        self.assertTrue(any(o['event_id']==received['id'] for o in contexts['C']['received_records']))

    def test_invalid_dms_cannot_complete_without_sources_or_reopen_terminal_events(self):
        s=self.state;event,start=self.propose();self.judge(start=start)
        records,contexts,allowed=role_events.package(s,'public')
        for status in ('completed','rejected','invented'):
            with self.subTest(status=status),self.assertRaises(ValueError):
                role_events.validate_decisions({'event_decisions':[{'id':event['id'],'status':status,'reason':'x','progress':'','source_ids':[]}]},records,allowed)
        role_events.request(s,'C',{'cancel_events':[event['id']]})
        self.judge('cancelled',reason='提前结束。');self.assertEqual(role_events.package(s,'public')[0],[])

    def test_capacity_and_proposed_event_reference_are_validated(self):
        s=self.state
        for _ in range(2):self.propose()
        data=role_events.role_context(s,'C');self.assertFalse(data['can_propose'])
        with self.assertRaises(ValueError):role_events.validate({'event_request':{'description':'x','completion_condition':'y','early_end_condition':''}},data)
        with self.assertRaises(ValueError):scheduling.validate({'mode':'wait','events':['proposed_event']},scheduling.context(s,'D'),'wait')

    def test_new_custom_wait_cannot_accidentally_subscribe_to_only_a_subcondition(self):
        data=scheduling.context(self.state,'C')
        with self.assertRaisesRegex(ValueError,'reference proposal'):
            scheduling.validate({'mode':'wait','events':['next_observation']},data,'wait',has_proposal=True)
        scheduling.validate({'mode':'wait','events':['proposed_event']},data,'wait',has_proposal=True)
        scheduling.validate({'mode':'continue','events':[]},data,'wait',has_proposal=True)

    def test_pinned_v50_dm_has_no_new_event_contract(self):
        s=self.state;e=w.speak(s,'D','我会继续检查材料。')
        self.app.adjudicate_ensemble(s,s['events'].index(e),self.caller(version='ai-tasks-v50.json'))
        data=next(d for t,d in self.inputs if t=='ensemble_dm')
        self.assertNotIn('tracked_events',data);self.assertNotIn('event_recipient_contexts',data)


if __name__=='__main__':unittest.main()
