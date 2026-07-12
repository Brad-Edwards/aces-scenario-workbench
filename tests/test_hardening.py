from __future__ import annotations

import importlib
import os
from io import StringIO
from unittest import mock

import pytest
from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.test import override_settings
from django.urls import reverse

import aces_scenario_workbench.settings as settings_module
from aces_scenario_workbench.accounts.models import Invitation
from aces_scenario_workbench.workbench.models import Project

User = get_user_model()
PASSWORD = "review-pass-42x"


# --- Content Security Policy -------------------------------------------------


def test_csp_header_carries_script_nonce(client):
    response = client.get(reverse("login"))
    assert response.status_code == 200
    policy = response.headers.get("Content-Security-Policy", "")
    assert "default-src 'self'" in policy
    assert "object-src 'none'" in policy
    assert "frame-ancestors 'none'" in policy
    assert "script-src 'self' 'nonce-" in policy
    # The inline theme script must carry the exact nonce advertised in the header.
    nonce = policy.split("'nonce-", 1)[1].split("'", 1)[0]
    assert f'nonce="{nonce}"'.encode() in response.content


def test_csp_excludes_admin(client):
    response = client.get("/admin/login/")
    assert response.status_code == 200
    assert "Content-Security-Policy" not in response.headers


# --- Rate limiting -----------------------------------------------------------


@pytest.mark.django_db
def test_password_reset_is_rate_limited(client):
    User.objects.create_user(email="member@example.com", password=PASSWORD)
    url = reverse("password_reset")
    for _ in range(5):
        assert client.post(url, {"email": "member@example.com"}).status_code == 302
    limited = client.post(url, {"email": "member@example.com"})
    assert limited.status_code == 429
    assert b"Too many requests" in limited.content


@pytest.mark.django_db
def test_invite_accept_is_rate_limited(client):
    project = Project.objects.create(slug="demo", name="Demo Project")
    invitation = Invitation.objects.create(email="new@example.com", project=project)
    url = reverse("invite-accept", args=[invitation.token])
    # A mismatched password keeps the invitation pending, so every POST counts.
    bad = {"display_name": "", "password1": PASSWORD, "password2": "different-pass-9"}
    for _ in range(10):
        assert client.post(url, bad).status_code == 200
    assert client.post(url, bad).status_code == 429


# --- Brute-force lockout (django-axes) ---------------------------------------


@override_settings(AXES_FAILURE_LIMIT=3)
@pytest.mark.django_db
def test_login_locks_out_after_repeated_failures(client):
    User.objects.create_user(email="member@example.com", password=PASSWORD)
    url = reverse("login")
    statuses = [
        client.post(url, {"username": "member@example.com", "password": "wrong-pass-1"}).status_code
        for _ in range(5)
    ]
    assert 429 in statuses
    # While locked, even correct credentials are refused.
    locked = client.post(url, {"username": "member@example.com", "password": PASSWORD})
    assert locked.status_code == 429


# --- HTTPS enforcement defaults ---------------------------------------------


def test_production_defaults_enable_https_enforcement():
    try:
        with mock.patch.dict(os.environ, {}, clear=True):
            mod = importlib.reload(settings_module)
            assert mod.DEBUG is False
            assert mod.SECURE_SSL_REDIRECT is True
            assert mod.SECURE_HSTS_SECONDS == 31536000
            assert mod.SESSION_COOKIE_SECURE is True
            assert mod.CSRF_COOKIE_SECURE is True
    finally:
        importlib.reload(settings_module)


def test_debug_relaxes_https_enforcement():
    try:
        with mock.patch.dict(os.environ, {"ACES_WORKBENCH_DEBUG": "true"}, clear=True):
            mod = importlib.reload(settings_module)
            assert mod.DEBUG is True
            assert mod.SECURE_SSL_REDIRECT is False
            assert mod.SECURE_HSTS_SECONDS == 0
            assert mod.SESSION_COOKIE_SECURE is False
    finally:
        importlib.reload(settings_module)


# --- doctor hardening report -------------------------------------------------


@pytest.mark.django_db
def test_doctor_reports_hardening_posture():
    out = StringIO()
    call_command("doctor", stdout=out)
    output = out.getvalue()
    for label in (
        "HTTPS redirect",
        "HSTS",
        "Secure cookies",
        "Brute-force protection",
        "Content-Security-Policy",
    ):
        assert label in output
