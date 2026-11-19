"""Fund, fund-scoped membership, and a minimal auditable event trail."""

import uuid

from django.conf import settings
from django.db import models
from django.db.models import Q


class Fund(models.Model):
    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        ACTIVE = "active", "Active"
        PAUSED = "paused", "Paused"
        COMPLETED = "completed", "Completed"
        CANCELLED = "cancelled", "Cancelled"

    class LotteryEligibilityPolicy(models.TextChoices):
        FULLY_SETTLED = "fully_settled", "Fully settled"
        ALLOW_OUTSTANDING = "allow_outstanding", "Allow outstanding"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=120)
    description = models.TextField(blank=True)
    lottery_eligibility_policy = models.CharField(
        max_length=24,
        choices=LotteryEligibilityPolicy.choices,
        default=LotteryEligibilityPolicy.FULLY_SETTLED,
    )
    target_share_count = models.PositiveIntegerField(null=True, blank=True)
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.DRAFT)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name="created_funds",
        on_delete=models.PROTECT,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("-created_at", "-id")
        constraints = (
            models.CheckConstraint(condition=~Q(name=""), name="fund_name_not_empty"),
            models.CheckConstraint(
                condition=Q(lottery_eligibility_policy__in=["fully_settled", "allow_outstanding"]),
                name="fund_valid_lottery_eligibility_policy",
            ),
            models.CheckConstraint(
                condition=Q(target_share_count__isnull=True) | Q(target_share_count__gte=1),
                name="fund_target_shares_positive",
            ),
            models.CheckConstraint(
                condition=Q(status__in=["draft", "active", "paused", "completed", "cancelled"]),
                name="fund_valid_status",
            ),
        )

    def __str__(self):
        return self.name


class FundMembership(models.Model):
    class Role(models.TextChoices):
        MANAGER = "manager", "Manager"
        MEMBER = "member", "Member"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    fund = models.ForeignKey(Fund, related_name="memberships", on_delete=models.PROTECT)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name="fund_memberships",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
    )
    guest_name = models.CharField(max_length=120, blank=True, default="")
    role = models.CharField(max_length=8, choices=Role.choices, default=Role.MEMBER)
    is_active = models.BooleanField(default=True)
    joined_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("joined_at", "id")
        constraints = (
            models.UniqueConstraint(fields=("fund", "user"), name="unique_user_per_fund"),
            models.CheckConstraint(
                condition=(
                    Q(user__isnull=False, guest_name="")
                    | (Q(user__isnull=True) & ~Q(guest_name=""))
                ),
                name="fund_membership_guest_identity",
            ),
            models.CheckConstraint(
                condition=~Q(role="manager") | Q(user__isnull=False),
                name="fund_manager_requires_user",
            ),
            models.UniqueConstraint(
                fields=("fund",),
                condition=Q(role="manager", is_active=True),
                name="unique_active_manager_per_fund",
            ),
            models.CheckConstraint(
                condition=Q(role__in=["manager", "member"]),
                name="fund_membership_valid_role",
            ),
        )

    def __str__(self):
        identity = self.user_id if self.user_id else f"guest: {self.guest_name}"
        return f"{self.fund_id}: {identity} ({self.role})"


class GuestSponsorship(models.Model):
    """Accepted sponsor of a guest; not an installment or financial ledger."""

    class Status(models.TextChoices):
        PENDING_SPONSOR = "pending_sponsor", "Pending sponsor consent"
        PENDING_MANAGER = "pending_manager", "Pending manager approval"
        ACTIVE = "active", "Active"
        REJECTED = "rejected", "Rejected"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    request_id = models.UUIDField(unique=True)
    fund = models.ForeignKey(
        Fund, related_name="guest_sponsorships", on_delete=models.PROTECT
    )
    guest_membership = models.OneToOneField(
        FundMembership, related_name="guest_sponsorship", on_delete=models.PROTECT
    )
    sponsor_membership = models.ForeignKey(
        FundMembership, related_name="sponsored_guest_requests", on_delete=models.PROTECT
    )
    requested_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name="guest_sponsorship_requests",
        on_delete=models.PROTECT,
    )
    is_legacy_attachment = models.BooleanField(default=False)
    status = models.CharField(max_length=20, choices=Status.choices)
    sponsor_accepted_at = models.DateTimeField(null=True, blank=True)
    approved_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("-created_at", "-id")
        constraints = (
            models.CheckConstraint(
                condition=Q(status__in=["pending_sponsor", "pending_manager", "active", "rejected"]),
                name="guest_sponsorship_valid_status",
            ),
            models.CheckConstraint(
                condition=~Q(status="active") | (
                    Q(sponsor_accepted_at__isnull=False) & Q(approved_at__isnull=False)
                ),
                name="guest_active_sponsorship_approved",
            ),
        )

    def __str__(self):
        return f"Guest sponsorship {self.id}: {self.status}"


class AuditLog(models.Model):
    """Non-user-editable application event; not a tamper-proof ledger."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    fund = models.ForeignKey(Fund, related_name="audit_events", on_delete=models.PROTECT)
    actor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    action = models.CharField(max_length=60)
    target_id = models.UUIDField()
    changed_fields = models.JSONField(default=list)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("-created_at", "-id")

    def __str__(self):
        return f"{self.action} @ {self.fund_id}"
