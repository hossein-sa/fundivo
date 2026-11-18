"""A local development-only OTP delivery adapter; no console/log output."""

import json
import os
from pathlib import Path

from django.conf import settings


class DeliveryUnavailable(Exception):
    """No safe OTP delivery provider is currently configured."""


def deliver_otp(phone: str, code: str) -> None:
    """Local outbox only. Replace with an SMS provider adapter before deployment."""
    backend = getattr(settings, "OTP_DELIVERY_BACKEND", "disabled")
    if backend != "local_file" or not settings.DEBUG:
        raise DeliveryUnavailable("OTP delivery is not configured.")

    path = Path(settings.BASE_DIR) / ".otp-outbox"
    flags = os.O_WRONLY | os.O_CREAT | os.O_APPEND
    descriptor = os.open(path, flags, 0o600)
    with os.fdopen(descriptor, "a", encoding="utf-8") as outbox:
        outbox.write(json.dumps({"phone_number": phone, "code": code}) + "\n")
