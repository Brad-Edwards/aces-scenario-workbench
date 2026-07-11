"""Root URL configuration."""

from __future__ import annotations

from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", include("aces_scenario_workbench.workbench.urls")),
]
