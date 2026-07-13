"""Ingest ACES scenario content into the workbench revision graph.

SDL modules are preferred as the authoritative scenario source when present.
Legacy projection files are still accepted for backwards compatibility and as
optional enrichment around SDL-defined modules. Imported content becomes an
immutable :class:`Revision` with its content objects. Ingestion is idempotent:
a revision is identified by a content digest, so re-importing identical content
is a no-op while changed content creates a new revision. The workbench never
writes back into a pack.
"""

from __future__ import annotations

import ast
import hashlib
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml
from aces_sdl import SDLMigrationPolicy, parse_sdl_file
from django.db import transaction

from .models import (
    Challenge,
    ChallengeEvidenceRequirement,
    Evidence,
    Revision,
    Scenario,
    Step,
    Tactic,
    Technique,
)

PROJECTION_CANDIDATES = (
    "atlas-technique-projection.yaml",
    "oracle/atlas-technique-projection.yaml",
)
CONTRACT_PATHS = {
    "challenges": "challenges/challenges.yaml",
    "placement": "flags/placement.yaml",
    "objectives": "oracle/objectives.yaml",
    "telemetry": "oracle/telemetry.yaml",
    "scoring": "oracle/scoring.yaml",
    "topology": "design/topology.yaml",
    "software_inventory": "design/software-inventory.yaml",
    "planned_assets": "assets/planned-assets.yaml",
    "affordances": "assets/affordances.yaml",
}
SDL_LOCAL_PREFIX = "local:"
SDL_PARSER_ISSUE = "https://github.com/Brad-Edwards/aces/issues/767"
SDL_MAPPING_SECTIONS = (
    "nodes",
    "infrastructure",
    "features",
    "entities",
    "accounts",
    "content",
    "relationships",
    "agents",
    "behavior_specifications",
    "behavior-specifications",
)


class ProjectionError(ValueError):
    """Raised when a projection file cannot be read or parsed."""


@dataclass
class LegacyChallengeContext:
    challenges: dict[str, dict[str, Any]]
    placements: list[dict[str, Any]]
    outcomes: dict[str, dict[str, Any]]
    path_steps: dict[str, dict[str, Any]]
    telemetry: dict[str, dict[str, Any]]
    awards: dict[str, dict[str, Any]]
    alternate_awards: list[dict[str, Any]]
    bundles: list[dict[str, Any]]
    runtime: dict[str, dict[str, Any]]
    steps: dict[str, Step]
    techniques_by_step: dict[str, list[Technique]]


@dataclass
class LegacyChallengeRow:
    placement: dict[str, Any]
    runtime_row: dict[str, Any]
    challenge_row: dict[str, Any]
    outcome: dict[str, Any]
    outcome_id: str
    canonical_steps: list[str]
    path_step_contracts: list[dict[str, Any]]
    award: dict[str, Any]
    evidence_ids: list[str]
    implemented: bool


@dataclass
class SdlChallengeContext:
    module_steps: dict[str, Step]
    steps_by_path: dict[str, Step]
    techniques_by_step: dict[str, list[Technique]]


def _text(entry: dict[str, Any], key: str, default: str = "") -> str:
    value = entry.get(key)
    return default if value is None else str(value)


def _mapping(data: dict[str, Any], key: str) -> dict[str, Any]:
    value = data.get(key)
    return value if isinstance(value, dict) else {}


def _mapping_any(data: dict[str, Any], *keys: str) -> dict[str, Any]:
    for key in keys:
        value = data.get(key)
        if isinstance(value, dict):
            return value
    return {}


def _text_any(entry: dict[str, Any], *keys: str, default: str = "") -> str:
    for key in keys:
        value = entry.get(key)
        if value is not None:
            return str(value)
    return default


def _sequence_any(entry: dict[str, Any], *keys: str) -> list[Any]:
    for key in keys:
        value = entry.get(key)
        if isinstance(value, list):
            return value
    return []


def _entries(data: dict[str, Any], key: str) -> list[dict[str, Any]]:
    value = data.get(key)
    return value if isinstance(value, list) else []


def _string_list(value: object) -> list[str]:
    return [str(item) for item in value] if isinstance(value, list) else []


def load_projection(path: Path) -> tuple[dict[str, Any], bytes]:
    """Load a projection from a file, or from a pack directory."""
    if path.is_dir():
        path = _resolve_in_directory(path)
    try:
        raw = path.read_bytes()
    except OSError as exc:
        raise ProjectionError(str(exc)) from exc
    return parse_projection(raw), raw


def load_pack_contracts(path: Path) -> dict[str, Any]:
    """Load optional challenge/scoring/evidence contracts from a pack directory."""
    if not path.is_dir():
        return {}

    contracts: dict[str, Any] = {}
    for key, relative_path in CONTRACT_PATHS.items():
        found = path / relative_path
        if found.is_file():
            contracts[key] = parse_projection(found.read_bytes())

    sdl = _load_sdl(path)
    if sdl:
        contracts["sdl"] = sdl

    runtime = _runtime_challenges(path)
    if runtime:
        contracts["runtime_challenges"] = runtime
    return contracts


def _load_sdl(pack_dir: Path) -> dict[str, Any]:
    for found in sorted((pack_dir / "sdl").glob("*.sdl.yaml")):
        if found.is_file():
            try:
                scenario = parse_sdl_file(found, migration_policy=SDLMigrationPolicy.ACCEPT)
            except Exception as exc:
                fallback = _raw_modular_sdl(found)
                fallback["parser_error"] = str(exc)
                fallback["parser"] = "raw-sdl-fallback"
                fallback["parser_issue"] = SDL_PARSER_ISSUE
                return fallback
            parsed = scenario.model_dump(mode="json")
            parsed["parser"] = "aces-sdl"
            parsed["advisories"] = [str(advisory) for advisory in scenario.advisories]
            return parsed
    return {}


def _raw_modular_sdl(root_path: Path) -> dict[str, Any]:
    """Read a root SDL file plus declared local imports without semantic expansion."""
    root = parse_projection(root_path.read_bytes())
    expanded: dict[str, Any] = {
        key: value for key, value in root.items() if key not in SDL_MAPPING_SECTIONS
    }
    expanded["raw_files"] = [
        {
            "path": root_path.name,
            "namespace": "",
            "section_counts": _sdl_section_counts(root),
        }
    ]
    for section in SDL_MAPPING_SECTIONS:
        if section in {"behavior-specifications"}:
            continue
        section_value = _mapping_any(root, section)
        if section_value:
            expanded[section] = dict(section_value)

    seen = {root_path.resolve()}
    for import_row in _sdl_import_rows(root):
        _merge_sdl_import(expanded, root_path.parent, import_row, seen)

    if "behavior-specifications" in expanded and "behavior_specifications" not in expanded:
        expanded["behavior_specifications"] = expanded.pop("behavior-specifications")
    return expanded


def _sdl_import_rows(sdl: dict[str, Any]) -> list[dict[str, Any]]:
    return [row for row in _sequence(sdl, "imports") if isinstance(row, dict)]


