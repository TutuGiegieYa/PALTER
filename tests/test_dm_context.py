"""DM sharing preserves occurrence-time knowledge and exact citation identity."""
from copy import deepcopy
import json
import random
import unittest

from palter import compact_context, context_economy, dm_context
from palter.ai_gateway import request_sizes
from palter.storage import canonical, StoreError
from tests.compact_fixture import expand, expand_dm_references
from tests import test_ensemble_review as fixtures

NEW = 'ai-tasks-v120.json'
OLD = 'ai-tasks-v119.json'


def knowledge(actor='A', private=False, version='original'):
    evidence=[{'id':'c1','title':'记录','observation':version+'共同正文'*300,
               'location':'r1','source':'原件','category':'document',
               'acquisition':{'event_id':actor+'-e1','method':'inspection'}}]
    if private:
        evidence.append({'id':'c2','observation':'A_PRIVATE_CANARY','acquisition':{'event_id':'A-e2'}})
    sources=[f'{actor}-o{i:06}' for i in range(1,31)]
    entries=[{'id':'m1','kind':'observed','text':'当时记忆'+actor,'sources':sources}]
    return {'evidence':evidence,'memory':{'entries':entries,'summary':'当时记忆'+actor,
            'sources':sources,'checkpoint':30},
            'belief':{'suspect':None,'explanation':'当时判断'+actor,'evidence_ids':['c1'],'testimony_ids':sources},
            'observations':[{'id':actor+'-o000030','event_id':'e30','kind':'testimony',
                'text':'实际收到的话','speaker':'B','channel':'public'}]}


def event(identity, actor='A', kind='testimony', snapshot=None):
    return {'id':identity,'actor':actor,'kind':kind,'target':None,'beat':1,
            'facts':{'text':'我保留自己的判断。','recipients':['A','B'],'channel':'public',
                     'speaker_knowledge':deepcopy(snapshot if snapshot is not None else knowledge(actor))}}


def wire(data):
    return context_economy.deduplicate_dm(compact_context.pack('ensemble_dm',data,authorized_keys=True))


def measure(value):
    return len(canonical([{'role':'user','content':compact_context.dumps(value)}]).encode())


class DmSharingTests(unittest.TestCase):
    def test_historical_gesture_shares_original_but_retains_actor_and_time(self):
        data={'utterances':[event('e3',snapshot=knowledge(private=True)),event('e4','B')],
              'recent_actual_events':[event('e1',kind='gesture'),{'id':'e2','facts':{'text':'场景事实'}}]}
        original=deepcopy(data);old=wire(data);new=dm_context.pack(old,measure)
        restored=expand(new)
        speakers=restored['utterances'];earlier=restored['recent_actual_events'][0]
        self.assertEqual({r['id'] for r in speakers[0]['facts']['speaker_knowledge']['evidence']},{'c1','c2'})
        for e in (speakers[1],earlier):
            self.assertEqual([r['id'] for r in e['facts']['speaker_knowledge']['evidence']],['c1'])
            self.assertNotIn('A_PRIVATE_CANARY',canonical(e))
        self.assertEqual(restored['recent_actual_events'][1],data['recent_actual_events'][1])
        self.assertEqual(sum(v.get('observation')==knowledge()['evidence'][0]['observation'] for v in new['sources'].values()),1)
        self.assertEqual(data,original)
        self.assertLess(measure(new),measure(old))

    def test_identical_snapshots_share_but_actors_and_changed_versions_do_not(self):
        same=knowledge();changed=knowledge(private=True)
        data={'utterances':[event('e1',snapshot=same),event('e2',snapshot=same),
                            event('e3','B',snapshot=same),event('e4',snapshot=changed)],'recent_actual_events':[]}
        projected=dm_context.normalize_history(wire(data));shared=dm_context.snapshot_references(projected)
        refs=[e['facts']['speaker_knowledge_ref'] for e in shared['utterances']]
        self.assertEqual(refs[0],refs[1]);self.assertNotEqual(refs[0],refs[2]);self.assertNotEqual(refs[0],refs[3])
        self.assertEqual(len(shared['knowledge_snapshots']),3)
        self.assertTrue(shared['knowledge_parts'])
        self.assertEqual(expand_dm_references(shared),projected)
        self.assertEqual([e['id'] for e in shared['utterances']],['e1','e2','e3','e4'])

    def test_same_evidence_id_with_distinct_bodies_keeps_each_version(self):
        data={'utterances':[event('e2',snapshot=knowledge(version='new'))],
              'recent_actual_events':[event('e1',kind='gesture',snapshot=knowledge(version='old'))]}
        packed=dm_context.pack(wire(data),measure);restored=expand(packed)
        self.assertTrue(restored['utterances'][0]['facts']['speaker_knowledge']['evidence'][0]['observation'].startswith('new'))
        self.assertTrue(restored['recent_actual_events'][0]['facts']['speaker_knowledge']['evidence'][0]['observation'].startswith('old'))
        self.assertEqual(len([k for k in packed['sources'] if k=='c1' or k.startswith('c1@')]),2)

    def test_ranges_keep_gaps_duplicates_order_prefix_and_padding(self):
        rows=[f'A-o{i:06}' for i in range(1,5)]+[f'A-o{i:06}' for i in range(6,9)]
        value={'sources':rows};new=dm_context.id_ranges(value)
        self.assertEqual(new,{'sources':{'id_ranges':['A-o000001~A-o000004','A-o000006~A-o000008']}})
        self.assertEqual(expand_dm_references(new),value)
        cases=[rows+rows,rows[::-1],['A-o01','A-o1','A-o02','A-o2'],
               [f'c{i}' for i in range(1,30)],['1','2','3','4','6','7','8'],
               ['A-o000001','B-o000002','A-o000003'],['c1',None,'c2'],[],['name~1','name~2','name~3']]
        rng=random.Random(120)
        cases += [rng.choices(rows+['B-o000001','c9'],k=40) for _ in range(100)]
        for row in cases:
            value={'memory':{'entries':[{'sources':row}]}}
            self.assertEqual(expand_dm_references(dm_context.id_ranges(value)),value)
            self.assertLessEqual(measure(dm_context.id_ranges(value)),measure(value))

    def test_source_bodies_prose_and_feedback_remain_exact(self):
        ids=[f'A-o{i:06}' for i in range(1,30)]
        value={'sources':{'s1':{'text':'1 2 3 不修改文字。'}},'belief':{'testimony_ids':ids},
               'validation_feedback':{'source_ids':ids,'instruction':'Retain original values.'}}
        new=dm_context.id_ranges(value)
        self.assertEqual(new['sources'],value['sources'])
        self.assertEqual(new['validation_feedback'],value['validation_feedback'])
        self.assertEqual(expand_dm_references(new),value)

    def test_many_actor_batch_roundtrips_and_small_inputs_never_grow(self):
        for size in (0,1,4,20):
            events=[event(f'e{i}',actor='ABCD'[i%4]) for i in range(size)]
            data=wire({'utterances':events[:4],'recent_actual_events':events[4:]})
            before=deepcopy(data);out=dm_context.pack(data,measure)
            self.assertLessEqual(measure(out),measure(data));self.assertEqual(data,before)
            expanded=expand_dm_references(out)
            self.assertIn(expanded,[data,dm_context.normalize_history(data)])
            self.assertEqual(out,dm_context.pack(data,measure))


