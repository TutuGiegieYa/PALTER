from copy import deepcopy
import json
from pathlib import Path
import tempfile
import threading
from concurrent.futures import ThreadPoolExecutor
import unittest
from unittest.mock import patch

from palter.ai_runtime import AIApplication
from palter import ai_world as w
from palter.deepseek import DeepSeek,Settings
from palter.storage import StoreError,canonical


def setup_fixture():
    return {"rooms":{k:{"name":v,"description":v+"的公开环境。"} for k,v in {"hall":"大厅","study":"书房","courtyard":"庭院"}.items()},
            "item":{"name":"蓝封信","description":"一封封好的信件"},"custody":"B",
            "roles":{c:{"name":{"A":"周砚","B":"林舟","C":"许宁"}[c],"persona":"各自有独立的目标。","goal":"找到物品并回到大厅。" if c=="A" else "按自己的判断行动。",
                        "location":"hall" if c!="C" else "courtyard","memories":[f"{c}_PRIVATE_CANARY"],"relationships":{o:"旧识" for o in "ABC" if o!=c}} for c in "ABC"}}


class ProviderDouble:
    def __init__(self):self.calls=[];self.policy=lambda actor,data:"wait";self.fail_task=None;self.block_task=None;self.entered=threading.Event();self.release=threading.Event()
    def __call__(self,payload):
        task=payload["messages"][0]["content"].split("PALTER_TASK: ")[1].split("\n")[0]
        data=json.loads(payload["messages"][-1]["content"])
        self.calls.append((task,deepcopy(payload),deepcopy(data)))
        if task==self.block_task:self.entered.set();self.release.wait(5)
        if task==self.fail_task:raise TimeoutError()
        if task=="introduction":
            out={"title":"可变的交接","introduction":"一场三人交接即将开始。你要寻找一封信。","item_name":"蓝封信"}
            if '"candidates"' in payload["messages"][0]["content"]:
                out={"candidates":[{**out,"title":f"独立候选 {i}","introduction":f"候选 {i} 的公开背景。"} for i in range(3)]}
        elif task=="initial_setup":out=setup_fixture()
        elif task=="character":out={"choice":self.policy(data["actor"],data),"speech":f"我是{data['actor']}，这是我的本轮发言。","thought":"这是角色自己的想法。","question_to":None}
        elif task=="action":out={"choice":"wait","needs_clarification":False,"clarification":""}
        elif task in ("dm","private_dm"):out={"assessments":[],"cues":[]}
        elif task=="world_event":out={"choice":"none"}
        elif task=="memory":
            ids=[o["id"] for o in data["observations"]]
            out={"summary":"这份记忆仅来自本人获得的经历。","sources":ids[-2:],"relationships":[{"target":next(c for c in "ABC" if c!=data["actor"]),"trust_delta":0.1,"reason":"根据亲眼见到或听到的交流。","sources":ids[-1:]}] if ids else []}
        elif task=="ending":out={"title":"你的经历告一段落","narrative":"会议开始了，你保留着自己获得的观察。","source_ids":[o["id"] for o in data["observations"][-2:]]}
        elif task=="review":out={"observation_ids":[o["id"] for o in data["observations"][:2]]}
        else:raise AssertionError(task)
        return {"model":"test-double","choices":[{"finish_reason":"stop","message":{"content":json.dumps(out,ensure_ascii=False)}}],
                "usage":{"prompt_tokens":100,"completion_tokens":20,"prompt_cache_hit_tokens":40,"prompt_cache_miss_tokens":60}}


