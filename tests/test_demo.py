import concurrent.futures
from copy import deepcopy
import json
from pathlib import Path
import tempfile
import threading
import unittest
from unittest.mock import patch

from palter.deepseek import DeepSeek, Settings, dotenv_values
from palter.engine import RuleError, initial_state, player_view, transition
from palter.server import Application
from palter.storage import Store, StoreError, canonical


def fake_response(payload):
    records = json.loads(payload["messages"][-1]["content"])["observations"]
    return {"model": "deepseek-flash", "choices": [{"finish_reason": "stop", "message": {"content": json.dumps({"observation_ids": [o["id"] for o in records[:2]]})}}],
            "usage": {"prompt_tokens": 100, "completion_tokens": 10, "prompt_cache_hit_tokens": 20, "prompt_cache_miss_tokens": 80}}


class DemoCase(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.database = Path(self.directory.name) / "game.db"
        self.payloads = []
        def transport(payload):
            self.payloads.append(deepcopy(payload))
            return fake_response(payload)
        self.client = DeepSeek(Settings(api_key="unit-test-only-secret"), transport)
        self.app = Application(self.database, self.client)
        self.store = self.app.store
        self.owner = self.store.session()["id"]
        self.sequence = 0
        self.state = self.store.create_game(self.owner, {"command_id": "create_0001", "expected_game_id": None})

    def command(self, kind, **extra):
        self.sequence += 1
        command = {"command_id": f"command_{self.sequence:04d}", "expected_revision": self.state["revision"], "kind": kind, **extra}
        self.state, receipt = self.store.execute(self.owner, self.state["id"], command)
        return command, receipt

    def start(self):
        self.command("confirm")
        self.command("ready")

    def action(self, action, target=None):
        return self.command("action", action=action, target=target)

    def review(self, name="review_0001"):
        return self.app.review(self.owner, self.state["id"], {"command_id": name, "expected_revision": self.state["revision"]})


class GameRulesTests(DemoCase):
    def test_reading_is_not_gameplay(self):
        self.command("confirm")
        before = deepcopy(self.state)
        _, receipt = self.action("wait")
        self.assertFalse(receipt["accepted"])
        self.assertEqual(self.state, before)
        self.assertEqual(self.state["letter_custody"], "B")
        self.assertEqual(self.state["events"], [])
        self.command("ready")
        self.assertEqual(self.state["beat"], 0)
        self.assertEqual(self.state["locations"]["B"], "hall")

    def test_three_documented_outcomes(self):
        sequences = {
            "delivered": [("follow", "B"), ("inspect", "drawer"), ("take", "letter"), ("move", "hall"), ("wait", None), ("wait", None)],
            "incomplete": [("wait", None), ("wait", None), ("wait", None), ("move", "study"), ("inspect", "drawer"), ("take", "letter")],
            "not_found": [("wait", None)] * 6,
        }
        for outcome, actions in sequences.items():
            with self.subTest(outcome=outcome):
                original = initial_state("fixed-game")
                for kind in ("confirm", "ready"):
                    original, _ = transition(original, {"kind": kind})
                result = deepcopy(original)
                for action, target in actions:
                    result, _ = transition(result, {"kind": "action", "action": action, "target": target})
                self.assertEqual(result["outcome"], outcome)
                self.assertEqual(result["phase"], "ended")
                self.assertEqual(result["beat"], 6)
                repeated = deepcopy(original)
                for action, target in actions:
                    repeated, _ = transition(repeated, {"kind": "action", "action": action, "target": target})
                self.assertEqual(result, repeated)
                with self.assertRaises(RuleError):
                    transition(result, {"kind": "action", "action": "wait"})

    def test_follow_observes_movement_not_inventory(self):
        self.start()
        self.action("follow", "B")
        view = player_view(self.state)
        self.assertEqual(view["scene"]["id"], "study")
        self.assertIsNone(self.state["knowledge"]["A"]["letter_location"])
        self.assertNotIn("包里", canonical(view))
        self.assertTrue(any("周砚来到书房" in o["text"] for o in self.state["observations"]["B"]))
        self.assertFalse(any("跟随" in o["text"] for o in self.state["observations"]["B"]))
        self.action("inspect", "drawer")
        self.assertEqual(self.state["knowledge"]["A"]["letter_location"], "drawer")
        self.assertTrue(any("看不清经手" in o["text"] for o in self.state["observations"]["A"]))

    def test_late_follow_does_not_rewrite_history(self):
        self.start()
        self.action("wait")
        before = deepcopy(self.state)
        _, receipt = self.action("follow", "B")
        self.assertFalse(receipt["accepted"])
        self.assertEqual(before, self.state)
        self.action("move", "study")
        self.action("inspect", "drawer")
        self.assertFalse(any("动了动书桌" in o["text"] for o in self.state["observations"]["A"]))
        self.assertEqual(len(self.state["observations"]["C"]), 1)
        self.assertEqual(self.state["observations"]["C"], before["observations"]["C"])

    def test_follow_expires_without_movement(self):
        self.start()
        _, receipt = self.action("follow", "C")
        self.assertFalse(receipt["accepted"])
        self.action("follow", "B")
        self.action("follow", "B")
        self.assertEqual(self.state["beat"], 2)
        self.assertEqual(self.state["locations"]["A"], "study")
        self.assertIn("这次跟随已结束", self.state["observations"]["A"][-1]["text"])

    def test_unknown_target_does_not_reveal_custody(self):
        self.start()
        before = deepcopy(self.state)
        _, first = self.action("take", "letter")
        self.assertFalse(first["accepted"])
        self.assertEqual(before, self.state)
        self.action("wait")
        self.action("wait")
        _, second = self.action("take", "letter")
        self.assertEqual(first["message"], second["message"])

    def test_pause_and_restore_do_not_advance(self):
        self.start()
        self.action("follow", "B")
        self.command("pause")
        saved = deepcopy(self.state)
        self.action("wait")
        self.assertEqual(self.state, saved)
        recovered = Store(self.database).state(self.owner, self.state["id"])
        self.assertEqual(saved, recovered)
        self.command("resume")
        self.assertEqual(self.state["beat"], 1)
        self.assertEqual(self.state["events"], saved["events"])


class PersistenceTests(DemoCase):
    def test_duplicate_returns_current_view_without_second_effect(self):
        self.start()
        command, receipt = self.action("wait")
        self.action("wait")
        before = deepcopy(self.state)
        state, repeated = self.store.execute(self.owner, self.state["id"], command)
        self.assertEqual(state, before)
        self.assertTrue(repeated["duplicate"])
        self.assertEqual(receipt["command_id"], repeated["command_id"])
        self.assertEqual(state["beat"], 2)
        with self.assertRaises(StoreError):
            self.store.execute(self.owner, self.state["id"], {**command, "action": "move", "target": "study"})

    def test_concurrent_double_click_and_stale_tab(self):
        self.start()
        command = {"command_id": "parallel_0001", "expected_revision": self.state["revision"], "kind": "action", "action": "wait"}
        with concurrent.futures.ThreadPoolExecutor(2) as pool:
            results = list(pool.map(lambda _: self.store.execute(self.owner, self.state["id"], command), range(2)))
        self.assertEqual(self.store.state(self.owner, self.state["id"])["beat"], 1)
        self.assertEqual(sum(r[1]["duplicate"] for r in results), 1)
        _, stale = self.store.execute(self.owner, self.state["id"], {**command, "command_id": "parallel_0002"})
        self.assertFalse(stale["accepted"])
        self.assertEqual(stale["code"], "stale_revision")

    def test_new_game_archives_without_destroying_old_observations(self):
        self.start()
        self.action("follow", "B")
        old = deepcopy(self.state)
        new = self.store.create_game(self.owner, {"command_id": "create_0002", "expected_game_id": old["id"]})
        archived = self.store.state(self.owner, old["id"])
        self.assertTrue(archived["archived"])
        self.assertEqual(archived["observations"], old["observations"])
        self.assertEqual(archived["events"], old["events"])
        self.assertEqual(new["beat"], 0)
        self.assertEqual(new["phase"], "introduction")
        with self.assertRaises(RuleError):
            transition(archived, {"kind": "action", "action": "wait"})

    def test_owner_boundary(self):
        other = self.store.session()["id"]
        with self.assertRaises(StoreError) as caught:
            self.store.state(other, self.state["id"])
        self.assertEqual(caught.exception.status, 404)

    def test_failed_transaction_rolls_back_effects_and_receipt(self):
        self.start()
        before = deepcopy(self.state)
        original = self.store.save
        def fail_after_save(con, state, previous):
            original(con, state, previous)
            raise RuntimeError("Simulated crash before commit")
        with patch.object(self.store, "save", side_effect=fail_after_save):
            with self.assertRaises(RuntimeError):
                self.action("wait")
        self.assertEqual(self.store.state(self.owner, before["id"]), before)
        with self.store.transaction(False) as con:
            self.assertIsNone(con.execute("SELECT 1 FROM commands WHERE game_id=? AND id=?", (before["id"], "command_0003")).fetchone())

    def test_player_projection_excludes_internal_data(self):
        self.start()
        self.action("wait")
        view = self.app.view(self.owner, self.state)
        for field in ("locations", "letter_custody", "knowledge", "events", "fixture_version", "owner"):
            self.assertNotIn(field, view)
        last = view["scene"]["last_seen"]
        self.assertEqual(last[0]["id"], "B")
        self.assertEqual(last[0]["beat"], 1)
        self.assertNotIn("unit-test-only-secret", canonical(view))


class ModelTests(DemoCase):
    def test_bounded_review_is_real_adapter_work_but_no_world_mutation(self):
        self.start()
        before = deepcopy(self.state)
        response = self.review()
        self.assertEqual(response["status"], "completed")
        self.assertEqual(self.store.state(self.owner, before["id"]), before)
        self.assertEqual(len(self.payloads), 1)
        user_data = json.loads(self.payloads[0]["messages"][-1]["content"])
        self.assertEqual(user_data, {"observations": before["observations"]["A"]})
        self.assertNotIn("包里", canonical(user_data))
        self.assertEqual(response["view"]["review"]["reported_usage"]["prompt_cache_hit_tokens"], 20)
        self.assertAlmostEqual(response["view"]["review"]["estimated_upper_usd"], .00003612)
        self.review("review_0002")
        self.assertEqual(len(self.payloads), 1, "Same authorized context uses the stored review")

    def test_budget_and_reading_gate(self):
        with self.assertRaises(StoreError):
            self.review()
        self.assertEqual(self.payloads, [])
        self.start()
        for i in range(3):
            self.action("wait")
            self.review(f"review_{i:04d}")
        self.action("wait")
        with self.assertRaises(StoreError) as caught:
            self.review("review_0004")
        self.assertEqual(caught.exception.code, "budget_exhausted")
        self.assertEqual(len(self.payloads), 3)

    def test_invalid_ids_rejected_without_losing_usage(self):
        self.start()
        def bad(payload):
            response = fake_response(payload)
            response["choices"][0]["message"]["content"] = '{"observation_ids":["B-o0001"]}'
            return response
        self.client.transport = bad
        response = self.review()
        self.assertEqual(response["status"], "failed")
        self.assertEqual(response["view"]["review"]["records"], [])
        self.assertEqual(response["view"]["review"]["calls"], 1)
        self.assertEqual(response["view"]["review"]["reported_usage"]["completion_tokens"], 10)

    def test_provider_failure_is_unknown_not_free(self):
        self.start()
        self.client.transport = lambda payload: (_ for _ in ()).throw(TimeoutError())
        response = self.review()
        self.assertEqual(response["status"], "failed")
        self.assertIsNone(response["view"]["review"]["estimated_upper_usd"])
        self.assertTrue(response["view"]["review"]["has_unknown_usage"])
        self.assertEqual(response["view"]["review"]["calls"], 1)

    def test_prefix_stable_and_each_payload_independent(self):
        self.start()
        first = self.client.payload(player_view(self.state))
        stable = deepcopy(first["messages"][0])
        first["messages"][0]["content"] = "modified by caller"
        self.action("wait")
        second = self.client.payload(player_view(self.state))
        self.assertEqual(second["messages"][0], stable)
        self.assertEqual(second["thinking"], {"type": "disabled"})
        self.assertEqual(second["response_format"], {"type": "json_object"})

    def test_pause_holds_completed_review_and_resume_reuses_it(self):
        self.start()
        entered, release = threading.Event(), threading.Event()
        def delayed(payload):
            entered.set()
            release.wait(5)
            return fake_response(payload)
        self.client.transport = delayed
        with concurrent.futures.ThreadPoolExecutor(1) as pool:
            future = pool.submit(self.review)
            self.assertTrue(entered.wait(3))
            self.command("pause")
            release.set()
            result = future.result(5)
        self.assertEqual(result["view"]["review"]["records"], [])
        with self.assertRaises(StoreError):
            self.review("review_paused")
        self.command("resume")
        self.assertTrue(self.app.view(self.owner, self.state)["review"]["records"])

    def test_dotenv_is_not_shell_execution(self):
        path = Path(self.directory.name)/"example.env"
        path.write_text('export DEEPSEEK_API_KEY="literal-$(do-not-execute)"\nDEEPSEEK_MODEL=deepseek-flash # comment\nIGNORED=value\n')
        values = dotenv_values(path)
        self.assertEqual(values["DEEPSEEK_API_KEY"], "literal-$(do-not-execute)")
        self.assertEqual(values["DEEPSEEK_MODEL"], "deepseek-flash")
        self.assertNotIn("IGNORED", values)


if __name__ == "__main__":
    unittest.main()
