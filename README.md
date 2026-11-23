# HomeLab Monitoring & Incident Response

`setup.sh` generates a Docker Compose lab: **Nagios Core** monitoring an **nginx** web server and a
**MariaDB** database, alert emails caught by **Mailpit**, **ServiceNow** incident creation, a
one-page **control console**, outage drills, runbooks and a sample RCA.

## Use it

```bash
bash setup.sh                       # creates ./homelab-monitoring and a random .env
cd homelab-monitoring
docker compose up -d --build
```

Then open the console at http://localhost:8090 (user `nagiosadmin`, password in `homelab-monitoring/.env`).
The generated project has its own detailed README with the architecture diagram, the list of checks,
the drills table and troubleshooting: see `homelab-monitoring/README.md` after running setup.

`setup.sh` refuses to run if `homelab-monitoring/docker-compose.yml` already exists. To regenerate,
run `docker compose down -v` in the project, delete the folder, then run `setup.sh` again.

## Repo layout

| Path | Purpose |
|---|---|
| `setup.sh` | Source of truth: generates the whole project (compose, Nagios config, plugin, bridge, console, docs) |
| `tests/` | Mock ServiceNow API plus plugin and bridge tests |
| `scripts/test.sh` | Lint, syntax, generated-project and unit tests (`make test`) |
| `scripts/drill.sh` | Runs one outage drill against the live stack and reports detection and recovery times |
| `homelab-monitoring/` | Generated output (untracked; do not edit by hand, change `setup.sh` instead) |

## Test

```bash
make test        # or: bash scripts/test.sh
```

Runs against a throwaway generated project, so it never touches your running stack or `.env`.

```bash
bash scripts/drill.sh db-crash db-fix 'SERVICE ALERT: db01;MySQL;CRITICAL;HARD' 'SERVICE ALERT: db01;MySQL;OK'
```

Drills need the stack running. Real ServiceNow credentials go only in `homelab-monitoring/.env`;
without them the bridge runs in dry-run mode.
