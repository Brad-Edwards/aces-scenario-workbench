"""Ingest an ACES scenario pack's ATLAS technique projection.

A projection is parsed into an immutable :class:`Revision` and its content
objects (tactics, steps, evidence, techniques). Ingestion is idempotent: a
revision is identified by a content digest, so re-importing identical content is
a no-op while changed content creates a new revision. The workbench never writes
back into a pack.
"""

from __future__ import annotations

import ast
import hashlib
import json
from pathlib import Path
from typing import Any

import yaml
from aces_sdl import SDLError, SDLMigrationPolicy, parse_sdl_file
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


class ProjectionError(ValueError):
    """Raised when a projection file cannot be read or parsed."""


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
            except SDLError as exc:
                fallback = parse_projection(found.read_bytes())
                fallback["parser_error"] = str(exc)
                fallback["parser"] = "yaml-fallback"
                return fallback
            parsed = scenario.model_dump(mode="json")
            parsed["parser"] = "aces-sdl"
            parsed["advisories"] = [str(advisory) for advisory in scenario.advisories]
            return parsed
    return {}


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


def _content_digest(projection: dict[str, Any], contracts: dict[str, Any]) -> str:
    if not contracts:
        return _digest(projection)
    return _digest({"projection": projection, "contracts": contracts})


@transaction.atomic
def import_projection(scenario: Scenario, data: dict[str, Any]) -> tuple[Revision, bool]:
    """Import a projection into ``scenario``; returns ``(revision, created)``."""
    return _import_revision(scenario, data, {}, _content_digest(data, {}))


