#!/usr/bin/env python3
"""Lab control console: one page to see status and run outage drills.

Reads Nagios status.dat via `docker exec mon01`, lists containers, tails the alert and
ServiceNow-bridge logs, lists Mailpit mail, and runs the scenarios in /scenarios/break-it.sh.
Protected by HTTP basic auth (nagiosadmin / NAGIOSADMIN_PASS). Needs the Docker socket,
which is root-equivalent on the host: lab use only, published on 127.0.0.1 only.
"""
import base64
import hmac
import json
import os
import subprocess
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

PASS = os.environ["NAGIOSADMIN_PASS"]
SCENARIOS = {
    "nginx-crash": "nginx-fix", "bad-config": "bad-config-fix", "db-crash": "db-fix",
    "disk-fill": "disk-fix", "cpu-load": "cpu-fix", "net-cut": "net-fix", "web-down": "web-up",
}
ALLOWED = set(SCENARIOS) | set(SCENARIOS.values()) | {"all-fixed"}
STATES_SVC = {"0": "OK", "1": "WARNING", "2": "CRITICAL", "3": "UNKNOWN"}
STATES_HOST = {"0": "UP", "1": "DOWN", "2": "UNREACHABLE"}


def sh(args, timeout=20):
    try:
        p = subprocess.run(args, capture_output=True, text=True, timeout=timeout)
        return (p.stdout + p.stderr).strip()
    except Exception as exc:  # noqa: BLE001
        return "error: %s" % exc


def nagios_status():
    raw = sh(["docker", "exec", "mon01", "cat", "/var/cache/nagios4/status.dat"])
    hosts, services, cur, kind = [], [], None, None
    for line in raw.splitlines():
        line = line.strip()
        if line.endswith("{") and line.split()[0] in ("hoststatus", "servicestatus"):
            kind, cur = line.split()[0], {}
        elif line == "}" and cur is not None:
            if kind == "hoststatus":
                hosts.append({"host": cur.get("host_name"), "state": STATES_HOST.get(cur.get("current_state"), "?"),
                              "output": cur.get("plugin_output", ""), "hard": cur.get("state_type") == "1"})
            elif kind == "servicestatus":
                services.append({"host": cur.get("host_name"), "service": cur.get("service_description"),
                                 "state": STATES_SVC.get(cur.get("current_state"), "?"),
                                 "output": cur.get("plugin_output", ""), "hard": cur.get("state_type") == "1",
                                 "attempt": "%s/%s" % (cur.get("current_attempt"), cur.get("max_attempts"))})
            cur = None
        elif cur is not None and "=" in line:
            k, v = line.split("=", 1)
            cur[k] = v
    return hosts, services


def containers():
    out = sh(["docker", "ps", "-a", "--filter", "label=com.docker.compose.project=homelab",
              "--format", "{{.Names}}|{{.Status}}"])
    return [dict(zip(("name", "status"), l.split("|", 1))) for l in out.splitlines() if "|" in l]


def mail():
    try:
        with urllib.request.urlopen("http://mailpit:8025/api/v1/messages?limit=8", timeout=5) as r:
            d = json.load(r)
        return {"total": d.get("total", 0), "items": [{"subject": m["Subject"], "at": m["Created"][:19]}
                                                      for m in d.get("messages", [])]}
    except Exception as exc:  # noqa: BLE001
        return {"total": 0, "items": [], "error": str(exc)}


def api_status():
    hosts, services = nagios_status()
    alerts = sh(["docker", "exec", "mon01", "sh", "-c",
                 "grep -E 'ALERT' /var/log/nagios4/nagios.log | tail -n 25"])
    bridge = sh(["docker", "exec", "mon01", "sh", "-c",
                 "tail -n 25 /var/log/nagios4/lab_notify.log 2>/dev/null"])
    snow = sh(["docker", "exec", "mon01", "sh", "-c", "[ -n \"$SNOW_INSTANCE\" ] && echo live || echo dry-run"])
    return {"hosts": hosts, "services": services, "containers": containers(), "mail": mail(),
            "alerts": alerts.splitlines()[::-1], "bridge": bridge.splitlines()[::-1], "snow_mode": snow,
            "scenarios": SCENARIOS}


