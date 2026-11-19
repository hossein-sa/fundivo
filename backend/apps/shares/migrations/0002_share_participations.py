"""Schema + data backfill for all preexisting individual/guest shares."""

import uuid

from django.db import migrations, models
from django.db.models import Q
from django.db.models.deletion import PROTECT


def backfill_initial_participations(apps, schema_editor):
    Share = apps.get_model("shares", "Share")
    ShareParticipation = apps.get_model("shares", "ShareParticipation")
    database = schema_editor.connection.alias
    batch = []
    for share in Share.objects.using(database).all().iterator(chunk_size=500):
        batch.append(
            ShareParticipation(
                share_id=share.pk,
                membership_id=share.membership_id,
                units=12,
            )
        )
        if len(batch) >= 500:
            ShareParticipation.objects.using(database).bulk_create(batch, batch_size=500)
            batch.clear()
    if batch:
        ShareParticipation.objects.using(database).bulk_create(batch, batch_size=500)


class Migration(migrations.Migration):
    dependencies = [
        ("funds", "0004_fund_lottery_eligibility_policy"),
        ("shares", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="share",
            name="participation_revision_id",
            field=models.UUIDField(blank=True, null=True, unique=True),
        ),
        migrations.CreateModel(
            name="ShareParticipation",
            fields=[
                ("id", models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False, serialize=False)),
                ("units", models.PositiveSmallIntegerField()),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("share", models.ForeignKey(on_delete=PROTECT, related_name="participations", to="shares.share")),
                ("membership", models.ForeignKey(on_delete=PROTECT, related_name="share_participations", to="funds.fundmembership")),
            ],
            options={"ordering": ("membership_id",)},
        ),
        migrations.AddConstraint(
            model_name="shareparticipation",
            constraint=models.UniqueConstraint(
                fields=("share", "membership"), name="unique_share_participation_membership"
            ),
        ),
        migrations.AddConstraint(
            model_name="shareparticipation",
            constraint=models.CheckConstraint(
                condition=Q(units__gte=1, units__lte=12),
                name="share_participation_units_1_12",
            ),
        ),
        migrations.RunPython(backfill_initial_participations, migrations.RunPython.noop),
    ]
