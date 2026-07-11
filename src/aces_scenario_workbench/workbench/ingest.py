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
    pack = str(data.get("pack") or "scenario")
    mapping_id = str(data.get("mapping_id") or "")
    framework = data.get("framework") or {}

    scenario, _ = Scenario.objects.get_or_create(
        project=project, slug=slugify(pack) or "scenario", defaults={"name": pack}
    )

    digest = _digest(data)
    existing = Revision.objects.filter(scenario=scenario, content_digest=digest).first()
    if existing is not None:
        return existing, False

    revision = Revision.objects.create(
        scenario=scenario,
        label=mapping_id or "revision",
        mapping_id=mapping_id,
        content_digest=digest,
        source_repo=str(data.get("source_oracle") or ""),
        framework_name=str(framework.get("name") or ""),
        framework_release=str(framework.get("release") or ""),
        metadata={
            "experience_contract": data.get("experience_contract") or {},
            "semantic_binding": data.get("semantic_binding") or {},
        },
    )
    _load_objects(revision, data)
    return revision, True


def _load_tactics(revision: Revision, data: dict[str, Any]) -> dict[str, Tactic]:
    tactics: dict[str, Tactic] = {}
    for entry in data.get("tactic_modules") or []:
        tactic = Tactic.objects.create(
            revision=revision,
            tactic_id=str(entry["tactic_id"]),
            name=str(entry.get("name") or ""),
        )
        tactics[tactic.tactic_id] = tactic
    return tactics


def _load_steps(revision: Revision, data: dict[str, Any]) -> tuple[dict[str, Step], set[str]]:
    steps: dict[str, Step] = {}
    evidence_ids: set[str] = set()
    for entry in data.get("steps") or []:
        step = Step.objects.create(
            revision=revision,
            path_step=str(entry["path_step"]),
            behavior_specification=str(entry.get("aces_behavior_specification") or ""),
            tier=str(entry.get("tier") or ""),
            surface=str(entry.get("surface") or ""),
            estimated_minutes=entry.get("estimated_minutes"),
            objective=str(entry.get("objective") or ""),
            flag_outcome=str(entry.get("flag_outcome") or ""),
            justification=str(entry.get("justification") or ""),
        )
        steps[step.path_step] = step
        for evidence_id in entry.get("evidence") or []:
            evidence_ids.add(str(evidence_id))
    return steps, evidence_ids


def _load_evidence(revision: Revision, evidence_ids: set[str]) -> dict[str, Evidence]:
    return {
        evidence_id: Evidence.objects.create(revision=revision, evidence_id=evidence_id)
        for evidence_id in sorted(evidence_ids)
    }


def _load_techniques(
    revision: Revision,
    data: dict[str, Any],
    tactics: dict[str, Tactic],
    steps: dict[str, Step],
    evidence: dict[str, Evidence],
) -> None:
    for entry in data.get("technique_catalog") or []:
        technique = Technique.objects.create(
            revision=revision,
            technique_id=str(entry["id"]),
            name=str(entry.get("name") or ""),
            surface=str(entry.get("surface") or ""),
            relationship=str(entry.get("relationship") or ""),
            coverage_status=str(entry.get("coverage_status") or ""),
            planned_action=str(entry.get("planned_action") or ""),
            rationale=str(entry.get("rationale") or ""),
            step=steps.get(str(entry.get("challenge_step") or "")),
            evidence=evidence.get(str(entry.get("evidence") or "")),
        )
        linked = [tactics[str(tid)] for tid in (entry.get("tactics") or []) if str(tid) in tactics]
        if linked:
            technique.tactics.set(linked)


def _load_objects(revision: Revision, data: dict[str, Any]) -> None:
    tactics = _load_tactics(revision, data)
    steps, evidence_ids = _load_steps(revision, data)
    for entry in data.get("technique_catalog") or []:
        if entry.get("evidence"):
            evidence_ids.add(str(entry["evidence"]))
    evidence = _load_evidence(revision, evidence_ids)
    _load_techniques(revision, data, tactics, steps, evidence)
