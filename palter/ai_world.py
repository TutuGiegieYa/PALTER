"""Shared-world effects for real AI controllers; no authored character schedule."""

from copy import deepcopy
import time

from .engine import RuleError, event, initial_state
from . import scenario as legacy

CATEGORIES = {
    "mystery": "悬疑推理", "drama": "关系与秘密", "negotiation": "阵营与谈判",
    "survival": "冒险与求生", "uncanny": "惊悚与异象", "exploration": "谜题与探索",
}
ADJACENCY = {"hall": ["study", "courtyard"], "study": ["hall"], "courtyard": ["hall"]}
CUES = {"pause": "说话时短暂停顿了一下", "fingers": "手指轻轻绞在一起", "gaze": "目光短暂移向一旁"}


def blank(game_id, category):
    state = initial_state(game_id)
    state.update(mode="ai", category=category, title="正在生成故事", introduction="", setup=None,
                 profiles={}, memory={}, relationships={}, chats={}, invitations=[], round=0,
                 public_turns={c: 0 for c in "ABC"}, obligations={c: False for c in "ABC"},
                 deadline=6, world_effects=[], ending=None, thoughts={c: [] for c in "ABC"})
    return state


def name(state, role):
    return state.get("profiles", {}).get(role, {}).get("name", "角色 "+role)


def rooms(state):
    setup = state.get("setup") or {}
    return setup.get("rooms", legacy.ROOMS)


def item_name(state):
    return (state.get("setup") or {}).get("item", {}).get("name", "交接信")


def chat_for(state, role):
    return next((c for c in state["chats"].values() if c["status"] == "active" and role in c["participants"]), None)


def note(state, role, source, text, channel="public", force=False, **learned):
    chat = chat_for(state, role)
    if not force and chat and channel != chat["id"]:
        return
    records = state["observations"][role]
    records.append({"id": f"{role}-o{len(records)+1:04d}", "event_id": source["id"],
                    "beat": state["beat"], "round": state["round"], "text": text, "channel": channel})
    state["knowledge"][role].update(learned)


def current_scene(state, role, source):
    place = state["locations"][role]
    note(state, role, source, rooms(state)[place]["description"])
    if place=="hall" and "courtyard_closed" in state["world_effects"]:
        note(state,role,source,"你现在看到通往庭院的路线已关闭。")
    for other, location in state["locations"].items():
        if other != role and location == place and not chat_for(state, role):
            state["knowledge"][role]["seen"][other] = {"location": place, "beat": state["beat"]}
            note(state, role, source, f"{name(state,other)}也在这里。")


def initialize(state, setup):
    state["setup"] = deepcopy(setup)
    state["profiles"] = deepcopy(setup["roles"])
    state["letter_custody"] = setup["custody"]
    state["locations"] = {c: setup["roles"][c]["location"] for c in "ABC"}
    for c in "ABC":
        state["knowledge"][c]["deadline"]=6
        state["memory"][c] = {"summary": "；".join(setup["roles"][c]["memories"]), "sources": []}
        state["relationships"][c] = {other: {"description": description, "trust": 0, "experiences": []}
                                      for other, description in setup["roles"][c]["relationships"].items()}
        if setup["custody"] == c:
            state["knowledge"][c]["letter_location"] = c
    state["phase"] = "reading"


def start(state):
    state["phase"] = "active"
    source = event(state, "play_started", None)
    for c in "ABC":
        current_scene(state,c,source)
        if state["letter_custody"] == c:
            note(state,c,source,f"{item_name(state)}现在由你随身保管。",force=True,letter_location=c)


def audience(state, actor, channel="public"):
    if channel == "public":
        return [c for c in "ABC" if not chat_for(state,c)]
    chat = state["chats"].get(channel)
    return list(chat["participants"]) if chat and chat["status"] == "active" and actor in chat["participants"] else []


