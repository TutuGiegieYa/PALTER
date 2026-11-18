"""Loopback HTTP transport; the game engine remains independent of HTTP."""

import argparse
from http.cookies import SimpleCookie, CookieError
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import hmac
import ipaddress
import json
from pathlib import Path
import re
import sys
import threading
from urllib.parse import urlsplit

from .deepseek import DeepSeek, Settings, ROOT
from .engine import player_view
from .storage import Store, StoreError, fingerprint


class Application:
    def __init__(self, database, model=None):
        self.store = Store(database)
        self.model = model if model is not None else DeepSeek(Settings.load())
        self.model_slots = threading.BoundedSemaphore(2)

    def create_game(self, owner, command):
        return self.store.create_game(owner, command)

    def command(self, owner, game_id, command):
        return self.store.execute(owner, game_id, command)

    def view(self, owner, state):
        view = player_view(state)
        summary = self.store.model_summary(owner, state["id"])
        # Only immutable, already acquired observation texts can be displayed.
        records = {o["id"]: o for o in view["observations"]}
        summary["records"] = [records[i] for i in summary.pop("selected") if i in records]
        summary["configured"] = self.model.configured
        summary["model"] = self.model.settings.model
        view["review"] = summary
        return view

    def review(self, owner, game_id, command):
        if set(command) != {"command_id", "expected_revision"} or type(command["expected_revision"]) is not int:
            raise StoreError("线索整理请求格式不正确。")
        if not self.model.configured:
            raise StoreError("尚未配置 DeepSeek；原始观察记录仍可查看。", 503, "not_configured")
        if not self.model_slots.acquire(blocking=False):
            raise StoreError("线索整理暂时繁忙，请稍后重试。", 503, "model_busy")
        try:
            state = self.store.state(owner, game_id)
            view = player_view(state)
            payload = self.model.payload(view)
            row, fresh = self.store.reserve_review(owner, game_id, command["command_id"], command["expected_revision"],
                                                  self.model.settings.model, self.model.prefix_hash, fingerprint(payload))
            if fresh:
                try:
                    result = self.model.review(view)
                except Exception:
                    # The provider may have accepted an interrupted request.
                    result = {"status": "failed", "latency_ms": 0, "usage": None, "error_code": "unexpected_failure"}
                self.store.finish_review(row["id"], result)
                status = result["status"]
            else:
                status = row["status"]
            return {"status": status, "cached": not fresh,
                    "message": "已从你的观察记录中整理出线索。" if status == "completed" else
                    "线索整理未完成，原始观察记录已保留。" if status != "pending" else "正在整理，请稍后查看。",
                    "view": self.view(owner, self.store.state(owner, game_id))}
        finally:
            self.model_slots.release()


class Server(ThreadingHTTPServer):
    daemon_threads = True

    def __init__(self, address, application):
        self.application = application
        super().__init__(address, Handler)
        if hasattr(application,'start_background'):application.start_background()

    def server_close(self):
        if hasattr(self.application,'stop_background'):self.application.stop_background()
        super().server_close()


