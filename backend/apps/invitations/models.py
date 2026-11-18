"""Invitation tokens are stored only as digests, never as bearer secrets."""

import uuid

from django.conf import settings
from django.db import models
from django.db.models import Q
from django.utils import timezone


class Invitation(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        ACCEPTED = "accepted", "Accepted"
        REJECTED = "rejected", "Rejected"
        REVOKED = "revoked", "Revoked"
        EXPIRED = "expired", "Expired"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    fund = models.ForeignKey(
        "funds.Fund", on_delete=models.PROTECT, related_name="invitations"
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="issued_invitations"
    )
    # HMAC of normalized phone scoped to the fund. Never disclose in public APIs.
    target_fingerprint = models.CharField(max_length=64)
    # SHA-256 of an independently generated 256-bit random bearer code.
    token_digest = models.CharField(max_length=64, unique=True)
    status = models.CharField(
        max_length=8, choices=Status.choices, default=Status.PENDING
    )
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    responded_at = models.DateTimeField(null=True, blank=True)
    responded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="responded_invitations",
    )

    class Meta:
        ordering = ("-created_at", "-id")
        constraints = (
            models.UniqueConstraint(
                fields=("fund", "target_fingerprint"),
                condition=Q(status="pending"),
                name="unique_pending_invite_fund_target",
            ),
            models.CheckConstraint(
                condition=Q(
                    status__in=["pending", "accepted", "rejected", "revoked", "expired"]
                ),
                name="invitation_valid_status",
            ),
        )
        indexes = (
            models.Index(fields=("fund", "created_at"), name="invite_fund_created_idx"),
        )

    @property
    def is_expired(self):
        return self.status == self.Status.EXPIRED or (
            self.status == self.Status.PENDING and self.expires_at <= timezone.now()
        )

    def __str__(self):
        return f"Invitation {self.pk} ({self.status})"