def speak(state, actor, text, target=None, gesture=None, channel=None):
    active_chat = chat_for(state,actor)
    channel = channel or (active_chat["id"] if active_chat else "public")
    recipients = audience(state,actor,channel)
    if not recipients:
        raise RuleError("当前谈话已经结束，请刷新。")
    source = event(state,"gesture" if gesture else "speech",actor,target,
                   text=text,gesture=gesture,channel=channel,recipients=recipients,locations=deepcopy(state["locations"]))
    for c in recipients:
        note(state,c,source,f"{name(state,actor)}：{text}" if not gesture else f"{name(state,actor)}{text}。",channel=channel,force=True)
    if text and not gesture:
        state["public_turns"][actor] = state["round"]
        state["obligations"][actor] = False
    elif gesture:
        state["obligations"][actor] = False
    if target in recipients and target != actor and ("?" in text or "？" in text):
        state["obligations"][target] = True
    if active_chat:
        active_chat["turns"].append({"event_id": source["id"], "speaker":actor,"text":text})
    return source


def invite(state, actor, target):
    if actor == target or target not in "ABC" or chat_for(state,actor) or chat_for(state,target):
        raise RuleError("对方或你现在不在公共讨论中。")
    if any(i["status"]=="pending" and i["from"]==actor and i["to"]==target for i in state["invitations"]):
        raise RuleError("这份邀请仍在等待答复。")
    source = speak(state,actor,f"我想和{name(state,target)}单独聊一聊，你愿意吗？",target,channel="public")
    invitation = {"id":f"invite-{len(state['invitations'])+1}","from":actor,"to":target,"status":"pending","event_id":source["id"]}
    state["invitations"].append(invitation)
    return invitation


def answer_invitation(state, actor, invitation_id, accept):
    invitation = next((i for i in state["invitations"] if i["id"]==invitation_id and i["to"]==actor and i["status"]=="pending"),None)
    if not invitation or chat_for(state,actor) or chat_for(state,invitation["from"]):
        raise RuleError("这份邀请已不可接受。")
    speak(state,actor,"我同意这次私聊。" if accept else "我现在不方便单独聊。",invitation["from"],channel="public")
    invitation["status"] = "accepted" if accept else "declined"
    if accept:
        chat_id=f"private-{len(state['chats'])+1}"
        participants=[invitation["from"],actor]
        state["chats"][chat_id]={"id":chat_id,"participants":participants,"status":"active","turns":[],
                                "expires":state.get("_operation_time",time.time())+90,"max_turns":4,"baseline":{c:deepcopy(state["profiles"][c]) for c in participants}}
        for i in state["invitations"]:
            if i["status"]=="pending" and any(c in participants for c in (i["from"],i["to"])):
                i["status"]="expired"


def close_chat(state, chat_id, reason="结束了私聊"):
    chat=state["chats"].get(chat_id)
    if not chat or chat["status"]!="active":return
    participants=list(chat["participants"])
    chat["status"]="closed"
    source=event(state,"private_closed",None,chat_id,reason=reason,participants=participants)
    for c in "ABC":
        if c in participants or not chat_for(state,c):
            note(state,c,source,f"{'、'.join(name(state,p) for p in participants)}{reason}。",force=c in participants)
    for c in participants:
        current_scene(state,c,source)


def expire_chats(state):
    for chat in list(state["chats"].values()):
        if chat["status"]=="active" and (len(chat["turns"])>=chat["max_turns"] or state.get("_operation_time",time.time())>=chat["expires"]):
            close_chat(state,chat["id"],"的私聊已达到上限，返回公共讨论")


def choices(state, actor, physical=True):
    chat=chat_for(state,actor)
    if chat:return [{"id":"wait","label":"继续交谈"},{"id":f"end:{chat['id']}","label":"结束私聊"}]
    result=[{"id":"wait","label":"等待"}]
    loc=state["locations"][actor]
    if physical:
        for destination in ADJACENCY[loc]:
            if destination=="courtyard" and "courtyard_closed" in state["world_effects"]:continue
            result.append({"id":f"move:{destination}","label":f"前往{rooms(state)[destination]['name']}"})
        result.append({"id":f"inspect:{'drawer' if loc=='study' else loc}","label":"查看书桌抽屉" if loc=="study" else "查看周围"})
        if state["knowledge"][actor]["letter_location"]=="drawer" and loc=="study":
            result.append({"id":"take:letter","label":f"拿取已找到的{item_name(state)}"})
        if state["letter_custody"]==actor and loc=="study":
            result.append({"id":"place:drawer","label":"把随身物品放入抽屉"})
        if actor=="A":
            for c in "BC":
                if state["locations"][c]==loc and not chat_for(state,c):result.append({"id":f"follow:{c}","label":f"跟随{name(state,c)}"})
    for c in "ABC":
        if c!=actor and not chat_for(state,c):result.append({"id":f"invite:{c}","label":f"公开邀请{name(state,c)}私聊"})
    for i in state["invitations"]:
        if i["status"]=="pending" and i["to"]==actor:
            result.extend([{"id":f"accept:{i['id']}","label":"同意私聊"},{"id":f"decline:{i['id']}","label":"拒绝私聊"}])
    return result


