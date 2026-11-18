"""Public authentication contracts and the read-only profile response."""

from rest_framework import serializers


class LoginTicketExchangeSerializer(serializers.Serializer):
    login_ticket = serializers.CharField(min_length=40, max_length=128, trim_whitespace=False)


class TokenPairSerializer(serializers.Serializer):
    access = serializers.CharField(read_only=True)
    refresh = serializers.CharField(read_only=True)
    token_type = serializers.CharField(read_only=True)
    expires_in = serializers.IntegerField(read_only=True)


class RefreshInputSerializer(serializers.Serializer):
    refresh = serializers.CharField(trim_whitespace=False)


class RefreshOutputSerializer(serializers.Serializer):
    access = serializers.CharField(read_only=True)
    refresh = serializers.CharField(read_only=True)


class LogoutSerializer(serializers.Serializer):
    refresh = serializers.CharField(trim_whitespace=False)


class UserProfileSerializer(serializers.Serializer):
    id = serializers.UUIDField(read_only=True)
    phone_number = serializers.CharField(read_only=True)
    is_phone_verified = serializers.BooleanField(read_only=True)
    date_joined = serializers.DateTimeField(read_only=True)
