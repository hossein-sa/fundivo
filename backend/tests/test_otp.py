"""OTP security and API contract tests with an isolated in-memory Redis."""

import json

import fakeredis
import pytest
from apps.accounts import otp
from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework.test import APIClient

PHONE = "+989123456789"


@pytest.fixture
def otp_context(monkeypatch, settings):
    client = fakeredis.FakeRedis(decode_responses=True)
    outbox = []
    monkeypatch.setattr(otp, "get_redis", lambda: client)
    monkeypatch.setattr(otp, "deliver_otp", lambda phone, code: outbox.append((phone, code)))
    settings.OTP_REDIS_PREFIX = "fundivo:test:otp"
    return client, outbox


@pytest.fixture
def api_client():
    return APIClient()


def _request(api_client, phone="09123456789"):
    return api_client.post(reverse("otp-request"), {"phone_number": phone}, format="json")


def _verify(api_client, code, phone="09123456789"):
    return api_client.post(
        reverse("otp-verify"),
        {"phone_number": phone, "code": code},
        format="json",
    )


def test_request_is_anonymous_and_does_not_disclose_code(api_client, otp_context):
    client, outbox = otp_context
    response = _request(api_client)
    assert response.status_code == 202
    assert len(outbox) == 1
    assert outbox[0][0] == PHONE
    assert outbox[0][1] not in response.content.decode()
    stored = client.get(otp._key(f"challenge:{otp._identifier(PHONE)}"))
    assert "digest" in json.loads(stored)
    assert "code" not in json.loads(stored)
    assert PHONE not in " ".join(client.scan_iter())


def test_request_response_does_not_depend_on_account_existence(
    api_client, otp_context, db
):
    first = _request(api_client)
    assert first.status_code == 202

    User = get_user_model()
    User.objects.create_user("09120000000")
    second = _request(api_client, phone="09120000000")
    assert second.status_code == 202
    assert second.data == first.data


def test_cooldown_does_not_send_a_second_code(api_client, otp_context):
    _, outbox = otp_context
    assert _request(api_client).status_code == 202
    assert _request(api_client).status_code == 202
    assert len(outbox) == 1


def test_request_rate_limit(api_client, otp_context):
    for _ in range(3):
        assert _request(api_client).status_code == 202
    assert _request(api_client).status_code == 429


def test_invalid_phone_and_code_rejected(api_client, otp_context):
    assert _request(api_client, "02112345678").status_code == 400
    assert _verify(api_client, "abcd12").status_code == 400


def test_wrong_code_and_expired_code_have_same_response(api_client, otp_context):
    redis_client, outbox = otp_context
    _request(api_client)
    wrong = _verify(api_client, "000000" if outbox[0][1] != "000000" else "111111")
    assert wrong.status_code == 400

    redis_client.delete(otp._key(f"challenge:{otp._identifier(PHONE)}"))
    expired = _verify(api_client, outbox[0][1])
    assert expired.status_code == 400
    assert expired.data == wrong.data


def test_five_wrong_attempts_destroy_challenge(api_client, otp_context):
    redis_client, outbox = otp_context
    _request(api_client)
    bad = "000000" if outbox[0][1] != "000000" else "111111"
    for _ in range(5):
        assert _verify(api_client, bad).status_code == 400
    key = otp._key(f"challenge:{otp._identifier(PHONE)}")
    assert not redis_client.exists(key)
    assert _verify(api_client, outbox[0][1]).status_code == 400


@pytest.mark.django_db
def test_verify_creates_verified_passwordless_user_and_one_use_ticket(
    api_client, otp_context
):
    _, outbox = otp_context
    _request(api_client)
    response = _verify(api_client, outbox[0][1])
    assert response.status_code == 200
    assert response.data["expires_in"] == 120
    ticket = response.data["login_ticket"]
    assert len(ticket) >= 40
    user = get_user_model().objects.get(phone_number=PHONE)
    assert user.is_phone_verified is True
    assert not user.has_usable_password()
    assert otp.consume_login_ticket(ticket) == str(user.pk)
    assert otp.consume_login_ticket(ticket) is None
    assert _verify(api_client, outbox[0][1]).status_code == 400


@pytest.mark.django_db
def test_verify_reuses_existing_user(api_client, otp_context):
    user = get_user_model().objects.create_user(PHONE)
    _, outbox = otp_context
    _request(api_client)
    assert _verify(api_client, outbox[0][1]).status_code == 200
    user.refresh_from_db()
    assert user.is_phone_verified is True
    assert get_user_model().objects.count() == 1


@pytest.mark.django_db
def test_inactive_user_is_not_reactivated(api_client, otp_context):
    user = get_user_model().objects.create_user(PHONE, is_active=False)
    _, outbox = otp_context
    _request(api_client)
    assert _verify(api_client, outbox[0][1]).status_code == 403
    user.refresh_from_db()
    assert user.is_active is False
    assert user.is_phone_verified is False


def test_verify_without_request_cannot_create_an_account(api_client, otp_context):
    assert _verify(api_client, "123456").status_code == 400


def test_code_data_has_ttl_and_attempt_counter(api_client, otp_context):
    client, _ = otp_context
    _request(api_client)
    key = otp._key(f"challenge:{otp._identifier(PHONE)}")
    value = json.loads(client.get(key))
    assert value["remaining"] == 5
    assert 0 < client.ttl(key) <= 300


def test_no_get_handlers_on_otp_endpoints(api_client, otp_context):
    assert api_client.get(reverse("otp-request")).status_code == 405
    assert api_client.get(reverse("otp-verify")).status_code == 405
