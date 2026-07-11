from __future__ import annotations

from django.contrib.auth.decorators import login_required
from django.http import Http404, HttpRequest, HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, render
from django.views.decorators.http import require_GET

from . import authz
from .models import Evidence, Project, Revision, Scenario, Step, Tactic, Technique


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


def _member_project(request: HttpRequest, slug: str) -> Project:
    project = get_object_or_404(Project, slug=slug)
    if not authz.is_member(request.user, project):
        raise Http404("No such project.")
    return project


def _scoped_revision(
    request: HttpRequest, project_slug: str, scenario_slug: str, revision_pk: int
) -> Revision:
    project = _member_project(request, project_slug)
    scenario = get_object_or_404(Scenario, project=project, slug=scenario_slug)
    return get_object_or_404(Revision, pk=revision_pk, scenario=scenario)


@login_required
@require_GET
def project_detail(request: HttpRequest, slug: str) -> HttpResponse:
    project = _member_project(request, slug)
    scenarios = project.scenarios.prefetch_related("revisions")
    return render(
        request, "workbench/project_detail.html", {"project": project, "scenarios": scenarios}
    )


@login_required
@require_GET
def revision_overview(
    request: HttpRequest, project_slug: str, scenario_slug: str, revision_pk: int
) -> HttpResponse:
    revision = _scoped_revision(request, project_slug, scenario_slug, revision_pk)
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


def _object_context(revision: Revision, obj: object, label: str) -> dict[str, object]:
    return {
        "revision": revision,
        "scenario": revision.scenario,
        "project": revision.scenario.project,
        "object_label": label,
        "object": obj,
    }


@login_required
@require_GET
def technique_detail(
    request: HttpRequest,
    project_slug: str,
    scenario_slug: str,
    revision_pk: int,
    technique_id: str,
) -> HttpResponse:
    revision = _scoped_revision(request, project_slug, scenario_slug, revision_pk)
    technique = get_object_or_404(Technique, revision=revision, technique_id=technique_id)
    return render(
        request,
        "workbench/technique_detail.html",
        _object_context(revision, technique, "Technique"),
    )


@login_required
@require_GET
def tactic_detail(
    request: HttpRequest, project_slug: str, scenario_slug: str, revision_pk: int, tactic_id: str
) -> HttpResponse:
    revision = _scoped_revision(request, project_slug, scenario_slug, revision_pk)
    tactic = get_object_or_404(Tactic, revision=revision, tactic_id=tactic_id)
    return render(
        request, "workbench/tactic_detail.html", _object_context(revision, tactic, "Tactic")
    )


@login_required
@require_GET
def step_detail(
    request: HttpRequest, project_slug: str, scenario_slug: str, revision_pk: int, path_step: str
) -> HttpResponse:
    revision = _scoped_revision(request, project_slug, scenario_slug, revision_pk)
    step = get_object_or_404(Step, revision=revision, path_step=path_step)
    return render(request, "workbench/step_detail.html", _object_context(revision, step, "Module"))


@login_required
@require_GET
def evidence_detail(
    request: HttpRequest, project_slug: str, scenario_slug: str, revision_pk: int, evidence_id: str
) -> HttpResponse:
    revision = _scoped_revision(request, project_slug, scenario_slug, revision_pk)
    evidence = get_object_or_404(Evidence, revision=revision, evidence_id=evidence_id)
    return render(
        request, "workbench/evidence_detail.html", _object_context(revision, evidence, "Evidence")
    )
