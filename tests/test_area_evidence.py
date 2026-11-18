"""Only searched, read local materials certify area exhaustion; remote views freeze."""
from copy import deepcopy
import json
import unittest

from palter import ensemble_world as w, exploration, spectator
from palter.storage import canonical
from tests import test_ensemble_review as fixture

VERSION='ai-tasks-v124.json'


class AreaEvidenceTests(unittest.TestCase):
    def setUp(self):
        self.f=fixture.ReviewFixTests();self.f.setUp();self.addCleanup(self.f.doCleanups)
        self.app,self.s=self.f.app,self.f.state
        self.app.configure_rules(self.s,self.f.caller(VERSION));self.s['agenda']=[]

    def room(self,actor='A',room='r2'):
        return next(r for r in exploration.for_role(self.s,actor,exhaustion=True) if r['room_id']==room)

    def read(self,actor='A',room='r2'):
        if self.s['locations'][actor]!=room:w.apply_choice(self.s,actor,'move:'+room)
        for record in exploration.visible_records(self.s,actor,room):
            if record['id'] not in self.s['known'][actor]:w.apply_choice(self.s,actor,'inspect:'+record['id'])

    def searched(self,actor='A',room='r2'):
        if self.s['locations'][actor]!=room:w.apply_choice(self.s,actor,'move:'+room)
        w.apply_choice(self.s,actor,'search');w.advance(self.s)

    def complete(self,actor='A',room='r2'):
        self.searched(actor,room);self.read(actor,room)
        self.assertTrue(self.room(actor,room)['no_new_evidence'])

    def test_visible_materials_read_without_search_are_not_certified(self):
        self.read()
        self.assertEqual(self.room()['visible_unread_records'],[])
        self.assertNotIn('no_new_evidence',self.room())

    def test_discovery_is_not_reading_and_certificate_follows_actual_acquisition(self):
        self.s['objects']['c2']['hidden']=True
        self.searched()
        self.assertFalse(self.s['objects']['c2']['hidden'])
        self.assertNotIn('c2',self.s['known']['A'])
        self.assertNotIn('no_new_evidence',self.room())
        self.read();self.assertTrue(self.room()['no_new_evidence'])
        self.assertTrue(any(o['evidence_id']=='c2' for o in self.s['observations']['A'] if o['kind']=='evidence'))

    def test_current_certificate_retracts_for_unread_or_hidden_material(self):
        self.complete()
        self.s['known']['A'].pop('c2')
        self.assertNotIn('no_new_evidence',self.room())
        self.read();self.assertTrue(self.room()['no_new_evidence'])
        self.s['objects']['c2']['hidden']=True
        self.assertNotIn('no_new_evidence',self.room())
        self.searched();self.assertTrue(self.room()['no_new_evidence'])

    def test_new_record_withdraws_certificate_until_read(self):
        self.complete();self.s.setdefault('created_documents',{})['new']={
            'id':'new','title':'新资料','observation':'新的实际记录。','location':'r2','category':'trace','source':'现场'}
        self.s['objects']['new']={'holder':'r2','condition':'intact','hidden':False,'protected':False}
        self.assertNotIn('no_new_evidence',self.room())
        w.apply_choice(self.s,'A','inspect:new');self.assertTrue(self.room()['no_new_evidence'])

    def test_failed_cancelled_and_ongoing_searches_do_not_count(self):
        self.read();w.apply_choice(self.s,'A','search')
        self.assertNotIn('no_new_evidence',self.room())
        w.apply_choice(self.s,'A','cancel_work')
        self.assertNotIn('no_new_evidence',self.room())
        w.apply_choice(self.s,'A','search');self.s['locations']['A']='r1';w.advance(self.s)
        self.assertEqual(self.s['activities'][-1]['status'],'failed')
        self.s['locations']['A']='r2';self.assertNotIn('no_new_evidence',self.room())

    def test_empty_searched_room_can_be_certified_but_untouched_room_cannot(self):
        for obj in self.s['objects'].values():
            if obj['holder']=='r2':obj['holder']='B'
        w.apply_choice(self.s,'A','move:r2');self.assertNotIn('no_new_evidence',self.room())
        self.searched();self.assertTrue(self.room()['no_new_evidence'])
        self.assertNotIn('no_new_evidence',self.room(room='r3'))

    def test_carried_and_destroyed_materials_are_outside_room_search(self):
        self.complete()
        self.s['objects']['c2'].update(holder='B',hidden=True)
        self.s['known']['A'].pop('c2')
        self.assertTrue(self.room()['no_new_evidence'])
        self.s['objects']['c2'].update(holder='r2',condition='destroyed')
        self.assertTrue(self.room()['no_new_evidence'])
        self.s['objects']['c2']['condition']='intact'
        self.assertNotIn('no_new_evidence',self.room())

    def test_another_role_search_or_oral_claim_does_not_certify_me(self):
        self.complete('B');self.read('A')
        w.speak(self.s,'B','这里已搜完，没有新材料。')
        self.s['memory']['A']['summary']='别人说全部搜完了。'
        self.assertNotIn('no_new_evidence',self.room('A'))
        self.assertTrue(self.room('B')['no_new_evidence'])

    def test_remote_snapshot_is_historical_and_does_not_leak_hidden_changes(self):
        self.complete();w.apply_choice(self.s,'A','move:r1')
        before=deepcopy(self.room());self.assertTrue(before['no_new_evidence']);self.assertFalse(before['snapshot_current'])
        self.s['objects']['c2']['hidden']=True
        self.assertEqual(self.room(),before)
        w.apply_choice(self.s,'A','move:r2')
        self.assertNotIn('no_new_evidence',self.room())
        self.assertTrue(self.room()['snapshot_current'])

    def test_receiving_opening_notice_suppresses_old_certificate(self):
        self.complete();w.apply_choice(self.s,'A','move:r1')
        w.apply_world(self.s,'records','fixture')
        self.assertTrue(self.room()['revisit_notice']);self.assertNotIn('no_new_evidence',self.room())

    def test_unheard_notice_does_not_change_remote_certificate(self):
        self.complete();w.apply_choice(self.s,'A','move:r1')
        w.apply_choice(self.s,'A','invite:D');w.apply_choice(self.s,'D','accept:i1')
        before=deepcopy(self.room());w.apply_world(self.s,'records','fixture')
        self.assertEqual(self.room(),before)

    def test_legacy_current_search_counts_but_remote_snapshot_needs_proof(self):
        self.s.pop('area_evidence_version')
        self.complete();w.apply_choice(self.s,'A','move:r1')
        self.assertNotIn('no_new_evidence',self.room())
        w.apply_choice(self.s,'A','move:r2');self.assertTrue(self.room()['no_new_evidence'])

    def test_projection_is_read_only_and_shared_by_player_and_spectator(self):
        self.complete();before=canonical(self.s)
        self.assertTrue(next(r for r in w.view(self.s,'A')['exploration'] if r['room_id']=='r2')['no_new_evidence'])
        self.assertTrue(next(r for r in spectator.view(self.s)['roles']['A']['exploration'] if r['room_id']=='r2')['no_new_evidence'])
        self.assertEqual(canonical(self.s),before)

    def test_old_projection_omits_field_even_with_new_snapshot(self):
        self.complete();w.apply_choice(self.s,'A','move:r1')
        self.assertTrue(self.s['exploration_snapshots']['A']['r2']['no_new_evidence'])
        self.assertTrue(all('no_new_evidence' not in r for r in exploration.for_role(self.s,'A')))

    def test_packed_role_request_includes_only_new_version_and_keeps_action_menu(self):
        self.complete();original=deepcopy(self.s)
        class Captured(Exception):pass
        for version in ('ai-tasks-v123.json',VERSION):
            captured=[]
            def call(stage,task,baseline,data,validate,actor=None):
                if task!='ensemble_role':return self.f.caller(version)(stage,task,baseline,data,validate,actor)
                body,_=self.app.gateway.payload(task,baseline,data,version)
                captured.append(json.loads(body['messages'][2]['content']));raise Captured()
            call.prefix_version=version
            with self.assertRaises(Captured):self.app.turn(deepcopy(original),'A',call,0)
            row=next(r for r in captured[0]['exploration'] if r['room_id']=='r2')
            self.assertEqual(row.get('no_new_evidence'),True if version==VERSION else None)
            self.assertIn('search',canonical(captured[0]['actions']))

    def test_prefix_adds_only_role_marker_and_guidance(self):
        old=deepcopy(self.app.gateway.versions['ai-tasks-v123.json']);new=deepcopy(self.app.gateway.versions[VERSION])
        self.assertEqual(new['ensemble_role'].pop('area_evidence_version'),1)
        for a,b in ((old['ensemble_role'],new['ensemble_role']),
                    (old['ensemble_role']['perspectives']['concealment'],new['ensemble_role']['perspectives']['concealment'])):
            before=a.pop('instruction');after=b.pop('instruction');self.assertTrue(after.startswith(before))
            self.assertIn('no_new_evidence=true',after[len(before):])
        self.assertEqual(old,new)


if __name__=='__main__':unittest.main()
