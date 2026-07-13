from __future__ import annotations

import pytest
from django.conf import settings
from django.contrib.auth import get_user_model
from django.urls import reverse

from aces_scenario_workbench.workbench.ingest import import_projection, load_projection
from aces_scenario_workbench.workbench.models import (
    ActivityEvent,
    Comment,
    Decision,
    Membership,
    ReviewState,
    ReviewStatus,
    Role,
    Scenario,
)

User = get_user_model()
SAMPLE = settings.BASE_DIR / "fixtures" / "sample-scenario" / "atlas-technique-projection.yaml"
TECH = "AML.T0000"


@pytest.fixture
def workspace(db):
    scenario = Scenario.objects.create(slug="demo", name="Demo Scenario")
    reviewer = User.objects.create_user(email="reviewer@example.com", password="review-pass-1")
    stakeholder = User.objects.create_user(email="stake@example.com", password="review-pass-1")
    Membership.objects.create(scenario=scenario, user=reviewer, role=Role.REVIEWER)
    Membership.objects.create(scenario=scenario, user=stakeholder, role=Role.STAKEHOLDER)
    data, _ = load_projection(SAMPLE)
    revision, _ = import_projection(scenario, data)
    return scenario, revision, reviewer, stakeholder


def _url(name, scenario, revision, extra):
    return reverse(name, args=[scenario.slug, revision.pk, *extra])


def test_reviewer_can_comment(client, workspace):
    scenario, revision, reviewer, _ = workspace
    client.force_login(reviewer)
    url = _url("object-comment", scenario, revision, ["technique", TECH])
    response = client.post(url, {"body": "Please clarify the rationale."})
    assert response.status_code == 302
    comment = Comment.objects.get()
    assert comment.body == "Please clarify the rationale."
    assert comment.object_stable_id == TECH
    assert ActivityEvent.objects.filter(verb="commented").exists()


def test_empty_comment_is_ignored(client, workspace):
    scenario, revision, reviewer, _ = workspace
    client.force_login(reviewer)
    url = _url("object-comment", scenario, revision, ["technique", TECH])
    response = client.post(url, {"body": "   "})
    assert response.status_code == 302
    assert Comment.objects.count() == 0


def test_stakeholder_cannot_comment(client, workspace):
    scenario, revision, _, stakeholder = workspace
    client.force_login(stakeholder)
    url = _url("object-comment", scenario, revision, ["technique", TECH])
    assert client.post(url, {"body": "hi"}).status_code == 403


def test_stakeholder_cannot_set_review_state(client, workspace):
    scenario, revision, _, stakeholder = workspace
    client.force_login(stakeholder)
    url = _url("object-review-state", scenario, revision, ["technique", TECH])
    assert client.post(url, {"status": "accepted"}).status_code == 403


def test_stakeholder_cannot_record_decision(client, workspace):
    scenario, revision, _, stakeholder = workspace
    client.force_login(stakeholder)
    url = _url("object-decision", scenario, revision, ["technique", TECH])
    assert client.post(url, {"decision": "accept"}).status_code == 403


def test_review_state_upserts(client, workspace):
    scenario, revision, reviewer, _ = workspace
    client.force_login(reviewer)
    url = _url("object-review-state", scenario, revision, ["technique", TECH])
    client.post(url, {"status": ReviewStatus.ACCEPTED})
    client.post(url, {"status": ReviewStatus.RESOLVED})
    state = ReviewState.objects.get()
    assert state.status == ReviewStatus.RESOLVED


def test_invalid_review_state_ignored(client, workspace):
    scenario, revision, reviewer, _ = workspace
    client.force_login(reviewer)
    url = _url("object-review-state", scenario, revision, ["technique", TECH])
    response = client.post(url, {"status": "bogus"})
    assert response.status_code == 302
    assert ReviewState.objects.count() == 0


def test_record_decision(client, workspace):
    scenario, revision, reviewer, _ = workspace
    client.force_login(reviewer)
    url = _url("object-decision", scenario, revision, ["technique", TECH])
    response = client.post(url, {"decision": "accept", "rationale": "Looks correct."})
    assert response.status_code == 302
    assert Decision.objects.get().rationale == "Looks correct."


def test_invalid_object_type_404(client, workspace):
    scenario, revision, reviewer, _ = workspace
    client.force_login(reviewer)
    url = _url("object-comment", scenario, revision, ["bogus", TECH])
    assert client.post(url, {"body": "hi"}).status_code == 404


def test_non_member_comment_404(client, workspace):
    scenario, revision, _, _ = workspace
    outsider = User.objects.create_user(email="out@example.com", password="review-pass-1")
    client.force_login(outsider)
    url = _url("object-comment", scenario, revision, ["technique", TECH])
    assert client.post(url, {"body": "hi"}).status_code == 404


def test_anonymous_comment_redirects(client, workspace):
    scenario, revision, _, _ = workspace
    url = _url("object-comment", scenario, revision, ["technique", TECH])
    assert client.post(url, {"body": "hi"}).status_code == 302


def test_detail_shows_comment_form_only_for_contributors(client, workspace):
    scenario, revision, reviewer, stakeholder = workspace
    detail = reverse("technique-detail", args=[scenario.slug, revision.pk, TECH])

    client.force_login(reviewer)
    assert b"Add a comment" in client.get(detail).content

    client.force_login(stakeholder)
    assert b"Add a comment" not in client.get(detail).content


def test_scenario_activity_view(client, workspace):
    scenario, revision, reviewer, _ = workspace
    client.force_login(reviewer)
    client.post(_url("object-comment", scenario, revision, ["technique", TECH]), {"body": "note"})
    response = client.get(reverse("scenario-activity", args=[scenario.slug]))
    assert response.status_code == 200
    assert b"commented" in response.content


def test_scenario_activity_requires_membership(client, workspace):
    scenario, _, _, _ = workspace
    outsider = User.objects.create_user(email="out@example.com", password="review-pass-1")
    client.force_login(outsider)
    assert client.get(reverse("scenario-activity", args=[scenario.slug])).status_code == 404
