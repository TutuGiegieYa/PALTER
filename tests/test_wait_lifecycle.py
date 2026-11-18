"""Finite, recipient-scoped waits; generic DM validity and deterministic deadlines."""
from copy import deepcopy
import unittest
from palter import ensemble_world as w, role_schedule as schedule, role_events, wait_lifecycle as waits, spectator
from palter.storage import canonical
from palter.storage import StoreError
from palter.ensemble import EnsembleApplication
from palter.deepseek import DeepSeek,Settings
from tests import test_ensemble_review as fixtures

VERSION='ai-tasks-v79.json'


class WaitLifecycleTests(unittest.TestCase):
    def setUp(self):
        self.f=fixtures.ReviewFixTests();self.f.setUp();self.addCleanup(self.f.doCleanups)
        self.app,self.s=self.f.app,self.f.state
        self.old=deepcopy(self.s)
        self.app.configure_rules(self.s,self.f.caller(VERSION));self.s['agenda']=[]

    def wait(self,actor='A',targets=(),**extra):
        self.s['agenda']=[q for q in self.s['agenda'] if q['actor']!=actor]
        data=schedule.context(self.s,actor);plan=dict(mode='wait',events=list(targets),**extra)
        schedule.validate(plan,data,'wait');schedule.commit(self.s,actor,plan,data)
        return self.s['role_waits'][actor]

    def review(self,status='active',reason='条件仍有实现路径。'):
        def change(task,out,data):
            if task=='ensemble_dm':
                for item in out['event_decisions']:item.update(status=status,reason=reason)
        self.app.adjudicate_ensemble(self.s,len(self.s['events']),self.f.caller(VERSION,change))

    def test_timeout_is_private_once_and_does_not_execute_an_action(self):
        wait=self.wait(targets=['next_observation'],timeout_seconds=10,wait_reason='等实际进展。')
        before=deepcopy(self.s);self.s['watch']['clock']=wait['deadline']-1;schedule.reconcile(self.s)
        self.assertTrue(schedule.waiting(self.s,'A'))
        self.s['watch']['clock']+=1;schedule.reconcile(self.s);schedule.reconcile(self.s)
        self.assertFalse(schedule.waiting(self.s,'A'))
        self.assertEqual(sum(q['actor']=='A' for q in self.s['agenda']),1)
        self.assertEqual(self.s['wait_results']['A']['status'],'timed_out')
        self.assertEqual(len([e for e in self.s['events'] if e['kind']=='wait_resolved']),1)
        self.assertEqual(self.s['locations'],before['locations']);self.assertFalse(self.f.inputs)
        for a in 'BCD':self.assertEqual(self.s['observations'][a],before['observations'][a])

    def test_timeout_validation_defaults_and_old_contract(self):
        wait=self.wait();self.assertEqual(wait['deadline']-wait['started_at'],30)
        for value in (None,True,0,9,301,10.0,'30'):
            with self.subTest(value=value),self.assertRaises(ValueError):self.wait(timeout_seconds=value)
        data=schedule.context(self.old,'A')
        with self.assertRaises(ValueError):schedule.validate({'mode':'wait','events':[],'timeout_seconds':30},data,'wait')

    def test_empty_location_is_reviewed_not_cancelled_by_engine(self):
        self.s['locations'].update(B='r2',C='r2',D='r2')
        self.wait(wait_reason='等待当前事项的后续。');schedule.reconcile(self.s)
        self.assertTrue(schedule.waiting(self.s,'A'));self.assertEqual(role_events.scopes_due(self.s),{'public'})
        self.review('active');self.assertTrue(schedule.waiting(self.s,'A'))
        self.assertEqual(role_events.scopes_due(self.s),set())
        before=len(self.f.inputs)
        for _ in range(5):schedule.reconcile(self.s);self.review()
        self.assertEqual(len(self.f.inputs),before)

    def test_dm_can_cancel_wait_after_perceptible_change_once(self):
        self.s['locations'].update(C='r2',D='r2');self.wait();self.review()
        w.apply_choice(self.s,'B','move:r2');schedule.reconcile(self.s)
        self.assertTrue(schedule.waiting(self.s,'A'));self.assertEqual(role_events.scopes_due(self.s),{'public'})
        self.review('cancelled','原先等待的交流已中止，继续等待没有明确对象。')
        self.assertFalse(schedule.waiting(self.s,'A'));self.assertEqual(len(self.s['agenda']),1)
        self.assertEqual(self.s['wait_results']['A']['status'],'cancelled')
        self.assertEqual(self.s['locations']['A'],'r1')
        self.review();self.assertEqual(len(self.s['agenda']),1)

    def test_fixed_outcome_is_engine_owned_even_when_alone(self):
        self.s['locations'].update(B='r2',C='r2',D='r2')
        w.apply_choice(self.s,'A','search');task=self.s['activities'][-1]
        self.wait(targets=['activity:'+task['id']]);self.assertEqual(role_events.scopes_due(self.s),set())
        w.advance(self.s);schedule.reconcile(self.s)
        self.assertFalse(schedule.waiting(self.s,'A'));self.assertFalse(self.f.inputs)

    def test_wait_timeout_does_not_close_shared_private_conversation(self):
        w.apply_choice(self.s,'B','invite:C');w.apply_choice(self.s,'C','accept:i1')
        chat=w.chat_for(self.s,'B');wait=self.wait(targets=['conversation:'+chat['id']],timeout_seconds=10)
        self.assertEqual(waits.review_records(self.s),[])
        self.s['watch']['clock']=wait['deadline'];schedule.reconcile(self.s)
        self.assertEqual(chat['status'],'active');self.assertFalse(schedule.waiting(self.s,'A'))

    def test_wait_timeout_leaves_custom_condition_unresolved(self):
        key=role_events.request(self.s,'A',{'event_request':{'description':'核对后续条件','completion_condition':'我收到约定的结果。','early_end_condition':''}})
        self.review();wait=self.wait(targets=['tracked:'+key],timeout_seconds=10)
        self.s['watch']['clock']=wait['deadline'];schedule.reconcile(self.s)
        self.assertEqual(self.s['tracked_events'][0]['status'],'active')
        self.assertEqual(self.s['wait_results']['A']['status'],'timed_out')

    def test_custom_conditions_get_generic_scoped_circumstances(self):
        self.s['locations'].update(B='r2',C='r2',D='r2')
        role_events.request(self.s,'A',{'event_request':{'description':'等待后续','completion_condition':'我收到后续记录。','early_end_condition':'约定撤销。'}})
        records,context,allowed=role_events.package(self.s,'public')
        presence=context['A']['current_circumstances']['presence']
        self.assertEqual(presence['people'],[]);self.assertTrue(presence['complete'])
        self.assertNotIn('r2',canonical(context['A']['current_circumstances']))
        self.review();self.assertEqual(role_events.scopes_due(self.s),set())
        w.apply_choice(self.s,'B','move:r1');self.assertEqual(role_events.scopes_due(self.s),{'public'})

    def test_private_perception_ignores_unheard_outside_changes(self):
        w.apply_choice(self.s,'A','invite:B');w.apply_choice(self.s,'B','accept:i1')
        schedule.reconcile(self.s)
        self.wait();self.review();before=canonical(waits.circumstances(self.s,'A'))
        w.apply_choice(self.s,'C','move:r2');w.speak(self.s,'D','OUTSIDE_WAIT_CANARY')
        self.assertEqual(canonical(waits.circumstances(self.s,'A')),before)
        self.assertEqual(role_events.scopes_due(self.s),set())
        self.assertNotIn('OUTSIDE_WAIT_CANARY',canonical(self.f.inputs))

    def test_dm_cannot_complete_wait_or_cite_another_roles_record(self):
        self.wait();records,_,allowed=role_events.package(self.s,'public')
        item={'id':records[0]['id'],'status':'completed','reason':'完成。','progress':'','source_ids':['A-o000001']}
        with self.assertRaises(ValueError):role_events.validate_decisions({'event_decisions':[item]},records,allowed)
        item.update(status='cancelled',source_ids=['B-o000001'])
        with self.assertRaises(ValueError):role_events.validate_decisions({'event_decisions':[item]},records,allowed)

    def test_existing_waits_upgrade_once_and_old_prefix_stays_unchanged(self):
        s=self.old;self.app.configure_rules(s,self.f.caller('ai-tasks-v78.json'));s['agenda']=[]
        schedule.commit(s,'A',{'mode':'wait','events':[]},schedule.context(s,'A'))
        before=deepcopy(s);self.app.configure_rules(s,self.f.caller('ai-tasks-v78.json'));self.assertEqual(s,before)
        s['watch']['clock']=100;self.app.configure_rules(s,self.f.caller(VERSION))
        self.assertEqual(s['role_waits']['A']['deadline'],130)
        s['watch']['clock']=110;self.app.configure_rules(s,self.f.caller(VERSION))
        self.assertEqual(s['role_waits']['A']['deadline'],130)

    def test_pause_and_resume_shift_real_time_but_not_spectator_time(self):
        self.s.pop('watch');self.s['_operation_time']=100;self.wait(timeout_seconds=30)
        self.s.update(phase='paused',paused_at=110);self.s['_operation_time']=200
        schedule.reconcile(self.s);self.assertTrue(schedule.waiting(self.s,'A'))
        self.assertEqual(waits.view(self.s,'A')['remaining_seconds'],20)
        waits.shift(self.s,90);self.s.update(phase='active',_operation_time=200);self.s.pop('paused_at')
        self.assertEqual(waits.view(self.s,'A')['remaining_seconds'],20)
        self.s['watch']={'clock':200};before=self.s['role_waits']['A']['deadline'];waits.shift(self.s,50)
        self.assertEqual(self.s['role_waits']['A']['deadline'],before)

    def test_direct_contact_interrupts_without_dm(self):
        self.wait();w.speak(self.s,'B','请回应我。','A');schedule.reconcile(self.s)
        self.assertFalse(schedule.waiting(self.s,'A'));self.assertEqual(waits.review_records(self.s),[])
        self.assertFalse(self.f.inputs)

    def test_all_waiting_clock_advances_to_deadline_without_a_role_call(self):
        for actor in w.ACTORS:self.wait(actor,timeout_seconds=10)
        self.review();before=len(self.f.inputs)
        spectator.background(self.app,self.s,self.f.caller(VERSION))
        self.assertEqual(self.s['watch']['clock'],10)
        self.assertEqual(len(self.f.inputs),before);self.assertEqual(set(q['actor'] for q in self.s['agenda']),set(w.ACTORS))
        self.assertFalse(self.s['role_waits'])

    def test_repeated_timeout_wait_cycles_pause_without_invented_progress(self):
        self.s['watch']['seen_progress']=sorted(spectator.progress_keys(self.s))
        for actor in w.ACTORS:w.enqueue(self.s,actor,'开始决定。')
        def idle(task,out,data):
            if task=='ensemble_role':out.update(action={'kind':'wait','args':[]},speech='',question_to=None,
                progress={'kind':'none','sources':[]},next_decision={'mode':'wait','events':[],'timeout_seconds':10})
        for _ in range(40):
            if self.s['phase']!='active':break
            spectator.background(self.app,self.s,self.f.caller(VERSION,idle))
        self.assertEqual(self.s['phase'],'paused');self.assertEqual(self.s['watch']['pause_reason'],'stagnation')
        self.assertEqual(self.s['locations'],self.old['locations'])

    def test_paid_role_and_wait_review_replay_after_restart_without_duplicate_calls(self):
        app=self.app;app.gateway.current_version=VERSION;owner=app.store.session()['id']
        saved=app.store.create_game(owner,{'command_id':'wait_recovery_fixture','expected_game_id':None},lambda gid:dict(deepcopy(self.s),id=gid))
        command={'command_id':'wait_review_operation','expected_revision':saved['revision'],'kind':'probe'};seen=[]
        def worker(s,call):
            start=len(s['events']);app.turn(s,'A',call,0);app.adjudicate_ensemble(s,start,call)
            seen.append(deepcopy(s['role_waits']['A']))
        def interrupted(s,call):
            worker(s,call);raise StoreError('Synthetic interruption after paid review',503,'connection_failed')
        with self.assertRaises(StoreError):app.operate(owner,saved['id'],command,interrupted)
        calls=len(self.f.provider.calls);self.assertEqual(calls,2)
        app=EnsembleApplication(app.store.path,DeepSeek(Settings(api_key='fixture'),self.f.provider))
        app.gateway.current_version='ai-tasks-v78.json'
        result,receipt=app.operate(owner,saved['id'],command,worker)
        self.assertTrue(receipt['accepted']);self.assertEqual(len(self.f.provider.calls),calls)
        self.assertEqual(seen[0],seen[1]);self.assertEqual(result['role_waits']['A'],seen[0])
        again,receipt=app.operate(owner,saved['id'],command,worker)
        self.assertTrue(receipt['duplicate']);self.assertEqual(again,result)

    def test_interactive_background_pump_wakes_only_the_expired_role(self):
        self.s.pop('watch');self.s['humans']=['A'];self.wait('B');self.s['role_waits']['B']['deadline']=0
        self.app.gateway.current_version=VERSION;owner=self.app.store.session()['id']
        saved=self.app.store.create_game(owner,{'command_id':'human_wait_fixture','expected_game_id':None},lambda gid:dict(deepcopy(self.s),id=gid))
        self.assertTrue(self.app.pump(saved['id'],force=True))
        result=self.app.store.state(owner,saved['id']);self.assertEqual(result['wait_results']['B']['status'],'timed_out')
        actors=[d['actor'] for task,baseline,d in self.f.provider.calls if task=='ensemble_role']
        self.assertEqual(actors,['B'])


if __name__=='__main__':unittest.main()
