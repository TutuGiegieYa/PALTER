"""Free investigation on a frozen case, sharing durable AI operations with legacy games."""

from copy import deepcopy
import time

from .ai_runtime import AIApplication, text, references
from . import case_world as w
from .case_authoring import frame, compile_case, candidate_casts, validate_generated_cast
from .engine import event, RuleError
from .storage import StoreError


class InvestigationApplication(AIApplication):
    gameplay="investigation"

    def create_game(self,owner,command):
        if not self.model.configured:raise StoreError("请先配置 DeepSeek，再创建案件。",503,"not_configured")
        if command.get("category","mystery")!="mystery":raise StoreError("当前新局优先提供悬疑推理案件。")
        state=self.store.create_game(owner,command,w.blank)
        operation={"command_id":"preview_"+command["command_id"],"expected_revision":0,"kind":"preview"}
        def build(state,call):
            version=getattr(call,'prefix_version',self.gateway.current_version)
            generated=self.gateway.versions[version]['case_introduction'].get('generated_cast',False)
            seed=int(state['id'][:8],16);rosters=None if generated else candidate_casts(seed)
            data={"seed":seed,"living_players":4,"deceased_victims":1,"human_actor":"A"}
            if generated:data['participants']=list(w.ACTORS)
            else:data['candidate_rosters']=rosters
            def validate(out):
                if not isinstance(out["candidates"],list) or len(out["candidates"])!=3:raise ValueError("candidate count")
                for c in out["candidates"]:
                    text(c["title"],100);text(c["introduction"],1200)
                    if generated:validate_generated_cast(c)
            out,_=call("preview","case_introduction",None,data,validate)
            index=int(state["id"][8:16],16)%3
            selected={k:out['candidates'][index][k] for k in ('title','introduction')}
            selected.update({k:out['candidates'][index][k] for k in ('cast','victim')} if generated else rosters[index])
            state.update(title=selected["title"],introduction=selected["introduction"],preview=selected)
        state,_=self.operate(owner,state["id"],operation,build)
        return state

    def view(self,owner,state):
        if state.get("gameplay")!="investigation":return super().view(owner,state)
        if state["phase"]=="active" and self.lock_for(state["id"]).acquire(False):
            try:
                if any(c["status"]=="active" and time.time()>=c["expires"] for c in state["chats"].values()):
                    with self.store.transaction() as con:
                        previous=self.store.load(con,owner,state["id"]);state=deepcopy(previous)
                        if state["phase"]=="active":
                            w.expire(state);state["revision"]+=1;self.store.save(con,state,previous)
            finally:self.lock_for(state["id"]).release()
        result=w.view(state)
        result["ai_trace"]=self.gateway.trace(owner,state["id"])
        result["ai_busy"]=result["ai_trace"]["operation_status"]=="pending"
        return result

    def command(self,owner,game_id,command):
        current=self.store.state(owner,game_id)
        if current.get("gameplay")!="investigation":return super().command(owner,game_id,command)
        allowed={"command_id","expected_revision","kind","choice","target","text","evidence_ids","suspect","channel","operation_id","gesture"}
        if set(command)-allowed or type(command.get("expected_revision")) is not int:raise StoreError("操作格式或状态版本无效。")
        for key,limit in (("text",4000),("choice",100),("target",50),("suspect",20),("channel",80)):
            if key in command and (not isinstance(command[key],str) or len(command[key])>limit):raise StoreError("操作内容格式无效。")
        kind=command.get("kind")
        if kind in ("pause","resume"):return self.control(owner,game_id,command)
        if kind=="cancel_pending":
            return super().command(owner,game_id,{k:v for k,v in command.items() if k in ("command_id","expected_revision","kind","operation_id")})
        state,receipt=self.operate(owner,game_id,command,lambda state,call:self.investigate(state,command,call))
        if receipt.get("accepted"):receipt["message"]="调查进展已保存。" if state["phase"]!="ended" else "本次推理已结案，可以查看真相复盘。"
        return state,receipt

    def review(self,owner,game_id,command):
        if self.store.state(owner,game_id).get("gameplay")!="investigation":return super().review(owner,game_id,command)
        # The notebook is a projection of committed evidence, never a solution oracle.
        return {"view":self.view(owner,self.store.state(owner,game_id)),"message":"已获得的线索都保存在调查笔记中。"}

    def investigate(self,state,command,call):
        kind=command["kind"]
        if kind=="confirm" and state["phase"]=="introduction":
            contract=frame(state["id"],state["preview"].get("cast"),state["preview"].get("victim"))
            authored,_=call("setup","case_setup",None,{"public_premise":state["preview"],"contract":contract},lambda out:compile_case(out,contract))
            w.initialize(state,compile_case(authored,contract));return
        if kind=="ready" and state["phase"]=="reading":
            state["phase"]="active";source=event(state,"investigation_started","A")
            for actor in w.ACTORS:w.note(state,actor,source,state["case"]["public_briefing"])
            return
        if state["phase"]!="active":raise RuleError("请先完成阅读或恢复调查。")
        w.expire(state)
        chat=w.chat_for(state,"A");channel=chat["id"] if chat else "public"
        if command.get("channel",channel)!=channel:raise RuleError("谈话范围已变化，内容未发送。")
        target=command.get("target")
        if target and (target not in w.NPCS or target not in w.audience(state,"A")):
            raise RuleError("这个角色当前不在你的谈话范围内。")
        ids=command.get("evidence_ids",[])
        if not isinstance(ids,list) or len(ids)>10 or any(not isinstance(i,str) for i in ids) or not set(ids)<=set(state["known"]["A"]):
            raise RuleError("只能引用你已经获得的证据。")
        if kind=="notebook":
            state["notebook"]={"text":command.get("text",""),"evidence_ids":list(dict.fromkeys(ids))};return
        if kind=="thought":
            words=text(command.get("text"),2000);state["thoughts"]["A"].append(words)
            def validate(out):text(out["summary"],2000)
            out,_=call("personal_memory","case_memory",w.baseline(state,"A"),w.context(state,"A"),validate,"A")
            state["memory"]["A"]=out["summary"];return
        if kind in ("accuse","close_case"):
            if chat:raise RuleError("请先结束私聊，再向所有人提交最终结论。")
            self.conclude(state,command,call);return
        if kind not in ("act","say","present","intent","gesture"):raise RuleError("不支持的调查操作。")
        start=len(state["events"]);words=command.get("text","").strip()
        choice=command.get("choice") if kind=="act" else None
        if kind=="intent":
            if not words:raise RuleError("请描述要尝试的行动。")
            available={c["id"] for c in w.choices(state,"A")}
            def validate(out):
                if out["choice"] is not None and out["choice"] not in available:raise ValueError("unsupported case action")
                text(out["clarification"],1000,True)
            out,_=call("interpret","case_action",w.baseline(state,"A"),{"request":words,"view":w.context(state,"A")},validate,"A")
            if out["choice"] is None:raise RuleError(out["clarification"] or "请明确调查目标。")
            choice=out["choice"];words=""
        if kind=="say" and not words:raise RuleError("请填写要追问或表达的内容。")
        if kind=="present" and not ids:raise RuleError("请先选择要出示的证据。")
        if choice is not None and choice not in {c["id"] for c in w.choices(state,"A")}:
            raise RuleError("当前无法执行这个行动，请查看最新现场。")
        state["beat"]+=1;state["round"]+=1
        if kind=="gesture":
            gesture=command.get("gesture")
            if gesture not in ("点头","摇头","示意稍后回答"):raise RuleError("请选择提供的回应动作。")
            w.speak(state,"A",gesture,target,"gesture")
        elif words and kind!="intent":w.speak(state,"A",words,target)
        if kind=="present":
            for clue_id in ids:w.effect(state,"A","share:"+clue_id)
        if choice:w.effect(state,"A",choice)
        # Scene reading and investigation are immediate; speech/evidence/wait create
        # one relevant decision opportunity instead of polling the entire cast.
        active = kind in ("say","present","gesture") or (choice and choice.split(":")[0] in ("wait","invite","accept","share","decline","end_private"))
        if active:
            if choice and choice.startswith("invite:"):target=choice.split(":",1)[1]
            recipients=[c for c in w.audience(state,"A") if c in w.NPCS]
            actor=target if target in recipients else recipients[(state["round"]-1)%len(recipients)] if recipients else None
            if actor:self.role_turn(state,actor,call,"response")
            # Private participants can miss actual outside developments. Only one
            # outside role gets an opportunity, from its own authorized context.
            if chat and state["round"]%2==0:
                outside=[c for c in w.NPCS if c not in chat["participants"]]
                if outside:self.role_turn(state,outside[(state["round"]//2)%len(outside)],call,"outside")
            self.adjudicate(state,start,call)
        w.expire(state)

    def role_turn(self,state,actor,call,stage):
        context=w.context(state,actor);allowed={c["id"] for c in context["choices"]}
        known=set(state["known"][actor]);observations={o["id"] for o in state["observations"][actor]}
        memory_sources=observations|known|set(state["case"]["roles"][actor]["knows"])
        recipients=w.audience(state,actor)
        def validate(out):
            if out["choice"] not in allowed:raise ValueError("invalid case choice")
            for key,limit in (("speech",1600),("memory",2000)):text(out[key],limit,key=="speech")
            references(out["memory_sources"],memory_sources,maximum=None)
            if out["suspect"] not in (None,*w.ACTORS):raise ValueError("invalid belief")
            references(out["evidence_ids"],known)
            if type(out["trust_delta"]) not in (int,float) or not -0.2<=out["trust_delta"]<=0.2:raise ValueError("trust change")
            if out.get("question_to") not in (None,*recipients):raise ValueError("invalid question recipient")
            if context["must_respond"] and not out["speech"].strip():raise ValueError("missing addressed response")
        out,call_id=call(stage+"_"+actor,"case_character",w.baseline(state,actor),context,validate,actor)
        state["memory"][actor]=out["memory"]
        state["trust"][actor]=max(-1,min(1,state["trust"][actor]+out["trust_delta"]))
        state["beliefs"][actor]={"suspect":out["suspect"],"evidence_ids":out["evidence_ids"],"call_id":call_id}
        start=len(state["events"])
        if out["speech"]:w.speak(state,actor,out["speech"],out.get("question_to"))
        if out["choice"]!="wait":w.effect(state,actor,out["choice"])
        for occurrence in state["events"][start:]:occurrence["facts"]["decision_call_id"]=call_id

    def adjudicate(self,state,start,call):
        speeches=[e for e in state["events"][start:] if e["kind"]=="testimony"]
        for channel in sorted({e["facts"]["channel"] for e in speeches}):
            utterances=[e for e in speeches if e["facts"]["channel"]==channel]
            indexed={e["id"]:e for e in utterances}
            participants=state["chats"][channel]["participants"] if channel!="public" else list({e["actor"] for e in utterances})
            def validate(out):
                if not isinstance(out["assessments"],list) or not isinstance(out["cues"],list):raise ValueError("DM arrays")
                for a in out["assessments"]:
                    if a["event_id"] not in indexed or a["verdict"] not in ("supported","known_contradiction","mistaken","uncertain"):raise ValueError("DM claim")
                if len(out["cues"])>2:raise ValueError("too many cues")
                for c in out["cues"]:
                    if c["event_id"] not in indexed or c["cue"] not in ("pause","gaze"):raise ValueError("DM cue")
            baseline=state["chats"][channel]["baseline"] if channel!="public" else {"scope":"public_dm"}
            data={"utterances":utterances,"history":state["case"]["history"],"speaker_knowledge":{c:w.baseline(state,c) for c in participants}}
            out,call_id=call("dm_"+channel,"case_dm",baseline,data,validate)
            state["assessments"].append({"call_id":call_id,"channel":channel,**out})
            for cue in out["cues"]:
                speech=indexed[cue["event_id"]];actor=speech["actor"]
                # Gaze requires co-location; a pause is heard by actual recipients.
                occurrence=event(state,"cue",actor,source_event=speech["id"],call_id=call_id)
                for recipient in speech["facts"]["recipients"]:
                    positions=speech["facts"]["locations"]
                    if cue["cue"]=="gaze" and positions[recipient]!=positions[actor]:continue
                    w.note(state,recipient,occurrence,w.name(state,actor)+("停顿了一下。" if cue["cue"]=="pause" else "移开了视线。"),"cue")

    def conclude(self,state,command,call):
        close=command["kind"]=="close_case";suspect=command.get("suspect")
        explanation=command.get("text","").strip();ids=command.get("evidence_ids",[])
        if not close and (suspect not in w.NPCS or not explanation):raise RuleError("请填写指认对象和你的推理过程。")
        evaluation={"suspect":suspect,"explanation":explanation,"evidence_ids":ids,"established":[]}
        if not close:
            def validate(out):
                if not isinstance(out["claims"],list) or len(out["claims"])>9:raise ValueError("theory claims")
                for claim in out["claims"]:
                    if claim["aspect"] not in w.ASPECTS or type(claim["supported"]) is not bool:raise ValueError("theory aspect")
                    if not isinstance(claim["quote"],str) or not claim["quote"].strip() or claim["quote"] not in explanation:raise ValueError("invented reasoning")
                    references(claim["evidence_ids"],set(ids))
            out,_=call("theory","case_theory",None,{"submitted_suspect":suspect,"explanation":explanation,
                         "cited_evidence":[w.clue_view(c) for c in state["case"]["clues"] if c["id"] in ids],"solution":state["case"]["solution"]},validate,"A")
            for aspect in w.ASPECTS:
                # A player's argument may span several quoted sentences. Only
                # supported claims contribute; jointly sufficient evidence need
                # not be repeated inside one artificially long sentence.
                supported={cid for claim in out["claims"] if claim["aspect"]==aspect and claim["supported"] for cid in claim["evidence_ids"]}
                if any(set(route)<=supported for route in state["case"]["proofs"][aspect]):
                    evaluation["established"].append(aspect)
            state["outcome"]="incorrect" if suspect!=state["case"]["solution"]["killer"] else "established" if set(evaluation["established"])==set(w.ASPECTS) else "unproven"
            w.speak(state,"A",f"我指认{w.name(state,suspect)}。"+explanation)
            for clue_id in ids:w.effect(state,"A","share:"+clue_id)
            for actor in w.NPCS:
                if not w.chat_for(state,actor):self.role_turn(state,actor,call,"final_response")
        else:state["outcome"]="unresolved"
        state["evaluation"]=evaluation
        state["social"]={"beliefs":[{"name":w.name(state,c),"suspect":w.name(state,state["beliefs"][c]["suspect"]) if state["beliefs"][c] and state["beliefs"][c]["suspect"] else "尚无结论","trust":state["trust"][c]} for c in w.NPCS],
                         "disclosures":sum(e["kind"]=="share" for e in state["events"])}
        def validate(out):text(out["title"],120);text(out["narrative"],3000)
        ending,_=call("ending","case_ending",None,{"outcome":state["outcome"],"evaluation":evaluation,"social":state["social"],
                     "solution":state["case"]["solution"],"history":state["case"]["history"],"player_experience":state["observations"]["A"][-30:]},validate,"A")
        state["ending"]=ending;state["phase"]="ended"
        for chat in state["chats"].values():
            if chat["status"]=="active":w.close_chat(state,chat,"结束了本次私聊")
        event(state,"case_closed","A",outcome=state["outcome"])
