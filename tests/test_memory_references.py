"""References are IDs: body budgets and authorization remain separate."""
from copy import deepcopy
import json
import unittest
from unittest.mock import patch

from palter import ensemble_world as w, ensemble_context, memory_entries as memory
from palter.ai_gateway import decode_response, MAX_DYNAMIC_CONTEXT_BYTES
from palter.storage import StoreError, canonical
from tests import test_memory_source_capacity as fixtures

VERSION = 'ai-tasks-v91.json'


class MemoryReferenceTests(unittest.TestCase):
    def setUp(self):
        f = fixtures.SourceCapacityTests(); f.setUp(); self.addCleanup(f.doCleanups)
        self.f = f; self.app = f.app; self.s = f.state; self.sources = list(f.sources)
        for i in range(84):
            w.speak(self.s, 'A', f'我记录第{i + 37}条待核实的说法。')
            self.sources.append(self.s['observations']['A'][-1]['id'])
        self.s['memory']['A'] = {'entries': [{'id': 'm1', 'kind': 'self_claim',
            'text': '我曾反复表明这些说法需要核对。', 'sources': self.sources}],
            'summary': '我曾反复表明这些说法需要核对。', 'sources': self.sources,
            'checkpoint': len(self.s['observations']['A'])}

    def test_120_references_survive_patch_and_snapshot_without_extra_compaction(self):
        before = deepcopy(self.s)
        update = {'upsert': deepcopy(self.s['memory']['A']['entries']), 'archive': [], 'processed_through': None}
        result, _ = memory.revised(self.s, 'A', update, set(self.sources))
        self.assertEqual(result['sources'], self.sources)
        memory.validate_snapshot(result['entries'], True)
        def forbidden(*args):raise AssertionError('Reference count must not trigger a call')
        forbidden.prefix_version = VERSION
        self.assertFalse(self.app.compact(self.s, 'A', forbidden))
        self.assertEqual(self.s, before)
        out = {'entries': update['upsert'], 'processed_through': None}
        self.app.summarize_chunk(self.s, 'A', self.f.caller(out, VERSION), len(self.s['observations']['A']))
        self.assertEqual(self.s['memory']['A']['sources'], self.sources)
        for key in ('case', 'events', 'observations', 'known'):self.assertEqual(self.s[key], before[key])

    def test_new_wire_has_no_source_limits_and_recalled_bodies_remain_bounded(self):
        data = w.context(self.s, 'A')
        ensemble_context.project(self.s, 'A', data, concise=True)
        self.assertLessEqual(len(data['recalled_sources']), 12)
        self.assertLessEqual(sum(len(canonical(o).encode()) for o in data['recalled_sources']), 6000)
        for task in ('ensemble_role', 'ensemble_memory'):
            payload, _ = self.app.gateway.payload(task, w.baseline(self.s, 'A'), data, VERSION)
            wire = json.loads(payload['messages'][-1]['content'])
            capacity = wire['memory']['capacity']
            self.assertEqual(capacity['unique_sources'], 120)
            self.assertEqual(wire['memory']['entries'][0]['sources'], self.sources)
            for key in ('maximum_unique_sources', 'maximum_sources_per_entry', 'free_sources'):
                self.assertNotIn(key, capacity)
            if task == 'ensemble_memory':
                self.assertEqual(wire['snapshot_limits'], {'entries': 6, 'text_characters': 699})

    def test_full_role_decision_accepts_120_references_through_all_validators(self):
        calls = []
        def call(stage, task, baseline, data, validate, actor=None):
            calls.append(task)
            payload, _ = self.app.gateway.payload(task, baseline, data, VERSION)
            out = decode_response(task, self.app.gateway.client.transport(payload))
            if task == 'ensemble_role':
                out['memory_update'] = {'upsert': deepcopy(self.s['memory']['A']['entries']),
                                        'archive': [], 'processed_through': None}
            validate(out)
            return out, 'synthetic_reference_validation'
        call.prefix_version = VERSION
        self.app.turn(self.s, 'A', call, 0)
        self.assertEqual(calls, ['ensemble_role'])
        self.assertEqual(self.s['memory']['A']['sources'], self.sources)

    def test_entry_text_request_and_authorization_guards_still_apply(self):
        rows = deepcopy(self.s['memory']['A']['entries'])
        for i in range(1, 13):rows.append(dict(deepcopy(rows[0]), id=f'm{i + 1}'))
        with self.assertRaises(memory.CapacityError):memory.validate_snapshot(rows, True)
        rows = [dict(row, text='待' * 250) for row in rows[:4]]
        memory.validate_snapshot(rows, True)  # Text length is no longer a storage rejection.
        update = {'upsert': deepcopy(self.s['memory']['A']['entries']), 'archive': [], 'processed_through': None}
        update['upsert'][0]['sources'].append('B-o999999')
        with self.assertRaises(memory.EntrySourcesError):memory.revised(self.s, 'A', update, set(self.sources))
        with self.assertRaises(StoreError) as error:
            self.app.gateway.payload('ensemble_role', w.baseline(self.s, 'A'), {'notes': 'x' * (MAX_DYNAMIC_CONTEXT_BYTES + 1)}, VERSION)
        self.assertEqual(error.exception.code, 'context_budget')

    def test_obsolete_source_feedback_retired_without_mutating_stored_data(self):
        inputs = [
            {'code': 'memory_capacity', 'scope': 'snapshot', 'actual': {'entries': 4, 'text_characters': 80, 'unique_sources': 21},
             'limits': {'entries': 6, 'text_characters': 699, 'unique_sources': 20, 'sources_per_entry': 8}},
            {'code': 'memory_entry_sources', 'entry_id': 'm4', 'actual': {'sources_per_entry': 10},
             'limits': {'sources_per_entry': 8}, 'problems': ['too_many_sources']},
            {'code': 'memory_entry_sources', 'entry_id': 'm4', 'actual': {'sources_per_entry': 10},
             'limits': {'sources_per_entry': 8}, 'problems': ['too_many_sources', 'unavailable_sources']}]
        for original in inputs:
            before = deepcopy(original); correction = memory.correction_feedback(original)
            self.assertEqual(original, before); self.assertEqual(correction['exceeded'], {})
            self.assertFalse(correction['source_count_limited'])
            self.assertNotIn('sources_per_entry', correction['limits'])
            self.assertNotIn('unique_sources', correction['limits'])
            self.assertNotIn('too_many_sources', correction.get('problems', []))
            if 'unavailable_sources' in original.get('problems', []):
                self.assertIn('unavailable_sources', correction['problems'])

    def test_old_count_failure_recovers_on_explicit_retry_with_same_prefix(self):
        f = fixtures.CapacityRecoveryTests(); f.setUp(); self.addCleanup(f.doCleanups)
        f.app.gateway.current_version = 'ai-tasks-v77.json'
        def transport(payload):
            f.payloads.append(deepcopy(payload))
            return {'choices': [{'finish_reason': 'stop', 'message': {'content': canonical(fixtures.snapshot(f.sources, 21))}}]}
        f.app.gateway.client.transport = transport
        def historical_limit(rows, source_capacity=False, text_budget=None):
            error = memory.CapacityError('compacted memory source capacity', rows, True, True)
            error.feedback['limits'].update(unique_sources=20, sources_per_entry=8)
            raise error
        with patch.object(memory, 'validate_snapshot', side_effect=historical_limit), patch.object(memory, 'correction_feedback', side_effect=deepcopy):
            with self.assertRaises(StoreError):f.app.operate(f.owner, f.gid, f.command, f.worker)
        old_calls = deepcopy(f.calls()); self.assertEqual(len(old_calls), 4)
        with self.assertRaises(StoreError):f.app.operate(f.owner, f.gid, f.command, f.worker)
        with f.app.store.transaction() as con:f.app.gateway.renew_retry(con, f.gid, f.command['command_id'])
        state, _ = f.app.operate(f.owner, f.gid, f.command, f.worker)
        self.assertEqual(memory.source_count(state['memory']['A']['entries']), 21)
        self.assertEqual(f.calls()[:4], old_calls)
        self.assertEqual(len({r['prefix_hash'] for r in f.calls()}), 1)
        wire = json.loads(f.payloads[-1]['messages'][-1]['content'])
        self.assertEqual(wire['validation_feedback']['exceeded'], {})
        self.assertFalse(wire['validation_feedback']['source_count_limited'])

    def test_new_prefix_preserves_unrelated_tasks_and_model_settings(self):
        old = self.app.gateway.versions['ai-tasks-v90.json']; new = self.app.gateway.versions[VERSION]
        for task in old:
            if task not in ('ensemble_role', 'ensemble_memory'):
                self.assertEqual(new[task], old[task]); continue
            for key in ('tokens', 'temperature', 'thinking', 'tools'):
                self.assertEqual(new[task].get(key), old[task].get(key))
            self.assertFalse(new[task]['memory_source_limits'])
        for spec in [new['ensemble_role'], *new['ensemble_role']['perspectives'].values(), new['ensemble_memory']]:
            self.assertIn('no per-entry or total source-ID count limit', spec['instruction'])
            for obsolete in ('1-8', 'at most 30 distinct source IDs', 'at most 20 unique sources', 'source headroom'):
                self.assertNotIn(obsolete, spec['instruction'])

    def test_recalled_source_cannot_rewind_checkpoint_and_feedback_is_exact(self):
        before = deepcopy(self.s)
        update = {'upsert': deepcopy(self.s['memory']['A']['entries']), 'archive': [],
                  'processed_through': self.sources[11]}
        with self.assertRaises(memory.CheckpointError) as error:
            memory.revised(self.s, 'A', update, set(), len(self.s['observations']['A']))
        self.assertEqual(error.exception.feedback['allowed_processed_through'], [None])
        self.assertEqual(self.s, before)
        update['processed_through'] = None
        result, _ = memory.revised(self.s, 'A', update, set(), len(self.s['observations']['A']))
        self.assertEqual(result['checkpoint'], before['memory']['A']['checkpoint'])
        self.assertEqual(result['sources'], self.sources)

    def test_pending_chunk_feedback_requires_last_supplied_record(self):
        self.s['memory']['A']['checkpoint'] -= 3
        update = {'upsert': [], 'archive': [], 'processed_through': None}
        before = deepcopy(self.s)
        with self.assertRaises(memory.CheckpointError) as error:
            memory.revised(self.s, 'A', update, set(self.sources[-3:]), len(self.s['observations']['A']))
        self.assertEqual(error.exception.feedback['allowed_processed_through'], [self.sources[-1]])
        self.assertEqual(self.s, before)

    def test_checkpoint_retry_reaches_model_and_replays_after_restart(self):
        f = fixtures.CapacityRecoveryTests(); f.setUp(); self.addCleanup(f.doCleanups)
        f.app.gateway.current_version = VERSION
        def transport(payload):
            f.payloads.append(deepcopy(payload))
            wire = json.loads(payload['messages'][-1]['content'])
            through = None if 'validation_feedback' in wire else f.sources[11]
            out = fixtures.snapshot(f.sources, 36, through)
            return {'choices': [{'finish_reason': 'stop', 'message': {'content': canonical(out)}}]}
        f.app.gateway.client.transport = transport
        def worker(state, call):f.app.summarize_chunk(state, 'A', call, len(state['observations']['A']))
        def interrupted(state, call):
            worker(state, call)
            raise StoreError('Synthetic paid-stage interruption', 503, 'connection_failed')
        with self.assertRaises(StoreError):f.app.operate(f.owner, f.gid, f.command, interrupted)
        before = deepcopy(f.calls()); self.assertEqual(len(before), 2)
        wire = json.loads(f.payloads[-1]['messages'][-1]['content'])
        self.assertEqual(wire['validation_feedback']['allowed_processed_through'], [None])
        from palter.ensemble import EnsembleApplication
        from palter.deepseek import DeepSeek, Settings
        f.app = EnsembleApplication(f.app.store.path, DeepSeek(Settings(api_key='fixture'), transport))
        state, _ = f.app.operate(f.owner, f.gid, f.command, worker)
        self.assertEqual(f.calls(), before)
        self.assertEqual(state['memory']['A']['checkpoint'], f.saved['memory']['A']['checkpoint'])
        self.assertEqual(memory.source_count(state['memory']['A']['entries']), 36)


if __name__ == '__main__':unittest.main()
