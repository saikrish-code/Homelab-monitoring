#!/usr/bin/env python3
"""Nagios email notifier -> SMTP server (Mailpit in this lab)."""
import argparse
import os
import smtplib
import sys
from datetime import datetime, timezone
from email.message import EmailMessage

LOG = os.environ.get("LAB_LOG", "/var/log/nagios4/lab_notify.log")


def log(msg):
    line = "%s notify_email %s" % (datetime.now(timezone.utc).isoformat(timespec="seconds"), msg)
    print(line)
    try:
        with open(LOG, "a") as fh:
            fh.write(line + "\n")
    except OSError:
        pass


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--kind", choices=["host", "service"], required=True)
    ap.add_argument("--type", required=True)
    ap.add_argument("--host", required=True)
    ap.add_argument("--address", default="")
    ap.add_argument("--service", default="")
    ap.add_argument("--state", required=True)
    ap.add_argument("--output", default="")
    ap.add_argument("--to", default="admin@lab.local")
    ap.add_argument("--datetime", default="")
    a = ap.parse_args()

    target = a.host if a.kind == "host" else "%s/%s" % (a.host, a.service)
    msg = EmailMessage()
    msg["Subject"] = "** %s %s Alert: %s is %s **" % (a.type, a.kind.title(), target, a.state)
    msg["From"] = "nagios@lab.local"
    msg["To"] = a.to or "admin@lab.local"
    msg.set_content(
        "Notification Type: %s\nHost: %s (%s)\nService: %s\nState: %s\nDate/Time: %s\n\nInfo:\n%s\n"
        % (a.type, a.host, a.address, a.service or "-", a.state, a.datetime, a.output)
    )
    try:
        with smtplib.SMTP(os.environ.get("SMTP_HOST", "mailpit"),
                          int(os.environ.get("SMTP_PORT", "1025")), timeout=10) as smtp:
            smtp.send_message(msg)
        log("sent: %s" % msg["Subject"])
    except Exception as exc:
        log("ERROR sending email: %s" % exc)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