PAGE = r"""<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Homelab Console</title><style>
:root{--bg:#f6f7f9;--fg:#1c2330;--card:#fff;--mut:#667085;--bd:#e2e5ea;--ok:#1a7f4b;--warn:#b7791f;--crit:#c0362c;--unk:#6b46c1}
@media(prefers-color-scheme:dark){:root{--bg:#12151b;--fg:#e6e9ef;--card:#1b2029;--mut:#98a2b3;--bd:#2b3340;--ok:#4cc38a;--warn:#e0b04a;--crit:#f2776c;--unk:#a78bfa}}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--fg);font:14px/1.45 system-ui,sans-serif}
header{display:flex;flex-wrap:wrap;gap:12px;align-items:center;padding:14px 16px;border-bottom:1px solid var(--bd);background:var(--card)}
h1{font-size:18px;margin:0;flex:1}a{color:inherit}main{padding:16px;display:grid;gap:16px;max-width:1200px;margin:auto}
.card{background:var(--card);border:1px solid var(--bd);border-radius:10px;padding:14px;overflow:auto}
h2{font-size:13px;text-transform:uppercase;letter-spacing:.05em;color:var(--mut);margin:0 0 10px}
.pill{display:inline-block;padding:1px 9px;border-radius:99px;font-size:12px;font-weight:600;border:1px solid currentColor}
.OK,.UP,.running{color:var(--ok)}.WARNING{color:var(--warn)}.CRITICAL,.DOWN,.exited{color:var(--crit)}.UNKNOWN,.UNREACHABLE{color:var(--unk)}
table{width:100%;border-collapse:collapse}td,th{text-align:left;padding:5px 8px;border-bottom:1px solid var(--bd);vertical-align:top}th{color:var(--mut);font-weight:500}
.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:8px}.sum{display:flex;gap:10px;flex-wrap:wrap}
.sum div{padding:8px 14px;border:1px solid var(--bd);border-radius:8px;min-width:90px}.sum b{font-size:22px;display:block}
button{font:inherit;padding:7px 10px;border-radius:8px;border:1px solid var(--bd);background:var(--card);color:var(--fg);cursor:pointer}
button.b{border-color:var(--crit);color:var(--crit)}button.f{border-color:var(--ok);color:var(--ok)}button:disabled{opacity:.5}
.pair{display:flex;flex-direction:column;gap:4px}pre{margin:0;font:12px/1.5 ui-monospace,monospace;white-space:pre-wrap;word-break:break-all;max-height:260px;overflow:auto}
.two{display:grid;grid-template-columns:repeat(auto-fit,minmax(340px,1fr));gap:16px}.mut{color:var(--mut)}
</style></head><body>
<header><h1>Homelab Console</h1><span class="mut" id="upd">loading...</span>
<a href="http://localhost:8080/" target="_blank">Nagios UI</a><a href="http://localhost:8025/" target="_blank">Mailpit</a>
<span class="pill" id="snow"></span></header>
<main>
<div class="card"><h2>Overview</h2><div class="sum" id="sum"></div></div>
<div class="card"><h2>Outage drills (break / fix)</h2><div class="grid" id="drills"></div>
<p class="mut" id="msg" style="margin:10px 0 0"></p>
<button style="margin-top:8px" onclick="run('all-fixed')">Fix everything (all-fixed)</button></div>
<div class="card"><h2>Hosts &amp; services</h2><table id="svc"></table></div>
<div class="two"><div class="card"><h2>Containers</h2><table id="ctr"></table></div>
<div class="card"><h2>Recent mail (Mailpit) <span id="mailn"></span></h2><table id="mail"></table></div></div>
<div class="two"><div class="card"><h2>Nagios alerts (newest first)</h2><pre id="alerts"></pre></div>
<div class="card"><h2>ServiceNow bridge log (newest first)</h2><pre id="bridge"></pre></div></div>
</main><script>
const $=id=>document.getElementById(id);const esc=s=>String(s).replace(/[&<>]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;'}[c]));
const pill=s=>`<span class="pill ${s}">${s}</span>`;
function ts(l){return l.replace(/^\[(\d+)\]/,(m,t)=>new Date(t*1000).toISOString().slice(11,19)+' ')}
async function load(){try{const r=await fetch('/api/status');if(!r.ok)throw r.status;const d=await r.json();
const rows=[...d.hosts.map(h=>({n:h.host,s:'(host)',st:h.state,o:h.output,h:h.hard})),...d.services.map(s=>({n:s.host,s:s.service,st:s.state,o:s.output,h:s.hard,a:s.attempt}))];
const c={OK:0,UP:0,WARNING:0,CRITICAL:0,DOWN:0,UNKNOWN:0,UNREACHABLE:0};rows.forEach(r=>c[r.st]=(c[r.st]||0)+1);
$('sum').innerHTML=[['OK',c.OK+c.UP],['WARNING',c.WARNING],['CRITICAL',c.CRITICAL+c.DOWN],['UNKNOWN',c.UNKNOWN+c.UNREACHABLE]].map(([k,v])=>`<div class="${k}"><b>${v}</b>${k}</div>`).join('');
$('svc').innerHTML='<tr><th>Host</th><th>Check</th><th>State</th><th>Output</th></tr>'+rows.map(r=>`<tr><td>${esc(r.n)}</td><td>${esc(r.s)}</td><td>${pill(r.st)}${r.st!='OK'&&r.st!='UP'&&!r.h?' <span class="mut">soft '+(r.a||'')+'</span>':''}</td><td class="mut">${esc(r.o)}</td></tr>`).join('');
$('ctr').innerHTML=d.containers.map(x=>`<tr><td>${esc(x.name)}</td><td class="${x.status.startsWith('Up')?'running':'exited'}">${esc(x.status)}</td></tr>`).join('');
$('mailn').textContent='('+d.mail.total+' total)';$('mail').innerHTML=d.mail.items.map(m=>`<tr><td class="mut">${m.at.slice(11)}</td><td>${esc(m.subject)}</td></tr>`).join('');
$('alerts').textContent=d.alerts.map(ts).join('\n');$('bridge').textContent=d.bridge.join('\n');
$('snow').textContent='ServiceNow: '+d.snow_mode;$('snow').className='pill '+(d.snow_mode=='live'?'OK':'WARNING');
if(!$('drills').dataset.done){$('drills').dataset.done=1;$('drills').innerHTML=Object.entries(d.scenarios).map(([b,f])=>`<div class="pair"><button class="b" onclick="run('${b}')">Break: ${b}</button><button class="f" onclick="run('${f}')">Fix: ${f}</button></div>`).join('')}
$('upd').textContent='updated '+new Date().toLocaleTimeString()}catch(e){$('upd').textContent='error loading status: '+e}}
async function run(s){const all=document.querySelectorAll('button');all.forEach(b=>b.disabled=true);$('msg').textContent='running '+s+'...';
try{const r=await fetch('/api/run',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({scenario:s})});const d=await r.json();
$('msg').textContent=s+': '+(d.ok?'done':'failed')+' - '+(d.output||'')+' (Nagios needs ~1-2 min to notice)'}catch(e){$('msg').textContent='error: '+e}
all.forEach(b=>b.disabled=false);load()}
load();setInterval(load,5000);
</script></body></html>"""


