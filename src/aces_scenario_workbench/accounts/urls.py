from __future__ import annotations

from django.contrib.auth import views as auth_views
from django.urls import path

from . import views

urlpatterns = [
    path(
        "login/",
        auth_views.LoginView.as_view(template_name="registration/login.html"),
        name="login",
    ),
    path("logout/", auth_views.LogoutView.as_view(), name="logout"),
    path("invite/<str:token>/", views.invite_accept, name="invite-accept"),
    path("me/", views.account, name="account"),
    path("me/export/", views.account_export, name="account-export"),
    path("me/delete/", views.account_delete, name="account-delete"),
]
