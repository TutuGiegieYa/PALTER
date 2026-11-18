"""Offline contract tests for the completed spectator-game findings."""
from copy import deepcopy
import json
from pathlib import Path
import tempfile
import unittest
from palter import ensemble_world as w, ensemble_context as context, spectator
from palter.ensemble import EnsembleApplication
from palter.deepseek import DeepSeek, Settings
from palter.scenario_cases import build
from palter.storage import StoreError, canonical
from tests.test_ensemble import EnsembleProvider, story_fixture


class ReviewFixTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.provider=EnsembleProvider()
        self.app=EnsembleApplication(Path(self.tmp.name)/'test.db',DeepSeek(Settings(api_key='fixture'),self.provider))
        # These direct response-mutation tests retain the published v62 contract.
        # v63 patches, lookup and isolation are covered by test_cost_optimization.
        self.app.gateway.current_version='ai-tasks-v62.json'
        self.state=w.blank('abcd'*6,'murder',0,'after');spectator.initialize(self.state)
        preview={'title':'测试','introduction':'核实原始记录。','cast':dict(zip(w.ACTORS,['甲','乙','丙','丁'])),'victim':'戊'}
        self.state['preview']=preview;self.state['closure']={'votes':[],'ready':False}
        w.initialize(self.state,build(story_fixture(),preview,'murder',3,[],rules_version=3));w.start(self.state)
        self.state['interaction_version']=2
        self.inputs=[]

    def caller(self,version='ai-tasks-v47.json',transform=None):
        def call(stage,task,baseline,data,validate,actor=None):
            self.inputs.append((task,deepcopy(data)))
            payload,_=self.app.gateway.payload(task,baseline,data,version)
            out=json.loads(self.provider(payload)['choices'][0]['message']['content'])
            if transform:transform(task,out,data)
            validate(out);return out,'explicit-provider-double'
        call.prefix_version=version
        return call

    def test_protected_and_copied_records_do_not_offer_repeat_noops(self):
        s=self.state;cid=next(c for c,o in s['objects'].items() if w.accessible(s,'A',c))
        s['objects'][cid]['protected']=False
        w.apply_choice(s,'A','protect:'+cid);count=len(s['events'])
        with self.assertRaises(StoreError):w.apply_choice(s,'A','protect:'+cid)
        self.assertEqual(len(s['events']),count)
        w.apply_choice(s,'A','copy:'+cid)
        with self.assertRaises(StoreError):w.apply_choice(s,'A','copy:'+cid)
        self.assertIn(cid,s['known']['A'])

    def test_periodic_speech_allows_silent_rotations_but_questions_are_immediate(self):
        s=self.state
        for a in 'BCD':w.speak(s,a,'交流进展')
        self.assertFalse(w.must_speak(s,'A'))
        for _ in range(2):
            for a in 'BCD':w.speak(s,a,'继续讨论')
        self.assertTrue(w.must_speak(s,'A'))
        w.speak(s,'A','我说明已经看到的情况。');self.assertFalse(w.must_speak(s,'A'))
        w.speak(s,'B','请解释这件事。','A',challenge=True)
        self.assertTrue(w.must_speak(s,'A'));self.assertTrue(s['obligations']['A']['response'])

    def test_relationship_bounds_and_original_self_claim_recall_do_not_rewrite_storage(self):
        s=self.state;e=w.speak(s,'A','我已经把材料封存了。')
        source=next(o['id'] for o in s['observations']['A'] if o['event_id']==e['id'])
        s['memory']['A'].update(summary='我声称材料已封存，尚无完成记录。',sources=[source])
        for _ in range(40):w.note(s,'A',w.emit(s,'observed'),'新的现场观察')
        for r in s['relationships']['A'].values():
            r['experiences']=[{'reason':'仍待核对的说法。'*30,'sources':[source],'call_id':str(i)} for i in range(500)]
        before=canonical(s);data=context.project(s,'A',w.context(s,'A'))
        self.assertEqual(canonical(s),before)
        self.assertEqual(data['recalled_sources'][0]['provenance'],'self_claim')
        for r in data['relationships'].values():
            self.assertLessEqual(len(r['experiences']),3);self.assertEqual(r['experience_count'],500)
        self.assertLess(len(canonical(data['relationships']).encode()),8500)
        self.app.gateway.payload('ensemble_role',w.baseline(s,'A'),data)

    def test_unheard_private_claim_is_never_recalled_or_accepted_as_final_source(self):
        s=self.state;w.apply_choice(s,'C','invite:D');w.apply_choice(s,'D','accept:i1')
        e=w.speak(s,'C','PRIVATE_HEARD_CANARY');sid=next(o['id'] for o in s['observations']['C'] if o['event_id']==e['id'])
        data=context.project(s,'A',w.context(s,'A'));self.assertNotIn('PRIVATE_HEARD_CANARY',canonical(data))
        def invalid(task,out,data):
            if task=='ensemble_role':out['testimony_ids']=[sid]
        with self.assertRaises(ValueError):self.app.turn(s,'A',self.caller(transform=invalid),0)
        with self.assertRaises(StoreError):self.app.play(s,'A',{'kind':'submit','suspect':'B','text':'我的推理','testimony_ids':[sid]},self.caller())

    def test_recombining_sources_cannot_reset_stagnation(self):
        s=self.state;s['beliefs']['A']={'suspect':'B','explanation':'我据材料推断。','evidence_ids':['c1','c2']}
        s['grounded_progress']={'A':{'kind':'deduction','sources':['c1','c2']}}
        seen=spectator.progress_keys(s)
        for ids in (['c1'],['c2'],['c2','c1']):
            s['beliefs']['A']['evidence_ids']=ids;s['grounded_progress']['A']={'kind':'answer','sources':ids}
            self.assertFalse(spectator.progress_keys(s)-seen)

    def test_final_argument_cites_heard_claim_separately_without_supplying_missing_records(self):
        s=self.state;e=w.speak(s,'B','我愿意解释之前的保管情况。')
        sid=next(o['id'] for o in s['observations']['A'] if o['event_id']==e['id'])
        for clue in s['case']['clues']:w.acquire(s,'A',clue['id'],e,'测试取得')
        s['submissions']['A']={'suspect':s['case']['solution']['killer'],'explanation':'我根据证言和材料判断。','evidence_ids':[],'testimony_ids':[sid]}
        self.app.conclude_ensemble(s,self.caller())
        data=next(d for t,d in self.inputs if t in ('case_theory','ensemble_theory'))
        self.assertEqual(data['cited_evidence'],[]);self.assertEqual(data['cited_testimony'][0]['id'],sid)
        self.assertEqual(data['cited_testimony'][0]['provenance'],'heard_claim')
        self.assertEqual(s['results']['participants']['A']['reasoning']['established'],[])
        self.assertFalse(s['results']['shared_success'])

    def test_role_submission_retains_chosen_sources_and_does_not_get_hidden_solution(self):
        s=self.state;s['closure']['ready']=True
        e=w.speak(s,'B','我愿意核对。');sid=next(o['id'] for o in s['observations']['A'] if o['event_id']==e['id'])
        w.acquire(s,'A','c1',e,'测试取得')
        def final(task,out,data):
            if task=='ensemble_role':out.update(choice='lock_conclusion',suspect='B',reasoning='我只知道下界，仍缺上界。',evidence_ids=['c1'],testimony_ids=[sid],final_conclusion={'suspect':None,'explanation':'我还缺上界，暂不作明确指认。','evidence_ids':['c1'],'testimony_ids':[sid]})
        self.app.turn(s,'A',self.caller(transform=final),0)
        self.assertEqual(s['beliefs']['A']['suspect'],'B');self.assertIsNone(s['submissions']['A']['suspect'])
        self.assertEqual(s['submissions']['A']['testimony_ids'],[sid]);self.assertEqual(s['submissions']['A']['evidence_ids'],['c1'])
        data=next(d for t,d in self.inputs if t=='ensemble_role')
        self.assertTrue(data['conclusion_task']['final']);self.assertNotIn('solution',data);self.assertNotIn('proof_routes',data)

    def test_old_pinned_turn_preserves_old_context_and_action_options(self):
        s=self.state;s.pop('interaction_version');cid=next(c for c,o in s['objects'].items() if w.accessible(s,'A',c))
        s['objects'][cid]['protected']=True
        self.provider.policy=lambda d:'protect:'+cid
        self.app.turn(s,'A',self.caller('ai-tasks-v42.json'),0)
        data=next(d for t,d in self.inputs if t=='ensemble_role')
        self.assertNotIn('recalled_sources',data);self.assertNotIn('conclusion_task',data)
        self.assertNotIn('interaction_version',s)

    def test_whole_argument_sources_keep_cross_paragraph_support_without_lowering_guards(self):
        for unsupported in (False,True):
            s=deepcopy(self.state);a='A';e=w.emit(s,'inspect',a)
            ids=list(dict.fromkeys(cid for routes in s['case']['proofs'].values() for cid in routes[0]))
            for cid in ids:w.acquire(s,a,cid,e,'fixture')
            s['submissions'][a]={'suspect':s['case']['solution']['killer'],'explanation':'我的时间、手法与人物论证。','evidence_ids':ids}
            def assess(task,out,data):
                if task in ('case_theory','ensemble_theory'):
                    out['argument_sources']=ids
                    for claim in out['claims']:
                        claim['evidence_ids']=['c1']
                        if unsupported and claim['aspect']=='method':claim['supported']=False
            self.app.conclude_ensemble(s,self.caller(transform=assess))
            self.assertEqual(s['results']['shared_success'],not unsupported)
        s=deepcopy(self.state);w.acquire(s,'A','c1',w.emit(s,'inspect','A'),'fixture')
        s['submissions']['A']={'suspect':'B','explanation':'引用范围必须守住。','evidence_ids':['c1']}
        def invalid(task,out,data):
            if task in ('case_theory','ensemble_theory'):out['argument_sources']=['c2']
        with self.assertRaises(ValueError):self.app.conclude_ensemble(s,self.caller(transform=invalid))

    def test_pending_observations_are_not_lost_when_recent_window_shrinks(self):
        s=self.state
        for _ in range(20):w.note(s,'A',w.emit(s,'observed'),'尚未整理的新观察')
        data=context.project(s,'A',w.context(s,'A'),concise=True,receipts=True)
        self.assertEqual([o['id'] for o in data['observations']],[o['id'] for o in s['observations']['A']])
        self.assertEqual(data['own_action_record']['count'],0)
        e=w.speak(s,'B','一条发言');cue=w.emit(s,'cue','B',source=e['id']);w.note(s,'A',cue,'停了一下。','cue')
        data=context.project(s,'A',w.context(s,'A'),concise=True,receipts=True)
        self.assertEqual(data['heard_statement_ids'],[o['id'] for o in s['observations']['A'] if o['kind']=='testimony'])
        self.assertNotIn(s['observations']['A'][-1]['id'],data['heard_statement_ids'])


if __name__=='__main__':unittest.main()
