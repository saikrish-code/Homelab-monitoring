# Runbook: web01 "HTTP" / "Process nginx" CRITICAL

- **Alert:** `HTTP CRITICAL - Connection refused` and/or `Process nginx CRITICAL: 0 processes`
- **Severity:** P2 (customer-facing site down)
- **Impact:** web site unavailable; database unaffected
- **Owner:** Linux Support

## Diagnosis
1. Is the host up? `docker ps --filter name=web01`
2. Is nginx running? `docker exec web01 supervisorctl -c /etc/supervisord-lab.conf status`
3. Why did it stop? `docker logs --tail 50 web01`
4. Is the config valid? `docker exec web01 nginx -t`

## Resolution
1. If config invalid: fix or remove the offending file in `/etc/nginx/conf.d/`.
2. Start nginx: `docker exec web01 supervisorctl -c /etc/supervisord-lab.conf start nginx`

## Verification
- `curl -s http://localhost:8081/health` returns `{"status":"ok",...}`
- Nagios HTTP + Process nginx back to OK; ServiceNow incident resolved.

## Escalation
- Not fixed within 15 min -> escalate to application owner.
