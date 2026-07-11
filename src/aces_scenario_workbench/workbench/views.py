from __future__ import annotations

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