def physical_effect(state, actor, action_id):
    action,_,target=action_id.partition(":")
    loc=state["locations"][actor]
    if action=="invite":invite(state,actor,target);return None
    if action in ("accept","decline"):answer_invitation(state,actor,target,action=="accept");return None
    if action=="end":close_chat(state,target);return None
    if action=="move":
        if target not in ADJACENCY[loc] or (target=="courtyard" and "courtyard_closed" in state["world_effects"]):
            raise RuleError("当前路线不能通行。")
        source=event(state,"move",actor,target,origin=loc,destination=target)
        for c,p in state["locations"].items():
            if c!=actor and p==loc and not chat_for(state,c):
                note(state,c,source,f"{name(state,actor)}离开{rooms(state)[loc]['name']}，走向{rooms(state)[target]['name']}。")
                state["knowledge"][c]["seen"][actor]={"location":target,"beat":state["beat"],"departed":True}
        state["locations"][actor]=target
        note(state,actor,source,f"你来到{rooms(state)[target]['name']}。",force=True)
        for c,p in state["locations"].items():
            if c!=actor and p==target and not chat_for(state,c):
                note(state,c,source,f"{name(state,actor)}来到这里。")
                state["knowledge"][c]["seen"][actor]={"location":target,"beat":state["beat"]}
        current_scene(state,actor,source)
        return source
    source=event(state,action,actor,target)
    if action=="inspect":
        if loc=="study" and target=="drawer":
            state["drawer_open"]=True
            found=state["letter_custody"]=="drawer"
            note(state,actor,source,f"你打开抽屉，看见{item_name(state)}。" if found else "你查看了抽屉，没有找到目标物品。",force=True,letter_location="drawer" if found else None)
            for c,p in state["locations"].items():
                if c!=actor and p==loc:note(state,c,source,f"{name(state,actor)}低头查看书桌抽屉。")
        else:note(state,actor,source,"你查看了周围，没有找到目标物品。",force=True)
    elif action=="take":
        if loc!="study" or state["letter_custody"]!="drawer":
            note(state,actor,source,"你检查了已知位置，物品已经不在那里。",force=True,letter_location=None)
            source["facts"]["outcome"]="unavailable"
        else:
            state["letter_custody"]=actor
            note(state,actor,source,f"你拿起并收好了{item_name(state)}。",force=True,letter_location=actor)
            for c,p in state["locations"].items():
                if c!=actor and p==loc:note(state,c,source,f"{name(state,actor)}从抽屉拿起一件物品，收在身上。")
    elif action=="place":
        if loc!="study" or state["letter_custody"]!=actor:raise RuleError("你现在没有可放置的目标物品。")
        state["letter_custody"]="drawer"
        note(state,actor,source,f"你把{item_name(state)}放进抽屉。",force=True,letter_location="drawer")
        for c,p in state["locations"].items():
            if c!=actor and p==loc:note(state,c,source,f"{name(state,actor)}往抽屉里放入一件物品。")
    elif action=="wait":note(state,actor,source,"你暂时留在原处。",force=True)
    else:raise RuleError("这个动作尚不在可执行范围内。")
    return source


def role_context(state, actor, physical=True):
    chat=chat_for(state,actor)
    return {"actor":actor,"beat":state["beat"],"round":state["round"],"deadline":state["knowledge"][actor].get("deadline",6),
            "location":state["locations"][actor],"rooms":rooms(state),
            "observations":deepcopy(state["observations"][actor][-18:]),
            "memory":deepcopy(state["memory"][actor]),"relationships":deepcopy(state["relationships"][actor]),
            "thoughts":deepcopy(state["thoughts"][actor][-3:]),
            "inventory":[item_name(state)] if state["letter_custody"]==actor else [],
            "allowed_choices":choices(state,actor,physical),
            "must_respond":state["obligations"][actor],"must_speak":state["round"]-state["public_turns"][actor]>=3,
            "channel":chat["id"] if chat else "public",
            "private_turns":deepcopy(chat["turns"][-4:]) if chat else [],
            "invitations":[deepcopy(i) for i in state["invitations"] if i["status"]=="pending" and i["to"]==actor]}


