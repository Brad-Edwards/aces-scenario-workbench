from __future__ import annotations

from django.apps import AppConfig


class AccountsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "aces_scenario_workbench.accounts"
    label = "accounts"
    verbose_name = "Accounts"