def _merge_sdl_import(
    expanded: dict[str, Any],
    base_dir: Path,
    import_row: dict[str, Any],
    seen: set[Path],
) -> None:
    source = _text(import_row, "source")
    if not source.startswith(SDL_LOCAL_PREFIX):
        return
    relative_source = source.removeprefix(SDL_LOCAL_PREFIX)
    imported_path = (base_dir / relative_source).resolve()
    if imported_path in seen:
        return
    seen.add(imported_path)
    imported = parse_projection(imported_path.read_bytes())
    namespace = _text(import_row, "namespace")
    expanded.setdefault("raw_files", []).append(
        {
            "path": relative_source,
            "namespace": namespace,
            "section_counts": _sdl_section_counts(imported),
        }
    )
    for section in SDL_MAPPING_SECTIONS:
        rows = _mapping_any(imported, section)
        if not rows:
            continue
        target_section = (
            "behavior_specifications" if section == "behavior-specifications" else section
        )
        target = expanded.setdefault(target_section, {})
        if isinstance(target, dict):
            _merge_sdl_mapping(target, rows, namespace)

    for nested_import in _sdl_import_rows(imported):
        _merge_sdl_import(expanded, imported_path.parent, nested_import, seen)


def _merge_sdl_mapping(
    target: dict[str, Any],
    rows: dict[str, Any],
    namespace: str,
) -> None:
    for key, value in rows.items():
        merged_key = str(key)
        if merged_key in target and target[merged_key] != value and namespace:
            merged_key = f"{namespace}.{merged_key}"
        if merged_key not in target:
            target[merged_key] = value


def _sdl_section_counts(sdl: dict[str, Any]) -> dict[str, int]:
    return {
        ("behavior_specifications" if section == "behavior-specifications" else section): len(
            _mapping_any(sdl, section)
        )
        for section in SDL_MAPPING_SECTIONS
        if _mapping_any(sdl, section)
    }


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
    raise ProjectionError(f"No legacy projection found under {directory}.")


