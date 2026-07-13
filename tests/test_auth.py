from __future__ import annotations

from datetime import timedelta

import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser
from django.urls import reverse
from django.utils import timezone

from aces_scenario_workbench.accounts.models import Invitation
from aces_scenario_workbench.workbench import authz
from aces_scenario_workbench.workbench.models import Membership, Role, Scenario

User = get_user_model()
STRONG_PASSWORD = "review-pass-42x"


@pytest.fixture
def scenario(db):
    return Scenario.objects.create(slug="demo", name="Demo Scenario")


@pytest.fixture
def member(db, scenario):
    user = User.objects.create_user(email="member@example.com", password=STRONG_PASSWORD)
    Membership.objects.create(scenario=scenario, user=user, role=Role.REVIEWER)
    return user


def test_dashboard_requires_login(client):
    response = client.get(reverse("dashboard"))
    assert response.status_code == 302
    assert reverse("login") in response.url


def test_dashboard_lists_only_member_scenarios(client, scenario, member):
    Scenario.objects.create(slug="other", name="Other Scenario")
    client.force_login(member)
    response = client.get(reverse("dashboard"))
    assert response.status_code == 200
    assert b"Demo Scenario" in response.content
    assert b"Other Scenario" not in response.content


def test_login_view_authenticates(client, member):
    response = client.post(
        reverse("login"),
        {"username": "member@example.com", "password": STRONG_PASSWORD},
    )
    assert response.status_code == 302
    assert response.url == reverse("spa-app")


def test_invite_accept_new_user(client, scenario):
    invitation = Invitation.objects.create(
        email="new@example.com", scenario=scenario, role=Role.AUTHOR
    )
    url = reverse("invite-accept", args=[invitation.token])

    get_response = client.get(url)
    assert get_response.status_code == 200
    assert b"password" in get_response.content.lower()

    post_response = client.post(
        url,
        {"display_name": "New Author", "password1": STRONG_PASSWORD, "password2": STRONG_PASSWORD},
    )
    assert post_response.status_code == 302
    assert post_response.url == reverse("spa-app")
    user = User.objects.get(email="new@example.com")
    assert user.display_name == "New Author"
    assert Membership.objects.filter(scenario=scenario, user=user, role=Role.AUTHOR).exists()
    invitation.refresh_from_db()
    assert invitation.accepted_at is not None


def test_invite_accept_existing_user_grants_membership(client, scenario):
    existing = User.objects.create_user(email="existing@example.com", password=STRONG_PASSWORD)
    invitation = Invitation.objects.create(
        email="existing@example.com", scenario=scenario, role=Role.STAKEHOLDER
    )
    response = client.post(reverse("invite-accept", args=[invitation.token]))
    assert response.status_code == 302
    assert response.url == reverse("login")
    assert Membership.objects.filter(scenario=scenario, user=existing).exists()


def test_invite_accept_password_mismatch_creates_no_user(client, scenario):
    invitation = Invitation.objects.create(email="bad@example.com", scenario=scenario)
    response = client.post(
        reverse("invite-accept", args=[invitation.token]),
        {"display_name": "", "password1": STRONG_PASSWORD, "password2": "different-pass-9"},
    )
    assert response.status_code == 200
    assert not User.objects.filter(email="bad@example.com").exists()


def test_invite_accept_weak_password_rejected(client, scenario):
    invitation = Invitation.objects.create(email="weak@example.com", scenario=scenario)
    response = client.post(
        reverse("invite-accept", args=[invitation.token]),
        {"display_name": "", "password1": "1234", "password2": "1234"},
    )
    assert response.status_code == 200
    assert not User.objects.filter(email="weak@example.com").exists()


def test_invite_accept_rejects_used_or_expired(client, scenario):
    used = Invitation.objects.create(
        email="used@example.com", scenario=scenario, accepted_at=timezone.now()
    )
    assert client.get(reverse("invite-accept", args=[used.token])).status_code == 410

    expired = Invitation.objects.create(email="old@example.com", scenario=scenario)
    expired.created_at = timezone.now() - timedelta(days=30)
    expired.save(update_fields=["created_at"])
    assert client.get(reverse("invite-accept", args=[expired.token])).status_code == 410


def test_invitation_helpers(scenario):
    invitation = Invitation.objects.create(email="i@example.com", scenario=scenario)
    assert invitation.is_pending() is True
    assert invitation.is_expired() is False
    assert str(invitation) == f"Invitation for i@example.com to {scenario.pk}"


@pytest.mark.django_db
def test_authz_helpers(scenario, member):
    assert authz.is_member(member, scenario) is True
    assert authz.user_role(member, scenario) == Role.REVIEWER
    assert authz.user_membership(AnonymousUser(), scenario) is None
    assert authz.user_role(AnonymousUser(), scenario) is None


@pytest.mark.django_db
def test_logout_requires_post(client, member):
    client.force_login(member)
    assert client.get(reverse("logout")).status_code == 405
    assert client.post(reverse("logout")).status_code == 302
