"""Shared scenario-scoped object resolution for views.

A user only reaches a scenario and its revisions when they are a member of that
scenario; anything else is a 404 so existence is not leaked.
"""

from __future__ import annotations

from django.http import Http404, HttpRequest
from django.shortcuts import get_object_or_404

from . import authz
from .models import Revision, Scenario


def member_scenario(request: HttpRequest, slug: str) -> Scenario:
    scenario = get_object_or_404(Scenario, slug=slug)
    if not authz.is_member(request.user, scenario):
        raise Http404("No such scenario.")
    return scenario


def scoped_revision(request: HttpRequest, scenario_slug: str, revision_pk: int) -> Revision:
    scenario = member_scenario(request, scenario_slug)
    return get_object_or_404(Revision, pk=revision_pk, scenario=scenario)
