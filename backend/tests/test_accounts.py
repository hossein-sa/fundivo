"""Phone identity, account creation, and minimal admin safety tests."""

import uuid

import pytest
from apps.accounts.phone_numbers import normalize_iranian_mobile
from django.conf import settings
from django.contrib import admin
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError


@pytest.mark.parametrize(
    "raw_phone",
    [
        "09123456789",
        "+989123456789",
        "00989123456789",
        "۹۸۹۱۲۳۴۵۶۷۸۹",
        "۰۹۱۲۳۴۵۶۷۸۹",
    ],
)
def test_phone_normalization(raw_phone):
    assert normalize_iranian_mobile(raw_phone) == "+989123456789"


@pytest.mark.parametrize("invalid", ["", "0912345678", "02112345678", "091234567890"])
def test_invalid_phone_numbers(invalid):
    with pytest.raises(ValueError):
        normalize_iranian_mobile(invalid)


def test_custom_user_is_configured():
    assert settings.AUTH_USER_MODEL == "accounts.User"
    assert get_user_model().USERNAME_FIELD == "phone_number"


@pytest.mark.django_db
def test_user_creation_is_unverified_and_has_no_usable_password():
    user = get_user_model().objects.create_user("09123456789")

    assert isinstance(user.pk, uuid.UUID)
    assert user.phone_number == "+989123456789"
    assert user.is_phone_verified is False
    assert user.is_staff is False
    assert user.is_active is True
    assert user.has_usable_password() is False


@pytest.mark.django_db
def test_duplicate_number_cannot_create_second_account():
    user_model = get_user_model()
    user_model.objects.create_user("09123456789")

    with pytest.raises(ValidationError):
        user_model.objects.create_user("00989123456789")


@pytest.mark.django_db
def test_direct_model_save_also_normalizes_phone():
    user = get_user_model()(phone_number="۰۹۱۲۳۴۵۶۷۸۹")
    user.set_unusable_password()
    user.save()

    assert user.phone_number == "+989123456789"


@pytest.mark.django_db
def test_platform_superuser_has_password_and_staff_permissions():
    user = get_user_model().objects.create_superuser(
        "+989123456789", password="example-strong-admin-password"
    )

    assert user.is_staff is True
    assert user.is_superuser is True
    assert user.check_password("example-strong-admin-password") is True
    assert user.is_phone_verified is False


def test_regular_users_cannot_be_created_with_passwords():
    with pytest.raises(ValueError):
        get_user_model().objects.create_user(
            "09123456789", password="not-allowed"
        )


def test_user_is_registered_in_admin():
    assert get_user_model() in admin.site._registry

@pytest.mark.parametrize("invalid", [None, 123])
def test_phone_number_rejects_invalid_types(invalid):
    with pytest.raises(TypeError):
        normalize_iranian_mobile(invalid)