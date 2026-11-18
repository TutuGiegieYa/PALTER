"""Immutable cases and recipient-scoped investigation effects, without act timers."""

from copy import deepcopy
import time

from .engine import RuleError, event
from .storage import fingerprint

ACTORS = "ABCD"
NPCS = "BCD"
ASPECTS = ("identity", "time", "method")


def prose(value, limit=1600):
    if not isinstance(value, str) or not value.strip() or len(value)>limit:
        raise ValueError("invalid case text")


def validate_case(case):
    """Check executable structure and provenance; semantic quality needs live QA."""
    for key in ("title", "public_briefing", "victim"):
        prose(case[key])
    if set(case["rooms"])!={"r1", "r2", "r3"} or set(case["roles"])!=set(ACTORS):
        raise ValueError("case roster or locations")
    if len(set([case['victim'],*[r['name'] for r in case['roles'].values()]]))!=5:
        raise ValueError("victim and living cast must be distinct")
    for room in case["rooms"].values():
        prose(room["name"],80); prose(room["description"],800)
    history=case["history"]
    if not isinstance(history,list) or not 6<=len(history)<=16:
        raise ValueError("case history size")
    facts={h["id"] for h in history}
    if len(facts)!=len(history):raise ValueError("duplicate history")
    for h in history:
        prose(h["id"],40); prose(h["time"],80); prose(h["text"],800)
    for actor,role in case["roles"].items():
        for key in ("name","persona","goal","cover_story"):prose(role[key],1200)
        if role["location"] not in case["rooms"]:raise ValueError("role location")
        if not isinstance(role["memories"],list) or not 1<=len(role["memories"])<=5:raise ValueError("role memories")
        for memory in role["memories"]:prose(memory,800)
        if not isinstance(role["knows"],list) or not set(role["knows"])<=facts:raise ValueError("role knowledge")
        if set(role["relationships"])!=set(ACTORS)-{actor}:raise ValueError("role relationships")
        for relation in role["relationships"].values():prose(relation,500)
    clues=case["clues"]
    if not isinstance(clues,list) or not 8<=len(clues)<=10:raise ValueError("evidence count")
    ids={c["id"] for c in clues}
    if len(ids)!=len(clues):raise ValueError("duplicate evidence")
    for clue in clues:
        for key in ("id","title","target","observation","source","time"):prose(clue[key],1200)
        if clue["location"] not in case["rooms"]:raise ValueError("evidence location")
        if not isinstance(clue["facts"],list) or not clue["facts"] or not set(clue["facts"])<=facts:
            raise ValueError("evidence provenance")
        if clue["kind"] not in ("last_alive","first_dead","presence","exclusion","mechanism","motive","context"):
            raise ValueError("evidence role")
        if clue["kind"] in ("last_alive","first_dead") and (type(clue["minute"]) is not int or not 0<=clue["minute"]<1440):
            raise ValueError("objective time anchor")
    solution=case["solution"]
    if solution["killer"] not in NPCS:raise ValueError("case killer")
    crime=next((h for h in history if h["id"]==solution["crime_fact"]),None)
    if not crime or solution["crime_fact"] not in case["roles"][solution["killer"]]["knows"]:
        raise ValueError("killer must know the crime")
    if any(solution["crime_fact"] in case["roles"][c]["knows"] for c in ACTORS if c!=solution["killer"]):
        raise ValueError("initial solution leak")
    window=solution["window"]
    if not isinstance(window,list) or len(window)!=2 or any(type(n) is not int for n in window) or not 0<=window[0]<window[1]<1440:
        raise ValueError("case time window")
    if type(crime.get("minute")) is not int or not window[0]<=crime["minute"]<=window[1]:raise ValueError("crime outside anchored window")
    for key in ("time","method","motive","reconstruction"):prose(solution[key],2500)
    if set(case["proofs"])!=set(ASPECTS):raise ValueError("proof aspects")
    for aspect,alternatives in case["proofs"].items():
        if not isinstance(alternatives,list) or not 1<=len(alternatives)<=3:raise ValueError("proof alternatives")
        for route in alternatives:
            if not isinstance(route,list) or len(set(route))!=len(route) or not set(route)<=ids or len(route)<(2 if aspect=="identity" else 1):
                raise ValueError("invalid evidence combination")
            records=[c for c in clues if c["id"] in route];kinds={c["kind"] for c in records}
            if aspect=="identity" and not {"presence","exclusion"}<=kinds:raise ValueError("identity needs positive presence and exclusions")
            if aspect=="method" and "mechanism" not in kinds:raise ValueError("method needs mechanism evidence")
            if aspect=="time":
                lower=[c["minute"] for c in records if c["kind"]=="last_alive"]
                upper=[c["minute"] for c in records if c["kind"]=="first_dead"]
                if not lower or not upper or [max(lower),min(upper)]!=window:raise ValueError("time proof lacks matching objective bounds")


