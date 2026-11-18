"""Explicit paid end-to-end check of the AI feature matrix, not an API hello test."""

import argparse
from collections import Counter
import json
from pathlib import Path
import secrets

from .ai_runtime import AIApplication
from .deepseek import ROOT

REQUIRED={"introduction","initial_setup","character","action","dm","private_dm","memory","world_event","ending","review"}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--report",type=Path,default=ROOT/".local/verification/ai-runtime-live.json")
    parser.add_argument("--database",type=Path,help="Preserve a protected diagnostic SQLite database")
    parser.add_argument("--resume",action="store_true",help="Resume a failed introduction/setup in --database")
    parser.add_argument("--recover",action="store_true",help="Explicitly recover the latest persisted command, reusing completed stages")
    args=parser.parse_args()
    if (args.resume or args.recover) and (not args.database or not args.database.exists()):
        parser.error("--resume/--recover requires an existing --database")
    database=args.database or args.report.with_name("ai-live-"+secrets.token_hex(6)+".sqlite3")
    database.parent.mkdir(parents=True,exist_ok=True,mode=0o700)
    app=AIApplication(database)
    if args.resume or args.recover:
        with app.store.transaction(False) as con:
            session=con.execute("SELECT * FROM sessions ORDER BY rowid DESC LIMIT 1").fetchone()
            owner=session["id"]
            latest=con.execute("SELECT id FROM games WHERE owner=? ORDER BY rowid DESC LIMIT 1",(owner,)).fetchone()
        state=app.store.state(owner,latest["id"])
    else:
        owner=app.store.session()["id"];state=None
    report={"provider":"DeepSeek","mode":"real","completed":False,"database":str(database)}
    try:
        if args.recover:
            with app.store.transaction(False) as con:
                row=con.execute("SELECT command FROM ai_operations WHERE game_id=? AND status IN ('failed','buffered','interrupted') ORDER BY started DESC LIMIT 1",(state["id"],)).fetchone()
            if not row or not row["command"]:raise ValueError("No recoverable persisted command")
            state,receipt=app.command(owner,state["id"],json.loads(row["command"]))
            assert receipt["accepted"],receipt
        if state is None:
            state=app.create_game(owner,{"command_id":secrets.token_hex(12),"expected_game_id":None,"category":"mystery"})
        def command(kind,**extra):
            nonlocal state
            state,receipt=app.command(owner,state["id"],{"command_id":secrets.token_hex(12),"expected_revision":state["revision"],"kind":kind,**extra})
            assert receipt["accepted"],receipt
        if state["phase"]=="introduction":command("confirm")
        if state["phase"]=="reading":
            assert not any(c["task"]=="character" for c in app.gateway.trace(owner,state["id"])["calls"])
            command("ready")
            command("thought",text="我暂时把自己的担忧留在心里，不向其他人说。")
            private_seen=False
            for target in "BC":
                command("invite",target=target,speech="我希望单独了解你亲眼看到的事情，你也可以选择拒绝。")
                chat=next((c for c in state["chats"].values() if c["status"]=="active" and "A" in c["participants"]),None)
                if chat:
                    command("say",text="请告诉我你自己亲眼见到的情况？这个问题只在我们之间讨论。",channel=chat["id"],question_to=target)
                    private_seen=True
                    if any(c["status"]=="active" and "A" in c["participants"] for c in state["chats"].values()):command("end_private")
                    break
            if not private_seen:
                incoming=next((i for i in state["invitations"] if i["to"]=="A" and i["status"]=="pending"),None)
                if incoming:
                    command("accept",target=incoming["id"])
                    chat=next(c for c in state["chats"].values() if c["status"]=="active" and "A" in c["participants"])
                    command("say",text="我们只聊各自看见的事。",channel=chat["id"])
                    if any(c["status"]=="active" and "A" in c["participants"] for c in state["chats"].values()):command("end_private")
            command("intent",text="我现在留在原地等待，不移动。",speech="我先留在原地，继续听听你们的说法。")
            app.review(owner,state["id"],{"command_id":secrets.token_hex(12),"expected_revision":state["revision"]})
            state=app.store.state(owner,state["id"])
        while state["phase"]=="active":
            active=next((c for c in state["chats"].values() if c["status"]=="active" and "A" in c["participants"]),None)
            if active:command("end_private",speech="我们先聊到这里。")
            command("action",action="wait",speech="我继续留意当前发生的事。")
        trace=app.gateway.trace(owner,state["id"])
        kinds=Counter(c["task"] for c in trace["calls"] if c["status"]=="completed")
        report.update(completed=state["phase"]=="ended" and REQUIRED<=set(kinds),tasks=dict(kinds),missing=sorted(REQUIRED-set(kinds)),
                      outcome=state["outcome"],calls=len(trace["calls"]),cost_upper_usd=trace["cost_upper_usd"],
                      errors=[{"task":c["task"],"error":c["error"]} for c in trace["calls"] if c["status"]!="completed"],
                      usage={k:sum((c["usage"] or {}).get(k) or 0 for c in trace["calls"]) for k in ("prompt_tokens","completion_tokens","prompt_cache_hit_tokens")},
                      actual_decision_link_count=sum(bool(e["facts"].get("decision_call_id")) for e in state["events"]),
                      private_conversations=len(state["chats"]),private_exchanges=sum(len(c["turns"]) for c in state["chats"].values()))
    except Exception as exc:
        report["error"]={"type":type(exc).__name__,"message":str(exc)}
        if state:report["trace"]=app.gateway.trace(owner,state["id"])
    finally:
        args.report.parent.mkdir(parents=True,exist_ok=True,mode=0o700)
        args.report.write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n")
        args.report.chmod(0o600)
    print(json.dumps({k:v for k,v in report.items() if k!="trace"},ensure_ascii=False,indent=2))
    if not report["completed"]:raise SystemExit(1)


if __name__=="__main__":main()
