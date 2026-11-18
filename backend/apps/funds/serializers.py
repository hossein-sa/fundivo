"""Explicit public Fund API fields; never expose private user attributes."""

from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers

from .models import Fund, FundMembership


class StrictWriteSerializer(serializers.ModelSerializer):
    """Reject unknown/read-only fields instead of silently ignoring them."""

    def to_internal_value(self, data):
        unknown = set(data) - set(self.fields)
        if unknown:
            raise serializers.ValidationError(
                {key: ["This field cannot be written."] for key in sorted(unknown)}
            )
        return super().to_internal_value(data)

    def validate_target_share_count(self, value):
        if value is not None and value < 1:
            raise serializers.ValidationError("Target share count must be positive.")
        return value

    def validate_name(self, value):
        cleaned = value.strip()
        if not cleaned:
            raise serializers.ValidationError("A non-empty fund name is required.")
        return cleaned


class FundCreateSerializer(StrictWriteSerializer):
    class Meta:
        model = Fund
        fields = ("name", "description", "target_share_count")


class FundEditSerializer(StrictWriteSerializer):
    class Meta:
        model = Fund
        fields = ("name", "description", "target_share_count")


class FundReadSerializer(serializers.ModelSerializer):
    my_role = serializers.SerializerMethodField()

    class Meta:
        model = Fund
        fields = (
            "id", "name", "description", "target_share_count", "status", "created_at", "updated_at", "my_role"
        )
        read_only_fields = fields

    @extend_schema_field(serializers.CharField(allow_null=True))
    def get_my_role(self, obj):
        request = self.context.get("request")
        if request is None or not request.user.is_authenticated:
            return None
        return FundMembership.objects.filter(
            fund=obj, user=request.user, is_active=True
        ).values_list("role", flat=True).first()


class MembershipReadSerializer(serializers.ModelSerializer):
    user_id = serializers.UUIDField(read_only=True)

    class Meta:
        model = FundMembership
        fields = ("id", "user_id", "role", "is_active", "joined_at")
        read_only_fields = fields
