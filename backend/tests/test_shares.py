"""Capacity, idempotency, permissions, rollback and ownership of participation shares."""

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


def client_for(user=None):
    client = APIClient()
    if user:
        client.credentials(HTTP_AUTHORIZATION=f"Bearer {RefreshToken.for_user(user).access_token}")
    return client


@pytest.fixture
def setup():
    users = get_user_model()
    manager = users.objects.create_user("09120000011", is_phone_verified=True)
    member = users.objects.create_user("09120000012", is_phone_verified=True)
    second_member = users.objects.create_user("09120000013", is_phone_verified=True)
    outsider = users.objects.create_user("09120000014", is_phone_verified=True)
    fund = create_fund(creator=manager, name="Capacity Fund")
    fund.target_share_count = 3
    fund.save(update_fields=["target_share_count"])
    membership = FundMembership.objects.create(fund=fund, user=member)
    second_membership = FundMembership.objects.create(fund=fund, user=second_member)
    return manager, member, second_member, outsider, fund, membership, second_membership


def share_url(fund):
    return reverse("fund-share-list", kwargs={"fund_id": fund.pk})


def post_shares(client, fund, membership_id, *, count=1, allocation_id=None):
    return client.post(
        share_url(fund),
        {
            "membership_id": str(membership_id),
            "count": count,
            "allocation_id": str(allocation_id or uuid.uuid4()),
        },
        format="json",
    )


def test_manager_allocates_two_to_member_and_audit(setup):
    manager, member, _, _, fund, membership, _ = setup
    response = post_shares(client_for(manager), fund, membership.pk, count=2)
    assert response.status_code == 201
    assert [share["number"] for share in response.data["shares"]] == [1, 2]
    assert Share.objects.filter(fund=fund, membership__user=member).count() == 2
    assert AuditLog.objects.filter(fund=fund, action="shares.allocated").count() == 1


def test_manager_may_hold_shares_or_manage_without_any(setup):
    manager, _, _, _, fund, _, _ = setup
    manager_membership = fund.memberships.get(user=manager)
    assert manager_membership.shares.count() == 0
    response = post_shares(client_for(manager), fund, manager_membership.pk, count=1)
    assert response.status_code == 201
    assert manager_membership.shares.count() == 1


def test_allocation_same_request_id_is_retry_safe(setup):
    manager, _, _, _, fund, membership, _ = setup
    request_id = uuid.uuid4()
    client = client_for(manager)
    first = post_shares(client, fund, membership.pk, count=2, allocation_id=request_id)
    repeated = post_shares(client, fund, membership.pk, count=2, allocation_id=request_id)
    assert first.status_code == 201
    assert repeated.status_code == 200
    assert first.data == repeated.data
    assert Share.objects.filter(fund=fund).count() == 2
    assert AuditLog.objects.filter(fund=fund, action="shares.allocated").count() == 1


def test_reusing_request_id_with_other_input_is_conflict(setup):
    manager, _, _, _, fund, membership, second_membership = setup
    request_id = uuid.uuid4()
    client = client_for(manager)
    assert post_shares(client, fund, membership.pk, count=2, allocation_id=request_id).status_code == 201
    assert post_shares(client, fund, second_membership.pk, count=2, allocation_id=request_id).status_code == 409
    assert post_shares(client, fund, membership.pk, count=1, allocation_id=request_id).status_code == 409
    assert Share.objects.count() == 2


def test_capacity_is_enforced_and_next_number_is_sequential(setup):
    manager, _, _, _, fund, membership, second_membership = setup
    client = client_for(manager)
    assert post_shares(client, fund, membership.pk, count=2).status_code == 201
    last = post_shares(client, fund, second_membership.pk, count=1)
    assert last.status_code == 201
    assert last.data["shares"][0]["number"] == 3
    assert post_shares(client, fund, membership.pk, count=1).status_code == 409
    assert Share.objects.filter(fund=fund).count() == 3


def test_target_capacity_required_before_allocation(setup):
    manager, _, _, _, fund, membership, _ = setup
    fund.target_share_count = None
    fund.save(update_fields=["target_share_count"])
    assert post_shares(client_for(manager), fund, membership.pk).status_code == 409


def test_draft_manager_can_change_capacity_but_not_below_issued(setup):
    manager, _, _, _, fund, membership, _ = setup
    client = client_for(manager)
    url = reverse("fund-detail", kwargs={"fund_id": fund.pk})
    assert client.patch(url, {"target_share_count": 4}, format="json").status_code == 200
    assert post_shares(client, fund, membership.pk, count=2).status_code == 201
    assert client.patch(url, {"target_share_count": 1}, format="json").status_code == 409
    assert client.patch(url, {"target_share_count": None}, format="json").status_code == 409
    fund.refresh_from_db()
    assert fund.target_share_count == 4


