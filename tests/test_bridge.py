"""ServiceNow bridge tests against the in-memory mock API (and dry-run mode)."""
import os
import subprocess
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(__file__))
import mock_snow  # noqa: E402

PROJECT = os.environ.get("PROJECT_DIR", os.path.join(os.path.dirname(__file__), "..", "homelab-monitoring"))
BRIDGE = os.path.join(PROJECT, "integration", "snow_incident.py")


class BridgeTest(unittest.TestCase):
    def setUp(self):
        self.srv = mock_snow.start()
        self.st = self.srv.state
        fd, self.log = tempfile.mkstemp(suffix=".log")
        os.close(fd)

    def tearDown(self):
        self.srv.shutdown()
        self.srv.server_close()
        os.unlink(self.log)

    def env(self, live=True):
        e = {k: v for k, v in os.environ.items() if not k.startswith("SNOW_")}
        e["LAB_LOG"] = self.log
        if live:
            e.update(SNOW_INSTANCE="http://127.0.0.1:%d" % self.srv.server_address[1],
                     SNOW_USER=mock_snow.USER, SNOW_PASS=mock_snow.PASS)
        return e

    def run_bridge(self, kind, typ, host, state, service="", output="out", live=True, env_extra=None):
        args = [sys.executable, "-I", BRIDGE, "--kind=" + kind, "--type=" + typ, "--host=" + host,
                "--address=1.2.3.4", "--state=" + state, "--output=" + output]
        if service:
            args.append("--service=" + service)
        e = self.env(live)
        e.update(env_extra or {})
        return subprocess.run(args, capture_output=True, text=True, env=e)

    def test_dry_run_creates_nothing(self):
        p = self.run_bridge("service", "PROBLEM", "web01", "CRITICAL", "HTTP", live=False)
        self.assertEqual(p.returncode, 0)
        self.assertIn("DRY-RUN", p.stdout)
        self.assertEqual(self.st.requests, [])

    def test_create_incident(self):
        p = self.run_bridge("service", "PROBLEM", "web01", "CRITICAL", "HTTP")
        self.assertEqual(p.returncode, 0, p.stdout)
        self.assertEqual(len(self.st.incidents), 1)
        inc = self.st.incidents[0]
        self.assertEqual(inc["correlation_id"], "web01/HTTP")
        self.assertEqual((inc["impact"], inc["urgency"]), ("2", "1"))
        self.assertIn("[Nagios] web01/HTTP is CRITICAL", inc["short_description"])

    def test_no_duplicate_on_repeat(self):
        self.run_bridge("service", "PROBLEM", "web01", "CRITICAL", "HTTP")
        self.run_bridge("service", "PROBLEM", "web01", "WARNING", "HTTP")
        self.assertEqual(len(self.st.incidents), 1)
        inc = self.st.incidents[0]
        self.assertEqual(len(inc["work_notes"]), 1)
        self.assertEqual((inc["impact"], inc["urgency"]), ("3", "2"))

    def test_different_services_get_separate_incidents(self):
        self.run_bridge("service", "PROBLEM", "web01", "CRITICAL", "HTTP")
        self.run_bridge("service", "PROBLEM", "web01", "CRITICAL", "Process nginx")
        self.assertEqual(len(self.st.incidents), 2)

    def test_resolve_on_recovery(self):
        self.run_bridge("service", "PROBLEM", "web01", "CRITICAL", "HTTP")
        p = self.run_bridge("service", "RECOVERY", "web01", "OK", "HTTP")
        self.assertEqual(p.returncode, 0, p.stdout)
        inc = self.st.incidents[0]
        self.assertEqual(inc["state"], "6")
        self.assertIn("recovered", inc["work_notes"][-1])

    def test_new_problem_after_resolve_creates_new_incident(self):
        self.run_bridge("service", "PROBLEM", "web01", "CRITICAL", "HTTP")
        self.run_bridge("service", "RECOVERY", "web01", "OK", "HTTP")
        self.run_bridge("service", "PROBLEM", "web01", "CRITICAL", "HTTP")
        self.assertEqual(len(self.st.incidents), 2)

    def test_recovery_without_incident_is_noop(self):
        p = self.run_bridge("service", "RECOVERY", "web01", "OK", "HTTP")
        self.assertEqual(p.returncode, 0)
        self.assertEqual(self.st.incidents, [])

    def test_resolve_failure_falls_back_to_note(self):
        self.run_bridge("service", "PROBLEM", "web01", "CRITICAL", "HTTP")
        self.st.reject_resolve = True
        p = self.run_bridge("service", "RECOVERY", "web01", "OK", "HTTP")
        self.assertEqual(p.returncode, 0, p.stdout)
        inc = self.st.incidents[0]
        self.assertEqual(inc["state"], "1")
        self.assertEqual(len(inc["work_notes"]), 1)

    def test_host_down_and_recovery(self):
        self.run_bridge("host", "PROBLEM", "db01", "DOWN")
        self.assertEqual(self.st.incidents[0]["correlation_id"], "db01/HOST")
        self.assertEqual(self.st.incidents[0]["category"], "network")
        self.run_bridge("host", "RECOVERY", "db01", "UP")
        self.assertEqual(self.st.incidents[0]["state"], "6")

    def test_ignored_notification_types(self):
        for t in ("ACKNOWLEDGEMENT", "FLAPPINGSTART", "DOWNTIMESTART"):
            p = self.run_bridge("service", t, "web01", "CRITICAL", "HTTP")
            self.assertEqual(p.returncode, 0)
        self.assertEqual(self.st.requests, [])

    def test_bad_credentials_exit_nonzero(self):
        p = self.run_bridge("service", "PROBLEM", "web01", "CRITICAL", "HTTP", env_extra={"SNOW_PASS": "wrong"})
        self.assertEqual(p.returncode, 1)
        self.assertIn("authentication failed", p.stdout)

    def test_assignment_group(self):
        self.run_bridge("service", "PROBLEM", "web01", "CRITICAL", "HTTP",
                        env_extra={"SNOW_ASSIGNMENT_GROUP_SYSID": "abc123"})
        self.assertEqual(self.st.incidents[0]["assignment_group"], "abc123")


if __name__ == "__main__":
    unittest.main()
