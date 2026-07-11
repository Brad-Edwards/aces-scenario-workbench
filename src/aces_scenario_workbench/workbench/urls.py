from __future__ import annotations

from django.urls import path

from . import views

urlpatterns = [
    path("", views.landing, name="landing"),
    path("healthz", views.healthz, name="healthz"),
    path("dashboard/", views.dashboard, name="dashboard"),
]
