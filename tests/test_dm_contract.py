"""Regression coverage for the real take failure and legacy DM replies."""

from copy import deepcopy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from palter.ai_gateway import normalize_output
from palter.ai_runtime import AIApplication
from palter.deepseek import DeepSeek, Settings
from palter.storage import StoreError
from tests.test_ai import ProviderDouble


class DMContractTests(unittest.TestCase):
    def test_only_affirmative_machine_aliases_are_normalized(self):
        for task in ("dm", "private_dm"):
            for verdict in ("true", "truthful", "supported", "false", "lying", True, None):
                with self.subTest(task=task, verdict=verdict):
                    output={"assessments":[{"speech_event_id":"e0001", "speaker":"B",
                                            "verdict":verdict, "source_ids":["e0001"]}], "cues":[]}
                    expected=deepcopy(output)
                    if verdict in ("true", "truthful"):
                        expected["assessments"][0]["verdict"]="supported"
                    self.assertEqual(normalize_output(task,output),expected)
        speech={"speech":"true truthful", "thought":"true"}
        self.assertEqual(normalize_output("character",deepcopy(speech)),speech)

    def setUp(self):
        self.directory=tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.provider=ProviderDouble()
        self.verdict=None
        self.invalid_reference=False

        def transport(payload):
            response=self.provider(payload)
            # Character calls can run concurrently; read the task from this request.
            task=payload["messages"][0]["content"].split("PALTER_TASK: ")[1].split("\n")[0]
            data=json.loads(payload["messages"][-1]["content"])
            if task=="initial_setup":
                output=json.loads(response["choices"][0]["message"]["content"])
                output["custody"]="drawer"
                response["choices"][0]["message"]["content"]=json.dumps(output)
            elif task=="dm" and self.verdict is not None:
                utterance=data["utterances"][0]
                output={"assessments":[{"speech_event_id":utterance["id"],
                                         "speaker":utterance["actor"], "verdict":self.verdict,
                                         "source_ids":["unknown_event" if self.invalid_reference else utterance["id"]]}],
                        "cues":[]}
                response["choices"][0]["message"]["content"]=json.dumps(output)
            return response

        self.app=AIApplication(Path(self.directory.name)/"game.sqlite3",
                               DeepSeek(Settings(api_key="test-key"),transport))
        self.app.gateway.current_version="ai-tasks-v6.json"
        self.owner=self.app.store.session()["id"]
        self.state=self.app.create_game(self.owner,{"command_id":"dm_create_0001", "expected_game_id":None})
        self.sequence=0

    def command(self,kind,**extra):
        self.sequence+=1
        command={"command_id":f"dm_command_{self.sequence:04d}",
                 "expected_revision":self.state["revision"], "kind":kind, **extra}
        self.state,receipt=self.app.command(self.owner,self.state["id"],command)
        return command,receipt

    def prepare_take(self):
        self.command("confirm")
        self.command("ready")
        self.command("action",action="move",target="study")
        self.command("action",action="inspect",target="drawer")

    def test_failed_legacy_take_recovers_without_repeating_role_calls_or_action(self):
        self.prepare_take()
        self.verdict="truthful"
        before=deepcopy(self.state)
        command={"command_id":"take_failure_0001", "expected_revision":before["revision"],
                 "kind":"action", "action":"take", "target":"letter", "speech":"我来拿取这件物品。"}
        with patch("palter.ai_gateway.normalize_output",side_effect=lambda task,value:value):
            with self.assertRaises(StoreError) as failed:
                self.app.command(self.owner,before["id"],command)
            self.assertEqual(failed.exception.code,"retry_exhausted")
        self.assertEqual(self.app.store.state(self.owner,before["id"]),before)
        role_calls=sum(task=="character" for task,_,_ in self.provider.calls)
        with self.app.store.transaction() as con:
            self.app.gateway.renew_retry(con,before["id"],command["command_id"])
        self.app.gateway.current_version="ai-tasks-v10.json"
        self.state,receipt=self.app.command(self.owner,before["id"],command)
        self.assertTrue(receipt["accepted"])
        self.assertEqual(self.state["letter_custody"],"A")
        self.assertEqual(self.state["beat"],before["beat"]+1)
        self.assertEqual(sum(task=="character" for task,_,_ in self.provider.calls),role_calls)
        self.assertEqual(self.state["dm_assessments"][-1]["assessments"][0]["verdict"],"supported")
        count=len(self.provider.calls)
        state,receipt=self.app.command(self.owner,before["id"],command)
        self.assertTrue(receipt["duplicate"])
        self.assertEqual(state,self.state)
        self.assertEqual(len(self.provider.calls),count)

    def test_unsupported_verdict_or_reference_still_rejects_atomic_take(self):
        self.prepare_take()
        for verdict,bad_reference in (("false",False),("true",True)):
            with self.subTest(verdict=verdict,bad_reference=bad_reference):
                self.verdict=verdict
                self.invalid_reference=bad_reference
                before=deepcopy(self.state)
                with self.assertRaises(StoreError) as failed:
                    self.command("action",action="take",target="letter",speech="我来拿取这件物品。")
                self.assertEqual(failed.exception.code,"retry_exhausted")
                self.assertEqual(self.app.store.state(self.owner,before["id"]),before)
                # A distinct invalid request needs an explicit cancellation first.
                with self.app.store.transaction() as con:
                    con.execute("UPDATE ai_operations SET status='cancelled' WHERE game_id=? AND status='failed'",(before['id'],))


if __name__=="__main__":
    unittest.main()
