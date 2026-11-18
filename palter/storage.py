"""Atomic game persistence, ownership, receipts, and model-call reservations."""

from contextlib import contextmanager
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import re
import secrets
import sqlite3
import time

from .engine import RuleError, initial_state, player_view, transition


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def fingerprint(value):
    return hashlib.sha256(canonical(value).encode()).hexdigest()


def observation_context(view):
    return {"observations": view["observations"]}


class StoreError(ValueError):
    def __init__(self, message, status=400, code="invalid_request"):
        super().__init__(message)
        self.status, self.code = status, code


class Store:
    def __init__(self, path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        with self.transaction() as con:
            con.executescript("""
                CREATE TABLE IF NOT EXISTS sessions (
                    id TEXT PRIMARY KEY, csrf TEXT NOT NULL, active_game TEXT);
                CREATE TABLE IF NOT EXISTS games (
                    id TEXT PRIMARY KEY, owner TEXT NOT NULL, state TEXT NOT NULL,
                    created REAL NOT NULL);
                CREATE INDEX IF NOT EXISTS game_owner ON games(owner);
                CREATE TABLE IF NOT EXISTS game_members (
                    game_id TEXT NOT NULL, session_id TEXT NOT NULL, actor TEXT NOT NULL,
                    PRIMARY KEY(game_id,session_id), UNIQUE(game_id,actor));
                CREATE TABLE IF NOT EXISTS commands (
                    game_id TEXT NOT NULL, id TEXT NOT NULL, digest TEXT NOT NULL,
                    receipt TEXT NOT NULL, PRIMARY KEY(game_id, id));
                CREATE TABLE IF NOT EXISTS creations (
                    owner TEXT NOT NULL, id TEXT NOT NULL, digest TEXT NOT NULL,
                    game_id TEXT NOT NULL, PRIMARY KEY(owner, id));
                CREATE TABLE IF NOT EXISTS model_calls (
                    id TEXT PRIMARY KEY, game_id TEXT NOT NULL, command_id TEXT NOT NULL,
                    context_hash TEXT NOT NULL, status TEXT NOT NULL, model TEXT NOT NULL,
                    revision INTEGER NOT NULL,
                    prefix_hash TEXT NOT NULL, request_hash TEXT,
                    started REAL NOT NULL, latency_ms INTEGER, usage TEXT,
                    cost_upper_usd REAL, selected TEXT, error_code TEXT,
                    returned_model TEXT, UNIQUE(game_id, command_id));
            """)
            # An interrupted request may have been billed. Never replay it on startup.
            con.execute("UPDATE model_calls SET status='interrupted', error_code='process_interrupted' WHERE status='pending'")
        self.path.chmod(0o600)

    @contextmanager
    def transaction(self, write=True):
        con = sqlite3.connect(self.path, timeout=15, isolation_level=None)
        con.row_factory = sqlite3.Row
        try:
            con.execute("BEGIN IMMEDIATE" if write else "BEGIN")
            yield con
            if con.in_transaction:
                con.commit()
        except BaseException:
            if con.in_transaction:
                con.rollback()
            raise
        finally:
            con.close()

    def session(self, token=None):
        with self.transaction() as con:
            row = con.execute("SELECT * FROM sessions WHERE id=?", (token,)).fetchone() if token else None
            if row is None:
                token, csrf = secrets.token_urlsafe(32), secrets.token_urlsafe(32)
                con.execute("INSERT INTO sessions(id,csrf) VALUES (?,?)", (token, csrf))
                row = con.execute("SELECT * FROM sessions WHERE id=?", (token,)).fetchone()
            return dict(row)

    def require_session(self, token):
        with self.transaction(False) as con:
            row = con.execute("SELECT * FROM sessions WHERE id=?", (token,)).fetchone()
            if not row:
                raise StoreError("会话已失效，请刷新页面。", 401, "session_required")
            return dict(row)

    @staticmethod
    def command_id(value):
        if not isinstance(value, str) or not re.fullmatch(r"[A-Za-z0-9_-]{8,100}", value):
            raise StoreError("操作标识无效，请刷新后重试。")
        return value

    @staticmethod
    def load(con, owner, game_id):
        row = con.execute("SELECT state FROM games WHERE id=? AND (owner=? OR EXISTS (SELECT 1 FROM game_members m WHERE m.game_id=games.id AND m.session_id=?))", (game_id, owner, owner)).fetchone()
        if row is None:
            raise StoreError("没有找到这局记录。", 404, "not_found")
        return json.loads(row["state"])

    @staticmethod
    def save(con, state, previous):
        if previous.get("case") is not None and state.get("case")!=previous["case"]:
            raise RuntimeError("Established case changed")
        if state.get("case") is not None and fingerprint(state["case"])!=state.get("case_hash"):
            raise RuntimeError("Case fingerprint mismatch")
        # Existing occurrences and acquired observations cannot be rewritten.
        if state["events"][:len(previous["events"])] != previous["events"]:
            raise RuntimeError("Committed history changed")
        for char, observations in previous["observations"].items():
            if state["observations"][char][:len(observations)] != observations:
                raise RuntimeError("Committed observations changed")
        con.execute("UPDATE games SET state=? WHERE id=?", (canonical(state), state["id"]))

    def create_game(self, owner, command, factory=initial_state):
        if not {"command_id", "expected_game_id"} <= set(command) or set(command)-{"command_id","expected_game_id","category","humans","opening"}:
            raise StoreError("新局请求格式不正确。")
        command_id = self.command_id(command["command_id"])
        digest = fingerprint(command)
        with self.transaction() as con:
            row = con.execute("SELECT * FROM creations WHERE owner=? AND id=?", (owner, command_id)).fetchone()
            if row:
                if row["digest"] != digest:
                    raise StoreError("操作标识已用于不同内容。", 409, "command_conflict")
                return self.load(con, owner, row["game_id"])
            current = con.execute("SELECT active_game FROM sessions WHERE id=?", (owner,)).fetchone()
            if current is None:
                raise StoreError("请先建立会话。", 401)
            if current["active_game"] != command["expected_game_id"]:
                raise StoreError("另一页面已更新游戏，请刷新后继续。", 409, "stale_revision")
            if current["active_game"]:
                previous = self.load(con, owner, current["active_game"])
                if not (previous.get('gameplay')=='ensemble' and len(previous['humans'])>1):
                    archived = deepcopy(previous)
                    archived["archived"] = True
                    archived["revision"] += 1
                    self.save(con, archived, previous)
            state = factory(secrets.token_hex(12))
            con.execute("INSERT INTO games VALUES (?,?,?,?)", (state["id"], owner, canonical(state), time.time()))
            con.execute("INSERT INTO creations VALUES (?,?,?,?)", (owner, command_id, digest, state["id"]))
            con.execute("UPDATE sessions SET active_game=? WHERE id=?", (state["id"], owner))
            return state

    def state(self, owner, game_id):
        with self.transaction(False) as con:
            return self.load(con, owner, game_id)

    def games(self, owner):
        with self.transaction(False) as con:
            rows = con.execute("SELECT state FROM games WHERE owner=? OR EXISTS (SELECT 1 FROM game_members m WHERE m.game_id=games.id AND m.session_id=?) ORDER BY created DESC", (owner,owner)).fetchall()
        states = [json.loads(r["state"]) for r in rows]
        return [{k: g[k] for k in ("id", "phase", "beat", "archived", "outcome")} for g in states]

    def execute(self, owner, game_id, command):
        allowed = {"command_id", "expected_revision", "kind", "action", "target"}
        if not isinstance(command, dict) or set(command) - allowed:
            raise StoreError("请求包含不支持的字段。")
        command_id = self.command_id(command.get("command_id"))
        if type(command.get("expected_revision")) is not int:
            raise StoreError("缺少有效的状态版本，请刷新。")
        if command.get("kind") != "action" and ({"action", "target"} & set(command)):
            raise StoreError("阶段操作不能附带角色行动。")
        if any(v is not None and not isinstance(v, str) for k, v in command.items() if k in ("action", "target", "kind")):
            raise StoreError("行动内容格式不正确。")
        digest = fingerprint(command)
        with self.transaction() as con:
            original = self.load(con, owner, game_id)
            row = con.execute("SELECT * FROM commands WHERE game_id=? AND id=?", (game_id, command_id)).fetchone()
            if row:
                if row["digest"] != digest:
                    raise StoreError("操作标识已用于不同内容。", 409, "command_conflict")
                return original, {**json.loads(row["receipt"]), "duplicate": True}
            state = original
            if original["revision"] != command["expected_revision"]:
                receipt = {"accepted": False, "code": "stale_revision", "message": "页面信息已更新，这次操作未执行。请查看最新状态。"}
            else:
                try:
                    state, result = transition(original, command)
                    self.save(con, state, original)
                    receipt = {"accepted": True, "code": result, "message": "行动已记录。" if command.get("kind") == "action" else "已更新。"}
                except RuleError as exc:
                    receipt = {"accepted": False, "code": exc.code, "message": str(exc)}
            receipt.update({"command_id": command_id, "duplicate": False})
            con.execute("INSERT INTO commands VALUES (?,?,?,?)", (game_id, command_id, digest, canonical(receipt)))
            return state, receipt

    def reserve_review(self, owner, game_id, command_id, revision, model, prefix_hash, request_hash):
        self.command_id(command_id)
        with self.transaction() as con:
            state = self.load(con, owner, game_id)
            context_hash = fingerprint(observation_context(player_view(state)))
            row = con.execute("SELECT * FROM model_calls WHERE game_id=? AND command_id=?", (game_id, command_id)).fetchone()
            if row:
                # A lost response can be recovered after the state has moved on.
                if row["revision"] != revision:
                    raise StoreError("操作标识已用于不同内容。", 409, "command_conflict")
                return dict(row), False
            if state["archived"] or state["phase"] not in ("active", "ended"):
                raise StoreError("请在游玩或结局界面整理已知线索。", 409, "wrong_phase")
            if state["revision"] != revision:
                raise StoreError("状态已更新，请查看最新记录后重试。", 409, "stale_revision")
            cached = con.execute("SELECT * FROM model_calls WHERE game_id=? AND context_hash=? AND status='completed' ORDER BY started DESC LIMIT 1", (game_id, context_hash)).fetchone()
            if cached:
                return dict(cached), False
            if con.execute("SELECT 1 FROM model_calls WHERE game_id=? AND status='pending'", (game_id,)).fetchone():
                raise StoreError("上一份线索整理还在进行，请稍后查看。", 409, "review_pending")
            if con.execute("SELECT COUNT(*) FROM model_calls WHERE game_id=?", (game_id,)).fetchone()[0] >= 3:
                raise StoreError("本局的三次线索整理额度已使用完，原始观察记录仍可随时查看。", 409, "budget_exhausted")
            call_id = secrets.token_hex(12)
            con.execute("INSERT INTO model_calls(id,game_id,command_id,context_hash,status,model,revision,prefix_hash,request_hash,started) VALUES (?,?,?,?,'pending',?,?,?,?,?)",
                        (call_id, game_id, command_id, context_hash, model, revision, prefix_hash, request_hash, time.time()))
            return dict(con.execute("SELECT * FROM model_calls WHERE id=?", (call_id,)).fetchone()), True

    def finish_review(self, call_id, result):
        with self.transaction() as con:
            con.execute("UPDATE model_calls SET status=?, latency_ms=?, usage=?, cost_upper_usd=?, selected=?, error_code=?, returned_model=? WHERE id=? AND status='pending'",
                        (result["status"], result["latency_ms"], canonical(result.get("usage")), result.get("cost_upper_usd"),
                         canonical(result.get("selected", [])), result.get("error_code"), result.get("returned_model"), call_id))

    def model_summary(self, owner, game_id):
        with self.transaction(False) as con:
            state = self.load(con, owner, game_id)
            calls = [dict(r) for r in con.execute("SELECT * FROM model_calls WHERE game_id=? ORDER BY started", (game_id,)).fetchall()]
        context_hash = fingerprint(observation_context(player_view(state)))
        current = [c for c in calls if c["context_hash"] == context_hash and c["status"] == "completed"]
        latest = current[-1] if current and state["phase"] in ("active", "ended") else None
        totals = {}
        usages = [json.loads(c["usage"]) if c["usage"] else None for c in calls]
        for key in ("prompt_tokens", "completion_tokens", "prompt_cache_hit_tokens", "prompt_cache_miss_tokens"):
            totals[key] = sum(u[key] for u in usages) if usages and all(isinstance(u, dict) and type(u.get(key)) is int for u in usages) else None
        costs = [c["cost_upper_usd"] for c in calls]
        return {"calls": len(calls), "limit": 3, "pending": any(c["status"] == "pending" for c in calls),
                "reported_usage": totals, "estimated_upper_usd": sum(costs) if costs and all(c is not None for c in costs) else None,
                "has_unknown_usage": any(u is None or any(value is None for value in u.values()) for u in usages),
                "selected": json.loads(latest["selected"]) if latest else [],
                "latest_status": calls[-1]["status"] if calls else None}
