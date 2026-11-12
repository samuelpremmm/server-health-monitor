"""Tests for the web dashboard. They start a real server on a free port using
sample data, so they run on any OS."""

import json
import threading
import unittest
import urllib.error
import urllib.request

from health_monitor import web


class TestWebDashboard(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = web.make_server("127.0.0.1", 0, web.CachedCollector(web.demo_report))
        cls.base = f"http://127.0.0.1:{cls.server.server_address[1]}"
        threading.Thread(target=cls.server.serve_forever, daemon=True).start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()

    def get(self, path):
        with urllib.request.urlopen(self.base + path, timeout=5) as r:
            return r.status, r.headers.get("Content-Type"), r.read()

    def test_dashboard_page(self):
        status, ctype, body = self.get("/")
        self.assertEqual(status, 200)
        self.assertIn("text/html", ctype)
        self.assertIn(b"Server Health Monitor", body)

    def test_api_health(self):
        status, ctype, body = self.get("/api/health")
        self.assertEqual(status, 200)
        self.assertEqual(ctype, "application/json")
        data = json.loads(body)
        self.assertEqual(data["cpu"]["usage_percent"], 40.0)   # from the fixtures
        self.assertEqual(data["memory"]["usage_percent"], 75.0)
        self.assertIn(data["overall_status"], ("OK", "WARNING", "CRITICAL"))
        self.assertIsInstance(data["alerts"], list)

    def test_healthz(self):
        status, _, body = self.get("/healthz")
        self.assertEqual(status, 200)
        self.assertEqual(json.loads(body), {"status": "ok"})

    def test_unknown_path_is_404(self):
        with self.assertRaises(urllib.error.HTTPError) as ctx:
            self.get("/nope")
        self.assertEqual(ctx.exception.code, 404)


class TestCachedCollector(unittest.TestCase):
    def test_caches_within_ttl(self):
        calls = []

        def collect():
            calls.append(1)
            return {"cpu": {"status": "OK"}, "memory": {"status": "OK"},
                    "disks": [], "thresholds": {}}

        cached = web.CachedCollector(collect, ttl=60)
        cached()
        cached()
        self.assertEqual(len(calls), 1)


if __name__ == "__main__":
    unittest.main()
