"""Inspect actual role requests: outward conclusions follow private role goals."""
from copy import deepcopy
import json
import unittest

from palter import ensemble_world as w, memory_entries
from palter.storage import canonical
from tests import test_ensemble_review as fixture


class FinalPerspectiveTests(unittest.TestCase):
    def setUp(self):
        f=fixture.ReviewFixTests();f.setUp();self.addCleanup(f.doCleanups)
        self.f=f;self.app=f.app;self.state=f.state
        self.culprit=self.state['case']['solution']['killer']

    def request(self,actor,version='ai-tasks-v71.json'):
        self.f.inputs=[];self.f.provider.calls=[]
        if self.state['closure']['ready']:
            self.f.provider.policy=lambda data:'lock_conclusion'
        self.app.turn(deepcopy(self.state),actor,self.f.caller(version),0)
        payload=next(p for task,p,data in self.f.provider.calls if task=='ensemble_role')
        data=next(d for task,d in self.f.inputs if task=='ensemble_role')
        return payload,data

    def test_final_culprit_request_excludes_investigator_goal_and_closure_guidance(self):
        self.state['closure']['ready']=True
        payload,data=self.request(self.culprit)
        prompt=payload['messages'][0]['content']
        self.assertIn('FINAL SUBMISSION (CONCEALMENT)',prompt)
        self.assertIn('CLOSURE CHOICE (CONCEALMENT)',prompt)
        self.assertNotIn('Explain identity/opportunity, correct time bounds',prompt)
        self.assertNotIn('When I already have a grounded position',prompt)
        self.assertNotIn('PRIVATE BELIEF:',prompt)
        self.assertNotIn('belief',data);self.assertNotIn('dimensions',data['conclusion_task'])
        baseline=json.loads(payload['messages'][1]['content'].split('\n',1)[1])
        self.assertIn('crime',{r['id'] for r in baseline['experienced_facts']})
        self.assertNotIn('solution',data)
        example=json.loads(prompt.split('EXAMPLE JSON:\n')[1])
        self.assertIn('strategy_update',example);self.assertNotIn('belief_update',example)
        self.assertIn('PALTER_TASK: ensemble_role\n',prompt)

    def test_investigator_request_keeps_evidence_guidance_without_private_crime(self):
        self.state['closure']['ready']=True
        actor=next(a for a in w.ACTORS if a!=self.culprit)
        payload,data=self.request(actor);prompt=payload['messages'][0]['content']
        self.assertIn('For murder investigators',prompt)
        self.assertIn('Explain identity/opportunity, correct time bounds',prompt)
        self.assertNotIn('ROLE PURPOSE (CONCEALMENT)',prompt)
        self.assertNotIn('FINAL SUBMISSION (CONCEALMENT)',prompt)
        self.assertIn('belief',data);self.assertNotIn('strategy',data)
        baseline=json.loads(payload['messages'][1]['content'].split('\n',1)[1])
        self.assertNotIn('crime',{r['id'] for r in baseline['experienced_facts']})

    def test_same_memory_and_tool_boundaries_apply_to_both_perspectives(self):
        culprit,_=self.request(self.culprit)
        innocent,_=self.request(next(a for a in w.ACTORS if a!=self.culprit))
        for payload in (culprit,innocent):
            prompt=payload['messages'][0]['content']
            for kind in memory_entries.KINDS:self.assertIn('"'+kind+'"',prompt)
        for key in ('tools','max_tokens','temperature','model','response_format'):
            self.assertEqual(culprit[key],innocent[key])
        self.assertNotEqual(culprit['messages'][0],innocent['messages'][0])

    def test_outward_positions_are_preserved_without_forcing_or_filtering_suspect(self):
        self.state['closure']['ready']=True
        other=next(a for a in w.ACTORS if a!=self.culprit)
        for suspect,explanation in ((None,'我保留异议，目前不指认任何人。'),
                                    (other,'这是我选择提交的怀疑，尚有缺口。'),
                                    (self.culprit,'我主动决定承认自己的行为。')):
            with self.subTest(suspect=suspect):
                state=deepcopy(self.state);original=deepcopy(state['case'])
                final={'suspect':suspect,'explanation':explanation,'evidence_ids':[],'testimony_ids':[]}
                def choose(task,out,data):
                    if task=='ensemble_role':
                        out.update(action={'kind':'lock_conclusion','args':[]},speech='',
                                   final_conclusion=deepcopy(final),strategy_update=None)
                self.app.turn(state,self.culprit,self.f.caller('ai-tasks-v71.json',choose),0)
                self.assertEqual(state['submissions'][self.culprit],final)
                self.assertEqual(state['case'],original)
                self.assertIsNone(state['beliefs'][self.culprit])

    def test_pinned_v70_keeps_its_existing_prompt_and_new_variant_is_cache_stable(self):
        old,_=self.request(self.culprit,'ai-tasks-v70.json')
        self.assertIn('Explain identity/opportunity, correct time bounds',old['messages'][0]['content'])
        new,data=self.request(self.culprit)
        baseline=w.baseline(self.state,self.culprit);baseline['decision_mode']='concealment'
        first,h1=self.app.gateway.payload('ensemble_role',baseline,data,'ai-tasks-v71.json')
        changed=deepcopy(data);changed['strategy']={'situation':'新增质疑。','plan':'我先回应。','sources':['crime']}
        second,h2=self.app.gateway.payload('ensemble_role',baseline,changed,'ai-tasks-v71.json')
        self.assertEqual(h1,h2);self.assertEqual(first['messages'][:2],second['messages'][:2])
        self.assertNotEqual(canonical(first),canonical(second))


if __name__=='__main__':unittest.main()
