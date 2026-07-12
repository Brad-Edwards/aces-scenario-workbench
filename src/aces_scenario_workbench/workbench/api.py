from __future__ import annotations

from typing import Any

from django.contrib.auth.decorators import login_required
from django.http import HttpRequest, HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404
from django.views.decorators.http import require_POST

from . import authz
from .ingest import ProjectionError, import_projection, parse_projection
from .models import Project, Role

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
    """Ingest a projection uploaded for a project (author/administrator only)."""
    project = get_object_or_404(Project, slug=slug)
    if authz.user_role(request.user, project) not in _ALLOWED_ROLES:
        return JsonResponse({"detail": "You do not have permission to upload."}, status=403)
    try:
        data = _read_projection(request)
    except UploadError as exc:
        return JsonResponse({"detail": exc.detail}, status=exc.status)
    revision, created = import_projection(project, data)
    return JsonResponse(
        {"revision": revision.pk, "created": created, "mapping_id": revision.mapping_id},
        status=201 if created else 200,
    )
