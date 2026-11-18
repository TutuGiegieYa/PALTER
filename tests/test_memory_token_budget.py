"""Memory completion tokens replace text ceilings without weakening provenance."""
from copy import deepcopy
import json
import unittest

from palter import ensemble_world as w, memory_entries as memory, memory_policy as policy
from palter.ai_gateway import decode_response
from palter.storage import StoreError,canonical
from tests import test_ensemble_review as fixtures

VERSION='ai-tasks-v99.json'


class MemoryTokenBudgetTests(unittest.TestCase):
    def setUp(self):
        f=fixtures.ReviewFixTests();f.setUp();self.addCleanup(f.doCleanups)
        self.f=f;self.app=f.app;self.s=f.state;self.app.gateway.current_version=VERSION
        self.app.gateway.retry_delays=(0,0,0);self.app.configure_rules(self.s,lambda:None)
        w.speak(self.s,'A','我声称会检查，仍待执行。')
        self.source=self.s['observations']['A'][-1]['id'];self.end=len(self.s['observations']['A'])

    def rows(self,length=1800,count=2):
        return [{'id':f'm{i}','kind':'self_claim','sources':[self.source],
                 'text':'我'*(length//count+(i<length%count))} for i in range(count)]

    def snapshot(self,length=900,count=2):
        return {'entries':self.rows(length,count),'processed_through':self.source}

    def caller(self,out,version=VERSION,inputs=None):
        def call(stage,task,baseline,data,validate,actor=None):
            payload,_=self.app.gateway.payload(task,baseline,data,version)
            if inputs is not None:inputs.append(payload)
            validate(out);return deepcopy(out),'token-budget-fixture'
        call.prefix_version=version;return call

    def seed(self,length=1800,count=2):
        rows=self.rows(length,count)
        self.s['memory']['A']={'entries':rows,'summary':'\n'.join(r['text'] for r in rows),
                             'sources':[self.source],'checkpoint':self.end}

    def test_long_complete_snapshot_is_accepted_for_current_and_pinned_recovery(self):
        for version in ('ai-tasks-v69.json','ai-tasks-v97.json','ai-tasks-v98.json',VERSION):
            with self.subTest(version=version):
                state=deepcopy(self.s);out=self.snapshot(1800);before=deepcopy(state)
                self.app.summarize_chunk(state,'A',self.caller(out,version),self.end)
                self.assertEqual(state['memory']['A']['entries'],out['entries'])
                self.assertEqual(state['memory']['A']['checkpoint'],self.end)
                for key in ('observations','events','known','case'):self.assertEqual(state[key],before[key])

    def test_full_role_patch_has_no_per_entry_total_or_derived_summary_character_cap(self):
        for version in ('ai-tasks-v97.json',VERSION):
            state=deepcopy(self.s)
            def update(task,out,data):
                if task=='ensemble_role':out['memory_update']={'upsert':self.rows(2400,3),'archive':[],
                                                            'processed_through':self.source}
            self.app.turn(state,'A',self.f.caller(version,update),0)
            self.assertEqual(state['memory']['A']['entries'],self.rows(2400,3))

    def test_new_wire_has_token_budget_and_no_character_capacity_or_targets(self):
        inputs=[]
        self.app.summarize_chunk(self.s,'A',self.caller(self.snapshot(),inputs=inputs),self.end)
        body=inputs[0];wire=json.loads(body['messages'][2]['content'])
        self.assertEqual(body['max_tokens'],2048)
        self.assertEqual(body['thinking'],{'type':'disabled'})
        self.assertEqual(wire['snapshot_limits'],{'entries':12})
        for field in ('memory','memory_maintenance','snapshot_limits'):
            self.assertNotIn('text_characters',canonical(wire[field]))
        self.assertEqual(wire['memory_maintenance']['output_budget'],'request.max_tokens')
        for spec in (self.app.gateway.versions[VERSION]['ensemble_memory'],
                     self.app.gateway.versions[VERSION]['ensemble_role'],
                     *self.app.gateway.versions[VERSION]['ensemble_role']['perspectives'].values()):
            for obsolete in ('950','400-550','150-250','400 characters per entry','8 sources per entry','30 unique sources'):
                self.assertNotIn(obsolete,spec['instruction'])

    def test_memory_length_alone_no_longer_triggers_compaction(self):
        self.seed(6000)
        self.assertFalse(policy.needed(self.s,'A',token_budget=True))
        self.assertTrue(policy.needed(self.s,'A',context_pressure=True,token_budget=True))
        policy.record(self.s,'A',policy.stats(self.s['memory']['A']),token_budget=True)
        self.assertFalse(policy.needed(self.s,'A',context_pressure=True,token_budget=True))
        self.assertNotIn('text_characters',canonical(self.s['memory_compactions']['A']))
        self.s['memory']['A']['entries'][0]['text']+='新信息'
        self.assertTrue(policy.needed(self.s,'A',context_pressure=True,token_budget=True))

    def test_entry_pressure_and_chronological_chunks_still_consolidate_without_idle_repeats(self):
        self.seed(1800,9)
        self.assertTrue(policy.needed(self.s,'A',token_budget=True))
        calls=[];out=self.snapshot();out['processed_through']=None
        self.assertTrue(self.app.compact(self.s,'A',self.caller(out,inputs=calls)))
        self.assertFalse(self.app.compact(self.s,'A',self.caller(out,inputs=calls)))
        self.assertEqual(len(calls),1)
        for i in range(25):w.note(self.s,'A',w.emit(self.s,'observation','A'),f'新记录{i}')
        out['processed_through']=self.s['observations']['A'][-1]['id']
        self.assertTrue(self.app.compact(self.s,'A',self.caller(out,inputs=calls)))
        self.assertEqual(len(calls),2)

    def test_unrelated_tasks_and_provider_caps_are_unchanged(self):
        old=self.app.gateway.versions['ai-tasks-v98.json'];new=self.app.gateway.versions[VERSION]
        self.assertEqual(set(new),set(old))
        for task in old:
            expected=deepcopy(old[task])
            if task=='ensemble_memory':
                expected['tokens']=2048
                expected['instruction']=expected['instruction'].replace('(6144 tokens for this task)',
                                                                      '(2048 tokens for this task)')
            self.assertEqual(expected,new[task])

    def test_retired_text_feedback_is_corrected_only_on_copy(self):
        old={'code':'memory_capacity','scope':'snapshot','actual':{'entries':8,'text_characters':1154},
             'limits':{'entries':12,'text_characters':950}}
        before=deepcopy(old);out=memory.correction_feedback(old)
        self.assertEqual(old,before);self.assertEqual(out['limits'],{'entries':12})
        self.assertEqual(out['exceeded'],{});self.assertFalse(out['text_character_limited'])

    def stored_work(self,provider):
        self.app.gateway.client.transport=provider
        self.s['watch'].update(budget_usd=2,call_limit=512)
        owner=self.app.store.session()['id']
        saved=self.app.store.create_game(owner,{'command_id':'token_create','expected_game_id':None},
                                         lambda gid:dict(deepcopy(self.s),id=gid))
        command={'command_id':'token_operation','expected_revision':saved['revision'],'kind':'probe'}
        def work(state,call):self.app.summarize_chunk(state,'A',call,self.end)
        return owner,saved,command,work

    def test_truncation_feedback_keeps_token_cap_and_paid_stage_replays_exactly(self):
        requests=[];out=self.snapshot()
        def provider(body):
            requests.append(deepcopy(body))
            truncated=len(requests)==1
            return {'choices':[{'finish_reason':'length' if truncated else 'stop',
                'message':{'content':'{"entries":[' if truncated else canonical(out)}}]}
        owner,saved,command,work=self.stored_work(provider)
        def interrupted(state,call):
            work(state,call);raise StoreError('fixture after completed paid memory',503,'connection_failed')
        with self.assertRaises(StoreError):self.app.operate(owner,saved['id'],command,interrupted)
        self.assertEqual(self.app.store.state(owner,saved['id'])['memory'],saved['memory'])
        with self.app.store.transaction(False) as con:before=[dict(r) for r in con.execute('SELECT * FROM ai_calls ORDER BY attempt')]
        self.assertEqual([r['status'] for r in before],['failed','completed'])
        self.assertEqual([p['max_tokens'] for p in requests],[2048,2048])
        wire=json.loads(requests[1]['messages'][2]['content'])
        self.assertEqual(wire['validation_feedback']['code'],'memory_output_truncated')
        self.assertIsNone(before[0]['result'])
        state,_=self.app.operate(owner,saved['id'],command,work)
        self.assertEqual(state['memory']['A']['entries'],out['entries']);self.assertEqual(len(requests),2)
        with self.app.store.transaction(False) as con:self.assertEqual([dict(r) for r in con.execute('SELECT * FROM ai_calls ORDER BY attempt')],before)

    def test_four_truncations_pause_without_partial_memory_or_automatic_token_increase(self):
        requests=[]
        def provider(body):
            requests.append(deepcopy(body))
            # Even syntactically valid content is incomplete when the provider says length.
            return {'choices':[{'finish_reason':'length','message':{'content':canonical(self.snapshot())}}]}
        owner,saved,command,work=self.stored_work(provider)
        with self.assertRaises(StoreError) as error:self.app.operate(owner,saved['id'],command,work)
        self.assertEqual(error.exception.code,'retry_exhausted')
        self.assertEqual([p['max_tokens'] for p in requests],[2048]*4)
        self.assertEqual(self.app.store.state(owner,saved['id'])['memory'],saved['memory'])
        with self.assertRaises(StoreError):self.app.operate(owner,saved['id'],command,work)
        self.assertEqual(len(requests),4)


if __name__=='__main__':unittest.main()
