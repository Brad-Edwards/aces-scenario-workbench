from __future__ import annotations

from urllib.parse import urlencode

from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Count, Q, QuerySet
from django.http import HttpRequest, HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_GET

from . import access
from .collab import object_collab_context
from .models import Evidence, ObjectType, Revision, Step, Tactic, Technique

TECHNIQUES_PER_PAGE = 25
_TECHNIQUE_FILTERS = ("q", "module", "tactic", "level")


@require_GET
def healthz(request: HttpRequest) -> JsonResponse:
    """Liveness probe used by local runs and hosted health checks."""
    return JsonResponse({"status": "ok"})


@require_GET
def landing(request: HttpRequest) -> HttpResponse:
    """Route users to the correct application entry point."""
    if request.user.is_authenticated:
        return redirect("spa-app")
    return redirect("login")


@login_required
@require_GET
def spa_app(request: HttpRequest, path: str = "") -> HttpResponse:
    """Authenticated SPA shell."""
    return render(request, "workbench/spa.html")


@require_GET
def privacy(request: HttpRequest) -> HttpResponse:
    """Privacy notice."""
    return render(request, "workbench/privacy.html")


def ratelimited(request: HttpRequest, _: Exception | None = None) -> HttpResponse:
    """Response for a request that exceeded a rate limit.

    Registered as ``RATELIMIT_VIEW``; django-ratelimit passes the raised
    exception as the second positional argument, which this view does not need.
    """
    return render(request, "429.html", status=429)


@login_required
@require_GET
def dashboard(request: HttpRequest) -> HttpResponse:
    """List the projects the signed-in user is a member of."""
    return render(request, "workbench/dashboard.html", {"projects": request.user.projects.all()})


@login_required
@require_GET
def project_detail(request: HttpRequest, slug: str) -> HttpResponse:
    project = access.member_project(request, slug)
    scenarios = project.scenarios.prefetch_related("revisions")
    return render(
        request, "workbench/project_detail.html", {"project": project, "scenarios": scenarios}
    )


@login_required
@require_GET
def project_activity(request: HttpRequest, slug: str) -> HttpResponse:
    project = access.member_project(request, slug)
    events = project.activity.select_related("actor")[:100]
    return render(request, "workbench/activity.html", {"project": project, "events": events})


def _filter_techniques(revision: Revision, filters: dict[str, str]) -> QuerySet[Technique]:
    """Techniques for a revision, narrowed by the search box and dropdown filters."""
    techniques = (
        revision.techniques.select_related("step", "evidence")
        .prefetch_related("tactics")
        .order_by("technique_id")
    )
    if filters["q"]:
        techniques = techniques.filter(
            Q(technique_id__icontains=filters["q"])
            | Q(name__icontains=filters["q"])
            | Q(planned_action__icontains=filters["q"])
            | Q(evidence__evidence_id__icontains=filters["q"])
        )
    if filters["module"]:
        techniques = techniques.filter(step__path_step=filters["module"])
    if filters["tactic"]:
        techniques = techniques.filter(tactics__tactic_id=filters["tactic"])
    if filters["level"]:
        techniques = techniques.filter(step__tier=filters["level"])
    return techniques.distinct()


def _dashboard_steps(revision: Revision) -> list[Step]:
    steps = list(
        revision.steps.prefetch_related(
            "techniques",
            "techniques__tactics",
            "techniques__evidence",
        )
    )
    for step in steps:
        tactic_by_id = {}
        evidence_by_id = {}
        techniques = list(step.techniques.all())
        for technique in techniques:
            for tactic in technique.tactics.all():
                tactic_by_id[tactic.tactic_id] = tactic
            if technique.evidence:
                evidence_by_id[technique.evidence.evidence_id] = technique.evidence
        step.technique_count = len(techniques)
        step.tactic_list = sorted(tactic_by_id.values(), key=lambda tactic: tactic.tactic_id)
        step.evidence_list = sorted(
            evidence_by_id.values(), key=lambda evidence: evidence.evidence_id
        )
    return steps


def _dashboard_tactics(revision: Revision) -> list[Tactic]:
    return list(
        revision.tactics.annotate(technique_count=Count("techniques", distinct=True)).order_by(
            "tactic_id"
        )
    )


def _integrity_fields(revision: Revision) -> list[tuple[str, str]]:
    metadata = revision.metadata if isinstance(revision.metadata, dict) else {}
    experience = metadata.get("experience_contract")
    if not isinstance(experience, dict):
        experience = {}
    fields = [
        ("Catalog digest", experience.get("catalog_digest", "")),
        ("Relationship digest", experience.get("relationship_digest", "")),
        ("Assignment digest", experience.get("assignment_digest", "")),
        ("Revision content digest", revision.content_digest),
    ]
    return [(label, str(value)) for label, value in fields if value]


