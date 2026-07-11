from __future__ import annotations

import pytest
from django.contrib.auth import get_user_model
from django.db import IntegrityError

from aces_scenario_workbench.workbench.models import (
    ActivityEvent,
    Comment,
    Decision,
    Evidence,
    Membership,
    ObjectType,
    Project,
    ReviewState,
    ReviewStatus,
    Revision,
    Role,
    Scenario,
    Step,
    Tactic,
    Technique,
)

User = get_user_model()


@pytest.fixture
def user(db):
    return User.objects.create_user(email="reviewer@example.com", password="review-pass-1")


@pytest.fixture
def revision(db):
    project = Project.objects.create(slug="demo", name="Demo Project")
    scenario = Scenario.objects.create(project=project, slug="sample", name="Sample Scenario")
    return Revision.objects.create(
        scenario=scenario,
        label="2026-06",
        mapping_id="sample-scenario-atlas-2026-06",
        content_digest="abc123",
    )


def test_project_scenario_revision_str(revision):
    assert str(revision.scenario.project) == "Demo Project"
    assert str(revision.scenario) == "Sample Scenario"
    assert str(revision) == "Sample Scenario @ 2026-06"


def test_membership_str_and_uniqueness(user, revision):
    project = revision.scenario.project
    membership = Membership.objects.create(project=project, user=user, role=Role.AUTHOR)
    assert str(membership) == f"{user} in {project} (Author)"
    with pytest.raises(IntegrityError):
        Membership.objects.create(project=project, user=user, role=Role.REVIEWER)


def test_atlas_objects_and_relations(revision):
    tactic = Tactic.objects.create(revision=revision, tactic_id="AML.TA0002", name="Reconnaissance")
    step = Step.objects.create(revision=revision, path_step="1", surface="research-workbench")
    evidence = Evidence.objects.create(revision=revision, evidence_id="ev-recon")
    technique = Technique.objects.create(
        revision=revision,
        technique_id="AML.T0000",
        name="Search Open Technical Databases",
        step=step,
        evidence=evidence,
    )
    technique.tactics.add(tactic)

    assert str(tactic) == "AML.TA0002 Reconnaissance"
    assert str(step) == "Step 1"
    assert str(evidence) == "ev-recon"
    assert str(technique) == "AML.T0000 Search Open Technical Databases"
    assert technique.is_subtechnique is False
    assert technique.parent_technique_id == "AML.T0000"
    assert list(technique.tactics.all()) == [tactic]
    assert list(step.techniques.all()) == [technique]


def test_subtechnique_parent_id(revision):
    sub = Technique.objects.create(revision=revision, technique_id="AML.T0000.000", name="Journals")
    assert sub.is_subtechnique is True
    assert sub.parent_technique_id == "AML.T0000"


def test_collaboration_models_str(user, revision):
    comment = Comment.objects.create(
        revision=revision,
        object_type=ObjectType.TECHNIQUE,
        object_stable_id="AML.T0000",
        author=user,
        body="Needs a clearer rationale.",
    )
    assert "AML.T0000" in str(comment)

    decision = Decision.objects.create(
        revision=revision,
        object_type=ObjectType.TECHNIQUE,
        object_stable_id="AML.T0000",
        author=user,
        decision="accept",
    )
    assert str(decision) == "Accept on technique:AML.T0000"

    state = ReviewState.objects.create(
        revision=revision,
        object_type=ObjectType.TECHNIQUE,
        object_stable_id="AML.T0000",
        status=ReviewStatus.ACCEPTED,
        updated_by=user,
    )
    assert str(state) == "technique:AML.T0000 = accepted"

    event = ActivityEvent.objects.create(
        project=revision.scenario.project, actor=user, verb="commented"
    )
    assert str(event) == f"{user} commented"


def test_review_state_uniqueness(user, revision):
    ReviewState.objects.create(revision=revision, object_type=ObjectType.STEP, object_stable_id="1")
    with pytest.raises(IntegrityError):
        ReviewState.objects.create(
            revision=revision, object_type=ObjectType.STEP, object_stable_id="1"
        )
