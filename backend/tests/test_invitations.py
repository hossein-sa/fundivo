"""Invitation consent, isolation, replay safety, and audit/transaction tests."""

from datetime import timedelta
from unittest.mock import patch

import pytest
from apps.funds.models import AuditLog, Fund, FundMembership
from apps.funds.services import create_fund
from apps.invitations.models import Invitation
from apps.invitations.services import digest_code
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

pytestmark = pytest.mark.django_db


@pytest.fixture
def actors():
    user_model = get_user_model()
    manager = user_model.objects.create_user("09120000011", is_phone_verified=True)
    intended = user_model.objects.create_user("09120000012", is_phone_verified=True)
    stranger = user_model.objects.create_user("09120000013", is_phone_verified=True)
    return manager, intended, stranger


@pytest.fixture
def fund(actors):
    return create_fund(creator=actors[0], name="Invited Family Fund")


def client_for(user=None):
    client = APIClient()
    if user is not None:
        token = RefreshToken.for_user(user)
        client.credentials(HTTP_AUTHORIZATION=f"Bearer {token.access_token}")
    return client


def create_url(fund):
    return reverse("fund-invitation-list", kwargs={"fund_id": fund.pk})


def invite(actors, fund):
    response = client_for(actors[0]).post(
        create_url(fund), {"phone_number": "09120000012"}, format="json"
    )
    assert response.status_code == 201, response.data
    return response.data["invitation_code"], response.data["id"]


def test_only_authenticated_manager_can_issue_invitations(actors, fund):
    manager, intended, stranger = actors
    url = create_url(fund)
    assert client_for().post(url, {"phone_number": "09120000012"}).status_code == 401
    assert client_for(intended).post(url, {"phone_number": "09120000013"}).status_code == 404
    assert client_for(stranger).get(url).status_code == 404
    FundMembership.objects.create(fund=fund, user=intended, role="member")
    assert client_for(intended).post(url, {"phone_number": "09120000013"}).status_code == 403
    assert client_for(intended).get(url).status_code == 403
    assert client_for(manager).get(url).status_code == 200


def test_creation_returns_secret_once_and_stores_hash_only(actors, fund):
    code, invitation_id = invite(actors, fund)
    assert len(code) == 43
    invitation = Invitation.objects.get(id=invitation_id)
    assert invitation.token_digest == digest_code(code)
    assert code not in invitation.token_digest
    assert invitation.target_fingerprint not in (actors[1].phone_number, code)
    manager_view = client_for(actors[0]).get(create_url(fund))
    assert manager_view.status_code == 200
    assert manager_view.data["count"] == 1
    listed = str(manager_view.data)
    assert code not in listed
    assert actors[1].phone_number not in listed
    assert invitation.target_fingerprint not in listed
    log = AuditLog.objects.get(fund=fund, action="invitation.created")
    assert log.actor == actors[0]
    assert code not in str(log.changed_fields)


def test_recipient_accepts_and_becomes_only_regular_member(actors, fund):
    _, recipient, _ = actors
    code, invitation_id = invite(actors, fund)
    response = client_for(recipient).post(
        reverse("invitation-accept"), {"code": code}, format="json"
    )
    assert response.status_code == 200, response.data
    membership = FundMembership.objects.get(fund=fund, user=recipient)
    assert response.data["membership"]["role"] == FundMembership.Role.MEMBER
    assert membership.is_active is True
    invitation = Invitation.objects.get(pk=invitation_id)
    assert invitation.status == Invitation.Status.ACCEPTED
    assert invitation.responded_by == recipient
    assert AuditLog.objects.filter(fund=fund, action="invitation.accepted").count() == 1
    fund_detail = reverse("fund-detail", kwargs={"fund_id": fund.pk})
    assert client_for(recipient).get(fund_detail).status_code == 200
    assert client_for(recipient).patch(
        fund_detail, {"name": "Forbidden"}, format="json"
    ).status_code == 403


def test_invitation_issued_before_account_exists_can_be_accepted_later(actors, fund):
    manager, _, _ = actors
    response = client_for(manager).post(
        create_url(fund), {"phone_number": "09120000014"}, format="json"
    )
    assert response.status_code == 201
    user = get_user_model().objects.create_user("09120000014", is_phone_verified=True)
    assert client_for(user).post(
        reverse("invitation-accept"), {"code": response.data["invitation_code"]}, format="json"
    ).status_code == 200


def test_other_verified_account_cannot_accept_or_reject_code(actors, fund):
    _, _, stranger = actors
    code, invitation_id = invite(actors, fund)
    for operation in ("invitation-accept", "invitation-reject"):
        response = client_for(stranger).post(
            reverse(operation), {"code": code}, format="json"
        )
        assert response.status_code == 400
    assert Invitation.objects.get(pk=invitation_id).status == Invitation.Status.PENDING
    assert not FundMembership.objects.filter(fund=fund, user=stranger).exists()


