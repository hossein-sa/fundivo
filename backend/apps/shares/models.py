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
