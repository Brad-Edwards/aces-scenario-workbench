# Product Intent

## Purpose

ACES Scenario Workbench is the human collaboration surface for developing and
reviewing ACES scenario packs. Machine-readable ACES and pack projections remain
the source of truth; the workbench makes their objects, relationships, revision
history, validation results, and review conversations navigable.

The initial KeplerOps prototype demonstrated that the combined scenario, ATLAS,
evidence, and progression model is substantially more useful when presented as
an interactive system than as a large YAML ledger or generated document.

## Primary Users

- Scenario authors developing ACES packs and their realization plans.
- Technical reviewers validating semantics, mappings, evidence, and progression.
- Client stakeholders reviewing the intended participant experience.
- Maintainers resolving review decisions into explicit source changes.

## Addressable Object Model

Every visible entity and relationship must have a stable, shareable URL. A table
row may open a detail drawer for fast navigation, but it must also resolve to a
real route. The initial route vocabulary is:

```text
/scenarios/{scenario}/revisions/{revision}
/scenarios/{scenario}/revisions/{revision}/modules/{module-id}
/scenarios/{scenario}/revisions/{revision}/techniques/{technique-id}
/scenarios/{scenario}/revisions/{revision}/tactics/{tactic-id}
/scenarios/{scenario}/revisions/{revision}/behaviors/{behavior-id}
/scenarios/{scenario}/revisions/{revision}/evidence/{evidence-id}
/scenarios/{scenario}/revisions/{revision}/mappings/{mapping-id}
```

Rows, chart segments, tags, ACES references, evidence identifiers, and relationship
edges are navigation controls, not inert labels.

## Detail Views

Each object detail view should expose, where applicable:

- canonical identifier, type, title, and description;
- source pack, revision, provenance, and source location;
- inbound and outbound relationships;
- validation state, warnings, and integrity digests;
- current and prior revision values;
- comments, decisions, and review activity;
- review state such as `unreviewed`, `accepted`, `needs-change`, or `resolved`.

Comments anchor to `(scenario, revision, object type, stable object id)`. They do
not anchor to generated HTML positions or YAML line numbers. A later revision may
carry a thread forward explicitly, but must not silently retarget it.

## Ingestion And Revisions

A scenario-pack pipeline should produce a versioned review bundle after the pack
passes its validators. The workbench ingests that bundle as an immutable revision
identified by repository, commit, scenario version, and content digest.

The first implementation should support upload or API ingestion of a bundle. Git
provider synchronization and pull-request automation can follow once the bundle
contract is stable.

The workbench database owns collaboration state. It does not become the canonical
store for ACES scenario definitions or private oracle ledgers.

## Security Boundary

Review bundles may contain operator- or oracle-level material. Authentication and
scenario-level authorization are required before content is returned to a client.
Hiding navigation controls in the browser is not authorization. Access events and
review-state changes should be auditable.

The initial roles are `author`, `reviewer`, `stakeholder`, and `administrator`.
Authorization must be enforceable per scenario or project, not only per deployment.

## Initial Implementation Slices

1. Define and validate a versioned review-bundle schema from the KeplerOps fixture.
2. Select the application stack and establish authenticated users and projects.
3. Ingest immutable scenario revisions and render the prototype overview.
4. Add stable detail routes for every object and relationship type.
5. Add anchored comments, review states, and an auditable activity stream.
6. Add revision comparison and explicit comment carry-forward.
7. Add proposed-change export without direct or silent source mutation.

## Seed Provenance

`fixtures/keplerops-ai/atlas-technique-projection.yaml` and `prototype/index.html`
are snapshots exported from `autarchy-ai/penumbra-scenarios`, KeplerOps work on
issue 352, at commit `bd185a9`. They exist to preserve the working concept and
provide an implementation fixture. The scenario pack remains authoritative.