def test_code_is_single_use(actors, fund):
    code, _ = invite(actors, fund)
    recipient = actors[1]
    url = reverse("invitation-accept")
    assert client_for(recipient).post(url, {"code": code}, format="json").status_code == 200
    assert client_for(recipient).post(url, {"code": code}, format="json").status_code == 400
    assert fund.memberships.filter(user=recipient).count() == 1


def test_accepted_target_cannot_be_invited_again(actors, fund):
    code, _ = invite(actors, fund)
    assert client_for(actors[1]).post(
        reverse("invitation-accept"), {"code": code}, format="json"
    ).status_code == 200
    assert client_for(actors[0]).post(
        create_url(fund), {"phone_number": "09120000012"}, format="json"
    ).status_code == 409


def test_no_duplicate_pending_invitations(actors, fund):
    invite(actors, fund)
    assert client_for(actors[0]).post(
        create_url(fund), {"phone_number": "+989120000012"}, format="json"
    ).status_code == 409


def test_expired_invitation_is_rejected_and_may_be_reissued(actors, fund):
    code, invitation_id = invite(actors, fund)
    Invitation.objects.filter(pk=invitation_id).update(
        expires_at=timezone.now() - timedelta(seconds=1)
    )
    assert client_for(actors[1]).post(
        reverse("invitation-accept"), {"code": code}, format="json"
    ).status_code == 400
    response = client_for(actors[0]).post(
        create_url(fund), {"phone_number": "09120000012"}, format="json"
    )
    assert response.status_code == 201
    assert Invitation.objects.get(pk=invitation_id).status == Invitation.Status.EXPIRED


def test_recipient_can_reject_and_rejected_code_cannot_be_accepted(actors, fund):
    code, invitation_id = invite(actors, fund)
    recipient = actors[1]
    response = client_for(recipient).post(
        reverse("invitation-reject"), {"code": code}, format="json"
    )
    assert response.status_code == 200
    assert response.data["status"] == "rejected"
    assert Invitation.objects.get(pk=invitation_id).status == Invitation.Status.REJECTED
    assert client_for(recipient).post(
        reverse("invitation-accept"), {"code": code}, format="json"
    ).status_code == 400
    assert not FundMembership.objects.filter(fund=fund, user=recipient).exists()


def test_manager_can_revoke_but_outsider_cannot(actors, fund):
    manager, recipient, stranger = actors
    code, invitation_id = invite(actors, fund)
    url = reverse("fund-invitation-revoke", kwargs={
        "fund_id": fund.id, "invitation_id": invitation_id,
    })
    assert client_for(stranger).post(url).status_code == 404
    response = client_for(manager).post(url)
    assert response.status_code == 200
    assert response.data["status"] == "revoked"
    assert client_for(recipient).post(
        reverse("invitation-accept"), {"code": code}, format="json"
    ).status_code == 400
    assert client_for(manager).post(url).status_code == 409


def test_fund_must_be_draft_to_issue_or_accept(actors, fund):
    code, _ = invite(actors, fund)
    Fund.objects.filter(pk=fund.id).update(status="active")
    assert client_for(actors[1]).post(
        reverse("invitation-accept"), {"code": code}, format="json"
    ).status_code == 409
    assert client_for(actors[0]).post(
        create_url(fund), {"phone_number": "09120000014"}, format="json"
    ).status_code == 409


def test_manager_cannot_invite_self_or_assign_roles(actors, fund):
    manager = actors[0]
    assert client_for(manager).post(
        create_url(fund), {"phone_number": manager.phone_number}, format="json"
    ).status_code == 400
    assert client_for(manager).post(
        create_url(fund), {"phone_number": "09120000012", "role": "manager"},
        format="json"
    ).status_code == 400


def test_reject_malformed_code_and_anonymous_access(actors):
    assert client_for().post(reverse("invitation-accept"), {"code": "x" * 43}).status_code == 401
    assert client_for(actors[1]).post(
        reverse("invitation-accept"), {"code": "x" * 43}, format="json"
    ).status_code == 400
    assert client_for(actors[1]).post(
        reverse("invitation-reject"), {"code": "bad"}, format="json"
    ).status_code == 400


def test_atomic_rollback_if_audit_write_fails(actors, fund):
    code, invitation_id = invite(actors, fund)
    with (
        patch("apps.invitations.services.AuditLog.objects.create", side_effect=RuntimeError("audit")),
        pytest.raises(RuntimeError, match="audit"),
    ):
        client_for(actors[1]).post(
            reverse("invitation-accept"), {"code": code}, format="json"
        )
    assert not FundMembership.objects.filter(fund=fund, user=actors[1]).exists()
    assert Invitation.objects.get(pk=invitation_id).status == Invitation.Status.PENDING


def test_issuer_limit_is_enforced(actors, fund):
    manager = actors[0]
    for n in range(20, 40):
        r = client_for(manager).post(
            create_url(fund), {"phone_number": f"0912000{n:04d}"}, format="json"
        )
        assert r.status_code == 201, r.data
    r = client_for(manager).post(
        create_url(fund), {"phone_number": "09120000014"}, format="json"
    )
    assert r.status_code == 429
