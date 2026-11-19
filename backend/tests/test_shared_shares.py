"""Draft fractional ownership with exact integers and strict fund isolation."""

import uuid
from unittest.mock import patch

import pytest
from apps.funds.models import AuditLog, Fund, FundMembership
from apps.funds.services import create_fund
from apps.shares.models import Share, ShareParticipation
from django.contrib.auth import get_user_model
from django.db import IntegrityError, transaction
from django.urls import reverse
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

pytestmark = pytest.mark.django_db


def as_user(user=None):
    client = APIClient()
    if user is not None:
        client.credentials(HTTP_AUTHORIZATION=f"Bearer {RefreshToken.for_user(user).access_token}")
    return client


@pytest.fixture
def case():
    users = get_user_model()
    manager = users.objects.create_user("09120000321", is_phone_verified=True)
    alice = users.objects.create_user("09120000322", is_phone_verified=True)
    bob = users.objects.create_user("09120000323", is_phone_verified=True)
    outsider = users.objects.create_user("09120000324", is_phone_verified=True)
    fund = create_fund(creator=manager, name="Shared 12 units", target_share_count=3)
    alice_mem = FundMembership.objects.create(fund=fund, user=alice)
    bob_mem = FundMembership.objects.create(fund=fund, user=bob)
    other = create_fund(creator=outsider, name="Unrelated fund")
    url = reverse("fund-share-list", kwargs={"fund_id": fund.id})
    response = as_user(manager).post(url, {
        "membership_id": str(alice_mem.id),
        "count": 1,
        "allocation_id": str(uuid.uuid4()),
    }, format="json")
    assert response.status_code == 201
    share = Share.objects.get(pk=response.data["shares"][0]["id"])
    return manager, alice, bob, outsider, fund, alice_mem, bob_mem, other, share


def proposal_url(fund, share):
    return reverse("fund-share-participations", kwargs={"fund_id": fund.pk, "share_id": share.pk})


def payload(alice_mem, bob_mem, *, a=6, b=6, request_id=None):
    return {
        "request_id": str(request_id or uuid.uuid4()),
        "participants": [
            {"membership_id": str(alice_mem.pk), "units": a},
            {"membership_id": str(bob_mem.pk), "units": b},
        ],
    }


def test_new_single_share_has_full_participation(case):
    _, _, _, _, _, alice_mem, _, _, share = case
    assert list(share.participations.values_list("membership_id", "units")) == [(alice_mem.pk, 12)]


def test_manager_can_create_half_share_and_new_partner_can_read(case):
    manager, alice, bob, _, fund, alice_mem, bob_mem, _, share = case
    response = as_user(manager).post(
        proposal_url(fund, share), payload(alice_mem, bob_mem), format="json"
    )
    assert response.status_code == 201
    assert sorted(p["units"] for p in response.data["participants"]) == [6, 6]
    assert sum(p.units for p in share.participations.all()) == 12
    # A share still contributes *one*, not two, units to fund capacity.
    assert Share.objects.filter(fund=fund).count() == 1
    for partner in (alice, bob):
        listing = as_user(partner).get(reverse("fund-share-list", kwargs={"fund_id": fund.pk}))
        assert listing.status_code == 200
        assert listing.data["count"] == 1
        assert listing.data["results"][0]["participations"]
    assert AuditLog.objects.filter(fund=fund, action="share.participation_proposed").count() == 1


def test_thirds_are_exact_and_not_floating_point(case):
    manager, _, _, _, fund, alice_mem, bob_mem, _, share = case
    manager_mem = FundMembership.objects.get(fund=fund, user=manager)
    body = {
        "request_id": str(uuid.uuid4()),
        "participants": [
            {"membership_id": str(alice_mem.pk), "units": 4},
            {"membership_id": str(bob_mem.pk), "units": 4},
            {"membership_id": str(manager_mem.pk), "units": 4},
        ],
    }
    r = as_user(manager).post(proposal_url(fund, share), body, format="json")
    assert r.status_code == 201
    assert [p["units"] for p in r.data["participants"]] == [4, 4, 4]
    assert all(type(p["units"]) is int for p in r.data["participants"])


def test_same_request_is_idempotent_but_new_request_cannot_rewrite(case):
    manager, _, _, _, fund, alice_mem, bob_mem, _, share = case
    client = as_user(manager)
    body = payload(alice_mem, bob_mem)
    first = client.post(proposal_url(fund, share), body, format="json")
    second = client.post(proposal_url(fund, share), body, format="json")
    third = client.post(proposal_url(fund, share), payload(alice_mem, bob_mem), format="json")
    assert (first.status_code, second.status_code, third.status_code) == (201, 200, 409)
    assert first.data == second.data
    assert ShareParticipation.objects.filter(share=share).count() == 2
    assert AuditLog.objects.filter(fund=fund, action="share.participation_proposed").count() == 1