@login_required
@require_GET
def revision_overview(
    request: HttpRequest, project_slug: str, scenario_slug: str, revision_pk: int
) -> HttpResponse:
    revision = access.scoped_revision(request, project_slug, scenario_slug, revision_pk)
    filters = {name: request.GET.get(name, "").strip() for name in _TECHNIQUE_FILTERS}
    paginator = Paginator(_filter_techniques(revision, filters), TECHNIQUES_PER_PAGE)
    page = paginator.get_page(request.GET.get("page"))
    active_filters = {name: value for name, value in filters.items() if value}
    steps = _dashboard_steps(revision)
    tactics = _dashboard_tactics(revision)
    max_tactic_count = max((tactic.technique_count for tactic in tactics), default=0) or 1
    shortest_minutes = min(
        (step.estimated_minutes for step in steps if step.estimated_minutes is not None),
        default=None,
    )
    total_minutes = sum(step.estimated_minutes or 0 for step in steps)
    context = {
        "revision": revision,
        "scenario": revision.scenario,
        "project": revision.scenario.project,
        "tactics": tactics,
        "steps": steps,
        "techniques": page,
        "page": page,
        "filters": filters,
        "filter_query": urlencode(active_filters),
        "has_filters": bool(active_filters),
        "match_count": paginator.count,
        "module_options": revision.steps.all(),
        "tactic_options": revision.tactics.all(),
        "level_options": sorted({t for t in revision.steps.values_list("tier", flat=True) if t}),
        "counts": {
            "tactics": revision.tactics.count(),
            "techniques": revision.techniques.count(),
            "steps": revision.steps.count(),
            "evidence": revision.evidence.count(),
            "quick_starts": sum(1 for step in steps if step.tier == "quick"),
        },
        "max_tactic_count": max_tactic_count,
        "shortest_minutes": shortest_minutes,
        "total_minutes": total_minutes,
        "integrity_fields": _integrity_fields(revision),
    }
    return render(request, "workbench/revision_overview.html", context)


def _object_context(
    request: HttpRequest,
    revision: Revision,
    obj: object,
    label: str,
    object_type: str,
    stable_id: str,
) -> dict[str, object]:
    context = {
        "revision": revision,
        "scenario": revision.scenario,
        "project": revision.scenario.project,
        "object_label": label,
        "object": obj,
        "object_type": object_type,
        "object_stable_id": stable_id,
    }
    context.update(object_collab_context(request, revision, object_type, stable_id))
    return context


@login_required
@require_GET
def technique_detail(
    request: HttpRequest,
    project_slug: str,
    scenario_slug: str,
    revision_pk: int,
    technique_id: str,
) -> HttpResponse:
    revision = access.scoped_revision(request, project_slug, scenario_slug, revision_pk)
    technique = get_object_or_404(Technique, revision=revision, technique_id=technique_id)
    context = _object_context(
        request, revision, technique, "Technique", ObjectType.TECHNIQUE, technique.technique_id
    )
    return render(request, "workbench/technique_detail.html", context)


@login_required
@require_GET
def tactic_detail(
    request: HttpRequest, project_slug: str, scenario_slug: str, revision_pk: int, tactic_id: str
) -> HttpResponse:
    revision = access.scoped_revision(request, project_slug, scenario_slug, revision_pk)
    tactic = get_object_or_404(Tactic, revision=revision, tactic_id=tactic_id)
    context = _object_context(
        request, revision, tactic, "Tactic", ObjectType.TACTIC, tactic.tactic_id
    )
    return render(request, "workbench/tactic_detail.html", context)


@login_required
@require_GET
def step_detail(
    request: HttpRequest, project_slug: str, scenario_slug: str, revision_pk: int, path_step: str
) -> HttpResponse:
    revision = access.scoped_revision(request, project_slug, scenario_slug, revision_pk)
    step = get_object_or_404(Step, revision=revision, path_step=path_step)
    context = _object_context(request, revision, step, "Module", ObjectType.STEP, step.path_step)
    return render(request, "workbench/step_detail.html", context)


@login_required
@require_GET
def evidence_detail(
    request: HttpRequest, project_slug: str, scenario_slug: str, revision_pk: int, evidence_id: str
) -> HttpResponse:
    revision = access.scoped_revision(request, project_slug, scenario_slug, revision_pk)
    evidence = get_object_or_404(Evidence, revision=revision, evidence_id=evidence_id)
    context = _object_context(
        request, revision, evidence, "Evidence", ObjectType.EVIDENCE, evidence.evidence_id
    )
    return render(request, "workbench/evidence_detail.html", context)
