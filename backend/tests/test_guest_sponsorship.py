"""Sponsor consent, manager approval, history safety and guest shares."""

import uuid
from unittest.mock import patch

import pytest
from apps.funds.models import AuditLog, Fund, FundMembership, GuestSponsorship
from apps.funds.services import create_fund
from apps.shares.models import Share, ShareParticipation
from django.contrib.auth import get_user_model
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
    manager = users.objects.create_user("09120000401", is_phone_verified=True)
    ali = users.objects.create_user("09120000402", is_phone_verified=True)
    reza = users.objects.create_user("09120000403", is_phone_verified=True)
    outsider = users.objects.create_user("09120000404", is_phone_verified=True)
    fund = create_fund(creator=manager, name="Sponsored guest test", target_share_count=4)
    manager_mem = FundMembership.objects.get(fund=fund, user=manager)
    ali_mem = FundMembership.objects.create(fund=fund, user=ali)
    reza_mem = FundMembership.objects.create(fund=fund, user=reza)
    other = create_fund(creator=outsider, name="Other Fund", target_share_count=2)
    return manager, ali, reza, outsider, fund, manager_mem, ali_mem, reza_mem, other


def base_url(fund):
    return reverse("fund-guest-sponsorship-list", kwargs={"fund_id": fund.pk})


def request_for(user, fund, **overrides):
    payload = {
        "request_id": str(uuid.uuid4()),
        "guest_name": " Aunt of Ali ",
        "accept_responsibility": True,
    }
    payload.update(overrides)
    return as_user(user).post(base_url(fund), payload, format="json")


def action_url(fund, sponsorship_id, action):
    return reverse(f"fund-guest-sponsorship-{action}", kwargs={
        "fund_id": fund.id, "sponsorship_id": sponsorship_id,
    })


def approve(manager, fund, sponsorship_id):
    return as_user(manager).post(action_url(fund, sponsorship_id, "approve"), {}, format="json")


def allocate(manager, fund, membership_id, count=1):
    return as_user(manager).post(
        reverse("fund-share-list", kwargs={"fund_id": fund.id}),
        {
            "membership_id": str(membership_id),
            "count": count,
            "allocation_id": str(uuid.uuid4()),
        },
        format="json",
    )


def test_member_proposes_with_explicit_consent_and_guest_is_inactive(case):
    _, ali, _, _, fund, _, ali_mem, _, _ = case
    count = get_user_model().objects.count()
    response = request_for(ali, fund)
    assert response.status_code == 201
    assert response.data["status"] == "pending_manager"
    assert response.data["sponsor_membership_id"] == str(ali_mem.pk)
    guest = FundMembership.objects.get(pk=response.data["guest_membership_id"])
    assert guest.user_id is None
    assert guest.guest_name == "Aunt of Ali"
    assert not guest.is_active
    assert get_user_model().objects.count() == count
    assert GuestSponsorship.objects.get(pk=response.data["id"]).sponsor_accepted_at is not None


def test_manager_approval_activates_guest_without_changing_identity(case):
    manager, ali, _, _, fund, _, _, _, _ = case
    created = request_for(ali, fund)
    response = approve(manager, fund, created.data["id"])
    assert response.status_code == 200
    assert response.data["status"] == "active"
    guest = FundMembership.objects.get(pk=created.data["guest_membership_id"])
    assert guest.is_active and guest.user_id is None
    assert GuestSponsorship.objects.get(pk=response.data["id"]).approved_at is not None
    assert AuditLog.objects.filter(fund=fund, action="sponsorship.manager_approved").exists()


def test_non_manager_cannot_approve(case):
    manager, ali, reza, _, fund, _, _, _, _ = case
    created = request_for(ali, fund)
    assert approve(reza, fund, created.data["id"]).status_code == 403
    assert approve(manager, fund, created.data["id"]).status_code == 200


