# Setup

A full walkthrough from install to a working, multi-user review workspace.

## 1. Install

Once released, from PyPI:

```bash
pip install aces-workbench     # or: uv tool install aces-workbench
```

Before the first release, from a source checkout:

```bash
pip install .        # or: uv tool install .
```

Requires Python 3.12+. SQLite needs nothing else; PostgreSQL needs the
`aces-workbench[postgres]` extra.

## 2. First run

```bash
export ACES_WORKBENCH_SECRET_KEY="$(python -c 'import secrets; print(secrets.token_urlsafe(50))')"
aces-workbench migrate
aces-workbench createadmin        # prompts for email + password
aces-workbench doctor             # confirm readiness
aces-workbench serve              # http://127.0.0.1:8000
```

`aces-workbench doctor` reports database, migration, secret-key, email, and
debug status so you can see what still needs configuration.

Set `ACES_WORKBENCH_SECRET_KEY` to a stable value; without it a random key is
used and sessions reset on every restart.

## 3. Create projects and add people

Sign in at `/accounts/login/` and open the Django admin at `/admin/`.

- **Create a project**: Admin → Projects → Add.
- **Add a member you can manage directly**: Admin → Users → Add (this sets a
  real password), then add a Membership on the project with a role
  (`author`, `reviewer`, `stakeholder`, `administrator`).
- **Invite by email**: Admin → Invitations → Add (email, project, role). An
  invitation email with an accept link is sent on save; the invitee sets their
  own password. Use the "Resend invitation email" action to send it again.

With the default console email backend, the invitation and password-reset
messages are printed to the server console rather than delivered — copy the link
from there for local use. Configure SMTP (below) to deliver for real.

## 4. Import a scenario

```bash
aces-workbench import /path/to/pack --project <project-slug>
```

Point it at a pack directory containing an ATLAS technique projection, or at the
projection file directly. Re-importing identical content is a no-op; changed
content creates a new revision.

## 5. Email (for invitations and password resets)

Email uses the console backend by default. To deliver over SMTP, set:

| Variable | Purpose |
| --- | --- |
| `ACES_WORKBENCH_EMAIL_HOST` | SMTP host (enables the SMTP backend) |
| `ACES_WORKBENCH_EMAIL_PORT` | SMTP port (default 587) |
| `ACES_WORKBENCH_EMAIL_USER` | SMTP username |
| `ACES_WORKBENCH_EMAIL_PASSWORD` | SMTP password |
| `ACES_WORKBENCH_EMAIL_USE_TLS` | `1`/`0` (default `1`) |
| `ACES_WORKBENCH_DEFAULT_FROM_EMAIL` | From address |

Password reset is available from the sign-in page ("Forgot your password?").

## 6. Hosting

See [`deployment.md`](deployment.md) for container and AWS deployment, including
the HTTPS-related environment variables.
