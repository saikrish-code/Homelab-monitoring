# Runbook: sustained high CPU load

- **Alert:** `CPU Load` WARNING/CRITICAL on web01 (load average 1/5/15 min)
- **Drill:** `scenarios/break-it.sh cpu-load` / `cpu-fix` (stress-ng, 3 workers per core, 10 min max)
- **Severity:** P3 (WARNING), P2 (CRITICAL)
- **Owner:** Linux Support
- **Lab caveat:** containers share the Docker host kernel, so load average reflects the whole Docker host,
  not only web01. db01 `CPU Load` may alert too, and unrelated host activity can trip it.

## Diagnosis
1. `docker exec web01 uptime` and `docker exec web01 top -b -n1 | head -15`
2. Which process? (`stress-ng` in the drill; in real life a runaway worker or traffic spike.)
3. Is it one host or all? Compare with `docker exec db01 uptime`.

## Resolution
1. Stop the offender: `docker exec web01 pkill stress-ng`
2. If legitimate load: scale out or tune the application; do not just kill production workers.

## Verification
- `uptime` 1-min load drops back below the warning threshold (takes a few minutes: the 5/15-min averages decay slowly).
- Nagios `CPU Load` OK; incident resolved.

## Escalation
- Load persists with no obvious process -> application owner / capacity planning.
