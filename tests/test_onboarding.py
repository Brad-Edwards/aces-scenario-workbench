from __future__ import annotations

from io import StringIO

import pytest
from django.contrib.admin.sites import AdminSite
from django.contrib.auth import get_user_model
from django.contrib.auth.tokens import default_token_generator
from django.contrib.messages.middleware import MessageMiddleware
from django.contrib.sessions.middleware import SessionMiddleware
from django.core import mail
from django.core.management import call_command
from django.db import DEFAULT_DB_ALIAS, connections
from django.db.utils import OperationalError
from django.test import RequestFactory
from django.urls import reverse
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode

from aces_scenario_workbench.accounts.admin import InvitationAdmin
from aces_scenario_workbench.accounts.emails import invitation_link, send_invitation_email
from aces_scenario_workbench.accounts.forms import UserChangeForm, UserCreationForm
from aces_scenario_workbench.accounts.models import Invitation
from aces_scenario_workbench.workbench.models import Project, Role

User = get_user_model()


@pytest.fixture
def project(db):
    return Project.objects.create(slug="demo", name="Demo Project")


def _admin_request(user):
    request = RequestFactory().post("/admin/")
    request.user = user
    SessionMiddleware(lambda r: None).process_request(request)
    MessageMiddleware(lambda r: None).process_request(request)
    request.session.save()
    return request


def test_invitation_link(project):
    invitation = Invitation.objects.create(email="a@example.com", project=project)
    link = invitation_link(invitation, "http://testserver/")
    assert link.endswith(f"/accounts/invite/{invitation.token}/")


def test_send_invitation_email(project):
    invitation = Invitation.objects.create(email="a@example.com", project=project)
    send_invitation_email(invitation, "http://testserver/")
    assert len(mail.outbox) == 1
    message = mail.outbox[0]
    assert message.to == ["a@example.com"]
    assert invitation.token in message.body


def test_invitation_admin_save_sends_email(project):
    admin = InvitationAdmin(Invitation, AdminSite())
    inviter = User.objects.create_user(email="admin@example.com", password="review-pass-1")
    request = _admin_request(inviter)
    invitation = Invitation(email="new@example.com", project=project, role=Role.AUTHOR)
    admin.save_model(request, invitation, form=None, change=False)
    assert invitation.pk is not None
    assert invitation.invited_by == inviter
    assert len(mail.outbox) == 1


def test_invitation_admin_resend_action(project):
    admin = InvitationAdmin(Invitation, AdminSite())
    inviter = User.objects.create_user(email="admin@example.com", password="review-pass-1")
    invitation = Invitation.objects.create(email="new@example.com", project=project)
    request = _admin_request(inviter)
    admin.resend_invitation_email(request, Invitation.objects.filter(pk=invitation.pk))
    assert len(mail.outbox) == 1


@pytest.mark.django_db
def test_user_creation_form_hashes_password():
    form = UserCreationForm(
        {
            "email": "new@example.com",
            "display_name": "New",
            "password1": "review-pass-9",
            "password2": "review-pass-9",
        }
    )
    assert form.is_valid(), form.errors
    user = form.save()
    assert user.check_password("review-pass-9")
    assert user.has_usable_password()


@pytest.mark.django_db
def test_user_creation_form_rejects_mismatch():
    form = UserCreationForm(
        {"email": "new@example.com", "password1": "review-pass-9", "password2": "different-9"}
    )
    assert not form.is_valid()
    assert "password2" in form.errors


@pytest.mark.django_db
def test_user_creation_form_rejects_weak_password():
    form = UserCreationForm({"email": "new@example.com", "password1": "1234", "password2": "1234"})
    assert not form.is_valid()


@pytest.mark.django_db
def test_user_change_form_instantiates():
    user = User.objects.create_user(email="a@example.com", password="review-pass-1")
    form = UserChangeForm(instance=user)
    assert "password" in form.fields


def test_login_page_has_forgot_link(client):
    response = client.get(reverse("login"))
    assert reverse("password_reset").encode() in response.content


@pytest.mark.django_db
def test_password_reset_uses_app_templates_not_admin(client):
    # Regression: django.contrib.admin ships registration/password_reset_*.html
    # and is earlier in INSTALLED_APPS, so app templates must be app-namespaced.
    response = client.get(reverse("password_reset"))
    assert response.status_code == 200
    rendered = {t.name for t in response.templates if t.name}
    assert "accounts/password_reset_form.html" in rendered
    assert "workbench/base.html" in rendered


@pytest.mark.django_db
def test_password_reset_sends_email(client):
    User.objects.create_user(email="member@example.com", password="review-pass-1")
    response = client.post(reverse("password_reset"), {"email": "member@example.com"})
    assert response.status_code == 302
    assert len(mail.outbox) == 1


@pytest.mark.django_db
def test_password_reset_confirm_sets_new_password(client):
    user = User.objects.create_user(email="member@example.com", password="review-pass-1")
    uid = urlsafe_base64_encode(force_bytes(user.pk))
    token = default_token_generator.make_token(user)
    start = client.get(reverse("password_reset_confirm", kwargs={"uidb64": uid, "token": token}))
    form_page = client.get(start.url)
    assert form_page.status_code == 200
    done = client.post(
        start.url, {"new_password1": "brand-new-pass-9", "new_password2": "brand-new-pass-9"}
    )
    assert done.status_code == 302
    user.refresh_from_db()
    assert user.check_password("brand-new-pass-9")


@pytest.mark.django_db
def test_doctor_reports_readiness():
    out = StringIO()
    call_command("doctor", stdout=out)
    output = out.getvalue()
    for label in ("Python", "Database", "Migrations", "Secret key", "Email", "Debug"):
        assert label in output


def test_doctor_handles_database_failure(monkeypatch):
    def boom(*args, **kwargs):
        raise OperationalError("unavailable")

    monkeypatch.setattr(connections[DEFAULT_DB_ALIAS], "cursor", boom)
    out = StringIO()
    call_command("doctor", stdout=out)
    assert "Database" in out.getvalue()
