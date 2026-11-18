"""Unused annotations cannot reject memory or become remembered facts."""
from copy import deepcopy
import json
import unittest

from palter import ensemble_world as w, memory_entries as memory
from palter.storage import canonical
from tests import test_ensemble_review as fixtures

VERSION = 'ai-tasks-v97.json'


class MemoryExtraFieldsTests(unittest.TestCase):
    def setUp(self):
        f = fixtures.ReviewFixTests(); f.setUp(); self.addCleanup(f.doCleanups)
        self.f = f; self.app = f.app; self.s = f.state
        self.app.gateway.current_version = VERSION
        w.speak(self.s, 'A', '我说过会检查，但还没有完成。')
        self.source = self.s['observations']['A'][-1]['id']
        self.supplied = {row['id'] for row in self.s['observations']['A']}
        # Deliberately retain the model's field order for pinned request replay.
        self.entry = {'id': 'm0', 'kind': 'self_claim', 'sources': [self.source],
                      'text': '我声称会检查，尚无完成回执。'}
        self.end = len(self.s['observations']['A'])

    def snapshot(self, note=None):
        return {'entries': [dict(deepcopy(self.entry), sources_note=note)],
                'processed_through': self.source, 'annotation': note}

    def patch(self, note=None):
        return {'upsert': [dict(deepcopy(self.entry), sources_note=note)],
                'archive': [], 'processed_through': self.source, 'annotation': note}

    def caller(self, out, version=VERSION):
        def call(stage, task, baseline, data, validate, actor=None):
            validate(out)
            return out, 'memory-extra-fields-fixture'
        call.prefix_version = version
        return call

    def test_snapshots_ignore_null_and_nonnull_metadata_without_mutation(self):
        for version in ('ai-tasks-v69.json', VERSION):
            for note in (None, 'unused annotation', {'archive': ['m0'], 'text': 'not a memory'}):
                with self.subTest(version=version, note=note):
                    state = deepcopy(self.s); before = deepcopy(state)
                    out = self.snapshot(note); raw = deepcopy(out)
                    self.app.summarize_chunk(state, 'A', self.caller(out, version), self.end)
                    self.assertEqual(state['memory']['A']['entries'], [self.entry])
                    self.assertEqual(list(state['memory']['A']['entries'][0]), list(self.entry))
                    self.assertEqual(state['memory']['A']['checkpoint'], self.end)
                    self.assertEqual(out, raw)
                    for key in ('case', 'events', 'observations', 'known'):
                        self.assertEqual(state[key], before[key])
                    self.assertNotIn('sources_note', canonical(memory.project(state['memory']['A'])))

    def test_incremental_patch_ignores_metadata_without_false_archival(self):
        initial = self.patch(); del initial['upsert'][0]['sources_note']
        memory.apply(self.s, 'A', initial, self.supplied)
        archived = deepcopy(self.s.get('memory_archive', {}).get('A', []))
        for note in (None, {'sources': ['FOREIGN'], 'text': 'do not merge'}):
            update = self.patch(note); raw = deepcopy(update)
            memory.apply(self.s, 'A', update, self.supplied)
            self.assertEqual(update, raw)
            self.assertEqual(self.s['memory']['A']['entries'], [self.entry])
            self.assertEqual(self.s.get('memory_archive', {}).get('A', []), archived)
        update = self.patch('do not archive'); update['upsert'][0]['text'] = '我仍需执行检查。'
        memory.apply(self.s, 'A', update, self.supplied)
        self.assertEqual(self.s['memory_archive']['A'], archived + [dict(self.entry, archived_revision=self.s['revision'])])

    def test_legacy_incremental_summary_envelope_ignores_extras(self):
        version = next(name for name, spec in self.app.gateway.versions.items()
                       if spec.get('ensemble_memory', {}).get('compact_context')
                       and not spec['ensemble_memory'].get('memory_snapshot'))
        out = {'memory_update': self.patch('unused'), 'annotation': None}
        self.app.summarize_chunk(self.s, 'A', self.caller(out, version), self.end)
        self.assertEqual(self.s['memory']['A']['entries'], [self.entry])

    def test_required_fields_cannot_be_replaced_by_annotations(self):
        for field in (*memory.ENTRY_FIELDS, 'entries', 'processed_through'):
            out = self.snapshot({'missing_value': 'not a substitute'})
            target = out['entries'][0] if field in memory.ENTRY_FIELDS else out
            del target[field]; before = deepcopy(self.s)
            with self.subTest(field=field), self.assertRaises(ValueError):
                self.app.summarize_chunk(self.s, 'A', self.caller(out), self.end)
            self.assertEqual(self.s, before)
        for field in ('upsert', 'archive', 'processed_through'):
            update = self.patch(); del update[field]
            with self.subTest(field=field), self.assertRaises(ValueError):
                memory.revised(self.s, 'A', update, {self.source})

    def test_known_field_validation_and_capacity_remain_strict(self):
        bad = [('id', None), ('kind', 'fact'), ('text', None), ('text', '   '),
               ('sources', None), ('sources', []), ('sources', [self.source, self.source]),
               ('sources', ['B-o999999'])]
        for key, value in bad:
            update = self.patch(); update['upsert'][0][key] = value
            before = deepcopy(self.s)
            with self.subTest(key=key, value=value), self.assertRaises(ValueError):
                memory.apply(self.s, 'A', update, {self.source})
            self.assertEqual(self.s, before)
        for count, size in ((13, 5), (13, 240)):
            out = self.snapshot(); out['entries'] = [dict(out['entries'][0], id=f'm{i}', text='x' * size) for i in range(count)]
            with self.subTest(count=count), self.assertRaises(memory.CapacityError):
                self.app.summarize_chunk(self.s, 'A', self.caller(out), self.end)
        out = self.snapshot(); out['processed_through'] = None
        with self.assertRaises(memory.CheckpointError):
            self.app.summarize_chunk(self.s, 'A', self.caller(out), self.end)

    def test_role_decision_uses_same_memory_projection(self):
        raw = []
        def transform(task, out, data):
            if task == 'ensemble_role':
                out['memory_update'] = self.patch({'fact': 'must not become known'})
                raw.append(out)
        self.app.turn(self.s, 'A', self.f.caller(VERSION, transform), 0)
        self.assertEqual(self.s['memory']['A']['entries'], [self.entry])
        self.assertIn('sources_note', raw[0]['memory_update']['upsert'][0])

    def test_gateway_accepts_once_preserves_raw_receipt_and_replays(self):
        calls = []; out = self.snapshot({'note': 'keep only in the raw receipt'})
        response = {'choices': [{'finish_reason': 'stop', 'message': {'content': canonical(out)}}],
                    'usage': {'prompt_tokens': 100, 'completion_tokens': 60,
                              'prompt_cache_hit_tokens': 40, 'prompt_cache_miss_tokens': 60}}
        def provider(payload):
            calls.append(deepcopy(payload)); return deepcopy(response)
        self.app.gateway.client.transport = provider
        owner = self.app.store.session()['id']; self.s['watch']['budget_usd'] = 2
        saved = self.app.store.create_game(owner, {'command_id': 'extra_create', 'expected_game_id': None},
                                          lambda gid: dict(deepcopy(self.s), id=gid))
        command = {'command_id': 'extra_operation', 'expected_revision': saved['revision'], 'kind': 'probe'}
        def work(state, call):
            self.app.summarize_chunk(state, 'A', call, len(state['observations']['A']))
        state, _ = self.app.operate(owner, saved['id'], command, work)
        self.assertEqual(len(calls), 1)
        self.assertEqual(state['memory']['A']['entries'], [self.entry])
        with self.app.store.transaction(False) as con:
            before = [dict(row) for row in con.execute('SELECT * FROM ai_calls')]
        self.assertEqual(before[0]['status'], 'completed')
        self.assertEqual(json.loads(before[0]['result']), out)
        self.assertEqual(json.loads(before[0]['response']), response)
        recovered, _ = self.app.operate(owner, saved['id'], command, work)
        self.assertEqual(recovered, state); self.assertEqual(len(calls), 1)
        with self.app.store.transaction(False) as con:
            self.assertEqual([dict(row) for row in con.execute('SELECT * FROM ai_calls')], before)


if __name__ == '__main__':
    unittest.main()
