# Prerequisites

Check the list for how you intend to run the workbench *before* you install, so
nothing blocks you partway through. Each mode builds on the one above it.

At any point, run `aces-workbench doctor` to see what is configured and what is
still missing.

## Everyone

- **Python 3.12 or newer**, or **Docker** if you prefer the container image.

That is all you need to try it locally.

## Local evaluation (SQLite)

Nothing beyond Python. The workbench uses a local SQLite file by default and
runs with `aces-workbench serve`. Suitable for a single person evaluating it on
`localhost`.

## Self-hosted team instance

Have these ready before install:

- **PostgreSQL** database and its connection string (`DATABASE_URL`). SQLite is
  for local use only.
- **A stable secret key** (`ACES_WORKBENCH_SECRET_KEY`). Generate one and store
  it in a secrets manager, not in source control. Without it, sessions reset on
  every restart.
- **An SMTP mail server** (host, port, credentials) if you want invitations and
  password-reset emails to be delivered. Without it, those messages only print
  to the server console and no one receives them.

## Public internet hosting

Everything above, plus — decide and provision these up front:

- **A domain name** for the instance (for example `scenarios.example.com`).
- **A TLS certificate**, terminated by a reverse proxy, load balancer, or CDN in
  front of the app. The workbench redirects HTTP to HTTPS and trusts the
  `X-Forwarded-Proto` header, but it does **not** hold the certificate itself —
  the layer in front does.
- **The public hostname(s)** to put in `ACES_WORKBENCH_ALLOWED_HOSTS`.
- **The public origin(s)** (scheme + host) to put in
  `ACES_WORKBENCH_CSRF_TRUSTED_ORIGINS`, e.g. `https://scenarios.example.com`.
- **A shared cache** (for example Redis, via `ACES_WORKBENCH_CACHE_URL`) if you
  run more than one worker process, so login and request rate limits are counted
  across all workers.
- Somewhere to keep the Django admin (`/admin/`) restricted to administrators.

!!! tip
    Set these as environment variables before the first public start, then run
    `aces-workbench doctor` on the server. It flags a missing secret key,
    console-only email, disabled HTTPS controls, and allowed-hosts / CSRF origins
    that are still at their local defaults — so you catch gaps before users do.

See the [go-live checklist](go-live-checklist.md) for the final pre-launch pass,
and [deployment](deployment.md) for how to wire each value up.
