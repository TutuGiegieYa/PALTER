"""Whole-memory rewrite feedback stays bounded, durable and version compatible."""
from copy import deepcopy
import json
import unittest
from unittest.mock import patch

from palter.ai_gateway import memory_rewrite_feedback
from palter import memory_entries, memory_policy
from palter import ensemble_world, working_context
from palter.deepseek import DeepSeek, Settings
from palter.ensemble import EnsembleApplication
from palter.storage import StoreError, canonical, fingerprint
from tests import test_memory_token_budget as fixtures


def old_feedback(max_tokens, length_failures=1):
    return {'code':'memory_output_truncated','max_tokens':max_tokens,
            'instruction':'Rewrite a concise complete entries snapshot within the same output token budget.'}


class MemoryRewriteTests(unittest.TestCase):
    def setUp(self):
        f=fixtures.MemoryTokenBudgetTests();f.setUp();self.addCleanup(f.doCleanups)
        self.f=f;self.app=f.app;self.app.gateway.current_version='ai-tasks-v103.json'
        self.requests=[];self.mode='length'
        self.owner,self.saved,self.command,self.work=f.stored_work(self.provider)

    def provider(self,body):
        self.requests.append(deepcopy(body))
        if self.mode=='network' and len(self.requests)==2:raise TimeoutError()
        truncated=self.mode=='length' or (self.mode in ('once','network') and len(self.requests)==1)
        output=self.f.snapshot(1024) if self.mode in ('oversized','text_edits','invalid_sources') and len(self.requests)==1 else self.f.snapshot()
        if self.mode=='text_edits' and len(self.requests)>1:
            output={'text_replacements':[{'id':row['id'],'text':row['text']} for row in output['entries']]}
        if self.mode=='invalid_sources' and len(self.requests)==1:
            output['entries'][0]['sources']=['B-o999999']
        if json.loads(body['messages'][2]['content']).get('repair_contract') and 'entries' in output:
            output={'text_replacements':[{'id':row['id'],'text':row['text']} for row in output['entries']]}
        return {'choices':[{'finish_reason':'length' if truncated else 'stop',
                'message':{'content':canonical(output)}}]}

    def operate(self,work=None):
        return self.app.operate(self.owner,self.saved['id'],self.command,work or self.work)

    def calls(self):
        with self.app.store.transaction(False) as con:
            return [dict(r) for r in con.execute('SELECT * FROM ai_calls ORDER BY attempt')]

    def test_successive_length_failures_change_rewrite_target_without_raising_cap(self):
        with self.assertRaises(StoreError) as error:self.operate()
        self.assertEqual(error.exception.code,'retry_exhausted')
        self.assertEqual([p['max_tokens'] for p in self.requests],[2048]*4)
        feedback=[json.loads(p['messages'][2]['content']).get('validation_feedback') for p in self.requests]
        self.assertIsNone(feedback[0])
        self.assertEqual([f['preferred_output_tokens'] for f in feedback[1:]],[1200,1000,800])
        self.assertEqual([f['length_failures'] for f in feedback[1:]],[1,2,3])
        self.assertTrue(all(f['target_is_advisory'] for f in feedback[1:]))
        self.assertEqual(self.app.store.state(self.owner,self.saved['id'])['memory'],self.saved['memory'])
        self.assertTrue(all(r['result'] is None for r in self.calls()))
        with self.assertRaises(StoreError):self.operate()
        self.assertEqual(len(self.requests),4)

    def test_old_exhausted_operation_gets_new_feedback_only_after_manual_renewal(self):
        self.app.gateway.current_version='ai-tasks-v99.json'
        with patch('palter.ai_gateway.memory_rewrite_feedback',side_effect=old_feedback):
            with self.assertRaises(StoreError):self.operate()
        before=deepcopy(self.calls())
        self.app=EnsembleApplication(self.app.store.path,DeepSeek(Settings(api_key='fixture'),self.provider))
        self.app.gateway.retry_delays=(0,0,0)
        with self.assertRaises(StoreError):self.operate()
        self.assertEqual(len(self.requests),4)
        with self.app.store.transaction() as con:
            self.app.gateway.renew_retry(con,self.saved['id'],self.command['command_id'])
        self.mode='valid';state,_=self.operate()
        self.assertEqual(len(self.requests),5)
        self.assertEqual(self.calls()[:4],before)
        body=self.requests[-1];feedback=json.loads(body['messages'][2]['content'])['validation_feedback']
        self.assertEqual(body['max_tokens'],2048)
        self.assertEqual(feedback['correction_version'],2)
        self.assertEqual(feedback['length_failures'],4)
        self.assertEqual(feedback['preferred_output_tokens'],800)
        self.assertEqual(state['memory']['A']['checkpoint'],self.f.end)
        with self.app.store.transaction(False) as con:
            self.assertEqual(con.execute('SELECT prefix_version FROM ai_operations').fetchone()[0],'ai-tasks-v99.json')

    def test_paid_old_feedback_replays_exactly_after_restart(self):
        self.app.gateway.current_version='ai-tasks-v99.json';self.mode='once'
        def interrupted(state,call):
            self.work(state,call);raise StoreError('fixture after paid memory',503,'connection_failed')
        with patch('palter.ai_gateway.memory_rewrite_feedback',side_effect=old_feedback):
            with self.assertRaises(StoreError):self.operate(interrupted)
        before=deepcopy(self.calls())
        self.assertNotIn('correction_version',json.loads(before[-1]['request_feedback']))
        self.app=EnsembleApplication(self.app.store.path,DeepSeek(Settings(api_key='fixture'),self.provider))
        state,_=self.operate()
        self.assertEqual(self.calls(),before);self.assertEqual(len(self.requests),2)
        self.assertEqual(state['memory']['A']['entries'],self.f.snapshot()['entries'])
        for row,request in zip(before,self.requests):self.assertEqual(row['request_hash'],fingerprint(request))

    def test_network_failure_does_not_escalate_rewrite_aggressiveness(self):
        self.mode='network';self.operate()
        feedback=[json.loads(p['messages'][2]['content']).get('validation_feedback') for p in self.requests]
        self.assertEqual(len(feedback),3);self.assertEqual(feedback[1],feedback[2])
        self.assertEqual(feedback[2]['length_failures'],1)
        self.assertEqual([p['max_tokens'] for p in self.requests],[2048]*3)

    def test_unrelated_tasks_and_token_caps_stay_unchanged(self):
        old=self.app.gateway.versions['ai-tasks-v99.json'];new=self.app.gateway.versions['ai-tasks-v103.json']
        for task in old:
            if task not in ('ensemble_memory','ensemble_role'):self.assertEqual(old[task],new[task])
            else:
                before=deepcopy(old[task]);after=deepcopy(new[task])
                self.assertNotEqual(before.pop('instruction'),after.pop('instruction'))
                self.assertEqual(after.pop('memory_character_budget'),1024)
                if task=='ensemble_memory':self.assertEqual(after.pop('memory_summary_view'),1)
                for key in before.get('perspectives',{}):
                    before['perspectives'][key].pop('instruction');after['perspectives'][key].pop('instruction')
                self.assertEqual(before,after)
        self.mode='valid';state,_=self.operate()
        self.assertEqual(state['memory']['A']['entries'],self.f.snapshot()['entries'])
        for n in (1,2,3,20):
            feedback=memory_rewrite_feedback(2048,n)
            self.assertEqual(feedback['max_tokens'],2048)
            self.assertLessEqual(feedback['preferred_output_tokens'],2048)

    def test_text_threshold_triggers_promptly_and_small_unchanged_summary_stays_idle(self):
        self.f.seed(1023);state=self.f.s
        self.assertFalse(memory_policy.needed(state,'A',token_budget=True,text_budget=1024))
        self.f.seed(1024)
        self.assertTrue(memory_policy.needed(state,'A',token_budget=True,text_budget=1024))
        self.f.seed(1023)
        memory_policy.record(state,'A',memory_policy.stats(state['memory']['A']),token_budget=True,text_budget=1024)
        self.assertFalse(memory_policy.needed(state,'A',token_budget=True,text_budget=1024))
        state['memory']['A']['entries'][0]['text']+='新'
        self.assertTrue(memory_policy.needed(state,'A',token_budget=True,text_budget=1024))

    def test_snapshot_counts_only_text_with_strict_1024_boundary(self):
        rows=self.f.rows(1023);rows[0]['sources']=[f'A-o{i:06d}' for i in range(100)]
        memory_entries.validate_snapshot(rows,text_budget=1024)
        rows[0]['text']+='字'
        with self.assertRaises(memory_entries.CapacityError) as error:
            memory_entries.validate_snapshot(rows,text_budget=1024)
        feedback=memory_entries.correction_feedback(error.exception.feedback)
        self.assertEqual(feedback['actual']['text_characters'],1024)
        self.assertEqual(feedback['limits'],{'entries':12,'text_characters':1023})
        self.assertEqual(feedback['exceeded']['text_characters']['reduce_by_at_least'],1)
        self.assertFalse(feedback['source_count_limited'])

    def test_overlong_complete_summary_gets_actionable_retry_then_commits_once(self):
        self.mode='oversized';state,_=self.operate();calls=self.calls()
        self.assertEqual([r['status'] for r in calls],['failed','completed'])
        self.assertEqual([p['max_tokens'] for p in self.requests],[2048,2048])
        wire=json.loads(self.requests[1]['messages'][2]['content'])
        self.assertEqual(wire['snapshot_limits'],{'entries':12,'text_characters':1023})
        feedback=json.loads(calls[1]['request_feedback'])
        self.assertEqual(feedback['code'],'memory_capacity')
        self.assertEqual(feedback['limits']['text_characters'],1023)
        self.assertTrue(feedback['text_character_limited'])
        self.assertEqual(sum(len(r['text']) for r in feedback['rejected_snapshot']),1024)
        self.assertEqual(feedback['rejected_snapshot'],json.loads(calls[0]['result'])['entries'])
        self.assertTrue(feedback['entry_targets_are_advisory'])
        self.assertLessEqual(sum(r['preferred_characters'] for r in feedback['entry_text_targets']),600)
        self.assertNotIn('rejected_snapshot',state['memory']['A'])
        self.assertEqual(state['memory']['A']['checkpoint'],self.f.end)
        self.assertEqual(sum(len(e['text']) for e in state['memory']['A']['entries']),900)
        self.assertEqual(state['observations'],self.saved['observations'])

    def test_summary_view_keeps_new_receipts_and_authorized_initial_facts_exact(self):
        data=ensemble_world.context(self.f.s,'A')
        data.update(belief={'summary':'separately stored reasoning'},strategy={'position':'separate strategy'},
                    exploration={'room':'separate exploration'},temporal_facts={'summary':'separate calculations'})
        data['evidence'].append({'id':'known_record','title':'owned original','text':'old body kept on demand'})
        baseline=ensemble_world.baseline(self.f.s,'A');before=deepcopy(data);base_before=deepcopy(baseline)
        old,_=self.app.gateway.payload('ensemble_memory',baseline,data,'ai-tasks-v99.json')
        body,_=self.app.gateway.payload('ensemble_memory',baseline,data,'ai-tasks-v103.json')
        wire=json.loads(body['messages'][2]['content']);old_wire=json.loads(old['messages'][2]['content'])
        for field in ('belief','strategy','exploration','temporal_facts'):self.assertNotIn(field,wire)
        self.assertEqual(wire['observations'],old_wire['observations'])
        for key in working_context.references(wire['observations']):
            self.assertEqual(wire['sources'][key],old_wire['sources'][key])
        self.assertNotIn('known_record',wire['sources'])
        self.assertIn('known_record',[r['id'] for r in working_context.rows(wire['evidence_catalog'])])
        projected=json.loads(body['messages'][1]['content'].split('\n',1)[1])
        self.assertEqual(projected,{key:baseline[key] for key in ('actor','cast','experienced_facts')})
        self.assertEqual(data,before);self.assertEqual(baseline,base_before)
        self.assertTrue(wire['working_context']['originals_preserved'])

    def test_text_only_retry_preserves_validated_metadata_and_paid_replay(self):
        self.mode='text_edits'
        def interrupted(state,call):
            self.work(state,call);raise StoreError('fixture after repaired memory',503,'connection_failed')
        with self.assertRaises(StoreError):self.operate(interrupted)
        before=self.calls();self.assertEqual([r['status'] for r in before],['failed','completed'])
        self.assertEqual(len(self.requests),2);self.assertNotIn('tools',self.requests[1])
        feedback=json.loads(before[1]['request_feedback'])
        self.assertTrue(feedback['validated_draft'])
        self.assertEqual(feedback['repair_contract'],'memory-text-repair-v2.txt')
        actual=json.loads(before[-1]['result']);draft=feedback['rejected_snapshot']
        for repaired,original in zip(actual['entries'],draft):
            for field in ('id','kind','sources'):self.assertEqual(repaired[field],original[field])
        self.assertEqual(actual['processed_through'],feedback['processed_through'])
        raw=json.loads(before[-1]['response'])['choices'][0]['message']['content']
        self.assertIn('text_replacements',json.loads(raw))
        self.app=EnsembleApplication(self.app.store.path,DeepSeek(Settings(api_key='fixture'),self.provider))
        state,_=self.operate();self.assertEqual(self.calls(),before);self.assertEqual(len(self.requests),2)
        self.assertEqual(state['memory']['A']['entries'],actual['entries'])

    def test_invalid_sources_cannot_be_frozen_into_a_text_repair(self):
        self.mode='invalid_sources';state,_=self.operate()
        feedback=json.loads(self.requests[1]['messages'][2]['content'])['validation_feedback']
        self.assertEqual(feedback['code'],'memory_entry_sources')
        self.assertNotIn('validated_draft',feedback);self.assertNotIn('repair_contract',feedback)
        self.assertNotIn('B-o999999',state['memory']['A']['sources'])

    def test_text_repair_rejects_missing_duplicate_and_foreign_ids(self):
        draft=self.f.snapshot()
        feedback={'repair_contract':'memory-text-repair-v2.txt','rejected_snapshot':draft['entries'],
                  'processed_through':draft['processed_through']}
        valid=[{'id':row['id'],'text':'我保留有来源的待查结论。'} for row in draft['entries']]
        for output in (draft,{'text_replacements':valid[:1]},
                       {'text_replacements':[valid[0],valid[0]]},
                       {'text_replacements':[valid[0],{'id':'m999','text':'异名'}]}):
            with self.assertRaises(ValueError):memory_entries.repaired_snapshot(output,feedback)


if __name__=='__main__':unittest.main()
