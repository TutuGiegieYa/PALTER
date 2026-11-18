"""Behavioral receipts for event-driven role decisions and scoped wakeups."""
from copy import deepcopy
import json
import unittest

from palter import ensemble_world as w, spectator, role_schedule as scheduling
from palter.ensemble import EnsembleApplication
from palter.deepseek import DeepSeek, Settings
from palter.storage import canonical
from tests import test_ensemble_review as fixture
from tests import test_spectator as watch_fixture


class RoleScheduleTests(unittest.TestCase):
    def setUp(self):
        fixture.ReviewFixTests.setUp(self)
        self.app.configure_rules(self.state,self.caller())
        self.state['agenda']=[]

    def caller(self,transform=None,version=None):
        return fixture.ReviewFixTests.caller(self,version or self.app.gateway.current_version,transform)

    def wait(self,actor,events=()):
        s=self.state;s['agenda']=[q for q in s['agenda'] if q['actor']!=actor]
        data=scheduling.context(s,actor);plan={'mode':'wait','events':list(events)}
        scheduling.validate(plan,data,'wait');scheduling.commit(s,actor,plan,data)

    def private(self):
        s=self.state;w.apply_choice(s,'A','invite:B');w.apply_choice(s,'B','accept:i1')
        scheduling.reconcile(s);return w.chat_for(s,'A')

    def test_both_waiters_are_idle_through_private_exchange_then_wake_once_without_secrets(self):
        s=self.state;chat=self.private()
        for actor in 'CD':self.wait(actor,['conversation:'+chat['id']])
        self.assertEqual(set(s['role_waits']),set('CD'))
        for n in range(4):w.speak(s,'AB'[n%2],'PRIVATE_EVENT_CANARY_'+str(n),'BA'[n%2]);scheduling.reconcile(s)
        self.assertFalse(any(q['actor'] in 'CD' for q in s['agenda']))
        before=len(self.provider.calls);w.close_chat(s,chat);scheduling.reconcile(s);scheduling.reconcile(s)
        self.assertEqual(len(self.provider.calls),before)
        self.assertEqual([q['actor'] for q in s['agenda']].count('C'),1)
        self.assertEqual([q['actor'] for q in s['agenda']].count('D'),1)
        self.assertFalse(any(scheduling.waiting(s,a) for a in 'CD'))
        for actor in 'CD':
            self.inputs=[];self.app.turn(s,actor,self.caller(),0,'等待的私聊已经结束。')
            data=next(d for t,d in self.inputs if t=='ensemble_role')
            self.assertIn('结束了私聊',canonical(data));self.assertNotIn('PRIVATE_EVENT_CANARY',canonical(data))

    def test_direct_question_interrupts_only_addressee_and_coalesces(self):
        s=self.state;chat=self.private();self.wait('C',['conversation:'+chat['id']])
        w.speak(s,'D','我先看已经拿到的记录。');scheduling.reconcile(s)
        self.assertTrue(scheduling.waiting(s,'C'))
        w.speak(s,'D','请你核对时间。','C');w.speak(s,'D','再看看这个差异。','C');scheduling.reconcile(s)
        self.assertFalse(scheduling.waiting(s,'C'));self.assertTrue(s['obligations']['C']['response'])
        self.assertEqual(sum(q['actor']=='C' for q in s['agenda']),1)
        self.assertTrue(s['chats'][chat['id']]['status']=='active')

    def test_waiting_broadcasts_are_recorded_without_periodic_paid_polling(self):
        s=self.state;self.wait('C')
        for n in range(18):w.speak(s,'D','PUBLIC_BACKLOG_'+str(n));scheduling.reconcile(s)
        self.assertTrue(w.must_speak(s,'C'));self.assertTrue(scheduling.waiting(s,'C'))
        self.assertFalse(any(q['actor']=='C' for q in s['agenda']));self.assertFalse(self.provider.calls)
        w.speak(s,'D','你怎么看？','C');self.app.turn(s,'C',self.caller(),0,'收到直接提问。')
        data=next(d for t,d in self.inputs if t=='ensemble_role')
        for n in range(18):self.assertIn('PUBLIC_BACKLOG_'+str(n),canonical(data))

    def test_long_wait_compacts_all_received_records_only_when_woken(self):
        s=self.state;self.private();self.wait('C')
        for n in range(40):
            w.speak(s,'D','RECEIVED_'+str(n));w.speak(s,'A','UNHEARD_BACKLOG_'+str(n),'B')
        self.assertFalse(self.provider.calls)
        w.speak(s,'D','轮到你核对了。','C');self.app.turn(s,'C',self.caller(),0)
        memory=[d for t,d in self.inputs if t=='ensemble_memory'];self.assertTrue(memory)
        all_context=canonical(self.inputs);self.assertNotIn('UNHEARD_BACKLOG',all_context)
        for n in range(40):self.assertIn('RECEIVED_'+str(n),all_context)
        self.assertEqual(sum(o['text'].startswith('RECEIVED_') for o in s['observations']['C']),40)

    def test_unobserved_or_nonexistent_event_cannot_be_subscribed(self):
        s=self.state;w.apply_choice(s,'A','search')
        data=scheduling.context(s,'C');key='activity:'+s['activities'][-1]['id']
        self.assertNotIn(key,{x['id'] for x in data['waitable_events']})
        for keys in ([key],['conversation:missing'],['own_activity'],['next_observation']*2):
            with self.subTest(keys=keys),self.assertRaises(ValueError):scheduling.validate({'mode':'wait','events':keys},data,'wait')

    def test_prospective_own_work_wait_wakes_on_actual_result(self):
        s=self.state
        def search(task,out,data):
            if task=='ensemble_role':out.update(choice='search',next_decision={'mode':'wait','events':['own_activity']})
        self.app.turn(s,'C',self.caller(search),0)
        self.assertTrue(scheduling.waiting(s,'C'));self.assertTrue(w.running(s,'C'))
        calls=len(self.provider.calls);w.advance(s);scheduling.reconcile(s)
        self.assertFalse(scheduling.waiting(s,'C'));self.assertEqual(len(self.provider.calls),calls)
        self.assertEqual(sum(q['actor']=='C' for q in s['agenda']),1)

    def test_failed_and_cancelled_work_also_wake_without_claiming_success(self):
        for outcome in ('failed','cancelled'):
            with self.subTest(outcome=outcome):
                s=deepcopy(self.state);w.apply_choice(s,'C','search');data=scheduling.context(s,'C')
                scheduling.commit(s,'C',{'mode':'wait','events':['activity:'+s['activities'][-1]['id']]},data)
                if outcome=='failed':s['locations']['C']='r2';w.advance(s)
                else:w.apply_choice(s,'C','cancel_work')
                scheduling.reconcile(s)
                self.assertEqual(s['activities'][-1]['status'],outcome);self.assertFalse(scheduling.waiting(s,'C'))
                self.assertEqual(sum(q['actor']=='C' for q in s['agenda']),1)

    def test_expired_invitation_wakes_sender_and_retains_historical_outcome(self):
        s=self.state;w.apply_choice(s,'C','invite:D');s['agenda']=[];self.wait('C',['invitation:i1'])
        s['watch']['clock']=301;w.expire(s);scheduling.reconcile(s)
        self.assertEqual(s['invitations'][0]['status'],'expired');self.assertFalse(scheduling.waiting(s,'C'))
        self.assertIn('已失效',canonical(s['observations']['C']))
        before=canonical(s);w.expire(s);scheduling.reconcile(s);self.assertEqual(canonical(s),before)

    def test_private_invitation_and_reply_interrupt_waiting_only_for_participants(self):
        s=self.state;self.wait('C');self.wait('D')
        w.apply_choice(s,'B','invite:C');self.assertFalse(scheduling.waiting(s,'C'));self.assertTrue(scheduling.waiting(s,'D'))
        w.apply_choice(s,'C','accept:i1');scheduling.reconcile(s);self.wait('C')
        w.speak(s,'B','PRIVATE_DIRECT_CANARY');scheduling.reconcile(s)
        self.assertFalse(scheduling.waiting(s,'C'));self.assertTrue(scheduling.waiting(s,'D'))
        self.assertNotIn('PRIVATE_DIRECT_CANARY',canonical(w.context(s,'D')))

    def test_next_observation_subscription_is_explicit_and_recipient_scoped(self):
        s=self.state;self.private();self.wait('C',['next_observation']);self.wait('D')
        w.speak(s,'A','PRIVATE_UNHEARD','B');scheduling.reconcile(s);self.assertTrue(scheduling.waiting(s,'C'))
        w.speak(s,'D','PUBLIC_HEARD');scheduling.reconcile(s);self.assertFalse(scheduling.waiting(s,'C'))
        self.assertTrue(scheduling.waiting(s,'D'))

    def test_known_chat_end_that_happens_during_decision_is_not_missed(self):
        s=self.state;chat=self.private();s['agenda']=[];data=scheduling.context(s,'C')
        w.close_chat(s,chat);scheduling.reconcile(s)
        scheduling.commit(s,'C',{'mode':'wait','events':['conversation:'+chat['id']]},data)
        self.assertFalse(scheduling.waiting(s,'C'));self.assertEqual(sum(q['actor']=='C' for q in s['agenda']),1)

    def test_unheard_chat_end_does_not_notify_a_now_absent_observer(self):
        s=self.state;chat=self.private();w.apply_choice(s,'C','invite:D');w.apply_choice(s,'D','accept:i2')
        scheduling.reconcile(s);self.wait('C',['conversation:'+chat['id']])
        w.close_chat(s,chat);scheduling.reconcile(s)
        self.assertTrue(scheduling.waiting(s,'C'));self.assertFalse(any(q['actor']=='C' for q in s['agenda']))

    def test_everyone_waiting_pauses_with_zero_calls_and_no_ending(self):
        s=self.state
        for a in w.ACTORS:self.wait(a)
        spectator.background(self.app,s,self.caller())
        self.assertEqual(s['phase'],'paused');self.assertEqual(s['watch']['pause_reason'],'waiting')
        self.assertFalse(self.provider.calls);self.assertIsNone(s['ending'])

    def test_silent_private_chat_expiry_advances_without_polling_then_wakes_waiters(self):
        s=self.state;chat=self.private()
        for a in w.ACTORS:self.wait(a,['conversation:'+chat['id']])
        spectator.background(self.app,s,self.caller())
        self.assertFalse(self.provider.calls);self.assertEqual(chat['status'],'closed')
        self.assertEqual({q['actor'] for q in s['agenda']},set(w.ACTORS))

    def test_subscriptions_survive_serialization_and_a_single_step_stops_after_timer(self):
        s=self.state;chat=self.private()
        for a in w.ACTORS:self.wait(a,['conversation:'+chat['id']])
        self.state=json.loads(canonical(s));s=self.state;s['watch']['single_step']=True
        spectator.background(self.app,s,self.caller())
        self.assertEqual(s['phase'],'paused');self.assertEqual(s['watch']['pause_reason'],'step')
        self.assertEqual({q['actor'] for q in s['agenda']},set(w.ACTORS));self.assertFalse(self.provider.calls)

    def test_old_pinned_operation_keeps_unscheduled_role_payload(self):
        s=deepcopy(self.state)
        for key in ('scheduling_version','role_waits','wake_cursors'):s.pop(key,None)
        self.app.turn(s,'C',self.caller(version='ai-tasks-v49.json'),0)
        data=next(d for t,d in self.inputs if t=='ensemble_role')
        self.assertNotIn('scheduling',data);self.assertFalse(scheduling.enabled(s))

    def test_background_calls_private_participants_only_until_chat_ends(self):
        s=self.state;chat=self.private()
        for actor in 'CD':self.wait(actor,['conversation:'+chat['id']])
        before=len(self.provider.calls)
        for _ in range(8):spectator.background(self.app,s,self.caller())
        decisions=[d['actor'] for t,p,d in self.provider.calls[before:] if t=='ensemble_role']
        self.assertEqual(len(decisions),8);self.assertEqual(set(decisions),set('AB'))
        self.assertEqual(len(chat['turns']),8)
        for _ in range(2):spectator.background(self.app,s,self.caller())
        decisions=[d['actor'] for t,p,d in self.provider.calls[before:] if t=='ensemble_role']
        self.assertEqual(set(decisions[-2:]),set('CD'));self.assertEqual(chat['status'],'closed')

    def test_either_participant_can_end_private_early_with_no_dm_decision(self):
        original=deepcopy(self.state)
        for actor in 'AB':
            self.state=deepcopy(original);s=self.state;chat=self.private()
            for waiter in 'CD':self.wait(waiter,['conversation:'+chat['id']])
            w.speak(s,'A','这件事我已经说完。','B')
            before=len(self.provider.calls);w.apply_choice(s,actor,'end_private');scheduling.reconcile(s)
            self.app.adjudicate_ensemble(s,len(s['events']),self.caller())
            self.assertEqual(chat['status'],'closed');self.assertEqual(len(chat['turns']),1)
            self.assertLess(s['watch']['clock'],chat['expires']);self.assertEqual(len(self.provider.calls),before)
            self.assertFalse(any(scheduling.waiting(s,a) for a in 'CD'))
            self.assertTrue(set('CD')<={q['actor'] for q in s['agenda']})

    def test_ai_can_choose_immediate_private_exit_without_required_speech(self):
        s=self.state;chat=self.private();w.speak(s,'A','请解释你刚才的说法。','B',challenge=True)
        def leave(task,out,data):
            if task=='ensemble_role':out.update(choice='end_private',speech='',gesture=None,next_decision={'mode':'wait','events':[]})
        self.app.turn(s,'B',self.caller(leave),0,'收到私聊质疑。')
        self.assertEqual(chat['status'],'closed');self.assertEqual(len(chat['turns']),1)
        self.assertFalse(s['obligations']['B']['explain'])
        self.assertEqual([t for t,p,d in self.provider.calls],['ensemble_role'])

    def test_ending_cancels_remaining_waits_without_faking_completion(self):
        s=self.state
        from palter import role_events
        role_events.request(s,'C',{'event_request':{'description':'未完成事项','completion_condition':'获得新信息','early_end_condition':''}})
        self.wait('C',['tracked:condition-1']);s['phase']='ended'
        role_events.end_story(s)
        self.assertFalse(s['role_waits']);self.assertEqual(s['tracked_events'][0]['status'],'cancelled')
        self.assertFalse(s['agenda'])

    def test_human_game_continuations_cannot_starve_due_physical_work(self):
        s=self.state;s.pop('watch');s['humans']=['A'];w.apply_choice(s,'C','search');s['next_tick']=0
        w.enqueue(s,'B','继续行动。');self.app.background(s,self.caller())
        self.assertEqual(s['activities'][-1]['status'],'completed');self.assertFalse(self.provider.calls)
        self.assertTrue(any(q['actor']=='C' for q in s['agenda']))


