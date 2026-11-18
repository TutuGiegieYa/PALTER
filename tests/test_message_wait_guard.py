"""Last-role wait admission and bounded, private recovery of stalled subscriptions."""
from copy import deepcopy
import json
import unittest
from unittest.mock import patch

from palter import ensemble_world as w, role_schedule as schedule, spectator, wait_lifecycle, wait_progress
from palter.ensemble import EnsembleApplication
from palter.model_contracts import ContractError
from palter.storage import canonical, fingerprint
from tests import test_ensemble_review as fixture

VERSION='ai-tasks-v123.json'


class MessageWaitGuardTests(unittest.TestCase):
    def setUp(self):
        self.f=fixture.ReviewFixTests();self.f.setUp();self.addCleanup(self.f.doCleanups)
        self.app,self.s=self.f.app,self.f.state
        self.app.gateway.current_version=VERSION;self.app.gateway.retry_delays=(0,0,0)
        self.app.configure_rules(self.s,self.f.caller(VERSION));self.s['agenda']=[]

    def context(self,actor='A'):
        return schedule.context(self.s,actor,limit_waits=2,explicit_options=True,
            own_action_completion=True,message_wait_guard=True)

    def park(self,actor,events=('next_observation',),guard=False):
        self.s['agenda']=[q for q in self.s['agenda'] if q['actor']!=actor]
        data=self.context(actor) if guard else schedule.context(self.s,actor)
        plan={'mode':'wait','events':list(events),'timeout_seconds':300}
        schedule.validate(plan,data,'wait');schedule.commit(self.s,actor,plan,data)
        wait=self.s['role_waits'][actor]
        if 'review_pending' in wait:
            wait.update(review_pending=False,review_checkpoint=len(self.s['observations'][actor]),
                reviewed_circumstances=fingerprint(wait_lifecycle.circumstances(self.s,actor)))
        return wait

    def all_waiting(self,events=('phase:conclusion',)):
        for actor in w.ACTORS:self.park(actor,events)
        self.s['watch']['seen_progress']=sorted(spectator.progress_keys(self.s))

    def decision(self,events=(),mode='wait',speech=''):
        def change(task,out,data):
            if task=='ensemble_role':
                out.update(action={'kind':'wait','args':[]},speech=speech,gesture=None,
                    memory_update=None,
                    progress={'kind':'none','sources':[]},relationships=[],
                    next_decision={'mode':mode,'events':list(events),'timeout_seconds':300})
                for key in ('belief_update','strategy_update'):
                    if key in out:out[key]=None
        return change

    def test_first_three_can_wait_but_last_cannot(self):
        for a in 'ABC':
            self.assertTrue(self.context(a)['message_wait_guard']['message_wait_allowed'])
            self.park(a,guard=True)
        data=self.context('D');before=canonical(self.s)
        self.assertFalse(data['message_wait_guard']['message_wait_allowed'])
        self.assertFalse(data['decision_options']['empty_wait_allowed'])
        self.assertTrue(data['decision_options']['wait_requires_concrete_event'])
        for events in ([],['next_observation']):
            with self.subTest(events=events),self.assertRaises(ContractError) as caught:
                schedule.validate({'mode':'wait','events':events},data,'wait')
            self.assertFalse(caught.exception.feedback['message_wait_allowed'])
        self.assertEqual(canonical(self.s),before)

    def test_guard_is_a_permission_without_peer_state(self):
        for a in 'BCD':self.park(a)
        guard=self.context()['message_wait_guard'];before=deepcopy(guard)
        for a in 'BCD':
            self.s['role_waits'][a]['wait_reason']='PRIVATE_WAIT_'+a
            self.s['locations'][a]='r2'
        self.assertEqual(self.context()['message_wait_guard'],before)
        self.assertNotIn('PRIVATE_WAIT',canonical(self.context()))
        self.assertEqual(set(guard),{'version','message_wait_allowed','message_only_events','direct_contact_wait_allowed','terminal_actions'})

    def test_aliases_and_empty_targets_block_but_concrete_or_targets_remain(self):
        for a in 'BCD':self.park(a)
        self.s['event_listeners']=[
            {'id':'message','actor':'A','events':['next_observation'],'description':'新消息'},
            {'id':'mixed','actor':'A','events':['next_observation','phase:conclusion'],'description':'消息或结案'},
            {'id':'foreign','actor':'B','events':['next_observation'],'description':'私有监听'}]
        data=self.context()
        self.assertEqual(data['message_wait_guard']['message_only_events'],['next_observation','listener:message'])
        self.assertEqual(data['decision_options']['disallowed_wait_events'],[])
        with self.assertRaises(ContractError):
            schedule.validate({'mode':'wait','events':['listener:message']},data,'wait')
        for events in (['listener:mixed'],['phase:conclusion'],['phase:conclusion','next_observation']):
            schedule.validate({'mode':'wait','events':events},data,'wait')
        self.s['role_next_observation_wait']={'A':True}
        with self.assertRaises(ContractError):
            schedule.validate({'mode':'wait','events':['listener:mixed']},self.context(),'wait')

    def test_empty_continue_blocked_but_role_chooses_action_or_response(self):
        for a in 'BCD':self.park(a)
        data=self.context();plan={'mode':'continue','events':[]}
        with self.assertRaises(ContractError):schedule.validate(plan,data,'wait',speech='',gesture=None)
        for choice,speech,gesture in (('search','',None),('wait','我先核对。',None),('wait','',{'kind':'nod'})):
            schedule.validate(plan,data,choice,speech=speech,gesture=gesture)
        schedule.validate({'mode':'wait','events':['own_activity']},data,'search')

    def test_actual_activity_wait_is_allowed_and_completes_normally(self):
        for a in 'BCD':self.park(a)
        data=self.context();plan={'mode':'wait','events':['own_activity']}
        schedule.validate(plan,data,'search')
        event=w.apply_choice(self.s,'A','search')
        schedule.commit(self.s,'A',plan,data,action_event=event)
        self.assertEqual(self.s['role_waits']['A']['events'],['activity:'+event['id']])
        self.assertFalse(wait_progress.recover(self.s))
        w.advance(self.s);schedule.reconcile(self.s)
        self.assertNotIn('A',self.s['role_waits'])

    def test_terminal_actions_do_not_sleep_and_are_not_rejected(self):
        for a in 'BCD':self.s['submissions'][a]={}
        for choice in ('lock_conclusion','leave'):
            schedule.validate({'mode':'wait','events':[]},self.context(),choice)
        self.s['closure']['ready']=True
        with self.assertRaises(ContractError):schedule.validate({'mode':'wait','events':[]},self.context(),'leave')

    def test_unfinished_human_can_act_and_finished_roles_do_not_block_admission(self):
        self.s['humans']=['D']
        for a in 'BC':self.park(a)
        self.assertTrue(self.context()['message_wait_guard']['message_wait_allowed'])
        self.s['submissions']['D']={}
        self.assertFalse(self.context()['message_wait_guard']['message_wait_allowed'])
        self.s['submissions']={};self.s['evacuated']=['D']
        self.assertFalse(self.context()['message_wait_guard']['message_wait_allowed'])
        self.s['closure']['ready']=True
        self.assertTrue(self.context()['message_wait_guard']['message_wait_allowed'])

    def test_commit_rechecks_stale_permission_before_mutating_waits(self):
        for a in 'BC':self.park(a)
        stale=self.context();self.assertTrue(stale['message_wait_guard']['message_wait_allowed'])
        self.park('D');before=canonical(self.s)
        with self.assertRaises(ContractError):
            schedule.commit(self.s,'A',{'mode':'wait','events':['next_observation']},stale)
        self.assertEqual(canonical(self.s),before)

    def test_native_listener_rebuild_preserves_guard_and_detects_alias(self):
        for a in 'BCD':self.park(a)
        seen=[]
        def tool_then_continue(task,out,data):
            if task!='ensemble_role':return
            seen.append(deepcopy(data['scheduling']))
            if '_tool_messages' not in data:
                out.clear();out['_tool_message']={'role':'assistant','content':None,'tool_calls':[
                    {'id':'listener','type':'function','function':{'name':'create_event_listener',
                        'arguments':canonical({'description':'留意新信息','event_ids':['next_observation'],
                            'completion_condition':'','early_end_condition':''})}}]}
            else:self.decision(mode='continue',speech='我先核对现有材料。')(task,out,data)
        self.app.turn(self.s,'A',self.f.caller(VERSION,tool_then_continue),0)
        self.assertEqual(len(seen),2)
        self.assertTrue(all(not d['message_wait_guard']['message_wait_allowed'] for d in seen))
        self.assertEqual(seen[1]['message_wait_guard']['message_only_events'],['next_observation','listener:listener-1'])
        self.assertEqual(len(self.s['decisions']),1)

    def test_old_pinned_role_keeps_its_context_and_behavior(self):
        for a in 'BCD':self.park(a)
        self.app.turn(self.s,'A',self.f.caller('ai-tasks-v122.json',self.decision(['next_observation'])),0)
        data=next(d for task,d in self.f.inputs if task=='ensemble_role')
        self.assertNotIn('message_wait_guard',data['scheduling'])
        self.assertIn('A',self.s['role_waits'])

    def test_recovery_wakes_oldest_once_and_preserves_private_targets(self):
        self.all_waiting();self.s['role_waits']['C']['started_at']=-1
        self.s['tracked_events']=[{'id':'known','creator':'C','status':'active','description':'核对结果'}]
        self.s['role_waits']['C']['events']=['tracked:known']
        before=deepcopy(self.s)
        self.assertTrue(wait_progress.recover(self.s))
        self.assertEqual(set(self.s['role_waits']),set('ABD'))
        self.assertEqual([q['actor'] for q in self.s['agenda']],['C'])
        self.assertEqual(self.s['tracked_events'],before['tracked_events'])
        self.assertEqual(self.s['locations'],before['locations'])
        self.assertEqual(self.s['wait_results']['C']['status'],'cancelled')
        for a in 'ABD':self.assertEqual(self.s['observations'][a],before['observations'][a])
        self.assertFalse(wait_progress.recover(self.s))
        self.assertFalse(self.f.inputs)

    def test_same_stagnation_episode_visits_each_role_once_then_pauses(self):
        self.all_waiting()
        for a in w.ACTORS:
            self.assertTrue(wait_progress.recover(self.s))
            self.assertEqual([q['actor'] for q in self.s['agenda']],[a])
            self.park(a,['phase:conclusion'])
        self.assertTrue(wait_progress.recover(self.s))
        self.assertEqual(self.s['phase'],'paused')
        self.assertEqual(self.s['watch']['pause_reason'],'waiting_stalled')
        self.assertEqual(self.s['watch']['wait_recovery']['reconsidered'],list(w.ACTORS))
        self.assertFalse(wait_progress.recover(self.s))

    def test_real_work_and_pending_scheduling_take_precedence(self):
        self.all_waiting();initial=deepcopy(self.s)
        for kind in ('activity','chat','invitation','world','agenda'):
            with self.subTest(kind=kind):
                self.s=deepcopy(initial)
                if kind=='activity':self.s['activities'].append({'status':'running'})
                if kind=='chat':self.s['chats']['test']={'status':'active'}
                if kind=='invitation':self.s['invitations'].append({'status':'pending'})
                if kind=='world':self.s['world_due']=True
                if kind=='agenda':self.s['agenda'].append({'actor':'A'})
                before=canonical(self.s)
                self.assertFalse(wait_progress.recover(self.s));self.assertEqual(canonical(self.s),before)

    def test_recovery_only_runs_in_active_enabled_all_ai_spectator(self):
        self.all_waiting();initial=deepcopy(self.s)
        for key,value in (('phase','paused'),('humans',['A']),('message_wait_guard_version',0)):
            self.s=deepcopy(initial);self.s[key]=value;before=canonical(self.s)
            self.assertFalse(wait_progress.recover(self.s));self.assertEqual(canonical(self.s),before)
        self.s=deepcopy(initial);self.s.pop('watch');self.assertFalse(wait_progress.recover(self.s))

    def test_real_progress_resets_episode_but_receipts_or_clock_do_not(self):
        self.all_waiting();wait_progress.recover(self.s);self.park('A',['phase:conclusion'])
        self.s['watch']['clock']+=5
        wait_progress.recover(self.s)
        self.assertEqual(self.s['watch']['wait_recovery']['reconsidered'],['A','B'])
        self.park('B',['phase:conclusion'])
        w.acquire(self.s,'A','c1',w.emit(self.s,'inspect','A'),'fixture')
        self.s['agenda']=[]
        wait_progress.recover(self.s)
        self.assertEqual(len(self.s['watch']['wait_recovery']['reconsidered']),1)

    def test_background_reviews_before_waking_then_queues_only_one_role(self):
        self.all_waiting(['next_observation'])
        for wait in self.s['role_waits'].values():wait['review_pending']=True
        with patch.object(self.app,'adjudicate_ensemble') as review:
            spectator.background(self.app,self.s,self.f.caller(VERSION))
        review.assert_called_once();self.assertEqual(len(self.s['role_waits']),4)
        for a,wait in self.s['role_waits'].items():
            wait.update(review_pending=False,reviewed_circumstances=fingerprint(wait_lifecycle.circumstances(self.s,a)))
        with patch.object(self.app,'turn') as turn,patch.object(self.app,'adjudicate_ensemble') as review:
            spectator.background(self.app,self.s,self.f.caller(VERSION))
        turn.assert_not_called();review.assert_not_called()
        self.assertEqual(len(self.s['role_waits']),3);self.assertEqual(len(self.s['agenda']),1)
        self.assertEqual(self.s['watch']['clock'],4)

    def test_background_full_stalled_cycle_is_bounded(self):
        self.all_waiting()
        for _ in range(12):
            if self.s['phase']!='active':break
            spectator.background(self.app,self.s,self.f.caller(VERSION,self.decision(['phase:conclusion'])))
        self.assertEqual(self.s['phase'],'paused')
        self.assertEqual(self.s['watch']['pause_reason'],'waiting_stalled')
        self.assertEqual(len([t for t,d in self.f.inputs if t=='ensemble_role']),4)
        self.assertEqual(self.s['watch']['steps'],9)

    def test_running_activity_deadline_precedes_wait_timeout(self):
        event=w.apply_choice(self.s,'A','search')
        self.park('A',['activity:'+event['id']])
        for a in 'BCD':self.park(a,['phase:conclusion'])
        self.s['next_tick']=10
        with patch.object(self.app,'turn') as turn,patch.object(self.app,'adjudicate_ensemble'):
            spectator.background(self.app,self.s,self.f.caller(VERSION))
            self.assertEqual(self.s['watch']['clock'],10)
            self.assertEqual(len(self.s['role_waits']),4)
            spectator.background(self.app,self.s,self.f.caller(VERSION))
        turn.assert_not_called()
        self.assertFalse(w.running(self.s,'A'));self.assertNotIn('wait_recovery',self.s['watch'])

    def test_manual_resume_preserves_episode_but_explicit_stalled_resume_resets_it(self):
        self.all_waiting();self.s['phase']='paused'
        self.s['watch'].update(pause_reason='manual',wait_recovery={'reconsidered':['A']})
        owner=self.app.store.session()['id']
        s=self.app.store.create_game(owner,{'command_id':'wait_create','expected_game_id':None},lambda gid:dict(self.s,id=gid))
        s,_=spectator.command(self.app,owner,s,{'command_id':'wait_resume','expected_revision':s['revision'],'kind':'watch_resume'})
        self.assertEqual(s['watch']['wait_recovery']['reconsidered'],['A'])
        with self.app.store.transaction() as con:
            old=self.app.store.load(con,owner,s['id']);s=deepcopy(old)
            s['phase']='paused';s['watch']['pause_reason']='waiting_stalled';s['revision']+=1
            self.app.store.save(con,s,old)
        s,_=spectator.command(self.app,owner,s,{'command_id':'stalled_resume','expected_revision':s['revision'],'kind':'watch_resume'})
        self.assertNotIn('wait_recovery',s['watch']);self.assertEqual(s['phase'],'active')

    def test_rejected_reply_retries_once_and_restart_reuses_paid_stage(self):
        for a in 'BCD':self.park(a)
        owner=self.app.store.session()['id']
        s=self.app.store.create_game(owner,{'command_id':'retry_create','expected_game_id':None},lambda gid:dict(self.s,id=gid))
        original=self.f.provider;sent=[]
        def transport(body):
            response=original(body)
            if 'PALTER_TASK: ensemble_role\n' in body['messages'][0]['content']:
                sent.append(deepcopy(body));out=json.loads(response['choices'][0]['message']['content'])
                self.decision(['next_observation'] if len(sent)==1 else ['phase:conclusion'])('ensemble_role',out,{})
                response['choices'][0]['message']['content']=canonical(out)
            return response
        self.app.gateway.client.transport=transport
        command={'command_id':'guard_retry','expected_revision':s['revision'],'kind':'background'}
        builder=lambda state,call:self.app.turn(state,'A',call,0)
        saved,_=self.app.operate(owner,s['id'],command,builder)
        self.assertEqual(len(sent),2);self.assertIn('message_wait_allowed',canonical(sent[1]))
        self.assertEqual(len(saved['decisions']),1)
        self.app=EnsembleApplication(self.app.store.path,self.app.gateway.client)
        duplicate,_=self.app.operate(owner,s['id'],command,builder)
        self.assertEqual(len(sent),2);self.assertEqual(len(duplicate['decisions']),1)

    def test_new_prefix_only_adds_scoped_scheduling_guidance(self):
        old=deepcopy(self.app.gateway.versions['ai-tasks-v122.json'])
        new=deepcopy(self.app.gateway.versions[VERSION])
        self.assertEqual(new['ensemble_role'].pop('message_wait_guard_version'),1)
        for a,b in ((old['ensemble_role'],new['ensemble_role']),
                    (old['ensemble_role']['perspectives']['concealment'],new['ensemble_role']['perspectives']['concealment'])):
            before=a.pop('instruction');after=b.pop('instruction')
            self.assertTrue(after.startswith(before+'\n'))
            self.assertIn('消息等待许可',after[len(before):])
        self.assertEqual(old,new)


if __name__=='__main__':unittest.main()
