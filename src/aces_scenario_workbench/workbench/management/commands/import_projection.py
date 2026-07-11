from __future__ import annotations

from pathlib import Path
from typing import Any

from django.core.management.base import BaseCommand, CommandError, CommandParser

from ...ingest import ProjectionError, import_projection, load_projection
from ...models import Project


class Command(BaseCommand):
    help = "Import an ACES scenario pack's ATLAS technique projection as a revision."

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument("path", help="Projection file, or a pack directory containing one.")
        parser.add_argument("--project", required=True, help="Target project slug.")

    def handle(self, *args: Any, **options: Any) -> None:
        try:
            project = Project.objects.get(slug=options["project"])
        except Project.DoesNotExist as exc:
            raise CommandError(f"No project with slug '{options['project']}'.") from exc

        try:
            data, _ = load_projection(Path(options["path"]))
        except ProjectionError as exc:
            raise CommandError(str(exc)) from exc

        revision, created = import_projection(project, data)
        if created:
            self.stdout.write(
                self.style.SUCCESS(f"Imported revision {revision.pk} ({revision.mapping_id}).")
            )
        else:
            self.stdout.write(f"Already up to date (revision {revision.pk}).")