@pytest.mark.parametrize("units", [(5, 6), (7, 7), (0, 12), (-1, 13)])
def test_invalid_unit_totals_rejected(case, units):
    manager, _, _, _, fund, alice_mem, bob_mem, _, share = case
    r = as_user(manager).post(
        proposal_url(fund, share), payload(alice_mem, bob_mem, a=units[0], b=units[1]),
        format="json",
    )
    assert r.status_code == 400
    assert list(share.participations.values_list("units", flat=True)) == [12]


def test_duplicate_participant_rejected(case):
    manager, _, _, _, fund, alice_mem, _, _, share = case
    body = payload(alice_mem, alice_mem)
    r = as_user(manager).post(proposal_url(fund, share), body, format="json")
    assert r.status_code == 400


def test_original_allottee_cannot_be_removed(case):
    manager, _, _, _, fund, alice_mem, bob_mem, _, share = case
    manager_mem = FundMembership.objects.get(fund=fund, user=manager)
    r = as_user(manager).post(
        proposal_url(fund, share), payload(manager_mem, bob_mem), format="json"
    )
    assert r.status_code == 400
    assert share.participations.get().membership_id == alice_mem.pk


def test_cross_fund_membership_rejected(case):
    manager, _, _, outsider, fund, alice_mem, _, other, share = case
    other_mem = FundMembership.objects.get(fund=other, user=outsider)
    r = as_user(manager).post(
        proposal_url(fund, share), payload(alice_mem, other_mem), format="json"
    )
    assert r.status_code == 400


def test_members_and_unauthorized_users_cannot_change_split(case):
    _, alice, bob, outsider, fund, alice_mem, bob_mem, _, share = case
    body = payload(alice_mem, bob_mem)
    url = proposal_url(fund, share)
    assert as_user(alice).post(url, body, format="json").status_code == 403
    assert as_user(bob).post(url, body, format="json").status_code == 403
    assert as_user(outsider).post(url, body, format="json").status_code == 404
    assert as_user().post(url, body, format="json").status_code == 401
    assert as_user(outsider).get(url).status_code == 404
    assert as_user(bob).get(url).status_code == 404  # not yet a participant


def test_disabled_member_and_guest_cannot_be_added_as_new_partner(case):
    manager, _, _, _, fund, alice_mem, bob_mem, _, share = case
    bob_mem.is_active = False
    bob_mem.save(update_fields=["is_active"])
    assert as_user(manager).post(
        proposal_url(fund, share), payload(alice_mem, bob_mem), format="json"
    ).status_code == 400
    guest = FundMembership.objects.create(fund=fund, guest_name="Grandmother")
    assert as_user(manager).post(
        proposal_url(fund, share), payload(alice_mem, guest), format="json"
    ).status_code == 400


def test_participation_policy_freezes_on_activation(case):
    manager, _, _, _, fund, alice_mem, bob_mem, _, share = case
    url = reverse("fund-detail", kwargs={"fund_id": fund.pk})
    client = as_user(manager)
    assert fund.lottery_eligibility_policy == "fully_settled"
    updated = client.patch(url, {"lottery_eligibility_policy": "allow_outstanding"}, format="json")
    assert updated.status_code == 200
    assert updated.data["lottery_eligibility_policy"] == "allow_outstanding"
    # There is no production activation API yet; simulate an activated row.
    Fund.objects.filter(pk=fund.pk).update(status=Fund.Status.ACTIVE)
    assert client.patch(url, {"lottery_eligibility_policy": "fully_settled"}, format="json").status_code == 409
    assert as_user(manager).post(
        proposal_url(fund, share), payload(alice_mem, bob_mem), format="json"
    ).status_code == 409
    fund.refresh_from_db()
    assert fund.lottery_eligibility_policy == "allow_outstanding"


def test_invalid_policy_rejected(case):
    manager, _, _, _, fund, *_ = case
    r = as_user(manager).patch(
        reverse("fund-detail", kwargs={"fund_id": fund.pk}),
        {"lottery_eligibility_policy": "anything"}, format="json"
    )
    assert r.status_code == 400


def test_database_prevents_duplicate_membership_for_same_share(case):
    _, _, _, _, _, alice_mem, _, _, share = case
    with pytest.raises(IntegrityError), transaction.atomic():
        ShareParticipation.objects.create(share=share, membership=alice_mem, units=1)


def test_database_rejects_out_of_range_units(case):
    _, _, _, _, _, _, bob_mem, _, share = case
    with pytest.raises(IntegrityError), transaction.atomic():
        ShareParticipation.objects.create(share=share, membership=bob_mem, units=13)


def test_transaction_rolls_back_on_audit_failure(case):
    manager, _, _, _, fund, alice_mem, bob_mem, _, share = case
    with (
        patch("apps.shares.participation_services.AuditLog.objects.create", side_effect=RuntimeError("boom")),
        pytest.raises(RuntimeError, match="boom"),
    ):
        as_user(manager).post(
            proposal_url(fund, share), payload(alice_mem, bob_mem), format="json"
        )
    share.refresh_from_db()
    assert share.participation_revision_id is None
    assert list(share.participations.values_list("membership_id", "units")) == [(alice_mem.pk, 12)]
