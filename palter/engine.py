"""Deterministic transitions and event-derived, recipient-scoped knowledge."""

from copy import deepcopy

from . import scenario as s


class RuleError(ValueError):
    def __init__(self, message, code="invalid_action"):
        super().__init__(message)
        self.code = code


def initial_state(game_id):
    state = {
        "id": game_id, "fixture_version": s.VERSION, "revision": 0,
        "phase": "introduction", "archived": False, "beat": 0,
        "locations": {"A": "hall", "B": "hall", "C": "courtyard"},
        "letter_custody": "B", "drawer_open": False,
        "events": [], "observations": {c: [] for c in s.PEOPLE},
        "knowledge": {c: {"seen": {}, "letter_location": None} for c in s.PEOPLE},
        "outcome": None,
    }
    # Initial private knowledge is data preparation, not an autonomous action.
    state["knowledge"]["B"]["letter_location"] = "B"
    return state


def event(state, kind, actor, target=None, **facts):
    item = {"id": f"e{len(state['events']) + 1:04d}", "definition_version": s.VERSION,
            "beat": state["beat"], "kind": kind, "actor": actor,
            "target": target, "state": "completed", "facts": facts}
    state["events"].append(item)
    return item


def observe(state, recipient, source, text, **learned):
    entries = state["observations"][recipient]
    entries.append({"id": f"{recipient}-o{len(entries) + 1:04d}",
                    "event_id": source["id"], "beat": state["beat"], "text": text})
    if "letter_location" in learned:
        state["knowledge"][recipient]["letter_location"] = learned["letter_location"]


def see_scene(state, recipient, source):
    location = state["locations"][recipient]
    observe(state, recipient, source, s.ROOMS[location]["description"])
    for character, place in state["locations"].items():
        if character != recipient and place == location:
            state["knowledge"][recipient]["seen"][character] = {"location": location, "beat": state["beat"]}
            observe(state, recipient, source, f"{s.PEOPLE[character]}也在{s.ROOMS[location]['name']}。")


def move(state, actor, destination):
    origin = state["locations"][actor]
    source = event(state, "move", actor, destination, origin=origin, destination=destination)
    for recipient, place in state["locations"].items():
        if recipient != actor and place == origin:
            observe(state, recipient, source, f"{s.PEOPLE[actor]}离开{s.ROOMS[origin]['name']}，走向{s.ROOMS[destination]['name']}。")
            state["knowledge"][recipient]["seen"][actor] = {"location": destination, "beat": state["beat"], "departed": True}
    state["locations"][actor] = destination
    observe(state, actor, source, f"你从{s.ROOMS[origin]['name']}来到{s.ROOMS[destination]['name']}。")
    for recipient, place in state["locations"].items():
        if recipient != actor and place == destination:
            observe(state, recipient, source, f"{s.PEOPLE[actor]}来到{s.ROOMS[destination]['name']}。")
            state["knowledge"][recipient]["seen"][actor] = {"location": destination, "beat": state["beat"]}
    see_scene(state, actor, source)
    return source


def scripted_turn(state):
    """The fixture's explicit ordering; never substitutes a new strategy."""
    beat = state["beat"]
    if beat == 1 and state["locations"]["B"] == "hall":
        return move(state, "B", "study")
    if beat == 2 and state["locations"]["B"] == "study" and state["letter_custody"] == "B":
        state["letter_custody"] = "drawer"
        state["drawer_open"] = False
        source = event(state, "place", "B", "drawer", item="letter", custody="drawer")
        observe(state, "B", source, "你把交接信放进书桌抽屉，合上抽屉。", letter_location="drawer")
        for recipient in ("A", "C"):
            if state["locations"][recipient] == "study":
                observe(state, recipient, source, "林舟伸手动了动书桌的抽屉，随后将它合上。你看不清经手的物件。")
        return source
    if beat == 3 and state["locations"]["B"] == "study":
        return move(state, "B", "hall")
    return event(state, "wait", "B", outcome="remained")


