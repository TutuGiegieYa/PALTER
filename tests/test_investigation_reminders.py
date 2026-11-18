"""Optional reminders: factual triggers, private scope, cooldown and recovery."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import unittest

from palter import ensemble_world as w, ensemble_context, spectator, investigation_reminders as reminders
from palter.deepseek import DeepSeek, Settings
from palter.ensemble import EnsembleApplication
from palter.storage import StoreError, canonical
from tests import test_ensemble_review as fixture

VERSION = 'ai-tasks-v77.json'


class ReminderTests(unittest.TestCase):
    def setUp(self):
        self.f = fixture.ReviewFixTests(); self.f.setUp(); self.addCleanup(self.f.doCleanups)
        self.app, self.s = self.f.app, self.f.state
        self.app.gateway.current_version = VERSION
        self.app.configure_rules(self.s, self.f.caller(VERSION))

    def data(self, actor='A'):
        d = w.context(self.s, actor)
        ensemble_context.investigation_state(self.s, actor, d)
        self.app.conversation_context(self.s, actor, d, self.f.caller(VERSION), 'ensemble_role')
        d['focus'] = w.decision_focus(self.s, actor)
        received = {o['event_id'] for o in self.s['observations'][actor]}
        agreed = {}
        for e in self.s['events']:
            if e['id'] in received and e['kind'] == 'closure_vote':agreed[e['actor']] = e['facts']['agreed']
        d['closure'] = {'ready': self.s['closure']['ready'], 'known_agreements': agreed}
        return d

    def preview(self, actor='A'):
        return reminders.prepare(self.s, actor, self.data(actor))

    def decision(self, actor='A', action='wait'):
        ticket = self.preview(actor)
        w.speak(self.s, actor, '我仍需核对已经听到的说法。')
        if action != 'wait':w.apply_choice(self.s, actor, action)
        reminders.commit(self.s, actor, ticket)
        return ticket['reminder']

    def prime(self, actor='A'):
        self.assertIsNone(self.decision(actor)); self.assertIsNone(self.decision(actor))

    def test_third_own_decision_has_factual_notice_and_four_decision_cooldown(self):
        self.prime()
        hint = self.decision()
        self.assertEqual(hint['own_decisions_without_new_investigation'], 2)
        self.assertEqual(hint['trigger'], 'no_new_investigation')
        areas = {r['room_id']: r for r in hint['personally_unchecked_areas']}
        self.assertEqual(areas['r1']['status'], 'visited')
        self.assertEqual(areas['r2']['status'], 'unvisited'); self.assertTrue(areas['r2']['can_move'])
        for _ in range(3):self.assertIsNone(self.decision())
        self.assertIsNotNone(self.decision())

    def test_no_other_players_turns_polls_or_memory_rewrites_advance_counter(self):
        self.decision()
        before = deepcopy(self.s['investigation_reminders']['A'])
        for _ in range(6):
            self.decision('B'); self.preview()
        self.s['memory']['A']['summary'] = '我听说这里已经搜过。'
        self.assertIsNone(self.preview()['reminder'])
        self.assertEqual(self.s['investigation_reminders']['A'], before)

    def test_new_inspection_and_visit_reset_streak_but_round_trip_does_not(self):
        self.prime(); self.decision(action='inspect:c1')
        self.assertEqual(self.s['investigation_reminders']['A']['quiet_decisions'], 0)
        self.decision(action='move:r2')
        self.assertEqual(self.s['investigation_reminders']['A']['quiet_decisions'], 0)
        self.decision(action='move:r1'); self.decision(action='move:r2')
        self.assertIsNotNone(self.preview()['reminder'])

    def test_received_material_resets_streak_without_marking_its_room_explored(self):
        self.prime()
        e = w.emit(self.s, 'share', 'B', 'c2')
        w.acquire(self.s, 'A', 'c2', e, '展示')
        ticket = self.preview()
        self.assertEqual(ticket['quiet_decisions'], 0); self.assertIsNone(ticket['reminder'])
        self.assertEqual(next(r for r in self.data()['exploration'] if r['room_id']=='r2')['status'], 'unvisited')

    def test_duplicate_delivery_is_not_new_material_but_changed_record_is(self):
        self.decision(action='inspect:c1'); self.prime()
        e = w.emit(self.s, 'share', 'B', 'c1'); w.acquire(self.s, 'A', 'c1', e, '重复展示')
        self.assertEqual(self.preview()['quiet_decisions'], 2)
        self.s['known']['A']['c1']['observation'] += ' 新取得的补充记录。'
        self.assertEqual(self.preview()['quiet_decisions'], 0)

    def test_search_completion_resets_streak_and_running_work_does_not_get_hint(self):
        self.prime(); self.decision(action='search')
        self.assertIsNone(self.preview()['reminder'])
        w.advance(self.s)
        self.assertEqual(self.preview()['quiet_decisions'], 0)

    def test_private_conversation_and_final_submission_suppress_reminder(self):
        self.prime(); w.apply_choice(self.s, 'A', 'invite:B'); w.apply_choice(self.s, 'B', 'accept:i1')
        self.assertIsNone(self.preview()['reminder'])
        w.apply_choice(self.s, 'A', 'end_private')
        self.assertIsNotNone(self.preview()['reminder'])
        self.s['closure']['ready'] = True
        self.assertIsNone(self.preview()['reminder'])

    def test_new_received_proposal_overrides_cooldown_once(self):
        self.prime(); self.decision(); self.assertIsNone(self.preview()['reminder'])
        w.apply_choice(self.s, 'B', 'close_vote:yes')
        hint = self.decision(); self.assertEqual(hint['trigger'], 'received_closure_proposal')
        self.assertIsNone(self.preview()['reminder'])
        w.apply_choice(self.s, 'C', 'close_vote:yes')
        self.assertEqual(self.preview()['reminder']['trigger'], 'received_closure_proposal')

    def test_unheard_proposals_and_hidden_progress_do_not_change_reminder(self):
        self.prime(); before = self.preview()
        w.apply_choice(self.s, 'B', 'move:r2'); w.apply_choice(self.s, 'B', 'inspect:c2')
        w.apply_choice(self.s, 'B', 'close_vote:yes')
        self.s['objects']['c4']['hidden'] = not self.s['objects']['c4']['hidden']
        after = self.preview()
        self.assertEqual(before, after)
        self.assertNotIn('c2', canonical(after['reminder']))

    def test_spoken_room_report_does_not_change_own_exploration_or_streak(self):
        self.prime(); before = self.preview()['reminder']
        w.speak(self.s, 'B', '我已检查所有地点，没必要再去了。')
        self.assertEqual(before, self.preview()['reminder'])

    def test_blocked_area_is_not_advertised_as_reachable(self):
        self.prime(); self.s['blocked_room'] = 'r2'
        hint = self.preview()['reminder']
        self.assertFalse(next(r for r in hint['personally_unchecked_areas'] if r['room_id']=='r2')['can_move'])

    def test_all_rooms_checked_have_no_reminder_and_changed_area_set_can_refresh(self):
        self.prime(); self.decision()
        for room in ('r1', 'r2', 'r3'):
            if self.s['locations']['A'] != room:self.decision(action='move:'+room)
            self.decision(action='search'); w.advance(self.s)
        self.decision(); self.decision(); self.assertIsNone(self.preview()['reminder'])

    def test_changed_area_set_refreshes_after_two_quiet_decisions(self):
        self.prime(); self.decision(action='move:r2')
        self.decision(); self.decision()
        # Only three decisions since the last hint, but arrival changed the scope.
        hint = self.preview()['reminder']
        self.assertIsNotNone(hint)
        self.assertEqual(next(r for r in hint['personally_unchecked_areas'] if r['room_id']=='r2')['status'], 'visited')

    def test_waiting_roles_are_not_awakened_just_to_deliver_reminders(self):
        self.prime()
        self.s['agenda'] = []; self.s['world_due'] = False
        self.s['role_waits'] = {a: {'events':['next_observation'],'labels':['等新消息'],
                                   'after_observation':len(self.s['observations'][a]),'channel':w.channel(self.s,a)} for a in w.ACTORS}
        self.s['wake_cursors'] = {a:len(self.s['observations'][a]) for a in w.ACTORS}
        before = deepcopy(self.s['investigation_reminders'])
        def no_call(*args):self.fail('An idle reminder must not call a model')
        no_call.prefix_version = VERSION
        self.app.background(self.s, no_call)
        self.assertEqual(self.s['watch']['pause_reason'], 'waiting')
        self.assertEqual(self.s['investigation_reminders'], before)

    def test_reminders_precede_existing_stagnation_pause_in_normal_fair_scheduling(self):
        self.f.provider.next_decision = lambda d: {'mode':'continue','events':[]}
        self.s['watch']['seen_progress'] = sorted(spectator.progress_keys(self.s))
        first = None
        for step in range(12):
            self.app.background(self.s, self.f.caller(VERSION))
            if first is None and any('investigation_reminder' in data for task,_,data in self.f.provider.calls if task=='ensemble_role'):
                first = step+1
                self.assertEqual(self.s['phase'], 'active')
        self.assertEqual(first, 9)
        self.assertEqual(self.s['watch']['pause_reason'], 'stagnation')

    def test_context_projection_is_pure_and_keeps_choices_history_and_waits(self):
        self.prime(); before = deepcopy(self.s)
        for _ in range(3):self.preview()
        self.assertEqual(self.s, before)
        menu = deepcopy(self.data()['choices'])
        self.assertEqual(menu, self.data()['choices'])
        self.assertIn('close_vote:yes', {c['id'] for c in menu})

    def test_real_turn_adds_notice_without_extra_call_or_forcing_action(self):
        self.f.provider.policy = lambda d: 'wait'
        for _ in range(3):self.app.turn(self.s, 'A', self.f.caller(VERSION), 0)
        calls = [(task, data) for task, _, data in self.f.provider.calls]
        self.assertEqual([task for task, _ in calls], ['ensemble_role']*3)
        self.assertNotIn('investigation_reminder', calls[0][1]); self.assertNotIn('investigation_reminder', calls[1][1])
        self.assertIn('investigation_reminder', calls[2][1])
        self.assertEqual([d['choice'] for d in self.s['decisions']], ['wait']*3)
        self.assertEqual(self.s['locations']['A'], 'r1')

    def test_old_version_keeps_context_and_counter_unchanged(self):
        self.prime(); before = deepcopy(self.s['investigation_reminders'])
        self.app.turn(self.s, 'A', self.f.caller('ai-tasks-v75.json'), 0)
        self.assertNotIn('investigation_reminder', self.f.provider.calls[-1][2])
        self.assertEqual(self.s['investigation_reminders'], before)

    def test_both_perspectives_and_prefix_artifacts_are_versioned(self):
        root = Path('palter/prefixes'); manifest = json.loads((root/'manifest.json').read_text())
        for name, digest in manifest.items():self.assertEqual(hashlib.sha256((root/name).read_bytes()).hexdigest(), digest)
        spec = self.app.gateway.versions[VERSION]; old = self.app.gateway.versions['ai-tasks-v75.json']
        self.assertIn('investigation_reminder', spec['ensemble_role']['instruction'])
        self.assertIn('own risks and objectives', spec['ensemble_role']['perspectives']['concealment']['instruction'])
        for role in (spec['ensemble_role'], *spec['ensemble_role']['perspectives'].values()):
            self.assertIn('their own receipts do not wake', role['instruction'])
            self.assertIn('"mode":"continue"', role['instruction'])
        for task in spec:
            if task != 'ensemble_role':self.assertEqual(spec[task], old[task])
            self.assertEqual(spec[task]['tokens'], old[task]['tokens'])


class ReminderRecoveryTests(unittest.TestCase):
    def test_native_lookup_continuation_keeps_one_notice_and_one_completed_decision(self):
        f = ReminderTests(); f.setUp(); self.addCleanup(f.doCleanups); f.prime()
        app = f.app; owner = app.store.session()['id']; payloads = []
        f.s['watch'].update(budget_usd=2, call_limit=128)
        saved = app.store.create_game(owner, {'command_id':'lookup_fixture','expected_game_id':None},
                                     lambda gid:dict(deepcopy(f.s), id=gid))
        source = saved['case']['roles']['A']['knows'][0]
        def transport(payload):
            payloads.append(deepcopy(payload))
            if len(payloads) == 1:
                tool = {'id':'lookup_reminder','type':'function','function':{'name':'read_sources',
                        'arguments':canonical({'requests':[{'id':source,'offset':0}]})}}
                return {'choices':[{'finish_reason':'tool_calls','message':{'role':'assistant','content':None,'tool_calls':[tool]}}]}
            return f.f.provider(payload)
        app.gateway.client.transport = transport
        state, _ = app.operate(owner,saved['id'], {'command_id':'lookup_probe','expected_revision':saved['revision'],'kind':'probe'},
                               lambda s,call:app.turn(s,'A',call,0))
        hints = [json.loads(next(m['content'] for m in p['messages'] if m['role']=='user'))['investigation_reminder'] for p in payloads]
        self.assertEqual(len(hints),2); self.assertEqual(hints[0],hints[1])
        self.assertEqual(state['investigation_reminders']['A']['completed_decisions'],3)

    def test_failed_attempt_and_restart_replay_do_not_double_count_or_consume_notice(self):
        f = ReminderTests(); f.setUp(); self.addCleanup(f.doCleanups); f.prime()
        app = f.app; app.gateway.retry_delays = (0, 0, 0)
        f.s['watch'].update(budget_usd=2, call_limit=128)
        owner = app.store.session()['id']
        saved = app.store.create_game(owner, {'command_id':'reminder_fixture','expected_game_id':None},
                                     lambda gid:dict(deepcopy(f.s), id=gid))
        gid = saved['id']; payloads = []; provider = f.f.provider
        def transport(payload):
            payloads.append(deepcopy(payload))
            if len(payloads) == 1:raise TimeoutError()
            return provider(payload)
        app.gateway.client.transport = transport
        command = {'command_id':'reminder_probe','expected_revision':saved['revision'],'kind':'probe'}
        def interrupted(state, call):
            app.turn(state, 'A', call, 0)
            raise StoreError('Synthetic interruption after role decision',503,'connection_failed')
        with self.assertRaises(StoreError):app.operate(owner,gid,command,interrupted)
        self.assertEqual(app.store.state(owner,gid)['investigation_reminders'], saved['investigation_reminders'])
        self.assertEqual(payloads[0], payloads[1])
        app = EnsembleApplication(app.store.path, DeepSeek(Settings(api_key='fixture'),transport))
        app.gateway.current_version = 'ai-tasks-v75.json'
        state, receipt = app.operate(owner,gid,command,lambda s,call:app.turn(s,'A',call,0))
        self.assertTrue(receipt['accepted']); self.assertEqual(len(payloads),2)
        self.assertEqual(state['investigation_reminders']['A']['completed_decisions'],3)
        self.assertEqual(state['investigation_reminders']['A']['last_reminder_at'],2)


if __name__ == '__main__':unittest.main()
