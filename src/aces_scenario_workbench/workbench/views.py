from __future__ import annotations

from django.contrib.auth.decorators import login_required
from django.http import HttpRequest, HttpResponse, JsonResponse
from django.shortcuts import render
from django.views.decorators.http import require_GET


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
    projects = request.user.projects.all()
    return render(request, "workbench/dashboard.html", {"projects": projects})