def validate_action(state, action, target):
    location = state["locations"]["A"]
    if action == "move":
        if target not in s.ROOMS[location]["neighbors"]:
            raise RuleError("请从当前地点相连的路线中选择目的地。")
    elif action == "inspect":
        if target != ("drawer" if location == "study" else location):
            raise RuleError("请先到达能够查看这个目标的位置。")
    elif action == "take":
        known = state["knowledge"]["A"]["letter_location"]
        if target != "letter" or known != "drawer" or location != "study":
            raise RuleError("先确认物品的位置，并到达可以接触它的地方。")
    elif action == "follow":
        if target not in ("B", "C") or state["locations"].get(target) != location:
            raise RuleError("只能跟随此刻在你面前、能够观察到的人。")
    elif action == "wait":
        if target not in (None, ""):
            raise RuleError("等待不需要选择目标。")
    else:
        raise RuleError("这个版本只支持移动、查看、拿取、跟随和等待。")


def resolve_action(state, action, target):
    validate_action(state, action, target)
    start = state["locations"]["A"]
    state["beat"] += 1
    other_event = scripted_turn(state)
    result = "success"
    if action == "move":
        move(state, "A", target)
    elif action == "follow":
        if (other_event["kind"] == "move" and other_event["actor"] == target
                and other_event["facts"]["origin"] == start):
            move(state, "A", other_event["facts"]["destination"])
        else:
            source = event(state, "follow", "A", target, outcome="no_movement")
            observe(state, "A", source, "这段时间里，对方没有作出你能跟随的移动。这次跟随已结束。")
            result = "no_movement"
    elif action == "inspect":
        source = event(state, "inspect", "A", target)
        if target == "drawer":
            state["drawer_open"] = True
            present = state["letter_custody"] == "drawer"
            source["facts"]["contents"] = ["letter"] if present else []
            observe(state, "A", source,
                    "你打开抽屉，看见一封带有蓝色封口的交接信。信封仍然封着。" if present else "你打开抽屉查看，里面没有交接信。",
                    letter_location="drawer" if present else None)
            for recipient in ("B", "C"):
                if state["locations"][recipient] == "study":
                    observe(state, recipient, source, "周砚打开书桌的抽屉，低头查看。你看不清抽屉里的细节。")
        else:
            observe(state, "A", source, "你仔细查看了周围，没有发现可辨认的交接信。")
    elif action == "take":
        source = event(state, "take", "A", "letter")
        if state["letter_custody"] == "drawer":
            state["letter_custody"] = "A"
            observe(state, "A", source, "你从抽屉里拿起交接信，妥善收好。", letter_location="A")
            for recipient in ("B", "C"):
                if state["locations"][recipient] == "study":
                    observe(state, recipient, source, "周砚从书桌抽屉拿起一只信封，收在身上。")
        else:
            source["facts"]["outcome"] = "not_available"
            observe(state, "A", source, "你伸手查看，但那封信已经不在原来的位置。", letter_location=None)
            result = "failed"
    else:
        source = event(state, "wait", "A")
        observe(state, "A", source, "你留在原地等了一会儿。")
    if state["beat"] == s.DEADLINE:
        state["phase"] = "ended"
        if state["letter_custody"] == "A" and state["locations"]["A"] == "hall":
            outcome = "delivered"
        elif state["letter_custody"] == "A" or state["knowledge"]["A"]["letter_location"]:
            outcome = "incomplete"
        else:
            outcome = "not_found"
        state["outcome"] = outcome
        source = event(state, "meeting_started", None, outcome=outcome)
        observe(state, "A", source, s.OUTCOMES[outcome]["text"])
    return result


