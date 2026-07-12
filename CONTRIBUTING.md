# Contributing

## Development environment

This repo uses [`uv`](https://docs.astral.dev/uv/) to manage the Python
environment and dev tooling (ruff, pytest).

```bash
uv sync            # create .venv and install runtime + dev dependencies
uv run pytest      # run the tests
uv run ruff check .    # lint
uv run ruff format .   # format
```

`make check` runs the CI-equivalent gate locally (lint + format check + tests).

## Commit-time hooks (run once per clone)

Commit-time hook **activation** is a separate contract from the committed
`.pre-commit-config.yaml` and from CI execution. Because `.git/hooks` is not
versioned, and because this machine uses a global `core.hooksPath` dispatcher
(under which a bare `pre-commit install` silently refuses to wire anything),
every fresh clone must run the repo-native installer once:

```bash
make hooks          # or: scripts/install-hooks.sh
```

This writes managed `pre-commit` and `pre-push` hooks into the clone-local hook
path the dispatcher delegates to, proves git actually dispatches to them, then
runs `pre-commit run --all-files`. It never touches global git config. Re-run it
after changing `.pre-commit-config.yaml`.

- **pre-commit**: general file checks, ruff lint (`--fix`) + format, gitleaks.
- **pre-push**: the test suite (`uv run pytest`).

It is normal for the formatters to make changes on the first run — stage them
and commit.

## Branching, releases, and versioning

- Feature branches open PRs into `dev`; `dev` is promoted to `main` by a PR.
- PR titles into `dev` follow Conventional Commits (`feat:`, `fix:`, `docs:`,
  `chore:`, …) and are enforced by `tools/check_pr_title.py`. The squash-merge
  title becomes the commit release-please reads.
- **release-please owns versioning and `CHANGELOG.md`.** Do not hand-edit
  `[project].version` in `pyproject.toml` or `CHANGELOG.md`. On merge to `main`,
  release-please maintains a `chore(main): release X.Y.Z` PR; merging it tags the
  release, publishes to PyPI (OIDC trusted publishing), and a back-merge PR
  syncs `main → dev`.
- Version mapping: `feat:` → minor, `fix:`/`perf:` → patch, `feat!:` or a
  `BREAKING CHANGE:` footer → major (demoted to minor pre-1.0). `docs`, `chore`,
  `refactor`, `test`, `ci`, `build` do not cut a release.

Publishing requires a one-time owner setup: a PyPI project with a Trusted
Publisher for this repo's `release-please.yml` and a GitHub Environment named
`pypi`.

## Ground Control

This repository is onboarded to Ground Control for requirements and workflow
automation. Its project, workflow commands, SonarCloud settings, and plan rules
live in `.ground-control.yaml` and `.gc/plan-rules.md`. See `AGENTS.md`.
