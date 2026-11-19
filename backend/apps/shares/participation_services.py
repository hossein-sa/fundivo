"""Atomic, one-time draft co-participation proposals (not financial obligations)."""

from django.db import transaction
from django.shortcuts import get_object_or_404
from rest_framework.exceptions import PermissionDenied, ValidationError

from apps.funds.models import AuditLog, Fund, FundMembership
from apps.funds.services import FundConflict

from .models import Share, ShareParticipation


@transaction.atomic
def propose_shared_participation(*, fund_id, share_id, actor, request_id, participants):
    """Convert one original 12-unit holding into one immutable draft split.

    The existing Share.membership is the *original allottee*, not the current
    ownership authority. ShareParticipation is the ownership authority.
    No installments or legally binding liabilities are created here.
    """
    fund = get_object_or_404(Fund.objects.select_for_update(), pk=fund_id)
    is_manager = FundMembership.objects.filter(
        fund=fund,
        user=actor,
        role=FundMembership.Role.MANAGER,
        is_active=True,
    ).exists()
    if not is_manager:
        raise PermissionDenied("Only the active fund manager may propose a split.")
    if fund.status != Fund.Status.DRAFT:
        raise FundConflict("Shares can only be split while the fund is in draft.")

    share = get_object_or_404(
        Share.objects.select_for_update().filter(fund=fund), pk=share_id
    )
    current = list(ShareParticipation.objects.filter(share=share).order_by("membership_id"))
    desired = {row["membership_id"]: row["units"] for row in participants}
    if len(desired) != len(participants) or sum(desired.values()) != 12 or len(desired) < 2:
        raise ValidationError("A split needs unique memberships whose units total 12.")

    if share.participation_revision_id is not None:
        original = {row.membership_id: row.units for row in current}
        if share.participation_revision_id == request_id and original == desired:
            return current, False
        raise FundConflict("This share has already been split; transfers require a future workflow.")

    # Never silently transfer away the initial allottee's entire participation.
    if share.membership_id not in desired:
        raise ValidationError({"participants": ["Include the original allottee."]})
    if len(current) != 1 or current[0].membership_id != share.membership_id or current[0].units != 12:
        raise FundConflict("Existing participation is not an unsplit whole share.")

    eligible_ids = set(
        FundMembership.objects.filter(
            fund=fund,
            pk__in=desired,
            is_active=True,
            user__isnull=False,  # guest sponsors/acceptance are a separate feature
        ).values_list("pk", flat=True)
    )
    if eligible_ids != set(desired):
        raise ValidationError(
            {"participants": ["Participants must be active registered members of this fund."]}
        )
    if Share.objects.filter(participation_revision_id=request_id).exclude(pk=share.pk).exists():
        raise FundConflict("This request ID was already used for another share.")

    ShareParticipation.objects.filter(share=share).delete()
    ShareParticipation.objects.bulk_create(
        [ShareParticipation(share=share, membership_id=member_id, units=units)
         for member_id, units in desired.items()]
    )
    share.participation_revision_id = request_id
    share.save(update_fields=["participation_revision_id"])
    AuditLog.objects.create(
        fund=fund,
        actor=actor,
        action="share.participation_proposed",
        target_id=share.pk,
        changed_fields=["participations"],
    )
    return list(ShareParticipation.objects.filter(share=share).order_by("membership_id")), True
