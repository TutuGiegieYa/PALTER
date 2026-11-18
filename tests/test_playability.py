"""Causal, reasoning and recovery regressions from the complete playthrough."""
from copy import deepcopy
from concurrent.futures import ThreadPoolExecutor
import unittest
from palter import ensemble_world as w
from palter.scenario_cases import build
from palter.storage import StoreError,canonical
import tests.test_ensemble as fixtures
from tests.test_ensemble import story_fixture


class PlayabilityTests(unittest.TestCase):
    setUp=fixtures.EnsembleTests.setUp
    create=fixtures.EnsembleTests.create
    cmd=fixtures.EnsembleTests.cmd
    state=fixtures.EnsembleTests.state
    change=fixtures.EnsembleTests.change

    def test_new_causal_structures_and_legacy_compilation_are_distinct(self):
        preview={'cast':dict(zip('ABCD',('甲','乙','丙','丁'))),'victim':'戊'}
        structures={}
        for seed in range(30):
            case=build(story_fixture(),preview,'murder',seed,['A'])
            old=build(story_fixture(),preview,'murder',seed,['A'],rules_version=1)
            self.assertNotIn('rules_version',old);self.assertEqual(case['rules_version'],3)
            records={c['id']:c for c in case['clues']}
            self.assertEqual(case['solution']['killer'],old['solution']['killer'])
            self.assertEqual(len(case['proofs']['identity']),2)
            for routes in case['proofs'].values():
                for route in routes:self.assertLessEqual(set(route),set(records))
            structures[case['family']]=case['proofs']
            if case['family']!='clock':
                self.assertNotIn('独自进入',records['c10']['observation'])
                self.assertIn('c14',records);witness=records['c14']['private_owner']
                self.assertNotEqual(witness,case['solution']['killer'])
                self.assertIn('handover',case['roles'][witness]['knows'])
                self.assertIn('s'+witness,records['c14']['reveals'])
                self.assertNotIn('c14',set(case['proofs']['identity'][0]))
                self.assertIn('c14',set(case['proofs']['identity'][1]))
        self.assertEqual(len({canonical(v) for v in structures.values()}),3)

    def test_scoped_focus_contains_owed_question_not_private_conversation(self):
        s=self.create();w.apply_choice(s,'C','invite:D');w.apply_choice(s,'D','accept:i1')
        w.speak(s,'C','OUTSIDE_FOCUS_SECRET',target='D')
        w.speak(s,'A','请解释刚才的时间矛盾。',target='B',challenge=True)
        focus=w.decision_focus(s,'B','收到质证')
        self.assertIn('时间矛盾',canonical(focus));self.assertNotIn('OUTSIDE_FOCUS_SECRET',canonical(focus))
        self.assertNotIn('C_PRIVATE_SECRET_CANARY',canonical(focus))

    def test_role_invitation_has_one_spoken_contribution(self):
        self.create(humans=1);self.provider.policy=lambda d:'invite:C'
        before=self.state();self.app.pump(self.gid,True);s=self.state()
        self.assertIsNone(s['background_error'])
        self.assertEqual(s['silent']['A'],before['silent']['A']+1)
        events=s['events'][len(before['events']):]
        self.assertEqual(sum(e['kind']=='testimony' for e in events),1)
        self.assertEqual(len(s['invitations']),1);self.assertTrue(s['obligations']['C']['response'])

    def test_private_reasoning_is_not_forced_into_speech(self):
        s=self.create(humans=1);actor=next(a for a in w.ai_roles(s) if w.perspective(s,a)=='investigation')
        def call(stage,task,baseline,data,validate,actor=None):
            out={'choice':'wait','speech':'我先保留判断。','gesture':None,'question_to':None,
                 'memory':'自己的判断','memory_sources':[],'relationships':[],
                 'suspect':'C','evidence_ids':[],'reasoning':'PRIVATE_REASONING_CANARY，仍需核对时间。','next_decision':{'mode':'wait','events':[]}}
            validate(out);return out,'test-call'
        call.prefix_version='ai-tasks-v62.json'
        self.app.turn(s,actor,call,0,'回应')
        self.assertIn('PRIVATE_REASONING_CANARY',s['beliefs'][actor]['explanation'])
        self.assertNotIn('PRIVATE_REASONING_CANARY',canonical(w.view(s,'A')))

    def close_with_split_claims(self,version=None,missing=None):
        s=self.create(humans=1);s['case']=build(story_fixture(),s['preview'],'murder',0,['A'])
        # An oracle fixture is appropriate here: this checks grading, not playability.
        for c in s['case']['clues']:w.acquire(s,'A',c['id'],{'id':'fixture'},'fixture')
        s['submissions']['A']={'suspect':s['case']['solution']['killer'],'explanation':'时间说明。机会说明。手法说明。','evidence_ids':list(s['known']['A'])}
        claims=[{'aspect':a,'quote':quote,'supported':True,'evidence_ids':ids} for a,quote,ids in
                [('time','时间说明。',['c1','c2']),('identity','机会说明。',['c8','c9','c10']),('method','手法说明。',['c7'])] if a!=missing]
        def call(stage,task,baseline,data,validate,actor=None):
            out={'claims':claims,'argument_sources':list(dict.fromkeys(cid for c in claims for cid in c['evidence_ids']))} if task in ('case_theory','ensemble_theory') else {'title':'结束','narrative':'结果依据实际证据。'}
            if data.get('review_version'):
                out['claims']=[dict(c,reason='合成论证中已说明该关联。') for c in claims]
                if missing:out['claims'].append({'aspect':missing,'supported':False,'evidence_ids':[],'reason':'未论述这一部分。'})
            validate(out);return out,'fixture'
        if version:call.prefix_version=version
        self.app.conclude_ensemble(s,call);return s

    def test_connected_reasoning_accepts_evidence_explained_in_separate_paragraphs(self):
        s=self.close_with_split_claims();self.assertEqual(s['results']['participants']['A']['reasoning']['result'],'established')

    def test_connected_reasoning_still_requires_each_explained_aspect(self):
        s=self.close_with_split_claims(missing='time')
        self.assertEqual(s['results']['participants']['A']['reasoning']['result'],'unproven')

    def test_pinned_old_grading_preserves_recovery_payloads(self):
        s=self.close_with_split_claims(version='ai-tasks-v29.json')
        self.assertEqual(s['results']['participants']['A']['reasoning']['established'],['time','method'])

    def test_ending_receives_public_words_not_private_chat_or_individual_scores(self):
        s=self.create();w.apply_choice(s,'C','invite:D');w.apply_choice(s,'D','accept:i1')
        w.speak(s,'C','PRIVATE_ENDING_CANARY',target='D')
        w.speak(s,'A','PUBLIC_ENDING_CANARY',target='B');captured={}
        def call(stage,task,baseline,data,validate,actor=None):
            self.assertEqual(task,'ensemble_ending');captured.update(data)
            out={'title':'结束','narrative':'按实际发生的事收束。'};validate(out);return out,'fixture'
        self.app.conclude_ensemble(s,call)
        self.assertIn('PUBLIC_ENDING_CANARY',canonical(captured['public_dialogue']))
        self.assertNotIn('PRIVATE_ENDING_CANARY',canonical(captured))
        self.assertNotIn('results',captured);self.assertFalse(captured['closure']['truth_established'])

    def test_repeating_public_evidence_does_not_farm_contribution_credit(self):
        s=self.create(humans=1);w.apply_choice(s,'B','inspect:c1')
        w.apply_choice(s,'B','share:c1');w.apply_choice(s,'A','share:c1')
        self.assertIn('c1',s['contributions']['B']);self.assertNotIn('c1',s['contributions']['A'])
        w.publish_contribution(s,'C','c1');self.assertNotIn('c1',s['contributions']['C'])
        s['contributions']['A']=list(s['case']['proofs']['identity'][0])
        evaluations={'B':{'result':'established'}}
        self.assertFalse(w.results(s,evaluations)['participants']['A']['primary'])
        evaluations['A']={'result':'unproven','established':['time'],'suspect':s['case']['solution']['killer']}
        self.assertTrue(w.results(s,evaluations)['participants']['A']['primary'])

    def test_copy_of_the_same_fact_cannot_earn_a_second_key_credit(self):
        s=self.create(humans=1)
        s['case']=build(story_fixture(),s['preview'],'murder',2,['A'])
        w.publish_contribution(s,'A','c9');w.publish_contribution(s,'A','c14')
        w.publish_contribution(s,'B','c14')
        self.assertEqual(s['contributions']['A'],['c9']);self.assertEqual(s['contributions']['B'],[])

    def test_cancel_human_failure_preserves_ai_agenda_and_is_idempotent(self):
        self.create(humans=1);self.provider.fail='ensemble_action'
        with self.assertRaises(StoreError):self.cmd('A','intent',text='检查现场')
        before=self.state();agenda=deepcopy(before['agenda'])
        operation=self.app.gateway.trace(self.owners['A'],self.gid)['operation_id']
        self.cmd('A','cancel_pending',operation_id=operation);first=self.state()
        self.assertEqual(first['agenda'],agenda)
        self.cmd('A','cancel_pending',operation_id=operation)
        self.assertEqual(self.state()['revision'],first['revision']);self.assertEqual(self.state()['agenda'],agenda)
        with self.assertRaises(StoreError):self.cmd('A','cancel_pending',operation_id='nonexistent')

    def test_cancel_inflight_background_does_not_restore_error_or_drop_next_turn(self):
        self.create(humans=1);before=self.state();self.provider.block='ensemble_role'
        try:
            with ThreadPoolExecutor(1) as pool:
                work=pool.submit(self.app.pump,self.gid,True);self.assertTrue(self.provider.entered.wait(2))
                operation=self.app.gateway.trace(self.owners['A'],self.gid)['operation_id']
                self.cmd('A','cancel_pending',operation_id=operation)
                self.provider.release.set();work.result(5)
        finally:self.provider.release.set()
        s=self.state();self.assertIsNone(s['background_error'])
        self.assertEqual(s['agenda'],before['agenda'][1:]);self.assertEqual(s['events'],before['events'])
        self.cmd('A','cancel_pending',operation_id=operation);self.assertEqual(self.state()['agenda'],s['agenda'])

    def test_retry_exhaustion_is_visible_before_another_click(self):
        self.create(humans=1);self.provider.fail='ensemble_role';self.app.pump(self.gid,True)
        self.assertTrue(self.app.view(self.owners['A'],self.state())['background_error']['retryable'])
        with self.assertRaises(StoreError):self.app.retry_background(self.owners['A'],self.gid)
        self.assertTrue(self.app.view(self.owners['A'],self.state())['background_error']['retryable'])
        self.assertEqual(sum(t=='ensemble_role' for t,_,_ in self.provider.calls),8)


if __name__=='__main__':unittest.main()
