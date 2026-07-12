from __future__ import annotations

from pathlib import Path
from typing import Any

from django.core.management.base import BaseCommand, CommandError, CommandParser

from ...ingest import ProjectionError, import_projection, load_projection
from ...models import Scenario


class Command(BaseCommand):
    help = "Import an ACES scenario pack's ATLAS technique projection as a revision."

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument("path", help="Projection file, or a pack directory containing one.")
        parser.add_argument("--scenario", required=True, help="Target scenario slug.")

    def handle(self, *args: Any, **options: Any) -> None:
        try:
            scenario = Scenario.objects.get(slug=options["scenario"])
        except Scenario.DoesNotExist as exc:
            raise CommandError(f"No scenario with slug '{options['scenario']}'.") from exc

        try:
            data, _ = load_projection(Path(options["path"]))
        except ProjectionError as exc:
            raise CommandError(str(exc)) from exc

        revision, created = import_projection(scenario, data)
        if created:
            self.stdout.write(
                self.style.SUCCESS(f"Imported revision {revision.pk} ({revision.mapping_id}).")
            )
        else:
            self.stdout.write(f"Already up to date (revision {revision.pk}).")
