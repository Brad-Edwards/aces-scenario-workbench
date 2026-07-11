from __future__ import annotations

import sys
from typing import Any

from django.conf import settings
from django.core.management.base import BaseCommand
from django.db import DEFAULT_DB_ALIAS, connections
from django.db.migrations.executor import MigrationExecutor
from django.db.utils import OperationalError


class Command(BaseCommand):
    help = "Report configuration and readiness of the workbench."

    def _report(self, name: str, value: str, ok: bool) -> None:
        marker = "OK  " if ok else "!!  "
        style = self.style.SUCCESS if ok else self.style.WARNING
        self.stdout.write(style(f"{marker}{name}: {value}"))

    def _database_ok(self) -> bool:
        try:
            connections[DEFAULT_DB_ALIAS].cursor()
        except OperationalError:
            return False
        return True

    def _report_migrations(self) -> None:
        executor = MigrationExecutor(connections[DEFAULT_DB_ALIAS])
        pending = executor.migration_plan(executor.loader.graph.leaf_nodes())
        message = "up to date" if not pending else f"{len(pending)} unapplied"
        self._report("Migrations", message, not pending)

    def handle(self, *args: Any, **options: Any) -> None:
        python_version = ".".join(str(part) for part in sys.version_info[:3])
        self._report("Python", python_version, sys.version_info >= (3, 12))

        database_ok = self._database_ok()
        self._report("Database", settings.DATABASES["default"]["ENGINE"], database_ok)
        if database_ok:
            self._report_migrations()

        key_message = (
            "configured"
            if not settings.SECRET_KEY_IS_EPHEMERAL
            else "ephemeral — set ACES_WORKBENCH_SECRET_KEY"
        )
        self._report("Secret key", key_message, not settings.SECRET_KEY_IS_EPHEMERAL)

        smtp = settings.EMAIL_BACKEND.endswith("smtp.EmailBackend")
        self._report("Email", "SMTP" if smtp else "console (no delivery)", smtp)
        self._report("Debug", str(settings.DEBUG), not settings.DEBUG)
