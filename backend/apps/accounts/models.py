"""Global identity only; fund-specific roles belong to FundMembership later."""

import uuid
from typing import ClassVar

from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin
from django.core.validators import RegexValidator
from django.db import models
from django.utils import timezone

from .managers import UserManager
from .phone_numbers import normalize_iranian_mobile


class User(AbstractBaseUser, PermissionsMixin):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    phone_number = models.CharField(
        max_length=13,
        unique=True,
        validators=[
            RegexValidator(
                regex=r"^\+989[0-9]{9}$",
                message="Phone number must use the +989XXXXXXXXX format.",
            )
        ],
    )
    is_phone_verified = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    date_joined = models.DateTimeField(default=timezone.now, editable=False)

    objects = UserManager()

    USERNAME_FIELD = "phone_number"
    REQUIRED_FIELDS: ClassVar[list[str]] = []

    class Meta:
        ordering = ("-date_joined",)

    def clean(self):
        super().clean()
        self.phone_number = normalize_iranian_mobile(self.phone_number)

    def save(self, *args, **kwargs):
        self.phone_number = normalize_iranian_mobile(self.phone_number)
        return super().save(*args, **kwargs)

    def __str__(self):
        return self.phone_number
