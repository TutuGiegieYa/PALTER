"""This action's completion, immediate or ongoing, with no self-polling wait."""
from copy import deepcopy
import unittest

from palter import ensemble_world as w, role_schedule as schedule
from palter.model_contracts import ContractError
from tests import test_ensemble_review as fixture

NEW='ai-tasks-v121.json'


class OwnActionTests(unittest.TestCase):
    def setUp(self):
        self.f=fixture.ReviewFixTests();self.f.setUp();self.addCleanup(self.f.doCleanups)
        self.app,self.s=self.f.app,self.f.state
        self.app.gateway.current_version=NEW
        self.app.configure_rules(self.s,self.f.caller(NEW));self.s['agenda']=[]

    def caller(self,choice='inspect:c1',speech='',gesture=None,events=None,version=NEW):
        kind,*args=choice.split(':')
        def change(task,out,data):
            if task=='ensemble_role':
                out.update(action={'kind':kind,'args':args},speech=speech,gesture=gesture,question_to=None,
                           next_decision={'mode':'wait','events':events or ['own_activity']})
        return self.f.caller(version,change)

    def test_immediate_inspection_records_result_then_queues_once_for_both_versions(self):
        for version in ('ai-tasks-v120.json',NEW):
            s=deepcopy(self.s);self.f.inputs=[]
            self.app.turn(s,'A',self.caller(version=version),0)
            inspected=next(e for e in s['events'] if e['kind']=='inspect')
            self.assertIn('c1',s['known']['A']);self.assertFalse(schedule.waiting(s,'A'))
            self.assertTrue(any(o['event_id']==inspected['id'] for o in s['observations']['A']))
            queued=[q for q in s['agenda'] if q['actor']=='A']
            self.assertEqual(len(queued),1);self.assertEqual(queued[0]['source'],inspected['id'])
            count=len(s['events'])
            for _ in range(5):schedule.reconcile(s)
            self.assertEqual(len(s['events']),count)
            self.assertEqual(sum(q['actor']=='A' for q in s['agenda']),1)
            self.assertEqual([task for task,_ in self.f.inputs],['ensemble_role'])
            context=self.f.inputs[0][1]['scheduling']
            self.assertEqual(bool(context.get('own_action_completion')),version==NEW)

    def test_new_context_explains_available_immediate_action_completion(self):
        data=schedule.context(self.s,'A',own_action_completion=True)
        option=next(o for o in data['after_action_events'] if o['id']=='own_activity')
        self.assertIn('inspect',option['actions']);self.assertIn('search',option['actions'])
        self.assertEqual(option['requires_outward_response_for'],['wait'])

    def test_running_action_waits_for_its_exact_terminal_result(self):
        self.s['activities'].append({'id':'old-work','actor':'A','status':'completed'})
        self.app.turn(self.s,'A',self.caller('search'),0)
        task=w.running(self.s,'A');self.assertIsNotNone(task)
        self.assertEqual(self.s['role_waits']['A']['events'],['activity:'+task['id']])
        self.assertFalse(any(q['actor']=='A' for q in self.s['agenda']))
        w.advance(self.s);schedule.reconcile(self.s)
        self.assertEqual(task['status'],'completed');self.assertFalse(schedule.waiting(self.s,'A'))
        self.assertEqual(sum(q['actor']=='A' for q in self.s['agenda']),1)

    def test_outward_reply_does_not_attach_to_an_older_still_running_activity(self):
        w.apply_choice(self.s,'A','search');old=w.running(self.s,'A')
        self.app.turn(self.s,'A',self.caller('wait',speech='我先记录目前看到的内容。'),0)
        self.assertEqual(old['status'],'running');self.assertFalse(schedule.waiting(self.s,'A'))
        source=next(q['source'] for q in self.s['agenda'] if q['actor']=='A')
        self.assertEqual(next(e['kind'] for e in self.s['events'] if e['id']==source),'testimony')

    def test_gesture_has_completion_but_empty_stationary_wait_does_not(self):
        self.app.turn(self.s,'A',self.caller('wait',gesture='点头'),0)
        self.assertFalse(schedule.waiting(self.s,'A'))
        data=schedule.context(self.s,'A',own_action_completion=True)
        with self.assertRaises(ContractError) as caught:
            schedule.validate({'mode':'wait','events':['own_activity']},data,'wait',speech='',gesture=None)
        receipt=caught.exception.feedback
        self.assertEqual(receipt['field'],'next_decision.events')
        self.assertEqual(receipt['invalid_events'],['own_activity'])
        self.assertNotIn('own_activity',receipt['allowed_events'])

    def test_completion_before_subscription_or_other_or_targets_is_not_lost(self):
        data=schedule.context(self.s,'A');event=w.apply_choice(self.s,'A','search')
        w.advance(self.s);self.s['agenda']=[]
        schedule.commit(self.s,'A',{'mode':'wait','events':['phase:conclusion','own_activity']},data,action_event=event)
        self.assertFalse(schedule.waiting(self.s,'A'));self.assertEqual(sum(q['actor']=='A' for q in self.s['agenda']),1)

    def test_missing_current_event_never_binds_a_historical_task(self):
        self.s['activities'].append({'id':'old-work','actor':'A','status':'completed'})
        with self.assertRaises(ValueError):
            schedule.commit(self.s,'A',{'mode':'wait','events':['own_activity']},schedule.context(self.s,'A'))
        self.assertFalse(schedule.waiting(self.s,'A'));self.assertFalse(self.s['agenda'])

    def test_failure_and_cancellation_end_wait_with_original_outcome(self):
        for outcome in ('failed','cancelled'):
            s=deepcopy(self.s);self.app.turn(s,'A',self.caller('search'),0);task=w.running(s,'A')
            if outcome=='failed':s['locations']['A']='r2';w.advance(s)
            else:w.apply_choice(s,'A','cancel_work')
            schedule.reconcile(s)
            self.assertEqual(task['status'],outcome);self.assertFalse(schedule.waiting(s,'A'))
            self.assertTrue(any(e['kind']=='action_'+outcome and e['facts']['started_by']==task['id'] for e in s['events']))

    def test_immediate_or_wait_keeps_recipient_scope_and_other_targets_validated(self):
        data=schedule.context(self.s,'A')
        plan={'mode':'wait','events':['own_activity','phase:conclusion']}
        schedule.validate(plan,data,'inspect:c1')
        with self.assertRaises(ContractError) as caught:
            schedule.validate({'mode':'wait','events':['own_activity','activity:FOREIGN']},data,'inspect:c1')
        self.assertEqual(caught.exception.feedback['invalid_events'],['activity:FOREIGN'])
        self.assertNotIn('activity:FOREIGN',caught.exception.feedback['allowed_events'])


if __name__=='__main__':unittest.main()
