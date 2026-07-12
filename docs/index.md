# ACES Scenario Workbench

A collaborative review surface for [ACES](https://github.com/Brad-Edwards/aces)
scenario packs. It turns validated pack content into an addressable,
database-backed workspace where authors, reviewers, and stakeholders inspect
scenario objects, discuss them, and record review decisions.

ACES packs remain the authoritative source of scenario content. The workbench
ingests immutable, versioned review bundles produced from packs; users, comments,
decisions, and review state live in the workbench database. The workbench never
writes changes back into a pack.

## Where to start

- **[Prerequisites](prerequisites.md)** — what you need in place *before* you
  install, for local use, a self-hosted team instance, or public internet
  hosting. Check this first so nothing blocks you halfway through.
- **[Setup](setup.md)** — install to a working, multi-user workspace.
- **[Access & registration](access-control.md)** — the invite-only account model
  and project roles.
- **[Deployment](deployment.md)** — container, configuration, and hosting.
- **[Go-live checklist](go-live-checklist.md)** — the final checks before you
  expose an instance to the internet.

## Run the readiness check anytime

Whatever stage you are at, `aces-workbench doctor` reports what is configured and
what still needs attention (database, secret key, email, HTTPS, allowed hosts,
and more), so you can see gaps up front instead of discovering them later.
