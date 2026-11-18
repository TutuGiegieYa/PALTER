"""Cost reductions preserve source boundaries, checkpoints and paid replay."""
from copy import deepcopy
import json
import unittest
from palter import (ensemble_world as w, ensemble_context, memory_entries, memory_policy,
                    delta_updates, context_economy, role_events, wait_lifecycle, compact_context, dm_repairs)
from palter.ai_gateway import request_sizes
from palter.storage import StoreError, canonical
from palter.ensemble import EnsembleApplication
from palter.deepseek import DeepSeek, Settings
from tests import test_ensemble_review as fixtures
from tests.compact_fixture import expand

VERSION='ai-tasks-v105.json'


class ContextEconomyTests(unittest.TestCase):
    def setUp(self):
        self.f=fixtures.ReviewFixTests();self.f.setUp();self.addCleanup(self.f.doCleanups)
        self.app=self.f.app;self.s=self.f.state;self.app.gateway.current_version=VERSION
        self.app.configure_rules(self.s,self.f.caller(VERSION));self.s['agenda']=[]

    def data(self):
        data=w.context(self.s,'A');ensemble_context.project(self.s,'A',data,True,True)
        self.app.conversation_context(self.s,'A',data,self.f.caller(VERSION),'ensemble_role')
        data['decision_mode']='investigation';return data

    def proposal(self,actor):
        return role_events.request(self.s,actor,{'event_request':{'description':'等待实际说明',
            'completion_condition':'收到关于此事的明确答复','early_end_condition':'不再可行'}})

    def active(self,identity):
        event=next(e for e in self.s['tracked_events'] if e['id']==identity);a=event['creator']
        event.update(status='active',checkpoint=len(self.s['observations'][a]),
            reviewed_circumstances=role_events.fingerprint(wait_lifecycle.circumstances(self.s,a)))
        return event

    def test_field_deltas_preserve_text_and_sources_and_validate_authority(self):
        source=self.s['observations']['A'][0]['id'];old={'id':'m7','kind':'unresolved','text':'我还需核实。','sources':[source]}
        self.s['memory']['A']['entries']=[old]
        row=w.emit(self.s,'test');w.note(self.s,'A',row,'新信息');new=self.s['observations']['A'][-1]['id']
        raw={'memory_update':{'upsert':[{'id':'m7','sources_add':[new]}],'processed_through':new}}
        before=deepcopy(self.s);out=delta_updates.expand(self.s,'A',raw)
        self.assertEqual(self.s,before);self.assertEqual(out['memory_update']['upsert'][0]['text'],old['text'])
        memory_entries.apply(self.s,'A',out['memory_update'],{r['id'] for r in self.s['observations']['A']})
        self.assertEqual(self.s['memory']['A']['entries'][0]['sources'],[source,new])
        bad=delta_updates.expand(self.s,'A',{'memory_update':{'upsert':[{'id':'m7','sources_add':['B-o99999']}],'processed_through':None}})
        with self.assertRaises(memory_entries.EntrySourcesError):memory_entries.revised(self.s,'A',bad['memory_update'],set())
        for patch in ({'id':'m7','sources':[source],'sources_add':[new]}, {'id':'m7','sources_remove':['unknown']}, {'id':'m8','text':'incomplete'}):
            with self.assertRaises(ValueError):delta_updates.expand(self.s,'A',{'memory_update':{'upsert':[patch],'processed_through':None}})

    def test_ack_only_is_explicit_and_cannot_skip_unsupplied_receipts(self):
        before=deepcopy(memory_entries.entries(self.s['memory']['A']));last=self.s['observations']['A'][-1]['id']
        patch=delta_updates.expand(self.s,'A',{'memory_update':{'processed_through':last}})['memory_update']
        with self.assertRaises(ValueError):memory_entries.revised(self.s,'A',patch,set())
        memory_entries.apply(self.s,'A',patch,{o['id'] for o in self.s['observations']['A']})
        self.assertEqual(memory_entries.entries(self.s['memory']['A']),before)
        self.assertEqual(self.s['memory']['A']['checkpoint'],len(self.s['observations']['A']))
        self.assertFalse(self.s.get('memory_archive'))

    def test_partial_private_interpretations_retain_unmodified_fields(self):
        self.s['beliefs']['A']={'suspect':'B','explanation':'旧判断','evidence_ids':[],'testimony_ids':[]}
        out=delta_updates.expand(self.s,'A',{'belief_update':{'patch':{'explanation':'新判断'}}})
        self.assertEqual(out['belief_update'],{**self.s['beliefs']['A'],'explanation':'新判断'})
        self.assertEqual(self.s['beliefs']['A']['explanation'],'旧判断')
        self.s.setdefault('strategies',{})['B']={'situation':'局面','plan':'旧计划','sources':[]}
        out=delta_updates.expand(self.s,'B',{'strategy_update':{'patch':{'plan':'新计划'}}})
        self.assertEqual(out['strategy_update'],{'situation':'局面','plan':'新计划','sources':[]})

    def test_memory_delta_ignores_unused_annotations_without_archiving_them(self):
        source=self.s['observations']['A'][0]['id']
        self.s['memory']['A']['entries']=[{'id':'m0','kind':'observed','text':'已有记录','sources':[source]}]
        raw={'memory_update':{'upsert':[{'id':'m0','text':'更新后的记录','sources_note':None}],
                              'processed_through':None}}
        patch=delta_updates.expand(self.s,'A',raw)['memory_update']
        memory_entries.apply(self.s,'A',patch,set())
        self.assertNotIn('sources_note',canonical(self.s['memory']))
        self.assertNotIn('sources_note',canonical(self.s.get('memory_archive',{})))
        self.assertIn('sources_note',raw['memory_update']['upsert'][0])

    def test_full_turn_uses_partial_memory(self):
        source=self.s['observations']['A'][0]['id'];self.s['memory']['A']['entries']=[{'id':'m0','kind':'observed','text':'原文','sources':[source]}]
        def transform(task,out,data):
            if task=='ensemble_role':out['memory_update']={'upsert':[{'id':'m0','text':'我记录当前经历。'}],'processed_through':None}
        self.app.turn(self.s,'A',self.f.caller(VERSION,transform),0)
        self.assertEqual(self.s['memory']['A']['entries'][0]['sources'],[source])
        self.assertEqual(self.s['memory']['A']['entries'][0]['text'],'我记录当前经历。')

    def test_conditional_guidance_does_not_change_fixed_prefix_or_leak_private_context(self):
        data=self.data();baseline=w.baseline(self.s,'A');data['conclusion_task']={'final':False}
        a,ha=self.app.gateway.payload('ensemble_role',baseline,data,VERSION)
        data['conclusion_task']={'final':True,'submission_format':'per_aspect','dimensions':['identity','time','method']}
        b,hb=self.app.gateway.payload('ensemble_role',baseline,data,VERSION)
        self.assertEqual(ha,hb);self.assertEqual(a['messages'][:2],b['messages'][:2])
        self.assertNotIn('final_submission',json.loads(a['messages'][2]['content']).get('active_guidance',{}))
        self.assertIn('final_submission',json.loads(b['messages'][2]['content'])['active_guidance'])
        self.assertNotIn('B_PRIVATE_SECRET_CANARY',canonical(a))
        data['conclusion_task']['final']=False;data['conversation']['channel']='p1'
        c,_=self.app.gateway.payload('ensemble_role',baseline,data,VERSION)
        self.assertIn('private_conversation',json.loads(c['messages'][2]['content'])['active_guidance'])
        data['conversation']['channel']='public'
        d,_=self.app.gateway.payload('ensemble_role',baseline,data,VERSION)
        self.assertNotIn('private_conversation',json.loads(d['messages'][2]['content']).get('active_guidance',{}))

    def test_dm_dedup_preserves_creator_scope_and_distinct_occurrences(self):
        w.apply_choice(self.s,'A','inspect:c1');e=w.speak(self.s,'A','重复的话')
        self.proposal('A');records,contexts,_=role_events.package(self.s,'public',True)
        data={'utterances':[e],'tracked_events':records,'event_recipient_contexts':contexts}
        old=deepcopy(data);wire=compact_context.pack('ensemble_dm',data,authorized_keys=True)
        compact=context_economy.deduplicate_dm(wire);restored=expand(compact)
        text=self.s['known']['A']['c1']['observation']
        self.assertEqual(sum(b.get('observation')==text for b in compact['sources'].values()),1)
        self.assertEqual(restored['event_recipient_contexts']['A']['acquired_evidence'][0]['observation'],text)
        self.assertEqual(data,old);self.assertNotIn('B_PRIVATE_SECRET_CANARY',canonical(compact))
        self.assertEqual(restored['utterances'][0]['facts']['speaker_knowledge']['evidence'][0]['id'],'c1')

    def test_only_changed_creators_are_reviewed_even_during_other_speech(self):
        a=self.proposal('A');b=self.proposal('B');self.active(a);self.active(b)
        event=w.emit(self.s,'private_receipt');w.note(self.s,'A',event,'只有我收到')
        records,contexts,_=role_events.package(self.s,'public',True)
        self.assertEqual([r['id'] for r in records],[a]);self.assertEqual(set(contexts),{'A'})
        legacy=role_events.package(self.s,'public')[0];self.assertEqual({r['id'] for r in legacy},{a,b})

    def test_pending_receipt_chunks_are_chronological_and_never_skip_history(self):
        identity=self.proposal('A');event=self.active(identity);start=event['checkpoint']
        for i in range(30):w.note(self.s,'A',w.emit(self.s,'fact'),str(i)+'细节'*160)
        seen=[];steps=0
        while role_events.due(self.s,event):
            records,contexts,allowed=role_events.package(self.s,'public',True);record=records[0]
            seen.extend(o['id'] for o in contexts['A']['received_records'])
            decision={'id':identity,'status':'active','reason':'仍需后续资料','progress':'保留已收到部分','source_ids':[],
                      'basis':{'kind':'received_condition','workflow_stage':None}}
            if record['review_range']['remaining']:
                with self.assertRaises(ValueError):role_events.validate_decisions({'event_decisions':[{**decision,'status':'cancelled'}]},records,allowed)
            role_events.validate_decisions({'event_decisions':[decision]},records,allowed)
            role_events.apply(self.s,[decision],'fixture',{identity:record['review_range']['through']});steps+=1
            self.assertLess(steps,31)
        self.assertGreater(steps,1);self.assertEqual(seen,[o['id'] for o in self.s['observations']['A'][start:]])
        self.assertEqual(event['checkpoint'],len(self.s['observations']['A']))

    def test_short_nine_entries_do_not_compact_but_1024_characters_still_do(self):
        source=self.s['observations']['A'][0]['id'];self.s['memory']['A']['entries']=[{'id':f'm{i}','kind':'unresolved','text':'待查','sources':[source]} for i in range(9)]
        self.assertFalse(memory_policy.needed(self.s,'A',token_budget=True,text_budget=1024,entry_trigger=12))
        self.s['memory']['A']['entries'][0]['text']='长'*(1024-16)
        self.assertTrue(memory_policy.needed(self.s,'A',token_budget=True,text_budget=1024,entry_trigger=12))

    def test_loop_context_is_scoped_optional_and_does_not_force_an_action(self):
        self.assertIsNone(context_economy.loop_context(self.s,'A'))
        self.s['decisions']=[{'actor':'A','choice':'wait'} for _ in range(3)]+[{'actor':'B','choice':'inspect:private-canary'}]
        before=deepcopy(self.s);value=context_economy.loop_context(self.s,'A')
        self.assertEqual(value['recent_own_choices'],['wait']*3);self.assertNotIn('private-canary',canonical(value));self.assertEqual(self.s,before)

    def test_new_prompt_is_smaller_without_changing_other_task_caps(self):
        data=self.data();base=w.baseline(self.s,'A')
        old,_=self.app.gateway.payload('ensemble_role',base,data,'ai-tasks-v103.json')
        new,_=self.app.gateway.payload('ensemble_role',base,data,VERSION)
        self.assertLess(request_sizes(new,2)['total_bytes'],request_sizes(old,2)['total_bytes']*.7)
        for task,spec in self.app.gateway.versions[VERSION].items():
            prior=self.app.gateway.versions['ai-tasks-v103.json'][task]
            self.assertEqual(spec['tokens'],prior['tokens']);self.assertEqual(spec['thinking'],prior['thinking'])
            if task not in ('ensemble_role','ensemble_dm','ensemble_memory'):self.assertEqual(spec,prior)

    def test_final_view_preserves_fixture_proof_bodies_and_source_access(self):
        for clue in self.s['case']['clues']:
            receipt=w.emit(self.s,'inspect','A',clue['id']);w.acquire(self.s,'A',clue['id'],receipt,'inspection')
        for _ in range(20):w.note(self.s,'A',w.emit(self.s,'fixture_receipt'),'我仍需核对材料。')
        data=self.data();data['conclusion_task']={'final':True,'submission_format':'per_aspect'}
        body,_=self.app.gateway.payload('ensemble_role',w.baseline(self.s,'A'),data,VERSION)
        view=json.loads(body['messages'][2]['content'])
        for identity in ('c1','c2','c3','c4','c7','c10','c11','c12'):
            self.assertEqual(view['sources'][identity]['observation'],self.s['known']['A'][identity]['observation'])
        self.assertEqual(view['source_access']['missing_body'],'on_demand_not_unknown')

    def test_event_repair_does_not_freeze_invalid_or_duplicate_judgments(self):
        self.proposal('A');self.proposal('B')
        records,_,allowed=role_events.package(self.s,'public',True)
        good={'id':records[0]['id'],'status':'active','reason':'尚待进展','progress':'','source_ids':[],
              'basis':{'kind':'current_circumstances','workflow_stage':None}}
        for rows in ([{**good,'id':'foreign'}],[good,good],[{**good,'source_ids':['B-private-unheard']}],
                     [{**good,'status':'invented'}]):
            error=ValueError('invalid judgments');error.feedback={}
            dm_repairs.attach(error,{'event_decisions':rows},records,allowed)
            self.assertNotIn('dm_event_repair',error.feedback)
        feedback={'dm_event_repair':1,'missing_ids':[records[1]['id']],
                  'validated_result':{'event_decisions':[good],'assessments':[]}}
        before=deepcopy(feedback)
        for rows in ([],[good],[{**good,'id':records[1]['id']}]*2):
            with self.assertRaises(ValueError):context_economy.merge_event_repair({'event_decisions':rows},feedback)
        self.assertEqual(feedback,before)

    def test_missing_dm_judgment_repairs_only_missing_records_and_replays_paid_result(self):
        self.proposal('A');self.proposal('B');self.s['phase']='active';self.s['watch'].update(budget_usd=2,call_limit=128)
        owner=self.app.store.session()['id']
        def factory(identity):s=deepcopy(self.s);s['id']=identity;return s
        saved=self.app.store.create_game(owner,{'command_id':'create_repair_test','expected_game_id':None},factory)
        calls=[]
        def provider(body):
            data=json.loads(body['messages'][2]['content']);calls.append(body)
            records=data['tracked_events'];selected=records[:1] if len(calls)==1 else records
            decisions=[{'id':r['id'],'status':'active','reason':'等待实际进展','progress':'','source_ids':[],
                'basis':{'kind':'current_circumstances','workflow_stage':None}} for r in selected]
            out={'event_decisions':decisions}
            if len(calls)==1:out.update(assessments=[],cues=[],disclosures=[])
            else:
                self.assertEqual(len(records),1);self.assertEqual(data['utterances'],[]);self.assertTrue(data['dm_event_repair'])
            return {'choices':[{'finish_reason':'stop','message':{'content':canonical(out)}}]}
        self.app.gateway.client.transport=provider;self.app.gateway.retry_delays=(0,0,0)
        command={'command_id':'repair_missing_dm','expected_revision':saved['revision'],'kind':'background'}
        def work(state,call):self.app.adjudicate_ensemble(state,len(state['events']),call)
        def interrupted(state,call):work(state,call);raise StoreError('after paid DM',503,'connection_failed')
        with self.assertRaises(StoreError):self.app.operate(owner,saved['id'],command,interrupted)
        self.assertEqual(len(calls),2)
        self.assertEqual([e['status'] for e in self.app.store.state(owner,saved['id'])['tracked_events']],['pending','pending'])
        with self.app.store.transaction(False) as con:before=[dict(r) for r in con.execute('SELECT * FROM ai_calls ORDER BY attempt')]
        self.assertIn('dm_event_repair',json.loads(before[1]['request_feedback']))
        self.app=EnsembleApplication(self.app.store.path,DeepSeek(Settings(api_key='fixture'),provider))
        state,_=self.app.operate(owner,saved['id'],command,work)
        self.assertEqual(len(calls),2);self.assertEqual([e['status'] for e in state['tracked_events']],['active','active'])
        with self.app.store.transaction(False) as con:self.assertEqual([dict(r) for r in con.execute('SELECT * FROM ai_calls ORDER BY attempt')],before)


if __name__=='__main__':unittest.main()