def test_manager_creating_own_guest_is_active_in_one_step(case):
    manager, _, _, _, fund, manager_mem, _, _, _ = case
    response = request_for(manager, fund, guest_name="Manager's mother")
    assert response.status_code == 201
    assert response.data["status"] == "active"
    assert response.data["sponsor_membership_id"] == str(manager_mem.pk)
    assert response.data["guest_is_active"] is True
    assert response.data["sponsor_accepted_at"] is not None
    assert response.data["approved_at"] is not None


def test_manager_proposes_another_sponsor_who_must_accept(case):
    manager, ali, _, _, fund, _, ali_mem, _, _ = case
    response = request_for(manager, fund, sponsor_membership_id=str(ali_mem.pk), accept_responsibility=False)
    assert response.status_code == 201
    assert response.data["status"] == "pending_sponsor"
    assert response.data["guest_is_active"] is False
    assert approve(manager, fund, response.data["id"]).status_code == 409
    accepted = as_user(ali).post(action_url(fund, response.data["id"], "accept"), {}, format="json")
    assert accepted.status_code == 200
    assert accepted.data["status"] == "pending_manager"
    assert approve(manager, fund, response.data["id"]).status_code == 200


def test_manager_cannot_accept_for_another_user(case):
    manager, _, _, _, fund, _, ali_mem, _, _ = case
    r = request_for(manager, fund, sponsor_membership_id=str(ali_mem.pk), accept_responsibility=True)
    assert r.status_code == 400
    assert GuestSponsorship.objects.count() == 0


def test_member_cannot_assign_sponsorship_to_someone_else(case):
    _, ali, _, _, fund, _, _, reza_mem, _ = case
    r = request_for(ali, fund, sponsor_membership_id=str(reza_mem.pk))
    assert r.status_code == 403
    assert GuestSponsorship.objects.count() == 0


def test_self_sponsorship_requires_true_explicit_consent(case):
    _, ali, _, _, fund, _, _, _, _ = case
    r = request_for(ali, fund, accept_responsibility=False)
    assert r.status_code == 400
    assert GuestSponsorship.objects.count() == 0


def test_sponsor_must_be_active_registered_member_in_same_fund(case):
    manager, _, _, outsider, fund, _, ali_mem, _, _ = case
    ali_mem.is_active = False
    ali_mem.save(update_fields=["is_active"])
    r = request_for(manager, fund, sponsor_membership_id=str(ali_mem.pk), accept_responsibility=False)
    assert r.status_code == 404
    other_mem = FundMembership.objects.get(fund__created_by=outsider, user=outsider)
    r = request_for(manager, fund, sponsor_membership_id=str(other_mem.pk), accept_responsibility=False)
    assert r.status_code == 404


def test_unrelated_member_cannot_accept(case):
    manager, _, reza, _, fund, _, ali_mem, _, _ = case
    r = request_for(manager, fund, sponsor_membership_id=str(ali_mem.pk), accept_responsibility=False)
    attempt = as_user(reza).post(action_url(fund, r.data["id"], "accept"), {}, format="json")
    assert attempt.status_code == 403


def test_nonmember_cannot_view_or_create(case):
    _, _, _, outsider, fund, _, _, _, _ = case
    assert as_user(outsider).get(base_url(fund)).status_code == 404
    assert request_for(outsider, fund).status_code == 404
    assert as_user().get(base_url(fund)).status_code == 401


def test_members_see_only_their_own_sponsored_guests(case):
    manager, ali, reza, _, fund, _, _, _, _ = case
    mine = request_for(ali, fund)
    other = request_for(reza, fund, guest_name="Reza's uncle")
    assert mine.status_code == 201 and other.status_code == 201
    ali_list = as_user(ali).get(base_url(fund))
    assert ali_list.status_code == 200 and ali_list.data["count"] == 1
    assert ali_list.data["results"][0]["id"] == mine.data["id"]
    manager_list = as_user(manager).get(base_url(fund))
    assert manager_list.status_code == 200 and manager_list.data["count"] == 2


