"""A Share is one distinct participation unit owned by a fund membership."""

import uuid

from django.db import models
from django.db.models import Q


class Share(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    fund = models.ForeignKey("funds.Fund", on_delete=models.PROTECT, related_name="shares")
    membership = models.ForeignKey(
        "funds.FundMembership", on_delete=models.PROTECT, related_name="shares"
    )
    number = models.PositiveIntegerField()
    # Same UUID for all shares from one client request; enables safe retries.
    allocation_id = models.UUIDField()
    # Set once when a draft whole share becomes a shared participation proposal.
    participation_revision_id = models.UUIDField(null=True, blank=True, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("number", "id")
        constraints = (
            models.UniqueConstraint(
                fields=("fund", "number"), name="unique_share_number_per_fund"
            ),
            models.CheckConstraint(condition=Q(number__gte=1), name="share_number_positive"),
        )
        indexes = (
            models.Index(fields=("fund", "allocation_id"), name="share_fund_alloc_idx"),
        )

    def __str__(self):
        return f"Share {self.number} of fund {self.fund_id}"


class ShareParticipation(models.Model):
    """Current fractional participation. Exactly 12 units form one whole share.

    The sum is validated atomically in services; PostgreSQL enforces only row
    bounds and uniqueness. All rows are draft proposals pending consent policy.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    share = models.ForeignKey(
        Share, related_name="participations", on_delete=models.PROTECT
    )
    membership = models.ForeignKey(
        "funds.FundMembership", related_name="share_participations", on_delete=models.PROTECT
    )
    units = models.PositiveSmallIntegerField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("membership_id",)
        constraints = (
            models.UniqueConstraint(
                fields=("share", "membership"),
                name="unique_share_participation_membership",
            ),
            models.CheckConstraint(
                condition=Q(units__gte=1, units__lte=12),
                name="share_participation_units_1_12",
            ),
        )

    def __str__(self):
        return f"{self.membership_id}: {self.units}/12 of {self.share_id}"
