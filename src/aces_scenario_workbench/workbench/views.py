from __future__ import annotations

from django.contrib.auth.decorators import login_required
from django.http import HttpRequest, HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, render
from django.views.decorators.http import require_GET

from . import access
from .collab import object_collab_context
from .models import Evidence, ObjectType, Revision, Step, Tactic, Technique


@require_GET
def healthz(request: HttpRequest) -> JsonResponse:
    """Liveness probe used by local runs and hosted health checks."""
    return JsonResponse({"status": "ok"})


@require_GET
def landing(request: HttpRequest) -> HttpResponse:
    """Public entry page."""
    return render(request, "workbench/landing.html")


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


@login_required
@require_GET
def revision_overview(
    request: HttpRequest, project_slug: str, scenario_slug: str, revision_pk: int
) -> HttpResponse:
    revision = access.scoped_revision(request, project_slug, scenario_slug, revision_pk)
    techniques = revision.techniques.select_related("step", "evidence").prefetch_related("tactics")
    context = {
        "revision": revision,
        "scenario": revision.scenario,
        "project": revision.scenario.project,
        "tactics": revision.tactics.all(),
        "steps": revision.steps.all(),
        "techniques": techniques,
        "counts": {
            "tactics": revision.tactics.count(),
            "techniques": revision.techniques.count(),
            "steps": revision.steps.count(),
            "evidence": revision.evidence.count(),
        },
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
