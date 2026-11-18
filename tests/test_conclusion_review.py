"""Final score provenance, declared equivalents, role reviews and pinned replay."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import unittest

from palter import ensemble_world as w, ensemble_review as review, spectator
from palter.scenario_cases import build
from palter.storage import canonical
from tests import test_ensemble_review as fixtures
from tests.test_ensemble import story_fixture

VERSION = 'ai-tasks-v73.json'


class ConclusionReviewTests(unittest.TestCase):
    def setUp(self):
        self.f = fixtures.ReviewFixTests(); self.f.setUp(); self.addCleanup(self.f.doCleanups)
        self.app = self.f.app
        self.prepare(1)

    def prepare(self, seed):
        preview = deepcopy(self.f.state['preview'])
        self.s = w.blank('abcd' * 6, 'murder', 0, 'after'); spectator.initialize(self.s)
        self.s['preview'] = preview
        self.s['closure'] = {'ready': True, 'votes': list('ABC')}
        w.initialize(self.s, build(story_fixture(), preview, 'murder', seed, [], rules_version=3)); w.start(self.s)
        self.s['exploration_version'] = 1
        self.actor = next(a for a in w.ACTORS if a != self.s['case']['solution']['killer'])
        self.f.inputs.clear()

    def acquire(self, ids, actor=None):
        actor = actor or self.actor
        for cid in ids:
            w.acquire(self.s, actor, cid, w.emit(self.s, 'inspect', actor, cid), '测试检查')

    def submit(self, ids, actor=None, **overrides):
        actor = actor or self.actor
        self.s['submissions'][actor] = {'suspect': self.s['case']['solution']['killer'],
            'explanation': '我根据时间边界、保管记录和现场痕迹相互核对，作出指认。',
            'evidence_ids': list(ids), 'testimony_ids': [], **overrides}

    def conclude(self, transform=None, version=VERSION):
        self.app.conclude_ensemble(self.s, self.f.caller(version, transform))
        return self.s['results']['participants'][self.actor]['reasoning']

    def test_mixed_originals_and_copies_establish_both_families(self):
        for seed, ids in ((1, ['c1','c2','c3','c4','c9','c10','c11']),
                          (2, ['c1','c2','c3','c11','c7','c9'])):
            with self.subTest(seed=seed):
                self.prepare(seed); self.acquire(ids); self.submit(ids)
                self.assertFalse(any(set(route) <= set(ids) for route in self.s['case']['proofs']['identity']))
                before = canonical({k:self.s[k] for k in ('known','observations','submissions','case')})
                r = self.conclude()
                self.assertEqual(r['result'], 'established')
                self.assertEqual(before, canonical({k:self.s[k] for k in ('known','observations','submissions','case')}))
                self.assertEqual(len([t for t,d in self.f.inputs if t == 'ensemble_theory']), 1)
                data = next(d for t,d in self.f.inputs if t == 'ensemble_theory')
                self.assertTrue(all(set(route) <= set(ids) for routes in data['proof_routes'].values() for route in routes))
                self.assertNotIn('process', data); self.assertNotIn('events', data)

    def test_missing_original_is_not_filled_by_unrelated_or_duplicate_copies(self):
        ids = ['c1','c3','c4','c7','c9','c10','c11','c14']
        self.acquire(ids); self.submit(ids)
        r = self.conclude()
        self.assertEqual(r['result'], 'unproven'); self.assertEqual(r['established'], ['method'])
        gap = r['aspects']['time']['gaps'][0]
        self.assertEqual(gap['status'], 'not_acquired'); self.assertEqual(gap['alternatives'][0]['id'], 'c2')

    def test_gap_distinguishes_acquired_uncited_and_selected_unused(self):
        ids = ['c1','c2','c3','c4','c9','c10','c11']
        for status in ('not_cited', 'not_used'):
            with self.subTest(status=status):
                self.prepare(1); self.acquire(ids)
                self.submit([c for c in ids if c != 'c2'] if status == 'not_cited' else ids)
                def response(task, out, data):
                    if task == 'ensemble_theory' and status == 'not_used':
                        out['argument_sources'].remove('c2')
                r = self.conclude(response)
                self.assertEqual(r['aspects']['time']['gaps'][0]['status'], status)
                self.assertFalse(r['aspects']['time']['established'])

    def test_complete_sources_do_not_repair_a_temporal_error(self):
        ids = ['c1','c2','c3','c4','c9','c10','c11']; self.acquire(ids); self.submit(ids)
        def response(task, out, data):
            if task == 'ensemble_theory':
                c = next(c for c in out['claims'] if c['aspect'] == 'time')
                c.update(supported=False, reason='把发现死亡的时刻当成精确死亡时刻。')
        r = self.conclude(response); a = r['aspects']['time']
        self.assertTrue(a['proof_covered']); self.assertFalse(a['established']); self.assertEqual(a['gaps'], [])
        self.assertIn('精确死亡', a['reason']); self.assertEqual(r['result'], 'unproven')

    def test_heard_document_description_never_supplies_document(self):
        ids = ['c1','c3','c4','c9','c10','c11']; self.acquire(ids)
        event = w.speak(self.s, 'D', '我看过首次确认死亡的原始记录。')
        sid = next(o['id'] for o in self.s['observations'][self.actor] if o['event_id'] == event['id'])
        self.submit(ids, testimony_ids=[sid])
        def response(task, out, data):
            if task == 'ensemble_theory':out['argument_sources'].append(sid)
        r = self.conclude(response)
        self.assertFalse(r['aspects']['time']['proof_covered']); self.assertEqual(r['testimony'][0]['provenance'], 'heard_claim')
        self.assertNotIn('c2', self.s['known'][self.actor])

    def test_invalid_or_unheard_model_sources_are_rejected(self):
        self.acquire(['c1']); self.submit(['c1'])
        def response(task, out, data):
            if task == 'ensemble_theory':out['argument_sources'].append('c2')
        with self.assertRaises(ValueError):self.conclude(response)
        self.assertNotEqual(self.s['phase'], 'ended')

    def test_missing_duplicate_aspect_or_empty_reason_rejected(self):
        claims = [{'aspect':a,'supported':False,'evidence_ids':[],'reason':'未论述。'} for a in review.ASPECTS]
        for bad in (claims[:2], [claims[0],claims[0],claims[2]], [dict(c, reason='') for c in claims]):
            with self.assertRaises(ValueError):review.validate_response({'claims':bad,'argument_sources':[]}, set())

    def test_wrong_accusation_cannot_win_even_if_model_claims_support(self):
        ids = ['c1','c2','c3','c4','c9','c10','c11']; self.acquire(ids); self.submit(ids, suspect=self.actor)
        r = self.conclude(); self.assertEqual(r['result'], 'incorrect'); self.assertFalse(r['accusation_correct'])
        self.assertFalse(r['aspects']['identity']['established'])
        self.assertFalse(self.s['results']['shared_success'])

    def test_no_submission_never_uses_private_belief_or_calls_theory(self):
        for actor in w.ACTORS:
            self.s['beliefs'][actor] = {'suspect':self.s['case']['solution']['killer'],'explanation':'私下的判断','evidence_ids':[]}
        r = self.conclude()
        self.assertEqual(r['result'], 'unresolved'); self.assertEqual(r['submission'], {})
        self.assertEqual([t for t,d in self.f.inputs], ['ensemble_ending'])

    def test_culprit_review_keeps_voluntary_admission_and_actual_objectives(self):
        self.actor = self.s['case']['solution']['killer']
        ids = ['c1','c2','c3','c4','c9','c10','c11']; self.acquire(ids); self.submit(ids)
        r = self.conclude(); p = self.s['results']['participants'][self.actor]
        self.assertEqual(r['perspective'], 'concealment'); self.assertEqual(r['result'], 'established')
        self.assertEqual(r['submission']['suspect'], self.actor)
        self.assertFalse(p['primary']); self.assertIn('避免定案', r['process']['primary_reason'])
        self.assertEqual(next(d for t,d in self.f.inputs if t == 'ensemble_theory')['perspective'], 'concealment')

    def test_culprit_without_accusation_is_not_forced_to_investigate(self):
        self.actor = self.s['case']['solution']['killer']; self.submit([], suspect=None, explanation='我保留我的立场。')
        w.contribute(self.s, self.actor, 'test-action')
        r = self.conclude()
        self.assertTrue(self.s['results']['participants'][self.actor]['primary'])
        self.assertIn('避免定案的目标达成', r['process']['primary_reason'])
        self.assertEqual([t for t,d in self.f.inputs], ['ensemble_ending'])
        for aspect in r['aspects'].values():
            self.assertFalse(aspect['evaluated']); self.assertIsNone(aspect['semantic_supported'])
            self.assertEqual(aspect['gaps'], [])

    def test_process_is_actor_scoped_and_never_supplies_missing_citations(self):
        self.acquire(['c1']); self.submit(['c1'])
        other = next(a for a in w.ACTORS if a != self.actor)
        self.acquire(['c2'], other)
        r = self.conclude()
        self.assertIn('not_acquired', [g['status'] for g in r['aspects']['time']['gaps']])
        self.assertEqual(r['process']['known_records'], len(self.s['known'][self.actor]))
        self.assertEqual(r['process']['received_records'], 0)
        self.assertIn('r3', [r['id'] for r in r['process']['unvisited_rooms']])

    def test_reviews_hidden_until_ended_and_historical_results_not_mutated(self):
        self.submit([], suspect=None); self.conclude()
        saved = canonical(self.s)
        self.s['phase'] = 'active'; self.assertIsNone(w.view(self.s, self.actor)['results'])
        self.s['phase'] = 'ended'; self.assertEqual(canonical(self.s), saved)
        projected = w.view(self.s, self.actor); projected['results']['shared_success'] = 'mutation'
        self.assertEqual(canonical(self.s), saved)

    def test_v72_payload_and_result_contract_retained(self):
        ids = ['c1','c2','c3','c4','c9','c10','c11']; self.acquire(ids); self.submit(ids)
        r = self.conclude(version='ai-tasks-v72.json')
        self.assertEqual(set(r), {'result','established','suspect'}); self.assertEqual(r['result'], 'unproven')
        old = next(d for t,d in self.f.inputs if t == 'ensemble_theory')
        self.assertNotIn('review_version', old); self.assertEqual(old['proof_routes']['identity'], [])
        root = Path('palter/prefixes'); manifest = json.loads((root/'manifest.json').read_text())
        for name,digest in manifest.items():self.assertEqual(hashlib.sha256((root/name).read_bytes()).hexdigest(), digest)
        v72 = json.loads((root/'ai-tasks-v72.json').read_text()); v73 = json.loads((root/VERSION).read_text())
        self.assertEqual([t for t in v73 if v73[t] != v72[t]], ['ensemble_theory'])
        self.assertEqual(v72['ensemble_theory']['tokens'], v73['ensemble_theory']['tokens'])


if __name__ == '__main__':unittest.main()
