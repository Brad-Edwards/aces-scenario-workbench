from __future__ import annotations

import secrets

from django.db import migrations, models
import django.db.models.deletion


def _move_invitations_to_scenarios(apps, schema_editor):
    Invitation = apps.get_model("accounts", "Invitation")
    Scenario = apps.get_model("workbench", "Scenario")

    scenarios_by_project: dict[int, list[object]] = {}
    for scenario in Scenario.objects.order_by("project_id", "id"):
        scenarios_by_project.setdefault(scenario.project_id, []).append(scenario)

    for invitation in list(Invitation.objects.select_related("project").order_by("id")):
        scenarios = scenarios_by_project.get(invitation.project_id, [])
        if not scenarios:
            continue
        invitation.scenario = scenarios[0]
        invitation.save(update_fields=["scenario"])
        for scenario in scenarios[1:]:
            Invitation.objects.create(
                email=invitation.email,
                scenario=scenario,
                project_id=invitation.project_id,
                role=invitation.role,
                token=secrets.token_urlsafe(32),
                invited_by_id=invitation.invited_by_id,
                created_at=invitation.created_at,
                accepted_at=invitation.accepted_at,
            )


class Migration(migrations.Migration):
    dependencies = [
        ("workbench", "0002_prepare_scenario_scope"),
        ("accounts", "0002_invitation"),
    ]

    operations = [
        migrations.AddField(
            model_name="invitation",
            name="scenario",
            field=models.ForeignKey(
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="invitations",
                to="workbench.scenario",
            ),
        ),
        migrations.RunPython(_move_invitations_to_scenarios, migrations.RunPython.noop),
        migrations.AlterField(
            model_name="invitation",
            name="scenario",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="invitations",
                to="workbench.scenario",
            ),
        ),
        migrations.RemoveField(
            model_name="invitation",
            name="project",
        ),
    ]