class Handler(BaseHTTPRequestHandler):
    server_version = "PALTER"

    def log_message(self, format, *args):
        # Do not log request bodies, cookies, credentials, or query strings.
        pass

    def send(self, status, body, content_type="application/json; charset=utf-8", cookie=None):
        raw = json.dumps(body, ensure_ascii=False).encode() if content_type.startswith("application/json") else body
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(raw)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Referrer-Policy", "no-referrer")
        self.send_header("Content-Security-Policy", "default-src 'self'; script-src 'self'; style-src 'self'; connect-src 'self'; img-src 'self' data:; frame-ancestors 'none'; base-uri 'none'; form-action 'self'")
        if cookie:
            self.send_header("Set-Cookie", f"palter_session={cookie}; HttpOnly; SameSite=Strict; Path=/; Max-Age=31536000")
        self.end_headers()
        try:
            self.wfile.write(raw)
        except (BrokenPipeError, ConnectionResetError):
            pass

    def check_origin(self):
        port = self.server.server_port
        allowed = {f"127.0.0.1:{port}", f"localhost:{port}", f"{self.server.server_address[0]}:{port}"}
        host = self.headers.get("Host", "")
        if host not in allowed:
            raise StoreError("请求地址不符合服务器配置。", 403, "invalid_host")
        origin = self.headers.get("Origin")
        if origin and origin != "http://" + host:
            raise StoreError("请求来源不符合当前会话。", 403, "invalid_origin")

    def session_token(self):
        try:
            cookies = SimpleCookie(self.headers.get("Cookie", ""))
            return cookies["palter_session"].value if "palter_session" in cookies else None
        except CookieError:
            return None

    def dispatch(self):
        self.check_origin()
        app = self.server.application
        parsed = urlsplit(self.path)
        path = parsed.path
        if parsed.query:
            raise StoreError("这个接口不接受额外的查询参数。")
        if self.command == "GET" and path in ("/", "/style.css", "/app.js", "/investigation.js", "/ensemble.js", "/spectator.js"):
            asset, mime = {"/": ("index.html", "text/html; charset=utf-8"), "/style.css": ("style.css", "text/css; charset=utf-8"), "/app.js": ("app.js", "text/javascript; charset=utf-8"), "/investigation.js": ("investigation.js", "text/javascript; charset=utf-8"), "/ensemble.js": ("ensemble.js", "text/javascript; charset=utf-8"), "/spectator.js": ("spectator.js", "text/javascript; charset=utf-8")}[path]
            return self.send(200, (Path(__file__).parent / "static" / asset).read_bytes(), mime)
        if self.command == "GET" and path == "/api/session":
            session = app.store.session(self.session_token())
            state = app.store.state(session["id"], session["active_game"]) if session["active_game"] else None
            return self.send(200, {"csrf": session["csrf"], "active_game": session["active_game"],
                                  "runtime_mode": getattr(app,"mode","offline"),
                                  "gameplay": getattr(app,"gameplay",None),
                                  "games": app.store.games(session["id"]),
                                  "view": app.view(session["id"], state) if state else None}, cookie=session["id"])
        session = app.store.require_session(self.session_token())
        match = re.fullmatch(r"/api/games/([a-f0-9]{24})(?:/(commands|review))?", path)
        if self.command == "GET" and match and match[2] is None:
            return self.send(200, {"view": app.view(session["id"], app.store.state(session["id"], match[1]))})
        if self.command != "POST":
            raise StoreError("没有找到这个页面。", 404, "not_found")
        if not hmac.compare_digest(self.headers.get("X-Palter-CSRF", ""), session["csrf"]):
            raise StoreError("会话校验失败，请刷新后重试。", 403, "invalid_csrf")
        if self.headers.get_content_type() != "application/json":
            raise StoreError("请求需要使用 JSON 格式。", 415)
        try:
            length = int(self.headers.get("Content-Length", "0"))
        except ValueError:
            raise StoreError("请求长度无效。") from None
        limit=24000 if getattr(app,"gameplay",None) in ("investigation","ensemble") else 4096
        if not 0 < length <= limit:
            raise StoreError("请求内容过大或为空。", 413)
        try:
            body = json.loads(self.rfile.read(length))
        except (ValueError, UnicodeDecodeError):
            raise StoreError("无法读取请求内容。") from None
        if not isinstance(body, dict):
            raise StoreError("请求需要是一个 JSON 对象。")
        if path == "/api/games":
            state = app.create_game(session["id"], body)
            return self.send(200, {"view": app.view(session["id"], state)})
        if path == '/api/join' and hasattr(app,'join'):
            state=app.join(session['id'],body)
            return self.send(200,{'view':app.view(session['id'],state)})
        if match and match[2] == "commands":
            state, receipt = app.command(session["id"], match[1], body)
            return self.send(200, {"receipt": receipt, "view": app.view(session["id"], state)})
        if match and match[2] == "review":
            return self.send(200, app.review(session["id"], match[1], body))
        raise StoreError("没有找到这个接口。", 404, "not_found")

    def handle_request(self):
        try:
            self.dispatch()
        except StoreError as exc:
            self.send(exc.status, {"error": {"code": exc.code, "message": str(exc)}})
        except Exception as exc:
            print(f"Request failed: {type(exc).__name__}", file=sys.stderr)
            self.send(500, {"error": {"code": "internal_error", "message": "本次请求未完成，请刷新查看已保存的状态。"}})

    do_GET = handle_request
    do_POST = handle_request


def main():
    parser = argparse.ArgumentParser(description="Run the local PALTER demo")
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--host", default="127.0.0.1", help="An explicit local IPv4 address; use a LAN interface address for invited multiplayer")
    parser.add_argument("--database", type=Path, default=ROOT / ".local" / "palter.sqlite3")
    parser.add_argument("--offline", action="store_true", help="Explicit scripted regression mode; no AI-driven characters")
    args = parser.parse_args()
    try:
        address=ipaddress.IPv4Address(args.host)
        if address.is_unspecified or address.is_multicast:raise ValueError()
    except ValueError:parser.error('--host requires an explicit unicast IPv4 interface address')
    if args.offline:
        app = Application(args.database)
    else:
        from .ensemble import EnsembleApplication
        app = EnsembleApplication(args.database)
    server = Server((str(address), args.port), app)
    print(f"PALTER: http://{address}:{server.server_port}", flush=True)
    print(f"DeepSeek configured: {app.model.configured}; model: {app.model.settings.model}", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
