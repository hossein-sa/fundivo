"""Sponsorship consent records; legacy guests are deliberately NOT auto-enrolled."""

import uuid

from django.conf import settings
from django.db import migrations, models
from django.db.models import Q
from django.db.models.deletion import PROTECT


class Migration(migrations.Migration):
    dependencies = [
        ("funds", "0004_fund_lottery_eligibility_policy"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="GuestSponsorship",
            fields=[
                ("id", models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False, serialize=False)),
                ("request_id", models.UUIDField(unique=True)),
                ("is_legacy_attachment", models.BooleanField(default=False)),
                ("status", models.CharField(
                    max_length=20,
                    choices=[
                        ("pending_sponsor", "Pending sponsor consent"),
                        ("pending_manager", "Pending manager approval"),
                        ("active", "Active"),
                        ("rejected", "Rejected"),
                    ],
                )),
                ("sponsor_accepted_at", models.DateTimeField(null=True, blank=True)),
                ("approved_at", models.DateTimeField(null=True, blank=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("fund", models.ForeignKey(to="funds.fund", on_delete=PROTECT, related_name="guest_sponsorships")),
                ("guest_membership", models.OneToOneField(to="funds.fundmembership", on_delete=PROTECT, related_name="guest_sponsorship")),
                ("sponsor_membership", models.ForeignKey(to="funds.fundmembership", on_delete=PROTECT, related_name="sponsored_guest_requests")),
                ("requested_by", models.ForeignKey(to=settings.AUTH_USER_MODEL, on_delete=PROTECT, related_name="guest_sponsorship_requests")),
            ],
            options={"ordering": ("-created_at", "-id")},
        ),
        migrations.AddConstraint(
            model_name="guestsponsorship",
            constraint=models.CheckConstraint(
                condition=Q(status__in=["pending_sponsor", "pending_manager", "active", "rejected"]),
                name="guest_sponsorship_valid_status",
            ),
        ),
        migrations.AddConstraint(
            model_name="guestsponsorship",
            constraint=models.CheckConstraint(
                condition=~Q(status="active") | (Q(sponsor_accepted_at__isnull=False) & Q(approved_at__isnull=False)),
                name="guest_active_sponsorship_approved",
            ),
        ),
    ]
