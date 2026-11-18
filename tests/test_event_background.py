"""A newly created wait retains known background without receiving a new message."""
from copy import deepcopy
import json
import unittest
from palter import ensemble_world as w, role_events, role_schedule, wait_lifecycle, context_economy, compact_context
from palter.deepseek import DeepSeek, Settings
from palter.ensemble import EnsembleApplication
from palter.storage import canonical, StoreError
from tests import test_ensemble_review as fixtures
from tests.compact_fixture import expand

VERSION='ai-tasks-v106.json'


class EventBackgroundTests(unittest.TestCase):
    def setUp(self):
        self.f=fixtures.ReviewFixTests();self.f.setUp();self.addCleanup(self.f.doCleanups)
        self.app,self.s=self.f.app,self.f.state
        self.app.gateway.current_version=VERSION
        self.app.configure_rules(self.s,self.f.caller(VERSION));self.s['agenda']=[]

    def wait(self,state=None,actor='A'):
        state=state or self.s
        state['agenda']=[q for q in state['agenda'] if q['actor']!=actor]
        role_schedule.commit(state,actor,{'mode':'wait','events':['next_observation'],'wait_reason':'等别人对原件的回应。'},role_schedule.context(state,actor))
        return state['role_waits'][actor]

    def decision(self,identity,sources):
        return {'id':identity,'status':'active','reason':'已经取得原件，仍可等待对方的回应。','progress':'等待回应。',
                'source_ids':sources,'basis':{'kind':'received_condition','workflow_stage':None}}

    def test_new_wait_keeps_pre_wait_speech_and_acquisition_without_advancing_cursor(self):
        speech=w.speak(self.s,'A','我先看这份原件。');w.apply_choice(self.s,'A','inspect:c1')
        wait=self.wait();before=deepcopy(self.s)
        records,contexts,allowed=role_events.package(self.s,'public',True,True)
        ctx=contexts['A'];self.assertEqual(ctx['received_records'],[])
        self.assertIn(speech['id'],allowed['A'])
        self.assertIn(self.s['observations']['A'][-1]['id'],allowed['A'])
        self.assertTrue(all(r['observation_index']<=wait['review_checkpoint'] for r in ctx['background_records']))
        record=records[0];self.assertEqual(record['review_range']['from_exclusive'],record['review_range']['through'])
        out={'event_decisions':[self.decision(wait['id'],[speech['id']])]}
        role_events.validate_decisions(out,records,allowed)
        self.assertEqual(self.s,before)
        role_events.apply(self.s,out['event_decisions'],'fixture',{wait['id']:record['review_range']['through']})
        role_schedule.reconcile(self.s)
        self.assertIn('A',self.s['role_waits']);self.assertEqual(role_events.scopes_due(self.s),set())
        w.speak(self.s,'B','我现在回应这份材料。');role_schedule.reconcile(self.s)
        self.assertNotIn('A',self.s['role_waits'])

    def test_new_rows_and_prior_support_are_distinct_and_full_sources_survive_pooling(self):
        old=w.speak(self.s,'B','此前收到的背景。');wait=self.wait()
        new=w.speak(self.s,'B','这才是等待后收到的消息。')
        records,ctx,allowed=role_events.package(self.s,'public',True,True)
        self.assertIn(old['id'],{r['event_id'] for r in ctx['A']['background_records']})
        self.assertEqual([r['event_id'] for r in ctx['A']['received_records']],[new['id']])
        wire=context_economy.deduplicate_dm(compact_context.pack('ensemble_dm',{'tracked_events':records,'event_recipient_contexts':ctx,'utterances':[]},authorized_keys=True))
        restored=expand(wire)['event_recipient_contexts']['A']
        self.assertEqual(restored['received_records'][0]['text'],'这才是等待后收到的消息。')
        self.assertGreater(restored['received_records'][0]['observation_index'],wait['review_checkpoint'])

    def test_background_is_bounded_and_excludes_unheard_private_messages(self):
        for i in range(30):w.note(self.s,'A',w.emit(self.s,'fixture'),'背景'+str(i)+'内容'*50)
        w.note(self.s,'B',w.emit(self.s,'private_fact'),'OTHER_PRIVATE_CANARY')
        self.wait();records,ctx,allowed=role_events.package(self.s,'public',True,True)
        self.assertLessEqual(len(ctx['A']['background_records']),6)
        self.assertNotIn('OTHER_PRIVATE_CANARY',canonical(ctx))
        foreign=self.s['observations']['B'][-1]['id']
        with self.assertRaises(role_events.EventSourceError) as caught:
            role_events.validate_decisions({'event_decisions':[self.decision(records[0]['id'],[foreign])]},records,allowed)
        feedback=caught.exception.feedback
        self.assertEqual(feedback['invalid_sources'],[foreign]);self.assertEqual(feedback['allowed_sources'],sorted(allowed['A']))
        self.assertNotIn(foreign,feedback['allowed_sources'])

    def test_private_wait_retains_own_speech_but_not_outside_speech(self):
        w.apply_choice(self.s,'A','invite:B');w.apply_choice(self.s,'B','accept:i1')
        role_schedule.reconcile(self.s);self.s['agenda']=[]
        own=w.speak(self.s,'A','私聊内的已有发言。');self.wait()
        outside=w.speak(self.s,'C','OUTSIDE_PRIVATE_WAIT_CANARY')
        records,ctx,allowed=role_events.package(self.s,w.channel(self.s,'A'),True,True)
        self.assertIn(own['id'],allowed['A']);self.assertNotIn(outside['id'],allowed['A'])
        self.assertNotIn('OUTSIDE_PRIVATE_WAIT_CANARY',canonical(ctx))
        self.assertEqual(ctx['A']['received_records'],[])

    def test_old_pinned_projection_stays_empty_and_private_upgrade_never_enters_wire(self):
        w.speak(self.s,'A','已听到的背景。');self.wait()
        old=role_events.package(self.s,'public',True)
        new=role_events.package(self.s,'public',True,True)
        data={'tracked_events':old[0],'event_recipient_contexts':old[1],'utterances':[]}
        body,hash1=self.app.gateway.payload('ensemble_dm',{},data,'ai-tasks-v105.json')
        data['_event_review_upgrade']={'tracked_events':new[0],'event_recipient_contexts':new[1]}
        again,hash2=self.app.gateway.payload('ensemble_dm',{},data,'ai-tasks-v105.json')
        self.assertEqual(body,again);self.assertEqual(hash1,hash2)
        self.assertEqual(old[1]['A']['received_records'],[])
        self.assertNotIn('background_records',old[1]['A'])

    def test_pinned_retry_adds_background_and_recovers_paid_result_after_restart(self):
        self.app.gateway.current_version='ai-tasks-v105.json';self.app.gateway.retry_delays=(0,0,0)
        self.s['watch'].update(budget_usd=2,call_limit=128)
        owner=self.app.store.session()['id']
        def factory(identity):s=deepcopy(self.s);s['id']=identity;return s
        saved=self.app.store.create_game(owner,{'command_id':'event_background_case','expected_game_id':None},factory)
        calls=[]
        def provider(body):
            calls.append(body);data=expand(json.loads(body['messages'][2]['content']))
            event=data['utterances'][0]['id'];record=data['tracked_events'][0]
            if len(calls)==1:self.assertNotIn('background_records',data['event_recipient_contexts']['A'])
            else:
                self.assertEqual(data['validation_feedback']['event_context_repair'],1)
                self.assertIn(event,data['validation_feedback']['allowed_sources'])
                self.assertEqual(data['validation_feedback']['invalid_sources'],[])
                self.assertTrue(data['event_recipient_contexts']['A']['background_records'])
            out={'assessments':[],'cues':[],'disclosures':[],
                 'event_decisions':[self.decision(record['id'],[event])]}
            return {'choices':[{'finish_reason':'stop','message':{'content':canonical(out)}}]}
        self.app.gateway.client.transport=provider
        command={'command_id':'event_background_step','expected_revision':saved['revision'],'kind':'background'}
        def work(state,call):
            start=len(state['events']);w.speak(state,'A','我想核对原件。');w.apply_choice(state,'A','inspect:c1');self.wait(state)
            self.app.adjudicate_ensemble(state,start,call)
        def interrupted(state,call):work(state,call);raise StoreError('after paid DM',503,'connection_failed')
        def old_failure(state,call):
            def once(stage,task,baseline,data,validate,actor=None):
                return self.app.gateway._attempt(owner,saved['id'],command['command_id'],stage,task,baseline,data,validate,actor,call.prefix_version)
            once.prefix_version=call.prefix_version
            work(state,once)
        with self.assertRaises(StoreError):self.app.operate(owner,saved['id'],command,old_failure)
        # Simulate the generic source error persisted by the published v105 code.
        # Only this isolated fixture row is changed, before testing recovery.
        with self.app.store.transaction() as con:
            con.execute('UPDATE ai_calls SET validation_feedback=?',
                (canonical({'code':'event_decision_contract','instruction':'event decision source invalid'}),))
        with self.assertRaises(StoreError):self.app.operate(owner,saved['id'],command,interrupted)
        self.assertEqual(len(calls),2)
        with self.app.store.transaction(False) as con:before=[dict(r) for r in con.execute('SELECT * FROM ai_calls ORDER BY attempt')]
        self.app=EnsembleApplication(self.app.store.path,DeepSeek(Settings(api_key='fixture'),provider))
        state,_=self.app.operate(owner,saved['id'],command,work)
        self.assertEqual(len(calls),2);self.assertIn('A',state['role_waits'])
        with self.app.store.transaction(False) as con:self.assertEqual([dict(r) for r in con.execute('SELECT * FROM ai_calls ORDER BY attempt')],before)

    def test_background_never_skips_pending_custom_event_chunks(self):
        w.speak(self.s,'A','建立关注事项前的背景。')
        identity=role_events.request(self.s,'A',{'event_request':{'description':'等对方核对','completion_condition':'我收到核对结果','early_end_condition':''}})
        tracker=self.s['tracked_events'][0];start=tracker['checkpoint'];seen=[]
        for i in range(20):w.note(self.s,'A',w.emit(self.s,'fixture'),'后续'+str(i)+'完整记录'*100)
        while role_events.due(self.s,tracker):
            records,ctx,allowed=role_events.package(self.s,'public',True,True)
            seen.extend(r['id'] for r in ctx['A']['received_records'])
            record=records[0];decision=self.decision(identity,[])
            role_events.validate_decisions({'event_decisions':[decision]},records,allowed)
            role_events.apply(self.s,[decision],'fixture',{identity:record['review_range']['through']})
        self.assertEqual(seen,[r['id'] for r in self.s['observations']['A'][start:]])

    def test_new_version_changes_only_dm_context_policy(self):
        previous=self.app.gateway.versions['ai-tasks-v105.json'];current=self.app.gateway.versions[VERSION]
        for task,spec in current.items():
            if task=='ensemble_dm':
                self.assertEqual({k:v for k,v in spec.items() if k not in ('event_background_version','economy_guidance')},
                                 {k:v for k,v in previous[task].items() if k!='economy_guidance'})
            else:self.assertEqual(spec,previous[task])


if __name__=='__main__':unittest.main()
