# Runbook: web01 /data filling up

- **Alert:** `Disk /data` WARNING (< 20% free) then CRITICAL (< 10% free) on web01
- **Drill:** `scenarios/break-it.sh disk-fill` / `disk-fix` (creates `/data/fill.bin`, 95 MB)
- **Severity:** P3 at WARNING, P2 at CRITICAL (writes will start failing)
- **Owner:** Linux Support

## Diagnosis
1. `docker exec web01 df -h /data`
2. Largest consumers: `docker exec web01 du -ah /data | sort -rh | head`
3. Is something still writing? `docker exec web01 ls -l --time-style=full-iso /data`

## Resolution
1. Remove the offending file (here `/data/fill.bin`): `docker exec web01 rm -f /data/fill.bin`
2. If it is legitimate growth: rotate/compress logs, or raise the volume size.

## Verification
- `df -h /data` shows > 20% free; Nagios `Disk /data` OK; incident resolved.

## Prevention
- Log rotation, alert at WARNING (already configured), capacity review.

## Escalation
- Cannot free space safely -> storage owner.
