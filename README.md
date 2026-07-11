# ACES Scenario Workbench

ACES Scenario Workbench is intended to be a collaborative review and
co-development application for ACES scenario packs. It will turn validated pack
content into an addressable review surface where authors, reviewers, and client
stakeholders can inspect scenario objects, discuss them, compare revisions, and
record decisions.

This repository is private and at inception status. It contains the original
KeplerOps ATLAS review application as a working prototype, not a selected
production stack.

## Product Boundary

- ACES scenario packs remain the authoritative source for scenario content.
- The workbench ingests immutable, versioned review bundles produced from packs.
- Users, comments, decisions, subscriptions, and review state belong to the
  workbench database.
- Comments attach to stable scenario object identifiers, never YAML line numbers.
- The workbench must not silently write changes into a scenario pack.
- An accepted review decision may later produce an explicit proposed patch or
  pull request for an author to review.

See [`docs/product-intent.md`](docs/product-intent.md) for the initial product
contract and implementation handoff.

## Prototype

The current prototype is a static, generated KeplerOps review surface. Its
projection input is a frozen fixture copied from the scenario pack at the point
this repository was created. It is deliberately non-authoritative.

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/python prototype/generate_review.py validate
.venv/bin/python prototype/generate_review.py serve --bind 127.0.0.1 --port 8008
```

Then open `http://127.0.0.1:8008`.

## Seed Layout

```text
docs/product-intent.md
fixtures/keplerops-ai/atlas-technique-projection.yaml
prototype/generate_review.py
prototype/index.html
tests/test_generate_review.py
```

The prototype establishes useful information architecture and visual behavior.
It should be replaced incrementally by the authenticated application rather
than treated as the long-term persistence or rendering architecture.
