# HomeLab Monitoring & Incident Response Stack

Dockerised mini data-centre: **Nagios Core** monitors an **nginx** web server and a
**MariaDB** database (agents: NRPE). Alerts are emailed (Mailpit) and turned into
**ServiceNow** incidents through the REST API. Outage drills, runbooks and an RCA complete
the incident-response loop.

```
Nagios (mon01) --checks--> web01 (nginx+NRPE) / db01 (MariaDB+NRPE)
      |-- SMTP --> Mailpit (inbox UI)
      '-- HTTPS REST --> ServiceNow PDI (create / update / resolve incident)
```

## Run

```bash
cp -n .env.example .env 2>/dev/null; docker compose up -d --build
docker compose ps
```

| What | URL |
|---|---|
| Nagios | http://localhost:8080  (user `nagiosadmin`, password = `NAGIOSADMIN_PASS` in `.env`) |
| Mailpit (alert emails) | http://localhost:8025 |
| web01 test site | http://localhost:8081 |

Give Nagios 2-3 minutes for the first full round of checks.

## ServiceNow (free Personal Developer Instance)

1. Request a PDI at developer.servicenow.com and log in at least every few days (idle PDIs are reclaimed).
2. In the instance: **User Administration > Users > New** -> user `nagios.integration`, set a password,
   grant role `itil`.
3. Put `SNOW_INSTANCE` (e.g. `dev12345`), `SNOW_USER`, `SNOW_PASS` into `.env`
   (single-quote the password if it has special characters).
4. `docker compose up -d mon01` to reload the environment.
5. Smoke test:
   ```bash
   docker exec -u nagios mon01 python3 /opt/lab/snow_incident.py \
     --kind=service --type=PROBLEM --host=web01 --service=TEST --state=CRITICAL --output="manual test"
   ```
   Without ServiceNow settings the bridge runs in dry-run mode and only logs.

Bridge log: `docker exec mon01 tail -f /var/log/nagios4/lab_notify.log`

## Outage drills

```bash
./scenarios/break-it.sh            # list scenarios
./scenarios/break-it.sh nginx-crash
# ... detect in Nagios, check the ServiceNow incident, troubleshoot, fix:
./scenarios/break-it.sh nginx-fix
```

Reset everything: `docker compose down -v && docker compose up -d --build`

## Handy commands

```bash
docker compose logs -f mon01                                  # Nagios + Apache logs
docker exec mon01 /usr/lib/nagios/plugins/check_nrpe -H 172.20.0.11 -c check_load
docker exec mon01 /usr/lib/nagios/plugins/check_http -H 172.20.0.11 -u /health
docker exec mon01 /usr/sbin/nagios4 -v /etc/nagios4/nagios.cfg  # validate config
docker exec mon01 supervisorctl -c /etc/supervisord-lab.conf restart nagios
```

## Notes

- CPU load is read from the Docker host kernel, so it reflects host-wide load.
- If NRPE shows "Could not complete SSL handshake", confirm `check_nrpe` and `nrpe` come from
  the same Ubuntu release (they do here) and check `docker compose logs web01`.
- If subnet 172.20.0.0/24 clashes with another Docker network, change it in
  `docker-compose.yml`, `nagios/lab/hosts.cfg` and both `nrpe.cfg` files.
- Never commit `.env`.

## Docs

`docs/runbooks/` runbooks, `docs/rca/` RCA reports, `docs/diagrams/` Mermaid architecture diagram.
