from __future__ import annotations

from pathlib import Path
from typing import Any

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError, CommandParser
from django.utils.text import slugify

from ...ingest import ProjectionError, import_pack, load_pack_metadata
from ...models import Membership, Role, Scenario


class Command(BaseCommand):
    help = "Create or update a scenario and import SDL-first pack content as an immutable revision."

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument(
            "path", help="Pack directory containing SDL modules or legacy projection files."
        )
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
        options = self._with_pack_metadata(source_path, options)
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

    def _with_pack_metadata(self, source_path: Path, options: dict[str, Any]) -> dict[str, Any]:
        metadata = load_pack_metadata(source_path)
        resolved = dict(options)
        if resolved["name"] is None and isinstance(metadata.get("title"), str):
            resolved["name"] = metadata["title"]
        if resolved["description"] is None and isinstance(metadata.get("description"), str):
            resolved["description"] = metadata["description"]
        return resolved

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
        status = None

        if email:
            user_model = get_user_model()
            try:
                user = user_model.objects.get(email=email)
            except user_model.DoesNotExist as exc:
                raise CommandError(f"No user with email '{email}'.") from exc
            status = self._sync_membership(scenario, user, options["role"])

        return status

    def _sync_membership(self, scenario: Scenario, user: object, role: str) -> str:
        membership, created = Membership.objects.get_or_create(
            scenario=scenario,
            user=user,
            defaults={"role": role},
        )
        status = "unchanged"
        if created:
            status = "created"
        elif membership.role != role:
            membership.role = role
            membership.save(update_fields=["role", "updated_at"])
            status = "updated"
        return status
