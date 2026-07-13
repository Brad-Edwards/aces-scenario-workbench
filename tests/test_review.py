from __future__ import annotations

import pytest
from django.conf import settings
from django.contrib.auth import get_user_model
from django.urls import reverse

from aces_scenario_workbench.workbench.ingest import import_projection, load_projection
from aces_scenario_workbench.workbench.models import Membership, Role, Scenario, Technique

User = get_user_model()
SAMPLE = settings.BASE_DIR / "fixtures" / "sample-scenario" / "atlas-technique-projection.yaml"


def _link(scenario, revision, technique_id):
    return f"/scenarios/{scenario.slug}/revisions/{revision.pk}/techniques/{technique_id}/".encode()


@pytest.fixture
def workspace(db):
    scenario = Scenario.objects.create(slug="demo", name="Demo Scenario")
    member = User.objects.create_user(email="member@example.com", password="review-pass-1")
    Membership.objects.create(scenario=scenario, user=member, role=Role.REVIEWER)
    data, _ = load_projection(SAMPLE)
    revision, _ = import_projection(scenario, data)
    return scenario, revision, member


def _args(scenario, revision):
    return [scenario.slug, revision.pk]


def test_scenario_detail_lists_revisions(client, workspace):
    scenario, revision, member = workspace
    client.force_login(member)
    response = client.get(reverse("scenario-detail", args=[scenario.slug]))
    assert response.status_code == 200
    assert b"Demo Scenario" in response.content
    assert revision.label.encode() in response.content


def test_revision_overview_renders(client, workspace):
    scenario, revision, member = workspace
    client.force_login(member)
    response = client.get(reverse("revision-overview", args=_args(scenario, revision)))
    assert response.status_code == 200
    assert b"Coverage overview" in response.content
    assert b"Behavior relationships by ref" in response.content
    assert b"Challenge progression" in response.content
    assert b"Behaviors" in response.content
    assert b"AML.T0000" in response.content
    assert b"Modules" in response.content
    assert b"Planned in-world variant" in response.content


def test_object_detail_pages(client, workspace):
    scenario, revision, member = workspace
    client.force_login(member)
    checks = {
        reverse(
            "technique-detail", args=[*_args(scenario, revision), "AML.T0000"]
        ): b"Planned action",
        reverse(
            "tactic-detail", args=[*_args(scenario, revision), "AML.TA0002"]
        ): b"Behaviors using this ref",
        reverse("step-detail", args=[*_args(scenario, revision), "1"]): b"Behaviors in this module",
        reverse(
            "evidence-detail", args=[*_args(scenario, revision), "ev-recon"]
        ): b"Behaviors requiring this evidence",
    }
    for url, needle in checks.items():
        response = client.get(url)
        assert response.status_code == 200, url
        assert needle in response.content, url


def test_non_member_gets_404(client, workspace):
    scenario, revision, _ = workspace
    outsider = User.objects.create_user(email="outsider@example.com", password="review-pass-1")
    client.force_login(outsider)
    assert client.get(reverse("scenario-detail", args=[scenario.slug])).status_code == 404
    assert (
        client.get(reverse("revision-overview", args=_args(scenario, revision))).status_code == 404
    )
    url = reverse("technique-detail", args=[*_args(scenario, revision), "AML.T0000"])
    assert client.get(url).status_code == 404


def test_anonymous_redirected_to_login(client, workspace):
    scenario, _, _ = workspace
    response = client.get(reverse("scenario-detail", args=[scenario.slug]))
    assert response.status_code == 302
    assert reverse("login") in response.url


def test_missing_object_returns_404(client, workspace):
    scenario, revision, member = workspace
    client.force_login(member)
    url = reverse("technique-detail", args=[*_args(scenario, revision), "AML.T9999"])
    assert client.get(url).status_code == 404


def test_spa_shell_uses_standalone_assets(client, workspace):
    _, _, member = workspace
    client.force_login(member)
    response = client.get(reverse("spa-app"))
    assert response.status_code == 200
    assert b"workbench/spa/app.css" in response.content
    assert b"workbench/spa/app.js" in response.content
    assert b"data-theme-toggle" not in response.content
    assert b"data-cookie-notice" not in response.content


def test_revision_overview_has_filter_toolbar(client, workspace):
    scenario, revision, member = workspace
    client.force_login(member)
    response = client.get(reverse("revision-overview", args=_args(scenario, revision)))
    for field in (b'name="q"', b'name="module"', b'name="tactic"', b'name="level"'):
        assert field in response.content
    assert b"Showing 3 of 3 behaviors" in response.content
    assert b'class="top-metric"' in response.content
    assert b'class="bar-row"' in response.content
    assert b'class="progress-step"' in response.content


def test_technique_search_matches_name_and_evidence_and_action(client, workspace):
    scenario, revision, member = workspace
    client.force_login(member)
    url = reverse("revision-overview", args=_args(scenario, revision))
    for query in ("Journals", "ev-recon", "Review published literature"):
        response = client.get(url, {"q": query})
        assert _link(scenario, revision, "AML.T0000.000") in response.content, query
        assert _link(scenario, revision, "AML.T0015") not in response.content, query


def test_technique_filters_by_tactic_module_and_level(client, workspace):
    scenario, revision, member = workspace
    client.force_login(member)
    url = reverse("revision-overview", args=_args(scenario, revision))
    for params in ({"tactic": "AML.TA0007"}, {"module": "2"}, {"level": "intermediate"}):
        response = client.get(url, params)
        assert _link(scenario, revision, "AML.T0015") in response.content, params
        assert _link(scenario, revision, "AML.T0000") not in response.content, params
        assert _link(scenario, revision, "AML.T0000.000") not in response.content, params


def test_technique_filters_combine(client, workspace):
    scenario, revision, member = workspace
    client.force_login(member)
    url = reverse("revision-overview", args=_args(scenario, revision))
    response = client.get(url, {"tactic": "AML.TA0002", "level": "quick"})
    assert b"Showing 2 of 3 behaviors matching your filters" in response.content
    assert _link(scenario, revision, "AML.T0015") not in response.content


def test_technique_search_no_match(client, workspace):
    scenario, revision, member = workspace
    client.force_login(member)
    url = reverse("revision-overview", args=_args(scenario, revision))
    response = client.get(url, {"q": "no-such-technique-xyz"})
    assert b"Showing 0 of 3 behaviors" in response.content
    assert b"No behaviors match your filters." in response.content


def test_techniques_paginate(client, workspace):
    scenario, revision, member = workspace
    Technique.objects.bulk_create(
        Technique(revision=revision, technique_id=f"AML.T9{i:03d}", name=f"Extra {i}")
        for i in range(27)
    )
    client.force_login(member)
    url = reverse("revision-overview", args=_args(scenario, revision))

    page1 = client.get(url)
    assert page1.content.count(b'class="tech-id"') == 25
    assert b"Page 1 of 2" in page1.content
    assert b"Next" in page1.content

    page2 = client.get(url, {"page": "2"})
    assert page2.content.count(b'class="tech-id"') == 5
    assert b"Page 2 of 2" in page2.content
    assert b"Previous" in page2.content
