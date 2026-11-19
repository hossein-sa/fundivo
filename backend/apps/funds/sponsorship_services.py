"""Consent-based guest sponsorship; no monetary obligation is generated yet."""

from django.db import transaction
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework.exceptions import PermissionDenied, ValidationError

from .models import AuditLog, Fund, FundMembership, GuestSponsorship
from .services import FundConflict


def _actor_membership(fund, actor):
    return get_object_or_404(
        FundMembership,
        fund=fund,
        user=actor,
        is_active=True,
    )


def _require_draft(fund):
    if fund.status != Fund.Status.DRAFT:
        raise FundConflict("Sponsorship changes require a draft fund.")


def _sponsor(fund, membership_id):
    return get_object_or_404(
        FundMembership,
        pk=membership_id,
        fund=fund,
        is_active=True,
        user__isnull=False,
    )


def _log(fund, actor, sponsorship, action):
    AuditLog.objects.create(
        fund=fund,
        actor=actor,
        action=action,
        target_id=sponsorship.pk,
        changed_fields=["status"],
    )


def _same_request(existing, *, actor, sponsor_id, guest_name=None, guest_id=None):
    return (
        existing.requested_by_id == actor.pk
        and existing.sponsor_membership_id == sponsor_id
        and (
            (guest_id is not None and existing.guest_membership_id == guest_id)
            or (guest_name is not None and existing.guest_membership.guest_name == guest_name
                and not existing.is_legacy_attachment)
        )
    )


@transaction.atomic
def create_sponsorship_request(
    *, fund_id, actor, request_id, guest_name, sponsor_membership_id=None,
    accept_responsibility=False,
):
    """Members may propose for themselves; managers may nominate another sponsor."""
    fund = get_object_or_404(Fund.objects.select_for_update(), pk=fund_id)
    current = _actor_membership(fund, actor)
    _require_draft(fund)
    if not actor.is_active or not actor.is_phone_verified:
        raise PermissionDenied("An active verified user is required.")

    sponsor = _sponsor(fund, sponsor_membership_id or current.pk)
    if current.role != FundMembership.Role.MANAGER and sponsor.pk != current.pk:
        raise PermissionDenied("Members can only sponsor their own guests.")
    if accept_responsibility and sponsor.pk != current.pk:
        raise ValidationError({"accept_responsibility": ["You cannot consent for someone else."]})
    if sponsor.pk == current.pk and not accept_responsibility:
        raise ValidationError({"accept_responsibility": ["Explicit consent is required."]})

    name = guest_name.strip()
    existing = GuestSponsorship.objects.filter(request_id=request_id).select_related("guest_membership").first()
    if existing:
        if _same_request(existing, actor=actor, sponsor_id=sponsor.pk, guest_name=name):
            return existing, False
        raise FundConflict("The request_id was used for a different request.")

    # Avoid unbounded pending placeholders by one member in a single draft fund.
    pending_count = GuestSponsorship.objects.filter(
        fund=fund,
        requested_by=actor,
        status__in=(GuestSponsorship.Status.PENDING_SPONSOR, GuestSponsorship.Status.PENDING_MANAGER),
    ).count()
    if pending_count >= 10:
        raise FundConflict("Too many pending sponsorship requests for this user.")

    manager_accepted = current.role == FundMembership.Role.MANAGER and sponsor.pk == current.pk
    now = timezone.now()
    if manager_accepted:
        status = GuestSponsorship.Status.ACTIVE
    elif sponsor.pk == current.pk:
        status = GuestSponsorship.Status.PENDING_MANAGER
    else:
        status = GuestSponsorship.Status.PENDING_SPONSOR

    guest = FundMembership.objects.create(
        fund=fund,
        user=None,
        guest_name=name,
        role=FundMembership.Role.MEMBER,
        is_active=manager_accepted,
    )
    sponsorship = GuestSponsorship.objects.create(
        fund=fund,
        guest_membership=guest,
        sponsor_membership=sponsor,
        requested_by=actor,
        request_id=request_id,
        is_legacy_attachment=False,
        status=status,
        sponsor_accepted_at=now if sponsor.pk == current.pk else None,
        approved_at=now if manager_accepted else None,
    )
    _log(fund, actor, sponsorship, "sponsorship.requested")
    return sponsorship, True


