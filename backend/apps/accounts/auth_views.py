"""JWT exchange/rotation/revocation endpoints and an authenticated profile."""

from drf_spectacular.utils import extend_schema
from redis.exceptions import RedisError
from rest_framework import status
from rest_framework.exceptions import APIException, PermissionDenied
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError
from rest_framework_simplejwt.settings import api_settings
from rest_framework_simplejwt.tokens import RefreshToken

from .auth_serializers import (
    LoginTicketExchangeSerializer,
    LogoutSerializer,
    RefreshInputSerializer,
    RefreshOutputSerializer,
    TokenPairSerializer,
    UserProfileSerializer,
)
from .auth_tokens import (
    InvalidLoginTicket,
    VerifiedTokenRefreshSerializer,
    exchange_login_ticket,
)


class InvalidSessionCredentials(APIException):
    """Explicit 401 for public endpoints without authentication backends."""

    status_code = 401
    default_detail = "Invalid or expired credentials."
    default_code = "invalid_credentials"


class TokenServiceUnavailable(APIException):
    status_code = 503
    default_detail = "Authentication service temporarily unavailable."
    default_code = "service_unavailable"


class LoginTicketExchangeView(APIView):
    authentication_classes = ()
    permission_classes = (AllowAny,)

    @extend_schema(
        tags=["Authentication"],
        request=LoginTicketExchangeSerializer,
        responses={200: TokenPairSerializer},
        description="Consume a one-use OTP login ticket and issue JWT access/refresh tokens.",
    )
    def post(self, request):
        serializer = LoginTicketExchangeSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            tokens = exchange_login_ticket(serializer.validated_data["login_ticket"])
        except InvalidLoginTicket as exc:
            raise InvalidSessionCredentials("Invalid or expired login ticket.") from exc
        except RedisError as exc:
            raise TokenServiceUnavailable() from exc
        return Response(tokens)


class SessionRefreshView(APIView):
    authentication_classes = ()
    permission_classes = (AllowAny,)

    @extend_schema(
        tags=["Authentication"],
        request=RefreshInputSerializer,
        responses={200: RefreshOutputSerializer},
        description="Rotate refresh token; blacklist the previous one.",
    )
    def post(self, request):
        serializer = VerifiedTokenRefreshSerializer(data=request.data)
        try:
            serializer.is_valid(raise_exception=True)
        except (InvalidToken, TokenError) as exc:
            raise InvalidSessionCredentials("Invalid refresh token.") from exc
        return Response(serializer.validated_data)


class SessionLogoutView(APIView):
    @extend_schema(
        tags=["Authentication"],
        request=LogoutSerializer,
        responses={204: None},
        description=(
            "Blacklist the supplied refresh token belonging to the current user. "
            "Already-issued access tokens expire naturally; they are not immediately revoked."
        ),
    )
    def post(self, request):
        serializer = LogoutSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            refresh = RefreshToken(serializer.validated_data["refresh"])
            owner_id = refresh.get(api_settings.USER_ID_CLAIM)
            if str(owner_id) != str(request.user.pk):
                raise PermissionDenied("Refresh token does not belong to this user.")
            refresh.blacklist()
        except TokenError as exc:
            raise InvalidToken("Invalid refresh token.") from exc
        return Response(status=status.HTTP_204_NO_CONTENT)


class UserMeView(APIView):
    @extend_schema(
        tags=["Users"],
        responses={200: UserProfileSerializer},
        description="Read the authenticated user's own public profile fields.",
    )
    def get(self, request):
        return Response(UserProfileSerializer(request.user).data)
