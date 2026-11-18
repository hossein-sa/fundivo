"""Explicit public input/output fields for invitations."""

from rest_framework import serializers

from apps.accounts.phone_numbers import normalize_iranian_mobile
from apps.funds.serializers import MembershipReadSerializer

from .models import Invitation


class StrictSerializer(serializers.Serializer):
    """Do not silently ignore fields like role, fund_id, or is_active."""

    def to_internal_value(self, data):
        unknown = set(data) - set(self.fields)
        if unknown:
            raise serializers.ValidationError(
                {key: ["Unknown field."] for key in sorted(unknown)}
            )
        return super().to_internal_value(data)


class InvitationCreateSerializer(StrictSerializer):
    phone_number = serializers.CharField(max_length=32)

    def validate_phone_number(self, value):
        try:
            return normalize_iranian_mobile(value)
        except (ValueError, TypeError) as exc:
            raise serializers.ValidationError("Invalid Iranian mobile number.") from exc


class InvitationCodeSerializer(StrictSerializer):
    code = serializers.CharField(min_length=43, max_length=43, trim_whitespace=False)


class InvitationReadSerializer(serializers.ModelSerializer):
    is_expired = serializers.BooleanField(read_only=True)

    class Meta:
        model = Invitation
        fields = ("id", "status", "is_expired", "created_at", "expires_at", "responded_at")
        read_only_fields = fields


class InvitationIssuedSerializer(InvitationReadSerializer):
    invitation_code = serializers.CharField(read_only=True)

    class Meta(InvitationReadSerializer.Meta):
        fields = (*InvitationReadSerializer.Meta.fields, "invitation_code")


class InvitationAcceptedSerializer(serializers.Serializer):
    detail = serializers.CharField(read_only=True)
    membership = MembershipReadSerializer(read_only=True)