def blank(identifier):
    return {"id":identifier,"mode":"ai","gameplay":"investigation","revision":0,
            "phase":"introduction","archived":False,"beat":0,"round":0,"outcome":None,
            "title":"正在准备案件","introduction":"","case":None,"case_hash":None,
            "events":[],"observations":{c:[] for c in ACTORS},"known":{c:[] for c in ACTORS},
            "locations":{},"memory":{c:"" for c in ACTORS},"thoughts":{c:[] for c in ACTORS},
            "trust":{c:0 for c in NPCS},"beliefs":{c:None for c in NPCS},
            "chats":{},"invitations":[],"notebook":{"text":"","evidence_ids":[]},
            "ending":None,"assessments":[],"obligations":{c:False for c in ACTORS}}


def initialize(state,case):
    validate_case(case)
    state["case"]=deepcopy(case);state["case_hash"]=fingerprint(case)
    state["title"]=case["title"];state["phase"]="reading"
    state["locations"]={c:r["location"] for c,r in case["roles"].items()}
    state["memory"]={c:"；".join(r["memories"]) for c,r in case["roles"].items()}


def name(state,actor):return state["case"]["roles"][actor]["name"]
def chat_for(state,actor):return next((c for c in state["chats"].values() if c["status"]=="active" and actor in c["participants"]),None)
def audience(state,actor):
    chat=chat_for(state,actor)
    return chat["participants"] if chat else [c for c in ACTORS if not chat_for(state,c)]


def note(state,actor,source,text,kind="observation",**extra):
    records=state["observations"][actor]
    records.append({"id":f"{actor}-o{len(records)+1:04d}","event_id":source["id"],
                    "beat":state["beat"],"text":text,"kind":kind,**extra})


def clue_view(clue):
    result={k:deepcopy(clue[k]) for k in ("id","title","target","location","observation","time")}
    # The author's hidden causal origin is not a player's acquired provenance.
    result["source"]=clue["target"]
    if clue.get("kind") in ("last_alive","first_dead"):
        result["time"]=f"{clue['minute']//60:02d}:{clue['minute']%60:02d}"
    return result


def acquire(state,actor,clue_id,source,via):
    clue=next(c for c in state["case"]["clues"] if c["id"]==clue_id)
    if clue_id not in state["known"][actor]:
        state["known"][actor].append(clue_id)
        note(state,actor,source,clue["observation"],"evidence",evidence_id=clue_id,via=via)


def speak(state,actor,words,target=None,kind="testimony"):
    chat=chat_for(state,actor);recipients=audience(state,actor)
    source=event(state,kind,actor,target,text=words,recipients=list(recipients),locations=deepcopy(state["locations"]),channel=chat["id"] if chat else "public")
    for recipient in recipients:
        note(state,recipient,source,words,kind,speaker=actor,speaker_name=name(state,actor),channel=source["facts"]["channel"])
    if target in recipients and target!=actor and ("？" in words or "?" in words):state["obligations"][target]=True
    state["obligations"][actor]=False
    if chat:chat["turns"].append({"event_id":source["id"],"speaker":actor,"text":words})
    return source


