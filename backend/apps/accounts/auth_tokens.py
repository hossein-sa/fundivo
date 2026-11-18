"""Exchange single-use OTP tickets and enforce verified JWT user identity."""

from django.contrib.auth import get_user_model
from rest_framework.exceptions import AuthenticationFailed
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.exceptions import InvalidToken
from rest_framework_simplejwt.serializers import TokenRefreshSerializer
from rest_framework_simplejwt.settings import api_settings
from rest_framework_simplejwt.tokens import RefreshToken

from .otp import consume_login_ticket


class InvalidLoginTicket(Exception):
    """Ticket expired, consumed, or does not belong to an eligible user."""


def exchange_login_ticket(ticket: str) -> dict[str, str | int]:
    """Consume ticket first, then issue one JWT pair for the verified account."""
    user_id = consume_login_ticket(ticket)
    if user_id is None:
        raise InvalidLoginTicket()

    User = get_user_model()
    try:
        user = User.objects.get(pk=user_id, is_active=True, is_phone_verified=True)
    except (User.DoesNotExist, ValueError, TypeError) as exc:
        raise InvalidLoginTicket() from exc

    refresh = RefreshToken.for_user(user)
    return {
        "access": str(refresh.access_token),
        "refresh": str(refresh),
        "token_type": "Bearer",
        "expires_in": int(api_settings.ACCESS_TOKEN_LIFETIME.total_seconds()),
    }


class VerifiedJWTAuthentication(JWTAuthentication):
    """In addition to Simple JWT checks, require mobile verification."""

    def get_user(self, validated_token):
        user = super().get_user(validated_token)
        if not user.is_phone_verified:
            raise AuthenticationFailed("Authentication credentials are invalid.")
        return user


class VerifiedTokenRefreshSerializer(TokenRefreshSerializer):
    """Refuse refresh when the account is inactive or no longer verified."""

    def validate(self, attrs):
        token = RefreshToken(attrs["refresh"])
        user_id = token.get(api_settings.USER_ID_CLAIM)
        if user_id is None:
            raise InvalidToken("Invalid refresh token.")

        User = get_user_model()
        try:
            user = User.objects.get(**{api_settings.USER_ID_FIELD: user_id})
        except (User.DoesNotExist, ValueError, TypeError) as exc:
            raise InvalidToken("Invalid refresh token.") from exc
        if not user.is_active or not user.is_phone_verified:
            raise InvalidToken("Invalid refresh token.")
        return super().validate(attrs)
