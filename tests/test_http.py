import http.cookiejar
import json
from pathlib import Path
import tempfile
import threading
import unittest
import urllib.error
import urllib.request

from palter.deepseek import DeepSeek, Settings
from palter.server import Application, Server
from .test_demo import fake_response


class HttpTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        model = DeepSeek(Settings(api_key="not-a-real-key"), fake_response)
        self.app = Application(Path(self.directory.name)/"http.db", model)
        self.server = Server(("127.0.0.1", 0), self.app)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.addCleanup(self.stop)
        self.base = f"http://127.0.0.1:{self.server.server_port}"
        self.opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()))
        _, self.session, _ = self.call("/api/session")

    def stop(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(3)

    def call(self, path, body=None, headers=None, opener=None):
        request_headers = {"Content-Type": "application/json"}
        if hasattr(self, "session"):
            request_headers["X-Palter-CSRF"] = self.session["csrf"]
        request_headers.update(headers or {})
        request = urllib.request.Request(self.base+path, data=json.dumps(body).encode() if body is not None else None, headers=request_headers)
        try:
            response = (opener or self.opener).open(request, timeout=5)
        except urllib.error.HTTPError as error:
            response = error
        with response:
            raw = response.read()
            return response.status, json.loads(raw) if response.headers.get_content_type()=="application/json" else raw, response.headers

    def create(self):
        status, data, _ = self.call("/api/games", {"command_id":"create_0001","expected_game_id":None})
        self.assertEqual(status, 200)
        return data["view"]

    def test_cookie_csrf_origin_and_allowlisted_assets(self):
        _, _, headers = self.call("/api/session")
        self.assertIn("HttpOnly", headers["Set-Cookie"])
        self.assertIn("SameSite=Strict", headers["Set-Cookie"])
        status, _, _ = self.call("/api/games", {"command_id":"create_0001","expected_game_id":None}, {"X-Palter-CSRF":"wrong"})
        self.assertEqual(status, 403)
        status, _, _ = self.call("/api/session", headers={"Origin":"https://unrelated.example"})
        self.assertEqual(status, 403)
        for path in ("/.env", "/palter/storage.py", "/../.env", "/.local/palter.sqlite3"):
            status, body, _ = self.call(path)
            self.assertEqual(status, 404)
            self.assertNotIn("not-a-real-key", json.dumps(body))
        status, html, headers = self.call("/")
        self.assertEqual(status, 200)
        self.assertIn("PALTER".encode(), html)
        self.assertIn("frame-ancestors 'none'", headers["Content-Security-Policy"])

    def test_wire_projection_rejects_other_role_and_foreign_game(self):
        view = self.create()
        for i, kind in enumerate(("confirm","ready")):
            status, data, _ = self.call(f"/api/games/{view['id']}/commands", {"command_id":f"command_{i:04d}","expected_revision":view["revision"],"kind":kind})
            self.assertEqual(status, 200)
            view = data["view"]
        for key in ("knowledge", "events", "locations", "letter_custody"):
            self.assertNotIn(key, view)
        self.assertNotIn("包里", json.dumps(view,ensure_ascii=False))
        status, _, _ = self.call(f"/api/games/{view['id']}?role=B")
        self.assertEqual(status, 400)
        other = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()))
        self.call("/api/session", opener=other)
        status, _, _ = self.call(f"/api/games/{view['id']}", opener=other)
        self.assertEqual(status, 404)
        status, _, _ = self.call(f"/api/games/{view['id']}/commands", {"command_id":"actor_0001","expected_revision":view["revision"],"kind":"action","action":"wait","actor":"B"})
        self.assertEqual(status, 400)

    def test_model_route_uses_same_player_boundary(self):
        view = self.create()
        for i, kind in enumerate(("confirm","ready")):
            _, data, _ = self.call(f"/api/games/{view['id']}/commands", {"command_id":f"command_{i:04d}","expected_revision":view["revision"],"kind":kind})
            view = data["view"]
        status, data, _ = self.call(f"/api/games/{view['id']}/review", {"command_id":"review_0001","expected_revision":view["revision"]})
        self.assertEqual(status, 200)
        self.assertEqual(data["status"], "completed")
        self.assertEqual(data["view"]["beat"], 0)
        self.assertTrue(data["view"]["review"]["records"])
        self.assertNotIn("not-a-real-key", json.dumps(data))

    def test_all_three_outcomes_through_http(self):
        paths = {
            "delivered": [("follow","B"),("inspect","drawer"),("take","letter"),("move","hall"),("wait",None),("wait",None)],
            "incomplete": [("wait",None)]*3+[("move","study"),("inspect","drawer"),("take","letter")],
            "not_found": [("wait",None)]*6,
        }
        current = None
        for index, (outcome, actions) in enumerate(paths.items()):
            _, data, _ = self.call("/api/games", {"command_id":f"create_http_{index}","expected_game_id":current})
            view = data["view"]
            current = view["id"]
            for n, command in enumerate([{"kind":"confirm"},{"kind":"ready"}]+[{"kind":"action","action":a,"target":t} for a,t in actions]):
                status, data, _ = self.call(f"/api/games/{current}/commands", {"command_id":f"http_action_{n:04d}","expected_revision":view["revision"],**command})
                self.assertEqual(status, 200)
                self.assertTrue(data["receipt"]["accepted"])
                view = data["view"]
            self.assertEqual(view["outcome"]["id"], outcome)
            _, restored, _ = self.call(f"/api/games/{current}")
            self.assertEqual(view, restored["view"])

    def test_server_restart_keeps_cookie_owned_game_and_history(self):
        view = self.create()
        for i, command in enumerate([{"kind":"confirm"},{"kind":"ready"},{"kind":"action","action":"wait"}]):
            _, data, _ = self.call(f"/api/games/{view['id']}/commands", {"command_id":f"restart_{i:04d}","expected_revision":view["revision"],**command})
            view = data["view"]
        self.stop()
        self.app = Application(Path(self.directory.name)/"http.db", DeepSeek(Settings(api_key="not-a-real-key"), fake_response))
        self.server = Server(("127.0.0.1",0),self.app)
        self.thread = threading.Thread(target=self.server.serve_forever,daemon=True)
        self.thread.start()
        self.base = f"http://127.0.0.1:{self.server.server_port}"
        status, restored, _ = self.call("/api/session")
        self.assertEqual(status,200)
        self.assertEqual(restored["view"],view)


if __name__ == "__main__":
    unittest.main()
