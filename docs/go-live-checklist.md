# Go-live checklist

Work through this before exposing an instance to the internet. See
[prerequisites](prerequisites.md) for what to have ready and
[deployment](deployment.md) for how to set each value.

## Infrastructure

- [ ] **TLS in front** of the app (reverse proxy, load balancer, or CDN) with a
      valid certificate, forwarding the `X-Forwarded-Proto` header.
- [ ] **PostgreSQL** provisioned; `DATABASE_URL` points at it (not SQLite).
- [ ] **Domain name** resolves to the service.
- [ ] **Shared cache** (`ACES_WORKBENCH_CACHE_URL`) if running more than one
      worker.

## Application configuration

- [ ] `ACES_WORKBENCH_SECRET_KEY` set to a stable value from a secrets manager.
- [ ] `ACES_WORKBENCH_ALLOWED_HOSTS` set to your public hostname(s).
- [ ] `ACES_WORKBENCH_CSRF_TRUSTED_ORIGINS` set to your public origin(s), e.g.
      `https://scenarios.example.com`.
- [ ] Debug is **off** (the default) so HTTPS redirect, HSTS, and secure cookies
      are enabled.
- [ ] SMTP configured (`ACES_WORKBENCH_EMAIL_*`) so invitations and password
      resets are delivered.

## Verify

- [ ] Run `aces-workbench doctor` on the server — every line reads `OK`, or you
      understand why a warning is acceptable for your deployment.
- [ ] Migrations are applied (`aces-workbench migrate`).
- [ ] The first administrator exists (`aces-workbench createadmin`).
- [ ] The Django admin (`/admin/`) is restricted to administrators.
- [ ] Sign in over HTTPS, create a project, and send yourself an invitation to
      confirm email delivery end to end.

## Operate

- [ ] Database backups are scheduled.
- [ ] Logs and errors are collected somewhere you will see them.
- [ ] A process exists to apply dependency and security updates.
