# Runbook: db01 MariaDB down

- **Alert:** `MySQL`, `MySQL Query customers rows` and `Process mariadbd` CRITICAL on db01
- **Drill:** `scenarios/break-it.sh db-crash` / `db-fix`
- **Severity:** P1 (data tier down)
- **Owner:** Database Support

## Diagnosis
1. Is db01 itself up? `docker ps --filter name=db01`
2. Process state: `docker exec db01 supervisorctl -c /etc/supervisord-lab.conf status`
3. Why did it die? `docker logs --tail 80 db01` (OOM, disk full, corrupted InnoDB, bad config)
4. Disk space: `docker exec db01 df -h /var/lib/mysql`

## Resolution
1. Start it: `docker exec db01 supervisorctl -c /etc/supervisord-lab.conf start mariadb`
2. Watch recovery in `docker logs -f db01` (InnoDB crash recovery after kill -9 can take a few seconds).
3. If it will not start: do not delete data files; escalate.

## Verification
- `docker exec db01 mariadb -uroot -p"$MARIADB_ROOT_PASSWORD" -e 'SELECT COUNT(*) FROM labdb.customers'`
- Nagios `MySQL`, `MySQL Query customers rows`, `Process mariadbd` OK; incidents resolved.

## Escalation
- Crash recurs, or recovery fails -> DBA on call. Capture logs before restarting again.
