from __future__ import annotations

from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.urls import reverse

from .models import Invitation


def invitation_link(invitation: Invitation, base_url: str) -> str:
    path = reverse("invite-accept", args=[invitation.token])
    return base_url.rstrip("/") + path


def send_invitation_email(invitation: Invitation, base_url: str) -> None:
    """Email the invitation accept link to the invited address."""
    link = invitation_link(invitation, base_url)
    subject = "You have been invited to the ACES Scenario Workbench"
    body = render_to_string(
        "accounts/email/invitation.txt",
        {"invitation": invitation, "link": link},
    )
    send_mail(subject, body, None, [invitation.email])
