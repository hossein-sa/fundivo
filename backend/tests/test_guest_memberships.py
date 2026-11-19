"""Guest membership isolation, permission, integrity and share allocation tests."""

import uuid
from unittest.mock import patch

import pytest
from apps.funds.models import AuditLog, Fund, FundMembership
from apps.funds.services import create_fund
from apps.shares.models import Share
from django.contrib.auth import get_user_model
from django.db import IntegrityError, transaction
from django.urls import reverse
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

pytestmark = pytest.mark.django_db


@pytest.fixture
def context():
    users = get_user_model()
    manager = users.objects.create_user("09120000301", is_phone_verified=True)
    member = users.objects.create_user("09120000302", is_phone_verified=True)
    outsider = users.objects.create_user("09120000303", is_phone_verified=True)
    fund = create_fund(creator=manager, name="Guest Fund", target_share_count=3)
    FundMembership.objects.create(fund=fund, user=member, role=FundMembership.Role.MEMBER)
    return manager, member, outsider, fund


def client_for(user=None):
    client = APIClient()
    if user is not None:
        client.credentials(HTTP_AUTHORIZATION=f"Bearer {RefreshToken.for_user(user).access_token}")
    return client


def guest_url(fund):
    return reverse("fund-guest-membership-create", kwargs={"fund_id": fund.pk})


def create_guest(manager, fund, name=" Sample Guest "):
    return client_for(manager).post(guest_url(fund), {"guest_name": name}, format="json")


def test_manager_creates_guest_without_user_account(context):
    manager, _, _, fund = context
    count_before = get_user_model().objects.count()
    r = create_guest(manager, fund)
    assert r.status_code == 201
    membership = FundMembership.objects.get(pk=r.data["id"])
    assert r.data["user_id"] is None
    assert r.data["guest_name"] == "Sample Guest"
    assert r.data["is_guest"] is True
    assert r.data["role"] == "member"
    assert r.data["is_active"] is True
    assert membership.user_id is None
    assert membership.guest_name == "Sample Guest"
    assert get_user_model().objects.count() == count_before
    log = AuditLog.objects.get(fund=fund, action="membership.guest_created")
    assert log.actor_id == manager.id
    assert log.target_id == membership.pk
    assert log.changed_fields == ["guest_name"]


def test_registered_membership_remains_unchanged_and_serializable(context):
    manager, member, _, fund = context
    assert create_guest(manager, fund).status_code == 201
    url = reverse("fund-membership-list", kwargs={"fund_id": fund.pk})
    r = client_for(manager).get(url)
    assert r.status_code == 200
    assert r.data["count"] == 3
    registered = next(m for m in r.data["results"] if m["user_id"] == str(member.id))
    guest = next(m for m in r.data["results"] if m["is_guest"])
    assert registered["is_guest"] is False
    assert registered["guest_name"] == ""
    assert guest["user_id"] is None
    assert guest["role"] == "member"
    assert all("phone_number" not in data for data in r.data["results"])


def test_member_cannot_create_guest(context):
    _, member, _, fund = context
    r = client_for(member).post(guest_url(fund), {"guest_name": "No"}, format="json")
    assert r.status_code == 403
    assert FundMembership.objects.filter(fund=fund, user__isnull=True).count() == 0


def test_nonmember_cannot_discover_fund_to_create_guest(context):
    _, _, outsider, fund = context
    r = client_for(outsider).post(guest_url(fund), {"guest_name": "No"}, format="json")
    assert r.status_code == 404


def test_anonymous_cannot_create_guest(context):
    _, _, _, fund = context
    r = client_for().post(guest_url(fund), {"guest_name": "No"}, format="json")
    assert r.status_code == 401


def test_inactive_manager_membership_cannot_create_guest(context):
    manager, _, _, fund = context
    fund.memberships.filter(user=manager).update(is_active=False)
    assert create_guest(manager, fund).status_code == 404


def test_non_draft_fund_rejects_guests(context):
    manager, _, _, fund = context
    Fund.objects.filter(pk=fund.pk).update(status=Fund.Status.ACTIVE)
    r = create_guest(manager, fund)
    assert r.status_code == 409
    assert FundMembership.objects.filter(fund=fund, user__isnull=True).count() == 0


@pytest.mark.parametrize("value", ["", "   ", "x" * 121])
def test_invalid_guest_names_rejected(context, value):
    manager, _, _, fund = context
    r = create_guest(manager, fund, name=value)
    assert r.status_code == 400


def test_guest_request_rejects_unknown_or_sensitive_fields(context):
    manager, _, _, fund = context
    r = client_for(manager).post(
        guest_url(fund),
        {"guest_name": "Placeholder", "role": "manager", "user_id": str(manager.id)},
        format="json",
    )
    assert r.status_code == 400
    assert FundMembership.objects.filter(fund=fund, user__isnull=True).count() == 0


def test_guest_can_own_a_draft_share_without_user_account(context):
    manager, member, _, fund = context
    guest_response = create_guest(manager, fund)
    guest_id = guest_response.data["id"]
    r = client_for(manager).post(
        reverse("fund-share-list", kwargs={"fund_id": fund.pk}),
        {
            "membership_id": guest_id,
            "count": 1,
            "allocation_id": str(uuid.uuid4()),
        },
        format="json",
    )
    assert r.status_code == 201
    share = Share.objects.get(pk=r.data["shares"][0]["id"])
    assert str(share.membership_id) == guest_id
    # Regular members can never see another membership's shares.
    member_list = client_for(member).get(reverse("fund-share-list", kwargs={"fund_id": fund.pk}))
    assert member_list.status_code == 200
    assert member_list.data["count"] == 0


def test_guest_creation_rolls_back_when_audit_fails(context):
    manager, _, _, fund = context
    with (
        patch("apps.funds.guest_services.AuditLog.objects.create", side_effect=RuntimeError("audit error")),
        pytest.raises(RuntimeError, match="audit error"),
    ):
        create_guest(manager, fund)
    assert FundMembership.objects.filter(fund=fund, user__isnull=True).count() == 0


def test_database_requires_name_for_guest(context):
    _, _, _, fund = context
    with pytest.raises(IntegrityError), transaction.atomic():
        FundMembership.objects.create(fund=fund, user=None, guest_name="")


def test_database_forbids_guest_name_on_registered_membership(context):
    _, member, _, fund = context
    with pytest.raises(IntegrityError), transaction.atomic():
        FundMembership.objects.filter(fund=fund, user=member).update(guest_name="Not guest")


def test_database_forbids_guest_manager(context):
    manager, _, _, _ = context
    # Create a fund without an active manager membership to ensure the
    # guest-manager constraint, not the unique-manager constraint, rejects it.
    empty_fund = Fund.objects.create(name="Unmanaged test fund", created_by=manager)
    with pytest.raises(IntegrityError), transaction.atomic():
        FundMembership.objects.create(
            fund=empty_fund,
            user=None,
            guest_name="Manager?",
            role=FundMembership.Role.MANAGER,
        )


def test_duplicate_guest_names_allowed_with_distinct_ids(context):
    manager, _, _, fund = context
    first = create_guest(manager, fund, name="Same Name")
    second = create_guest(manager, fund, name="Same Name")
    assert first.status_code == second.status_code == 201
    assert first.data["id"] != second.data["id"]


def test_no_guest_edit_or_delete_endpoint(context):
    manager, _, _, fund = context
    client = client_for(manager)
    assert client.patch(guest_url(fund), {"guest_name": "New"}, format="json").status_code == 405
    assert client.delete(guest_url(fund)).status_code == 405
