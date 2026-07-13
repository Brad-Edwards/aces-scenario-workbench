from __future__ import annotations

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
from django.utils.text import slugify


BAD_SCENARIO_LABELS = {"scenario under test"}
BAD_SCENARIO_SLUGS = {"scenario-under-test"}


def _clean_name(value: str, fallback: str = "Untitled scenario") -> str:
    value = (value or "").strip()
    if not value or value.lower() in BAD_SCENARIO_LABELS:
        return fallback
    return value


def _clean_slug(value: str, name: str) -> str:
    value = (value or "").strip()
    if not value or value in BAD_SCENARIO_SLUGS:
        value = slugify(_clean_name(name))
    return value or "scenario"


def _dedupe_slug(base: str, seen: set[str]) -> str:
    candidate = base
    suffix = 2
    while candidate in seen:
        candidate = f"{base}-{suffix}"
        suffix += 1
    seen.add(candidate)
    return candidate


def _project_scenarios(Project, Scenario):
    mapping = {}
    for project in Project.objects.order_by("id"):
        scenarios = list(Scenario.objects.filter(project=project).order_by("id"))
        if not scenarios:
            scenarios = [
                Scenario.objects.create(
                    project=project,
                    slug=_clean_slug(project.slug, project.name),
                    name=_clean_name(project.name),
                    description=project.description,
                )
            ]
        mapping[project.pk] = scenarios
    return mapping


def _prepare_scenario_scope(apps, schema_editor):
    Project = apps.get_model("workbench", "Project")
    Scenario = apps.get_model("workbench", "Scenario")
    Membership = apps.get_model("workbench", "Membership")
    ActivityEvent = apps.get_model("workbench", "ActivityEvent")

    scenario_by_project = _project_scenarios(Project, Scenario)

    for membership in list(Membership.objects.select_related("project").order_by("id")):
        scenarios = scenario_by_project[membership.project_id]
        membership.scenario = scenarios[0]
        membership.save(update_fields=["scenario"])
        for scenario in scenarios[1:]:
            Membership.objects.get_or_create(
                scenario=scenario,
                user_id=membership.user_id,
                defaults={
                    "project_id": membership.project_id,
                    "role": membership.role,
                },
            )

    for event in list(ActivityEvent.objects.select_related("project").order_by("id")):
        scenarios = scenario_by_project[event.project_id]
        event.scenario = scenarios[0]
        event.save(update_fields=["scenario"])
        for scenario in scenarios[1:]:
            ActivityEvent.objects.create(
                scenario=scenario,
                project_id=event.project_id,
                actor_id=event.actor_id,
                verb=event.verb,
                object_type=event.object_type,
                object_stable_id=event.object_stable_id,
                metadata=event.metadata,
                created_at=event.created_at,
            )

    seen: set[str] = set()
    for scenario in Scenario.objects.select_related("project").order_by("project_id", "id"):
        scenario.name = _clean_name(scenario.name)
        base = _clean_slug(scenario.slug, scenario.name)
        scenario.slug = _dedupe_slug(base, seen)
        scenario.save(update_fields=["name", "slug"])


class Migration(migrations.Migration):
    dependencies = [
        ("workbench", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="membership",
            name="scenario",
            field=models.ForeignKey(
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="memberships",
                to="workbench.scenario",
            ),
        ),
        migrations.AddField(
            model_name="activityevent",
            name="scenario",
            field=models.ForeignKey(
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="activity",
                to="workbench.scenario",
            ),
        ),
        migrations.RemoveConstraint(
            model_name="membership",
            name="unique_project_member",
        ),
        migrations.RemoveConstraint(
            model_name="scenario",
            name="unique_scenario_slug",
        ),
        migrations.RunPython(_prepare_scenario_scope, migrations.RunPython.noop),
        migrations.AlterField(
            model_name="scenario",
            name="slug",
            field=models.SlugField(unique=True),
        ),
        migrations.AlterField(
            model_name="membership",
            name="scenario",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="memberships",
                to="workbench.scenario",
            ),
        ),
        migrations.AlterField(
            model_name="activityevent",
            name="scenario",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="activity",
                to="workbench.scenario",
            ),
        ),
        migrations.RemoveField(
            model_name="membership",
            name="project",
        ),
        migrations.RemoveField(
            model_name="activityevent",
            name="project",
        ),
        migrations.AlterModelOptions(
            name="membership",
            options={"ordering": ["scenario", "user"]},
        ),
        migrations.AddConstraint(
            model_name="membership",
            constraint=models.UniqueConstraint(
                fields=("scenario", "user"), name="unique_scenario_member"
            ),
        ),
    ]
