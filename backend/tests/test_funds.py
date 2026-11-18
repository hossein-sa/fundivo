"""Fund creation, transaction guarantees, fund-scoped roles and IDOR tests."""

import uuid
from unittest.mock import patch

import pytest
from apps.funds.models import AuditLog, Fund, FundMembership
from apps.funds.services import create_fund
from django.contrib.auth import get_user_model
from django.db import IntegrityError, transaction
from django.urls import reverse
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

pytestmark = pytest.mark.django_db


@pytest.fixture
def actors():
    user_model = get_user_model()
    creator = user_model.objects.create_user("09120000001", is_phone_verified=True)
    member = user_model.objects.create_user("09120000002", is_phone_verified=True)
    outsider = user_model.objects.create_user("09120000003", is_phone_verified=True)
    return creator, member, outsider


def api_client(user=None):
    client = APIClient()
    if user is not None:
        access = str(RefreshToken.for_user(user).access_token)
        client.credentials(HTTP_AUTHORIZATION=f"Bearer {access}")
    return client


@pytest.fixture
def fund_with_roles(actors):
    creator, member, _ = actors
    fund = create_fund(creator=creator, name="Family Fund", description="Initial draft")
    FundMembership.objects.create(fund=fund, user=member, role=FundMembership.Role.MEMBER)
    return fund


def test_anonymous_cannot_list_or_create_funds():
    client = api_client()
    assert client.get(reverse("fund-list")).status_code == 401
    assert client.post(reverse("fund-list"), {"name": "Secret"}, format="json").status_code == 401


def test_creator_becomes_manager_atomically_and_audit_is_recorded(actors):
    creator, _, _ = actors
    r = api_client(creator).post(
        reverse("fund-list"), {"name": "  New Fund  ", "description": "test"}, format="json"
    )
    assert r.status_code == 201
    fund = Fund.objects.get(pk=r.data["id"])
    membership = fund.memberships.get(user=creator)
    assert fund.name == "New Fund"
    assert fund.status == Fund.Status.DRAFT
    assert fund.created_by_id == creator.pk
    assert membership.role == FundMembership.Role.MANAGER
    assert membership.is_active is True
    assert r.data["my_role"] == "manager"
    assert creator.is_staff is False
    log = AuditLog.objects.get(fund=fund, action="fund.created")
    assert log.actor_id == creator.pk
    assert log.changed_fields == ["name", "description"]


def test_create_fund_rolls_back_if_audit_fails(actors):
    creator, _, _ = actors

    with (
        patch(
            "apps.funds.services.AuditLog.objects.create",
            side_effect=RuntimeError("failure"),
        ),
        pytest.raises(RuntimeError, match="failure"),
    ):
        create_fund(creator=creator, name="Rollback test")

    assert not Fund.objects.filter(name="Rollback test").exists()
    assert not FundMembership.objects.filter(user=creator).exists()


@pytest.mark.parametrize("bad_payload", [
    {"name": ""},
    {"name": "   "},
    {"name": "Valid", "status": "active"},
    {"name": "Valid", "created_by": "other"},
])
def test_create_rejects_invalid_or_forbidden_fields(actors, bad_payload):
    creator, _, _ = actors
    r = api_client(creator).post(reverse("fund-list"), bad_payload, format="json")
    assert r.status_code == 400
    assert Fund.objects.count() == 0


def test_unverified_user_cannot_create_even_with_forged_jwt(actors):
    creator, _, _ = actors
    creator.is_phone_verified = False
    creator.save(update_fields=["is_phone_verified"])
    r = api_client(creator).post(reverse("fund-list"), {"name": "Denied"}, format="json")
    assert r.status_code == 401


def test_user_can_be_manager_in_one_fund_and_member_in_another(actors):
    creator, member, _ = actors
    fund_a = create_fund(creator=creator, name="Fund A")
    fund_b = create_fund(creator=member, name="Fund B")
    FundMembership.objects.create(fund=fund_b, user=creator, role=FundMembership.Role.MEMBER)
    r = api_client(creator).get(reverse("fund-list"))
    assert r.status_code == 200
    assert r.data["count"] == 2
    roles = {item["id"]: item["my_role"] for item in r.data["results"]}
    assert roles[str(fund_a.id)] == "manager"
    assert roles[str(fund_b.id)] == "member"


def test_list_and_detail_are_scoped_to_active_members(actors, fund_with_roles):
    creator, member, outsider = actors
    assert api_client(creator).get(reverse("fund-list")).data["count"] == 1
    assert api_client(member).get(reverse("fund-list")).data["count"] == 1
    assert api_client(outsider).get(reverse("fund-list")).data["count"] == 0
    url = reverse("fund-detail", kwargs={"fund_id": fund_with_roles.id})
    assert api_client(outsider).get(url).status_code == 404
    assert api_client(member).get(url).status_code == 200
    assert api_client(outsider).get(reverse("fund-detail", kwargs={"fund_id": uuid.uuid4()})).status_code == 404


