"""Add the draft-configurable lottery eligibility rule (not applied until lottery phase)."""

from django.db import migrations, models
from django.db.models import Q


class Migration(migrations.Migration):
    dependencies = [
        ("funds", "0003_fundmembership_guest_name_alter_fundmembership_user_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="fund",
            name="lottery_eligibility_policy",
            field=models.CharField(
                choices=[
                    ("fully_settled", "Fully settled"),
                    ("allow_outstanding", "Allow outstanding"),
                ],
                default="fully_settled",
                max_length=24,
            ),
        ),
        migrations.AddConstraint(
            model_name="fund",
            constraint=models.CheckConstraint(
                condition=Q(lottery_eligibility_policy__in=["fully_settled", "allow_outstanding"]),
                name="fund_valid_lottery_eligibility_policy",
            ),
        ),
    ]
