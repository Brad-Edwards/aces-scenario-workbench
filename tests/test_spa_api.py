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
    challenge = revision.challenges.get(flag_id="flag-recon")
    challenge.metadata = {
        **challenge.metadata,
        "participant": {"objective": "Review the exposed reconnaissance surface."},
        "sdl_challenge": {
            "proof_obligation": "recon-receipt",
            "target_minutes": 12,
            "authority_scope_refs": ["nodes.core.participant-workstation"],
        },
        "related_systems": [
            {
                "id": "participant-workstation",
                "type": "vm",
                "description": "Participant workstation.",
                "service": "browser-terminal",
                "service_port": 443,
                "service_description": "Browser terminal.",
                "reference": "nodes.core.participant-workstation.services.browser-terminal",
            }
        ],
    }
    challenge.save(update_fields=["metadata"])
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
    assert '"project"' not in json.dumps(payload).lower()
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
    assert "content_digest" not in json.dumps(payload).lower()
    assert '"project"' not in json.dumps(payload).lower()


def test_revision_workspace_returns_collaboration_counts(client, spa_workspace):
    _, _, revision, member, _ = spa_workspace
    client.force_login(member)

    response = client.get(reverse("api-revision-workspace", args=[revision.pk]))

    assert response.status_code == 200
    payload = response.json()
    first_module = next(module for module in payload["modules"] if module["id"] == "1")
    first_technique = next(
        technique
        for technique in payload["techniques"]
        if technique["id"] == "SDL.1.reconnaissance"
    )
    assert first_module["commentCount"] == 1
    assert first_module["decisionCount"] == 1
    assert first_module["behaviorSpecification"] == "module-01-recon"
    assert first_module["flagOutcome"] == "recon"
    assert first_module["justification"] == "Directly selectable reconnaissance action."
    assert first_technique["surface"] == "module-01-recon"
    assert first_technique["relationship"] == "sdl_behavior_ref"
    assert first_technique["coverageStatus"] == "draft"
    assert first_technique["rationale"] == "Derived from ACES SDL ai_offensive_behavior_refs."
    recon_challenge = next(
        challenge for challenge in payload["challenges"] if challenge["id"] == "flag-recon"
    )
    planned_challenge = next(
        challenge for challenge in payload["challenges"] if challenge["id"] == "flag-evasion"
    )
    assert payload["summary"]["challengeCount"] == 2
    assert payload["summary"]["implementedChallengeCount"] == 1
    assert payload["summary"]["plannedChallengeCount"] == 1
    assert payload["summary"]["totalMinutes"] == 45
    assert payload["scoring"]["max_points"] == 250
    assert payload["environment"]["counts"]["assets"] == 1
    assert payload["topology"]["source"] == "sdl"
    assert payload["topology"]["coverage"]["sdl_node_count"] == 2
    assert payload["topology"]["nodes"][0]["id"] == "participant-workstation"
    assert payload["topology"]["nodes"][1]["services"][0]["id"] == "proof-api"
    assert payload["topology"]["agents"][0]["initial_hosts"] == [
        "participant-workstation",
        "proof-service",
    ]
    assert recon_challenge["flagId"] == "flag-recon"
    assert recon_challenge["outcome"] == "recon"
    assert recon_challenge["module"] == "1"
    assert recon_challenge["status"] == "Implemented"
    assert recon_challenge["readiness"]["runtime"] is True
    assert recon_challenge["scoring"]["points"] == 100
    assert recon_challenge["techniqueIds"] == ["SDL.1.reconnaissance"]
    assert recon_challenge["participant"]["objective"] == (
        "Review the exposed reconnaissance surface."
    )
    assert recon_challenge["organizer"]["proof_obligation"] == "recon-receipt"
    assert recon_challenge["relatedSystems"][0]["service"] == "browser-terminal"
    assert recon_challenge["evidenceRequirements"][0]["evidenceId"] == "ev-recon"
    assert recon_challenge["evidenceRequirements"][0]["eventKind"] == "recon_verdict"
    assert recon_challenge["evidenceRequirements"][0]["proofFields"] == [
        "actor_role",
        "asset_id",
        "event_kind",
        "outcome_id",
        "range_instance",
        "participant",
        "timestamp",
        "status",
        "digest",
    ]
    assert planned_challenge["status"] == "Planned"
    assert planned_challenge["implemented"] is False
    assert planned_challenge["readiness"]["runtime"] is False
    assert planned_challenge["readiness"]["scoring"] is True
    assert payload["comments"][0]["body"] == "Needs one check."
    assert payload["comments"][0]["edited"] is False
    assert payload["decisions"][0]["decision"] == "Needs change"
    assert "content_digest" not in json.dumps(payload).lower()
    assert '"project"' not in json.dumps(payload).lower()