@transaction.atomic
def attach_existing_guest(
    *, fund_id, guest_id, actor, request_id, sponsor_membership_id,
    accept_responsibility=False,
):
    """Attach a sponsor to an old guest without modifying existing shares."""
    fund = get_object_or_404(Fund.objects.select_for_update(), pk=fund_id)
    current = _actor_membership(fund, actor)
    if current.role != FundMembership.Role.MANAGER:
        raise PermissionDenied("Only a manager may attach a legacy guest.")
    _require_draft(fund)
    guest = get_object_or_404(
        FundMembership,
        pk=guest_id,
        fund=fund,
        user__isnull=True,
    )
    sponsor = _sponsor(fund, sponsor_membership_id)
    if accept_responsibility and sponsor.pk != current.pk:
        raise ValidationError({"accept_responsibility": ["You cannot consent for someone else."]})
    if sponsor.pk == current.pk and not accept_responsibility:
        raise ValidationError({"accept_responsibility": ["Explicit consent is required."]})

    already = GuestSponsorship.objects.filter(request_id=request_id).select_related("guest_membership").first()
    if already:
        if _same_request(already, actor=actor, sponsor_id=sponsor.pk, guest_id=guest.pk):
            return already, False
        raise FundConflict("The request_id was used for a different request.")
    if GuestSponsorship.objects.filter(guest_membership=guest).exists():
        raise FundConflict("A sponsorship record already exists for this guest.")

    manager_accepted = sponsor.pk == current.pk
    now = timezone.now()
    sponsorship = GuestSponsorship.objects.create(
        fund=fund,
        guest_membership=guest,
        sponsor_membership=sponsor,
        requested_by=actor,
        request_id=request_id,
        is_legacy_attachment=True,
        status=(GuestSponsorship.Status.ACTIVE if manager_accepted
                else GuestSponsorship.Status.PENDING_SPONSOR),
        sponsor_accepted_at=now if manager_accepted else None,
        approved_at=now if manager_accepted else None,
    )
    # Legacy membership stays active; no shares, UUIDs or financial data change.
    _log(fund, actor, sponsorship, "sponsorship.legacy_attached")
    return sponsorship, True


@transaction.atomic
def decide_sponsorship(*, fund_id, sponsorship_id, actor, decision):
    fund = get_object_or_404(Fund.objects.select_for_update(), pk=fund_id)
    current = _actor_membership(fund, actor)
    _require_draft(fund)
    sponsorship = get_object_or_404(
        GuestSponsorship.objects.select_for_update().select_related(
            "guest_membership", "sponsor_membership"
        ),
        pk=sponsorship_id, fund=fund,
    )
    manager = current.role == FundMembership.Role.MANAGER
    sponsor = current.pk == sponsorship.sponsor_membership_id
    if decision == "accept":
        if not sponsor:
            raise PermissionDenied("Only the nominated sponsor may consent.")
        if sponsorship.status != GuestSponsorship.Status.PENDING_SPONSOR:
            raise FundConflict("This sponsorship is not waiting for sponsor consent.")
        if not current.is_active or current.user_id is None:
            raise PermissionDenied("An active registered sponsor is required.")
        sponsorship.sponsor_accepted_at = timezone.now()
        sponsorship.status = GuestSponsorship.Status.PENDING_MANAGER
        action = "sponsorship.sponsor_accepted"
    elif decision == "approve":
        if not manager:
            raise PermissionDenied("Only a fund manager may approve a sponsorship.")
        if sponsorship.status != GuestSponsorship.Status.PENDING_MANAGER:
            raise FundConflict("Sponsor consent is required before manager approval.")
        if not sponsorship.sponsor_membership.is_active or sponsorship.sponsor_membership.user_id is None:
            raise FundConflict("The nominated sponsor is no longer eligible.")
        sponsorship.status = GuestSponsorship.Status.ACTIVE
        sponsorship.approved_at = timezone.now()
        if not sponsorship.guest_membership.is_active:
            sponsorship.guest_membership.is_active = True
            sponsorship.guest_membership.save(update_fields=["is_active"])
        action = "sponsorship.manager_approved"
    elif decision == "reject":
        if not manager and not sponsor:
            raise PermissionDenied("Only the manager or nominated sponsor may reject.")
        if sponsorship.status not in (
            GuestSponsorship.Status.PENDING_SPONSOR,
            GuestSponsorship.Status.PENDING_MANAGER,
        ):
            raise FundConflict("Only pending sponsorships can be rejected.")
        sponsorship.status = GuestSponsorship.Status.REJECTED
        action = "sponsorship.rejected"
    else:
        raise ValueError("Unsupported sponsorship decision.")

    sponsorship.save(update_fields=["status", "sponsor_accepted_at", "approved_at", "updated_at"])
    _log(fund, actor, sponsorship, action)
    return sponsorship
