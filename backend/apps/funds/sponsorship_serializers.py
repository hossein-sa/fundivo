"""Explicit, small API contracts for guest financial sponsorship consent."""

from rest_framework import serializers

from .models import GuestSponsorship


class StrictInputSerializer(serializers.Serializer):
    def to_internal_value(self, data):
        unknown = set(data) - set(self.fields)
        if unknown:
            raise serializers.ValidationError(
                {field: ["Unknown input field."] for field in sorted(unknown)}
            )
        return super().to_internal_value(data)


class SponsorshipCreateSerializer(StrictInputSerializer):
    request_id = serializers.UUIDField()
    guest_name = serializers.CharField(max_length=120, trim_whitespace=True)
    sponsor_membership_id = serializers.UUIDField(required=False)
    accept_responsibility = serializers.BooleanField(default=False)


class SponsorshipAttachSerializer(StrictInputSerializer):
    request_id = serializers.UUIDField()
    sponsor_membership_id = serializers.UUIDField()
    accept_responsibility = serializers.BooleanField(default=False)


class GuestSponsorshipReadSerializer(serializers.ModelSerializer):
    # Keep this as a simple string to avoid an unrelated OpenAPI status-enum collision.
    status = serializers.CharField(read_only=True)
    guest_membership_id = serializers.UUIDField(read_only=True)
    sponsor_membership_id = serializers.UUIDField(read_only=True)
    guest_name = serializers.CharField(source="guest_membership.guest_name", read_only=True)
    guest_is_active = serializers.BooleanField(source="guest_membership.is_active", read_only=True)

    class Meta:
        model = GuestSponsorship
        fields = (
            "id", "request_id", "guest_membership_id", "guest_name", "guest_is_active",
            "sponsor_membership_id", "status", "sponsor_accepted_at", "approved_at",
            "created_at", "updated_at",
        )
        read_only_fields = fields