def import_pack(scenario: Scenario, path: Path) -> tuple[Revision, bool]:
    """Import a full pack directory when available, including challenge contracts."""
    data, _ = load_projection(path)
    contracts = load_pack_contracts(path)
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
    entities = _mapping(sdl, "entities")
    agents = _mapping(sdl, "agents")
    behavior_specs = _mapping_any(sdl, "behavior_specifications", "behavior-specifications")
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
        "nodes": [
            _sdl_node_row(key, value, assets_by_id, services_by_id)
            for key, value in sorted(nodes.items())
        ],
        "entities": [_sdl_entity_row(key, value) for key, value in sorted(entities.items())],
        "agents": [_sdl_agent_row(key, value) for key, value in sorted(agents.items())],
        "behavior_specs": [
            _sdl_behavior_spec_row(key, value) for key, value in sorted(behavior_specs.items())
        ],
        "zones": [_zone_row(row) for row in _entries(topology, "zones")],
        "networks": [_network_row(row) for row in _entries(topology, "networks")],
        "links": _sdl_topology_links(entities, agents, nodes, behavior_specs),
        "coverage": {
            "sdl_node_count": len(nodes),
            "sdl_service_count": sum(
                len(_sequence(value, "services"))
                for value in nodes.values()
                if isinstance(value, dict)
            ),
            "sdl_agent_count": len(agents),
            "sdl_entity_count": len(entities),
            "sdl_behavior_spec_count": len(behavior_specs),
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


def _sdl_behavior_spec_row(spec_id: str, row: object) -> dict[str, Any]:
    row = row if isinstance(row, dict) else {}
    return {
        "id": spec_id,
        "semantic_version": _text_any(row, "semantic_version", "semantic-version"),
        "lifecycle_state": _text_any(row, "lifecycle_state", "lifecycle-state"),
        "participant_refs": _string_list(row.get("participant_refs"))
        or _string_list(row.get("participant-refs")),
        "ai_offensive_behavior_refs": _string_list(row.get("ai_offensive_behavior_refs"))
        or _string_list(row.get("ai-offensive-behavior-refs")),
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


def _sdl_topology_links(
    entities: dict[str, Any],
    agents: dict[str, Any],
    nodes: dict[str, Any],
    behavior_specs: dict[str, Any],
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

    for spec_id, spec in sorted(behavior_specs.items()):
        if not isinstance(spec, dict):
            continue
        participants = _string_list(spec.get("participant_refs")) or _string_list(
            spec.get("participant-refs")
        )
        for participant in participants:
            if participant in agents:
                links.append({"source": participant, "target": spec_id, "type": "agent-behavior"})
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

    challenges = {
        _text(row, "flag_id"): row
        for row in _entries(contracts.get("challenges", {}), "challenges")
    }
    placements = _entries(contracts.get("placement", {}), "flags")
    outcomes = {
        _text(row, "id"): row for row in _entries(contracts.get("objectives", {}), "outcomes")
    }
    path_steps = {
        _text(row, "id"): row for row in _entries(contracts.get("objectives", {}), "path_steps")
    }
    telemetry = {
        _text(row, "evidence"): row for row in _entries(contracts.get("telemetry", {}), "events")
    }
    scoring = contracts.get("scoring", {})
    awards = {
        _award_id(row): row
        for row in _entries(scoring if isinstance(scoring, dict) else {}, "awards")
        if _award_id(row)
    }
    alternate_awards = _entries(scoring if isinstance(scoring, dict) else {}, "alternate_awards")
    bundles = _entries(scoring if isinstance(scoring, dict) else {}, "bundles")
    runtime = contracts.get("runtime_challenges", {})
    runtime = runtime if isinstance(runtime, dict) else {}

    steps = {step.path_step: step for step in revision.steps.all()}
    techniques_by_step: dict[str, list[Technique]] = {}
    for technique in revision.techniques.select_related("step").all():
        if technique.step_id:
            techniques_by_step.setdefault(technique.step.path_step, []).append(technique)

    for placement in placements:
        outcome_id = _text(placement, "outcome")
        runtime_row = runtime.get(outcome_id)
        challenge_row = challenges.get(_text(placement, "flag_id"))
        outcome = outcomes.get(outcome_id)
        if not isinstance(runtime_row, dict) or not challenge_row or not outcome:
            if not challenge_row or not outcome:
                continue
            runtime_row = {}

        if not isinstance(runtime_row, dict):
            continue

        canonical_steps = _string_list(outcome.get("canonical_steps"))
        step = steps.get(canonical_steps[0]) if canonical_steps else None
        path_step_contracts = [
            path_steps.get(path_step_id, {})
            for path_step_id in canonical_steps
            if isinstance(path_steps.get(path_step_id, {}), dict)
        ]
        source_path = _first_evidence_source(path_step_contracts)
        award = awards.get(outcome_id, {})
        evidence_ids = _challenge_evidence_ids(outcome, placement)
        implemented = bool(runtime_row)
        challenge = Challenge.objects.create(
            revision=revision,
            step=step,
            flag_id=_text(placement, "flag_id"),
            outcome_id=outcome_id,
            title=_text(challenge_row, "title"),
            question=_text(challenge_row, "question"),
            category=_text(challenge_row, "category"),
            difficulty=_text(challenge_row, "difficulty"),
            points=_int_or_none(challenge_row.get("points"))
            or _int_or_none(award.get("points") if isinstance(award, dict) else None),
            hints=_string_list(challenge_row.get("hints")),
            implemented=implemented,
            runtime_entrypoint=_text(runtime_row, "entrypoint"),
            source_path=source_path,
            metadata={
                "delivery": _mapping(placement, "delivery"),
                "profiles": _string_list(placement.get("profiles")),
                "canonical_steps": canonical_steps,
                "objective": {
                    "title": _text(outcome, "title"),
                    "success_state": _text(outcome, "success_state"),
                },
                "scoring": _award_row(award) if isinstance(award, dict) else {},
                "alternate_awards": [
                    _award_row(row) for row in alternate_awards if _award_id(row) == outcome_id
                ],
                "bundles": [
                    _bundle_row(row) for row in bundles if outcome_id in _bundle_outcomes(row)
                ],
                "readiness": {
                    "challenge_contract": True,
                    "placement": True,
                    "objective": True,
                    "scoring": isinstance(award, dict) and bool(award),
                    "runtime": implemented,
                    "telemetry": all(evidence_id in telemetry for evidence_id in evidence_ids),
                    "evidence_contract": _all_evidence_has_contract(
                        evidence_ids, path_step_contracts
                    ),
                },
            },
        )
        linked_techniques = []
        for path_step_id in canonical_steps:
            linked_techniques.extend(techniques_by_step.get(path_step_id, []))
        if linked_techniques:
            challenge.techniques.set(linked_techniques)
        _load_challenge_evidence(
            challenge,
            revision,
            outcome,
            placement,
            path_step_contracts,
            telemetry,
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
    for node in parsed.body:
        if isinstance(node, ast.Assign) and _assigned_to(node, "QUICK_CHALLENGES"):
            try:
                value = _literal_with_constants(node.value, constants)
            except ValueError:
                return {}
            if isinstance(value, (list, tuple)):
                rows = {}
                for item in value:
                    if isinstance(item, dict):
                        outcome_id = item.get("id")
                        if isinstance(outcome_id, str) and outcome_id:
                            rows[outcome_id] = {
                                "title": str(item.get("title") or ""),
                                "entrypoint": str(item.get("entrypoint") or ""),
                            }
                return rows
    return {}


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
        return constants[node.id]
    if isinstance(node, ast.Constant):
        return node.value
    if isinstance(node, ast.Tuple):
        return tuple(_literal_with_constants(item, constants) for item in node.elts)
    if isinstance(node, ast.List):
        return [_literal_with_constants(item, constants) for item in node.elts]
    if isinstance(node, ast.Dict):
        return {
            _literal_with_constants(key, constants): _literal_with_constants(value, constants)
            for key, value in zip(node.keys, node.values, strict=True)
            if key is not None
        }
    raise ValueError("unsupported literal")
