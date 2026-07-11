from __future__ import annotations

from django.http import HttpRequest, HttpResponse, JsonResponse
from django.shortcuts import render


def healthz(request: HttpRequest) -> JsonResponse:
    """Liveness probe used by local runs and hosted health checks."""
    return JsonResponse({"status": "ok"})


def landing(request: HttpRequest) -> HttpResponse:
    """Public entry page."""
    return render(request, "workbench/landing.html")
