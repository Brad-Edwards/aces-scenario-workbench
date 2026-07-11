from __future__ import annotations

from django.urls import path

from . import api, views

urlpatterns = [
    path("", views.landing, name="landing"),
    path("healthz", views.healthz, name="healthz"),
    path("dashboard/", views.dashboard, name="dashboard"),
    path(
        "api/projects/<slug:slug>/revisions",
        api.upload_revision,
        name="api-upload-revision",
    ),
]
