"""Redis-backed, rate-limited, one-time mobile verification and login grants."""

import hashlib
import hmac
import json
import secrets

import redis
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from redis.exceptions import WatchError

from .otp_delivery import deliver_otp


class OTPInvalid(Exception):
    """An incorrect, consumed, or expired code (same public error)."""


class OTPTooManyRequests(Exception):
    """A request or verification rate limit was exceeded."""


class OTPUnavailable(Exception):
    """A Redis operation could not be completed safely."""


class OTPAccountDisabled(Exception):
    """An already-registered account is inactive."""


def get_redis():
    return redis.Redis.from_url(
        settings.REDIS_URL,
        decode_responses=True,
        socket_connect_timeout=2,
        socket_timeout=2,
    )


def _identifier(value: str) -> str:
    """Do not expose raw phone numbers or IP addresses in Redis key names."""
    return hmac.new(
        settings.SECRET_KEY.encode(),
        value.encode(),
        hashlib.sha256,
    ).hexdigest()


def _code_digest(phone: str, code: str) -> str:
    return _identifier(f"otp-code:{phone}:{code}")


def _key(suffix: str) -> str:
    return f"{settings.OTP_REDIS_PREFIX}:{suffix}"


def _limited(redis_client, key: str, limit: int, window: int = 3600) -> bool:
    """A short fixed window: SET NX + INCR, with expiration on the initial key."""
    redis_client.set(key, 0, nx=True, ex=window)
    return redis_client.incr(key) > limit


def request_code(phone: str, client_ip: str) -> None:
    """Rate-limit and send an OTP without exposing account-existence details."""
    client = get_redis()
    phone_tag = _identifier(phone)
    ip_tag = _identifier(client_ip)

    phone_limited = _limited(client, _key(f"req:phone:{phone_tag}"), 3)
    ip_limited = _limited(client, _key(f"req:ip:{ip_tag}"), 20)
    if phone_limited or ip_limited:
        raise OTPTooManyRequests()

    cooldown_key = _key(f"cooldown:{phone_tag}")
    if not client.set(cooldown_key, "1", nx=True, ex=60):
        return  # Always return the same response; no second code is sent.

    code = f"{secrets.randbelow(1_000_000):06d}"
    challenge_key = _key(f"challenge:{phone_tag}")
    challenge = {"digest": _code_digest(phone, code), "remaining": 5}
    client.set(challenge_key, json.dumps(challenge), ex=300)

    try:
        deliver_otp(phone, code)
    except Exception:
        # Never leave a challenge whose code the user could not receive.
        client.delete(challenge_key)
        client.delete(cooldown_key)
        raise


def _consume_challenge(client, phone: str, code: str) -> None:
    """WATCH/MULTI guarantees a code can only be consumed once, even under races."""
    key = _key(f"challenge:{_identifier(phone)}")
    expected = _code_digest(phone, code)

    for _ in range(5):
        try:
            with client.pipeline() as pipe:
                pipe.watch(key)
                encoded = pipe.get(key)
                if encoded is None:
                    raise OTPInvalid()
                challenge = json.loads(encoded)
                matched = hmac.compare_digest(challenge["digest"], expected)
                remaining = int(challenge["remaining"]) - 1

                pipe.multi()
                if matched or remaining <= 0:
                    pipe.delete(key)
                else:
                    challenge["remaining"] = remaining
                    pipe.set(key, json.dumps(challenge), keepttl=True)
                pipe.execute()

                if not matched:
                    raise OTPInvalid()
                return
        except WatchError:
            continue

    raise OTPUnavailable("Concurrent verification contention.")


def _ensure_verified_user(phone: str):
    """Create a passwordless user only after OTP success; keep inactive users inactive."""
    User = get_user_model()
    with transaction.atomic():
        try:
            user = User.objects.select_for_update().get(phone_number=phone)
        except User.DoesNotExist:
            try:
                # Nested savepoint lets us recover from a concurrent unique-key race.
                with transaction.atomic():
                    user = User.objects.create_user(phone_number=phone)
            except (IntegrityError, ValidationError):
                # Concurrent creation; fetch the winning row.
                user = User.objects.select_for_update().get(phone_number=phone)

        if not user.is_active:
            raise OTPAccountDisabled()
        if not user.is_phone_verified:
            user.is_phone_verified = True
            user.save(update_fields=["is_phone_verified"])
        return user


def verify_code(phone: str, code: str, client_ip: str) -> str:
    """Consume OTP, verify identity, then issue a *non-JWT* one-time login ticket."""
    client = get_redis()
    phone_limited = _limited(client, _key(f"verify:phone:{_identifier(phone)}"), 15)
    ip_limited = _limited(client, _key(f"verify:ip:{_identifier(client_ip)}"), 50)
    if phone_limited or ip_limited:
        raise OTPTooManyRequests()

    _consume_challenge(client, phone, code)
    user = _ensure_verified_user(phone)

    ticket = secrets.token_urlsafe(32)
    ticket_digest = hashlib.sha256(ticket.encode()).hexdigest()
    stored = client.set(
        _key(f"ticket:{ticket_digest}"),
        str(user.pk),
        nx=True,
        ex=120,
    )
    if not stored:
        raise OTPUnavailable("Could not allocate a login ticket.")
    return ticket


def consume_login_ticket(ticket: str) -> str | None:
    """Reserved for the JWT exchange endpoint: GETDEL is single-use."""
    ticket_digest = hashlib.sha256(ticket.encode()).hexdigest()
    return get_redis().getdel(_key(f"ticket:{ticket_digest}"))
