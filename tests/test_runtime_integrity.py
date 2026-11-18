"""Source-scoped facts, structured conclusions and engineering-owned transitions."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import unittest

from palter import (ensemble_world as w, spectator, source_provenance, temporal_facts as timing,
                    final_arguments, role_schedule as schedule, role_events, event_tools,
                    wait_lifecycle, workflow_events, ensemble_review)
from palter.scenario_cases import build
from palter.storage import canonical
from tests.test_ensemble import story_fixture
from tests import test_ensemble_review as fixtures

VERSION='ai-tasks-v88.json'


class RuntimeIntegrityTests(unittest.TestCase):
    def setUp(self):
        self.f=fixtures.ReviewFixTests();self.f.setUp();self.addCleanup(self.f.doCleanups)
        self.app=self.f.app;self.prepare()

    def prepare(self,seed=19,rules=5):
        s=w.blank('abcd'*6,'murder',0,'after');spectator.initialize(s)
        s['preview']=deepcopy(self.f.state['preview']);s['closure']={'votes':[],'ready':False}
        w.initialize(s,build(story_fixture(),s['preview'],'murder',seed,[],rules_version=rules));w.start(s)
        self.s=s;self.app.configure_rules(s,self.f.caller(VERSION));s['agenda']=[]
        self.actor=next(a for a in 'ABCD' if a!=s['case']['solution']['killer'])

    def acquire(self,ids,actor=None):
        actor=actor or self.actor
        for cid in ids:w.acquire(self.s,actor,cid,w.emit(self.s,'inspect',actor,cid),'检查')

    def value(self,actor=None):
        return {'suspect':self.s['case']['solution']['killer'],'aspects':[
            {'aspect':a,'explanation':'我用实际取得的记录论证。','evidence_ids':ids,'testimony_ids':[],'gaps':''}
            for a,ids in [('identity',['c7','c9','c10']),('time',['c1','c2']),('method',['c4','c7','c10'])]]}

    def tool(self,end_on=None):
        args={'description':'等同伴回报','event_ids':[],'completion_condition':'同伴回来并说明检查结果。','early_end_condition':''}
        if end_on is not None:args['end_on']=end_on
        return {'id':'tool_1','type':'function','function':{'name':'create_event_listener','arguments':json.dumps(args)}}

    def test_points_durations_intersection_and_containment_are_distinct(self):
        self.acquire(['c1','c2','c9','c14']);data=timing.for_role(self.s,self.actor)
        facts={f['label']:f for f in data['facts']}
        self.assertEqual(facts['tool_custody']['duration_minutes'],18)
        self.assertEqual(facts['death_bounds_not_exact_death']['duration_minutes'],12)
        self.assertEqual(facts['tool_custody']['source_ids'][-2:],['c9','c14'])
        self.assertNotIn('duration_minutes',facts['last_verified_alive'])
        overlap=data['comparisons'][0]
        self.assertEqual(overlap['overlap']['duration_minutes'],9)
        self.assertFalse(overlap['left_contains_right']);self.assertFalse(overlap['right_contains_left'])
        self.assertNotIn('actual_crime',facts)

    def test_hidden_endpoint_and_different_clock_cannot_make_a_window(self):
        self.acquire(['c1']);data=timing.project(list(self.s['known'][self.actor].values()))
        self.assertFalse(any(f['kind']=='interval' for f in data['facts']))
        rows=[{'id':'a','temporal':[timing.interval('a',10,20,'one')]},
              {'id':'b','temporal':[timing.interval('b',15,25,'two')]}]
        self.assertEqual(timing.project(rows)['comparisons'],[])
        self.assertEqual(timing.interval('overnight',1435,1445)['duration_minutes'],10)
        with self.assertRaises(ValueError):timing.interval('ambiguous',1435,5)

    def test_clock_correction_needs_acquired_calibration(self):
        self.prepare(seed=18);self.acquire(['c3'])
        before=timing.project(list(self.s['known'][self.actor].values()))
        self.assertEqual(len(before['facts']),1)
        self.acquire(['c4']);after=timing.project(list(self.s['known'][self.actor].values()))
        self.assertEqual(after['facts'][-1]['minute'],18*60+18+6)
        self.assertEqual(after['facts'][-1]['source_ids'],['c3','c4'])

    def test_unverified_public_voice_does_not_reveal_playback(self):
        self.acquire(['c3'])
        self.assertEqual(self.s['known'][self.actor]['c3']['temporal'][0]['label'],'public_voice')
        self.assertNotIn('playback',canonical(timing.project(list(self.s['known'][self.actor].values()))))

    def test_old_cases_are_not_backfilled_or_given_new_proof_routes(self):
        self.prepare(rules=3);before=canonical(self.s['case']);self.acquire(['c1','c2','c9'])
        self.assertEqual(timing.for_role(self.s,self.actor),{'facts':[],'comparisons':[],'calibrations':[]})
        self.assertTrue(all('c3' in route for route in self.s['case']['proofs']['identity']))
        self.assertEqual(canonical(self.s['case']),before)

    def test_source_origins_remain_claims_even_when_mixed_with_a_record(self):
        a=self.actor;other=next(b for b in 'ABCD' if b!=a);self.acquire(['c4'])
        e=w.speak(self.s,other,'经手栏空着，我检查过。');sid=next(o['id'] for o in self.s['observations'][a] if o['event_id']==e['id'])
        row={'id':'m1','kind':'unresolved','text':'有人声称有空白栏，需要核对。','sources':['c4',sid]}
        self.s['memory'][a].update(entries=[row],sources=['c4',sid])
        data=w.context(self.s,a);origin=data['source_provenance']
        self.assertEqual(origin['c4']['kind'],'acquired_record');self.assertEqual(origin[sid],{'kind':'heard_claim','speaker':other})
        self.assertNotIn('经手栏',self.s['known'][a]['c4']['observation'])
        self.assertEqual(data['memory']['entries'],[row])
        own=w.speak(self.s,a,'我的说法。');own_id=next(o['id'] for o in self.s['observations'][a] if o['event_id']==own['id'])
        self.assertEqual(w.context(self.s,a)['source_provenance'][own_id]['kind'],'self_claim')

    def test_memory_wire_keeps_origin_index_and_only_scoped_numeric_facts(self):
        self.acquire(['c1']);a=self.actor;self.app.summarize_chunk(self.s,a,self.f.caller(VERSION),len(self.s['observations'][a]))
        data=next(d for task,d in reversed(self.f.inputs) if task=='ensemble_memory')
        payload,_=self.app.gateway.payload('ensemble_memory',w.baseline(self.s,a),data,VERSION)
        wire=json.loads(payload['messages'][-1]['content'])
        self.assertIn('source_provenance',wire);self.assertIn('temporal_facts',wire)
        self.assertNotIn('actual_crime',canonical(wire))

    def test_union_has_every_selected_aspect_source_without_inventing_any(self):
        self.acquire(['c1','c2','c4','c7','c9','c10','c3'])
        result=final_arguments.normalize(self.s,self.actor,self.value())
        self.assertEqual(set(result['evidence_ids']),{'c1','c2','c4','c7','c9','c10'})
        self.assertNotIn('c3',result['evidence_ids']);self.assertEqual(len(result['evidence_ids']),6)
        self.assertIn('时间边界',result['explanation'])
        self.assertEqual(result['aspects'],self.value()['aspects'])

    def test_final_structure_and_authorization_are_validated(self):
        self.acquire(['c1','c2','c4','c7','c9','c10'])
        for kind in ('missing','duplicate','unknown','unheard'):
            v=self.value()
            if kind=='missing':v['aspects'].pop()
            if kind=='duplicate':v['aspects'][0]['aspect']='time'
            if kind=='unknown':v['aspects'][0]['evidence_ids']=['c8']
            if kind=='unheard':v['aspects'][0]['testimony_ids']=['C-o999999']
            with self.subTest(kind=kind),self.assertRaises(ValueError):final_arguments.normalize(self.s,self.actor,v)
        v=self.value();v['suspect']=None
        self.assertIsNone(final_arguments.normalize(self.s,self.actor,v)['suspect'])
        v['suspect']=self.actor;self.assertEqual(final_arguments.normalize(self.s,self.actor,v)['suspect'],self.actor)

    def test_recording_verified_comparison_no_longer_requires_raw_precursor(self):
        self.acquire(['c1','c2','c4','c7','c9','c10'])
        self.s['submissions'][self.actor]=final_arguments.normalize(self.s,self.actor,self.value())
        review=ensemble_review.evaluate(self.s,self.actor,self.f.caller(VERSION))
        self.assertEqual(review['result'],'established')
        data=next(d for task,d in reversed(self.f.inputs) if task=='ensemble_theory')
        self.assertEqual(data['submitted_aspects'],self.value()['aspects'])
        self.assertTrue(data['temporal_facts']['comparisons'])
        # A semantic error remains a failure despite correct supplied arithmetic.
        def reject(task,out,data):
            next(c for c in out['claims'] if c['aspect']=='time').update(supported=False,reason='提交内容把交集误当作全部保管时长。')
        r=ensemble_review.evaluate(self.s,self.actor,self.f.caller(VERSION,reject))
        self.assertEqual(r['result'],'unproven');self.assertTrue(r['aspects']['time']['proof_covered'])

    def test_custom_end_on_waits_for_actual_quorum_and_resolves_once(self):
        receipt=event_tools.execute(self.s,'A',self.tool(['phase:conclusion']),'fixture_call')
        schedule.commit(self.s,'A',{'mode':'wait','events':[receipt['wait_event']]},schedule.context(self.s,'A'))
        tracker=self.s['tracked_events'][0]
        for actor in 'BC':
            w.apply_choice(self.s,actor,'close_vote:yes');schedule.reconcile(self.s)
            self.assertEqual(tracker['status'],'pending')
            self.assertEqual(workflow_events.context(self.s,'A')['stage'],'investigation')
        w.apply_choice(self.s,'D','close_vote:yes');schedule.reconcile(self.s);schedule.reconcile(self.s)
        self.assertEqual(tracker['status'],'cancelled');self.assertEqual(tracker['resolved_by'],'engine')
        self.assertEqual(workflow_events.context(self.s,'A')['stage'],'conclusion')
        self.assertEqual(sum(e['kind']=='tracking_resolved' for e in self.s['events']),1)
        self.assertEqual(sum(q['actor']=='A' for q in self.s['agenda']),1)
        self.assertFalse(self.f.inputs)

    def test_phase_listener_and_scoped_dm_circumstances(self):
        self.s['locations']['B']='r2'
        w.apply_choice(self.s,'B','close_vote:yes')
        ctx=workflow_events.context(self.s,'A')
        self.assertNotIn('B',ctx['known_agreements']);self.assertEqual(ctx['stage'],'investigation')
        data=schedule.context(self.s,'A');schedule.commit(self.s,'A',{'mode':'wait','events':['phase:conclusion']},data)
        schedule.reconcile(self.s);self.assertIn('A',self.s['role_waits'])
        self.assertEqual(wait_lifecycle.circumstances(self.s,'A')['workflow'],ctx)
        w.apply_choice(self.s,'C','close_vote:yes');w.apply_choice(self.s,'D','close_vote:yes');schedule.reconcile(self.s)
        self.assertNotIn('A',self.s['role_waits'])
        self.assertNotIn('phase:conclusion',{r['id'] for r in schedule.options(self.s,'A')})

    def test_early_private_close_ends_bound_tracker_without_dm(self):
        w.apply_choice(self.s,'B','invite:C');w.apply_choice(self.s,'C','accept:i1')
        chat=next(iter(self.s['chats'].values()))
        event_tools.execute(self.s,'A',self.tool(['conversation:'+chat['id']]),'fixture_call')
        w.apply_choice(self.s,'B','end_private');schedule.reconcile(self.s)
        self.assertEqual(self.s['tracked_events'][0]['status'],'cancelled');self.assertFalse(self.f.inputs)

    def test_native_listener_targets_are_authorized_and_replay_idempotent(self):
        with self.assertRaises(ValueError):event_tools.validate_call(self.s,'A',self.tool(['conversation:unseen']))
        t=self.tool(['phase:conclusion']);a=event_tools.execute(self.s,'A',t,'fixture_call');b=event_tools.execute(self.s,'A',t,'fixture_call')
        self.assertEqual(a,b);self.assertEqual(len(self.s['tracked_events']),1)
        self.s['locations']['A']='r3';schedule.reconcile(self.s)
        self.assertEqual(self.s['tracked_events'][0]['status'],'pending')

    def test_workflow_basis_rejects_premature_stage_and_unrequested_cancellation(self):
        event_tools.execute(self.s,'A',self.tool(),'fixture_call')
        w.apply_choice(self.s,'B','close_vote:yes')
        records,_,allowed=role_events.package(self.s,'public')
        value={'id':records[0]['id'],'status':'cancelled','reason':'已进入结案。','progress':'',
               'source_ids':[],'basis':{'kind':'workflow_transition','workflow_stage':'conclusion'}}
        before=canonical(self.s)
        with self.assertRaises(role_events.DecisionBasisError) as error:
            role_events.validate_decisions({'event_decisions':[value]},records,allowed)
        self.assertEqual(error.exception.feedback['actual_context']['workflow_stage'],'investigation')
        self.assertEqual(canonical(self.s),before)
        value['basis']={'kind':'owner_request','workflow_stage':None}
        with self.assertRaises(role_events.DecisionBasisError):role_events.validate_decisions({'event_decisions':[value]},records,allowed)
        value.update(status='active',basis={'kind':'current_circumstances','workflow_stage':None})
        role_events.validate_decisions({'event_decisions':[value]},records,allowed)

    def test_event_correction_retry_and_paid_recovery_keep_exact_requests(self):
        self.app.gateway.current_version=VERSION;self.app.gateway.retry_delays=(0,0,0)
        event_tools.execute(self.s,'A',self.tool(),'fixture_call');w.apply_choice(self.s,'B','close_vote:yes')
        self.s['watch']['budget_usd']=1
        owner=self.app.store.session()['id']
        def factory(gid):
            s=deepcopy(self.s);s['id']=gid;return s
        s=self.app.store.create_game(owner,{'command_id':'create_fixture','expected_game_id':None},factory)
        provider=self.app.gateway.client.transport;requests=[]
        def transport(payload):
            requests.append(deepcopy(payload));out=provider(payload)
            data=json.loads(payload['messages'][-1]['content'])
            if 'validation_feedback' not in data:
                result=json.loads(out['choices'][0]['message']['content'])
                result['event_decisions'][0].update(status='cancelled',reason='误把第一票当结案。',
                    basis={'kind':'workflow_transition','workflow_stage':'conclusion'})
                out['choices'][0]['message']['content']=json.dumps(result,ensure_ascii=False)
            else:self.assertEqual(data['validation_feedback']['code'],'event_decision_basis')
            return out
        self.app.gateway.client.transport=transport
        interrupted=True
        def work(state,call):
            self.app.adjudicate_ensemble(state,len(state['events']),call)
            if interrupted:raise RuntimeError('fixture interruption after paid DM result')
        command={'command_id':'verify_fixture','expected_revision':0,'kind':'probe'}
        with self.assertRaises(RuntimeError):self.app.operate(owner,s['id'],command,work)
        self.assertEqual(self.app.store.state(owner,s['id'])['tracked_events'][0]['status'],'pending')
        with self.app.store.transaction(False) as con:
            paid=dict(con.execute("SELECT * FROM ai_calls WHERE status='completed'").fetchone())
        self.assertEqual(len(requests),2);interrupted=False
        result,_=self.app.operate(owner,s['id'],command,work)
        self.assertEqual(len(requests),2);self.assertEqual(result['tracked_events'][0]['status'],'active')
        with self.app.store.transaction(False) as con:
            self.assertEqual(dict(con.execute('SELECT * FROM ai_calls WHERE id=?',(paid['id'],)).fetchone()),paid)

    def test_v88_remains_flash_no_thinking_and_preserves_published_files(self):
        task=self.app.gateway.versions[VERSION]['ensemble_dm']
        self.assertIn('{id,status,reason,progress,source_ids,basis:{kind,workflow_stage}}',task['instruction'])
        self.assertNotIn('each supplied tracker: {id,status,reason,progress,source_ids}.',task['instruction'])
        for task in self.app.gateway.versions[VERSION]:
            payload,_=self.app.gateway.payload(task,None,{},VERSION)
            self.assertEqual(payload['thinking'],{'type':'disabled'});self.assertNotIn('reasoning_effort',payload)
            self.assertEqual(payload['model'],'deepseek-flash')
        root=Path('palter/prefixes');manifest=json.loads((root/'manifest.json').read_text())
        for name,digest in manifest.items():self.assertEqual(hashlib.sha256((root/name).read_bytes()).hexdigest(),digest)


if __name__=='__main__':unittest.main()