def transition(original, command):
    """Return a new state; a rejected request cannot partly mutate its input."""
    state = deepcopy(original)
    if state["archived"]:
        raise RuleError("这是一局已保存的记录，可以回顾或开始新局。", "read_only")
    kind = command.get("kind")
    phase = state["phase"]
    if kind == "confirm" and phase == "introduction":
        state["phase"] = "reading"
        result = "reading"
    elif kind == "ready" and phase == "reading":
        state["phase"] = "active"
        source = event(state, "play_started", None)
        for character in s.PEOPLE:
            see_scene(state, character, source)
        observe(state, "B", source, "交接信还在你的包里。", letter_location="B")
        result = "started"
    elif kind == "pause" and phase == "active":
        state["phase"] = "paused"
        result = "paused"
    elif kind == "resume" and phase == "paused":
        state["phase"] = "active"
        result = "resumed"
    elif kind == "action" and phase == "active":
        result = resolve_action(state, command.get("action"), command.get("target"))
    else:
        raise RuleError("当前阶段不能执行这项操作，请刷新后查看可用操作。", "wrong_phase")
    state["revision"] += 1
    return state, result


def options_for(state):
    if state["phase"] != "active" or state["archived"]:
        return []
    location = state["locations"]["A"]
    options = [{"action": "move", "label": "移动", "targets": [{"id": n, "label": s.ROOMS[n]["name"]} for n in s.ROOMS[location]["neighbors"]]}]
    options.append({"action": "inspect", "label": "查看", "targets": [{"id": "drawer" if location == "study" else location, "label": "书桌抽屉" if location == "study" else "当前地点"}]})
    take = state["knowledge"]["A"]["letter_location"] == "drawer" and location == "study"
    options.append({"action": "take", "label": "拿取", "targets": [{"id": "letter", "label": "交接信（已知位置）"}] if take else [], "reason": "发现并接近物品后可以拿取。"})
    people = [{"id": c, "label": s.PEOPLE[c]} for c, p in state["locations"].items() if c != "A" and p == location]
    options.append({"action": "follow", "label": "跟随", "targets": people, "reason": "身边有可观察的人时可以跟随一次移动。"})
    options.append({"action": "wait", "label": "等待", "targets": [{"id": "", "label": "留在原地"}]})
    return options


def player_view(state):
    """Only this explicit projection crosses the ordinary player boundary."""
    phase = state["phase"]
    view = {"id": state["id"], "revision": state["revision"], "phase": phase,
            "archived": state["archived"], "beat": state["beat"], "deadline": s.DEADLINE,
            "title": "失踪的交接信", "introduction": s.INTRODUCTION,
            "briefing": s.BRIEFING if phase != "introduction" else [],
            "map": [{"id": k, "name": v["name"], "neighbors": v["neighbors"]} for k, v in s.ROOMS.items()],
            "observations": [], "scene": None, "inventory": [], "options": [], "outcome": None}
    if phase in ("active", "paused", "ended"):
        location = state["locations"]["A"]
        present = [{"id": c, "name": s.PEOPLE[c]} for c, p in state["locations"].items() if c != "A" and p == location]
        visible_ids = {p["id"] for p in present}
        last_seen = [{"id": c, "name": s.PEOPLE[c], **known} for c, known in state["knowledge"]["A"]["seen"].items() if c not in visible_ids]
        view["scene"] = {"id": location, "name": s.ROOMS[location]["name"], "description": s.ROOMS[location]["description"], "people": present, "last_seen": last_seen,
                         "objects": ["书桌", "抽屉"] if location == "study" else ["长桌", "座钟"] if location == "hall" else ["石阶"]}
        view["observations"] = deepcopy(state["observations"]["A"])
        view["options"] = options_for(state)
        if state["letter_custody"] == "A":
            view["inventory"] = [{"id": "letter", "name": "交接信", "description": "带蓝色封口的信封，尚未拆开。"}]
        if state["outcome"]:
            view["outcome"] = {"id": state["outcome"], **s.OUTCOMES[state["outcome"]]}
    return view
