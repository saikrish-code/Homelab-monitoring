#!/usr/bin/env python3
"""Nagios -> ServiceNow incident bridge (REST Table API).

PROBLEM  : create an incident, or add a work note (and re-rate) if one is already open
RECOVERY : add a work note and resolve the open incident
Other notification types (ACKNOWLEDGEMENT, FLAPPING*, DOWNTIME*) are ignored.

Dedupe key = correlation_id = "<host>/<service>" (or "<host>/HOST").
Without SNOW_INSTANCE/SNOW_USER/SNOW_PASS the script runs in DRY-RUN mode and only logs.
"""
import argparse
import os
import sys
import time
from datetime import datetime, timezone

import requests

LOG = os.environ.get("LAB_LOG", "/var/log/nagios4/lab_notify.log")

# Nagios state -> (impact, urgency).  Priority = f(impact, urgency) inside ServiceNow.
SEVERITY = {
    "CRITICAL": (2, 1),
    "DOWN": (2, 1),
    "UNREACHABLE": (2, 1),
    "WARNING": (3, 2),
    "UNKNOWN": (3, 3),
}
OPEN_STATES = "1,2,3"  # New, In Progress, On Hold


def now():
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")


def log(msg):
    line = "%s snow_incident %s" % (datetime.now(timezone.utc).isoformat(timespec="seconds"), msg)
    print(line)
    try:
        with open(LOG, "a") as fh:
            fh.write(line + "\n")
    except OSError:
        pass


def snow_config():
    inst = os.environ.get("SNOW_INSTANCE", "").strip()
    user = os.environ.get("SNOW_USER", "")
    pw = os.environ.get("SNOW_PASS", "")
    if not (inst and user and pw):
        return None
    if inst.startswith("http"):
        base = inst
    elif "." in inst:
        base = "https://" + inst
    else:
        base = "https://%s.service-now.com" % inst
    return base.rstrip("/"), user, pw


def request(sess, method, url, **kw):
    """HTTP call with one retry on network errors."""
    last = None
    for attempt in (1, 2):
        try:
            return sess.request(method, url, timeout=20, **kw)
        except requests.RequestException as exc:
            last = exc
            log("network error (attempt %d): %s" % (attempt, exc))
            time.sleep(2)
    raise last


def find_open(sess, base, key):
    r = request(sess, "GET", base + "/api/now/table/incident", params={
        "sysparm_query": "correlation_id=%s^stateIN%s" % (key.replace("^", "_"), OPEN_STATES),
        "sysparm_fields": "sys_id,number,state",
        "sysparm_limit": 1,
    })
    if r.status_code == 401:
        raise RuntimeError("ServiceNow authentication failed (HTTP 401) - check SNOW_USER/SNOW_PASS")
    r.raise_for_status()
    rows = r.json().get("result", [])
    return rows[0] if rows else None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--kind", choices=["host", "service"], required=True)
    ap.add_argument("--type", required=True)
    ap.add_argument("--host", required=True)
    ap.add_argument("--address", default="")
    ap.add_argument("--service", default="")
    ap.add_argument("--state", required=True)
    ap.add_argument("--output", default="")
    a = ap.parse_args()

    if a.type not in ("PROBLEM", "RECOVERY"):
        log("ignoring notification type %s for %s" % (a.type, a.host))
        return 0

    is_service = a.kind == "service"
    key = "%s/%s" % (a.host, a.service) if is_service else "%s/HOST" % a.host
    label = "%s/%s" % (a.host, a.service) if is_service else "Host %s" % a.host
    impact, urgency = SEVERITY.get(a.state.upper(), (3, 3))

    cfg = snow_config()
    if cfg is None:
        log("DRY-RUN %s %s state=%s key=%s output=%s" % (a.type, label, a.state, key, a.output))
        return 0

    base, user, pw = cfg
    sess = requests.Session()
    sess.auth = (user, pw)
    sess.headers.update({"Accept": "application/json", "Content-Type": "application/json"})

    try:
        existing = find_open(sess, base, key)

        if a.type == "PROBLEM":
            note = "[%s] %s is %s: %s" % (now(), label, a.state, a.output)
            if existing:
                r = request(sess, "PATCH", "%s/api/now/table/incident/%s" % (base, existing["sys_id"]),
                            json={"work_notes": note, "impact": str(impact), "urgency": str(urgency)})
                r.raise_for_status()
                log("updated %s (%s): %s" % (existing["number"], key, a.state))
            else:
                body = {
                    "short_description": "[Nagios] %s is %s" % (label, a.state),
                    "description": "Nagios alert\nHost: %s (%s)\nService: %s\nState: %s\nOutput: %s\nDetected: %s"
                                   % (a.host, a.address, a.service or "-", a.state, a.output, now()),
                    "impact": str(impact),
                    "urgency": str(urgency),
                    "category": "software" if is_service else "network",
                    "correlation_id": key,
                }
                group = os.environ.get("SNOW_ASSIGNMENT_GROUP_SYSID", "").strip()
                if group:
                    body["assignment_group"] = group
                r = request(sess, "POST", base + "/api/now/table/incident", json=body)
                r.raise_for_status()
                log("created %s for %s" % (r.json()["result"]["number"], key))

        else:  # RECOVERY
            if not existing:
                log("RECOVERY for %s but no open incident found - nothing to do" % key)
                return 0
            url = "%s/api/now/table/incident/%s" % (base, existing["sys_id"])
            note = "[%s] Monitoring reports %s recovered (%s): %s" % (now(), label, a.state, a.output)
            resolve = {
                "work_notes": note,
                "state": "6",
                "close_code": "Solved (Permanently)",
                "close_notes": "Auto-resolved: Nagios reports recovery. %s" % a.output,
            }
            r = request(sess, "PATCH", url, json=resolve)
            if r.status_code >= 400:
                # Resolution code values differ between releases -> fall back to a note
                log("resolve failed (HTTP %s): %s - adding work note only" % (r.status_code, r.text[:200]))
                r = request(sess, "PATCH", url, json={"work_notes": note})
                r.raise_for_status()
            else:
                log("resolved %s (%s)" % (existing["number"], key))

    except Exception as exc:
        log("ERROR %s %s: %s" % (a.type, key, exc))
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
