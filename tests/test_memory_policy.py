"""Soft summary goals, pressure hysteresis, authority and pinned recovery."""
from copy import deepcopy
import json
import unittest
from unittest.mock import patch

from palter import memory_entries as memory, memory_policy as policy, ensemble_world as w
from palter.deepseek import DeepSeek,Settings
from palter.ensemble import EnsembleApplication
from palter.storage import canonical,StoreError
from tests import test_ensemble_review as fixtures

VERSION='ai-tasks-v94.json'


class MemoryPolicyTests(unittest.TestCase):
    def setUp(self):
        f=fixtures.ReviewFixTests();f.setUp();self.addCleanup(f.doCleanups)
        self.f=f;self.app=f.app;self.s=f.state;self.app.gateway.current_version=VERSION
        self.app.configure_rules(self.s,lambda:None)
        self.source=self.s['observations']['A'][-1]['id'];self.calls=[]

    def rows(self,length=730,count=6):
        return [{'id':f'm{i}','kind':'observed','text':'我'*(length//count+(i<length%count)),
                 'sources':[self.source]} for i in range(count)]

    def seed(self,length=850,count=6):
        rows=self.rows(length,count)
        self.s['memory']['A']={'entries':rows,'summary':'\n'.join(row['text'] for row in rows),
            'sources':[self.source],'checkpoint':len(self.s['observations']['A'])}

    def observe(self,count):
        for i in range(count):w.note(self.s,'A',w.emit(self.s,'observation','A'),f'我收到新的现场记录{i}。')

    def caller(self,length=730,count=6,version=VERSION):
        def call(stage,task,baseline,data,validate,actor=None):
            self.calls.append((stage,task,deepcopy(data)))
            out={'entries':self.rows(length,count),
                 'processed_through':data['observations'][-1]['id'] if data['observations'] else None}
            validate(out);return out,stage
        call.prefix_version=version;return call

    def test_targets_are_advisory_for_current_and_pinned_snapshots(self):
        for version in ('ai-tasks-v93.json',VERSION):
            for length,count in ((730,6),(763,6),(798,7),(950,12)):
                with self.subTest(version=version,length=length,count=count):
                    self.seed(710);before=deepcopy(self.s)
                    self.app.summarize_chunk(self.s,'A',self.caller(length,count,version),len(self.s['observations']['A']))
                    self.assertEqual(policy.stats(self.s['memory']['A'])['text_characters'],length)
                    self.assertEqual(self.s['memory']['A']['entries'],self.rows(length,count))
                    for key in ('observations','known','events','case'):self.assertEqual(self.s[key],before[key])

    def test_real_hard_limits_still_reject_without_partial_commit(self):
        for length,count in ((951,13),(800,13)):
            self.seed(710);before=deepcopy(self.s)
            with self.assertRaises(memory.CapacityError):self.app.summarize_chunk(self.s,'A',self.caller(length,count),len(self.s['observations']['A']))
            self.assertEqual(self.s,before)

    def test_valid_size_does_not_relax_source_or_checkpoint_rules(self):
        self.seed(710);self.observe(2)
        out={'entries':self.rows(),'processed_through':self.s['observations']['A'][-1]['id']}
        out['entries'][0]['sources']=['B-o999999']
        def call(stage,task,baseline,data,validate,actor=None):validate(out)
        call.prefix_version=VERSION
        with self.assertRaises(memory.EntrySourcesError):self.app.summarize_chunk(self.s,'A',call,len(self.s['observations']['A']))
        out['entries']=self.rows();out['processed_through']=self.source
        with self.assertRaises(memory.CheckpointError):self.app.summarize_chunk(self.s,'A',call,len(self.s['observations']['A']))

    def test_soft_trigger_has_headroom_and_source_counts_do_not_trigger_it(self):
        self.seed(849);self.assertFalse(policy.needed(self.s,'A'))
        self.seed(850);self.assertTrue(policy.needed(self.s,'A'))
        self.seed(450,9);self.assertTrue(policy.needed(self.s,'A'))
        self.seed(450);self.s['memory']['A']['entries'][0]['sources']=[f'A-o{i:06}' for i in range(1000)]
        self.assertFalse(policy.needed(self.s,'A'))

    def test_no_idle_recompaction_and_soft_pressure_waits_for_information(self):
        self.seed(880);policy.record(self.s,'A',policy.stats(self.s['memory']['A']))
        self.assertFalse(self.app.compact(self.s,'A',self.caller(880)))
        self.app.summarize(self.s,'A',self.caller(880));self.assertFalse(self.calls)
        self.observe(7);self.assertFalse(policy.needed(self.s,'A'))
        self.observe(1);self.assertTrue(policy.needed(self.s,'A'))

    def test_own_decision_cooldown_requires_new_information_or_growth(self):
        self.seed(880);policy.record(self.s,'A',policy.stats(self.s['memory']['A']))
        self.s['decisions']=[{'actor':'B'}]*20+[{'actor':'A'}]*4
        self.assertFalse(policy.needed(self.s,'A'))
        self.observe(1);self.assertTrue(policy.needed(self.s,'A'))

    def test_growing_near_hard_limit_bypasses_cooldown_but_unchanged_does_not(self):
        self.seed(880);policy.record(self.s,'A',policy.stats(self.s['memory']['A']))
        self.seed(900);self.assertTrue(policy.needed(self.s,'A'))
        policy.record(self.s,'A',policy.stats(self.s['memory']['A']))
        self.assertFalse(policy.needed(self.s,'A'))
        self.observe(1);self.assertFalse(policy.needed(self.s,'A'))
        self.assertFalse(policy.needed(self.s,'A',context_pressure=True))
        self.seed(910);self.assertTrue(policy.needed(self.s,'A',context_pressure=True))

    def test_request_pressure_does_not_rewrite_short_memory_without_reducible_history(self):
        self.seed(450);self.observe(1)
        self.assertFalse(policy.needed(self.s,'A',context_pressure=True))
        self.observe(12);self.assertTrue(policy.needed(self.s,'A',context_pressure=True))

    def test_pending_chunks_bypass_cooldown_without_an_immediate_second_rewrite(self):
        for version in ('ai-tasks-v93.json',VERSION):
            self.seed(710);policy.record(self.s,'A',policy.stats(self.s['memory']['A']));self.observe(25);self.calls=[]
            self.assertTrue(self.app.compact(self.s,'A',self.caller(730,version=version)))
            self.assertEqual(len(self.calls),1)
            self.assertEqual(self.s['memory']['A']['checkpoint'],len(self.s['observations']['A']))

    def test_current_metadata_has_lengths_targets_and_historical_wire_stays_pinned(self):
        self.seed(880);self.app.summarize_chunk(self.s,'A',self.caller(),len(self.s['observations']['A']))
        data=self.calls[0][2];self.assertEqual(data['memory_maintenance']['current']['text_characters'],880)
        self.assertEqual(sum(row['text_characters'] for row in data['memory_maintenance']['current']['entry_lengths']),880)
        for version,expected in ((VERSION,{'entries':12,'text_characters':950}),('ai-tasks-v93.json',{'entries':6,'text_characters':699})):
            body,_=self.app.gateway.payload('ensemble_memory',w.baseline(self.s,'A'),data,version)
            wire=json.loads(body['messages'][2]['content']);self.assertEqual(wire['snapshot_limits'],expected)
            self.assertEqual('memory_maintenance' in wire,version==VERSION)

    def test_old_capacity_feedback_becomes_advisory_only_for_new_attempts(self):
        old={'code':'memory_capacity','scope':'snapshot','actual':{'entries':6,'text_characters':730},
             'limits':{'entries':6,'text_characters':699}}
        before=deepcopy(old);result=memory.correction_feedback(old)
        self.assertEqual(result['limits'],{'entries':12});self.assertEqual(result['exceeded'],{})
        self.assertFalse(result['text_character_limited'])
        self.assertTrue(result['targets']['advisory']);self.assertEqual(old,before)

    def test_request_pressure_gets_one_rewrite_then_rebuilds_role_context(self):
        self.seed(710);self.observe(3);original=self.app.gateway.payload;first=True;tasks=[]
        def payload(*args,**kwargs):
            nonlocal first
            if first:first=False;raise StoreError('synthetic byte pressure',409,'context_budget')
            return original(*args,**kwargs)
        base=self.f.caller(VERSION)
        def call(stage,task,baseline,data,validate,actor=None):
            tasks.append(task)
            if task=='ensemble_memory':
                out={'entries':self.rows(500),'processed_through':data['observations'][-1]['id']};validate(out);return out,stage
            return base(stage,task,baseline,data,validate,actor)
        call.prefix_version=VERSION
        with patch.object(self.app.gateway,'payload',side_effect=payload):self.app.turn(self.s,'A',call,0)
        self.assertEqual(tasks,['ensemble_memory','ensemble_role'])
        self.assertEqual(len([d for d in self.s['decisions'] if d['actor']=='A']),1)

    def test_pinned_paid_tool_and_new_retry_accept_730_without_rebuying_or_mutation(self):
        self.seed(710);self.app.gateway.current_version='ai-tasks-v93.json';self.app.gateway.retry_delays=(0,0,0)
        source=self.source;requests=[];out={'entries':self.rows(730),'processed_through':None}
        def provider(payload):
            requests.append(deepcopy(payload))
            if not any(m['role']=='tool' for m in payload['messages']):
                choice={'finish_reason':'tool_calls','message':{'role':'assistant','content':None,'tool_calls':[{
                    'id':'paid_read','type':'function','function':{'name':'read_sources','arguments':canonical({'requests':[{'id':source}]})}}]}}
            else:choice={'finish_reason':'stop','message':{'content':canonical(out)}}
            return {'choices':[choice],'usage':{'prompt_tokens':100,'completion_tokens':30,'prompt_cache_hit_tokens':40,'prompt_cache_miss_tokens':60}}
        self.app.gateway.client.transport=provider
        owner=self.app.store.session()['id'];self.s['watch']['budget_usd']=2
        saved=self.app.store.create_game(owner,{'command_id':'capacity_recovery_create','expected_game_id':None},lambda gid:dict(deepcopy(self.s),id=gid))
        command={'command_id':'capacity_recovery_operation','expected_revision':saved['revision'],'kind':'probe'}
        def work(state,call):self.app.summarize_chunk(state,'A',call,len(state['observations']['A']))
        def historical(rows,source_capacity=False,text_budget=None):
            error=memory.CapacityError('old snapshot ceiling',rows,True);error.feedback['limits']={'entries':6,'text_characters':699};raise error
        with patch.object(memory,'validate_snapshot',side_effect=historical),patch.object(memory,'correction_feedback',side_effect=deepcopy):
            with self.assertRaises(StoreError):self.app.operate(owner,saved['id'],command,work)
        with self.app.store.transaction(False) as con:before=[dict(r) for r in con.execute('SELECT * FROM ai_calls ORDER BY started')]
        self.assertEqual([r['status'] for r in before],['completed']+['failed']*4)
        self.app=EnsembleApplication(self.app.store.path,DeepSeek(Settings(api_key='fixture'),provider));self.app.gateway.retry_delays=(0,0,0)
        with self.app.store.transaction() as con:self.app.gateway.renew_retry(con,saved['id'],command['command_id'])
        state,_=self.app.operate(owner,saved['id'],command,work)
        self.assertEqual(state['memory']['A']['entries'],out['entries']);self.assertEqual(len(requests),6)
        with self.app.store.transaction(False) as con:after=[dict(r) for r in con.execute('SELECT * FROM ai_calls ORDER BY started')]
        self.assertEqual(after[:5],before);self.assertEqual(after[-1]['prefix_hash'],before[-1]['prefix_hash'])
        wire=json.loads(requests[-1]['messages'][2]['content'])
        self.assertEqual(wire['snapshot_limits']['text_characters'],699)
        self.assertNotIn('text_characters',wire['validation_feedback']['limits'])


if __name__=='__main__':unittest.main()
