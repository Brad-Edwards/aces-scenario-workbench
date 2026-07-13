from __future__ import annotations

import json

import pytest
from django.conf import settings
from django.contrib.auth import get_user_model
from django.urls import reverse

from aces_scenario_workbench.workbench.ingest import import_projection, load_projection
from aces_scenario_workbench.workbench.models import (
    Comment,
    Decision,
    Membership,
    ObjectType,
    Project,
    Role,
)

User = get_user_model()
SAMPLE = settings.BASE_DIR / "fixtures" / "sample-scenario" / "atlas-technique-projection.yaml"


@pytest.fixture
def user_with_data(db):
    project = Project.objects.create(slug="demo", name="Demo Project")
    user = User.objects.create_user(
        email="member@example.com", password="review-pass-1", display_name="Member One"
    )
    Membership.objects.create(project=project, user=user, role=Role.REVIEWER)
    data, _ = load_projection(SAMPLE)
    revision, _ = import_projection(project, data)
    anchor = {
        "revision": revision,
        "object_type": ObjectType.TECHNIQUE,
        "object_stable_id": "AML.T0000",
    }
    Comment.objects.create(author=user, body="A review note.", **anchor)
    Decision.objects.create(author=user, decision="accept", rationale="ok", **anchor)
    return user


def test_account_page_requires_login(client):
    response = client.get(reverse("account"))
    assert response.status_code == 302
    assert reverse("login") in response.url


def test_account_page_shows_email(client, user_with_data):
    client.force_login(user_with_data)
    response = client.get(reverse("account"))
    assert response.status_code == 200
    assert b"member@example.com" in response.content


def test_account_export(client, user_with_data):
    client.force_login(user_with_data)
    response = client.get(reverse("account-export"))
    assert response.status_code == 200
    assert response["Content-Disposition"].startswith("attachment")
    payload = json.loads(response.content)
    assert payload["email"] == "member@example.com"
    assert payload["memberships"][0]["project"] == "demo"
    assert payload["comments"][0]["body"] == "A review note."
    assert payload["decisions"][0]["decision"] == "accept"


def test_account_export_requires_login(client):
    assert client.get(reverse("account-export")).status_code == 302


def test_account_delete_removes_user_and_content(client, user_with_data):
    client.force_login(user_with_data)
    confirm = client.get(reverse("account-delete"))
    assert confirm.status_code == 200
    assert b"Type your email address to confirm" in confirm.content

    rejected = client.post(reverse("account-delete"), {"confirm_email": "wrong@example.com"})
    assert rejected.status_code == 400
    assert User.objects.filter(email="member@example.com").exists()

    response = client.post(reverse("account-delete"), {"confirm_email": "member@example.com"})
    assert response.status_code == 302
    assert response.url == reverse("landing")
    assert not User.objects.filter(email="member@example.com").exists()
    assert Comment.objects.count() == 0
    assert Decision.objects.count() == 0


def test_account_delete_requires_post(client, user_with_data):
    client.force_login(user_with_data)
    assert client.get(reverse("account-delete")).status_code == 200


def test_privacy_page_is_public(client):
    response = client.get(reverse("privacy"))
    assert response.status_code == 200
    assert b"Privacy" in response.content
