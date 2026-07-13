from __future__ import annotations

from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("accounts", "0003_invitation_scenario_scope"),
        ("workbench", "0002_prepare_scenario_scope"),
    ]

    operations = [
        migrations.AddField(
            model_name="scenario",
            name="members",
            field=models.ManyToManyField(
                related_name="scenarios",
                through="workbench.Membership",
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.RemoveField(
            model_name="scenario",
            name="project",
        ),
        migrations.AlterModelOptions(
            name="scenario",
            options={"ordering": ["name"]},
        ),
        migrations.DeleteModel(
            name="Project",
        ),
    ]
