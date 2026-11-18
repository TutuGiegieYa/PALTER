"""Role-specific grading, scoped final evidence, outcomes and historical replay."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import unittest

from palter import ensemble_world as w, ensemble_position_review as position
from palter.storage import canonical
from tests import test_conclusion_review as fixtures

VERSION = 'ai-tasks-v96.json'
IDS = ['c1','c2','c3','c4','c9','c10','c11']


class PositionReviewTests(unittest.TestCase):
    def setUp(self):
        self.f = fixtures.ConclusionReviewTests(); self.f.setUp(); self.addCleanup(self.f.doCleanups)
        self.s = self.f.s; self.app = self.f.app
        self.killer = self.s['case']['solution']['killer']; self.investigator = self.f.actor

    def conclude(self, transform=None, version=VERSION):
        self.f.conclude(transform, version)
        return self.s['results']['participants'][self.killer]['reasoning']

    def defense(self, suspect=None, text='我没有实施伤害，暂不指认别人。'):
        self.f.submit([], self.killer, suspect=suspect, explanation=text)
        w.contribute(self.s, self.killer, 'actual-test-participation')

    def establish(self, ids=IDS):
        self.f.acquire(ids, self.investigator); self.f.submit(ids, self.investigator)

    def inputs(self):
        return [d for t,d in self.f.f.inputs if t == 'ensemble_theory']

    def test_denial_has_separate_contract_and_actual_case_exposure(self):
        self.establish(); self.defense(self.investigator)
        before = canonical({k:self.s[k] for k in ('known','observations','beliefs','submissions','case')})
        r = self.conclude(); p = self.s['results']['participants'][self.killer]
        self.assertEqual(r['assessment_type'], 'position'); self.assertNotIn('aspects', r)
        self.assertNotIn('accusation_correct', r); self.assertEqual(r['established'], [])
        self.assertEqual(r['result'], 'position_recorded'); self.assertFalse(p['primary'])
        self.assertTrue(r['exposure']['established'])
        self.assertEqual(r['exposure']['established_by'], [{'actor':self.investigator,
            'name':w.name(self.s,self.investigator),'self_submission':False}])
        self.assertEqual(before, canonical({k:self.s[k] for k in ('known','observations','beliefs','submissions','case')}))
        inputs = self.inputs(); self.assertNotIn('review_mode', inputs[0])
        self.assertEqual(inputs[-1]['review_mode'], 'concealment')
        self.assertNotIn('solution', inputs[-1]); self.assertNotIn('proof_routes', inputs[-1])
        self.assertNotIn('history', inputs[-1]); self.assertNotIn('belief', inputs[-1])

    def test_withheld_accusation_gets_position_review_without_deduction_penalty(self):
        self.defense(); r = self.conclude()
        self.assertEqual(len(self.inputs()), 1)
        self.assertTrue(self.s['results']['participants'][self.killer]['primary'])
        self.assertFalse(r['exposure']['established']); self.assertNotIn('aspects',r)

    def test_no_submission_or_empty_explanation_needs_no_review_call(self):
        self.s['beliefs'][self.killer] = {'suspect':self.killer,'explanation':'私下知道自己所为','evidence_ids':IDS}
        self.s['strategies'] = {self.killer:{'situation':'PRIVATE_STRATEGY','plan':'PRIVATE_PLAN'}}
        r = self.conclude()
        self.assertEqual(self.inputs(), []); self.assertIsNone(r['position_assessment'])
        self.assertFalse(r['exposure']['established']); self.assertEqual(r['submission'], {})

    def test_only_used_final_originals_enter_comparison_not_entire_holdings(self):
        self.establish(); self.f.acquire(['c5'],self.investigator); self.defense()
        def remove(task,out,data):
            if task=='ensemble_theory' and data.get('review_mode')!='concealment':
                out['argument_sources'].remove('c2')
        r=self.conclude(remove);d=self.inputs()[-1]
        self.assertNotIn('c2',{s['id'] for s in d['final_evidence']})
        self.assertNotIn('c5',{s['id'] for s in d['final_evidence']})
        self.assertEqual(self.s['known'][self.killer], {})
        self.assertFalse(r['exposure']['established'])

    def test_cited_heard_statement_remains_attributed_and_cannot_be_sole_proof(self):
        event=w.speak(self.s,self.investigator,'我声称见过交接记录。')
        sid=next(o['id'] for o in self.s['observations'][self.killer] if o['event_id']==event['id'])
        self.defense(); self.s['submissions'][self.killer]['testimony_ids']=[sid]
        def assess(task,out,data):
            if data.get('review_mode')=='concealment':
                self.assertEqual(data['cited_testimony'][0]['provenance'],'heard_claim')
                out['evidence_checks']=[{'statement':'我没有实施伤害','status':'unresolved',
                    'reason':'发言尚不能独立证实这项说法。','source_ids':[sid]}]
        r=self.conclude(assess); self.assertEqual(r['position_assessment']['evidence_checks'][0]['status'],'unresolved')

    def test_explicit_admission_preserves_full_proof_requirements(self):
        self.f.acquire(IDS,self.killer); self.f.submit(IDS,self.killer)
        r=self.conclude();self.assertEqual(r['assessment_type'],'admission')
        self.assertEqual(r['result'],'established'); self.assertEqual(len(self.inputs()),1)
        self.assertEqual(self.inputs()[0]['review_mode'],'admission')
        self.assertFalse(self.s['results']['participants'][self.killer]['primary'])
        self.assertTrue(r['exposure']['established_by'][0]['self_submission'])

    def test_admission_without_evidence_does_not_establish_case(self):
        self.f.submit([],self.killer,explanation='我承认自己实施了伤害。')
        r=self.conclude();self.assertEqual(r['result'],'unproven')
        self.assertFalse(self.s['results']['shared_success'])
        self.assertFalse(any(a['proof_covered'] for a in r['aspects'].values()))

    def test_ambiguous_text_does_not_replace_locked_suspect(self):
        self.defense(self.investigator,text='我承认自己说过假话，但最终仍指认对方。')
        r=self.conclude();self.assertEqual(r['assessment_type'],'position')
        self.assertEqual(r['suspect'],self.investigator);self.assertFalse(r['exposure']['established'])

    def test_unauthorized_sources_invented_quotes_and_model_scores_are_rejected(self):
        good={'position_summary':'保留立场。','evidence_checks':[{'statement':'我否认伤害',
            'status':'contradicted','reason':'与原始记录相冲突。','source_ids':['c1']}]}
        position.validate(good,'我否认伤害。',{'c1'},{'B-o000002'})
        for change in ('source','quote','testimony','winner','claims','status'):
            bad=deepcopy(good);check=bad['evidence_checks'][0]
            if change=='source':check['source_ids']=['private-unsubmitted']
            elif change=='quote':check['statement']='我承认伤害'
            elif change=='testimony':check['source_ids']=['B-o000002']
            elif change=='winner':bad['primary']=True
            elif change=='claims':bad['claims']=[]
            else:check['status']='established'
            with self.subTest(change=change),self.assertRaises(position.PositionReviewError) as caught:
                position.validate(bad,'我否认伤害。',{'c1'},{'B-o000002'})
            self.assertEqual(caught.exception.feedback['code'],'position_review_contract')

    def test_new_and_legacy_objective_results_agree_for_denial_and_admission(self):
        self.establish();self.defense(self.investigator);template=deepcopy(self.s)
        self.conclude();new={a:(p['primary'],p['personal'],p['success']) for a,p in self.s['results']['participants'].items()}
        self.s.clear();self.s.update(deepcopy(template));self.f.f.inputs.clear()
        old=self.conclude(version='ai-tasks-v94.json')
        self.assertEqual(new,{a:(p['primary'],p['personal'],p['success']) for a,p in self.s['results']['participants'].items()})
        self.assertEqual(old['review_version'],1);self.assertIn('aspects',old)
        self.assertTrue(all('review_mode' not in d for d in self.inputs()))

    def test_reviews_stay_hidden_before_ending_and_projection_does_not_mutate_saved_review(self):
        self.defense();self.conclude();saved=canonical(self.s)
        self.s['phase']='active';self.assertIsNone(w.view(self.s,self.killer)['results'])
        self.s['phase']='ended';v=w.view(self.s,self.killer)
        v['results']['participants'][self.killer]['reasoning']['position_assessment']['position_summary']='changed'
        self.assertEqual(canonical(self.s),saved)

    def test_private_variants_keep_generic_trace_task_and_published_prefixes(self):
        self.defense();self.conclude();data=self.inputs()[-1]
        body,_=self.app.gateway.payload('ensemble_theory',None,data,VERSION)
        self.assertIn('PALTER_TASK: ensemble_theory\n',body['messages'][0]['content'])
        self.assertIn('OUTWARD-POSITION REVIEW',body['messages'][0]['content'])
        self.assertNotIn('Return exactly three claims',body['messages'][0]['content'])
        root=Path('palter/prefixes');old=json.loads((root/'ai-tasks-v94.json').read_text());new=json.loads((root/VERSION).read_text())
        self.assertEqual([k for k in new if old[k]!=new[k]],['ensemble_theory'])
        for name,digest in json.loads((root/'manifest.json').read_text()).items():
            self.assertEqual(hashlib.sha256((root/name).read_bytes()).hexdigest(),digest)

    def test_failed_position_review_reuses_paid_investigator_after_restart(self):
        from palter.deepseek import DeepSeek,Settings
        from palter.ensemble import EnsembleApplication
        from palter.storage import StoreError
        self.establish();self.defense(self.investigator)
        self.app.gateway.current_version=VERSION;self.app.gateway.retry_delays=(0,0,0)
        self.s['watch']['budget_usd']=2
        owner=self.app.store.session()['id']
        saved=self.app.store.create_game(owner,{'command_id':'position_retry_create','expected_game_id':None},
            lambda gid:dict(deepcopy(self.s),id=gid))
        command={'command_id':'position_retry_operation','expected_revision':saved['revision'],'kind':'probe'}
        provider=self.f.f.provider;fail=True
        def transport(payload):
            response=provider(payload)
            data=json.loads(payload['messages'][-1]['content'])
            if fail and data.get('review_mode')=='concealment':
                out={'position_summary':'保留立场。','evidence_checks':[{'statement':'我从未提交的句子',
                     'status':'unresolved','reason':'待核对。','source_ids':[]}]}
                response['choices'][0]['message']['content']=canonical(out)
            return response
        self.app.gateway.client.transport=transport
        with self.assertRaises(StoreError) as error:self.app.operate(owner,saved['id'],command,self.app.conclude_ensemble)
        self.assertEqual(error.exception.code,'retry_exhausted')
        with self.app.store.transaction(False) as con:
            before=[dict(row) for row in con.execute('SELECT * FROM ai_calls ORDER BY started')]
        self.assertEqual([row['status'] for row in before],['completed']+['failed']*4)
        self.assertEqual(json.loads(before[-1]['validation_feedback'])['code'],'position_review_contract')
        fail=False
        app=EnsembleApplication(self.app.store.path,DeepSeek(Settings(api_key='fixture'),transport));app.gateway.retry_delays=(0,0,0)
        with app.store.transaction() as con:app.gateway.renew_retry(con,saved['id'],command['command_id'])
        state,_=app.operate(owner,saved['id'],command,app.conclude_ensemble)
        with app.store.transaction(False) as con:after=[dict(row) for row in con.execute('SELECT * FROM ai_calls ORDER BY started')]
        self.assertEqual(after[:5],before);self.assertEqual(len(after),7)
        self.assertEqual(after[-2]['prefix_hash'],before[-1]['prefix_hash'])
        self.assertEqual(state['phase'],'ended')
        self.assertEqual(state['results']['participants'][self.killer]['reasoning']['assessment_type'],'position')


if __name__=='__main__':unittest.main()
