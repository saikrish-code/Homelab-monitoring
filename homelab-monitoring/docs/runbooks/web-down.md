# Runbook: web01 host DOWN

- **Alert:** `Host web01 is DOWN` (Nagios host check, ping); every web01 service goes UNREACHABLE/CRITICAL
- **Drill:** `scenarios/break-it.sh web-down` / `web-up`
- **Severity:** P1 (whole web tier gone)
- **Owner:** Infrastructure

## Diagnosis
1. Is the container running? `docker ps -a --filter name=web01` (Exited = stopped or crashed)
2. Why did it stop? `docker logs --tail 50 web01` and `docker inspect -f '{{.State.ExitCode}} {{.State.OOMKilled}}' web01`
3. If running but unreachable, see the net-cut runbook.
4. Do other hosts still work (`db01` UP)? If yes the fault is isolated to web01.

## Resolution
1. `docker start web01` (or `scenarios/break-it.sh web-up`)
2. If it will not start: `docker compose up -d web01` and read the build/start error.
3. Note `/data` is tmpfs: files there are lost on restart (expected for the lab).

## Verification
- `docker exec mon01 /usr/lib/nagios/plugins/check_host -H 172.20.0.11` -> `OK`
- `curl -s http://localhost:8081/health` returns `{"status":"ok",...}`
- Nagios: web01 UP, services OK; the incident `web01/HOST` auto-resolves; RECOVERY mail in Mailpit.

## Escalation
- Container will not start after 2 attempts, or OOMKilled -> escalate to platform owner.
