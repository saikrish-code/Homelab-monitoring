# Runbook: nginx fails to start after a config change

- **Alert:** `HTTP`, `Process nginx` and `App Health JSON` CRITICAL on web01 (connection refused / 0 processes)
- **Drill:** `scenarios/break-it.sh bad-config` / `bad-config-fix`
- **Severity:** P2
- **Owner:** Linux Support / change author

## Diagnosis
1. `docker exec web01 supervisorctl -c /etc/supervisord-lab.conf status` -> nginx `FATAL`/`BACKOFF`
2. `docker exec web01 nginx -t` -> names the file and line (here `/etc/nginx/conf.d/broken.conf`)
3. What changed recently? `docker exec web01 ls -lt /etc/nginx/conf.d/`

## Resolution
1. Fix or remove the offending file: `docker exec web01 rm -f /etc/nginx/conf.d/broken.conf`
2. Re-validate: `docker exec web01 nginx -t`
3. Start nginx: `docker exec web01 supervisorctl -c /etc/supervisord-lab.conf start nginx`

## Verification
- `nginx -t` reports `syntax is ok`; `curl -s http://localhost:8081/health` returns ok.
- Nagios checks OK; incidents resolved.

## Prevention
- Always run `nginx -t` before reloading. Keep config in version control and review changes.

## Escalation
- Cannot identify the bad change within 15 min -> escalate to the change author / application owner.
