#!/usr/bin/env python3
"""Nagios plugin: fetch a JSON endpoint and verify a field equals an expected value.

Exit codes: 0 OK, 1 WARNING (value == --warn-value, or slower than --warn-time),
            2 CRITICAL (fetch failed, wrong value, or slower than --crit-time),
            3 UNKNOWN (not valid JSON).
Perfdata: time=<seconds>s;<warn>;<crit>;0
"""
import argparse
import json
import sys
import time
import urllib.request

OK, WARNING, CRITICAL, UNKNOWN = 0, 1, 2, 3


def fmt(v):
    return "" if v is None else "%g" % v


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("-u", "--url", required=True)
    ap.add_argument("-k", "--key", default="status")
    ap.add_argument("-e", "--expect", default="ok")
    ap.add_argument("-W", "--warn-value", default="degraded",
                    help="field value that maps to WARNING (default: degraded)")
    ap.add_argument("-w", "--warn-time", type=float, default=None, help="warn if response slower than N seconds")
    ap.add_argument("-c", "--crit-time", type=float, default=None, help="critical if response slower than N seconds")
    ap.add_argument("-t", "--timeout", type=float, default=10)
    args = ap.parse_args(argv)

    start = time.time()
    try:
        with urllib.request.urlopen(args.url, timeout=args.timeout) as resp:
            body = resp.read().decode("utf-8", "replace")
    except Exception as exc:  # connection refused, timeout, HTTP 4xx/5xx ...
        print("JSON CRITICAL - cannot fetch %s: %s" % (args.url, exc))
        return CRITICAL
    elapsed = time.time() - start
    perf = "| time=%.3fs;%s;%s;0" % (elapsed, fmt(args.warn_time), fmt(args.crit_time))

    try:
        data = json.loads(body)
    except ValueError:
        print("JSON UNKNOWN - response from %s is not valid JSON %s" % (args.url, perf))
        return UNKNOWN

    value = data.get(args.key) if isinstance(data, dict) else None
    if str(value) != args.expect:
        if str(value) == args.warn_value:
            print("JSON WARNING - %s=%s at %s %s" % (args.key, value, args.url, perf))
            return WARNING
        print("JSON CRITICAL - %s=%r (expected %r) at %s %s" % (args.key, value, args.expect, args.url, perf))
        return CRITICAL
    if args.crit_time is not None and elapsed > args.crit_time:
        print("JSON CRITICAL - %s=%s but response took %.3fs (> %gs) %s" % (args.key, value, elapsed, args.crit_time, perf))
        return CRITICAL
    if args.warn_time is not None and elapsed > args.warn_time:
        print("JSON WARNING - %s=%s but response took %.3fs (> %gs) %s" % (args.key, value, elapsed, args.warn_time, perf))
        return WARNING
    print("JSON OK - %s=%s at %s %s" % (args.key, value, args.url, perf))
    return OK


if __name__ == "__main__":
    sys.exit(main())
