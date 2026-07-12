# ADR-001: Front-End Product Readiness Boundaries

Date: 2026-07-12

Status: Accepted

## Context

Issue #33 is a cross-cutting product-readiness repair. It touches public entry,
authenticated review chrome, dashboard density, branding, cookie notice, admin
exposure, accessibility, forms, error pages, and print output.

The repository already has important boundaries that must remain intact:

- ACES packs and review bundles are the source of scenario content; the
  workbench database owns collaboration state only.
- Project membership is the authorization boundary, enforced in
  `workbench.access` and `workbench.authz`.
- Account creation is invite-only through the existing accounts app.
- Security posture is centralized in Django settings, middleware, CSP,
  django-axes, django-ratelimit, CSRF, and the `doctor` command.
- `prototype/` is non-authoritative seed material; production UI belongs in the
  Django views, templates, and static assets.

## Decision

The front-end overhaul remains a server-rendered Django application. It must
restore the dashboard-quality experience through existing views, templates, and
static assets rather than introducing a separate client app, a duplicate domain
schema, or persisted reporting tables.

Dashboard metrics, tactic bars, progression cards, digest/integrity details, and
print output are derived from the existing `Revision` object graph
(`tactics`, `steps`, `techniques`, `evidence`, `metadata`,
`content_digest`). They are presentation context, not new persistence.

Brand, metadata, legal chrome, footer links, and default page structure are
centralized in `workbench/base.html` and static files under
`workbench/static/workbench/`. Assets and fonts must be same-origin static
assets; do not add CDN-hosted fonts, scripts, or images that would weaken the
current CSP and offline install story.

The Django admin is not a public landing target. It is mounted through one
normalized setting such as `ACES_WORKBENCH_ADMIN_PATH`, with the root URL
configuration, CSP admin exclusion, documentation, `doctor`, and tests all
deriving from the same value. The default must not be the conventional
`admin/`. Treat the admin path as noise reduction, not as a secret or a
substitute for staff authentication and deployment-layer restriction.

Public entry remains invite-only: anonymous users get a clear sign-in path,
privacy/cookie links, and product context, but not open registration. Staff-only
admin navigation may be shown after authentication using Django's `admin:index`
URL, never as a public call to action.

Cookie notice is informational for the current cookie/storage surface:
session/CSRF cookies plus the local theme preference in `localStorage`. Do not
add analytics or non-essential storage as part of this issue. If future
non-essential storage is introduced, consent categories belong behind one
central legal/chrome seam rather than scattered per-template checks.

Custom 404, 429, and 500 pages use the same branded base where safe and must not
leak exception details. The existing 429 rate-limit handling remains canonical.

Print/PDF support is HTML-first: use print styles and, if needed, a print-mode
variant of the revision overview. Do not add a server-side PDF renderer or
headless browser dependency unless a later requirement explicitly needs it.

## Required Cross-Cutting Contracts

Security gates the implementation must pass:

- Authentication: reuse Django auth views, the custom email user model,
  password validators, django-axes, and django-ratelimit. Do not create open
  registration or parallel login/reset flows.
- Authorization: use `login_required`, `access.member_project`,
  `access.scoped_revision`, and `authz.can_contribute`; hiding links is not
  authorization.
- CSRF and destructive actions: account deletion and all state-changing forms
  remain POST plus CSRF. Add a confirmation step for account deletion without
  bypassing the existing export/delete account contract.
- Admin exposure: validate the configured admin path as a relative URL path
  without query strings, fragments, absolute URLs, backslashes, or `..`
  segments. Keep the path out of public anonymous chrome.
- CSP: keep scripts same-origin plus nonce. No inline event handlers, inline
  style attributes, or remote scripts/fonts. If a pre-paint theme script remains
  inline, it must carry the existing per-request CSP nonce.
- Cookie/storage notice: disclose session, CSRF, and theme-preference storage.
  Any banner dismissal storage must itself be covered by the notice.
- Error envelopes: UI errors render branded templates; API upload errors keep
  the existing JSON `{"detail": ...}` shape and must not expose secrets or
  stack traces.
- OS/runtime exposure: new operational knobs belong in environment variables
  read by settings, not command-line arguments. Admin path configuration is not
  a secret; do not print secrets, tokens, or configured secret values.

Canonical incumbents to build on:

- Settings/env helpers in `aces_scenario_workbench.settings`.
- Readiness reporting in `workbench.management.commands.doctor`.
- URL names from `accounts.urls`, `workbench.urls`, and Django `admin:index`.
- Account forms/views in `accounts.forms` and `accounts.views`.
- Project authorization helpers in `workbench.access` and `workbench.authz`.
- Collaboration context/actions in `workbench.collab`.
- Projection parsing/import rules in `workbench.ingest`.
- Existing test suites for hardening, auth, accounts, review views, collab,
  ingest, CLI, and onboarding.
- Local gates: `make check`, `uv run ruff check .`,
  `uv run ruff format --check .`, and `uv run pytest`.

Extensibility seams:

- Admin mount path: one normalized setting used by URLs, CSP, docs, doctor, and
  tests.
- Legal chrome: one footer/cookie-notice surface for privacy, terms/cookie copy,
  and any future consent categories.
- Brand metadata: base-template blocks/defaults for title, description,
  Open Graph/Twitter text, theme color, and icon assets.
- Tier display: one CSS token/data-attribute vocabulary for `quick`,
  `intermediate`, and `advanced`; do not encode colors independently in each
  template.
- Print mode: a revision-overview rendering seam that can later feed a real PDF
  service if required.

## Non-Goals

- No rewrite to a SPA or client-side routing architecture.
- No model rename or migration from `Step`/`path_step` to "Module" as part of
  front-end polish; choose display labels deliberately while preserving storage
  and URL contracts.
- No new ingestion schema, review-state workflow, role model, or authorization
  hierarchy.
- No analytics, tracking pixels, third-party asset CDNs, or non-essential
  cookies/storage.
- No server-side PDF generation dependency.
- No broad refactor of domain services, admin models, or migrations merely to
  support visual polish.

## Anti-Patterns To Avoid

- Linking anonymous users to the admin or treating an obscured admin path as the
  only protection.
- Recomputing authorization in templates instead of using the server-side
  helpers.
- Duplicating review summary data in new tables when it can be derived from a
  revision.
- Adding a second form-validation layer in templates or JavaScript that diverges
  from Django forms and model choices.
- Hard-coding `/admin/`, tier colors, legal links, or metadata in multiple
  templates.
- Using inline handlers, unsafe-inline CSP, remote fonts, or remote UI scripts
  for convenience.
- Rendering false accessibility state from the server, such as a theme toggle
  `aria-pressed` value that can only be corrected later by JavaScript.
