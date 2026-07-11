from __future__ import annotations

from django.apps import AppConfig


class WorkbenchConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "aces_scenario_workbench.workbench"
    label = "workbench"
    verbose_name = "Workbench"