def ai_view(state):
    view={"id":state["id"],"revision":state["revision"],"phase":state["phase"],"archived":state["archived"],
          "beat":state["beat"],"deadline":state["knowledge"]["A"].get("deadline",6),"mode":"ai","title":state["title"],
          "introduction":state["introduction"],"category":state["category"],
          "map":[{"id":k,"name":v["name"],"neighbors":ADJACENCY[k]} for k,v in rooms(state).items()],
          "briefing":[],"observations":[],"scene":None,"inventory":[],"options":[],"outcome":None,
          "invitations":[],"invite_targets":[],"chat":None,"memory":None,"relationships":None,"must_speak":False,"must_respond":False}
    view["cast"]=[{"id":c,"name":name(state,c)} for c in "ABC"]
    view["player_name"]=name(state,"A")
    view["goal"]=state.get("profiles",{}).get("A",{}).get("goal","找到目标物品并带回公共地点。")
    if state["setup"] and state["phase"]!="introduction":
        p=state["profiles"]["A"]
        view["briefing"]=[f"你是{p['name']}。{p['persona']}",f"你的目标：{p['goal']}",*p["memories"]]
    if state["phase"] not in ("active","paused","ended"):return view
    loc=state["locations"]["A"]
    chat=chat_for(state,"A")
    people=[] if chat else [{"id":c,"name":name(state,c)} for c,p in state["locations"].items() if c!="A" and p==loc]
    seen=[] if chat else [{"id":c,"name":name(state,c),**v} for c,v in state["knowledge"]["A"]["seen"].items() if c not in {p["id"] for p in people}]
    view["scene"]={"id":loc,"name":rooms(state)[loc]["name"],"description":"你正处于私聊中，未接收外部发生的事情。" if chat else rooms(state)[loc]["description"],
                   "people":people,"last_seen":seen,"objects":[] if chat else (["书桌","抽屉"] if loc=="study" else ["周围环境"])}
    view["observations"]=deepcopy(state["observations"]["A"])
    view["memory"]=deepcopy(state["memory"]["A"])
    view["relationships"]=deepcopy(state["relationships"]["A"])
    view["must_speak"]=state["round"]-state["public_turns"]["A"]>=3
    view["must_respond"]=state["obligations"]["A"]
    if state["letter_custody"]=="A":view["inventory"]=[{"id":"letter","name":item_name(state),"description":state["setup"]["item"]["description"]}]
    if state["phase"]=="active" and not state["archived"]:
        for action,label in [("move","移动"),("inspect","查看"),("take","拿取"),("place","放置"),("follow","跟随"),("wait","等待")]:
            opts=[{"id":choice["id"].partition(":")[2],"label":choice["label"]} for choice in choices(state,"A") if choice["id"].partition(":")[0]==action]
            view["options"].append({"action":action,"label":label,"targets":opts,"reason":"当前没有你能够执行的目标。"})
    view["invitations"]=[{"id":i["id"],"from":i["from"],"name":name(state,i["from"])} for i in state["invitations"] if i["to"]=="A" and i["status"]=="pending"]
    view["invite_targets"]=[o["id"].partition(":")[2] for o in choices(state,"A") if o["id"].startswith("invite:")]
    if chat:
        partner=next(c for c in chat["participants"] if c!="A")
        view["chat"]={"id":chat["id"],"partner_id":partner,"partner":name(state,partner),"turns":deepcopy(chat["turns"]),"limit":chat["max_turns"],"expires":chat["expires"]}
    if state["outcome"]:
        view["outcome"]={"id":state["outcome"],"title":(state.get("ending") or {}).get("title",legacy.OUTCOMES[state["outcome"]]["title"]),
                         "text":(state.get("ending") or {}).get("narrative",legacy.OUTCOMES[state["outcome"]]["text"])}
    return view
