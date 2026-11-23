"""Exit-code and perfdata tests for check_json_status.py."""
import json
import os
import subprocess
import sys
import threading
import time
import unittest
from http.server import BaseHTTPRequestHandler, HTTPServer

PROJECT = os.environ.get("PROJECT_DIR", os.path.join(os.path.dirname(__file__), "..", "homelab-monitoring"))
PLUGIN = os.path.join(PROJECT, "nagios", "plugins", "check_json_status.py")


class H(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def do_GET(self):
        if self.path == "/ok":
            body = json.dumps({"status": "ok"})
        elif self.path == "/degraded":
            body = json.dumps({"status": "degraded"})
        elif self.path == "/bad":
            body = json.dumps({"status": "down"})
        elif self.path == "/notjson":
            body = "<html>hi</html>"
        elif self.path == "/slow":
            time.sleep(0.4)
            body = json.dumps({"status": "ok"})
        else:
            self.send_response(500)
            self.end_headers()
            return
        self.send_response(200)
        self.end_headers()
        self.wfile.write(body.encode())


class PluginTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.srv = HTTPServer(("127.0.0.1", 0), H)
        cls.port = cls.srv.server_address[1]
        threading.Thread(target=cls.srv.serve_forever, daemon=True).start()

    @classmethod
    def tearDownClass(cls):
        cls.srv.shutdown()
        cls.srv.server_close()

    def run_plugin(self, path, *extra):
        p = subprocess.run(
            [sys.executable, "-I", PLUGIN, "-u", "http://127.0.0.1:%d%s" % (self.port, path), *extra],
            capture_output=True, text=True)
        return p.returncode, p.stdout

    def test_ok_with_perfdata(self):
        rc, out = self.run_plugin("/ok")
        self.assertEqual(rc, 0)
        self.assertIn("JSON OK", out)
        self.assertRegex(out, r"\| time=\d+\.\d{3}s;;;0")

    def test_warning_on_degraded(self):
        self.assertEqual(self.run_plugin("/degraded")[0], 1)

    def test_warning_on_slow(self):
        rc, out = self.run_plugin("/slow", "-w", "0.2", "-c", "5")
        self.assertEqual(rc, 1)
        self.assertIn("time=", out)

    def test_critical_on_slow(self):
        self.assertEqual(self.run_plugin("/slow", "-c", "0.2")[0], 2)

    def test_critical_wrong_value(self):
        self.assertEqual(self.run_plugin("/bad")[0], 2)

    def test_critical_http_error(self):
        self.assertEqual(self.run_plugin("/500")[0], 2)

    def test_critical_connection_refused(self):
        p = subprocess.run([sys.executable, "-I", PLUGIN, "-u", "http://127.0.0.1:1/x", "-t", "2"],
                           capture_output=True, text=True)
        self.assertEqual(p.returncode, 2)

    def test_unknown_not_json(self):
        self.assertEqual(self.run_plugin("/notjson")[0], 3)

    def test_custom_key_expect(self):
        self.assertEqual(self.run_plugin("/ok", "-k", "missing", "-e", "x")[0], 2)


if __name__ == "__main__":
    unittest.main()
