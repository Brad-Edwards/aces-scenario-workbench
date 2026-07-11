from __future__ import annotations

from django.contrib import messages
from django.contrib.auth import get_user_model, login
from django.http import HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_http_methods

from .forms import AcceptInvitationForm
from .models import Invitation

User = get_user_model()


@require_http_methods(["GET", "POST"])
def invite_accept(request: HttpRequest, token: str) -> HttpResponse:
    """Accept a project invitation, registering a new account when needed."""
    invitation = get_object_or_404(Invitation, token=token)
    if not invitation.is_pending():
        return render(
            request, "accounts/invite_invalid.html", {"invitation": invitation}, status=410
        )

    existing = User.objects.filter(email__iexact=invitation.email).first()

    if request.method == "POST":
        if existing is not None:
            invitation.accept(existing)
            messages.success(request, "You have been added to the project. Please sign in.")
            return redirect("login")
        form = AcceptInvitationForm(request.POST)
        if form.is_valid():
            user = User(
                email=invitation.email,
                display_name=form.cleaned_data["display_name"],
                is_active=True,
            )
            user.set_password(form.cleaned_data["password1"])
            user.save()
            invitation.accept(user)
            login(request, user)
            return redirect("dashboard")
    else:
        form = None if existing is not None else AcceptInvitationForm()

    return render(
        request,
        "accounts/invite_accept.html",
        {"form": form, "invitation": invitation, "existing": existing is not None},
    )