def test_members_cannot_allocate_shares(setup):
    _, member, _, outsider, fund, membership, _ = setup
    assert post_shares(client_for(member), fund, membership.pk).status_code == 403
    assert post_shares(client_for(outsider), fund, membership.pk).status_code == 404
    assert post_shares(client_for(), fund, membership.pk).status_code == 401


def test_cross_fund_membership_is_not_allocatable(setup):
    manager, _, _, outsider, fund, _, _ = setup
    another = create_fund(creator=outsider, name="Other Fund")
    another_membership = another.memberships.get(user=outsider)
    assert post_shares(client_for(manager), fund, another_membership.pk).status_code == 404
    assert Share.objects.count() == 0


def test_inactive_member_cannot_receive_shares(setup):
    manager, _, _, _, fund, membership, _ = setup
    membership.is_active = False
    membership.save(update_fields=["is_active"])
    assert post_shares(client_for(manager), fund, membership.pk).status_code == 404


def test_shares_visible_only_to_owner_or_manager(setup):
    manager, member, second_member, outsider, fund, membership, second_membership = setup
    c = client_for(manager)
    a = post_shares(c, fund, membership.pk)
    b = post_shares(c, fund, second_membership.pk)
    assert a.status_code == 201 and b.status_code == 201
    assert c.get(share_url(fund)).data["count"] == 2
    assert client_for(member).get(share_url(fund)).data["count"] == 1
    assert client_for(second_member).get(share_url(fund)).data["count"] == 1
    assert client_for(outsider).get(share_url(fund)).status_code == 404
    assert client_for().get(share_url(fund)).status_code == 401
    other_share = b.data["shares"][0]["id"]
    detail = reverse("fund-share-detail", kwargs={"fund_id": fund.pk, "share_id": other_share})
    assert client_for(member).get(detail).status_code == 404
    assert c.get(detail).status_code == 200
    assert client_for(second_member).get(detail).status_code == 200


def test_share_allocation_restricted_to_drafts(setup):
    manager, _, _, _, fund, membership, _ = setup
    Fund.objects.filter(pk=fund.pk).update(status=Fund.Status.ACTIVE)
    assert post_shares(client_for(manager), fund, membership.pk).status_code == 409


@pytest.mark.parametrize("count", [0, -1, 21, "bad"])
def test_invalid_share_counts_rejected(setup, count):
    manager, _, _, _, fund, membership, _ = setup
    response = post_shares(client_for(manager), fund, membership.pk, count=count)
    assert response.status_code == 400
    assert Share.objects.count() == 0


def test_unknown_input_and_bad_uuid_rejected(setup):
    manager, _, _, _, fund, membership, _ = setup
    client = client_for(manager)
    payload = {"membership_id": str(membership.pk), "count": 1, "allocation_id": str(uuid.uuid4()), "role": "manager"}
    assert client.post(share_url(fund), payload, format="json").status_code == 400
    payload.pop("role")
    payload["allocation_id"] = "no"
    assert client.post(share_url(fund), payload, format="json").status_code == 400


def test_allocation_rolls_back_if_audit_fails(setup):
    manager, _, _, _, fund, membership, _ = setup
    with (
        patch("apps.shares.services.AuditLog.objects.create", side_effect=RuntimeError("failure")),
        pytest.raises(RuntimeError, match="failure"),
    ):
        post_shares(client_for(manager), fund, membership.pk, count=2)
    assert Share.objects.count() == 0


def test_database_enforces_unique_share_number(setup):
    manager, _, _, _, fund, membership, _ = setup
    assert post_shares(client_for(manager), fund, membership.pk).status_code == 201
    with pytest.raises(IntegrityError), transaction.atomic():
        Share.objects.create(fund=fund, membership=membership, number=1, allocation_id=uuid.uuid4())


def test_shares_cannot_be_put_or_deleted(setup):
    manager, _, _, _, fund, membership, _ = setup
    client = client_for(manager)
    shares = post_shares(client, fund, membership.pk).data["shares"]
    url = reverse("fund-share-detail", kwargs={"fund_id": fund.pk, "share_id": shares[0]["id"]})
    assert client.patch(url, {"number": 99}, format="json").status_code == 405
    assert client.delete(url).status_code == 405
    assert client.put(share_url(fund), {"count": 1}, format="json").status_code == 405


def test_shares_registered_read_only_in_admin():
    from apps.shares.admin import ShareAdmin
    from django.contrib import admin

    assert Share in admin.site._registry
    registration = admin.site._registry[Share]
    assert isinstance(registration, ShareAdmin)
    assert registration.has_add_permission(None) is False
    assert registration.has_change_permission(None) is False
    assert registration.has_delete_permission(None) is False