class AITests(unittest.TestCase):
    def setUp(self):
        self.directory=tempfile.TemporaryDirectory();self.addCleanup(self.directory.cleanup)
        self.provider=ProviderDouble()
        self.app=AIApplication(Path(self.directory.name)/"ai.db",DeepSeek(Settings(api_key="test-key"),self.provider))
        self.owner=self.app.store.session()["id"]
        self.state=self.app.create_game(self.owner,{"command_id":"create_ai_0001","expected_game_id":None,"category":"mystery"})
        self.n=0
    def command(self,kind,**extra):
        self.n+=1
        cmd={"command_id":f"ai_command_{self.n:04d}","expected_revision":self.state["revision"],"kind":kind,**extra}
        self.state,receipt=self.app.command(self.owner,self.state["id"],cmd)
        return cmd,receipt
    def start(self):self.command("confirm");self.command("ready")
    def tasks(self):return [task for task,_,_ in self.provider.calls]

    def test_generation_and_initial_reading_are_real_distinct_tasks(self):
        self.assertEqual(self.tasks(),["introduction"])
        self.assertEqual(self.state["events"],[])
        self.command("confirm")
        self.assertEqual(self.tasks(),["introduction","initial_setup"])
        self.assertEqual(self.state["phase"],"reading")
        self.assertNotIn("B_PRIVATE_CANARY",canonical(self.app.view(self.owner,self.state)))
        self.command("ready")
        self.assertNotIn("character",self.tasks())

    def test_candidate_selection_is_stable_and_only_selected_premise_reaches_setup(self):
        preview=deepcopy(self.state["preview"])
        count=len(self.provider.calls)
        repeated=self.app.create_game(self.owner,{"command_id":"create_ai_0001","expected_game_id":None,"category":"mystery"})
        self.assertEqual(repeated["preview"],preview)
        self.assertEqual(len(self.provider.calls),count)
        self.assertNotIn("candidates",self.app.view(self.owner,repeated))
        self.assertEqual(repeated["events"],[])
        with self.app.store.transaction(False) as con:
            candidates=json.loads(con.execute("SELECT result FROM ai_calls WHERE game_id=? AND task='introduction'",(self.state["id"],)).fetchone()[0])["candidates"]
        self.assertIn(preview,candidates)
        self.command("confirm")
        setup_input=next(data for task,_,data in self.provider.calls if task=="initial_setup")
        self.assertEqual(setup_input["public_candidate"],preview)
        for candidate in candidates:
            if candidate!=preview:self.assertNotIn(candidate["introduction"],canonical(setup_input))


    def test_model_choices_change_actual_actions_without_beat_script(self):
        self.start()
        self.provider.policy=lambda actor,data:"move:study" if actor=="B" else "wait"
        with patch("palter.engine.scripted_turn",side_effect=AssertionError("Script must not run")):
            self.command("action",action="follow",target="B")
        self.assertEqual(self.state["locations"]["B"],"study")
        self.assertEqual(self.state["locations"]["A"],"study")
        self.assertEqual(self.state["letter_custody"],"B")
        self.provider.policy=lambda actor,data:"place:drawer" if actor=="B" else "wait"
        self.command("action",action="inspect",target="drawer")
        self.assertEqual(self.state["letter_custody"],"drawer")
        events=[e for e in self.state["events"] if e["actor"]=="B" and e["kind"]=="place"]
        self.assertTrue(events[0]["facts"]["decision_call_id"])
        for task in ("character","dm","memory","world_event"):self.assertIn(task,self.tasks())

    def test_role_inputs_are_isolated_and_memory_updates_have_sources(self):
        self.start()
        self.command("thought",text="A_THOUGHT_CANARY")
        self.command("action",action="wait",speech="我们先讨论一下。")
        for task,payload,data in self.provider.calls:
            if task=="character":
                raw=canonical(payload);actor=data["actor"]
                self.assertNotIn("A_THOUGHT_CANARY",raw)
                self.assertNotIn(("C" if actor=="B" else "B")+"_PRIVATE_CANARY",raw)
        self.assertTrue(self.state["memory"]["A"]["call_id"])
        self.assertTrue(self.state["relationships"]["A"]["B"]["experiences"])

    def test_private_consent_dedicated_dm_and_missed_outside_events(self):
        self.start()
        def policy(actor,data):
            if actor=="B":
                invitation=next((i for i in data["invitations"] if i["to"]=="B"),None)
                return "accept:"+invitation["id"] if invitation else "wait"
            return "move:hall" if data["location"]=="courtyard" and any(o["id"]=="move:hall" for o in data["allowed_choices"]) else "wait"
        self.provider.policy=policy
        self.command("invite",target="B")
        view=self.app.view(self.owner,self.state)
        self.assertIsNotNone(view["chat"])
        chat=view["chat"]["id"]
        self.command("say",text="这段话只告诉你。",channel=chat)
        self.assertIn("private_dm",self.tasks())
        c_text=canonical(self.state["observations"]["C"])
        self.assertNotIn("这段话只告诉你",c_text)
        a_text=canonical(self.state["observations"]["A"])
        self.assertNotIn("许宁离开",a_text)
        for task,_,data in self.provider.calls:
            if task in ("dm","private_dm"):
                for occurrence in data["actual_events"]:
                    if occurrence["kind"] in ("speech","gesture","behavioral_cue"):
                        self.assertEqual(occurrence["facts"]["channel"],data["channel"])
        original_baseline=deepcopy(self.state["chats"][chat]["baseline"])
        self.command("end_private")
        self.assertEqual(original_baseline,self.state["chats"][chat]["baseline"])
        self.assertIsNone(self.app.view(self.owner,self.state)["chat"])

    def test_free_form_and_generated_ending_use_model(self):
        self.start()
        self.command("intent",text="我决定先留在原地观察。",speech="我先看看情况。")
        for _ in range(5):self.command("action",action="wait",speech="我还在观察。")
        self.assertEqual(self.state["phase"],"ended")
        self.assertIn("action",self.tasks())
        self.assertIn("ending",self.tasks())
        self.assertEqual(self.state["ending"]["title"],"你的经历告一段落")

    def test_duplicate_does_not_repeat_billable_steps_or_action(self):
        self.start()
        cmd,_=self.command("action",action="wait",speech="先等等。")
        count=len(self.provider.calls);before=deepcopy(self.state)
        state,receipt=self.app.command(self.owner,self.state["id"],cmd)
        self.assertTrue(receipt["duplicate"])
        self.assertEqual(state,before)
        self.assertEqual(len(self.provider.calls),count)

    def test_failure_is_visible_without_scripted_fallback(self):
        self.start();before=deepcopy(self.state)
        self.provider.fail_task="character"
        with self.assertRaises(StoreError):self.command("action",action="wait")
        self.assertEqual(self.app.store.state(self.owner,self.state["id"]),before)
        trace=self.app.gateway.trace(self.owner,self.state["id"])
        self.assertTrue(any(c["status"]=="failed" for c in trace["calls"]))

    def test_addressed_question_requires_response_before_unrelated_action(self):
        self.start()
        previous=deepcopy(self.state)
        w.speak(self.state,"B","你愿意回答这个问题吗？","A")
        with self.app.store.transaction() as con:self.app.store.save(con,self.state,previous)
        count=len(self.provider.calls)
        with self.assertRaisesRegex(StoreError,"有人向你提问"):
            self.command("action",action="wait")
        self.assertEqual(len(self.provider.calls),count)
        self.command("gesture",text="点了点头")
        self.assertFalse(self.state["obligations"]["A"])

    def test_private_channel_cannot_be_rebroadcast_after_closing(self):
        self.start()
        self.provider.policy=lambda actor,data:"accept:"+data["invitations"][0]["id"] if data["invitations"] else "wait"
        self.command("invite",target="B")
        channel=w.chat_for(self.state,"A")["id"]
        self.command("end_private")
        count=len(self.provider.calls)
        with self.assertRaisesRegex(StoreError,"会话范围"):
            self.command("say",text="PRIVATE_STALE_CANARY",channel=channel)
        self.assertEqual(len(self.provider.calls),count)
        self.assertNotIn("PRIVATE_STALE_CANARY",canonical(self.app.store.state(self.owner,self.state["id"])))

    def test_pause_buffers_and_resumes_cached_stages(self):
        self.start();self.provider.block_task="character"
        cmd={"command_id":"inflight_0001","expected_revision":self.state["revision"],"kind":"action","action":"wait"}
        with ThreadPoolExecutor(1) as pool:
            future=pool.submit(self.app.command,self.owner,self.state["id"],cmd)
            self.assertTrue(self.provider.entered.wait(3))
            self.command("pause")
            self.provider.release.set()
            state,receipt=future.result(10)
        self.assertTrue(receipt["pending"])
        self.assertEqual(state["beat"],0)
        self.assertEqual(state["phase"],"paused")
        self.command("resume")
        self.app.gateway.current_version="ai-tasks-v3.json"
        self.state,_=self.app.command(self.owner,self.state["id"],cmd)
        self.assertEqual(self.state["beat"],1)
        self.assertEqual(sum(task=="character" for task,_,_ in self.provider.calls),2)


if __name__=="__main__":unittest.main()
