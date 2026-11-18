"""Recipient boundaries for travel, local speech, invitations and structured recall."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import unittest

from palter import ensemble_world as w, action_feedback, compact_context, role_schedule, exploration
from palter.storage import StoreError, canonical
from tests import test_ensemble_review as fixtures

VERSION='ai-tasks-v74.json'


class LocalCommunicationTests(unittest.TestCase):
    def setUp(self):
        self.f=fixtures.ReviewFixTests();self.f.setUp();self.addCleanup(self.f.doCleanups)
        self.s=self.f.state;self.app=self.f.app
        self.app.configure_rules(self.s,self.f.caller(VERSION))
        self.s['locations'].update(A='r1',B='r1',C='r3',D='r2')
        self.s['agenda']=[]

    def observations(self, actor, event):
        return [o for o in self.s['observations'][actor] if o['event_id']==event['id']]

    def turn(self, speech='', target=None, choice='move:r3'):
        def change(task,out,data):
            if task=='ensemble_role':out.update(action={'kind':choice.split(':')[0],'args':choice.split(':')[1:]},speech=speech,question_to=target,next_decision={'mode':'continue','events':[]})
        self.app.turn(self.s,'A',self.f.caller(VERSION,change),0)

    def test_speech_gestures_and_questions_are_local(self):
        before=deepcopy(self.s['silent'])
        e=w.speak(self.s,'A','我现在只和眼前的人说话。','B',challenge=True)
        self.assertEqual(e['facts']['recipients'],['A','B']);self.assertEqual(e['facts']['room'],'r1')
        self.assertTrue(self.s['obligations']['B']['response'])
        for a in 'CD':
            self.assertEqual(self.observations(a,e),[]);self.assertEqual(self.s['silent'][a],before[a])
            self.assertFalse(self.s['obligations'][a]['response'])
        with self.assertRaises(StoreError):w.speak(self.s,'A','隔空问话','C')
        e=w.speak(self.s,'A','我想问不在场的人。','C',allow_unheard=True)
        self.assertTrue(e['facts']['unheard_target']);self.assertEqual(self.observations('C',e),[])
        e=w.speak(self.s,'A','点头',gesture=True)
        self.assertEqual(e['facts']['recipients'],['A','B'])

    def test_presented_documents_do_not_cross_rooms_or_backfill_after_arrival(self):
        w.apply_choice(self.s,'A','inspect:c1');e=w.apply_choice(self.s,'A','share:c1')
        self.assertIn('c1',self.s['known']['B']);self.assertNotIn('c1',self.s['known']['C'])
        self.assertEqual(e['facts']['recipients'],['A','B'])
        w.apply_choice(self.s,'C','move:r1')
        self.assertNotIn('c1',self.s['known']['C']);self.assertEqual(self.observations('C',e),[])
        w.apply_choice(self.s,'A','share:c1');self.assertIn('c1',self.s['known']['C'])

    def test_silent_move_exposes_only_departure_or_arrival(self):
        self.turn()
        e=next(e for e in self.s['events'] if e['kind']=='move')
        self.assertEqual(e['target'],'r3');self.assertEqual(e['facts']['origin'],'r1')
        self.assertEqual(self.observations('B',e)[0]['text'],'甲离开了这里。')
        self.assertEqual(self.observations('C',e)[0]['text'],'甲来到了这里。')
        self.assertEqual(self.observations('D',e),[])
        self.assertIn('档案间',self.observations('A',e)[0]['text'])
        self.assertFalse(any(e['kind']=='testimony' for e in self.s['events']))
        self.assertEqual([t for t,d in self.f.inputs],['ensemble_role'])

    def test_departure_receipt_and_source_lookup_never_reveal_destination(self):
        self.turn()
        groups=action_feedback.for_role(self.s,'B')['groups']
        move=next(g for g in groups if g['action']=='move')
        self.assertEqual(move['args'],[]);self.assertEqual(move['location'],'r1')
        self.assertNotIn('recipients',move['recent'][0]);self.assertNotIn('r3',canonical(move))
        arrival=next(g for g in action_feedback.for_role(self.s,'C')['groups'] if g['action']=='move')
        self.assertEqual(arrival['args'],['r3']);self.assertNotIn('r1',canonical(arrival))
        self.assertFalse(any(g['action']=='move' for g in action_feedback.for_role(self.s,'D')['groups']))
        observation=next(o for o in self.s['observations']['B'] if o['text']=='甲离开了这里。')
        read=compact_context.lookup(self.s,'B',{'requests':[{'id':observation['id']}]})
        self.assertNotIn('档案间',canonical(read));self.assertNotIn('r3',canonical(read))

    def test_departure_speech_may_disclose_conceal_or_mislead(self):
        # Spoken claim deliberately differs from the actual destination.
        self.turn('我去工作室看看。')
        speech=next(e for e in self.s['events'] if e['kind']=='testimony')
        move=next(e for e in self.s['events'] if e['kind']=='move')
        self.assertEqual(speech['facts']['text'],'我去工作室看看。')
        self.assertLess(speech['id'],move['id']);self.assertEqual(self.s['locations']['A'],'r3')
        self.assertEqual(speech['facts']['recipients'],['A','B'])
        self.assertEqual(self.observations('C',speech),[]);self.assertEqual(self.observations('D',speech),[])
        self.assertNotIn('档案间',''.join(o['text'] for o in self.s['observations']['B']))

    def test_move_speech_is_optional_for_culprit_too(self):
        culprit=self.s['case']['solution']['killer']
        def choose(task,out,data):
            if task=='ensemble_role':out.update(action={'kind':'move','args':['r2']},speech='',question_to=None,next_decision={'mode':'continue','events':[]})
        self.app.turn(self.s,culprit,self.f.caller(VERSION,choose),0)
        self.assertEqual(self.s['locations'][culprit],'r2')
        self.assertFalse(any(e['kind']=='testimony' for e in self.s['events']))

    def test_human_move_speech_and_action_share_one_command(self):
        self.app.play(self.s,'A',{'kind':'act','choice':'move:r3','text':'我先离开一下。'},self.f.caller(VERSION))
        speech=next(e for e in self.s['events'] if e['kind']=='testimony')
        self.assertEqual(speech['facts']['recipients'],['A','B']);self.assertEqual(self.s['locations']['A'],'r3')
        self.assertEqual([t for t,d in self.f.inputs],['ensemble_dm'])
        self.assertEqual(self.observations('C',speech),[])

    def test_invalid_move_does_not_deliver_departure_speech(self):
        before=canonical(self.s)
        with self.assertRaises(StoreError):self.app.play(self.s,'A',{'kind':'act','choice':'move:no-room','text':'我出发了。'},self.f.caller(VERSION))
        self.assertEqual(canonical(self.s),before)

    def test_invitation_requires_colocation_and_expires_on_separation(self):
        choices={c['id'] for c in w.choices(self.s,'A')}
        self.assertIn('invite:B',choices);self.assertNotIn('invite:C',choices)
        with self.assertRaises(StoreError):w.apply_choice(self.s,'A','invite:C')
        w.apply_choice(self.s,'A','invite:B')
        w.apply_choice(self.s,'A','move:r3')
        self.assertEqual(self.s['invitations'][0]['status'],'expired')
        with self.assertRaises(StoreError):w.apply_choice(self.s,'B','accept:i1')
        self.assertFalse(self.s['chats'])

    def test_private_speech_and_end_are_not_broadcast_to_other_rooms(self):
        w.apply_choice(self.s,'A','invite:B');w.apply_choice(self.s,'B','accept:i1')
        e=w.speak(self.s,'A','只有我们听到。')
        self.assertEqual(e['facts']['recipients'],['A','B'])
        w.apply_choice(self.s,'B','end_private');end=self.s['events'][-1]
        for a in 'CD':self.assertEqual(self.observations(a,end),[])
        self.assertNotIn('move:r3',{c['id'] for c in w.choices(self.s,'A')} if w.chat_for(self.s,'A') else set())

    def test_follow_is_explicit_and_followers_really_observe_the_destination(self):
        w.apply_choice(self.s,'B','follow:A');self.turn()
        self.assertEqual(self.s['locations']['B'],'r3')
        e=next(e for e in self.s['events'] if e['kind']=='move')
        self.assertEqual(e['facts']['followers'],['B'])
        self.assertIn('档案间',self.observations('B',e)[0]['text'])
        self.assertEqual(next(g for g in action_feedback.for_role(self.s,'B')['groups'] if g['action']=='move')['args'],['r3'])
        self.assertNotEqual(next(r for r in exploration.for_role(self.s,'B') if r['room_id']=='r3')['status'],'unvisited')

    def test_privately_occupied_witness_does_not_receive_movement(self):
        self.s['locations']['C']='r1'
        w.apply_choice(self.s,'B','invite:C');w.apply_choice(self.s,'C','accept:i1')
        self.turn();e=next(e for e in self.s['events'] if e['kind']=='move')
        for actor in 'BC':self.assertEqual(self.observations(actor,e),[])

    def test_only_local_next_observation_subscriber_wakes(self):
        self.s['agenda']=[]
        for a in 'BCD':
            self.s['role_waits'][a]={'events':['next_observation'],'labels':['下一条观察'],
                'after_observation':len(self.s['observations'][a]),'channel':'public'}
        w.speak(self.s,'A','我核对了一点情况。');role_schedule.reconcile(self.s)
        self.assertNotIn('B',self.s['role_waits']);self.assertIn('C',self.s['role_waits']);self.assertIn('D',self.s['role_waits'])

    def test_no_periodic_monologue_required_when_alone_and_world_notices_remain_global(self):
        self.s['silent']['D']=100
        self.assertFalse(w.must_speak(self.s,'D'))
        before={a:len(self.s['observations'][a]) for a in w.ACTORS}
        w.apply_world(self.s,'block:r2','fixture')
        for a in w.ACTORS:self.assertGreater(len(self.s['observations'][a]),before[a])

    def test_pending_memory_count_is_not_a_wait_completion_count(self):
        w.speak(self.s,'D','我先整理自己已经看到的情况。')
        role_schedule.commit(self.s,'D',{'mode':'wait','events':['next_observation']},role_schedule.context(self.s,'D'))
        display=role_schedule.view(self.s,'D')
        self.assertTrue(display['waiting']);self.assertGreater(display['unread'],0)
        w.speak(self.s,'A','这句话只在另一间房里说。');role_schedule.reconcile(self.s)
        self.assertTrue(role_schedule.waiting(self.s,'D'))
        w.apply_choice(self.s,'A','move:r2');role_schedule.reconcile(self.s)
        self.assertFalse(role_schedule.waiting(self.s,'D'))

    def test_migration_closes_remote_legacy_private_chat_without_rewriting_history(self):
        self.s.pop('communication_version')
        w.apply_choice(self.s,'A','invite:C');w.apply_choice(self.s,'C','accept:i1')
        speech=w.speak(self.s,'A','旧版已收到的内容。');old=deepcopy(speech)
        self.app.configure_rules(self.s,self.f.caller(VERSION))
        self.assertIsNone(w.chat_for(self.s,'A'));self.assertEqual(speech,old)
        self.assertEqual(self.observations('C',speech)[0]['text'],'旧版已收到的内容。')

    def test_alone_presentation_and_monologue_are_not_received_public_disclosures(self):
        self.s['locations']['B']='r2';w.apply_choice(self.s,'A','inspect:c1');w.apply_choice(self.s,'A','share:c1')
        self.assertNotIn('c1',self.s['public_evidence']);self.assertNotIn('c1',self.s['contributions']['A'])
        start=len(self.s['events']);w.speak(self.s,'A','我独自复述自己掌握的事。')
        def disclose(task,out,data):
            if task=='ensemble_dm':out['disclosures']=[{'event_id':data['utterances'][0]['id'],'evidence_id':'c1'}]
        self.app.adjudicate_ensemble(self.s,start,self.f.caller(VERSION,disclose))
        self.assertFalse(w.public_disclosure(self.s['disclosures'][-1]))
        self.assertNotIn('c1',self.s['contributions']['A'])

    def test_retry_reuses_atomic_movement_and_speech_receipts(self):
        self.app.gateway.current_version=VERSION;owner=self.app.store.session()['id']
        def factory(gid):
            s=deepcopy(self.s);s['id']=gid;return s
        s=self.app.store.create_game(owner,{'command_id':'fixture_create','expected_game_id':None},factory)
        command={'command_id':'move_and_speech','expected_revision':0,'kind':'act','choice':'move:r3','text':'我先离开。'}
        run=lambda s,call:self.app.play(s,'A',command,call)
        first,_=self.app.operate(owner,s['id'],command,run)
        again,receipt=self.app.operate(owner,s['id'],command,run)
        self.assertTrue(receipt['duplicate']);self.assertEqual(canonical(first),canonical(again))
        self.assertEqual(sum(e['kind']=='testimony' for e in again['events']),1)
        self.assertEqual(sum(e['kind']=='move' for e in again['events']),1)

    def test_pinned_v73_preserves_previous_scope_and_published_prefixes(self):
        self.s.pop('communication_version')
        self.app.configure_rules(self.s,self.f.caller('ai-tasks-v73.json'))
        self.assertFalse(w.local_communication(self.s));self.assertEqual(w.audience(self.s,'A'),list('ABCD'))
        e=w.apply_choice(self.s,'A','move:r3')
        self.assertIn('档案间',self.observations('B',e)[0]['text'])
        self.assertNotIn('movement_views',e['facts'])
        root=Path('palter/prefixes');manifest=json.loads((root/'manifest.json').read_text())
        for name,digest in manifest.items():self.assertEqual(hashlib.sha256((root/name).read_bytes()).hexdigest(),digest)


if __name__=='__main__':unittest.main()