class H(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def _authed(self):
        h = self.headers.get("Authorization", "")
        if h.startswith("Basic "):
            try:
                user, _, pw = base64.b64decode(h[6:]).decode().partition(":")
                if user == "nagiosadmin" and hmac.compare_digest(pw, PASS):
                    return True
            except Exception:  # noqa: BLE001
                pass
        self.send_response(401)
        self.send_header("WWW-Authenticate", 'Basic realm="Homelab Console"')
        self.end_headers()
        return False

    def _send(self, code, body, ctype):
        data = body.encode()
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        if not self._authed():
            return
        if self.path == "/api/status":
            self._send(200, json.dumps(api_status()), "application/json")
        elif self.path in ("/", "/index.html"):
            self._send(200, PAGE, "text/html; charset=utf-8")
        else:
            self._send(404, "not found", "text/plain")

    def do_POST(self):
        if not self._authed():
            return
        if self.path != "/api/run":
            return self._send(404, "not found", "text/plain")
        try:
            name = json.loads(self.rfile.read(int(self.headers.get("Content-Length", 0)) or 0)).get("scenario")
        except ValueError:
            name = None
        if name not in ALLOWED:  # whitelist: never pass user text to a shell
            return self._send(400, json.dumps({"ok": False, "output": "unknown scenario"}), "application/json")
        p = subprocess.run(["bash", "/scenarios/break-it.sh", name], capture_output=True, text=True, timeout=90)
        out = (p.stdout + p.stderr).strip().splitlines()
        self._send(200, json.dumps({"ok": p.returncode == 0, "output": " ".join(out[-3:])}), "application/json")


if __name__ == "__main__":
    ThreadingHTTPServer(("0.0.0.0", 8090), H).serve_forever()
