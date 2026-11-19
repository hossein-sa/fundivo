"""Manager-only creation of non-login guest memberships while funds are drafts."""

from django.db import transaction
from rest_framework.exceptions import PermissionDenied

from .models import AuditLog, Fund, FundMembership
from .services import FundConflict


@transaction.atomic
def create_guest_membership(*, fund_id, actor, guest_name: str) -> FundMembership:
    """Create a named placeholder without creating or linking a user account."""
    if not actor.is_active or not actor.is_phone_verified:
        raise PermissionDenied("A verified active account is required.")

    fund = Fund.objects.select_for_update().get(pk=fund_id)
    is_manager = FundMembership.objects.filter(
        fund=fund,
        user=actor,
        role=FundMembership.Role.MANAGER,
        is_active=True,
    ).exists()
    if not is_manager:
        raise PermissionDenied("Only the fund manager may add guest memberships.")
    if fund.status != Fund.Status.DRAFT:
        raise FundConflict("Guest memberships can only be created while a fund is in draft.")

    normalized_name = guest_name.strip()
    if not normalized_name or len(normalized_name) > 120:
        raise ValueError("A guest name of 1 to 120 characters is required.")

    membership = FundMembership.objects.create(
        fund=fund,
        user=None,
        guest_name=normalized_name,
        role=FundMembership.Role.MEMBER,
    )
    AuditLog.objects.create(
        fund=fund,
        actor=actor,
        action="membership.guest_created",
        target_id=membership.pk,
        changed_fields=["guest_name"],
    )
    return membership