def test_spa_comment_endpoint_allows_challenges_and_ttps(client, spa_workspace):
    _, _, revision, member, _ = spa_workspace
    client.force_login(member)

    challenge_response = client.post(
        reverse(
            "api-object-comment",
            args=[revision.pk, ObjectType.CHALLENGE, "flag-recon"],
        ),
        data=json.dumps({"body": "Challenge evidence needs a receipt example."}),
        content_type="application/json",
    )
    technique_response = client.post(
        reverse(
            "api-object-comment",
            args=[revision.pk, ObjectType.TECHNIQUE, "SDL.1.reconnaissance"],
        ),
        data=json.dumps({"body": "Tie this behavior back to the implemented path."}),
        content_type="application/json",
    )

    assert challenge_response.status_code == 201
    assert technique_response.status_code == 201
    assert Comment.objects.filter(
        revision=revision,
        object_type=ObjectType.CHALLENGE,
        object_stable_id="flag-recon",
        body="Challenge evidence needs a receipt example.",
    ).exists()
    assert Comment.objects.filter(
        revision=revision,
        object_type=ObjectType.TECHNIQUE,
        object_stable_id="SDL.1.reconnaissance",
        body="Tie this behavior back to the implemented path.",
    ).exists()

    workspace = client.get(reverse("api-revision-workspace", args=[revision.pk])).json()
    challenge = next(item for item in workspace["challenges"] if item["id"] == "flag-recon")
    technique = next(
        item for item in workspace["techniques"] if item["id"] == "SDL.1.reconnaissance"
    )
    assert challenge["commentCount"] == 1
    assert technique["commentCount"] == 1


def test_spa_decision_endpoint_allows_challenges_only(client, spa_workspace):
    _, _, revision, member, _ = spa_workspace
    client.force_login(member)

    challenge_response = client.post(
        reverse(
            "api-object-decision",
            args=[revision.pk, ObjectType.CHALLENGE, "flag-recon"],
        ),
        data=json.dumps(
            {"decision": DecisionType.ACCEPT, "rationale": "Evidence contract is good."}
        ),
        content_type="application/json",
    )
    technique_response = client.post(
        reverse(
            "api-object-decision",
            args=[revision.pk, ObjectType.TECHNIQUE, "SDL.1.reconnaissance"],
        ),
        data=json.dumps(
            {"decision": DecisionType.ACCEPT, "rationale": "Should not be accepted here."}
        ),
        content_type="application/json",
    )

    assert challenge_response.status_code == 201
    assert challenge_response.json()["decision"]["decision"] == "Accept"
    assert Decision.objects.filter(
        revision=revision,
        object_type=ObjectType.CHALLENGE,
        object_stable_id="flag-recon",
        decision=DecisionType.ACCEPT,
    ).exists()
    assert technique_response.status_code == 400
    assert not Decision.objects.filter(
        revision=revision,
        object_type=ObjectType.TECHNIQUE,
        object_stable_id="SDL.1.reconnaissance",
        decision=DecisionType.ACCEPT,
    ).exists()


def test_spa_collaboration_endpoints_reject_non_members(client, spa_workspace):
    _, _, revision, _, outsider = spa_workspace
    client.force_login(outsider)

    comment_response = client.post(
        reverse(
            "api-object-comment",
            args=[revision.pk, ObjectType.CHALLENGE, "flag-recon"],
        ),
        data=json.dumps({"body": "Not allowed."}),
        content_type="application/json",
    )
    decision_response = client.post(
        reverse(
            "api-object-decision",
            args=[revision.pk, ObjectType.CHALLENGE, "flag-recon"],
        ),
        data=json.dumps({"decision": DecisionType.ACCEPT}),
        content_type="application/json",
    )

    assert comment_response.status_code == 404
    assert decision_response.status_code == 404


def test_spa_api_rejects_non_members(client, spa_workspace):
    scenario, _, revision, _, outsider = spa_workspace
    client.force_login(outsider)

    assert client.get(reverse("api-scenario-detail", args=[scenario.slug])).status_code == 404
    assert client.get(reverse("api-revision-workspace", args=[revision.pk])).status_code == 404
