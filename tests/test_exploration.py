"""Investigation progress never comes from speech or hidden world knowledge."""
from copy import deepcopy
import unittest

from palter import ensemble_world as w,exploration,evidence_sharing,ensemble_context
from tests import test_evidence_sharing as fixtures


class ExplorationTests(unittest.TestCase):
    def setUp(self):
        self.fixture=fixtures.EvidenceSharingTests();self.fixture.setUp();self.addCleanup(self.fixture.doCleanups)
        self.state=self.fixture.state;self.state['exploration_version']=1

    def rooms(self,actor='A'):
        return {r['room_id']:r for r in exploration.for_role(self.state,actor)}

    def test_start_and_unvisited_rooms_do_not_expose_hidden_inventory(self):
        rows=self.rooms();self.assertEqual(rows['r1']['status'],'visited')
        self.assertEqual(rows['r2']['status'],'unvisited');self.assertIsNone(rows['r2']['visible_unread_records'])
        self.assertEqual(rows['r3']['personally_checked'],[])
        before=deepcopy(rows);self.state['objects']['c4'].update(hidden=False,condition='destroyed')
        self.assertEqual(before,self.rooms())

    def test_visiting_checking_and_searching_are_distinct(self):
        s=self.state;w.apply_choice(s,'A','move:r2')
        self.assertEqual(self.rooms()['r2']['status'],'visited')
        w.apply_choice(s,'A','inspect:c2')
        self.assertEqual(self.rooms()['r2']['status'],'partial')
        self.assertEqual(self.rooms()['r2']['personally_checked'],[{'id':'c2','title':s['known']['A']['c2']['title']}])
        self.assertEqual(self.rooms()['r2']['completed_searches'],0)
        w.apply_choice(s,'A','search');w.apply_choice(s,'A','cancel_work')
        self.assertEqual(self.rooms()['r2']['completed_searches'],0)
        w.apply_choice(s,'A','search');w.advance(s)
        self.assertEqual(self.rooms()['r2']['completed_searches'],1)
        self.assertEqual(self.rooms('B')['r2']['status'],'unvisited')

    def test_visible_acquired_does_not_claim_hidden_evidence_exhausted(self):
        s=self.state
        for cid,obj in s['objects'].items():
            if obj['holder']=='r2':obj['hidden']=cid!='c2'
        w.apply_choice(s,'A','move:r2');w.apply_choice(s,'A','inspect:c2')
        row=self.rooms()['r2'];self.assertEqual(row['status'],'visible_acquired')
        self.assertEqual(row['visible_unread_records'],[]);self.assertEqual(row['completed_searches'],0)
        self.assertTrue(s['objects']['c7']['hidden'])

    def test_presentation_has_its_own_source_and_does_not_explore_source_room(self):
        s=self.state;w.apply_choice(s,'A','move:r2');original=w.apply_choice(s,'A','inspect:c2')
        share=w.apply_choice(s,'A','share:c2')
        self.assertEqual(s['known']['B']['c2']['acquired_event'],share['id'])
        self.assertNotEqual(s['known']['B']['c2']['acquired_event'],original['id'])
        self.assertEqual(self.rooms('B')['r2']['status'],'unvisited')
        self.assertEqual(exploration.acquisitions(s,'A')['c2']['method'],'personal_inspection')
        origin=exploration.acquisitions(s,'B')['c2'];self.assertEqual(origin['method'],'presentation');self.assertEqual(origin['from_actor'],'A')
        # A later forwarding receipt names the actual presenter, not the original inspector.
        s['known']['C'].pop('c2');s['observations']['C']=[o for o in s['observations']['C'] if o.get('evidence_id')!='c2']
        w.apply_choice(s,'B','share:c2');self.assertEqual(exploration.acquisitions(s,'C')['c2']['from_actor'],'B')

    def test_legacy_copied_via_is_corrected_in_projection_without_mutation(self):
        s=self.state;s.pop('exploration_version');self.fixture.acquire('A','c4');w.apply_choice(s,'A','share:c4')
        self.assertEqual(s['known']['B']['c4']['via'],'亲自检查');before=deepcopy(s)
        record=w.view(s,'B')['evidence'][0]
        self.assertEqual(record['acquisition']['method'],'presentation');self.assertEqual(record['acquisition']['from_actor'],'A')
        self.assertNotIn('via',record);self.assertNotIn('acquired_event',record)
        self.assertEqual(s,before)

    def test_oral_reports_and_fallible_summaries_do_not_create_evidence_or_progress(self):
        s=self.state;before=self.rooms('A')
        e=w.speak(s,'B','我已搜遍工作室，所有材料都检查过了，发现现场的记录写明了时间。')
        s['memory']['A']['summary']='别人说工作室已经查完。'
        self.assertEqual(before,self.rooms('A'));self.assertNotIn('c2',s['known']['A'])
        o=next(o for o in s['observations']['A'] if o['event_id']==e['id'])
        self.assertEqual(ensemble_context.observation(o,'A')['provenance'],'heard_claim')

    def test_remote_snapshot_never_updates_from_unobserved_handling(self):
        s=self.state;w.apply_choice(s,'A','move:r2');w.apply_choice(s,'A','inspect:c2');w.apply_choice(s,'A','move:r1')
        before=self.rooms()['r2'];s['objects']['c5']['condition']='destroyed';s['objects']['c7']['hidden']=True
        self.assertEqual(before,self.rooms()['r2'])
        w.apply_choice(s,'A','move:r2');after=self.rooms()['r2']
        self.assertNotIn('c5',[r['id'] for r in after['visible_unread_records']])
        self.assertNotIn('c7',[r['id'] for r in after['visible_unread_records']])

    def test_received_notice_can_request_revisit_without_revealing_contents(self):
        s=self.state;w.apply_choice(s,'A','move:r3');w.apply_choice(s,'A','move:r1')
        self.fixture.private('B','C');w.apply_world(s,'records','fixture')
        self.assertTrue(self.rooms()['r3']['revisit_notice'])
        self.assertIsNone(self.rooms('B')['r3']['visible_unread_records'])
        self.assertFalse(self.rooms('B')['r3']['revisit_notice'])
        self.assertNotIn('c4',[r['id'] for r in self.rooms()['r3']['visible_unread_records']])

    def test_follow_arrival_is_actual_visit_not_other_players_movement(self):
        s=self.state;w.apply_choice(s,'A','follow:B');w.apply_choice(s,'B','move:r2')
        self.assertEqual(self.rooms()['r2']['status'],'visited')
        self.assertEqual(self.rooms('C')['r2']['status'],'unvisited')

    def test_witnessed_delivery_counts_other_presenters_without_hidden_holdings(self):
        s=self.state;self.fixture.acquire('A','c1');w.apply_choice(s,'A','share:c1')
        status=evidence_sharing.for_role(s,'B',witnessed=True)['c1']
        self.assertFalse(status['shown_by_me']);self.assertEqual(status['witnessed_receivers'],['A','C','D'])
        self.fixture.acquire('B','c4');before=evidence_sharing.for_role(s,'B',witnessed=True)['c4']
        self.fixture.acquire('C','c4');self.assertEqual(before,evidence_sharing.for_role(s,'B',witnessed=True)['c4'])

    def test_new_role_and_memory_contexts_include_receipts_but_pinned_v61_does_not(self):
        s=self.state;self.fixture.acquire('A','c4');w.apply_choice(s,'A','share:c4');original=deepcopy(s)
        for version in ['ai-tasks-v61.json','ai-tasks-v62.json']:
            sample=deepcopy(original);sample.pop('exploration_version');self.fixture.inputs=[]
            app=self.fixture.app;call=self.fixture.caller(version)
            app.turn(sample,'B',call,0)
            app.summarize_chunk(sample,'B',call,len(sample['observations']['B']))
            for task,data in self.fixture.inputs:
                if task not in ('ensemble_role','ensemble_memory'):continue
                if version.endswith('v61.json'):
                    self.assertNotIn('exploration',data);self.assertNotIn('acquisition',data['evidence'][0])
                    if task=='ensemble_role':self.assertIn('available_unread_records',data['focus'])
                else:
                    self.assertIn('exploration',data);self.assertEqual(data['evidence'][0]['acquisition']['method'],'presentation')
                    if task=='ensemble_role':
                        self.assertIn('currently_accessible_unread_records',data['focus'])
                        self.assertNotIn('available_unread_records',data['focus'])


if __name__=='__main__':unittest.main()