def test_idempotent_retry_does_not_create_duplicate_guest(case):
    _, ali, _, _, fund, _, _, _, _ = case
    request_id = str(uuid.uuid4())
    one = request_for(ali, fund, request_id=request_id)
    two = request_for(ali, fund, request_id=request_id)
    assert one.status_code == 201 and two.status_code == 200
    assert one.data["id"] == two.data["id"]
    assert FundMembership.objects.filter(fund=fund, user__isnull=True).count() == 1
    assert GuestSponsorship.objects.count() == 1


def test_reused_request_id_with_different_guest_is_conflict(case):
    _, ali, _, _, fund, _, _, _, _ = case
    request_id = str(uuid.uuid4())
    assert request_for(ali, fund, request_id=request_id).status_code == 201
    assert request_for(ali, fund, request_id=request_id, guest_name="Someone else").status_code == 409


def test_unknown_fields_and_blank_name_rejected(case):
    _, ali, _, _, fund, _, _, _, _ = case
    assert request_for(ali, fund, role="manager").status_code == 400
    assert request_for(ali, fund, guest_name=" ").status_code == 400
    assert GuestSponsorship.objects.count() == 0


def test_pending_guest_cannot_be_allocated_a_share(case):
    manager, ali, _, _, fund, _, _, _, _ = case
    response = request_for(ali, fund)
    attempt = allocate(manager, fund, response.data["guest_membership_id"])
    assert attempt.status_code == 404
    assert Share.objects.count() == 0


def test_approved_guest_can_hold_share_and_sponsor_can_view(case):
    manager, ali, reza, _, fund, _, _, _, _ = case
    request = request_for(ali, fund)
    assert approve(manager, fund, request.data["id"]).status_code == 200
    allocation = allocate(manager, fund, request.data["guest_membership_id"])
    assert allocation.status_code == 201
    ali_shares = as_user(ali).get(reverse("fund-share-list", kwargs={"fund_id": fund.id}))
    assert ali_shares.status_code == 200 and ali_shares.data["count"] == 1
    reza_shares = as_user(reza).get(reverse("fund-share-list", kwargs={"fund_id": fund.id}))
    assert reza_shares.status_code == 200 and reza_shares.data["count"] == 0


def test_approved_guest_can_join_fractional_share_proposal(case):
    manager, ali, _, _, fund, _, ali_mem, _, _ = case
    request = request_for(ali, fund)
    approve(manager, fund, request.data["id"])
    allocation = allocate(manager, fund, ali_mem.pk)
    assert allocation.status_code == 201
    share_id = allocation.data["shares"][0]["id"]
    split = as_user(manager).post(
        reverse("fund-share-participations", kwargs={"fund_id": fund.id, "share_id": share_id}),
        {
            "request_id": str(uuid.uuid4()),
            "participants": [
                {"membership_id": str(ali_mem.pk), "units": 6},
                {"membership_id": request.data["guest_membership_id"], "units": 6},
            ],
        },
        format="json",
    )
    assert split.status_code == 201
    assert sum(ShareParticipation.objects.filter(share_id=share_id).values_list("units", flat=True)) == 12


def test_unsponsored_legacy_guest_cannot_join_new_split(case):
    manager, _ali, _, _, fund, _, ali_mem, _, _ = case
    old_guest = FundMembership.objects.create(fund=fund, user=None, guest_name="Legacy")
    allocation = allocate(manager, fund, ali_mem.pk)
    share_id = allocation.data["shares"][0]["id"]
    split = as_user(manager).post(
        reverse("fund-share-participations", kwargs={"fund_id": fund.id, "share_id": share_id}),
        {"request_id": str(uuid.uuid4()), "participants": [
            {"membership_id": str(ali_mem.pk), "units": 6},
            {"membership_id": str(old_guest.pk), "units": 6},
        ]},
        format="json",
    )
    assert split.status_code == 400


