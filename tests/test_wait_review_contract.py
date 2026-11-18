"""Completed-purpose compatibility, typed wait reviews and recoverable schema errors."""
from copy import deepcopy
import json
from pathlib import Path
import unittest

from palter import ensemble_world as w, role_events, role_schedule as schedule, wait_lifecycle as waits
from palter.storage import canonical
from tests import test_runtime_integrity as fixtures

VERSION='ai-tasks-v89.json'


class WaitReviewContractTests(unittest.TestCase):
    def setUp(self):
        self.f=fixtures.RuntimeIntegrityTests();self.f.setUp();self.addCleanup(self.f.doCleanups)
        self.app,self.s=self.f.app,self.f.s
        self.app.gateway.current_version=VERSION;self.app.configure_rules(self.s,self.f.f.caller(VERSION))

    def wait(self,actor='A',targets=('next_observation',),reason='等待检查结果。'):
        self.s['agenda']=[q for q in self.s['agenda'] if q['actor']!=actor]
        plan={'mode':'wait','events':list(targets),'wait_reason':reason,'timeout_seconds':60}
        data=schedule.context(self.s,actor);schedule.validate(plan,data,'wait');schedule.commit(self.s,actor,plan,data)
        return self.s['role_waits'][actor]

    def inspect_and_wait(self):
        w.apply_choice(self.s,'A','inspect:c1');return self.wait()

    def decision(self,record,status='completed',sources=None):
        return {'id':record['id'],'status':status,'reason':'已经收到检查结果，无需继续等这份结果。','progress':'检查记录已收到。',
                'source_ids':sources if sources is not None else ['c1'],
                'basis':{'kind':'received_condition','workflow_stage':None}}

    def test_completed_purpose_ends_subscription_once_without_completing_work(self):
        w.apply_choice(self.s,'B','search');work=deepcopy(self.s['activities'])
        self.inspect_and_wait();records,_,allowed=role_events.package(self.s,'public');item=self.decision(records[0])
        original=deepcopy(item);role_events.validate_decisions({'event_decisions':[item]},records,allowed)
        role_events.apply(self.s,[item],'fixture_dm')
        self.assertEqual(item,original);self.assertNotIn('A',self.s['role_waits'])
        r=self.s['wait_results']['A'];self.assertEqual(r['status'],'cancelled')
        self.assertEqual(r['resolution_kind'],'purpose_satisfied');self.assertEqual(r['reported_status'],'completed')
        self.assertEqual(r['source_ids'],['c1']);self.assertEqual(self.s['activities'],work)
        self.assertFalse(waits.apply_review(self.s,item,'fixture_repeat'))
        self.assertEqual(sum(e['kind']=='wait_resolved' for e in self.s['events']),1)
        self.assertEqual(sum(q['actor']=='A' for q in self.s['agenda']),1)
        self.assertFalse(any(e['kind']=='action_completed' for e in self.s['events']))

    def test_new_records_expose_status_contract_and_exact_registration_boundary(self):
        wait=self.inspect_and_wait();records,contexts,_=role_events.package(self.s,'public');record=records[0]
        self.assertEqual(record['record_type'],'wait_validity');self.assertEqual(record['allowed_statuses'],['active','cancelled'])
        boundary=self.s['observations']['A'][wait['after_observation']-1]['id']
        self.assertEqual(record['wait_context']['started_after_observation'],boundary)
        self.assertEqual(record['wait_context']['fixed_completion_owner'],'engine')
        self.assertIn(boundary,{r['id'] for r in contexts['A']['received_records']})
        self.assertNotIn('B_PRIVATE_SECRET_CANARY',canonical(contexts['A']))

    def test_v88_wait_completion_compatibility_does_not_change_its_request_fields(self):
        self.s.pop('event_contract_version');self.inspect_and_wait()
        records,_,allowed=role_events.package(self.s,'public')
        self.assertNotIn('allowed_statuses',records[0]);self.assertNotIn('wait_context',records[0])
        role_events.validate_decisions({'event_decisions':[self.decision(records[0])]},records,allowed)
        self.s.pop('event_basis_version');records,_,allowed=role_events.package(self.s,'public')
        with self.assertRaises(role_events.EventDecisionError):
            role_events.validate_decisions({'event_decisions':[self.decision(records[0])]},records,allowed)

    def test_compatibility_requires_scoped_support_and_cannot_override_workflow(self):
        self.inspect_and_wait();records,_,allowed=role_events.package(self.s,'public')
        for sources in ([],['B-o000001'],['UNKNOWN_SOURCE_CANARY']):
            with self.subTest(sources=sources),self.assertRaises(role_events.EventDecisionError) as error:
                role_events.validate_decisions({'event_decisions':[self.decision(records[0],sources=sources)]},records,allowed)
            self.assertNotIn('UNKNOWN_SOURCE_CANARY',canonical(error.exception.feedback))
        item=self.decision(records[0]);item['basis']={'kind':'workflow_transition','workflow_stage':'conclusion'}
        with self.assertRaises(role_events.DecisionBasisError):role_events.validate_decisions({'event_decisions':[item]},records,allowed)
        self.assertIn('A',self.s['role_waits'])

    def test_fixed_wait_is_not_a_dm_validity_record_and_cannot_be_resolved_by_dm(self):
        w.apply_choice(self.s,'B','invite:C');w.apply_choice(self.s,'C','accept:i1');chat=next(iter(self.s['chats'].values()))
        wait=self.wait(targets=['conversation:'+chat['id']]);before=deepcopy(chat)
        self.assertEqual(role_events.package(self.s,'public')[0],[])
        self.assertFalse(waits.apply_review(self.s,self.decision(wait),'fixture_dm'))
        self.assertEqual(chat,before);self.assertIn('A',self.s['role_waits'])
        w.apply_choice(self.s,'B','end_private');schedule.reconcile(self.s)
        self.assertNotIn('A',self.s['role_waits']);self.assertEqual(chat['status'],'closed')

    def test_custom_completion_stays_custom_completion_in_a_mixed_batch(self):
        self.inspect_and_wait()
        role_events.request(self.s,'A',{'event_request':{'description':'确认已取得记录','completion_condition':'我实际取得最后一次即时回应记录。','early_end_condition':''}})
        records,_,allowed=role_events.package(self.s,'public')
        self.assertEqual(len(records),2)
        decisions=[self.decision(e) for e in records]
        before=deepcopy(self.s)
        for batch in (decisions,list(reversed(decisions))):
            self.s=deepcopy(before)
            role_events.validate_decisions({'event_decisions':batch},records,allowed);role_events.apply(self.s,batch,'fixture_dm')
            self.assertEqual(self.s['tracked_events'][0]['status'],'completed')
            self.assertNotIn('A',self.s['role_waits'])
            self.assertEqual(sum(q['actor']=='A' for q in self.s['agenda']),1)
            self.assertLessEqual(sum(e['kind']=='wait_resolved' for e in self.s['events']),1)
            self.assertEqual(sum(e['kind']=='tracking_resolved' for e in self.s['events']),1)

    def test_count_identity_and_status_failures_supply_bounded_contract_feedback(self):
        self.inspect_and_wait();records,_,allowed=role_events.package(self.s,'public');good=self.decision(records[0],'active')
        for items in ([],[good,good],[dict(good,id='UNKNOWN_SOURCE_CANARY')],[dict(good,status='rejected')],[None]):
            with self.subTest(items=items),self.assertRaises(role_events.EventDecisionError) as error:
                role_events.validate_decisions({'event_decisions':items},records,allowed)
            feedback=error.exception.feedback
            self.assertEqual(feedback['code'],'event_decision_contract')
            self.assertEqual(feedback['expected_records'][0]['allowed_statuses'],['active','cancelled'])
            self.assertNotIn('UNKNOWN_SOURCE_CANARY',canonical(feedback));self.assertLess(len(canonical(feedback)),1500)

    def test_invalid_wait_status_is_corrected_and_paid_reply_survives_recovery(self):
        self.inspect_and_wait();self.s['watch']['budget_usd']=1;self.app.gateway.retry_delays=(0,0,0)
        owner=self.app.store.session()['id']
        def factory(gid):
            s=deepcopy(self.s);s['id']=gid;return s
        s=self.app.store.create_game(owner,{'command_id':'create_fixture','expected_game_id':None},factory)
        provider=self.app.gateway.client.transport;requests=[]
        def transport(payload):
            requests.append(deepcopy(payload));response=provider(payload);data=json.loads(payload['messages'][-1]['content'])
            out=json.loads(response['choices'][0]['message']['content'])
            if 'validation_feedback' not in data:out['event_decisions'][0]['status']='rejected'
            else:
                self.assertEqual(data['validation_feedback']['code'],'event_decision_contract')
                self.assertEqual(data['validation_feedback']['expected_records'][0]['allowed_statuses'],['active','cancelled'])
            response['choices'][0]['message']['content']=json.dumps(out,ensure_ascii=False);return response
        self.app.gateway.client.transport=transport;interrupt=True
        def work(state,call):
            self.app.adjudicate_ensemble(state,len(state['events']),call)
            if interrupt:raise RuntimeError('fixture interruption after paid DM')
        command={'command_id':'verify_fixture','expected_revision':0,'kind':'probe'}
        with self.assertRaises(RuntimeError):self.app.operate(owner,s['id'],command,work)
        self.assertEqual(len(requests),2)
        with self.app.store.transaction(False) as con:
            paid=dict(con.execute("SELECT * FROM ai_calls WHERE status='completed'").fetchone())
            failed=dict(con.execute("SELECT * FROM ai_calls WHERE status='failed'").fetchone())
        self.assertEqual(json.loads(failed['validation_feedback'])['code'],'event_decision_contract')
        self.assertEqual(json.loads(paid['request_feedback'])['code'],'event_decision_contract')
        interrupt=False;state,_=self.app.operate(owner,s['id'],command,work)
        self.assertEqual(len(requests),2);self.assertIn('A',state['role_waits'])
        with self.app.store.transaction(False) as con:self.assertEqual(dict(con.execute('SELECT * FROM ai_calls WHERE id=?',(paid['id'],)).fetchone()),paid)

    def test_v89_guidance_distinguishes_waits_and_stays_flash_without_thinking(self):
        root=Path('palter/prefixes');spec=json.loads((root/VERSION).read_text())
        self.assertIn('Read record_type and allowed_statuses FIRST',spec['ensemble_dm']['instruction'])
        self.assertIn('including when the stated purpose is already satisfied',spec['ensemble_dm']['instruction'])
        for task in spec:
            payload,_=self.app.gateway.payload(task,None,{},VERSION)
            self.assertEqual(payload['thinking'],{'type':'disabled'});self.assertNotIn('reasoning_effort',payload)
            self.assertEqual(payload['model'],'deepseek-flash')


if __name__=='__main__':unittest.main()
