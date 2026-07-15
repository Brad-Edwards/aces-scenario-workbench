from __future__ import annotations

from typing import Any

from django.contrib import messages
from django.contrib.auth import get_user_model, login, logout, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import PasswordChangeForm
from django.http import HttpRequest, HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_GET, require_http_methods
from django_ratelimit.decorators import ratelimit

from .forms import AcceptInvitationForm
from .models import Invitation

User = get_user_model()


def _apply_invitation(
    request: HttpRequest,
    invitation: Invitation,
    existing: User | None,
    form: AcceptInvitationForm | None,
) -> HttpResponse | None:
    """Perform an invitation acceptance; returns a redirect, or None if invalid."""
    if existing is not None:
        invitation.accept(existing)
        messages.success(request, "You have been added to the scenario. Please sign in.")
        return redirect("login")
    if form is not None and form.is_valid():
        user = User(
            email=invitation.email,
            display_name=form.cleaned_data["display_name"],
            is_active=True,
        )
        user.set_password(form.cleaned_data["password1"])
        user.save()
        invitation.accept(user)
        # Multiple auth backends are configured (django-axes sits in front of the
        # model backend), so the backend must be named for a manual login.
        login(request, user, backend="django.contrib.auth.backends.ModelBackend")
        return redirect("spa-app")
    return None


@ratelimit(key="ip", rate="10/h", method="POST", block=True)
@require_http_methods(["GET", "POST"])
def invite_accept(request: HttpRequest, token: str) -> HttpResponse:
    """Accept a scenario invitation, registering a new account when needed."""
    invitation = get_object_or_404(Invitation, token=token)
    if not invitation.is_pending():
        return render(
            request, "accounts/invite_invalid.html", {"invitation": invitation}, status=410
        )
    existing = User.objects.filter(email__iexact=invitation.email).first()
    form = AcceptInvitationForm(request.POST or None) if existing is None else None
    if request.method == "POST":
        response = _apply_invitation(request, invitation, existing, form)
        if response is not None:
            return response
    return render(
        request,
        "accounts/invite_accept.html",
        {"form": form, "invitation": invitation, "existing": existing is not None},
    )


def _export_payload(user: User) -> dict[str, Any]:
    return {
        "email": user.email,
        "display_name": user.display_name,
        "date_joined": user.date_joined.isoformat(),
        "memberships": [
            {"scenario": m.scenario.slug, "role": m.role}
            for m in user.memberships.select_related("scenario")
        ],
        "comments": [
            {
                "object_type": c.object_type,
                "object_stable_id": c.object_stable_id,
                "body": c.body,
                "created_at": c.created_at.isoformat(),
            }
            for c in user.comments.all()
        ],
        "decisions": [
            {
                "object_type": d.object_type,
                "object_stable_id": d.object_stable_id,
                "decision": d.decision,
                "rationale": d.rationale,
                "created_at": d.created_at.isoformat(),
            }
            for d in user.decisions.all()
        ],
    }


@login_required
@require_http_methods(["GET", "POST"])
def account(request: HttpRequest) -> HttpResponse:
    """The signed-in user's profile and account controls."""
    password_form = PasswordChangeForm(request.user, request.POST or None)
    if request.method == "POST" and password_form.is_valid():
        user = password_form.save()
        update_session_auth_hash(request, user)
        messages.success(request, "Your password has been changed.")
        return redirect("account")
    return render(request, "accounts/account.html", {"password_form": password_form})


@login_required
@require_GET
def account_export(request: HttpRequest) -> JsonResponse:
    """Download the signed-in user's personal data (GDPR access)."""
    response = JsonResponse(_export_payload(request.user), json_dumps_params={"indent": 2})
    response["Content-Disposition"] = 'attachment; filename="aces-workbench-account.json"'
    return response


@login_required
@require_http_methods(["GET", "POST"])
def account_delete(request: HttpRequest) -> HttpResponse:
    """Confirm and delete the signed-in user's account and personal content."""
    if request.method == "GET":
        return render(request, "accounts/account_confirm_delete.html")
    if request.POST.get("confirm_email", "").strip().lower() != request.user.email.lower():
        messages.error(request, "Enter your email address to confirm account deletion.")
        return render(request, "accounts/account_confirm_delete.html", status=400)
    user = request.user
    logout(request)
    user.delete()
    return redirect("landing")
