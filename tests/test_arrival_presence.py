"""Arrival snapshots, local perception and omniscient display boundaries."""
from copy import deepcopy
import unittest

from palter import ensemble_world as w, spectator, compact_context
from palter.storage import canonical
from tests import test_ensemble_review as fixture

VERSION='ai-tasks-v78.json'


class ArrivalPresenceTests(unittest.TestCase):
    def setUp(self):
        self.f=fixture.ReviewFixTests();self.f.setUp();self.addCleanup(self.f.doCleanups)
        self.app,self.s=self.f.app,self.f.state
        self.app.configure_rules(self.s,self.f.caller(VERSION))
        self.s['locations'].update(A='r1',B='r1',C='r3',D='r2')
        self.s['agenda']=[]

    def receipt(self,actor,event):
        return next(o for o in self.s['observations'][actor] if o['event_id']==event['id'])

    def test_available_and_empty_rooms(self):
        e=w.apply_choice(self.s,'A','move:r3');o=self.receipt('A',e)
        self.assertEqual(o['text'],'你来到档案间。丙也在这里，可以直接交流。')
        self.assertEqual(o['arrival_presence']['people'],[dict(id='C',name='丙',can_talk=True,private_conversation=False)])
        self.s['locations']['B']='r2'
        e=w.apply_choice(self.s,'A','move:r1')
        self.assertEqual(self.receipt('A',e)['text'],'你来到会客室。这里没有其他人。')

    def private_pair(self):
        self.s['locations'].update(B='r3',C='r3')
        w.apply_choice(self.s,'B','invite:C');w.apply_choice(self.s,'C','accept:i1')
        return w.speak(self.s,'B','PRIVATE_ARRIVAL_CANARY')

    def test_private_occupants_visible_without_delivery_or_backfill(self):
        speech=self.private_pair();before={a:deepcopy(self.s['observations'][a]) for a in 'BCD'}
        e=w.apply_choice(self.s,'A','move:r3');o=self.receipt('A',e)
        self.assertIn('乙、丙也在这里，正在私聊',o['text'])
        self.assertTrue(all(not p['can_talk'] for p in o['arrival_presence']['people']))
        for a in 'BCD':self.assertEqual(self.s['observations'][a],before[a])
        self.assertNotIn('PRIVATE_ARRIVAL_CANARY',canonical(w.context(self.s,'A')))
        self.assertNotIn('invite:B',{c['id'] for c in w.choices(self.s,'A')})
        self.assertEqual(w.audience(self.s,'A'),['A'])

    def test_departure_and_remote_roles_never_receive_destination_roster(self):
        e=w.apply_choice(self.s,'A','move:r3')
        o=self.receipt('B',e);self.assertEqual(o['text'],'甲离开了这里。')
        self.assertNotIn('arrival_presence',o)
        read=compact_context.lookup(self.s,'B',{'requests':[{'id':o['id']}]})
        self.assertNotIn('档案间',canonical(read));self.assertNotIn('arrival_presence',canonical(read))
        self.assertFalse(any(o['event_id']==e['id'] for o in self.s['observations']['D']))

    def test_followers_get_their_own_simultaneous_arrival_snapshot(self):
        self.s['following']['B']='A'
        e=w.apply_choice(self.s,'A','move:r3')
        self.assertEqual([p['id'] for p in self.receipt('A',e)['arrival_presence']['people']],['B','C'])
        self.assertEqual([p['id'] for p in self.receipt('B',e)['arrival_presence']['people']],['A','C'])
        self.assertTrue(self.receipt('B',e)['text'].startswith('你跟随甲来到档案间。'))

    def test_history_does_not_change_when_people_leave_or_chat_ends(self):
        self.private_pair();e=w.apply_choice(self.s,'A','move:r3');before=deepcopy(self.receipt('A',e))
        w.close_chat(self.s,w.chat_for(self.s,'B'));w.apply_choice(self.s,'C','move:r1')
        self.assertEqual(self.receipt('A',e),before)
        read=compact_context.lookup(self.s,'A',{'requests':[{'id':before['id']}]})
        self.assertIn(before['text'],canonical(read))
        self.assertEqual([p['id'] for p in w.scene_presence(self.s,'A')['people']],['B'])

    def test_current_context_distinguishes_presence_from_listeners(self):
        self.private_pair();w.apply_choice(self.s,'A','move:r3')
        data={};self.app.conversation_context(self.s,'A',data,self.f.caller(VERSION),'ensemble_role')
        self.assertEqual(data['conversation']['listeners'],{})
        self.assertEqual(len(data['conversation']['presence']['people']),2)
        data={};self.app.conversation_context(self.s,'B',data,self.f.caller(VERSION),'ensemble_role')
        p=data['conversation']['presence'];self.assertFalse(p['complete'])
        self.assertEqual(p['scope'],'private_conversation');self.assertEqual([x['id'] for x in p['people']],['C'])
        self.assertTrue(p['people'][0]['can_talk'])

    def test_old_version_context_and_receipts_unchanged(self):
        self.s.pop('presence_version');self.app.configure_rules(self.s,self.f.caller('ai-tasks-v77.json'))
        e=w.apply_choice(self.s,'A','move:r3');self.assertEqual(self.receipt('A',e)['text'],'你来到档案间。')
        self.assertNotIn('arrival_presence',self.receipt('A',e))
        data={};self.app.conversation_context(self.s,'A',data,self.f.caller('ai-tasks-v77.json'),'ensemble_role')
        self.assertNotIn('presence',data['conversation'])

    def test_spectator_movement_once_in_third_person_preserves_role_history(self):
        self.s['following']['B']='A';e=w.apply_choice(self.s,'A','move:r3');before=deepcopy(self.s)
        result=spectator.view(self.s);rows=[o for o in result['timeline'] if o['event_id']==e['id']]
        self.assertEqual(len(rows),1);self.assertEqual(rows[0]['text'],'甲来到档案间。乙随行。')
        self.assertEqual(self.s,before)
        self.assertIn(self.receipt('A',e),result['roles']['A']['observations'])
        self.assertIn(self.receipt('B',e),result['roles']['B']['observations'])

    def test_move_has_no_extra_model_call_or_scheduling_effect(self):
        def move(task,out,data):
            if task=='ensemble_role':out.update(action={'kind':'move','args':['r3']},speech='',question_to=None,next_decision={'mode':'continue','events':[]})
        self.app.turn(self.s,'A',self.f.caller(VERSION,move),0)
        self.assertEqual([t for t,d in self.f.inputs],['ensemble_role'])
        self.assertTrue(self.receipt('A',next(e for e in self.s['events'] if e['kind']=='move'))['arrival_presence'])


if __name__=='__main__':unittest.main()
