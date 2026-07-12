# ACES Scenario Workbench

A collaborative review surface for [ACES](https://github.com/Brad-Edwards/aces)
scenario packs. It turns validated pack content into an addressable,
database-backed workspace where authors, reviewers, and stakeholders inspect
scenario objects, discuss them, and record review decisions.

ACES (Agentic Cyber Environment System) packs remain the authoritative source
of scenario content. The workbench ingests immutable, versioned review bundles
produced from packs; users, comments, decisions, and review state live in the
workbench database. The workbench never writes changes back into a pack.

## Quick start (local)

Requires Python 3.12+.

```bash
pip install aces-workbench      # or: uv tool install aces-workbench
aces-workbench migrate
aces-workbench createadmin               # create the first administrator
aces-workbench doctor                    # check readiness
aces-workbench serve                     # http://127.0.0.1:8000
```

Before the first PyPI release, install from a source checkout with
`pip install .`. See [`docs/setup.md`](docs/setup.md) for the full setup
walkthrough (projects, invitations, email, password reset).

By default the workbench uses a local SQLite database (`db.sqlite3` in the
current directory). Point it at PostgreSQL by setting `DATABASE_URL`:

```bash
export DATABASE_URL=postgres://user:pass@localhost:5432/workbench
```

The Django admin (`/admin/`) is available to administrators for creating
projects and managing membership.

## Documentation

Full documentation is published at
<https://brad-edwards.github.io/aces-scenario-workbench/>. Start with
[Prerequisites](docs/prerequisites.md) for what you need in place before
installing, then [Setup](docs/setup.md), [Access & registration](docs/access-control.md),
[Deployment](docs/deployment.md), and the [go-live checklist](docs/go-live-checklist.md).

## Product boundary

- ACES scenario packs remain the authoritative source for scenario content.
- The workbench ingests immutable, versioned review bundles produced from packs.
- Users, comments, decisions, and review state belong to the workbench database.
- Comments attach to stable scenario object identifiers, never YAML line numbers.
- The workbench must not silently write changes into a scenario pack.

See [`docs/product-intent.md`](docs/product-intent.md) for the full product
contract.

## Configuration

All configuration is environment-driven:

| Variable | Default | Purpose |
| --- | --- | --- |
| `DATABASE_URL` | SQLite `db.sqlite3` | Database connection |
| `ACES_WORKBENCH_SECRET_KEY` | random per start | Django secret key (set a stable value outside local dev) |
| `ACES_WORKBENCH_DEBUG` | `false` | Enable Django debug mode |
| `ACES_WORKBENCH_ALLOWED_HOSTS` | `localhost,127.0.0.1,[::1]` | Comma-separated allowed hosts |
| `ACES_WORKBENCH_EMAIL_HOST` | _(unset → console)_ | SMTP host; enables email delivery for invitations and password resets |
| `ACES_WORKBENCH_CACHE_URL` | in-memory | Cache used by the request rate limiter; set a shared cache (e.g. `redis://…`) behind multiple workers |

Email uses a console backend by default (messages print to the server console);
see [`docs/setup.md`](docs/setup.md) for the full email variable list.

## Security

The workbench is built to run on the public internet. Outside debug mode it
enforces HTTPS (redirect, HSTS, secure cookies), sends a Content-Security-Policy
that allows no inline scripts beyond a per-request nonce, sets clickjacking and
MIME-sniffing protections, locks out repeated failed logins (django-axes), and
rate-limits password-reset and invitation requests. `aces-workbench doctor`
reports the live posture. `aces-workbench serve` is the development server and
runs in debug mode; host with the container path in
[`docs/deployment.md`](docs/deployment.md). Keep the Django admin
(`/admin/`) restricted to administrators.

## CLI

```text
aces-workbench serve [--host H] [--port P]   # run the app (applies migrations first)
aces-workbench migrate                        # apply database migrations
aces-workbench createadmin                    # create an administrator account
aces-workbench import <path> --project <slug> # import a pack's ATLAS projection
aces-workbench doctor                         # report configuration readiness
aces-workbench manage <command> [...]         # any Django management command
```

Administrators create projects and invite members from the Django admin
(`/admin/`); import a scenario pack's ATLAS technique projection with
`aces-workbench import <pack-path> --project <slug>`.

## Development

```bash
uv sync
uv run pytest          # tests
uv run ruff check .    # lint
uv run ruff format .   # format
make hooks             # activate commit-time hooks (once per clone)
```

See [`CONTRIBUTING.md`](CONTRIBUTING.md) for the developer workflow.

## Deployment

Run from a single container against PostgreSQL, or locally against SQLite. See
[`docs/deployment.md`](docs/deployment.md) for local Docker Compose and an AWS
example.

## Privacy

The workbench stores account data and the review activity you create. Signed-in
users can export or delete their own data from the account page; the in-app
privacy notice is at `/privacy/`.

## License

MIT. See [`LICENSE`](LICENSE).
