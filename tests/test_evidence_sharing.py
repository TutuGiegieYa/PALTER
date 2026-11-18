"""Evidence delivery and disclosure boundaries, including immutable old saves."""
from copy import deepcopy
import json
from pathlib import Path
import tempfile
import unittest

from palter import ensemble_world as w, evidence_sharing as sharing, spectator
from palter.deepseek import DeepSeek, Settings
from palter.ensemble import EnsembleApplication
from palter.scenario_cases import build
from tests.test_ensemble import EnsembleProvider, story_fixture


class EvidenceSharingTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.provider=EnsembleProvider()
        self.app=EnsembleApplication(Path(self.tmp.name)/'test.db',DeepSeek(Settings(api_key='fixture'),self.provider))
        s=w.blank('abcd'*6,'murder',0,'after');spectator.initialize(s)
        preview={'title':'测试','introduction':'核对资料。','cast':dict(zip('ABCD',['甲','乙','丙','丁'])),'victim':'戊'}
        s['preview']=preview;s['closure']={'votes':[],'ready':False}
        w.initialize(s,build(story_fixture(),preview,'murder',3,[],rules_version=3));w.start(s)
        s.update(scheduling_version=2,evidence_sharing_version=1)
        self.state=s;self.inputs=[]

    def acquire(self,actor,cid):
        s=self.state;e=w.emit(s,'inspect',actor,cid);w.acquire(s,actor,cid,e,'亲自检查')

    def private(self,a,b):
        s=self.state;w.apply_choice(s,a,'invite:'+b);w.apply_choice(s,b,'accept:'+s['invitations'][-1]['id'])

    def disclose(self,actor,cid):
        s=self.state;e=w.speak(s,actor,'我说过这份材料的内容。')
        s['disclosures'].append({'event_id':e['id'],'evidence_id':cid,'channel':e['facts']['channel']})
        if e['facts']['channel']=='public':w.publish_contribution(s,actor,cid)
        return e

    def caller(self,version):
        def call(stage,task,baseline,data,validate,actor=None):
            self.inputs.append((task,deepcopy(data)))
            payload,_=self.app.gateway.payload(task,baseline,data,version)
            out=json.loads(self.provider(payload)['choices'][0]['message']['content'])
            validate(out);return out,'fixture'
        call.prefix_version=version
        return call

    def test_spoken_disclosure_is_not_presentation_or_acquisition(self):
        self.acquire('A','c4');self.disclose('A','c4')
        focus=w.decision_focus(self.state,'A');status=focus['evidence_sharing']['c4']
        self.assertTrue(status['spoken_by_me']);self.assertFalse(status['shown_by_me'])
        self.assertNotIn('c4',focus['already_shared']);self.assertNotIn('c4',self.state['known']['B'])
        self.assertIn('c4',self.state['contributions']['A'])

    def test_public_share_excludes_private_absence_and_repeat_reaches_returnees(self):
        self.acquire('A','c4');self.private('C','D')
        s=self.state;e=w.apply_choice(s,'A','share:c4')
        self.assertEqual(e['facts']['channel'],'public');self.assertEqual(e['facts']['recipients'],['A','B'])
        self.assertEqual(sharing.for_role(s,'A')['c4']['shown_to'],['B'])
        self.assertEqual(sharing.for_role(s,'A')['c4']['not_shown_to'],['C','D'])
        w.close_chat(s,w.chat_for(s,'C'))
        self.assertNotIn('c4',s['known']['C'])
        repeat=w.apply_choice(s,'A','share:c4')
        self.assertEqual(repeat['facts']['recipients'],list('ABCD'))
        self.assertEqual(sharing.for_role(s,'A')['c4']['shown_to'],list('BCD'))
        self.assertIn('c4',s['known']['C']);self.assertEqual(len(sharing.ledger(s)['presentations']),2)

    def test_private_disclosure_and_share_are_absent_from_outside_projection(self):
        for a in 'AB':self.acquire(a,'c4')
        s=self.state;before=sharing.for_role(s,'B');self.private('A','D')
        self.disclose('A','c4');w.apply_choice(s,'A','share:c4')
        self.assertEqual(before,sharing.for_role(s,'B'))
        self.assertEqual(sharing.for_role(s,'A')['c4']['shown_to'],['D'])
        self.assertFalse(sharing.for_role(s,'D')['c4']['shown_by_me'])
        self.assertEqual(sharing.ledger(s)['presentations'][0]['channel'],'private-1')
        self.assertEqual(sharing.omniscient(s)['c4']['known_by'],['A','B','D'])

    def test_own_repeat_counts_even_when_another_role_has_first_disclosure_credit(self):
        self.acquire('A','c1');s=self.state
        w.apply_choice(s,'A','share:c1');w.apply_choice(s,'B','share:c1')
        self.assertNotIn('c1',s['contributions']['B'])
        self.assertIn('c1',w.decision_focus(s,'B')['already_shared'])
        self.assertEqual(sharing.for_role(s,'B')['c1']['shown_to'],['A','C','D'])

    def test_legacy_reconstruction_is_read_only_and_uses_receipts_not_current_custody(self):
        s=self.state;s.pop('evidence_sharing_version')
        self.acquire('A','c4');self.private('C','D');public=w.apply_choice(s,'A','share:c4')
        self.acquire('C','c2');private=w.apply_choice(s,'C','share:c2')
        w.close_chat(s,w.chat_for(s,'C'));s['objects']['c4']['condition']='destroyed'
        old=deepcopy(s);rows={r['event_id']:r for r in sharing.ledger(s)['presentations']}
        self.assertEqual(rows[public['id']]['recipients'],['A','B']);self.assertEqual(rows[public['id']]['channel'],'public')
        self.assertEqual(rows[private['id']]['channel'],'private-1');self.assertEqual(rows[private['id']]['recipients'],['C','D'])
        self.assertIn('c4',s['known']['B']);self.assertEqual(s,old)
        # Older chats may lack start receipts: unknown is safer than a guess.
        s['chats']['private-1'].pop('started_by')
        self.assertTrue(all(r['channel'] is None for r in sharing.ledger(s)['presentations']))

    def test_missing_old_receipts_never_invent_recipients(self):
        self.acquire('A','c4');s=self.state;s.pop('evidence_sharing_version')
        e=w.emit(s,'share','A','c4');row=sharing.ledger(s)['presentations'][0]
        self.assertEqual(row['event_id'],e['id']);self.assertEqual(row['recipients'],[])
        self.assertEqual(sharing.for_role(s,'A')['c4']['shown_to'],[])
        self.assertFalse(sharing.for_role(s,'A')['c4']['recipient_history_complete'])

    def test_independent_discovery_does_not_leak_into_role_sharing_status(self):
        self.acquire('A','c4');s=self.state;before=sharing.for_role(s,'A')
        self.acquire('B','c4');self.assertEqual(before,sharing.for_role(s,'A'))
        self.assertEqual(sharing.omniscient(s)['c4']['known_by'],['A','B'])
        view=w.view(s,'A');self.assertNotIn('known_by',view['evidence'][0]['sharing'])

    def test_current_ai_context_receives_correct_status_and_old_context_is_preserved(self):
        self.acquire('A','c4');self.disclose('A','c4');original=deepcopy(self.state)
        for version in ['ai-tasks-v60.json','ai-tasks-v61.json']:
            s=deepcopy(original);s.pop('evidence_sharing_version');self.inputs=[]
            self.app.turn(s,'A',self.caller(version),0)
            focus=next(d['focus'] for task,d in self.inputs if task=='ensemble_role')
            if version=='ai-tasks-v60.json':
                self.assertNotIn('evidence_sharing',focus);self.assertIn('c4',focus['already_shared'])
                self.assertNotIn('evidence_sharing_version',s)
            else:
                self.assertNotIn('c4',focus['already_shared'])
                self.assertTrue(focus['evidence_sharing']['c4']['spoken_by_me'])
                self.assertEqual(s['evidence_sharing_version'],1)


if __name__=='__main__':unittest.main()
