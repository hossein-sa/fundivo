"""Input validation is separate from OTP business operations."""

from rest_framework import serializers

from .phone_numbers import normalize_iranian_mobile


class OTPRequestSerializer(serializers.Serializer):
    phone_number = serializers.CharField(max_length=32)

    def validate_phone_number(self, value):
        try:
            return normalize_iranian_mobile(value)
        except (ValueError, TypeError) as exc:
            raise serializers.ValidationError("Enter a valid Iranian mobile number.") from exc


class OTPVerifySerializer(OTPRequestSerializer):
    code = serializers.RegexField(r"^[0-9]{6}$", max_length=6)


class OTPRequestResponseSerializer(serializers.Serializer):
    detail = serializers.CharField(read_only=True)


class OTPVerifyResponseSerializer(serializers.Serializer):
    login_ticket = serializers.CharField(read_only=True)
    expires_in = serializers.IntegerField(read_only=True)