class DurableWaitTests(unittest.TestCase):
    def setUp(self):watch_fixture.SpectatorTests.setUp(self)
    def create(self):return watch_fixture.SpectatorTests.create(self)
    def state(self):return watch_fixture.SpectatorTests.state(self)
    def cmd(self,*args,**kwargs):return watch_fixture.SpectatorTests.cmd(self,*args,**kwargs)

    def test_waiting_is_saved_and_repeated_pumps_and_restart_do_not_call_models(self):
        # Published pre-timeout saves retain their indefinite-wait contract.
        self.app.gateway.current_version='ai-tasks-v78.json'
        self.create();self.cmd('watch_resume')
        for _ in range(5):self.app.pump(self.gid,True)
        s=self.state();self.assertEqual(s['watch']['pause_reason'],'waiting')
        self.assertEqual(set(s['role_waits']),set(w.ACTORS));calls=len(self.provider.calls)
        self.app=EnsembleApplication(self.app.store.path,DeepSeek(Settings(api_key='fixture'),self.provider))
        self.app.gateway.current_version='ai-tasks-v78.json'
        for _ in range(20):self.assertFalse(self.app.pump(self.gid,True))
        self.cmd('watch_resume');self.app.pump(self.gid,True)
        self.assertEqual(len(self.provider.calls),calls);self.assertEqual(self.state()['watch']['pause_reason'],'waiting')

    def test_dm_failure_retries_same_proposal_without_repeating_paid_role(self):
        self.app.gateway.current_version='ai-tasks-v55.json'  # Inline proposal recovery before native event tools.
        self.create();original=self.provider
        def transport(payload):
            response=original(payload)
            if 'PALTER_TASK: ensemble_role\n' in payload['messages'][0]['content']:
                out=json.loads(response['choices'][0]['message']['content'])
                out.update(event_request={'description':'等收到下一份原始材料','completion_condition':'我实际获得新的原始材料','early_end_condition':''},next_decision={'mode':'wait','events':['proposed_event']})
                response['choices'][0]['message']['content']=json.dumps(out,ensure_ascii=False)
            return response
        self.app.gateway.client.transport=transport;self.provider.fail='ensemble_dm';self.cmd('watch_resume');self.app.pump(self.gid,True)
        self.assertEqual(self.state()['watch']['pause_reason'],'error');self.assertFalse(self.state().get('tracked_events'))
        self.provider.fail=None;self.cmd('watch_resume');self.app.pump(self.gid,True)
        s=self.state();self.assertIsNone(s['background_error']);self.assertEqual(len(s['tracked_events']),1)
        self.assertEqual(s['tracked_events'][0]['status'],'active');self.assertTrue(scheduling.waiting(s,'A'))
        self.assertEqual(sum(t=='ensemble_role' for t,_,_ in self.provider.calls),1)


if __name__=='__main__':unittest.main()