def test_legacy_guest_attachment_preserves_existing_share(case):
    manager, _, _, _, fund, manager_mem, _, _, _ = case
    old_guest = FundMembership.objects.create(fund=fund, user=None, guest_name="Existing aunt")
    allocation = allocate(manager, fund, old_guest.pk)
    assert allocation.status_code == 201
    before = Share.objects.get(pk=allocation.data["shares"][0]["id"])
    attach_url = reverse("fund-guest-sponsorship-attach", kwargs={
        "fund_id": fund.id, "guest_id": old_guest.id,
    })
    payload = {
        "request_id": str(uuid.uuid4()),
        "sponsor_membership_id": str(manager_mem.pk),
        "accept_responsibility": True,
    }
    added = as_user(manager).post(attach_url, payload, format="json")
    assert added.status_code == 201
    assert added.data["status"] == "active"
    retry = as_user(manager).post(attach_url, payload, format="json")
    assert retry.status_code == 200 and retry.data["id"] == added.data["id"]
    before.refresh_from_db()
    old_guest.refresh_from_db()
    assert before.membership_id == old_guest.pk
    assert old_guest.is_active
    assert ShareParticipation.objects.get(share=before).units == 12


def test_existing_guest_cannot_be_assigned_two_sponsors(case):
    manager, _, _, _, fund, manager_mem, ali_mem, _, _ = case
    old_guest = FundMembership.objects.create(fund=fund, user=None, guest_name="Existing")
    url = reverse("fund-guest-sponsorship-attach", kwargs={
        "fund_id": fund.id, "guest_id": old_guest.id,
    })
    first = as_user(manager).post(url, {
        "request_id": str(uuid.uuid4()),
        "sponsor_membership_id": str(manager_mem.pk),
        "accept_responsibility": True,
    }, format="json")
    assert first.status_code == 201
    second = as_user(manager).post(url, {
        "request_id": str(uuid.uuid4()),
        "sponsor_membership_id": str(ali_mem.pk),
        "accept_responsibility": False,
    }, format="json")
    assert second.status_code == 409


def test_regular_member_cannot_attach_existing_guest(case):
    _, ali, _, _, fund, _, ali_mem, _, _ = case
    old_guest = FundMembership.objects.create(fund=fund, user=None, guest_name="Existing")
    url = reverse("fund-guest-sponsorship-attach", kwargs={
        "fund_id": fund.id, "guest_id": old_guest.id,
    })
    r = as_user(ali).post(url, {
        "request_id": str(uuid.uuid4()),
        "sponsor_membership_id": str(ali_mem.pk),
        "accept_responsibility": True,
    }, format="json")
    assert r.status_code == 403


def test_sponsor_or_manager_can_reject_pending_request(case):
    manager, ali, _, _, fund, _, ali_mem, _, _ = case
    created = request_for(manager, fund, sponsor_membership_id=str(ali_mem.pk), accept_responsibility=False)
    reject = as_user(ali).post(action_url(fund, created.data["id"], "reject"), {}, format="json")
    assert reject.status_code == 200
    assert reject.data["status"] == "rejected"
    assert reject.data["guest_is_active"] is False
    assert approve(manager, fund, created.data["id"]).status_code == 409


def test_active_sponsorship_cannot_be_rejected(case):
    manager, _, _, _, fund, _, _, _, _ = case
    created = request_for(manager, fund)
    reject = as_user(manager).post(action_url(fund, created.data["id"], "reject"), {}, format="json")
    assert reject.status_code == 409


def test_non_draft_fund_rejects_request_and_decisions(case):
    manager, ali, _, _, fund, _, _, _, _ = case
    created = request_for(ali, fund)
    Fund.objects.filter(pk=fund.pk).update(status=Fund.Status.ACTIVE)
    assert request_for(ali, fund).status_code == 409
    assert approve(manager, fund, created.data["id"]).status_code == 409


def test_audit_failure_rolls_back_guest_and_sponsorship(case):
    _, ali, _, _, fund, _, _, _, _ = case
    with (
        patch("apps.funds.sponsorship_services.AuditLog.objects.create", side_effect=RuntimeError("audit failure")),
        pytest.raises(RuntimeError, match="audit failure"),
    ):
        request_for(ali, fund)
    assert GuestSponsorship.objects.count() == 0
    assert FundMembership.objects.filter(fund=fund, user__isnull=True).count() == 0
