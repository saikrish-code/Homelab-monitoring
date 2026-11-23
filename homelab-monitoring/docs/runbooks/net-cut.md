# Runbook: web01 unreachable on the network

- **Alert:** web01 Host DOWN (ping fails) while the container is still running
- **Drill:** `scenarios/break-it.sh net-cut` / `net-fix` (disconnects web01 from `homelab_labnet`)
- **Severity:** P1
- **Owner:** Network / Infrastructure

## Diagnosis
1. Container is running but unreachable: `docker ps --filter name=web01` shows Up.
2. Network membership: `docker inspect -f '{{json .NetworkSettings.Networks}}' web01` (empty = detached).
3. From mon01: `docker exec mon01 ping -c2 172.20.0.11` fails; `db01` still answers -> isolated fault.

## Resolution
1. Reattach with its fixed IP: `docker network connect --ip 172.20.0.11 homelab_labnet web01`
   (or `scenarios/break-it.sh net-fix`).
2. Confirm the IP: `docker exec web01 hostname -i` -> `172.20.0.11`.

## Verification
- Ping and NRPE work from mon01; Nagios web01 UP and services OK; incident `web01/HOST` resolved.

## Escalation
- Reconnect fails (address in use, network missing) -> platform owner.
