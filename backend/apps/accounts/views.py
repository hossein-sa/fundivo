"""Public OTP endpoints; all other DRF endpoints remain authenticated by default."""

from drf_spectacular.utils import extend_schema
from redis.exceptions import RedisError
from rest_framework import status
from rest_framework.exceptions import APIException, PermissionDenied, Throttled
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from .otp import (
    OTPAccountDisabled,
    OTPInvalid,
    OTPTooManyRequests,
    OTPUnavailable,
    request_code,
    verify_code,
)
from .otp_delivery import DeliveryUnavailable
from .serializers import (
    OTPRequestResponseSerializer,
    OTPRequestSerializer,
    OTPVerifyResponseSerializer,
    OTPVerifySerializer,
)


class ServiceUnavailable(APIException):
    status_code = 503
    default_detail = "Service temporarily unavailable."
    default_code = "service_unavailable"


class InvalidCode(APIException):
    status_code = 400
    default_detail = "Invalid or expired code."
    default_code = "invalid_code"


def _client_ip(request):
    # Only trust REMOTE_ADDR. Forwarded IP headers require a vetted proxy setup.
    return request.META.get("REMOTE_ADDR", "unknown")


class OTPRequestView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]

    @extend_schema(
        tags=["Authentication"],
        request=OTPRequestSerializer,
        responses={202: OTPRequestResponseSerializer},
        description="Request an OTP. Does not reveal whether an account exists.",
    )
    def post(self, request):
        serializer = OTPRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            request_code(serializer.validated_data["phone_number"], _client_ip(request))
        except OTPTooManyRequests as exc:
            raise Throttled(detail="Too many requests.") from exc
        except (RedisError, OTPUnavailable, DeliveryUnavailable, OSError) as exc:
            raise ServiceUnavailable() from exc
        return Response(
            {"detail": "If delivery is available, a code has been sent."},
            status=status.HTTP_202_ACCEPTED,
        )


class OTPVerifyView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]

    @extend_schema(
        tags=["Authentication"],
        request=OTPVerifySerializer,
        responses={200: OTPVerifyResponseSerializer},
        description="Verify OTP and receive a short-lived, one-use login ticket; not a JWT.",
    )
    def post(self, request):
        serializer = OTPVerifySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        try:
            ticket = verify_code(data["phone_number"], data["code"], _client_ip(request))
        except OTPInvalid as exc:
            raise InvalidCode() from exc
        except OTPTooManyRequests as exc:
            raise Throttled(detail="Too many attempts.") from exc
        except OTPAccountDisabled as exc:
            raise PermissionDenied("Account unavailable.") from exc
        except (RedisError, OTPUnavailable) as exc:
            raise ServiceUnavailable() from exc
        return Response({"login_ticket": ticket, "expires_in": 120})
