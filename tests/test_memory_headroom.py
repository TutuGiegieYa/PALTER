"""Summary reserve, bounded repair and paid-stage compatibility."""
from copy import deepcopy
import json
import unittest

from palter import memory_entries as memory, memory_policy, memory_headroom, working_context
from palter.ai_gateway import decode_response
from palter.ensemble import EnsembleApplication
from palter.storage import StoreError,canonical,fingerprint
from tests import test_memory_token_budget as fixtures

VERSION='ai-tasks-v122.json'


class MemoryHeadroomTests(unittest.TestCase):
    def setUp(self):
        self.f=fixtures.MemoryTokenBudgetTests();self.f.setUp();self.addCleanup(self.f.doCleanups)
        self.app=self.f.app;self.s=self.f.s;self.app.gateway.current_version=VERSION

    def test_summary_rejects_seven_even_when_short_but_active_memory_accepts_twelve(self):
        for count in (7,12):
            with self.assertRaises(memory.CapacityError) as caught:
                memory.validate_snapshot(self.f.rows(300,count),text_budget=1024,entry_limit=6)
            feedback=memory.correction_feedback(caught.exception.feedback)
            self.assertEqual(feedback['limits'],{'entries':6,'text_characters':1023})
            self.assertEqual(feedback['exceeded']['entries']['reduce_by_at_least'],count-6)
            self.assertNotIn('repair_contract',feedback)
        memory.validate_snapshot(self.f.rows(300,6),text_budget=1024,entry_limit=6)
        memory.validate_snapshot(self.f.rows(300,12))  # Historical paid snapshots.
        patch={'upsert':self.f.rows(600,12),'archive':[],'processed_through':self.f.source}
        revised,_=memory.revised(self.s,'A',patch,{o['id'] for o in self.s['observations']['A']})
        self.assertEqual(len(revised['entries']),12)

    def test_context_and_validator_agree_and_six_slots_accept_new_information(self):
        inputs=[];self.f.seed(600,12)
        output=self.f.snapshot(600,6);output['processed_through']=None
        before=deepcopy(self.s)
        self.app.summarize_chunk(self.s,'A',self.f.caller(output,VERSION,inputs),self.f.end)
        wire=json.loads(inputs[0]['messages'][2]['content'])
        self.assertEqual(wire['snapshot_limits']['entries'],6)
        self.assertEqual(wire['memory_maintenance']['hard_limits']['entries'],6)
        self.assertEqual(wire['memory']['capacity']['maximum'],12)
        self.assertEqual(wire['summary_capacity']['reserved_entries'],6)
        for key in ('events','observations','case','known'):self.assertEqual(self.s[key],before[key])
        for index in range(6,12):
            self.assertFalse(memory_policy.needed(self.s,'A',token_budget=True,text_budget=1024,entry_trigger=12))
            memory.apply(self.s,'A',{'upsert':[{'id':f'm{index}','kind':'self_claim','text':'我保留新的承诺。',
                'sources':[self.f.source]}],'archive':[],'processed_through':None},set())
        self.assertEqual(len(self.s['memory']['A']['entries']),12)
        self.assertTrue(memory_policy.needed(self.s,'A',token_budget=True,text_budget=1024,entry_trigger=12))

    def test_entry_overflow_retries_full_snapshot_and_preserves_ledger(self):
        requests=[]
        def provider(body):
            requests.append(deepcopy(body));count=(12,7,6)[min(len(requests)-1,2)]
            return {'choices':[{'finish_reason':'stop','message':{'content':canonical(self.f.snapshot(600,count))}}]}
        owner,saved,command,work=self.f.stored_work(provider)
        result,_=self.app.operate(owner,saved['id'],command,work)
        self.assertEqual(len(result['memory']['A']['entries']),6)
        self.assertEqual([p['max_tokens'] for p in requests],[2048]*3)
        for body in requests[1:]:
            wire=json.loads(body['messages'][2]['content']);fb=wire['validation_feedback']
            self.assertEqual(fb['limits']['entries'],6);self.assertNotIn('repair_contract',fb)
            self.assertNotIn('entry_text_targets',fb)
        with self.app.store.transaction(False) as con:
            calls=con.execute('SELECT * FROM ai_calls ORDER BY attempt').fetchall()
        self.assertEqual([r['status'] for r in calls],['failed','failed','completed'])
        self.assertEqual([r['request_hash'] for r in calls],[fingerprint(p) for p in requests])

    def test_text_only_repair_retains_six_entry_limit(self):
        requests=[]
        def provider(body):
            requests.append(deepcopy(body));wire=json.loads(body['messages'][2]['content'])
            if wire.get('repair_contract'):
                self.assertEqual(wire['snapshot_limits']['entries'],6)
                out={'text_replacements':[{'id':r['id'],'text':'我保留已发生的承诺。'} for r in wire['rewrite_entries']]}
            else:out=self.f.snapshot(1100,6)
            return {'choices':[{'finish_reason':'stop','message':{'content':canonical(out)}}]}
        owner,saved,command,work=self.f.stored_work(provider)
        result,_=self.app.operate(owner,saved['id'],command,work)
        self.assertEqual(len(requests),2);self.assertEqual(len(result['memory']['A']['entries']),6)

    def test_foreign_sources_remain_invalid_and_failure_never_commits_memory(self):
        out=self.f.snapshot(300,6);out['entries'][0]['sources']=['FOREIGN_CANARY']
        before=deepcopy(self.s['memory'])
        with self.assertRaises(memory.EntrySourcesError):
            self.app.summarize_chunk(self.s,'A',self.f.caller(out,VERSION),self.f.end)
        self.assertEqual(self.s['memory'],before)

    def test_new_version_changes_only_memory_contract(self):
        old=self.app.gateway.versions['ai-tasks-v121.json'];new=self.app.gateway.versions[VERSION]
        for task in old:
            a=deepcopy(old[task]);b=deepcopy(new[task])
            if task=='ensemble_memory':
                self.assertEqual(b.pop('memory_snapshot_max_entries'),6)
                self.assertNotEqual(a.pop('instruction'),b.pop('instruction'))
            self.assertEqual(a,b)

    def test_recovery_requires_available_retry_and_preserves_paid_role_tools(self):
        failed={'actor':'A','task':'ensemble_role','stage':'role_A','status':'failed',
            'validation_feedback':canonical({'code':'memory_capacity','scope':'active_memory'})}
        rows=[deepcopy(failed) for _ in range(4)]
        self.assertEqual(memory_headroom.recovery_actors(rows),set())
        progress={'role_A':{'start':4,'round':1}}
        self.assertEqual(memory_headroom.recovery_actors(rows,progress),{'A'})
        paid={**failed,'status':'completed','validation_feedback':None}
        self.assertEqual(memory_headroom.recovery_actors([*rows,paid],progress),set())
        repair={**paid,'task':'ensemble_memory','stage':'memory_headroom_A_2'}
        self.assertEqual(memory_headroom.recovery_actors([*rows,paid,repair],progress),{'A'})

    def test_pinned_full_summary_gets_one_repair_after_retry_and_replays_after_restart(self):
        self.app.gateway.current_version='ai-tasks-v121.json';self.f.seed(600,12)
        requests=[];original=self.f.f.provider
        def provider(body):
            requests.append(deepcopy(body));wire=json.loads(body['messages'][2]['content'])
            if 'PALTER_TASK: ensemble_memory\n' in body['messages'][0]['content']:
                observations=working_context.rows(wire['observations'])
                out=self.f.snapshot(600,6 if 'summary_capacity' in wire else 12)
                out['processed_through']=observations[-1]['id'] if observations else None
            else:
                out=decode_response('ensemble_role',original(body),tools=True)
                out.update(action={'kind':'inspect','args':['c1']},speech='',gesture=None,
                    memory_update={'upsert':[{'id':'m99','kind':'self_claim','text':'我保留尚未履行的承诺。',
                    'sources':[self.f.source]}],'archive':[],'processed_through':None},
                    relationships=[],progress={'kind':'none','sources':[]},
                    next_decision={'mode':'continue','events':[]},cancel_events=[])
                for field in ('belief_update','strategy_update'):
                    if field in out:out[field]=None
            return {'choices':[{'finish_reason':'stop','message':{'content':canonical(out)}}]}
        owner,saved,command,_=self.f.stored_work(provider)
        def work(state,call):self.app.turn(state,'A',call,0)
        def rows():
            with self.app.store.transaction(False) as con:return [dict(r) for r in con.execute('SELECT * FROM ai_calls ORDER BY started')]
        with self.assertRaises(StoreError):self.app.operate(owner,saved['id'],command,work)
        before=rows();self.assertEqual([r['status'] for r in before],['completed']+['failed']*4)
        with self.assertRaises(StoreError):self.app.operate(owner,saved['id'],command,work)
        self.assertEqual(rows(),before);self.assertEqual(len(requests),5)
        with self.app.store.transaction() as con:self.app.gateway.renew_retry(con,saved['id'],command['command_id'])
        def interrupted(state,call):
            work(state,call);raise StoreError('synthetic stop after paid role',503,'connection_failed')
        with self.assertRaises(StoreError):self.app.operate(owner,saved['id'],command,interrupted)
        after=rows();self.assertEqual(after[:5],before)
        self.assertEqual([r['stage'] for r in after[5:]],['memory_headroom_A_'+str(self.f.end),'role_A'])
        self.assertTrue(all(r['status']=='completed' for r in after[5:]))
        self.assertIsNone(json.loads(after[-1]['request_feedback']))
        self.app=EnsembleApplication(self.app.store.path,self.app.gateway.client)
        state,_=self.app.operate(owner,saved['id'],command,work)
        self.assertEqual(rows(),after);self.assertEqual(len(requests),7)
        self.assertEqual(len(state['memory']['A']['entries']),7);self.assertIn('c1',state['known']['A'])
        self.assertEqual([r['request_hash'] for r in after],[fingerprint(p) for p in requests])


if __name__=='__main__':unittest.main()
