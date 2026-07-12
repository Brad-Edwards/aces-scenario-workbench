# Deployment

The workbench is a standard Django application. It runs from a single container
against PostgreSQL, or locally from a pip install against SQLite.

## Local (SQLite, no container)

```bash
pip install aces-workbench
aces-workbench migrate
aces-workbench createadmin
aces-workbench serve
```

## Local (container + PostgreSQL)

```bash
export ACES_WORKBENCH_SECRET_KEY="$(python -c 'import secrets; print(secrets.token_urlsafe(50))')"
docker compose up --build
```

The web container applies migrations on start and serves with gunicorn on
`http://localhost:8000`. Create the first administrator once the stack is up:

```bash
docker compose exec web aces-workbench createadmin
```

## Container image

Each release publishes an image to the GitHub Container Registry, tagged with the
version and `latest`:

```bash
docker run --rm -p 8000:8000 \
  -e ACES_WORKBENCH_SECRET_KEY="$(python -c 'import secrets; print(secrets.token_urlsafe(50))')" \
  -e DATABASE_URL="postgres://user:pass@host:5432/workbench" \
  ghcr.io/brad-edwards/aces-workbench:latest
```

The container applies migrations on start and serves with gunicorn. It runs with
the HTTPS controls on (debug off); terminate TLS in front of it and forward
`X-Forwarded-Proto`, or set `ACES_WORKBENCH_SSL_REDIRECT=0` when serving plain
HTTP behind another layer.

## Configuration

Set these in the container/host environment for a hosted deployment:

| Variable | Purpose |
| --- | --- |
| `DATABASE_URL` | `postgres://…` connection string |
| `ACES_WORKBENCH_SECRET_KEY` | stable secret key (required) |
| `ACES_WORKBENCH_ALLOWED_HOSTS` | comma-separated hostnames |
| `ACES_WORKBENCH_CSRF_TRUSTED_ORIGINS` | comma-separated origins for the public URL |
| `ACES_WORKBENCH_CACHE_URL` | shared cache for rate limiting behind multiple workers, e.g. `redis://host:6379/0` |
| `ACES_WORKBENCH_SECURE_COOKIES` | secure session/CSRF cookies (default on when debug is off) |
| `ACES_WORKBENCH_SSL_REDIRECT` | redirect HTTP→HTTPS at the app (default on when debug is off) |
| `ACES_WORKBENCH_HSTS_SECONDS` | HSTS max-age (default `31536000` when debug is off) |
| `ACES_WORKBENCH_HSTS_INCLUDE_SUBDOMAINS` | apply HSTS to subdomains (default `1`) |
| `ACES_WORKBENCH_HSTS_PRELOAD` | set the HSTS preload flag (default `0`) |
| `ACES_WORKBENCH_AXES_FAILURE_LIMIT` | failed logins per IP before lockout (default `5`) |
| `ACES_WORKBENCH_AXES_COOLOFF_HOURS` | lockout duration in hours (default `1`) |

The HTTPS controls are on by default outside debug mode; the app trusts the
`X-Forwarded-Proto` header so the redirect does not loop behind a TLS-terminating
proxy. A Content-Security-Policy with a per-request script nonce (no inline
scripts) is applied to every response except the Django admin, which ships inline
scripts it does not nonce — keep `/admin/` restricted to administrators. The
in-memory rate-limit cache is per worker; set `ACES_WORKBENCH_CACHE_URL` to a
shared cache so limits hold across processes.

## AWS (example)

The image runs on any container host. One AWS path is below; use your own AWS
profile and a region of your choice (shown as `<region>`).

1. Build and push the image to ECR:

   ```bash
   aws --profile <your-profile> --region <region> ecr create-repository \
     --repository-name aces-workbench
   docker build -t aces-workbench .
   # tag and push to the ECR repository URI from the previous command
   ```

2. Provision a PostgreSQL database (RDS for PostgreSQL) in the same region and
   note its connection string.

3. Run the image on a container service (for example AWS App Runner or ECS
   Fargate), setting `DATABASE_URL`, `ACES_WORKBENCH_SECRET_KEY`,
   `ACES_WORKBENCH_ALLOWED_HOSTS`, `ACES_WORKBENCH_SECURE_COOKIES=1`, and
   `ACES_WORKBENCH_CSRF_TRUSTED_ORIGINS`.

4. To serve on your own domain or under a path prefix (for example
   `scenarios.example.com` or `example.com/scenarios`), route that host or prefix
   to the service (for example a CloudFront behavior or an ALB path rule) and
   include the public origin in `ACES_WORKBENCH_CSRF_TRUSTED_ORIGINS`.

Store `ACES_WORKBENCH_SECRET_KEY` and database credentials in a secrets manager,
not in source control.
