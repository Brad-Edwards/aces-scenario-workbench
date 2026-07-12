from __future__ import annotations

from django.contrib.auth import views as auth_views
from django.urls import path
from django_ratelimit.decorators import ratelimit

from . import views

# Throttle password-reset requests by IP so the endpoint cannot be used to flood
# an address with reset mail. Only the POST (email request) is limited.
password_reset_view = ratelimit(key="ip", rate="5/h", method="POST", block=True)(
    auth_views.PasswordResetView.as_view(
        template_name="accounts/password_reset_form.html",
        email_template_name="accounts/password_reset_email.html",
        subject_template_name="accounts/password_reset_subject.txt",
    )
)

urlpatterns = [
    path(
        "login/",
        auth_views.LoginView.as_view(template_name="registration/login.html"),
        name="login",
    ),
    path("logout/", auth_views.LogoutView.as_view(), name="logout"),
    path("password-reset/", password_reset_view, name="password_reset"),
    path(
        "password-reset/done/",
        auth_views.PasswordResetDoneView.as_view(template_name="accounts/password_reset_done.html"),
        name="password_reset_done",
    ),
    path(
        "reset/<uidb64>/<token>/",
        auth_views.PasswordResetConfirmView.as_view(
            template_name="accounts/password_reset_confirm.html"
        ),
        name="password_reset_confirm",
    ),
    path(
        "reset/done/",
        auth_views.PasswordResetCompleteView.as_view(
            template_name="accounts/password_reset_complete.html"
        ),
        name="password_reset_complete",
    ),
    path("invite/<str:token>/", views.invite_accept, name="invite-accept"),
    path("me/", views.account, name="account"),
    path("me/export/", views.account_export, name="account-export"),
    path("me/delete/", views.account_delete, name="account-delete"),
]
