"""Real model-driven orchestration with scoped context and atomic world commits."""

from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
import json
import threading
import time

from . import ai_world as w
from .ai_gateway import Gateway, PausedWork
from .engine import RuleError, event
from .server import Application
from .storage import StoreError, canonical, fingerprint


def text(value,limit=1200,empty=False):
    if not isinstance(value,str) or len(value)>limit or (not empty and not value.strip()):raise ValueError("invalid text")
    return value.strip()


def references(value,known,maximum=30):
    if (not isinstance(value,list) or (maximum is not None and len(value)>maximum)
            or any(not isinstance(i,str) or i not in known for i in value)):raise ValueError("invalid references")


class AIApplication(Application):
    mode="ai"
    def __init__(self,database,model=None):
        super().__init__(database,model)
        self.gateway=Gateway(self.store,self.model)
        self.locks={};self.lock_guard=threading.Lock()

    def lock_for(self,game_id):
        with self.lock_guard:return self.locks.setdefault(game_id,threading.Lock())

    def view(self,owner,state):
        if state.get("mode")!="ai":
            copied=deepcopy(state);copied["archived"]=True
            result=super().view(owner,copied)
            result["mode"]="offline"
            return result
        if state["phase"]=="active" and not self.lock_for(state["id"]).locked():
            expired=any(c["status"]=="active" and time.time()>=c["expires"] for c in state["chats"].values())
            if expired:
                with self.store.transaction() as con:
                    previous=self.store.load(con,owner,state["id"]);state=deepcopy(previous)
                    w.expire_chats(state)
                    state["revision"]+=1;self.store.save(con,state,previous)
        view=w.ai_view(state)
        trace=self.gateway.trace(owner,state["id"])
        view["ai_trace"]=trace
        view["ai_busy"]=trace["operation_status"]=="pending"
        calls=trace["calls"]
        review_calls=[c for c in calls if c["task"]=="review"]
        selection=state.get("review_selection",{})
        known={o["id"]:o for o in view["observations"]}
        review_current=selection.get("context")==fingerprint(view["observations"]) and state["phase"] in ("active","ended")
        keys=("prompt_tokens","completion_tokens","prompt_cache_hit_tokens","prompt_cache_miss_tokens")
        usage={k:sum(c["usage"][k] for c in review_calls) if review_calls and all(c["usage"] and c["usage"].get(k) is not None for c in review_calls) else None for k in keys}
        view["review"]={"calls":len(review_calls),"limit":3,"pending":False,"configured":self.model.configured,
                        "model":self.model.settings.model,"reported_usage":usage,
                        "records":[known[i] for i in selection.get("ids",[]) if i in known] if review_current else [],
                        "estimated_upper_usd":sum(c["cost_upper_usd"] or 0 for c in review_calls) if review_calls else None}
        return view

    def create_game(self,owner,command):
        if not self.model.configured:raise StoreError("请先配置 .env 中的 DEEPSEEK_API_KEY；AI 模式不会使用脚本替代。",503,"not_configured")
        category=command.get("category","mystery")
        if category not in w.CATEGORIES:raise StoreError("请选择支持的故事分类。")
        state=self.store.create_game(owner,command,lambda identifier:w.blank(identifier,category))
        op={"command_id":"preview_"+command["command_id"],"expected_revision":0,"kind":"preview"}
        def build(state,call):
            seed={"category":w.CATEGORIES[category],"roles":3,"human_roles":1,"creativity_seed":int(state["id"][:8],16),
                  "mechanics":"三个地点、寻找并带回一件物品、公开讨论与双方同意的私聊；不是预先安排角色行为。"}
            def validate(out):
                candidates=out.get("candidates")
                if candidates is not None:
                    if not isinstance(candidates,list) or len(candidates)!=3:raise ValueError("invalid candidate batch")
                else:candidates=[out]  # Recover operations pinned to the original single-preview contract.
                for candidate in candidates:
                    for key in ("title","introduction","item_name"):text(candidate[key],1200)
            result,_=call("preview","introduction",None,seed,validate)
            if "candidates" in result:
                # Choose once from independent public alternatives, without scoring,
                # filtering or another model call. A retry retains the same choice.
                result=result["candidates"][int(state["id"][8:16],16)%3]
            state["title"]=result["title"];state["introduction"]=result["introduction"];state["preview"]=result
        state,_=self.operate(owner,state["id"],op,build)
        return state

    def operate(self,owner,game_id,command,builder):
        command_id=self.store.command_id(command.get("command_id"))
        digest=fingerprint(command)
        lock=self.lock_for(game_id)
        if not lock.acquire(False):raise StoreError("这一局的 AI 正在处理上一项操作，请稍后恢复同一操作。",503,"ai_pending")
        try:
            with self.store.transaction() as con:
                current=self.store.load(con,owner,game_id)
                row=con.execute("SELECT * FROM ai_operations WHERE game_id=? AND id=?",(game_id,command_id)).fetchone()
                if row:
                    if row["digest"]!=digest:raise StoreError("这个操作标识已用于不同内容。",409,"command_conflict")
                    if row["status"]=="completed":return current,{**json.loads(row["result"]),"duplicate":True}
                    if row["status"]=="cancelled":raise StoreError("这项未完成操作已取消。",409,"cancelled")
                    base=json.loads(row["base_state"]);started=row["started"]
                    prefix_version=row["prefix_version"] or self.gateway.current_version
                    con.execute("UPDATE ai_operations SET status='pending',error=NULL WHERE game_id=? AND id=?",(game_id,command_id))
                else:
                    if current["archived"]:raise StoreError("这局记录仅可回顾，请开始新的 AI 游戏。",409,"archived")
                    if current["revision"]!=command.get("expected_revision"):raise StoreError("页面信息已更新，这次操作未执行。",409,"stale_revision")
                    if con.execute("SELECT 1 FROM ai_operations o WHERE game_id=? AND (status IN ('pending','buffered') OR (status IN ('failed','interrupted') AND EXISTS (SELECT 1 FROM ai_calls c WHERE c.game_id=o.game_id AND c.operation_id=o.id)))",(game_id,)).fetchone():raise StoreError("请先恢复或取消上一项 AI 操作。",503,"ai_pending")
                    base=current;started=time.time();prefix_version=self.gateway.current_version
                    con.execute("INSERT INTO ai_operations(game_id,id,digest,base_state,status,started,command,prefix_version) VALUES (?,?,?,?,'pending',?,?,?)",(game_id,command_id,digest,canonical(base),started,canonical(command),prefix_version))
            work=deepcopy(base);work["_operation_time"]=started
            if 'watch' in work:
                # Playback controls are outside model context and can change while buffered.
                for key in ('budget_usd','speed','single_step'):
                    work['watch'][key]=current['watch'][key]
                work['watch']['call_limit']=current['watch'].get('call_limit',128)
            def call(stage,task,baseline,data,validator,actor=None):
                if task=='ensemble_role' and actor in call.memory_headroom_recovery:
                    validator.revalidate_role_feedback=True
                with self.model_slots:
                    return self.gateway.call(owner,game_id,command_id,stage,task,baseline,data,validator,actor,prefix_version)
            call.prefix_version=prefix_version
            from . import memory_headroom
            with self.store.transaction(False) as con:
                rows=con.execute('SELECT actor,stage,task,status,validation_feedback FROM ai_calls '
                    'WHERE game_id=? AND operation_id=?',(game_id,command_id)).fetchall()
                progress=self.gateway.retry_state(con,game_id,command_id)
            call.memory_headroom_recovery=memory_headroom.recovery_actors(rows,progress)
            try:
                if current["phase"]=="paused":raise PausedWork()
                builder(work,call)
                work.pop("_operation_time",None)
                with self.store.transaction() as con:
                    current=self.store.load(con,owner,game_id)
                    status=con.execute("SELECT status FROM ai_operations WHERE game_id=? AND id=?",(game_id,command_id)).fetchone()[0]
                    if status=="cancelled":raise StoreError("操作已取消，模型结果未应用。",409,"cancelled")
                    if current["phase"]=="paused":raise PausedWork()
                    if current["archived"] or current["events"]!=base["events"] or current["observations"]!=base["observations"]:
                        raise StoreError("真实状态已变化，旧模型结果未应用。",409,"stale_work")
                    paused_delta=current.get("pause_accumulated",0)-base.get("pause_accumulated",0)
                    for chat in work.get("chats",{}).values():
                        if chat["status"]=="active":chat["expires"]+=paused_delta
                    if work.get('gameplay')=='ensemble':
                        from . import wait_lifecycle
                        wait_lifecycle.shift(work,paused_delta)
                        work['next_tick']+=paused_delta
                        for invitation in work['invitations']:
                            if invitation['status']=='pending':invitation['expires']+=paused_delta
                        if work['phase']=='reading' and base['phase']!='reading' and work['reading_deadline'] is not None:
                            # Readers get the full interval after setup is delivered,
                            # including after a long provider retry or recovery.
                            work['reading_deadline']=time.time()+120
                    work["pause_accumulated"]=current.get("pause_accumulated",0)
                    if 'watch' in work:
                        from .spectator import merge_controls
                        merge_controls(work,current,base)
                    work["revision"]=current["revision"]+1
                    self.store.save(con,work,current)
                    receipt={"accepted":True,"code":"ai_completed","message":"AI 已完成本轮处理。","command_id":command_id,"duplicate":False}
                    con.execute("UPDATE ai_operations SET status='completed',result=? WHERE game_id=? AND id=?",(canonical(receipt),game_id,command_id))
                    return work,receipt
            except PausedWork:
                with self.store.transaction() as con:
                    status=con.execute('SELECT status FROM ai_operations WHERE game_id=? AND id=?',(game_id,command_id)).fetchone()[0]
                    if status=='cancelled':raise StoreError('操作已取消。',409,'cancelled')
                    con.execute("UPDATE ai_operations SET status='buffered' WHERE game_id=? AND id=?",(game_id,command_id))
                return self.store.state(owner,game_id),{"accepted":False,"pending":True,"code":"ai_paused","message":"已暂停，模型结果保留，恢复后继续。"}
            except Exception as exc:
                failure={'code':getattr(exc,'code','invalid_action' if isinstance(exc,RuleError) else 'internal_error'),
                         'message':str(exc) if isinstance(exc,(StoreError,RuleError)) else '这一步遇到内部错误，已有进展保留。'}
                with self.store.transaction() as con:con.execute("UPDATE ai_operations SET status='failed',error=? WHERE game_id=? AND id=? AND status!='cancelled'",(canonical(failure),game_id,command_id))
                if isinstance(exc,(StoreError,RuleError)):raise StoreError(str(exc),getattr(exc,"status",409),getattr(exc,"code","invalid_action")) from None
                raise
        finally:lock.release()

    def command(self,owner,game_id,command):
        allowed={"command_id","expected_revision","kind","action","target","text","speech","question_to","operation_id","channel"}
        if set(command)-allowed or type(command.get("expected_revision")) is not int:raise StoreError("请求字段或状态版本不正确。")
        state=self.store.state(owner,game_id)
        if state.get("mode")!="ai":raise StoreError("这是旧规则演示记录，请开始新的 AI 游戏。",409,"offline_record")
        kind=command.get("kind")
        for field,limit in (("text",1200),("speech",1000)):
            if field in command and (not isinstance(command[field],str) or len(command[field])>limit):
                raise StoreError("发言或行动输入格式不正确，或超出了长度限制。")
        if kind in ("say","thought","intent") and not command.get("text","").strip():
            raise StoreError("请先填写要提交的内容。")
        if command.get("question_to") not in (None,"A","B","C"):
            raise StoreError("发言对象无效。")
        if kind in ("pause","resume"):
            return self.control(owner,game_id,command)
        if kind=="cancel_pending":
            with self.store.transaction() as con:
                self.store.load(con,owner,game_id)
                con.execute("UPDATE ai_operations SET status='cancelled' WHERE game_id=? AND id=? AND status NOT IN ('completed','cancelled')",(game_id,command.get("operation_id")))
            return self.store.state(owner,game_id),{"accepted":True,"code":"cancelled","message":"未完成的操作已取消；已产生的调用用量仍保留。"}
        return self.operate(owner,game_id,command,lambda state,call:self.build(state,command,call))

    def control(self,owner,game_id,command):
        with self.store.transaction() as con:
            previous=self.store.load(con,owner,game_id)
            self.store.command_id(command.get("command_id"))
            row=con.execute("SELECT * FROM commands WHERE game_id=? AND id=?",(game_id,command["command_id"])).fetchone()
            if row:
                if row["digest"]!=fingerprint(command):raise StoreError("这个操作标识已用于不同内容。",409,"command_conflict")
                return previous,{**json.loads(row["receipt"]),"duplicate":True}
            if previous["archived"]:raise StoreError("已归档记录不能修改。",409,"archived")
            if previous["revision"]!=command["expected_revision"]:raise StoreError("页面状态已更新。",409,"stale_revision")
            state=deepcopy(previous);kind=command["kind"]
            if kind=="pause" and state["phase"]=="active":
                state["phase"]="paused";state["paused_at"]=time.time()
            elif kind=="resume" and state["phase"]=="paused":
                duration=time.time()-state.pop("paused_at",time.time())
                state["pause_accumulated"]=state.get("pause_accumulated",0)+duration
                for chat in state["chats"].values():
                    if chat["status"]=="active":chat["expires"]+=duration
                if state.get('gameplay')=='ensemble':
                    from . import wait_lifecycle
                    wait_lifecycle.shift(state,duration)
                    state['next_tick']+=duration
                    for invitation in state['invitations']:
                        if invitation['status']=='pending':invitation['expires']+=duration
                state["phase"]="active"
            else:raise StoreError("当前阶段不能切换暂停状态。",409,"wrong_phase")
            state["revision"]+=1;self.store.save(con,state,previous)
            receipt={"accepted":True,"code":kind,"message":"已暂停。" if kind=="pause" else "已恢复。"}
            con.execute("INSERT INTO commands VALUES (?,?,?,?)",(game_id,command["command_id"],fingerprint(command),canonical(receipt)))
            return state,receipt

    def setup(self,state,call):
        def validate(out):
            if set(out["rooms"])!={"hall","study","courtyard"} or set(out["roles"])!={"A","B","C"}:raise ValueError("invalid roster")
            if out["custody"] not in ("B","C","drawer"):raise ValueError("invalid custody")
            for room in out["rooms"].values():text(room["name"],40);text(room["description"],800)
            text(out["item"]["name"],100);text(out["item"]["description"],500)
            for c,p in out["roles"].items():
                for key,limit in [("name",40),("persona",1200),("goal",600)]:text(p[key],limit)
                if p["location"] not in w.ADJACENCY or (c=="A" and p["location"]!="hall"):raise ValueError("invalid start")
                if not isinstance(p["memories"],list) or not 1<=len(p["memories"])<=5:raise ValueError("invalid memories")
                for value in p["memories"]:text(value,800)
                if set(p["relationships"])!=set("ABC")-{c}:raise ValueError("invalid relationships")
                for value in p["relationships"].values():text(value,500)
        setup,_=call("setup","initial_setup",None,{"public_candidate":state["preview"],"category":w.CATEGORIES[state["category"]],"supported_actions":"移动、查看、拿取、放置、跟随、交谈、私聊邀请/同意/拒绝。物品只能放入书房抽屉；A 的目标是把目标物品带回 hall。"},validate)
        setup["item"]["name"]=state["preview"]["item_name"]
        w.initialize(state,setup)

    def build(self,state,command,call):
        kind=command["kind"]
        if kind=="confirm" and state["phase"]=="introduction":self.setup(state,call);return
        if kind=="ready" and state["phase"]=="reading":w.start(state);return
        if kind=="review":
            if state["phase"] not in ("active","ended"):raise RuleError("请在游玩或结局界面整理线索。")
            known={o["id"] for o in state["observations"]["A"]}
            def validate(out):references(out["observation_ids"],known)
            out,_=call("review","review",None,{"observations":state["observations"]["A"][-30:]},validate,"A")
            state["review_selection"]={"ids":out["observation_ids"][:4],"context":fingerprint(state["observations"]["A"])}
            return
        if state["phase"]!="active":raise RuleError("请先完成阅读并进入游戏。")
        w.expire_chats(state)
        active_chat=w.chat_for(state,"A")
        if command.get("channel") is not None and command["channel"]!=(active_chat["id"] if active_chat else "public"):
            raise RuleError("会话范围已经变化，原话未发送。请确认当前会话后重新提交。")
        before={c:len(state["observations"][c]) for c in "ABC"}
        if kind=="thought":
            state["thoughts"]["A"].append(text(command.get("text"),1000))
            self.update_memory(state,"A",call,"thought_memory");return
        human_choice=None
        if kind=="action":human_choice=command.get("action","")+(":"+command["target"] if command.get("target") else "")
        elif kind=="intent":
            context=w.role_context(state,"A")
            known={o["id"] for o in context["allowed_choices"]}
            def validate(out):
                if type(out["needs_clarification"]) is not bool:raise ValueError("clarification flag")
                if not out["needs_clarification"] and out["choice"] not in known:raise ValueError("unsupported interpretation")
                text(out.get("clarification",""),1000,True)
            interpreted,_=call("interpret","action",state["profiles"]["A"],{"request":text(command.get("text"),1200),"view":context},validate,"A")
            if interpreted["needs_clarification"]:raise RuleError(interpreted["clarification"] or "请明确本轮要尝试的动作。")
            human_choice=interpreted["choice"]
        elif kind=="invite":human_choice="invite:"+str(command.get("target",""))
        elif kind in ("accept","decline"):human_choice=kind+":"+str(command.get("target",""))
        elif kind=="end_private":
            chat=w.chat_for(state,"A")
            if not chat:raise RuleError("你目前没有进行中的私聊。")
            human_choice="end:"+chat["id"]
        elif kind not in ("say","gesture"):raise RuleError("不支持的交互类型。")
        if human_choice and human_choice not in {o["id"] for o in w.choices(state,"A")}:
            raise RuleError("这个目标现在不在你可以执行的范围内。")
        physical=bool(human_choice and human_choice.partition(":")[0] in ("move","inspect","take","place","follow","wait")) or bool(w.chat_for(state,"A") and kind=="say")
        supplied=command.get("speech") or (command.get("text") if kind=="say" else "")
        if state["obligations"]["A"] and not supplied and kind not in ("gesture","invite","accept","decline"):
            raise RuleError("有人向你提问，请先用话语或提供的动作回应，也可以随行动附上回答。")
        if state["round"]-state["public_turns"]["A"]>=3 and not supplied and kind not in ("end_private","accept","decline","invite"):
            raise RuleError("已经几个交流回合没有发言，请先说一句话，或随行动附上一句发言。")
        state["round"]+=1
        if physical:state["beat"]+=1
        if supplied:w.speak(state,"A",text(supplied,1000),command.get("question_to"))
        if kind=="gesture":
            gesture=command.get("text")
            if gesture not in ("点了点头","摇了摇头","耸了耸肩"):raise RuleError("请选择提供的回应动作。")
            w.speak(state,"A",gesture,command.get("question_to"),gesture=gesture)
        w.expire_chats(state)
        if human_choice and human_choice.startswith(("invite:","accept:","decline:","end:")):
            w.physical_effect(state,"A",human_choice);human_choice=None
        # Independent role inputs never include the human's unspoken action choice.
        with ThreadPoolExecutor(max_workers=2) as pool:
            futures={c:pool.submit(self.decide,state,c,physical,call) for c in "BC"}
            decisions={c:f.result() for c,f in futures.items()}
        moves={}
        for c in "BC":
            decision,call_id,channel=decisions[c]
            old_count=len(state["events"])
            if decision["thought"]:state["thoughts"][c].append(decision["thought"])
            if decision["speech"] and w.audience(state,c,channel):
                w.speak(state,c,decision["speech"],decision.get("question_to"),channel=channel)
                w.expire_chats(state)
            try:
                result=w.physical_effect(state,c,decision["choice"])
                if result and result["kind"]=="move":moves[c]=result
            except RuleError:
                source=event(state,"action_failed",c,outcome="preconditions_changed")
                w.note(state,c,source,"情况发生变化，你这次尝试没有完成。",force=True)
            for source in state["events"][old_count:]:source["facts"]["decision_call_id"]=call_id
        if human_choice:
            if human_choice.startswith("follow:"):
                target=human_choice.partition(":")[2];movement=moves.get(target)
                if movement and movement["facts"]["origin"]==state["locations"]["A"]:w.physical_effect(state,"A","move:"+movement["facts"]["destination"])
                else:
                    source=event(state,"follow", "A",target,outcome="no_visible_movement")
                    w.note(state,"A",source,"对方没有作出你能跟随的移动，这次跟随结束。",force=True)
            else:w.physical_effect(state,"A",human_choice)
        self.dm(state,call,before)
        if physical:self.world_event(state,call)
        w.expire_chats(state)
        with ThreadPoolExecutor(max_workers=2) as pool:
            futures=[pool.submit(self.update_memory,state,c,call,"memory_"+c) for c in "ABC" if len(state["observations"][c])>before[c]]
            for f in futures:f.result()
        if state["beat"]>=state["deadline"]:
            state["phase"]="ended"
            for chat in state["chats"].values():
                if chat["status"]=="active":w.close_chat(state,chat["id"],"结束了本次私聊")
            state["outcome"]="delivered" if state["letter_custody"]=="A" and state["locations"]["A"]=="hall" else "incomplete" if state["letter_custody"]=="A" or state["knowledge"]["A"]["letter_location"] else "not_found"
            known={o["id"] for o in state["observations"]["A"]}
            def validate(out):text(out["title"],100);text(out["narrative"],2500);references(out["source_ids"],known)
            ending,call_id=call("ending","ending",state["profiles"]["A"],{"actual_outcome":state["outcome"],"observations":state["observations"]["A"][-30:],"memory":state["memory"]["A"]},validate,"A")
            state["ending"]={**ending,"call_id":call_id}

    def decide(self,state,actor,physical,call):
        context=w.role_context(state,actor,physical)
        allowed={o["id"] for o in context["allowed_choices"]}
        def validate(out):
            if out["choice"] not in allowed:raise ValueError("invalid action choice")
            text(out["speech"],1000,True);text(out["thought"],1000,True)
            if context["must_speak"] or context["must_respond"]:
                if not out["speech"].strip():raise ValueError("missing required response")
            if out.get("question_to") not in (None,"A","B","C"):raise ValueError("invalid addressee")
        result,call_id=call("decide_"+actor,"character",state["profiles"][actor],context,validate,actor)
        return result,call_id,context["channel"]

    def dm(self,state,call,before):
        new_ids={o["event_id"] for c in "ABC" for o in state["observations"][c][before[c]:]}
        channels={e["facts"].get("channel","public") for e in state["events"] if e["kind"]=="speech" and any(o["event_id"]==e["id"] for c in "ABC" for o in state["observations"][c][before[c]:])}
        # Action/event adjudication is still a model task even in a quiet round.
        channels.add("public")
        for channel in sorted(channels):
            speeches=[e for e in state["events"][-24:] if e["id"] in new_ids and e["kind"]=="speech" and e["facts"]["channel"]==channel]
            participants=state["chats"].get(channel,{}).get("participants",list("ABC"))
            actual=[e for e in state["events"][-32:] if
                    (e["kind"] in ("speech","gesture","behavioral_cue") and e["facts"].get("channel")==channel) or
                    (e["kind"] not in ("speech","gesture","behavioral_cue","private_closed") and
                     (channel=="public" or e["actor"] in participants))]
            known={e["id"] for e in actual}
            speech_map={e["id"]:e for e in speeches}
            def validate(out):
                if not isinstance(out["assessments"],list) or not isinstance(out["cues"],list) or len(out["cues"])>3:raise ValueError("invalid DM output")
                for a in out["assessments"]:
                    if a["speech_event_id"] not in speech_map or a["speaker"]!=speech_map[a["speech_event_id"]]["actor"] or a["verdict"] not in ("supported","known_contradiction","mistaken","uncertain"):raise ValueError("invalid claim assessment")
                    references(a["source_ids"],known)
                seen=set()
                for cue in out["cues"]:
                    if cue["speech_event_id"] not in speech_map or cue["speaker"]!=speech_map[cue["speech_event_id"]]["actor"] or cue["cue"] not in w.CUES or cue["speaker"] in seen:raise ValueError("invalid cue")
                    seen.add(cue["speaker"])
            baseline=state["chats"][channel]["baseline"] if channel!="public" else {"role":"system_dm","outside_fiction":True}
            data={"channel":channel,"utterances":speeches,"actual_events":actual,
                  "actual_custody":state["letter_custody"],"speaker_knowledge":{c:{"initial":state["profiles"][c],"memory":state["memory"][c],"observations":state["observations"][c][-18:]} for c in participants}}
            out,call_id=call("dm_"+channel,"dm" if channel=="public" else "private_dm",baseline,data,validate)
            state.setdefault("dm_assessments",[]).append({"call_id":call_id,"channel":channel,"assessments":out["assessments"]})
            for cue in out["cues"]:
                utterance=speech_map[cue["speech_event_id"]];actor=cue["speaker"]
                source=event(state,"behavioral_cue",actor,channel,code=cue["cue"],dm_call_id=call_id,speech_event_id=utterance["id"])
                for recipient in utterance["facts"]["recipients"]:
                    positions=utterance["facts"]["locations"]
                    if cue["cue"]!="pause" and (recipient==actor or positions[recipient]!=positions[actor]):continue
                    w.note(state,recipient,source,f"{w.name(state,actor)}{w.CUES[cue['cue']]}。",channel=channel,force=True)

    def world_event(self,state,call):
        eligible=["none"]
        eligible.append("courtyard_open" if "courtyard_closed" in state["world_effects"] else "courtyard_closed")
        if state["deadline"]==6 and state["beat"]<6:eligible.append("meeting_delay")
        def validate(out):
            if out["choice"] not in eligible:raise ValueError("unsupported event")
        out,call_id=call("world_event","world_event",{"supported_effects":{"courtyard_closed":"天气变化，通往庭院的路线暂时关闭；可从庭院返回。","courtyard_open":"庭院路线重新开放。","meeting_delay":"当前截止时间延后一节拍，仅允许一次。","none":"不产生事件"}},
                         {"beat":state["beat"],"deadline":state["deadline"],"eligible":eligible,"current_effects":state["world_effects"]},validate)
        choice=out["choice"]
        if choice=="none":return
        if choice=="meeting_delay":state["deadline"]=7;message="公共通知：本轮截止时间延后一节拍。"
        elif choice=="courtyard_closed":state["world_effects"].append(choice);message="天气转坏，通往庭院的路线暂时关闭，身在庭院的人仍可返回。"
        else:state["world_effects"].remove("courtyard_closed");message="天气稍缓，通往庭院的路线重新开放。"
        source=event(state,"world_event",None,choice,selection_call_id=call_id)
        for c in "ABC":
            w.note(state,c,source,message,**({"deadline":state["deadline"]} if choice=="meeting_delay" else {}))

    def update_memory(self,state,actor,call,stage):
        records=state["observations"][actor][-30:];known={o["id"] for o in state["observations"][actor]}
        def validate(out):
            text(out["summary"],2000);references(out["sources"],known,maximum=None)
            if not isinstance(out["relationships"],list) or len(out["relationships"])>2:raise ValueError("relationships")
            for r in out["relationships"]:
                if r["target"] not in set("ABC")-{actor} or type(r["trust_delta"]) not in (int,float) or not -0.2<=r["trust_delta"]<=0.2:raise ValueError("invalid relationship update")
                text(r["reason"],600);references(r["sources"],known)
                if not r["sources"]:raise ValueError("unsourced relationship change")
        result,call_id=call(stage,"memory",state["profiles"][actor],{"actor":actor,"observations":records,"previous":state["memory"][actor],"relationships":state["relationships"][actor],"private_thoughts":state["thoughts"][actor][-3:]},validate,actor)
        state["memory"][actor]={"summary":result["summary"],"sources":result["sources"],"call_id":call_id}
        for update in result["relationships"]:
            relation=state["relationships"][actor][update["target"]]
            relation["trust"]=max(-1,min(1,relation["trust"]+update["trust_delta"]))
            relation["experiences"].append({"reason":update["reason"],"sources":update["sources"],"call_id":call_id})

    def review(self,owner,game_id,command):
        state,receipt=self.command(owner,game_id,{**command,"kind":"review"})
        return {"status":"completed" if receipt.get("accepted") else "pending","receipt":receipt,"message":receipt["message"],"view":self.view(owner,state)}
