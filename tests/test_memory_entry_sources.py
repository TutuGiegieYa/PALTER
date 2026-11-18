"""Authorized memory references, scoped correction and pinned recovery."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import unittest

from palter import ensemble_world as w, memory_entries as memory
from palter.deepseek import DeepSeek, Settings
from palter.ensemble import EnsembleApplication
from palter.storage import StoreError, canonical
from tests import test_memory_source_capacity as fixtures


class EntrySourceTests(unittest.TestCase):
    calls = fixtures.CapacityRecoveryTests.calls

    def setUp(self):
        fixtures.CapacityRecoveryTests.setUp(self)
        self.app.gateway.current_version = 'ai-tasks-v89.json'
        self.saved['memory']['A'] = {
            'entries': [{'id': 'm4', 'kind': 'self_claim', 'text': '我反复表示要核对记录。',
                         'sources': self.sources[:7]}],
            'summary': '我反复表示要核对记录。', 'sources': self.sources[:7], 'checkpoint': 0}
        with self.app.store.transaction() as con:
            con.execute('UPDATE games SET state=? WHERE id=?', (canonical(self.saved), self.gid))

    def update(self, count):
        return {'upsert': [{'id': 'm4', 'kind': 'self_claim', 'text': '我仍想核对记录。',
                            'sources': self.sources[:count]}],
                'archive': [], 'processed_through': None}

    def transport(self, payload):
        self.payloads.append(deepcopy(payload))
        wire = json.loads(payload['messages'][-1]['content'])
        update = self.update(10)
        if wire.get('validation_feedback', {}).get('code') != 'memory_entry_sources':
            update['upsert'][0]['sources'].append('B-o999999')
        return {'choices': [{'finish_reason': 'stop', 'message': {
            'content': canonical({'memory_update': update})}}]}

    def worker(self, state, call):
        data = w.context(state, 'A'); supplied = {o['id'] for o in data['observations']}
        def validate(out):memory.revised(state, 'A', out['memory_update'], supplied)
        out, _ = call('role_A', 'ensemble_role', w.baseline(state, 'A'), data, validate, 'A')
        memory.apply(state, 'A', out['memory_update'], supplied)

    def test_7_to_10_update_retains_every_reference(self):
        before = deepcopy(self.saved)
        result, _ = memory.revised(self.saved, 'A', self.update(10), set(self.sources))
        self.assertEqual(result['entries'][0]['sources'], self.sources[:10])
        self.assertEqual(self.saved, before)

    def test_source_shape_duplicates_and_private_ids_remain_rejected(self):
        for sources, reason in [(None, 'expected_list'), ([], 'empty_sources'),
                                ([self.sources[0]] * 2, 'duplicate_sources'),
                                (['B-o999999'], 'unavailable_sources'),
                                ([{'secret': 'not a source'}], 'unavailable_sources')]:
            with self.subTest(sources=sources):
                patch = self.update(1); patch['upsert'][0]['sources'] = sources
                with self.assertRaises(memory.EntrySourcesError) as error:
                    memory.revised(self.saved, 'A', patch, set(self.sources))
                self.assertIn(reason, error.exception.feedback['problems'])
                self.assertNotIn('B-o999999', canonical(error.exception.feedback))
                self.assertNotIn('not a source', canonical(error.exception.feedback))

    def test_pinned_role_retry_gets_feedback_and_keeps_originals(self):
        self.app.gateway.client.transport = self.transport
        state, _ = self.app.operate(self.owner, self.gid, self.command, self.worker)
        wires = [json.loads(p['messages'][-1]['content']) for p in self.payloads]
        feedback = wires[1].pop('validation_feedback')
        self.assertEqual(wires[0], wires[1])
        self.assertEqual(feedback['problems'], ['unavailable_sources'])
        self.assertEqual(feedback['limits'], {})
        self.assertFalse(feedback['source_count_limited'])
        rows = self.calls()
        self.assertEqual([r['status'] for r in rows], ['failed', 'completed'])
        self.assertEqual(len({r['prefix_hash'] for r in rows}), 1)
        self.assertEqual(json.loads(rows[1]['request_feedback']), feedback)
        for key in ('observations', 'events', 'known', 'case'):
            self.assertEqual(state[key], self.saved[key])
        self.assertEqual(state['memory_archive']['A'][0]['sources'], self.sources[:7])

    def test_paid_corrected_stage_replays_after_restart_without_new_call(self):
        self.app.gateway.client.transport = self.transport
        def interrupted(state, call):
            self.worker(state, call)
            raise StoreError('Fixture interrupted after paid stage', 503, 'connection_failed')
        with self.assertRaises(StoreError):
            self.app.operate(self.owner, self.gid, self.command, interrupted)
        before = self.calls()
        self.app = EnsembleApplication(self.app.store.path, DeepSeek(Settings(api_key='fixture'), self.transport))
        self.app.operate(self.owner, self.gid, self.command, self.worker)
        self.assertEqual(len(self.payloads), 2)
        self.assertEqual(self.calls(), before)

    def test_four_failures_require_manual_retry_and_preserve_feedback(self):
        def bad(payload):
            response = self.transport(payload)
            invalid = self.update(10); invalid['upsert'][0]['sources'].append('B-o999999')
            response['choices'][0]['message']['content'] = canonical({'memory_update': invalid})
            return response
        self.app.gateway.client.transport = bad
        with self.assertRaises(StoreError) as error:
            self.app.operate(self.owner, self.gid, self.command, self.worker)
        self.assertEqual(error.exception.code, 'retry_exhausted')
        self.assertEqual(self.app.store.state(self.owner, self.gid)['memory'], self.saved['memory'])
        before = self.calls(); self.assertEqual(len(before), 4)
        self.app = EnsembleApplication(self.app.store.path, DeepSeek(Settings(api_key='fixture'), self.transport))
        self.app.gateway.retry_delays = (0, 0, 0)
        with self.assertRaises(StoreError):self.app.operate(self.owner, self.gid, self.command, self.worker)
        self.assertEqual(self.calls(), before)
        with self.app.store.transaction() as con:
            self.app.gateway.renew_retry(con, self.gid, self.command['command_id'])
        self.app.operate(self.owner, self.gid, self.command, self.worker)
        self.assertEqual(len(self.calls()), 5)
        self.assertEqual(self.calls()[:4], before)
        self.assertEqual(len({r['prefix_hash'] for r in self.calls()}), 1)

    def test_snapshot_retries_get_same_entry_correction(self):
        self.app.gateway.current_version = 'ai-tasks-v90.json'
        def transport(payload):
            response = self.transport(payload)
            update = self.update(10)
            if len(self.payloads) == 1:update['upsert'][0]['sources'].append('B-o999999')
            response['choices'][0]['message']['content'] = canonical({
                'entries': update['upsert'], 'processed_through': self.sources[-1]})
            return response
        def worker(state, call):
            self.app.summarize_chunk(state, 'A', call, len(state['observations']['A']))
        self.app.gateway.client.transport = transport
        state, _ = self.app.operate(self.owner, self.gid, self.command, worker)
        self.assertEqual([r['status'] for r in self.calls()], ['failed', 'completed'])
        self.assertEqual(state['memory']['A']['checkpoint'], len(state['observations']['A']))

    def test_old_version_keeps_unmodified_retry_payload(self):
        self.app.gateway.current_version = 'ai-tasks-v74.json'
        def transport(payload):
            response = self.transport(payload)
            if len(self.payloads) > 1:
                response['choices'][0]['message']['content'] = canonical({'memory_update': self.update(8)})
            return response
        self.app.gateway.client.transport = transport
        self.app.operate(self.owner, self.gid, self.command, self.worker)
        self.assertEqual(self.payloads[0], self.payloads[1])
        self.assertTrue(all(r['validation_feedback'] is None for r in self.calls()))

    def test_prefix_changes_only_memory_guidance_and_preserves_settings(self):
        root = Path('palter/prefixes')
        for name, digest in json.loads((root/'manifest.json').read_text()).items():
            self.assertEqual(hashlib.sha256((root/name).read_bytes()).hexdigest(), digest)
        old = self.app.gateway.versions['ai-tasks-v89.json']
        new = deepcopy(self.app.gateway.versions['ai-tasks-v90.json'])
        for spec in [new['ensemble_role'], *new['ensemble_role']['perspectives'].values(), new['ensemble_memory']]:
            self.assertTrue(spec['instruction'].startswith('ENTRY SOURCE BUDGET:'))
            spec['instruction'] = spec['instruction'].split('\n', 1)[1]
        self.assertEqual(new, old)


if __name__ == '__main__':unittest.main()