def close_chat(state,chat,reason="结束了私聊"):
    chat["status"]="closed"
    source=event(state,"private_closed",None,chat["id"])
    for actor in ACTORS:
        if actor in chat["participants"] or not chat_for(state,actor):
            note(state,actor,source,"、".join(name(state,c) for c in chat["participants"])+reason+"。")


def expire(state):
    now=state.get("_operation_time",time.time())
    for chat in state["chats"].values():
        if chat["status"]=="active" and (len(chat["turns"])>=8 or now>=chat["expires"]):close_chat(state,chat,"的私聊已结束")


def choices(state,actor):
    chat=chat_for(state,actor)
    options=[{"id":"wait","label":"留意其他人的行动"}]
    if chat:options.append({"id":"end_private","label":"结束私聊"})
    else:
        options += [{"id":"move:"+r,"label":"前往"+room["name"]} for r,room in state["case"]["rooms"].items() if r!=state["locations"][actor]]
        options += [{"id":"inspect:"+c["id"],"label":"检查"+c["target"]} for c in state["case"]["clues"] if c["location"]==state["locations"][actor] and c["id"] not in state["known"][actor]]
        pending={i['to'] for i in state['invitations'] if i['from']==actor and i['status']=='pending'}
        options += [{"id":"invite:"+c,"label":"邀请"+name(state,c)+"私聊"} for c in ACTORS if c!=actor and not chat_for(state,c) and c not in pending]
        for invitation in state["invitations"]:
            if invitation["status"]=="pending" and invitation["to"]==actor:
                options += [{"id":kind+":"+invitation["id"],"label":label} for kind,label in (("accept","同意私聊"),("decline","拒绝私聊"))]
    options += [{"id":"share:"+c["id"],"label":"出示"+c["title"]} for c in state["case"]["clues"] if c["id"] in state["known"][actor]]
    return options


def effect(state,actor,choice):
    if choice not in {c["id"] for c in choices(state,actor)}:raise RuleError("当前无法执行这个行动。")
    kind,_,target=choice.partition(":")
    if kind=="invite":
        if any(i["status"]=="pending" and i["from"]==actor and i["to"]==target for i in state["invitations"]):raise RuleError("对方尚未回复邀请。")
        source=speak(state,actor,f"{name(state,target)}，我想和你单独聊聊，可以吗？",target)
        state["invitations"].append({"id":f"invite-{len(state['invitations'])+1}","from":actor,"to":target,"status":"pending","event_id":source["id"]})
        return source
    if kind in ("accept","decline"):
        invitation=next(i for i in state["invitations"] if i["id"]==target)
        source=speak(state,actor,"我同意单独聊聊。" if kind=="accept" else "我想先留在这里。",invitation["from"])
        invitation["status"]=kind
        if kind=="accept":
            cid=f"private-{len(state['chats'])+1}";participants=[invitation["from"],actor]
            state["chats"][cid]={"id":cid,"participants":participants,"status":"active","turns":[],"expires":state.get("_operation_time",time.time())+300,
                                   "baseline":{c:baseline(state,c) for c in participants}}
            for i in state["invitations"]:
                if i["status"]=="pending" and any(c in participants for c in (i["from"],i["to"])):i["status"]="expired"
        return source
    if kind=="end_private":
        close_chat(state,chat_for(state,actor));return state["events"][-1]
    source=event(state,kind,actor,target)
    if kind=="inspect":acquire(state,actor,target,source,"亲自检查")
    elif kind=="share":
        for recipient in audience(state,actor):acquire(state,recipient,target,source,name(state,actor)+"出示")
        for recipient in audience(state,actor):
            note(state,recipient,source,name(state,actor)+"出示了"+next(c["title"] for c in state["case"]["clues"] if c["id"]==target)+"。")
    elif kind=="move":
        origin=state["locations"][actor];state["locations"][actor]=target
        for recipient in ACTORS:
            if recipient==actor or (not chat_for(state,recipient) and state["locations"][recipient] in (origin,target)):
                note(state,recipient,source,name(state,actor)+"前往了"+state["case"]["rooms"][target]["name"]+"。")
    return source


