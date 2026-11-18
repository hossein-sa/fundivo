"""Transactional business operations for funds."""

from django.db import transaction
from rest_framework.exceptions import APIException, PermissionDenied

from .models import AuditLog, Fund, FundMembership


class FundConflict(APIException):
    status_code = 409
    default_detail = "This operation is not allowed in the fund's current state."
    default_code = "fund_state_conflict"


@transaction.atomic
def create_fund(*, creator, name: str, description: str = "") -> Fund:
    """A new fund and its manager must be created as one atomic operation."""
    if not creator.is_active or not creator.is_phone_verified:
        raise PermissionDenied("A verified active account is required.")

    fund = Fund.objects.create(
        created_by=creator,
        name=name,
        description=description,
    )
    FundMembership.objects.create(
        fund=fund,
        user=creator,
        role=FundMembership.Role.MANAGER,
    )
    AuditLog.objects.create(
        fund=fund,
        actor=creator,
        action="fund.created",
        target_id=fund.pk,
        changed_fields=["name", "description"],
    )
    return fund


@transaction.atomic
def edit_fund_draft(*, fund_id, actor, changes: dict) -> Fund:
    """Lock before checking role/state so concurrent edits remain consistent."""
    fund = Fund.objects.select_for_update().get(pk=fund_id)
    is_manager = FundMembership.objects.filter(
        fund=fund,
        user=actor,
        role=FundMembership.Role.MANAGER,
        is_active=True,
    ).exists()
    if not is_manager:
        raise PermissionDenied("Only the fund manager can edit this fund.")
    if fund.status != Fund.Status.DRAFT:
        raise FundConflict()

    changed_fields = [key for key, value in changes.items() if getattr(fund, key) != value]
    if changed_fields:
        for key in changed_fields:
            setattr(fund, key, changes[key])
        fund.save(update_fields=[*changed_fields, "updated_at"])
        AuditLog.objects.create(
            fund=fund,
            actor=actor,
            action="fund.updated",
            target_id=fund.pk,
            changed_fields=changed_fields,
        )
    return fund
