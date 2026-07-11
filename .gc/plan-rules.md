# aces-scenario-workbench plan rules

Mandatory constraints the `/implement` skill applies during the plan phase.
These encode the hard rules for this repository; keep them aligned with
`README.md` and `docs/product-intent.md`.

- Plans MUST run `uv run ruff check .` and `uv run ruff format --check .`
  before declaring completion.
- Plans MUST run `uv run pytest` before declaring completion.
- Plans MUST set `ACES_REQUIREMENT_UID` when the branch name does not already
  contain a requirement UID such as `WB-001`.
- Plans MUST keep IMPLEMENTS and TESTS traceability in Ground Control aligned
  with the changed code and tests.
- Plans MUST honour the product boundary in `README.md` and
  `docs/product-intent.md`:
  - ACES scenario packs remain the authoritative source for scenario content;
    the workbench ingests immutable, versioned review bundles produced from
    packs.
  - The workbench MUST NOT silently write changes back into a scenario pack.
    An accepted review decision may only produce an explicit proposed patch or
    pull request for an author to review.
  - Comments and review anchors attach to stable scenario object identifiers,
    never to YAML line numbers.
- Plans MUST treat everything under `prototype/` and `fixtures/` as
  non-authoritative seed material: it demonstrates information architecture and
  visual behaviour and is to be replaced incrementally by the authenticated
  application, not extended as the long-term persistence or rendering
  architecture.
- Plans that add architecture-authority artifacts (ADRs) MUST place them under
  `docs/decisions/adrs/`.
