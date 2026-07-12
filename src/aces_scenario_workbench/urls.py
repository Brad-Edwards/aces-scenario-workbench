"""Root URL configuration."""

from __future__ import annotations

from django.conf import settings
from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path(settings.ADMIN_PATH, admin.site.urls),
    path("accounts/", include("aces_scenario_workbench.accounts.urls")),
    path("", include("aces_scenario_workbench.workbench.urls")),
]
