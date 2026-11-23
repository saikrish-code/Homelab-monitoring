#!/usr/bin/env bash
# Run one outage drill end to end against the live stack and report timings.
#   scripts/drill.sh <break> <fix> <detect-regex> <recover-regex>
# e.g. scripts/drill.sh db-crash db-fix 'SERVICE ALERT: db01;MySQL;CRITICAL;HARD' 'SERVICE ALERT: db01;MySQL;OK'
#      scripts/drill.sh web-down web-up 'HOST ALERT: web01;DOWN;HARD' 'HOST ALERT: web01;UP'
# Passes if Nagios logs a line matching <detect-regex> after the break and one matching
# <recover-regex> after the fix; then prints what the email/incident bridge logged.
# DRILL_HOLD (default 15s) is how long the fault is held after detection; use ~90 for
# host-level drills so the host reaches HARD DOWN and notifications fire.
set -uo pipefail
export MSYS_NO_PATHCONV=1
BREAK="$1"; FIX="$2"; DETECT="$3"; RECOVER="$4"
HOLD="${DRILL_HOLD:-15}"
TIMEOUT="${DRILL_TIMEOUT:-420}"
cd "$(dirname "$0")/../homelab-monitoring"

nlog() { docker exec mon01 cat /var/log/nagios4/nagios.log; }
wait_for() {  # $1 = grep -E pattern, matched only against alerts newer than $T0
  local end=$((SECONDS + TIMEOUT))
  while [ $SECONDS -lt $end ]; do
    if nlog | awk -v t="$T0" -F'[][]' '$2>=t' | grep -E "$1" >/dev/null; then return 0; fi
    sleep 10
  done
  return 1
}

T0=$(docker exec mon01 date +%s)
S=$SECONDS
echo "[drill] break: $BREAK"
bash scenarios/break-it.sh "$BREAK"
if wait_for "$DETECT"; then
  echo "[drill] DETECTED after $((SECONDS - S))s"
else
  echo "[drill] FAIL: not detected within ${TIMEOUT}s"; bash scenarios/break-it.sh "$FIX" || true; exit 1
fi
sleep "$HOLD"
echo "[drill] fix: $FIX"
T0=$(docker exec mon01 date +%s)
S=$SECONDS
bash scenarios/break-it.sh "$FIX"
if wait_for "$RECOVER"; then
  echo "[drill] RECOVERED after $((SECONDS - S))s"
else
  echo "[drill] FAIL: no recovery within ${TIMEOUT}s"; exit 1
fi
sleep 20
echo "[drill] bridge + email log (last 14):"
docker exec mon01 tail -n 14 /var/log/nagios4/lab_notify.log | cut -c1-200
echo "[drill] PASS"
