from __future__ import annotations

from pathlib import Path
from typing import Any

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError, CommandParser
from django.utils.text import slugify

from ...ingest import ProjectionError, import_pack
from ...models import Membership, Role, Scenario


class Command(BaseCommand):
    help = (
        "Create or update a scenario and import a pack's ATLAS technique projection "
        "as an immutable revision."
    )

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument("path", help="Projection file, or a pack directory containing one.")
        parser.add_argument(
            "--slug",
            help="Scenario slug. Defaults to a slugified version of the input directory name.",
        )
        parser.add_argument("--name", help="Scenario display name.")
        parser.add_argument("--description", help="Scenario description.")
        parser.add_argument(
            "--grant-user",
            help="Email address to grant access to after syncing.",
        )
        parser.add_argument(
            "--role",
            choices=[role.value for role in Role],
            default=Role.AUTHOR,
            help="Role to assign with --grant-user. Defaults to author.",
        )

    def handle(self, *args: Any, **options: Any) -> None:
        source_path = Path(options["path"])
        slug = options["slug"] or slugify(source_path.name)
        if not slug:
            raise CommandError("Could not infer a scenario slug; pass --slug.")

        scenario, scenario_created = self._sync_scenario(slug, options)
        try:
            revision, revision_created = import_pack(scenario, source_path)
        except ProjectionError as exc:
            raise CommandError(str(exc)) from exc
        membership_result = self._grant_user(scenario, options)

        if scenario_created:
            self.stdout.write(self.style.SUCCESS(f"Created scenario {scenario.slug}."))
        else:
            self.stdout.write(f"Updated scenario {scenario.slug}.")

        if revision_created:
            self.stdout.write(
                self.style.SUCCESS(f"Imported revision {revision.pk} ({revision.mapping_id}).")
            )
        else:
            self.stdout.write(f"Already up to date (revision {revision.pk}).")
        implemented = revision.challenges.filter(implemented=True).count()
        planned = revision.challenges.filter(implemented=False).count()
        self.stdout.write(
            f"Synced {revision.challenges.count()} challenge contract(s) "
            f"({implemented} implemented, {planned} planned)."
        )

        if membership_result == "created":
            self.stdout.write("Granted scenario access.")
        elif membership_result == "updated":
            self.stdout.write("Updated scenario access.")
        elif membership_result == "unchanged":
            self.stdout.write("Scenario access already present.")

    def _sync_scenario(self, slug: str, options: dict[str, Any]) -> tuple[Scenario, bool]:
        scenario, created = Scenario.objects.get_or_create(
            slug=slug,
            defaults=self._create_defaults(slug, options),
        )
        if not created:
            update_fields = []
            if options["name"] is not None and scenario.name != options["name"]:
                scenario.name = options["name"]
                update_fields.append("name")
            if (
                options["description"] is not None
                and scenario.description != options["description"]
            ):
                scenario.description = options["description"]
                update_fields.append("description")
            if update_fields:
                scenario.save(update_fields=[*update_fields, "updated_at"])
        return scenario, created

    def _create_defaults(self, slug: str, options: dict[str, Any]) -> dict[str, str]:
        defaults = {
            "name": options["name"] or slug,
        }
        if options["description"] is not None:
            defaults["description"] = options["description"]
        return defaults

    def _grant_user(self, scenario: Scenario, options: dict[str, Any]) -> str | None:
        email = options["grant_user"]
        if not email:
            return None

        User = get_user_model()
        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist as exc:
            raise CommandError(f"No user with email '{email}'.") from exc

        membership, created = Membership.objects.get_or_create(
            scenario=scenario,
            user=user,
            defaults={"role": options["role"]},
        )
        if created:
            return "created"
        if membership.role != options["role"]:
            membership.role = options["role"]
            membership.save(update_fields=["role", "updated_at"])
            return "updated"
        return "unchanged"
