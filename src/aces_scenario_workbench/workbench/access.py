"""Shared project-scoped object resolution for views.

A user only reaches a project (and its scenarios/revisions) they are a member
of; anything else is a 404 so existence is not leaked.
"""

from __future__ import annotations

from django.http import Http404, HttpRequest
from django.shortcuts import get_object_or_404

from . import authz
from .models import Project, Revision, Scenario


def member_project(request: HttpRequest, slug: str) -> Project:
    project = get_object_or_404(Project, slug=slug)
    if not authz.is_member(request.user, project):
        raise Http404("No such project.")
    return project


def scoped_revision(
    request: HttpRequest, project_slug: str, scenario_slug: str, revision_pk: int
) -> Revision:
    project = member_project(request, project_slug)
    scenario = get_object_or_404(Scenario, project=project, slug=scenario_slug)
    return get_object_or_404(Revision, pk=revision_pk, scenario=scenario)
