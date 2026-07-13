from __future__ import annotations

import importlib
import os
from io import StringIO
from unittest import mock

import pytest
from django.contrib.auth import get_user_model
from django.core.exceptions import ImproperlyConfigured
from django.core.management import call_command
from django.test import override_settings
from django.urls import reverse

import aces_scenario_workbench.settings as settings_module
from aces_scenario_workbench.accounts.models import Invitation
from aces_scenario_workbench.workbench.models import Scenario

User = get_user_model()
PASSWORD = "review-pass-42x"


# --- Content Security Policy -------------------------------------------------


def test_login_csp_has_no_inline_scripts(client):
    response = client.get(reverse("login"))
    assert response.status_code == 200
    policy = response.headers.get("Content-Security-Policy", "")
    assert "default-src 'self'" in policy
    assert "object-src 'none'" in policy
    assert "frame-ancestors 'none'" in policy
    assert "script-src 'self'" in policy
    assert "'unsafe-inline'" not in policy
    assert b"<script" not in response.content
    assert b"data-theme-toggle" not in response.content


def test_csp_excludes_admin(client):
    response = client.get(f"/{settings_module.ADMIN_PATH}login/")
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
    scenario = Scenario.objects.create(slug="demo", name="Demo Scenario")
    invitation = Invitation.objects.create(email="new@example.com", scenario=scenario)
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
@override_settings(
    DEBUG=False,
    SECURE_SSL_REDIRECT=True,
    SECURE_HSTS_SECONDS=31536000,
    SESSION_COOKIE_SECURE=True,
    CSRF_COOKIE_SECURE=True,
    ADMIN_PATH="control/",
)
def test_doctor_reports_hardening_posture():
    out = StringIO()
    call_command("doctor", stdout=out)
    output = out.getvalue()
    assert "OK  HTTPS redirect: on" in output
    assert "OK  HSTS: 31536000s" in output
    assert "OK  Secure cookies: on" in output
    assert "OK  Brute-force protection: django-axes" in output
    assert "OK  Content-Security-Policy: on" in output
    assert "OK  Admin path: /control/" in output


@pytest.mark.django_db
@override_settings(
    DEBUG=False,
    SECURE_SSL_REDIRECT=False,
    SECURE_HSTS_SECONDS=0,
    SESSION_COOKIE_SECURE=False,
    CSRF_COOKIE_SECURE=True,
    ADMIN_PATH="admin/",
)
def test_doctor_flags_insecure_hardening_posture():
    out = StringIO()
    call_command("doctor", stdout=out)
    output = out.getvalue()
    assert "!!  HTTPS redirect: off" in output
    assert "!!  HSTS: off" in output
    assert "!!  Secure cookies: off" in output
    assert "!!  Admin path: /admin/" in output


def test_admin_is_not_mounted_at_default_path(client):
    assert client.get("/admin/login/").status_code == 404
    assert client.get(f"/{settings_module.ADMIN_PATH}login/").status_code == 200


def test_admin_path_rejects_invalid_values():
    for value in ("", "../admin", "http://example.test/admin", "control?next=/", r"ops\\admin"):
        with pytest.raises(ImproperlyConfigured):
            settings_module._env_relative_path("ACES_WORKBENCH_TEST_ADMIN_PATH", value)
