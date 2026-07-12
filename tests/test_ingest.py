from __future__ import annotations

import pytest
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management import call_command
from django.core.management.base import CommandError
from django.urls import reverse

from aces_scenario_workbench.workbench.ingest import (
    ProjectionError,
    import_projection,
    load_projection,
    parse_projection,
)
from aces_scenario_workbench.workbench.models import Membership, Role, Scenario

User = get_user_model()
SAMPLE = settings.BASE_DIR / "fixtures" / "sample-scenario" / "atlas-technique-projection.yaml"


@pytest.fixture
def scenario(db):
    return Scenario.objects.create(slug="demo", name="Demo Scenario")


def _sample_data():
    data, _ = load_projection(SAMPLE)
    return data


def test_import_creates_revision_graph(scenario):
    revision, created = import_projection(scenario, _sample_data())
    assert created is True
    assert revision.scenario.slug == "demo"
    assert revision.tactics.count() == 2
    assert revision.steps.count() == 2
    assert revision.techniques.count() == 3
    assert revision.evidence.count() == 2

    technique = revision.techniques.get(technique_id="AML.T0000")
    assert technique.step.path_step == "1"
    assert technique.evidence.evidence_id == "ev-recon"
    assert [t.tactic_id for t in technique.tactics.all()] == ["AML.TA0002"]


def test_import_is_idempotent(scenario):
    revision1, created1 = import_projection(scenario, _sample_data())
    revision2, created2 = import_projection(scenario, _sample_data())
    assert created1 is True
    assert created2 is False
    assert revision1.pk == revision2.pk
    assert scenario.revisions.count() == 1


def test_changed_content_creates_new_revision(scenario):
    import_projection(scenario, _sample_data())
    changed = _sample_data()
    changed["technique_catalog"].append(
        {"id": "AML.T9999", "name": "Extra", "tactics": ["AML.TA0002"], "challenge_step": "1"}
    )
    revision, created = import_projection(scenario, changed)
    assert created is True
    assert scenario.revisions.count() == 2
    assert revision.techniques.count() == 4


def test_load_projection_from_directory(tmp_path):
    (tmp_path / "atlas-technique-projection.yaml").write_bytes(SAMPLE.read_bytes())
    data, raw = load_projection(tmp_path)
    assert data["pack"] == "sample-scenario"
    assert raw


def test_load_projection_missing(tmp_path):
    with pytest.raises(ProjectionError):
        load_projection(tmp_path)


def test_load_projection_missing_file(tmp_path):
    with pytest.raises(ProjectionError):
        load_projection(tmp_path / "does-not-exist.yaml")


def test_parse_projection_rejects_invalid_yaml():
    with pytest.raises(ProjectionError):
        parse_projection(b"key: [unclosed")


def test_parse_projection_rejects_non_mapping():
    with pytest.raises(ProjectionError):
        parse_projection(b"- one\n- two\n")


def test_management_command(scenario):
    call_command("import_projection", str(SAMPLE), scenario="demo")
    call_command("import_projection", str(SAMPLE), scenario="demo")
    assert scenario.revisions.count() == 1


@pytest.mark.django_db
def test_management_command_unknown_scenario():
    with pytest.raises(CommandError):
        call_command("import_projection", str(SAMPLE), scenario="missing")


def test_management_command_bad_path(scenario):
    with pytest.raises(CommandError):
        call_command("import_projection", str(SAMPLE.parent / "nope.yaml"), scenario="demo")


@pytest.mark.django_db
def test_sync_scenario_command_creates_scenario_and_revision():
    call_command("sync_scenario", str(SAMPLE.parent), slug="demo", name="Demo Scenario")
    scenario = Scenario.objects.get(slug="demo")
    assert scenario.name == "Demo Scenario"
    assert scenario.revisions.count() == 1

    call_command("sync_scenario", str(SAMPLE.parent), slug="demo")
    scenario.refresh_from_db()
    assert scenario.name == "Demo Scenario"
    assert scenario.revisions.count() == 1


@pytest.mark.django_db
def test_sync_scenario_command_infers_slug_from_directory():
    call_command("sync_scenario", str(SAMPLE.parent))
    scenario = Scenario.objects.get(slug="sample-scenario")
    assert scenario.revisions.count() == 1


@pytest.mark.django_db
def test_sync_scenario_command_grants_user_access():
    user = User.objects.create_user(email="author@example.com", password="review-pass-1")
    call_command(
        "sync_scenario",
        str(SAMPLE.parent),
        slug="demo",
        grant_user=user.email,
        role=Role.AUTHOR,
    )
    membership = Membership.objects.get(scenario__slug="demo", user=user)
    assert membership.role == Role.AUTHOR

    call_command(
        "sync_scenario",
        str(SAMPLE.parent),
        slug="demo",
        grant_user=user.email,
        role=Role.ADMINISTRATOR,
    )
    membership.refresh_from_db()
    assert membership.role == Role.ADMINISTRATOR


@pytest.mark.django_db
def test_sync_scenario_command_unknown_grant_user():
    with pytest.raises(CommandError):
        call_command(
            "sync_scenario",
            str(SAMPLE.parent),
            slug="demo",
            grant_user="missing@example.com",
        )


def _upload():
    return SimpleUploadedFile("projection.yaml", SAMPLE.read_bytes(), content_type="text/yaml")


def test_api_upload_author(client, scenario):
    author = User.objects.create_user(email="author@example.com", password="review-pass-1")
    Membership.objects.create(scenario=scenario, user=author, role=Role.AUTHOR)
    client.force_login(author)
    url = reverse("api-upload-revision", args=["demo"])

    created = client.post(url, {"file": _upload()})
    assert created.status_code == 201
    assert created.json()["created"] is True

    again = client.post(url, {"file": _upload()})
    assert again.status_code == 200
    assert again.json()["created"] is False


def test_api_upload_forbidden_for_viewer(client, scenario):
    viewer = User.objects.create_user(email="viewer@example.com", password="review-pass-1")
    Membership.objects.create(scenario=scenario, user=viewer, role=Role.STAKEHOLDER)
    client.force_login(viewer)
    response = client.post(reverse("api-upload-revision", args=["demo"]), {"file": _upload()})
    assert response.status_code == 403


def test_api_upload_requires_file(client, scenario):
    author = User.objects.create_user(email="author@example.com", password="review-pass-1")
    Membership.objects.create(scenario=scenario, user=author, role=Role.AUTHOR)
    client.force_login(author)
    response = client.post(reverse("api-upload-revision", args=["demo"]))
    assert response.status_code == 400


def test_api_upload_rejects_invalid_yaml(client, scenario):
    author = User.objects.create_user(email="author@example.com", password="review-pass-1")
    Membership.objects.create(scenario=scenario, user=author, role=Role.AUTHOR)
    client.force_login(author)
    bad = SimpleUploadedFile("bad.yaml", b"- not\n- a mapping\n", content_type="text/yaml")
    response = client.post(reverse("api-upload-revision", args=["demo"]), {"file": bad})
    assert response.status_code == 400


def test_api_upload_requires_login(client, scenario):
    response = client.post(reverse("api-upload-revision", args=["demo"]), {"file": _upload()})
    assert response.status_code == 302
