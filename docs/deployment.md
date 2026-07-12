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

## Configuration

Set these in the container/host environment for a hosted deployment:

| Variable | Purpose |
| --- | --- |
| `DATABASE_URL` | `postgres://…` connection string |
| `ACES_WORKBENCH_SECRET_KEY` | stable secret key (required) |
| `ACES_WORKBENCH_ALLOWED_HOSTS` | comma-separated hostnames |
| `ACES_WORKBENCH_SECURE_COOKIES` | `1` behind HTTPS (default follows debug) |
| `ACES_WORKBENCH_SSL_REDIRECT` | `1` to redirect HTTP→HTTPS at the app |
| `ACES_WORKBENCH_HSTS_SECONDS` | HSTS max-age when terminating TLS at the app |
| `ACES_WORKBENCH_CSRF_TRUSTED_ORIGINS` | comma-separated origins for the public URL |

## AWS (ca-central-1)

The image is deployable to AWS in the Canada Central region using the
`catalyst-dev` profile. One container-based path:

1. Build and push the image to ECR:

   ```bash
   aws --profile catalyst-dev --region ca-central-1 ecr create-repository \
     --repository-name aces-workbench
   docker build -t aces-workbench .
   # tag and push to the ECR repository URI from the previous command
   ```

2. Provision a PostgreSQL database (RDS for PostgreSQL) in `ca-central-1` and
   note its connection string.

3. Run the image on a container service in `ca-central-1` (for example AWS App
   Runner or ECS Fargate), setting `DATABASE_URL`, `ACES_WORKBENCH_SECRET_KEY`,
   `ACES_WORKBENCH_ALLOWED_HOSTS`, `ACES_WORKBENCH_SECURE_COOKIES=1`, and
   `ACES_WORKBENCH_CSRF_TRUSTED_ORIGINS`.

4. To serve under `keplerops.com/scenarios`, route that path prefix to the
   service (for example a CloudFront behavior or an ALB path rule) and include
   the public origin in `ACES_WORKBENCH_CSRF_TRUSTED_ORIGINS`.

Store `ACES_WORKBENCH_SECRET_KEY` and database credentials in a secrets manager,
not in source control.