def test_inactive_membership_cannot_view_or_update_fund(actors, fund_with_roles):
    _, member, _ = actors
    m = fund_with_roles.memberships.get(user=member)
    m.is_active = False
    m.save(update_fields=["is_active"])
    url = reverse("fund-detail", kwargs={"fund_id": fund_with_roles.id})
    assert api_client(member).get(url).status_code == 404
    assert api_client(member).patch(url, {"name": "Hijack"}, format="json").status_code == 404


def test_manager_can_update_draft_and_audit_names_of_changed_fields(actors, fund_with_roles):
    creator, _, _ = actors
    url = reverse("fund-detail", kwargs={"fund_id": fund_with_roles.id})
    r = api_client(creator).patch(url, {"name": "Updated"}, format="json")
    assert r.status_code == 200
    fund_with_roles.refresh_from_db()
    assert fund_with_roles.name == "Updated"
    log = AuditLog.objects.get(fund=fund_with_roles, action="fund.updated")
    assert log.changed_fields == ["name"]
    assert log.actor == creator
    assert AuditLog.objects.filter(fund=fund_with_roles).count() == 2
    # A no-op update should not create spurious audit entries.
    assert api_client(creator).patch(url, {"name": "Updated"}, format="json").status_code == 200
    assert AuditLog.objects.filter(fund=fund_with_roles).count() == 2


def test_member_cannot_patch_even_when_they_can_read(actors, fund_with_roles):
    _, member, _ = actors
    url = reverse("fund-detail", kwargs={"fund_id": fund_with_roles.id})
    assert api_client(member).patch(url, {"name": "Hijack"}, format="json").status_code == 403
    fund_with_roles.refresh_from_db()
    assert fund_with_roles.name == "Family Fund"


def test_manager_cannot_set_status_or_role_or_remove_fund(actors, fund_with_roles):
    creator, _, _ = actors
    url = reverse("fund-detail", kwargs={"fund_id": fund_with_roles.id})
    c = api_client(creator)
    assert c.patch(url, {"status": "active"}, format="json").status_code == 400
    assert c.patch(url, {"role": "manager"}, format="json").status_code == 400
    assert c.put(url, {"name": "new"}, format="json").status_code == 405
    assert c.delete(url).status_code == 405


def test_non_draft_fund_cannot_be_edited(actors, fund_with_roles):
    creator, _, _ = actors
    Fund.objects.filter(pk=fund_with_roles.pk).update(status=Fund.Status.ACTIVE)
    url = reverse("fund-detail", kwargs={"fund_id": fund_with_roles.id})
    assert api_client(creator).patch(url, {"name": "Changed"}, format="json").status_code == 409


def test_membership_self_endpoint_hides_other_funds(actors, fund_with_roles):
    _, member, outsider = actors
    url = reverse("fund-membership-me", kwargs={"fund_id": fund_with_roles.id})
    r = api_client(member).get(url)
    assert r.status_code == 200
    assert r.data["role"] == "member"
    assert r.data["user_id"] == str(member.pk)
    assert api_client(outsider).get(url).status_code == 404


def test_only_manager_can_list_memberships_without_exposing_phone(actors, fund_with_roles):
    creator, member, outsider = actors
    url = reverse("fund-membership-list", kwargs={"fund_id": fund_with_roles.id})
    r = api_client(creator).get(url)
    assert r.status_code == 200
    assert r.data["count"] == 2
    assert all("phone_number" not in entry for entry in r.data["results"])
    assert api_client(member).get(url).status_code == 403
    assert api_client(outsider).get(url).status_code == 404


def test_database_disallows_duplicate_membership(actors, fund_with_roles):
    creator, _, _ = actors
    with pytest.raises(IntegrityError), transaction.atomic():
        FundMembership.objects.create(
            fund=fund_with_roles, user=creator, role=FundMembership.Role.MEMBER
        )


def test_database_disallows_second_active_manager(actors, fund_with_roles):
    _, member, _ = actors
    with pytest.raises(IntegrityError), transaction.atomic():
        FundMembership.objects.filter(fund=fund_with_roles, user=member).update(role="manager")


def test_manager_identity_cannot_be_changed_using_membership_api(actors, fund_with_roles):
    creator, _, _ = actors
    url = reverse("fund-membership-list", kwargs={"fund_id": fund_with_roles.id})
    assert api_client(creator).post(url, {"role": "manager"}, format="json").status_code == 405


def test_funds_registered_read_only_in_django_admin():
    from apps.funds.admin import AuditLogAdmin, FundAdmin, FundMembershipAdmin
    from django.contrib import admin

    assert Fund in admin.site._registry
    assert FundMembership in admin.site._registry
    assert AuditLog in admin.site._registry
    for model, admin_class in (
            (Fund, FundAdmin),
            (FundMembership, FundMembershipAdmin),
            (AuditLog, AuditLogAdmin),
    ):
        registered = admin.site._registry[model]
        assert isinstance(registered, admin_class)
        assert registered.has_add_permission(None) is False
        assert registered.has_change_permission(None) is False
        assert registered.has_delete_permission(None) is False
