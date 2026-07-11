"""Ingest an ACES scenario pack's ATLAS technique projection.

A projection is parsed into an immutable :class:`Revision` and its content
objects (tactics, steps, evidence, techniques). Ingestion is idempotent: a
revision is identified by a content digest, so re-importing identical content is
a no-op while changed content creates a new revision. The workbench never writes
back into a pack.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

import yaml
from django.db import transaction
from django.utils.text import slugify

from .models import Evidence, Project, Revision, Scenario, Step, Tactic, Technique

PROJECTION_CANDIDATES = (
    "atlas-technique-projection.yaml",
    "oracle/atlas-technique-projection.yaml",
)


class ProjectionError(ValueError):
    """Raised when a projection file cannot be read or parsed."""


def _text(entry: dict[str, Any], key: str, default: str = "") -> str:
    value = entry.get(key)
    return default if value is None else str(value)


def _mapping(data: dict[str, Any], key: str) -> dict[str, Any]:
    value = data.get(key)
    return value if isinstance(value, dict) else {}


def _entries(data: dict[str, Any], key: str) -> list[dict[str, Any]]:
    value = data.get(key)
    return value if isinstance(value, list) else []


def load_projection(path: Path) -> tuple[dict[str, Any], bytes]:
    """Load a projection from a file, or from a pack directory."""
    if path.is_dir():
        path = _resolve_in_directory(path)
    try:
        raw = path.read_bytes()
    except OSError as exc:
        raise ProjectionError(str(exc)) from exc
    return parse_projection(raw), raw


def parse_projection(raw: bytes) -> dict[str, Any]:
    try:
        data = yaml.safe_load(raw)
    except yaml.YAMLError as exc:
        raise ProjectionError(f"Invalid YAML: {exc}") from exc
    if not isinstance(data, dict):
        raise ProjectionError("Projection file is not a mapping.")
    return data


def _resolve_in_directory(directory: Path) -> Path:
    for candidate in PROJECTION_CANDIDATES:
        found = directory / candidate
        if found.is_file():
            return found
    raise ProjectionError(f"No ATLAS technique projection found under {directory}.")


def _digest(data: dict[str, Any]) -> str:
    canonical = json.dumps(data, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(canonical).hexdigest()


@transaction.atomic
def import_projection(project: Project, data: dict[str, Any]) -> tuple[Revision, bool]:
    """Import a projection into ``project``; returns ``(revision, created)``."""
    pack = _text(data, "pack", "scenario")
    framework = _mapping(data, "framework")

    scenario, _ = Scenario.objects.get_or_create(
        project=project, slug=slugify(pack) or "scenario", defaults={"name": pack}
    )

    digest = _digest(data)
    existing = Revision.objects.filter(scenario=scenario, content_digest=digest).first()
    if existing is not None:
        return existing, False

    revision = Revision.objects.create(
        scenario=scenario,
        label=_text(data, "mapping_id", "revision"),
        mapping_id=_text(data, "mapping_id"),
        content_digest=digest,
        source_repo=_text(data, "source_oracle"),
        framework_name=_text(framework, "name"),
        framework_release=_text(framework, "release"),
        metadata={
            "experience_contract": _mapping(data, "experience_contract"),
            "semantic_binding": _mapping(data, "semantic_binding"),
        },
    )
    _load_objects(revision, data)
    return revision, True


def _load_tactics(revision: Revision, data: dict[str, Any]) -> dict[str, Tactic]:
    tactics: dict[str, Tactic] = {}
    for entry in _entries(data, "tactic_modules"):
        tactic = Tactic.objects.create(
            revision=revision,
            tactic_id=_text(entry, "tactic_id"),
            name=_text(entry, "name"),
        )
        tactics[tactic.tactic_id] = tactic
    return tactics


def _load_steps(revision: Revision, data: dict[str, Any]) -> tuple[dict[str, Step], set[str]]:
    steps: dict[str, Step] = {}
    evidence_ids: set[str] = set()
    for entry in _entries(data, "steps"):
        step = Step.objects.create(
            revision=revision,
            path_step=_text(entry, "path_step"),
            behavior_specification=_text(entry, "aces_behavior_specification"),
            tier=_text(entry, "tier"),
            surface=_text(entry, "surface"),
            estimated_minutes=entry.get("estimated_minutes"),
            objective=_text(entry, "objective"),
            flag_outcome=_text(entry, "flag_outcome"),
            justification=_text(entry, "justification"),
        )
        steps[step.path_step] = step
        evidence_ids.update(str(evidence_id) for evidence_id in _sequence(entry, "evidence"))
    return steps, evidence_ids


def _sequence(entry: dict[str, Any], key: str) -> list[Any]:
    value = entry.get(key)
    return value if isinstance(value, list) else []


def _load_evidence(revision: Revision, evidence_ids: set[str]) -> dict[str, Evidence]:
    return {
        evidence_id: Evidence.objects.create(revision=revision, evidence_id=evidence_id)
        for evidence_id in sorted(evidence_ids)
    }


def _technique_tactics(entry: dict[str, Any], tactics: dict[str, Tactic]) -> list[Tactic]:
    return [tactics[str(tid)] for tid in _sequence(entry, "tactics") if str(tid) in tactics]


def _load_techniques(
    revision: Revision,
    data: dict[str, Any],
    tactics: dict[str, Tactic],
    steps: dict[str, Step],
    evidence: dict[str, Evidence],
) -> None:
    for entry in _entries(data, "technique_catalog"):
        technique = Technique.objects.create(
            revision=revision,
            technique_id=_text(entry, "id"),
            name=_text(entry, "name"),
            surface=_text(entry, "surface"),
            relationship=_text(entry, "relationship"),
            coverage_status=_text(entry, "coverage_status"),
            planned_action=_text(entry, "planned_action"),
            rationale=_text(entry, "rationale"),
            step=steps.get(_text(entry, "challenge_step")),
            evidence=evidence.get(_text(entry, "evidence")),
        )
        linked = _technique_tactics(entry, tactics)
        if linked:
            technique.tactics.set(linked)


def _load_objects(revision: Revision, data: dict[str, Any]) -> None:
    tactics = _load_tactics(revision, data)
    steps, evidence_ids = _load_steps(revision, data)
    for entry in _entries(data, "technique_catalog"):
        evidence_id = _text(entry, "evidence")
        if evidence_id:
            evidence_ids.add(evidence_id)
    evidence = _load_evidence(revision, evidence_ids)
    _load_techniques(revision, data, tactics, steps, evidence)
