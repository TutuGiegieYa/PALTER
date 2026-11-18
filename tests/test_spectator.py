"""Spectator ownership, autonomous lifecycle, recovery and spending contracts."""
from copy import deepcopy
from concurrent.futures import ThreadPoolExecutor
import json
from pathlib import Path
import tempfile
import time
import unittest
from palter.deepseek import DeepSeek,Settings
from palter.ensemble import EnsembleApplication
from palter import ensemble_world as w,spectator
from palter.storage import StoreError,canonical
from tests.test_ensemble import EnsembleProvider


class SpectatorTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.provider=EnsembleProvider()
        self.app=EnsembleApplication(Path(self.tmp.name)/'watch.sqlite3',DeepSeek(Settings(api_key='fixture'),self.provider))
        self.owner=self.app.store.session()['id'];self.serial=0
    def create(self,scenario='murder',opening='after'):
        s=self.app.create_game(self.owner,{'command_id':'create_watch_001','expected_game_id':None,'category':scenario,'humans':0,'opening':opening})
        self.gid=s['id'];self.cmd('confirm');return self.state()
    def state(self):return self.app.store.state(self.owner,self.gid)
    def cmd(self,kind,**extra):
        self.serial+=1
        return self.app.command(self.owner,self.gid,{'command_id':f'watch_command_{self.serial:04d}','expected_revision':self.state()['revision'],'kind':kind,**extra})
    def change(self,fn):
        with self.app.store.transaction() as con:
            old=self.app.store.load(con,self.owner,self.gid);s=deepcopy(old);fn(s);s['revision']+=1;self.app.store.save(con,s,old)
    def pump(self,n=1):
        for _ in range(n):self.app.pump(self.gid,force=True)
        return self.state()
    def test_owner_has_no_seat_and_omniscient_view_cannot_be_requested_by_strangers(self):
        s=self.create();self.assertEqual(s['humans'],[]);self.assertEqual(s['joined'],[])
        self.assertEqual(self.app.actor(self.owner,self.gid),'observer')
        v=self.app.view(self.owner,s);self.assertTrue(v['spectator']);self.assertEqual(set(v['roles']),set('ABCD'))
        self.assertIn('B_PRIVATE_SECRET_CANARY',canonical(v));self.assertNotIn('B_PRIVATE_SECRET_CANARY',canonical(w.context(s,'A')))
        stranger=self.app.store.session()['id']
        with self.assertRaises(StoreError):self.app.store.state(stranger,self.gid)
        for kind in ('say','act','submit','thought','ready','pause','resume'):
            with self.subTest(kind=kind),self.assertRaises(StoreError):self.cmd(kind)
        with self.assertRaises(StoreError):self.app.join(stranger,{'command_id':'join_watch_001','code':str(s['join_code'])})
    def test_prepared_game_waits_for_explicit_start_and_interactive_opening_has_four_decisions(self):
        s=self.create(opening='interactive');self.assertEqual(s['phase'],'reading');self.assertIsNone(s['reading_deadline'])
        self.assertEqual(set(s['intentions']),set('ABCD'));self.assertEqual(sum(t=='ensemble_opening' for t,_,_ in self.provider.calls),4)
        calls=len(self.provider.calls);self.assertFalse(self.app.pump(self.gid,True));self.assertEqual(len(self.provider.calls),calls)
    def test_single_step_is_idempotent_and_does_not_run_another_role(self):
        self.create();body={'command_id':'single_step_001','expected_revision':self.state()['revision'],'kind':'watch_step'}
        self.app.command(self.owner,self.gid,body);self.app.command(self.owner,self.gid,body)
        s=self.pump(3);self.assertEqual(s['phase'],'paused');self.assertEqual(s['watch']['steps'],1)
        self.assertEqual(sum(s['watch']['turns'].values()),1)
        self.assertEqual(s['watch']['pause_reason'],'step')
    def test_idle_agenda_keeps_running_fairly_and_stagnation_pauses_without_ending(self):
        self.provider.next_decision=lambda d:{'mode':'continue','events':[]}
        self.create();self.cmd('watch_resume');s=self.pump(16)
        self.assertEqual(s['phase'],'paused');self.assertEqual(s['watch']['pause_reason'],'stagnation')
        self.assertEqual(set(s['watch']['turns'].values()),{3});self.assertIsNone(s['ending'])
        self.cmd('watch_resume');self.assertEqual(self.state()['watch']['stagnant'],0)
    def test_disconnect_pauses_and_a_new_view_does_not_resume(self):
        self.create();self.cmd('watch_resume');self.app._seen[self.gid]=time.time()-61
        self.assertFalse(self.app.pump(self.gid));s=self.state();self.assertEqual(s['watch']['pause_reason'],'disconnected')
        self.app.view(self.owner,s);self.assertFalse(self.app.pump(self.gid));self.assertEqual(self.state()['phase'],'paused')
    def test_speed_does_not_change_game_clock_per_step(self):
        self.create();self.cmd('watch_step');a=self.pump();self.cmd('watch_speed',speed='fast');self.cmd('watch_step');b=self.pump()
        self.assertEqual(a['watch']['clock'],2);self.assertEqual(b['watch']['clock'],4)
    def test_three_assents_then_independent_locks_end_all_seven_scenarios(self):
        for scenario in ('murder','theft','family','council','rescue','house','archive'):
            with self.subTest(scenario=scenario):
                if hasattr(self,'gid'):self.owner=self.app.store.session()['id']
                self.create(scenario)
                self.provider.policy=lambda d:'lock_conclusion' if d['closure']['ready'] else 'close_vote:yes'
                self.cmd('watch_resume');s=self.pump(12)
                self.assertEqual(s['phase'],'ended');self.assertEqual(set(s['submissions']),set('ABCD'))
                self.assertEqual(len(s['closure']['votes']),3);self.assertIsNotNone(s['ending'])
    def test_shared_role_context_is_identical_without_controller_or_spectator_flags(self):
        s=self.create();ordinary=deepcopy(s);ordinary.pop('watch');ordinary['humans']=['A']
        payloads=[]
        def call(stage,task,baseline,data,validate,actor=None):
            payloads.append((deepcopy(baseline),deepcopy(data)))
            out={'choice':'wait','speech':'我先核对自己的记忆。','gesture':None,'question_to':None,'memory':'自己的记忆',
                 'memory_sources':[],'relationships':[],'suspect':None,'evidence_ids':[],'reasoning':'','situation':'我只根据收到的信息判断局势。','strategy':'我决定先回应。','assessment_sources':[],'progress':{'kind':'none','sources':[]}}
            out['next_decision']={'mode':'wait','events':[]};validate(out);return out,'fixture'
        call.prefix_version='ai-tasks-v62.json'  # Preserve this direct legacy response fixture.
        self.app.turn(s,'B',call,0);self.app.turn(ordinary,'B',call,0)
        self.assertEqual(payloads[0],payloads[1]);self.assertNotIn('watch',payloads[0][1]);self.assertNotIn('humans',payloads[0][1])
    def test_pause_during_call_buffers_then_reuses_paid_stage(self):
        self.create();self.cmd('watch_resume');self.provider.block='ensemble_role'
        with ThreadPoolExecutor() as pool:
            future=pool.submit(self.app.pump,self.gid,True);self.assertTrue(self.provider.entered.wait(2))
            self.cmd('watch_pause');self.provider.release.set();future.result(3)
        self.assertEqual(self.state()['watch']['steps'],0);self.assertEqual(self.state()['phase'],'paused')
        self.provider.block=None;self.cmd('watch_resume');s=self.pump()
        self.assertEqual(s['watch']['steps'],1);self.assertEqual(sum(t=='ensemble_role' for t,_,_ in self.provider.calls),1)
    def test_step_in_flight_cannot_be_double_scheduled(self):
        self.create();self.cmd('watch_step');self.provider.block='ensemble_role'
        with ThreadPoolExecutor() as pool:
            future=pool.submit(self.app.pump,self.gid,True);self.assertTrue(self.provider.entered.wait(2))
            with self.assertRaises(StoreError):self.cmd('watch_step')
            self.provider.release.set();future.result(3)
        self.assertEqual(self.state()['watch']['steps'],1);self.assertEqual(self.state()['phase'],'paused')
    def test_buffered_single_step_can_resume_continuously_without_repeating_paid_role(self):
        self.create();self.cmd('watch_step');self.provider.block='ensemble_role'
        with ThreadPoolExecutor() as pool:
            future=pool.submit(self.app.pump,self.gid,True);self.assertTrue(self.provider.entered.wait(2))
            self.cmd('watch_pause');self.provider.release.set();future.result(3)
        self.provider.block=None;self.cmd('watch_resume');s=self.pump()
        self.assertEqual(s['phase'],'active');self.assertEqual(s['watch']['steps'],1)
        self.assertEqual(sum(t=='ensemble_role' for t,_,_ in self.provider.calls),1)
    def test_another_role_can_react_before_timed_work_advances(self):
        self.create();self.provider.policy=lambda d:'search' if d['actor']=='A' else 'wait'
        self.cmd('watch_resume');first=self.pump()
        self.assertIsNotNone(w.running(first,'A'));self.assertEqual(first['watch']['turns']['A'],1)
        second=self.pump()
        self.assertEqual(second['watch']['turns']['B'],1);self.assertEqual(second['beat'],first['beat'])
        third=self.pump();self.assertGreater(third['beat'],second['beat'])
    def test_budget_reservation_stops_before_provider_and_topup_is_idempotent(self):
        self.create();self.change(lambda s:s['watch'].update(budget_usd=.000001));self.cmd('watch_resume');before=len(self.provider.calls)
        s=self.pump();self.assertEqual(len(self.provider.calls),before);self.assertEqual(s['watch']['pause_reason'],'budget')
        body={'command_id':'topup_watch_001','expected_revision':s['revision'],'kind':'watch_add_budget'}
        self.app.command(self.owner,self.gid,body);self.app.command(self.owner,self.gid,body)
        self.assertAlmostEqual(self.state()['watch']['budget_usd'],.050001);self.assertEqual(self.state()['phase'],'paused')
        self.cmd('watch_resume');s=self.pump();self.assertEqual(s['watch']['steps'],1)
        self.assertAlmostEqual(s['watch']['budget_usd'],.050001)
    def test_topup_during_call_survives_atomic_world_commit(self):
        self.create();self.cmd('watch_resume');self.provider.block='ensemble_role'
        with ThreadPoolExecutor() as pool:
            future=pool.submit(self.app.pump,self.gid,True);self.assertTrue(self.provider.entered.wait(2))
            self.cmd('watch_add_budget');self.cmd('watch_add_calls');self.provider.release.set();future.result(3)
        self.assertAlmostEqual(self.state()['watch']['budget_usd'],.15)
        self.assertEqual(self.state()['watch']['call_limit'],192)
    def test_unknown_usage_retains_reservation_in_budget(self):
        self.create();original=self.provider
        def missing(payload):
            out=original(payload);out.pop('usage');return out
        self.app.gateway.client.transport=missing;self.cmd('watch_step');self.pump()
        trace=self.app.gateway.trace(self.owner,self.gid)
        self.assertGreater(trace['reserved_cost_usd'],0);self.assertGreater(trace['accounted_cost_usd'],trace['cost_upper_usd']);self.assertTrue(trace['unknown_usage'])
    def test_call_ceiling_cannot_be_bypassed_by_adding_money(self):
        self.create()
        with self.app.store.transaction() as con:
            columns=[x[1] for x in con.execute('PRAGMA table_info(ai_calls)')]
            row=dict(con.execute('SELECT * FROM ai_calls LIMIT 1').fetchone())
            count=con.execute('SELECT COUNT(*) FROM ai_calls').fetchone()[0]
            for i in range(count,128):
                row['id']='synthetic-cap-'+str(i)
                con.execute('INSERT INTO ai_calls('+','.join(columns)+') VALUES ('+','.join('?' for _ in columns)+')',[row[k] for k in columns])
        self.cmd('watch_add_budget')
        with self.assertRaisesRegex(StoreError,'128'):self.cmd('watch_resume')
    def test_extend_old_game_limit_and_resume_the_same_partly_completed_operation(self):
        self.create();self.change(lambda s:s['watch'].pop('call_limit'))
        self.assertEqual(self.app.gateway.trace(self.owner,self.gid)['limit'],128)
        with self.app.store.transaction() as con:
            row=dict(con.execute('SELECT * FROM ai_calls LIMIT 1').fetchone());columns=list(row)
            count=con.execute('SELECT COUNT(*) FROM ai_calls').fetchone()[0]
            for i in range(count,127):
                row['id']='old-limit-fixture-'+str(i)
                con.execute('INSERT INTO ai_calls('+','.join(columns)+') VALUES ('+','.join('?' for _ in columns)+')',[row[k] for k in columns])
        self.cmd('watch_resume');s=self.pump();operation=s['watch']['recovery_operation']
        self.assertEqual(s['watch']['pause_reason'],'call_limit');self.assertEqual(s['watch']['steps'],0)
        self.assertFalse(s['background_error']['retryable'])
        body={'command_id':'call_topup_0001','expected_revision':s['revision'],'kind':'watch_add_calls'}
        self.app.command(self.owner,self.gid,body);self.app.command(self.owner,self.gid,body)
        s=self.state();self.assertEqual(s['watch']['call_limit'],192);self.assertEqual(s['phase'],'paused')
        self.assertEqual(s['watch']['budget_usd'],.10);self.assertEqual(s['watch']['recovery_operation'],operation)
        # Reload the app to prove the new allowance and recovery pointer are persisted.
        self.app=EnsembleApplication(Path(self.tmp.name)/'watch.sqlite3',DeepSeek(Settings(api_key='fixture'),self.provider))
        self.cmd('watch_step');s=self.pump()
        self.assertEqual(s['watch']['steps'],1);self.assertEqual(s['watch']['call_limit'],192)
        self.assertEqual(sum(t=='ensemble_role' for t,_,_ in self.provider.calls),1)
        trace=self.app.gateway.trace(self.owner,self.gid)
        self.assertEqual(len(trace['calls']),129);self.assertEqual(trace['limit'],192)
        with self.app.store.transaction(False) as con:
            self.assertEqual(con.execute('SELECT status FROM ai_operations WHERE id=?',(operation,)).fetchone()[0],'completed')
    def test_more_calls_do_not_bypass_money_or_exhausted_stage_retries(self):
        self.create();self.change(lambda s:s['watch'].update(budget_usd=.000001))
        self.cmd('watch_add_calls');self.cmd('watch_resume');before=len(self.provider.calls);s=self.pump()
        self.assertEqual(s['watch']['pause_reason'],'budget');self.assertEqual(len(self.provider.calls),before)
        self.assertEqual(s['watch']['budget_usd'],.000001)
        self.change(lambda s:s.update(background_error={'code':'retry_budget','retryable':False,'operation_id':'exhausted_stage'}))
        self.cmd('watch_add_calls')
        with self.assertRaisesRegex(StoreError,'重试上限'):self.cmd('watch_resume')
    def test_omniscient_private_dialogue_never_enters_an_outside_role_view(self):
        self.create()
        def private(s):
            w.apply_choice(s,'C','invite:D');w.apply_choice(s,'D','accept:i1');w.speak(s,'C','SPECTATOR_PRIVATE_CANARY',target='D')
        self.change(private);s=self.state();v=self.app.view(self.owner,s)
        self.assertIn('SPECTATOR_PRIVATE_CANARY',canonical(v['timeline']))
        self.assertNotIn('SPECTATOR_PRIVATE_CANARY',canonical(w.context(s,'A')))
        self.assertNotIn('SPECTATOR_PRIVATE_CANARY',canonical(v['roles']['A']['observations']))
    def test_empty_searches_and_backtracking_do_not_repeatedly_count_as_progress(self):
        s=self.create();initial=spectator.progress_keys(s)
        w.apply_choice(s,'A','move:r2');visited=spectator.progress_keys(s)
        self.assertTrue(visited-initial)
        w.apply_choice(s,'A','move:r1');self.assertFalse(spectator.progress_keys(s)-(initial|visited))
        for _ in range(2):
            w.apply_choice(s,'A','search');w.advance(s);w.advance(s)
            initial|=spectator.progress_keys(s)
        w.apply_choice(s,'A','search');w.advance(s);w.advance(s)
        self.assertFalse(spectator.progress_keys(s)-initial)
    def test_normal_participant_cannot_request_spectator_controls_or_truth(self):
        s=self.app.create_game(self.owner,{'command_id':'normal_game_001','expected_game_id':None,'humans':1,'category':'murder'})
        self.gid=s['id'];self.cmd('confirm');v=self.app.view(self.owner,self.state())
        self.assertNotIn('spectator',v);self.assertNotIn('truth',v)
        with self.assertRaises(StoreError):self.cmd('watch_resume')
        with self.assertRaises(StoreError):self.cmd('watch_add_calls')

    def test_roles_may_use_or_ignore_heard_words_but_not_an_unheard_private_source(self):
        s=self.create();w.apply_choice(s,'C','invite:D');w.apply_choice(s,'D','accept:i1')
        private=w.speak(s,'C','UNHEARD_PROGRESS_SOURCE',target='D')
        public=w.speak(s,'A','你对我刚才的说法有什么疑问？',target='B')
        heard=next(o['id'] for o in s['observations']['B'] if o['event_id']==public['id'])
        unheard=next(o['id'] for o in s['observations']['C'] if o['event_id']==private['id'])
        progress={'kind':'answer','sources':[heard]}
        def call(stage,task,baseline,data,validate,actor=None):
            if task=='ensemble_memory':
                out={'summary':'稍早听到的说法仍待核实。','sources':[]}
                validate(out);return out,'fixture-memory'
            out={'choice':'wait','speech':'我听到了，但还需要核对。','gesture':None,'question_to':None,'memory':'尚待核实的说法',
                 'memory_sources':[],'relationships':[],'suspect':None,'evidence_ids':[],'reasoning':'','situation':'我只根据收到的信息判断局势。','strategy':'我决定先回应。','assessment_sources':[],'progress':deepcopy(progress)}
            out['next_decision']={'mode':'wait','events':[]};validate(out);return out,'fixture'
        call.prefix_version='ai-tasks-v62.json'
        self.app.turn(deepcopy(s),'B',call,0)
        for i in range(30):
            event=w.emit(s,'fixture_observation');w.note(s,'B',event,'后来取得的现场观察。')
        self.assertNotIn(heard,{o['id'] for o in w.context(s,'B')['observations']})
        self.app.turn(deepcopy(s),'B',call,0)
        progress={'kind':'none','sources':[]};self.app.turn(deepcopy(s),'B',call,0)
        progress={'kind':'answer','sources':[unheard]}
        with self.assertRaises(ValueError):self.app.turn(deepcopy(s),'B',call,0)


if __name__=='__main__':unittest.main()
