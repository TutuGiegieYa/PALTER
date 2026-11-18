"""Source pressure, correction feedback and durable version-pinned recovery."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import unittest

from palter import ensemble_world as w, memory_entries
from palter.deepseek import DeepSeek, Settings
from palter.ensemble import EnsembleApplication
from palter.storage import StoreError, canonical
from tests import test_ensemble_review as fixture


VERSION = 'ai-tasks-v75.json'


def pressure_state(state, actor='A', count=25):
    """Same dimensions as the incident; all text and observations are synthetic."""
    sources = []
    for i in range(36):
        w.speak(state, actor, f'我保留第{i+1}项待核实的说法。')
        sources.append(state['observations'][actor][-1]['id'])
    rows = [{'id': f'm{i}', 'kind': 'self_claim', 'text': '待'*(82 if i == 0 else 80),
             'sources': sources[i:count:8]} for i in range(8)]
    state['memory'][actor] = {'entries': rows, 'summary': '\n'.join(r['text'] for r in rows),
                              'sources': sources[:count], 'checkpoint': len(state['observations'][actor])}
    return sources


def snapshot(sources, count=20, through=None):
    return {'entries': [{'id': f'm{i}', 'kind': 'self_claim', 'text': '我保留这些待核实的说法。',
                         'sources': sources[i:count:4]} for i in range(4)], 'processed_through': through}


def oversized_snapshot(sources):
    out = snapshot(sources)
    out['entries']=[dict(deepcopy(out['entries'][i%4]),id=f'm{i}') for i in range(13)]
    return out


class SourceCapacityTests(unittest.TestCase):
    def setUp(self):
        f = fixture.ReviewFixTests(); f.setUp(); self.addCleanup(f.doCleanups)
        self.app, self.state = f.app, f.state
        self.app.gateway.current_version = VERSION
        self.sources = pressure_state(self.state)

    def caller(self, out, version=VERSION):
        def call(stage, task, baseline, data, validate, actor=None):
            validate(out)
            return deepcopy(out), 'source-capacity-fixture'
        call.prefix_version = version
        return call

    def test_25_to_31_update_is_accepted_and_keeps_originals(self):
        state = self.state; before = deepcopy(state)
        patch = {'upsert': [{'id': 'm9', 'kind': 'self_claim', 'text': '我还有待核实的新说法。',
                            'sources': self.sources[25:31]}], 'archive': [], 'processed_through': None}
        supplied = {o['id'] for o in state['observations']['A']}
        result, _ = memory_entries.revised(state, 'A', patch, supplied)
        self.assertEqual(memory_entries.source_count(result['entries']), 31)
        self.assertEqual(state, before)
        memory_entries.apply(state, 'A', patch, supplied)
        self.assertEqual(memory_entries.source_count(state['memory']['A']['entries']), 31)
        for key in ('observations', 'known', 'events', 'case'):
            self.assertEqual(state[key], before[key])

    def test_source_pressure_boundary_and_old_version_behavior(self):
        for count in (23, 24, 25, 30):
            state = deepcopy(self.state); pressure_state(state, count=count)
            self.assertEqual(memory_entries.needs_compaction(state['memory']['A'], True), count >= 24)
            self.assertFalse(self.app.compact(state, 'A', self.caller(snapshot(self.sources), 'ai-tasks-v74.json')))

    def test_snapshots_accept_source_counts_above_former_limits(self):
        for count in (21, 24, 30, 36):
            with self.subTest(count=count):
                state = deepcopy(self.state)
                self.app.summarize_chunk(state, 'A', self.caller(snapshot(self.sources, count)),
                                         len(state['observations']['A']))
                self.assertEqual(memory_entries.source_count(state['memory']['A']['entries']), count)
                self.assertEqual(state['observations'], self.state['observations'])

    def test_unique_count_deduplicates_across_entries_and_legacy_memory(self):
        memory = {'entries': [{'id': f'm{i}', 'text': '我记住这项说法。', 'sources': self.sources[:8]} for i in range(4)],
                  'checkpoint': 0}
        self.assertEqual(memory_entries.project(memory, True, True)['capacity']['unique_sources'], 8)
        legacy = {'summary': '我记住之前的说法。', 'sources': self.sources[:25], 'checkpoint': 0}
        self.assertTrue(memory_entries.needs_compaction(legacy, True))

    def test_new_wire_includes_active_and_snapshot_limits_and_old_wire_does_not(self):
        data = w.context(self.state, 'A'); before = deepcopy(data)
        for task in ('ensemble_role', 'ensemble_memory'):
            for version in ('ai-tasks-v74.json', VERSION):
                payload, _ = self.app.gateway.payload(task, w.baseline(self.state, 'A'), data, version)
                wire = json.loads(payload['messages'][-1]['content'])
                capacity = wire['memory']['capacity']
                if version == VERSION:
                    self.assertEqual(capacity['unique_sources'], 25)
                    self.assertEqual(capacity['free_sources'], 5)
                    self.assertEqual(capacity['maximum_unique_sources'], 30)
                    self.assertEqual(capacity['maximum_sources_per_entry'], 8)
                    if task == 'ensemble_memory':self.assertEqual(wire['snapshot_limits']['unique_sources'], 20)
                else:
                    self.assertNotIn('unique_sources', capacity)
                    self.assertNotIn('snapshot_limits', wire)
        self.assertEqual(data, before)

    def test_multiple_pending_chunks_compact_without_idle_repetition(self):
        self.state['memory']['A']['checkpoint'] = 0
        calls = []
        def call(stage, task, baseline, data, validate, actor=None):
            calls.append(stage)
            out = snapshot(self.sources, through=data['observations'][-1]['id'])
            validate(out); return out, 'chunk-fixture'
        call.prefix_version = VERSION
        self.app.summarize(self.state, 'A', call)
        self.assertEqual(len(calls), 2)
        self.assertEqual(self.state['memory']['A']['checkpoint'], len(self.state['observations']['A']))
        self.assertFalse(self.app.compact(self.state, 'A', call))
        self.assertEqual(len(calls), 2)

    def test_new_limits_preserve_source_authorization_and_checkpoint_guards(self):
        for change in ('unknown_source', 'skipped_observation', 'duplicate_source'):
            state = deepcopy(self.state); out = snapshot(self.sources)
            if change == 'unknown_source':out['entries'][0]['sources'] = ['B-o999999']
            elif change == 'duplicate_source':out['entries'][0]['sources'] = [self.sources[0]] * 2
            else:
                state['memory']['A']['checkpoint'] -= 1
                out['processed_through'] = state['observations']['A'][-2]['id']
            before = deepcopy(state)
            with self.subTest(change=change), self.assertRaises(ValueError):
                self.app.summarize_chunk(state, 'A', self.caller(out), len(state['observations']['A']))
            self.assertEqual(state, before)

    def test_prefix_hashes_and_perspectives_match_new_contract(self):
        root = Path('palter/prefixes'); manifest = json.loads((root/'manifest.json').read_text())
        for name, digest in manifest.items():
            self.assertEqual(hashlib.sha256((root/name).read_bytes()).hexdigest(), digest)
        spec = self.app.gateway.versions[VERSION]
        for role in (spec['ensemble_role'], *spec['ensemble_role']['perspectives'].values()):
            self.assertIn('at most 30 distinct source IDs', role['instruction'])
            self.assertIn('validation_feedback', role['instruction'])
        self.assertIn('at most 20 unique sources', spec['ensemble_memory']['instruction'])
        old = self.app.gateway.versions['ai-tasks-v74.json']
        for task in spec:
            if task not in ('ensemble_role', 'ensemble_memory'):self.assertEqual(spec[task], old[task])
            self.assertEqual(spec[task]['tokens'], old[task]['tokens'])


class CapacityRecoveryTests(unittest.TestCase):
    def setUp(self):
        f = fixture.ReviewFixTests(); f.setUp(); self.addCleanup(f.doCleanups)
        self.app = f.app; self.app.gateway.current_version = VERSION; self.app.gateway.retry_delays = (0, 0, 0)
        self.sources = pressure_state(f.state)
        f.state['watch'].update(budget_usd=2.0, call_limit=512)
        self.owner = self.app.store.session()['id']
        self.saved = self.app.store.create_game(self.owner, {'command_id': 'capacity_fixture', 'expected_game_id': None},
            lambda gid: dict(deepcopy(f.state), id=gid))
        self.gid = self.saved['id']; self.payloads = []
        self.command = {'command_id': 'capacity_operation', 'expected_revision': self.saved['revision'], 'kind': 'capacity_probe'}

    def transport(self, payload):
        self.payloads.append(deepcopy(payload))
        out = oversized_snapshot(self.sources) if len(self.payloads) == 1 else snapshot(self.sources)
        return {'choices': [{'finish_reason': 'stop', 'message': {'content': json.dumps(out, ensure_ascii=False)}}],
                'usage': {'prompt_tokens': 100, 'completion_tokens': 200, 'prompt_cache_hit_tokens': 40, 'prompt_cache_miss_tokens': 60}}

    def worker(self, state, call):
        self.app.summarize(state, 'A', call)

    def calls(self):
        with self.app.store.transaction(False) as con:
            return [dict(r) for r in con.execute('SELECT * FROM ai_calls WHERE game_id=? ORDER BY attempt', (self.gid,))]

    def test_snapshot_retry_receives_counts_and_reuses_prefix(self):
        self.app.gateway.client.transport = self.transport
        state, _ = self.app.operate(self.owner, self.gid, self.command, self.worker)
        wires = [json.loads(p['messages'][-1]['content']) for p in self.payloads]
        self.assertNotIn('validation_feedback', wires[0])
        feedback = wires[1].pop('validation_feedback')
        self.assertEqual(wires[0], wires[1])
        self.assertEqual(feedback['actual']['entries'], 13)
        self.assertEqual(feedback['limits'], {'entries':12})
        self.assertNotIn('unique_sources', feedback['limits'])
        self.assertEqual(feedback['scope'], 'snapshot')
        self.assertEqual(feedback['exceeded'], {'entries': {'actual': 13, 'maximum': 12, 'reduce_by_at_least': 1}})
        self.assertFalse(feedback['source_count_limited'])
        self.assertNotIn('A-o', canonical(feedback))
        rows = self.calls()
        self.assertEqual([r['status'] for r in rows], ['failed', 'completed'])
        self.assertEqual(len({r['prefix_hash'] for r in rows}), 1)
        self.assertEqual(len({r['request_hash'] for r in rows}), 2)
        self.assertEqual(json.loads(rows[1]['request_feedback']), feedback)
        self.assertEqual(state['observations'], self.saved['observations'])

    def test_completed_corrected_stage_replays_after_restart_without_extra_calls(self):
        self.app.gateway.client.transport = self.transport
        def interrupted(state, call):
            self.worker(state, call)
            raise StoreError('Synthetic interruption after the paid stage', 503, 'connection_failed')
        with self.assertRaises(StoreError):self.app.operate(self.owner, self.gid, self.command, interrupted)
        self.assertEqual(self.app.store.state(self.owner, self.gid)['memory'], self.saved['memory'])
        self.app = EnsembleApplication(self.app.store.path, DeepSeek(Settings(api_key='fixture'), self.transport))
        self.app.gateway.current_version = 'ai-tasks-v74.json'
        state, receipt = self.app.operate(self.owner, self.gid, self.command, self.worker)
        self.assertTrue(receipt['accepted']); self.assertEqual(len(self.payloads), 2)
        self.assertEqual(len(self.calls()), 2)
        self.assertEqual(memory_entries.source_count(state['memory']['A']['entries']), 20)

    def test_four_failures_then_manual_retry_keeps_feedback_and_original_state(self):
        def bad(payload):
            response = self.transport(payload)
            response['choices'][0]['message']['content'] = canonical(oversized_snapshot(self.sources))
            return response
        self.app.gateway.client.transport = bad
        with self.assertRaises(StoreError) as error:self.app.operate(self.owner, self.gid, self.command, self.worker)
        self.assertEqual(error.exception.code, 'retry_exhausted')
        self.assertEqual(len(self.calls()), 4)
        self.assertEqual(self.app.store.state(self.owner, self.gid)['memory'], self.saved['memory'])
        self.app = EnsembleApplication(self.app.store.path, DeepSeek(Settings(api_key='fixture'), self.transport))
        self.app.gateway.retry_delays = (0, 0, 0)
        with self.assertRaises(StoreError):self.app.operate(self.owner, self.gid, self.command, self.worker)
        self.assertEqual(len(self.calls()), 4)
        with self.app.store.transaction() as con:self.app.gateway.renew_retry(con, self.gid, self.command['command_id'])
        state, _ = self.app.operate(self.owner, self.gid, self.command, self.worker)
        self.assertEqual(len(self.calls()), 5)
        self.assertIn('validation_feedback', json.loads(self.payloads[-1]['messages'][-1]['content']))
        self.assertEqual(json.loads(self.payloads[-1]['messages'][-1]['content'])['validation_feedback']['exceeded']['entries']['reduce_by_at_least'], 1)
        self.assertEqual(memory_entries.source_count(state['memory']['A']['entries']), 20)

    def test_legacy_paid_correction_without_request_feedback_replays_original_hash(self):
        from unittest.mock import patch
        self.app.gateway.client.transport = self.transport
        def interrupted(state, call):
            self.worker(state, call)
            raise StoreError('Synthetic interruption after old paid stage', 503, 'connection_failed')
        with patch.object(memory_entries, 'correction_feedback', side_effect=deepcopy):
            with self.assertRaises(StoreError):self.app.operate(self.owner, self.gid, self.command, interrupted)
        with self.app.store.transaction() as con:
            con.execute('UPDATE ai_calls SET request_feedback=NULL WHERE game_id=?', (self.gid,))
        old_hashes=[r['request_hash'] for r in self.calls()]
        self.app=EnsembleApplication(self.app.store.path, DeepSeek(Settings(api_key='fixture'), self.transport))
        state,receipt=self.app.operate(self.owner,self.gid,self.command,self.worker)
        self.assertTrue(receipt['accepted']);self.assertEqual(len(self.payloads),2)
        self.assertEqual([r['request_hash'] for r in self.calls()],old_hashes)

    def test_legacy_exhausted_v77_gets_correction_only_on_explicit_retry(self):
        from unittest.mock import patch
        self.app.gateway.current_version='ai-tasks-v77.json'
        def bad(payload):
            response=self.transport(payload)
            response['choices'][0]['message']['content']=canonical(oversized_snapshot(self.sources))
            return response
        self.app.gateway.client.transport=bad
        with patch.object(memory_entries,'correction_feedback',side_effect=deepcopy):
            with self.assertRaises(StoreError):self.app.operate(self.owner,self.gid,self.command,self.worker)
        with self.app.store.transaction() as con:
            con.execute('UPDATE ai_calls SET request_feedback=NULL WHERE game_id=?',(self.gid,))
        old_calls=deepcopy(self.calls())
        self.app=EnsembleApplication(self.app.store.path, DeepSeek(Settings(api_key='fixture'),self.transport))
        self.app.gateway.retry_delays=(0,0,0)
        with self.assertRaises(StoreError):self.app.operate(self.owner,self.gid,self.command,self.worker)
        self.assertEqual(len(self.calls()),4)
        with self.app.store.transaction() as con:self.app.gateway.renew_retry(con,self.gid,self.command['command_id'])
        state,receipt=self.app.operate(self.owner,self.gid,self.command,self.worker)
        self.assertTrue(receipt['accepted']);self.assertEqual(self.calls()[:4],old_calls)
        wire=json.loads(self.payloads[-1]['messages'][-1]['content'])
        self.assertFalse(wire['validation_feedback']['source_count_limited'])
        self.assertEqual(len({r['prefix_hash'] for r in self.calls()}),1)

    def test_active_role_patch_feedback_is_scoped_and_does_not_commit_rejected_patch(self):
        payloads = []; sources = self.sources
        def transport(payload):
            payloads.append(deepcopy(payload))
            patch = {'upsert': [{'id': 'm9', 'kind': 'self_claim', 'text': '待' * 309 if len(payloads) == 1 else '我保留新说法。',
                                'sources': sources[25:31]}],
                     'archive': [], 'processed_through': None}
            if len(payloads)==1:patch['upsert']=[dict(deepcopy(patch['upsert'][0]),id=f'm{i}') for i in range(9,14)]
            return {'choices': [{'finish_reason': 'stop', 'message': {'content': canonical({'memory_update': patch})}}]}
        def worker(state, call):
            data = w.context(state, 'A'); supplied = {o['id'] for o in data['observations']}
            def validate(out):memory_entries.revised(state, 'A', out['memory_update'], supplied)
            out, _ = call('role_A', 'ensemble_role', w.baseline(state, 'A'), data, validate, 'A')
            memory_entries.apply(state, 'A', out['memory_update'], supplied)
        self.app.gateway.client.transport = transport
        state, _ = self.app.operate(self.owner, self.gid, self.command, worker)
        feedback = json.loads(payloads[-1]['messages'][-1]['content'])['validation_feedback']
        self.assertEqual(feedback['actual']['entries'], 13)
        self.assertEqual(feedback['limits'], {'entries':12})
        self.assertEqual(feedback['scope'], 'active_memory')
        self.assertEqual(memory_entries.source_count(state['memory']['A']['entries']), 31)
        self.assertNotIn('memory_archive', state)

    def test_old_pinned_memory_retries_keep_identical_request_and_no_new_feedback(self):
        self.app.gateway.current_version = 'ai-tasks-v74.json'
        def transport(payload):
            response = self.transport(payload)
            if len(self.payloads) == 1:
                out = oversized_snapshot(self.sources)
                response['choices'][0]['message']['content'] = canonical(out)
            return response
        self.app.gateway.client.transport = transport
        self.app.operate(self.owner, self.gid, self.command, self.worker)
        self.assertEqual(self.payloads[0], self.payloads[1])
        self.assertTrue(all(row['validation_feedback'] is None for row in self.calls()))


if __name__ == '__main__':unittest.main()
