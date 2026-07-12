from __future__ import annotations

from typing import Any

from django.contrib.auth.decorators import login_required
from django.db.models import Count
from django.http import HttpRequest, HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404
from django.views.decorators.http import require_GET, require_POST

from . import authz
from .ingest import ProjectionError, import_projection, parse_projection
from .models import Challenge, Evidence, ObjectType, Revision, Role, Scenario, Step, Technique

_ALLOWED_ROLES = {Role.AUTHOR, Role.ADMINISTRATOR}


class UploadError(Exception):
    def __init__(self, detail: str, status: int) -> None:
        super().__init__(detail)
        self.detail = detail
        self.status = status


def _read_projection(request: HttpRequest) -> dict[str, Any]:
    upload = request.FILES.get("file")
    if upload is None:
        raise UploadError("No file provided.", 400)
    try:
        return parse_projection(upload.read())
    except ProjectionError as exc:
        raise UploadError(str(exc), 400) from exc


@login_required
@require_POST
def upload_revision(request: HttpRequest, slug: str) -> HttpResponse:
    """Ingest a projection uploaded for a scenario (author/administrator only)."""
    scenario = get_object_or_404(Scenario, slug=slug)
    if authz.user_role(request.user, scenario) not in _ALLOWED_ROLES:
        return JsonResponse({"detail": "You do not have permission to upload."}, status=403)
    try:
        data = _read_projection(request)
    except UploadError as exc:
        return JsonResponse({"detail": exc.detail}, status=exc.status)
    revision, created = import_projection(scenario, data)
    return JsonResponse(
        {"revision": revision.pk, "created": created, "mapping_id": revision.mapping_id},
        status=201 if created else 200,
    )


@login_required
@require_GET
def current_user(request: HttpRequest) -> JsonResponse:
    return JsonResponse(
        {
            "email": request.user.email,
            "displayName": request.user.get_short_name(),
            "isStaff": request.user.is_staff,
        }
    )


@login_required
@require_GET
def scenario_list(request: HttpRequest) -> JsonResponse:
    scenarios = (
        Scenario.objects.filter(memberships__user=request.user)
        .annotate(revision_count=Count("revisions", distinct=True))
        .prefetch_related("memberships")
    )
    return JsonResponse(
        {"scenarios": [_scenario_row(scenario, request.user) for scenario in scenarios]}
    )


@login_required
@require_GET
def scenario_detail(request: HttpRequest, slug: str) -> JsonResponse:
    scenario = get_object_or_404(
        Scenario.objects.annotate(
            revision_count=Count("revisions", distinct=True)
        ).prefetch_related(
            "memberships",
            "revisions",
            "revisions__steps",
            "revisions__techniques",
            "revisions__evidence",
            "revisions__challenges",
            "revisions__comments",
            "revisions__decisions",
        ),
        slug=slug,
        memberships__user=request.user,
    )
    return JsonResponse(
        {
            "scenario": _scenario_row(scenario, request.user),
            "revisions": [_revision_row(revision) for revision in scenario.revisions.all()],
        }
    )


@login_required
@require_GET
def revision_workspace(request: HttpRequest, revision_pk: int) -> JsonResponse:
    revision = get_object_or_404(
        Revision.objects.select_related("scenario").prefetch_related(
            "steps",
            "steps__techniques",
            "steps__techniques__evidence",
            "techniques",
            "techniques__tactics",
            "techniques__evidence",
            "evidence",
            "evidence__techniques",
            "challenges",
            "challenges__step",
            "challenges__techniques",
            "challenges__evidence_requirements",
            "challenges__evidence_requirements__evidence",
            "comments",
            "comments__author",
            "decisions",
            "decisions__author",
        ),
        pk=revision_pk,
        scenario__memberships__user=request.user,
    )
    comment_counts = _anchor_counts(revision.comments.all())
    decision_counts = _anchor_counts(revision.decisions.all())
    return JsonResponse(
        {
            "id": revision.pk,
            "label": revision.label,
            "scenario": {
                "slug": revision.scenario.slug,
                "name": revision.scenario.name,
                "description": revision.scenario.description,
            },
            "framework": _framework_label(revision),
            "createdAt": revision.created_at.isoformat(),
            "modules": [
                _module_row(step, comment_counts, decision_counts) for step in revision.steps.all()
            ],
            "techniques": [
                _technique_row(technique, comment_counts, decision_counts)
                for technique in revision.techniques.all()
            ],
            "evidence": [
                _evidence_row(evidence, comment_counts, decision_counts)
                for evidence in revision.evidence.all()
            ],
            "challenges": [
                _challenge_row(challenge, comment_counts, decision_counts)
                for challenge in revision.challenges.all()
            ],
            "comments": [
                {
                    "id": comment.pk,
                    "objectType": comment.object_type,
                    "objectId": comment.object_stable_id,
                    "body": comment.body,
                    "author": comment.author.get_short_name(),
                    "createdAt": comment.created_at.isoformat(),
                    "updatedAt": comment.updated_at.isoformat(),
                    "edited": False,
                }
                for comment in revision.comments.all()
            ],
            "decisions": [
                {
                    "id": decision.pk,
                    "objectType": decision.object_type,
                    "objectId": decision.object_stable_id,
                    "decision": decision.get_decision_display(),
                    "rationale": decision.rationale,
                    "author": decision.author.get_short_name(),
                    "createdAt": decision.created_at.isoformat(),
                }
                for decision in revision.decisions.all()
            ],
        }
    )


