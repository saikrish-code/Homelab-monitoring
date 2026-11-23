# Architecture

Rendered by GitHub, GitLab, VS Code and any Mermaid-aware viewer. To edit as draw.io:
in diagrams.net use *Arrange > Insert > Advanced > Mermaid* and paste the block below.

```mermaid
flowchart LR
  user([Operator browser])
  subgraph host[Docker host]
    subgraph labnet["labnet 172.20.0.0/24"]
      mon01["mon01 .10<br/>Nagios Core + Apache :80<br/>snow_incident.py / notify_email.py"]
      web01["web01 .11<br/>nginx :80 + NRPE :5666"]
      db01["db01 .12<br/>MariaDB :3306 + NRPE :5666"]
      mailpit["mailpit .20<br/>SMTP :1025 / UI :8025"]
    end
  end
  snow[("ServiceNow instance<br/>REST Table API")]

  user -- "8080 (Nagios UI)" --> mon01
  user -- "8081 (site)" --> web01
  user -- "8025 (mail UI)" --> mailpit
  mon01 -- "check_http, check_json_status" --> web01
  mon01 -- "NRPE 5666" --> web01
  mon01 -- "NRPE 5666, check_mysql 3306" --> db01
  mon01 -- "SMTP 1025 alert mail" --> mailpit
  mon01 -- "HTTPS incident create / note / resolve" --> snow
```

## Alert flow

```mermaid
sequenceDiagram
  participant N as Nagios (mon01)
  participant T as Target (web01/db01)
  participant M as Mailpit
  participant S as ServiceNow
  N->>T: active check (retry until HARD)
  T-->>N: CRITICAL
  N->>M: PROBLEM email
  N->>S: find open incident by correlation_id
  alt none open
    N->>S: POST incident
  else already open
    N->>S: PATCH work note (no duplicate)
  end
  N->>T: next checks
  T-->>N: OK
  N->>M: RECOVERY email
  N->>S: PATCH work note + state=Resolved
```

Without `SNOW_*` credentials in `.env` the ServiceNow steps run in dry-run mode (logged only, in
`/var/log/nagios4/lab_notify.log` inside mon01).
