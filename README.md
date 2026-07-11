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
pip install aces-scenario-workbench      # or: uv tool install aces-scenario-workbench
aces-workbench migrate
aces-workbench createadmin               # create the first administrator
aces-workbench serve                     # http://127.0.0.1:8000
```

By default the workbench uses a local SQLite database (`db.sqlite3` in the
current directory). Point it at PostgreSQL by setting `DATABASE_URL`:

```bash
export DATABASE_URL=postgres://user:pass@localhost:5432/workbench
```

The Django admin (`/admin/`) is available to administrators for creating
projects and managing membership.

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

## CLI

```text
aces-workbench serve [--host H] [--port P]   # run the app (applies migrations first)
aces-workbench migrate                        # apply database migrations
aces-workbench createadmin                    # create an administrator account
aces-workbench import <path> --project <slug> # import a pack's ATLAS projection
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
(ca-central-1) path.

## Privacy

The workbench stores account data and the review activity you create. Signed-in
users can export or delete their own data from the account page; the in-app
privacy notice is at `/privacy/`.

## License

MIT. See [`LICENSE`](LICENSE).
