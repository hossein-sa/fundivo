"""Invitation operations: consent, uniqueness, audit, and concurrency safety."""

import hashlib
import hmac
import secrets
from datetime import timedelta

from django.conf import settings
from django.contrib.auth import get_user_model
from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import (
    APIException,
    NotFound,
    PermissionDenied,
    ValidationError,
)

from apps.accounts.phone_numbers import normalize_iranian_mobile
from apps.funds.models import AuditLog, Fund, FundMembership

from .models import Invitation

INVITE_LIFETIME = timedelta(hours=48)
MAX_INVITES_PER_FUND_PER_DAY = 20
INVALID_CODE = {"code": ["Invalid or expired invitation."]}


class InvitationConflict(APIException):
    status_code = 409
    default_detail = "Invitation or membership conflicts with current state."
    default_code = "invitation_conflict"


class InvitationRateLimited(APIException):
    status_code = 429
    default_detail = "Invitation creation limit reached for this fund."
    default_code = "invitation_rate_limited"


def target_fingerprint(fund_id, phone_number):
    """Fund-specific HMAC avoids retaining phone numbers in invitation records."""
    normalized = normalize_iranian_mobile(phone_number)
    message = f"fundivo-invitation-v1:{fund_id}:{normalized}".encode()
    return hmac.new(settings.SECRET_KEY.encode(), message, hashlib.sha256).hexdigest()


def digest_code(code):
    return hashlib.sha256(code.encode("ascii")).hexdigest()


def require_manager(*, fund, actor):
    if not FundMembership.objects.filter(
        fund=fund, user=actor, is_active=True, role=FundMembership.Role.MANAGER
    ).exists():
        raise PermissionDenied("Only the active fund manager may manage invitations.")


def manager_fund_or_error(*, fund_id, actor):
    try:
        fund = Fund.objects.get(pk=fund_id)
    except Fund.DoesNotExist as exc:
        raise NotFound() from exc
    # Don't leak the existence of another user's fund.
    if not FundMembership.objects.filter(fund=fund, user=actor, is_active=True).exists():
        raise NotFound()
    require_manager(fund=fund, actor=actor)
    return fund


@transaction.atomic
def create_invitation(*, fund_id, actor, phone_number):
    fund = Fund.objects.select_for_update().filter(pk=fund_id).first()
    if fund is None:
        raise NotFound()
    if not FundMembership.objects.filter(fund=fund, user=actor, is_active=True).exists():
        raise NotFound()
    require_manager(fund=fund, actor=actor)
    if fund.status != Fund.Status.DRAFT:
        raise InvitationConflict("Invitations currently require a draft fund.")

    fingerprint = target_fingerprint(fund.id, phone_number)
    if fingerprint == target_fingerprint(fund.id, actor.phone_number):
        raise ValidationError({"phone_number": ["You already manage this fund."]})

    # Existing (even inactive) memberships require an explicit recovery policy.
    # The database's fund-user unique constraint still protects simultaneous acceptance.
    user = get_user_model().objects.filter(phone_number=normalize_iranian_mobile(phone_number)).first()
    if user and FundMembership.objects.filter(fund=fund, user=user).exists():
        raise InvitationConflict("Account already has a membership in this fund.")

    now = timezone.now()
    Invitation.objects.filter(
        fund=fund, target_fingerprint=fingerprint,
        status=Invitation.Status.PENDING, expires_at__lte=now,
    ).update(status=Invitation.Status.EXPIRED)
    if Invitation.objects.filter(
        fund=fund, target_fingerprint=fingerprint, status=Invitation.Status.PENDING
    ).exists():
        raise InvitationConflict("There is already a pending invitation for this recipient.")
    if Invitation.objects.filter(
        fund=fund, created_at__gte=now - timedelta(hours=24)
    ).count() >= MAX_INVITES_PER_FUND_PER_DAY:
        raise InvitationRateLimited()

    code = secrets.token_urlsafe(32)
    invitation = Invitation.objects.create(
        fund=fund,
        created_by=actor,
        target_fingerprint=fingerprint,
        token_digest=digest_code(code),
        expires_at=now + INVITE_LIFETIME,
    )
    AuditLog.objects.create(
        fund=fund, actor=actor, action="invitation.created",
        target_id=invitation.id, changed_fields=["status", "expires_at"],
    )
    return invitation, code


def _locate_invitation(code):
    # Never put invitation codes in URLs: access logs and browser history are not safe.
    if not isinstance(code, str) or len(code) != 43 or not all(
        char in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_" for char in code
    ):
        raise ValidationError(INVALID_CODE)
    invitation = Invitation.objects.filter(token_digest=digest_code(code)).first()
    if invitation is None:
        raise ValidationError(INVALID_CODE)
    return invitation


@transaction.atomic
def respond_to_invitation(*, actor, code, accept):
    initial = _locate_invitation(code)
    # Consistent lock order across creation/revoke/accept: fund -> invitation.
    fund = Fund.objects.select_for_update().get(pk=initial.fund_id)
    invitation = Invitation.objects.select_for_update().get(pk=initial.pk)
    if invitation.status != Invitation.Status.PENDING or invitation.expires_at <= timezone.now():
        raise ValidationError(INVALID_CODE)
    if not actor.is_active or not actor.is_phone_verified:
        raise PermissionDenied("A verified active account is required.")
    if not hmac.compare_digest(
        invitation.target_fingerprint,
        target_fingerprint(fund.id, actor.phone_number),
    ):
        raise ValidationError(INVALID_CODE)
    if fund.status != Fund.Status.DRAFT:
        raise InvitationConflict("The fund is not accepting invitations now.")
    if FundMembership.objects.filter(fund=fund, user=actor).exists():
        raise InvitationConflict("Account already has a membership in this fund.")

    now = timezone.now()
    if accept:
        membership = FundMembership.objects.create(
            fund=fund, user=actor, role=FundMembership.Role.MEMBER
        )
        invitation.status = Invitation.Status.ACCEPTED
        action = "invitation.accepted"
    else:
        membership = None
        invitation.status = Invitation.Status.REJECTED
        action = "invitation.rejected"
    invitation.responded_by = actor
    invitation.responded_at = now
    invitation.save(update_fields=["status", "responded_by", "responded_at"])
    AuditLog.objects.create(
        fund=fund, actor=actor, action=action,
        target_id=invitation.id, changed_fields=["status"],
    )
    return invitation, membership


@transaction.atomic
def revoke_invitation(*, actor, fund_id, invitation_id):
    fund = Fund.objects.select_for_update().filter(pk=fund_id).first()
    if fund is None or not FundMembership.objects.filter(
        fund=fund, user=actor, is_active=True
    ).exists():
        raise NotFound()
    require_manager(fund=fund, actor=actor)
    invitation = Invitation.objects.select_for_update().filter(
        fund=fund, pk=invitation_id
    ).first()
    if invitation is None:
        raise NotFound()
    if invitation.status != Invitation.Status.PENDING or invitation.expires_at <= timezone.now():
        raise InvitationConflict("Only unexpired pending invitations can be revoked.")
    invitation.status = Invitation.Status.REVOKED
    invitation.responded_by = actor
    invitation.responded_at = timezone.now()
    invitation.save(update_fields=["status", "responded_by", "responded_at"])
    AuditLog.objects.create(
        fund=fund, actor=actor, action="invitation.revoked",
        target_id=invitation.id, changed_fields=["status"],
    )
    return invitation
