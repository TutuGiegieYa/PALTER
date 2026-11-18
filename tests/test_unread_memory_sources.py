"""Pre-action citations, precise scoped correction and paid tool recovery."""
from copy import deepcopy
import json
import unittest
from unittest.mock import patch

from palter import ensemble_world as w, memory_entries as memory, compact_context
from palter.deepseek import DeepSeek, Settings
from palter.ensemble import EnsembleApplication
from palter.storage import StoreError, canonical
from tests import test_runtime_integrity as fixtures

VERSION = 'ai-tasks-v92.json'


class UnreadMemoryTests(unittest.TestCase):
    def setUp(self):
        self.f = fixtures.RuntimeIntegrityTests(); self.f.setUp(); self.addCleanup(self.f.doCleanups)
        self.app, self.s, self.actor = self.f.app, self.f.s, self.f.actor
        self.app.gateway.current_version = VERSION; self.app.gateway.retry_delays = (0, 0, 0)
        self.cid = 'c10'
        self.s['locations'] = dict.fromkeys('ABCD', self.s['objects'][self.cid]['holder'])
        self.s['objects'][self.cid]['hidden'] = False
        speaker = next(a for a in 'ABCD' if a != self.actor)
        w.speak(self.s, speaker, '桌上有一份独立记录，我们还没有翻开。')
        self.heard = self.s['observations'][self.actor][-1]['id']
        self.payloads = []

    def output(self, unread=True):
        out = deepcopy(self.app.gateway.versions[VERSION]['ensemble_role']['example'])
        out.update(action={'kind': 'inspect', 'args': [self.cid]}, speech='我这就亲手核对那份记录。',
            memory_update={'upsert': [{'id': 'm1', 'kind': 'unresolved',
                'text': '我听到有人提及桌上的独立记录，尚未亲自核实，准备查看。',
                'sources': [self.heard, self.cid] if unread else [self.heard]}],
                'archive': [], 'processed_through': self.heard},
            next_decision={'mode': 'continue', 'events': []})
        return out

    def test_exact_unread_id_disclosed_only_from_own_action_menu(self):
        before = deepcopy(self.s)
        data = w.context(self.s, self.actor)
        with self.assertRaises(memory.EntrySourcesError) as error:
            memory.decision(self.s, self.actor, self.output(), data)
        feedback = memory.correction_feedback(error.exception.feedback)
        self.assertEqual(feedback['invalid_sources'], [
            {'index': 1, 'id': self.cid, 'reason': 'visible_but_unread', 'permitted_use': 'action_target_only'}])
        self.assertEqual(feedback['invalid_source_count'], 1)
        self.assertIn('pre-action knowledge', feedback['instruction'])
        self.assertEqual(self.s, before)
        self.s['objects'][self.cid]['hidden'] = True
        with self.assertRaises(memory.EntrySourcesError) as error:
            memory.decision(self.s, self.actor, self.output(), w.context(self.s, self.actor))
        self.assertNotIn(self.cid, canonical(error.exception.feedback))
        self.assertEqual(error.exception.feedback['invalid_sources'], [{'index': 1, 'reason': 'not_authorized'}])

    def test_unavailable_lookup_does_not_acquire_but_actual_inspection_does(self):
        before = deepcopy(self.s)
        result = compact_context.lookup(self.s, self.actor, {'requests': [{'id': self.cid}]})
        self.assertEqual(result['sources'], [{'id': self.cid, 'status': 'unavailable'}])
        self.assertEqual(self.s, before)
        w.apply_choice(self.s, self.actor, 'inspect:' + self.cid)
        data = w.context(self.s, self.actor)
        out = memory.decision(self.s, self.actor, self.output(), data)
        self.assertIn(self.cid, out['memory_sources'])
        self.assertIn(self.cid, self.s['known'][self.actor])

    def test_heard_mention_can_support_unresolved_memory_before_inspection(self):
        before = deepcopy(self.s)
        out = memory.decision(self.s, self.actor, self.output(False), w.context(self.s, self.actor))
        self.assertEqual(out['choice'], 'inspect:' + self.cid)
        self.assertEqual(out['memory_sources'], [self.heard])
        self.assertNotIn(self.cid, self.s['known'][self.actor])
        self.assertEqual(self.s, before)

    def test_snapshot_uses_same_scoped_feedback(self):
        out = self.output()['memory_update']
        def call(stage, task, baseline, data, validate, actor=None):
            validate({'entries': out['upsert'], 'processed_through': self.heard})
        call.prefix_version = VERSION
        with self.assertRaises(memory.EntrySourcesError) as error:
            self.app.summarize_chunk(self.s, self.actor, call, len(self.s['observations'][self.actor]))
        self.assertEqual(error.exception.feedback['invalid_sources'][0]['id'], self.cid)

    def transport(self, payload):
        self.payloads.append(deepcopy(payload))
        if not any(m['role'] == 'tool' for m in payload['messages']):
            return {'choices': [{'finish_reason': 'tool_calls', 'message': {'role': 'assistant', 'content': '',
                'tool_calls': [{'id': 'synthetic_lookup', 'type': 'function', 'function': {
                    'name': 'read_sources', 'arguments': canonical({'requests': [{'id': self.cid}]})}}]}}]}
        data = json.loads(next(m['content'] for m in payload['messages'] if m['role'] == 'user'))
        feedback = data.get('validation_feedback', {})
        precise = any(row.get('id') == self.cid for row in feedback.get('invalid_sources', []))
        return {'choices': [{'finish_reason': 'stop', 'message': {'content': canonical(self.output(not precise))}}]}

    def test_native_continuation_correction_and_paid_stages_replay_without_rebuying(self):
        self.s['watch'].update(budget_usd=1, call_limit=64)
        self.app.gateway.client.transport = self.transport
        owner = self.app.store.session()['id']
        state = self.app.store.create_game(owner, {'command_id': 'create_unread_fixture', 'expected_game_id': None},
            lambda gid: dict(deepcopy(self.s), id=gid))
        command = {'command_id': 'inspect_unread_fixture', 'expected_revision': state['revision'], 'kind': 'probe'}
        def work(state, call):self.app.turn(state, self.actor, call, 0)
        def interrupted(state, call):
            work(state, call)
            raise StoreError('Synthetic interruption after paid continuation', 503, 'connection_failed')
        with self.assertRaises(StoreError):self.app.operate(owner, state['id'], command, interrupted)
        with self.app.store.transaction(False) as con:
            rows = [dict(r) for r in con.execute('SELECT * FROM ai_calls WHERE game_id=? ORDER BY started', (state['id'],))]
        self.assertEqual([r['status'] for r in rows], ['completed', 'failed', 'completed'])
        self.assertEqual(json.loads(rows[2]['request_feedback'])['invalid_sources'][0]['id'], self.cid)
        self.assertEqual(self.app.store.state(owner, state['id'])['known'], state['known'])
        self.app = EnsembleApplication(self.app.store.path, DeepSeek(Settings(api_key='fixture'), self.transport))
        result, _ = self.app.operate(owner, state['id'], command, work)
        self.assertEqual(len(self.payloads), 3)
        with self.app.store.transaction(False) as con:
            self.assertEqual([dict(r) for r in con.execute('SELECT * FROM ai_calls WHERE game_id=? ORDER BY started', (state['id'],))], rows)
        self.assertIn(self.cid, result['known'][self.actor])
        self.assertEqual(result['memory'][self.actor]['sources'], [self.heard])
        self.assertEqual(sum(e['kind']=='inspect' and e['actor']==self.actor and e['target']==self.cid
                             for e in result['events']), 1)

    def test_diagnostic_bound_does_not_limit_stored_citations(self):
        unknown = ['foreign-private-' + str(i) for i in range(40)]
        error = memory.EntrySourcesError('m1', unknown, set()).with_context(w.context(self.s, self.actor))
        self.assertEqual(error.feedback['invalid_source_count'], 40)
        self.assertTrue(error.feedback['invalid_sources_truncated'])
        self.assertEqual(len(error.feedback['invalid_sources']), 12)
        self.assertNotIn('foreign-private', canonical(error.feedback))

    def test_exhausted_v91_feedback_is_enriched_locally_before_manual_retry(self):
        self.app.gateway.current_version = 'ai-tasks-v91.json'
        self.s['watch'].update(budget_usd=1, call_limit=64)
        self.app.gateway.client.transport = self.transport
        owner = self.app.store.session()['id']
        state = self.app.store.create_game(owner, {'command_id': 'create_old_unread', 'expected_game_id': None},
            lambda gid: dict(deepcopy(self.s), id=gid))
        command = {'command_id': 'inspect_old_unread', 'expected_revision': state['revision'], 'kind': 'probe'}
        def work(state, call):self.app.turn(state, self.actor, call, 0)
        # Recreate the previous generic failure without changing saved history.
        with patch.object(memory.EntrySourcesError, 'with_context', lambda error, data: error):
            with self.assertRaises(StoreError):self.app.operate(owner, state['id'], command, work)
        def rows():
            with self.app.store.transaction(False) as con:
                return [dict(r) for r in con.execute('SELECT * FROM ai_calls WHERE game_id=? ORDER BY started', (state['id'],))]
        before = rows(); self.assertEqual(len(before), 5)
        self.app = EnsembleApplication(self.app.store.path, DeepSeek(Settings(api_key='fixture'), self.transport))
        self.app.gateway.retry_delays = (0, 0, 0)
        with self.assertRaises(StoreError):self.app.operate(owner, state['id'], command, work)
        self.assertEqual(rows(), before)
        with self.app.store.transaction() as con:self.app.gateway.renew_retry(con, state['id'], command['command_id'])
        result, _ = self.app.operate(owner, state['id'], command, work)
        after = rows(); self.assertEqual(after[:5], before); self.assertEqual(len(after), 6)
        self.assertEqual(json.loads(after[-1]['request_feedback'])['invalid_sources'][0]['id'], self.cid)
        self.assertEqual(after[-1]['status'], 'completed')
        self.assertIn(self.cid, result['known'][self.actor])

    def test_prefix_changes_only_guidance_and_retains_unbounded_citations(self):
        old = self.app.gateway.versions['ai-tasks-v91.json']; new = deepcopy(self.app.gateway.versions[VERSION])
        for spec in [new['ensemble_role'], *new['ensemble_role']['perspectives'].values(), new['ensemble_memory']]:
            self.assertTrue(spec['instruction'].startswith('PRE-ACTION MEMORY:'))
            spec['instruction'] = spec['instruction'].split('\n', 1)[1]
        self.assertEqual(new, old)


if __name__ == '__main__':unittest.main()
