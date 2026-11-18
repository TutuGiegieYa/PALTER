"""Bounded thinking headroom with immutable receipts and atomic memory recovery."""
from copy import deepcopy
import json
import unittest
from unittest.mock import patch

from palter.ai_gateway import reserve_cost
from palter.deepseek import DeepSeek,Settings
from palter.ensemble import EnsembleApplication
from palter.storage import StoreError,canonical,fingerprint
from tests import test_memory_source_capacity as fixtures


class ThinkingRecoveryTests(unittest.TestCase):
    def setUp(self):
        f=fixtures.CapacityRecoveryTests();f.setUp();self.addCleanup(f.doCleanups)
        self.f=f;self.app=f.app;self.app.gateway.current_version='ai-tasks-v82.json'
        self.payloads=[];self.mode='once';self.failures=0
        self.app.gateway.client.transport=self.transport

    def transport(self,payload):
        self.payloads.append(deepcopy(payload));index=len(self.payloads)
        if self.mode=='network' and index==2:raise TimeoutError()
        truncated=self.mode=='length' or (self.mode in ('once','network','budget') and index==1)
        if self.mode=='budget' and index==1:
            larger=deepcopy(payload);larger['max_tokens']*=2
            with self.app.store.transaction() as con:
                state=self.app.store.load(con,self.f.owner,self.f.gid);old=deepcopy(state)
                state['watch']['budget_usd']=(reserve_cost(payload)+reserve_cost(larger))/2
                self.app.store.save(con,state,old)
        if self.mode=='schema':content='not json'
        else:content='' if truncated else canonical(fixtures.snapshot(self.f.sources))
        return {'choices':[{'finish_reason':'length' if truncated else 'stop',
            'message':{'role':'assistant','content':content,'reasoning_content':'synthetic reasoning'}}],
            'usage':{'prompt_tokens':0,'completion_tokens':0,'prompt_cache_hit_tokens':0,'prompt_cache_miss_tokens':0}}

    def operate(self,worker=None):
        return self.app.operate(self.f.owner,self.f.gid,self.f.command,worker or self.f.worker)

    def restart(self):
        self.app=EnsembleApplication(self.app.store.path,DeepSeek(Settings(api_key='fixture'),self.transport))
        self.app.gateway.retry_delays=(0,0,0)
        self.f.app=self.app

    def renew(self):
        with self.app.store.transaction() as con:self.app.gateway.renew_retry(con,self.f.gid,self.f.command['command_id'])

    def test_truncation_grows_cap_and_records_actual_hash_and_reservation(self):
        state,_=self.operate();rows=self.f.calls()
        self.assertEqual([p['max_tokens'] for p in self.payloads],[2424,4848])
        self.assertEqual(self.payloads[0]['messages'],self.payloads[1]['messages'])
        self.assertEqual(self.payloads[1]['thinking'],{'type':'enabled'})
        self.assertEqual(self.payloads[1]['reasoning_effort'],'low')
        self.assertEqual(json.loads(rows[1]['request_settings']),{'max_tokens':4848})
        self.assertNotEqual(rows[0]['prefix_hash'],rows[1]['prefix_hash'])
        for row,payload in zip(rows,self.payloads):
            self.assertEqual(row['request_hash'],fingerprint(payload))
            self.assertEqual(row['reserved_cost_usd'],reserve_cost(payload))
        self.assertEqual(state['observations'],self.f.saved['observations'])
        self.assertEqual(len(state['memory']['A']['entries']),4)

    def test_four_attempts_are_bounded_and_manual_retry_keeps_allowance(self):
        self.mode='length'
        with self.assertRaises(StoreError) as error:self.operate()
        self.assertEqual(error.exception.code,'retry_exhausted')
        self.assertEqual([p['max_tokens'] for p in self.payloads],[2424,4848,8192,8192])
        self.assertEqual(self.app.store.state(self.f.owner,self.f.gid)['memory'],self.f.saved['memory'])
        old=deepcopy(self.f.calls());self.restart()
        with self.assertRaises(StoreError):self.operate()
        self.assertEqual(len(self.payloads),4)
        self.renew();self.mode='valid';state,_=self.operate()
        self.assertEqual(self.payloads[-1]['max_tokens'],8192)
        self.assertEqual(self.f.calls()[:4],old)
        self.assertEqual(len(state['memory']['A']['entries']),4)

    def test_paid_stage_replays_identical_override_after_restart(self):
        def interrupted(state,call):
            self.f.worker(state,call)
            raise StoreError('Synthetic interruption after memory',503,'connection_failed')
        with self.assertRaises(StoreError):self.operate(interrupted)
        old=deepcopy(self.f.calls());self.restart();state,_=self.operate()
        self.assertEqual(len(self.payloads),2);self.assertEqual(self.f.calls(),old)
        self.assertEqual(len(state['memory']['A']['entries']),4)

    def test_existing_exhausted_v82_can_recover_without_changing_its_pin(self):
        self.mode='length'
        with patch('palter.ai_gateway.retry_request_settings',return_value=None):
            with self.assertRaises(StoreError):self.operate()
        with self.app.store.transaction() as con:
            con.execute('UPDATE ai_calls SET request_settings=NULL WHERE game_id=?',(self.f.gid,))
        old=deepcopy(self.f.calls());self.restart();self.renew();self.mode='valid';self.operate()
        self.assertEqual([p['max_tokens'] for p in self.payloads],[2424]*4+[4848])
        self.assertEqual(self.f.calls()[:4],old)
        with self.app.store.transaction(False) as con:
            self.assertEqual(con.execute('SELECT prefix_version FROM ai_operations WHERE game_id=?',(self.f.gid,)).fetchone()[0],'ai-tasks-v82.json')

    def test_schema_failures_keep_the_original_allowance(self):
        self.mode='schema'
        with self.assertRaises(StoreError):self.operate()
        self.assertEqual([p['max_tokens'] for p in self.payloads],[2424]*4)

    def test_non_thinking_calls_retain_their_original_contract(self):
        self.app.gateway.current_version='ai-tasks-v79.json';self.mode='length'
        with self.assertRaises(StoreError):self.operate()
        self.assertEqual([p['max_tokens'] for p in self.payloads],[1400]*4)

    def test_transport_failure_does_not_reset_or_further_raise_allowance(self):
        self.mode='network';self.operate()
        self.assertEqual([p['max_tokens'] for p in self.payloads],[2424,4848,4848])

    def test_raised_cap_still_requires_remaining_dollar_budget(self):
        self.mode='budget'
        with self.assertRaises(StoreError) as error:self.operate()
        self.assertEqual(error.exception.code,'watch_budget');self.assertEqual(len(self.payloads),1)
        self.assertEqual(self.app.store.state(self.f.owner,self.f.gid)['memory'],self.f.saved['memory'])

    def test_new_defaults_only_raise_memory_and_role_caps(self):
        gateway=self.app.gateway
        old=gateway.versions['ai-tasks-v82.json'];new=gateway.versions['ai-tasks-v83.json']
        for task,spec in old.items():
            expected=deepcopy(spec)
            if task in ('memory','case_memory','ensemble_memory','ensemble_role'):expected['tokens']=6144
            self.assertEqual(new[task],expected)
        for settings in ({'max_tokens':8193},{'max_tokens':0},{'max_tokens':True},{'model':'other'}):
            with self.assertRaises(ValueError):gateway.payload('ensemble_memory',{}, {},'ai-tasks-v82.json',settings)


if __name__=='__main__':unittest.main()
