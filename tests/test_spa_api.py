from __future__ import annotations

import json

import pytest
from django.conf import settings
from django.contrib.auth import get_user_model
from django.urls import reverse

from aces_scenario_workbench.workbench.ingest import import_pack
from aces_scenario_workbench.workbench.models import (
    Comment,
    Decision,
    DecisionType,
    Membership,
    ObjectType,
    Role,
    Scenario,
)

User = get_user_model()
SAMPLE = settings.BASE_DIR / "fixtures" / "sample-scenario"


@pytest.fixture
def spa_workspace(db):
    scenario = Scenario.objects.create(slug="demo", name="Demo Scenario", description="Demo access")
    other = Scenario.objects.create(slug="other", name="Other Scenario")
    member = User.objects.create_user(
        email="member@example.com", password="review-pass-42x", display_name="Member"
    )
    outsider = User.objects.create_user(email="outsider@example.com", password="review-pass-42x")
    Membership.objects.create(scenario=scenario, user=member, role=Role.REVIEWER)
    Membership.objects.create(scenario=other, user=outsider, role=Role.REVIEWER)
    revision, _ = import_pack(scenario, SAMPLE)
    Comment.objects.create(
        revision=revision,
        object_type=ObjectType.STEP,
        object_stable_id="1",
        author=member,
        body="Needs one check.",
    )
    Decision.objects.create(
        revision=revision,
        object_type=ObjectType.STEP,
        object_stable_id="1",
        author=member,
        decision=DecisionType.NEEDS_CHANGE,
        rationale="Add the missing evidence note.",
    )
    return scenario, other, revision, member, outsider


def test_current_user_requires_login(client):
    response = client.get(reverse("api-current-user"))
    assert response.status_code == 302
    assert reverse("login") in response.url


def test_current_user_payload(client, spa_workspace):
    _, _, _, member, _ = spa_workspace
    client.force_login(member)

    response = client.get(reverse("api-current-user"))

    assert response.status_code == 200
    assert response.json() == {
        "email": "member@example.com",
        "displayName": "Member",
        "isStaff": False,
    }


def test_scenario_list_is_scoped_to_membership(client, spa_workspace):
    scenario, other, _, member, _ = spa_workspace
    client.force_login(member)

    response = client.get(reverse("api-scenarios"))

    assert response.status_code == 200
    payload = response.json()
    assert [row["slug"] for row in payload["scenarios"]] == [scenario.slug]
    assert other.slug not in json.dumps(payload)
    assert "project" not in json.dumps(payload).lower()
    assert payload["scenarios"][0]["role"] == "Reviewer"
    assert payload["scenarios"][0]["revisionCount"] == 1


def test_scenario_detail_returns_table_ready_revisions(client, spa_workspace):
    scenario, _, revision, member, _ = spa_workspace
    client.force_login(member)

    response = client.get(reverse("api-scenario-detail", args=[scenario.slug]))

    assert response.status_code == 200
    payload = response.json()
    row = payload["revisions"][0]
    assert row["id"] == revision.pk
    assert row["moduleCount"] == revision.steps.count()
    assert row["techniqueCount"] == revision.techniques.count()
    assert row["evidenceCount"] == revision.evidence.count()
    assert row["challengeCount"] == revision.challenges.count()
    assert row["commentCount"] == 1
    assert row["decisionCount"] == 1
    assert "digest" not in json.dumps(payload).lower()
    assert "project" not in json.dumps(payload).lower()


def test_revision_workspace_returns_collaboration_counts(client, spa_workspace):
    _, _, revision, member, _ = spa_workspace
    client.force_login(member)

    response = client.get(reverse("api-revision-workspace", args=[revision.pk]))

    assert response.status_code == 200
    payload = response.json()
    first_module = next(module for module in payload["modules"] if module["id"] == "1")
    first_technique = next(
        technique for technique in payload["techniques"] if technique["id"] == "AML.T0000"
    )
    assert first_module["commentCount"] == 1
    assert first_module["decisionCount"] == 1
    assert first_module["behaviorSpecification"] == "module-01-recon"
    assert first_module["flagOutcome"] == "recon"
    assert first_module["justification"] == "Directly selectable reconnaissance action."
    assert first_technique["surface"] == "research-workbench"
    assert first_technique["relationship"] == "planned_variant"
    assert first_technique["coverageStatus"] == "planned"
    assert first_technique["rationale"] == "A reconnaissance variant satisfied only by ev-recon."
    assert payload["challenges"][0]["flagId"] == "flag-recon"
    assert payload["challenges"][0]["outcome"] == "recon"
    assert payload["challenges"][0]["module"] == "1"
    assert payload["challenges"][0]["techniqueIds"] == ["AML.T0000", "AML.T0000.000"]
    assert payload["challenges"][0]["evidenceRequirements"][0]["evidenceId"] == "ev-recon"
    assert payload["challenges"][0]["evidenceRequirements"][0]["eventKind"] == "recon_verdict"
    assert payload["comments"][0]["body"] == "Needs one check."
    assert payload["comments"][0]["edited"] is False
    assert payload["decisions"][0]["decision"] == "Needs change"
    assert "digest" not in json.dumps(payload).lower()
    assert "project" not in json.dumps(payload).lower()


def test_spa_api_rejects_non_members(client, spa_workspace):
    scenario, _, revision, _, outsider = spa_workspace
    client.force_login(outsider)

    assert client.get(reverse("api-scenario-detail", args=[scenario.slug])).status_code == 404
    assert client.get(reverse("api-revision-workspace", args=[revision.pk])).status_code == 404