def _digest(data: dict[str, Any]) -> str:
    canonical = json.dumps(data, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(canonical).hexdigest()


def _content_digest(projection: dict[str, Any], contracts: dict[str, Any]) -> str:
    if not contracts:
        return _digest(projection)
    return _digest({"projection": projection, "contracts": contracts})


def _sdl_defines_modules(sdl: object) -> bool:
    return isinstance(sdl, dict) and bool(
        _mapping_any(sdl, "behavior_specifications", "behavior-specifications")
    )


def _projection_from_sdl(sdl: dict[str, Any], projection: dict[str, Any]) -> dict[str, Any]:
    """Adapt SDL behavior specifications into the workbench's revision graph shape."""
    behavior_specs = _mapping_any(sdl, "behavior_specifications", "behavior-specifications")
    projection_rows = _sdl_projection_rows(_sdl_module_specs(behavior_specs), projection)
    techniques = [technique for row in projection_rows for technique in row["techniques"]]
    framework = _mapping(projection, "framework")

    return {
        "schema_version": 1,
        "mapping_id": f"{_text(sdl, 'name', 'scenario')}-sdl-{_text(sdl, 'version', 'revision')}",
        "pack": _text(sdl, "name"),
        "source_oracle": "sdl",
        "semantic_binding": {"source": "aces-sdl", "parser": _text(sdl, "parser")},
        "framework": framework
        or {
            "name": "ACES SDL",
            "release": _text(sdl, "version"),
        },
        "experience_contract": _mapping(projection, "experience_contract"),
        "steps": [row["step"] for row in projection_rows],
        "tactic_modules": _sdl_tactic_modules(techniques),
        "technique_catalog": techniques,
    }


def _sdl_projection_rows(
    module_specs: dict[str, Any], projection: dict[str, Any]
) -> list[dict[str, Any]]:
    enrichment = _sdl_projection_enrichment(projection)
    return [
        _sdl_projection_row(index, behavior_id, spec, enrichment)
        for index, (behavior_id, spec) in enumerate(sorted(module_specs.items()), start=1)
    ]


def _sdl_projection_enrichment(
    projection: dict[str, Any],
) -> dict[str, dict[str, dict[str, Any]]]:
    step_rows = _entries(projection, "steps")
    return {
        "by_behavior": {
            _text(row, "aces_behavior_specification"): row
            for row in step_rows
            if _text(row, "aces_behavior_specification")
        },
        "by_id": {_text(row, "path_step"): row for row in step_rows},
    }


def _sdl_projection_row(
    index: int,
    behavior_id: str,
    spec: object,
    enrichment: dict[str, dict[str, dict[str, Any]]],
) -> dict[str, Any]:
    spec_row = spec if isinstance(spec, dict) else {}
    path_step = _path_step_from_behavior_id(behavior_id, index)
    step_enrichment = enrichment["by_behavior"].get(behavior_id) or enrichment["by_id"].get(
        path_step, {}
    )
    evidence = _string_list(step_enrichment.get("evidence"))
    return {
        "step": _sdl_step_row(behavior_id, path_step, spec_row, step_enrichment, evidence),
        "techniques": _sdl_technique_rows(behavior_id, path_step, spec_row, evidence),
    }


def _sdl_step_row(
    behavior_id: str,
    path_step: str,
    spec: dict[str, Any],
    enrichment: dict[str, Any],
    evidence: list[str],
) -> dict[str, Any]:
    return {
        "path_step": path_step,
        "aces_behavior_specification": behavior_id,
        "tier": _text(enrichment, "tier") or _text_any(spec, "lifecycle_state", "lifecycle-state"),
        "surface": _text(enrichment, "surface") or _surface_from_behavior_id(behavior_id),
        "estimated_minutes": enrichment.get("estimated_minutes"),
        "objective": _text(enrichment, "objective")
        or f"Exercise SDL behavior specification {behavior_id}.",
        "evidence": evidence,
        "flag_outcome": _text(enrichment, "flag_outcome"),
        "justification": _text(enrichment, "justification")
        or "Defined by the ACES SDL behavior specification.",
    }


def _sdl_technique_rows(
    behavior_id: str,
    path_step: str,
    spec: dict[str, Any],
    evidence: list[str],
) -> list[dict[str, Any]]:
    return [
        {
            "id": _sdl_technique_id(path_step, ref, behavior_id),
            "name": _behavior_ref_name(ref),
            "tactics": [ref],
            "challenge_step": path_step,
            "surface": behavior_id,
            "evidence": evidence[0] if evidence else "",
            "relationship": "sdl_behavior_ref",
            "coverage_status": _text_any(spec, "lifecycle_state", "lifecycle-state"),
            "planned_action": f"Exercise {ref} through {behavior_id}.",
            "rationale": "Derived from ACES SDL ai_offensive_behavior_refs.",
        }
        for ref in _sdl_behavior_refs(spec)
    ]


def _sdl_tactic_modules(techniques: list[dict[str, Any]]) -> list[dict[str, Any]]:
    steps_by_tactic = _sdl_steps_by_tactic(techniques)
    return [
        {
            "tactic_id": tactic_id,
            "name": _behavior_ref_name(tactic_id),
            "challenge_steps": sorted(challenge_steps),
        }
        for tactic_id, challenge_steps in sorted(steps_by_tactic.items())
    ]


def _sdl_steps_by_tactic(techniques: list[dict[str, Any]]) -> dict[str, set[str]]:
    steps_by_tactic: dict[str, set[str]] = {}
    for row in techniques:
        challenge_step = row.get("challenge_step")
        if not isinstance(challenge_step, str):
            continue
        for tactic_id in _string_list(row.get("tactics")):
            steps_by_tactic.setdefault(tactic_id, set()).add(challenge_step)
    return steps_by_tactic


def _sdl_module_specs(behavior_specs: dict[str, Any]) -> dict[str, Any]:
    return {
        key: value
        for key, value in behavior_specs.items()
        if not _sdl_challenge_extension(value if isinstance(value, dict) else {})
    }


def _sdl_challenge_specs(behavior_specs: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {
        key: value
        for key, value in behavior_specs.items()
        if isinstance(value, dict) and _sdl_challenge_extension(value)
    }


def _sdl_challenge_extension(spec: dict[str, Any]) -> dict[str, Any]:
    extensions = _mapping(spec, "extensions")
    value = extensions.get("x-keplerops:challenge")
    return value if isinstance(value, dict) else {}


def _path_step_from_behavior_id(behavior_id: str, index: int) -> str:
    match = re.search(r"(?:^|-)module-(\d+)", behavior_id)
    if match:
        return str(int(match.group(1)))
    match = re.search(r"(?:^|-)m(?:odule)?[-_]?(\d+)", behavior_id, re.IGNORECASE)
    if match:
        return str(int(match.group(1)))
    return str(index)


def _surface_from_behavior_id(behavior_id: str) -> str:
    match = re.match(r"module-\d+-(.+)", behavior_id)
    return match.group(1) if match else behavior_id


def _sdl_behavior_refs(spec: dict[str, Any]) -> list[str]:
    return _string_list(spec.get("ai_offensive_behavior_refs")) or _string_list(
        spec.get("ai-offensive-behavior-refs")
    )


def _sdl_technique_id(path_step: str, behavior_ref: str, behavior_id: str = "") -> str:
    base = f"SDL.{path_step}.{behavior_ref}"
    if len(base) <= 32:
        return base
    digest = hashlib.sha1(f"{path_step}:{behavior_id}:{behavior_ref}".encode()).hexdigest()[:8]
    prefix = f"SDL.{path_step}."
    suffix = f".{digest}"
    slug_limit = max(1, 32 - len(prefix) - len(suffix))
    slug = behavior_ref[:slug_limit].rstrip("-_.") or "behavior"
    return f"{prefix}{slug}{suffix}"


def _behavior_ref_name(behavior_ref: str) -> str:
    return behavior_ref.replace("-", " ").replace("_", " ").title()


@transaction.atomic
def import_projection(scenario: Scenario, data: dict[str, Any]) -> tuple[Revision, bool]:
    """Import a projection into ``scenario``; returns ``(revision, created)``."""
    return _import_revision(scenario, data, {}, _content_digest(data, {}))


def import_pack(scenario: Scenario, path: Path) -> tuple[Revision, bool]:
    """Import a full pack directory when available, including challenge contracts."""
    contracts = load_pack_contracts(path)
    projection_error: ProjectionError | None = None
    try:
        projection, _ = load_projection(path)
    except ProjectionError as exc:
        projection = {}
        projection_error = exc
    if _sdl_defines_modules(contracts.get("sdl", {})):
        data = _projection_from_sdl(contracts["sdl"], projection)
    elif projection:
        data = projection
    elif projection_error:
        raise projection_error
    else:
        raise ProjectionError(f"No importable scenario content found under {path}.")
    return _import_revision(scenario, data, contracts, _content_digest(data, contracts))


@transaction.atomic
def _import_revision(
    scenario: Scenario,
    data: dict[str, Any],
    contracts: dict[str, Any],
    digest: str,
) -> tuple[Revision, bool]:
    framework = _mapping(data, "framework")
    metadata = _revision_metadata(data, contracts)

    existing = Revision.objects.filter(scenario=scenario, content_digest=digest).first()
    if existing is not None:
        if existing.metadata != metadata:
            existing.metadata = metadata
            existing.save(update_fields=["metadata", "updated_at"])
        return existing, False

    revision = Revision.objects.create(
        scenario=scenario,
        label=_text(data, "mapping_id", "revision"),
        mapping_id=_text(data, "mapping_id"),
        content_digest=digest,
        source_repo=_text(data, "source_oracle"),
        framework_name=_text(framework, "name"),
        framework_release=_text(framework, "release"),
        metadata=metadata,
    )
    _load_objects(revision, data)
    _load_challenges(revision, contracts)
    return revision, True


def _revision_metadata(data: dict[str, Any], contracts: dict[str, Any]) -> dict[str, Any]:
    return {
        "experience_contract": _mapping(data, "experience_contract"),
        "semantic_binding": _mapping(data, "semantic_binding"),
        "challenge_contracts": _contract_metadata(contracts),
        "scoring": _scoring_metadata(contracts.get("scoring", {})),
        "environment": _environment_metadata(contracts),
        "schedule": _schedule_metadata(data, contracts),
        "telemetry": _telemetry_metadata(contracts.get("telemetry", {})),
        "topology": _sdl_topology_metadata(contracts.get("sdl", {}), contracts.get("topology", {})),
    }


def _contract_metadata(contracts: dict[str, Any]) -> dict[str, Any]:
    if not contracts:
        return {}
    return {
        "has_challenges": bool(contracts.get("challenges")),
        "has_placement": bool(contracts.get("placement")),
        "has_objectives": bool(contracts.get("objectives")),
        "has_telemetry": bool(contracts.get("telemetry")),
        "has_scoring": bool(contracts.get("scoring")),
        "has_topology": bool(contracts.get("topology")),
        "has_software_inventory": bool(contracts.get("software_inventory")),
        "has_planned_assets": bool(contracts.get("planned_assets")),
        "has_affordances": bool(contracts.get("affordances")),
        "has_sdl": bool(contracts.get("sdl")),
        "implemented_outcomes": sorted(contracts.get("runtime_challenges", {})),
    }


def _scoring_metadata(scoring: object) -> dict[str, Any]:
    scoring = scoring if isinstance(scoring, dict) else {}
    return {
        "mode": _text(scoring, "mode"),
        "max_points": _int_or_none(scoring.get("max_points")),
        "awards": [_award_row(row) for row in _entries(scoring, "awards")],
        "alternate_awards": [_award_row(row) for row in _entries(scoring, "alternate_awards")],
        "bundles": [_bundle_row(row) for row in _entries(scoring, "bundles")],
    }


def _award_row(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": _award_id(row),
        "points": _int_or_none(row.get("points")),
        "evidence": _string_list(row.get("evidence")),
        "required_outcomes": _string_list(row.get("required_outcomes")),
        "description": _text(row, "description"),
    }


def _bundle_row(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": _text(row, "id") or _text(row, "bundle_id"),
        "title": _text(row, "title") or _text(row, "name"),
        "description": _text(row, "description"),
        "outcomes": _string_list(row.get("outcomes")) or _string_list(row.get("required_outcomes")),
        "points": _int_or_none(row.get("points")),
    }


def _environment_metadata(contracts: dict[str, Any]) -> dict[str, Any]:
    topology = contracts.get("topology", {})
    topology = topology if isinstance(topology, dict) else {}
    inventory = contracts.get("software_inventory", {})
    inventory = inventory if isinstance(inventory, dict) else {}
    planned_assets = contracts.get("planned_assets", {})
    planned_assets = planned_assets if isinstance(planned_assets, dict) else {}
    affordances = contracts.get("affordances", {})
    affordances = affordances if isinstance(affordances, dict) else {}
    sdl = contracts.get("sdl", {})
    sdl = sdl if isinstance(sdl, dict) else {}

    return {
        "assets": [_asset_row(row) for row in _entries(topology, "assets")],
        "services": [_service_row(row) for row in _entries(topology, "services")],
        "applications": [_application_row(row) for row in _entries(topology, "applications")],
        "datasets": [_dataset_row(row) for row in _entries(topology, "datasets")],
        "artifacts": [_artifact_row(row) for row in _entries(topology, "artifacts")],
        "path_objectives": [
            _path_objective_row(row) for row in _entries(topology, "path_objectives")
        ],
        "validation_flows": [
            _validation_flow_row(row) for row in _entries(topology, "validation_flows")
        ],
        "software_components": [
            _software_component_row(row) for row in _entries(inventory, "components")
        ],
        "planned_assets": [
            _planned_asset_row(row) for row in _entries(planned_assets, "asset_sets")
        ],
        "affordances": [_affordance_row(row) for row in _entries(affordances, "affordances")],
        "sdl_behavior_specs": _sdl_behavior_rows(
            _mapping_any(sdl, "behavior_specifications", "behavior-specifications")
        ),
        "counts": {
            "profiles": _mapping_count(topology.get("profiles")),
            "zones": len(_entries(topology, "zones")),
            "networks": len(_entries(topology, "networks")),
            "assets": len(_entries(topology, "assets")),
            "services": len(_entries(topology, "services")),
            "applications": len(_entries(topology, "applications")),
            "datasets": len(_entries(topology, "datasets")),
            "artifacts": len(_entries(topology, "artifacts")),
            "path_objectives": len(_entries(topology, "path_objectives")),
        },
    }


def _schedule_metadata(data: dict[str, Any], contracts: dict[str, Any]) -> dict[str, Any]:
    steps = _entries(data, "steps")
    return {
        "total_minutes": sum(
            value
            for value in (_int_or_none(row.get("estimated_minutes")) for row in steps)
            if value
        ),
        "module_count": len(steps),
        "outcome_count": len(_entries(contracts.get("objectives", {}), "outcomes")),
    }


def _telemetry_metadata(telemetry: object) -> dict[str, Any]:
    telemetry = telemetry if isinstance(telemetry, dict) else {}
    return {
        "sink_service": _text(telemetry, "sink_service"),
        "safe_fields": _string_list(telemetry.get("safe_fields")),
        "forbidden_fields": _string_list(telemetry.get("forbidden_fields")),
        "negative_gates": [_generic_id_row(row) for row in _entries(telemetry, "negative_gates")],
    }


def _sdl_topology_metadata(sdl: object, topology: object) -> dict[str, Any]:
    sdl = sdl if isinstance(sdl, dict) else {}
    topology = topology if isinstance(topology, dict) else {}
    nodes = _mapping(sdl, "nodes")
    infrastructure = _mapping(sdl, "infrastructure")
    relationships = _mapping(sdl, "relationships")
    entities = _mapping(sdl, "entities")
    agents = _mapping(sdl, "agents")
    assets = _entries(topology, "assets")
    services = _entries(topology, "services")
    assets_by_id = {_text(row, "id"): row for row in assets if _text(row, "id")}
    services_by_id = {_text(row, "id"): row for row in services if _text(row, "id")}

    return {
        "source": "sdl",
        "parser": _text(sdl, "parser"),
        "advisories": _string_list(sdl.get("advisories")),
        "parser_error": _text(sdl, "parser_error"),
        "name": _text(sdl, "name"),
        "version": _text(sdl, "version"),
        "description": _text(sdl, "description"),
        "infrastructure": [
            _sdl_infrastructure_row(key, value, nodes)
            for key, value in sorted(infrastructure.items())
        ],
        "relationships": [
            _sdl_relationship_row(key, value) for key, value in sorted(relationships.items())
        ],
        "nodes": [
            _sdl_node_row(key, value, assets_by_id, services_by_id)
            for key, value in sorted(nodes.items())
        ],
        "entities": [_sdl_entity_row(key, value) for key, value in sorted(entities.items())],
        "agents": [_sdl_agent_row(key, value) for key, value in sorted(agents.items())],
        "zones": [_zone_row(row) for row in _entries(topology, "zones")],
        "networks": [_network_row(row) for row in _entries(topology, "networks")],
        "links": _sdl_actor_links(entities, agents, nodes),
        "coverage": {
            "sdl_node_count": len(nodes),
            "sdl_infrastructure_count": len(infrastructure),
            "sdl_relationship_count": len(relationships),
            "sdl_service_count": sum(
                len(_sequence(value, "services"))
                for value in nodes.values()
                if isinstance(value, dict)
            ),
            "sdl_agent_count": len(agents),
            "sdl_entity_count": len(entities),
            "contract_asset_count": len(assets),
            "contract_service_count": len(services),
            "contract_assets_missing_from_sdl": [
                _asset_row(row) for row in assets if _text(row, "id") not in nodes
            ],
            "contract_services_missing_from_sdl": [
                _service_row(row)
                for row in services
                if _text(row, "id") not in _sdl_service_names(nodes)
            ],
        },
    }


def _sdl_infrastructure_row(
    infrastructure_id: str,
    row: object,
    nodes: dict[str, Any],
) -> dict[str, Any]:
    row = row if isinstance(row, dict) else {}
    node = nodes.get(infrastructure_id, {})
    node = node if isinstance(node, dict) else {}
    properties = _mapping(row, "properties")
    return {
        "id": infrastructure_id,
        "type": _text(row, "type") or _text(node, "type"),
        "count": _int_or_none(row.get("count")),
        "cidr": _text(properties, "cidr"),
        "gateway": _text(properties, "gateway"),
        "internal": bool(properties.get("internal")),
        "description": _text(node, "description") or _text(row, "description"),
        "properties": _string_mapping(properties),
    }


def _sdl_relationship_row(relationship_id: str, row: object) -> dict[str, Any]:
    row = row if isinstance(row, dict) else {}
    properties = _mapping(row, "properties")
    return {
        "id": relationship_id,
        "type": _text(row, "type"),
        "source": _text(row, "source"),
        "target": _text(row, "target"),
        "ports": _text(properties, "ports"),
        "category": _text(properties, "category"),
        "properties": _string_mapping(properties),
    }


def _sdl_node_row(
    node_id: str,
    row: object,
    assets_by_id: dict[str, dict[str, Any]],
    services_by_id: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    row = row if isinstance(row, dict) else {}
    asset = assets_by_id.get(node_id, {})
    services = [_sdl_service_row(service, services_by_id) for service in _sequence(row, "services")]
    return {
        "id": node_id,
        "type": _text(row, "type"),
        "os": _text(row, "os"),
        "os_version": _text_any(row, "os_version", "os-version"),
        "resources": _string_mapping(row.get("resources")),
        "description": _text(row, "description"),
        "services": services,
        "zone": _text(asset, "zone"),
        "networks": _string_list(asset.get("networks")),
        "role": _text(asset, "role"),
        "visibility": _text(asset, "visibility"),
        "implementation_status": _text(asset, "implementation_status"),
    }


def _sdl_service_row(row: object, services_by_id: dict[str, dict[str, Any]]) -> dict[str, Any]:
    row = row if isinstance(row, dict) else {}
    service_id = _text(row, "name") or _text(row, "id")
    service = services_by_id.get(service_id, {})
    return {
        "id": service_id,
        "name": service_id,
        "port": _int_or_none(row.get("port")),
        "asset": _text(service, "asset"),
        "software_component": _text(service, "software_component"),
        "visibility": _text(service, "visibility"),
        "reset_owner": _text(service, "reset_owner"),
        "description": _text(service, "description"),
    }


def _sdl_entity_row(entity_id: str, row: object) -> dict[str, Any]:
    row = row if isinstance(row, dict) else {}
    return {
        "id": entity_id,
        "role": _text(row, "role"),
        "description": _text(row, "description"),
    }


def _sdl_agent_row(agent_id: str, row: object) -> dict[str, Any]:
    row = row if isinstance(row, dict) else {}
    initial_knowledge = _mapping_any(row, "initial_knowledge", "initial-knowledge")
    return {
        "id": agent_id,
        "entity": _text(row, "entity"),
        "description": _text(row, "description"),
        "initial_hosts": _string_list(initial_knowledge.get("hosts")),
        "initial_services": _string_list(initial_knowledge.get("services")),
    }


def _zone_row(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "name": _text(row, "name"),
        "kind": _text(row, "kind"),
        "networks": _string_list(row.get("networks")),
        "description": _text(row, "description"),
    }


def _network_row(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "name": _text(row, "name"),
        "zone": _text(row, "zone"),
        "scope": _text(row, "scope"),
        "isolation": _text(row, "isolation"),
        "providers": _string_list(row.get("providers")),
        "routes": _string_list(row.get("routes")),
    }


def _sdl_actor_links(
    entities: dict[str, Any],
    agents: dict[str, Any],
    nodes: dict[str, Any],
) -> list[dict[str, str]]:
    links: list[dict[str, str]] = []
    for agent_id, agent in sorted(agents.items()):
        if not isinstance(agent, dict):
            continue
        entity_id = _text(agent, "entity")
        if entity_id in entities:
            links.append({"source": entity_id, "target": agent_id, "type": "entity-agent"})
        initial_knowledge = _mapping_any(agent, "initial_knowledge", "initial-knowledge")
        for host in _string_list(initial_knowledge.get("hosts")):
            if host in nodes:
                links.append({"source": agent_id, "target": host, "type": "agent-node"})
        for service in _string_list(initial_knowledge.get("services")):
            links.append({"source": agent_id, "target": service, "type": "agent-service"})
    return links


def _sdl_service_names(nodes: dict[str, Any]) -> set[str]:
    names: set[str] = set()
    for node in nodes.values():
        if not isinstance(node, dict):
            continue
        for service in _sequence(node, "services"):
            if isinstance(service, dict):
                service_id = _text(service, "name") or _text(service, "id")
                if service_id:
                    names.add(service_id)
    return names


def _string_mapping(value: object) -> dict[str, str]:
    if not isinstance(value, dict):
        return {}
    return {str(key): str(item) for key, item in value.items()}


def _asset_row(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": _text(row, "id"),
        "hostname": _text(row, "hostname"),
        "asset_type": _text(row, "asset_type"),
        "role": _text(row, "role"),
        "zone": _text(row, "zone"),
        "networks": _string_list(row.get("networks")),
        "software_component": _text(row, "software_component"),
        "visibility": _text(row, "visibility"),
        "reset_owner": _text(row, "reset_owner"),
        "implementation_status": _text(row, "implementation_status"),
        "description": _text(row, "description"),
    }


def _service_row(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": _text(row, "id"),
        "asset": _text(row, "asset"),
        "ports": [str(port) for port in _sequence(row, "ports")],
        "software_component": _text(row, "software_component"),
        "visibility": _text(row, "visibility"),
        "reset_owner": _text(row, "reset_owner"),
        "description": _text(row, "description"),
    }


def _application_row(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": _text(row, "id"),
        "asset": _text(row, "asset"),
        "app_type": _text(row, "app_type"),
        "software_component": _text(row, "software_component"),
        "auth_service": _text(row, "auth_service"),
        "visibility": _text(row, "visibility"),
        "reset_owner": _text(row, "reset_owner"),
        "description": _text(row, "description"),
    }


def _dataset_row(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": _text(row, "id"),
        "kind": _text(row, "kind"),
        "locations": _string_list(row.get("locations")),
        "synthetic": bool(row.get("synthetic")),
        "visibility": _text(row, "visibility"),
        "reset_owner": _text(row, "reset_owner"),
        "proof": _mapping(row, "proof"),
        "description": _text(row, "description"),
    }


def _artifact_row(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": _text(row, "id"),
        "kind": _text(row, "kind"),
        "asset": _text(row, "asset"),
        "visibility": _text(row, "visibility"),
        "reset_owner": _text(row, "reset_owner"),
        "secret_handling": _text(row, "secret_handling"),
        "description": _text(row, "description"),
    }


def _path_objective_row(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": _text(row, "id"),
        "title": _text(row, "title"),
        "success_states": _string_list(row.get("success_states")),
        "build_targets": _string_list(row.get("build_targets")),
        "test_targets": _string_list(row.get("test_targets")),
        "walkthrough_targets": _string_list(row.get("walkthrough_targets")),
    }


def _validation_flow_row(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": _text(row, "id"),
        "command": _text(row, "command"),
        "covers": _string_list(row.get("covers")),
    }


def _software_component_row(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": _text(row, "component_id") or _text(row, "id"),
        "topology_refs": _string_list(row.get("topology_refs")),
        "upstream": _text(row, "upstream"),
        "operating_mode": _text(row, "operating_mode"),
        "profiles": _string_list(row.get("profiles")),
        "authenticity": _text(row, "authenticity"),
        "path_critical": bool(row.get("path_critical")),
    }


def _planned_asset_row(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": _text(row, "asset_id") or _text(row, "id"),
        "category": _text(row, "category"),
        "implementation_status": _text(row, "implementation_status"),
        "paths": _string_list(row.get("paths")),
        "visibility": _text(row, "visibility"),
        "source_refs": _string_list(row.get("source_refs")),
        "topology_refs": _string_list(row.get("topology_refs")),
        "implementation_plan": _text(row, "implementation_plan"),
    }


def _affordance_row(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": _text(row, "id"),
        "title": _text(row, "title") or _text(row, "name"),
        "type": _text(row, "type") or _text(row, "kind"),
        "asset": _text(row, "asset"),
        "description": _text(row, "description"),
    }


def _sdl_behavior_rows(rows: dict[str, Any]) -> list[dict[str, Any]]:
    return [{"id": key, "title": _text(value, "title")} for key, value in sorted(rows.items())]


def _generic_id_row(row: dict[str, Any]) -> dict[str, Any]:
    return {"id": _text(row, "id"), "description": _text(row, "description")}


def _mapping_count(value: object) -> int:
    return len(value) if isinstance(value, dict) else 0


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


def _load_challenges(revision: Revision, contracts: dict[str, Any]) -> None:
    if not contracts:
        return
    behavior_specs = _contract_behavior_specs(contracts)
    if _sdl_challenge_specs(behavior_specs):
        _load_sdl_challenges(revision, behavior_specs)
    else:
        _load_legacy_challenges(revision, _legacy_challenge_context(revision, contracts))


def _contract_behavior_specs(contracts: dict[str, Any]) -> dict[str, Any]:
    sdl = contracts.get("sdl", {})
    return _mapping_any(
        sdl if isinstance(sdl, dict) else {},
        "behavior_specifications",
        "behavior-specifications",
    )


def _legacy_challenge_context(
    revision: Revision, contracts: dict[str, Any]
) -> LegacyChallengeContext:
    scoring = contracts.get("scoring", {})
    scoring = scoring if isinstance(scoring, dict) else {}
    runtime = contracts.get("runtime_challenges", {})
    return LegacyChallengeContext(
        challenges=_rows_by_key(contracts.get("challenges", {}), "challenges", "flag_id"),
        placements=_entries(contracts.get("placement", {}), "flags"),
        outcomes=_rows_by_key(contracts.get("objectives", {}), "outcomes", "id"),
        path_steps=_rows_by_key(contracts.get("objectives", {}), "path_steps", "id"),
        telemetry=_rows_by_key(contracts.get("telemetry", {}), "events", "evidence"),
        awards=_award_rows(scoring),
        alternate_awards=_entries(scoring, "alternate_awards"),
        bundles=_entries(scoring, "bundles"),
        runtime=runtime if isinstance(runtime, dict) else {},
        steps=_revision_steps_by_path(revision),
        techniques_by_step=_techniques_by_step(revision),
    )


def _rows_by_key(source: object, section: str, key: str) -> dict[str, dict[str, Any]]:
    return {_text(row, key): row for row in _entries(source, section)}


def _award_rows(scoring: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {_award_id(row): row for row in _entries(scoring, "awards") if _award_id(row)}


def _revision_steps_by_path(revision: Revision) -> dict[str, Step]:
    return {step.path_step: step for step in revision.steps.all()}


def _revision_module_steps(revision: Revision) -> dict[str, Step]:
    return {
        step.behavior_specification: step
        for step in revision.steps.all()
        if step.behavior_specification
    }


def _techniques_by_step(revision: Revision) -> dict[str, list[Technique]]:
    techniques_by_step: dict[str, list[Technique]] = {}
    for technique in revision.techniques.select_related("step").all():
        if technique.step_id:
            techniques_by_step.setdefault(technique.step.path_step, []).append(technique)
    return techniques_by_step


def _load_legacy_challenges(revision: Revision, context: LegacyChallengeContext) -> None:
    for placement in context.placements:
        challenge_row = _legacy_challenge_row(placement, context)
        if challenge_row is None:
            continue
        challenge = _create_legacy_challenge(revision, challenge_row, context)
        _link_challenge_to_steps(challenge, challenge_row.canonical_steps, context)
        _load_challenge_evidence(
            challenge,
            revision,
            challenge_row.outcome,
            challenge_row.placement,
            challenge_row.path_step_contracts,
            context.telemetry,
        )


def _legacy_challenge_row(
    placement: dict[str, Any], context: LegacyChallengeContext
) -> LegacyChallengeRow | None:
    outcome_id = _text(placement, "outcome")
    challenge_row = context.challenges.get(_text(placement, "flag_id"))
    outcome = context.outcomes.get(outcome_id)
    if not challenge_row or not outcome:
        return None

    canonical_steps = _string_list(outcome.get("canonical_steps"))
    path_step_contracts = _path_step_contracts(canonical_steps, context)
    runtime_row = context.runtime.get(outcome_id)
    return LegacyChallengeRow(
        placement=placement,
        runtime_row=runtime_row if isinstance(runtime_row, dict) else {},
        challenge_row=challenge_row,
        outcome=outcome,
        outcome_id=outcome_id,
        canonical_steps=canonical_steps,
        path_step_contracts=path_step_contracts,
        award=context.awards.get(outcome_id, {}),
        evidence_ids=_challenge_evidence_ids(outcome, placement),
        implemented=isinstance(runtime_row, dict) and bool(runtime_row),
    )


def _path_step_contracts(
    canonical_steps: list[str], context: LegacyChallengeContext
) -> list[dict[str, Any]]:
    return [
        path_step
        for path_step_id in canonical_steps
        if isinstance((path_step := context.path_steps.get(path_step_id, {})), dict)
    ]


def _create_legacy_challenge(
    revision: Revision,
    row: LegacyChallengeRow,
    context: LegacyChallengeContext,
) -> Challenge:
    return Challenge.objects.create(
        revision=revision,
        step=context.steps.get(row.canonical_steps[0]) if row.canonical_steps else None,
        flag_id=_text(row.placement, "flag_id"),
        outcome_id=row.outcome_id,
        title=_text(row.challenge_row, "title"),
        question=_text(row.challenge_row, "question"),
        category=_text(row.challenge_row, "category"),
        difficulty=_text(row.challenge_row, "difficulty"),
        points=_int_or_none(row.challenge_row.get("points"))
        or _int_or_none(row.award.get("points")),
        hints=_string_list(row.challenge_row.get("hints")),
        implemented=row.implemented,
        runtime_entrypoint=_text(row.runtime_row, "entrypoint"),
        source_path=_first_evidence_source(row.path_step_contracts),
        metadata=_legacy_challenge_metadata(row, context),
    )


def _legacy_challenge_metadata(
    row: LegacyChallengeRow,
    context: LegacyChallengeContext,
) -> dict[str, Any]:
    return {
        "delivery": _mapping(row.placement, "delivery"),
        "profiles": _string_list(row.placement.get("profiles")),
        "canonical_steps": row.canonical_steps,
        "objective": {
            "title": _text(row.outcome, "title"),
            "success_state": _text(row.outcome, "success_state"),
        },
        "scoring": _award_row(row.award),
        "alternate_awards": [
            _award_row(award)
            for award in context.alternate_awards
            if _award_id(award) == row.outcome_id
        ],
        "bundles": [
            _bundle_row(bundle)
            for bundle in context.bundles
            if row.outcome_id in _bundle_outcomes(bundle)
        ],
        "readiness": _legacy_challenge_readiness(row, context),
    }


def _legacy_challenge_readiness(
    row: LegacyChallengeRow,
    context: LegacyChallengeContext,
) -> dict[str, bool]:
    return {
        "challenge_contract": True,
        "placement": True,
        "objective": True,
        "scoring": bool(row.award),
        "runtime": row.implemented,
        "telemetry": all(evidence_id in context.telemetry for evidence_id in row.evidence_ids),
        "evidence_contract": _all_evidence_has_contract(row.evidence_ids, row.path_step_contracts),
    }


def _link_challenge_to_steps(
    challenge: Challenge,
    canonical_steps: list[str],
    context: LegacyChallengeContext,
) -> None:
    linked_techniques = _techniques_for_steps(context.techniques_by_step, canonical_steps)
    if linked_techniques:
        challenge.techniques.set(linked_techniques)


def _techniques_for_steps(
    techniques_by_step: dict[str, list[Technique]], path_step_ids: list[str]
) -> list[Technique]:
    techniques = []
    for path_step_id in path_step_ids:
        techniques.extend(techniques_by_step.get(path_step_id, []))
    return techniques


def _load_sdl_challenges(revision: Revision, behavior_specs: dict[str, Any]) -> None:
    context = _sdl_challenge_context(revision)
    challenge_specs = _sdl_challenge_specs(behavior_specs)
    for index, (spec_id, spec) in enumerate(sorted(challenge_specs.items())):
        _load_sdl_challenge(revision, context, index, spec_id, spec)


def _sdl_challenge_context(revision: Revision) -> SdlChallengeContext:
    return SdlChallengeContext(
        module_steps=_revision_module_steps(revision),
        steps_by_path=_revision_steps_by_path(revision),
        techniques_by_step=_techniques_by_step(revision),
    )


def _load_sdl_challenge(
    revision: Revision,
    context: SdlChallengeContext,
    index: int,
    spec_id: str,
    spec: dict[str, Any],
) -> None:
    extension = _sdl_challenge_extension(spec)
    step = _sdl_challenge_step(context, spec_id, extension, index)
    evidence_key = _sdl_challenge_evidence_key(extension)
    challenge = _create_sdl_challenge(revision, spec_id, extension, step, evidence_key)
    _link_sdl_challenge_techniques(challenge, step, context)
    _load_sdl_challenge_evidence(challenge, revision, spec_id, extension, evidence_key)


def _sdl_challenge_step(
    context: SdlChallengeContext,
    spec_id: str,
    extension: dict[str, Any],
    index: int,
) -> Step | None:
    module_id = _text(extension, "module")
    step = context.module_steps.get(module_id)
    if step is None and module_id:
        step = context.steps_by_path.get(_path_step_from_behavior_id(module_id, index + 1))
    if step is None:
        step = context.steps_by_path.get(_path_step_from_behavior_id(spec_id, index + 1))
    return step


def _sdl_challenge_evidence_key(extension: dict[str, Any]) -> str:
    return _text(extension, "proof_obligation") or _text(extension, "telemetry_profile")


def _create_sdl_challenge(
    revision: Revision,
    spec_id: str,
    extension: dict[str, Any],
    step: Step | None,
    evidence_key: str,
) -> Challenge:
    module_id = _text(extension, "module")
    points = _int_or_none(extension.get("points"))
    return Challenge.objects.create(
        revision=revision,
        step=step,
        flag_id=_sdl_challenge_flag_id(spec_id, extension),
        outcome_id=_text(extension, "outcome"),
        title=_text(extension, "title") or spec_id,
        question=_text(extension, "proof_obligation"),
        category=module_id,
        difficulty=_text(extension, "difficulty"),
        points=points,
        hints=[],
        implemented=_sdl_challenge_implemented(extension),
        runtime_entrypoint="",
        source_path=f"sdl:{spec_id}",
        metadata=_sdl_challenge_metadata(spec_id, extension, step, points, evidence_key),
    )


def _sdl_challenge_flag_id(spec_id: str, extension: dict[str, Any]) -> str:
    return _text(extension, "flag_id") or _text(extension, "challenge_id") or spec_id


def _sdl_challenge_implemented(extension: dict[str, Any]) -> bool:
    return _text(extension, "implementation_status") == "source-implemented"


def _sdl_challenge_metadata(
    spec_id: str,
    extension: dict[str, Any],
    step: Step | None,
    points: int | None,
    evidence_key: str,
) -> dict[str, Any]:
    return {
        "sdl_behavior_specification": spec_id,
        "canonical_steps": [step.path_step] if step else [],
        "delivery": {
            "interfaces": _string_list(extension.get("interfaces")),
            "live_fire": bool(extension.get("live_fire")),
        },
        "scoring": {
            "id": _text(extension, "outcome"),
            "points": points,
            "evidence": [evidence_key] if evidence_key else [],
            "description": _text(extension, "proof_obligation"),
        },
        "readiness": {
            "sdl_challenge": True,
            "module": step is not None,
            "scoring": points is not None,
            "evidence": bool(evidence_key),
            "runtime": _sdl_challenge_implemented(extension),
        },
        "sdl_challenge": _sdl_challenge_detail_metadata(spec_id, extension),
    }


def _sdl_challenge_detail_metadata(spec_id: str, extension: dict[str, Any]) -> dict[str, Any]:
    return {
        "challenge_id": _text(extension, "challenge_id") or spec_id,
        "disposition": _text(extension, "disposition"),
        "prerequisites": _string_list(extension.get("prerequisites")),
        "hint_costs": [
            value for value in _sequence(extension, "hint_costs") if isinstance(value, int)
        ],
        "target_minutes": _int_or_none(extension.get("target_minutes")),
        "min_minutes": _int_or_none(extension.get("min_minutes")),
        "max_minutes": _int_or_none(extension.get("max_minutes")),
        "telemetry_profile": _text(extension, "telemetry_profile"),
        "proof_obligation": _text(extension, "proof_obligation"),
        "reliability": _text(extension, "reliability"),
        "implementation_status": _text(extension, "implementation_status"),
        "issue": _int_or_none(extension.get("issue")),
    }


def _link_sdl_challenge_techniques(
    challenge: Challenge, step: Step | None, context: SdlChallengeContext
) -> None:
    if step and context.techniques_by_step.get(step.path_step):
        challenge.techniques.set(context.techniques_by_step[step.path_step])


def _load_sdl_challenge_evidence(
    challenge: Challenge,
    revision: Revision,
    spec_id: str,
    extension: dict[str, Any],
    evidence_key: str,
) -> None:
    if not evidence_key:
        return

    proof_obligation = _text(extension, "proof_obligation")
    evidence, _ = Evidence.objects.get_or_create(
        revision=revision,
        evidence_id=evidence_key,
        defaults={"description": f"Proof obligation: {proof_obligation}"},
    )
    if not evidence.description:
        evidence.description = f"Proof obligation: {proof_obligation}"
        evidence.save(update_fields=["description"])
    ChallengeEvidenceRequirement.objects.create(
        challenge=challenge,
        evidence=evidence,
        evidence_key=evidence_key,
        predicate=proof_obligation,
        source_path=f"sdl:{spec_id}",
        event_kind=_text(extension, "telemetry_profile"),
        proof_fields=[],
    )


def _load_challenge_evidence(
    challenge: Challenge,
    revision: Revision,
    outcome: dict[str, Any],
    placement: dict[str, Any],
    path_step_contracts: list[dict[str, Any]],
    telemetry: dict[str, dict[str, Any]],
) -> None:
    evidence_ids = _challenge_evidence_ids(outcome, placement)
    path_step_evidence = _evidence_contracts(path_step_contracts)

    for evidence_id in evidence_ids:
        event = telemetry.get(evidence_id, {})
        evidence_contract = path_step_evidence.get(evidence_id, {})
        evidence, _ = Evidence.objects.get_or_create(revision=revision, evidence_id=evidence_id)
        predicate = _text(evidence_contract, "predicate")
        if predicate and not evidence.description:
            evidence.description = predicate
            evidence.save(update_fields=["description"])
        ChallengeEvidenceRequirement.objects.create(
            challenge=challenge,
            evidence=evidence,
            evidence_key=evidence_id,
            predicate=predicate,
            source_path=_text(evidence_contract, "source"),
            event_id=_text(event, "id"),
            event_kind=_text(event, "event_kind"),
            source_service=_text(event, "source_service"),
            source_asset=_text(event, "source_asset"),
            freshness_seconds=_int_or_none(event.get("freshness_seconds")),
            reset_owner=_text(event, "reset_owner"),
            fields=_string_list(event.get("fields")),
            proof_fields=_string_list(evidence_contract.get("proof_fields")),
        )


def _challenge_evidence_ids(outcome: dict[str, Any], placement: dict[str, Any]) -> list[str]:
    evidence_ids = _string_list(outcome.get("required_evidence"))
    placement_evidence = _text(placement, "evidence")
    if placement_evidence and placement_evidence not in evidence_ids:
        evidence_ids.append(placement_evidence)
    return evidence_ids


def _evidence_contracts(path_step_contracts: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    contracts: dict[str, dict[str, Any]] = {}
    for path_step_contract in path_step_contracts:
        for row in _entries(path_step_contract, "required_evidence"):
            evidence_id = _text(row, "id")
            if evidence_id:
                contracts[evidence_id] = row
    return contracts


def _all_evidence_has_contract(
    evidence_ids: list[str], path_step_contracts: list[dict[str, Any]]
) -> bool:
    contracts = _evidence_contracts(path_step_contracts)
    return bool(evidence_ids) and all(evidence_id in contracts for evidence_id in evidence_ids)


def _first_evidence_source(path_step_contracts: list[dict[str, Any]]) -> str:
    for path_step_contract in path_step_contracts:
        for row in _entries(path_step_contract, "required_evidence"):
            source = _text(row, "source")
            if source:
                return source
    return ""


def _award_id(row: dict[str, Any]) -> str:
    return _text(row, "id") or _text(row, "outcome")


def _bundle_outcomes(row: dict[str, Any]) -> list[str]:
    return _string_list(row.get("outcomes")) or _string_list(row.get("required_outcomes"))


def _int_or_none(value: object) -> int | None:
    return value if isinstance(value, int) and not isinstance(value, bool) and value >= 0 else None


def _runtime_challenges(pack_dir: Path) -> dict[str, dict[str, Any]]:
    for path in _runtime_candidates(pack_dir):
        try:
            parsed = ast.parse(path.read_text())
        except (OSError, SyntaxError):
            continue
        rows = _extract_runtime_rows(parsed)
        if rows:
            return rows
    return {}


def _runtime_candidates(pack_dir: Path) -> list[Path]:
    return sorted((pack_dir / "assets/services").glob("*-runtime/app.py"))


def _extract_runtime_rows(parsed: ast.Module) -> dict[str, dict[str, Any]]:
    constants = _module_string_constants(parsed)
    assignment = _quick_challenges_assignment(parsed)
    if assignment is None:
        return {}

    try:
        value = _literal_with_constants(assignment.value, constants)
    except ValueError:
        return {}
    return _runtime_rows_from_literal(value)


def _quick_challenges_assignment(parsed: ast.Module) -> ast.Assign | None:
    for node in parsed.body:
        if isinstance(node, ast.Assign) and _assigned_to(node, "QUICK_CHALLENGES"):
            return node
    return None


def _runtime_rows_from_literal(value: object) -> dict[str, dict[str, Any]]:
    if not isinstance(value, (list, tuple)):
        return {}

    rows = {}
    for item in value:
        row = _runtime_row(item)
        if row is not None:
            rows[row[0]] = row[1]
    return rows


def _runtime_row(item: object) -> tuple[str, dict[str, str]] | None:
    if not isinstance(item, dict):
        return None
    outcome_id = item.get("id")
    if not isinstance(outcome_id, str) or not outcome_id:
        return None
    return outcome_id, {
        "title": str(item.get("title") or ""),
        "entrypoint": str(item.get("entrypoint") or ""),
    }


def _module_string_constants(parsed: ast.Module) -> dict[str, str]:
    constants = {}
    for node in parsed.body:
        if (
            isinstance(node, ast.Assign)
            and len(node.targets) == 1
            and isinstance(node.value, ast.Constant)
        ):
            target = node.targets[0]
            if isinstance(target, ast.Name) and isinstance(node.value.value, str):
                constants[target.id] = node.value.value
    return constants


def _assigned_to(node: ast.Assign, name: str) -> bool:
    return any(isinstance(target, ast.Name) and target.id == name for target in node.targets)


def _literal_with_constants(node: ast.AST, constants: dict[str, str]) -> object:
    if isinstance(node, ast.Name) and node.id in constants:
        value = constants[node.id]
    elif isinstance(node, ast.Constant):
        value = node.value
    elif isinstance(node, ast.Tuple):
        value = tuple(_literal_with_constants(item, constants) for item in node.elts)
    elif isinstance(node, ast.List):
        value = [_literal_with_constants(item, constants) for item in node.elts]
    elif isinstance(node, ast.Dict):
        value = {
            _literal_with_constants(key, constants): _literal_with_constants(value, constants)
            for key, value in zip(node.keys, node.values, strict=True)
            if key is not None
        }
    else:
        raise ValueError("unsupported literal")
    return value