class DmBudgetTests(unittest.TestCase):
    def setUp(self):
        self.f=fixtures.ReviewFixTests();self.f.setUp();self.addCleanup(self.f.doCleanups)
        self.gateway=self.f.app.gateway

    def test_new_dm_budget_also_allows_pinned_retries_without_changing_their_wire(self):
        data={'utterances':[],'recent_actual_events':[],'padding':'x'*100_000}
        old,_=self.gateway.payload('ensemble_dm',{},data,OLD)
        body,_=self.gateway.payload('ensemble_dm',{},data,NEW)
        self.assertEqual(old['messages'][2:],body['messages'][2:])
        self.assertGreater(request_sizes(body,2)['dynamic_bytes'],51_200)
        with self.assertRaises(StoreError) as caught:
            self.gateway.payload('ensemble_dm',{},dict(data,padding='x'*512_000),NEW)
        self.assertIn('512 KB',str(caught.exception));self.assertIn('1000 KB',str(caught.exception))
        with self.assertRaises(StoreError):
            self.gateway.payload('ensemble_dm',{},dict(data,padding='x'*512_000),OLD)

    def test_total_limit_is_independent_and_non_dm_limits_do_not_change(self):
        data={'utterances':[],'recent_actual_events':[],'padding':'x'*100_000}
        with self.assertRaises(StoreError):
            self.gateway.payload('ensemble_dm',{'history':'x'*910_000},data,NEW)
        for task in ('ensemble_theory','ensemble_ending'):
            with self.assertRaises(StoreError) as caught:self.gateway.payload(task,{},data,NEW)
            self.assertIn('51.2 KB',str(caught.exception));self.assertIn('90 KB',str(caught.exception))

    def test_prefix_only_changes_dm_input_contract_and_limits(self):
        old=self.gateway.versions[OLD];new=deepcopy(self.gateway.versions[NEW])
        dm=new['ensemble_dm'];prior=old['ensemble_dm']
        self.assertEqual(dm.pop('context_limits'),{'dynamic_bytes':512000,'total_bytes':1000000})
        self.assertEqual(dm.pop('knowledge_sharing_version'),1)
        self.assertTrue(dm['instruction'].startswith(prior['instruction']))
        dm['instruction']=prior['instruction']
        self.assertEqual(new,old)

    def test_final_gateway_payload_uses_same_lossless_projection_with_feedback(self):
        data={'utterances':[event('e2')],'recent_actual_events':[event('e1',kind='gesture')],
              'validation_feedback':{'code':'fixture','source_ids':['A-o000001']}}
        before=deepcopy(data)
        old,_=self.gateway.payload('ensemble_dm',{},data,OLD)
        new,_=self.gateway.payload('ensemble_dm',{},data,NEW)
        old_data=json.loads(old['messages'][2]['content']);new_data=json.loads(new['messages'][2]['content'])
        self.assertLess(request_sizes(new,2)['dynamic_bytes'],request_sizes(old,2)['dynamic_bytes'])
        self.assertEqual(expand_dm_references(new_data),dm_context.normalize_history(old_data))
        self.assertEqual(data,before)
        self.assertEqual(new['messages'][:1][0]['role'],'system')
        self.assertEqual(old['messages'][1],new['messages'][1])


if __name__=='__main__':unittest.main()
