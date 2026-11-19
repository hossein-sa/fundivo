"""Concurrency-safe and retry-safe draft share allocation."""

from django.db import transaction
from django.shortcuts import get_object_or_404
from rest_framework.exceptions import PermissionDenied

from apps.funds.models import AuditLog, Fund, FundMembership
from apps.funds.services import FundConflict

from .models import Share, ShareParticipation


@transaction.atomic
def allocate_shares(*, fund_id, actor, membership_id, count, allocation_id):
    """Lock the fund to serialize allocations and prevent capacity oversubscription.

    A repeated allocation_id returns the original shares only when its input matches.
    The client must send a fresh UUID for each genuinely new allocation operation.
    """
    fund = Fund.objects.select_for_update().get(pk=fund_id)
    is_manager = FundMembership.objects.filter(
        fund=fund,
        user=actor,
        is_active=True,
        role=FundMembership.Role.MANAGER,
    ).exists()
    if not is_manager:
        raise PermissionDenied("Only the fund manager may allocate shares.")

    membership = get_object_or_404(
        FundMembership.objects.filter(fund=fund, is_active=True), pk=membership_id
    )
    existing = list(
        Share.objects.filter(fund=fund, allocation_id=allocation_id).order_by("number")
    )
    if existing:
        if len(existing) != count or any(share.membership_id != membership.pk for share in existing):
            raise FundConflict("Allocation ID was already used for different input.")
        return existing, False

    if fund.status != Fund.Status.DRAFT:
        raise FundConflict("Shares can only be allocated while a fund is in draft.")
    if fund.target_share_count is None:
        raise FundConflict("Set the fund's target_share_count before allocating shares.")

    # Fund row lock ensures concurrent calls cannot both pass the capacity check.
    existing_count = Share.objects.filter(fund=fund).count()
    if existing_count + count > fund.target_share_count:
        raise FundConflict("Share allocation would exceed the fund's capacity.")
    last_number = (
        Share.objects.filter(fund=fund).order_by("-number")
        .values_list("number", flat=True).first()
        or 0
    )
    new_shares = [
        Share(
            fund=fund,
            membership=membership,
            number=last_number + position,
            allocation_id=allocation_id,
        )
        for position in range(1, count + 1)
    ]
    Share.objects.bulk_create(new_shares)
    # Every new individually allocated share begins with a full 12/12 holding.
    ShareParticipation.objects.bulk_create(
        [ShareParticipation(share=share, membership=membership, units=12)
         for share in new_shares]
    )
    AuditLog.objects.create(
        fund=fund,
        actor=actor,
        action="shares.allocated",
        target_id=allocation_id,
        changed_fields=["membership_id", "count"],
    )
    return new_shares, True