def _scenario_row(scenario: Scenario, user: object) -> dict[str, object]:
    membership = next(
        (membership for membership in scenario.memberships.all() if membership.user_id == user.pk),
        None,
    )
    return {
        "slug": scenario.slug,
        "name": scenario.name,
        "description": scenario.description,
        "role": membership.get_role_display() if membership else "",
        "revisionCount": getattr(scenario, "revision_count", 0),
        "updatedAt": scenario.updated_at.isoformat(),
    }


def _revision_row(revision: Revision) -> dict[str, object]:
    return {
        "id": revision.pk,
        "label": revision.label,
        "packVersion": revision.pack_version,
        "framework": _framework_label(revision),
        "createdAt": revision.created_at.isoformat(),
        "updatedAt": revision.updated_at.isoformat(),
        "moduleCount": revision.steps.count(),
        "techniqueCount": revision.techniques.count(),
        "evidenceCount": revision.evidence.count(),
        "challengeCount": revision.challenges.count(),
        "commentCount": revision.comments.count(),
        "decisionCount": revision.decisions.count(),
    }


def _framework_label(revision: Revision) -> str:
    return " ".join(part for part in (revision.framework_name, revision.framework_release) if part)


def _anchor_counts(items: object) -> dict[tuple[str, str], int]:
    counts: dict[tuple[str, str], int] = {}
    for item in items:
        key = (item.object_type, item.object_stable_id)
        counts[key] = counts.get(key, 0) + 1
    return counts


def _module_row(
    step: Step,
    comment_counts: dict[tuple[str, str], int],
    decision_counts: dict[tuple[str, str], int],
) -> dict[str, object]:
    key = (ObjectType.STEP, step.path_step)
    evidence_ids = {
        technique.evidence_id for technique in step.techniques.all() if technique.evidence_id
    }
    return {
        "id": step.path_step,
        "name": step.surface or f"Module {step.path_step}",
        "behaviorSpecification": step.behavior_specification,
        "tier": step.tier,
        "objective": step.objective,
        "minutes": step.estimated_minutes,
        "flagOutcome": step.flag_outcome,
        "justification": step.justification,
        "techniqueCount": step.techniques.count(),
        "evidenceCount": len(evidence_ids),
        "commentCount": comment_counts.get(key, 0),
        "decisionCount": decision_counts.get(key, 0),
    }


def _technique_row(
    technique: Technique,
    comment_counts: dict[tuple[str, str], int],
    decision_counts: dict[tuple[str, str], int],
) -> dict[str, object]:
    key = (ObjectType.TECHNIQUE, technique.technique_id)
    return {
        "id": technique.technique_id,
        "name": technique.name,
        "module": technique.step.path_step if technique.step else "",
        "tactics": [tactic.name for tactic in technique.tactics.all()],
        "evidence": technique.evidence.evidence_id if technique.evidence else "",
        "surface": technique.surface,
        "relationship": technique.relationship,
        "coverageStatus": technique.coverage_status,
        "plannedAction": technique.planned_action,
        "rationale": technique.rationale,
        "commentCount": comment_counts.get(key, 0),
        "decisionCount": decision_counts.get(key, 0),
    }


def _evidence_row(
    evidence: Evidence,
    comment_counts: dict[tuple[str, str], int],
    decision_counts: dict[tuple[str, str], int],
) -> dict[str, object]:
    key = (ObjectType.EVIDENCE, evidence.evidence_id)
    return {
        "id": evidence.evidence_id,
        "description": evidence.description,
        "techniqueCount": evidence.techniques.count(),
        "commentCount": comment_counts.get(key, 0),
        "decisionCount": decision_counts.get(key, 0),
    }


def _challenge_row(
    challenge: Challenge,
    comment_counts: dict[tuple[str, str], int],
    decision_counts: dict[tuple[str, str], int],
) -> dict[str, object]:
    key = (ObjectType.CHALLENGE, challenge.flag_id)
    return {
        "id": challenge.flag_id,
        "flagId": challenge.flag_id,
        "outcome": challenge.outcome_id,
        "title": challenge.title,
        "question": challenge.question,
        "category": challenge.category,
        "difficulty": challenge.difficulty,
        "points": challenge.points,
        "hints": challenge.hints,
        "implemented": challenge.implemented,
        "runtimeEntrypoint": challenge.runtime_entrypoint,
        "sourcePath": challenge.source_path,
        "module": challenge.step.path_step if challenge.step else "",
        "moduleName": challenge.step.surface if challenge.step else "",
        "techniqueIds": [technique.technique_id for technique in challenge.techniques.all()],
        "evidenceRequirements": [
            {
                "evidenceId": requirement.evidence_key,
                "predicate": requirement.predicate,
                "sourcePath": requirement.source_path,
                "eventId": requirement.event_id,
                "eventKind": requirement.event_kind,
                "sourceService": requirement.source_service,
                "sourceAsset": requirement.source_asset,
                "freshnessSeconds": requirement.freshness_seconds,
                "resetOwner": requirement.reset_owner,
            }
            for requirement in challenge.evidence_requirements.all()
        ],
        "commentCount": comment_counts.get(key, 0),
        "decisionCount": decision_counts.get(key, 0),
    }
