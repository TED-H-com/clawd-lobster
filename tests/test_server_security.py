"""Request guard of the local web server (CSRF and DNS rebinding).

Starts the real handler on a random 127.0.0.1 port and sends raw requests,
so the Host, Origin and X-Clawd-Token headers are exactly what each test
says they are.
"""
import json
import os
import re
import stat
import subprocess
import sys
import tempfile
import threading
import unittest
from http.client import HTTPConnection
from http.server import ThreadingHTTPServer
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from clawd_lobster import server

# Every POST route changes state or runs something, so all of them need the token
STATE_CHANGING = [
    "/api/onboarding/session",
    "/api/onboarding/check",
    "/api/onboarding/intent",
    "/api/onboarding/reconcile",
    "/api/onboarding/handoff-gen",
    "/api/onboarding/detect",
    "/api/controller/acquire",
    "/api/controller/renew",
    "/api/controller/release",
    "/api/controller/handoff",
    "/api/workspaces/create",
    "/api/squad/chat",
    "/api/squad/start",
    "/api/vault/test",
    "/api/vault/save",
    "/api/skills/spec/install",
    "/api/skills/spec/verify",
    "/api/jobs/register",
]


class ServerTestCase(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.httpd = ThreadingHTTPServer(("127.0.0.1", 0), server._Handler)
        cls.httpd.daemon_threads = True
        cls.port = cls.httpd.server_address[1]
        cls.host = f"127.0.0.1:{cls.port}"
        cls.token = server.get_ui_token()
        cls.thread = threading.Thread(target=cls.httpd.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.httpd.shutdown()
        cls.httpd.server_close()

    def send(self, method, path, headers=None, body=None, host=True):
        """Send one request. host=True adds Host: 127.0.0.1:<port>."""
        all_headers = {}
        if host is True:
            all_headers["Host"] = self.host
        elif host:
            all_headers["Host"] = host
        all_headers.update(headers or {})
        payload = None
        if body is not None:
            payload = json.dumps(body).encode("utf-8")
            all_headers["Content-Type"] = "application/json"
            all_headers["Content-Length"] = str(len(payload))
        conn = HTTPConnection("127.0.0.1", self.port, timeout=10)
        try:
            conn.putrequest(method, path, skip_host=True, skip_accept_encoding=True)
            for name, value in all_headers.items():
                conn.putheader(name, value)
            conn.endheaders(payload)
            resp = conn.getresponse()
            text = resp.read().decode("utf-8", "replace")
            return resp.status, dict(resp.getheaders()), text
        finally:
            conn.close()

    def post(self, path, body=None, token=True, headers=None, **kwargs):
        all_headers = {}
        if token is True:
            all_headers[server.TOKEN_HEADER] = self.token
        elif token:
            all_headers[server.TOKEN_HEADER] = token
        all_headers.update(headers or {})
        return self.send("POST", path, all_headers, body if body is not None else {}, **kwargs)

    def assertForbidden(self, result, fragment=""):
        status, headers, text = result
        self.assertEqual(status, 403, text)
        self.assertIn(fragment, json.loads(text)["error"])
        self.assertNotIn(self.token, text)
        self.assertFalse(any(h.lower().startswith("access-control-") for h in headers))


class TestPages(ServerTestCase):

    def test_pages_carry_the_token_and_refuse_caching_and_framing(self):
        for path in ("/onboarding", "/workspaces", "/squad", "/skills", "/credentials",
                     "/settings", "/guide"):
            status, headers, text = self.send("GET", path)
            self.assertEqual(status, 200, path)
            self.assertIn(f'<meta name="clawd-token" content="{self.token}">', text, path)
            self.assertEqual(headers.get("Cache-Control"), "no-store", path)
            self.assertEqual(headers.get("X-Frame-Options"), "DENY", path)
            self.assertIn("frame-ancestors 'none'", headers.get("Content-Security-Policy", ""))

    def test_meta_tag_sits_inside_head(self):
        html = server._inject_token("<!DOCTYPE html><html><head lang='en'><title>x</title></head></html>")
        self.assertRegex(html, r"<head lang='en'><meta name=\"clawd-token\" content=\"[^\"]+\"><title>")

    def test_pages_send_the_token_header_on_every_post(self):
        from clawd_lobster import pages, pages_onboarding
        page_sources = [pages.ONBOARDING_PAGE, pages.WORKSPACES_PAGE, pages.SQUAD_PAGE]
        page_sources += [v for k, v in vars(pages_onboarding).items()
                         if isinstance(v, str) and "fetch(" in v]
        checked = 0
        for source in page_sources:
            for match in re.finditer(r"method:\s*'POST'", source):
                window = source[match.start():match.start() + 200]
                self.assertRegex(window, r"clawdHeaders\(\)|authHeaders\(\)|X-Clawd-Token",
                                 window)
                checked += 1
        self.assertGreater(checked, 5)


class TestHostCheck(ServerTestCase):

    def test_local_host_names_are_accepted(self):
        for host in (self.host, f"localhost:{self.port}", f"LOCALHOST:{self.port}"):
            status, _, text = self.send("GET", "/api/status", host=host)
            self.assertEqual(status, 200, host)
            self.assertTrue(json.loads(text)["ok"])

    def test_other_hosts_are_rejected(self):
        for host in (f"attacker.example:{self.port}",   # DNS rebinding
                     f"127.0.0.1:{self.port + 1}",       # wrong port
                     "127.0.0.1",                        # no port
                     f"127.0.0.1.attacker.example:{self.port}"):
            self.assertForbidden(self.send("GET", "/onboarding", host=host), "Host")
            self.assertForbidden(self.post("/api/squad/chat", {"message": ""}, host=host), "Host")

    def test_missing_host_is_rejected(self):
        self.assertForbidden(self.send("GET", "/api/status", host=None), "Host")


class TestOriginCheck(ServerTestCase):

    def test_same_origin_is_accepted(self):
        for host in (self.host, f"localhost:{self.port}"):
            status, _, text = self.post("/api/squad/chat", {"message": ""}, host=host,
                                        headers={"Origin": f"http://{host}"})
            self.assertEqual(status, 200, text)

    def test_other_origins_are_rejected(self):
        for origin in ("http://attacker.example", "null", f"http://127.0.0.1:{self.port + 1}",
                       f"https://127.0.0.1:{self.port}", f"http://localhost:{self.port}"):
            result = self.post("/api/squad/chat", {"message": ""}, headers={"Origin": origin})
            self.assertForbidden(result, "cross-origin")
        result = self.send("GET", "/api/status", headers={"Origin": "http://attacker.example"})
        self.assertForbidden(result, "cross-origin")


class TestTokenCheck(ServerTestCase):

    def test_post_without_token_is_rejected_everywhere(self):
        for path in STATE_CHANGING:
            self.assertForbidden(self.post(path, token=False), server.TOKEN_HEADER)

    def test_post_with_wrong_token_is_rejected_everywhere(self):
        for path in STATE_CHANGING:
            self.assertForbidden(self.post(path, token="not-the-token"), server.TOKEN_HEADER)
            self.assertForbidden(self.post(path, token=self.token[:-1]), server.TOKEN_HEADER)

    def test_get_with_token_in_query_is_not_enough_for_post(self):
        result = self.post(f"/api/squad/chat?token={self.token}", {"message": ""}, token=False)
        self.assertForbidden(result, server.TOKEN_HEADER)

    def test_requests_with_the_token_reach_the_handlers(self):
        status, _, text = self.post("/api/squad/chat", {"message": ""})
        self.assertEqual((status, json.loads(text)), (200, {"response": "", "discovery_complete": False}))

        status, _, text = self.post("/api/workspaces/create", {"name": ""})
        self.assertEqual(status, 400)
        self.assertEqual(json.loads(text)["error"], "Name is required")

        status, _, text = self.post("/api/squad/start", {})
        self.assertEqual(status, 400)
        self.assertEqual(json.loads(text)["error"], "workspace is required")

    def test_session_auth_still_applies_after_the_token_check(self):
        status, _, text = self.post("/api/controller/acquire", {"session_id": "x", "holder": "web"})
        self.assertEqual(status, 401)
        self.assertIn("Authentication required", json.loads(text)["error"])

    def test_tokens_are_compared_in_constant_time(self):
        with patch.object(server.hmac, "compare_digest",
                          wraps=server.hmac.compare_digest) as compare:
            self.post("/api/squad/chat", {"message": ""}, token="wrong")
            self.post("/api/squad/chat", {"message": ""})
        self.assertEqual(compare.call_count, 2)

    def test_token_is_new_in_every_process(self):
        code = "from clawd_lobster import server; print(server.get_ui_token())"
        root = str(Path(__file__).resolve().parent.parent)
        tokens = {subprocess.run([sys.executable, "-c", code], cwd=root, capture_output=True,
                                 text=True, check=True).stdout.strip() for _ in range(2)}
        tokens.add(self.token)
        self.assertEqual(len(tokens), 3)
        self.assertTrue(all(len(t) >= 40 for t in tokens))


class TestCors(ServerTestCase):

    def test_preflight_is_refused(self):
        result = self.send("OPTIONS", "/api/workspaces/create", headers={
            "Origin": "http://attacker.example",
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "content-type, x-clawd-token",
        })
        self.assertForbidden(result, "cross-origin")

    def test_responses_never_carry_cors_headers(self):
        for result in (self.send("GET", "/api/status"), self.send("GET", "/onboarding"),
                       self.post("/api/squad/chat", {"message": ""})):
            self.assertFalse(any(h.lower().startswith("access-control-") for h in result[1]))


class TestSquadStateApproval(ServerTestCase):

    def test_state_endpoint_reports_how_the_spec_was_approved(self):
        with tempfile.TemporaryDirectory() as ws:
            legacy = {"phase": "done", "approved": True, "review_round": 5, "turns": [
                {"role": "reviewer", "signal": {"verdict": "NEEDS_REVISION"}}]}
            (Path(ws) / ".spec-squad.json").write_text(json.dumps(legacy), encoding="utf-8")
            status, _, text = self.send("GET", f"/api/squad/state?workspace={ws}")
        self.assertEqual(status, 200)
        self.assertEqual(json.loads(text)["squad_state"]["approval"], "round_limit")


class TestStartup(unittest.TestCase):

    def test_allowed_hosts(self):
        self.assertEqual(server._allowed_hosts(3333), {"127.0.0.1:3333", "localhost:3333"})
        self.assertEqual(server._allowed_hosts(80),
                         {"127.0.0.1:80", "localhost:80", "127.0.0.1", "localhost"})

    def test_token_file_is_private_and_holds_the_token(self):
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "sub" / "server-3333.token"
            with patch.object(server, "token_file_path", return_value=target):
                path = server._write_token_file(3333)
            self.assertEqual(path, target)
            self.assertEqual(target.read_text(encoding="utf-8"), server.get_ui_token())
            if os.name == "posix":
                self.assertEqual(stat.S_IMODE(target.stat().st_mode), 0o600)

    def test_start_server_binds_loopback_and_removes_the_token_file(self):
        seen = {}

        class FakeServer:
            def __init__(self, address, handler):
                seen["address"] = address

            def serve_forever(self):
                seen["token_file_existed"] = target.exists()
                raise KeyboardInterrupt

            def server_close(self):
                seen["closed"] = True

        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "server-4545.token"
            with patch.object(server, "HTTPServer", FakeServer), \
                 patch.object(server, "token_file_path", return_value=target), \
                 patch("builtins.print"):
                server.start_server(port=4545, open_browser=False)
            self.assertEqual(seen["address"], ("127.0.0.1", 4545))
            self.assertTrue(seen["token_file_existed"])
            self.assertTrue(seen["closed"])
            self.assertFalse(target.exists())


if __name__ == "__main__":
    unittest.main(verbosity=2)


class TestDirectHandlers(unittest.TestCase):
    def setUp(self):
        from unittest.mock import MagicMock
        from clawd_lobster.server import _Handler
        self.handler = MagicMock(spec=_Handler)
        self.handler.headers = {"Host": "localhost"}
        self.handler.server = MagicMock()
        self.handler.server.server_address = ("127.0.0.1", 8080)

        self.handler._send_html = MagicMock()
        self.handler._send_json = MagicMock()
        self.handler._read_body = MagicMock()
        self.handler._send_redirect = MagicMock()
        self.handler._serve_asset = MagicMock()
        self.handler._serve_screenshot = MagicMock()
        self.handler.send_error = MagicMock()

        self.handler._check_token = MagicMock(return_value=True)
        self.handler._require_auth = MagicMock(return_value=True)
        self.handler._guard = MagicMock(return_value=True)

    def test_routing_and_guards(self):
        from clawd_lobster.server import _Handler

        # Test unknown routes
        self.handler.path = "/unknown"
        _Handler.do_GET(self.handler)
        self.handler.send_error.assert_called_with(404)

        self.handler.path = "/api/unknown"
        _Handler.do_POST(self.handler)
        self.handler.send_error.assert_called_with(404)

        # Test auth bypass / auth failure
        self.handler._require_auth.return_value = False

        self.handler.path = "/api/onboarding/manifest"
        _Handler.do_GET(self.handler) # returns early because require_auth returns false

        self.handler.path = "/api/onboarding/intent"
        _Handler.do_POST(self.handler) # returns early because require_auth returns false

        # Test missing / bad token for state changing
        self.handler._guard.return_value = False
        _Handler.do_POST(self.handler) # returns early

    def test_routes(self):
        from clawd_lobster.server import _Handler

        # Test basic routes
        self.handler.path = "/guide"
        _Handler._route_guide(self.handler, {})

        self.handler.path = "/settings"
        _Handler._route_settings(self.handler, {})

        self.handler.path = "/credentials"
        _Handler._route_credentials(self.handler, {})

        self.handler.path = "/skills"
        _Handler._route_skills(self.handler, {})

        self.handler.path = "/workspaces"
        _Handler._route_workspaces(self.handler, {})

        self.handler.path = "/onboarding"
        _Handler._route_onboarding(self.handler, {})

        self.handler.path = "/squad"
        _Handler._route_squad(self.handler, {})

    def test_squad_endpoints(self):
        from clawd_lobster.server import _Handler
        import json

        # squad chat missing args
        self.handler.path = "/api/squad/chat"
        self.handler._read_body.return_value = {"message": ""}
        _Handler._api_squad_chat(self.handler)
        self.handler._send_json.assert_called_with({"response": "", "discovery_complete": False})

        # squad start
        self.handler.path = "/api/squad/start"
        self.handler._read_body.return_value = {"project_desc": "d", "workspace": "w"}
        _Handler._api_squad_start(self.handler)

        # squad state
        self.handler.path = "/api/squad/state"
        _Handler._api_squad_state(self.handler, {"workspace": ["ws1"]})

    def test_vault_endpoints(self):
        from clawd_lobster.server import _Handler
        import json

        # vault test
        self.handler.path = "/api/vault/test"
        self.handler._read_body.return_value = {"user": "u", "password": "p", "dsn": "d"}
        _Handler._api_vault_test(self.handler)

        # vault save
        self.handler.path = "/api/vault/save"
        self.handler._read_body.return_value = {"user": "u", "password": "p", "dsn": "d", "wallet_dir": "w"}
        _Handler._api_vault_save(self.handler)

    def test_ob_endpoints(self):
        from clawd_lobster.server import _Handler
        from unittest.mock import patch, MagicMock

        with patch('clawd_lobster.server.ob_api') as mock_ob:
            mock_ob.get_state.return_value = ({"status": "ok"}, 200)
            _Handler._api_ob_state(self.handler, {})

            mock_ob.get_manifest.return_value = ({"status": "ok"}, 200)
            _Handler._api_ob_manifest(self.handler, {})

            mock_ob.get_events.return_value = ({"status": "ok"}, 200)
            _Handler._api_ob_events(self.handler, {})

            mock_ob.get_health.return_value = ({"status": "ok"}, 200)
            _Handler._api_ob_health(self.handler, {})

            mock_ob.get_controller.return_value = ({"status": "ok"}, 200)
            _Handler._api_ob_controller(self.handler, {})

            mock_ob.get_skills_catalog.return_value = ({"status": "ok"}, 200)
            _Handler._api_skills_catalog(self.handler, {})

            mock_ob.get_jobs_status.return_value = ({"status": "ok"}, 200)
            _Handler._api_jobs_status(self.handler, {})

            # Posts
            self.handler._read_body.return_value = {}
            mock_ob.apply_intent.return_value = ({"status": "ok"}, 200)
            _Handler._api_ob_intent(self.handler)

            mock_ob.run_reconcile.return_value = ({"status": "ok"}, 200)
            _Handler._api_ob_reconcile(self.handler)

            mock_ob.acquire_lease.return_value = ({"status": "ok"}, 200)
            _Handler._api_ob_lease_acquire(self.handler)

            mock_ob.renew_lease.return_value = ({"status": "ok"}, 200)
            _Handler._api_ob_lease_renew(self.handler)

            mock_ob.release_lease.return_value = ({"status": "ok"}, 200)
            _Handler._api_ob_lease_release(self.handler)

            mock_ob.handoff_lease.return_value = ({"status": "ok"}, 200)
            _Handler._api_ob_lease_handoff(self.handler)

            mock_ob.generate_handoff.return_value = ({"status": "ok"}, 200)
            _Handler._api_ob_handoff_gen(self.handler)

            mock_ob.detect_handoff_state.return_value = ({"status": "ok"}, 200)
            _Handler._api_ob_detect(self.handler)

            mock_ob.create_session.return_value = ({"status": "ok"}, 200)
            _Handler._api_ob_create_session(self.handler)

            mock_ob.verify_skill.return_value = ({"status": "ok"}, 200)
            self.handler.path = "/api/skills/skill1/verify"
            _Handler.do_POST(self.handler)

            mock_ob.install_skill.return_value = ({"status": "ok"}, 200)
            self.handler.path = "/api/skills/skill1/install"
            _Handler.do_POST(self.handler)

            mock_ob.register_jobs.return_value = ({"status": "ok"}, 200)
            self.handler.path = "/api/jobs/register"
            _Handler.do_POST(self.handler)

    def test_workspace_creation(self):
        from clawd_lobster.server import _Handler
        from unittest.mock import patch, MagicMock

        # Test missing name
        self.handler.path = "/api/workspaces/create"
        self.handler._read_body.return_value = {"domain": "d", "description": "d"}
        _Handler._api_workspaces_create(self.handler)
        self.handler._send_json.assert_called_with({"ok": False, "error": "Name is required"}, status=400)

        # Test fallback minimal workspace creation
        self.handler._read_body.return_value = {"name": "ws1", "domain": "d", "description": "d"}

        self.handler._create_workspace_internal.side_effect = Exception("Test fallback")
        _Handler._api_workspaces_create(self.handler)
        self.handler._send_json.assert_called_with({"ok": False, "error": "Test fallback"}, status=400)

        self.handler._create_workspace_internal.side_effect = None
        self.handler._create_workspace_internal.return_value = {"id": "ws1"}
        _Handler._api_workspaces_create(self.handler)
        self.handler._send_json.assert_called_with({"ok": True, "workspace": {"id": "ws1"}})

    def test_create_workspace_internal_fallback(self):
        from clawd_lobster.server import _Handler
        from unittest.mock import patch, MagicMock

        with patch('importlib.import_module') as mock_import, \
             patch('clawd_lobster.server._resolve_workspace_root', return_value="/tmp"), \
             patch('clawd_lobster.server.Path') as mock_path, \
             patch('clawd_lobster.server._get_workspaces_json_path'), \
             patch('clawd_lobster.server._read_json'), \
             patch('clawd_lobster.server.date'), \
             patch('clawd_lobster.server._write_json'):

             mock_import.side_effect = Exception("Fallback")
             mock_ws_root = MagicMock()
             mock_path.return_value = mock_ws_root
             mock_ws_path = MagicMock()
             mock_ws_root.__truediv__.return_value = mock_ws_path
             mock_claude_md = MagicMock()
             mock_ws_path.__truediv__.return_value = mock_claude_md

             res = _Handler._create_workspace_internal(self.handler, "ws1", "d", "desc")
             self.assertEqual(res["id"], "ws1")

    def test_squad_chat_no_discovery_turn(self):
        from clawd_lobster.server import _Handler
        from unittest.mock import patch, MagicMock
        import builtins
        from unittest.mock import ANY

        self.handler.path = "/api/squad/chat"
        self.handler._read_body.return_value = {"message": "hello", "workspace": "ws1"}

        mock_squad = MagicMock()
        del mock_squad.discovery_turn_sync

        orig_import = builtins.__import__
        def mock_import(name, globals=None, locals=None, fromlist=(), level=0):
            if 'squad' in name or (fromlist and 'squad' in fromlist):
                raise ImportError("mock no squad")
            return orig_import(name, globals, locals, fromlist, level)

        with patch('builtins.__import__', side_effect=mock_import):
            _Handler._api_squad_chat(self.handler)
            self.handler._send_json.assert_called_with({
                "response": (
                    "The Spec Squad chat is being set up. "
                    "Please use the terminal mode for now:\n\n"
                    "  clawd-lobster squad start"
                ),
                "discovery_complete": False,
            })

    def test_squad_start_fail(self):
        from clawd_lobster.server import _Handler
        from unittest.mock import patch, MagicMock
        import builtins
        from unittest.mock import ANY

        self.handler.path = "/api/squad/start"
        self.handler._read_body.return_value = {"project_desc": "hello", "workspace": "ws1"}

        mock_squad = MagicMock()
        del mock_squad.run_squad_web

        orig_import = builtins.__import__
        def mock_import(name, globals=None, locals=None, fromlist=(), level=0):
            if 'squad' in name or (fromlist and 'squad' in fromlist):
                raise ImportError("mock no squad")
            return orig_import(name, globals, locals, fromlist, level)

        with patch('builtins.__import__', side_effect=mock_import):
            # it was deleted

            _Handler._api_squad_start(self.handler)
            self.handler._send_json.assert_called_with({
                "ok": False,
                "error": "Squad module not yet available. Use terminal mode.",
            })

    def test_squad_state_with_workspace(self):
        from clawd_lobster.server import _Handler
        from unittest.mock import patch, MagicMock
        import builtins
        from unittest.mock import ANY

        mock_squad = MagicMock()

        orig_import = builtins.__import__
        def mock_import(name, globals=None, locals=None, fromlist=(), level=0):
            if 'squad' in name or (fromlist and 'squad' in fromlist):
                return mock_squad
            return orig_import(name, globals, locals, fromlist, level)

        with patch('clawd_lobster.server.Path') as mock_path, \
             patch('clawd_lobster.server._read_json') as mock_read, \
             patch('builtins.__import__', side_effect=mock_import):

             mock_ws = MagicMock()
             mock_path.return_value = mock_ws
             mock_state = MagicMock()
             mock_ws.__truediv__.return_value = mock_state
             mock_state.exists.return_value = True
             mock_read.return_value = {"phase": "review"}

             # `squad` module is mocked, so let's mock the `is_process_running` equivalent
             mock_squad.get_status_sync.return_value = True

             _Handler._api_squad_state(self.handler, {"workspace": ["ws1"]})
             self.handler._send_json.assert_called_with({
                 "phase": "review",
                 "squad_running": False,
                 "squad_state": {"phase": "review", "approval": ANY}
             })

    def test_vault_test_db(self):
        from clawd_lobster.server import _Handler
        from unittest.mock import patch, MagicMock
        import builtins
        from unittest.mock import ANY

        self.handler.path = "/api/vault/test"
        self.handler._read_body.return_value = {"user": "u", "password": "p", "dsn": "d", "wallet_dir": "w", "wallet_password": "wp"}

        mock_db = MagicMock()
        mock_conn = MagicMock()
        mock_conn.cursor.return_value.fetchone.return_value = ["19c"]
        mock_db.connect.return_value = mock_conn

        orig_import = builtins.__import__
        def mock_import(name, globals=None, locals=None, fromlist=(), level=0):
            if name == 'oracledb':
                return mock_db
            return orig_import(name, globals, locals, fromlist, level)

        with patch('builtins.__import__', side_effect=mock_import):
            _Handler._api_vault_test(self.handler)
            self.handler._send_json.assert_called_with({"ok": True, "version": "19c"})

            mock_db.connect.side_effect = Exception("DB error")
            _Handler._api_vault_test(self.handler)
            self.handler._send_json.assert_called_with({"ok": False, "error": "DB error"})

    def test_vault_save_db(self):
        from clawd_lobster.server import _Handler
        from unittest.mock import patch, MagicMock
        import builtins
        from unittest.mock import ANY
        import json

        self.handler.path = "/api/vault/save"
        self.handler._read_body.return_value = {"user": "u", "password": "p", "dsn": "d", "wallet_dir": "w", "wallet_password": "wp", "init_schema": True}

        mock_vault_init = MagicMock()
        mock_vault_init.init_schema.return_value = True

        orig_import = builtins.__import__
        def mock_import(name, globals=None, locals=None, fromlist=(), level=0):
            if name == 'vault_init':
                return mock_vault_init
            return orig_import(name, globals, locals, fromlist, level)

        with patch('clawd_lobster.server.Path') as mock_path, \
             patch('builtins.__import__', side_effect=mock_import), \
             patch('clawd_lobster.server._write_json') as mock_write_json:

             mock_home = MagicMock()
             mock_path.home.return_value = mock_home
             mock_clawd = MagicMock()
             mock_home.__truediv__.return_value = mock_clawd

             mock_config = MagicMock()
             mock_clawd.__truediv__.return_value = mock_config

             mock_config.exists.return_value = True
             mock_config.read_text.return_value = "{}"
             mock_config.with_suffix.return_value = MagicMock()

             _Handler._api_vault_save(self.handler)
             self.handler._send_json.assert_called_with({"ok": True, "message": "Oracle Vault enabled."})
             mock_config.with_suffix.return_value.write_text.assert_called()

    def test_onboarding_instructions_errors(self):
        from clawd_lobster.server import _Handler
        from unittest.mock import patch, MagicMock

        # Missing session_id
        self.handler.path = "/api/onboarding/instructions"
        _Handler._api_onboarding_instructions(self.handler, {})
        self.handler._send_json.assert_called_with({"ok": False, "error": "session_id required"}, status=400)

        # Missing CLAUDE.md
        with patch('clawd_lobster.server.onboarding.ONBOARDING_DIR') as mock_dir:
            mock_session_dir = MagicMock()
            mock_dir.__truediv__.return_value = mock_session_dir
            mock_claude_md = MagicMock()
            mock_session_dir.__truediv__.return_value = mock_claude_md
            mock_claude_md.exists.return_value = False

            _Handler._api_onboarding_instructions(self.handler, {"session_id": ["ws1"]})
            self.handler._send_json.assert_called_with({"ok": False, "error": "Instructions not found"}, status=404)

            # IOError
            mock_claude_md.exists.return_value = True
            mock_claude_md.read_text.side_effect = OSError("Read error")
            _Handler._api_onboarding_instructions(self.handler, {"session_id": ["ws1"]})
            self.handler._send_json.assert_called_with({"ok": False, "error": "Read error"}, status=500)
