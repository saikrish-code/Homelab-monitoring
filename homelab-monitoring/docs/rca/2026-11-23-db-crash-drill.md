# RCA: db01 MariaDB killed (lab drill, 2026-11-23)

| Field | Value |
|---|---|
| Incident # | none (ServiceNow bridge in DRY-RUN mode; correlation keys `db01/MySQL`, `db01/MySQL Query customers rows`, `db01/Process mariadbd`) |
| Date | 2026-11-23 |
| Duration | about 2m 15s from fault to full recovery (~07:43:00 - 07:45:35 UTC) |
| Severity | P1 (data tier down) - simulated |
| Author | drill operator |
| Source | `scenarios/break-it.sh db-crash` then `db-fix`, driven by `scripts/drill.sh` |

## Summary
In a planned drill, `mariadbd` on db01 was killed with `kill -9`. Nagios detected the outage on three
checks, sent PROBLEM emails to Mailpit and invoked the ServiceNow bridge (dry-run). MariaDB was restarted
through supervisord and all three checks recovered, with RECOVERY emails and bridge calls. No data loss
(the `customers` query returned its 5 rows after recovery). This is a simulated fault, not a production
incident.

## Timeline (UTC, from `nagios.log` and `lab_notify.log`)
| Time | Event |
|---|---|
| ~07:43:00 | Fault introduced: `docker exec db01 pkill -9 mariadbd` |
| 07:43:16 | `MySQL` CRITICAL (SOFT 1): connection refused (111) |
| 07:43:26 | `MySQL Query customers rows` CRITICAL (SOFT 1) |
| 07:43:35 | `Process mariadbd` CRITICAL (SOFT 1): 0 processes |
| 07:44:16 | `MySQL` CRITICAL HARD (attempt 2); notification sent, bridge called |
| 07:44:26 | `MySQL Query customers rows` HARD; notified |
| 07:44:35 | `Process mariadbd` HARD; notified |
| ~07:44:35 | Fix applied: `supervisorctl start mariadb` (`db-fix`) |
| 07:45:16 | `MySQL` OK (HARD); RECOVERY mail + bridge call |
| 07:45:26 | `MySQL Query customers rows` OK; returned 5 rows |
| 07:45:35 | `Process mariadbd` OK; all recovered |

Detection to HARD took about 74 s (check interval 1 min, 2 attempts); recovery was confirmed about 44 s
after the restart, bounded by the 1-minute check interval.

## Root cause (5 Whys)
1. Why did the site's data tier fail? `mariadbd` was not running.
2. Why was it not running? It was killed with SIGKILL (the drill).
3. Why did it not restart by itself? db01's supervisord entry has `autorestart=false` by design,
   so the drill outage persists until an operator acts.
4. Why was a SIGKILL able to take the service down? Nothing restarts or fails over the database;
   there is a single instance.
5. Why single instance? Lab scope. **Root cause:** single, non-self-healing database instance.

## What went well / what did not
- Went well: all three related checks detected the fault within ~75 s of HARD; emails and bridge
  calls fired for each; data intact after InnoDB crash recovery.
- Did not: three separate alerts (three incidents in ServiceNow) for one fault; no correlation or
  parent/child grouping. Nagios macro sanitisation strips apostrophes from output (`Can't` -> `Cant`).

## Corrective and preventive actions
| Action | Owner | Due |
|---|---|---|
| Group MySQL/process/query alerts into one incident (e.g. correlate on host, or add service dependencies) | Monitoring | open |
| Enable `autorestart=true` with a backoff in production-like setups, keep alerting on restarts | Platform | open |
| Add replication or backups for a real database tier | DBA | open |

## Lessons learned
- A check interval of 1 minute with 2 attempts means about 1-2 minutes before notification.
- Drills should hold a fault long enough to reach HARD state; a host that recovers while still SOFT
  generates no notification (observed in an early net-cut run).