def baseline(state,actor):
    profile=state["case"]["roles"][actor]
    return {"actor":actor,"profile":deepcopy(profile),"experienced_facts":[deepcopy(h) for h in state["case"]["history"] if h["id"] in profile["knows"]],
            "cast":{c:r["name"] for c,r in state["case"]["roles"].items()}}


def context(state,actor):
    return {"actor":actor,"location":state["locations"][actor],"rooms":deepcopy(state["case"]["rooms"]),
            "evidence":[clue_view(c) for c in state["case"]["clues"] if c["id"] in state["known"][actor]],
            "observations":deepcopy(state["observations"][actor][-24:]),"memory":state["memory"][actor],
            "thoughts":state["thoughts"][actor][-3:],"choices":choices(state,actor),
            "trust_in_player":state["trust"].get(actor,0),"must_respond":state["obligations"][actor],"recipients":audience(state,actor),
            "invitations":[deepcopy(i) for i in state["invitations"] if i["to"]==actor and i["status"]=="pending"]}


def view(state):
    result={k:deepcopy(state[k]) for k in ("id","mode","gameplay","revision","phase","archived","beat","title","introduction","outcome")}
    result.update(briefing=[],cast=[],rooms=[],evidence=[],observations=[],notebook=deepcopy(state["notebook"]),invitations=[],chat=None,options=[],scene=None)
    if not state["case"]:return result
    case=state["case"];player=case["roles"]["A"]
    experienced=[h["time"]+"："+h["text"] for h in case["history"] if h["id"] in player["knows"]]
    relations=["你与"+name(state,c)+"："+relation for c,relation in player['relationships'].items()]
    result.update(cast=[{"id":c,"name":r["name"]} for c,r in case["roles"].items()],player_name=player["name"],
                  briefing=list(dict.fromkeys([case["public_briefing"],player["persona"],player["goal"],*relations,*player["memories"],*experienced])),
                  rooms=[{"id":r,"name":p["name"]} for r,p in case["rooms"].items()])
    if state["phase"]=="reading":return result
    loc=state["locations"]["A"];chat=chat_for(state,"A")
    by_id={c["id"]:c for c in case["clues"]}
    result.update(scene={"id":loc,**case["rooms"][loc]},evidence=[clue_view(by_id[key]) for key in state["known"]["A"]],
                  observations=deepcopy(state["observations"]["A"]),memory=state["memory"]["A"],must_respond=state["obligations"]["A"],
                  invitations=[deepcopy(i) for i in state["invitations"] if i["to"]=="A" and i["status"]=="pending"])
    if state["phase"]=="active" and not state["archived"]:result["options"]=choices(state,"A")
    if chat:result["chat"]={"id":chat["id"],"partner":next(name(state,c) for c in chat["participants"] if c!="A"),"participants":chat["participants"],"turns":deepcopy(chat["turns"])}
    if state["phase"]=="ended":
        result["ending"]=deepcopy(state["ending"])
        result["resolution"]={"killer":name(state,case["solution"]["killer"]),**{k:v for k,v in case["solution"].items() if k!="killer"},
                              "history":deepcopy(case["history"]),"proofs":deepcopy(case["proofs"]),"all_evidence":[clue_view(c) for c in case["clues"]],
                              "evaluation":deepcopy(state.get("evaluation",{})),"social":deepcopy(state.get("social",{}))}
    return result
