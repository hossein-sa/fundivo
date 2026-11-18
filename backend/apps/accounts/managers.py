"""Creation rules for OTP-only end users and password-based platform admins."""

from django.contrib.auth.base_user import BaseUserManager

from .phone_numbers import normalize_iranian_mobile


class UserManager(BaseUserManager):
    use_in_migrations = True

    def create_user(self, phone_number: str, password=None, **extra_fields):
        if password is not None:
            raise ValueError("Regular users must authenticate using OTP, not a password.")

        extra_fields.setdefault("is_staff", False)
        extra_fields.setdefault("is_superuser", False)
        if extra_fields["is_staff"] or extra_fields["is_superuser"]:
            raise ValueError("Use create_superuser() for platform administrators.")

        user = self.model(
            phone_number=normalize_iranian_mobile(phone_number),
            **extra_fields,
        )
        user.set_unusable_password()
        user.full_clean()
        user.save(using=self._db)
        return user

    def create_superuser(self, phone_number: str, password: str, **extra_fields):
        if not password:
            raise ValueError("A platform administrator must have a password.")

        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("is_active", True)

        for field in ("is_staff", "is_superuser", "is_active"):
            if extra_fields[field] is not True:
                raise ValueError(f"A superuser must have {field}=True.")

        user = self.model(
            phone_number=normalize_iranian_mobile(phone_number),
            **extra_fields,
        )
        user.set_password(password)
        user.full_clean()
        user.save(using=self._db)
        return user
