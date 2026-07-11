from __future__ import annotations

import pytest
from django.conf import settings
from django.contrib.auth import get_user_model
from django.urls import reverse

from aces_scenario_workbench.workbench.ingest import import_projection, load_projection
from aces_scenario_workbench.workbench.models import Membership, Project, Role

User = get_user_model()
SAMPLE = settings.BASE_DIR / "fixtures" / "sample-scenario" / "atlas-technique-projection.yaml"


@pytest.fixture
def workspace(db):
    project = Project.objects.create(slug="demo", name="Demo Project")
    member = User.objects.create_user(email="member@example.com", password="review-pass-1")
    Membership.objects.create(project=project, user=member, role=Role.REVIEWER)
    data, _ = load_projection(SAMPLE)
    revision, _ = import_projection(project, data)
    return project, revision, member


def _args(project, revision):
    return [project.slug, revision.scenario.slug, revision.pk]


def test_project_detail_lists_revisions(client, workspace):
    project, revision, member = workspace
    client.force_login(member)
    response = client.get(reverse("project-detail", args=[project.slug]))
    assert response.status_code == 200
    assert b"sample-scenario" in response.content
    assert revision.label.encode() in response.content


def test_revision_overview_renders(client, workspace):
    project, revision, member = workspace
    client.force_login(member)
    response = client.get(reverse("revision-overview", args=_args(project, revision)))
    assert response.status_code == 200
    assert b"Techniques" in response.content
    assert b"AML.T0000" in response.content
    assert b"Modules" in response.content


def test_object_detail_pages(client, workspace):
    project, revision, member = workspace
    client.force_login(member)
    checks = {
        reverse(
            "technique-detail", args=[*_args(project, revision), "AML.T0000"]
        ): b"Planned action",
        reverse(
            "tactic-detail", args=[*_args(project, revision), "AML.TA0002"]
        ): b"Techniques in this tactic",
        reverse("step-detail", args=[*_args(project, revision), "1"]): b"Techniques in this module",
        reverse(
            "evidence-detail", args=[*_args(project, revision), "ev-recon"]
        ): b"Techniques requiring this evidence",
    }
    for url, needle in checks.items():
        response = client.get(url)
        assert response.status_code == 200, url
        assert needle in response.content, url


def test_non_member_gets_404(client, workspace):
    project, revision, _ = workspace
    outsider = User.objects.create_user(email="outsider@example.com", password="review-pass-1")
    client.force_login(outsider)
    assert client.get(reverse("project-detail", args=[project.slug])).status_code == 404
    assert (
        client.get(reverse("revision-overview", args=_args(project, revision))).status_code == 404
    )
    url = reverse("technique-detail", args=[*_args(project, revision), "AML.T0000"])
    assert client.get(url).status_code == 404


def test_anonymous_redirected_to_login(client, workspace):
    project, _, _ = workspace
    response = client.get(reverse("project-detail", args=[project.slug]))
    assert response.status_code == 302
    assert reverse("login") in response.url


def test_missing_object_returns_404(client, workspace):
    project, revision, member = workspace
    client.force_login(member)
    url = reverse("technique-detail", args=[*_args(project, revision), "AML.T9999"])
    assert client.get(url).status_code == 404


def test_landing_has_theme_toggle_and_stylesheet(client):
    response = client.get(reverse("landing"))
    assert b"data-theme-toggle" in response.content
    assert b"workbench/app.css" in response.content
