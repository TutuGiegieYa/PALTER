"""Closure thinking headroom, scoring boundaries and paid-stage recovery."""
from copy import deepcopy
import json
import unittest

from palter.ai_gateway import reserve_cost
from palter.deepseek import DeepSeek, Settings
from palter.ensemble import EnsembleApplication
from palter.storage import StoreError, fingerprint
from tests import test_conclusion_review as fixtures

VERSION = 'ai-tasks-v84.json'


class ConclusionThinkingTests(unittest.TestCase):
    def setUp(self):
        self.f = fixtures.ConclusionReviewTests(); self.f.setUp()
        self.addCleanup(self.f.doCleanups)
        self.app = self.f.app; self.app.gateway.current_version = VERSION
        self.app.gateway.retry_delays = (0, 0, 0)
        ids = ['c1', 'c2', 'c3', 'c4', 'c9', 'c10', 'c11']
        self.f.acquire(ids); self.f.submit(ids)
        self.f.s['watch'].update(budget_usd=1, call_limit=64)
        self.owner = self.app.store.session()['id']
        self.saved = self.app.store.create_game(self.owner,
            {'command_id':'synthetic_setup', 'expected_game_id':None},
            lambda gid: dict(deepcopy(self.f.s), id=gid))
        self.gid = self.saved['id']
        self.command = {'command_id':'synthetic_closure',
                        'expected_revision':self.saved['revision'], 'kind':'probe'}
        self.payloads = []; self.fail_task = None
        self.app.gateway.client.transport = self.transport

    def transport(self, payload):
        self.payloads.append(deepcopy(payload))
        task = payload['messages'][0]['content'].split('PALTER_TASK: ')[1].split('\n')[0]
        if task == self.fail_task:
            return {'choices':[{'finish_reason':'length', 'message':{
                'content':'', 'reasoning_content':'Synthetic truncated assessment'}}],
                'usage':{'prompt_tokens':0, 'completion_tokens':0}}
        return self.f.f.provider(payload)

    def run_closure(self):
        return self.app.operate(self.owner, self.gid, self.command, self.app.conclude_ensemble)

    def rows(self):
        with self.app.store.transaction(False) as con:
            return [dict(r) for r in con.execute(
                'SELECT * FROM ai_calls WHERE game_id=? ORDER BY started', (self.gid,))]

    def restart_and_renew(self):
        self.app = EnsembleApplication(self.app.store.path,
            DeepSeek(Settings(api_key='fixture'), self.transport))
        self.app.gateway.retry_delays = (0, 0, 0)
        with self.app.store.transaction() as con:
            self.app.gateway.renew_retry(con, self.gid, self.command['command_id'])

    def test_new_defaults_keep_wire_contract_and_all_unrelated_tasks(self):
        gateway = self.app.gateway
        self.assertEqual(gateway.current_version, VERSION)
        old = gateway.versions['ai-tasks-v83.json']; new = gateway.versions[VERSION]
        affected = {'case_theory':8192, 'ensemble_theory':8192,
                    'ending':4096, 'case_ending':4096, 'ensemble_ending':4096}
        for task in old:
            if task not in affected:
                self.assertEqual(old[task], new[task]); continue
            before, _ = gateway.payload(task, None, {}, 'ai-tasks-v83.json')
            after, _ = gateway.payload(task, None, {}, VERSION)
            self.assertEqual(after['max_tokens'], affected[task])
            self.assertEqual(after['thinking'], {'type':'enabled'})
            self.assertEqual(after['reasoning_effort'], 'low')
            self.assertEqual(after['model'], 'deepseek-flash')
            self.assertEqual(after['response_format'], before['response_format'])
            self.assertEqual(old[task]['example'], new[task]['example'])
            self.assertGreater(reserve_cost(after), reserve_cost(before))
            if task.endswith('theory'):
                self.assertTrue(new[task]['instruction'].endswith(old[task]['instruction']))
            else:
                self.assertEqual(after['messages'], before['messages'])

    def test_new_closure_cap_exhaustion_is_bounded_and_atomic(self):
        self.fail_task = 'ensemble_theory'
        with self.assertRaises(StoreError) as error:
            self.run_closure()
        self.assertEqual(error.exception.code, 'retry_exhausted')
        self.assertEqual([p['max_tokens'] for p in self.payloads], [8192] * 4)
        saved = self.app.store.state(self.owner, self.gid)
        for key in ('results', 'ending', 'events', 'known', 'submissions'):
            self.assertEqual(saved[key], self.saved[key])
        old = self.rows(); self.restart_and_renew(); self.fail_task = None
        result, _ = self.run_closure()
        self.assertEqual(result['phase'], 'ended')
        self.assertEqual(self.rows()[:4], old)
        self.assertEqual(sum(e['kind']=='ended' for e in result['events']), 1)
        self.assertEqual([p['max_tokens'] for p in self.payloads[-2:]], [8192, 4096])

    def test_old_closure_reuses_paid_assessment_after_restart(self):
        self.app.gateway.current_version = 'ai-tasks-v83.json'
        self.fail_task = 'ensemble_ending'
        with self.assertRaises(StoreError):
            self.run_closure()
        self.assertEqual([p['max_tokens'] for p in self.payloads], [2624, 2324, 4648, 8192, 8192])
        old = self.rows(); self.restart_and_renew(); self.fail_task = None
        result, _ = self.run_closure()
        self.assertEqual(result['phase'], 'ended')
        self.assertEqual(self.rows()[:5], old)
        self.assertEqual(len(self.payloads), 6)
        self.assertEqual(self.payloads[-1]['max_tokens'], 8192)
        with self.app.store.transaction(False) as con:
            pin = con.execute('SELECT prefix_version FROM ai_operations WHERE game_id=?', (self.gid,)).fetchone()[0]
        self.assertEqual(pin, 'ai-tasks-v83.json')
        for row, payload in zip(self.rows(), self.payloads):
            self.assertEqual(row['request_hash'], fingerprint(payload))
            self.assertEqual(row['reserved_cost_usd'], reserve_cost(payload))

    def test_new_guidance_keeps_temporal_errors_and_source_permissions_enforced(self):
        def temporal_error(task, out, data):
            if task == 'ensemble_theory':
                next(c for c in out['claims'] if c['aspect']=='time').update(
                    supported=False, reason='把发现时刻当成精确死亡时刻。')
        result = self.f.conclude(temporal_error, version=VERSION)
        self.assertEqual(result['result'], 'unproven')
        self.assertTrue(result['aspects']['time']['proof_covered'])
        self.assertFalse(result['aspects']['time']['established'])
        self.f.s['phase'] = 'active'
        def invalid_source(task, out, data):
            if task == 'ensemble_theory':out['argument_sources'].append('unheard_source')
        with self.assertRaises(ValueError):self.f.conclude(invalid_source, version=VERSION)


if __name__ == '__main__':
    unittest.main()
