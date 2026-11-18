"""A final confession cannot alter another player's assessment or objective result."""
from copy import deepcopy
import json
from pathlib import Path
import unittest

from palter import ensemble_world as w
from palter.storage import canonical
from tests import test_position_review as fixtures
from tests.test_position_review_markup import render

VERSION='ai-tasks-v97.json'


class AdmissionIsolationTests(unittest.TestCase):
    def setUp(self):
        self.f=fixtures.PositionReviewTests();self.f.setUp();self.addCleanup(self.f.doCleanups)
        self.s=self.f.s;self.app=self.f.app;self.killer=self.f.killer;self.actor=self.f.investigator
        self.others=[a for a in w.ACTORS if a!=self.killer]

    def conclusions(self, own='unproven', peer=False):
        assessments={a:{'result':'unresolved','established':[],'suspect':None} for a in w.ACTORS}
        assessments[self.actor]={'result':own,'established':['time'] if own=='unproven' else list(('identity','time','method')) if own=='established' else [],
            'suspect':self.killer if own in ('unproven','established') else None}
        if peer:assessments[next(a for a in self.others if a!=self.actor)]={'result':'established','established':['identity','time','method'],'suspect':self.killer}
        return assessments

    def test_all_investigator_results_are_invariant_under_culprit_final_result(self):
        # Cover correct/incorrect/missing/incomplete submissions, cooperation and
        # both old and current cooperation requirements, without changing history.
        for rules in (1,5):
            self.s['case']['rules_version']=rules
            for own in ('unresolved','incorrect','unproven','established'):
                for peer in (False,True):
                    for contribution in (False,True):
                        self.s['contributions'][self.actor]=self.s['case']['proofs']['identity'][0][:2] if contribution else []
                        evaluations=self.conclusions(own,peer)
                        expected=None
                        for culprit_result in ('position_recorded','unproven','established'):
                            evaluations[self.killer]={'result':culprit_result,'established':[], 'suspect':self.killer}
                            result=w.results(self.s,evaluations,isolate_admission=True)
                            participants={a:result['participants'][a] for a in self.others}
                            if expected is None:expected=deepcopy(participants)
                            with self.subTest(rules=rules,own=own,peer=peer,contribution=contribution,culprit_result=culprit_result):
                                self.assertEqual(participants,expected)

    def test_confession_no_longer_unlocks_cooperation_victory(self):
        self.s['contributions'][self.actor]=self.s['case']['proofs']['identity'][0][:2]
        evaluations=self.conclusions();evaluations[self.killer]={'result':'established','established':['identity','time','method'],'suspect':self.killer}
        old=w.results(self.s,evaluations);new=w.results(self.s,evaluations,isolate_admission=True)
        self.assertTrue(old['participants'][self.actor]['primary'])
        self.assertFalse(new['participants'][self.actor]['primary'])
        self.assertTrue(new['shared_success']);self.assertTrue(new['admission_established'])
        self.assertFalse(new['investigation_success']);self.assertNotIn('scoring_version',old)

    def test_cooperation_from_another_investigator_still_counts(self):
        self.s['contributions'][self.actor]=self.s['case']['proofs']['identity'][0][:2]
        result=w.results(self.s,self.conclusions(peer=True),isolate_admission=True)
        self.assertTrue(result['investigation_success']);self.assertTrue(result['participants'][self.actor]['primary'])
        self.assertFalse(result['admission_established'])

    def test_confession_changes_culprit_avoidance_but_not_other_objectives(self):
        w.contribute(self.s,self.killer,'actual-participation');evaluations=self.conclusions()
        before=w.results(self.s,evaluations,isolate_admission=True)
        evaluations[self.killer]={'result':'established','established':['identity','time','method'],'suspect':self.killer}
        after=w.results(self.s,evaluations,isolate_admission=True)
        self.assertTrue(before['participants'][self.killer]['primary']);self.assertFalse(after['participants'][self.killer]['primary'])
        self.assertEqual(before['participants'][self.killer]['personal'],after['participants'][self.killer]['personal'])

    def prepare_partial(self):
        self.f.establish();self.f.f.acquire(fixtures.IDS,self.killer)
        for cid in ('c1','c2'):w.contribute(self.s,self.actor,cid)
        w.contribute(self.s,self.killer,'actual-participation')
        return deepcopy(self.s)

    def partial_review(self,task,out,data):
        if task=='ensemble_theory' and not data.get('review_mode'):
            next(c for c in out['claims'] if c['aspect']=='time').update(supported=False,reason='提交中的时间论述不完整。')

    def run_variant(self,base,kind,version=VERSION):
        self.s.clear();self.s.update(deepcopy(base));self.f.f.f.inputs.clear()
        if kind=='denial':self.f.f.submit([],self.killer,suspect=None,explanation='我否认参与，保留立场。')
        else:self.f.f.submit(fixtures.IDS if kind=='supported' else [],self.killer,explanation='我承认自己实施了伤害，并说明时间、人物与手法。')
        self.f.conclude(self.partial_review,version=version)
        return deepcopy(self.s['results'])

    def test_full_flow_freezes_investigator_review_process_and_outcomes(self):
        base=self.prepare_partial();variants={k:self.run_variant(base,k) for k in ('denial','unsupported','supported')}
        for actor in self.others:
            self.assertEqual(variants['denial']['participants'][actor],variants['supported']['participants'][actor])
            self.assertEqual(variants['denial']['participants'][actor],variants['unsupported']['participants'][actor])
        self.assertFalse(variants['supported']['participants'][self.actor]['primary'])
        self.assertFalse(variants['supported']['participants'][self.actor]['reasoning']['process']['truth_established'])
        self.assertTrue(variants['supported']['shared_success'])
        self.assertFalse(variants['unsupported']['shared_success'])

    def test_pinned_v96_keeps_its_historical_scoring_and_metadata(self):
        base=self.prepare_partial();result=self.run_variant(base,'supported',version='ai-tasks-v96.json')
        self.assertTrue(result['participants'][self.actor]['primary'])
        self.assertNotIn('scoring_version',result);self.assertNotIn('investigation_success',result)
        self.assertTrue(result['participants'][self.actor]['reasoning']['process']['truth_established'])

    def test_model_requests_are_identical_and_investigators_never_receive_final_confession(self):
        base=self.prepare_partial();payloads=[]
        for kind in ('denial','supported'):
            self.run_variant(base,kind);inputs=self.f.f.f.inputs
            investigator=[]
            for task,data in inputs:
                if task not in ('ensemble_theory','ensemble_ending'):continue
                old,_=self.app.gateway.payload(task,None,data,'ai-tasks-v96.json')
                new,_=self.app.gateway.payload(task,None,data,VERSION)
                self.assertEqual(old,new)
                if task=='ensemble_theory' and not data.get('review_mode'):investigator.append(deepcopy(data))
            payloads.append(investigator)
        self.assertEqual(payloads[0],payloads[1])
        old=json.loads(Path('palter/prefixes/ai-tasks-v96.json').read_text())
        new=json.loads(Path('palter/prefixes/'+VERSION).read_text());new['ensemble_theory'].pop('admission_isolation')
        self.assertEqual(old,new)

    def test_header_separates_admission_from_player_success_without_changing_legacy(self):
        base=self.prepare_partial();result=self.run_variant(base,'supported');before=canonical(result)
        html=render(result)
        self.assertIn('凶手的供述已有证据支持；非凶手玩家的评测按各自提交独立保留',html)
        self.assertEqual(canonical(result),before)
        panel=html.split('id="ending-review-'+self.actor+'"',1)[1].split('<details class="ending-role-review"',1)[0]
        self.assertIn('主要目标未达成',panel);self.assertIn('指认正确，论证未完整成立',panel)
        old=self.run_variant(base,'supported',version='ai-tasks-v96.json')
        self.assertNotIn('非凶手玩家的评测按各自提交独立保留',render(old))

    def test_other_scenarios_keep_existing_scoring_contract(self):
        for scenario in ('theft','family','council','rescue','house','archive'):
            self.s['scenario']=scenario
            self.assertEqual(w.results(self.s,{}),w.results(self.s,{},isolate_admission=True))


if __name__=='__main__':unittest.main()
