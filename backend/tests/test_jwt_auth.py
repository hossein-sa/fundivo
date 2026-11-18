"""JWT issuance, rotation, blacklist, user isolation, and profile tests."""

import hashlib

import fakeredis
import pytest
from apps.accounts import otp
from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

pytestmark = pytest.mark.django_db
PHONE = "+989123456789"


@pytest.fixture
def auth_context(monkeypatch, settings):
    store = fakeredis.FakeRedis(decode_responses=True)
    outbox = []
    monkeypatch.setattr(otp, "get_redis", lambda: store)
    monkeypatch.setattr(otp, "deliver_otp", lambda phone, code: outbox.append((phone, code)))
    settings.OTP_REDIS_PREFIX = "fundivo:test:jwt"
    return store, outbox


@pytest.fixture
def client():
    return APIClient()


def _issue_tokens(client, auth_context, phone="09123456789"):
    _, outbox = auth_context
    r = client.post(reverse("otp-request"), {"phone_number": phone}, format="json")
    assert r.status_code == 202
    assert outbox
    r = client.post(
        reverse("otp-verify"), {"phone_number": phone, "code": outbox[-1][1]}, format="json"
    )
    assert r.status_code == 200
    ticket = r.data["login_ticket"]
    r = client.post(reverse("auth-token-exchange"), {"login_ticket": ticket}, format="json")
    assert r.status_code == 200
    return r.data, ticket


def _bearer(client, access):
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {access}")


def test_exchange_and_authenticated_profile(client, auth_context):
    tokens, _ = _issue_tokens(client, auth_context)
    assert tokens["token_type"] == "Bearer"
    assert tokens["access"] != tokens["refresh"]
    assert tokens["expires_in"] == 300

    _bearer(client, tokens["access"])
    r = client.get(reverse("users-me"))
    assert r.status_code == 200
    assert r.data["phone_number"] == PHONE
    assert r.data["is_phone_verified"] is True
    assert "id" in r.data
    assert "password" not in r.data
    assert "is_staff" not in r.data


def test_ticket_cannot_be_reused(client, auth_context):
    _, ticket = _issue_tokens(client, auth_context)
    r = client.post(reverse("auth-token-exchange"), {"login_ticket": ticket}, format="json")
    assert r.status_code == 401


@pytest.mark.parametrize("value", ["not-a-valid-ticket", "x" * 43])
def test_invalid_ticket_rejected(client, auth_context, value):
    r = client.post(reverse("auth-token-exchange"), {"login_ticket": value}, format="json")
    assert r.status_code in (400, 401)
    assert "access" not in r.data


def test_expired_ticket_rejected(client, auth_context):
    store, _ = auth_context
    _, ticket = _issue_tokens(client, auth_context)
    store.delete(otp._key(f"ticket:{hashlib.sha256(ticket.encode()).hexdigest()}"))
    r = client.post(reverse("auth-token-exchange"), {"login_ticket": ticket}, format="json")
    assert r.status_code == 401


def test_user_disabled_between_verify_and_exchange(client, auth_context):
    store, outbox = auth_context
    client.post(reverse("otp-request"), {"phone_number": PHONE}, format="json")
    r = client.post(
        reverse("otp-verify"), {"phone_number": PHONE, "code": outbox[-1][1]}, format="json"
    )
    assert r.status_code == 200
    ticket = r.data["login_ticket"]
    user = get_user_model().objects.get(phone_number=PHONE)
    user.is_active = False
    user.save(update_fields=["is_active"])
    r = client.post(reverse("auth-token-exchange"), {"login_ticket": ticket}, format="json")
    assert r.status_code == 401
    assert store.get(otp._key(f"ticket:{hashlib.sha256(ticket.encode()).hexdigest()}")) is None


def test_profile_requires_valid_access_token(client, auth_context):
    assert client.get(reverse("users-me")).status_code == 401
    _bearer(client, "not-a-token")
    assert client.get(reverse("users-me")).status_code == 401


def test_refresh_rotates_and_blacklists_old_token(client, auth_context):
    tokens, _ = _issue_tokens(client, auth_context)
    r = client.post(reverse("auth-token-refresh"), {"refresh": tokens["refresh"]}, format="json")
    assert r.status_code == 200
    assert r.data["access"] != tokens["access"]
    assert r.data["refresh"] != tokens["refresh"]
    assert client.post(reverse("auth-token-refresh"), {"refresh": tokens["refresh"]}, format="json").status_code == 401
    _bearer(client, r.data["access"])
    assert client.get(reverse("users-me")).status_code == 200


def test_logout_revokes_refresh_not_current_access(client, auth_context):
    tokens, _ = _issue_tokens(client, auth_context)
    _bearer(client, tokens["access"])
    assert client.post(reverse("auth-token-logout"), {"refresh": tokens["refresh"]}, format="json").status_code == 204
    assert client.post(reverse("auth-token-refresh"), {"refresh": tokens["refresh"]}, format="json").status_code == 401
    assert client.get(reverse("users-me")).status_code == 200


def test_logout_requires_authorized_access_token(client, auth_context):
    tokens, _ = _issue_tokens(client, auth_context)
    assert client.post(reverse("auth-token-logout"), {"refresh": tokens["refresh"]}, format="json").status_code == 401


def test_cannot_logout_another_users_refresh_token(client, auth_context):
    tokens, _ = _issue_tokens(client, auth_context)
    other = get_user_model().objects.create_user("09120000001", is_phone_verified=True)
    other_refresh = str(RefreshToken.for_user(other))
    _bearer(client, tokens["access"])
    assert client.post(reverse("auth-token-logout"), {"refresh": other_refresh}, format="json").status_code == 403
    assert client.post(reverse("auth-token-refresh"), {"refresh": other_refresh}, format="json").status_code == 200


def test_refresh_denied_for_inactive_user(client, auth_context):
    tokens, _ = _issue_tokens(client, auth_context)
    user = get_user_model().objects.get(phone_number=PHONE)
    user.is_active = False
    user.save(update_fields=["is_active"])
    assert client.post(reverse("auth-token-refresh"), {"refresh": tokens["refresh"]}, format="json").status_code == 401
    _bearer(client, tokens["access"])
    assert client.get(reverse("users-me")).status_code == 401


def test_refresh_and_access_denied_for_unverified_user(client, auth_context):
    tokens, _ = _issue_tokens(client, auth_context)
    user = get_user_model().objects.get(phone_number=PHONE)
    user.is_phone_verified = False
    user.save(update_fields=["is_phone_verified"])
    assert client.post(reverse("auth-token-refresh"), {"refresh": tokens["refresh"]}, format="json").status_code == 401
    _bearer(client, tokens["access"])
    assert client.get(reverse("users-me")).status_code == 401


@pytest.mark.parametrize("name", ["auth-token-exchange", "auth-token-refresh", "auth-token-logout"])
def test_auth_token_operations_are_post_only(client, auth_context, name):
    assert client.get(reverse(name)).status_code in (401, 405)
