"""Role specialization uses authorized self-knowledge, never the observer's truth."""
from copy import deepcopy
import json
import unittest
from palter import ensemble_world as w, spectator
from palter.scenario_cases import build
from palter.storage import canonical
from tests import test_ensemble_review as fixture
from tests.test_ensemble import story_fixture


class CulpritPerspectiveTests(unittest.TestCase):
    def setUp(self):
        fixture.ReviewFixTests.setUp(self)
        self.culprit=self.state['case']['solution']['killer']

    def caller(self,version=None,transform=None):
        return fixture.ReviewFixTests.caller(self,version or self.app.gateway.current_version,transform)

    def test_perspective_depends_only_on_own_fixed_knowledge_and_objective(self):
        s=self.state;a=self.culprit
        self.assertEqual(w.perspective(s,a),'concealment')
        innocent=next(b for b in w.ACTORS if b!=a)
        s['case']['solution']['killer']=innocent
        self.assertEqual(w.perspective(s,a),'concealment')
        self.assertEqual(w.perspective(s,innocent),'investigation')
        s['case']['roles'][a]['knows'].remove('crime')
        self.assertEqual(w.perspective(s,a),'investigation')

    def test_culprit_receives_strategy_contract_without_detective_belief_or_closure_checklist(self):
        s=self.state;a=self.culprit
        s['beliefs'][a]={'suspect':a,'explanation':'STALE_SELF_DEDUCTION','evidence_ids':[]}
        self.app.turn(s,a,self.caller(),0)
        data=next(d for t,d in self.inputs if t=='ensemble_role')
        self.assertEqual(data['decision_mode'],'concealment');self.assertNotIn('belief',data)
        self.assertNotIn('STALE_SELF_DEDUCTION',canonical(data));self.assertNotIn('dimensions',data['conclusion_task'])
        _,payload,_=next(c for c in self.provider.calls if c[0]=='ensemble_role')
        prompt=payload['messages'][0]['content']
        self.assertIn('PALTER_TASK: ensemble_role\n',prompt)
        self.assertNotIn('DEDUCTION: For murder',prompt)
        example=json.loads(prompt.split('EXAMPLE JSON:\n')[1])
        self.assertNotIn('suspect',example);self.assertNotIn('reasoning',example);self.assertNotIn('evidence_ids',example)
        self.assertIn('situation',example);self.assertIn('strategy',example)
        self.assertIsNone(s['beliefs'][a]);self.assertIn(a,s['strategies'])
        self.assertEqual(s['case']['roles'][a]['knows'],self.state['case']['roles'][a]['knows'])

    def test_private_strategy_persists_but_other_roles_and_regular_views_do_not_receive_it(self):
        s=self.state;a=self.culprit;b=next(x for x in w.ACTORS if x!=a)
        def planned(task,out,data):
            if task=='ensemble_role':out.update(situation='PRIVATE_STRATEGY_CANARY',strategy='我先回应眼前的质疑。',assessment_sources=['crime'])
        self.app.turn(s,a,self.caller(transform=planned),0)
        self.assertNotIn('PRIVATE_STRATEGY_CANARY',canonical(w.context(s,b)))
        self.assertNotIn('PRIVATE_STRATEGY_CANARY',canonical(w.baseline(s,b)))
        self.assertNotIn('PRIVATE_STRATEGY_CANARY',canonical(w.view(s,b)))
        self.assertEqual(spectator.view(s)['roles'][a]['strategy']['situation'],'PRIVATE_STRATEGY_CANARY')
        self.inputs=[];self.app.turn(s,a,self.caller(),0)
        data=next(d for t,d in self.inputs if t=='ensemble_role')
        self.assertEqual(data['strategy']['situation'],'PRIVATE_STRATEGY_CANARY')

    def test_strategy_cannot_cite_an_unheard_private_source(self):
        s=self.state;a=self.culprit;others=[b for b in w.ACTORS if b!=a]
        w.apply_choice(s,others[0],'invite:'+others[1]);w.apply_choice(s,others[1],'accept:i1')
        event=w.speak(s,others[0],'UNHEARD_PRIVATE_STRATEGY_CANARY',others[1])
        source=next(o['id'] for o in s['observations'][others[0]] if o['event_id']==event['id'])
        def invalid(task,out,data):
            if task=='ensemble_role':out['assessment_sources']=[source]
        with self.assertRaises(ValueError):self.app.turn(s,a,self.caller(transform=invalid),0)
        data=next(d for t,d in self.inputs if t=='ensemble_role')
        self.assertNotIn('UNHEARD_PRIVATE_STRATEGY_CANARY',canonical(data))

    def test_final_position_is_independent_and_admission_is_not_filtered_by_code(self):
        s=self.state;a=self.culprit;s['closure']['ready']=True
        def final(task,out,data):
            if task=='ensemble_role':
                out.update(choice='lock_conclusion',situation='我知道自己做过什么，当前收到的证据仍有争议。',strategy='我选择保留异议。',assessment_sources=['crime'],
                    final_conclusion={'suspect':None,'explanation':'我认为现有材料不足以完成指认。','evidence_ids':[],'testimony_ids':[]})
        self.app.turn(s,a,self.caller(transform=final),0)
        data=next(d for t,d in self.inputs if t=='ensemble_role')
        self.assertEqual([c['id'] for c in data['choices']],['lock_conclusion'])
        self.assertEqual(data['focus']['currently_accessible_unread_records'],[])
        self.assertIsNone(s['submissions'][a]['suspect']);self.assertIsNone(s['beliefs'][a])
        self.assertIn('crime',s['case']['roles'][a]['knows'])
        s=deepcopy(self.state);s['submissions']={};s['closure']['ready']=False
        def admission(task,out,data):
            if task=='ensemble_role':out['speech']='我选择告诉你们：是我做的。'
        self.app.turn(s,a,self.caller(transform=admission),0)
        self.assertEqual([e for e in s['events'] if e['kind']=='testimony'][-1]['facts']['text'],'我选择告诉你们：是我做的。')

    def test_pinned_v47_retains_original_detective_contract_and_default_variant(self):
        s=self.state;a=self.culprit
        self.app.turn(s,a,self.caller('ai-tasks-v47.json'),0)
        data=next(d for t,d in self.inputs if t=='ensemble_role')
        self.assertNotIn('decision_mode',data);self.assertIn('belief',data)
        self.assertNotIn('strategies',s);self.assertIsNotNone(s['beliefs'][a])
        prompt=next(p['messages'][0]['content'] for t,p,d in self.provider.calls if t=='ensemble_role')
        self.assertIn('DEDUCTION: For murder',prompt)

    def test_unsubmitted_historical_self_belief_is_not_graded_as_an_accusation(self):
        s=self.state;a=self.culprit
        s['beliefs'][a]={'suspect':a,'explanation':'旧版私下自我指认。','evidence_ids':[]}
        self.app.conclude_ensemble(s,self.caller())
        self.assertFalse(any(t=='ensemble_theory' for t,d in self.inputs))
        self.assertEqual(s['results']['participants'][a]['reasoning']['result'],'unresolved')

    def test_final_phase_rejects_further_investigation_but_old_pinned_choices_remain(self):
        s=self.state;s['closure']['ready']=True
        def wait(task,out,data):
            if task=='ensemble_role':out['choice']='wait'
        with self.assertRaises(ValueError):self.app.turn(deepcopy(s),self.culprit,self.caller(transform=wait),0)
        self.inputs=[];self.app.turn(deepcopy(s),self.culprit,self.caller('ai-tasks-v48.json',transform=wait),0)
        data=next(d for t,d in self.inputs if t=='ensemble_role')
        self.assertIn('wait',[c['id'] for c in data['choices']])

    def test_innocent_and_non_murder_roles_keep_their_original_decision_fields(self):
        s=self.state;a=next(a for a in w.ACTORS if a!=self.culprit)
        self.app.turn(s,a,self.caller(),0)
        data=next(d for t,d in self.inputs if t=='ensemble_role')
        self.assertEqual(data['decision_mode'],'investigation');self.assertIn('belief',data)
        self.assertIsNotNone(s['beliefs'][a]);self.assertNotIn(a,s.get('strategies',{}))
        other=w.blank('abcd'*6,'rescue',0,'after');other['preview']=s['preview'];other['closure']={'ready':False,'votes':[]}
        w.initialize(other,build(story_fixture(),other['preview'],'rescue',3,[],rules_version=3));w.start(other)
        self.inputs=[];self.app.turn(other,'A',self.caller(),0)
        self.assertEqual(next(d for t,d in self.inputs if t=='ensemble_role')['decision_mode'],'objectives')


if __name__=='__main__':unittest.main()
