"""Minimal in-memory mock of the ServiceNow Table API (incident) for bridge tests."""
import base64
import json
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import parse_qs, urlparse

USER, PASS = "mockuser", "mockpass"


class State:
    def __init__(self):
        self.incidents = []
        self.requests = []
        self.reject_resolve = False


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def _send(self, code, obj):
        data = json.dumps(obj).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def _auth(self):
        exp = "Basic " + base64.b64encode(("%s:%s" % (USER, PASS)).encode()).decode()
        if self.headers.get("Authorization") != exp:
            self._send(401, {"error": {"message": "User Not Authenticated"}})
            return False
        return True

    def _body(self):
        n = int(self.headers.get("Content-Length", 0))
        return json.loads(self.rfile.read(n) or b"{}")

    def do_GET(self):
        st = self.server.state
        st.requests.append(("GET", self.path))
        if not self._auth():
            return
        q = parse_qs(urlparse(self.path).query).get("sysparm_query", [""])[0]
        corr, states = None, []
        for term in q.split("^"):
            if term.startswith("correlation_id="):
                corr = term.split("=", 1)[1]
            elif term.startswith("stateIN"):  # ServiceNow IN syntax has no "="
                states = term[len("stateIN"):].split(",")
        rows = [i for i in st.incidents if i.get("correlation_id") == corr and i["state"] in states]
        self._send(200, {"result": rows[:1]})

    def do_POST(self):
        st = self.server.state
        body = self._body()
        st.requests.append(("POST", self.path, body))
        if not self._auth():
            return
        n = len(st.incidents) + 1
        inc = dict(body, sys_id="sys%04d" % n, number="INC%07d" % n, state="1", work_notes=[])
        st.incidents.append(inc)
        self._send(201, {"result": inc})

    def do_PATCH(self):
        st = self.server.state
        body = self._body()
        st.requests.append(("PATCH", self.path, body))
        if not self._auth():
            return
        sid = self.path.rstrip("/").split("/")[-1].split("?")[0]
        for inc in st.incidents:
            if inc["sys_id"] == sid:
                if body.get("state") == "6" and st.reject_resolve:
                    self._send(400, {"error": {"message": "invalid close_code"}})
                    return
                note = body.pop("work_notes", None)
                if note:
                    inc["work_notes"].append(note)
                inc.update(body)
                self._send(200, {"result": inc})
                return
        self._send(404, {"error": {"message": "not found"}})


def start(port=0):
    srv = HTTPServer(("127.0.0.1", port), Handler)
    srv.state = State()
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv


if __name__ == "__main__":
    s = start(8099)
    print("mock ServiceNow on http://127.0.0.1:8099 (user=%s)" % USER)
    threading.Event().wait()
