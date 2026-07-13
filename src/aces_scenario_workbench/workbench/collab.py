"""Collaboration actions: anchored comments, review state, and decisions.

Every artifact anchors to ``(revision, object_type, object_stable_id)`` so a
thread never depends on YAML line numbers or generated HTML, and never carries
across revisions unless explicitly copied. Contribution is role-gated.
"""

from __future__ import annotations

from django.contrib.auth.decorators import login_required
from django.http import Http404, HttpRequest, HttpResponse, HttpResponseForbidden
from django.shortcuts import redirect
from django.views.decorators.http import require_POST

from . import access, authz
from .models import (
    ActivityEvent,
    Comment,
    Decision,
    DecisionType,
    ObjectType,
    ReviewState,
    ReviewStatus,
    Revision,
    Scenario,
)

_DETAIL_URL = {
    ObjectType.TECHNIQUE: "technique-detail",
    ObjectType.TACTIC: "tactic-detail",
    ObjectType.STEP: "step-detail",
    ObjectType.EVIDENCE: "evidence-detail",
}


def object_collab_context(
    request: HttpRequest, revision: Revision, object_type: str, object_stable_id: str
) -> dict[str, object]:
    """Comments, decisions, review state, and role for one object."""
    anchor = {
        "revision": revision,
        "object_type": object_type,
        "object_stable_id": object_stable_id,
    }
    return {
        "comments": Comment.objects.filter(**anchor).select_related("author"),
        "decisions": Decision.objects.filter(**anchor).select_related("author"),
        "review_state": ReviewState.objects.filter(**anchor).first(),
        "can_contribute": authz.can_contribute(request.user, revision.scenario),
        "review_statuses": ReviewStatus.choices,
        "decision_types": DecisionType.choices,
    }


def _valid_object_type(object_type: str) -> None:
    if object_type not in ObjectType.values:
        raise Http404("Unknown object type.")


def _record(scenario: Scenario, actor: object, verb: str, object_type: str, stable_id: str) -> None:
    ActivityEvent.objects.create(
        scenario=scenario,
        actor=actor,
        verb=verb,
        object_type=object_type,
        object_stable_id=stable_id,
    )


def _back(revision: Revision, object_type: str, stable_id: str) -> HttpResponse:
    return redirect(_DETAIL_URL[object_type], revision.scenario.slug, revision.pk, stable_id)


@login_required
@require_POST
def post_comment(
    request: HttpRequest,
    scenario_slug: str,
    revision_pk: int,
    object_type: str,
    object_stable_id: str,
) -> HttpResponse:
    _valid_object_type(object_type)
    revision = access.scoped_revision(request, scenario_slug, revision_pk)
    scenario = revision.scenario
    if not authz.can_contribute(request.user, scenario):
        return HttpResponseForbidden("You do not have permission to comment.")
    body = request.POST.get("body", "").strip()
    if body:
        Comment.objects.create(
            revision=revision,
            object_type=object_type,
            object_stable_id=object_stable_id,
            author=request.user,
            body=body,
        )
        _record(scenario, request.user, "commented", object_type, object_stable_id)
    return _back(revision, object_type, object_stable_id)


@login_required
@require_POST
def set_review_state(
    request: HttpRequest,
    scenario_slug: str,
    revision_pk: int,
    object_type: str,
    object_stable_id: str,
) -> HttpResponse:
    _valid_object_type(object_type)
    revision = access.scoped_revision(request, scenario_slug, revision_pk)
    scenario = revision.scenario
    if not authz.can_contribute(request.user, scenario):
        return HttpResponseForbidden("You do not have permission to set review state.")
    status = request.POST.get("status", "")
    if status in ReviewStatus.values:
        ReviewState.objects.update_or_create(
            revision=revision,
            object_type=object_type,
            object_stable_id=object_stable_id,
            defaults={"status": status, "updated_by": request.user},
        )
        _record(
            scenario, request.user, f"set review state to {status}", object_type, object_stable_id
        )
    return _back(revision, object_type, object_stable_id)


@login_required
@require_POST
def record_decision(
    request: HttpRequest,
    scenario_slug: str,
    revision_pk: int,
    object_type: str,
    object_stable_id: str,
) -> HttpResponse:
    _valid_object_type(object_type)
    revision = access.scoped_revision(request, scenario_slug, revision_pk)
    scenario = revision.scenario
    if not authz.can_contribute(request.user, scenario):
        return HttpResponseForbidden("You do not have permission to record decisions.")
    decision = request.POST.get("decision", "")
    if decision in DecisionType.values:
        Decision.objects.create(
            revision=revision,
            object_type=object_type,
            object_stable_id=object_stable_id,
            author=request.user,
            decision=decision,
            rationale=request.POST.get("rationale", "").strip(),
        )
        _record(
            scenario, request.user, f"recorded decision {decision}", object_type, object_stable_id
        )
    return _back(revision, object_type, object_stable_id)
