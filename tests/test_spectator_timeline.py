"""Event attribution without rewriting speech, receipts or scoped role knowledge."""
from copy import deepcopy
import unittest

from palter import ensemble_world as w, spectator
from palter.storage import canonical
from tests import test_ensemble_review as fixture


class SpectatorTimelineTests(unittest.TestCase):
    def setUp(self):
        self.f=fixture.ReviewFixTests();self.f.setUp();self.addCleanup(self.f.doCleanups)
        self.s=self.f.state;self.f.app.configure_rules(self.s,self.f.caller('ai-tasks-v121.json'))
        self.s['locations']=dict.fromkeys(w.ACTORS,'r1');self.s['agenda']=[]

    def timeline(self):return spectator.view(self.s)['timeline']

    def test_four_inspections_are_named_actions_with_bodies_only_in_details(self):
        for a in w.ACTORS:w.apply_choice(self.s,a,'inspect:c1')
        before=deepcopy(self.s);view=spectator.view(self.s)
        rows=[r for r in view['timeline'] if r['kind']=='inspect']
        self.assertEqual(len(rows),4);self.assertEqual(len({r['event_id'] for r in rows}),4)
        body=self.s['known']['A']['c1']['observation']
        for a,row in zip(w.ACTORS,rows):
            self.assertIn(w.name(self.s,a),row['text']);self.assertNotIn(body,row['text'])
            self.assertEqual(row['details'][0]['text'],body);self.assertEqual(row['details'][0]['recipients'],[a])
            self.assertEqual(view['roles'][a]['observations'],w.observed_dialogue(self.s,a))
        self.assertEqual(self.s,before)

    def test_same_shared_event_merges_receipts_but_retains_different_perceptions(self):
        e=w.emit(self.s,'fixture_fact','A')
        for a in 'ABC':w.note(self.s,a,e,'共同收到的事实。')
        w.note(self.s,'D',e,'你还注意到了另一项细节。')
        rows=[r for r in self.timeline() if r['event_id']==e['id']]
        self.assertEqual(len(rows),1);row=rows[0]
        self.assertNotIn('你',row['text']);self.assertEqual(len(row['details']),2)
        self.assertEqual(row['details'][0]['recipients'],list('ABC'))
        self.assertEqual(row['details'][1]['text'],'你还注意到了另一项细节。')
        self.assertEqual(row['details'][1]['recipients'],['D'])

    def test_same_speech_in_distinct_events_stays_exact_including_you(self):
        text='你能再说明一下吗？'
        first=w.speak(self.s,'A',text);second=w.speak(self.s,'B',text)
        rows=[r for r in self.timeline() if r['event_id'] in (first['id'],second['id'])]
        self.assertEqual(len(rows),2);self.assertEqual([r['text'] for r in rows],[text,text])
        self.assertEqual([r['speaker_name'] for r in rows],['甲','乙'])

    def test_search_follow_and_cancellation_use_third_person_but_keep_raw_receipts(self):
        follow=w.apply_choice(self.s,'A','follow:B');search=w.apply_choice(self.s,'A','search')
        cancel=w.apply_choice(self.s,'A','cancel_work');before=deepcopy(self.s)
        rows={r['event_id']:r for r in self.timeline()}
        for event in (follow,search,cancel):
            row=rows[event['id']]
            self.assertIn('甲',row['text']);self.assertNotIn('你',row['text'])
            self.assertTrue(any('你' in d['text'] for d in row['details']))
        self.assertEqual(self.s,before)

    def test_private_speech_remains_scoped_in_role_views_and_exact_for_spectator(self):
        w.apply_choice(self.s,'A','invite:B');w.apply_choice(self.s,'B','accept:i1')
        e=w.speak(self.s,'A','你记下这个 PRIVATE_CANARY。');view=spectator.view(self.s)
        row=next(r for r in view['timeline'] if r['event_id']==e['id'])
        self.assertEqual(row['text'],'你记下这个 PRIVATE_CANARY。');self.assertEqual(set(row['recipients']),{'A','B'})
        self.assertNotIn('PRIVATE_CANARY',canonical(view['roles']['C']['observations']))
        self.assertNotIn('speaker_knowledge',canonical(row));self.assertNotIn('assessments',row)

    def test_shared_evidence_body_and_announcement_stay_in_one_event_card(self):
        w.apply_choice(self.s,'A','inspect:c1');e=w.apply_choice(self.s,'A','share:c1')
        rows=[r for r in self.timeline() if r['event_id']==e['id']]
        self.assertEqual(len(rows),1)
        body=self.s['known']['A']['c1']['observation']
        self.assertEqual(sum(d['text']==body for d in rows[0]['details']),1)
        self.assertNotIn(body,rows[0]['text'])


if __name__=='__main__':unittest.main()
